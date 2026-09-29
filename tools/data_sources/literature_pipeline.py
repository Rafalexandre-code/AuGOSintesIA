#!/usr/bin/env python3
"""Pipeline bibliográfico: OpenAlex → Crossref → Unpaywall → texto integral OA (PDF / XML do PMC) → extração.

Etapas (cada uma lê a saída da anterior em --out, padrão outputs/literature_pipeline/):
  search   OpenAlex: busca booleana em título+resumo, filtros de ano, citações, DOI, acesso aberto; ordena por relevância
  crossref metadados por DOI (editora, licenças, links de texto integral, relações de material suplementar, retratações)
  oa       Unpaywall: melhor local de acesso aberto (PDF/landing), licença, versão
  fetch    baixa PDFs OA e XML JATS do PubMed Central (quando há PMCID)
  all      as quatro em sequência
Resultado: works.csv (uma linha por DOI, deduplicado; marca o que já está em literature/, no dataset de Cruse e na
semente) + fulltext/ + to_extract.jsonl (fila para o extrator LLM — NanoExtractor em
projects/literature-llm/Synthesis-Properties-Database-for-Nanomaterials ou external/literature-llm/lematerial-llm-synthesis;
normalize os reagentes extraídos com tools/data_sources/reagents.py).

Identificação (recomendado; vai nos cabeçalhos/parâmetros das APIs):
  export LIT_MAILTO=seu@email          # polite pool de OpenAlex/Crossref e e-mail exigido pelo Unpaywall
  export OPENALEX_API_KEY=...          # opcional
  export NCBI_API_KEY=...              # opcional (E-utilities)

Exemplos:
  python tools/data_sources/literature_pipeline.py all --from-year 2015 --max 500
  python tools/data_sources/literature_pipeline.py search --query '("gold nanoparticle" OR AuNP) AND ("graphene oxide" OR rGO)' --oa-only
  python tools/data_sources/literature_pipeline.py search --dry-run          # só mostra a URL da consulta
Só biblioteca padrão. Precisa de rede (bloqueada no contêiner de desenvolvimento: rode localmente).
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "outputs", "literature_pipeline")
DEFAULT_QUERY = ('("gold nanoparticle" OR "gold nanoparticles" OR AuNP OR AuNPs) AND '
                 '("graphene oxide" OR GO OR rGO) AND (synthesis OR reduction OR nucleation)')
MAILTO = os.environ.get("LIT_MAILTO", "")
UA = {"User-Agent": f"AuGOSintesIA-literature/1.0 (mailto:{MAILTO or 'unknown'})"}

WORK_FIELDS = ["doi", "openalex_id", "title", "year", "venue", "type", "cited_by_count", "relevance_score", "is_oa",
               "oa_status", "oa_url", "pmcid", "has_fulltext", "datasets", "publisher", "license", "crossref_links",
               "supplement_hint", "is_retracted_or_updated", "unpaywall_pdf", "unpaywall_landing", "unpaywall_license",
               "unpaywall_version", "fulltext_file", "in_literature_corpus", "in_cruse", "in_seed", "abstract"]


# ---------------------------------------------------------------------------------------------- utilidades

def norm_doi(doi: str | None) -> str:
    if not doi:
        return ""
    d = doi.strip().lower()
    d = re.sub(r"^(https?://)?(dx\.)?doi\.org/", "", d)
    d = re.sub(r"^doi:\s*", "", d)
    return d.rstrip(".;, ")


def norm_title(t: str | None) -> str:
    return re.sub(r"[^a-z0-9]", "", (t or "").lower())


def get_json(url: str, headers: dict | None = None, retries: int = 4) -> dict | None:
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={**UA, "Accept": "application/json", **(headers or {})})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code in (429, 500, 502, 503, 504) and i < retries - 1:
                time.sleep(2 ** (i + 1))
                continue
            raise
        except urllib.error.URLError:
            if i < retries - 1:
                time.sleep(2 ** (i + 1))
                continue
            raise
    return None


def invert_abstract(inv: dict | None) -> str:
    if not inv:
        return ""
    pos = sorted((p, w) for w, ps in inv.items() for p in ps)
    return " ".join(w for _p, w in pos)


def read_jsonl(path: str) -> list[dict]:
    if not os.path.exists(path):
        sys.exit(f"falta {path}: rode a etapa anterior")
    with open(path, encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


def write_jsonl(path: str, rows) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------------------------- 1. OpenAlex

def openalex_url(query: str, from_year: int | None, to_year: int | None, oa_only: bool, min_citations: int | None,
                 cursor: str = "*", per_page: int = 200) -> str:
    flt = [f"title_and_abstract.search:{query}", "has_doi:true"]
    if from_year or to_year:
        flt.append(f"publication_year:{from_year or ''}-{to_year or ''}")
    if oa_only:
        flt.append("is_oa:true")
    if min_citations:
        flt.append(f"cited_by_count:>{min_citations - 1}")
    params = {"filter": ",".join(flt), "sort": "relevance_score:desc", "per_page": per_page, "cursor": cursor}
    if MAILTO:
        params["mailto"] = MAILTO
    if os.environ.get("OPENALEX_API_KEY"):
        params["api_key"] = os.environ["OPENALEX_API_KEY"]
    return "https://api.openalex.org/works?" + urllib.parse.urlencode(params)


def stage_search(a) -> None:
    if a.dry_run:
        print(openalex_url(a.query, a.from_year, a.to_year, a.oa_only, a.min_citations))
        return
    works, seen, cursor = [], set(), "*"
    while cursor and len(works) < a.max:
        page = get_json(openalex_url(a.query, a.from_year, a.to_year, a.oa_only, a.min_citations, cursor))
        if not page:
            break
        for w in page.get("results", []):
            doi = norm_doi(w.get("doi"))
            key = doi or norm_title(w.get("title"))
            if not key or key in seen:
                continue
            seen.add(key)
            loc = w.get("primary_location") or {}
            oa = w.get("open_access") or {}
            works.append({
                "doi": doi, "openalex_id": w.get("id", ""), "title": w.get("title") or "",
                "year": w.get("publication_year"), "venue": ((loc.get("source") or {}).get("display_name") or ""),
                "type": w.get("type", ""), "cited_by_count": w.get("cited_by_count", 0),
                "relevance_score": w.get("relevance_score"), "is_oa": oa.get("is_oa"),
                "oa_status": oa.get("oa_status", ""), "oa_url": oa.get("oa_url") or "",
                "pmcid": (w.get("ids") or {}).get("pmcid", "") or "", "has_fulltext": w.get("has_fulltext"),
                "datasets": "|".join(w.get("datasets") or []), "abstract": invert_abstract(w.get("abstract_inverted_index")),
            })
            if len(works) >= a.max:
                break
        cursor = (page.get("meta") or {}).get("next_cursor")
        print(f"OpenAlex: {len(works)} trabalhos ...", file=sys.stderr)
    os.makedirs(a.out, exist_ok=True)
    write_jsonl(os.path.join(a.out, "openalex.jsonl"), works)
    with open(os.path.join(a.out, "query.json"), "w", encoding="utf-8") as fh:
        json.dump({"query": a.query, "from_year": a.from_year, "to_year": a.to_year, "oa_only": a.oa_only,
                   "min_citations": a.min_citations, "max": a.max, "date": time.strftime("%Y-%m-%d"),
                   "n": len(works)}, fh, ensure_ascii=False, indent=2)
    print(f"-> {len(works)} trabalhos em {os.path.relpath(a.out, ROOT)}/openalex.jsonl")


# ---------------------------------------------------------------------------------------------- 2. Crossref

def stage_crossref(a) -> None:
    works = read_jsonl(os.path.join(a.out, "openalex.jsonl"))
    for i, w in enumerate(works):
        if not w["doi"]:
            continue
        q = f"?mailto={urllib.parse.quote(MAILTO)}" if MAILTO else ""
        m = (get_json(f"https://api.crossref.org/works/{urllib.parse.quote(w['doi'])}{q}") or {}).get("message", {})
        links = m.get("link") or []
        rel = m.get("relation") or {}
        w["publisher"] = m.get("publisher", "")
        w["license"] = "|".join(sorted({l.get("URL", "") for l in m.get("license") or []}))
        w["crossref_links"] = "|".join(f"{l.get('content-type', '')}={l.get('URL', '')}" for l in links)[:1000]
        w["supplement_hint"] = int(any("supplement" in k or k == "has-part" for k in rel)
                                   or any("suppl" in (l.get("URL") or "").lower() for l in links))
        w["is_retracted_or_updated"] = int(bool(m.get("update-to")) or bool(m.get("updated-by")))
        if not w.get("title") and m.get("title"):
            w["title"] = m["title"][0]
        if (i + 1) % 50 == 0:
            print(f"Crossref: {i + 1}/{len(works)}", file=sys.stderr)
        time.sleep(0.05)
    write_jsonl(os.path.join(a.out, "crossref.jsonl"), works)
    print(f"-> {len(works)} registros com metadados Crossref")


# ---------------------------------------------------------------------------------------------- 3. Unpaywall

def stage_oa(a) -> None:
    if not MAILTO:
        sys.exit("Unpaywall exige e-mail: export LIT_MAILTO=seu@email")
    works = read_jsonl(os.path.join(a.out, "crossref.jsonl"))
    for i, w in enumerate(works):
        if not w["doi"]:
            continue
        u = get_json(f"https://api.unpaywall.org/v2/{urllib.parse.quote(w['doi'])}?email={urllib.parse.quote(MAILTO)}")
        best = (u or {}).get("best_oa_location") or {}
        w["unpaywall_pdf"] = best.get("url_for_pdf") or ""
        w["unpaywall_landing"] = best.get("url_for_landing_page") or best.get("url") or ""
        w["unpaywall_license"] = best.get("license") or ""
        w["unpaywall_version"] = best.get("version") or ""
        if (i + 1) % 50 == 0:
            print(f"Unpaywall: {i + 1}/{len(works)}", file=sys.stderr)
        time.sleep(0.1)
    write_jsonl(os.path.join(a.out, "unpaywall.jsonl"), works)
    print(f"-> {sum(bool(w.get('unpaywall_pdf')) for w in works)} com PDF OA de {len(works)}")


# ---------------------------------------------------------------------------------------------- 4. texto integral

def _safe(doi: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", doi)


def stage_fetch(a) -> None:
    works = read_jsonl(os.path.join(a.out, "unpaywall.jsonl"))
    fdir = os.path.join(a.out, "fulltext")
    os.makedirs(fdir, exist_ok=True)
    queue = []
    for w in works:
        w["fulltext_file"] = ""
        if w.get("pmcid"):
            pmc = re.sub(r"\D", "", w["pmcid"].rsplit("/", 1)[-1])
            url = ("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&rettype=xml&id=" + pmc
                   + (f"&api_key={os.environ['NCBI_API_KEY']}" if os.environ.get("NCBI_API_KEY") else ""))
            out = os.path.join(fdir, _safe(w["doi"]) + ".pmc.xml")
        elif w.get("unpaywall_pdf"):
            url, out = w["unpaywall_pdf"], os.path.join(fdir, _safe(w["doi"]) + ".pdf")
        else:
            continue
        if not os.path.exists(out):
            try:
                req = urllib.request.Request(url, headers=UA)
                with urllib.request.urlopen(req, timeout=120) as r, open(out, "wb") as fh:
                    fh.write(r.read())
                time.sleep(0.4)
            except Exception as exc:  # noqa: BLE001 — editora bloqueia robôs, link quebrado etc.
                print(f"  falhou {w['doi']}: {exc}", file=sys.stderr)
                continue
        w["fulltext_file"] = os.path.relpath(out, a.out)
        queue.append({"doi": w["doi"], "title": w["title"], "file": w["fulltext_file"],
                      "format": "jats-xml" if out.endswith(".xml") else "pdf", "license": w.get("unpaywall_license", "")})
    write_jsonl(os.path.join(a.out, "fulltext.jsonl"), works)
    write_jsonl(os.path.join(a.out, "to_extract.jsonl"), queue)
    finalize(a, works)
    print(f"-> {len(queue)} textos integrais em {os.path.relpath(fdir, ROOT)}/ (fila: to_extract.jsonl)")


# ---------------------------------------------------------------------------------------------- consolidação

def local_dois() -> dict[str, set[str]]:
    out = {"literature": set(), "cruse": set(), "seed": set()}
    rel = os.path.join(ROOT, "literature", "relatorio.csv")
    if os.path.exists(rel):
        with open(rel, encoding="utf-8-sig") as fh:
            out["literature"] = {norm_doi(r.get("doi")) for r in csv.DictReader(fh, delimiter=";") if r.get("doi")}
    cruse = os.path.join(ROOT, "datasets", "aunp-text-mined", "aunp-synthesis_dataset_2021-9-14.json")
    if os.path.exists(cruse) and os.path.getsize(cruse) > 1000:  # ignora ponteiro LFS
        out["cruse"] = {norm_doi(a["doi"]) for a in json.load(open(cruse, encoding="utf-8"))}
    seed = os.path.join(ROOT, "datasets", "literature-seed", "aunp_literature_seed.csv")
    if os.path.exists(seed):
        with open(seed, encoding="utf-8") as fh:
            out["seed"] = {norm_doi(r["doi"]) for r in csv.DictReader(fh) if r["doi"]}
    return out


def finalize(a, works: list[dict]) -> None:
    loc = local_dois()
    for w in works:
        w["in_literature_corpus"] = int(w["doi"] in loc["literature"])
        w["in_cruse"] = int(w["doi"] in loc["cruse"])
        w["in_seed"] = int(w["doi"] in loc["seed"])
    with open(os.path.join(a.out, "works.csv"), "w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=WORK_FIELDS, extrasaction="ignore")
        wr.writeheader()
        wr.writerows(works)
    print(f"-> works.csv: {len(works)} DOIs; já no corpus {sum(w['in_literature_corpus'] for w in works)}, "
          f"em Cruse {sum(w['in_cruse'] for w in works)}, na semente {sum(w['in_seed'] for w in works)}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stage", choices=["search", "crossref", "oa", "fetch", "all"])
    ap.add_argument("--query", default=DEFAULT_QUERY)
    ap.add_argument("--from-year", type=int)
    ap.add_argument("--to-year", type=int)
    ap.add_argument("--oa-only", action="store_true")
    ap.add_argument("--min-citations", type=int)
    ap.add_argument("--max", type=int, default=1000)
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    stages = ["search", "crossref", "oa", "fetch"] if a.stage == "all" else [a.stage]
    for s in stages:
        {"search": stage_search, "crossref": stage_crossref, "oa": stage_oa, "fetch": stage_fetch}[s](a)
        if a.dry_run:
            break


if __name__ == "__main__":
    main()
