# 🌐 AtomGPT.org API (AGAPI): Agentic AI for Materials Science

[![Open in Google Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/knc6/jarvis-tools-notebooks/blob/master/jarvis-tools-notebooks/agapi_example.ipynb)
[![PyPI](https://img.shields.io/pypi/v/agapi)](https://pypi.org/project/agapi/)
[![License](https://img.shields.io/badge/license-Apache-blue)](LICENSE)

Empower your materials science research with AtomGPT's Agentic AI API (**AGAPI**). AGAPI removes complex software setups, commercial API cost allowing you to perform advanced predictions, analyses, and explorations through natural language or Python, accelerating materials discovery and design. AGAPI implements a modular architecture separating the reasoning layer (LLM brain) from the execution layer (scientific tools and databases as hands) through a unified REST API interface. This design follows established principles of agentic AI systems.



## 🚀 Quickstart

**1. Get your API key** — sign up at [AtomGPT.org](https://atomgpt.org) → Account → Settings, then:

```bash
pip install agapi jarvis-tools scipy httpx
export AGAPI_KEY="sk-your-key-here"
```

**2. Initialize client and agent:**

```python
import os
from agapi.agents.client import AGAPIClient
from agapi.agents import AGAPIAgent
from agapi.agents.functions import *
from jarvis.io.vasp.inputs import Poscar

# Direct function calls (API client)
client = AGAPIClient(api_key=os.environ.get("AGAPI_KEY"))
result = query_by_formula("Si", client)
print(result["materials"][25]["formula"], result["materials"][25]["mbj_bandgap"])

# Natural language queries (AI agent)
agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))
response = agent.query_sync("What is the bandgap of Silicon?")
print(response)
```

---

## ✨ Key Capabilities

### Common Inputs

```python
SI_PRIM = """Si
1.0
0 2.734 2.734
2.734 0 2.734
2.734 2.734 0
Si
2
direct
0 0 0
0.25 0.25 0.25
"""

GAAS_PRIM = """GaAs
1.0
0 2.875 2.875
2.875 0 2.875
2.875 2.875 0
Ga As
1 1
direct
0 0 0
0.25 0.25 0.25
"""

SI_XRD = """28.44 1.00
47.30 0.55
56.12 0.30
"""
```

---

### 1. Materials API Query
Access JARVIS-DFT and more.

**API Example:**
```python
from agapi.agents.functions import (
    query_by_formula,
    query_by_jid,
    query_by_elements,
    query_by_property,
    find_extreme,
    alignn_predict,
    alignn_ff_relax,
    slakonet_bandstructure,
    generate_interface,
    make_supercell,
    substitute_atom,
    create_vacancy,
    generate_xrd_pattern,
    protein_fold,
    diffractgpt_predict,
    alignn_ff_single_point,
    alignn_ff_optimize,
    alignn_ff_md,
    pxrd_match,
    xrd_analyze,
    microscopygpt_analyze,
    query_mp,
    query_oqmd,
    search_arxiv,
    search_crossref,
    openfold_predict,
    list_jarvis_columns,
)

r = query_by_formula("Si", client)
assert "error" not in r

r = query_by_jid("JVASP-1002", client)
assert isinstance(r.get("POSCAR"), str)

r = query_by_elements("Si", client)
assert "error" not in r

r = query_by_property("bandgap", 0.1, 3.0, elements="Si", api_client=client)
assert "error" not in r

r = find_extreme("bulk modulus", True, elements="Si", api_client=client)
assert "error" not in r
```

**Natural Language Example:**
```python
agent.query_sync("Show me all MgB2 polymorphs")
agent.query_sync("What's the Tc_Supercon for MgB2 and what's the JARVIS-ID for it?")
agent.query_sync("What's the stiffest Si,O material?")
agent.query_sync("Find materials with bulk modulus > 200 GPa")
agent.query_sync("Compare bandgaps across BN, AlN, GaN, InN")
agent.query_sync("What are the formation energies of SiC, AlN, MgO?")
```

---

### 2. AI Property Prediction (ALIGNN)
Predict bandgap, formation energy, elastic moduli, and more using graph neural networks.

**API Example:**
```python
from agapi.agents.functions import alignn_predict

r = alignn_predict(jid="JVASP-1002", api_client=client)
assert r.get("status") == "success"
```

**Natural Language Example:**
```python
agent.query_sync("Predict properties of JARVIS-ID JVASP-1002 with ALIGNN")
agent.query_sync(f"Predict properties using ALIGNN for this structure:\n\n{SI_PRIM}")
```

---

### 3. AI Force Field (ALIGNN-FF)
Structure relaxation, single-point energy, and MD with near-DFT accuracy.

**API Example:**
```python
from agapi.agents.functions import alignn_ff_relax, alignn_ff_single_point

r = alignn_ff_relax(SI_PRIM, api_client=client)
assert r.get("status") == "success"
print(Poscar.from_string(r["relaxed_poscar"]))   # view relaxed structure

r = alignn_ff_single_point(SI_PRIM, api_client=client)
assert "energy_eV" in r
```

**Natural Language Example:**
```python
agent.query_sync(f"Optimize structure with ALIGNN-FF:\n\n{SI_PRIM}")
agent.query_sync("Get the single-point energy of this Si primitive cell.")
```

---

### 4. Band Structure (SlakoNet)
Tight-binding band structures from neural network Slater-Koster parameters.

**API Example:**
```python
from agapi.agents.functions import slakonet_bandstructure

r = slakonet_bandstructure(SI_PRIM, api_client=client)
assert r.get("status") == "success"
```

**Natural Language Example:**
```python
agent.query_sync("Compute the band structure of Si.")
agent.query_sync(f"Plot the electronic band structure for this POSCAR:\n\n{SI_PRIM}")
```

---

### 5. XRD / DiffractGPT
Match PXRD patterns, identify phases, and analyze experimental diffraction data.

**API Example:**
```python
from agapi.agents.functions import pxrd_match, xrd_analyze, diffractgpt_predict

r = pxrd_match("Si", SI_XRD, api_client=client)
assert isinstance(r, dict)
if "matched_poscar" in r:
    print(Poscar.from_string(r["matched_poscar"]))   # view matched structure

r = xrd_analyze("Si", SI_XRD, api_client=client)
assert isinstance(r, dict)

r = diffractgpt_predict("Si", "28.4(1.0),47.3(0.49)", client)
assert isinstance(r, dict)
```

**Natural Language Example:**
```python
agent.query_sync("Identify the phase from this XRD pattern for Silicon: [XRD data]")
agent.query_sync("Analyze this PXRD pattern and suggest possible structures.")
```

---

### 6. STEM / MicroscopyGPT
Analyze STEM, TEM, and electron microscopy images using AI — identify atomic columns, measure lattice spacings, detect defects, and interpret microstructure.

**API Example:**
```python
from agapi.agents.functions import microscopygpt_analyze

r = microscopygpt_analyze("HRTEM image of Si lattice", api_client=client)
assert isinstance(r, dict)
```

**Natural Language Example:**
```python
agent.query_sync("Analyze this STEM image of a GaN thin film: [image]")
agent.query_sync("What defects are visible in this HRTEM image?")
agent.query_sync("Measure the d-spacing from this electron diffraction pattern.")
```



---

### 7. Structure Manipulation
Supercells, substitutions, vacancies, and XRD pattern generation — runs locally, no API call needed.

**API Example:**
```python
from agapi.agents.functions import make_supercell, substitute_atom, create_vacancy, generate_xrd_pattern

r = make_supercell(SI_PRIM, [2, 2, 1])
assert r["supercell_atoms"] > r["original_atoms"]
print(f"Original atoms: {r['original_atoms']}, Supercell atoms: {r['supercell_atoms']}")
# Expected: Original atoms: 2, Supercell atoms: 8

r = substitute_atom(GAAS_PRIM, "Ga", "Al", 1)
assert "Al" in r["new_formula"]
# Expected new_formula: AlAs

r = create_vacancy(GAAS_PRIM, "Ga", 1)
assert r["new_atoms"] == r["original_atoms"] - 1
# Expected: one fewer atom than original

r = generate_xrd_pattern(SI_PRIM)
assert r["formula"] == "Si"
```

**Natural Language Example:**
```python
agent.query_sync("Make a 2x1x1 supercell of the most stable GaN.")
agent.query_sync("Substitute one Ga with Al in this GaAs structure.")
agent.query_sync("Create a Ga vacancy in GaAs and predict its properties.")
```

---

### 8. Interface Generation
Build heterostructure interfaces between two materials.

**API Example:**
```python
from agapi.agents.functions import generate_interface

r = generate_interface(SI_PRIM, GAAS_PRIM, api_client=client)
assert r.get("status") == "success"
```

**Natural Language Example:**
```python
agent.query_sync("""
    Create a GaN/AlN heterostructure interface:
    1. Find GaN (most stable)
    2. Find AlN (most stable)
    3. Generate (001)/(001) interface
    4. Show POSCAR
""", max_context_messages=20)
```

---

### 9. Literature Search
Search arXiv and Crossref for relevant research papers.

**API Example:**
```python
from agapi.agents.functions import search_arxiv, search_crossref

r = search_arxiv("GaN", max_results=2, api_client=client)
assert isinstance(r, dict)

r = search_crossref("GaN", rows=2, api_client=client)
assert isinstance(r, dict)
```

**Natural Language Example:**
```python
agent.query_sync("Find recent papers on perovskite solar cells on arXiv.")
agent.query_sync("Search for publications about ALIGNN neural networks.")
```

---

## 🔧 Multi-Step Agentic Workflow

```python
agent.query_sync("""
1. Find all GaN materials in the JARVIS-DFT database
2. Get the POSCAR for the most stable one
3. Make a 2x1x1 supercell
4. Substitute one Ga with Al
5. Generate powder XRD pattern
6. Optimize structure with ALIGNN-FF
7. Predict properties with ALIGNN
""", max_context_messages=20, verbose=True)

agent.query_sync("""
Create a GaN/AlN heterostructure interface:
1. Find GaN (most stable)
2. Find AlN (most stable)
3. Generate (001)/(001) interface
4. Show POSCAR
""", max_context_messages=20, verbose=True)
```

---

## 🤖 Supported LLM Backends

AGAPI supports multiple LLM backends. Set `model` when initializing the agent:

```python
agent = AGAPIAgent(
    api_key=os.environ.get("AGAPI_KEY"),
    model="openai/gpt-oss-20b" 
)
```

Available models:

| Provider | Model |
|---|---|
| OpenAI | `openai/gpt-oss-20b` |
| OpenAI | `openai/gpt-oss-120b` |
| Meta | `meta/llama-4-maverick-17b-128e-instruct` |
| Meta | `meta/llama-3.2-90b-vision-instruct` |
| Meta | `meta/llama-3.2-1b-instruct` |
| Google | `google/gemini-2.5-flash` |
| Google | `google/gemma-3-27b-it` |
| DeepSeek | `deepseek-ai/deepseek-v3.1` |
| Moonshot | `moonshotai/kimi-k2-instruct-0905` |
| Qwen | `qwen/qwen3-next-80b-a3b-instruct` |


---

## 📦 Available APIs/Functions

| Function | Description |
|---|---|
| `query_by_formula` | Search by chemical formula |
| `query_by_jid` | Fetch by JARVIS ID |
| `query_by_elements` | Filter by constituent elements |
| `query_by_property` | Filter by property range |
| `find_extreme` | Find max/min property material |
| `alignn_predict` | GNN property prediction |
| `alignn_ff_relax` | Structure relaxation |
| `alignn_ff_single_point` | Single-point energy |
| `slakonet_bandstructure` | TB band structure |
| `generate_interface` | Heterostructure builder |
| `make_supercell` | Supercell generation |
| `substitute_atom` | Atomic substitution |
| `create_vacancy` | Vacancy creation |
| `generate_xrd_pattern` | Simulated XRD |
| `pxrd_match / xrd_analyze` | XRD phase matching |
| `diffractgpt_predict` | AI XRD interpretation |
| `microscopygpt_analyze` | AI STEM/TEM image analysis |
| `query_mp` | Materials Project query |
| `search_arxiv / search_crossref` | Literature search |
| `protein_fold` | Protein structure prediction |

...
---

## 📖 References

If you find this work helpful, please cite:

1. **AGAPI-Agents: An Open-Access Agentic AI Platform for Accelerated Materials Design on AtomGPT.org**
   https://doi.org/10.48550/arXiv.2512.11935

2. **ChatGPT Material Explorer: Design and Implementation of a Custom GPT Assistant for Materials Science Applications**
   https://doi.org/10.1016/j.commatsci.2025.114063

3. **The JARVIS Infrastructure Is All You Need for Materials Design**
   https://doi.org/10.1016/j.commatsci.2025.114063

📄 Full publication list: [Google Scholar](https://scholar.google.com/citations?hl=en&user=YVP36YgAAAAJ&view_op=list_works&sortby=pubdate)

---

## 📚 Resources

- 🔬 **Research Group**: [AtomGPTLab @ JHU](https://choudhary.wse.jhu.edu/)
- 📖 **Docs**: [AtomGPT.org/docs](https://atomgpt.org/docs)
- 🧪 **Colab**: [AGAPI Example Notebook](https://colab.research.google.com/github/knc6/jarvis-tools-notebooks/blob/master/jarvis-tools-notebooks/agapi_example.ipynb)
- ▶️ **YouTube**: [Demo Playlist](https://www.youtube.com/playlist?list=PLjf6vHVv7AoInTVQmfNSMs_12DBXYCcDd)

---

## ❤️ Note

**AGAPI (ἀγάπη)** is a Greek word meaning *unconditional love*. 

## Disclaimer

AtomGPT.org can make mistakes — please verify critical results. We hope this API fosters open, collaborative, and accelerated discovery in materials science.
