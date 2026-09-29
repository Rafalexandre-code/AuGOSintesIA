"""Calculadoras ASE para o sistema GO–Au, com uma interface única (usadas por go_au.py, jarvis_ff.py e chipsff_run.py).

| nome          | origem                                  | elementos      | pesos / parâmetros                                   |
|---------------|-----------------------------------------|----------------|------------------------------------------------------|
| alignn-ff     | JARVIS-ML (ALIGNN-FF, external/jarvis)  | toda a tabela  | figshare (baixar com jarvis_data.py download) ou     |
|               |                                         |                | pasta de um modelo treinado aqui (--model-path)      |
| mace-mp       | MACE-MP-0 (Materials Project)           | 89 elementos   | GitHub (ACEsuit/mace-mp), baixa sozinho              |
| mace-mp-d3    | MACE-MP-0 + dispersão D3(BJ)            | 89 elementos   | idem + torch-dftd (adesão Au/grafeno, GO empilhado)  |
| chgnet        | CHGNet                                  | 89 elementos   | dentro do pacote PyPI                                |
| sevennet      | SevenNet-0                              | 89 elementos   | dentro do pacote PyPI                                |
| go-mace-23    | projects/atomistic/GO-MACE-23           | C, H, O        | versionado (sem Au: só para o GO isolado)            |
| lammps-eam    | JARVIS-FF (LAMMPS + EAM de Au)          | Au             | Au_u3.eam do pacote lammps convertido para setfl     |
| emt           | ASE EMT                                 | H C N O Al Ni Cu Pd Ag Pt Au | só para testes rápidos (não quantitativo) |

Os MLFFs universais (ALIGNN-FF, MACE-MP-0, CHGNet, SevenNet) foram treinados em DFT-PBE/optB88 de cristais; energias
de adsorção de Au em GO são estimativas de triagem, a validar com DFT (JARVIS-DFT/QE) nos candidatos finais — o mesmo
fluxo de validação do CHIPS-FF/JARVIS-FF.
"""
from __future__ import annotations

import os
import shutil
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
GO_MACE_MODEL = os.path.join(ROOT, "projects", "atomistic", "GO-MACE-23", "models", "fitting", "potential",
                             "iter-12-final-model", "go-mace-23.pt")
NAMES = ("alignn-ff", "mace-mp", "mace-mp-d3", "chgnet", "sevennet", "go-mace-23", "lammps-eam", "emt")
EMT_ELEMENTS = {"H", "C", "N", "O", "Al", "Ni", "Cu", "Pd", "Ag", "Pt", "Au"}


def lammps_potentials_dir() -> str:
    import lammps

    return os.path.join(os.path.dirname(lammps.__file__), "share", "lammps", "potentials")


def lammps_executable() -> str:
    exe = shutil.which("lmp") or os.path.join(os.path.dirname(sys.executable), "lmp")
    if not os.path.exists(exe):
        raise FileNotFoundError("executável 'lmp' não encontrado (pip install 'lammps[mpi]'; ambiente jarvis)")
    return exe


def funcfl_to_setfl(funcfl: str, out: str, element: str | None = None) -> str:
    """Converte um potencial EAM 'funcfl' (pair_style eam, ex.: Au_u3.eam) para 'setfl' (eam/alloy).

    O JARVIS-FF (jarvis.tasks.lammps) escreve `pair_coeff * * arquivo Elemento`, que só vale para eam/alloy.
    Conversão (manual do LAMMPS, pair_eam): φ(r) = 27,2·0,529·Z(r)²/r, e o setfl guarda r·φ(r) = 27,2·0,529·Z(r)².
    """
    import numpy as np

    with open(funcfl) as fh:
        lines = fh.read().splitlines()
    comment = lines[0].strip()
    znum, mass, alat, lattice = lines[1].split()[:4]
    nrho, drho, nr, dr, cut = lines[2].split()[:5]
    nrho, nr = int(nrho), int(nr)
    vals = np.array(" ".join(lines[3:]).replace("D", "E").split(), dtype=float)
    F, Z, rho = vals[:nrho], vals[nrho:nrho + nr], vals[nrho + nr:nrho + 2 * nr]
    if len(rho) != nr:
        raise ValueError(f"{funcfl}: esperado {nrho + 2 * nr} valores, lidos {len(vals)}")
    el = element or os.path.basename(funcfl).split("_")[0]
    rphi = 27.2 * 0.529 * Z ** 2

    def block(a):
        return "\n".join(" ".join(f"{x:.16e}" for x in a[i:i + 5]) for i in range(0, len(a), 5))

    with open(out, "w") as fh:
        fh.write(f"setfl convertido de {os.path.basename(funcfl)} ({comment})\n"
                 "gerado por code/atomistic/calculators.py (funcfl -> eam/alloy)\n\n")
        fh.write(f"1 {el}\n{nrho} {drho} {nr} {dr} {cut}\n{znum} {mass} {alat} {lattice}\n")
        fh.write(block(F) + "\n" + block(rho) + "\n" + block(rphi) + "\n")
    return out


