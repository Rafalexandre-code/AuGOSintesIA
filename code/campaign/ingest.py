#!/usr/bin/env python3
"""Ingestão: medidas brutas → aunp_characterization.csv e outcomes.csv (o que o AuNP Designer lê) — §4.4, §4.17.

Sem este passo, J (o objetivo principal) teria de ser digitado à mão a partir da saída do uvvis.py, sem conferência
com o arquivo bruto. Aqui tudo é DERIVADO dos arquivos registrados, com as regras do pré-registro, e pode ser
refeito e conferido a qualquer momento (`check`).

1. UV-Vis (spectra.csv, técnica UV-Vis, com synthesis_id): cada leitura é corrigida (branco, diluição, caminho
   óptico) e dá J (Eq. 1, alvo/faixa/sₘ/normalização do pré-registro), LSPR, A_LSPR, FWHM e o tamanho pelo ajuste
   do espectro inteiro por Mie (spectral/mie.py fit_size_distribution: ensemble log-normal + fundo do GO). Leituras
   repetidas da mesma síntese (duplicata da SOP-UVVIS-01) viram média; o desvio entre leituras fica em
   aunp_characterization (repetibilidade do instrumento). Em outcomes, J vai SEM incerteza: a leitura repetida não
   mede a variação entre preparações, e o GP deve inferi-la (designer.py noise-check decide sobre heteroscedasticidade).
2. Tamanho (objetivo size_mean_nm): da TEM quando existe. A TEM cobre só ~30 das 60 sínteses (§4.12) e o Designer
   precisa de todos os objetivos — sem este passo, DESCARTARIA as demais. Nas sínteses sem TEM, o tamanho vem do
   ajuste de Mie CALIBRADO contra a TEM do próprio laboratório (ridge de ln d_TEM em [ln d_Mie, LSPR, FWHM,
   GO mg/mL]); a incerteza registrada é o erro leave-one-out da calibração, então o GP pesa esses pontos menos que os
   da TEM. Com menos de MIN_PAIRS pares, usa o Mie sem calibração com incerteza UNCALIBRATED_REL (aviso). No
   simulador o ajuste de Mie erra ~9 % em d — otimista, porque dados e ajuste usam o mesmo Mie; daí a calibração.
3. Restrição size_cv: SÓ da TEM — a dispersão não é identificável pelo UV-Vis (correlação ≈ 0,15 no simulador).
   Sínteses sem TEM ficam sem CV; o GP dessa restrição usa só as medidas (designer.py aceita a lacuna).
4. Restrição A_LSPR: do UV-Vis (média das leituras).

Uso:
    python code/campaign/ingest.py add datasets/lab saida_tem.csv [saida_dls.csv ...]   # linhas de tem.py/dls.py --out
    python code/campaign/ingest.py derive datasets/lab            # mostra o que seria gravado
    python code/campaign/ingest.py derive datasets/lab --write    # grava aunp_characterization + outcomes
    python code/campaign/ingest.py check datasets/lab             # confere outcomes.csv × arquivos brutos (código 1 se diverge)
"""
from __future__ import annotations

import argparse
import os
import sys
import warnings

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path[:0] = [HERE, os.path.join(ROOT, "code", "spectral")]
import mie  # noqa: E402
import prereg  # noqa: E402
import uvvis  # noqa: E402

VERSION = "ingest-1"
MIN_PAIRS = 6
UNCALIBRATED_REL = 0.30
UV_QUANTITIES = ("spectral_loss_J", "LSPR_nm", "A_LSPR", "LSPR_FWHM_nm", "d_Haiss_ratio_nm", "d_Mie_nm")


def _read(lab: str, table: str) -> pd.DataFrame:
    p = os.path.join(lab, f"{table}.csv")
    return pd.read_csv(p) if os.path.exists(p) else pd.DataFrame()


def _num(v, default=float("nan")) -> float:
    v = pd.to_numeric(v, errors="coerce")
    return float(v) if pd.notna(v) else default


# ---------------------------------------------------------------------------------------------- UV-Vis

