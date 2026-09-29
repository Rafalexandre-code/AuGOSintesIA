---
title: AI Detector
---

# AI Detector

Detect AI-generated text using a hybrid approach: statistical analysis (sentence uniformity, vocabulary repetition, AI marker phrases, punctuation diversity) combined with an LLM judge for style classification. Supports text input or PDF/TXT file upload.

[:material-open-in-new: Open App](https://atomgpt.org/ai_detector){ .md-button .md-button--primary }

---

## Overview

The AI Detector computes 6 statistical signals that distinguish AI-generated text from human writing, then optionally asks an LLM to analyze writing style. The final score is a weighted combination (60% LLM + 40% statistical when LLM is enabled). Verdicts range from "human" to "ai" based on the combined probability.

**Statistical signals:** burstiness (sentence length variance), vocabulary richness (type-token ratio), word formality (avg word length), sentence starter diversity, AI marker phrase density, punctuation diversity.

!!! info "Data Source"
    **Statistical analysis** — built-in heuristics.
    **LLM judge** — configurable LLM backend for style classification.

## Endpoints

### `POST /ai_detector/scan` — Scan text for AI content

Upload text or a file (PDF/TXT) for AI detection. Uses multipart form data.

```bash
curl -X POST "https://atomgpt.org/ai_detector/scan" \
  -H "Authorization: Bearer sk-XYZ" \
  -F "text=Artificial intelligence has become an increasingly important tool in modern scientific research. It is worth noting that machine learning methods have shown remarkable potential in materials discovery. Furthermore, the integration of large language models into scientific workflows represents a groundbreaking development." \
  -F "use_llm=true"
```

Scan without LLM (statistical only, faster):

```bash
curl -X POST "https://atomgpt.org/ai_detector/scan" \
  -H "Authorization: Bearer sk-XYZ" \
  -F "text=So I was trying to get ALIGNN to work on my perovskite dataset and it kept crashing. Turns out I had NaN values in 3 of my structures. Took me two days to figure that out!" \
  -F "use_llm=false"
```

Scan a PDF file:

```bash
curl -X POST "https://atomgpt.org/ai_detector/scan" \
  -H "Authorization: Bearer sk-XYZ" \
  -F "file=@paper.pdf" \
  -F "use_llm=true"
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `text` | string | — | Text to analyze (provide `text` or `file`) |
| `file` | file | — | PDF or TXT file to analyze |
| `use_llm` | string | `"true"` | Use LLM judge (`"true"` or `"false"`) |

**Response** is streamed as NDJSON (`application/x-ndjson`) with progressive updates:

1. `{"type": "status", "message": "Running statistical analysis..."}`
2. `{"type": "stats", "data": {...}}` — statistical scores
3. `{"type": "status", "message": "Running LLM analysis..."}` (if use_llm)
4. `{"type": "llm", "data": {...}}` — LLM verdict (if use_llm)
5. `{"type": "result", ...}` — final combined result

**Final result fields:**

| Field | Description |
|-------|-------------|
| `ai_probability` | Combined AI probability (0–100%) |
| `verdict` | `"human"`, `"likely_human"`, `"mixed"`, `"likely_ai"`, or `"ai"` |
| `stat_probability` | Statistical-only AI probability |
| `llm_probability` | LLM-only AI probability (null if disabled) |
| `statistical.scores` | Per-signal breakdown (burstiness, vocabulary, word_length, sentence_starters, ai_phrases, punctuation) |
| `llm_judge.reasoning` | LLM explanation |
| `llm_judge.signals` | Per-signal indicators from LLM |

---

## Python Examples

=== "Scan text"

    ```python
    import requests

    response = requests.post(
        "https://atomgpt.org/ai_detector/scan",
        headers={"Authorization": "Bearer sk-XYZ"},
        data={
            "text": "It is important to note that machine learning has shown remarkable potential...",
            "use_llm": "true",
        },
    )
    # Parse NDJSON stream
    for line in response.text.strip().split("\n"):
        if line.strip():
            import json
            chunk = json.loads(line)
            if chunk.get("type") == "result":
                print(f"Verdict: {chunk['verdict']}")
                print(f"AI probability: {chunk['ai_probability']}%")
                print(f"  Statistical: {chunk['stat_probability']}%")
                print(f"  LLM: {chunk.get('llm_probability', 'N/A')}%")
    ```

=== "Scan PDF"

    ```python
    import requests

    with open("paper.pdf", "rb") as f:
        response = requests.post(
            "https://atomgpt.org/ai_detector/scan",
            headers={"Authorization": "Bearer sk-XYZ"},
            files={"file": ("paper.pdf", f, "application/pdf")},
            data={"use_llm": "true"},
        )
    import json
    for line in response.text.strip().split("\n"):
        if line.strip():
            chunk = json.loads(line)
            if chunk.get("type") == "result":
                print(f"Verdict: {chunk['verdict']} ({chunk['ai_probability']}%)")
    ```

## AGAPI Agent [WIP]

```python
from agapi.agents import AGAPIAgent
import os

agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))
response = agent.query_sync("Check if this text is AI-generated: Furthermore, it is essential to note...")
print(response)
```

## References

- [atomgptlab](https://github.com/atomgptlab)
