#!/usr/bin/env python3
"""GO Navigator — descritores por lote de óxido de grafeno, com incerteza.

Lê as tabelas do modelo de dados (datasets/data-model/, preenchidas em datasets/lab/) e devolve, para cada lote de GO,
média ± desvio de cada descritor (C/O, ID/IG, espessura…). Se ``go_descriptors.csv`` existir, ele é usado; senão os
descritores são agregados de ``go_characterization.csv`` (via ``go_samples.csv``). O resultado (padronizado) é o
"contexto" que o AuNP Designer usa para transferir conhecimento entre lotes.

Uso:
    python code/go_navigator/batch_descriptors.py datasets/lab            # tabela lote × descritor
    python code/go_navigator/batch_descriptors.py datasets/lab --write    # grava go_descriptors.csv (--force sobrescreve)
"""
from __future__ import annotations

import argparse
import os

import numpy as np
import pandas as pd


def _read(lab_dir: str, table: str) -> pd.DataFrame | None:
    path = os.path.join(lab_dir, f"{table}.csv")
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path)
    return df if len(df) else None


def aggregate_from_measurements(lab_dir: str) -> pd.DataFrame:
    """go_characterization + go_samples -> linhas de go_descriptors (método 'pooled')."""
    meas, samples = _read(lab_dir, "go_characterization"), _read(lab_dir, "go_samples")
    if meas is None or samples is None:
        return pd.DataFrame(columns=["go_batch_id", "descriptor", "mean", "sd", "n", "unit", "method"])
    m = meas.merge(samples[["go_sample_id", "go_batch_id"]], on="go_sample_id", how="left")
    g = m.groupby(["go_batch_id", "quantity"])
    out = g["value"].agg(["mean", "std", "count"]).reset_index()
    out.columns = ["go_batch_id", "descriptor", "mean", "sd", "n"]
    out["unit"] = g["unit"].first().values
    out["method"] = np.where(out["n"] > 1, "pooled", "single")
    out["source_measurements"] = g["measurement_id"].agg(lambda s: "|".join(map(str, s))).values
    # desvio entre lotes (efeito de lote) de cada descritor
    between = out.groupby("descriptor")["mean"].std()
    out["between_batch_sd"] = out["descriptor"].map(between)
    return out


def load_batch_descriptors(lab_dir: str) -> pd.DataFrame:
    """Tabela longa: go_batch_id, descriptor, mean, sd, n (de go_descriptors.csv ou agregada das medidas)."""
    d = _read(lab_dir, "go_descriptors")
    return d if d is not None else aggregate_from_measurements(lab_dir)


def batch_matrix(lab_dir: str, descriptors: list[str] | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(médias lote × descritor, desvios lote × descritor). Descritores ausentes num lote ficam NaN."""
    d = load_batch_descriptors(lab_dir)
    if d.empty:
        return pd.DataFrame(), pd.DataFrame()
    mean = d.pivot_table(index="go_batch_id", columns="descriptor", values="mean")
    sd = d.pivot_table(index="go_batch_id", columns="descriptor", values="sd") if "sd" in d else mean * np.nan
    if descriptors:
        mean, sd = mean.reindex(columns=descriptors), sd.reindex(columns=descriptors)
    return mean, sd


def standardized_context(lab_dir: str, descriptors: list[str] | None = None) -> pd.DataFrame:
    """Descritores padronizados (z-score entre lotes); NaN -> 0 (= média dos lotes). Entrada do GP contextual."""
    mean, _ = batch_matrix(lab_dir, descriptors)
    if mean.empty:
        return mean
    z = (mean - mean.mean()) / mean.std(ddof=0).replace(0, 1)
    return z.fillna(0.0)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("lab_dir")
    ap.add_argument("--write", action="store_true", help="grava go_descriptors.csv agregado das medidas")
    ap.add_argument("--force", action="store_true", help="sobrescreve um go_descriptors.csv existente")
    a = ap.parse_args()
    if a.write:
        path = os.path.join(a.lab_dir, "go_descriptors.csv")
        if _read(a.lab_dir, "go_descriptors") is not None and not a.force:
            raise SystemExit(f"{path} já existe (pode ter sido curado à mão); use --force para sobrescrever")
        agg = aggregate_from_measurements(a.lab_dir)
        agg.to_csv(path, index=False)
        print(f"go_descriptors.csv: {len(agg)} linhas")
    mean, sd = batch_matrix(a.lab_dir)
    if mean.empty:
        print("sem descritores (preencha go_characterization.csv / go_descriptors.csv)")
        return
    print((mean.round(3).astype(str) + " ± " + sd.round(3).astype(str)).to_string())


if __name__ == "__main__":
    main()
