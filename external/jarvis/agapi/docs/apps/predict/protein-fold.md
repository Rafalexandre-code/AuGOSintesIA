---
title: Protein Fold
---

# Protein Fold

Protein structure prediction using ESMFold (Meta) and OpenFold3 (NVIDIA). Paste an amino acid sequence to get a 3D PDB structure with interactive 3Dmol viewer. Two backends: ESMFold via the ESM Atlas API for single-chain folding, and OpenFold3 via NVIDIA Health API for protein-DNA complex prediction.

[:material-open-in-new: Open App](https://atomgpt.org/protein_fold){ .md-button .md-button--primary }

---

## Overview

The Protein Fold app provides two structure prediction backends. ESMFold takes a single amino acid sequence (10–400 residues) and returns a PDB structure via Meta's ESM Atlas API. OpenFold3 takes a protein sequence plus two DNA sequences and predicts the protein-DNA complex via NVIDIA's Health API. The web UI includes an interactive 3Dmol viewer with cartoon/sphere/stick/line rendering, spin control, and PDB download.

!!! info "Data Source"
    **ESMFold** — `api.esmatlas.com/foldSequence/v1/pdb/` (Meta AI).
    **OpenFold3** — `health.api.nvidia.com` (NVIDIA BioNeMo).

## Endpoints

### `POST /protein_fold/predict` — Fold sequence (web UI, JSON)

Predict 3D structure from amino acid sequence. Returns PDB content, atom count, residue count, amino acid composition, and molecular weight.

```bash
curl -X POST "https://atomgpt.org/protein_fold/predict" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "sequence": "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAVQVKVKALPDAQFEVVHSLAKWKRQQQ"
  }'
```

| Field | Type | Description |
|-------|------|-------------|
| `sequence` | string | Amino acid sequence (standard one-letter codes: ACDEFGHIKLMNPQRSTVWY, 10–400 residues) |

**Response:**

| Field | Description |
|-------|-------------|
| `pdb_content` | Full PDB file content |
| `sequence` | Cleaned uppercase sequence |
| `sequence_length` | Number of residues |
| `num_atoms` | Total atoms in PDB |
| `num_residues` | Unique residue count |
| `composition` | Amino acid composition dict (e.g. `{"ALA": 5, "GLY": 3}`) |
| `molecular_weight` | Estimated molecular weight (Da) |

---

### `GET /protein_fold/query` — Fold sequence (API key, plain text PDB)

Returns the raw PDB file as plain text.

```bash
curl "https://atomgpt.org/protein_fold/query?sequence=MKTAYIAKQRQISFVKSHFS&APIKEY=sk-XYZ" \
  -H "accept: text/plain" \
  --output structure.pdb
```

---

### `POST /protein_fold/query` — Fold sequence (session auth, ZIP or JSON)

Returns PDB as a ZIP file (default) or JSON.

```bash
curl -X POST "https://atomgpt.org/protein_fold/query" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "sequence=MKTAYIAKQRQISFVKSHFS&format=zip" \
  --output protein_structure.zip
```

| Param | Default | Description |
|-------|---------|-------------|
| `sequence` | required | Amino acid sequence |
| `format` | `"zip"` | `"zip"` (PDB in ZIP archive) or `"json"` (PDB as JSON string) |

---

### `GET /openfold/query` — Protein-DNA complex (NVIDIA OpenFold3)

Predict a protein-DNA complex structure using NVIDIA's OpenFold3 API.

```bash
curl "https://atomgpt.org/openfold/query?protein_sequence=MKTAYIAKQRQISFVKSHFS&dna1=ATCGATCG&dna2=CGATCGAT&APIKEY=sk-XYZ" \
  -H "accept: text/plain" \
  --output complex.pdb
```

| Param | Description |
|-------|-------------|
| `protein_sequence` | Protein amino acid sequence |
| `dna1` | First DNA strand sequence |
| `dna2` | Second DNA strand sequence (complementary) |

Returns plain-text PDB of the predicted complex.

---

## Python Examples

=== "Fold a protein"

    ```python
    import requests

    response = requests.post(
        "https://atomgpt.org/protein_fold/predict",
        headers={
            "Authorization": "Bearer sk-XYZ",
            "accept": "application/json",
            "Content-Type": "application/json",
        },
        json={
            "sequence": "KVFGRCELAAAMKRHGLDNYRGYSLGNWVCAAKFESNFNTQATNRNTDGSTDYGILQINSRWWCNDGRTPGSRNLCNIPCSALLSSDITASVNCAKKIVSDGNGMNAWVAWRNRCKGTDVQAWIRGCRL"
        },
    )
    data = response.json()
    if data["success"]:
        print(f"Residues: {data['num_residues']}")
        print(f"Atoms: {data['num_atoms']}")
        print(f"MW: {data['molecular_weight']:.0f} Da")
        with open("structure.pdb", "w") as f:
            f.write(data["pdb_content"])
        print("Saved structure.pdb")
    ```

=== "Get raw PDB"

    ```python
    import requests

    response = requests.get(
        "https://atomgpt.org/protein_fold/query",
        params={
            "sequence": "MKTAYIAKQRQISFVKSHFS",
            "APIKEY": "sk-XYZ",
        },
    )
    with open("peptide.pdb", "w") as f:
        f.write(response.text)
    ```

=== "Protein-DNA complex"

    ```python
    import requests

    response = requests.get(
        "https://atomgpt.org/openfold/query",
        params={
            "protein_sequence": "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGD",
            "dna1": "ATCGATCGATCG",
            "dna2": "CGATCGATCGAT",
            "APIKEY": "sk-XYZ",
        },
    )
    with open("complex.pdb", "w") as f:
        f.write(response.text)
    print("Saved protein-DNA complex PDB")
    ```

## AGAPI Agent

```python
from agapi.agents import AGAPIAgent
import os

agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))

# Fold protein
response = agent.query_sync("Fold this protein sequence: MKTAYIAKQRQISFVKSHFS")
print(response)
```

## References

- Z. Lin et al., Science 379, 1123 (2023) — ESMFold [:material-link: DOI](https://doi.org/10.1126/science.ade2574)
- [facebookresearch/esm](https://github.com/facebookresearch/esm)
- [NVIDIA OpenFold3](https://health.api.nvidia.com)
