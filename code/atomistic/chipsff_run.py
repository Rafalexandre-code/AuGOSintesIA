#!/usr/bin/env python3
"""CHIPS-FF (JARVIS) para avaliar MLFFs universais contra o JARVIS-DFT, com os ajustes necessários para rodar aqui.

O CHIPS-FF (external/jarvis/chipsff) relaxa a estrutura e calcula EOS/módulo, energia de formação, tensor elástico,
superfícies, vacâncias, fônons e MD, comparando cada número com o JARVIS-DFT. Este invólucro:
  - usa a reconstrução offline do JARVIS-DFT (dft_3d, vacancydb, surfacedb) quando o figshare não responde (o
    CHIPS-FF sempre carrega esses conjuntos);
  - aceita um JVASP (ex.: JVASP-825, Au fcc) ou um arquivo local, preenchendo os valores de referência do JARVIS-DFT
    também para o arquivo local (--ref-jid);
  - contorna um defeito do CHIPS-FF: sem tensor elástico de referência, o padrão `[[0, 0, 0, [0, 0, 0, 0]]]` quebra
    em `[3][3]`; aqui a referência ausente vira uma matriz 6×6 de zeros (erro reportado como NaN).
Resultados em outputs/atomistic/chipsff/<nome>_<calculadora>/ (JSON + figuras do próprio CHIPS-FF).

Uso:
    python code/atomistic/chipsff_run.py --jid JVASP-825 --calculators mace chgnet sevennet
    python code/atomistic/chipsff_run.py --structure minha.vasp --ref-jid JVASP-825 --calculators mace \\
           --properties relax_structure calculate_ev_curve analyze_surfaces analyze_defects
Calculadoras do CHIPS-FF que funcionam sem rede para pesos: mace (GitHub), chgnet e sevennet (pesos no pacote);
alignn_ff exige o modelo do figshare (jarvis_data.py download --alignn-ff …).
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import jarvis_data as JD  # noqa: E402

FAST = ["relax_structure", "calculate_ev_curve", "calculate_formation_energy", "calculate_elastic_tensor",
        "analyze_surfaces", "analyze_defects"]


def run(calc, jid=None, structure=None, ref_jid=None, properties=FAST, surfaces=((1, 1, 1), (1, 0, 0)),
        outdir=None, steps=200):
    if not JD.figshare_reachable():
        JD.use_offline_cache()
        if not os.path.isfile(os.path.join(JD.offline_cache_dir(), "jarvis_data", JD.DFT3D_TAG + ".zip")):
            JD.build_offline_dft3d()
        JD.build_offline_defects()   # vacancydb/surfacedb (rápido)
    from chipsff.general_material_analyzer import MaterialsAnalyzer
    from jarvis.db.figshare import data

    dataset = data("dft_3d")
    chem = os.path.join(os.path.dirname(sys.modules["chipsff.general_material_analyzer"].__file__),
                        "chemical_potentials.json")
    relax = {"filter_type": "ExpCellFilter", "constant_volume": True, "fmax": 0.05, "steps": steps}
    kw = dict(calculator_type=calc, chemical_potentials_file=chem, properties_to_calculate=list(properties),
              bulk_relaxation_settings={"filter_type": "ExpCellFilter",
                                        "relaxation_settings": {"fmax": 0.05, "steps": steps, "constant_volume": False}},
              surface_settings={"indices_list": [list(s) for s in surfaces], "layers": 4, "vacuum": 18,
                                "relaxation_settings": relax},
              defect_settings={"generate_settings": {"on_conventional_cell": True, "enforce_c_size": 8, "extend": 1},
                               "relaxation_settings": relax},
              dataset=dataset)
    outdir = outdir or os.path.join(JD.ROOT, "outputs", "atomistic", "chipsff")
    os.makedirs(outdir, exist_ok=True)
    cwd = os.getcwd()
    os.chdir(outdir)
    try:
        if structure:
            an = MaterialsAnalyzer(structure_path=os.path.abspath(os.path.join(cwd, structure)), **kw)
            if ref_jid:
                an.reference_data = next(r for r in dataset if r["jid"] == ref_jid)
        else:
            an = MaterialsAnalyzer(jid=jid, **kw)
        ref = dict(an.reference_data or {})
        et = ref.get("elastic_tensor")
        no_elastic_ref = not isinstance(et, list) or len(et) < 4
        if no_elastic_ref:
            ref["elastic_tensor"] = [[0.0] * 6 for _ in range(6)]
        an.reference_data = ref
        an.run_all()
        name = an.output_dir
    finally:
        os.chdir(cwd)
    res_files = [f for f in os.listdir(os.path.join(outdir, name)) if f.endswith("_results.json")]
    res = json.load(open(os.path.join(outdir, name, res_files[0]))) if res_files else {}
    if no_elastic_ref:   # erro contra o zero de preenchimento não tem significado
        for k in ("err_c11", "err_c44"):
            if k in res.get("errors", {}):
                res["errors"][k] = None
        res["nota"] = "sem tensor elástico de referência (reconstrução offline): err_c11/err_c44 omitidos"
    return os.path.join(outdir, name), res


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--jid", help="material do JARVIS-DFT (ex.: JVASP-825 = Au fcc; JVASP-48 = grafite)")
    g.add_argument("--structure", help="POSCAR/CIF local")
    ap.add_argument("--ref-jid", help="JVASP de referência para o arquivo local")
    ap.add_argument("--calculators", nargs="+", default=["mace"])
    ap.add_argument("--properties", nargs="+", default=FAST)
    ap.add_argument("--steps", type=int, default=200)
    a = ap.parse_args(argv)
    for c in a.calculators:
        path, res = run(c, a.jid, a.structure, a.ref_jid, a.properties, steps=a.steps)
        keep = {k: res.get(k) for k in ("final_lattice_params", "modulus", "form_en", "elastic_tensor",
                                        "surface_energy", "vacancy_energy", "errors") if k in res}
        print(f"== {c}: {os.path.relpath(path, JD.ROOT)}")
        print(json.dumps(keep, indent=1, default=str)[:3000])


if __name__ == "__main__":
    main()
