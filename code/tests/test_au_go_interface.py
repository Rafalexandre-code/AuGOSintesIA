"""code/atomistic/au_go_interface.py sem o MACE: a montagem do potencial híbrido (com calculadoras baratas no lugar do
GO-MACE-23 e do MACE-MP-0) e a geometria (recorte periódico, grafeno, pontos de partida do Au, sorteio dos sítios)."""
import os
import sys

import numpy as np
import pytest

pytest.importorskip("ase")
pytest.importorskip("scipy")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "code", "atomistic"))
import au_go_interface as A  # noqa: E402
import go_sites as G  # noqa: E402


def _toy(seed=0):
    """GO de brinquedo (grafeno + 2 O por cima) com 2 Au acima; GO primeiro, como no script."""
    from ase import Atoms

    rng = np.random.default_rng(seed)
    c = A.graphene_patch(6.0)
    o = np.array([[0.7, 1.3, 0.0], [-1.5, 1.4, 1.2]])
    au = np.array([[0.4, 3.6, 0.3], [-0.5, 5.9, -0.2]])
    pos = np.r_[c, o, au] + rng.normal(0, 0.03, (len(c) + 4, 3))
    return Atoms(symbols=["C"] * len(c) + ["O", "O", "Au", "Au"], positions=pos, pbc=False), len(c) + 2


def test_potencial_hibrido_soma_as_parcelas(monkeypatch):
    """E = E_GO(GO) + E_MP(GO+Au) − E_MP(GO), forças = −∇E (diferenças finitas), e o modo rígido = E_MP(tudo) + cte."""
    from ase.calculators.emt import EMT
    from ase.calculators.lj import LennardJones

    gom, mp = LennardJones(sigma=2.0, epsilon=0.01, rc=6.0), EMT()
    monkeypatch.setattr(A, "calcs", lambda dtype="float32": (gom, mp))
    atoms, n = _toy()
    e_go, _ = A.ef(gom, atoms[:n])
    e_all, f_all = A.ef(mp, atoms)
    e_mpgo, _ = A.ef(mp, atoms[:n])
    h = A.hybrid_calculator(n)
    a = atoms.copy()
    a.calc = h
    assert a.get_potential_energy() == pytest.approx(e_go + e_all - e_mpgo, abs=1e-9)
    assert A.hybrid_energy(atoms, n)["E"] == pytest.approx(e_go + e_all - e_mpgo, abs=1e-9)
    f = a.get_forces()
    assert np.allclose(f[n:], f_all[n:])                   # no Au só a parcela do MACE-MP
    for i in (0, n - 1, n, n + 1):                         # −dE/dx por diferenças finitas, num C, num O e nos Au
        for k in range(3):
            ep, em = atoms.copy(), atoms.copy()
            ep.positions[i, k] += 1e-4
            em.positions[i, k] -= 1e-4
            d = (A.hybrid_energy(ep, n)["E"] - A.hybrid_energy(em, n)["E"]) / 2e-4
            assert f[i, k] == pytest.approx(-d, abs=2e-4)
    r = atoms.copy()
    r.calc = A.hybrid_calculator(n, rigid=True)
    assert r.get_potential_energy() == pytest.approx(e_go + e_all - e_mpgo, abs=1e-9)
    assert np.allclose(r.get_forces()[n:], f_all[n:])
    assert A.hybrid_energy(atoms[n:], 0)["E"] == pytest.approx(A.ef(mp, atoms[n:])[0])   # ouro sozinho: só MACE-MP


