#!/usr/bin/env python3
"""Remove as saídas (imagens, tabelas, logs) dos notebooks Jupyter de uma pasta, mantendo o código e o texto.

Usado por tools/fetch_external.sh em repositórios de tutoriais cujo tamanho vem quase todo das saídas
(ex.: jarvis-tools-notebooks: 107 MB -> 14 MB). Uso: python tools/strip_notebook_outputs.py <pasta> [...]
"""
from __future__ import annotations

import glob
import json
import os
import sys


def strip(path: str) -> bool:
    try:
        with open(path, encoding="utf-8") as fh:
            nb = json.load(fh)
    except (OSError, ValueError) as err:   # notebook corrompido upstream: deixa como está
        print(f"ignorado {path}: {err}", file=sys.stderr)
        return False
    for cell in nb.get("cells", []):
        if cell.get("cell_type") == "code":
            cell["outputs"] = []
            cell["execution_count"] = None
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(nb, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    n = sum(strip(p) for d in sys.argv[1:] for p in glob.glob(os.path.join(d, "**", "*.ipynb"), recursive=True))
    print(f"{n} notebooks sem saídas")
