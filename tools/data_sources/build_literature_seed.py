#!/usr/bin/env python3
"""Semente de literatura GO–AuNP: junta as três bases de síntese de ouro do repositório numa tabela única.

Fontes (todas locais; as duas primeiras exigem ``git lfs pull``):
  * Cruse et al., Sci. Data 2022 (figshare 10.6084/m9.figshare.16614262) — ``datasets/aunp-text-mined/``:
    uma linha por parágrafo de receita (materiais + quantidades, ações, condições), com morfologia/tamanho do artigo.
  * NSP, Gu et al., ACS Nano 2026 (HF Kai-gu/Synthesis-Properties-Database-for-Nanomaterials) —
    ``datasets/nanocrystal-synthesis-db/dataset_low_conf_skip-clean.json``: uma linha por rota cujo produto é de Au.
  * AuNCs tiolados (Zenodo 15739032, 207 entradas) — ``datasets/aunc-fluorescence/``.

Os reagentes passam pelo dicionário PubChem (``tools/data_sources/reagents.py``): todas as grafias de HAuCl4 viram
``HAuCl4`` etc. A coluna ``mentions_graphene_oxide`` marca registros que citam GO/rGO (subconjunto GO–AuNP).

Uso:
    python tools/data_sources/build_literature_seed.py            # -> datasets/literature-seed/
    python tools/data_sources/build_literature_seed.py --nsp-all  # usa dataset.json (bruto, inclui baixa confiança)
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import os
import re
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reagents import ROOT, Normalizer  # noqa: E402

CRUSE = os.path.join(ROOT, "datasets", "aunp-text-mined", "aunp-synthesis_dataset_2021-9-14.json")
NSP_CLEAN = os.path.join(ROOT, "datasets", "nanocrystal-synthesis-db", "dataset_low_conf_skip-clean.json")
NSP_RAW = os.path.join(ROOT, "datasets", "nanocrystal-synthesis-db", "dataset.json")
AUNC = os.path.join(ROOT, "datasets", "aunc-fluorescence", "DATASET_AuNCs.csv")
OUT = os.path.join(ROOT, "datasets", "literature-seed")

FIELDS = ["seed_id", "source", "source_ref", "doi", "title", "year", "citations", "product",
          "morphology_raw", "morphology_class", "size_text", "size_nm", "abs_peak_text", "abs_peak_nm",
          "em_peak_nm", "exc_nm", "seed_mediated", "gold_precursor", "gold_precursor_form", "gold_precursor_amount",
          "reductants", "capping_ligands", "solvents", "pH_adjusters", "additives", "supports", "other_reagents",
          "unresolved_materials", "temperature_C", "time_text", "pH", "actions", "mentions_graphene_oxide",
          "confidence"]

ROLE_COLUMN = {
    "gold_precursor": "gold_precursor", "reductant": "reductants", "reductant_stabilizer": "reductants",
    "reductant_oxidant": "reductants", "surfactant": "capping_ligands", "capping_agent": "capping_ligands",
    "polyelectrolyte": "capping_ligands", "phase_transfer": "capping_ligands", "solvent": "solvents",
    "pH_adjuster": "pH_adjusters", "salt": "additives", "additive": "additives", "support": "supports",
    "support_precursor": "supports", "silica_precursor": "other_reagents", "other": "other_reagents",
}
GO_ENTITIES = {"graphene_oxide", "reduced_graphene_oxide"}

# Morfologias: primeiro os regex publicados por Cruse et al. (projects/literature-llm/text-mined-aunp-synthesis/
# rsc/aunp_morph_syns_regex.json: rod, sphere, cube, octahedra, hexagon, star, wire, triangle, plate, tube,
# prismatic, pyramid — sensíveis a maiúsculas, como no original); depois as classes que eles não cobrem.
CRUSE_MORPH = os.path.join(ROOT, "projects", "literature-llm", "text-mined-aunp-synthesis", "rsc",
                           "aunp_morph_syns_regex.json")
_PRE = [("cluster", re.compile(r"cluster|\bncs?\b|\bauncs?\b|\bau\d+", re.I))]
_POST = [("star", re.compile(r"branched|urchin|flower|dendrit", re.I)),
         ("shell/cage", re.compile(r"shell|cage|hollow|frame|core", re.I)),
         ("particle", re.compile(r"particle|\bnps?\b|\bgnps?\b|\baunps?\b|colloid|nanocrystal|dot|seed", re.I))]


def _load_morph() -> list[tuple[str, re.Pattern]]:
    cruse = []
    if os.path.exists(CRUSE_MORPH):
        for cls, pats in json.load(open(CRUSE_MORPH, encoding="utf-8")).items():
            cruse.append((cls, re.compile("|".join(f"(?:{p})" for p in pats))))
    return _PRE + cruse + _POST


MORPH_CLASSES = _load_morph()


def morph_class(names) -> str:
    found = []
    for n in names:
        for cls, pat in MORPH_CLASSES:
            if pat.search(n):
                if cls not in found:
                    found.append(cls)
                break
    return "|".join(found)


_NUM = re.compile(r"(\d+(?:\.\d+)?)")


def nm_values(text: str) -> list[float]:
    """Números seguidos de 'nm' em texto livre (ex.: '48 ± 8 nm' -> [48])."""
    vals = []
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*(?:±\s*\d+(?:\.\d+)?\s*)?(?:-|–|to)?\s*(\d+(?:\.\d+)?)?\s*nm", text):
        vals.append(float(m.group(1)))
    return vals


def median_str(vals) -> str:
    return f"{statistics.median(vals):g}" if vals else ""


def classify(n: Normalizer, names, text_for_scan: str = "") -> dict[str, list[str]]:
    cols: dict[str, list[str]] = collections.defaultdict(list)
    forms, unresolved = [], []
    ents = []
    for name in names:
        r = n.normalize(name)
        if not r:
            unresolved.append(name)
            continue
        ents.append(r["entity_id"])
        if r["role"] == "gold_precursor" and r["form"]:
            forms.append(r["form"])
    if text_for_scan:
        ents += sorted(n.find_in_text(text_for_scan))
    for eid in dict.fromkeys(ents):
        col = ROLE_COLUMN.get(n.by_id[eid]["role"])
        if col and eid not in cols[col]:
            cols[col].append(eid)
    cols["gold_precursor_form"] = list(dict.fromkeys(forms))
    cols["unresolved_materials"] = list(dict.fromkeys(unresolved))
    cols["_entities"] = list(dict.fromkeys(ents))
    return cols


def _join(v) -> str:
    return "|".join(str(x) for x in v if str(x) != "")


# ---------------------------------------------------------------------------------------------- Cruse et al.

def rows_cruse(n: Normalizer):
    data = json.load(open(CRUSE, encoding="utf-8"))
    for art in data:
        paras = art["paragraphs"]
        morph_all, sizes_all, nm_all = [], [], []
        for p in paras:
            mi = p["morphological_information"]
            morph_all += mi["morphologies"]
            if mi["sizes"]:
                sizes_all.append(f"{', '.join(mi['sizes'])} [{', '.join(mi['units']) or '?'}]")
                if mi["units"] == ["nm"]:
                    nm_all += [float(x) for s in mi["sizes"] for x in _NUM.findall(s)]
        art_text = " ".join(p["text"] for p in paras)
        art_go = bool(n.find_in_text(art_text) & GO_ENTITIES)
        for p in paras:
            mq = p.get("materials_and_quantities")
            if not p.get("contains_recipe") or not mq:
                continue
            names = [m["material"] for m in mq]
            cols = classify(n, names)
            gold_amt = []
            for m in mq:
                r = n.normalize(m["material"])
                if r and r["role"] == "gold_precursor":
                    gold_amt += [f"{a['value']} {a['unit']}".strip() for a in m["amount"] if a.get("value") != ""]
            temps, times, actions = [], [], []
            for s in p.get("synth_actions") or []:
                actions.append(s["type"])
                c = s.get("conditions") or {}
                if c.get("temperature") and c["temperature"].get("unit") in ("°C", "℃", "C"):
                    temps += c["temperature"]["value"]
                if c.get("time"):
                    times += [f"{v:g} {c['time']['unit']}" for v in c["time"]["value"]]
            yield {
                "seed_id": f"cruse:{p['_id']}", "source": "cruse2022", "source_ref": "10.6084/m9.figshare.16614262",
                "doi": art["doi"], "year": art.get("publication_year", ""), "citations": art.get("times_referenced", ""),
                "product": "Au", "morphology_raw": _join(dict.fromkeys(morph_all))[:300],
                "morphology_class": morph_class(dict.fromkeys(morph_all)), "size_text": " ; ".join(sizes_all)[:300],
                "size_nm": median_str(nm_all), "seed_mediated": int(bool(p.get("seed_mediated"))),
                "gold_precursor": _join(cols["gold_precursor"]), "gold_precursor_form": _join(cols["gold_precursor_form"]),
                "gold_precursor_amount": _join(dict.fromkeys(gold_amt)),
                **{c: _join(cols[c]) for c in ("reductants", "capping_ligands", "solvents", "pH_adjusters",
                                               "additives", "supports", "other_reagents")},
                "unresolved_materials": _join(cols["unresolved_materials"])[:300],
                "temperature_C": _join(dict.fromkeys(f"{t:g}" for t in temps)), "time_text": _join(dict.fromkeys(times)),
                "actions": ">".join(actions),
                "mentions_graphene_oxide": int(art_go or bool(set(cols["_entities"]) & GO_ENTITIES)),
                "confidence": "text-mined",
            }


# ---------------------------------------------------------------------------------------------- NSP

GOLD_PRODUCT = re.compile(r"(?<![A-Za-z])Au(?![a-z])|gold", re.I)
TEMP = re.compile(r"(-?\d+(?:\.\d+)?)\s*°\s*C")


def _props(lst, pid):
    out = []
    for p in lst or []:
        if p.get("product_id") == pid:
            out += [f"{d.get('property_name', '')}: {d.get('value', '')}" for d in p.get("property_details") or []]
    return out


def rows_nsp(n: Normalizer, path: str):
    data = json.load(open(path, encoding="utf-8"))
    for rec in data:
        ec = rec.get("extracted_content")
        if not isinstance(ec, dict):
            continue
        steps = {s.get("step_number"): s.get("step_content", "") for s in ec.get("synthesis_steps") or []}
        para_go = None
        for route in ec.get("synthesis_routes") or []:
            prod = route.get("product_name") or ""
            if not GOLD_PRODUCT.search(prod):
                continue
            seq = [s.strip() for s in re.split(r"→|->", route.get("route_sequence") or "") if s.strip()]
            text = " ".join(steps.get(s, "") for s in seq) or " ".join(steps.values())
            cols = classify(n, [], text_for_scan=text)
            if para_go is None:
                para_go = bool(n.find_in_text(rec.get("paragraph", "")) & GO_ENTITIES)
            pid = route.get("product_id")
            size = _props(ec.get("size_shape_properties"), pid)
            absn = _props(ec.get("absorption_spectra_properties"), pid)
            emi = _props(ec.get("emission_spectra_properties"), pid)
            title = rec.get("title", "")
            doi = title if re.match(r"^10\.\d{4,}/", title) else ""
            yield {
                "seed_id": f"nsp:{rec['sample_id']}:{pid}", "source": "nsp2026",
                "source_ref": "hf:Kai-gu/Synthesis-Properties-Database-for-Nanomaterials", "doi": doi,
                "title": "" if doi else title[:200], "product": prod[:120],
                "morphology_raw": _join(size)[:300], "morphology_class": morph_class([prod] + size),
                "size_text": _join(size)[:300], "size_nm": median_str(nm_values(" ".join(size))),
                "abs_peak_text": _join(absn)[:200], "abs_peak_nm": median_str(nm_values(" ".join(absn))),
                "em_peak_nm": median_str(nm_values(" ".join(emi))),
                "seed_mediated": int(bool(re.search(r"\bseed", text, re.I))),
                "gold_precursor": _join(cols["gold_precursor"]),
                **{c: _join(cols[c]) for c in ("reductants", "capping_ligands", "solvents", "pH_adjusters",
                                               "additives", "supports", "other_reagents")},
                "temperature_C": _join(dict.fromkeys(TEMP.findall(text))),
                "actions": " | ".join(steps.get(s, "") for s in seq)[:1500],
                "mentions_graphene_oxide": int(para_go or bool(set(cols["_entities"]) & GO_ENTITIES)),
                "confidence": rec.get("confidence", ""),
            }


# ---------------------------------------------------------------------------------------------- AuNCs

def rows_aunc(n: Normalizer):
    with open(AUNC, encoding="latin-1") as fh:
        rd = csv.reader(fh, delimiter=";")
        next(rd)  # Entry;Size (nm);Measuring Solvent;λexc;λem;Ligand;Au atoms;Synthesis T (°C);pH;time (h);DOI
        for r in rd:
            if not r or not r[0].strip():
                continue
            r += [""] * (11 - len(r))
            entry, size, solv, exc, em, lig, au_atoms, temp, ph, time_h, doi = [x.strip() for x in r[:11]]
            doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi)
            cols = classify(n, [lig, solv])
            yield {
                "seed_id": f"aunc:{entry}", "source": "aunc2025", "source_ref": "zenodo:15739032", "doi": doi,
                "product": f"Au{au_atoms} NC" if au_atoms else "Au NC", "morphology_raw": "nanocluster",
                "morphology_class": "cluster", "size_text": f"{size} nm" if size else "", "size_nm": size,
                "em_peak_nm": em, "exc_nm": exc,
                "capping_ligands": _join(cols["capping_ligands"] or [lig]), "solvents": _join(cols["solvents"] or [solv]),
                "temperature_C": "25" if temp.upper() == "RT" else temp, "time_text": f"{time_h} h" if time_h else "",
                "pH": ph, "mentions_graphene_oxide": 0, "confidence": "curated",
            }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--nsp-all", action="store_true", help="usa dataset.json (bruto) em vez do limpo")
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()
    n = Normalizer()
    os.makedirs(a.out, exist_ok=True)
    rows = []
    for name, gen in (("cruse2022", rows_cruse(n)), ("nsp2026", rows_nsp(n, NSP_RAW if a.nsp_all else NSP_CLEAN)),
                      ("aunc2025", rows_aunc(n))):
        before = len(rows)
        rows += [{k: row.get(k, "") for k in FIELDS} for row in gen]
        print(f"{name}: {len(rows) - before} registros")
    for fname, subset in (("aunp_literature_seed.csv", rows),
                          ("go_aunp_subset.csv", [r for r in rows if r["mentions_graphene_oxide"] == 1])):
        with open(os.path.join(a.out, fname), "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(subset)
        print(f"-> {os.path.relpath(os.path.join(a.out, fname), ROOT)}: {len(subset)} linhas")

    def top(col, k=15):
        c = collections.Counter(x for r in rows for x in str(r[col]).split("|") if x)
        return c.most_common(k)

    summary = {
        "registros_por_fonte": dict(collections.Counter(r["source"] for r in rows)),
        "dois_distintos": len({r["doi"].lower() for r in rows if r["doi"]}),
        "com_mencao_a_GO": sum(r["mentions_graphene_oxide"] == 1 for r in rows),
        "com_precursor_de_ouro_identificado": sum(bool(r["gold_precursor"]) for r in rows),
        "com_tamanho_nm": sum(bool(r["size_nm"]) for r in rows),
        "top_precursores": top("gold_precursor"), "top_redutores": top("reductants"),
        "top_estabilizantes": top("capping_ligands"), "top_morfologias": top("morphology_class"),
        "top_suportes": top("supports"),
    }
    with open(os.path.join(a.out, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False)[:1500])


if __name__ == "__main__":
    main()
