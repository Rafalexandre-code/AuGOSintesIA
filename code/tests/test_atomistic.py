"""Testes de code/atomistic (ecossistema JARVIS). Rodar no ambiente jarvis:
    .venvs/jarvis/bin/python -m pytest code/tests/test_atomistic.py -q
No ambiente core (sem jarvis-tools) o arquivo inteiro é pulado.
"""
import glob
import os
import sys

import numpy as np
import pytest

pytest.importorskip("jarvis.core.atoms")
pytest.importorskip("ase")

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "code", "atomistic"))

import calculators as C  # noqa: E402
import jarvis_data as JD  # noqa: E402


def test_atomgpt_text_structures_match_jarvis_poscars():
    """As estruturas em texto do AtomGPT reproduzem os POSCAR completos do JARVIS-DFT (amostra do ALIGNN)."""
    import json
    import zipfile

    from jarvis.core.atoms import Atoms

    with zipfile.ZipFile(JD.ATOMGPT_STRUCTS) as z:
        entries = {e["id"]: e["desc"] for e in json.loads(z.read(z.namelist()[0]))}
    pos = glob.glob(os.path.join(ROOT, "external/jarvis/alignn/alignn/examples/sample_data/POSCAR-*.vasp"))
    n = 0
    for p in pos:
        jid = os.path.basename(p)[len("POSCAR-"):-len(".vasp")]
        if jid not in entries:
            continue
        ref, rec = Atoms.from_poscar(p), JD.parse_atomgpt_structure(entries[jid])
        assert sorted(rec.elements) == sorted(ref.elements)
        assert abs(rec.volume / ref.volume - 1) < 0.03      # rede com 0,01 Å de precisão
        n += 1
    assert n >= 20


def test_offline_dft3d_is_readable_by_jarvis_tools(tmp_path, monkeypatch):
    path = JD.build_offline_dft3d(cache=str(tmp_path), limit=300)
    JD.build_offline_defects(cache=str(tmp_path))
    monkeypatch.setenv("ATOMGPTLAB_CACHE", str(tmp_path))
    from jarvis.db.figshare import data

    d = data("dft_3d")        # mesmo nome de arquivo do figshare: o jarvis-tools lê do cache sem rede
    assert os.path.isfile(path) and len(d) == 300
    assert all(r["reconstrucao_offline"] for r in d)
    assert sum(r["formation_energy_peratom"] != "na" for r in d) > 150
    vac = data("vacancydb")
    assert any(v["id"] == "JVASP-825_Au_a_0" for v in vac)


def test_leaderboard_resolves_task_collisions():
    reg = JD.load_leaderboard("dft_3d_optb88vdw_bandgap")       # existe em regressão e em classificação
    vals = [v for split in reg.values() for v in split.values()]
    assert len(vals) > 50000 and max(float(v) for v in vals) > 2     # regressão (eV), não rótulos 0/1


def test_jarvis_ff_legacy_has_au():
    df = JD.jff_legacy()
    au = df[df["composition"] == "Au32"]
    assert len(au) >= 2 and au["energy"].between(-4.1, -3.5).all()


@pytest.mark.skipif(not os.path.exists(os.path.join(os.path.dirname(sys.executable), "lmp")),
                    reason="LAMMPS (lammps[mpi]) ausente")
def test_eam_setfl_conversion_and_jarvis_ff_elastic(tmp_path):
    """Au_u3 (funcfl) → setfl: energia coesiva e constantes elásticas de Foiles et al. (1986) pelo fluxo JARVIS-FF."""
    import jarvis_ff as F
    from ase.build import bulk

    at = bulk("Au", "fcc", a=4.08, cubic=True)
    at.calc = C.get_calculator("lammps-eam", elements={"Au"}, workdir=str(tmp_path))
    assert at.get_potential_energy() / len(at) == pytest.approx(-3.93, abs=0.005)
    el = F.jarvis_ff_elastic(str(tmp_path / "jff"))
    assert el["C11_GPa"] == pytest.approx(183, abs=3)
    assert el["C12_GPa"] == pytest.approx(159, abs=3)
    assert el["C44_GPa"] == pytest.approx(45, abs=2)


def test_go_generator_and_au_placement():
    import go_au as G

    go = G.make_go(0.3, 0.5, seed=1, nx=3, nz=2)
    comp = G.composition(go)
    assert comp["O_C_real"] == pytest.approx(0.3, abs=0.05)
    assert comp["f_OH_real"] == pytest.approx(0.5, abs=0.15)
    s = G.place_au(go, 1, np.random.default_rng(0))
    d = s.get_distances(len(s) - 1, range(len(s) - 1), mic=True)
    assert s.get_chemical_symbols()[-1] == "Au" and 1.8 < d.min() < 3.5


def test_adsorption_energy_runs_with_emt():
    import go_au as G

    e, go, s = G.adsorption_energy(0.2, 0.5, seed=3, calc=C.get_calculator("emt"), steps=5, nx=3, nz=2)
    assert np.isfinite(e) and len(s) == len(go) + 1


def test_calculator_domain_checks():
    with pytest.raises(ValueError):
        C.get_calculator("go-mace-23", elements={"C", "O", "Au"})
    with pytest.raises(ValueError):
        C.get_calculator("nao-existe")


def test_slakonet_bundled_si_model():
    """SlaKoNet (tight-binding aprendido do JARVIS) com o modelo de Si que vem no repositório."""
    pytest.importorskip("slakonet")
    from ase.build import bulk
    from slakonet.ase_calc import SlaKoNetCalculator
    from slakonet.optim import MultiElementSkfParameterOptimizer

    m = MultiElementSkfParameterOptimizer.load_ultra_compact(
        os.path.join(ROOT, "external/jarvis/slakonet/slakonet/tests/Si_only.pt")).float().eval()
    si = bulk("Si", "diamond", a=5.43)
    si.calc = SlaKoNetCalculator(m, kpoints=(3, 3, 3))
    assert np.isfinite(si.get_potential_energy())


def test_atombench_scores_identity_reconstruction(tmp_path):
    """AtomBench (métricas de modelos generativos) no conjunto AtomGen do Leaderboard: predição = alvo."""
    import csv
    import subprocess

    exe = os.path.join(os.path.dirname(sys.executable), "atombench")
    if not os.path.exists(exe):
        pytest.skip("atombench ausente")
    test = JD.load_leaderboard("AI/AtomGen/dft_3d_Tc_supercon")["test"]
    bench = tmp_path / "bench"
    bench.mkdir()
    with open(bench / "ident.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "target", "prediction"])
        for k, v in list(test.items())[:20]:
            w.writerow([k, v, v])
    r = subprocess.run([exe, str(bench), str(tmp_path / "out")], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-500:]
    assert (tmp_path / "out" / "numerical_calculations").is_dir()
