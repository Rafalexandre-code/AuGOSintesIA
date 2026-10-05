"""Site AuGOSintesIA (code/webapp): só dados experimentais, GP exportado = posterior do GPyTorch, J igual ao do
pré-registro, e os dados versionados em site/data/ completos e coerentes."""
import json
import os
import re
import sys

import numpy as np
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "code", "webapp"))
import analyses  # noqa: E402
import build_site  # noqa: E402
import expdata  # noqa: E402


def test_so_dados_experimentais():
    lit = expdata.literature()
    assert set(lit["source"]) <= set(expdata.SOURCES) and len(lit) > 10_000
    for name, spec in expdata.BENCHMARKS.items():
        assert os.path.exists(os.path.join(expdata.BOCODE, spec[0])), name
        assert expdata.benchmark_size(name) >= 100
    # nenhum gerador do simulador ou de dados sintéticos é importado pelo site
    src = "".join(open(os.path.join(ROOT, "code", "webapp", f), encoding="utf-8").read()
                  for f in ("expdata.py", "analyses.py", "build_site.py"))
    for bad in ("simulator", "sim_lab", "campaign_sim", "calibrate", "RAMBOAU", "make_synthetic", "miso"):
        assert not re.search(rf"\b(import|from)\s+\S*{bad}", src), bad


def test_gp_exportado_igual_ao_posterior():
    import torch
    raw, u = expdata.agnp()
    cols = list(raw.columns[:-1])
    X = u[cols].to_numpy(float)[:60]
    Xn = (X - X.min(0)) / (X.max(0) - X.min(0))
    y = np.log(u["mean"].to_numpy(float))[:60]
    m = analyses._gp_fit(Xn, y)
    gp = json.loads(json.dumps(analyses._gp_export(m, Xn)))           # como o site recebe (JSON)
    Xq = np.random.default_rng(0).random((25, Xn.shape[1]))
    mu, sd = analyses.gp_predict(gp, Xq)
    with torch.no_grad():
        p = m.posterior(torch.tensor(Xq, dtype=torch.double))
    assert np.allclose(mu, p.mean.numpy().ravel(), atol=1e-5)
    assert np.allclose(sd, p.variance.sqrt().numpy().ravel(), rtol=1e-3, atol=1e-6)


def test_pico_parabolico():
    w = np.arange(400.0, 901.0, 2.0)
    for c in (517.3, 530.9, 601.1):
        e = np.exp(-0.5 * ((w - c) / 25) ** 2)
        assert abs(analyses._peak(w, e) - c) < 0.05


def _js_ensemble_J(opt: dict, d: float, s: float) -> float:
    """Porta para numpy do que app.js faz na aba Óptica (ensemble log-normal na grade + Eq. 1)."""
    wl, dg = np.array(opt["wl"]), np.array(opt["d"])
    C = np.array(opt["C_ext"]) * np.array(opt["C_ext_max"])[:, None]
    sl = np.sqrt(np.log(1 + s * s))
    w = np.exp(-0.5 * ((np.log(dg) - (np.log(d) - sl * sl / 2)) / sl) ** 2)
    E = (w / w.sum()) @ C
    tg = opt["target"]
    g = np.arange(tg["grid"][0], tg["grid"][1] + 1e-9, tg["grid"][2])
    e, t = np.interp(g, wl, E), np.interp(g, tg["wl"], tg["E"])
    return float(np.mean(((e / e.max() - t / t.max()) / tg["s_m"]) ** 2))


@pytest.fixture(scope="module")
def site():
    if not os.path.exists(os.path.join(build_site.SITE, "data", "overview.js")):
        pytest.skip("site/ não gerado (python code/webapp/build_site.py)")
    return {s: build_site._read(s) for s in ["overview"] + build_site.SECTIONS}


def test_dados_do_site_completos(site):
    for s, d in site.items():
        assert d, s
    assert len(site["overview"]["map"]) == 18
    assert {m["status"] for m in site["overview"]["map"]} <= {"experimental", "parcial", "laboratorio"}
    k = site["overview"]["kpis"]
    assert k["literature_records"] == site["literature"]["n"] and k["agnp_measurements"] == 3295
    txt = "".join(open(os.path.join(build_site.SITE, "data", f"{s}.js"), encoding="utf-8").read() for s in site)
    assert "SIMULADO" not in txt and "NaN" not in txt
    html = open(os.path.join(build_site.SITE, "index.html"), encoding="utf-8").read()
    for s in ["overview"] + build_site.SECTIONS:
        assert f'src="data/{s}.js"' in html
    assert os.path.exists(os.path.join(build_site.SITE, "vendor", "plotly.min.js"))


