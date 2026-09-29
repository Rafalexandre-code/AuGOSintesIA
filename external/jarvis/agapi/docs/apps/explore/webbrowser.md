---
title: Web Browser
---

# Web Browser

Search the web via DuckDuckGo and fetch/extract content from any URL. Returns clean text, links, images, and metadata. Supports configurable extraction options.

[:material-open-in-new: Open App](https://atomgpt.org/webbrowser){ .md-button .md-button--primary }

---

## Overview

!!! info "Data Source"
    **DuckDuckGo Search** (no API key) + **BeautifulSoup** (HTML parsing).

## Endpoints

### `POST /webbrowser/search` — Search the web

```bash
curl -X POST "https://atomgpt.org/webbrowser/search" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -d '{"query": "perovskite solar cells 2024", "max_results": 10}'
```

**Response:** `query, total, results[]` (title, url, snippet).

---

### `POST /webbrowser/fetch` — Fetch and extract URL content

```bash
curl -X POST "https://atomgpt.org/webbrowser/fetch" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://en.wikipedia.org/wiki/Perovskite", "extract_text": true, "extract_links": true}'
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `url` | string | required | URL to fetch |
| `extract_text` | bool | true | Extract clean text (max 10K chars) |
| `extract_links` | bool | false | Extract links (max 200) |
| `extract_images` | bool | false | Extract images (max 100) |

**Response:** `url, status_code, content_type, title, meta_description, text, word_count, links[], images[], fetch_time_s`.


## AGAPI Agent

```python
from agapi.agents import AGAPIAgent
import os
agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))
response = agent.query_sync("Show web browser data")
print(response)
```

## References

- DuckDuckGo Search [:material-link: DOI](https://github.com/deedy5/duckduckgo_search)
- [atomgptlab/jarvis](https://github.com/atomgptlab/jarvis)
