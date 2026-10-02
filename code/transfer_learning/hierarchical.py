#!/usr/bin/env python3
"""GP hierárquico para transferência entre lotes e fornecedores (§4.7, Objetivo 5) e métrica de transferência.

Modelo (efeitos aleatórios funcionais, aninhados):
    f(x, fornecedor s, lote b) = g(x) + h_s(x) + u_b(x)
    k((x,s,b),(x',s',b')) = k_g(x,x') + 1[s = s'] · k_s(x,x') + 1[b = b'] · k_b(x,x')
com k_g, k_s, k_b Matérn-5/2 + ARD independentes. Consequências úteis para a campanha:
  * um lote NOVO (sem dados) é previsto pela parte global + a do seu fornecedor, com a variância extra de k_b — a
    incerteza honesta de "lote não visto" (o GP multitarefa/ICM não prevê tarefa sem dados);
  * o quanto cada nível importa sai das escalas aprendidas (fração de variância global / fornecedor / lote);
  * com um único fornecedor o nível do meio some sozinho (indicador constante).

`experiments_to_match` implementa o critério da proposta: "a validade do transfer learning será julgada pelo número
de experimentos necessários para alcançar desempenho equivalente ao treinamento do zero".
"""
from __future__ import annotations

import numpy as np


def _delta_kernel_class():
    from gpytorch.kernels import Kernel

    class DeltaKernel(Kernel):
        """k(i, j) = 1 se o rótulo inteiro na coluna ativa é igual, 0 caso contrário (sem hiperparâmetros)."""
        has_lengthscale = False

        def forward(self, x1, x2, diag=False, **params):
            a, b = x1[..., 0], x2[..., 0]
            if diag:
                return (a == b).to(x1.dtype)
            return (a.unsqueeze(-1) == b.unsqueeze(-2)).to(x1.dtype)

    return DeltaKernel


def matern52(d: int, active_dims=None):
    """Matérn-5/2 + ARD com o prior de comprimento escalado pela dimensão (padrão do BoTorch; Hvarfner et al., ICML
    2024): sem ele, com poucas dezenas de pontos a máxima verossimilhança leva os comprimentos a ~0 e o GP vira ruído
    branco (média constante longe dos dados, aquisição e valor da informação nulos)."""
    import math
    from gpytorch.kernels import MaternKernel
    from gpytorch.priors import LogNormalPrior
    return MaternKernel(nu=2.5, ard_num_dims=d, active_dims=active_dims,
                        lengthscale_prior=LogNormalPrior(math.sqrt(2) + math.log(d) / 2, math.sqrt(3)))


def hierarchical_kernel(recipe_dims: list[int], level_dims: list[int]):
    """k_g(x) + Σ_ℓ δ_ℓ · k_ℓ(x) sobre as colunas `recipe_dims` (contínuas) e `level_dims` (rótulos inteiros)."""
    from gpytorch.kernels import ScaleKernel
    Delta = _delta_kernel_class()
    d = len(recipe_dims)
    k = ScaleKernel(matern52(d, recipe_dims))
    for lv in level_dims:
        k = k + ScaleKernel(matern52(d, recipe_dims)) * Delta(active_dims=[lv])
    return k


def build_hierarchical_gp(tx, ty, recipe_dims: list[int], level_dims: list[int], bounds, train_Yvar=None):
    """SingleTaskGP com o kernel hierárquico; as colunas de nível não são normalizadas."""
    from botorch.models import SingleTaskGP
    from botorch.models.transforms import Normalize, Standardize
    d = tx.shape[-1]
    return SingleTaskGP(tx, ty, train_Yvar=train_Yvar, covar_module=hierarchical_kernel(recipe_dims, level_dims),
                        input_transform=Normalize(d, indices=recipe_dims, bounds=bounds),
                        outcome_transform=Standardize(1))


def variance_shares(model) -> dict:
    """Fração da variância a priori explicada por cada nível (global, depois níveis na ordem de level_dims)."""
    from gpytorch.kernels import ProductKernel, ScaleKernel
    parts, k = [], model.covar_module
    stack = list(k.kernels) if hasattr(k, "kernels") and not isinstance(k, ProductKernel) else [k]
    for sub in stack:
        sk = sub if isinstance(sub, ScaleKernel) else next(x for x in sub.kernels if isinstance(x, ScaleKernel))
        parts.append(float(sk.outputscale.detach()))
    tot = sum(parts) or 1.0
    names = ["global"] + [f"nivel_{i}" for i in range(1, len(parts))]
    return {n: p / tot for n, p in zip(names, parts)}


def experiments_to_threshold(curve: np.ndarray, threshold: float, lower_is_better: bool = True) -> float:
    """Nº de experimentos (índice 1-based) até a curva de melhor-acumulado atingir o limiar; inf se não atingir
    (observação censurada — trate com `censored_mean`)."""
    c = np.asarray(curve, float)
    hit = np.where(c <= threshold)[0] if lower_is_better else np.where(c >= threshold)[0]
    return float(hit[0] + 1) if hit.size else float("inf")


def censored_mean(times: np.ndarray, budget: float) -> dict:
    """Média restrita (RMST) do nº de experimentos até o critério, com censura no orçamento (Kaplan–Meier)."""
    t = np.asarray(times, float)
    event = np.isfinite(t)
    t = np.where(event, t, budget)
    grid = np.unique(np.r_[0.0, np.sort(t[event]), budget])
    surv, s = [], 1.0
    for g in grid:
        at_risk = np.sum(t >= g)
        d = np.sum((t == g) & event)
        if at_risk > 0 and d > 0:
            s *= 1 - d / at_risk
        surv.append(s)
    surv = np.array(surv)
    rmst = float(np.sum(np.diff(grid) * surv[:-1]))
    return {"rmst": rmst, "fraction_reached": float(event.mean()), "budget": float(budget)}


def experiments_to_match(transfer_curves: np.ndarray, scratch_curves: np.ndarray, scratch_budget: int,
                         lower_is_better: bool = True) -> dict:
    """Critério da proposta (§4.7): desempenho de referência = mediana do do-zero ao fim do orçamento; mede quantos
    experimentos cada estratégia leva até alcançá-lo (com censura) e a economia relativa do transfer."""
    ref = float(np.median(np.asarray(scratch_curves)[:, scratch_budget - 1]))
    tt = np.array([experiments_to_threshold(c, ref, lower_is_better) for c in transfer_curves])
    ts = np.array([experiments_to_threshold(c, ref, lower_is_better) for c in scratch_curves])
    budget = max(np.asarray(transfer_curves).shape[1], np.asarray(scratch_curves).shape[1])
    a, b = censored_mean(tt, budget), censored_mean(ts, budget)
    return {"reference_performance": ref, "transfer": a, "scratch": b,
            "relative_saving": 1 - a["rmst"] / b["rmst"] if b["rmst"] > 0 else float("nan")}
