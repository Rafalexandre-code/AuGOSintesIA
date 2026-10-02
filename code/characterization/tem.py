#!/usr/bin/env python3
"""TEM: distribuição de tamanho de AuNP por segmentação clássica (limiar + watershed), sem GPU.

Pipeline: suavização gaussiana → limiar de Otsu (partículas escuras em campo claro; --bright para o inverso) →
remoção de ruído e preenchimento → divisão de partículas encostadas por watershed na transformada de distância →
descarta objetos na borda e pouco circulares → diâmetro equivalente (nm) = √(4·área/π)·tamanho do pixel.

Tamanho do pixel: --nm-per-px, ou lido dos metadados de arquivos .dm3/.dm4/.emd/.tif via RosettaSciIO.
Para imagens difíceis (baixo contraste, partículas sobre GO dobrado), use segmentação por SAM — ex.: NP-SAM
(Larsen et al.) ou github.com/brunoaugustoam/AnalysisOfNanoparticlesUsingSAM (Sci. Rep. 2025) — e reaproveite
`summarize()`/`to_rows()` daqui com a máscara resultante.

Associação AuNP–GO (--go-association, §4.2): em campo claro há TRÊS níveis de cinza — AuNP (escuras), folha de GO
(contraste fraco) e fundo/filme de carbono (claro). Um limiar de Otsu multinível (3 classes) separa os três; para cada
partícula, o anel ao redor dela (largura ≈ raio) é classificado: se ≥ 50 % do anel é GO, a partícula está sobre o GO.
Saídas: GO_associated_fraction (IC de Wilson 95 %), GO_area_fraction e a SELETIVIDADE de nucleação
= (partículas/área de GO) ÷ (partículas/área livre), com correção de Haldane: > 1 indica nucleação preferencial no GO
(o que a proposta quer controlar); ≈ 1, deposição aleatória; < 1, partículas formadas em solução e não ancoradas.

Uso:
    python code/characterization/tem.py imagem.tif --nm-per-px 0.25 [--go-association] [--synthesis SYN-0001 --out m.csv]
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
            min_diameter_px: float | None = None, classes: int = 2) -> np.ndarray:
    """Rótulos das partículas. min_diameter_px (menor diâmetro esperado, em px) controla a separação do watershed:
    picos da transformada de distância mais próximos que ~0,7·raio mínimo não viram partículas separadas."""
    from scipy import ndimage as ndi
    from skimage import feature, filters, measure, morphology, segmentation
    im = filters.gaussian(img, sigma=sigma)
    if classes > 2:     # com GO: só a classe mais extrema (AuNP) vira partícula
        t = filters.threshold_multiotsu(im, classes=classes)
        mask = im > t[-1] if bright else im < t[0]
    else:
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


def go_association(img: np.ndarray, labels: np.ndarray, bright: bool = False, sigma: float = 2.0,
                   min_go_ring: float = 0.5) -> dict:
    """Conta partículas sobre GO e fora dele (anel ao redor de cada partícula) e as áreas de GO e de fundo."""
    from scipy.ndimage import binary_dilation
    from skimage import filters, measure, morphology
    im = filters.gaussian(img, sigma=sigma)
    cls = np.digitize(im, filters.threshold_multiotsu(im, classes=3))     # 0 escuro … 2 claro
    if bright:
        cls = 2 - cls
    near = binary_dilation(labels > 0, morphology.disk(2))
    go, bg = (cls == 1) & ~near, (cls == 2) & ~near
    on = off = 0
    for r in measure.regionprops(labels):
        rad = max(2, int(round(r.equivalent_diameter_area / 2)))
        r0, c0, r1, c1 = r.bbox
        pad = 2 * rad + 3
        sl = (slice(max(0, r0 - pad), r1 + pad), slice(max(0, c0 - pad), c1 + pad))
        reg = labels[sl] == r.label
        ring = binary_dilation(reg, morphology.disk(rad + 3)) & ~binary_dilation(reg, morphology.disk(3))
        n_go, n_bg = int(go[sl][ring].sum()), int(bg[sl][ring].sum())
        if n_go + n_bg == 0:
            continue
        if n_go / (n_go + n_bg) >= min_go_ring:
            on += 1
        else:
            off += 1
    return {"n_on_GO": on, "n_off_GO": off, "area_GO_px": int(go.sum()), "area_bg_px": int(bg.sum())}


def association_summary(counts: list[dict], nm_per_px: list[float]) -> dict:
    """Agrega várias imagens: fração associada (Wilson 95 %), fração de área de GO e seletividade de nucleação."""
    on = sum(c["n_on_GO"] for c in counts)
    off = sum(c["n_off_GO"] for c in counts)
    a_go = sum(c["area_GO_px"] * s ** 2 for c, s in zip(counts, nm_per_px)) / 1e6      # µm²
    a_bg = sum(c["area_bg_px"] * s ** 2 for c, s in zip(counts, nm_per_px)) / 1e6
    n = on + off
    out = {"n_classified": n, "GO_area_fraction": a_go / (a_go + a_bg) if a_go + a_bg else float("nan")}
    if n:
        p, z = on / n, 1.959964
        den = 1 + z ** 2 / n
        mid, half = (p + z ** 2 / (2 * n)) / den, z * np.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / den
        out.update({"GO_associated_fraction": p, "GO_associated_ci_low": mid - half, "GO_associated_ci_high": mid + half})
    if a_go > 0 and a_bg > 0:
        out["nucleation_selectivity"] = ((on + 0.5) / a_go) / ((off + 0.5) / a_bg)
        out["density_on_GO_per_um2"] = on / a_go
    return out


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
    units = {"GO_associated_fraction": "fraction", "GO_area_fraction": "fraction", "nucleation_selectivity": "ratio",
             "density_on_GO_per_um2": "um-2"}
    for j, q in enumerate(units, len(rows) + 1):
        if q not in s:
            continue
        ci = q == "GO_associated_fraction"
        rows.append({"measurement_id": f"M-TEM-{synthesis_id}-{j:02d}", "synthesis_id": synthesis_id,
                     "technique": "TEM", "quantity": q, "value": round(float(s[q]), 4),
                     "uncertainty": round((s["GO_associated_ci_high"] - s["GO_associated_ci_low"]) / 2, 4) if ci else "",
                     "uncertainty_type": "ci95" if ci else "", "n_replicates": s["n_classified"],
                     "unit": units[q],
                     "method_details": "Otsu multinível (3 classes) + anel ao redor de cada partícula "
                                       "(code/characterization/tem.py --go-association)", "raw_data_file": files})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("images", nargs="+")
    ap.add_argument("--nm-per-px", type=float)
    ap.add_argument("--bright", action="store_true", help="partículas claras (ex.: HAADF-STEM)")
    ap.add_argument("--min-px", type=int, default=20)
    ap.add_argument("--min-diameter-nm", type=float, help="menor diâmetro esperado (melhora a separação de partículas encostadas)")
    ap.add_argument("--go-association", action="store_true",
                    help="classifica cada partícula como sobre o GO ou fora dele (3 classes de cinza)")
    ap.add_argument("--synthesis", default="SYN")
    ap.add_argument("--out")
    a = ap.parse_args()
    allds, counts, scales = [], [], []
    for f in a.images:
        img, nm = load_image(f)
        nm = a.nm_per_px or nm
        if not nm:
            raise SystemExit(f"{f}: informe --nm-per-px (sem metadado de escala)")
        mdp = a.min_diameter_nm / nm if a.min_diameter_nm else None
        labels = segment(img, a.bright, a.min_px, min_diameter_px=mdp, classes=3 if a.go_association else 2)
        allds.append(particle_sizes(labels, nm))
        if a.go_association:
            counts.append(go_association(img, labels, a.bright))
            scales.append(nm)
    s = summarize(np.concatenate(allds))
    if counts:
        s.update(association_summary(counts, scales))
    print({k: round(v, 3) if isinstance(v, float) else v for k, v in s.items()})
    if a.out:
        rows = to_rows(s, a.synthesis, "|".join(a.images))
        with open(a.out, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)


if __name__ == "__main__":
    main()
