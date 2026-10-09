#!/usr/bin/env python3
"""Gera o site AuGOSintesIA (site/) a partir SÓ de dados experimentais — §§4.1–4.18 da proposta FAPESP.

Etapas: análises (analyses.py) → site/data/*.js (window.AUGO.<seção> = {...}) → site/index.html (documento completo,
abre com duplo clique, sem servidor) e, com --artifact, uma versão de página única com tudo embutido.

Uso:
    python code/webapp/build_site.py                 # tudo (benchmark ~5 min com 4 processos)
    python code/webapp/build_site.py --reuse         # reaproveita as seções já calculadas em site/data/
    python code/webapp/build_site.py --artifact out.html
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import sys
import time
import warnings

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SITE = os.path.join(ROOT, "site")
sys.path.insert(0, HERE)
import analyses  # noqa: E402
import expdata  # noqa: E402

SECTIONS = ["literature", "optics", "designer", "benchmark", "interpret", "variability", "causal", "xrd", "aunc", "predictor",
            "gostruct"]


def _write(name: str, obj: dict) -> None:
    os.makedirs(os.path.join(SITE, "data"), exist_ok=True)
    js = json.dumps(obj, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    with open(os.path.join(SITE, "data", f"{name}.js"), "w", encoding="utf-8") as fh:
        fh.write(f"window.AUGO=window.AUGO||{{}};window.AUGO[{json.dumps(name)}]={js};\n")


def _read(name: str) -> dict | None:
    p = os.path.join(SITE, "data", f"{name}.js")
    if not os.path.exists(p):
        return None
    txt = open(p, encoding="utf-8").read()
    return json.loads(txt[txt.index("]=", txt.index("window.AUGO[")) + 2:].rstrip().rstrip(";"))


def compute(reuse: bool = False, workers: int = 4) -> dict:
    out = {}
    steps = [("literature", analyses.literature), ("optics", analyses.optics),
             ("designer", lambda: analyses.add_calibration(analyses.designer_agnp())), ("benchmark", lambda: analyses.add_paired_stats(analyses.benchmark(workers=workers))),
             ("interpret", lambda: analyses.interpretability(out["designer"])),
             ("variability", analyses.variability), ("causal", analyses.causal), ("xrd", analyses.xrd),
             ("aunc", analyses.aunc_section), ("predictor", analyses.predictor), ("gostruct", analyses.go_structures)]
    for name, fn in steps:
        prev = _read(name) if reuse else None
        if prev is not None:
            out[name] = prev
            if name == "benchmark":                         # estatística pareada é barata: sempre recalculada
                _write(name, analyses.add_paired_stats(prev))
            elif name == "designer":                        # idem para a calibração (só usa a validação cruzada)
                _write(name, analyses.add_calibration(prev))
            print(f"  {name:12s} reaproveitado")
            continue
        t = time.time()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            out[name] = fn()
        _write(name, out[name])
        print(f"  {name:12s} {time.time() - t:6.1f} s")
    return out


def overview(d: dict) -> dict:
    """KPIs e a correspondência seção da proposta → aba do site, com o estado de cada uma."""
    lit, opt, des, ben = d["literature"], d["optics"], d["designer"], d["benchmark"]
    var, cau, xr = d["variability"], d["causal"], d["xrd"]
    gp_win = {}
    for name, ds in ben["datasets"].items():
        r = ds["reach_top5"]
        gp_win[name] = {a: r[a]["median_experiments"] for a in ben["arms"]}
    return {
        "generated": dt.date.today().isoformat(),
        "kpis": {"literature_records": lit["n"], "literature_dois": lit["n_doi"], "go_records": lit["n_go"],
                 "go_dois": lit["n_go_doi"], "agnp_measurements": des["n_measurements"],
                 "agnp_conditions": des["n_conditions"], "aunc_entries": d["aunc"]["n"],
                 "mie_validation_n": opt["lit_spheres"]["n"],
                 "mie_median_abs_residual": opt["lit_spheres"]["median_abs_residual"],
                 "designer_cv_r2": des["cv"]["r2"], "designer_coverage": des["cv"]["coverage95"],
                 "causal_ratio": cau["ratio"], "causal_ci": cau["ratio_ci95"],
                 "xrd_energy_keV": (xr["geometry"] or {}).get("energy_keV"),
                 "turkevich_papers": var["turkevich"]["n_papers"], "turkevich_fold": var["turkevich"]["fold_1sd"],
                 "benchmarks": len(ben["datasets"])},
        "experiments_to_top5": gp_win,
        "benchmark_measurements": {n: expdata.benchmark_size(n) for n in ben["datasets"]},
        "map": [
            {"sec": "4.1", "title": "Revisão e curadoria dos dados", "tab": "literatura", "status": "experimental"},
            {"sec": "4.2", "title": "Caracterização do GO e GO Navigator", "tab": "caracterizacao", "status": "parcial",
             "note": "XRD real (padrão CeO2); os lotes de GO dependem das medidas do laboratório"},
            {"sec": "4.3", "title": "Reagentes e impurezas", "tab": "literatura", "status": "parcial",
             "note": "redutores e ligantes da literatura; impurezas por lote dependem do laboratório"},
            {"sec": "4.4", "title": "Produto e função objetivo J", "tab": "optica", "status": "experimental"},
            {"sec": "4.5", "title": "AuNP Designer", "tab": "designer", "status": "experimental",
             "note": "campanha real de nanopartículas de prata (perda espectral medida)"},
            {"sec": "4.6", "title": "Modelos de forma espectral", "tab": "optica", "status": "experimental"},
            {"sec": "4.7", "title": "Transferência entre lotes e fontes", "tab": "variabilidade", "status": "parcial",
             "note": "generalização para artigo novo (AuNC); entre lotes de GO depende do laboratório"},
            {"sec": "4.8", "title": "MISO (multi-fonte de informação)", "tab": "sobre", "status": "laboratorio",
             "note": "exige UV-Vis, DLS e TEM das mesmas sínteses"},
            {"sec": "4.9", "title": "Análise causal", "tab": "causal", "status": "experimental"},
            {"sec": "4.10", "title": "Modelagem física", "tab": "optica", "status": "experimental",
             "note": "Mie com constantes ópticas medidas, validada contra a literatura"},
            {"sec": "4.11", "title": "Campanha prospectiva", "tab": "sobre", "status": "laboratorio"},
            {"sec": "4.12", "title": "Microscopia e confirmação", "tab": "sobre", "status": "laboratorio"},
            {"sec": "4.13", "title": "Interpretabilidade (SHAP)", "tab": "interpretabilidade", "status": "experimental"},
            {"sec": "4.14", "title": "Sustentabilidade", "tab": "literatura", "status": "parcial",
             "note": "tendência de escolha de reagentes; custos dependem do laboratório"},
            {"sec": "4.15", "title": "Benchmarking de algoritmos", "tab": "aprendizado", "status": "experimental"},
            {"sec": "4.16", "title": "Self-driving lab / cloud lab", "tab": "aprendizado", "status": "parcial",
             "note": "campanhas reais reexecutadas em laço fechado; integração com robô é condicional"},
            {"sec": "4.17", "title": "QC, rastreabilidade, reprodutibilidade", "tab": "variabilidade",
             "status": "experimental"},
            {"sec": "4.18", "title": "Decisão e incerteza", "tab": "preditor", "status": "experimental",
             "note": "preditor com intervalos conformais por artigo; EI e calibração do GP no Designer"},
        ]}


# three.js r147 (MIT; github.com/mrdoob/three.js, tag r147): última versão com build UMD e OrbitControls em examples/js,
# que funcionam como <script> comum, sem módulos, dentro da página única
THREE_JS = ("three.min.js", "OrbitControls.js", "RoomEnvironment.js")


def _page(inline: bool) -> str:
    """index.html: documento completo (inline=False, arquivos ao lado) ou corpo de página única com tudo embutido."""
    tpl = open(os.path.join(HERE, "template.html"), encoding="utf-8").read()
    css = open(os.path.join(HERE, "app.css"), encoding="utf-8").read()
    js = open(os.path.join(HERE, "app.js"), encoding="utf-8").read()
    guide = open(os.path.join(HERE, "guide.js"), encoding="utf-8").read()
    nano = open(os.path.join(HERE, "nano3d.js"), encoding="utf-8").read()
    if not inline:
        body = tpl.replace("{{STYLE}}", '<link rel="stylesheet" href="assets/app.css">')
        data = "\n".join(f'<script src="data/{s}.js"></script>' for s in ["overview"] + SECTIONS)
        body = body.replace("{{SCRIPTS}}", '<script src="vendor/plotly.min.js"></script>\n' + "".join(
            f'<script src="vendor/{v}"></script>\n' for v in THREE_JS) + data + '\n<script src="assets/guide.js"></script>\n'
            '<script src="assets/nano3d.js"></script>\n<script src="assets/app.js"></script>')
        return "<!doctype html>\n<html lang=\"pt-BR\">\n<head>\n<meta charset=\"utf-8\">\n" \
               "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">\n" \
               + body.replace("<!--BODY-->", "</head>\n<body>") + "\n</body>\n</html>\n"
    # o plotly.min.js tem um U+FFFD literal numa regex; a escape \uFFFD é equivalente em JS e não confunde validadores
    plotly = open(os.path.join(SITE, "vendor", "plotly.min.js"), encoding="utf-8").read().replace("\ufffd", "\\uFFFD")
    datas = "".join(open(os.path.join(SITE, "data", f"{s}.js"), encoding="utf-8").read()
                    for s in ["overview"] + SECTIONS)
    body = tpl.replace("{{STYLE}}", f"<style>\n{css}\n</style>").replace("<!--BODY-->", "")
    three = "".join(f"<script>{open(os.path.join(HERE, 'vendor', v), encoding='utf-8').read()}</script>\n" for v in THREE_JS)
    return body.replace("{{SCRIPTS}}", f"<script>{plotly}</script>\n{three}<script>window.AUGO_EMBED=true;{datas}</script>\n"
                                       f"<script>{guide}</script>\n<script>{nano}</script>\n<script>{js}</script>")


def build(reuse: bool = False, artifact: str | None = None, workers: int = 4) -> None:
    print("análises (só dados experimentais):")
    d = compute(reuse, workers)
    _write("overview", overview(d))
    os.makedirs(os.path.join(SITE, "assets"), exist_ok=True)
    os.makedirs(os.path.join(SITE, "vendor"), exist_ok=True)
    shutil.copy(os.path.join(HERE, "app.css"), os.path.join(SITE, "assets", "app.css"))
    shutil.copy(os.path.join(HERE, "app.js"), os.path.join(SITE, "assets", "app.js"))
    shutil.copy(os.path.join(HERE, "guide.js"), os.path.join(SITE, "assets", "guide.js"))
    shutil.copy(os.path.join(HERE, "nano3d.js"), os.path.join(SITE, "assets", "nano3d.js"))
    for v in THREE_JS + ("LICENSE-three.txt",):
        shutil.copy(os.path.join(HERE, "vendor", v), os.path.join(SITE, "vendor", v))
    import plotly
    src = os.path.join(os.path.dirname(plotly.__file__), "package_data", "plotly.min.js")
    shutil.copy(src, os.path.join(SITE, "vendor", "plotly.min.js"))
    with open(os.path.join(SITE, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(_page(inline=False))
    print(f"-> {os.path.relpath(SITE, ROOT)}/index.html")
    if artifact:
        with open(artifact, "w", encoding="utf-8") as fh:
            fh.write(_page(inline=True))
        print(f"-> {artifact} ({os.path.getsize(artifact) / 1e6:.1f} MB, página única)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reuse", action="store_true", help="reaproveita seções já calculadas em site/data/")
    ap.add_argument("--artifact", help="também grava uma página única com tudo embutido")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    build(a.reuse, a.artifact, a.workers)


if __name__ == "__main__":
    main()
