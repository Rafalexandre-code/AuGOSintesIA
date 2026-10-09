"""Química das folhas de óxido de grafeno (GO) publicadas: leitura, ligações, tipo de cada átomo e recorte da cena.

Usado por code/webapp/analyses.py (composição e recorte da aba Nanocompósito 3D) e por au_go_interface.py (sítios
onde o Au é colocado), para que o site e o cálculo atomístico classifiquem os átomos da mesma forma. Só numpy/scipy.

Estruturas: El-Machachi et al., Angew. Chem. Int. Ed. 2024, e202410088 (dados: Zenodo 10.5281/zenodo.14066557),
em projects/atomistic/GO-MACE-23/structures/{900K,1200K,1500K}/optimized.xyz — folha periódica em x e z, normal y.
"""
from __future__ import annotations

import os

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
GO_MACE = os.path.join(ROOT, "projects", "atomistic", "GO-MACE-23", "structures")
GO_TYPES = ["C sp²", "C sp³", "C de borda", "O epóxi", "O hidroxila", "O éter", "O carbonila", "O carboxila", "O lactona",
            "O outro", "H"]
CUT = {("C", "C"): 1.85, ("C", "O"): 1.75, ("C", "H"): 1.25, ("O", "H"): 1.20, ("O", "O"): 0.0, ("H", "H"): 0.0}


def read_xyz(path: str):
    """(elementos, posições Å, rede 3×3) de um extxyz com Lattice="..." (as estruturas publicadas)."""
    with open(path, encoding="utf-8") as fh:
        n = int(fh.readline())
        hdr = fh.readline()
        lat = np.array([float(x) for x in hdr.split('Lattice="')[1].split('"')[0].split()]).reshape(3, 3)
        rows = [fh.readline().split() for _ in range(n)]
    return np.array([r[0] for r in rows]), np.array([[float(v) for v in r[1:4]] for r in rows]), lat


def structure(T: str):
    """Folha publicada `T` ("900K", "1200K" ou "1500K"): elementos, posições e caixa periódica (Lx, 0, Lz)."""
    el, pos, lat = read_xyz(os.path.join(GO_MACE, T, "optimized.xyz"))
    return el, pos, np.array([lat[0, 0], 0.0, lat[2, 2]])


def neighbors(el: np.ndarray, pos: np.ndarray, box: np.ndarray):
    """Ligações por distância (C–C < 1,85; C–O < 1,75; C–H < 1,25; O–H < 1,20 Å), periódico em x e z.
    Devolve (lista de vizinhos de cada átomo, posições dobradas para dentro da caixa)."""
    from scipy.spatial import cKDTree
    p = pos.copy()
    p[:, 0] %= box[0]
    p[:, 2] %= box[2]
    tree = cKDTree(np.c_[p[:, 0], p[:, 1] - p[:, 1].min(), p[:, 2]], boxsize=[box[0], 1e6, box[2]])
    pr = tree.query_pairs(1.9, output_type="ndarray")
    dv = p[pr[:, 0]] - p[pr[:, 1]]
    dv[:, 0] -= box[0] * np.round(dv[:, 0] / box[0])
    dv[:, 2] -= box[2] * np.round(dv[:, 2] / box[2])
    d = np.linalg.norm(dv, axis=1)
    ok = np.array([d[k] < CUT.get((el[a], el[b]), CUT.get((el[b], el[a]), 0)) for k, (a, b) in enumerate(pr)])
    nb = [[] for _ in el]
    for a, b in pr[ok]:
        nb[a].append(b)
        nb[b].append(a)
    return nb, p


def classify(el: np.ndarray, pos: np.ndarray, box: np.ndarray):
    """Tipo de cada átomo (índice em GO_TYPES): C sp³ (4 vizinhos), C de borda (menos de 3 vizinhos C: bordas de
    buracos e da folha), O por grupo funcional (epóxi = ponte entre dois C ligados; éter = ponte entre C não ligados;
    hidroxila; carbonila C=O; carboxila COOH; lactona/anidrido = C=O cujo carbono também tem um O em ponte) e o lado
    da folha de cada O (+1 em cima, −1 embaixo). Devolve (tipos, lados, posições dobradas)."""
    t, side, p, _ = classify_nb(el, pos, box)
    return t, side, p


def classify_nb(el: np.ndarray, pos: np.ndarray, box: np.ndarray):
    """Como classify(), devolvendo também a lista de vizinhos."""
    nb, p = neighbors(el, pos, box)
    t = np.full(len(el), 9)
    side = np.zeros(len(el), int)
    for i, e in enumerate(el):
        if e == "H":
            t[i] = 10
        elif e == "C":
            ncc = sum(el[j] == "C" for j in nb[i])
            t[i] = 1 if len(nb[i]) >= 4 else 2 if ncc < 3 else 0
    hasH = lambda j: any(el[q] == "H" for q in nb[j])                                     # noqa: E731
    for i in np.where(el == "O")[0]:
        nc = [j for j in nb[i] if el[j] == "C"]
        nh = [j for j in nb[i] if el[j] == "H"]
        if nc:
            side[i] = 1 if p[i, 1] >= np.mean(p[nc, 1]) else -1
        if len(nc) == 2 and not nh:
            if nc[1] in nb[nc[0]]:
                t[i] = 3
            else:
                carb = any(len([q for q in nb[c] if el[q] == "O" and q != i and len(nb[q]) == 1]) for c in nc)
                t[i] = 8 if carb else 5
        elif len(nc) == 1 and len(nh) == 1:
            others = [q for q in nb[nc[0]] if el[q] == "O" and q != i]
            t[i] = 7 if others else 4
        elif len(nc) == 1 and not nh:
            others = [q for q in nb[nc[0]] if el[q] == "O" and q != i]
            t[i] = 7 if any(hasH(q) for q in others) else 8 if others else 6
    return t, side, p, nb


def flattest_crop(el: np.ndarray, p: np.ndarray, box: np.ndarray, crop: float = 96.0, step: float = 8.0):
    """Centro do recorte quadrado (lado `crop` Å) mais plano — menor desvio-padrão da altura dos C —, numa grade de
    centros com passo `step`, com periodicidade em x e z. Devolve (cx, cz, dx, dz, máscara, y0 = mediana dos C)."""
    isC = el == "C"
    best = None
    for cx in np.arange(0, box[0], step):
        for cz in np.arange(0, box[2], step):
            dx = (p[:, 0] - cx + box[0] / 2) % box[0] - box[0] / 2
            dz = (p[:, 2] - cz + box[2] / 2) % box[2] - box[2] / 2
            m = (np.abs(dx) <= crop / 2) & (np.abs(dz) <= crop / 2)
            sd = float(p[m & isC, 1].std())
            if best is None or sd < best[0]:
                best = (sd, cx, cz, dx, dz, m)
    sd, cx, cz, dx, dz, m = best
    return float(cx), float(cz), dx, dz, m, float(np.median(p[m & isC, 1])), sd
