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
