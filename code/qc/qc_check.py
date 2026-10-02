#!/usr/bin/env python3
"""Controle de qualidade automático dos dados de laboratório (§4.4, §4.12, §4.17), com os critérios de
config/qc_criteria.yaml.

Verificações por síntese (pass / warn / fail):
  * UV-Vis: metadados obrigatórios (diluição, caminho óptico, tempo), janela de tempo, faixa linear de absorbância,
    linha de base em 800 nm (espalhamento/agregação), duplicata de leitura (RMS relativo), branco de GO presente
    para sínteses com GO, λ_LSPR plausível;
  * TEM: nº de partículas suficiente;
  * dispersão de GO: idade no uso;
  * síntese: preparação única (alíquotas da mesma preparação não contam como sínteses independentes).
Cartas de controle (deriva entre dias) nos controles sem GO / de referência: fase I com os primeiros N controles,
Shewhart (±kσ) e EWMA (Roberts 1959; detecta deriva lenta que o Shewhart perde). Controle fora de controle marca
`warn` em todas as sínteses do mesmo bloco (dia).

Saídas: <lab>/qc_results.csv (synthesis_id, check, status, value, limit, message) e <lab>/qc_control_chart.csv.
O AuNP Designer exclui do ajuste as sínteses com algum `fail` (designer.usable_syntheses).

Uso:
    python code/qc/qc_check.py datasets/lab [--criteria config/qc_criteria.yaml]
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "code", "spectral"))
DEFAULT_CRITERIA = os.path.join(ROOT, "config", "qc_criteria.yaml")
COLUMNS = ["synthesis_id", "check", "status", "value", "limit", "message"]


def load_criteria(path: str | None = None) -> dict:
    import yaml
    with open(path or DEFAULT_CRITERIA, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _read(lab: str, table: str) -> pd.DataFrame:
    p = os.path.join(lab, f"{table}.csv")
    return pd.read_csv(p) if os.path.exists(p) else pd.DataFrame()


def _row(sid, check, status, value="", limit="", message=""):
    return {"synthesis_id": sid, "check": check, "status": status, "value": value, "limit": limit, "message": message}


def _num(x):
    try:
        v = float(x)
        return v if np.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def check_uvvis(lab: str, syn: pd.DataFrame, spectra: pd.DataFrame, crit: dict) -> list[dict]:
    import uvvis
    c = crit["uvvis"]
    out = []
    uv = spectra[spectra.get("technique", pd.Series(dtype=str)).astype(str) == "UV-Vis"] if not spectra.empty else spectra
    blanks = set(syn.loc[syn["is_control"].fillna("").astype(str) == "GO_blank", "go_batch_id"].dropna().astype(str)) \
        if "is_control" in syn else set()
    for _, s in syn.iterrows():
        sid = s["synthesis_id"]
        if str(s.get("is_control", "")) == "GO_blank":
            continue
        rows = uv[uv["synthesis_id"].astype(str) == str(sid)] if not uv.empty else uv
        if rows.empty:
            out.append(_row(sid, "uvvis_present", "fail", 0, ">=1", "síntese sem espectro UV-Vis (resposta primária)"))
            continue
        r0 = rows.iloc[0]
        miss = [m for m in c["require_metadata"] if _num(r0.get(m)) is None]
        out.append(_row(sid, "uvvis_metadata", "warn" if miss else "pass", "|".join(miss), "",
                        f"metadados ausentes: {miss}" if miss else ""))
        t = _num(r0.get("time_after_prep_min"))
        if t is not None:
            lo, hi = c["time_after_prep_min"]
            out.append(_row(sid, "uvvis_time_window", "pass" if lo <= t <= hi else "warn", t, f"[{lo}, {hi}]",
                            "" if lo <= t <= hi else "leitura fora da janela do SOP"))
        go_b = "" if pd.isna(s.get("go_batch_id")) else str(s.get("go_batch_id"))
        if c.get("require_blank_for_GO") and go_b:
            has_blank = rows.get("blank_spectrum_id", pd.Series(dtype=str)).notna().any() or go_b in blanks
            out.append(_row(sid, "uvvis_go_blank", "pass" if has_blank else "warn", int(has_blank), "1",
                            "" if has_blank else f"sem branco de GO tratado do lote {go_b}"))
        spec = []
        for _, r in rows.iterrows():
            f = os.path.join(lab, str(r.get("file", "")))
            if os.path.exists(f):
                spec.append(uvvis.read_spectrum(f))
        if not spec:
            out.append(_row(sid, "uvvis_raw_file", "fail", 0, "exists", "arquivo bruto do espectro não encontrado"))
            continue
        w, a = spec[0]
        amax = float(np.nanmax(a))
        am = c["absorbance_max"]
        st = "fail" if amax > am["fail_above"] else ("warn" if amax > am["warn_above"] or amax < am["warn_below"] else "pass")
        out.append(_row(sid, "uvvis_absorbance_range", st, round(amax, 4),
                        f"[{am['warn_below']}, {am['warn_above']}] (fail > {am['fail_above']})",
                        {"fail": "saturação", "warn": "fora da faixa linear/sinal fraco"}.get(st, "")))
        a800 = float(np.interp(800.0, w, a)) if w.min() <= 800 <= w.max() else None
        if a800 is not None and amax > 0:
            ratio = a800 / amax
            lim = c["baseline_800_over_max"]["warn_above"]
            out.append(_row(sid, "uvvis_baseline_800", "warn" if ratio > lim else "pass", round(ratio, 4), f"<= {lim}",
                            "espalhamento/agregação ou fundo não subtraído" if ratio > lim else ""))
        try:
            lam = uvvis.lspr(w, a)["LSPR_nm"]
            lo, hi = c["lspr_nm"]
            ok = lam is not None and lo <= lam <= hi
            out.append(_row(sid, "uvvis_lspr_plausible", "pass" if ok else "warn", round(lam, 2) if lam else "",
                            f"[{lo}, {hi}]", "" if ok else "banda plasmônica ausente ou deslocada"))
        except Exception as exc:  # noqa: BLE001
            out.append(_row(sid, "uvvis_lspr_plausible", "warn", "", "", f"λ_LSPR não determinado ({exc})"))
        dr = c["duplicate_reads"]
        if len(spec) >= dr["required"]:
            (w1, a1), (w2, a2) = spec[0], spec[1]
            a2i = np.interp(w1, w2, a2)
            rel = float(np.sqrt(np.mean((a1 - a2i) ** 2)) / max(np.nanmax(a1), 1e-9))
            st = "fail" if rel > dr["fail_relative_rms"] else ("warn" if rel > dr["max_relative_rms"] else "pass")
            out.append(_row(sid, "uvvis_duplicate_reads", st, round(rel, 4), f"<= {dr['max_relative_rms']}",
                            "" if st == "pass" else "leituras repetidas discordam"))
        else:
            out.append(_row(sid, "uvvis_duplicate_reads", "warn", len(spec), f">= {dr['required']}",
                            "SOP-UVVIS-01 pede leitura em duplicata"))
    return out


def check_tem(syn: pd.DataFrame, char: pd.DataFrame, crit: dict) -> list[dict]:
    if char.empty or "technique" not in char:
        return []
    c = crit["tem"]["min_particles"]
    out = []
    tem = char[char["technique"].astype(str) == "TEM"]
    for sid, g in tem.groupby("synthesis_id"):
        n = g.loc[g["quantity"] == "n_particles", "value"]
        n = _num(n.iloc[0]) if len(n) else _num(g["n_replicates"].max()) if "n_replicates" in g else None
        if n is None:
            continue
        st = "fail" if n < c["fail_below"] else ("warn" if n < c["warn_below"] else "pass")
        out.append(_row(sid, "tem_particle_count", st, int(n), f">= {c['warn_below']} (fail < {c['fail_below']})",
                        "" if st == "pass" else "poucas partículas para a distribuição de tamanho"))
    return out


def check_go_age(lab: str, syn: pd.DataFrame, crit: dict) -> list[dict]:
    gs = _read(lab, "go_samples")
    if gs.empty or "age_days" not in gs or "go_sample_id" not in syn:
        return []
    age = dict(zip(gs["go_sample_id"].astype(str), gs["age_days"]))
    lim = crit["go_dispersion"]["max_age_days"]
    out = []
    for _, s in syn.iterrows():
        a = _num(age.get(str(s.get("go_sample_id", ""))))
        if a is not None:
            out.append(_row(s["synthesis_id"], "go_dispersion_age", "warn" if a > lim else "pass", a, f"<= {lim}",
                            "dispersão de GO velha" if a > lim else ""))
    return out


def check_preparations(syn: pd.DataFrame, crit: dict) -> list[dict]:
    if not crit["synthesis"].get("unique_preparation") or "preparation_id" not in syn:
        return []
    out = []
    p = syn["preparation_id"].fillna("").astype(str).str.strip()     # pandas 3: astype(str) mantém NaN
    dup = p[(p != "") & p.duplicated(keep=False)]
    for sid, prep in zip(syn.loc[dup.index, "synthesis_id"], dup):
        out.append(_row(sid, "independent_preparation", "fail", prep, "única",
                        "mesma preparação registrada como sínteses diferentes (alíquotas não são sínteses novas)"))
    return out


def control_chart(syn: pd.DataFrame, char: pd.DataFrame, crit: dict) -> pd.DataFrame:
    """Cartas Shewhart + EWMA nos controles sem GO/de referência, na ordem de execução."""
    cc = crit["control_chart"]
    if char.empty or "is_control" not in syn:
        return pd.DataFrame()
    ctl = syn[syn["is_control"].astype(str).isin(["no_GO", "reference"])].copy()
    if ctl.empty:
        return pd.DataFrame()
    sort = [c for c in ("date", "block", "run_order") if c in ctl]
    ctl = ctl.sort_values(sort) if sort else ctl
    rows = []
    lam, L, k, n0 = cc["ewma_lambda"], cc["ewma_L"], cc["shewhart_k"], int(cc["baseline_points"])
    for q in cc["quantities"]:
        vals = char[char["quantity"] == q].groupby("synthesis_id")["value"].mean()
        x = ctl["synthesis_id"].map(vals)
        sub = ctl.assign(x=x).dropna(subset=["x"])
        if len(sub) < 3:
            continue
        base = sub["x"].iloc[:n0]
        mu, sd = float(base.mean()), float(base.std(ddof=1)) if len(base) > 1 else 0.0
        sd = sd if sd > 0 else max(abs(mu) * 1e-3, 1e-9)
        z = mu
        for t, (_, r) in enumerate(sub.iterrows(), start=1):
            z = lam * r["x"] + (1 - lam) * z
            lim = L * sd * np.sqrt(lam / (2 - lam) * (1 - (1 - lam) ** (2 * t)))
            rows.append({"synthesis_id": r["synthesis_id"], "block": r.get("block", ""), "quantity": q, "value": r["x"],
                         "center": mu, "sd_phase1": sd, "phase": "I" if t <= n0 else "II",
                         "shewhart_out": bool(abs(r["x"] - mu) > k * sd), "ewma": z,
                         "ewma_out": bool(abs(z - mu) > lim)})
    return pd.DataFrame(rows)


def run(lab: str, criteria: str | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    crit = load_criteria(criteria)
    syn = _read(lab, "aunp_syntheses")
    if syn.empty:
        raise SystemExit(f"{lab}: sem aunp_syntheses.csv")
    if "status" in syn:
        syn = syn[syn["status"].astype(str).isin(["done", "repeated", "nan", ""]) | syn["status"].isna()]
    char = _read(lab, "aunp_characterization")
    rows = (check_uvvis(lab, syn, _read(lab, "spectra"), crit) + check_tem(syn, char, crit)
            + check_go_age(lab, syn, crit) + check_preparations(syn, crit))
    chart = control_chart(syn, char, crit)
    if not chart.empty:
        bad = chart[(chart["phase"] == "II") & (chart["shewhart_out"] | chart["ewma_out"])]
        for _, b in bad.iterrows():
            day = syn.loc[syn.get("block", pd.Series("", index=syn.index)).astype(str) == str(b["block"]), "synthesis_id"]
            for sid in day:
                rows.append(_row(sid, f"control_chart_day_{b['quantity']}", "warn", round(float(b["value"]), 4), f"{b['quantity']} sob "
                                 "controle", f"controle {b['synthesis_id']} fora de controle ({b['quantity']}) no "
                                 f"bloco {b['block']}: possível deriva do dia"))
    res = pd.DataFrame(rows, columns=COLUMNS)
    sev = res["status"].map({"fail": 0, "warn": 1, "pass": 2})          # uma linha por (síntese, verificação): a pior
    res = res.assign(_s=sev).sort_values("_s").drop_duplicates(["synthesis_id", "check"]).drop(columns="_s")
    return res.sort_values(["synthesis_id", "check"]).reset_index(drop=True), chart


def failed_syntheses(lab: str) -> set:
    """Sínteses com algum `fail` em <lab>/qc_results.csv (vazio se o QC ainda não rodou)."""
    p = os.path.join(lab, "qc_results.csv")
    if not os.path.exists(p):
        return set()
    q = pd.read_csv(p)
    return set(q.loc[q["status"] == "fail", "synthesis_id"].astype(str))


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("lab")
    ap.add_argument("--criteria")
    a = ap.parse_args(argv)
    res, chart = run(a.lab, a.criteria)
    res.to_csv(os.path.join(a.lab, "qc_results.csv"), index=False)
    if not chart.empty:
        chart.to_csv(os.path.join(a.lab, "qc_control_chart.csv"), index=False)
    worst = res.groupby("synthesis_id")["status"].agg(lambda s: "fail" if (s == "fail").any() else
                                                      ("warn" if (s == "warn").any() else "pass"))
    print(f"{len(worst)} sínteses: {worst.value_counts().to_dict()}; verificações: "
          f"{res.groupby(['check', 'status']).size().unstack(fill_value=0).to_dict(orient='index')}")
    for _, r in res[res["status"] == "fail"].iterrows():
        print(f"FAIL  {r['synthesis_id']}: {r['check']} — {r['message']} ({r['value']})")
    if not chart.empty:
        ooc = chart[(chart["phase"] == "II") & (chart["shewhart_out"] | chart["ewma_out"])]
        print(f"carta de controle: {len(chart)} pontos, {len(ooc)} fora de controle")
    print(f"-> {os.path.join(a.lab, 'qc_results.csv')}")


if __name__ == "__main__":
    main()
