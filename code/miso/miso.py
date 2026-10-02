#!/usr/bin/env python3
"""MISO — otimização com múltiplas fontes de informação de custos diferentes (§4.8, Objetivo 4).

Fontes (config/preregistration.yaml → miso): UV-Vis (custo 1), DLS (2) e TEM (20); a fonte-alvo é a TEM. Uma consulta
(x, s) = sintetizar na receita x e medir o tamanho com a técnica s; objetivo y = −[ln(d_s/d*)]² (d* = 20 nm).

Três modelos de covariância entre fontes, os mesmos comparados por Herbol et al. (2020) no ClancyLab-PAL
(external/multi-fidelity/ClancyLab-PAL):
  MGP  (Poloczek, Wang & Frazier 2017, misoKG): f_s(x) = f_alvo(x) + δ_s(x), δ_s GPs independentes, δ_alvo = 0
  ICM  (coregionalização intrínseca): Cov = B[s,s']·k(x,x'), B = WWᵀ + diag(κ) aprendida
  PCM  (correlação de Pearson): Cov = σ²·B[s,s']·k(x,x'), B FIXA = correlações de Pearson entre as fontes nos pontos
       medidos por ambas; com < 4 pontos em comum, entre as médias de GPs independentes nos pontos observados
Aquisição: gradiente do conhecimento (KG) DISCRETO e EXATO (Frazier, Powell & Dayanik 2009) por unidade de custo
    KG(x, s) = E[max_{x'∈D} μ_{n+1}(x', alvo) | y_s(x)] − max_{x'∈D} μ_n(x', alvo);   escolhe argmax KG(x, s)/c_s
μ_{n+1} é afim em Z ~ N(0, 1): a esperança do máximo de retas sai do envelope superior, sem Monte Carlo.

Simulação (dados SIMULADOS, code/benchmarking/simulator.py): a TEM mede o tamanho com ~2 % de erro; o DLS vê o
diâmetro hidrodinâmico (casca de 3 nm, inflado pelo GO); o UV-Vis infere o tamanho pelo LSPR via Mie — e é quase
CEGO abaixo de ~30 nm (o LSPR anda < 1 nm e nem é monótono), justamente perto do alvo: um caso em que a fonte barata
pode enganar, e que o benchmark precisa mostrar. `benchmark` compara MGP/ICM/PCM × só-TEM no mesmo orçamento (arrependimento simples da
recomendação × custo acumulado; custo até o critério com censura).

Uso:
    python code/miso/miso.py run --model MGP --seed 0 [--budget 160]
    python code/miso/miso.py benchmark --seeds 8 --workers 4               # SIMULADO -> outputs/miso/
"""
from __future__ import annotations

import argparse
import functools
import json
import os
import sys
import time
import warnings

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
for _sub in ("benchmarking", "spectral", "campaign", "transfer_learning"):
    sys.path.insert(0, os.path.join(HERE, "..", _sub))
import simulator as sim  # noqa: E402

MODELS = ("MGP", "ICM", "PCM", "TEM-only")
DEFAULT_SOURCES = (("TEM", 20.0), ("UV-Vis", 1.0), ("DLS", 2.0))     # índice 0 = fonte-alvo


def sources_from_prereg() -> tuple[tuple[str, float], ...]:
    """Fontes e custos do pré-registro, com a fonte-alvo no índice 0."""
    try:
        import prereg
        m = prereg.load()["miso"]
        src = [(s["name"], float(s["cost"])) for s in m["sources"]]
        tgt = m.get("target_source", src[-1][0])
        return tuple(sorted(src, key=lambda s: s[0] != tgt))
    except Exception:            # noqa: BLE001 — pré-registro ausente/inválido: valores padrão documentados
        return DEFAULT_SOURCES


def objective_from_size(d, target: float = 20.0):
    return -np.log(np.asarray(d, float) / target) ** 2


# ---------------------------------------------------------------------------------------------- fontes simuladas

@functools.lru_cache(maxsize=1)
def _lspr_table() -> tuple[np.ndarray, np.ndarray]:
    import uvvis
    d = np.exp(np.linspace(np.log(4.0), np.log(120.0), 160))
    return d, np.array([uvvis.lspr(sim.WL, sim.unit_spectrum(x, 0.08))["LSPR_nm"] for x in d])


