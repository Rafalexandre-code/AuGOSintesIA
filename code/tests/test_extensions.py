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
            "code/fingerprint", "tools/data_sources"):
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
    assert r["permutation"]["exact"] and r["permutation"]["n_permutations"] == 24 ** 3
    assert r["effect_GO_low_vs_high"] > 0 and r["permutation"]["p_two_sided"]["effect_GO_low_vs_high"] < 0.05
    rng = np.random.default_rng(0)                                   # sem efeito nenhum: p grandes em média
    df = pd.DataFrame([{"go": g, "imp": i, "block": b, "y": rng.normal()} for b in range(3) for g, i in factorial.CELLS])
    assert factorial.permutation_test(df)["p_two_sided"]["interaction"] > 0.01
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
