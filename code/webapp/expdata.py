"""Carregadores dos dados EXPERIMENTAIS usados no site (nada simulado entra aqui).

Fontes (todas medidas em laboratório, por nós ou por terceiros, e publicadas):
  * literatura — datasets/literature-seed/aunp_literature_seed.csv: Cruse et al. 2022 (Sci. Data, figshare
    10.6084/m9.figshare.16614262), NSP 2026 e AuNCs; resultados experimentais relatados nos artigos e extraídos por
    NLP/LLM (o texto pode trazer erros de extração; ver o README da pasta);
  * AgNP — Mekki-Berrada et al., npj Comput. Mater. 7:55 (2021): síntese de nanopartículas de prata em microfluídica,
    perda espectral medida contra um espectro-alvo, com réplicas;
  * AuNC — datasets/aunc-fluorescence: emissão de nanoaglomerados de ouro (DOI por linha);
  * benchmarks experimentais de otimização (Liang et al., npj Comput. Mater. 7:188, 2021, via BOCoDe): P3HT/CNT
    (condutividade), perovskitas (instabilidade), crossed barrel (tenacidade), AutoAM (impressão);
  * constantes ópticas medidas do Au (Johnson & Christy 1972) e quadros de difração de CeO2 (detector GE, .ge3).
"""
from __future__ import annotations

import os
import re

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
BOCODE = os.path.join(ROOT, "projects", "bayesian-optimization", "BOCoDe", "bocode", "opt_problems", "materials", "data")

REDUCTANTS = ["trisodium_citrate", "NaBH4", "ascorbic_acid", "tannic_acid", "H2O2", "hydroxylamine_HCl",
              "hydroquinone", "hydrazine", "THPC", "glucose"]
CAPPING = ["CTAB", "PVP", "PEG", "CTAC", "GSH", "TOAB", "BSA", "oleylamine", "dodecanethiol", "oleic_acid"]
MORPH = ["sphere", "rod", "cluster", "shell/cage", "plate", "triangle", "star", "cube", "wire", "octahedra",
         "hexagon", "prismatic", "tube", "pyramid", "particle"]
SOURCES = {"cruse2022": "Cruse et al. 2022", "nsp2026": "NSP 2026", "aunc2025": "AuNCs 2025"}


def _first(v: str, vocab: list[str]) -> int:
    """Índice do primeiro item do vocabulário presente na lista 'a|b|c' (-1 se nenhum)."""
    if not isinstance(v, str):
        return -1
    items = v.split("|")
    for i, name in enumerate(vocab):
        if name in items:
            return i
    return -1


def morphology(v: str) -> int:
    """Morfologia dominante: a primeira classe específica (≠ particle) citada; 'particle' se só houver ela."""
    if not isinstance(v, str):
        return -1
    items = v.split("|")
    for i, name in enumerate(MORPH[:-1]):
        if name in items:
            return i
    return len(MORPH) - 1 if "particle" in items else -1


def literature() -> pd.DataFrame:
    d = pd.read_csv(os.path.join(ROOT, "datasets", "literature-seed", "aunp_literature_seed.csv"), low_memory=False)
    out = pd.DataFrame({
        "source": d["source"], "doi": d["doi"].fillna(""), "title": d["title"].fillna(""),
        "year": pd.to_numeric(d["year"], errors="coerce"),
        "size_nm": pd.to_numeric(d["size_nm"], errors="coerce"),
        "peak_nm": pd.to_numeric(d["abs_peak_nm"], errors="coerce"),
        "em_nm": pd.to_numeric(d["em_peak_nm"], errors="coerce"),
        "T_C": pd.to_numeric(d["temperature_C"], errors="coerce"),
        "seed": pd.to_numeric(d["seed_mediated"], errors="coerce").fillna(0).astype(int),
        "reductant": d["reductants"].map(lambda v: _first(v, REDUCTANTS)),
        "capping": d["capping_ligands"].map(lambda v: _first(v, CAPPING)),
        "morph": d["morphology_class"].map(morphology),
        "go": d["mentions_graphene_oxide"].astype(str).str.lower().isin(["1", "true", "1.0"]).astype(int),
        "supports": d["supports"].fillna(""), "reductants_raw": d["reductants"].fillna(""),
        "capping_raw": d["capping_ligands"].fillna(""), "morph_raw": d["morphology_class"].fillna(""),
    })
    # faixas físicas plausíveis (o texto minerado traz unidades erradas): fora delas, o valor vira ausente
    out.loc[~out["size_nm"].between(0.5, 1000), "size_nm"] = np.nan
    out.loc[~out["peak_nm"].between(300, 1400), "peak_nm"] = np.nan
    out.loc[~out["T_C"].between(-80, 400), "T_C"] = np.nan
    return out