def size_from_lspr(lspr_nm: float, tol_nm: float = 0.5) -> float:
    """Inversão de Mie LSPR → tamanho como média a posteriori (prior uniforme em ln d, verossimilhança gaussiana de
    largura `tol_nm`). O LSPR NÃO é monótono abaixo de ~30 nm (amortecimento de superfície desloca as partículas
    pequenas para o vermelho; mínimo ≈ 523 nm em ~15 nm): ali a inversão é ambígua e devolve um tamanho "médio"."""
    d, lam = _lspr_table()
    w = np.exp(-0.5 * ((lam - lspr_nm) / tol_nm) ** 2)
    if w.sum() < 1e-12:
        return float(d[np.argmin(np.abs(lam - lspr_nm))])
    return float(np.exp(np.sum(w * np.log(d)) / w.sum()))


class SimulatedSources:
    """Fontes de informação SIMULADAS sobre o mesmo processo (uma nova síntese por consulta)."""

    def __init__(self, names: tuple[str, ...], batch: str = "L1", seed: int = 0, target_nm: float = 20.0):
        self.names, self.batch, self.target = names, batch, target_nm
        self.rng = np.random.default_rng(seed)
        self.space = dict(sim.SPACE)

    def cond(self, u: np.ndarray) -> dict:
        return {k: lo + float(v) * (hi - lo) for (k, (lo, hi)), v in zip(self.space.items(), u)}

    def size(self, u: np.ndarray, source: str) -> float:
        c = self.cond(u)
        r = sim.simulate(c, self.batch, rng=self.rng)
        d = r["size_mean_nm"]
        if source == "TEM":
            return d * (1 + self.rng.normal(0, 0.02))
        if source == "DLS":
            return (d + 3.0) * (1 + 1.5 * c["GO_mg_mL"]) * (1 + self.rng.normal(0, 0.04))
        if source == "UV-Vis":
            return size_from_lspr(r["LSPR_nm"]) if np.isfinite(r["LSPR_nm"]) else 4.0
        raise ValueError(f"fonte desconhecida {source!r}")

    def measure(self, u: np.ndarray, source: str) -> float:
        return float(objective_from_size(max(self.size(u, source), 1.0), self.target))

    def truth(self, U: np.ndarray) -> np.ndarray:
        """Objetivo ESPERADO (sem ruído) da fonte-alvo: referência para o arrependimento."""
        return np.array([objective_from_size(sim.simulate(self.cond(u), self.batch, noiseless=True)["size_mean_nm"],
                                             self.target) for u in U])


# ---------------------------------------------------------------------------------------------- modelos

def _kernels():
    from gpytorch.kernels import Kernel

    class SourceIndicator(Kernel):
        """k = 1[s = j]·1[s' = j]: liga o termo de discrepância δ_j só às observações da fonte j."""
        has_lengthscale = False

        def __init__(self, j: int, **kw):
            super().__init__(**kw)
            self.j = j

        def forward(self, x1, x2, diag=False, **params):
            a, b = (x1[..., 0].round() == self.j).to(x1.dtype), (x2[..., 0].round() == self.j).to(x1.dtype)
            return a * b if diag else a.unsqueeze(-1) * b.unsqueeze(-2)

    class FixedTask(Kernel):
        """k = B[s, s'] com B fixa (sem hiperparâmetros): o PCM."""
        has_lengthscale = False

        def __init__(self, B, **kw):
            import torch
            super().__init__(**kw)
            self.register_buffer("B", torch.as_tensor(B, dtype=torch.double))

        def forward(self, x1, x2, diag=False, **params):
            i, j = x1[..., 0].round().long(), x2[..., 0].round().long()
            return self.B[i, j] if diag else self.B[i.unsqueeze(-1), j.unsqueeze(-2)]

    return SourceIndicator, FixedTask


def nearest_correlation(B: np.ndarray, floor: float = 1e-3) -> np.ndarray:
    """Projeta uma matriz simétrica na matriz de correlação PSD mais próxima (corte de autovalores)."""
    B = (B + B.T) / 2
    w, V = np.linalg.eigh(B)
    B = (V * np.maximum(w, floor)) @ V.T
    d = np.sqrt(np.diag(B))
    return B / np.outer(d, d)


