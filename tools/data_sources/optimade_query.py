#!/usr/bin/env python3
"""Camada computacional: consulta NOMAD, Materials Cloud, Materials Project, OQMD, AFLOW e JARVIS pelo padrão OPTIMADE.

Serve para descritores/estruturas de referência (Au metálico, óxidos/cloretos de Au, carbono/grafite, Au–C–O…) —
NÃO substitui os dados experimentais do projeto. Usa o cliente oficial ``optimade`` (código de referência em
external/data-access/optimade-python-tools), que descobre as URLs de cada provedor pelo registro providers.optimade.org.

Instalação: tools/setup_env.sh data-sources && source .venvs/data-sources/bin/activate

Exemplos:
    python tools/data_sources/optimade_query.py                                   # consultas padrão do projeto
    python tools/data_sources/optimade_query.py --filter 'elements HAS ALL "Au","O" AND nelements=2' --providers mp,oqmd
    python tools/data_sources/optimade_query.py --count                           # só conta resultados por provedor
    python tools/data_sources/optimade_query.py --dry-run                          # mostra filtros e provedores

Materials Project nativo (mais propriedades): mp-api com MP_API_KEY; JARVIS nativo: jarvis-tools
(``from jarvis.db.figshare import data; d = data("dft_3d")``).
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "outputs", "optimade")
# IDs do registro OPTIMADE: mp=Materials Project, oqmd, aflow, nmd=NOMAD, mcloud=Materials Cloud, jarvis
PROVIDERS = ["mp", "oqmd", "aflow", "nmd", "mcloud", "jarvis"]
DEFAULT_FILTERS = {
    "au_elemental": 'elements HAS ONLY "Au"',
    "au_oxides_chlorides": '(elements HAS ALL "Au","O" OR elements HAS ALL "Au","Cl") AND nelements<=3',
    "au_carbon": 'elements HAS ALL "Au","C" AND nelements<=3',
    "carbon_oxygen_hydrogen": 'elements HAS ONLY "C","O","H" AND nsites<=200',
}
FIELDS = ["id", "chemical_formula_reduced", "chemical_formula_descriptive", "nelements", "elements", "nsites",
          "nperiodic_dimensions", "last_modified"]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--filter", help="filtro OPTIMADE (padrão: consultas do projeto)")
    ap.add_argument("--providers", default=",".join(PROVIDERS))
    ap.add_argument("--max-per-provider", type=int, default=200)
    ap.add_argument("--count", action="store_true")
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    filters = {"custom": a.filter} if a.filter else DEFAULT_FILTERS
    providers = [p.strip() for p in a.providers.split(",") if p.strip()]
    if a.dry_run:
        print(json.dumps({"providers": providers, "filters": filters}, indent=2, ensure_ascii=False))
        return
    try:
        from optimade.client import OptimadeClient
    except ImportError:
        sys.exit("instale o cliente: tools/setup_env.sh data-sources && source .venvs/data-sources/bin/activate")

    client = OptimadeClient(include_providers=providers, max_results_per_provider=a.max_per_provider, silent=True)
    os.makedirs(a.out, exist_ok=True)
    for name, flt in filters.items():
        if a.count:
            res = client.count(flt)["structures"][flt]
            for url, n in sorted(res.items()):
                print(f"{name:26} {n!s:>8}  {url}")
            continue
        res = client.get(flt, response_fields=FIELDS)["structures"][flt]
        path = os.path.join(a.out, f"{name}.csv")
        n = 0
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=["base_url"] + FIELDS)
            w.writeheader()
            for url, qr in res.items():
                for e in qr.get("data") or []:
                    attrs = e.get("attributes", {})
                    row = {"base_url": url, "id": e.get("id", "")}
                    row.update({k: (json.dumps(attrs[k]) if isinstance(attrs.get(k), list) else attrs.get(k, ""))
                                for k in FIELDS[1:]})
                    w.writerow(row)
                    n += 1
                for err in qr.get("errors") or []:
                    print(f"  aviso {url}: {str(err)[:160]}", file=sys.stderr)
        print(f"{name}: {n} estruturas -> {os.path.relpath(path, ROOT)}")


if __name__ == "__main__":
    main()
