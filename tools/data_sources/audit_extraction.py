#!/usr/bin/env python3
"""Auditoria da extração de receitas/propriedades da literatura (§4.1): precisão de campos, taxa de campos ausentes,
concordância com referência e calibração da confiança — antes de usar dados minerados para priorizar a campanha.

Três etapas:
  1. `physics` — auditoria automática, sem humano: consistência físico-química entre campos. Para AuNP esféricas,
     o λ do pico plasmônico extraído é comparado com o previsto pelo tamanho extraído (Mie com as constantes de
     Johnson & Christy, code/spectral/mie.py); grandes desvios indicam erro de extração (ou morfologia não esférica).
     Também confere faixas plausíveis (tamanho 1–500 nm, λ 380–1100 nm) e coerência entre texto e valor.
  2. `sample` — amostra ESTRATIFICADA (fonte × menção a GO × campo preenchido/vazio) para anotação humana: uma planilha
     com o valor extraído, o trecho de evidência e colunas em branco `correct` (1/0) e `present_in_source` (1/0, para
     campos vazios) — mede precisão E taxa de ausência falsa.
  3. `score` — lê a planilha anotada e calcula, por campo e por fonte, precisão e taxa de ausência falsa com IC 95 %
     de Wilson, concordância entre dois anotadores (κ de Cohen, se houver `correct_2`) e precisão por nível de
     confiança declarado (calibração).
A proposta usa os dados minerados como priorização, não como substitutos das medidas (§4.1): o relatório diz em
quais campos se pode confiar e quanto.

Uso:
    python tools/data_sources/audit_extraction.py physics [--out outputs/audit/physics.csv]
    python tools/data_sources/audit_extraction.py sample --n-per-stratum 8 --out outputs/audit/anotar.csv
    python tools/data_sources/audit_extraction.py score outputs/audit/anotar.csv
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SEED = os.path.join(ROOT, "datasets", "literature-seed", "aunp_literature_seed.csv")
OUT = os.path.join(ROOT, "outputs", "audit")
FIELDS = {   # campo auditado -> coluna de evidência mostrada ao anotador
    "gold_precursor": "gold_precursor_amount", "reductants": "actions", "capping_ligands": "actions",
    "size_nm": "size_text", "abs_peak_nm": "abs_peak_text", "morphology_class": "morphology_raw",
    "mentions_graphene_oxide": "supports",
}
SPHERE_LIKE = ("sphere", "particle")
PURE_AU = r"(?i)^(?!.*(?:@|core|shell|alloy|\bAg\b|\bPt\b|\bPd\b|\bCu\b|silver|platinum)).*(?:\bAu\b|gold)"


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z ** 2 / n
    c = (p + z ** 2 / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / den
    return (max(0.0, c - h), min(1.0, c + h))


def cohen_kappa(a, b) -> float:
    a, b = np.asarray(a, int), np.asarray(b, int)
    po = np.mean(a == b)
    pe = np.mean(a) * np.mean(b) + (1 - np.mean(a)) * (1 - np.mean(b))
    return float((po - pe) / (1 - pe)) if pe < 1 else float("nan")


def load_seed(path: str = SEED) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str).fillna("")


# ---------------------------------------------------------------------------------------------- física

def lspr_from_size_table(d_grid=np.arange(2, 201, 1.0)) -> pd.Series:
    """λ do máximo de extinção (Mie, Au em água, dispersão 10 %) para cada diâmetro da grade."""
    sys.path.insert(0, os.path.join(ROOT, "code", "spectral"))
    import mie
    wl = np.arange(450.0, 800.0, 1.0)
    return pd.Series([wl[np.argmax(mie.ensemble_extinction(wl, d, 0.10, n_sizes=5))] for d in d_grid], index=d_grid)


def physics_audit(seed: pd.DataFrame, tol_nm: float = 25.0) -> pd.DataFrame:
    """Uma linha por registro com tamanho E pico: λ previsto pelo tamanho × λ extraído, e flags de plausibilidade."""
    s = pd.to_numeric(seed["size_nm"], errors="coerce")
    pure = seed["product"].str.contains(PURE_AU, regex=True)
    a = pd.to_numeric(seed["abs_peak_nm"], errors="coerce")
    table = lspr_from_size_table()
    rows = []
    for i in seed.index:
        flags = []
        if np.isfinite(s[i]) and not 1 <= s[i] <= 500:
            flags.append("tamanho_implausivel")
        if np.isfinite(a[i]) and not 380 <= a[i] <= 1100:
            flags.append("pico_implausivel")
        pred = np.nan
        sphere = any(m in seed.at[i, "morphology_class"] for m in SPHERE_LIKE) and not any(
            m in seed.at[i, "morphology_class"] for m in ("rod", "star", "shell", "plate", "prism", "triangle", "wire"))
        if sphere and np.isfinite(s[i]) and np.isfinite(a[i]) and 5 <= s[i] <= 200 and pure[i]:
            pred = float(table.iloc[int(np.argmin(np.abs(table.index - s[i])))])
            if abs(a[i] - pred) > tol_nm:
                flags.append("pico_incoerente_com_tamanho")
        if flags or np.isfinite(pred):
            rows.append({"seed_id": seed.at[i, "seed_id"], "source": seed.at[i, "source"], "doi": seed.at[i, "doi"],
                         "size_nm": s[i], "abs_peak_nm": a[i], "lspr_pred_mie_nm": pred,
                         "residual_nm": a[i] - pred if np.isfinite(pred) else np.nan, "flags": "|".join(flags),
                         "size_text": seed.at[i, "size_text"][:120], "abs_peak_text": seed.at[i, "abs_peak_text"][:120]})
    return pd.DataFrame(rows)


def physics_summary(df: pd.DataFrame) -> dict:
    out = {}
    for src, g in df.groupby("source"):
        chk = g[np.isfinite(g["lspr_pred_mie_nm"])]
        k = int(chk["flags"].str.contains("pico_incoerente").sum())
        out[src] = {"pares_tamanho_pico_esfericos": int(len(chk)), "incoerentes": k,
                    "fracao_coerente": 1 - k / len(chk) if len(chk) else float("nan"),
                    "ic95_fracao_coerente": wilson(len(chk) - k, len(chk)),
                    "residuo_mediano_nm": float(chk["residual_nm"].median()) if len(chk) else float("nan"),
                    "implausiveis": int(g["flags"].str.contains("implausivel").sum())}
    return out


# ---------------------------------------------------------------------------------------------- amostra

def stratified_sample(seed: pd.DataFrame, n_per_stratum: int = 8, rng_seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(rng_seed)
    rows = []
    for field, ev in FIELDS.items():
        filled = seed[field].astype(str).str.strip().ne("") & seed[field].astype(str).ne("0") \
            if field != "mentions_graphene_oxide" else seed[field].eq("1")
        for (src, go), g in seed.assign(_f=filled).groupby(["source", "mentions_graphene_oxide"]):
            for f_state, gg in g.groupby("_f"):
                take = gg.iloc[rng.permutation(len(gg))[:n_per_stratum]]
                for _, r in take.iterrows():
                    rows.append({"seed_id": r["seed_id"], "source": src, "mentions_GO": go, "doi": r["doi"],
                                 "title": r["title"][:120], "field": field, "extracted_value": r[field],
                                 "extracted_empty": int(not f_state), "evidence": str(r.get(ev, ""))[:300],
                                 "confidence": r.get("confidence", ""), "stratum_size": len(gg),
                                 "correct": "", "present_in_source": "", "correct_2": "", "annotator": "", "notes": ""})
    df = pd.DataFrame(rows)
    return df.iloc[rng.permutation(len(df))].reset_index(drop=True)   # ordem aleatória: evita vício de ordem


def score(sheet: pd.DataFrame) -> dict:
    """Precisão (campos preenchidos) e taxa de ausência falsa (campos vazios que existiam na fonte), por campo e
    fonte, ponderadas pelo tamanho do estrato (estimativa para a semente inteira) e com IC de Wilson (não ponderado)."""
    sh = sheet.copy()
    out = {"por_campo": {}, "calibracao_por_confianca": {}, "kappa": {}}
    for field, g in sh.groupby("field"):
        filled = g[(g["extracted_empty"].astype(int) == 0) & g["correct"].astype(str).isin(["0", "1"])]
        empty = g[(g["extracted_empty"].astype(int) == 1) & g["present_in_source"].astype(str).isin(["0", "1"])]
        k, n = int(filled["correct"].astype(int).sum()), len(filled)
        m, ne = int(empty["present_in_source"].astype(int).sum()), len(empty)
        w = filled["stratum_size"].astype(float)
        out["por_campo"][field] = {
            "n_anotados": n, "precisao": k / n if n else float("nan"), "ic95": wilson(k, n),
            "precisao_ponderada": float(np.average(filled["correct"].astype(int), weights=w)) if n else float("nan"),
            "n_vazios_anotados": ne, "ausencia_falsa": m / ne if ne else float("nan"), "ic95_ausencia": wilson(m, ne),
            "por_fonte": {s: {"n": len(x), "precisao": float(x["correct"].astype(int).mean())}
                          for s, x in filled.groupby("source")}}
        both = filled[filled["correct_2"].astype(str).isin(["0", "1"])]
        if len(both) >= 5:
            out["kappa"][field] = cohen_kappa(both["correct"].astype(int), both["correct_2"].astype(int))
    ann = sh[sh["correct"].astype(str).isin(["0", "1"]) & (sh["extracted_empty"].astype(int) == 0)]
    for conf, g in ann.groupby("confidence"):
        k, n = int(g["correct"].astype(int).sum()), len(g)
        out["calibracao_por_confianca"][conf or "sem_rotulo"] = {"n": n, "precisao": k / n, "ic95": wilson(k, n)}
    return out


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    ph = sub.add_parser("physics")
    ph.add_argument("--tol-nm", type=float, default=25.0)
    ph.add_argument("--out", default=os.path.join(OUT, "physics_audit.csv"))
    sa = sub.add_parser("sample")
    sa.add_argument("--n-per-stratum", type=int, default=8)
    sa.add_argument("--seed", type=int, default=0)
    sa.add_argument("--out", default=os.path.join(OUT, "amostra_para_anotar.csv"))
    sc = sub.add_parser("score")
    sc.add_argument("sheet")
    a = ap.parse_args(argv)
    if a.cmd == "physics":
        df = physics_audit(load_seed(), a.tol_nm)
        os.makedirs(os.path.dirname(a.out), exist_ok=True)
        df.to_csv(a.out, index=False)
        print(json.dumps(physics_summary(df), indent=1, ensure_ascii=False, default=float))
        print(f"-> {os.path.relpath(a.out, ROOT)}")
    elif a.cmd == "sample":
        df = stratified_sample(load_seed(), a.n_per_stratum, a.seed)
        os.makedirs(os.path.dirname(a.out), exist_ok=True)
        df.to_csv(a.out, index=False)
        print(f"{len(df)} itens ({df['field'].nunique()} campos) -> {os.path.relpath(a.out, ROOT)}; preencha `correct` "
              f"(campos preenchidos) e `present_in_source` (campos vazios), depois rode `score`")
    else:
        print(json.dumps(score(pd.read_csv(a.sheet, dtype=str).fillna("")), indent=1, ensure_ascii=False,
                         default=float))


if __name__ == "__main__":
    main()