def pearson_matrix(U: np.ndarray, s: np.ndarray, y: np.ndarray, n_sources: int, min_overlap: int = 4) -> np.ndarray:
    """Correlações entre fontes: Pearson nos pontos medidos por ambas; com poucos pontos em comum, Pearson entre as
    médias de GPs independentes (um por fonte) avaliadas em todos os pontos observados."""
    B = np.eye(n_sources)
    keys = [tuple(np.round(u, 9)) for u in U]
    by = [{k: v for k, v, ss in zip(keys, y, s) if ss == j} for j in range(n_sources)]
    preds = None
    for i in range(n_sources):
        for j in range(i + 1, n_sources):
            common = sorted(set(by[i]) & set(by[j]))
            if len(common) >= min_overlap:
                a, b = [by[i][k] for k in common], [by[j][k] for k in common]
            else:
                if preds is None:
                    preds = [_independent_mean(U[s == k], y[s == k], U) for k in range(n_sources)]
                a, b = preds[i], preds[j]
            r = np.corrcoef(a, b)[0, 1] if np.std(a) > 0 and np.std(b) > 0 else 0.0
            B[i, j] = B[j, i] = float(np.clip(np.nan_to_num(r), -0.99, 0.99))
    return nearest_correlation(B)


def _independent_mean(Ux: np.ndarray, y: np.ndarray, Uq: np.ndarray) -> np.ndarray:
    import torch
    from botorch.models import SingleTaskGP
    from botorch.models.transforms import Standardize
    if len(y) < 3:
        return np.full(len(Uq), float(np.mean(y)) if len(y) else 0.0)
    m = SingleTaskGP(torch.tensor(Ux), torch.tensor(y).unsqueeze(-1), outcome_transform=Standardize(1))
    _fit(m)
    with torch.no_grad():
        return m.posterior(torch.tensor(Uq)).mean.squeeze(-1).numpy()


def _fit(model) -> None:
    import torch
    from botorch.exceptions.errors import ModelFittingError
    from botorch.fit import fit_gpytorch_mll
    from gpytorch.mlls import ExactMarginalLogLikelihood
    mll = ExactMarginalLogLikelihood(model.likelihood, model)
    for k in range(4):
        try:
            with torch.random.fork_rng():
                torch.manual_seed(101 * (k + 1))
                fit_gpytorch_mll(mll)
            return
        except ModelFittingError:
            continue
    mll.eval()


def build_model(kind: str, U: np.ndarray, s: np.ndarray, y: np.ndarray, noise_var: np.ndarray, n_sources: int,
                fit: bool = True, state: dict | None = None):
    """GP sobre (x ∈ [0,1]^D, fonte) com o kernel do modelo `kind`. `state` reaproveita hiperparâmetros (sem ajuste)."""
    import torch
    from botorch.models import SingleTaskGP
    from botorch.models.transforms import Standardize
    from gpytorch.kernels import IndexKernel, MaternKernel, ScaleKernel
    from gpytorch.priors import GammaPrior, LogNormalPrior
    SourceIndicator, FixedTask = _kernels()
    D = U.shape[1]
    xd = list(range(D))

    # Priors (estimativa MAP): sem eles, com 2–3 pontos da fonte-alvo a escala de f_alvo colapsa para 0 no MGP
    # (não identificável) e o KG fica nulo. Comprimento: o prior padrão do BoTorch escalado pela dimensão;
    # escalas: Gamma(2, ·) tem densidade 0 em 0 — f_alvo com média 1 (Y padronizado) e discrepâncias δ_s com 0,5.
    def matern():
        return MaternKernel(nu=2.5, ard_num_dims=D, active_dims=xd,
                            lengthscale_prior=LogNormalPrior(np.sqrt(2) + np.log(D) / 2, np.sqrt(3)))

    def scaled(k, mean_var=1.0):
        return ScaleKernel(k, outputscale_prior=GammaPrior(2.0, 2.0 / mean_var))
    if kind == "TEM-only" or n_sources == 1:
        covar = scaled(matern())
    elif kind == "MGP":
        covar = scaled(matern())
        for j in range(1, n_sources):
            covar = covar + scaled(matern(), 0.5) * SourceIndicator(j, active_dims=[D])
    elif kind == "ICM":
        covar = matern() * IndexKernel(num_tasks=n_sources, rank=1, active_dims=[D])
    elif kind == "PCM":       # B é buffer: com `state`, a B do último ajuste é reaproveitada junto
        B = np.eye(n_sources) if state is not None else pearson_matrix(U, s, y, n_sources)
        covar = scaled(matern() * FixedTask(B, active_dims=[D]))
    else:
        raise ValueError(f"modelo {kind!r}; use {MODELS}")
    X = torch.tensor(np.c_[U, s], dtype=torch.double)
    Y = torch.tensor(y, dtype=torch.double).unsqueeze(-1)
    Yv = torch.tensor(noise_var[s.astype(int)], dtype=torch.double).unsqueeze(-1)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")          # a coluna da fonte não está em [0, 1] (é um rótulo)
        m = SingleTaskGP(X, Y, train_Yvar=Yv, covar_module=covar, outcome_transform=Standardize(1))
        if state is not None:
            try:
                m.load_state_dict(state, strict=False)
                fit = False
            except RuntimeError:
                fit = True
        if fit:
            _fit(m)
    m.eval()
    return m


