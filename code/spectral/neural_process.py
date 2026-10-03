#!/usr/bin/env python3
"""Modelo diferenciável de forma espectral por Neural Process (§4.6, Objetivo 4) + regressor condições → z.

Arquitetura (a de referência da proposta: encoder de espectros → z → decoder; regressor condições → z):
  * Neural Process latente (Garnelo et al. 2018) sobre a FUNÇÃO A(λ): o encoder agrega pontos (λ, A) de um espectro
    numa distribuição q(z | pontos) (média/variância, invariante à ordem); o decoder dá N(μ(z, λ), σ²(z, λ)) em
    qualquer λ — com poucos pontos (ex.: leitura em 3 comprimentos de onda) ainda há um z com incerteza;
  * regressor: um GP (Matérn-5/2 + ARD, o do Designer) por dimensão de z, de (receita + descritores do lote) para
    a média de z, com a variância do encoder como ruído de observação;
  * predição: z ~ GP(x), espectro ~ decoder(z) → média, banda de 90 % e a distribuição da perda J (Eq. 1);
  * tudo em PyTorch: a perda J do espectro previsto é DIFERENCIÁVEL em x → `inverse_design` busca a receita por
    gradiente (multi-start). Com < 200 espectros a proposta trata isso como estudo computacional (aviso emitido).
Avaliação (§4.6): erro espectral, calibração (cobertura da banda) e transferência entre lotes (leave-one-batch-out,
reajustando também o NP sem o lote deixado de fora).

Uso:
    python code/spectral/neural_process.py lbo datasets/lab [--steps 2000]
    python code/spectral/neural_process.py design datasets/lab --batch L2 [--out outputs/np_design.json]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import warnings

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path[:0] = [HERE, os.path.join(ROOT, "code", "campaign"), os.path.join(ROOT, "code", "aunp_designer"),
                os.path.join(ROOT, "code", "go_navigator")]
MIN_SPECTRA_FOR_DESIGN = 200


def _torch():
    import torch
    return torch


def _mlp(sizes):
    nn = _torch().nn
    layers = []
    for a, b in zip(sizes[:-1], sizes[1:]):
        layers += [nn.Linear(a, b), nn.GELU()]
    return nn.Sequential(*layers[:-1])


class SpectralNP:
    """Neural Process latente sobre espectros numa grade fixa (λ normalizado a [−1, 1], A dividido pela escala)."""

    def __init__(self, grid: np.ndarray, dz: int = 6, hidden: int = 128, seed: int = 0):
        torch = _torch()
        torch.manual_seed(seed)
        self.grid, self.dz = np.asarray(grid, float), dz
        self.lam = torch.tensor((self.grid - self.grid.min()) / np.ptp(self.grid) * 2 - 1, dtype=torch.float32)
        self.enc = _mlp([2, hidden, hidden, hidden])
        self.head = _mlp([hidden, hidden, 2 * dz])
        self.dec = _mlp([dz + 1, hidden, hidden, hidden, 2])
        self.scale = 1.0

    def parameters(self):
        return list(self.enc.parameters()) + list(self.head.parameters()) + list(self.dec.parameters())

    def encode(self, A, mask=None):
        """A: (n, L) já escalado; mask (n, L) booleana dos pontos de contexto. -> (μ_z, σ_z)."""
        torch = _torch()
        n, L = A.shape
        x = torch.stack([self.lam.expand(n, L), A], dim=-1)
        r = self.enc(x)
        m = torch.ones(n, L, 1) if mask is None else mask.unsqueeze(-1).float()
        r = (r * m).sum(1) / m.sum(1).clamp_min(1.0)
        h = self.head(r)
        return h[:, :self.dz], 0.05 + 0.95 * torch.nn.functional.softplus(h[:, self.dz:])

    def decode(self, z):
        """z: (..., dz) -> μ, σ em (..., L) (escala do modelo)."""
        torch = _torch()
        L = len(self.grid)
        zz = z.unsqueeze(-2).expand(*z.shape[:-1], L, self.dz)
        lam = self.lam.view(*([1] * (z.dim() - 1)), L, 1).expand(*z.shape[:-1], L, 1)
        o = self.dec(torch.cat([zz, lam], dim=-1))
        return o[..., 0], 0.005 + torch.nn.functional.softplus(o[..., 1])

    def fit(self, spectra: np.ndarray, steps: int = 2500, batch: int = 32, lr: float = 2e-3, seed: int = 0,
            verbose: bool = False) -> "SpectralNP":
        torch = _torch()
        from torch.distributions import Normal, kl_divergence
        S = np.asarray(spectra, float)
        self.scale = float(np.nanpercentile(np.abs(S), 99)) or 1.0
        A = torch.tensor(S / self.scale, dtype=torch.float32)
        opt = torch.optim.Adam(self.parameters(), lr=lr)
        g = torch.Generator().manual_seed(seed)
        n, L = A.shape
        for it in range(steps):
            idx = torch.randint(0, n, (min(batch, n),), generator=g)
            a = A[idx]
            k = int(torch.randint(3, max(4, L // 2), (1,), generator=g))
            ctx = torch.zeros_like(a, dtype=torch.bool)
            ctx[:, torch.randperm(L, generator=g)[:k]] = True
            mu_t, sd_t = self.encode(a)
            mu_c, sd_c = self.encode(a, ctx)
            z = mu_t + sd_t * torch.randn(mu_t.shape, generator=g)
            m, s = self.decode(z)
            nll = -Normal(m, s).log_prob(a).sum(-1)
            kl = kl_divergence(Normal(mu_t, sd_t), Normal(mu_c, sd_c)).sum(-1)
            loss = (nll + kl).mean() / L
            opt.zero_grad()
            loss.backward()
            opt.step()
            if verbose and it % 250 == 0:
                print(f"passo {it:5d}  perda {loss.item():.4f}")
        return self

    def latent(self, spectra: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        torch = _torch()
        with torch.no_grad():
            mu, sd = self.encode(torch.tensor(np.asarray(spectra, float) / self.scale, dtype=torch.float32))
        return mu.numpy().astype(float), sd.numpy().astype(float)

    def reconstruct(self, spectra: np.ndarray) -> np.ndarray:
        torch = _torch()
        mu, _ = self.latent(spectra)
        with torch.no_grad():
            m, _ = self.decode(torch.tensor(mu, dtype=torch.float32))
        return m.numpy() * self.scale


class ConditionalSpectralModel:
    """NP + GPs condições → z. `predict` dá amostras de espectros; `mean_spectrum_torch` é diferenciável em x."""

    def __init__(self, np_model: SpectralNP, bounds: np.ndarray):
        self.np, self.bounds = np_model, np.asarray(bounds, float)
        self.gps = []

    def fit(self, X: np.ndarray, spectra: np.ndarray) -> "ConditionalSpectralModel":
        torch = _torch()
        from botorch.models import SingleTaskGP
        from botorch.models.transforms import Normalize, Standardize
        from gpytorch.kernels import ScaleKernel
        import designer
        import hierarchical
        mu, sd = self.np.latent(spectra)
        tx = torch.tensor(X, dtype=torch.double)
        b = torch.tensor(self.bounds, dtype=torch.double)
        self.gps = []
        for j in range(mu.shape[1]):
            m = SingleTaskGP(tx, torch.tensor(mu[:, j:j + 1], dtype=torch.double),
                             train_Yvar=torch.tensor(sd[:, j:j + 1] ** 2, dtype=torch.double).clamp_min(1e-6),
                             covar_module=ScaleKernel(hierarchical.matern52(X.shape[1])),
                             input_transform=Normalize(X.shape[1], bounds=b), outcome_transform=Standardize(1))
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                designer._fit(m)
            self.gps.append(m)
        return self

    def z_posterior(self, X):
        torch = _torch()
        X = X if isinstance(X, torch.Tensor) else torch.tensor(np.asarray(X, float), dtype=torch.double)
        posts = [g.posterior(X) for g in self.gps]
        mean = torch.cat([p.mean for p in posts], dim=-1)
        var = torch.cat([p.variance for p in posts], dim=-1)
        return mean, var

    def mean_spectrum_torch(self, X):
        mean, _ = self.z_posterior(X)
        m, _ = self.np.decode(mean.float())
        return m * self.np.scale

    def predict(self, X: np.ndarray, n_samples: int = 200, seed: int = 0) -> dict:
        torch = _torch()
        g = torch.Generator().manual_seed(seed)
        with torch.no_grad():
            mean, var = self.z_posterior(X)
            z = mean.float().unsqueeze(0) + var.float().sqrt().unsqueeze(0) * torch.randn(
                (n_samples, *mean.shape), generator=g)
            m, s = self.np.decode(z)
            samples = (m + s * torch.randn(m.shape, generator=g)) * self.np.scale
        S = samples.numpy()
        return {"mean": S.mean(0), "q05": np.quantile(S, 0.05, axis=0), "q95": np.quantile(S, 0.95, axis=0),
                "samples": S}


def _normalize_torch(a, how: str):
    torch = _torch()
    if how == "max":
        return a / a.max(dim=-1, keepdim=True).values.clamp_min(1e-9)
    if how == "area":
        return a / a.abs().sum(-1, keepdim=True).clamp_min(1e-9) * a.shape[-1]
    return a if torch.is_tensor(a) else a


def inverse_design(model: ConditionalSpectralModel, target: np.ndarray, s_m, norm: str = "max",
                   fixed: dict[int, float] | None = None, n_starts: int = 16, steps: int = 150, seed: int = 0,
                   n_train: int | None = None, n_mc: int = 16, X_obs: np.ndarray | None = None,
                   y_obs: np.ndarray | None = None, n_warm: int = 5, return_all: bool = False) -> dict:
    """Receita que minimiza o J ESPERADO (sobre a incerteza preditiva) por gradiente (Adam, multi-start). Com dados
    observados (X_obs, J observado y_obs), parte também das `n_warm` melhores receitas medidas e as mantém como
    candidatas: o resultado nunca é uma extrapolação pior, pelo modelo, que o melhor ponto já medido."""
    torch = _torch()
    if n_train is not None and n_train < MIN_SPECTRA_FOR_DESIGN:
        warnings.warn(f"só {n_train} espectros (< {MIN_SPECTRA_FOR_DESIGN}): design inverso como estudo "
                      "computacional, não para fundamentar conclusões químicas (§4.6)")
    lo, hi = (torch.tensor(model.bounds[i], dtype=torch.double) for i in (0, 1))
    d = len(lo)
    g = torch.Generator().manual_seed(seed)
    u0 = torch.rand((n_starts, d), generator=g, dtype=torch.double)
    warm = None
    if X_obs is not None and y_obs is not None and len(X_obs):
        best = np.argsort(np.asarray(y_obs, float))[:n_warm]
        warm = torch.tensor((np.asarray(X_obs, float)[best] - model.bounds[0]) / (model.bounds[1] - model.bounds[0]),
                            dtype=torch.double).clamp(0, 1)
        u0 = torch.cat([warm, u0])
    u = u0.clone().requires_grad_(True)
    tgt = _normalize_torch(torch.tensor(np.asarray(target, float), dtype=torch.float32), norm)
    sm = torch.tensor(np.broadcast_to(np.asarray(s_m, float), tgt.shape).copy(), dtype=torch.float32)
    fixed = fixed or {}
    mask = torch.ones(d, dtype=torch.double)
    val = torch.zeros(d, dtype=torch.double)
    for j, v in fixed.items():
        mask[j], val[j] = 0.0, (v - lo[j]) / (hi[j] - lo[j])
    opt = torch.optim.Adam([u], lr=0.05)
    eps_z = torch.randn((n_mc, 1, model.np.dz), generator=g)        # amostras fixas (reparametrização)

    def J(uu, robust=True):
        """J esperado sob a incerteza do GP em z (média sobre amostras): o otimizador não pode explorar regiões onde
        o modelo é incerto — o J do espectro MÉDIO subestima a perda fora dos dados."""
        x = lo + (hi - lo) * (uu.clamp(0, 1) * mask + val)
        mean, var = model.z_posterior(x)
        z = mean.float().unsqueeze(0) + (var.float().sqrt().unsqueeze(0) * eps_z if robust else 0.0)
        m, _ = model.np.decode(z)
        e = _normalize_torch(m * model.np.scale, norm)
        return (((e - tgt) / sm) ** 2).mean(-1).mean(0)
    for _ in range(steps):
        loss = J(u).sum()
        opt.zero_grad()
        loss.backward()
        opt.step()
        with torch.no_grad():
            u.clamp_(0, 1)
    with torch.no_grad():
        cand = torch.cat([u, warm]) if warm is not None else u
        Js = J(cand)
        k = int(torch.argmin(Js))
        u = cand
        J_mean_spec = float(J(u[k:k + 1], robust=False)[0])
        from_observed = bool(warm is not None and k >= len(u) - len(warm))
        x = (lo + (hi - lo) * (u[k].clamp(0, 1) * mask + val)).numpy()
    pred = model.predict(x[None, :], n_samples=300)
    tg = np.asarray(target, float)
    Jdist = [float(np.mean(((_norm_np(sp, norm) - _norm_np(tg, norm)) / np.asarray(s_m)) ** 2)) for sp in pred["samples"][:, 0]]
    extra = {}
    if return_all:                                   # todos os pontos otimizados: candidatos para o GP decidir
        with torch.no_grad():
            allx = (lo + (hi - lo) * (u.clamp(0, 1) * mask + val)).numpy()
        extra = {"candidates": allx, "candidates_J_expected": Js.numpy().astype(float),
                 "candidates_from_observed": np.arange(len(allx)) >= len(allx) - (len(warm) if warm is not None else 0)}
    return {**extra, "x": x, "J_expected": float(Js[k]), "J_mean_spectrum": J_mean_spec,
            "is_observed_recipe": from_observed,
            "J_predictive_median": float(np.median(Jdist)),
            "J_predictive_90": [float(np.quantile(Jdist, 0.05)), float(np.quantile(Jdist, 0.95))],
            "predicted_mean": pred["mean"][0], "band90": (pred["q05"][0], pred["q95"][0])}


def _norm_np(a, how):
    a = np.asarray(a, float)
    if how == "max":
        return a / max(a.max(), 1e-9)
    if how == "area":
        return a / max(np.abs(a).sum(), 1e-9) * len(a)
    return a


def lbo(X: np.ndarray, spectra: np.ndarray, batches: np.ndarray, grid: np.ndarray, bounds: np.ndarray,
        steps: int = 2500, seed: int = 0) -> pd.DataFrame:
    """Leave-one-batch-out: NP e GPs reajustados sem o lote; RMSE espectral × referência (espectro médio do treino)
    e cobertura da banda de 90 %."""
    rows = []
    for b in np.unique(batches):
        tr, te = batches != b, batches == b
        npm = SpectralNP(grid, seed=seed).fit(spectra[tr], steps=steps, seed=seed)
        cm = ConditionalSpectralModel(npm, bounds).fit(X[tr], spectra[tr])
        p = cm.predict(X[te])
        rows.append({"held_out_batch": b, "n": int(te.sum()),
                     "rmse_np": float(np.sqrt(np.mean((p["mean"] - spectra[te]) ** 2))),
                     "rmse_mean_spectrum": float(np.sqrt(np.mean((spectra[tr].mean(0) - spectra[te]) ** 2))),
                     "coverage90": float(np.mean((spectra[te] >= p["q05"]) & (spectra[te] <= p["q95"])))})
    return pd.DataFrame(rows)


def from_lab(lab: str) -> dict:
    """Espectros (1ª leitura por síntese, na grade pré-registrada), condições (receita + descritores do lote)."""
    import designer
    import prereg
    import uvvis
    from batch_descriptors import standardized_context
    cfg = prereg.load()
    grid = prereg.grid(cfg)
    syn = designer.usable_syntheses(lab).set_index("synthesis_id")
    sp = pd.read_csv(os.path.join(lab, "spectra.csv"))
    sp = sp[sp["technique"].astype(str) == "UV-Vis"].drop_duplicates("synthesis_id")
    sp = sp[sp["synthesis_id"].isin(syn.index)]
    space = designer.DEFAULT_SPACE
    z = standardized_context(lab)
    S, X, B = [], [], []
    for _, r in sp.iterrows():
        w, a = uvvis.read_spectrum(os.path.join(lab, r["file"]))
        a = uvvis.correct(w, a, None, float(r.get("dilution_factor", 1) or 1), float(r.get("path_length_mm", 10) or 10))
        S.append(np.interp(grid, w, a))
        s = syn.loc[r["synthesis_id"]]
        ctx = z.loc[s["go_batch_id"]].to_numpy(float) if s["go_batch_id"] in z.index else np.zeros(z.shape[1])
        X.append(np.r_[[float(s[k]) for k in space], ctx])
        B.append(str(s["go_batch_id"]))
    X = np.array(X)
    lo = np.r_[[space[k][0] for k in space], X[:, len(space):].min(0) - 1 if z.shape[1] else []]
    hi = np.r_[[space[k][1] for k in space], X[:, len(space):].max(0) + 1 if z.shape[1] else []]
    return {"grid": grid, "spectra": np.array(S), "X": X, "batches": np.array(B), "bounds": np.vstack([lo, hi]),
            "columns": list(space) + [f"ctx_{c}" for c in z.columns], "context": z, "cfg": cfg}


def rank_with_gp(lab: str, res: dict, space_cols: list[str], batch: str, lots: dict | None = None,
                 representation: str = "go") -> pd.DataFrame:
    """Candidatos do NP + a proposta do próprio Designer, ordenados pela aquisição do GP (mesmo critério)."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "aunp_designer"))
    import designer
    space = designer.DEFAULT_SPACE
    camp = designer.load_campaign(lab, space, representation, designer.default_logs(), designer.default_eps(),
                                  constraints=designer.default_constraints())
    fixed = designer.fixed_context(lab, camp, batch, lots or {})
    np_c = pd.DataFrame(res["candidates"][:, :len(space_cols)], columns=space_cols)
    np_c = np_c.assign(source=np.where(res["candidates_from_observed"], "NP (partida em receita medida)", "NP"),
                       J_expected_NP=res["candidates_J_expected"])
    gp_c = designer.propose(camp, space, q=1, fixed=fixed, lab=lab)[list(space)].assign(source="Designer (GP)",
                                                                                       J_expected_NP=np.nan)
    allc = pd.concat([np_c, gp_c], ignore_index=True).drop_duplicates(subset=list(space))
    allc["acquisition_GP"] = designer.acquisition_values(camp, space, allc, fixed)
    return allc.sort_values("acquisition_GP", ascending=False).reset_index(drop=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("lbo", "design"):
        p = sub.add_parser(name)
        p.add_argument("lab")
        p.add_argument("--steps", type=int, default=2500)
        p.add_argument("--out")
        if name == "design":
            p.add_argument("--batch", required=True)
            p.add_argument("--rank-with-gp", action="store_true",
                           help="ordena os candidatos do NP pela aquisição do AuNP Designer, ao lado da proposta do "
                                "próprio Designer (o NP gera, o GP decide)")
            p.add_argument("--lot", action="append", default=[], help="papel=lote (para o contexto de impurezas)")
    a = ap.parse_args()
    d = from_lab(a.lab)
    print(f"{len(d['spectra'])} espectros, {d['X'].shape[1]} entradas, lotes {sorted(set(d['batches']))}")
    if a.cmd == "lbo":
        res = lbo(d["X"], d["spectra"], d["batches"], d["grid"], d["bounds"], a.steps)
        print(res.round(4).to_string(index=False))
        out = res.to_dict("records")
    else:
        import prereg
        cfg = d["cfg"]
        npm = SpectralNP(d["grid"]).fit(d["spectra"], steps=a.steps)
        cm = ConditionalSpectralModel(npm, d["bounds"]).fit(d["X"], d["spectra"])
        n_space = len(prereg.search_space(cfg))
        ctx = d["context"]
        fixed = {n_space + i: float(v) for i, v in enumerate(ctx.loc[a.batch])} if a.batch in ctx.index else {}
        _, tgt = prereg.target_spectrum(cfg)
        norm = cfg["target_spectrum"].get("normalization", "max")
        sm = prereg.s_m(cfg)
        y_obs = [float(np.mean(((_norm_np(sp, norm) - _norm_np(tgt, norm)) / np.asarray(sm)) ** 2)) for sp in d["spectra"]]
        res = inverse_design(cm, tgt, sm, norm, fixed, n_train=len(d["spectra"]), X_obs=d["X"], y_obs=y_obs,
                             return_all=a.rank_with_gp)
        out = {"recipe": dict(zip(d["columns"][:n_space], map(float, res["x"][:n_space]))),
               "J_expected": res["J_expected"], "J_predictive_median": res["J_predictive_median"],
               "J_predictive_90": res["J_predictive_90"], "batch": a.batch}
        print(json.dumps(out, indent=1, ensure_ascii=False))
        if a.rank_with_gp:
            table = rank_with_gp(a.lab, res, d["columns"][:n_space], a.batch, dict(x.split("=", 1) for x in a.lot))
            print(table.round(4).to_string(index=False))
            out = {"inverse_design": out, "ranking": table.to_dict("records")}
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1, default=float, ensure_ascii=False)


if __name__ == "__main__":
    main()