def read_uvvis(lab: str, cfg: dict | None = None) -> pd.DataFrame:
    """Uma linha por leitura de UV-Vis de síntese: J, LSPR, A_LSPR, FWHM, d_Haiss e d_Mie (espectro corrigido)."""
    cfg = cfg or prereg.load()
    sp = _read(lab, "spectra")
    if sp.empty:
        return pd.DataFrame()
    sp["synthesis_id"] = sp["synthesis_id"].fillna("").astype(str) if "synthesis_id" in sp else ""
    files = dict(zip(sp["spectrum_id"].astype(str), sp["file"].astype(str)))
    uv = sp[(sp["technique"].astype(str) == "UV-Vis") & (sp["synthesis_id"] != "")]
    rows = []
    for _, r in uv.iterrows():
        path = os.path.join(lab, str(r["file"]))
        if not os.path.exists(path):
            raise FileNotFoundError(f"spectra.csv → {r['spectrum_id']}: arquivo bruto ausente ({r['file']})")
        w, A = uvvis.read_spectrum(path)
        blank = None
        bid = str(r.get("blank_spectrum_id", "") or "")
        if bid and bid != "nan":
            if bid not in files:
                raise KeyError(f"{r['spectrum_id']}: blank_spectrum_id {bid!r} não está em spectra.csv")
            blank = uvvis.read_spectrum(os.path.join(lab, files[bid]))
        A = uvvis.correct(w, A, blank, _num(r.get("dilution_factor"), 1.0), _num(r.get("path_length_mm"), 10.0))
        d = uvvis.lspr(w, A)
        f = mie.fit_size_distribution(w, A)
        rows.append({"spectrum_id": r["spectrum_id"], "synthesis_id": r["synthesis_id"],
                     "spectral_loss_J": prereg.spectral_loss(w, A, cfg),
                     **{k: d[k] for k in ("LSPR_nm", "A_LSPR", "LSPR_FWHM_nm", "d_Haiss_ratio_nm")},
                     "d_Mie_nm": f["d_post_mean_nm"], "d_Mie_sd_log": f["d_post_sd_log"]})
    return pd.DataFrame(rows)


def uv_summary(readings: pd.DataFrame) -> pd.DataFrame:
    """Média por síntese e desvio entre leituras (repetibilidade)."""
    g = readings.groupby("synthesis_id")
    m = g[list(UV_QUANTITIES) + ["d_Mie_sd_log"]].mean()
    s = g[list(UV_QUANTITIES)].std(ddof=1).add_suffix("_sd")
    return m.join(s).join(g.size().rename("n_readings")).join(g["spectrum_id"].first().rename("spectrum_id"))


# ---------------------------------------------------------------------------------------------- TEM e calibração

def tem_table(lab: str) -> pd.DataFrame:
    """size_mean_nm, size_cv e a incerteza da média (sem) por síntese; com várias medidas, a de mais partículas."""
    cols = ["size_mean_nm", "size_mean_sem", "size_cv", "tem_ids"]
    ch = _read(lab, "aunp_characterization")
    if ch.empty:
        return pd.DataFrame(columns=cols)
    t = ch[ch["technique"].astype(str) == "TEM"].copy()
    t["n"] = pd.to_numeric(t["n_replicates"], errors="coerce").fillna(0) if "n_replicates" in t else 0
    out = {}
    for sid, g in t.groupby("synthesis_id"):
        def pick(q):
            x = g[g["quantity"] == q].sort_values("n")
            return x.iloc[-1] if len(x) else None
        mean, sd, cv = pick("size_mean_nm"), pick("size_sd_nm"), pick("size_cv")
        if mean is None:
            continue
        cv_v = _num(cv["value"]) if cv is not None else (_num(sd["value"]) / _num(mean["value"]) if sd is not None
                                                          else float("nan"))
        ids = [x["measurement_id"] for x in (mean, sd, cv) if x is not None]
        out[sid] = {"size_mean_nm": _num(mean["value"]), "size_mean_sem": _num(mean.get("uncertainty")),
                    "size_cv": cv_v, "tem_ids": "|".join(map(str, ids))}
    return pd.DataFrame.from_dict(out, orient="index", columns=cols)


def _features(uv: pd.DataFrame, syn: pd.DataFrame) -> pd.DataFrame:
    f = pd.DataFrame(index=uv.index)
    f["ln_d_mie"] = np.log(uv["d_Mie_nm"])
    f["LSPR_nm"] = uv["LSPR_nm"]
    f["LSPR_FWHM_nm"] = uv["LSPR_FWHM_nm"]
    go = pd.to_numeric(syn.set_index("synthesis_id")["GO_mg_mL"], errors="coerce") if "GO_mg_mL" in syn else None
    f["GO_mg_mL"] = go.reindex(uv.index).fillna(0.0) if go is not None else 0.0
    return f


