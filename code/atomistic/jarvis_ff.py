#!/usr/bin/env python3
"""JARVIS-FF: validação de campos de força (clássicos e de ML) contra o JARVIS-DFT para o Au das AuNPs.

Calcula, com cada calculadora pedida, o parâmetro de rede e o módulo volumétrico (EOS), a energia de superfície
(111)/(100) e a energia de formação de vacância, e compara com o JARVIS-DFT (JVASP-825, fcc Au; reconstrução offline
ou arquivo original) e com o JARVIS-FF (dados LAMMPS versionados). Para o EAM clássico usa também o fluxo LAMMPS do
próprio jarvis-tools (jarvis.tasks.lammps.LammpsJob + inelast.mod → C11, C12, C44), que é como o JARVIS-FF foi gerado.

Superfícies e vacâncias de Au definem a forma e a estabilidade das AuNPs (facetas {111}/{100}); é o que o JARVIS-FF
chama de "caracterizar superfícies e defeitos para validar contra DFT". Os resultados vão para
outputs/atomistic/jarvis_ff_<data>.csv.

Uso:
    python code/atomistic/jarvis_ff.py --calculators lammps-eam mace-mp emt
    python code/atomistic/jarvis_ff.py --calculators alignn-ff --model-path outputs/atomistic/alignn_ff_model
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import calculators as C  # noqa: E402
import jarvis_data as JD  # noqa: E402

EV_A2_TO_J_M2 = 16.0217663


def _relax(atoms, fmax=0.02, steps=200):
    from ase.optimize import BFGS

    BFGS(atoms, logfile=None).run(fmax=fmax, steps=steps)
    return atoms


def bulk_eos(calc, element="Au", a_guess=4.08):
    """Parâmetro de rede (Å), energia por átomo (eV) e módulo volumétrico B (GPa) por Birch–Murnaghan."""
    from ase.build import bulk
    from ase.eos import EquationOfState
    from ase.units import kJ

    vols, ens = [], []
    for s in np.linspace(0.97, 1.03, 7):
        at = bulk(element, "fcc", a=a_guess * s, cubic=True)
        at.calc = calc
        vols.append(at.get_volume())
        ens.append(at.get_potential_energy())
    v0, e0, b = EquationOfState(vols, ens, eos="birchmurnaghan").fit()
    a0 = v0 ** (1 / 3)
    return a0, e0 / 4, b / kJ * 1.0e24


def surface_energy(calc, a0, e_bulk, element="Au", facet="111", layers=6):
    from ase.build import fcc100, fcc111

    build = fcc111 if facet == "111" else fcc100
    slab = build(element, size=(1, 1, layers), a=a0, vacuum=10.0, periodic=True)
    slab.calc = calc
    from ase.constraints import FixAtoms

    z = slab.positions[:, 2]
    slab.set_constraint(FixAtoms(mask=np.abs(z - np.median(z)) < 1.0))   # camadas centrais fixas (como bulk)
    _relax(slab)
    area = np.linalg.norm(np.cross(slab.cell[0], slab.cell[1]))
    return (slab.get_potential_energy() - len(slab) * e_bulk) / (2 * area) * EV_A2_TO_J_M2


def vacancy_energy(calc, a0, e_bulk, element="Au", rep=3):
    from ase.build import bulk

    sc = bulk(element, "fcc", a=a0, cubic=True).repeat(rep)
    del sc[0]
    sc.calc = calc
    _relax(sc, fmax=0.03, steps=150)
    return sc.get_potential_energy() - len(sc) * e_bulk


def jarvis_ff_elastic(workdir, a0=4.08):
    """C11, C12, C44 (GPa) pelo fluxo LAMMPS do jarvis-tools (JARVIS-FF), com o EAM Au_u3 em formato setfl."""
    import jarvis.tasks.lammps.templates as tpl
    from ase.build import bulk
    from jarvis.core.atoms import ase_to_atoms
    from jarvis.io.lammps.outputs import analyze_log
    from jarvis.tasks.lammps.lammps import LammpsJob

    tdir = os.path.dirname(tpl.__file__)
    os.makedirs(workdir, exist_ok=True)
    pot = C.au_setfl(os.path.join(workdir, "potentials"))
    # o inelast.mod do jarvis-tools inclui "/users/knc6/displace.mod" (caminho do autor): usamos uma cópia corrigida
    mod = os.path.join(workdir, "inelast_local.mod")
    with open(os.path.join(tdir, "inelast.mod")) as fh:
        txt = fh.read().replace("/users/knc6/displace.mod", os.path.join(tdir, "displace.mod"))
    with open(mod, "w") as fh:
        fh.write(txt)
    params = {"pair_style": "eam/alloy", "pair_coeff": pot, "atom_style": "charge",
              "control_file": "inelast_local.mod"}
    cwd = os.getcwd()
    os.chdir(workdir)
    try:
        LammpsJob(atoms=ase_to_atoms(bulk("Au", "fcc", a=a0, cubic=True)), parameters=params, copy_files=[mod],
                  lammps_cmd=f"{C.lammps_executable()} < in.main > out", jobname="Au_ELASTIC", attempts=2).runjob()
        r = analyze_log(os.path.join(workdir, "Au_ELASTIC", "log.lammps"))
    finally:
        os.chdir(cwd)
    c11, c12, c44 = r[3], r[6], r[9]   # ordem de analyze_log: en, press, toten, c11, c22, c33, c12, c13, c23, c44…
    return {"C11_GPa": c11, "C12_GPa": c12, "C44_GPa": c44, "B_elastic_GPa": (c11 + 2 * c12) / 3}


def dft_reference(jid="JVASP-825"):
    recs = [r for r in JD.dft3d() if r["jid"] == jid]
    if not recs:
        return {}
    r = recs[0]
    from jarvis.core.atoms import Atoms

    at = Atoms.from_dict(r["atoms"])
    a_conv = (at.volume * 4 / at.num_atoms) ** (1 / 3)   # célula convencional fcc = 4 átomos
    return {"a_A": a_conv, "B_GPa": r.get("bulk_modulus_kv"), "fonte": "reconstrução offline" if r.get(
        "reconstrucao_offline") else "JARVIS-DFT (figshare)"}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--calculators", nargs="+", default=["lammps-eam", "mace-mp"])
    ap.add_argument("--model-path", help="pasta de um ALIGNN-FF treinado (alignn-ff)")
    ap.add_argument("--skip-defects", action="store_true", help="só EOS (rápido)")
    ap.add_argument("--out", default=os.path.join(JD.ROOT, "outputs", "atomistic"))
    a = ap.parse_args(argv)

    import pandas as pd

    os.makedirs(a.out, exist_ok=True)
    work = tempfile.mkdtemp(prefix="jarvis_ff_")
    rows = []
    ref = dft_reference()
    print(f"JARVIS-DFT JVASP-825 (Au fcc, {ref.get('fonte', '—')}): a = {ref.get('a_A', float('nan')):.3f} Å, "
          f"B = {ref.get('B_GPa')} GPa")
    jff = JD.jff_legacy()
    for _, r in jff[jff["composition"] == "Au32"].iterrows():
        print(f"JARVIS-FF (LAMMPS) {r['forcefield']}: E = {r['energy']} eV/átomo, Bv = {r['Bv']} GPa")
    for name in a.calculators:
        t = time.time()
        calc = C.get_calculator(name, model_path=a.model_path, elements={"Au"}, workdir=work)
        a0, e0, b = bulk_eos(calc)
        row = {"calculadora": name, "a_A": a0, "E_bulk_eV_atomo": e0, "B_GPa": b}
        if not a.skip_defects:
            row["gamma_111_J_m2"] = surface_energy(calc, a0, e0, facet="111")
            row["gamma_100_J_m2"] = surface_energy(calc, a0, e0, facet="100")
            row["E_vac_eV"] = vacancy_energy(calc, a0, e0)
        if name == "lammps-eam":
            row.update(jarvis_ff_elastic(os.path.join(work, "jff"), a0))
        row["dA_vs_DFT_%"] = 100 * (a0 / ref["a_A"] - 1) if ref else np.nan
        row["dB_vs_DFT_%"] = 100 * (b / float(ref["B_GPa"]) - 1) if ref and ref.get("B_GPa") not in (None, "na") else np.nan
        row["tempo_s"] = time.time() - t
        rows.append(row)
        print({k: (round(float(v), 3) if isinstance(v, (float, np.floating)) else v) for k, v in row.items()})
    shutil.rmtree(work, ignore_errors=True)
    df = pd.DataFrame(rows)
    path = os.path.join(a.out, f"jarvis_ff_{time.strftime('%Y%m%d-%H%M%S')}.csv")
    df.to_csv(path, index=False)
    print(df.round(3).to_string(index=False))
    print("->", os.path.relpath(path, JD.ROOT))
    return df


if __name__ == "__main__":
    main()
