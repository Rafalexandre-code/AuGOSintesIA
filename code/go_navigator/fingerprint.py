#!/usr/bin/env python3
"""Batch Fingerprint por autoencoder + Active Subspace (§4.2; Atividade 3.1) — módulo EXPLORATÓRIO.

Batch Fingerprint: vetor latente curto (padrão 2 dimensões) que resume os descritores de um lote de GO.
  * Autoencoder (PyTorch) treinado com AUMENTO PELA INCERTEZA: cada época sorteia descritores de N(média, sd do lote)
    — com 6 lotes, é o que impede o autoencoder de decorar 6 pontos. Com menos de 2·(nº de descritores) lotes, a
    proposta pede cautela: o código cai para PCA (o autoencoder linear ótimo) e avisa.
  * Utilidade (como a proposta define): contribuição incremental para o modelo, por leave-one-batch-out — o braço
    'go' do Designer é avaliado com os descritores brutos e com o fingerprint (numa cópia do laboratório).
Active Subspace (Constantine 2015): C = E[∇f ∇fᵀ] da média a posteriori do GP do Designer sobre (receita, contexto);
os autovetores de maior autovalor são as direções que mais mudam o desfecho, e o salto entre autovalores diz quantas
importam. Gradientes por autodiferenciação no GP.

Uso:
    python code/go_navigator/fingerprint.py fingerprint datasets/lab [--latent 2]
    python code/go_navigator/fingerprint.py evaluate datasets/lab           # LBO: brutos × fingerprint
    python code/go_navigator/fingerprint.py active-subspace datasets/lab [--representation go]
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import warnings

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path[:0] = [HERE, os.path.join(ROOT, "code", "aunp_designer")]


def fingerprint(mean: pd.DataFrame, sd: pd.DataFrame, latent: int = 2, epochs: int = 2000, seed: int = 0,
                force_ae: bool = False) -> tuple[pd.DataFrame, dict]:
    """mean/sd: lote × descritor. -> (lote × fp1..fpL, informações do método)."""
    import torch
    M = mean.dropna(axis=1, how="any")
    S = sd.reindex_like(M).fillna(0.0)
    mu, scale = M.mean(), M.std(ddof=0).replace(0, 1)
    Z = ((M - mu) / scale).to_numpy(float)
    Zs = (S / scale).to_numpy(float)
    n, d = Z.shape
    latent = min(latent, d, max(n - 1, 1))
    info = {"n_batches": n, "n_descriptors": d, "latent": latent}
    if n < 2 * d and not force_ae:
        warnings.warn(f"só {n} lotes para {d} descritores: Batch Fingerprint por PCA (autoencoder linear); o "
                      "autoencoder não-linear exige mais lotes (§4.2)")
        U, sv, Vt = np.linalg.svd(Z - Z.mean(0), full_matrices=False)
        fp = (Z - Z.mean(0)) @ Vt[:latent].T
        info.update({"method": "PCA", "explained_variance": (sv[:latent] ** 2 / (sv ** 2).sum()).tolist(),
                     "loadings": dict(zip(M.columns, Vt[:latent].T.tolist()))})
    else:
        torch.manual_seed(seed)
        nn = torch.nn
        enc = nn.Sequential(nn.Linear(d, 16), nn.Tanh(), nn.Linear(16, latent))
        dec = nn.Sequential(nn.Linear(latent, 16), nn.Tanh(), nn.Linear(16, d))
        opt = torch.optim.Adam(list(enc.parameters()) + list(dec.parameters()), lr=1e-2, weight_decay=1e-4)
        Zt, St = torch.tensor(Z, dtype=torch.float32), torch.tensor(Zs, dtype=torch.float32)
        for _ in range(epochs):
            x = Zt + St * torch.randn_like(Zt)                  # aumento pela incerteza de cada lote
            loss = ((dec(enc(x)) - Zt) ** 2).mean()
            opt.zero_grad()
            loss.backward()
            opt.step()
        with torch.no_grad():
            fp = enc(Zt).numpy()
            rec = float(((dec(enc(Zt)) - Zt) ** 2).mean())
        info.update({"method": "autoencoder", "reconstruction_mse": rec})
    return pd.DataFrame(fp, index=M.index, columns=[f"fp{i + 1}" for i in range(latent)]), info


def evaluate(lab: str, latent: int = 2) -> pd.DataFrame:
    """LBO do braço 'go' com descritores brutos × com o fingerprint (cópia temporária do laboratório)."""
    import designer
    from batch_descriptors import batch_matrix
    mean, sd = batch_matrix(lab)
    fp, info = fingerprint(mean, sd, latent)
    space = designer.DEFAULT_SPACE
    raw = designer.validate_lbo(lab, space, ("go",), designer.default_logs(), designer.default_eps())
    tmp = tempfile.mkdtemp()
    try:
        work = os.path.join(tmp, "lab")
        shutil.copytree(lab, work)
        long = fp.reset_index().melt(id_vars=fp.index.name or "index", var_name="descriptor", value_name="mean")
        long = long.rename(columns={fp.index.name or "index": "go_batch_id"}).assign(sd=0.0, n=1, unit="a.u.")
        long.to_csv(os.path.join(work, "go_descriptors.csv"), index=False)
        fpr = designer.validate_lbo(work, space, ("go",), designer.default_logs(), designer.default_eps())
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    out = pd.concat([raw.assign(context="descritores brutos"), fpr.assign(context=f"fingerprint ({info['method']})")])
    return out


def active_subspace(lab: str, representation: str = "go", n_samples: int = 2000, objective: int = 0,
                    seed: int = 0) -> dict:
    import torch
    import designer
    space = designer.DEFAULT_SPACE
    camp = designer.load_campaign(lab, space, representation, designer.default_logs(), designer.default_eps())
    model, _, _, bounds = designer.build_model(camp, space)
    g = torch.Generator().manual_seed(seed)
    lo, hi = bounds[0], bounds[1]
    U = torch.rand((n_samples, len(lo)), generator=g, dtype=torch.double)
    X = (lo + (hi - lo) * U).requires_grad_(True)
    mu = model.models[objective].posterior(X).mean.sum()
    grad = torch.autograd.grad(mu, X)[0] * (hi - lo)              # gradiente na escala normalizada [0, 1]
    G = grad.detach().numpy()
    C = G.T @ G / len(G)
    w, V = np.linalg.eigh(C)
    o = np.argsort(w)[::-1]
    w, V = w[o], V[:, o]
    cols = list(camp.X.columns)
    gaps = (w[:-1] / np.clip(w[1:], 1e-300, None)).tolist()
    return {"objective": list(camp.objs.index)[objective], "eigenvalues": w.tolist(),
            "eigenvalue_ratio_gaps": gaps, "suggested_dimension": int(np.argmax(gaps) + 1) if gaps else 1,
            "first_direction": dict(zip(cols, V[:, 0].round(4).tolist())),
            "second_direction": dict(zip(cols, V[:, 1].round(4).tolist())) if V.shape[1] > 1 else {}}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("fingerprint", "evaluate", "active-subspace"):
        p = sub.add_parser(name)
        p.add_argument("lab")
        p.add_argument("--latent", type=int, default=2)
        p.add_argument("--representation", default="go")
    a = ap.parse_args()
    if a.cmd == "fingerprint":
        from batch_descriptors import batch_matrix
        fp, info = fingerprint(*batch_matrix(a.lab), a.latent)
        print(fp.round(4).to_string())
        print(json.dumps(info, indent=1, default=float))
    elif a.cmd == "evaluate":
        print(evaluate(a.lab, a.latent).round(4).to_string(index=False))
    else:
        print(json.dumps(active_subspace(a.lab, a.representation), indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
