---
title: Quantum Computation
---

# Quantum Computation

Run quantum chemistry simulations on Wannier tight-binding Hamiltonians from JARVIS-DFT. Two tabs: (1) VQE — variational quantum eigensolver at a single k-point using Qiskit statevector simulator with EfficientSU2 (circuit6) ansatz, returning ground-state energy, Pauli decomposition, and circuit diagram; (2) Bandstructure — full VQD bandstructure across the Brillouin zone via JARVIS `get_bandstruct`, comparing quantum (VQD) vs classical (NumPy) eigenvalues. Supports both electron and phonon Hamiltonians.

[:material-open-in-new: Open App](https://atomgpt.org/quantum){ .md-button .md-button--primary }

---

## Overview

The Quantum Computation app bridges Wannier tight-binding Hamiltonians with quantum computing. It loads the WTBH from JARVIS-DFT, builds H(k) at the requested k-point, decomposes it into a sum of Pauli operators, then runs Qiskit VQE (or VQD for bandstructure) on a statevector simulator. The EfficientSU2 ansatz (`QuantumCircuitLibrary.circuit6`) parameterizes the trial wavefunction. Results are compared against classical NumPy diagonalization.

!!! info "Data Source"
    **JARVIS-WTB** — Wannier tight-binding Hamiltonians via `jarvis.db.figshare.get_wann_electron` / `get_wann_phonon`.
    **Qiskit** — VQE/VQD via `jarvis.io.qiskit.inputs.HermitianSolver` (requires `qiskit==0.41.1`, `qiskit-aer`).

## Available Materials

| JID | Formula | Type | Qubits | Description |
|-----|---------|------|--------|-------------|
| JVASP-816 | Al | electron | 3 | FCC Aluminum |
| JVASP-1002 | Si | electron | 3 | Diamond Silicon |
| JVASP-1174 | GaAs | electron | 4 | Zinc blende GaAs |
| JVASP-35680 | PbS | electron | 4 | Hexagonal PbS |
| JVASP-39 | Cu | electron | 3 | FCC Copper |
| JVASP-816 | Al | phonon | 2 | Al phonon |
| JVASP-1002 | Si | phonon | 3 | Si phonon |

## Endpoints

### `GET /quantum/materials` — List available materials

```bash
curl "https://atomgpt.org/quantum/materials" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "accept: application/json"
```

Returns `{"materials": [{"jid": "JVASP-816", "formula": "Al", "type": "electron", "qubits": 3, "desc": "FCC Aluminum"}, ...]}`.

---

### `POST /quantum/vqe` — VQE at a single k-point

Run Qiskit VQE on the Wannier Hamiltonian H(k) at a specific k-point. Returns VQE ground-state energy, classical eigenvalues, Pauli decomposition, and circuit diagram.

```bash
curl -X POST "https://atomgpt.org/quantum/vqe" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "jid": "JVASP-816",
    "kpoint": [0.5, 0.0, 0.5],
    "ham_type": "electron",
    "reps": 2,
    "backend": "statevector_simulator"
  }'
```

Phonon example:

```bash
curl -X POST "https://atomgpt.org/quantum/vqe" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "jid": "JVASP-1002",
    "kpoint": [0.0, 0.0, 0.0],
    "ham_type": "phonon",
    "reps": 2
  }'
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `jid` | string | `"JVASP-816"` | JARVIS material ID |
| `kpoint` | list[float] | `[0.5, 0.0, 0.5]` | k-point in fractional coordinates [kx, ky, kz] |
| `ham_type` | string | `"electron"` | `"electron"` or `"phonon"` |
| `reps` | int | 2 | EfficientSU2 circuit repetitions (1–5) |
| `backend` | string | `"statevector_simulator"` | Qiskit Aer backend |

**Response:**

| Field | Description |
|-------|-------------|
| `vqe_ground_state` | VQE ground-state energy relative to E_F (eV) |
| `classical_ground_state` | NumPy ground-state energy (eV) |
| `error_eV` | Absolute error between VQE and classical |
| `classical_eigenvalues` | All eigenvalues from NumPy (eV, relative to E_F) |
| `n_qubits` | Number of qubits = log₂(matrix_size) |
| `matrix_size` | Hamiltonian dimension |
| `n_pauli_terms` | Number of Pauli operators in decomposition |
| `n_circuit_params` | Number of variational parameters |
| `circuit_depth` | Quantum circuit depth |
| `circuit_diagram` | ASCII text diagram of the EfficientSU2 circuit |
| `pauli_decomposition` | Top Pauli terms with coefficients |

---

### `POST /quantum/bandstructure` — Full VQD bandstructure

Compute band structure across the Brillouin zone using JARVIS `get_bandstruct`. Runs VQD at each k-point along the high-symmetry path and compares with classical diagonalization.

```bash
curl -X POST "https://atomgpt.org/quantum/bandstructure" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "jid": "JVASP-816",
    "ham_type": "electron",
    "line_density": 3
  }'
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `jid` | string | `"JVASP-816"` | JARVIS material ID |
| `ham_type` | string | `"electron"` | `"electron"` or `"phonon"` |
| `line_density` | int | 1 | K-point density along path (higher = more k-points, slower) |

