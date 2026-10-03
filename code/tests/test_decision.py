"""Testes de MISO (KG exato, MGP/ICM/PCM), do valor da informação (EVPI/EVSI) e da causal (IPW, mediação). Rodar:
.venvs/core/bin/python -m pytest code/tests -q
"""
import json
import os
import subprocess
import sys
import warnings

import numpy as np
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for sub in ("code/miso", "code/decision", "code/aunp_designer", "code/campaign", "code/sustainability", "code/causal"):
    sys.path.insert(0, os.path.join(ROOT, sub))
PY = sys.executable


def test_kg_exact_matches_monte_carlo():
    import miso
    rng = np.random.default_rng(1)
    for n in (2, 15, 60):
        a, b = rng.normal(size=n), rng.normal(size=n)
        a[: n // 3] = a[0]                                       # empates e retas dominadas
        z = rng.normal(size=300_000)
        mc = np.max(a[:, None] + b[:, None] * z[None], axis=0).mean() - a.max()
        assert miso.expected_max_affine(a, b) == pytest.approx(mc, abs=0.01)
    assert miso.expected_max_affine(np.array([1.0, 0.0]), np.zeros(2)) == 0.0   # sem incerteza, sem valor


def test_mgp_borrows_strength_from_cheap_source():
    """Fonte barata densa e correlacionada + 3 pontos da fonte-alvo: o MGP prevê o alvo melhor que o GP só-alvo."""
    import miso
    rng = np.random.default_rng(0)
    f0 = lambda u: np.sin(6 * u[:, 0]) + 0.5 * u[:, 1]          # noqa: E731
    Uc = rng.random((40, 2))
    Ut = np.array([[0.1, 0.2], [0.5, 0.8], [0.9, 0.4]])
    U = np.vstack([Ut, Uc])
    s = np.r_[np.zeros(3, int), np.ones(40, int)]
    y = np.r_[f0(Ut), f0(Uc) + 0.3 * Uc[:, 0] - 0.2]
    noise = np.array([1e-4, 1e-4])
    G = rng.random((200, 2))
    import torch
    err = {}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for kind in ("MGP", "ICM", "PCM", "TEM-only"):
            uu, ss, yy = (U, s, y) if kind != "TEM-only" else (Ut, np.zeros(3, int), f0(Ut))
            m = miso.build_model(kind, uu, ss, yy, noise, 2)
            with torch.no_grad():
                mu = m.posterior(torch.tensor(np.c_[G, np.zeros(len(G))])).mean.squeeze(-1).numpy()
            err[kind] = np.sqrt(np.mean((mu - f0(G)) ** 2))
    assert err["MGP"] < 0.5 * err["TEM-only"]
    assert err["ICM"] < err["TEM-only"]
    B = miso.pearson_matrix(U, s, y, 2)
    assert B[0, 1] > 0.5 and np.all(np.linalg.eigvalsh(B) > 0)          # só 3 pontos-alvo: correlação prevista


def test_lspr_inversion_is_blind_near_target():
    import miso
    big = miso.size_from_lspr(551.0)
    assert big == pytest.approx(80, rel=0.1)                     # partículas grandes: LSPR informa o tamanho
    small = [miso.size_from_lspr(x) for x in (522.9, 523.2, 523.5)]
    assert max(small) - min(small) < 8                           # perto de 20 nm, quase não distingue tamanhos


def test_miso_campaign_runs_within_budget():
    import miso
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        r = miso.run("MGP", seed=0, budget=70, n_candidates=24, n_init_cheap=4, n_init_target=2, max_iter=3)
    assert r["history"][-1]["cost"] <= 70 and r["final_regret"] >= 0
    assert sum(r["queries"].values()) == r["history"][-1]["n_obs"]


def test_evpi_evsi_match_analytic_quadratic():
    """U(a, θ) = −(a − θ)², θ ~ N(0, 1): EVPI = 1 e EVSI(σ) = 1/(1 + σ²)."""
    import voi
    rng = np.random.default_rng(0)
    a = np.linspace(-4, 4, 161)
    theta = rng.normal(size=(4000, 1))
    U = -(a[:, None] - theta[None, :, 0]) ** 2
    assert voi.evpi(U) == pytest.approx(1.0, abs=0.05)
    for sd in (0.5, 1.0, 2.0):
        e = voi.evsi(U, theta, [0], np.array([sd]), lambda k: rng.normal(size=(k, 1)), 1500, rng)
        assert e["evsi"] == pytest.approx(1 / (1 + sd ** 2), abs=4 * e["evsi_se"] + 0.02)
    assert voi.evsi(U, theta, [], np.array([1.0]), None)["evsi"] == 0.0
    rows = voi.best_subset({(): 0.0, ("XPS",): 0.5, ("Raman",): 0.1}, {"XPS": 400.0, "Raman": 50.0}, 1000.0)
    assert [r["techniques"] for r in rows] == [["XPS"], ["Raman"], []] and rows[0]["net_value"] == pytest.approx(100)


def test_voi_on_lab_and_sustainability_link(tmp_path):
    import designer
    import voi
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        designer.demo(str(tmp_path / "d"), iterations=1, q=2, seed=4)
        lab = str(tmp_path / "d" / "lab")
        res = voi.analyze(lab, n_actions=32, n_prior=400, n_outer=150)
    assert set(res["evsi_by_technique"]) == {"XPS", "Raman"}
    assert res["evpi"] >= 0 and res["evsi_all_techniques"] >= 0
    assert all(e["evsi"] <= res["evpi"] + 4 * e["evsi_se"] + 1e-9 for e in res["evsi_by_technique"].values())
    assert res["subsets"][0]["net_value"] >= res["subsets"][-1]["net_value"]
    out = tmp_path / "voi.json"
    out.write_text(json.dumps(res, default=float))
    r = subprocess.run([PY, os.path.join(ROOT, "code/sustainability/metrics.py"), "from-lab", lab, "--voi", str(out)],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr[-2000:]
    assert "caracterizacao_compensa" in r.stdout


def test_ipw_removes_confounding_continuous_and_binary():
    import pandas as pd
    import causal_analysis as ca
    rng = np.random.default_rng(3)
    n = 600
    x = rng.normal(size=n)                                             # contexto do lote (C/O)
    t = 0.8 * x + rng.normal(0, 0.6, n)                                # receita escolhida olhando o lote
    y = 2.0 * t + 3.0 * x + rng.normal(0, 0.5, n)
    df = pd.DataFrame({"C_O_ratio": x, "GO_mg_mL": t, "size_mean_nm": y})
    r = ca.ipw(None, "GO_mg_mL", "size_mean_nm", df=df, n_boot=100)
    assert r["covariates"] == ["C_O_ratio"]                            # pais do tratamento no DAG
    assert abs(r["effect_unadjusted"] - 2.0) > 1.0                     # ingênuo: muito viesado
    assert r["effect"] == pytest.approx(2.0, abs=0.35)
    assert abs(r["balance"][0]["corr_after"]) < 1e-6 and r["balance_ok"]      # balanço exato
    rp = ca.ipw(None, "GO_mg_mL", "size_mean_nm", df=df, n_boot=0, weights="propensity")
    assert abs(rp["effect"] - 2.0) < abs(r["effect_unadjusted"] - 2.0)           # clássico: corrige só em parte
    tb = (rng.random(n) < 1 / (1 + np.exp(-1.5 * x))).astype(float)
    yb = 1.0 * tb + 2.0 * x + rng.normal(0, 0.5, n)
    rb = ca.ipw(None, "GO_mg_mL", "size_mean_nm", df=pd.DataFrame({"C_O_ratio": x, "GO_mg_mL": tb,
                                                                   "size_mean_nm": yb}), n_boot=100)
    assert rb["estimand"] == "ATE" and rb["effect"] == pytest.approx(1.0, abs=0.35)
    assert abs(rb["balance"][0]["smd_after"]) < 0.01 < 0.25 < abs(rb["balance"][0]["smd_before"])
    lo, hi = rb["ci95_bootstrap"]
    assert lo < rb["effect"] < hi


def test_mediation_recovers_direct_and_indirect_effects():
    import pandas as pd
    import causal_analysis as ca
    rng = np.random.default_rng(5)
    n = 800
    t = rng.normal(size=n)
    m = 0.5 + 2.0 * t + rng.normal(0, 0.5, n)
    y = 1.0 + 0.5 * t + 1.5 * m + rng.normal(0, 0.5, n)
    df = pd.DataFrame({"C_O_ratio": t, "size_mean_nm": m, "spectral_loss_J": y})
    r = ca.mediation(None, "C_O_ratio", "size_mean_nm", "spectral_loss_J", df=df, n_boot=200)
    assert r["NIE"] == pytest.approx(3.0, abs=0.2) and r["NDE"] == pytest.approx(0.5, abs=0.15)
    assert r["NIE_ci95"][0] < 3.0 < r["NIE_ci95"][1] and r["treatment_induced_confounders"] == []
    y2 = 1.0 + 0.5 * t + 1.5 * m + 0.4 * t * m + rng.normal(0, 0.5, n)   # com interação T×M
    r2 = ca.mediation(None, "C_O_ratio", "size_mean_nm", "spectral_loss_J",
                      df=df.assign(spectral_loss_J=y2), n_boot=50)
    t0 = t.mean()
    assert r2["NDE"] == pytest.approx(0.5 + 0.4 * (0.5 + 2.0 * t0), abs=0.2)
    assert r2["NIE"] == pytest.approx(2.0 * (1.5 + 0.4 * (t0 + 1)), abs=0.3)
    df3 = df.assign(GO_mg_mL=0.3 * t + rng.normal(0, 1, n))           # receita: descendente do C/O e pai de M e Y
    r3 = ca.mediation(None, "C_O_ratio", "size_mean_nm", "spectral_loss_J", df=df3, n_boot=20)
    assert "GO_mg_mL" in r3["treatment_induced_confounders"] and "ATENÇÃO" in r3["interpretation"]
