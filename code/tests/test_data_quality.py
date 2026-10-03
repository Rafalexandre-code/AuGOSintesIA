"""Testes de qualidade e rastreabilidade: QC automático, sustentabilidade a partir das tabelas, Instance Map,
auditoria da extração da literatura. Rodar: .venvs/core/bin/python -m pytest code/tests -q
"""
import os
import shutil
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for sub in ("code/qc", "code/sustainability", "code/aunp_designer", "code/campaign", "code/spectral",
            "code/benchmarking", "tools/data_sources"):
    sys.path.insert(0, os.path.join(ROOT, sub))


@pytest.fixture(scope="module")
def lab(tmp_path_factory):
    import designer
    out = tmp_path_factory.mktemp("demo_quality")
    designer.demo(str(out), iterations=1, q=2, seed=4)
    return str(out / "lab")


def test_qc_passes_clean_data_and_catches_problems(lab, tmp_path):
    import qc_check
    res, _ = qc_check.run(lab)
    assert not (res["status"] == "fail").any()
    assert (res.loc[res["check"] == "uvvis_duplicate_reads", "status"] == "pass").all()
    bad = tmp_path / "lab"
    shutil.copytree(lab, bad)
    syn = pd.read_csv(bad / "aunp_syntheses.csv")
    syn["preparation_id"] = syn["preparation_id"].astype(object)
    syn.loc[[0, 1], "preparation_id"] = "PREP-X"                     # alíquota contada como duas sínteses
    syn.to_csv(bad / "aunp_syntheses.csv", index=False)
    sp = pd.read_csv(bad / "spectra.csv")
    f = bad / sp.loc[0, "file"]
    d = np.loadtxt(f, delimiter=",", skiprows=1)
    d[:, 1] *= 20                                                     # saturação
    np.savetxt(f, d, delimiter=",", header="wavelength_nm,absorbance", comments="")
    res2, _ = qc_check.run(str(bad))
    fails = set(res2.loc[res2["status"] == "fail", "check"])
    assert {"independent_preparation", "uvvis_absorbance_range"} <= fails
    res2.to_csv(bad / "qc_results.csv", index=False)
    import designer
    used = designer.usable_syntheses(str(bad))
    assert not set(used["synthesis_id"]) & set(res2.loc[res2["status"] == "fail", "synthesis_id"])


def test_control_chart_flags_drift():
    import qc_check
    crit = qc_check.load_criteria()
    n = 12
    syn = pd.DataFrame({"synthesis_id": [f"C{i}" for i in range(n)], "is_control": "no_GO",
                        "block": [f"DAY{i:02d}" for i in range(n)], "run_order": 1,
                        "date": [f"2026-01-{i + 1:02d}" for i in range(n)]})
    lspr = [520.0, 520.4, 519.7, 520.2, 519.8] + [520.0 + 0.6 * k for k in range(1, 8)]   # deriva lenta
    char = pd.DataFrame({"synthesis_id": syn["synthesis_id"], "quantity": "LSPR_nm", "value": lspr})
    cc = qc_check.control_chart(syn, char, crit)
    assert cc.loc[cc["phase"] == "II", "ewma_out"].any()


def test_sustainability_from_lab(lab):
    import metrics
    fl = metrics.flows_from_lab(lab)
    a, b = fl["sem_caracterizacao_adicional"], fl["com_caracterizacao_adicional"]
    assert b["cost"] > a["cost"] > 0 and a["product_g"] > 0
    assert 0 < a["sEF"] < a["cEF"]                                   # sEF exclui a água
    d = metrics.decide_characterization(fl, delta_loss=10.0, delta_uncertainty=0.0, lam=1.0, value_per_unit=1e6)
    assert d["caracterizacao_compensa"] is True
    d2 = metrics.decide_characterization(fl, delta_loss=1e-6, delta_uncertainty=0.0, lam=1.0, value_per_unit=1.0)
    assert d2["caracterizacao_compensa"] is False


