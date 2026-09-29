---
title: Phonon DOS
---

# Phonon DOS

Visualize and compare phonon density of states from JARVIS-DFT. Vibrational spectra fetched from JARVIS XML pages via `Webpage.get_dft_phonon_dos()`. Includes filtering of non-DOS keys (elastic properties, metadata) that leak from the XML parser.

[:material-open-in-new: Open App](https://atomgpt.org/phonon_dos){ .md-button .md-button--primary }

---

## Overview

Search materials by formula, JARVIS ID, elements, space group, or property ranges. Click any result to fetch and plot the full spectrum. All search results are capped at 500 entries.

!!! info "Data Source"
    **JARVIS-DFT** — phonon DOS fetched via `jarvis.db.webpages.Webpage.get_dft_phonon_dos()`.

## Endpoints

### `POST /phonon_dos/search` — Search materials

```bash
curl -X POST "https://atomgpt.org/phonon_dos/search" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "formula": "Si"
  }'
```

Search with elements:

```bash
curl -X POST "https://atomgpt.org/phonon_dos/search" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "elements": ["Ti", "O"],
    "element_mode": "all"
  }'
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `formula` | string | null | Chemical formula |
| `jid` | string | null | Exact JARVIS ID |
| `elements` | list[string] | null | Element symbols |
| `element_mode` | string | "any" | "any", "all", or "exact" |
| `bandgap_min` | float | null | Min OptB88vdW band gap (eV) |
| `bandgap_max` | float | null | Max OptB88vdW band gap (eV) |
| `spacegroup` | string | null | Space group substring |

**Response fields:** `jid, formula, spacegroup, optb88vdw_bandgap, mbj_bandgap, magmom`.

!!! note
    Pre-filtered to materials with `bulk_modulus_kv != 'na'` (materials with mechanical data tend to have phonon DOS).

---

### `GET /phonon_dos/data/{jid}` — Fetch spectrum data

Fetch phonon DOS spectrum for a single material. Returns frequency axis and DOS channels.

```bash
curl "https://atomgpt.org/phonon_dos/data/JVASP-1002" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "accept: application/json"
```

**Response:**

```json
{
  "jid": "JVASP-1002",
  "formula": "Si",
  "bandgap": 0.611,
  "frequencies": [0.0, 0.5, 1.0, ...],
  "components": {
    "Total": [0.0, 0.12, 0.35, ...]
  }
}
```

Frequency axis searched across keys: `frequencies`, `frequency`, `phonon_dos_frequencies`, `omega`. Non-DOS keys (elastic constants, metadata scalars) are filtered out. Only arrays matching the frequency axis length are included as channels.

---

## Python Examples

=== "Search"

    ```python
    import requests

    response = requests.post(
        "https://atomgpt.org/phonon_dos/search",
        headers={
            "Authorization": "Bearer sk-XYZ",
            "accept": "application/json",
            "Content-Type": "application/json",
        },
        json={"formula": "Si"},
    )
    data = response.json()
    print(f"Found {data['total']} materials")
    for m in data["results"][:5]:
        print(f"  {m['jid']}: {m['formula']}")
    ```

=== "Fetch data"

    ```python
    import requests

    response = requests.get(
        "https://atomgpt.org/phonon_dos/data/JVASP-1002",
        headers={"Authorization": "Bearer sk-XYZ"},
    )
    data = response.json()
    print(f"{data['formula']} — {len(data['frequencies'])} frequency points")
    print(f"Max frequency: {max(data['frequencies']):.1f} THz")
    ```

## AGAPI Agent

```python
from agapi.agents import AGAPIAgent
import os

agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))
response = agent.query_sync("Show phonon dos for Silicon")
print(response)
```

## References

- K. Choudhary et al., Phys. Rev. Mat. 7, 023803 (2023) [:material-link: DOI](https://doi.org/10.1103/PhysRevMaterials.7.023803)
- [atomgptlab/jarvis](https://github.com/atomgptlab/jarvis)