def _ridge_loo(X: np.ndarray, y: np.ndarray, lam: float) -> tuple[np.ndarray, float, float]:
    """Ridge em X padronizado; devolve (coef com intercepto, média, dp), erro LOO exato (matriz chapéu) e R² LOO."""
    mu, sd = X.mean(0), X.std(0)
    sd[sd == 0] = 1.0
    Z = np.c_[np.ones(len(X)), (X - mu) / sd]
    P = np.eye(Z.shape[1]) * lam
    P[0, 0] = 0.0
    G = np.linalg.solve(Z.T @ Z + P, Z.T)
    beta = G @ y
    loo = (y - Z @ beta) / np.clip(1 - np.diag(Z @ G), 1e-6, None)
    return np.r_[beta, mu, sd], float(np.sqrt(np.mean(loo ** 2))), float(1 - np.mean(loo ** 2) / max(np.var(y), 1e-12))


def calibrate(feat: pd.DataFrame, target: pd.Series, lams=(0.1, 1.0, 10.0, 100.0)) -> dict | None:
    """UV-Vis → TEM: escolhe λ pelo erro LOO; devolve o modelo e o erro de previsão (para a incerteza)."""
    ok = feat.notna().all(1) & target.notna()
    X, y = feat[ok].to_numpy(float), target[ok].to_numpy(float)
    if len(y) < MIN_PAIRS:
        return None
    lam, params, rmse, r2 = min(((lam, *_ridge_loo(X, y, lam)) for lam in lams), key=lambda t: t[2])
    k = X.shape[1]
    return {"lambda": lam, "beta": params[:k + 1], "mu": params[k + 1:2 * k + 1], "sd": params[2 * k + 1:],
            "loo_rmse": rmse, "loo_r2": r2, "n_pairs": int(len(y))}


def predict(model: dict, feat: pd.DataFrame) -> pd.Series:
    Z = (feat.to_numpy(float) - model["mu"]) / model["sd"]
    return pd.Series(model["beta"][0] + Z @ model["beta"][1:], index=feat.index)


# ---------------------------------------------------------------------------------------------- derivação