def go_subset() -> pd.DataFrame:
    return pd.read_csv(os.path.join(ROOT, "datasets", "literature-seed", "go_aunp_subset.csv"))


def agnp() -> tuple[pd.DataFrame, pd.DataFrame]:
    """(medidas individuais, condições únicas com média, dp e nº de réplicas da perda espectral)."""
    a = pd.read_csv(os.path.join(BOCODE, "AgNP_dataset.csv"))
    cols = list(a.columns[:-1])
    u = a.groupby(cols, sort=False)["loss"].agg(["mean", "std", "count", "min", "max"]).reset_index()
    return a, u


AGNP_LABELS = {"QAgNO3(%)": "Q AgNO₃ (%)", "Qpva(%)": "Q PVA (%)", "Qtsc(%)": "Q citrato (%)",
               "Qseed(%)": "Q sementes (%)", "Qtot(uL/min)": "Q total (µL/min)"}


def aunc() -> pd.DataFrame:
    d = pd.read_csv(os.path.join(ROOT, "datasets", "aunc-fluorescence", "DATASET_AuNCs.csv"), sep=";",
                    encoding="latin-1")
    d.columns = ["entry", "size_nm", "solvent", "exc_nm", "em_nm", "ligand", "au_atoms", "T_raw", "pH", "time_h",
                 "doi"]

    def temp(v):
        nums = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", str(v))]
        if not nums:
            return np.nan
        return float(np.mean(nums))               # "25-30" → 27,5; "RT" → ausente
    d["T_C"] = d["T_raw"].map(temp)
    d.loc[d["T_raw"].astype(str).str.upper().str.contains("RT|ROOM"), "T_C"] = 25.0
    for c in ("size_nm", "exc_nm", "em_nm", "pH", "time_h", "au_atoms"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["ligand"] = d["ligand"].astype(str).str.strip()
    d["solvent"] = d["solvent"].astype(str).str.strip().str.lower()
    return d


BENCHMARKS = {   # nome: (arquivo, objetivo, minimizar?, rótulo do objetivo, referência)
    "AgNP": ("AgNP_dataset.csv", "loss", True, "perda espectral", "Mekki-Berrada et al. 2021"),
    "P3HT/CNT": ("P3HT_dataset.csv", None, False, "condutividade (S/cm)", "Bash et al. 2021"),
    "Perovskita": ("Perovskite_dataset.csv", None, True, "índice de instabilidade", "Sun et al. 2021"),
    "Crossed barrel": ("Crossed barrel_dataset.csv", "toughness", False, "tenacidade", "Gongora et al. 2020"),
    "AutoAM": ("AutoAM_dataset.csv", "Score", False, "escore de impressão", "Deneault et al. 2021"),
}


def benchmark_size(name: str) -> int:
    """Número de medidas (linhas, com réplicas) da campanha experimental."""
    return int(len(pd.read_csv(os.path.join(BOCODE, BENCHMARKS[name][0]), encoding="utf-8-sig")))


def benchmark(name: str) -> tuple[np.ndarray, np.ndarray, list[str], bool, str]:
    """Pool de condições ÚNICAS (média das réplicas), escalado em [0, 1]: (X, y, colunas, minimizar, rótulo)."""
    f, obj, minimize, label, _ = BENCHMARKS[name]
    d = pd.read_csv(os.path.join(BOCODE, f), encoding="utf-8-sig")
    obj = obj or d.columns[-1]
    feats = [c for c in d.columns if c != obj]
    u = d.groupby(feats, sort=False)[obj].mean().reset_index()
    X = u[feats].to_numpy(float)
    lo, hi = X.min(0), X.max(0)
    return (X - lo) / np.where(hi > lo, hi - lo, 1.0), u[obj].to_numpy(float), feats, minimize, label
