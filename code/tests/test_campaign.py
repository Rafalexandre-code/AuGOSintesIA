"""Testes do planejamento da campanha e das extensões do Designer (pré-registro, plano experimental, restrições,
GP hierárquico, noise-check, métrica de transferência). Rodar: .venvs/core/bin/python -m pytest code/tests -q
"""
import os
import shutil
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for sub in ("code/campaign", "code/aunp_designer", "code/transfer_learning", "code/spectral", "code/benchmarking",
            "code/go_navigator", "tools/data_sources"):
    sys.path.insert(0, os.path.join(ROOT, sub))


# ------------------------------------------------------------------ pré-registro

def test_prereg_loads_and_target_spectrum():
    import prereg
    import uvvis
    cfg = prereg.load()
    w, e = prereg.target_spectrum(cfg)
    assert w[0] == 400 and w[-1] == 800
    assert 518 <= uvvis.lspr(w, e)["LSPR_nm"] <= 526          # AuNP de 20 nm em água
    assert "time_min" in prereg.search_space(cfg)              # Tabela 1: tempo é variável de decisão
    assert prereg.spectral_loss(w, e, cfg) == pytest.approx(0.0, abs=1e-12)


def test_prereg_freeze_check_amend(tmp_path):
    import prereg
    import yaml
    p, lock = tmp_path / "pr.yaml", tmp_path / "pr.lock.json"
    shutil.copy(prereg.DEFAULT_PATH, p)
    assert prereg.check(str(p), str(lock))["state"] == "draft"
    prereg.freeze(str(p), str(lock))
    assert prereg.check(str(p), str(lock))["state"] == "frozen_ok"
    cfg = yaml.safe_load(open(p))
    cfg["loss"]["epsilon"]["value"] = 0.123                   # aplicação da regra do piloto: não viola
    yaml.safe_dump(cfg, open(p, "w"), allow_unicode=True)
    assert prereg.check(str(p), str(lock))["state"] == "frozen_ok"
    cfg["relevance_threshold"] = 0.10                          # mudança de decisão sem emenda: violação
    yaml.safe_dump(cfg, open(p, "w"), allow_unicode=True)
    assert prereg.check(str(p), str(lock))["state"] == "violated"
    cfg["amendments"] = [{"date": "2026-10-01", "change": "limiar 10 %", "reason": "teste", "before_unblinding": True}]
    yaml.safe_dump(cfg, open(p, "w"), allow_unicode=True)
    assert prereg.check(str(p), str(lock))["state"] == "amended"


def test_prereg_rejects_inconsistent_plan():
    import copy
    import prereg
    cfg = copy.deepcopy(prereg.load())
    cfg["batches"]["reserved"] = ["L1"]
    with pytest.raises(prereg.PreregError):
        prereg.validate(cfg)


# ------------------------------------------------------------------ plano experimental

def test_plan_budget_blocks_and_controls():
    import plan
    import prereg
    cfg = prereg.load()
    res = plan.generate(cfg=cfg)
    p, bud = res["plan"], cfg["budget"]
    counted = p[p["stage"] != "control"]
    assert len(counted) == 60
    assert counted["stage"].value_counts().to_dict() == {s: int(bud[s]) for s in prereg.STAGES}
    reserved = set(cfg["batches"]["reserved"])
    assert set(counted[counted["stage"] == "confirmation"]["go_batch_id"]) == reserved
    assert not reserved & set(counted[counted["stage"] != "confirmation"]["go_batch_id"])
    init = counted[counted["stage"] == "initialization"]
    per_day = init.groupby(["day", "go_batch_id"]).size().unstack(fill_value=0)
    assert (per_day.max(axis=1) - per_day.min(axis=1)).max() <= 1        # lote não se confunde com dia
    assert init.drop_duplicates(list(res["space"])).shape[0] == int(bud["initialization"]) // len(cfg["batches"]["development"])
    for _, g in p.groupby("day"):
        assert sorted(g["run_order"]) == list(range(1, len(g) + 1))
    assert {"no_GO", "GO_blank"} <= set(p["is_control"])
    v = p[[c for c in p.columns if c.startswith("V_")]].apply(pd.to_numeric, errors="coerce")
    assert (v.fillna(0) >= 0).all().all()


def test_maximin_beats_plain_lhs():
    from scipy.spatial.distance import pdist
    from scipy.stats import qmc
    import plan
    import prereg
    space = prereg.search_space()
    _, d = plan.maximin_lhs(space, 4, seed=1, tries=300)
    plain = [pdist(qmc.LatinHypercube(len(space), seed=s).random(4)).min() for s in range(50)]
    assert d >= np.median(plain)


