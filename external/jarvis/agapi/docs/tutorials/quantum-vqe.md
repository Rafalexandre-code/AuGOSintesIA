---
title: Quantum VQE for Solids
---

# Quantum VQE for Solids

Run VQE and VQD on Wannier tight-binding Hamiltonians to predict electronic and phonon bandstructures using quantum algorithms.

## Install

```bash
pip install jarvis-tools qiskit==0.41.1 qiskit-aer
```

## VQE at a Single K-point

```python
from jarvis.db.figshare import get_wann_electron, get_hk_tb
from jarvis.io.qiskit.inputs import HermitianSolver
from jarvis.core.circuits import QuantumCircuitLibrary
from qiskit import Aer

# Load Wannier TB Hamiltonian for Aluminum
backend = Aer.get_backend("statevector_simulator")
wtbh, Ef, atoms = get_wann_electron("JVASP-816")

# Build H(k) at X-point
hk = get_hk_tb(w=wtbh, k=[0.5, 0., 0.5])

# Setup VQE
HS = HermitianSolver(hk)
n_qubits = HS.n_qubits()
circ = QuantumCircuitLibrary(n_qubits=n_qubits, reps=1).circuit6()

# Run VQE
en, vqe_result, vqe = HS.run_vqe(var_form=circ, backend=backend)
vals, vecs = HS.run_numpy()

print(f"Classical ground state: {vals[0]-Ef:.4f} eV")
print(f"VQE ground state:      {en-Ef:.4f} eV")
print(f"Error:                 {abs(en-vals[0]):.6f} eV")
```

## Full Bandstructure with VQD

```python
from jarvis.io.qiskit.inputs import get_bandstruct

out = get_bandstruct(w=wtbh, atoms=atoms, line_density=1, savefig=False)

# out["eigvals_q"]  = VQD eigenvalues (quantum)
# out["eigvals_np"] = numpy eigenvalues (classical)
# out["kpts"]       = k-point coordinates
# out["new_labels"] = high-symmetry point labels
```

## Plot Bandstructure Comparison

```python
import matplotlib.pyplot as plt
import numpy as np

eigvals_q = np.array(out["eigvals_q"]).real
eigvals_np = np.array(out["eigvals_np"]).real
nk, nb = eigvals_np.shape

for b in range(nb):
    plt.plot(range(nk), eigvals_np[:, b], 'b-', linewidth=1.5,
             label='Classical' if b == 0 else '')
    plt.plot(range(nk), eigvals_q[:, b], 'r.', markersize=3,
             label='VQD' if b == 0 else '')

plt.ylabel("Energy (eV)")
plt.legend()
plt.title("Al Electronic Bandstructure: Classical vs VQD")
plt.savefig("al_bands_vqd.png", dpi=150)
plt.show()
```

## Key Concepts

**Wannier TBH**: Compact representation of DFT electronic structure. 307 electronic + 933 phonon Hamiltonians available in JARVIS.

**VQE**: Variational Quantum Eigensolver — finds ground state energy using parameterized quantum circuits.

**VQD**: Variational Quantum Deflation — extends VQE to find excited states by deflating previously found eigenvalues.

**Circuit-6**: EfficientSU2 ansatz with RY+RZ gates and CNOT entangling layers.

## Reference

K. Choudhary, J. Phys.: Condens. Matter 33, 385501 (2021) — [DOI](https://doi.org/10.1088/1361-648X/ac1154)
