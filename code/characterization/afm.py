#!/usr/bin/env python3
"""AFM de folhas de GO: espessura, tamanho lateral e fração de monocamadas (§4.2; "tamanho lateral e espessura por
AFM quando disponível").

Pipeline: nivelamento (plano ajustado só no substrato, iterativo: o plano é refeito sem os pixels altos) → limiar de
Otsu → rótulos → por folha: espessura = mediana da altura na folha − mediana do substrato ao redor (anel), tamanho
lateral = √área, nº de camadas ≈ espessura / espessura da monocamada (GO hidratado ≈ 0,9–1,2 nm; --monolayer-nm).
Folhas encostadas na borda são descartadas (área truncada).

Entrada: matriz de alturas (CSV/TXT sem cabeçalho, TIFF, ou .npy) + --nm-per-px; alturas em nm (--height-scale para
converter). Arquivos de instrumento (.spm, .ibw, .gwy): exporte a matriz no Gwyddion.

Uso:
    python code/characterization/afm.py img.txt --nm-per-px 9.77 [--sample GO-B01-S01 --out afm.csv]
"""
from __future__ import annotations

import argparse
import csv

import numpy as np

MONOLAYER_NM = 1.0


def load_height(path: str, height_scale: float = 1.0) -> np.ndarray:
    if path.lower().endswith(".npy"):
        z = np.load(path)
    elif path.lower().endswith((".tif", ".tiff")):
        from skimage import io
        z = io.imread(path).astype(float)
    else:
        z = np.loadtxt(path, delimiter="," if path.lower().endswith(".csv") else None)
    return np.asarray(z, float) * height_scale


def level(z: np.ndarray, iters: int = 3) -> tuple[np.ndarray, np.ndarray]:
    """Subtrai o plano do substrato (ajuste só nos pixels abaixo do limiar a cada iteração). -> (z nivelado, máscara)."""
    from skimage.filters import threshold_otsu
    ny, nx = z.shape
    yy, xx = np.mgrid[:ny, :nx]
    A = np.c_[np.ones(z.size), xx.ravel(), yy.ravel()]
    sub = np.ones(z.shape, bool)
    zl = z
    for _ in range(iters):
        coef = np.linalg.lstsq(A[sub.ravel()], z.ravel()[sub.ravel()], rcond=None)[0]
        zl = z - (A @ coef).reshape(z.shape)
        sub = zl < threshold_otsu(zl)
    return zl - np.median(zl[sub]), ~sub


def flakes(z: np.ndarray, mask: np.ndarray, nm_per_px: float, min_px: int = 30, monolayer_nm: float = MONOLAYER_NM):
    from scipy import ndimage as ndi
    from skimage import measure, morphology, segmentation
    mask = morphology.remove_small_objects(ndi.binary_fill_holes(mask), max_size=min_px)
    lab = segmentation.clear_border(measure.label(mask))
    out = []
    for r in measure.regionprops(lab):
        reg = lab == r.label
        ring = ndi.binary_dilation(reg, iterations=4) & ~ndi.binary_dilation(reg, iterations=1) & ~mask
        base = np.median(z[ring]) if ring.any() else 0.0
        t = float(np.median(z[reg]) - base)
        out.append({"thickness_nm": t, "lateral_size_um": float(np.sqrt(r.area) * nm_per_px / 1000),
                    "n_layers": t / monolayer_nm})
    return out


def summarize(fl: list[dict], monolayer_nm: float = MONOLAYER_NM) -> dict:
    if not fl:
        return {"n_flakes": 0}
    t = np.array([f["thickness_nm"] for f in fl])
    L = np.array([f["lateral_size_um"] for f in fl])
    sd = lambda a: float(np.std(a, ddof=1)) if len(a) > 1 else float("nan")   # noqa: E731
    return {"n_flakes": len(fl), "thickness_nm": (float(np.median(t)), sd(t)),
            "lateral_size_um": (float(np.median(L)), sd(L)),
            "monolayer_fraction": (float(np.mean(t < 1.5 * monolayer_nm)), float("nan"))}


def to_rows(s: dict, sample_id: str, files: str = "") -> list[dict]:
    rows = []
    for i, q in enumerate(("thickness_nm", "lateral_size_um", "monolayer_fraction"), 1):
        if q not in s:
            continue
        v, sd = s[q]
        rows.append({"measurement_id": f"M-AFM-{sample_id}-{i:02d}", "go_sample_id": sample_id, "technique": "AFM",
                     "quantity": q, "value": round(v, 4), "uncertainty": "" if not np.isfinite(sd) else round(sd, 4),
                     "uncertainty_type": "" if not np.isfinite(sd) else "sd", "n_replicates": s["n_flakes"],
                     "unit": "nm" if q.endswith("nm") else ("um" if q.endswith("um") else "fraction"),
                     "method_details": "nivelamento por plano no substrato + Otsu; mediana por folha "
                                       "(code/characterization/afm.py)", "raw_data_file": files})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("images", nargs="+")
    ap.add_argument("--nm-per-px", type=float, required=True)
    ap.add_argument("--height-scale", type=float, default=1.0, help="fator para converter a altura em nm")
    ap.add_argument("--monolayer-nm", type=float, default=MONOLAYER_NM)
    ap.add_argument("--sample", default="GO-SAMPLE")
    ap.add_argument("--out")
    a = ap.parse_args()
    fl = []
    for f in a.images:
        z, m = level(load_height(f, a.height_scale))
        fl += flakes(z, m, a.nm_per_px, monolayer_nm=a.monolayer_nm)
    s = summarize(fl, a.monolayer_nm)
    print(s)
    if a.out and s.get("n_flakes"):
        rows = to_rows(s, a.sample, "|".join(a.images))
        with open(a.out, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)


if __name__ == "__main__":
    main()
