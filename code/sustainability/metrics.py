#!/usr/bin/env python3
"""Sustentabilidade e custo-benefício (§4.14), fronteira do sistema = síntese + caracterização.

* E-factor simplificado = massa de resíduos / massa de produto (Sheldon). Em `from-lab` saem as duas formas de
  Sheldon (Green Chem. 2017, 19, 18): sEF (sem água: insumos não aquosos − produto) e cEF (com água: resíduos medidos).
* EcoScale (Van Aken, Strekowski & Patiny, Beilstein J. Org. Chem. 2006, 2, 3): 100 − Σ penalidades. A penalidade
  de rendimento, (100 − rendimento%)/2, é calculada aqui; as demais (preço, segurança, montagem, temperatura/tempo,
  isolamento) devem ser atribuídas a partir da tabela do artigo e passadas em `penalties` — não são inventadas aqui.
* Custo por informação útil: CPU = custo total / (Δperda acumulada + λ·Δincerteza), com λ definido a priori.
* Comparação de dois fluxos (com e sem caracterização adicional) a partir das tabelas do laboratório
  (`from-lab`): a tabela `resources` dá custo, massa de insumos e de resíduos por fluxo; a massa de produto vem das
  sínteses (Au reduzido + GO); Δperda e Δincerteza do fluxo com caracterização vêm do valor da informação
  (`code/decision/voi.py`, EVSI) ou da comparação de braços da campanha. λ e o conjunto "caracterização básica" são
  os do pré-registro — nada é escolhido depois de ver os resultados.

Uso:
    python code/sustainability/metrics.py --waste-g 12.4 --product-g 0.018 --yield 82 --penalty safety=10 --penalty price=3
    python code/sustainability/metrics.py --cpu --cost 350 --dloss 0.8 --dunc 0.15 --lam 2
    python code/sustainability/metrics.py from-lab datasets/lab [--voi outputs/voi/voi.json]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

AU_G_MOL = 196.967
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


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


def product_mass_g(syn, char=None):
    """Massa de produto por síntese: Au(0) = [Au(III)]·V·M·rendimento (+ GO = c_GO·V). Rendimento de
    aunp_characterization (yield_pct) quando medido; senão 100 % (limite superior, marcado na saída)."""
    import pandas as pd
    v_l = pd.to_numeric(syn.get("total_volume_mL"), errors="coerce").fillna(10.0) / 1000.0
    au = pd.to_numeric(syn["HAuCl4_mM"], errors="coerce").fillna(0) / 1000.0 * v_l * AU_G_MOL
    y = pd.Series(1.0, index=syn.index)
    if char is not None and not char.empty:
        yy = char[char["quantity"] == "yield_pct"].groupby("synthesis_id")["value"].mean() / 100.0
        y = syn["synthesis_id"].map(yy).fillna(1.0).clip(0, 1)
    go = pd.to_numeric(syn.get("GO_mg_mL"), errors="coerce").fillna(0) / 1000.0 * v_l * 1000.0
    return pd.Series((au * y + go).to_numpy(), index=syn["synthesis_id"])


def flows_from_lab(lab: str, basic_techniques=("UV-Vis",)) -> dict:
    """Custo, insumos, resíduos e E-factor de dois fluxos: só caracterização básica × com a adicional."""
    import pandas as pd
    res = pd.read_csv(os.path.join(lab, "resources.csv"))
    syn = pd.read_csv(os.path.join(lab, "aunp_syntheses.csv"))
    if "status" in syn:
        syn = syn[syn["status"].fillna("done").astype(str) != "planned"]
    char_p = os.path.join(lab, "aunp_characterization.csv")
    char = pd.read_csv(char_p) if os.path.exists(char_p) else None
    prod = float(product_mass_g(syn, char).sum())
    tech = res["technique"].fillna("").astype(str)
    is_water = res["item"].fillna("").astype(str).str.lower().str.contains("água|agua|water|h2o")
    in_basic = (res["flow"] != "characterization") | tech.isin(basic_techniques)
    out = {}
    for name, sel in (("sem_caracterizacao_adicional", in_basic), ("com_caracterizacao_adicional", res.index == res.index)):
        r = res[sel]
        waste = pd.to_numeric(r.loc[r["category"] == "waste", "mass_g"], errors="coerce").sum()
        mass = pd.to_numeric(r["mass_g"], errors="coerce")
        is_in = r["category"].isin(["reagent", "solvent", "consumable"])
        inputs = mass[is_in].sum()
        inputs_dry = mass[is_in & ~is_water[sel]].sum()
        out[name] = {"cost": float(pd.to_numeric(r["cost"], errors="coerce").sum()), "waste_g": float(waste),
                     "inputs_g": float(inputs), "product_g": prod,
                     "sEF": e_factor(max(float(inputs_dry) - prod, 0.0), prod) if prod > 0 else float("nan"),
                     "cEF": e_factor(float(waste), prod) if prod > 0 and waste > 0 else
                     (e_factor(float(inputs) - prod, prod) if prod > 0 else float("nan")),
                     "cEF_basis": "resíduos medidos" if waste > 0 else "insumos − produto (sem resíduo registrado)",
                     "instrument_h": float(pd.to_numeric(r.loc[r["category"] == "instrument_time", "amount"],
                                                         errors="coerce").sum()),
                     "energy_kWh": float(pd.to_numeric(r.loc[r["category"] == "energy", "amount"], errors="coerce").sum())}
    out["product_mass_note"] = "rendimento medido" if char is not None and (char["quantity"] == "yield_pct").any() \
        else "rendimento 100 % assumido (limite superior)"
    return out


def decide_characterization(flows: dict, delta_loss: float, delta_uncertainty: float, lam: float,
                            value_per_unit: float | None = None, base_delta_loss: float = 0.0,
                            base_delta_uncertainty: float = 0.0) -> dict:
    """Caracterização adicional compensa se o custo por unidade de informação útil INCREMENTAL (custo extra /
    (Δperda + λ·Δincerteza) extras) não passa do valor pré-registrado por unidade de informação."""
    a = flows["sem_caracterizacao_adicional"]
    b = flows["com_caracterizacao_adicional"]
    extra_cost = b["cost"] - a["cost"]
    cpu_inc = cost_per_useful_information(extra_cost, delta_loss - base_delta_loss,
                                          delta_uncertainty - base_delta_uncertainty, lam)
    return {"custo_adicional": extra_cost, "ganho_util": (delta_loss - base_delta_loss)
            + lam * (delta_uncertainty - base_delta_uncertainty), "CPU_incremental": cpu_inc,
            "valor_por_unidade_preregistrado": value_per_unit,
            "caracterizacao_compensa": None if value_per_unit is None else bool(cpu_inc <= value_per_unit),
            "sEF_adicional": b["sEF"] - a["sEF"], "cEF_adicional": b["cEF"] - a["cEF"]}


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "from-lab":
        return main_from_lab(sys.argv[2:])
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


def main_from_lab(argv) -> None:
    ap = argparse.ArgumentParser(prog="metrics.py from-lab")
    ap.add_argument("lab")
    ap.add_argument("--voi", help="JSON do code/decision/voi.py (usa o EVSI como Δperda do fluxo com caracterização)")
    ap.add_argument("--dloss", type=float, help="Δperda do fluxo com caracterização (alternativa ao --voi)")
    ap.add_argument("--dunc", type=float, default=0.0)
    a = ap.parse_args(argv)
    sys.path.insert(0, os.path.join(ROOT, "code", "campaign"))
    import prereg
    cfg = prereg.load()
    sus = cfg["sustainability"]
    flows = flows_from_lab(a.lab, tuple(sus.get("basic_characterization", ["UV-Vis"])))
    out = {"flows": flows, "lambda": float(sus["cpu_lambda"])}
    dl, du = a.dloss, a.dunc
    if a.voi:
        v = json.load(open(a.voi, encoding="utf-8"))
        dl = float(v["evsi_all_techniques"])
        du = float(v.get("expected_sd_reduction_all", 0.0))
    if dl is not None:
        out["decision"] = decide_characterization(flows, dl, du, float(sus["cpu_lambda"]),
                                                  sus.get("value_per_unit_information"))
    print(json.dumps(out, indent=1, ensure_ascii=False, default=float))


if __name__ == "__main__":
    main()
