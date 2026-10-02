"""Testes dos complementos ao núcleo: frente de Pareto no benchmark, subconjunto de TEM, fatorial 2×2, interações
(H de Friedman), correção de hardware. Rodar: .venvs/core/bin/python -m pytest code/tests -q
"""
import os
import sys
import warnings

import numpy as np
import pandas as pd
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for sub in ("code/campaign", "code/aunp_designer", "code/transfer_learning", "code/benchmarking", "code/spectral",
            "code/go_navigator", "code/qc", "code/characterization", "code/miso", "code/decision", "code/kinetics",
            "code/sustainability", "code/go_navigator", "tools/data_sources"):
    sys.path.insert(0, os.path.join(ROOT, sub))
warnings.filterwarnings("ignore")


def test_pareto_metrics_rank_dominating_front():
    import stats
    import campaign_sim as cs
    F_good = np.array([[0.0, 2.0], [1.0, 1.0], [2.0, 0.0]])
    F_bad = F_good + 1.0
    assert len(cs._pareto(np.vstack([F_good, F_bad]))) == 3
    ref = np.array([4.0, 4.0])
    front = cs._pareto(np.vstack([F_good, F_bad]))
    g, b = stats.hv_igd_spread(F_good, ref, front), stats.hv_igd_spread(F_bad, ref, front)
    assert g["hypervolume"] > b["hypervolume"] and g["igd"] < b["igd"] and g["igd"] == pytest.approx(0.0)


def test_tem_subset_spread_over_stages():
    import plan
    import prereg
    cfg = prereg.load()
    p = plan.generate(cfg=cfg)["plan"]
    t = p[(p["stage"] != "control") & (p["tem"] == "sim")]
    spec = cfg["tem_subset"]
    n_arms = len(prereg.arms(cfg)["prospective"])
    assert t["stage"].value_counts().to_dict() == {"pilot": spec["pilot"], "initialization": spec["initialization"],
                                                    "adaptive": spec["adaptive_rounds"] * n_arms,
                                                    "confirmation": spec["confirmation"]}
    ini = t[t["stage"] == "initialization"]
    assert ini["go_batch_id"].nunique() == len(cfg["batches"]["development"])
    assert t[t["stage"] == "adaptive"].groupby("round")["arm"].nunique().eq(n_arms).all()   # o par inteiro vai à TEM


def test_factorial_design_and_exact_analysis(tmp_path):
    import factorial
    import sim_lab
    syn = factorial.design("L1", "L3", "RED-A", "RED-B", replicates=3, role="reductant", seed=2)
    assert len(syn) == 12 and syn.groupby("block")["design_id"].apply(
        lambda s: s.str.extract(r"FAC:(\w+-\w+)")[0].nunique()).eq(4).all()     # bloco completo
    lab = str(tmp_path / "lab")
    sim_lab.init_lab(lab, ("L1", "L3"), seed=0)
    sim_lab.run_syntheses(lab, syn.assign(status="done"), np.random.default_rng(0))
    r = factorial.analyze(lab)
    assert r["permutation_sharp_null"]["exact"] and r["permutation_sharp_null"]["n_permutations"] == 24 ** 3
    go = r["main_effects_restricted_randomization"]["GO_low_vs_high"]
    assert go["exact"] and go["n_assignments"] == 64 and r["effect_GO_low_vs_high"] > 0 and go["p_two_sided"] < 0.05
    imp = r["main_effects_restricted_randomization"]["impurity"]
    lo, hi = sorted((go, imp), key=lambda t: t["p_two_sided"])
    assert lo["p_holm"] == pytest.approx(min(1, 2 * lo["p_two_sided"])) and hi["p_holm"] >= lo["p_holm"]
    rng = np.random.default_rng(0)                                   # sem efeito nenhum: p grandes em média
    df = pd.DataFrame([{"go": g, "imp": i, "block": b, "y": rng.normal()} for b in range(3) for g, i in factorial.CELLS])
    assert factorial.permutation_test(df)["p_two_sided"]["interaction"] > 0.01
    # efeito GRANDE de GO e nenhum de impureza: a randomização restrita mantém o nível do teste da impureza
    rej = []
    for k in range(300):
        y = rng.normal(0, 1, 12) + 5.0 * np.array([g == "low" for b in range(3) for g, _ in factorial.CELLS])
        dk = pd.DataFrame([{"go": g, "imp": i, "block": b} for b in range(3) for g, i in factorial.CELLS]).assign(y=y)
        rej.append(factorial.restricted_test(dk, "imp")["p_two_sided"] < 0.05)
    assert np.mean(rej) <= 0.07
    w = factorial._weights(df["go"].to_numpy(), df["imp"].to_numpy())
    c = factorial.contrasts(df)
    assert w[2] @ df["y"].to_numpy() == pytest.approx(c["interaction"])


