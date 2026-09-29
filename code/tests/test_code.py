"""Testes do código do projeto (code/). Rodar: .venvs/core/bin/python -m pytest code/tests -q

Os sinais sintéticos abaixo têm parâmetros CONHECIDOS e servem só para verificar se os ajustes recuperam os valores.
"""
import json
import os
import subprocess
import sys

import numpy as np
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for sub in ("code/spectral", "code/characterization", "code/benchmarking", "code/aunp_designer",
            "code/go_navigator", "code/causal", "code/sustainability", "tools/data_sources"):
    sys.path.insert(0, os.path.join(ROOT, sub))

rng = np.random.default_rng(0)


# ------------------------------------------------------------------ espectral

def test_mie_lspr_matches_literature():
    import mie
    wl = np.arange(450, 700, 1.0)
    lam = {d: wl[np.argmax(mie.extinction_cross_section(wl, d))] for d in (20, 60, 100)}
    assert 518 <= lam[20] <= 524          # AuNP de 20 nm em água: ~520 nm
    assert 530 <= lam[60] <= 542
    assert 560 <= lam[100] <= 580
    assert lam[20] < lam[60] < lam[100]


def test_uvvis_lspr_and_loss():
    import mie
    import uvvis
    wl = np.arange(350, 800, 1.0)
    A = mie.ensemble_extinction(wl, 15)
    r = uvvis.lspr(wl, A)
    assert abs(r["LSPR_nm"] - 522) < 3
    assert abs(r["d_Haiss_ratio_nm"] - 15) < 3          # relação de Haiss (A_LSPR/A450) para d pequeno
    assert uvvis.spectral_loss_J(wl, A, wl, A, s=0.01) == pytest.approx(0.0)
    B = mie.ensemble_extinction(wl, 60)
    assert uvvis.spectral_loss_J(wl, B, wl, A, s=0.01, norm="max") > 10
    corr = uvvis.correct(wl, A + 0.1, blank=(wl, np.full_like(wl, 0.1)), dilution=2, path_mm=5)
    assert np.allclose(corr, 4 * A)


def test_uvvis_real_spectra_bespoke():
    """λmax em espectros REAIS (KIST Bespoke, AgNP) vs. valores publicados pelos autores."""
    import glob
    import uvvis
    fs = glob.glob(os.path.join(ROOT, "external/aunp-spectral/BespokeSynthesisPlatform/Result/**/*.json"), recursive=True)
    diffs = []
    for f in fs:
        u = json.load(open(f)).get("result", {}).get("GetUVdata", {})
        if "Property" not in u:
            continue
        lm = u["Property"]["lambdamax"]
        lm = lm[0] if isinstance(lm, list) else lm
        diffs.append(uvvis.lspr(np.array(u["Wavelength"]), np.array(u["RawSpectrum"]), window=(350, 800))["LSPR_nm"] - lm)
    if not diffs:
        pytest.skip("espectros do Bespoke ausentes")
    assert np.median(np.abs(diffs)) < 1.0


# ------------------------------------------------------------------ caracterização

def test_raman_recovers_widths():
    import raman
    x = np.linspace(900, 2000, 1100)
    L = lambda c, w, h: h * (w / 2) ** 2 / ((x - c) ** 2 + (w / 2) ** 2)   # noqa: E731
    y = L(1350, 120, 900) + L(1590, 80, 1000) + 0.3 * (x - 900) + 200 + rng.normal(0, 10, x.size)
    f = raman.fit(x, y, "2band")
    assert f["D_FWHM_cm-1"][0] == pytest.approx(120, rel=0.05)
    assert f["G_FWHM_cm-1"][0] == pytest.approx(80, rel=0.05)
    assert f["ID_IG"][0] == pytest.approx(0.9, rel=0.05)


def test_xps_c1s_fractions():
    import xps
    be = np.linspace(280, 295, 600)
    G = lambda c, s: np.exp(-(be - c) ** 2 / (2 * s ** 2))   # noqa: E731
    frac = {"CC": (284.8, .50), "C-O": (286.8, .30), "C=O": (287.9, .12), "O-C=O": (289.0, .08)}
    sig = sum(a * G(c, 0.55) for c, a in frac.values()) * 1000
    bg = np.cumsum(sig[::-1])[::-1]
    bg = 50 + 200 * (bg.max() - bg) / bg.max()
    r = xps.fit_c1s(be, sig + bg + rng.normal(0, 5, be.size))
    for k, (_, a) in frac.items():
        assert r[f"C1s_{k}_pct"][0] == pytest.approx(100 * a, abs=3)
    assert xps.c_over_o(1.0, 2.93) == pytest.approx(1.0)


