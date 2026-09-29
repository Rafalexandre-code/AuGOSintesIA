---
title: Quick Start
---

# Quick Start

Get started with AtomGPT.org in 2 minutes.

## 1. Install

```bash
pip install agapi jarvis-tools scipy httpx
```

## 2. Get Your API Key

Sign up at [AtomGPT.org](https://atomgpt.org) → Account → Settings:

```bash
export AGAPI_KEY="sk-your-key-here"
```

## 3. Direct API Calls

```python
import os
from agapi.agents.client import AGAPIClient
from agapi.agents.functions import *

client = AGAPIClient(api_key=os.environ.get("AGAPI_KEY"))
result = query_by_formula("Si", client)
print(result["materials"][25]["formula"], result["materials"][25]["mbj_bandgap"])
```

## 4. Natural Language Agent

```python
from agapi.agents import AGAPIAgent

agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))
response = agent.query_sync("What is the bandgap of Silicon?")
print(response)
```

## 5. Multi-Step Workflows

```python
agent.query_sync("""
1. Find all GaN materials in JARVIS-DFT
2. Get POSCAR for the most stable one
3. Make a 2x1x1 supercell
4. Substitute one Ga with Al
5. Generate powder XRD pattern
6. Optimize structure with ALIGNN-FF
7. Predict properties with ALIGNN
""", max_context_messages=20, verbose=True)
```

## 6. Browse Web Apps

Visit [atomgpt.org/apps](https://atomgpt.org/apps) for 50+ interactive apps — no code needed.

## Next Steps

- [Authentication](authentication.md) — API key details
- [Python Client](../api/python-client.md) — All functions
- [AGAPI Agents](../api/agents.md) — LLM agent setup
- [Tutorials](../tutorials/) — Step-by-step guides