def test_instance_map_rocrate_and_integrity(lab, tmp_path):
    import instance_map as im
    g = im.build(lab)
    assert not [i for i in g.issues if i["level"] == "error"]
    crate = im.to_rocrate(g, lab)
    ids = {e["@id"] for e in crate["@graph"]}
    assert "./" in ids and "ro-crate-metadata.json" in ids
    files = [e for e in crate["@graph"] if isinstance(e.get("@type"), list) and "File" in e["@type"]]
    assert files and all(len(f["sha256"]) == 64 for f in files)
    sid = pd.read_csv(os.path.join(lab, "aunp_syntheses.csv"))["synthesis_id"].iloc[-1]
    mer = im.lineage(g, sid)
    assert mer.startswith("graph LR") and "wasGeneratedBy" in mer
    broken = tmp_path / "lab"
    shutil.copytree(lab, broken)
    os.remove(broken / pd.read_csv(broken / "spectra.csv")["file"].iloc[0])
    assert any("ausente" in i["message"] for i in im.build(str(broken)).issues)


def test_seed_size_parser_ignores_uncertainty_and_fringes():
    import build_literature_seed as b
    assert b.size_values("61 ± 6, 17 ± 2") == [61.0, 17.0]
    assert b.size_values("0.24, 0.34") == []                         # franjas de rede, não tamanho
    assert b.size_values("10-20") == [15.0]
    seed = pd.read_csv(os.path.join(ROOT, "datasets/literature-seed/aunp_literature_seed.csv"), dtype=str)
    s = pd.to_numeric(seed.loc[seed["source"] == "cruse2022", "size_nm"], errors="coerce")
    assert (s.dropna() >= 1).all()


def test_audit_statistics_and_physics():
    import audit_extraction as ae
    lo, hi = ae.wilson(8, 10)
    assert lo < 0.8 < hi and 0 <= lo and hi <= 1
    assert ae.cohen_kappa([1, 1, 0, 0], [1, 1, 0, 0]) == pytest.approx(1.0)
    seed = pd.DataFrame([
        {"seed_id": "a", "source": "x", "doi": "", "product": "Au nanoparticles", "morphology_class": "sphere",
         "size_nm": "20", "abs_peak_nm": "522", "size_text": "", "abs_peak_text": ""},
        {"seed_id": "b", "source": "x", "doi": "", "product": "Au nanoparticles", "morphology_class": "sphere",
         "size_nm": "20", "abs_peak_nm": "640", "size_text": "", "abs_peak_text": ""},
        {"seed_id": "c", "source": "x", "doi": "", "product": "Au@Ag core-shell", "morphology_class": "sphere",
         "size_nm": "20", "abs_peak_nm": "640", "size_text": "", "abs_peak_text": ""}])
    df = ae.physics_audit(seed).set_index("seed_id")
    assert df.loc["a", "flags"] == "" and "pico_incoerente_com_tamanho" in df.loc["b", "flags"]
    assert "c" not in df.index                                        # núcleo-casca não é testado por Mie de Au
    sheet = pd.DataFrame({"field": ["size_nm"] * 4, "extracted_empty": [0, 0, 0, 1], "correct": ["1", "1", "0", ""],
                          "present_in_source": ["", "", "", "1"], "correct_2": ["", "", "", ""],
                          "stratum_size": [10, 10, 10, 5], "source": "x", "confidence": "high"})
    sc = ae.score(sheet)["por_campo"]["size_nm"]
    assert sc["precisao"] == pytest.approx(2 / 3) and sc["ausencia_falsa"] == 1.0


def test_data_model_has_new_tables():
    import lab_data_model as m
    assert {"resources", "qc_results"} <= set(m.TABLES)
    dd = pd.read_csv(os.path.join(ROOT, "datasets/data-model/data_dictionary.csv"))
    assert {"resources", "qc_results"} <= set(dd["table"])
