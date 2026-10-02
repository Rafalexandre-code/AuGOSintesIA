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



def test_tem_go_association():
    import tem
    from skimage.draw import disk
    img, cs = np.full((600, 600), 210.0), []
    img[:, :300] = 150.0                                     # folha de GO (contraste fraco) na metade esquerda
    on_target = 0
    while len(cs) < 24:
        c = rng.integers(40, 560, 2)
        if abs(c[1] - 300) < 30 or not all(np.hypot(*(c - o)) > 50 for o in cs):
            continue
        cs.append(c)
        on_target += c[1] < 300
        rr, cc = disk(tuple(c), 12, shape=img.shape)
        img[rr, cc] = 50.0
    img += rng.normal(0, 6, img.shape)
    lab = tem.segment(img, min_diameter_px=20, classes=3)
    s = tem.summarize(tem.particle_sizes(lab, 1.0))
    assert s["n_particles"] >= 22                            # o GO não vira "partícula" com 3 classes
    a = tem.association_summary([tem.go_association(img, lab)], [1.0])
    assert a["n_classified"] >= 22
    assert a["GO_associated_fraction"] == pytest.approx(on_target / 24, abs=0.06)
    assert a["GO_area_fraction"] == pytest.approx(0.5, abs=0.05)
    assert a["GO_associated_ci_low"] < a["GO_associated_fraction"] < a["GO_associated_ci_high"]
    rows = tem.to_rows({**s, **a}, "SYN-1")
    assert {"GO_associated_fraction", "nucleation_selectivity"} <= {r["quantity"] for r in rows}


def test_ftir_ratios_and_water_flag():
    import ftir
    x = np.linspace(600, 4000, 3401)
    G = lambda c, w, a: a * np.exp(-0.5 * ((x - c) / w) ** 2)   # noqa: E731
    bands = {"CO": G(1725, 20, 0.30), "H2O": G(1625, 22, 0.20), "CC": G(1580, 25, 0.40),
             "COC": G(1230, 18, 0.25), "alk": G(1055, 20, 0.35), "OH": G(3350, 180, 0.15)}
    y = sum(bands.values()) + 0.05 + 2e-5 * (x - 600) + rng.normal(0, 0.002, x.size)
    r = ftir.analyze(x, y)
    area = {k: np.trapezoid(v, x) for k, v in bands.items()}
    assert r["FTIR_CO_CC"] == pytest.approx(area["CO"] / area["CC"], rel=0.10)
    assert r["FTIR_COC_CC"] == pytest.approx(area["COC"] / area["CC"], rel=0.15)
    assert r["FTIR_water_frac"] == pytest.approx(area["H2O"] / (area["H2O"] + area["CC"]), abs=0.08)
    rows = ftir.to_rows(ftir.summarize([r, ftir.analyze(x, y + rng.normal(0, 0.002, x.size))]), "GO-1", max_water=0.1)
    assert any("umidade" in row["notes"] for row in rows if row["quantity"] == "FTIR_water_frac")


def test_xrd_d001_and_au_crystallite():
    import xrd
    tt = np.arange(5, 45, 0.02)
    y = (xrd.pseudo_voigt(tt, 1000, 10.5, 1.2, 0.3) + xrd.pseudo_voigt(tt, 600, 38.2, 0.8, 0.5)
         + 300 * np.exp(-tt / 15) + 50 + rng.normal(0, 3, tt.size))
    r = xrd.analyze(tt, y)
    assert r["d001_nm"][0] == pytest.approx(xrd.bragg_d_nm(10.5), rel=0.005)
    assert r["d001_nm"][0] == pytest.approx(0.842, abs=0.005)
    L = 0.94 * 1.5406 / (np.radians(0.8) * np.cos(np.radians(19.1))) / 10
    assert r["Au_crystallite_nm"][0] == pytest.approx(L, rel=0.05)
    assert r["frac_graphitic"][0] < 0.05                      # sem pico de grafite em 26,5°
    assert r["n_layers"][0] > 1