def derive(lab: str, cfg: dict | None = None) -> dict:
    """Calcula as linhas derivadas (sem gravar): {'characterization', 'outcomes', 'calibration', 'readings',
    'warnings'}."""
    cfg = cfg or prereg.load()
    syn = _read(lab, "aunp_syntheses")
    if syn.empty:
        raise SystemExit(f"{lab}: aunp_syntheses.csv vazio ou ausente")
    status = syn["status"].astype(str) if "status" in syn else pd.Series("done", index=syn.index)
    done = syn[~status.isin(["planned", "failed"])]
    readings = read_uvvis(lab, cfg)
    uv = uv_summary(readings) if not readings.empty else pd.DataFrame()
    tem = tem_table(lab)
    warn = []
    no_uv = sorted(set(done["synthesis_id"].astype(str)) - set(uv.index))
    if no_uv:
        warn.append(f"{len(no_uv)} síntese(s) feita(s) sem UV-Vis em spectra.csv: {no_uv[:5]}{'…' * (len(no_uv) > 5)}")
    sha = prereg.sha256(cfg)
    objectives = {o["name"]: o for o in cfg["objectives"]}
    cons = prereg.constraints(cfg)
    char = []
    for sid, r in uv.iterrows():
        for q in UV_QUANTITIES:
            if not np.isfinite(r[q]):
                continue
            sd = r[f"{q}_sd"]
            char.append({"measurement_id": f"M-UV-{sid}-{q}", "synthesis_id": sid, "technique": "UV-Vis",
                         "quantity": q, "spectrum_id": r["spectrum_id"], "value": float(r[q]),
                         "uncertainty": float(sd) if np.isfinite(sd) else "",
                         "uncertainty_type": "sd" if np.isfinite(sd) else "", "n_replicates": int(r["n_readings"]),
                         "unit": "nm" if q.endswith("_nm") else "a.u.",
                         "method_details": f"{VERSION}: média de {int(r['n_readings'])} leitura(s); prereg {sha[:12]}",
                         "notes": "derivado (code/campaign/ingest.py)"})
    # tamanho: TEM quando há; senão Mie do UV-Vis calibrado na TEM. CV: só TEM.
    cal = {"size": None}
    pred_size = pd.Series(dtype=float)
    if not uv.empty:
        feat = _features(uv, done)
        cal["size"] = calibrate(feat, np.log(tem.reindex(feat.index)["size_mean_nm"].astype(float)))
        if cal["size"]:
            pred_size = predict(cal["size"], feat.dropna())
        elif set(uv.index) - set(tem.index):
            warn.append(f"calibração UV-Vis→TEM do tamanho: menos de {MIN_PAIRS} pares com UV-Vis e TEM — sínteses "
                        f"sem TEM usam o ajuste de Mie sem calibração (incerteza {100 * UNCALIBRATED_REL:.0f} %)")
    outc = []
    for sid in sorted(set(uv.index) | set(tem.index)):
        rows = []
        if sid in uv.index:
            rows.append(("spectral_loss_J", uv.loc[sid, "spectral_loss_J"], "", f"M-UV-{sid}-spectral_loss_J", "UV-Vis"))
        if sid in tem.index and np.isfinite(tem.loc[sid, "size_mean_nm"]):
            t = tem.loc[sid]
            rows.append(("size_mean_nm", t["size_mean_nm"], t["size_mean_sem"], t["tem_ids"], "TEM"))
            if np.isfinite(t["size_cv"]):
                rows.append(("size_cv", t["size_cv"], "", t["tem_ids"], "TEM"))
        elif sid in pred_size.index:
            d = float(np.exp(pred_size[sid]))
            m = cal["size"]
            rows.append(("size_mean_nm", d, d * m["loo_rmse"], f"M-UV-{sid}-d_Mie_nm",
                         f"UV-Vis (Mie) calibrado na TEM (n={m['n_pairs']}, erro LOO {100 * m['loo_rmse']:.0f} %)"))
        elif sid in uv.index and np.isfinite(uv.loc[sid, "d_Mie_nm"]):
            d = float(uv.loc[sid, "d_Mie_nm"])
            rel = float(np.hypot(UNCALIBRATED_REL, uv.loc[sid, "d_Mie_sd_log"]))
            rows.append(("size_mean_nm", d, d * rel, f"M-UV-{sid}-d_Mie_nm", "UV-Vis (Mie) sem calibração"))
        if sid in uv.index and np.isfinite(uv.loc[sid, "A_LSPR"]):
            rows.append(("A_LSPR", uv.loc[sid, "A_LSPR"], "", f"M-UV-{sid}-A_LSPR", "UV-Vis"))
        for name, value, unc, src, how in rows:
            if name in objectives:
                direction, target = objectives[name]["direction"], objectives[name].get("target", "")
            elif name in cons:
                lo, hi = cons[name]
                direction, target = "constraint", hi if hi is not None else lo
            else:
                continue
            unc = _num(unc)
            outc.append({"synthesis_id": sid, "objective": name, "value": float(value),
                         "uncertainty": unc if np.isfinite(unc) else "", "direction": direction,
                         "target_value": "" if target is None else target, "derived_from": src,
                         "model_version": f"{VERSION}/prereg:{sha[:12]}", "notes": f"fonte: {how}"})
    return {"characterization": pd.DataFrame(char), "outcomes": pd.DataFrame(outc), "calibration": cal,
            "readings": readings, "warnings": warn}


# ---------------------------------------------------------------------------------------------- gravação e conferência

def _is_derived(df: pd.DataFrame, col: str) -> pd.Series:
    v = df[col] if col in df else pd.Series("", index=df.index)
    return v.fillna("").astype(str).str.startswith(VERSION)


def compare(lab: str, new: pd.DataFrame, rtol: float = 1e-6, atol: float = 1e-9) -> pd.DataFrame:
    """Linhas de outcomes.csv cujo valor difere do derivado, que faltam ou que não são deriváveis dos brutos."""
    old = _read(lab, "outcomes")
    cols = ["synthesis_id", "objective", "value", "recorded", "status"]
    if old.empty:
        return new.assign(recorded=np.nan, status="ausente")[cols]
    key = ["synthesis_id", "objective"]
    m = new[key + ["value"]].merge(old[key + ["value"]].rename(columns={"value": "recorded"}), on=key, how="outer",
                                   indicator=True)
    same = np.isclose(pd.to_numeric(m["value"]), pd.to_numeric(m["recorded"]), rtol=rtol, atol=atol)
    m["status"] = np.where(m["_merge"] == "left_only", "ausente",
                           np.where(m["_merge"] == "right_only", "não derivável", np.where(same, "ok", "diverge")))
    keep = m["objective"].isin(set(new["objective"]))       # objetivos que a ingestão não produz ficam fora
    return m[keep & (m["status"] != "ok")][cols]