def test_gp_do_site_e_cv(site):
    D = site["designer"]
    Xn = (np.array(D["points"]["X"]) - D["lo"]) / (np.array(D["hi"]) - D["lo"])
    mu, _ = analyses.gp_predict(D["gp"], Xn)
    y = np.log(D["points"]["mean"])
    assert np.corrcoef(mu, y)[0, 1] > 0.95                              # ajuste no treino
    assert D["cv"]["r2"] > 0.8 and 0.85 <= D["cv"]["coverage95"] <= 1.0
    assert all(s["lo"] <= s["pred_loss"] <= s["hi"] for s in D["suggestions"])


def test_J_do_navegador_igual_ao_preregistro(site):
    sys.path[:0] = [os.path.join(ROOT, "code", d) for d in ("spectral", "campaign")]
    import mie
    import prereg
    import uvvis
    opt = site["optics"]
    cfg = prereg.load()
    tw, te = prereg.target_spectrum(cfg)
    grid, sm = prereg.grid(cfg), float(np.mean(prereg.s_m(cfg)))
    assert _js_ensemble_J(opt, opt["target"]["diameter"], opt["target"]["sigma"]) < 0.05      # no alvo, J ≈ 0
    for d, s in ((12.0, 0.10), (35.0, 0.15)):
        ref = uvvis.spectral_loss_J(grid, mie.ensemble_extinction(grid, d, s), tw, te, s=sm, grid=grid, norm="max")
        assert 0.6 < _js_ensemble_J(opt, d, s) / ref < 1.6                      # discretizações diferentes do ensemble
    assert opt["lit_spheres"]["n"] > 500 and opt["lit_spheres"]["median_abs_residual"] < 8


def test_xrd_e_causal(site):
    g = site["xrd"]["geometry"]
    assert g["n_rings"] >= 10 and g["rms_residual_px"] < 0.5 and 40 < g["energy_keV"] < 120
    assert all(abs(r["resid_px"]) < 1 for r in site["xrd"]["rings"] if r["resid_px"] is not None)
    C = site["causal"]
    assert C["ratio_ci95"][0] < C["ratio"] < C["ratio_ci95"][1] and C["e_value"] > 1
    assert max(abs(v) for v in C["smd_after"]) < 0.1


def test_benchmark_pareado(site):
    B = site["benchmark"]
    for name, ds in B["datasets"].items():
        for a in B["arms"][1:]:
            pr = ds["paired"][a]
            assert pr["wins"] + pr["ties"] + pr["losses"] == B["seeds"], (name, a)
            assert 0 <= pr["p"] <= 1
        assert all(1 <= m <= ds["budget"] + 1 for m in ds["median_censored"].values())
    # recalcular a partir das sementes dá o mesmo resultado (idempotente)
    again = analyses.add_paired_stats(json.loads(json.dumps(B)))
    assert again["datasets"]["AgNP"]["paired"] == B["datasets"]["AgNP"]["paired"]


def test_referencias_dos_pontos_3d(site):
    L = site["literature"]
    R, t = L["records"], L["tri_ref"]
    assert len(t["idx"]) == len(t["title"]) == len(t["doi"]) > 100
    for i in t["idx"]:
        assert R["size"][i] is not None and R["peak"][i] is not None and R["T"][i] is not None
    assert sum(L["n_by_source"].values()) == L["n"]


def test_mie_confere_com_haiss(site):
    H = site["optics"]["haiss"]
    assert H["max_abs_diff"] < 5 and 517 < H["mie_20nm"] < 526          # Haiss et al. 2007; LSPR de 20 nm ≈ 520 nm
    water = site["optics"]["n_eff_test"][0]
    assert water["n"] == 1.333 and water["haiss_max"] < 5


def test_escolha_do_modelo_e_efeitos_intervencionais(site):
    D = site["designer"]
    mc = {m["model"]: m for m in D["model_comparison"]}
    prop = mc["Matérn-5/2 (proposta)"]
    assert abs(prop["r2"] - D["cv"]["r2"]) < 1e-3                          # mesmas dobras da validação principal (reajuste)
    assert min(m["nlpd"] for m in D["model_comparison"][:4]) > prop["nlpd"] - 0.05   # núcleos empatam: escolha robusta
    for e in D["do_effects"]:
        assert e["ratio_ci95"][0] <= e["ratio"] <= e["ratio_ci95"][1] and e["n"] > 100


def test_efeitos_causais_conferem_com_a_literatura(site):
    E = {e["key"]: e for e in site["causal"]["effects"]}
    assert set(E) == {"redutor", "sementes", "ctab", "tiol"}
    assert E["redutor"]["estimate"] < 1 and E["sementes"]["estimate"] > 1 and E["ctab"]["estimate"] > 1 and E["tiol"]["estimate"] < 1
    for e in E.values():
        assert e["verdict"].startswith("confirma"), e["key"]
        if e["robust"]:
            assert max(abs(v) for v in e["smd_ebal"]) < 0.1               # balanceamento exato nas médias
            assert e["e_value_ci"] > 1.5
