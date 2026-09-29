---
title: Unit Converter
---

# Unit Converter

Convert between units for the seven SI fundamental quantities: Length, Mass, Time, Electric Current, Temperature, Amount of Substance, and Luminous Intensity. All conversion logic is client-side JavaScript; the backend only serves the HTML template.

[:material-open-in-new: Open App](https://atomgpt.org/unit_converter){ .md-button .md-button--primary }

---

## Overview

!!! info "Data Source"
    Client-side only — no backend data.

## Endpoint

### `GET /unit_converter` — HTML page

```bash
curl "https://atomgpt.org/unit_converter"
```

This is a client-side-only app with no API endpoints. The backend serves only the HTML page containing JavaScript unit conversion logic.

!!! note
    No authentication required. No POST/JSON endpoints — all computation happens in-browser.

---

## Supported Quantity Categories

Length, Mass, Time, Electric Current, Temperature, Amount of Substance, Luminous Intensity.

---

## AGAPI Agent

```python
from agapi.agents import AGAPIAgent
import os
agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))
response = agent.query_sync("Convert 1 angstrom to nanometers")
print(response)
```

## References

- [NIST SI Units](https://www.nist.gov/pml/owm/metric-si/si-units)
- [atomgptlab/jarvis](https://github.com/atomgptlab/jarvis)