# ---------------------------------------------------------------------------------------------- KG exato

def expected_max_affine(a: np.ndarray, b: np.ndarray) -> float:
    """E[max_i (a_i + b_i Z)] − max_i a_i, Z ~ N(0,1), exato pelo envelope superior das retas (Frazier et al. 2009)."""
    from scipy.stats import norm
    a, b = np.asarray(a, float), np.asarray(b, float)
    o = np.lexsort((a, b))
    a, b = a[o], b[o]
    keep = np.r_[b[1:] != b[:-1], True]              # mesma inclinação: fica a de maior intercepto
    a, b = a[keep], b[keep]
    A, B, C = [a[0]], [b[0]], [-np.inf]
    for ai, bi in zip(a[1:], b[1:]):
        while True:
            z = (A[-1] - ai) / (bi - B[-1])
            if z <= C[-1]:
                A.pop(), B.pop(), C.pop()
            else:
                break
        A.append(ai), B.append(bi), C.append(z)
    A, B = np.array(A), np.array(B)
    lo, hi = np.array(C), np.r_[C[1:], np.inf]
    e = np.sum(A * (norm.cdf(hi) - norm.cdf(lo)) + B * (norm.pdf(lo) - norm.pdf(hi)))
    return float(max(e - a.max(), 0.0))


def kg_per_cost(model, D: np.ndarray, costs: np.ndarray, noise_var: np.ndarray, sources: list[int]) -> np.ndarray:
    """KG(x, s)/c_s para todo x ∈ D e s ∈ `sources` (−inf nas fontes fora da lista). Retorna (S × M)."""
    import torch
    M, S = len(D), len(costs)
    Z = np.vstack([np.c_[D, np.full(M, j)] for j in range(S)])
    with torch.no_grad():
        post = model.posterior(torch.tensor(Z, dtype=torch.double))
        mu = post.mean.squeeze(-1).numpy()
        cov = post.mvn.covariance_matrix.numpy()
    a = mu[:M]
    out = np.full((S, M), -np.inf)
    for j in sources:
        for i in range(M):
            c = j * M + i
            sd = np.sqrt(max(cov[c, c] + noise_var[j], 1e-12))
            out[j, i] = expected_max_affine(a, cov[:M, c] / sd) / costs[j]
    return out


# ---------------------------------------------------------------------------------------------- campanha

def pilot_noise(src: SimulatedSources, names: tuple[str, ...], n: int = 5) -> np.ndarray:
    """Variância do objetivo por fonte a partir de réplicas no centro do espaço (como o piloto pré-registrado)."""
    u0 = np.full(len(src.space), 0.5)
    return np.array([max(np.var([src.measure(u0, s) for _ in range(n)], ddof=1), 1e-5) for s in names])