def write(lab: str, res: dict, force: bool = False) -> None:
    """Substitui as linhas derivadas por esta ferramenta; valores digitados que divergirem exigem force=True."""
    o = res["outcomes"]
    if not o.empty and not force:
        old = _read(lab, "outcomes")
        if not old.empty:
            manual = old[~_is_derived(old, "model_version")][["synthesis_id", "objective"]]
            diff = compare(lab, o).merge(manual, on=["synthesis_id", "objective"])
            diff = diff[diff["status"] == "diverge"]
            if len(diff):
                raise SystemExit("outcomes.csv tem valores digitados que divergem dos derivados dos arquivos brutos "
                                 f"({len(diff)}):\n{diff.head(20).to_string(index=False)}\n"
                                 "Confira; para substituir pelos derivados use --force.")
    for table, df, key in (("aunp_characterization", res["characterization"], ["measurement_id"]),
                           ("outcomes", o, ["synthesis_id", "objective"])):
        if df.empty:
            continue
        old = _read(lab, table)
        if not old.empty:
            old = old.merge(df[key], on=key, how="left", indicator=True)
            df = pd.concat([old[old["_merge"] == "left_only"].drop(columns="_merge"), df], ignore_index=True)
        df.to_csv(os.path.join(lab, f"{table}.csv"), index=False)


def add_rows(lab: str, files: list[str], table: str = "aunp_characterization") -> int:
    """Acrescenta linhas geradas por tem.py/dls.py/… --out; measurement_id repetido com valor diferente é erro."""
    old = _read(lab, table)
    new = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    if "measurement_id" not in new:
        raise SystemExit("arquivo sem measurement_id: não é saída de uma ferramenta de caracterização")
    syn = _read(lab, "aunp_syntheses")
    known = set(syn["synthesis_id"].astype(str)) if "synthesis_id" in syn else set()
    if "synthesis_id" in new:
        bad = sorted(set(new["synthesis_id"].dropna().astype(str)) - known - {""})
        if bad:
            raise SystemExit(f"synthesis_id inexistente(s) em aunp_syntheses.csv: {bad}")
    n_old = len(old)
    if not old.empty:
        same = new.merge(old[["measurement_id", "value"]], on="measurement_id", suffixes=("", "_old"))
        conflict = same[~np.isclose(pd.to_numeric(same["value"]), pd.to_numeric(same["value_old"]))]
        if len(conflict):
            raise SystemExit(f"measurement_id já existe com outro valor: {conflict['measurement_id'].tolist()}")
        new = pd.concat([old, new[~new["measurement_id"].isin(old["measurement_id"])]], ignore_index=True)
    new.to_csv(os.path.join(lab, f"{table}.csv"), index=False)
    return int(len(new) - n_old)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a_ = sub.add_parser("add", help="acrescenta linhas de tem.py/dls.py/… --out")
    a_.add_argument("lab")
    a_.add_argument("files", nargs="+")
    d_ = sub.add_parser("derive", help="deriva J, LSPR, tamanho (TEM ou UV-Vis calibrado) → outcomes")
    d_.add_argument("lab")
    d_.add_argument("--write", action="store_true")
    d_.add_argument("--force", action="store_true", help="substitui valores digitados que divergem")
    c_ = sub.add_parser("check", help="confere outcomes.csv contra os arquivos brutos")
    c_.add_argument("lab")
    a = ap.parse_args()
    if a.cmd == "add":
        print(f"{add_rows(a.lab, a.files)} linha(s) nova(s) em aunp_characterization.csv")
        return
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = derive(a.lab)
    for w in res["warnings"]:
        print("AVISO:", w)
    m = res["calibration"].get("size")
    if m:
        print(f"calibração UV-Vis (Mie) → TEM do tamanho: {m['n_pairs']} pares, erro LOO {100 * m['loo_rmse']:.0f} % "
              f"em d, R² LOO {m['loo_r2']:.2f}")
    o = res["outcomes"]
    if a.cmd == "derive":
        src = o["notes"].str.replace(r" \(n=.*", "", regex=True)
        print(o.groupby(["objective", src]).size().rename("sínteses").to_string())
        if a.write:
            write(a.lab, res, a.force)
            print(f"-> {a.lab}/aunp_characterization.csv e outcomes.csv atualizados ({VERSION})")
        return
    diff = compare(a.lab, o)
    if diff.empty:
        print(f"outcomes.csv confere com os arquivos brutos ({len(o)} valores)")
        return
    print(diff.to_string(index=False))
    sys.exit(1)


if __name__ == "__main__":
    main()