def test_tem_sizes():
    import tem
    from skimage.draw import disk
    img, cs = np.full((500, 500), 200.0), []
    while len(cs) < 25:
        c = rng.integers(30, 470, 2)
        if all(np.hypot(*(c - o)) > 45 for o in cs):
            cs.append(c)
            rr, cc = disk(tuple(c), rng.normal(20, 2) / 2 / 0.5, shape=img.shape)
            img[rr, cc] = 60
    img += rng.normal(0, 8, img.shape)
    s = tem.summarize(tem.particle_sizes(tem.segment(img, min_diameter_px=30), 0.5))
    assert s["n_particles"] >= 22
    assert s["size_mean_nm"] == pytest.approx(20, abs=1.5)


# ------------------------------------------------------------------ estatística e sustentabilidade

def test_stats():
    import stats
    adj = stats.holm({"a": 0.01, "b": 0.04, "c": 0.03})
    assert adj["a"] == pytest.approx(0.03) and adj["c"] == pytest.approx(0.06) and adj["b"] == pytest.approx(0.06)
    r = stats.paired_bootstrap_relative_reduction(np.full(10, 2.0), np.full(10, 1.6))
    assert r["mean_reduction"] == pytest.approx(0.2)
    hv = stats.hv_igd_spread(np.array([[0.0, 1.0], [1.0, 0.0]]), np.array([2.0, 2.0]))
    assert hv["hypervolume"] == pytest.approx(3.0)


def test_sustainability():
    import metrics
    assert metrics.e_factor(10, 2) == 5
    assert metrics.ecoscale(80)["ecoscale"] == 90
    assert metrics.cost_per_useful_information(100, 0.5, 0.25, 2) == pytest.approx(100.0)


def test_e_value():
    import causal_analysis as ca
    assert ca.e_value_rr(2.0) == pytest.approx(2 + np.sqrt(2))
    assert ca.e_value_rr(0.5) == pytest.approx(ca.e_value_rr(2.0))


# ------------------------------------------------------------------ laço completo (simulado)

@pytest.fixture(scope="module")
def sim_lab_dir(tmp_path_factory):
    import designer
    out = tmp_path_factory.mktemp("demo")
    designer.demo(str(out), iterations=2, q=2, seed=1)
    return str(out / "lab")


def test_demo_tables_valid(sim_lab_dir):
    import lab_data_model
    assert lab_data_model.validate(sim_lab_dir) == 0


@pytest.mark.parametrize("rep", ["recipe", "batch", "go", "go+impurities"])
def test_propose_all_representations(sim_lab_dir, rep):
    import designer
    camp = designer.load_campaign(sim_lab_dir, designer.DEFAULT_SPACE, rep, ("spectral_loss_J",))
    fixed = designer.fixed_context(sim_lab_dir, camp, "L2", {"reductant": "RED-B"})
    c = designer.propose(camp, designer.DEFAULT_SPACE, q=2, fixed=fixed, seed=3)
    assert len(c) == 2
    for v, (lo, hi) in designer.DEFAULT_SPACE.items():
        assert c[v].between(lo - 1e-6, hi + 1e-6).all()
    assert "pred_spectral_loss_J" in c and (c["pred_spectral_loss_J"] > -1e-3).all()


def test_novelty_and_lbo(sim_lab_dir):
    import designer
    camp = designer.load_campaign(sim_lab_dir, designer.DEFAULT_SPACE, "go", ("spectral_loss_J",))
    c = designer.propose(camp, designer.DEFAULT_SPACE, q=3, novelty_w=0.5, seed=0,
                         fixed=designer.fixed_context(sim_lab_dir, camp, "L1", None))
    assert len(c) == 3 and len(c.round(6).drop_duplicates()) == 3
    res = designer.validate_lbo(sim_lab_dir, designer.DEFAULT_SPACE, ("recipe", "go"), ("spectral_loss_J",))
    assert set(res["representation"]) == {"recipe", "go"} and res["rmse"].notna().all()


def test_causal_runs(sim_lab_dir):
    import causal_analysis as ca
    r = ca.estimate(sim_lab_dir, "C_O_ratio", "size_mean_nm", refute=False)
    assert r["n"] > 10 and np.isfinite(r["effect_per_unit"])


def test_cli_help():
    for script in ("code/aunp_designer/designer.py", "code/benchmarking/campaign_sim.py", "code/causal/causal_analysis.py",
                   "code/spectral/uvvis.py", "code/spectral/mie.py", "code/characterization/raman.py",
                   "code/characterization/xps.py", "code/characterization/tem.py", "code/sustainability/metrics.py"):
        assert subprocess.run([sys.executable, os.path.join(ROOT, script), "--help"], capture_output=True).returncode == 0
