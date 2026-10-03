#!/usr/bin/env python3
"""Plano de análise pré-registrado (config/preregistration.yaml): leitura, validação, selo e emendas.

A proposta (§III, §4.4, §4.5, §4.14) exige que alvo espectral, faixa, normalização, tolerâncias, ε e λ sejam fixados
ANTES de comparar as estratégias. Este módulo é o único ponto de leitura desses valores para o resto do código e
torna o plano verificável:
  * `freeze` grava config/preregistration.lock.json com o sha256 do conteúdo normalizado, a data e o commit;
  * `check` compara o arquivo atual com o selo: mudança sem nova entrada em `amendments` é erro (como num registro
    de ensaio clínico — a emenda fica datada e justificada);
  * `epsilon` e `s-m` aplicam as REGRAS pré-registradas aos dados do piloto (não são escolhas posteriores).

Uso:
    python code/campaign/prereg.py show
    python code/campaign/prereg.py check                 # status do selo/emendas
    python code/campaign/prereg.py freeze                # congela (antes da primeira síntese adaptativa)
    python code/campaign/prereg.py target --out alvo.csv # espectro-alvo E*(λ) na grade pré-registrada
    python code/campaign/prereg.py s-m leitura1.csv leitura2.csv …   # sₘ por λ a partir de leituras repetidas
    python code/campaign/prereg.py epsilon datasets/lab  # ε = 1 % da mediana de J no piloto
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DEFAULT_PATH = os.path.join(ROOT, "config", "preregistration.yaml")
LOCK_PATH = os.path.join(ROOT, "config", "preregistration.lock.json")
sys.path.insert(0, os.path.join(ROOT, "code", "spectral"))

REQUIRED = ("target_spectrum", "loss", "objectives", "search_space", "batches", "budget", "relevance_threshold",
            "sustainability", "acquisition")
STAGES = ("pilot", "initialization", "adaptive", "confirmation")


class PreregError(ValueError):
    pass


def path() -> str:
    return os.environ.get("GOAUNP_PREREG", DEFAULT_PATH)


def load(p: str | None = None) -> dict:
    import yaml
    p = p or path()
    with open(p, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    validate(cfg)
    return cfg


def validate(cfg: dict) -> None:
    miss = [k for k in REQUIRED if k not in cfg]
    if miss:
        raise PreregError(f"pré-registro sem as chaves {miss}")
    for name, b in cfg["search_space"].items():
        if len(b) != 2 or not float(b[0]) < float(b[1]):
            raise PreregError(f"search_space.{name}: limites inválidos {b}")
    bud = cfg["budget"]
    if any(int(bud.get(s, -1)) < 0 for s in STAGES):
        raise PreregError(f"budget precisa de {STAGES}")
    dev, res = cfg["batches"]["development"], cfg["batches"]["reserved"]
    if set(dev) & set(res):
        raise PreregError(f"lotes ao mesmo tempo de desenvolvimento e reservados: {set(dev) & set(res)}")
    if int(bud["initialization"]) % len(dev):
        raise PreregError("budget.initialization deve ser múltiplo do nº de lotes de desenvolvimento")
    for o in cfg["objectives"]:
        if o["direction"] not in ("minimize", "maximize", "target"):
            raise PreregError(f"objetivo {o['name']}: direção {o['direction']!r}")
        if o["direction"] == "target" and "target" not in o:
            raise PreregError(f"objetivo {o['name']}: direção target sem 'target'")
    for c in cfg.get("constraints", []) or []:
        if c.get("lower") is None and c.get("upper") is None:
            raise PreregError(f"restrição {c['name']}: informe lower e/ou upper")
    if not 0 < float(cfg["relevance_threshold"]) < 1:
        raise PreregError("relevance_threshold deve estar entre 0 e 1")
    if cfg["acquisition"]["default"] not in ("qnehvi", "qlognehvi"):
        raise PreregError("acquisition.default: qnehvi | qlognehvi")
    if "arms" in cfg:
        pa = cfg["arms"].get("prospective", [])
        unknown = [x for x in pa + cfg["arms"].get("offline", []) if x not in cfg.get("representations", [])]
        if unknown:
            raise PreregError(f"arms: braços fora de representations: {unknown}")
        if len(pa) < 2 or cfg["arms"].get("reference", pa[0]) not in pa:
            raise PreregError("arms.prospective precisa de ≥ 2 braços, incluindo arms.reference")
        if int(bud["adaptive"]) % len(pa):
            raise PreregError("budget.adaptive deve ser múltiplo do nº de braços prospectivos (pareamento por rodada)")
        if int(bud["confirmation"]) % len(pa):
            raise PreregError("budget.confirmation deve ser múltiplo do nº de braços prospectivos (pares de confirmação)")


# ---------------------------------------------------------------------------------------------- acessores

def search_space(cfg: dict | None = None) -> dict:
    cfg = cfg or load()
    return {k: [float(v[0]), float(v[1])] for k, v in cfg["search_space"].items()}


def log_objectives(cfg: dict | None = None) -> tuple:
    cfg = cfg or load()
    return tuple(o["name"] for o in cfg["objectives"] if o.get("log"))


def arms(cfg: dict | None = None) -> dict:
    """Braços prospectivos e de referência (comparação pareada por rodada) e braços avaliados fora da bancada."""
    cfg = cfg or load()
    a = dict(cfg.get("arms") or {})
    a.setdefault("prospective", ["recipe", "go+impurities"])
    a.setdefault("reference", a["prospective"][0])
    a.setdefault("allocation", "paired_by_round")
    a.setdefault("offline", list(cfg.get("representations", [])))
    return a


def constraints(cfg: dict | None = None) -> dict:
    """{nome: (lower|None, upper|None)}"""
    cfg = cfg or load()
    return {c["name"]: (c.get("lower"), c.get("upper")) for c in cfg.get("constraints", []) or []}


def epsilon(cfg: dict | None = None) -> float:
    cfg = cfg or load()
    return float(cfg["loss"]["epsilon"]["value"])


def grid(cfg: dict | None = None) -> np.ndarray:
    t = (cfg or load())["target_spectrum"]
    lo, hi = t["range_nm"]
    return np.arange(float(lo), float(hi) + 1e-9, float(t["step_nm"]))


def target_spectrum(cfg: dict | None = None) -> tuple[np.ndarray, np.ndarray]:
    """E*(λ) na grade pré-registrada (antes da normalização, que a perda aplica a E e a E*)."""
    cfg = cfg or load()
    t, w = cfg["target_spectrum"], grid(cfg)
    if t["kind"] == "file":
        import uvvis
        fw, fa = uvvis.read_spectrum(os.path.join(ROOT, t["file"]))
        return w, np.interp(w, fw, fa)
    import mie
    ext = mie.ensemble_extinction(w, float(t["diameter_nm"]), float(t.get("relative_dispersion", 0)),
                                  n_medium=float(t.get("medium_index", 1.333)))
    return w, float(t.get("amplitude", 1.0)) * ext / ext.max()


def s_m(cfg: dict | None = None) -> np.ndarray | float:
    """sₘ na grade: arquivo gerado pela regra pré-registrada, ou o piso enquanto o piloto não foi feito."""
    cfg = cfg or load()
    ls = cfg["loss"]["s_m"]
    f = os.path.join(ROOT, ls["file"]) if ls.get("file") else None
    if f and os.path.exists(f):
        d = np.loadtxt(f, delimiter=",", skiprows=1)
        return np.maximum(np.interp(grid(cfg), d[:, 0], d[:, 1]), float(ls["floor"]))
    return float(ls["floor"])


def spectral_loss(w: np.ndarray, E: np.ndarray, cfg: dict | None = None) -> float:
    """J (Eq. 1) com alvo, grade, normalização e sₘ do pré-registro."""
    import uvvis
    cfg = cfg or load()
    tw, te = target_spectrum(cfg)
    norm = cfg["target_spectrum"].get("normalization", "none")
    return uvvis.spectral_loss_J(w, E, tw, te, s=s_m(cfg), grid=grid(cfg), norm=None if norm == "none" else norm)


# ---------------------------------------------------------------------------------------------- selo e emendas

def _canonical(cfg: dict) -> bytes:
    c = copy.deepcopy(cfg)
    c.pop("status", None)                  # o status muda ao congelar; não faz parte do conteúdo selado
    c.pop("amendments", None)              # emendas são registradas à parte e conferidas em check()
    # ε é preenchido depois do piloto pela REGRA selada (loss.epsilon.rule); o valor em si não é uma decisão
    c.get("loss", {}).get("epsilon", {}).pop("value", None)
    return json.dumps(c, sort_keys=True, ensure_ascii=False, default=str).encode()


def sha256(cfg: dict) -> str:
    return hashlib.sha256(_canonical(cfg)).hexdigest()


def _git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True,
                              timeout=20).stdout.strip()
    except Exception:  # noqa: BLE001
        return ""


def freeze(p: str | None = None, lock: str = LOCK_PATH, force: bool = False) -> dict:
    import yaml
    p = p or path()
    cfg = load(p)
    if os.path.exists(lock) and not force:
        raise PreregError(f"já congelado ({lock}); mudanças agora são emendas — edite `amendments` e use check")
    rec = {"sha256": sha256(cfg), "frozen_at": datetime.now().isoformat(timespec="seconds"),
           "git_commit": _git_commit(), "file": os.path.relpath(p, ROOT), "n_amendments": len(cfg.get("amendments") or [])}
    with open(lock, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=1)
    text = open(p, encoding="utf-8").read()
    if "status: draft" in text:
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(text.replace("status: draft", "status: frozen", 1))
    yaml.safe_load(open(p, encoding="utf-8"))        # continua válido
    return rec


def check(p: str | None = None, lock: str = LOCK_PATH) -> dict:
    """{'state': 'draft'|'frozen_ok'|'amended'|'violated', ...}"""
    cfg = load(p)
    if not os.path.exists(lock):
        return {"state": "draft", "sha256": sha256(cfg),
                "message": "plano NÃO congelado: congele antes da primeira rodada adaptativa (prereg.py freeze)"}
    rec = json.load(open(lock, encoding="utf-8"))
    now, n_am = sha256(cfg), len(cfg.get("amendments") or [])
    if now == rec["sha256"]:
        return {"state": "frozen_ok", "sha256": now, "frozen_at": rec["frozen_at"]}
    if n_am > rec.get("n_amendments", 0):
        bad = [a for a in cfg["amendments"][rec.get("n_amendments", 0):]
               if not all(a.get(k) for k in ("date", "change", "reason"))]
        if bad:
            return {"state": "violated", "message": f"emenda(s) sem date/change/reason: {bad}"}
        return {"state": "amended", "sha256": now, "frozen_sha256": rec["sha256"],
                "amendments": cfg["amendments"][rec.get("n_amendments", 0):]}
    return {"state": "violated", "sha256": now, "frozen_sha256": rec["sha256"],
            "message": "o plano mudou depois de congelado sem emenda registrada em `amendments`"}


def guard(context: str = "") -> dict:
    """Usado pelos scripts: avisa se o plano está em rascunho e falha se foi violado."""
    st = check()
    if st["state"] == "violated":
        raise PreregError(f"{context}: {st['message']}")
    if st["state"] == "draft":
        print(f"AVISO ({context}): {st['message']}", file=sys.stderr)
    return st


# ---------------------------------------------------------------------------------------------- regras do piloto

def s_m_from_replicates(files: list[str], cfg: dict | None = None, out: str | None = None) -> np.ndarray:
    import uvvis
    cfg = cfg or load()
    if len(files) < 5:
        raise PreregError(f"a regra pré-registrada pede >= 5 leituras repetidas (recebidas {len(files)})")
    w = grid(cfg)
    A = np.vstack([uvvis.resample(*uvvis.read_spectrum(f), w) for f in files])
    sd = np.maximum(A.std(axis=0, ddof=1), float(cfg["loss"]["s_m"]["floor"]))
    out = out or os.path.join(ROOT, cfg["loss"]["s_m"]["file"])
    np.savetxt(out, np.c_[w, sd], delimiter=",", header="wavelength_nm,s_m", comments="")
    return sd


def epsilon_from_pilot(lab: str, cfg: dict | None = None) -> float:
    import pandas as pd
    cfg = cfg or load()
    syn = pd.read_csv(os.path.join(lab, "aunp_syntheses.csv"))
    out = pd.read_csv(os.path.join(lab, "outcomes.csv"))
    pilot = syn.loc[syn["campaign_id"].astype(str).str.upper().str.startswith("PILOT"), "synthesis_id"]
    j = out[(out["objective"] == "spectral_loss_J") & out["synthesis_id"].isin(pilot)]["value"]
    if j.empty:
        raise PreregError("nenhuma síntese de piloto (campaign_id PILOT…) com spectral_loss_J")
    return 0.01 * float(np.median(j))


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("show")
    sub.add_parser("check")
    fz = sub.add_parser("freeze")
    fz.add_argument("--force", action="store_true")
    t = sub.add_parser("target")
    t.add_argument("--out")
    s = sub.add_parser("s-m")
    s.add_argument("files", nargs="+")
    e = sub.add_parser("epsilon")
    e.add_argument("lab")
    a = ap.parse_args(argv)
    if a.cmd == "show":
        cfg = load()
        print(json.dumps({"status": cfg["status"], "sha256": sha256(cfg), "search_space": search_space(cfg),
                          "objectives": cfg["objectives"], "constraints": constraints(cfg),
                          "epsilon": epsilon(cfg), "budget": cfg["budget"]}, indent=1, ensure_ascii=False))
    elif a.cmd == "check":
        st = check()
        print(json.dumps(st, indent=1, ensure_ascii=False, default=str))
        sys.exit(1 if st["state"] == "violated" else 0)
    elif a.cmd == "freeze":
        print(json.dumps(freeze(force=a.force), indent=1))
    elif a.cmd == "target":
        w, e = target_spectrum()
        if a.out:
            np.savetxt(a.out, np.c_[w, e], delimiter=",", header="wavelength_nm,absorbance", comments="")
        import uvvis
        print(f"E*(λ): {len(w)} pontos {w[0]:.0f}–{w[-1]:.0f} nm; LSPR {uvvis.lspr(w, e)['LSPR_nm']:.1f} nm")
    elif a.cmd == "s-m":
        sd = s_m_from_replicates(a.files)
        print(f"sₘ: mediana {np.median(sd):.4f}, máx {sd.max():.4f} -> {load()['loss']['s_m']['file']}")
    elif a.cmd == "epsilon":
        eps = epsilon_from_pilot(a.lab)
        print(f"ε pela regra pré-registrada = {eps:.4g}. Copie para loss.epsilon.value (é a aplicação da regra, "
              f"não uma emenda; anote a data em notes se quiser).")


if __name__ == "__main__":
    main()