**Response:**

| Field | Description |
|-------|-------------|
| `eigvals_classical` | 2D array (nkpts × nbands) from NumPy |
| `eigvals_vqd` | 2D array (nkpts × nbands) from Qiskit VQD |
| `n_kpoints` | Number of k-points along path |
| `n_bands` | Number of bands |
| `labels` | High-symmetry point labels with k-point indices |
| `mae_eV` | Mean absolute error between VQD and classical (eV) |
| `formula` | Chemical formula |

---

## Python Examples

=== "VQE at single k-point"

    ```python
    import requests

    response = requests.post(
        "https://atomgpt.org/quantum/vqe",
        headers={
            "Authorization": "Bearer sk-XYZ",
            "accept": "application/json",
            "Content-Type": "application/json",
        },
        json={
            "jid": "JVASP-816",
            "kpoint": [0.5, 0.0, 0.5],
            "ham_type": "electron",
            "reps": 2,
        },
    )
    data = response.json()
    print(f"Material: {data['jid']} ({data['ham_type']})")
    print(f"Qubits: {data['n_qubits']}, Pauli terms: {data['n_pauli_terms']}")
    print(f"VQE ground state:      {data['vqe_ground_state']:.6f} eV")
    print(f"Classical ground state: {data['classical_ground_state']:.6f} eV")
    print(f"Error: {data['error_eV']:.6f} eV")
    print(f"\nAll eigenvalues:")
    for i, e in enumerate(data["classical_eigenvalues"]):
        print(f"  Band {i+1}: {e:.4f} eV")
    ```

=== "Bandstructure"

    ```python
    import requests

    response = requests.post(
        "https://atomgpt.org/quantum/bandstructure",
        headers={
            "Authorization": "Bearer sk-XYZ",
            "accept": "application/json",
            "Content-Type": "application/json",
        },
        json={
            "jid": "JVASP-816",
            "ham_type": "electron",
            "line_density": 3,
        },
    )
    data = response.json()
    print(f"{data['formula']} — {data['n_kpoints']} k-points, {data['n_bands']} bands")
    print(f"MAE (VQD vs classical): {data['mae_eV']:.6f} eV")
    print(f"Labels: {[(l['label'], l['index']) for l in data['labels']]}")
    ```

=== "Plot VQD vs classical"

    ```python
    import requests
    import matplotlib.pyplot as plt
    import numpy as np

    response = requests.post(
        "https://atomgpt.org/quantum/bandstructure",
        headers={
            "Authorization": "Bearer sk-XYZ",
            "Content-Type": "application/json",
        },
        json={"jid": "JVASP-816", "ham_type": "electron", "line_density": 3},
    )
    data = response.json()

    eigvals_np = np.array(data["eigvals_classical"])
    eigvals_vqd = np.array(data["eigvals_vqd"])
    nk = data["n_kpoints"]

    fig, ax = plt.subplots(figsize=(8, 5))
    for b in range(eigvals_np.shape[1]):
        ax.plot(range(nk), eigvals_np[:, b], "b-", lw=1.5,
                label="Classical" if b == 0 else "")
        ax.plot(range(nk), eigvals_vqd[:, b], "ro", ms=3, alpha=0.7,
                label="VQD" if b == 0 else "")

    for lbl in data["labels"]:
        ax.axvline(lbl["index"], color="gray", ls="--", lw=0.5)
        ax.text(lbl["index"], ax.get_ylim()[0], lbl["label"],
                ha="center", va="top", fontsize=9)

    ax.set_ylabel("Energy (eV)")
    ax.set_title(f"{data['formula']} — MAE: {data['mae_eV']:.4f} eV")
    ax.legend()
    plt.tight_layout()
    plt.savefig("quantum_bands.png", dpi=150)
    ```

## AGAPI Agent

```python
from agapi.agents import AGAPIAgent
import os

agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))

# VQE
response = agent.query_sync("Run VQE for Al at the X point using quantum computation")
print(response)

# Bandstructure
response = agent.query_sync("Compute quantum bandstructure for Si using VQD")
print(response)
```

## References

- K. Choudhary, J. Phys.: Condens. Matter 33, 385501 (2021) [:material-link: DOI](https://doi.org/10.1088/1361-648X/ac1154)
- BenchQC (2025) [:material-link: DOI](https://arxiv.org/abs/2502.09595)
- K. Choudhary, Comp. Mat. Sci. 259, 114063 (2025) [:material-link: DOI](https://doi.org/10.1016/j.commatsci.2025.114063)
- [atomgptlab/jarvis](https://github.com/atomgptlab/jarvis)
