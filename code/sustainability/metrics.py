#!/usr/bin/env python3
"""Sustentabilidade e custo-benefício (§4.14), fronteira do sistema = síntese + caracterização.

* E-factor simplificado = massa de resíduos / massa de produto (Sheldon).
* EcoScale (Van Aken, Strekowski & Patiny, Beilstein J. Org. Chem. 2006, 2, 3): 100 − Σ penalidades. A penalidade
  de rendimento, (100 − rendimento%)/2, é calculada aqui; as demais (preço, segurança, montagem, temperatura/tempo,
  isolamento) devem ser atribuídas a partir da tabela do artigo e passadas em `penalties` — não são inventadas aqui.
* Custo por informação útil: CPU = custo total / (Δperda acumulada + λ·Δincerteza), com λ definido a priori.
* Comparação de dois fluxos (com e sem caracterização adicional) a partir das tabelas do laboratório.

Uso:
    python code/sustainability/metrics.py --waste-g 12.4 --product-g 0.018 --yield 82 --penalty safety=10 --penalty price=3
    python code/sustainability/metrics.py --cpu --cost 350 --dloss 0.8 --dunc 0.15 --lam 2
"""
from __future__ import annotations

import argparse
import json


def e_factor(waste_mass_g: float, product_mass_g: float) -> float:
    return waste_mass_g / product_mass_g


def ecoscale(yield_pct: float, penalties: dict[str, float] | None = None) -> dict:
    pen = {"yield": (100.0 - yield_pct) / 2.0, **(penalties or {})}
    score = 100.0 - sum(pen.values())
    grade = "excelente" if score > 75 else ("aceitável" if score >= 50 else "inadequado")
    return {"ecoscale": score, "grade": grade, "penalties": pen}


def cost_per_useful_information(total_cost: float, delta_loss: float, delta_uncertainty: float, lam: float) -> float:
    """CPU = custo / (Δperda acumulada + λ·Δincerteza). Δ positivos = melhora (redução de perda/incerteza)."""
    denom = delta_loss + lam * delta_uncertainty
    return float("inf") if denom <= 0 else total_cost / denom


def compare_flows(flow_a: dict, flow_b: dict, lam: float) -> dict:
    """flow = {"cost": R$, "waste_g": g, "product_g": g, "delta_loss": ..., "delta_uncertainty": ...}."""
    out = {}
    for name, f in (("A", flow_a), ("B", flow_b)):
        out[name] = {"E_factor": e_factor(f["waste_g"], f["product_g"]),
                     "CPU": cost_per_useful_information(f["cost"], f["delta_loss"], f["delta_uncertainty"], lam)}
    out["caracterização_compensa"] = out["B"]["CPU"] < out["A"]["CPU"]
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--waste-g", type=float)
    ap.add_argument("--product-g", type=float)
    ap.add_argument("--yield", dest="yld", type=float)
    ap.add_argument("--penalty", action="append", default=[], help="nome=pontos (tabela de Van Aken et al. 2006)")
    ap.add_argument("--cpu", action="store_true")
    ap.add_argument("--cost", type=float)
    ap.add_argument("--dloss", type=float)
    ap.add_argument("--dunc", type=float, default=0.0)
    ap.add_argument("--lam", type=float, default=1.0)
    a = ap.parse_args()
    out = {}
    if a.waste_g is not None and a.product_g:
        out["E_factor"] = e_factor(a.waste_g, a.product_g)
    if a.yld is not None:
        out.update(ecoscale(a.yld, {k: float(v) for k, v in (p.split("=", 1) for p in a.penalty)}))
    if a.cpu:
        out["CPU"] = cost_per_useful_information(a.cost, a.dloss, a.dunc, a.lam)
    print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
