#!/usr/bin/env python3
"""Encurta nomes de arquivo cujo caminho dentro deste repositório passa de um limite (padrão 180 caracteres).

O Windows não faz checkout de caminhos com mais de ~260 caracteres (sem `git config core.longpaths true`), e o
repositório costuma ficar numa pasta de projetos do usuário (~45 caracteres). Usado
por tools/fetch_external.sh em cada cópia de external/. O nome novo mantém o começo do original, acrescenta um
hash curto (estável) e preserva a extensão; a correspondência fica em NOMES_ENCURTADOS.txt na raiz da cópia.

Uso: python tools/shorten_long_paths.py <pasta_da_copia> <prefixo_no_repo> [limite]
     ex.: python tools/shorten_long_paths.py /tmp/x/jarvis-tools-notebooks external/jarvis/jarvis-tools-notebooks 180
"""
from __future__ import annotations

import hashlib
import os
import sys


def shorten(src: str, prefix: str, limit: int = 180) -> list[tuple[str, str]]:
    renamed = []
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d != ".git"]
        for f in files:
            rel = os.path.relpath(os.path.join(root, f), src).replace(os.sep, "/")
            full = f"{prefix}/{rel}"
            excess = len(full) - limit
            if excess <= 0:
                continue
            stem, ext = os.path.splitext(f)
            tag = hashlib.sha1(f.encode()).hexdigest()[:8]
            keep = len(stem) - excess - len(tag) - 1
            if keep < 8:
                raise SystemExit(f"não dá para encurtar só o nome do arquivo (pasta longa demais): {full}")
            new = f"{stem[:keep].rstrip('_ -.,')}_{tag}{ext}"
            os.rename(os.path.join(root, f), os.path.join(root, new))
            renamed.append((rel, os.path.relpath(os.path.join(root, new), src).replace(os.sep, "/")))
    if renamed:
        with open(os.path.join(src, "NOMES_ENCURTADOS.txt"), "w", encoding="utf-8") as fh:
            fh.write(f"# Arquivos renomeados por tools/shorten_long_paths.py (caminho no repositório > {limit} caracteres,\n"
                     "# para o checkout funcionar no Windows). original<TAB>novo\n")
            for old, new in sorted(renamed):
                fh.write(f"{old}\t{new}\n")
    return renamed


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    done = shorten(sys.argv[1], sys.argv[2].rstrip("/"), int(sys.argv[3]) if len(sys.argv) > 3 else 180)
    for old, new in done:
        print(f"encurtado: {old} -> {new}")