def test_hibrido_por_elemento_independe_da_ordem(monkeypatch):
    """A versão por elemento (calculators "hybrid", go_au.py) dá a mesma energia que a por ordem, com os átomos em
    qualquer ordem; GO puro = só o potencial do GO; ouro puro = só o universal."""
    from ase.calculators.emt import EMT
    from ase.calculators.lj import LennardJones

    gom, mp = LennardJones(sigma=2.0, epsilon=0.01, rc=6.0), EMT()
    monkeypatch.setattr(A, "calcs", lambda dtype="float32": (gom, mp))
    atoms, n = _toy(1)
    ref = A.hybrid_energy(atoms, n)["E"]
    perm = np.random.default_rng(3).permutation(len(atoms))
    b = atoms[perm]
    b.calc = A.element_hybrid_calculator()
    assert b.get_potential_energy() == pytest.approx(ref, abs=1e-9)
    a = atoms.copy()
    a.calc = A.hybrid_calculator(n)
    assert np.allclose(b.get_forces(), a.get_forces()[perm])
    g = atoms[:n]
    g.calc = A.element_hybrid_calculator()
    assert g.get_potential_energy() == pytest.approx(A.ef(gom, atoms[:n])[0])
    u = atoms[n:]
    u.calc = A.element_hybrid_calculator()
    assert u.get_potential_energy() == pytest.approx(A.ef(mp, atoms[n:])[0])


def test_geometria_do_recorte_e_dos_pontos_de_partida():
    g = A.graphene_patch(10.0)
    from scipy.spatial import cKDTree

    d, _ = cKDTree(g).query(g, k=5)
    assert np.allclose(d[:, 1], 1.42, atol=1e-6) and np.hypot(g[:, 0], g[:, 2]).max() < 10
    assert np.min(np.hypot(g[:, 0], g[:, 2])) < 1e-9 and np.allclose(g[:, 1], 0)
    inner = np.hypot(g[:, 0], g[:, 2]) < 7
    assert np.allclose(d[inner, 1:4], 1.42, atol=1e-6) and np.all(d[inner, 4] > 2.4)   # favo de mel: 3 vizinhos a 1,42 Å
    s = int(np.argmin(np.hypot(g[:, 0], g[:, 2])))
    starts = A.place_atom(g, s, 2.2, side=1)
    assert len(starts) == 3
    assert starts[0][1] > 2.2 and starts[0][1] >= max(x[1] for x in starts)   # a primeira é a direção mais livre
    for q, dmin in starts:
        assert np.linalg.norm(q - g[s]) == pytest.approx(2.2) and q[1] > g[s, 1] and dmin > 1.5
    u = [(q - g[s]) / 2.2 for q, _ in starts]
    assert all(np.degrees(np.arccos(np.clip(u[i] @ u[j], -1, 1))) > 50 for i in range(3) for j in range(i))
    box = np.array([20.0, 0.0, 15.0])                      # recorte periódico: átomo do outro lado da caixa entra
    p = np.array([[0.5, 0, 0.5], [19.6, 0.2, 14.8], [10, 0, 7]])
    idx, loc = A.carve(p, box, 0.5, 0.5, 3.0)
    assert list(idx) == [0, 1] and np.allclose(loc, [[0, 0, 0], [-0.9, 0.2, -0.7]])    # x, z em relação ao centro


def test_sitios_sorteados_na_folha_publicada():
    el, pos, box = G.structure("1500K")
    t, side, p, nb = G.classify_nb(el, pos, box)
    s = A.pick_sites(el, p, box, t, side, nb, 3, 15)
    by = {}
    for x in s:
        by.setdefault(x["type"], []).append(x["atom"])
        assert G.GO_TYPES[t[x["atom"]]] == x["type"]
    assert set(by) <= set(A.SITE_TYPES) and all(len(v) <= 3 for v in by.values())
    assert "O epóxi" not in by and {"O carbonila", "O éter", "C de borda", "C sp²"} <= set(by)   # 1500 K: sem epóxi
    for ty, v in by.items():
        for i in v:
            for j in v:
                if i < j:
                    d = p[i] - p[j]
                    d[0] -= box[0] * np.round(d[0] / box[0])
                    d[2] -= box[2] * np.round(d[2] / box[2])
                    assert np.linalg.norm(d) > 12, ty
    edge = by["C de borda"]
    assert all(len(nb[i]) == 2 and all(el[j] == "C" for j in nb[i]) for i in edge)    # ligações pendentes


