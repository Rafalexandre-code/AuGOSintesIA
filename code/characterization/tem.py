#!/usr/bin/env python3
"""TEM: distribuição de tamanho de AuNP por segmentação clássica (limiar + watershed), sem GPU.

Pipeline: suavização gaussiana → limiar de Otsu (partículas escuras em campo claro; --bright para o inverso) →
remoção de ruído e preenchimento → divisão de partículas encostadas por watershed na transformada de distância →
descarta objetos na borda e pouco circulares → diâmetro equivalente (nm) = √(4·área/π)·tamanho do pixel.

Tamanho do pixel: --nm-per-px, ou lido dos metadados de arquivos .dm3/.dm4/.emd/.tif via RosettaSciIO.
Para imagens difíceis (baixo contraste, partículas sobre GO dobrado), use segmentação por SAM — ex.: NP-SAM
(Larsen et al.) ou github.com/brunoaugustoam/AnalysisOfNanoparticlesUsingSAM (Sci. Rep. 2025) — e reaproveite
`summarize()`/`to_rows()` daqui com a máscara resultante.

Uso:
    python code/characterization/tem.py imagem.tif --nm-per-px 0.25 [--synthesis SYN-0001 --out medidas.csv]
"""
from __future__ import annotations

import argparse
import csv

import numpy as np


def load_image(path: str) -> tuple[np.ndarray, float | None]:
    """-> (imagem 2D float, nm por pixel ou None)."""
    if path.lower().endswith((".dm3", ".dm4", ".emd", ".ser", ".mrc")):
        import importlib  # leitores do RosettaSciIO (ambiente core)
        ext = path.lower().rsplit(".", 1)[1]
        mod = {"dm3": "rsciio.digitalmicrograph", "dm4": "rsciio.digitalmicrograph", "emd": "rsciio.emd",
               "ser": "rsciio.tia", "mrc": "rsciio.mrc"}[ext]
        d = importlib.import_module(mod).file_reader(path)[0]
        ax = d["axes"][-1]
        scale = ax.get("scale")
        unit = str(ax.get("units", "nm"))
        factor = {"nm": 1, "µm": 1000, "μm": 1000, "um": 1000, "Å": 0.1, "A": 0.1, "pm": 1e-3}
        if scale and unit not in factor:
            raise ValueError(f"{path}: unidade de escala desconhecida {unit!r}; informe --nm-per-px")
        nm = scale * factor[unit] if scale else None
        data = np.asarray(d["data"], float)
        if data.ndim == 3:            # série/pilha: usa a média dos quadros
            data = data.mean(axis=0)
        return data, nm
    from skimage import io
    img = io.imread(path)
    if img.ndim == 3:
        img = img[..., :3].mean(-1)
    return img.astype(float), None


def segment(img: np.ndarray, bright: bool = False, min_px: int = 20, sigma: float = 1.0,
            min_diameter_px: float | None = None) -> np.ndarray:
    """Rótulos das partículas. min_diameter_px (menor diâmetro esperado, em px) controla a separação do watershed:
    picos da transformada de distância mais próximos que ~0,7·raio mínimo não viram partículas separadas."""
    from scipy import ndimage as ndi
    from skimage import feature, filters, measure, morphology, segmentation
    im = filters.gaussian(img, sigma=sigma)
    th = filters.threshold_otsu(im)
    mask = im > th if bright else im < th
    mask = morphology.remove_small_objects(mask, max_size=min_px)
    mask = ndi.binary_fill_holes(mask)
    dist = ndi.distance_transform_edt(mask)
    md = int(0.7 * min_diameter_px / 2) if min_diameter_px else max(2, int(np.sqrt(min_px) / 2))
    coords = feature.peak_local_max(dist, min_distance=max(2, md), labels=measure.label(mask), exclude_border=False)
    markers = np.zeros_like(dist, dtype=int)
    markers[tuple(coords.T)] = np.arange(1, len(coords) + 1)
    labels = segmentation.watershed(-dist, markers, mask=mask)
    return segmentation.clear_border(labels)


def particle_sizes(labels: np.ndarray, nm_per_px: float, min_circularity: float = 0.6) -> np.ndarray:
    from skimage import measure
    d = []
    for r in measure.regionprops(labels):
        if r.perimeter == 0:
            continue
        circ = 4 * np.pi * r.area / r.perimeter ** 2
        if circ >= min_circularity:
            d.append(r.equivalent_diameter_area * nm_per_px)
    return np.array(d)


def summarize(d_nm: np.ndarray) -> dict:
    n = len(d_nm)
    if n == 0:
        return {"n_particles": 0}
    mean, sd = float(np.mean(d_nm)), float(np.std(d_nm, ddof=1)) if n > 1 else float("nan")
    return {"n_particles": n, "size_mean_nm": mean, "size_sd_nm": sd, "size_cv": sd / mean,
            "size_median_nm": float(np.median(d_nm)), "size_mean_sem_nm": sd / np.sqrt(n) if n > 1 else float("nan")}


def to_rows(s: dict, synthesis_id: str, files: str = "") -> list[dict]:
    rows = []
    for i, q in enumerate(("size_mean_nm", "size_sd_nm", "size_cv", "n_particles"), 1):
        if q not in s:
            continue
        rows.append({"measurement_id": f"M-TEM-{synthesis_id}-{i:02d}", "synthesis_id": synthesis_id,
                     "technique": "TEM", "quantity": q, "value": round(float(s[q]), 4),
                     "uncertainty": round(s["size_mean_sem_nm"], 4) if q == "size_mean_nm" else "",
                     "uncertainty_type": "sem" if q == "size_mean_nm" else "", "n_replicates": s["n_particles"],
                     "unit": "nm" if q.endswith("nm") else ("count" if q == "n_particles" else "a.u."),
                     "method_details": "Otsu + watershed (code/characterization/tem.py)", "raw_data_file": files})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("images", nargs="+")
    ap.add_argument("--nm-per-px", type=float)
    ap.add_argument("--bright", action="store_true", help="partículas claras (ex.: HAADF-STEM)")
    ap.add_argument("--min-px", type=int, default=20)
    ap.add_argument("--min-diameter-nm", type=float, help="menor diâmetro esperado (melhora a separação de partículas encostadas)")
    ap.add_argument("--synthesis", default="SYN")
    ap.add_argument("--out")
    a = ap.parse_args()
    allds = []
    for f in a.images:
        img, nm = load_image(f)
        nm = a.nm_per_px or nm
        if not nm:
            raise SystemExit(f"{f}: informe --nm-per-px (sem metadado de escala)")
        mdp = a.min_diameter_nm / nm if a.min_diameter_nm else None
        allds.append(particle_sizes(segment(img, a.bright, a.min_px, min_diameter_px=mdp), nm))
    s = summarize(np.concatenate(allds))
    print({k: round(v, 3) if isinstance(v, float) else v for k, v in s.items()})
    if a.out:
        rows = to_rows(s, a.synthesis, "|".join(a.images))
        with open(a.out, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)


if __name__ == "__main__":
    main()
