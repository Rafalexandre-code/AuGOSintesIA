#!/usr/bin/env python3
"""Busca no corpus dos 65 artigos do projeto (literature/chunks.jsonl) por BM25 — sem dependências.

Uso:
    python tools/search_literature.py "oxygen groups gold nucleation graphene oxide"
    python tools/search_literature.py "qNEHVI batch noise" -k 5 --tipo texto
    python tools/search_literature.py "Raman ID/IG" --json          # saída para outro programa (ex.: prompt de LLM)
Cada resultado traz título, ano, DOI e páginas — cite sempre `titulo` + `paginas`.
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CHUNKS = os.path.join(ROOT, "literature", "chunks.jsonl")
_TOK = re.compile(r"[a-z0-9]+(?:[/-][a-z0-9]+)*")


def tokens(text: str) -> list[str]:
    return _TOK.findall(text.lower())


class BM25:
    def __init__(self, docs: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.docs, self.k1, self.b = docs, k1, b
        self.avg = sum(map(len, docs)) / max(len(docs), 1)
        df = collections.Counter(t for d in docs for t in set(d))
        n = len(docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}
        self.tf = [collections.Counter(d) for d in docs]

    def scores(self, query: list[str]) -> list[float]:
        out = []
        for d, tf in zip(self.docs, self.tf):
            s, norm = 0.0, self.k1 * (1 - self.b + self.b * len(d) / self.avg)
            for t in query:
                f = tf.get(t)
                if f:
                    s += self.idf[t] * f * (self.k1 + 1) / (f + norm)
            out.append(s)
        return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("query")
    ap.add_argument("-k", type=int, default=8)
    ap.add_argument("--tipo", help="filtra o tipo do trecho (texto, misto, referência, figura…)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    chunks = [json.loads(line) for line in open(CHUNKS, encoding="utf-8")]
    if a.tipo:
        chunks = [c for c in chunks if c.get("tipo") == a.tipo]
    else:  # listas de referências poluem a busca
        chunks = [c for c in chunks if c.get("tipo") != "referência"]
    chunks = [c for c in chunks if len(tokens(c.get("texto", ""))) >= 20]  # fragmentos de figura quase vazios
    bm = BM25([tokens(f"{c.get('titulo', '')} {c.get('secao', '')} {c.get('texto', '')}") for c in chunks])
    sc = bm.scores(tokens(a.query))
    best = sorted(range(len(chunks)), key=sc.__getitem__, reverse=True)[:a.k]
    hits = [{**{k: chunks[i].get(k) for k in ("titulo", "ano", "doi", "paginas", "secao", "texto")},
             "score": round(sc[i], 2)} for i in best if sc[i] > 0]
    if a.json:
        print(json.dumps(hits, ensure_ascii=False, indent=1))
        return
    for h in hits:
        print(f"[{h['score']}] {h['titulo']} ({h['ano']}) p. {h['paginas']} — {h.get('secao') or ''}\n"
              f"    doi:{h['doi']}\n    {' '.join(h['texto'].split())[:400]}…\n")


if __name__ == "__main__":
    main()