def test_dls_cumulants_recover_size():
    import dls
    tau = np.logspace(-7, -1, 200)
    q2 = dls.q_vector(173, 633) ** 2
    D = lambda d: 1.380649e-23 * 298.15 / (3 * np.pi * dls.water_viscosity_mPas(25) * 1e-3 * d * 1e-9)   # noqa: E731
    g2 = 1 + 0.8 * np.exp(-2 * D(50) * q2 * tau) + rng.normal(0, 1e-4, tau.size)
    r = dls.analyze(tau, g2)
    assert r["hydrodynamic_nm"] == pytest.approx(50, rel=0.03) and r["PDI"] < 0.05
    sizes = np.exp(rng.normal(np.log(50), 0.35, 400))       # polidisperso: PDI cresce
    g1 = np.mean([d ** 6 * np.exp(-D(d) * q2 * tau) for d in sizes], axis=0) / np.mean(sizes ** 6)
    r2 = dls.analyze(tau, 0.8 * g1 ** 2)                     # formato g2 − 1
    assert r2["PDI"] > 0.05
    assert dls.water_viscosity_mPas(25) == pytest.approx(0.890, abs=0.005)

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



def test_baseline_strategies_propose(sim_lab_dir):
    import designer
    import strategies
    camp = designer.load_campaign(sim_lab_dir, designer.DEFAULT_SPACE, "go", ("spectral_loss_J",))
    fixed = designer.fixed_context(sim_lab_dir, camp, "L2", None)
    for f in (strategies.propose_gp_ei, strategies.propose_rf_qnehvi, strategies.propose_random):
        c = f(camp, designer.DEFAULT_SPACE, 2, fixed, 0)
        assert c.shape == (2, camp.X.shape[1]) and np.allclose(c["ctx_C_O_ratio"], fixed["ctx_C_O_ratio"])
        for k, (lo, hi) in designer.DEFAULT_SPACE.items():
            assert c[k].between(lo - 1e-9, hi + 1e-9).all()


def test_time_to_criterion_and_logrank():
    import pandas as pd
    import stats
    rows = []
    for seed in range(6):
        for n in range(1, 11):
            rows.append({"arm": "fast", "seed": seed, "n": n, "value": 10 - n})            # atinge 5 em n = 5
            rows.append({"arm": "slow", "seed": seed, "n": n, "value": 10 - 0.4 * n})      # nunca atinge (censura)
    r = stats.time_to_criterion(pd.DataFrame(rows), 5.0, reference="slow")
    assert r["arms"]["fast"]["rmst"] == pytest.approx(5.0) and r["arms"]["fast"]["fraction_reached"] == 1.0
    assert r["arms"]["slow"]["rmst"] == pytest.approx(10.0) and r["arms"]["slow"]["fraction_reached"] == 0.0
    assert r["arms"]["fast"]["logrank_p"] < 0.01
    assert stats.logrank(np.array([3.0, 5, np.inf]), np.array([3.0, 5, np.inf]), 10) == pytest.approx(1.0)

def test_causal_runs(sim_lab_dir):
    import causal_analysis as ca
    r = ca.estimate(sim_lab_dir, "C_O_ratio", "size_mean_nm", refute=False)
    assert r["n"] > 10 and np.isfinite(r["effect_per_unit"])


def test_cli_help():
    for script in ("code/aunp_designer/designer.py", "code/benchmarking/campaign_sim.py", "code/causal/causal_analysis.py",
                   "code/spectral/uvvis.py", "code/spectral/mie.py", "code/characterization/raman.py",
                   "code/characterization/xps.py", "code/characterization/tem.py", "code/sustainability/metrics.py",
                   "code/characterization/ftir.py", "code/characterization/xrd.py", "code/characterization/dls.py",
                   "code/miso/miso.py", "code/decision/voi.py", "code/qc/qc_check.py", "code/campaign/plan.py",
                   "code/campaign/prereg.py"):
        assert subprocess.run([sys.executable, os.path.join(ROOT, script), "--help"], capture_output=True).returncode == 0


# ------------------------------------------------------------------ regressões da revisão de 2026-09-29