def test_h_statistic_detects_interaction():
    import designer
    f = lambda Z: Z[:, 0] + Z[:, 1] + 2 * Z[:, 2] * Z[:, 3]          # noqa: E731
    X = np.random.default_rng(0).uniform(-1, 1, (40, 4))
    assert designer.h_statistic(f, X, 0, 1) == pytest.approx(0.0, abs=1e-9)
    assert designer.h_statistic(f, X, 2, 3) > 0.5


def test_hardware_linear_correction_recovers_offset():
    import hardware
    rng = np.random.default_rng(0)
    space = {"a": [0, 1], "b": [0, 1], "c": [0, 1]}
    f = lambda X: np.sin(3 * X[:, 0]) + X[:, 1] ** 2                # noqa: E731
    Xr, Xh = rng.random((30, 3)), rng.random((10, 3))
    df = pd.concat([pd.DataFrame(Xr, columns=list("abc")).assign(hardware="hot_plate", y=f(Xr) + rng.normal(0, .05, 30)),
                    pd.DataFrame(Xh, columns=list("abc")).assign(
                        hardware="flow_reactor", y=f(Xh) + 0.8 + 0.6 * (Xh[:, 2] - .5) + rng.normal(0, .05, 10))])
    r = hardware.fit(df, space, "y", n_boot=60)["platforms"]["flow_reactor"]
    assert r["offset"] == pytest.approx(0.8, abs=0.1) and r["offset_significant"]
    assert r["correction_improves"] and r["rmse_loo_corrected"] < 0.3 * r["rmse_loo_uncorrected"]



def test_neural_process_predicts_spectra_with_calibrated_band():
    import neural_process as npm
    import simulator as sim
    from scipy.stats import qmc
    import torch
    torch.manual_seed(0)
    rng = np.random.default_rng(0)
    keys = list(sim.SPACE)
    U = qmc.LatinHypercube(len(keys), seed=1).random(60)
    X, S, B = [], [], []
    for i, u in enumerate(U):
        b = ("L1", "L2", "L3")[i % 3]
        c = {k: lo + x * (hi - lo) for (k, (lo, hi)), x in zip(sim.SPACE.items(), u)}
        S.append(sim.simulate(c, b, rng=rng)["spectrum"])
        X.append([c[k] for k in keys] + [sim.BATCHES[b]["C_O_ratio"]])
        B.append(b)
    X, S, B = np.array(X), np.array(S), np.array(B)
    bounds = np.vstack([[sim.SPACE[k][0] for k in keys] + [1.4], [sim.SPACE[k][1] for k in keys] + [2.3]])
    m = npm.SpectralNP(sim.WL, dz=4, hidden=64).fit(S, steps=800)
    assert np.sqrt(np.mean((m.reconstruct(S) - S) ** 2)) < 0.5 * S.std()
    tr, te = B != "L2", B == "L2"                                     # lote do meio: interpolação de contexto
    cm = npm.ConditionalSpectralModel(m, bounds).fit(X[tr], S[tr])
    p = cm.predict(X[te], n_samples=100)
    assert np.sqrt(np.mean((p["mean"] - S[te]) ** 2)) < np.sqrt(np.mean((S[tr].mean(0) - S[te]) ** 2))
    cover = np.mean((S[te] >= p["q05"]) & (S[te] <= p["q95"]))
    assert 0.5 < cover <= 1.0
    with pytest.warns(UserWarning, match="estudo computacional"):
        d = npm.inverse_design(cm, sim.target_spectrum(), 0.02, "max", fixed={6: 2.2}, n_starts=4, steps=20,
                               n_train=len(S), X_obs=X[tr], y_obs=np.arange(tr.sum(), dtype=float))
    assert np.all(d["x"] >= bounds[0] - 1e-6) and np.all(d["x"] <= bounds[1] + 1e-6) and d["x"][6] == pytest.approx(2.2)


def test_miso_proposes_from_lab_tables(tmp_path):
    import designer
    import miso
    lab = str(tmp_path / "d")
    designer.demo(lab, iterations=1, q=2, seed=4)
    r = miso.propose_from_lab(os.path.join(lab, "lab"), "PCM", n_candidates=64, top=3)
    assert r["n_observations"]["TEM"] > 0 and r["n_observations"]["UV-Vis"] > 0
    assert len(r["next_queries"]) == 3 and all(q["technique"] in r["noise_var"] for q in r["next_queries"])
    rec = r["recommendation_confirmed"]
    syn = pd.read_csv(os.path.join(lab, "lab", "aunp_syntheses.csv"))
    assert np.isclose(syn["HAuCl4_mM"], rec["HAuCl4_mM"]).any()          # confirmada = um ponto já medido por TEM


