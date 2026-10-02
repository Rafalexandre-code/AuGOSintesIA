"""Caracterização condicional (AFM, zeta, ICP, OCP, mapa Raman, SERS, SAXS, survey de XPS) com sinais sintéticos de
parâmetros CONHECIDOS. Rodar: .venvs/core/bin/python -m pytest code/tests -q
"""
import os
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for sub in ("code/characterization", "code/spectral"):
    sys.path.insert(0, os.path.join(ROOT, sub))
rng = np.random.default_rng(0)


def test_afm_thickness_on_tilted_substrate():
    import afm
    ny = nx = 256
    yy, xx = np.mgrid[:ny, :nx]
    z = 0.004 * xx - 0.002 * yy + rng.normal(0, 0.05, (ny, nx))          # substrato inclinado + ruído
    for (cy, cx), t in (((60, 60), 1.0), ((60, 180), 1.0), ((180, 70), 2.0), ((190, 190), 1.0)):
        z[cy - 20:cy + 20, cx - 25:cx + 25] += t
    zl, mask = afm.level(z)
    fl = afm.flakes(zl, mask, nm_per_px=10.0)
    assert len(fl) == 4
    t = sorted(f["thickness_nm"] for f in fl)
    assert t[:3] == pytest.approx([1.0, 1.0, 1.0], abs=0.15) and t[3] == pytest.approx(2.0, abs=0.15)
    s = afm.summarize(fl)
    assert s["monolayer_fraction"][0] == pytest.approx(0.75)
    assert s["lateral_size_um"][0] == pytest.approx(np.sqrt(40 * 50) * 10 / 1000, rel=0.1)


def test_zeta_smoluchowski_and_henry():
    import zeta
    assert zeta.zeta_mV(2.0) == pytest.approx(25.6, abs=0.5)               # μ = 2 μm·cm/V·s a 25 °C
    assert zeta.henry_f(1000) == pytest.approx(1.5, abs=0.01) and zeta.henry_f(1e-3) == pytest.approx(1.0, abs=0.01)
    assert zeta.debye_length_nm(1.0) == pytest.approx(9.6, abs=0.2)          # 1 mM 1:1 → κ⁻¹ ≈ 9,6 nm
    assert zeta.zeta_mV(2.0, ionic_strength_mM=1.0, radius_nm=2.0) > zeta.zeta_mV(2.0)   # Hückel > Smoluchowski


def test_icp_gold_balance():
    import icp
    b = icp.balance(total_mg_L=9.6, supernatant_mg_L=0.48, dilution=10, volume_mL=10, HAuCl4_mM=0.5, GO_mg_mL=0.2)
    assert b["recovery"][0] == pytest.approx(96 / (0.5 * 196.96657), rel=1e-6) and b["balance_closes"]
    assert b["yield_pct"][0] == pytest.approx(95.0)
    au_solid = (96 - 4.8) * 10 / 1000
    assert b["Au_loading_wt"][0] == pytest.approx(100 * au_solid / (au_solid + 2.0))


def test_ocp_induction_and_plateau():
    import ocp
    t = np.linspace(0, 600, 1201)
    E = 300 - 150 / (1 + np.exp(-(t - 200) / 15)) + rng.normal(0, 0.5, t.size)   # queda sigmoidal em ~200 s
    f = ocp.features(t, E)
    assert f["dE_mV"] == pytest.approx(-150, abs=3)
    assert f["t_max_rate_s"] == pytest.approx(200, abs=10)
    assert f["t_induction_s"] < f["t_max_rate_s"] < f["t95_s"] < 300


def test_raman_map_detects_spatial_domains():
    import raman_map
    x, y = np.meshgrid(np.arange(15), np.arange(15))
    smooth = 0.9 + 0.01 * x.ravel() + rng.normal(0, 0.003, x.size)       # gradiente: domínios
    noise = 0.9 + rng.normal(0, 0.03, x.size)                             # ruído puro
    df = pd.DataFrame({"x": x.ravel(), "y": y.ravel(), "smooth": smooth, "noise": noise})
    s = raman_map.spatial_summary(df, ["smooth", "noise"])
    assert s["smooth"]["spatially_structured"] and s["smooth"]["morans_I"] > 0.5
    assert not s["noise"]["spatially_structured"] and abs(s["noise"]["morans_I"]) < 0.15


def test_sers_enhancement_factor():
    import sers
    x = np.linspace(1200, 1500, 600)
    peak = lambda a: a * np.exp(-0.5 * ((x - 1362) / 6) ** 2) + 50 + 0.02 * (x - 1200)   # noqa: E731
    ref = (x, peak(10.0))
    s = [(x, peak(a)) for a in (9000.0, 10000.0, 11000.0)]
    r = sers.enhancement(s, ref, 1362, 30, c_sers=1e-6, c_ref=1e-2)
    assert r["SERS_EF"][0] == pytest.approx(1e7, rel=0.02)
    assert r["SERS_RSD_pct"][0] == pytest.approx(10.0, rel=0.05)


def test_saxs_recovers_sphere_size():
    import saxs
    q = np.linspace(0.05, 1.5, 300)                                        # nm⁻¹
    I = 1e3 * saxs.sphere_intensity(q, 10.0, 0.08) + 0.01
    I *= 1 + rng.normal(0, 0.01, q.size)
    r = saxs.analyze(q, I)
    assert r["size_mean_nm"][0] == pytest.approx(20.0, rel=0.03)
    assert r["size_cv"][0] == pytest.approx(0.08, abs=0.03)
    g = saxs.guinier(q, 1e3 * saxs.sphere_intensity(q, 10.0, 0.0))
    assert g["R_sphere_nm"] == pytest.approx(10.0, rel=0.05)


def test_xps_survey_sulfur_ratio():
    import xps
    c = xps.survey_composition({"C1s": 1000.0, "O1s": 2930.0 * 0.5, "S2p": 1.68 * 20})
    assert c["O_C_ratio"][0] == pytest.approx(0.5) and c["S_C_ratio"][0] == pytest.approx(0.02)
    assert sum(v[0] for k, v in c.items() if k.endswith("_at_pct")) == pytest.approx(100)
