---
title: Materials Explorer
---

# Materials Explorer

Search and explore **76,000+ materials** in JARVIS-DFT plus the Crystallography Open Database (COD). Filter by formula, elements (ANY/ALL/EXACT mode with periodic table selector), space group, and 19 property ranges across electronic, thermodynamic, mechanical, magnetic, optical, thermoelectric, and structural categories. Results are paginated, sortable, and exportable as CSV or JSON.

[:material-open-in-new: Open App](https://atomgpt.org/materials_explorer){ .md-button .md-button--primary }

---

## Overview

The Materials Explorer provides advanced search across two databases: JARVIS-DFT (`dft_3d`, 76K+ materials with DFT-computed properties) and COD (experimental crystal structures). The JARVIS search supports 19 numeric property filters with min/max ranges, while COD supports formula, element, and space group filters. Results are capped at 1,000 entries per query.

!!! info "Data Source"
    **JARVIS-DFT** — `dft_3d` via `jarvis.db.figshare.data('dft_3d')`, 76K+ materials with OptB88vdW properties.
    **COD** — Crystallography Open Database, experimental structures.

## Searchable Properties (JARVIS)

| Category | Property | Key | Unit |
|----------|----------|-----|------|
| Electronic | MBJ Band Gap | `mbj_bandgap` | eV |
| Electronic | OptB88vdW Band Gap | `optb88vdw_bandgap` | eV |
| Electronic | HSE Band Gap | `hse_gap` | eV |
| Electronic | Spillage | `spillage` | — |
| Thermodynamic | Formation Energy | `formation_energy` | eV/atom |
| Thermodynamic | Energy Above Hull | `ehull` | eV/atom |
| Thermodynamic | Exfoliation Energy | `exfoliation_energy` | meV/atom |
| Mechanical | Bulk Modulus | `bulk_modulus_kv` | GPa |
| Mechanical | Shear Modulus | `shear_modulus_gv` | GPa |
| Mechanical | Poisson Ratio | `poisson` | — |
| Magnetic | Magnetic Moment | `magmom_oszicar` | μB |
| Magnetic | Superconducting Tc | `Tc_supercon` | K |
| Optical | SLME | `slme` | % |
| Dielectric | Max Dielectric | `dfpt_piezo_max_dielectric` | — |
| Thermoelectric | n-Seebeck | `n-Seebeck` | μV/K |
| Thermoelectric | p-Seebeck | `p-Seebeck` | μV/K |
| Structure | Density | `density` | g/cm³ |
| Structure | Dimensionality | `dimensionality` | — |

## Endpoints

### `GET /materials_explorer/properties` — Property catalog

Returns the list of all searchable properties with column names, labels, and units.

```bash
curl "https://atomgpt.org/materials_explorer/properties" \
  -H "accept: application/json"
```

---

### `POST /materials_explorer/search` — Search materials

Search across JARVIS-DFT or COD with formula, element, space group, and property range filters.

```bash
curl -X POST "https://atomgpt.org/materials_explorer/search" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "database": "jarvis",
    "formula": "SrTiO3"
  }'
```

Search with element and property filters:

```bash
curl -X POST "https://atomgpt.org/materials_explorer/search" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "database": "jarvis",
    "elements": ["Ti", "O"],
    "element_mode": "all",
    "property_filters": {
      "optb88vdw_bandgap": {"min": 1.0, "max": 3.0},
      "formation_energy": {"min": null, "max": 0.0}
    },
    "result_properties": ["optb88vdw_bandgap", "bulk_modulus_kv"]
  }'
```

Search COD:

```bash
curl -X POST "https://atomgpt.org/materials_explorer/search" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "database": "cod",
    "elements": ["Si", "O"],
    "element_mode": "all"
  }'
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `database` | string | `"jarvis"` | `"jarvis"` or `"cod"` |
| `formula` | string | null | Chemical formula (e.g. `"SrTiO3"`, `"MoS2"`) — auto-reduced |
| `jid` | string | null | Exact JARVIS ID (e.g. `"JVASP-1002"`) or COD ID |
| `spacegroup` | string | null | Space group symbol substring (e.g. `"Fm-3m"`) |
| `elements` | list[string] | null | Element symbols (e.g. `["Ti", "O"]`) |
| `element_mode` | string | `"any"` | `"any"` (contains any), `"all"` (contains all), `"exact"` (exactly these) |
| `property_filters` | dict | null | Property range filters: `{"key": {"min": float, "max": float}}` |
| `result_properties` | list[string] | null | Extra property keys to include in results beyond defaults |

**Response (JARVIS):**

```json
{
  "database": "jarvis",
  "total": 42,
  "results": [
    {
      "jid": "JVASP-1002",
      "formula": "Si",
      "spacegroup": "Fd-3m",
      "mbj_bandgap": 1.156,
      "formation_energy": -0.005,
      "ehull": 0.0,
      "optb88vdw_bandgap": 0.611,
      "bulk_modulus_kv": 88.89
    }
  ]
}
```

Core fields always returned: `jid`, `formula`, `spacegroup`, `mbj_bandgap`, `formation_energy`, `ehull`. Additional properties appear when listed in `result_properties`.

**Response (COD):** `id`, `formula`, `spacegroup`, `authors`.

---

## Python Examples

=== "Search by formula"

    ```python
    import requests

    response = requests.post(
        "https://atomgpt.org/materials_explorer/search",
        headers={
            "Authorization": "Bearer sk-XYZ",
            "accept": "application/json",
            "Content-Type": "application/json",
        },
        json={"database": "jarvis", "formula": "SrTiO3"},
    )
    data = response.json()
    print(f"Found {data['total']} materials")
    for m in data["results"][:5]:
        print(f"  {m['jid']}: {m['formula']} gap={m['mbj_bandgap']} eV")
    ```

=== "Filter by elements + properties"

    ```python
    import requests

    response = requests.post(
        "https://atomgpt.org/materials_explorer/search",
        headers={
            "Authorization": "Bearer sk-XYZ",
            "accept": "application/json",
            "Content-Type": "application/json",
        },
        json={
            "database": "jarvis",
            "elements": ["Ti", "O"],
            "element_mode": "all",
            "property_filters": {
                "optb88vdw_bandgap": {"min": 1.0, "max": 4.0},
                "bulk_modulus_kv": {"min": 100, "max": None},
            },
            "result_properties": ["optb88vdw_bandgap", "bulk_modulus_kv"],
        },
    )
    data = response.json()
    for m in data["results"][:10]:
        print(f"{m['jid']:12s} {m['formula']:10s} "
              f"gap={m.get('optb88vdw_bandgap', 'N/A')} eV  "
              f"Kv={m.get('bulk_modulus_kv', 'N/A')} GPa")
    ```

=== "Search COD"

    ```python
    import requests

    response = requests.post(
        "https://atomgpt.org/materials_explorer/search",
        headers={
            "Authorization": "Bearer sk-XYZ",
            "accept": "application/json",
            "Content-Type": "application/json",
        },
        json={
            "database": "cod",
            "formula": "TiO2",
        },
    )
    data = response.json()
    print(f"COD: {data['total']} entries for TiO2")
    for m in data["results"][:5]:
        print(f"  COD-{m['id']}: {m['formula']} ({m['spacegroup']})")
    ```

=== "Direct JARVIS"

    ```python
    from jarvis.db.figshare import data

    dft = data("dft_3d")
    results = [
        e for e in dft
        if "Si" in e.get("atoms", {}).get("elements", [])
        and e.get("optb88vdw_bandgap") not in (None, "na")
        and float(e["optb88vdw_bandgap"]) > 1.0
    ]
    print(f"Found {len(results)} Si materials with gap > 1 eV")
    ```

## AGAPI Agent

```python
from agapi.agents import AGAPIAgent
import os

agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))
response = agent.query_sync("Find materials containing Ti and O with band gap > 2 eV")
print(response)
```

## References

- K. Choudhary, Comp. Mat. Sci. 259, 114063 (2025) [:material-link: DOI](https://doi.org/10.1016/j.commatsci.2025.114063)
- K. Choudhary et al., npj Comp. Mat. 6, 173 (2020) [:material-link: DOI](https://doi.org/10.1038/s41524-020-00440-1)
- [JARVIS-DFT Database](https://jarvis.nist.gov)
- [atomgptlab/jarvis](https://github.com/atomgptlab/jarvis)
