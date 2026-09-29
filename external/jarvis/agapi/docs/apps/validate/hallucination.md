---
title: Hallucination Detector
---

# Hallucination Detector

Verify academic references in LLM-generated text against Semantic Scholar. Extracts references using LLM-based structured extraction (with regex fallback), then checks each title against the Semantic Scholar API with composite scoring: 60% title fuzzy match + 25% author match + 15% journal match. Supports text input or PDF upload. Results stream progressively as each reference is verified.

[:material-open-in-new: Open App](https://atomgpt.org/hallucination_detector){ .md-button .md-button--primary }

---

## Overview

The Hallucination Detector addresses fabricated academic references in LLM-generated text. The pipeline is: (1) extract references from the bibliography section using an LLM (OpenAI SDK with structured JSON extraction), falling back to regex parsing if LLM fails; (2) for each reference, search Semantic Scholar's paper search API; (3) compute a composite verification score using rapidfuzz token_set_ratio on title, author last-name matching, and journal/venue matching; (4) classify as "verified" (≥threshold), "partial" (≥60), or "likely hallucinated" (<60).

!!! info "Data Source"
    **Semantic Scholar API** — `api.semanticscholar.org/graph/v1/paper/search` for paper verification.
    **LLM** — OpenAI-compatible endpoint for structured reference extraction.
    **rapidfuzz** — `token_set_ratio` for fuzzy title/journal matching.

## Endpoints

### `POST /hallucination/check_stream` — Verify references in text

Upload text or a PDF containing academic references. The detector extracts references, then verifies each against Semantic Scholar. Results stream as NDJSON with a configurable delay between API calls.

```bash
curl -X POST "https://atomgpt.org/hallucination/check_stream" \
  -H "Authorization: Bearer sk-XYZ" \
  -F 'text=This paper discusses materials discovery using AI.

References
[1] Kamal Choudhary, Brian DeCost, and Francesca Tavazza. Benchmarking graph neural networks for materials chemistry. npj Computational Materials, 6(1), 2020.
[2] Kamal Choudhary. AtomGPT: Atomistic generative pretrained transformer for forward and inverse materials design. The Journal of Physical Chemistry Letters, 15(27):6909-6917, 2024.
[3] Fake Q. Author. Quantum blockchain neural networks for perpetual motion machines. Nature of Nonsense, 99:1-99, 2099.' \
  -F "top_k=5" \
  -F "threshold=80" \
  -F "sleep_sec=2.0"
```

Verify a PDF:

```bash
curl -X POST "https://atomgpt.org/hallucination/check_stream" \
  -H "Authorization: Bearer sk-XYZ" \
  -F "file=@paper.pdf" \
  -F "top_k=5" \
  -F "threshold=80"
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `text` | string | — | Text with references section (provide `text` or `file`) |
| `file` | file | — | PDF file to extract and verify |
| `ss_api_key` | string | `""` | Optional Semantic Scholar API key (built-in key used by default) |
| `top_k` | int | 5 | Number of Semantic Scholar results to check per reference (1–20) |
| `threshold` | int | 80 | Composite score threshold for "verified" status (30–100) |
| `sleep_sec` | float | 2.0 | Delay between Semantic Scholar queries to avoid rate limiting (1–60) |

**Response** is streamed as NDJSON (`application/x-ndjson`) with progressive updates:

1. `{"type": "extracting", "message": "Extracting references..."}`
2. `{"type": "total", "total": N, "method_used": "llm"}` — extraction complete
3. `{"type": "checking", "index": i, "total": N, "title_guess": "..."}` — per-reference progress
4. `{"type": "result", "index": i, ...}` — per-reference verification result
5. `{"type": "done", "total": N, "method_used": "llm"}` — all checks complete

**Per-reference result fields:**

| Field | Description |
|-------|-------------|
| `status` | `"verified"` (score ≥ threshold), `"partial"` (≥ 60), or `"likely hallucinated"` (< 60) |
| `score` | Composite score (0–100): 60% title + 25% author + 15% journal |
| `title_score` | Fuzzy title match score alone |
| `author_score` | Author last-name match percentage (null if no authors extracted) |
| `journal_score` | Journal/venue fuzzy match (null if no journal extracted) |
| `year_match` | `true`/`false`/`null` — whether extracted year matches |
| `best_match` | Best matching paper title from Semantic Scholar |
| `matched_authors` | Author names from the matched paper |
| `matched_venue` | Journal/venue from the matched paper |
| `matched_year` | Publication year from the matched paper |
| `total_hits` | Total Semantic Scholar search results |
| `query` | Cleaned search query sent to Semantic Scholar |
| `reference` | Original extracted reference text |

---

## Python Examples

=== "Verify references"

    ```python
    import requests
    import json

    TEXT = """
    This paper builds on prior work in materials AI.

    References
    [1] Kamal Choudhary et al. The joint automated repository for various
        integrated simulations (JARVIS). npj Computational Materials, 6, 173, 2020.
    [2] Fake Q. Author. Quantum blockchain for perpetual motion. Nature of
        Nonsense, 99:1-99, 2099.
    """

    response = requests.post(
        "https://atomgpt.org/hallucination/check_stream",
        headers={"Authorization": "Bearer sk-XYZ"},
        data={
            "text": TEXT,
            "top_k": "5",
            "threshold": "80",
            "sleep_sec": "2.0",
        },
        stream=True,
    )

    verified, flagged = 0, 0
    for line in response.iter_lines():
        if not line:
            continue
        chunk = json.loads(line)
        if chunk["type"] == "result":
            status = chunk["status"]
            icon = "✓" if status == "verified" else "~" if status == "partial" else "✗"
            print(f"  {icon} [{chunk['score']:.0f}%] {chunk['reference'][:60]}")
            print(f"     → {chunk['best_match'][:60]}")
            if status == "verified":
                verified += 1
            else:
                flagged += 1
        elif chunk["type"] == "done":
            print(f"\nTotal: {chunk['total']}, Verified: {verified}, Flagged: {flagged}")
    ```

=== "Verify PDF"

    ```python
    import requests
    import json

    with open("paper.pdf", "rb") as f:
        response = requests.post(
            "https://atomgpt.org/hallucination/check_stream",
            headers={"Authorization": "Bearer sk-XYZ"},
            files={"file": ("paper.pdf", f, "application/pdf")},
            data={"threshold": "75"},
            stream=True,
        )

    hallucinated = []
    for line in response.iter_lines():
        if not line:
            continue
        chunk = json.loads(line)
        if chunk["type"] == "result" and chunk["status"] == "likely hallucinated":
            hallucinated.append({
                "ref": chunk["reference"][:80],
                "score": chunk["score"],
                "best_match": chunk["best_match"][:60],
            })

    if hallucinated:
        print(f"Found {len(hallucinated)} potentially hallucinated references:")
        for h in hallucinated:
            print(f"  ✗ [{h['score']:.0f}%] {h['ref']}")
            print(f"     Best match: {h['best_match']}")
    else:
        print("All references verified!")
    ```

=== "Batch check files"

    ```python
    import requests
    import json
    import glob

    for pdf_path in glob.glob("papers/*.pdf"):
        with open(pdf_path, "rb") as f:
            response = requests.post(
                "https://atomgpt.org/hallucination/check_stream",
                headers={"Authorization": "Bearer sk-XYZ"},
                files={"file": (pdf_path, f, "application/pdf")},
                data={"threshold": "80"},
                stream=True,
            )

        results = {"verified": 0, "partial": 0, "hallucinated": 0}
        for line in response.iter_lines():
            if line:
                chunk = json.loads(line)
                if chunk["type"] == "result":
                    if chunk["status"] == "verified":
                        results["verified"] += 1
                    elif chunk["status"] == "partial":
                        results["partial"] += 1
                    else:
                        results["hallucinated"] += 1

        total = sum(results.values())
        print(f"{pdf_path}: {total} refs — {results}")
    ```

## AGAPI Agent [WIP]

```python
from agapi.agents import AGAPIAgent
import os

agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))
response = agent.query_sync("Verify the references in this text for hallucinations")
print(response)
```

## References

- [atomgptlab](https://github.com/atomgptlab)