def test_kinetics_identifiability_and_stop_rule():
    import kinetics as kin
    rng = np.random.default_rng(0)
    t = np.linspace(0, 600, 120)
    theta = [np.log10(2e-4), np.log10(0.03), 0.8, 0.02]
    r = kin.check(t, kin.model(t, theta) + rng.normal(0, 0.005, t.size), n_recovery=6)
    assert r["interpretable"] and r["positivity"] and r["conservation_max_error"] < 1e-8
    assert np.log10(r["fit"]["k1"]) == pytest.approx(theta[0], abs=0.3) and np.log10(r["fit"]["k2"]) == pytest.approx(theta[1], abs=0.2)
    t2 = np.linspace(400, 600, 40)                                          # só o platô: nada a identificar
    r2 = kin.check(t2, kin.model(t2, theta) + rng.normal(0, 0.005, t2.size), n_recovery=5)
    assert not r2["interpretable"] and r2["stop_reasons"]


def test_batch_fingerprint_autoencoder_and_pca_fallback():
    import fingerprint as fpm
    s = np.linspace(-1, 1, 24)                                              # 24 lotes numa variedade 1D
    mean = pd.DataFrame({"C_O_ratio": 2 + 0.4 * s, "ID_IG": 1 + 0.1 * s ** 2, "d001_nm": 0.8 + 0.05 * np.sin(2 * s)},
                        index=[f"B{i}" for i in range(24)])
    sd = mean * 0 + 0.01
    fp, info = fpm.fingerprint(mean, sd, latent=1, epochs=800)
    assert info["method"] == "autoencoder" and abs(np.corrcoef(fp["fp1"], s)[0, 1]) > 0.95
    with pytest.warns(UserWarning, match="PCA"):
        fp2, info2 = fpm.fingerprint(mean.iloc[:4], sd.iloc[:4], latent=1)
    assert info2["method"] == "PCA" and len(fp2) == 4


def test_exploratory_strategies_and_sustainability_extensions(tmp_path):
    import designer
    import metrics
    import strategies
    lab = str(tmp_path / "d")
    designer.demo(lab, iterations=1, q=2, seed=4)
    lab = os.path.join(lab, "lab")
    space = designer.DEFAULT_SPACE
    camp = designer.load_campaign(lab, space, "go", designer.default_logs(), designer.default_eps(),
                                  constraints=designer.default_constraints())
    fixed = designer.fixed_context(lab, camp, "L2", {"reductant": "RED-A"})
    for f in (strategies.propose_optuna_tpe, strategies.propose_dnn_qnehvi):
        c = f(camp, space, 2, fixed, 0)
        assert c.shape == (2, camp.X.shape[1]) and np.allclose(c["ctx_C_O_ratio"], fixed["ctx_C_O_ratio"])
    c = strategies.propose_egbo(camp, space, 2, fixed, 0, pop=16, gens=3, n_sobol=64)
    assert all(c[k].between(lo - 1e-9, hi + 1e-9).all() for k, (lo, hi) in space.items())
    assert metrics.capital_recovery_factor(0.0, 10) == pytest.approx(0.1)
    co = metrics.capex_opex({"discount_rate": 0.0, "instruments": {"X": {"capex": 1000, "lifetime_years": 10,
                             "maintenance_per_year": 0, "analyses_per_year": 100}}, "consumables_per_analysis": {"X": 2}})
    assert co["X"]["capex_per_analysis"] == pytest.approx(1.0) and co["X"]["total_per_analysis"] == pytest.approx(3.0)
    g = metrics.complexgapi({"yield_pct": 95, "solvent": "ethanol", "time_min": 500},
                            {"yield_pct": {"type": "numeric", "green_min": 89, "yellow_min": 70},
                             "solvent": {"type": "categorical", "green": ["water"], "yellow": ["ethanol"]},
                             "time_min": {"type": "numeric_max", "green_max": 60, "yellow_max": 240},
                             "purification": {"type": "categorical", "green": ["none"]}})
    assert g["pictogram"] == "GYR-" and g["counts"] == {"green": 1, "yellow": 1, "red": 1}


def test_sizing_scenarios_and_report(tmp_path):
    """Fatorial ponta a ponta, resumos dos cenários de dimensionamento e o relatório."""
    import json
    import campaign_sim as cs
    row = cs.run_factorial("null-r3", 0, str(tmp_path))[0]
    assert 0 < row["p_imp"] <= 1 and 0 < row["p_go"] <= 1 and np.isfinite(row["eff_int"])
    cv = pd.DataFrame([{**row, "seed": s} for s in range(3)])
    fac = cs.summarize_factorial(cv)
    bat = cs.summarize_batches(pd.DataFrame([{"arm": "contextual-K6", "seed": s, "n": 6, "p_batch": p,
                                              "batch_ratio": 0.9, "batch_d": [-0.1] * 6, "best_loss": 1.0}
                                             for s, p in enumerate((0.01, 0.2, 0.03))]))
    assert bat["rows"]["contextual-K6"]["rejection"] == pytest.approx(2 / 3)
    for name, s in (("factorial", fac), ("batches", bat)):
        os.makedirs(tmp_path / "out" / name)
        with open(tmp_path / "out" / name / "summary.json", "w") as fh:
            json.dump(s, fh, default=float)
    md = cs.report(str(tmp_path / "out"))
    assert "Fatorial 2×2" in md and "Mais lotes de GO" in md and "| 6 |" in md