def test_contato_au_grafeno_geometria():
    """A célula do contato Au(111)/grafeno (`contact`): grafeno 2×2 com C–C de 1,42 Å e 3 vizinhos; Au(111) √3×√3R30°
    com 3 átomos por camada, vizinhos no plano a L/√3, camadas internas com 12 vizinhos (cada camada sobre os buracos
    da anterior) e empilhamento ABC (a 4ª camada sobre a 1ª); e o mínimo da parábola usado nas varreduras."""
    from ase import Atoms
    from ase.neighborlist import neighbor_list

    cell, au, c = A.au_graphene_slab()
    assert len(c) == 8 and len(au) == 12
    i, d = neighbor_list("id", Atoms("C8", positions=c + [0, 0, 20], cell=cell, pbc=True), 1.6)
    assert np.allclose(d, 1.42, atol=0.01) and np.all(np.bincount(i) == 3)
    z = np.round(au[:, 2], 3)
    layers = np.unique(z)
    assert len(layers) == 4 and np.allclose(np.diff(layers), 4.111 / np.sqrt(3), atol=1e-3)
    for zl in layers:
        i, d = neighbor_list("id", Atoms("Au3", positions=au[z == zl], cell=cell, pbc=True), 3.0)
        assert np.allclose(d, 4.92 / np.sqrt(3), atol=1e-6) and np.all(np.bincount(i) == 6)
    i, d = neighbor_list("id", Atoms("Au12", positions=au, cell=cell, pbc=True), 3.1)
    cnt = np.bincount(i, minlength=12)
    assert np.all(cnt[(z == layers[1]) | (z == layers[2])] == 12) and np.all(cnt[(z == layers[0]) | (z == layers[3])] == 9)
    xy = lambda zl: np.sort(np.round(au[z == zl][:, :2], 4), axis=0)                    # noqa: E731
    assert np.allclose(xy(layers[3]), xy(layers[0])) and not np.allclose(xy(layers[1]), xy(layers[0]))
    x = np.linspace(0, 1, 6)
    xm, ym = A._parabola_min(x, 3 * (x - 0.37) ** 2 - 0.5, 2)
    assert xm == pytest.approx(0.37) and ym == pytest.approx(-0.5)
    assert A._parabola_min(x, x, 0) == (0.0, 0.0)                                          # na ponta: o próprio ponto


def test_filme_de_ouro_da_interface_e_au111():
    """go_au.py interface confere o filme de ouro: o Au(111) do contato passa (área por átomo 2,9 % menor que a do Au(111) real); o mesmo
    filme esticado como o InterMat chegou a fazer (13 Å² por átomo, planos a 1,4 Å) é recusado."""
    from ase import Atoms

    import go_au

    cell, au, c = A.au_graphene_slab()
    good = Atoms(symbols=["Au"] * len(au) + ["C"] * len(c), positions=np.r_[au, c + [0, 0, 20]], cell=cell, pbc=True)
    chk = go_au.au_film_check(good, np.array(good.get_chemical_symbols()) == "Au")
    assert chk["ok"] and chk["n_au_layers"] == 4 and chk["au_area_per_atom_A2"] == pytest.approx(4.92 ** 2 * np.sqrt(3) / 2 / 3, abs=1e-3)
    bad = good.copy()
    bad.set_cell(cell * np.array([[1.35], [1.35], [1.0]]), scale_atoms=False)
    m = np.array(bad.get_chemical_symbols()) == "Au"
    bad.positions[m, :2] *= 1.35
    bad.positions[m, 2] = 5 + (bad.positions[m, 2] - 5) * 1.4 / (4.111 / np.sqrt(3))
    chk = go_au.au_film_check(bad, m)
    assert not chk["ok"] and chk["au_area_per_atom_A2"] > 12 and chk["au_layer_spacing_A"] == pytest.approx(1.4, abs=0.06)