def run(kind: str, seed: int = 0, budget: float = 160.0, sources=None, n_candidates: int = 128,
        n_init_cheap: int = 8, n_init_target: int = 2, refit_every: int = 4, max_iter: int = 150,
        batch: str = "L1", verbose: bool = False) -> dict:
    """Uma campanha simulada. Retorna o histórico (custo acumulado, arrependimento simples da recomendação)."""
    from scipy.stats import qmc
    sources = tuple(sources or sources_from_prereg())
    names = tuple(n for n, _ in sources)
    costs = np.array([c for _, c in sources])
    S = len(names)
    src = SimulatedSources(names, batch, seed)
    rng = np.random.default_rng(seed)
    D = qmc.Sobol(len(src.space), seed=seed).random(n_candidates)
    truth = src.truth(D)
    best_true = truth.max()
    noise = pilot_noise(src, names)
    use = [0] if kind == "TEM-only" else list(range(S))
    U, s, y = [], [], []
    spent = 0.0
    init = qmc.LatinHypercube(len(src.space), seed=seed + 1).random(n_init_cheap)
    if kind == "TEM-only":            # mesmo custo inicial que os braços MISO, todo em TEM
        n_t = max(1, int(round((n_init_cheap * costs[1:].sum() + n_init_target * costs[0]) / costs[0])))
        plan = [(u, 0) for u in init[:n_t]] + [(u, 0) for u in rng.random((max(0, n_t - len(init)), len(src.space)))]
    else:
        plan = [(u, j) for u in init for j in range(1, S)] + [(u, 0) for u in init[:n_init_target]]
    for u, j in plan:
        U.append(u), s.append(j), y.append(src.measure(u, names[j]))
        spent += costs[j]
    hist, state, it = [], None, 0
    truth_cache: dict = {}

    def true_at(u):
        key = tuple(np.round(u, 12))
        if key not in truth_cache:
            truth_cache[key] = float(src.truth(np.asarray([u]))[0])
        return truth_cache[key]

    def record(model):
        """Duas regras de recomendação: (a) argmax da média a posteriori da fonte-alvo no conjunto D; (b) CONFIRMADA:
        entre os pontos já medidos pela fonte-alvo, o de maior média a posteriori — não aposta num ponto que só as
        fontes baratas viram (protege contra fontes baratas enganosas perto do ótimo)."""
        import torch
        with torch.no_grad():
            mu = model.posterior(torch.tensor(np.c_[D, np.zeros(len(D))], dtype=torch.double)).mean.squeeze(-1).numpy()
            Ut = np.array([u for u, ss in zip(U, s) if ss == 0])
            mt = model.posterior(torch.tensor(np.c_[Ut, np.zeros(len(Ut))], dtype=torch.double)).mean.squeeze(-1).numpy()
        k = int(np.argmax(mu))
        hist.append({"cost": spent, "regret": float(best_true - truth[k]),
                     "regret_confirmed": max(float(best_true - true_at(Ut[int(np.argmax(mt))])), 0.0),
                     "n_obs": len(y), "n_target": int(np.sum(np.array(s) == 0))})
    while True:
        Ua, sa, ya = np.array(U), np.array(s), np.array(y)
        refit = state is None or it % refit_every == 0
        model = build_model(kind, Ua, sa, ya, noise, S, fit=refit, state=None if refit else state)
        state = {k: v for k, v in model.state_dict().items() if k.startswith(("covar_module", "mean_module"))}
        record(model)
        afford = [j for j in use if spent + costs[j] <= budget + 1e-9]
        if not afford or it >= max_iter:
            break
        sc = kg_per_cost(model, D, costs, noise, afford)
        if not np.isfinite(sc).any() or sc.max() <= 0:          # KG nulo: explora a maior variância por custo
            j = min(afford, key=lambda q: costs[q])
            i = int(rng.integers(len(D)))
        else:
            j, i = np.unravel_index(int(np.argmax(sc)), sc.shape)
        U.append(D[i]), s.append(int(j)), y.append(src.measure(D[i], names[j]))
        spent += costs[j]
        it += 1
        if verbose:
            print(f"[{kind} s{seed}] it {it:3d} fonte {names[j]:7s} custo {spent:6.1f} regret {hist[-1]['regret']:.4f}")
    return {"model": kind, "seed": seed, "budget": budget, "sources": dict(sources), "history": hist,
            "final_regret": hist[-1]["regret"], "final_regret_confirmed": hist[-1]["regret_confirmed"],
            "queries": {n: int(np.sum(np.array(s) == k)) for k, n in enumerate(names)}}


