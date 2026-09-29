---
title: Apps Overview
description: All 50+ AtomGPT web applications organized by category
---
# Apps Overview

AtomGPT.org hosts **54 web applications** for materials science, AI, and scientific exploration. Each app provides a web interface, REST API endpoints, and Python examples for agentic workflows.

## Categories

| Category | Apps | Description |
|----------|------|-------------|
| [**Explore**](explore/) | 32 | Browse databases, search materials, visualize properties, literature, astronomy |
| [**Build**](build/) | 5 | Construct structures, build polymers, design workflows, web terminal |
| [**Predict**](predict/) | 6 | ML predictions, force fields, quantum algorithms |
| [**Characterize**](characterize/) | 3 | Match spectra, analyze images, identify structures |
| [**Apply**](apply/) | 8 | Screen materials, predict hardness, melting points, corrosion stability |
| [**Validate**](validate/) | 2 | Verify AI outputs, check references |

## Architecture

Every app follows the same pattern:

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  HTML/JS    │────▶│  FastAPI      │────▶│  JARVIS     │
│  Frontend   │◀────│  Backend      │◀────│  Data/ML    │
└─────────────┘     └──────────────┘     └─────────────┘
       │                    │
       ▼                    ▼
   Web Browser         REST API
                    (for agents/scripts)
```

- **Frontend**: Single HTML file with embedded CSS/JS, dark theme
- **Backend**: FastAPI route with authentication, served from `custom_routes/`
- **Data**: JARVIS-DFT (76K materials), ALIGNN models, Wannier TBH databases, external APIs (RCSB PDB, OMIM, SDSS, arXiv, Crossref)
