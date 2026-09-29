---
title: SDSS SkyServer Explorer
---

# SDSS SkyServer Explorer

Query the Sloan Digital Sky Survey (DR18) — 4M+ spectra of stars, galaxies, and quasars. Supports custom SQL queries (CasJobs syntax), radial/cone search by sky coordinates, and sky image cutouts. Preset queries for bright galaxies, quasars (z>2), cool stars, AGN hosts, and white dwarfs.

[:material-open-in-new: Open App](https://atomgpt.org/sdss){ .md-button .md-button--primary }

---

## Overview

!!! info "Data Source"
    **SDSS SkyServer DR18** REST API (skyserver.sdss.org).

## Endpoints

### `POST /sdss/query` — Run SQL query

```bash
curl -X POST "https://atomgpt.org/sdss/query" \
  -H "Content-Type: application/json" \
  -d '{"preset": "galaxies_bright"}'
```

Or custom SQL:

```bash
curl -X POST "https://atomgpt.org/sdss/query" \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT TOP 10 p.objID, p.ra, p.dec, s.z AS redshift FROM PhotoObj p JOIN SpecObj s ON s.bestobjid=p.objid WHERE s.class=\'GALAXY\'"}'
```

### `GET /sdss/query` — API key auth

```bash
curl "https://atomgpt.org/sdss/query?preset=quasars&APIKEY=sk-XYZ"
```

---

### `POST /sdss/radial_search` — Cone search

```bash
curl -X POST "https://atomgpt.org/sdss/radial_search" \
  -H "Content-Type: application/json" \
  -d '{"ra": 197.614, "dec": 18.438, "radius": 1.0, "limit": 50}'
```

### `GET /sdss/image_url` — Sky image cutout URL

```bash
curl "https://atomgpt.org/sdss/image_url?ra=197.614&dec=18.438&scale=0.4&width=256&height=256"
```

**Presets:** `galaxies_bright, quasars, stars_cool, supernovae_host, white_dwarfs`.


## AGAPI Agent

```python
from agapi.agents import AGAPIAgent
import os
agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))
response = agent.query_sync("Show sdss skyserver explorer data")
print(response)
```

## References

- Sloan Digital Sky Survey [:material-link: DOI](https://www.sdss.org)
- [atomgptlab/jarvis](https://github.com/atomgptlab/jarvis)
