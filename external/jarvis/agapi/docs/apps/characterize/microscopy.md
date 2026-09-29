---
title: Microscopy Suite
---

# Microscopy Suite

Three-tab microscopy platform: (1) STEM Analyzer — AI-powered structure prediction from STEM/TEM images using MicroscopyGPT + SAM3 atomic column segmentation, (2) STEM Generator — simulate STEM images from crystal structures using STEMConv, (3) STM Viewer — browse pre-computed scanning tunneling microscopy images from JARVIS-DFT.

[:material-open-in-new: Open App](https://atomgpt.org/microscopy){ .md-button .md-button--primary }

---

## Overview

The Microscopy Suite bridges experimental imaging with computational materials science. Upload a STEM/TEM image and MicroscopyGPT predicts the underlying crystal structure (POSCAR). Detect atomic columns with SAM3 segmentation. Simulate what STEM images look like for any crystal structure. Browse 5K+ pre-computed STM images from the JARVIS-DFT database.

!!! info "Data Source"
    **MicroscopyGPT** —fine-tuned model (vLLM served).
    **SAM3** — Segment Anything Model for atomic dots detection.
    **STEMConv** — Convolution approximation for STEM image simulation.
    **JARVIS-DFT STM** — Pre-computed Tersoff-Hamann STM images from NIST/JARVIS-DFT.

## Endpoints

### `POST /microscopy/predict` — Predict structure from STEM image

Upload a STEM/TEM image + chemical formula. MicroscopyGPT generates the crystal structure (lattice parameters, atomic positions). Returns POSCAR and 3D viewer data.

```bash
curl -X POST "https://atomgpt.org/microscopy/predict" \
  -H "Authorization: Bearer sk-XYZ" \
  -F "image=@stem_image.png" \
  -F "formula=MoS2" \
  -F "temperature=0.0" \
  -F "do_sample=false" \
  -F "top_p=0.9"
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `image` | file | required | STEM/TEM image (PNG, JPG) |
| `formula` | string | required | Chemical formula (e.g. `"MoS2"`, `"GaN"`, `"Si"`) |
| `temperature` | float | 0.0 | Generation temperature (0 = deterministic) |
| `do_sample` | bool | false | Enable sampling |
| `top_p` | float | 0.9 | Nucleus sampling threshold |

**Response** includes `poscar`, `raw_output`, `backend` (`vllm_qwen2vl` ), and `atoms_info` (num_atoms, elements, volume, lattice_abc, lattice_angles).

---

### `POST /microscopy/segment` — Detect atomic columns (JSON)

Upload a STEM image and detect atomic column positions using SAM3 segmentation. Returns bounding boxes, centers, and scores.

```bash
curl -X POST "https://atomgpt.org/microscopy/segment" \
  -H "Authorization: Bearer sk-XYZ" \
  -F "image=@stem_image.png" \
  -F "prompt=dots" \
  -F "max_detections=200" \
  -F "score_threshold=0.3"
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `image` | file | required | STEM/TEM image |
| `prompt` | string | `"dots"` | Detection prompt (`"dots"`, `"atoms"`, `"circles"`) |
| `max_detections` | int | 200 | Maximum detections |
| `score_threshold` | float | 0.3 | Minimum confidence score |

**Response** includes `num_detections`, `centers` (x,y pairs), `boxes`, `scores`, `lattice_stats` (avg_nearest_distance), `image_size`.

---

### `POST /microscopy/segment_visualize` — Detect atoms (PNG overlay)

Same parameters as `/segment` but returns a PNG image with detection overlay drawn on the original image.

```bash
curl -X POST "https://atomgpt.org/microscopy/segment_visualize" \
  -H "Authorization: Bearer sk-XYZ" \
  -F "image=@stem_image.png" \
  -F "prompt=dots" \
  -F "score_threshold=0.5" \
  --output segmented.png
```

Returns `image/png` with bounding boxes and centers drawn.

---

### `POST /microscopy/stem_generate` — Simulate STEM image from POSCAR

Generate a simulated STEM image from a crystal structure using STEMConv convolution approximation.

```bash
curl -X POST "https://atomgpt.org/microscopy/stem_generate" \
  -H "Authorization: Bearer sk-XYZ" \
  -F "poscar_text=System
1.0
1.232 -2.134 0.0
1.232 2.134 0.0
0.0 0.0 30.803
C
2
direct
0.0 0.0 0.0633
0.3333 0.6667 0.0633" \
  -F "output_size=256" \
  -F "power_factor=1.7" \
  -F "px_scale=0.2" \
  -F "surface_layers=1" \
  -F "miller_index=0_0_1"
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `poscar_text` | string | required | VASP POSCAR structure |
| `output_size` | int | 256 | Image size in pixels (128, 256, 512) |
| `power_factor` | float | 1.7 | Contrast power factor |
| `px_scale` | float | 0.2 | Pixel scale (Å/pixel) |
| `surface_layers` | int | 1 | Number of surface layers |
| `miller_index` | string | `"0_0_1"` | Miller indices as `h_k_l` |

**Response** includes `image_base64` (PNG), `miller_index`, `output_size`, `num_atoms`, `formula`.

---

### `POST /microscopy/stm_image` — Pre-computed STM from JARVIS-DFT

Fetch and render Tersoff-Hamann STM images from the JARVIS-DFT STM database hosted at NIST.

```bash
curl -X POST "https://atomgpt.org/microscopy/stm_image" \
  -H "Authorization: Bearer sk-XYZ" \
  -F "jid=JVASP-667" \
  -F "bias_type=Positive" \
  -F "stm_type=Constant height" \
  -F "min_size=20" \
  -F "ext=0.15"
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `jid` | string | required | JARVIS ID (e.g. `"JVASP-667"`) |
| `bias_type` | string | `"Positive"` | `"Positive"` or `"Negative"` |
| `stm_type` | string | `"Constant height"` | `"Constant height"` or `"Constant current"` |
| `min_size` | float | 20.0 | Minimum image size (Å) |
| `ext` | float | 0.15 | Extension parameter for constant current mode |
| `zcut` | float | (auto) | Optional z-axis cutoff |

**Response** includes `image_base64` (PNG), `jid`, `bias_type`, `stm_type`, `processing_time`.

---

### `GET /microscopy/health` — Service health check

```bash
curl "https://atomgpt.org/microscopy/health" \
  -H "Authorization: Bearer sk-XYZ"
```

Returns status of the MicroscopyGPT backend service and vLLM availability.

---

## Python Examples

=== "Predict structure"

    ```python
    import requests

    with open("stem_image.png", "rb") as f:
        response = requests.post(
            "https://atomgpt.org/microscopy/predict",
            headers={
                "Authorization": "Bearer sk-XYZ",
                "accept": "application/json",
            },
            files={"image": ("stem.png", f, "image/png")},
            data={"formula": "MoS2", "temperature": "0.0"},
        )
    data = response.json()
    if data["success"]:
        print(f"Atoms: {data['atoms_info']['num_atoms']}")
        print(f"Elements: {data['atoms_info']['elements']}")
        print(f"POSCAR:\n{data['poscar'][:300]}")
    ```

=== "Segment atoms"

    ```python
    import requests

    with open("stem_image.png", "rb") as f:
        response = requests.post(
            "https://atomgpt.org/microscopy/segment",
            headers={
                "Authorization": "Bearer sk-XYZ",
                "accept": "application/json",
            },
            files={"image": ("stem.png", f, "image/png")},
            data={"prompt": "dots", "score_threshold": "0.3"},
        )
    data = response.json()
    print(f"Detected {data['num_detections']} atoms")
    for c in data["centers"][:5]:
        print(f"  ({c[0]:.1f}, {c[1]:.1f})")
    ```

=== "Generate STEM"

    ```python
    import requests

    GRAPHENE = """System
    1.0
    1.232 -2.134 0.0
    1.232 2.134 0.0
    0.0 0.0 30.803
    C
    2
    direct
    0.0 0.0 0.0633
    0.3333 0.6667 0.0633"""

    response = requests.post(
        "https://atomgpt.org/microscopy/stem_generate",
        headers={
            "Authorization": "Bearer sk-XYZ",
            "accept": "application/json",
        },
        data={
            "poscar_text": GRAPHENE,
            "output_size": "256",
            "miller_index": "0_0_1",
        },
    )
    data = response.json()
    if data["success"]:
        import base64
        with open("stem_sim.png", "wb") as f:
            f.write(base64.b64decode(data["image_base64"]))
        print(f"Saved: {data['formula']} [{data['miller_index']}]")
    ```

=== "STM image"

    ```python
    import requests

    response = requests.post(
        "https://atomgpt.org/microscopy/stm_image",
        headers={
            "Authorization": "Bearer sk-XYZ",
            "accept": "application/json",
        },
        data={
            "jid": "JVASP-667",
            "bias_type": "Positive",
            "stm_type": "Constant height",
        },
    )
    data = response.json()
    if data["success"]:
        import base64
        with open("stm.png", "wb") as f:
            f.write(base64.b64decode(data["image_base64"]))
        print(f"STM for {data['jid']} ({data['processing_time']}s)")
    ```

## AGAPI Agent [WIP]

```python
from agapi.agents import AGAPIAgent
import os

agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))

# Analyze STEM image
response = agent.query_sync("Analyze this STEM image of GaN and predict the structure")
print(response)

# Generate STEM simulation
response = agent.query_sync("Simulate a STEM image of graphene along [001]")
print(response)

# STM image
response = agent.query_sync("Show the STM image for JVASP-667 with positive bias")
print(response)
```

## References

- J. Phys. Chem. Lett. 16, 7028 (2025) — MicroscopyGPT [:material-link: DOI](https://doi.org/10.1021/acs.jpclett.5c01257)
- J. Chem. Inf. Model 63, 1708 (2023) — AtomVision [:material-link: DOI](https://doi.org/10.1021/acs.jcim.2c01533)
- Sci. Data 8, 57 (2021) — JARVIS STM Database
- [atomgptlab/atomvision](https://github.com/atomgptlab/atomvision)
- [atomgptlab/atomgpt](https://github.com/atomgptlab/atomgpt)
