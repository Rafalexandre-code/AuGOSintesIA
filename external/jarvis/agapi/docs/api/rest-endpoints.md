---
title: REST Endpoints
---

# REST Endpoints

Every AtomGPT.org web app exposes REST API endpoints. All `POST` endpoints require authentication.

## Authentication

```
Authorization: Bearer YOUR_API_KEY
```

Get your key at [AtomGPT.org](https://atomgpt.org) → Account → Settings.

## Common Patterns

Every app follows the same URL pattern:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/{app_name}` | HTML web interface |
| `POST` | `/{app_name}/search` | Search/query |
| `POST` | `/{app_name}/compute` | Run computation |
| `GET` | `/{app_name}/detail/{id}` | Get single item |

## Key Endpoints

### Materials Explorer

```
POST /materials_explorer/search
```
```json
{
  "formula": "SrTiO3",
  "elements": ["Ti", "O"],
  "element_mode": "all",
  "bandgap_min": 0.5,
  "bandgap_max": 3.0
}
```

### ALIGNN Predictor

```
POST /alignn/predict
```
```json
{"jid": "JVASP-1002", "model": "jv_optb88vdw_bandgap"}
```

### ALIGNN-FF

```
POST /alignn_ff_dynamics/relax
POST /alignn_ff_dynamics/single_point
POST /alignn_ff_dynamics/md
```
```json
{"poscar": "Si\n1.0\n0 2.734 2.734\n..."}
```

### SlakoNet

```
POST /slakonet/compute
```
```json
{"poscar": "Si\n1.0\n...", "kpath_density": 20}
```

### XRD / DiffractGPT

```
POST /pxrd/compute
POST /pxrd/match
```
```json
{"jid": "JVASP-1002"}
{"formula": "Si", "xrd_data": "28.44 1.00\n47.30 0.55"}
```

### Structure Tools

```
POST /heterostructure/generate
POST /quantum/vqe
POST /reaction_network/balance
POST /hea/compute
```

### OPTIMADE

```
POST /optimade_explorer/query
```
```json
{"filter_string": "elements HAS ANY \"Si\",\"Ge\" AND nelements=2"}
```

## Rate Limits

- 100 requests/minute per API key
- Larger queries (bandstructure, MD) may take 10-60 seconds

## Error Responses

```json
{"detail": "Error description here"}
```

Common HTTP status codes: `401` (unauthorized), `400` (bad request), `404` (not found), `500` (server error).
