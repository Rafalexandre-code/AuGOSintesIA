#!/usr/bin/env python3
"""Interface Au–GO nas folhas de GO publicadas, com um potencial híbrido (GO-MACE-23 + MACE-MP-0 + D3).

As folhas: El-Machachi et al., Angew. Chem. Int. Ed. 2024, e202410088 — GO depois de 2 ns de dinâmica molecular a
900, 1 200 e 1 500 K com o GO-MACE-23, otimizado (projects/atomistic/GO-MACE-23/structures). Pergunta: onde e com
que força o ouro se prende a cada "lote" de GO?

Potencial (embutimento subtrativo, como no ONIOM):

    E(GO + Au) = E_GO-MACE-23(GO) + E_MP(GO + Au) − E_MP(GO),    E_MP = MACE-MP-0 (small) + D3(BJ)

O GO-MACE-23 (PBE, treinado em GO) descreve as ligações do próprio GO; o MACE-MP-0 (PBE, universal, cobre o Au) entra
só pela diferença, isto é, pelo que muda quando o ouro está presente (Au–O, Au–C, Au–Au e a dispersão D3). Motivo,
medido aqui: na geometria otimizada da folha de 900 K o GO-MACE-23 dá forças de ~0,001 eV/Å e o MACE-MP-0 sozinho,
~0,9 eV/Å (mediana) — usado puro, ele deformaria o próprio GO.

Referências sem o átomo isolado (o E0 de regressão do MACE-MP-0 não é a energia de um átomo livre): μ(Au) = energia
por átomo do ouro maciço no mesmo potencial; energia de sítio = E(GO+Au) − E(GO) − μ(Au) (negativa = o átomo prefere
o sítio ao ouro maciço; quanto mais negativa, mais forte a ancoragem). Adesão da partícula = E(GO+Au_n) − E(GO) −
E(Au_n isolada relaxada), sem μ.

Subcomandos (saídas em outputs/atomistic/au_go_interface; `collect` grava o conjunto versionado):
    refs      μ(Au maciço), a₀ e γ(111) do Au no mesmo potencial
    contact   Au(111)/grafeno: distância e energia de ligação no mesmo potencial (comparar com vdW-DF e STM)
    sites     um átomo de Au em cada tipo de sítio (epóxi, hidroxila, éter, carbonila, carboxila, lactona, C de borda,
              C sp²) e no grafeno intacto; recorte de 13 Å com borda fixa; relaxa o Au e o GO a até 5,5 Å dele
    particle  a nanopartícula da cena 3D (Wulff–Winterbottom, d = 1,5 nm: 119 átomos) relaxada no centro do recorte
              da cena (folhas 900/1200/1500 K) e sobre grafeno; adesão, área de contato, ligações Au–O
    crosscheck  a interação partícula–folha com outro tamanho do MACE-MP-0, na mesma geometria (--mp-size medium)
    collect   junta tudo em datasets/au-go-interface/ (lido por code/webapp/analyses.py → aba Nanocompósito 3D)

Ambiente: jarvis (`tools/setup_env.sh jarvis`: mace-torch + torch-dftd + ase); os pesos do MACE-MP-0 vêm do GitHub
(ACEsuit/mace-mp) na primeira execução; `particle` usa o node para gerar a partícula com code/webapp/nano3d.js.
Custo (CPU, 1 núcleo): ~3 s por avaliação de 300 átomos; rode várias partes em paralelo (--part i/n, --threads 1).

    python code/atomistic/au_go_interface.py refs
    python code/atomistic/au_go_interface.py sites --structure 900K --per-type 3 --part 0/2
    python code/atomistic/au_go_interface.py sites --structure graphene
    python code/atomistic/au_go_interface.py particle --structure 900K
    python code/atomistic/au_go_interface.py collect
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import subprocess
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import go_sites as G  # noqa: E402

ROOT = G.ROOT
OUT = os.path.join(ROOT, "outputs", "atomistic", "au_go_interface")
DATA = os.path.join(ROOT, "datasets", "au-go-interface")
GO_MACE_MODEL = os.path.join(ROOT, "projects", "atomistic", "GO-MACE-23", "models", "fitting", "potential",
                             "iter-12-final-model", "go-mace-23.pt")
NANO3D = os.path.join(ROOT, "code", "webapp", "nano3d.js")
STRUCTURES = ("900K", "1200K", "1500K")
SITE_TYPES = ("O epóxi", "O hidroxila", "O éter", "O carbonila", "O carboxila", "O lactona", "C de borda", "C sp²")
A_CC = 1.42
AU_AREA_111 = 4.078 ** 2 * np.sqrt(3) / 4          # Å² por átomo num plano (111) do ouro
EV_A2_TO_J_M2 = 16.0218


# ------------------------------------------------------------------------------------------------------ potenciais
_CALCS: dict = {}
MP_SIZE = "small"                 # "medium" só na validação (--mp-size medium): ~3× mais lento


def calcs(dtype: str = "float32"):
    """(GO-MACE-23, MACE-MP-0 [MP_SIZE] + D3(BJ)) na precisão pedida, carregados uma vez por processo."""
    if (dtype, MP_SIZE) not in _CALCS:
        from mace.calculators import MACECalculator, mace_mp

        gom = MACECalculator(model_paths=GO_MACE_MODEL, device="cpu", default_dtype=dtype)
        mp = mace_mp(model=MP_SIZE, device="cpu", default_dtype=dtype, dispersion=True)
        _CALCS[dtype, MP_SIZE] = (gom, mp)
    return _CALCS[dtype, MP_SIZE]


def _sfx() -> str:
    return "" if MP_SIZE == "small" else f"_{MP_SIZE}"


def ef(calc, atoms):
    """Energia (eV) e forças (eV/Å) de uma cópia de `atoms` (sem vínculos) com `calc`."""
    a = atoms.copy()
    a.constraints = []
    a.calc = calc
    return float(a.get_potential_energy()), a.get_forces()


def hybrid_calculator(n_go: int, dtype: str = "float32", rigid: bool = False):
    """Calculadora ASE do potencial híbrido; os `n_go` primeiros átomos são o GO, os demais o ouro.
    rigid=True: o GO fica parado e só E_MP(GO+Au) é recalculado (as outras parcelas são constantes)."""
    from ase.calculators.calculator import Calculator, all_changes

    class Hybrid(Calculator):
        implemented_properties = ["energy", "forces"]

        def __init__(self):
            super().__init__()
            self.const = None

        def calculate(self, atoms=None, properties=("energy",), system_changes=all_changes):
            super().calculate(atoms, properties, system_changes)
            gom, mp = calcs(dtype)
            a = self.atoms
            e2, f2 = ef(mp, a)
            if rigid:
                if self.const is None:
                    self.const = ef(gom, a[:n_go])[0] - ef(mp, a[:n_go])[0]
                self.results = {"energy": e2 + self.const, "forces": f2}
                return
            e1, f1 = ef(gom, a[:n_go])
            e3, f3 = ef(mp, a[:n_go])
            f = f2.copy()
            f[:n_go] += f1 - f3
            self.results = {"energy": e1 + e2 - e3, "forces": f}

    return Hybrid()


def element_hybrid_calculator(dtype: str = "float64", go_elements=("C", "H", "O")):
    """O mesmo potencial híbrido, com o GO definido pelos elementos (C, H, O) e não pela ordem dos átomos: serve para
    qualquer sistema GO + metal, periódico ou não (calculators.get_calculator("hybrid") → go_au.py). GO puro = GO-MACE-23;
    metal puro = MACE-MP-0 + D3."""
    from ase.calculators.calculator import Calculator, all_changes

    class ElementHybrid(Calculator):
        implemented_properties = ["energy", "forces"]

        def calculate(self, atoms=None, properties=("energy",), system_changes=all_changes):
            super().calculate(atoms, properties, system_changes)
            gom, mp = calcs(dtype)
            a = self.atoms
            go = np.array([x in go_elements for x in a.get_chemical_symbols()])
            e, f = 0.0, np.zeros((len(a), 3))
            if (~go).any():
                e2, f2 = ef(mp, a)
                e, f = e + e2, f + f2
                if go.any():
                    e3, f3 = ef(mp, a[go])
                    e -= e3
                    f[go] -= f3
            if go.any():
                e1, f1 = ef(gom, a[go])
                e += e1
                f[go] += f1
            self.results = {"energy": e, "forces": f}

    return ElementHybrid()


def hybrid_energy(atoms, n_go: int, dtype: str = "float64") -> dict:
    """Energia híbrida e as três parcelas (eV), numa avaliação pontual."""
    gom, mp = calcs(dtype)
    e1 = ef(gom, atoms[:n_go])[0] if n_go else 0.0
    e2 = ef(mp, atoms)[0]
    e3 = ef(mp, atoms[:n_go])[0] if n_go else 0.0
    return {"E": e1 + e2 - e3, "E_gomace": e1, "E_mp_total": e2, "E_mp_go": e3}


def relax(atoms, free, calc, fmax: float = 0.05, steps: int = 300, opt: str = "LBFGS", logfile: str | None = None) -> dict:
    """Relaxa os átomos de `free` (máscara) com os demais fixos. Devolve passos, convergência e fmax final."""
    from ase.constraints import FixAtoms
    from ase.optimize import BFGS, FIRE, LBFGS

    atoms.constraints = [FixAtoms(mask=~np.asarray(free))]
    atoms.calc = calc
    t0 = time.time()
    o = {"LBFGS": LBFGS, "BFGS": BFGS, "FIRE": FIRE}[opt](atoms, logfile=logfile, maxstep=0.15)
    o.run(fmax=fmax, steps=steps)
    f = atoms.get_forces()
    fm = float(np.sqrt((f ** 2).sum(1)).max())
    return {"steps": int(o.nsteps), "fmax": fm, "converged": fm <= fmax + 1e-9, "seconds": round(time.time() - t0, 1)}


# ------------------------------------------------------------------------------------------------------ geometria
def fib_sphere(n: int = 400) -> np.ndarray:
    k = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * k / n)
    th = np.pi * (1 + 5 ** 0.5) * k
    return np.c_[np.cos(th) * np.sin(phi), np.cos(phi), np.sin(th) * np.sin(phi)]     # y = normal da folha


def carve(p: np.ndarray, box: np.ndarray, cx: float, cz: float, R: float):
    """Átomos a até R Å de (cx, cz) no plano, com x e z desdobrados em torno do centro (recorte sem periodicidade)."""
    dx = (p[:, 0] - cx + box[0] / 2) % box[0] - box[0] / 2
    dz = (p[:, 2] - cz + box[2] / 2) % box[2] - box[2] / 2
    idx = np.where(np.hypot(dx, dz) < R)[0]
    return idx, np.c_[dx[idx], p[idx, 1], dz[idx]]


def graphene_patch(R: float) -> np.ndarray:
    """Grafeno perfeito (C–C 1,42 Å) num disco de raio R no plano xz, y = 0; um átomo no centro."""
    a = A_CC * np.sqrt(3)
    a1, a2 = np.array([a, 0.0]), np.array([a / 2, a * np.sqrt(3) / 2])
    n = int(R / a) + 3
    pts = [i * a1 + j * a2 + b for i in range(-2 * n, 2 * n + 1) for j in range(-2 * n, 2 * n + 1)
           for b in (np.zeros(2), np.array([0.0, A_CC]))]
    pts = np.array([q for q in pts if np.hypot(*q) < R])
    return np.c_[pts[:, 0], np.zeros(len(pts)), pts[:, 1]]


def place_atom(pos: np.ndarray, site: int, r0: float, side: int = 0, n: int = 3, sep_deg: float = 50.0):
    """Posições iniciais do Au a r0 Å do átomo do sítio: as `n` direções mais livres (400 direções; do lado do grupo
    se side ≠ 0), separadas por mais de `sep_deg`. Devolve [(posição, distância ao vizinho mais próximo), ...]."""
    s, others = pos[site], np.delete(pos, site, axis=0)
    dirs = fib_sphere()
    if side:
        dirs = dirs[dirs[:, 1] * side > 0.2]
    q = s + r0 * dirs
    dmin = np.min(np.linalg.norm(others[None, :, :] - q[:, None, :], axis=2), axis=1)
    out: list = []
    for k in np.argsort(-dmin):
        if all(np.degrees(np.arccos(np.clip(dirs[k] @ dirs[j], -1, 1))) > sep_deg for j in out):
            out.append(int(k))
        if len(out) == n:
            break
    return [(q[k], float(dmin[k])) for k in out]


def scene_particle(d: float = 1.5, adh: float = 0.35) -> dict:
    """A mesma nanopartícula da cena 3D (AUGO_N3CORE.buildParticle em code/webapp/nano3d.js), em Å, com o primeiro
    plano de ouro a 3,4 Å do plano da folha (y) e o centro em x = z = 0."""
    js = ("const fs=require('fs'),vm=require('vm');const c={window:{},setTimeout};vm.createContext(c);"
          f"vm.runInContext(fs.readFileSync({json.dumps(NANO3D)},'utf8'),c);"
          f"const p=c.window.AUGO_N3CORE.buildParticle({d},{adh});"
          "console.log(JSON.stringify({P:p.P,foot:p.foot,N:p.N,d:p.d,yau:c.window.AUGO_N3CORE.Y_AU}))")
    r = json.loads(subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout)
    r["P"] = np.array(r["P"], float)
    return r


def contacts(au: np.ndarray, pos: np.ndarray, el: np.ndarray, types: list | None = None) -> list:
    """Pares Au–átomo do GO mais curtos que uma ligação (Au–O 2,6; Au–C 2,6; Au–H 2,2 Å)."""
    lim = {"O": 2.6, "C": 2.6, "H": 2.2}
    out = []
    for k, q in enumerate(au):
        d = np.linalg.norm(pos - q, axis=1)
        for j in np.where(d < 2.7)[0]:
            if d[j] < lim[el[j]]:
                out.append({"au": k, "go": int(j), "el": str(el[j]), "d": round(float(d[j]), 3),
                            **({"type": types[j]} if types is not None else {})})
    return out


def broken_bonds(el: np.ndarray, p0: np.ndarray, p1: np.ndarray, near: np.ndarray) -> list:
    """Ligações do GO (C–O, C–C, O–H, C–H) presentes antes e rompidas depois (> 1,3 × o limite) perto do ouro."""
    from scipy.spatial import cKDTree

    out = []
    for a, b in cKDTree(p0).query_pairs(1.9):
        if not (near[a] or near[b]):
            continue
        lim = G.CUT.get((el[a], el[b]), G.CUT.get((el[b], el[a]), 0))
        if lim and np.linalg.norm(p0[a] - p0[b]) < lim and np.linalg.norm(p1[a] - p1[b]) > 1.3 * lim:
            out.append({"a": int(a), "b": int(b), "pair": f"{el[a]}–{el[b]}", "d0": round(float(np.linalg.norm(p0[a] - p0[b])), 3),
                        "d1": round(float(np.linalg.norm(p1[a] - p1[b])), 3)})
    return out


# ------------------------------------------------------------------------------------------------------ equilíbrio
def force_map(T: str, R: float = 19.0, keep: float = 11.0) -> np.ndarray:
    """|F| de cada átomo da folha publicada `T` no GO-MACE-23, em ladrilhos (recortes de R Å; vale só para os átomos a
    menos de `keep` Å do centro, cujo ambiente de 7,4 Å está inteiro no recorte). Em cache em outputs/. As folhas
    "otimizadas" têm regiões fora do equilíbrio neste potencial (até ~16 eV/Å na de 1 500 K) — sítios perto delas saem
    do sorteio, senão uma relaxação do próprio GO seria contada como adsorção."""
    f = os.path.join(OUT, f"forces_{T}.npy")
    fn = np.load(f) if os.path.exists(f) else None
    if fn is not None and np.isfinite(fn).all():
        return fn
    from ase import Atoms

    el, pos, box = G.structure(T)
    p = G.classify(el, pos, box)[2]
    calc = calcs("float32")[0]

    def tile(cx, cz):
        idx, loc = carve(p, box, cx, cz, R)
        ff = np.linalg.norm(ef(calc, Atoms(symbols=list(el[idx]), positions=loc, pbc=False))[1], axis=1)
        return idx, np.hypot(loc[:, 0], loc[:, 2]), ff

    if fn is None:
        fn, best = np.full(len(el), np.nan), np.full(len(el), np.inf)
        step = keep * np.sqrt(3)                   # discos de raio `keep` cobrem o plano numa grade hexagonal
        for j, cz in enumerate(np.arange(0, box[2], step * np.sqrt(3) / 2)):
            for cx in np.arange((j % 2) * step / 2, box[0], step):
                idx, r, ff = tile(cx, cz)
                m = (r < keep) & (r < best[idx])
                fn[idx[m]], best[idx[m]] = ff[m], r[m]
    while np.isnan(fn).any():                      # a grade não fecha na costura periódica: ladrilhos nos que faltam
        k = int(np.where(np.isnan(fn))[0][0])
        idx, r, ff = tile(p[k, 0], p[k, 2])
        m = (r < keep) & np.isnan(fn[idx])
        fn[idx[m]] = ff[m]
    os.makedirs(OUT, exist_ok=True)
    np.save(f, fn)
    return fn


def near_bad(p: np.ndarray, box: np.ndarray, fn: np.ndarray, fbad: float = 1.0, dist: float = 8.0) -> np.ndarray:
    """Átomos a menos de `dist` Å (periódico em x e z) de algum átomo com |F| > fbad eV/Å."""
    from scipy.spatial import cKDTree

    q = np.c_[p[:, 0], p[:, 1] - p[:, 1].min(), p[:, 2]]
    bad = np.where(np.nan_to_num(fn, nan=0.0) > fbad)[0]
    out = np.zeros(len(p), bool)
    if len(bad):
        for nbrs in cKDTree(q, boxsize=[box[0], 1e6, box[2]]).query_ball_point(q[bad], dist):
            out[nbrs] = True
    return out


# ------------------------------------------------------------------------------------------------------ refs
def cmd_refs(a) -> None:
    """μ(Au) e a₀ (EOS do fcc), γ(111) (placa de 8 camadas, 2 de cada lado relaxadas) no MACE-MP-0 small + D3."""
    from ase.build import bulk, fcc111
    from ase.eos import EquationOfState

    _, mp = calcs("float64")
    vols, ens = [], []
    for a0 in np.linspace(3.95, 4.20, 11):
        b = bulk("Au", "fcc", a=a0, cubic=True)
        e, _ = ef(mp, b)
        vols.append(b.get_volume() / len(b))
        ens.append(e / len(b))
    v0, e0, B = EquationOfState(vols, ens).fit()
    a0 = (4 * v0) ** (1 / 3)
    s = fcc111("Au", size=(3, 3, 8), a=a0, vacuum=12.0, periodic=True)
    e_unrel, _ = ef(mp, s)
    area = np.linalg.norm(np.cross(s.cell[0], s.cell[1]))
    z = s.positions[:, 2]
    zs = np.sort(np.unique(np.round(z, 2)))
    free = (z <= zs[1] + 0.1) | (z >= zs[-2] - 0.1)
    info = relax(s, free, mp, fmax=0.02, steps=200, opt="BFGS")
    e_rel, _ = ef(mp, s)
    from ase import Atoms

    e_free = ef(mp, Atoms("Au", positions=[[0.0, 0.0, 0.0]], pbc=False))[0]   # E0 de regressão: não é um átomo livre real
    out = {"model": f"MACE-MP-0 {MP_SIZE} + D3(BJ), float64", "mu_Au_eV": e0, "a0_A": a0,
           "E_free_atom_model_eV": e_free - e0,
           "B_GPa": B / 1e9 * 1.602176634e-19 / 1e-30, "gamma111_J_m2": (e_rel - len(s) * e0) / (2 * area) * EV_A2_TO_J_M2,
           "gamma111_unrelaxed_J_m2": (e_unrel - len(s) * e0) / (2 * area) * EV_A2_TO_J_M2, "slab_relax": info}
    os.makedirs(OUT, exist_ok=True)
    json.dump(out, open(os.path.join(OUT, f"refs{_sfx()}.json"), "w"), indent=1)
    print(json.dumps(out, indent=1))


def mu_au() -> float:
    f = os.path.join(OUT, f"refs{_sfx()}.json")
    if not os.path.exists(f):
        raise SystemExit("rode antes: au_go_interface.py refs")
    return float(json.load(open(f))["mu_Au_eV"])


def _parabola_min(x, y, k: int):
    """Mínimo da parábola pelos 3 pontos em torno do índice k (x igualmente espaçado); nas pontas, o próprio ponto."""
    if 0 < k < len(x) - 1:
        den = y[k - 1] - 2 * y[k] + y[k + 1]
        if den > 0:
            t = 0.5 * (y[k - 1] - y[k + 1]) / den
            return float(x[k] + t * (x[1] - x[0])), float(y[k] - 0.25 * (y[k - 1] - y[k + 1]) * t)
    return float(x[k]), float(y[k])


def au_graphene_slab(L: float = 4.92, a0: float = 4.111, n_layers: int = 4):
    """Grafeno 2×2 (8 C) e Au(111) √3×√3R30° (3 Au por camada, empilhamento ABC, camadas a a₀/√3) na mesma célula
    hexagonal de lado L: o ouro fica comprimido no plano para casar as redes (2,3 % com o a₀ do modelo; as duas partes
    ficam rígidas, e a deformação se cancela na energia de ligação). Devolve (célula, posições do Au, posições do C)."""
    A = np.array([[L, 0, 0], [L / 2, L * np.sqrt(3) / 2, 0]])
    a1, a2 = A / 2
    c = np.array([i * a1 + j * a2 + b for i in range(2) for j in range(2) for b in (np.zeros(3), (a1 + a2) / 3)])
    stack = np.array([[0, 0], [0, 1 / 3], [0, 2 / 3]])
    au = np.array([np.r_[((f + stack[k % 3]) % 1) @ A[:, :2], 5.0 + k * a0 / np.sqrt(3)]
                   for k in range(n_layers) for f in np.array([[0, 0], [1 / 3, 1 / 3], [2 / 3, 2 / 3]])])
    return np.r_[A, [[0, 0, 45.0]]], au, c


def cmd_contact(a) -> None:
    """Au(111)/grafeno no mesmo potencial (as duas partes rígidas): distância de equilíbrio e energia de ligação por C,
    com e sem D3. Para comparar: o vdW-DF dá ligação fraca a 3,40–3,72 Å nos oito metais estudados, inclusive o Au
    (Vanin et al., Phys. Rev. B 81, 081408, 2010), e o STM limita a atração grafeno–Au a menos de 13 meV por C (Nie et
    al., Phys. Rev. B 85, 205406, 2012). Grava em refs[_medium].json → au_graphene."""
    from ase import Atoms
    from mace.calculators import mace_mp

    f = os.path.join(OUT, f"refs{_sfx()}.json")
    if not os.path.exists(f):
        raise SystemExit(f"rode antes: au_go_interface.py refs{' --mp-size ' + MP_SIZE if MP_SIZE != 'small' else ''}")
    refs = json.load(open(f))
    cell, au, c = au_graphene_slab(a0=refs["a0_A"])
    calc = {"d3": calcs("float64")[1], "mace": mace_mp(model=MP_SIZE, device="cpu", default_dtype="float64", dispersion=False)}

    def e(pos, sym, k):
        return ef(calc[k], Atoms(symbols=sym, positions=pos, cell=cell, pbc=True))[0]

    e_au = {k: e(au, ["Au"] * len(au), k) for k in calc}
    ztop, ds = au[:, 2].max(), np.round(np.arange(2.2, 5.01, 0.1), 2)
    curve = np.full((len(ds), 2), np.inf)
    for shift in (np.zeros(3), (cell[0] + cell[1]) / 6):            # C sobre Au e C sobre buraco: fica o menor
        e_c = {k: e(c + shift + [0, 0, ztop + 15], ["C"] * len(c), k) for k in calc}
        for i, d in enumerate(ds):
            pos = np.r_[au, c + shift + [0, 0, ztop + d]]
            eb = [(e(pos, ["Au"] * len(au) + ["C"] * len(c), k) - e_au[k] - e_c[k]) / len(c) * 1000 for k in calc]
            if eb[0] < curve[i, 0]:
                curve[i] = eb
    k = int(np.argmin(curve[:, 0]))
    d_eq, e_b = _parabola_min(ds, curve[:, 0], k)
    j = int(np.argmin(curve[:, 1]))
    refs["au_graphene"] = {"d_eq_A": round(d_eq, 3), "E_b_meV_per_C": round(e_b, 1),
                           "E_b_D3_meV_per_C": round(float(curve[k, 0] - curve[k, 1]), 1),
                           "mace_only_min": [float(ds[j]), round(float(curve[j, 1]), 1)],
                           "curve": [[float(d), round(float(x), 2), round(float(y), 2)] for d, (x, y) in zip(ds, curve)],
                           "setup": "grafeno 2×2 / Au(111) √3×√3R30°, 4 camadas, rígidos; curva: [d (Å), E_b com D3, sem D3] meV/C",
                           "reference": "vdW-DF 3,40–3,72 Å (Vanin et al. 2010); STM < 13 meV/C (Nie et al. 2012)"}
    json.dump(refs, open(f + ".tmp", "w"), indent=1)
    os.replace(f + ".tmp", f)                          # outros processos (sites) leem este arquivo
    print(f"Au(111)/grafeno, MACE-MP-0 {MP_SIZE} + D3: d = {d_eq:.2f} Å, E_b = {e_b:.1f} meV/C "
          f"(D3 {refs['au_graphene']['E_b_D3_meV_per_C']:.1f}; sem D3, mínimo {curve[j, 1]:.1f} meV/C a {ds[j]:.1f} Å)")


def cmd_crosscheck(a) -> None:
    """A adesão da partícula depende do modelo? Com o GO e a partícula parados na geometria relaxada, varre a altura da
    partícula (−0,4 a +1,6 Å) e calcula a interação E_MP(GO+Au) − E_MP(GO) − E_MP(Au) no MACE-MP-0 [--mp-size] + D3 (a
    parcela do GO-MACE-23 se cancela; sem a deformação da folha e da partícula, que entra na adesão relaxada). Grava em
    particle_T.json → interaction[tamanho]; `particle --resume` apaga (a geometria muda)."""
    import torch
    from ase import Atoms

    torch.set_num_threads(a.threads)
    _, mp = calcs("float64")
    hs = np.round(np.arange(-0.4, 1.61, 0.2), 2)
    for f in sorted(glob.glob(os.path.join(OUT, f"particle_{a.pattern}.json"))):
        r = json.load(open(f))
        go = Atoms(symbols=r["go_el"], positions=r["go_pos"], pbc=False)
        au = np.array(r["au_pos"])
        gold = lambda h: Atoms(symbols=["Au"] * len(au), positions=au + [0, h, 0], pbc=False)   # noqa: E731
        e_go, e_au = ef(mp, go)[0], ef(mp, gold(0.0))[0]
        E = np.array([ef(mp, go + gold(h))[0] - e_go - e_au for h in hs])
        h_min, e_min = _parabola_min(hs, E, int(np.argmin(E)))
        r.setdefault("interaction", {})[MP_SIZE] = {"h_A": hs.tolist(), "E_eV": np.round(E, 4).tolist(), "h_min_A": round(h_min, 3),
                                                    "E_min_eV": round(e_min, 4), "E_at_relaxed_eV": round(float(E[hs == 0][0]), 4)}
        json.dump(r, open(f, "w"))
        print(f"{r['structure']}: interação no {MP_SIZE} = {E[hs == 0][0]:+.3f} eV na geometria relaxada; mínimo "
              f"{e_min:+.3f} eV a {h_min:+.2f} Å (adesão relaxada no small: {r['E_adh_eV']:+.3f} eV)", flush=True)


# ------------------------------------------------------------------------------------------------------ sites
def pick_sites(el, p, box, t, side, nb, per_type: int, seed: int, avoid=None) -> list:
    """Até `per_type` átomos de cada tipo de SITE_TYPES, sorteados e a mais de 12 Å uns dos outros. "C sp²" = os C sp²
    mais distantes de qualquer O (domínios de grafeno); "C de borda" = de preferência C com só 2 vizinhos C e nada
    ligado (ligação pendente na borda de um buraco)."""
    from scipy.spatial import cKDTree

    rng = np.random.default_rng(seed)
    q = np.c_[p[:, 0], p[:, 1] - p[:, 1].min(), p[:, 2]]

    def dist(i, j):                                   # distância com periodicidade em x e z
        d = q[i] - q[j]
        d[0] -= box[0] * np.round(d[0] / box[0])
        d[2] -= box[2] * np.round(d[2] / box[2])
        return float(np.linalg.norm(d))

    out = []
    for name in SITE_TYPES:
        cand = np.where(t == G.GO_TYPES.index(name))[0]
        if name == "C de borda":
            dang = np.array([i for i in cand if len(nb[i]) == 2 and all(el[j] == "C" for j in nb[i])], int)
            cand = dang if len(dang) >= per_type else cand
        if name == "C sp²" and len(cand):
            dO, _ = cKDTree(q[el == "O"], boxsize=[box[0], 1e6, box[2]]).query(q[cand])
            cand = cand[np.argsort(-dO)[:max(4 * per_type, 12)]]
        chosen: list[int] = []
        for i in rng.permutation(cand):
            if avoid is not None and avoid[i]:            # região fora do equilíbrio: pula (o próximo sorteado entra)
                continue
            if all(dist(i, j) > 12 for j in chosen):
                chosen.append(int(i))
            if len(chosen) == per_type:
                break
        out += [{"type": name, "atom": i, "side": int(side[i])} for i in chosen]
    return out


def prerelax_go(go, free, fmax: float = 0.03, steps: int = 300):
    """Relaxa só o GO (GO-MACE-23) nos átomos `free`; devolve (cópia relaxada, resumo, energia em float64)."""
    g = go.copy()
    rp = relax(g, np.asarray(free), calcs("float32")[0], fmax=fmax, steps=steps, opt="BFGS")
    return g, rp, ef(calcs("float64")[0], g)[0]


def run_site(el_all, p_all, box, types_all, site: dict, R: float = 13.0, r_free: float = 5.5, mu: float = 0.0,
             label: str = "") -> dict:
    """Um átomo de Au num sítio: recorte, posição inicial, relaxação rígida (só o Au) e híbrida (Au + GO a até
    r_free Å), energias em float64."""
    from ase import Atoms

    i0 = site["atom"]
    if box is None:                                   # grafeno: recorte já centrado
        idx, pos = np.arange(len(el_all)), p_all.copy()
    else:
        idx, pos = carve(p_all, box, p_all[i0, 0], p_all[i0, 2], R)
    el = el_all[idx]
    s = int(np.where(idx == i0)[0][0])
    is_C = el[s] == "C"
    side = site.get("side", 0) if not is_C else (1 if site["type"] == "C sp²" else 0)
    go = Atoms(symbols=list(el), positions=pos, pbc=False)
    n = len(go)
    e_go = ef(calcs("float64")[0], go)[0]                                # GO puro: só o GO-MACE-23 (já otimizado)
    # GO parado: o Au parte de 3 direções livres a ~2,2 Å do sítio; fica a de menor energia
    free = np.r_[np.zeros(n, bool), True]
    calc_rig = hybrid_calculator(n, "float32", rigid=True)
    starts = []
    for au0, dmin in place_atom(pos, s, 2.2 if is_C else 2.15, side):
        trial = go + Atoms("Au", positions=[au0])
        rr = relax(trial, free, calc_rig, fmax=0.05, steps=150, opt="BFGS")
        starts.append((float(trial.get_potential_energy()), trial, rr, dmin, au0))
    starts.sort(key=lambda x: x[0])
    _, sys_, r1, dmin, au0 = starts[0]
    e_rig = hybrid_energy(sys_, n)["E"]
    p_rig = sys_.positions.copy()
    near0 = (np.linalg.norm(pos - p_rig[n], axis=1) < r_free) | (np.linalg.norm(pos - pos[s], axis=1) < r_free)
    # referência: o GO SEM ouro relaxado com os mesmos átomos livres (a estrutura publicada pode não estar num mínimo
    # local do recorte; sem isso, uma relaxação do próprio GO seria contada como adsorção); o Au parte desse GO
    go_rel, rp, e_go_rel = prerelax_go(go, near0)
    sys_.positions[:n] = go_rel.positions
    free = np.r_[near0, True]
    r2 = relax(sys_, free, hybrid_calculator(n, "float32"), fmax=0.05, steps=250, opt="BFGS")
    en = hybrid_energy(sys_, n)
    p1 = sys_.positions
    tl = [G.GO_TYPES[k] for k in types_all[idx]] if types_all is not None else ["C sp²"] * n
    cts = contacts(p1[n:], p1[:n], el, tl)
    res = {"label": label, **site, "n_atoms": n + 1, "n_free_go": int(near0.sum()), "start_dmin_A": round(dmin, 3),
           "starts_E_rigid_f32_eV": [round(x[0] - starts[0][0], 4) for x in starts], "au_start": au0.tolist(),
           "E_go_eV": e_go, "E_go_relaxed_eV": e_go_rel, "go_prerelax_eV": e_go_rel - e_go, "go_prerelax": rp,
           "E_rigid_eV": e_rig, "E_eV": en["E"], "parts": en,
           "E_site_eV": en["E"] - e_go_rel - mu, "E_site_rigid_eV": e_rig - e_go - mu,
           "relax_rigid": r1, "relax": r2, "contacts": cts,
           "broken": broken_bonds(el, pos, p1[:n], near0),
           "site_shift_A": float(np.linalg.norm(p1[s] - pos[s])), "au_rigid": p_rig[n].tolist(), "au": p1[n].tolist(),
           "au_height_A": float(p1[n, 1] - np.median(pos[np.linalg.norm(pos[:, [0, 2]] - p1[n, [0, 2]], axis=1) < 6, 1]))}
    return res


def cmd_sites(a) -> None:
    import torch

    torch.set_num_threads(a.threads)
    mu = mu_au()
    os.makedirs(OUT, exist_ok=True)
    part, nparts = (int(x) for x in a.part.split("/"))
    out = os.path.join(OUT, f"sites_{a.structure}_{part}of{nparts}{_sfx()}.jsonl")
    done = {json.loads(line)["label"] for f in glob.glob(os.path.join(OUT, f"sites_{a.structure}_*of*.jsonl"))
            if f.endswith(f"{_sfx()}.jsonl") and (_sfx() or not f.endswith("_medium.jsonl")) for line in open(f)}
    if a.structure == "graphene":
        pos = graphene_patch(a.radius)
        el = np.array(["C"] * len(pos))
        sites = [{"type": "grafeno intacto", "atom": int(np.argmin(np.hypot(pos[:, 0], pos[:, 2]))), "side": 1}]
        jobs = [(f"graphene-{k}", s) for k, s in enumerate(sites)]
        box, types = None, None
    else:
        el, pos, box = G.structure(a.structure)
        t, side, p, nb = G.classify_nb(el, pos, box)
        pos, types = p, t
        avoid = near_bad(p, box, force_map(a.structure)) if a.equilibrium else None
        sites = pick_sites(el, p, box, t, side, nb, a.per_type, seed={"900K": 9, "1200K": 12, "1500K": 15}[a.structure], avoid=avoid)
        jobs = [(f"{a.structure}-{s['type']}-{s['atom']}", s) for s in sites]
    if a.atoms:                                      # validação: só estes átomos da lista sorteada
        keep = {int(x) for x in a.atoms.split(",")}
        jobs = [j for j in jobs if j[1]["atom"] in keep]
    jobs = [j for k, j in enumerate(jobs) if k % nparts == part and j[0] not in done]
    print(f"{len(jobs)} sítios nesta parte ({len(done)} já feitos)", flush=True)
    for label, s in jobs:
        t0 = time.time()
        r = run_site(el, pos, box, types, s, R=a.radius, mu=mu, label=label)
        r["structure"] = a.structure
        r["seconds"] = round(time.time() - t0, 1)
        with open(out, "a") as fh:
            fh.write(json.dumps(r) + "\n")
        print(f"{label}: E_sítio = {r['E_site_eV']:+.3f} eV (rígido {r['E_site_rigid_eV']:+.3f}), "
              f"{len(r['contacts'])} contatos, {len(r['broken'])} ligações rompidas, {r['seconds']:.0f} s", flush=True)


# ------------------------------------------------------------------------------------------------------ particle
def resume_particle(a) -> None:
    """Continua uma partícula que parou no limite de passos (relax.converged = False): parte da geometria salva, relaxa
    com --opt (FIRE por padrão: estável com modos duros, como C=O, misturados aos moles, como a partícula deslizando; o
    LBFGS chegou a travar aí com 2 eV/Å; BFGS, com a hessiana inteira, é a alternativa) e reavalia as energias."""
    from ase import Atoms

    f = os.path.join(OUT, f"particle_{a.structure}.json")
    r = json.load(open(f))
    if r["relax"]["converged"]:
        print(f"{a.structure}: já convergida (fmax {r['relax']['fmax']:.3f})")
        return
    el, n = r["go_el"], len(r["go_el"])
    sys_ = Atoms(symbols=el + ["Au"] * r["N_Au"], positions=np.r_[np.array(r["go_pos"]), np.array(r["au_pos"])], pbc=False)
    g0 = np.array(r["go_pos0"])
    free = np.r_[np.hypot(g0[:, 0], g0[:, 2]) < r["foot_A"] + a.free_margin, np.ones(r["N_Au"], bool)]
    olog = os.path.join(OUT, "logs", f"particle_{a.structure}_otimizador.log")
    r2 = relax(sys_, free, hybrid_calculator(n, "float32"), fmax=a.fmax, steps=a.steps, opt=a.opt, logfile=olog)
    print(f"  continuação ({a.opt}): {r2}", flush=True)
    en = hybrid_energy(sys_, n)
    p1 = sys_.positions
    e_go = r.get("E_go_relaxed_eV", r["E_go_eV"])
    e_adh = en["E"] - e_go - r["E_Au_iso_eV"]
    au = p1[n:]
    near = np.min(np.linalg.norm(g0[:, None, :] - au[None, :, :], axis=2), axis=1) < 6.0
    r.pop("interaction", None)                         # a conferência com outro modelo era da geometria antiga
    r.update({"E_eV": en["E"], "parts": en, "E_adh_eV": e_adh, "W_adh_J_m2": float(-e_adh / r["contact_area_A2"] * EV_A2_TO_J_M2),
              "contacts": contacts(au, p1[:n], np.array(el), r["go_types"]), "broken": broken_bonds(np.array(el), g0, p1[:n], near),
              "relax_first": r["relax"], "relax": {**r2, "steps": r["relax"]["steps"] + r2["steps"]},
              "go_pos": np.round(p1[:n], 4).tolist(), "au_pos": np.round(au, 4).tolist(),
              "net_force_Au_eV_A": np.round(ef(calcs("float64")[1], sys_)[1][n:].sum(0), 4).tolist()})
    json.dump(r, open(f, "w"))
    print(f"  E_adh = {e_adh:+.3f} eV · {len(r['contacts'])} contatos", flush=True)


def cmd_particle(a) -> None:
    import torch
    from ase import Atoms

    torch.set_num_threads(a.threads)
    if a.resume:
        resume_particle(a)
        return
    os.makedirs(OUT, exist_ok=True)
    part = scene_particle(a.d, a.adh)
    P = part["P"].copy()
    foot = float(part["foot"])
    if a.structure == "graphene":
        pos = graphene_patch(a.radius)
        el = np.array(["C"] * len(pos))
        idx, types, y0, info = np.arange(len(pos)), ["C sp²"] * len(pos), 0.0, {}
    else:
        el_all, pos_all, box = G.structure(a.structure)
        t, side, p = G.classify(el_all, pos_all, box)
        cx, cz, _, _, _, y0, sd = G.flattest_crop(el_all, p, box)
        idx, pos = carve(p, box, cx, cz, a.radius)
        el = el_all[idx]
        types = [G.GO_TYPES[k] for k in t[idx]]
        pos[:, 1] -= y0                                  # mesmo referencial do recorte da cena (y0 = mediana dos C)
        info = {"crop_center_A": [cx, cz], "y0_A": y0, "crop_sd_A": sd}
    # mesma regra da cena (nano3d.js, buildAtomic): a partícula pousa nos átomos mais altos sob ela
    off = {"C": 3.25, "O": 2.15, "H": 2.0}
    under = np.hypot(pos[:, 0], pos[:, 2]) < foot + 1
    top = max(pos[k, 1] + off[el[k]] for k in np.where(under)[0])
    P[:, 1] += top - part["yau"]
    go = Atoms(symbols=list(el), positions=pos, pbc=False)
    n = len(go)
    sys_ = go + Atoms(symbols=["Au"] * len(P), positions=P)
    tag = a.structure
    print(f"{tag}: {n} átomos de GO + {len(P)} Au (pegada {foot:.1f} Å)", flush=True)
    # partícula isolada (referência da adesão)
    iso = Atoms(symbols=["Au"] * len(P), positions=P, pbc=False)
    _, mp32 = calcs("float32")
    r_iso = relax(iso, np.ones(len(P), bool), mp32, fmax=0.03, steps=600)
    e_iso = hybrid_energy(iso, 0)["E"]
    e_go = ef(calcs("float64")[0], go)[0]
    print(f"  Au isolada: {r_iso}", flush=True)
    free_go = np.hypot(pos[:, 0], pos[:, 2]) < foot + a.free_margin
    # a regra da cena (topo + folga) deixa a partícula alta onde o átomo mais alto não fica sob um átomo de ouro, e a
    # atração de van der Waals, espalhada por 119 átomos (~0,02 eV/Å cada), não dispara o critério de força por átomo:
    # varre a altura do corpo rígido (GO e partícula parados) e começa do mínimo de energia
    calc_rig = hybrid_calculator(n, "float32", rigid=True)
    scan = []
    for dh in np.arange(0.0, -5.01, -0.25):
        t = sys_.copy()
        t.positions[n:, 1] += dh
        dmin = float(np.min(np.linalg.norm(t.positions[n:, None, :] - pos[None, :, :], axis=2)))
        if dmin < 1.9:
            break
        t.calc = calc_rig
        scan.append((round(float(dh), 2), float(t.get_potential_energy()), round(dmin, 3)))
    drop = min(scan, key=lambda x: x[1])[0]
    sys_.positions[n:, 1] += drop
    print(f"  varredura de altura: desce {-drop:.2f} Å (ΔE = {min(x[1] for x in scan) - scan[0][1]:+.3f} eV)", flush=True)
    olog = os.path.join(OUT, "logs", f"particle_{tag}_otimizador.log")             # passo a passo (acompanhar)
    os.makedirs(os.path.dirname(olog), exist_ok=True)
    r1 = relax(sys_, np.r_[np.zeros(n, bool), np.ones(len(P), bool)], calc_rig, fmax=a.fmax, steps=a.steps, logfile=olog)
    e_rig = hybrid_energy(sys_, n)["E"]
    p_rig = sys_.positions[n:].copy()
    print(f"  rígido: {r1}, E_adh = {e_rig - e_go - e_iso:+.3f} eV", flush=True)
    go_rel, rp, e_go_rel = prerelax_go(go, free_go)          # referência: o GO sem ouro relaxado nos mesmos átomos livres
    print(f"  GO sem ouro relaxado: {rp}, ΔE = {e_go_rel - e_go:+.3f} eV", flush=True)
    sys_.positions[:n] = go_rel.positions
    r2 = relax(sys_, np.r_[free_go, np.ones(len(P), bool)], hybrid_calculator(n, "float32"), fmax=a.fmax, steps=a.steps,
               logfile=olog)
    en = hybrid_energy(sys_, n)
    p1 = sys_.positions
    f_au = ef(calcs("float64")[1], sys_)[1][n:]                      # força líquida no ouro (só a parcela com Au)
    print(f"  híbrido: {r2}, E_adh = {en['E'] - e_go_rel - e_iso:+.3f} eV", flush=True)
    au = p1[n:]
    base = au[:, 1] < au[:, 1].min() + 1.2                        # primeiro plano de ouro (contato)
    e_adh = en["E"] - e_go_rel - e_iso
    area = base.sum() * AU_AREA_111
    near = np.min(np.linalg.norm(pos[:, None, :] - au[None, :, :], axis=2), axis=1) < 6.0
    res = {"structure": a.structure, "d_nm": part["d"], "d_input": a.d, "adh_input": a.adh, "N_Au": int(len(P)), "foot_A": foot, "n_go": n,
           "n_free_go": int(free_go.sum()), "radius_A": a.radius, **info,
           "E_go_eV": e_go, "E_go_relaxed_eV": e_go_rel, "go_prerelax_eV": e_go_rel - e_go, "go_prerelax": rp,
           "E_Au_iso_eV": e_iso, "E_eV": en["E"], "parts": en, "E_rigid_eV": e_rig,
           "E_adh_eV": e_adh, "E_adh_rigid_eV": e_rig - e_go - e_iso, "n_interface_Au": int(base.sum()),
           "contact_area_A2": float(area), "W_adh_J_m2": float(-e_adh / area * EV_A2_TO_J_M2),
           "contacts": contacts(au, p1[:n], el, types), "broken": broken_bonds(el, pos, p1[:n], near),
           "relax_iso": r_iso, "relax_rigid": r1, "relax": r2, "height_scan": scan, "drop_A": float(drop),
           "net_force_Au_eV_A": np.round(f_au.sum(0), 4).tolist(),
           "go_index": idx.tolist(), "go_el": el.tolist(), "go_types": types,
           "go_pos0": np.round(pos, 4).tolist(), "go_pos": np.round(p1[:n], 4).tolist(),
           "au_pos0": np.round(P, 4).tolist(), "au_pos_rigid": np.round(p_rig, 4).tolist(), "au_pos": np.round(au, 4).tolist()}
    json.dump(res, open(os.path.join(OUT, f"particle_{tag}.json"), "w"))
    print(f"  W_adh = {res['W_adh_J_m2']:.3f} J/m² · {len(res['contacts'])} contatos · {len(res['broken'])} ligações rompidas",
          flush=True)


# ------------------------------------------------------------------------------------------------------ recheck
def cmd_recheck(a) -> None:
    """Resultados de antes da pré-relaxação do GO: refaz só a relaxação do GO sem ouro (mesmos átomos livres). Se a
    energia do GO muda menos que --tol, o resultado vale como está (anota go_prerelax_eV); senão, apaga a linha (sítio)
    ou renomeia o arquivo (partícula) para ser recalculado com o protocolo novo."""
    import torch
    from ase import Atoms

    torch.set_num_threads(a.threads)
    cache = {}
    for f in sorted(glob.glob(os.path.join(OUT, f"sites_{a.pattern}.jsonl"))):      # só arquivos que nenhum processo escreve
        rows, keep = [json.loads(line) for line in open(f)], []
        for r in rows:
            if "go_prerelax_eV" in r:
                keep.append(r)
                continue
            T = r["structure"]
            if T == "graphene":
                pos = graphene_patch(13.0)
                el, idx = np.array(["C"] * len(pos)), np.arange(len(pos))
            else:
                if T not in cache:
                    el_all, pos_all, box = G.structure(T)
                    cache[T] = (el_all, G.classify(el_all, pos_all, box)[2], box)
                el_all, p_all, box = cache[T]
                idx, pos = carve(p_all, box, p_all[r["atom"], 0], p_all[r["atom"], 2], 13.0)
                el = el_all[idx]
            s = int(np.where(idx == r["atom"])[0][0])
            near0 = (np.linalg.norm(pos - np.array(r["au_rigid"]), axis=1) < 5.5) | (np.linalg.norm(pos - pos[s], axis=1) < 5.5)
            _, rp, e_rel = prerelax_go(Atoms(symbols=list(el), positions=pos, pbc=False), near0)
            d = e_rel - r["E_go_eV"]
            if abs(d) <= a.tol:
                r.update({"go_prerelax_eV": d, "go_prerelax": rp, "E_go_relaxed_eV": e_rel})
                keep.append(r)
            print(f"{r['label']}: GO sem ouro relaxado ΔE = {d:+.4f} eV → {'mantém' if abs(d) <= a.tol else 'REFAZER'}", flush=True)
        with open(f, "w") as fh:
            fh.writelines(json.dumps(r) + "\n" for r in keep)
    for f in sorted(glob.glob(os.path.join(OUT, f"particle_{a.pattern}.json"))):
        r = json.load(open(f))
        if "go_prerelax_eV" in r:
            continue
        g0 = np.array(r["go_pos0"])
        free = np.hypot(g0[:, 0], g0[:, 2]) < r["foot_A"] + 6.0
        _, rp, e_rel = prerelax_go(Atoms(symbols=r["go_el"], positions=g0, pbc=False), free)
        d = e_rel - r["E_go_eV"]
        print(f"{os.path.basename(f)}: GO sem ouro relaxado ΔE = {d:+.4f} eV → {'mantém' if abs(d) <= a.tol else 'REFAZER'}", flush=True)
        if abs(d) <= a.tol:
            r.update({"go_prerelax_eV": d, "go_prerelax": rp, "E_go_relaxed_eV": e_rel})
            json.dump(r, open(f, "w"))
        else:
            os.replace(f, f + ".refazer")


def selection(T: str, per_type: int = 3, equilibrium: bool = True) -> list:
    """Os sítios sorteados de uma folha (o mesmo sorteio de `sites`), como rótulos."""
    el, pos, box = G.structure(T)
    t, side, p, nb = G.classify_nb(el, pos, box)
    avoid = near_bad(p, box, force_map(T)) if equilibrium else None
    s = pick_sites(el, p, box, t, side, nb, per_type, seed={"900K": 9, "1200K": 12, "1500K": 15}[T], avoid=avoid)
    return [f"{T}-{x['type']}-{x['atom']}" for x in s]


def cmd_prune(a) -> None:
    """Tira dos resultados (small e medium) os sítios que não estão no sorteio atual — o que pula regiões fora do
    equilíbrio —, para que `sites` calcule os substitutos e `collect` use só o sorteio vigente."""
    for T in STRUCTURES:
        sel = set(selection(T, a.per_type))
        for f in sorted(glob.glob(os.path.join(OUT, f"sites_{T}_*.jsonl"))):
            if f.endswith("_medium.jsonl"):          # a validação só vale em pares com o small (collect filtra)
                continue
            rows = [json.loads(line) for line in open(f)]
            keep = [r for r in rows if r["label"] in sel]
            for r in rows:
                if r["label"] not in sel:
                    print(f"fora do sorteio (região fora do equilíbrio ou espaçamento): {r['label']} [{os.path.basename(f)}]")
            with open(f, "w") as fh:
                fh.writelines(json.dumps(r) + "\n" for r in keep)
        print(f"{T}: {len(sel)} sítios no sorteio", flush=True)


# ------------------------------------------------------------------------------------------------------ collect
def cmd_collect(a) -> None:
    """outputs/atomistic/au_go_interface → datasets/au-go-interface/ (refs.json, sites.csv, particles.json)."""
    import csv

    os.makedirs(DATA, exist_ok=True)
    refs = json.load(open(os.path.join(OUT, "refs.json")))
    files = sorted(glob.glob(os.path.join(OUT, "sites_*.jsonl")))
    rows = [json.loads(line) for f in files if not f.endswith("_medium.jsonl") for line in open(f)]
    med = [json.loads(line) for f in files if f.endswith("_medium.jsonl") for line in open(f)]
    cols = ["structure", "type", "atom", "side", "E_ads_eV", "E_site_eV", "E_site_rigid_eV", "n_contacts", "contacts", "broken",
            "go_prerelax_eV", "site_shift_A", "au_height_A", "converged", "fmax", "steps", "n_atoms", "n_free_go", "seconds"]
    e_free = refs["E_free_atom_model_eV"]
    with open(os.path.join(DATA, "sites.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for r in sorted(rows, key=lambda r: (r["structure"], SITE_TYPES.index(r["type"]) if r["type"] in SITE_TYPES else 99, r["atom"])):
            w.writerow([r["structure"], r["type"], r["atom"], r["side"], round(r["E_site_eV"] - e_free, 4), round(r["E_site_eV"], 4),
                        round(r["E_site_rigid_eV"], 4), len(r["contacts"]),
                        " ".join(f"{c['el']}({c.get('type', '')}):{c['d']}" for c in r["contacts"]),
                        " ".join(f"{b['pair']}:{b['d0']}->{b['d1']}" for b in r["broken"]), round(r.get("go_prerelax_eV", 0.0), 4),
                        round(r["site_shift_A"], 3),
                        round(r["au_height_A"], 3), r["relax"]["converged"], round(r["relax"]["fmax"], 4), r["relax"]["steps"],
                        r["n_atoms"], r["n_free_go"], r["seconds"]])
    parts = {}
    for f in sorted(glob.glob(os.path.join(OUT, "particle_*.json"))):
        r = json.load(open(f))
        parts[r["structure"]] = r
    val = None
    fm = os.path.join(OUT, "refs_medium.json")
    if med and os.path.exists(fm):                   # validação: mesmos sítios com o MACE-MP-0 medium
        rm = json.load(open(fm))
        small = {r["label"]: r for r in rows}
        val = {"model": rm["model"], "refs": {k: rm[k] for k in ("mu_Au_eV", "a0_A", "gamma111_J_m2", "E_free_atom_model_eV",
                                                                 "au_graphene") if k in rm},
               "sites": [[r["structure"], r["type"], r["atom"], small[r["label"]]["E_site_eV"] - refs["E_free_atom_model_eV"],
                          r["E_site_eV"] - rm["E_free_atom_model_eV"], len(small[r["label"]]["contacts"]), len(r["contacts"])]
                         for r in med if r["label"] in small]}
    eq = {}                                          # quanto de cada folha publicada está fora do equilíbrio no GO-MACE-23
    for T in STRUCTURES:
        f = os.path.join(OUT, f"forces_{T}.npy")
        if os.path.exists(f):
            fn = np.load(f)
            eq[T] = {"n_atoms": int(len(fn)), "n_checked": int(np.isfinite(fn).sum()), "median_eV_A": float(np.nanmedian(fn)),
                     "n_gt_0p1": int(np.nansum(fn > 0.1)), "n_gt_1": int(np.nansum(fn > 1)), "n_gt_5": int(np.nansum(fn > 5)),
                     "fmax_eV_A": float(np.nanmax(fn))}
    json.dump({"refs": refs, "particles": parts, "validation_medium": val, "equilibrium": eq},
              open(os.path.join(DATA, "particles.json"), "w"), separators=(",", ":"))
    print(f"{len(rows)} sítios, {len(parts)} partículas, {len(val['sites']) if val else 0} sítios na validação → "
          f"{os.path.relpath(DATA, ROOT)}")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("refs")
    r.add_argument("--mp-size", choices=("small", "medium"), default="small")
    s = sub.add_parser("sites")
    s.add_argument("--structure", choices=STRUCTURES + ("graphene",), required=True)
    s.add_argument("--per-type", type=int, default=3)
    s.add_argument("--radius", type=float, default=13.0)
    s.add_argument("--part", default="0/1")
    s.add_argument("--threads", type=int, default=1)
    s.add_argument("--mp-size", choices=("small", "medium"), default="small")
    s.add_argument("--atoms", default="", help="só estes átomos (índices na folha, separados por vírgula)")
    s.add_argument("--no-equilibrium", dest="equilibrium", action="store_false",
                   help="não pular sítios perto de regiões fora do equilíbrio (|F| > 1 eV/Å no GO-MACE-23)")
    p = sub.add_parser("particle")
    p.add_argument("--structure", choices=STRUCTURES + ("graphene",), required=True)
    p.add_argument("--d", type=float, default=1.5)
    p.add_argument("--adh", type=float, default=0.35)
    p.add_argument("--radius", type=float, default=20.0)
    p.add_argument("--free-margin", type=float, default=6.0)
    p.add_argument("--steps", type=int, default=600)
    p.add_argument("--fmax", type=float, default=0.03)
    p.add_argument("--resume", action="store_true", help="continua uma relaxação que parou no limite de passos")
    p.add_argument("--opt", choices=("FIRE", "BFGS", "LBFGS"), default="FIRE", help="otimizador da continuação (--resume)")
    p.add_argument("--threads", type=int, default=1)
    ct = sub.add_parser("contact")
    ct.add_argument("--mp-size", choices=("small", "medium"), default="small")
    x = sub.add_parser("crosscheck")
    x.add_argument("--mp-size", choices=("small", "medium"), default="small")
    x.add_argument("--pattern", default="*", help="folha (ex.: 900K); só partículas já terminadas")
    x.add_argument("--threads", type=int, default=1)
    c = sub.add_parser("recheck")
    c.add_argument("--tol", type=float, default=0.01)
    c.add_argument("--threads", type=int, default=1)
    c.add_argument("--pattern", default="*", help="parte do nome dos arquivos (ex.: 900K_*of2 ou 900K)")
    pr = sub.add_parser("prune")
    pr.add_argument("--per-type", type=int, default=3)
    sub.add_parser("collect")
    a = ap.parse_args(argv)
    global MP_SIZE
    MP_SIZE = getattr(a, "mp_size", "small")
    {"refs": cmd_refs, "contact": cmd_contact, "sites": cmd_sites, "particle": cmd_particle, "crosscheck": cmd_crosscheck,
     "recheck": cmd_recheck, "prune": cmd_prune, "collect": cmd_collect}[a.cmd](a)


if __name__ == "__main__":
    main()