def test_read_spectrum_formats(tmp_path):
    """CSV brasileiro (';' + vírgula decimal) era lido errado em silêncio: '510,5;0,431' -> (510.0, 5.0)."""
    import uvvis
    files = {"br.csv": "lambda;abs\n500,0;0,100\n510,5;0,431\n520,0;0,500\n",
             "us.csv": "wl,abs\n500,0.1\n510.5,0.431\n520,0.5\n",
             "tab.txt": "500\t0,1\n510,5\t0,431\n520\t0,5\n", "sp.txt": "500 0.1\n510.5 0.431\n520 0.5\n"}
    for name, text in files.items():
        (tmp_path / name).write_text(text)
        w, a = uvvis.read_spectrum(str(tmp_path / name))
        assert np.allclose(w, [500, 510.5, 520]) and np.allclose(a, [0.1, 0.431, 0.5]), name
    wl = np.arange(400, 800, 1.0)
    band = np.exp(-((wl - 530) / 30) ** 2)
    assert uvvis.lspr(wl[::-1], band[::-1])["LSPR_nm"] == pytest.approx(530, abs=0.5)   # ordem decrescente


def test_validator_messages(tmp_path, capsys):
    import lab_data_model
    (tmp_path / "go_batches.csv").write_text("go_batch_id;source_type\nB1;commercial\n")
    assert lab_data_model.validate(str(tmp_path)) == 1
    assert "';'" in capsys.readouterr().out
    (tmp_path / "go_batches.csv").write_text("go_batch_id,source_type,date_prepared\nB1,commercial,29/09/2026\n")
    (tmp_path / "aunp_syntheses.csv").write_text(
        "synthesis_id,gold_precursor_lot_id,method,HAuCl4_mM,run_order\nS1,L1,one_pot,\"0,25\",3.0\n")
    (tmp_path / "reagent_lots.csv").write_text("lot_id,entity_id,chemical_name,supplier,lot_number\nL1,HAuCl4,x,y,z\n")
    assert lab_data_model.validate(str(tmp_path)) == 1
    out = capsys.readouterr().out
    assert "AAAA-MM-DD" in out and "ponto decimal" in out and "run_order" not in out


def test_designer_context_errors(sim_lab_dir):
    import designer
    camp = designer.load_campaign(sim_lab_dir, designer.DEFAULT_SPACE, "batch", ("spectral_loss_J",))
    with pytest.raises(ValueError, match="batch"):
        designer.fixed_context(sim_lab_dir, camp, "L9", None)          # lote nunca sintetizado
    camp = designer.load_campaign(sim_lab_dir, designer.DEFAULT_SPACE, "go", ("spectral_loss_J",))
    with pytest.raises(ValueError, match="--batch"):
        designer.fixed_context(sim_lab_dir, camp, None, None)          # contexto não pode ficar livre
    with pytest.raises(ValueError, match="novelty_w"):
        designer.propose(camp, designer.DEFAULT_SPACE, q=1, novelty_w=1.5,
                         fixed=designer.fixed_context(sim_lab_dir, camp, "L1", None))
    with pytest.raises(ValueError, match="inexistentes"):
        designer.load_campaign(sim_lab_dir, designer.DEFAULT_SPACE, "go", ("nao_existe",))


def test_sim_lab_keeps_given_lots(tmp_path):
    import designer
    import pandas as pd
    import sim_lab
    lab = str(tmp_path / "lab")
    sim_lab.init_lab(lab, seed=0)
    c = pd.DataFrame([{k: (lo + hi) / 2 for k, (lo, hi) in designer.DEFAULT_SPACE.items()}] * 2)
    syn = designer.proposals_to_syntheses(c, designer.DEFAULT_SPACE, "L1", "T", 1).assign(status="done")
    syn.loc[0, "reductant_lot_id"] = "RED-B"              # só a segunda linha fica sem lote
    sim_lab.run_syntheses(lab, syn, np.random.default_rng(0))
    got = pd.read_csv(os.path.join(lab, "aunp_syntheses.csv"))
    assert got.loc[0, "reductant_lot_id"] == "RED-B" and got.loc[1, "reductant_lot_id"] in ("RED-A", "RED-B")
