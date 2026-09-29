---
title: Tokenizer Playground
---

# Tokenizer Playground

Visualize how different tokenizers break text into tokens. Supports tiktoken encodings (GPT-4, GPT-3.5, GPT-2, o200k), plus character-level and whitespace tokenizers for comparison. Shows token count, character count, per-token text, and token IDs.

[:material-open-in-new: Open App](https://atomgpt.org/tokenizer){ .md-button .md-button--primary }

---

## Overview

!!! info "Data Source"
    **tiktoken** library — cl100k_base, o200k_base, gpt2, p50k_base, p50k_edit, r50k_base encodings.

## Endpoints

### `POST /tokenizer/tokenize` — Tokenize text

```bash
curl -X POST "https://atomgpt.org/tokenizer/tokenize" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -d '{"text": "SrTiO3 is a perovskite oxide", "tokenizer": "cl100k_base"}'
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `text` | string | required | Input text (max 50,000 characters) |
| `tokenizer` | string | `cl100k_base` | Tokenizer name (see below) |

**Available tokenizers:**

| Name | Description |
|------|-------------|
| `gpt-4 / gpt-4o / gpt-3.5-turbo` | cl100k_base (GPT-4/3.5 family) |
| `gpt-4o (o200k)` | o200k_base (GPT-4o optimized) |
| `gpt-2` | GPT-2 BPE tokenizer |
| `cl100k_base` | Direct encoding name |
| `o200k_base` | Direct encoding name |
| `p50k_base` | Codex-era encoding |
| `character` | Character-level (1 char = 1 token) |
| `whitespace` | Whitespace + punctuation split |

**Response:**

```json
{
  "tokenizer": "cl100k_base",
  "text": "SrTiO3 is a perovskite oxide",
  "n_tokens": 9,
  "n_chars": 28,
  "tokens": ["Sr", "Ti", "O", "3", " is", " a", " per", "ovsk", "ite oxide"],
  "token_ids": [21521, 46465, 46, 18, 374, 264, 824, 17487, 1029]
}
```

---

## Python Examples

=== "Tokenize"

    ```python
    import requests

    response = requests.post(
        "https://atomgpt.org/tokenizer/tokenize",
        headers={
            "Authorization": "Bearer sk-XYZ",
            "Content-Type": "application/json",
        },
        json={"text": "SrTiO3 is a perovskite oxide", "tokenizer": "cl100k_base"},
    )
    data = response.json()
    print(f"Tokens: {data['n_tokens']}, Chars: {data['n_chars']}")
    for tok, tid in zip(data["tokens"], data["token_ids"]):
        print(f"  [{tid}] {repr(tok)}")
    ```

=== "Compare tokenizers"

    ```python
    import requests

    text = "La2CuO4 superconductor Tc=40K"
    H = {"Authorization": "Bearer sk-XYZ", "Content-Type": "application/json"}
    for tok in ["cl100k_base", "o200k_base", "gpt-2", "character"]:
        r = requests.post("https://atomgpt.org/tokenizer/tokenize",
            headers=H, json={"text": text, "tokenizer": tok})
        d = r.json()
        print(f"  {tok}: {d['n_tokens']} tokens")
    ```

## AGAPI Agent

```python
from agapi.agents import AGAPIAgent
import os
agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))
response = agent.query_sync("Tokenize SrTiO3 with GPT-4 tokenizer")
print(response)
```

## References

- [OpenAI tiktoken](https://github.com/openai/tiktoken)
- [atomgptlab/jarvis](https://github.com/atomgptlab/jarvis)