def test_plan_rows_pass_validator(tmp_path):
    import lab_data_model
    import plan
    res = plan.generate()
    syn = plan.to_syntheses(res["plan"], res["space"], lots={"gold": "LOT-AU", "reductant": "LOT-RED"})
    syn.to_csv(tmp_path / "aunp_syntheses.csv", index=False)
    assert lab_data_model.validate(str(tmp_path)) == 0


# ------------------------------------------------------------------ Designer: restrições, hierárquico, ruído

@pytest.fixture(scope="module")
def lab(tmp_path_factory):
    import designer
    out = tmp_path_factory.mktemp("demo_campaign")
    designer.demo(str(out), iterations=2, q=2, seed=2)
    return str(out / "lab")


def test_constraints_enter_acquisition(lab):
    import designer
    space = designer.DEFAULT_SPACE
    camp = designer.load_campaign(lab, space, "go", designer.default_logs(), designer.default_eps(),
                                  constraints=designer.default_constraints())
    assert set(camp.cons) == {"size_cv", "A_LSPR"} and camp.C.shape == (len(camp.X), 2)
    c = designer.propose(camp, space, q=2, fixed=designer.fixed_context(lab, camp, "L1", None), seed=0)
    assert c["p_feasible"].between(0, 1).all()
    assert c.attrs["acq"] == "qnehvi"                          # padrão da proposta


def test_hierarchical_new_batch_and_lbo(lab):
    import designer
    import hierarchical
    space = designer.DEFAULT_SPACE
    camp = designer.load_campaign(lab, space, "hierarchical", designer.default_logs(), designer.default_eps())
    fx_new = designer.fixed_context(lab, camp, "L5", None)
    assert fx_new["lvl_batch"] == max(camp.level_maps["lvl_batch"].values()) + 1
    c = designer.propose(camp, space, q=2, fixed=fx_new, seed=1)
    assert len(c) == 2
    model, *_ = designer.build_model(camp, space)
    sh = hierarchical.variance_shares(model.models[0])
    assert sum(sh.values()) == pytest.approx(1.0) and set(sh) == {"global", "nivel_1"}
    res = designer.validate_lbo(lab, space, ("hierarchical",), designer.default_logs(), designer.default_eps())
    assert res["rmse"].notna().all() and res["coverage95"].between(0, 1).all()


def test_noise_check_rule(lab):
    import designer
    r = designer.noise_check(lab, designer.DEFAULT_SPACE)
    assert r["recommended_acq"] in ("qnehvi", "qlognehvi")
    assert r["recommended_acq"] == ("qlognehvi" if r["heteroscedastic"] else "qnehvi")


def test_confirmation_never_trains(lab, tmp_path):
    import designer
    syn = pd.read_csv(os.path.join(lab, "aunp_syntheses.csv"))
    shutil.copytree(lab, tmp_path / "lab")
    syn.loc[syn.index[:3], "campaign_id"] = "CONFIRMATION"
    syn.to_csv(tmp_path / "lab" / "aunp_syntheses.csv", index=False)
    used = designer.usable_syntheses(str(tmp_path / "lab"))
    assert not (used["campaign_id"] == "CONFIRMATION").any()
    assert len(designer.usable_syntheses(str(tmp_path / "lab"), include_confirmation=True)) == len(used) + 3


# ------------------------------------------------------------------ métrica de transferência

def test_experiments_to_match():
    import hierarchical as H
    assert H.experiments_to_threshold([5, 4, 3, 2], 3) == 3
    assert H.experiments_to_threshold([5, 4], 1) == float("inf")
    km = H.censored_mean(np.array([2.0, 4.0, np.inf]), budget=10)
    assert km["fraction_reached"] == pytest.approx(2 / 3)
    assert km["rmst"] == pytest.approx(2 + 2 * (2 / 3) + 6 * (1 / 3))      # área sob a curva de sobrevivência
    scratch = np.array([[9, 7, 5, 4, 3], [8, 6, 5, 4, 3]], float)
    transfer = np.array([[4, 3, 3, 2, 2], [5, 3, 2, 2, 2]], float)
    r = H.experiments_to_match(transfer, scratch, scratch_budget=5)
    assert r["reference_performance"] == 3 and r["relative_saving"] > 0.4


