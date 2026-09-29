---
title: AGAPI Agents
---

# AGAPI Agents

The AGAPI Agent uses natural language to orchestrate multi-step materials science workflows.

## Setup

```python
import os
from agapi.agents import AGAPIAgent

agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))
```

## Natural Language Queries

```python
# Simple property lookup
agent.query_sync("What is the bandgap of Silicon?")

# Database search
agent.query_sync("Show me all MgB2 polymorphs")
agent.query_sync("Find materials with bulk modulus > 200 GPa")

# Comparisons
agent.query_sync("Compare bandgaps across BN, AlN, GaN, InN")

# Predictions
agent.query_sync("Predict properties of JVASP-1002 with ALIGNN")

# Characterization
agent.query_sync("Identify the phase from this XRD pattern for Silicon")
agent.query_sync("Analyze this STEM image of a GaN thin film")

# Literature
agent.query_sync("Find recent papers on perovskite solar cells on arXiv")
```

## Multi-Step Workflows

The agent chains multiple tools automatically:

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

```python
agent.query_sync("""
Create a GaN/AlN heterostructure interface:
1. Find GaN (most stable)
2. Find AlN (most stable)
3. Generate (001)/(001) interface
4. Show POSCAR
""", max_context_messages=20, verbose=True)
```

## Supported LLM Backends

Set `model` when initializing the agent:

```python
agent = AGAPIAgent(
    api_key=os.environ.get("AGAPI_KEY"),
    model="openai/gpt-oss-20b"
)
```

| Provider | Model |
|----------|-------|
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

## Architecture

AGAPI implements a modular architecture separating the **reasoning layer** (LLM brain) from the **execution layer** (scientific tools and databases) through a unified REST API interface.

```
┌──────────────────┐
│  Natural Language │  ← user prompt
└────────┬─────────┘
         ▼
┌──────────────────┐
│   LLM Backend    │  ← GPT-OSS / Llama / Gemini / DeepSeek
│  (Reasoning)     │
└────────┬─────────┘
         ▼
┌──────────────────┐
│  AGAPI Functions │  ← query_by_formula, alignn_predict, ...
│  (Execution)     │
└────────┬─────────┘
         ▼
┌──────────────────┐
│  AtomGPT.org API │  ← JARVIS-DFT, ALIGNN, ALIGNN-FF, ...
│  (Data + Models) │
└──────────────────┘
```

!!! info "AGAPI Name"
    **AGAPI (ἀγάπη)** is a Greek word meaning *unconditional love*.