def cost_to_criterion(history: list[dict], threshold: float, key: str = "regret") -> float:
    """Custo acumulado até o arrependimento ficar ≤ limiar (inf = censurado no orçamento)."""
    for h in history:
        if h[key] <= threshold:
            return h["cost"]
    return float("inf")


def summarize_runs(runs: list[dict], budget: float, threshold: float) -> dict:
    import hierarchical
    out = {}
    for kind in dict.fromkeys(r["model"] for r in runs):
        rr = [r for r in runs if r["model"] == kind]
        row = {"queries_mean": {k: float(np.mean([r["queries"][k] for r in rr])) for k in rr[0]["queries"]},
               "best_regret_during_mean": float(np.mean([min(h["regret"] for h in r["history"]) for r in rr]))}
        for rule, key in (("", "regret"), ("_confirmed", "regret_confirmed")):
            fr = np.array([r["history"][-1][key] for r in rr])
            ctc = np.array([cost_to_criterion(r["history"], threshold, key) for r in rr])
            row.update({f"final_regret{rule}_mean": float(fr.mean()), f"final_regret{rule}_median": float(np.median(fr)),
                        f"hit_rate{rule}": float(np.mean(np.isfinite(ctc))),
                        f"cost_to_criterion{rule}_rmst": hierarchical.censored_mean(ctc, budget)})
        out[kind] = row
    return out


def _bench_job(kind: str, seed: int, budget: float, kw: dict) -> dict:
    import torch
    torch.set_num_threads(1)
    warnings.simplefilter("ignore")
    t0 = time.time()
    r = run(kind, seed, budget, **kw)
    r["seconds"] = round(time.time() - t0, 1)
    return r


def benchmark(seeds: int = 8, budget: float = 160.0, models=MODELS, out: str | None = None, threshold: float = 0.01,
              workers: int = 1, **kw) -> dict:
    from concurrent.futures import ProcessPoolExecutor
    jobs = [(kind, seed, budget, kw) for seed in range(seeds) for kind in models]
    if workers > 1:
        with ProcessPoolExecutor(workers) as ex:
            runs = list(ex.map(_bench_job, *zip(*jobs)))
    else:
        runs = [_bench_job(*j) for j in jobs]
    for r in runs:
        print(f"{r['model']:8s} semente {r['seed']}: arrependimento final {r['final_regret']:.4f}  "
              f"consultas {r['queries']}  ({r['seconds']} s)", flush=True)
    summary = summarize_runs(runs, budget, threshold)
    res = {"SIMULADO": True, "criterion_regret": threshold, "budget": budget, "seeds": seeds, "summary": summary,
           "runs": runs}
    if out:
        os.makedirs(out, exist_ok=True)
        with open(os.path.join(out, "miso_benchmark.json"), "w", encoding="utf-8") as fh:
            json.dump(res, fh, indent=1, default=float)
    return res


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("run")
    p.add_argument("--model", choices=MODELS, default="MGP")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--budget", type=float, default=160.0)
    p.add_argument("--candidates", type=int, default=128)
    b = sub.add_parser("benchmark")
    b.add_argument("--seeds", type=int, default=8)
    b.add_argument("--budget", type=float, default=160.0)
    b.add_argument("--models", nargs="+", choices=MODELS, default=list(MODELS))
    b.add_argument("--candidates", type=int, default=128)
    b.add_argument("--threshold", type=float, default=0.01, help="critério de arrependimento (unidades do objetivo)")
    b.add_argument("--workers", type=int, default=1, help="processos em paralelo")
    b.add_argument("--out", default=os.path.join(HERE, "..", "..", "outputs", "miso"))
    a = ap.parse_args()
    if a.cmd == "run":
        r = run(a.model, a.seed, a.budget, n_candidates=a.candidates, verbose=True)
        print(json.dumps({k: v for k, v in r.items() if k != "history"}, indent=1))
    else:
        res = benchmark(a.seeds, a.budget, a.models, a.out, a.threshold, a.workers, n_candidates=a.candidates)
        print(json.dumps(res["summary"], indent=1, default=float))


if __name__ == "__main__":
    main()
