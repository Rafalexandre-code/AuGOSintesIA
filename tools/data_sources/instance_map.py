#!/usr/bin/env python3
"""Instance Map do laboratório (Punz et al., Beilstein J. Nanotechnol. 2025; §4.1, §4.17): grafo de proveniência que
liga fonte → lote → amostra → síntese → medida → arquivo bruto → desfecho → versão da análise, com termos W3C PROV-O,
exportado como RO-Crate 1.1 (JSON-LD) para o depósito FAIR.

Nós (tipo PROV) e relações:
  prov:Entity    lote de reagente, análise de impureza, lote de GO, amostra de GO, medida, descritor, espectro,
                 arquivo bruto, produto da síntese, desfecho, resultado de QC, recurso consumido
  prov:Activity  síntese (usa lotes/amostra, gera o produto, segue um protocolo), rodada do otimizador
  prov:Plan      protocolo (SOP)        prov:Agent  operador
  arestas: prov:used, prov:wasGeneratedBy, prov:wasDerivedFrom, prov:hadPlan, prov:wasAssociatedWith,
           prov:wasInformedBy (síntese ← rodada do otimizador que a propôs)
Verificações de integridade: arquivos brutos ausentes, referências quebradas, sínteses sem espectro, desfechos sem
medida de origem, alíquotas contadas como sínteses (mesma preparação).

Saídas (padrão outputs/instance_map/): ro-crate-metadata.json, instance_map.graphml (Gephi/Cytoscape),
integrity.csv; `lineage <synthesis_id>` imprime a cadeia de uma síntese em Mermaid.

Uso:
    python tools/data_sources/instance_map.py build datasets/lab [--out outputs/instance_map]
    python tools/data_sources/instance_map.py lineage datasets/lab SYN-0001
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import date

import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROV = "http://www.w3.org/ns/prov#"


class Graph:
    def __init__(self):
        self.nodes: dict[str, dict] = {}
        self.edges: list[tuple[str, str, str]] = []
        self.issues: list[dict] = []

    def node(self, nid: str, ptype: str, label: str, **attrs):
        n = self.nodes.setdefault(nid, {"@id": nid, "prov_type": ptype, "label": label})
        n.update({k: v for k, v in attrs.items() if v not in ("", None) and not (isinstance(v, float) and pd.isna(v))})
        return nid

    def edge(self, src: str, rel: str, dst: str):
        self.edges.append((src, rel, dst))

    def issue(self, level: str, where: str, msg: str):
        self.issues.append({"level": level, "where": where, "message": msg})


def _read(lab: str, t: str) -> pd.DataFrame:
    p = os.path.join(lab, f"{t}.csv")
    return pd.read_csv(p, dtype=str).fillna("") if os.path.exists(p) else pd.DataFrame()


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build(lab: str) -> Graph:
    g = Graph()
    T = {t: _read(lab, t) for t in ("protocols", "reagent_lots", "reagent_analyses", "go_batches", "go_samples",
                                    "go_characterization", "go_descriptors", "aunp_syntheses", "spectra",
                                    "aunp_characterization", "outcomes", "qc_results", "resources")}
    ids = {}

    def file_node(rel: str, where: str) -> str | None:
        if not rel:
            return None
        nid = f"file:{rel}"
        full = os.path.join(lab, rel)
        if nid not in g.nodes:
            if os.path.exists(full):
                g.node(nid, "prov:Entity", os.path.basename(rel), kind="raw_file", path=rel, sha256=_sha256(full),
                       contentSize=os.path.getsize(full))
            else:
                g.node(nid, "prov:Entity", os.path.basename(rel), kind="raw_file", path=rel, missing=True)
                g.issue("error", where, f"arquivo bruto ausente: {rel}")
        return nid

    for _, r in T["protocols"].iterrows():
        ids[("protocol", r["protocol_id"])] = g.node(f"protocol:{r['protocol_id']}", "prov:Plan", r["title"],
                                                     version=r.get("version"), file=r.get("file"), doi=r.get("doi"))
    for _, r in T["reagent_lots"].iterrows():
        g.node(f"lot:{r['lot_id']}", "prov:Entity", r["chemical_name"], kind="reagent_lot", supplier=r["supplier"],
               lot_number=r["lot_number"], pubchem_cid=r.get("pubchem_cid"))
    for _, r in T["reagent_analyses"].iterrows():
        n = g.node(f"analysis:{r['analysis_id']}", "prov:Entity", f"{r['analyte']} = {r['value']} {r.get('unit', '')}",
                   kind="impurity_analysis", value=r["value"], unit=r.get("unit"), method=r.get("method"))
        g.edge(n, "prov:wasDerivedFrom", f"lot:{r['lot_id']}")
        if f"lot:{r['lot_id']}" not in g.nodes:
            g.issue("error", f"reagent_analyses:{r['analysis_id']}", f"lote {r['lot_id']} inexistente")
    for _, r in T["go_batches"].iterrows():
        g.node(f"gobatch:{r['go_batch_id']}", "prov:Entity", r["go_batch_id"], kind="go_batch",
               supplier=r.get("supplier"), synthesis_method=r.get("synthesis_method"))
    for _, r in T["go_samples"].iterrows():
        n = g.node(f"gosample:{r['go_sample_id']}", "prov:Entity", r["go_sample_id"], kind="go_sample",
                   prep_type=r.get("prep_type"), age_days=r.get("age_days"))
        g.edge(n, "prov:wasDerivedFrom", f"gobatch:{r['go_batch_id']}")
    for kind, tab, parent in (("go_measurement", "go_characterization", "go_sample_id"),
                              ("aunp_measurement", "aunp_characterization", "synthesis_id")):
        for _, r in T[tab].iterrows():
            n = g.node(f"meas:{r['measurement_id']}", "prov:Entity", f"{r['technique']} {r['quantity']} = {r['value']}",
                       kind=kind, technique=r["technique"], quantity=r["quantity"], value=r["value"],
                       uncertainty=r.get("uncertainty"), unit=r.get("unit"))
            g.edge(n, "prov:wasDerivedFrom", f"gosample:{r[parent]}" if parent == "go_sample_id" else f"product:{r[parent]}")
            if r.get("spectrum_id"):
                g.edge(n, "prov:wasDerivedFrom", f"spectrum:{r['spectrum_id']}")
            for f in str(r.get("raw_data_file", "")).split("|"):
                fn = file_node(f.strip(), f"{tab}:{r['measurement_id']}")
                if fn:
                    g.edge(n, "prov:wasDerivedFrom", fn)
            if r.get("protocol_id"):
                g.edge(n, "prov:hadPlan", f"protocol:{r['protocol_id']}")
    for _, r in T["go_descriptors"].iterrows():
        n = g.node(f"descriptor:{r['go_batch_id']}:{r['descriptor']}", "prov:Entity",
                   f"{r['descriptor']} = {r['mean']} ± {r.get('sd', '')}", kind="go_descriptor")
        g.edge(n, "prov:wasDerivedFrom", f"gobatch:{r['go_batch_id']}")
        for m in str(r.get("source_measurements", "")).split("|"):
            if m.strip():
                g.edge(n, "prov:wasDerivedFrom", f"meas:{m.strip()}")
    syn = T["aunp_syntheses"]
    prep_seen: dict[str, str] = {}
    for _, r in syn.iterrows():
        sid = r["synthesis_id"]
        act = g.node(f"synthesis:{sid}", "prov:Activity", sid, kind="synthesis", status=r.get("status"),
                     block=r.get("block"), run_order=r.get("run_order"), date=r.get("date"),
                     is_control=r.get("is_control"))
        prod = g.node(f"product:{sid}", "prov:Entity", f"produto {sid}", kind="aunp_product")
        g.edge(prod, "prov:wasGeneratedBy", act)
        for col in ("gold_precursor_lot_id", "reductant_lot_id", "stabilizer_lot_id"):
            if r.get(col):
                g.edge(act, "prov:used", f"lot:{r[col]}")
                if f"lot:{r[col]}" not in g.nodes:
                    g.issue("error", f"aunp_syntheses:{sid}", f"{col}={r[col]} não está em reagent_lots")
        if r.get("go_sample_id"):
            g.edge(act, "prov:used", f"gosample:{r['go_sample_id']}")
        elif r.get("go_batch_id"):
            g.edge(act, "prov:used", f"gobatch:{r['go_batch_id']}")
        if r.get("protocol_id"):
            g.edge(act, "prov:hadPlan", f"protocol:{r['protocol_id']}")
        if r.get("operator"):
            g.edge(act, "prov:wasAssociatedWith", g.node(f"agent:{r['operator']}", "prov:Agent", r["operator"]))
        if r.get("campaign_id") and r.get("design_id"):
            rnd = g.node(f"design:{r['campaign_id']}", "prov:Activity", f"otimizador {r['campaign_id']}",
                         kind="optimizer_round")
            g.edge(act, "prov:wasInformedBy", rnd)
        p = r.get("preparation_id", "")
        if p:
            if p in prep_seen and r.get("status") != "repeated":
                g.issue("error", f"aunp_syntheses:{sid}", f"mesma preparação de {prep_seen[p]} ({p}): alíquota contada "
                                                          f"como síntese")
            prep_seen.setdefault(p, sid)
    for _, r in T["spectra"].iterrows():
        n = g.node(f"spectrum:{r['spectrum_id']}", "prov:Entity", r["spectrum_id"], kind="spectrum",
                   technique=r["technique"], dilution_factor=r.get("dilution_factor"),
                   path_length_mm=r.get("path_length_mm"), time_after_prep_min=r.get("time_after_prep_min"))
        if r.get("synthesis_id"):
            g.edge(n, "prov:wasDerivedFrom", f"product:{r['synthesis_id']}")
            if syn.empty or r["synthesis_id"] not in set(syn["synthesis_id"]):
                g.issue("error", f"spectra:{r['spectrum_id']}", f"síntese {r['synthesis_id']} inexistente")
        if r.get("go_sample_id"):
            g.edge(n, "prov:wasDerivedFrom", f"gosample:{r['go_sample_id']}")
        if r.get("blank_spectrum_id"):
            g.edge(n, "prov:used", f"spectrum:{r['blank_spectrum_id']}")
        fn = file_node(r.get("file", ""), f"spectra:{r['spectrum_id']}")
        if fn:
            g.edge(n, "prov:wasDerivedFrom", fn)
    with_uv = set(T["spectra"].loc[T["spectra"].get("technique", pd.Series(dtype=str)) == "UV-Vis", "synthesis_id"]) \
        if not T["spectra"].empty else set()
    for _, r in syn.iterrows():
        if r.get("status", "done") in ("done", "") and r.get("is_control") != "GO_blank" and r["synthesis_id"] not in with_uv:
            g.issue("warning", f"aunp_syntheses:{r['synthesis_id']}", "síntese sem espectro UV-Vis registrado")
    for _, r in T["outcomes"].iterrows():
        n = g.node(f"outcome:{r['synthesis_id']}:{r['objective']}", "prov:Entity",
                   f"{r['objective']} = {r['value']}", kind="outcome", direction=r["direction"],
                   model_version=r.get("model_version"))
        g.edge(n, "prov:wasDerivedFrom", f"product:{r['synthesis_id']}")
        src = [m for m in str(r.get("derived_from", "")).split("|") if m.strip()]
        for m in src:
            g.edge(n, "prov:wasDerivedFrom", f"meas:{m.strip()}")
        if not src:
            g.issue("info", f"outcomes:{r['synthesis_id']}:{r['objective']}", "desfecho sem derived_from (medidas de origem)")
    for _, r in T["qc_results"].iterrows():
        if r["status"] != "pass":
            n = g.node(f"qc:{r['synthesis_id']}:{r['check']}", "prov:Entity", f"QC {r['check']}: {r['status']}",
                       kind="qc_result", status=r["status"])
            g.edge(n, "prov:wasDerivedFrom", f"product:{r['synthesis_id']}")
    for _, r in T["resources"].iterrows():
        n = g.node(f"resource:{r['resource_id']}", "prov:Entity", f"{r['item']} {r['amount']} {r['unit']}",
                   kind="resource", category=r["category"], flow=r["flow"], cost=r.get("cost"))
        if r.get("synthesis_id"):
            rel = "prov:wasGeneratedBy" if r["category"] == "waste" else None
            if rel:
                g.edge(n, rel, f"synthesis:{r['synthesis_id']}")
            else:
                g.edge(f"synthesis:{r['synthesis_id']}", "prov:used", n)
    dangling = {d for _, _, d in g.edges if d not in g.nodes}
    for d in sorted(dangling):
        g.issue("error", d, "referência a um nó inexistente")
    return g


def to_rocrate(g: Graph, lab: str, name: str = "GO–AuNP laboratory instance map") -> dict:
    graph = [{"@id": "ro-crate-metadata.json", "@type": "CreativeWork", "conformsTo": {"@id": "https://w3id.org/ro/crate/1.1"},
              "about": {"@id": "./"}},
             {"@id": "./", "@type": "Dataset", "name": name, "datePublished": date.today().isoformat(),
              "description": "Instance Map (Punz et al. 2025) do projeto GO–AuNP: proveniência W3C PROV-O de lotes, "
                             "amostras, sínteses, medidas, arquivos brutos e desfechos.",
              "license": {"@id": "https://creativecommons.org/licenses/by/4.0/"},
              "hasPart": [{"@id": n["path"]} for n in g.nodes.values() if n.get("kind") == "raw_file" and not n.get("missing")]
              + [{"@id": f"{t}.csv"} for t in sorted(f[:-4] for f in os.listdir(lab) if f.endswith(".csv"))]}]
    for t in sorted(f for f in os.listdir(lab) if f.endswith(".csv")):
        graph.append({"@id": t, "@type": "File", "encodingFormat": "text/csv", "sha256": _sha256(os.path.join(lab, t))})
    out_edges: dict[str, dict[str, list]] = {}
    for s, rel, d in g.edges:
        out_edges.setdefault(s, {}).setdefault(rel, []).append({"@id": d})
    for nid, n in g.nodes.items():
        ent = {"@id": n.get("path", nid) if n.get("kind") == "raw_file" else nid,
               "@type": ["File", n["prov_type"]] if n.get("kind") == "raw_file" else n["prov_type"], "name": n["label"]}
        ent.update({k: v for k, v in n.items() if k not in ("@id", "prov_type", "label", "path")})
        ent.update(out_edges.get(nid, {}))
        graph.append(ent)
    return {"@context": ["https://w3id.org/ro/crate/1.1/context", {"prov": PROV, "sha256": "https://w3id.org/ro/terms/workflow-run#sha256"}],
            "@graph": graph}


def to_graphml(g: Graph, path: str) -> None:
    import networkx as nx
    G = nx.DiGraph()
    for nid, n in g.nodes.items():
        G.add_node(nid, **{k: str(v) for k, v in n.items() if k != "@id"})
    for s, rel, d in g.edges:
        G.add_edge(s, d, relation=rel)
    nx.write_graphml(G, path)


def lineage(g: Graph, sid: str) -> str:
    """Mermaid com tudo de que o produto da síntese depende (ancestrais) e o que dele deriva."""
    start = {f"synthesis:{sid}", f"product:{sid}"}
    up, frontier = set(start), set(start)
    while frontier:
        nxt = {d for s, _, d in g.edges if s in frontier} - up
        up |= nxt
        frontier = nxt
    down = {s for s, _, d in g.edges if d in start}
    keep = up | down
    lines = ["graph LR"]
    alias = {n: f"n{i}" for i, n in enumerate(sorted(keep))}
    for n in sorted(keep):
        lab = g.nodes.get(n, {}).get("label", n).replace('"', "'")
        lines.append(f'  {alias[n]}["{lab}"]')
    for s, rel, d in g.edges:
        if s in keep and d in keep:
            lines.append(f"  {alias[s]} -->|{rel.split(':')[1]}| {alias[d]}")
    return "\n".join(lines)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("lab")
    b.add_argument("--out", default=os.path.join(ROOT, "outputs", "instance_map"))
    li = sub.add_parser("lineage")
    li.add_argument("lab")
    li.add_argument("synthesis_id")
    a = ap.parse_args(argv)
    g = build(a.lab)
    if a.cmd == "lineage":
        print(lineage(g, a.synthesis_id))
        return
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "ro-crate-metadata.json"), "w", encoding="utf-8") as fh:
        json.dump(to_rocrate(g, a.lab), fh, indent=1, ensure_ascii=False)
    to_graphml(g, os.path.join(a.out, "instance_map.graphml"))
    pd.DataFrame(g.issues, columns=["level", "where", "message"]).to_csv(os.path.join(a.out, "integrity.csv"), index=False)
    kinds = pd.Series([n.get("kind", n["prov_type"]) for n in g.nodes.values()]).value_counts().to_dict()
    lv = pd.Series([i["level"] for i in g.issues]).value_counts().to_dict() if g.issues else {}
    print(f"{len(g.nodes)} nós {kinds}; {len(g.edges)} relações PROV; integridade: {lv or 'sem problemas'}")
    print(f"-> {os.path.relpath(a.out, ROOT)}/ (ro-crate-metadata.json, instance_map.graphml, integrity.csv)")


if __name__ == "__main__":
    main()
