---
title: ALIGNN Predictor
---

# ALIGNN Predictor

Predict 15+ materials properties simultaneously using ALIGNN (Atomistic Line Graph Neural Network) pretrained models. Input by JARVIS ID or POSCAR structure. Properties span energy/stability, electronic band gaps, mechanical moduli, dielectric/piezoelectric constants, topological spillage, SLME, magnetic moment, superconducting Tc, and interface band offsets.

[:material-open-in-new: Open App](https://atomgpt.org/alignn){ .md-button .md-button--primary }

---

## Overview

The ALIGNN Predictor runs 15 pretrained ALIGNN models in one call to predict a comprehensive set of materials properties from crystal structure alone. Max 50 atoms per structure. Three endpoints are available: GET (API key auth), POST (session auth for web UI), and web_predict (structured JSON response with all 15 properties organized by category).

!!! info "Data Source"
    **ALIGNN pretrained models** — 15+ models from [`alignn.pretrained`](https://github.com/atomgptlab/alignn/blob/main/alignn/pretrained.py), trained on JARVIS-DFT data.

## Predicted Properties

| Category | Property | Unit | Model Key |
|----------|----------|------|-----------|
| Energy | Formation energy | eV/atom | `jv_formation_energy_peratom_alignn` |
| Energy | Total energy (OptB88vdW) | eV/atom | `jv_optb88vdw_total_energy_alignn` |
| Energy | Energy above hull | eV/atom | `jv_ehull_alignn` |
| Electronic | Band gap (OptB88vdW) | eV | `jv_optb88vdw_bandgap_alignn` |
| Electronic | Band gap (mBJ) | eV | `jv_mbj_bandgap_alignn` |
| Mechanical | Bulk modulus (Kv) | GPa | `jv_bulk_modulus_kv_alignn` |
| Mechanical | Shear modulus (Gv) | GPa | `jv_shear_modulus_gv_alignn` |
| Dielectric | Dielectric constant (εx) | — | `jv_epsx_alignn` |
| Piezoelectric | Piezoelectric constant | — | `jv_dfpt_piezo_max_dielectric_alignn` |
| Topological | SOC spillage | — | `jv_spillage_alignn` |
| Optical | SLME | % | `jv_slme_alignn` |
| Magnetic | Magnetic moment | μB | `jv_magmom_oszicar_alignn` |
| Superconducting | Tc | K | `jv_supercon_tc_alignn` |
| Interface | CBM (InterMat) | eV | `intermat_cbm` |
| Interface | VBM (InterMat) | eV | `intermat_vbm` |

## Endpoints

### `GET /alignn/query` — Predict by JARVIS ID or POSCAR (API key)

```bash
curl "https://atomgpt.org/alignn/query?jid=JVASP-1002&APIKEY=sk-XYZ" \
  -H "accept: application/json"
```

With POSCAR string (URL-encoded):

```bash
curl "https://atomgpt.org/alignn/query?poscar=Si%0A1.0%0A0%202.734%202.734%0A2.734%200%202.734%0A2.734%202.734%200%0ASi%0A2%0Adirect%0A0%200%200%0A0.25%200.25%200.25&APIKEY=sk-XYZ" \
  -H "accept: application/json"
```

| Param | Description |
|-------|-------------|
| `jid` | JARVIS ID (e.g. `JVASP-1002`) — provide `jid` OR `poscar` |
| `poscar` | URL-encoded POSCAR string |
| `APIKEY` | API key (query parameter auth) |

Returns raw prediction dict with all model keys.

---

### `POST /alignn/query` — Predict from file or string (session auth)

Upload a POSCAR file:

```bash
curl -X POST "https://atomgpt.org/alignn/query" \
  -H "Authorization: Bearer sk-XYZ" \
  -F "file=@POSCAR"
```

Or submit as form string:

```bash
curl -X POST "https://atomgpt.org/alignn/query" \
  -H "Authorization: Bearer sk-XYZ" \
  -F "poscar_string=Si
1.0
0 2.734 2.734
2.734 0 2.734
2.734 2.734 0
Si
2
direct
0 0 0
0.25 0.25 0.25"
```

---

### `POST /alignn/web_predict` — Structured predictions (JSON body)

Returns all 15 properties organized in a clean structure with formula and atom count.

```bash
curl -X POST "https://atomgpt.org/alignn/web_predict" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "poscar": "Si\n1.0\n0 2.734 2.734\n2.734 0 2.734\n2.734 2.734 0\nSi\n2\ndirect\n0 0 0\n0.25 0.25 0.25"
  }'
```

**Response:**

```json
{
  "formula": "Si",
  "num_atoms": 2,
  "properties": {
    "formation_energy": -0.005,
    "total_energy": -5.412,
    "ehull": 0.0,
    "bandgap_optb88": 0.611,
    "bandgap_mbj": 1.156,
    "bulk_modulus": 88.9,
    "shear_modulus": 51.5,
    "epsx": 12.3,
    "piezoelectric": 0.0,
    "spillage": 0.32,
    "slme": 5.2,
    "magmom": 0.0,
    "supercon_tc": 0.0,
    "intermat_cbm": -4.1,
    "intermat_vbm": -5.3
  }
}
```

---

## Python Examples

=== "Query by JID"

    ```python
    import requests

    response = requests.get(
        "https://atomgpt.org/alignn/query",
        headers={"accept": "application/json"},
        params={"jid": "JVASP-1002", "APIKEY": "sk-XYZ"},
    )
    data = response.json()
    print(f"Band gap (OptB88): {data['jv_optb88vdw_bandgap_alignn'][0]:.3f} eV")
    print(f"Formation energy: {data['jv_formation_energy_peratom_alignn'][0]:.3f} eV/atom")
    ```

=== "Web predict (structured)"

    ```python
    import requests

    response = requests.post(
        "https://atomgpt.org/alignn/web_predict",
        headers={
            "Authorization": "Bearer sk-XYZ",
            "accept": "application/json",
            "Content-Type": "application/json",
        },
        json={"poscar": open("POSCAR").read()},
    )
    data = response.json()
    print(f"{data['formula']} ({data['num_atoms']} atoms)")
    p = data["properties"]
    print(f"  Formation energy: {p['formation_energy']:.3f} eV/atom")
    print(f"  Band gap (OPT): {p['bandgap_optb88']:.3f} eV")
    print(f"  Band gap (MBJ): {p['bandgap_mbj']:.3f} eV")
    print(f"  Bulk modulus: {p['bulk_modulus']:.1f} GPa")
    print(f"  Supercon Tc: {p['supercon_tc']:.2f} K")
    ```

=== "Upload POSCAR file"

    ```python
    import requests

    with open("POSCAR", "rb") as f:
        response = requests.post(
            "https://atomgpt.org/alignn/query",
            headers={"Authorization": "Bearer sk-XYZ"},
            files={"file": ("POSCAR", f)},
        )
    data = response.json()
    for key, val in sorted(data.items()):
        if key.endswith("_alignn") or key.startswith("intermat"):
            print(f"  {key}: {val}")
    ```

## AGAPI Agent

```python
from agapi.agents import AGAPIAgent
import os

agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))

# Predict properties
response = agent.query_sync("Predict all ALIGNN properties for JVASP-1002")
print(response)

# Compare materials
response = agent.query_sync("Compare the band gap of Si and GaAs using ALIGNN")
print(response)
```

## References

- K. Choudhary, B. DeCost, npj Comp. Mat. 7, 185 (2021) — ALIGNN [:material-link: DOI](https://doi.org/10.1038/s41524-021-00650-1)
- K. Choudhary, Comp. Mat. Sci. 259, 114063 (2025) [:material-link: DOI](https://doi.org/10.1016/j.commatsci.2025.114063)
- [atomgptlab/alignn](https://github.com/atomgptlab/alignn)