# ------------------------------------------------------------------ comparação prospectiva pareada (§4.18)

def test_plan_pairs_arms_by_round():
    import plan
    import prereg
    cfg = prereg.load()
    arms = prereg.arms(cfg)["prospective"]
    p = plan.generate(cfg=cfg)["plan"]
    ad = p[p["stage"] == "adaptive"]
    assert ad["arm"].value_counts().to_dict() == {a: int(cfg["budget"]["adaptive"]) // len(arms) for a in arms}
    per = ad.groupby("round").agg(n=("arm", "size"), arms=("arm", "nunique"), days=("day", "nunique"),
                                  batches=("go_batch_id", "nunique"))
    assert (per["n"] == len(arms)).all() and (per["arms"] == len(arms)).all()
    assert (per["days"] == 1).all() and (per["batches"] == 1).all()     # mesmo dia e mesmo lote no par


def test_prereg_rejects_bad_arms():
    import copy
    import prereg
    cfg = copy.deepcopy(prereg.load())
    cfg["arms"]["prospective"] = ["recipe", "nao_existe"]
    with pytest.raises(prereg.PreregError):
        prereg.validate(cfg)
    cfg = copy.deepcopy(prereg.load())
    cfg["arms"]["prospective"] = ["recipe", "go", "hierarchical", "batch", "go+impurities"]   # 24 não divide por 5
    with pytest.raises(prereg.PreregError):
        prereg.validate(cfg)


def test_arm_filter_keeps_trajectories_independent(lab, tmp_path):
    import designer
    work = tmp_path / "lab"
    shutil.copytree(lab, work)
    syn = pd.read_csv(work / "aunp_syntheses.csv")
    syn["design_id"] = syn["design_id"].astype(object)
    adapt = syn.index[syn["campaign_id"].astype(str).str.startswith("SIM")]
    half = len(adapt) // 2
    syn.loc[adapt[:half], "design_id"] = "recipe:it01-q1"
    syn.loc[adapt[half:], "design_id"] = "go+impurities:it01-q1"
    syn.to_csv(work / "aunp_syntheses.csv", index=False)
    n_all = len(designer.usable_syntheses(str(work)))
    a = set(designer.usable_syntheses(str(work), arm="recipe")["synthesis_id"])
    b = set(designer.usable_syntheses(str(work), arm="go+impurities")["synthesis_id"])
    shared = a & b
    assert len(a) + len(b) - len(shared) == n_all and len(a - b) == half and len(b - a) == len(adapt) - half
    assert designer.arm_of("go+impurities:it03-q1") == "go+impurities" and designer.arm_of("D05-02") == ""


def test_randomization_analysis_exact_and_calibrated():
    import analysis
    from scipy.stats import wilcoxon
    rng = np.random.default_rng(1)
    d = rng.normal(-0.3, 0.5, 12)
    assert analysis.sign_flip_test(d) == analysis.sign_flip_test(d[::-1])           # exato: não depende da ordem
    assert abs(analysis.sign_flip_test(d) - wilcoxon(d, alternative="less").pvalue) < 0.02
    f = np.cumsum(analysis._signed_rank_null(12))
    assert f[13] <= 0.025 < f[14]                                  # valor crítico tabelado: n = 12 → 13
    cover = np.mean([(lambda h: h["ci"][0] <= 0.2 <= h["ci"][1])(analysis.hodges_lehmann(rng.normal(0.2, 1, 12)))
                     for _ in range(600)])
    assert 0.92 <= cover <= 0.99
    alpha = np.mean([analysis.sign_flip_test(rng.normal(0, 1, 10)) < 0.05 for _ in range(600)])
    assert alpha <= 0.07
    long = pd.DataFrame({"arm": ["recipe", "go", "recipe", "go", ""], "round": [1, 1, 2, 2, None],
                         "go_batch_id": ["L1", "L1", "L2", "L2", "L1"], "value": [2.0, 1.0, 4.0, 1.0, 3.0]})
    pr = analysis.paired_differences(long, "recipe", "go", 0.0)
    assert np.allclose(pr["d"], [np.log(0.5), np.log(0.25)])
    cur = analysis.cumulative_curves(long, ["recipe", "go"], ["L1", "L2"]).set_index(["arm", "round"])
    assert cur.loc[("go", 2), "best_loss_balanced"] == pytest.approx(1.0)
    assert np.isnan(cur.loc[("recipe", 0), "best_loss_balanced"]) or cur.loc[("recipe", 0), "n_batches_with_data"] == 1