def au_setfl(workdir: str) -> str:
    os.makedirs(workdir, exist_ok=True)
    return funcfl_to_setfl(os.path.join(lammps_potentials_dir(), "Au_u3.eam"), os.path.join(workdir, "Au_u3.eam.alloy"))


def get_calculator(name: str = "mace-mp", model_path: str | None = None, device: str = "cpu",
                   elements=None, workdir: str | None = None, **kw):
    """Devolve uma calculadora ASE. `elements` (opcional) é checado contra o domínio de cada potencial."""
    els = set(elements or [])
    if name in ("mace-mp", "mace-mp-d3"):
        from mace.calculators import mace_mp

        # PBE não descreve van der Waals: sem D3, Au sobre grafeno quase não se liga
        return mace_mp(model=kw.get("size", "small"), device=device, default_dtype=kw.get("dtype", "float64"),
                       dispersion=name == "mace-mp-d3")
    if name == "alignn-ff":
        from alignn.ff.ff import AlignnAtomwiseCalculator, default_path

        path = model_path or os.environ.get("ALIGNN_FF_MODEL")
        if path is None:
            try:
                path = default_path()   # baixa do figshare na primeira vez (bloqueado no contêiner de nuvem)
            except Exception as err:     # noqa: BLE001 — a mensagem abaixo diz o que fazer
                raise RuntimeError("modelo ALIGNN-FF pré-treinado indisponível (figshare). Rode com rede: python "
                                   "code/atomistic/jarvis_data.py download --alignn-ff v12.2.2024_mp_1.5mill, ou "
                                   "passe --model-path de um ALIGNN-FF treinado (go_au.py train-alignn-ff).") from err
        return AlignnAtomwiseCalculator(path=path, device=device)
    if name == "chgnet":
        from chgnet.model.dynamics import CHGNetCalculator

        return CHGNetCalculator(use_device=device)
    if name == "sevennet":
        from sevenn.calculator import SevenNetCalculator

        return SevenNetCalculator(model=kw.get("model", "7net-0"), device=device)
    if name == "go-mace-23":
        if els - {"C", "H", "O"}:
            raise ValueError(f"GO-MACE-23 só cobre C/H/O (pedido: {sorted(els)}); use mace-mp/alignn-ff para Au")
        from mace.calculators import MACECalculator

        return MACECalculator(model_paths=GO_MACE_MODEL, device=device, default_dtype="float64")
    if name == "lammps-eam":
        if els - {"Au"}:
            raise ValueError("lammps-eam (Au_u3) só cobre Au; para C/H/O use CH.airebo/ffield.reax.* à parte")
        from ase.calculators.lammpsrun import LAMMPS

        pot = au_setfl(os.path.join(workdir or os.path.join(ROOT, "outputs", "atomistic"), "potentials"))
        os.environ.setdefault("ASE_LAMMPSRUN_COMMAND", lammps_executable())
        # caminho absoluto: o ASE não roda o lmp dentro da pasta temporária para onde copia `files`
        return LAMMPS(pair_style="eam/alloy", pair_coeff=[f"* * {pot} Au"], specorder=["Au"], keep_tmp_files=False)
    if name == "emt":
        if els - EMT_ELEMENTS:
            raise ValueError(f"EMT não tem parâmetros para {sorted(els - EMT_ELEMENTS)}")
        from ase.calculators.emt import EMT

        return EMT()
    raise ValueError(f"calculadora desconhecida: {name} (opções: {', '.join(NAMES)})")
