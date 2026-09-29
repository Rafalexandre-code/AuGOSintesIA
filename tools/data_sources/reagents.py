#!/usr/bin/env python3
"""Dicionário de reagentes normalizado com PubChem (entidade única por substância).

Junta o dicionário curado ``datasets/reagents/aliases.tsv`` (sinônimos, siglas, padrões) com as fichas PubChem
já baixadas em ``datasets/pubchem/`` (nome, fórmula, massa molar, IUPAC, SMILES, InChI, InChIKey, CAS,
sinônimos). Exemplo: "HAuCl4·3H2O", "chloroauric acid", "tetrachloroauric acid", "gold chloride" e
"hydrogen tetrachloroaurate" viram a entidade ``HAuCl4`` (CID 28133), com a hidratação em ``form``.

Uso:
    python tools/data_sources/reagents.py build            # gera reagent_dictionary.csv e pubchem_records.csv (offline)
    python tools/data_sources/reagents.py build --online   # também resolve no PubChem (PUG REST) as entidades sem CID
    python tools/data_sources/reagents.py normalize "HAuCl4·3H2O" "sodium citrate dihydrate"
    python tools/data_sources/reagents.py cruse            # aplica ao dataset de Cruse et al. (relatório de cobertura)

Como biblioteca:
    from reagents import Normalizer
    n = Normalizer()
    n.normalize("Gold(III) chloride trihydrate")   # -> {'entity_id': 'HAuCl4', 'form': 'trihydrate', ...}
    n.find_in_text("... 1 mL of 25 mM HAuCl4 was added to 0.1 M CTAB ...")   # -> {'HAuCl4', 'CTAB'}
"""
from __future__ import annotations

import argparse
import collections
import csv
import glob
import json
import os
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PUBCHEM_DIR = os.path.join(ROOT, "datasets", "pubchem")
REAGENTS_DIR = os.path.join(ROOT, "datasets", "reagents")
ALIASES = os.path.join(REAGENTS_DIR, "aliases.tsv")
CRUSE_JSON = os.path.join(ROOT, "datasets", "aunp-text-mined", "aunp-synthesis_dataset_2021-9-14.json")
# dicionários de sinônimos dos próprios autores do dataset (Cruse et al.), usados para validação cruzada
CRUSE_RSC = os.path.join(ROOT, "projects", "literature-llm", "text-mined-aunp-synthesis", "rsc")
# rótulo do regex de Cruse -> entidades deste dicionário consideradas equivalentes
CRUSE_LABEL_TO_ENTITIES = {
    "AuCl3": {"AuCl3", "HAuCl4"},  # Cruse chama "gold(III) chloride" de AuCl3; aqui vai para HAuCl4 (ambíguo)
    "NaAuCl4": {"NaAuCl4"}, "HAuCl4": {"HAuCl4"}, "Ag+": {"AgNO3", "Ag"}, "AgNO3": {"AgNO3"}, "NaBH4": {"NaBH4"},
    "ascorbic acid": {"ascorbic_acid"}, "HQ": {"hydroquinone"}, "H2O2": {"H2O2"},
    "citrate": {"trisodium_citrate", "citric_acid"}, "sodium citrate": {"trisodium_citrate"}, "CTAB": {"CTAB"},
    "CTAC": {"CTAC"}, "BSA": {"BSA"}, "PVP": {"PVP"}, "PDDA": {"PDDA"}, "TOAB": {"TOAB"}, "TEOS": {"TEOS"},
    "DMF": {"DMF"}, "organic solvent": {"ethanol", "toluene", "PEG", "ethylene_glycol", "isopropanol", "methanol"},
    "H2O": {"water"}, "HCl": {"HCl"}, "NaOH": {"NaOH"}, "HNO3": {"HNO3"}, "H2SO4": {"H2SO4"},
}

MAX_PUBCHEM_SYNONYMS = 25

# ---------------------------------------------------------------------------------------------- normalização

_HYDRATE_WORDS = {
    "monohydrate": "monohydrate", "dihydrate": "dihydrate", "dehydrate": "dihydrate", "trihydrate": "trihydrate",
    "tetrahydrate": "tetrahydrate", "pentahydrate": "pentahydrate", "hexahydrate": "hexahydrate",
    "hydrate": "hydrate", "hydrated": "hydrate", "anhydrous": "anhydrous",
}
_HYDRATE_N = {"1": "monohydrate", "2": "dihydrate", "3": "trihydrate", "4": "tetrahydrate", "5": "pentahydrate",
              "6": "hexahydrate", "x": "hydrate", "n": "hydrate", "": "hydrate"}
_DOTS = "·•∙⋅・*"
_RE_HYDRATE_FORMULA = re.compile(r"\s*[" + re.escape(_DOTS) + r".]\s*([0-9xn]?)\s*h2o\b")
_RE_HYDRATE_WORD = re.compile(r"\b(" + "|".join(sorted(_HYDRATE_WORDS, key=len, reverse=True)) + r")\b")
_RE_PURITY = re.compile(r"\(\s*[<>≥≤~]?\s*\d+(\.\d+)?\s*%.*?\)|\b\d+(\.\d+)?\s*%")


def clean_text(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "").lower()
    s = s.replace("−", "-").replace("–", "-").replace("—", "-").replace("‐", "-")
    return s.strip()


def split_form(name: str) -> tuple[str, str]:
    """Separa a água de hidratação/forma do nome: ('haucl4', 'trihydrate')."""
    s = clean_text(name)
    s = _RE_PURITY.sub(" ", s)
    form = ""
    m = _RE_HYDRATE_FORMULA.search(s)
    if m:
        form = _HYDRATE_N.get(m.group(1), "hydrate")
        s = s[: m.start()] + s[m.end():]
    m = _RE_HYDRATE_WORD.search(s)
    if m:
        form = form or _HYDRATE_WORDS[m.group(1)]
        s = s[: m.start()] + s[m.end():]
    return s.strip(" ,;:"), form


def key_of(name: str) -> str:
    base, _ = split_form(name)
    return re.sub(r"[\s\-_]+", "", base).strip(" ,;:.")


# ---------------------------------------------------------------------------------------------- PubChem local

def _walk_pugview(sec: dict, path: list[str], out: dict[str, list[str]]):
    head = sec.get("TOCHeading")
    p = path + [head] if head else path
    for inf in sec.get("Information", []):
        val = inf.get("Value", {})
        strings = [x.get("String") for x in val.get("StringWithMarkup", []) if x.get("String")]
        if "Number" in val:
            strings += [str(x) for x in val["Number"]]
        out.setdefault(" > ".join(p), []).extend(strings)
    for s in sec.get("Section", []):
        _walk_pugview(s, p, out)


def _pugview_xml_to_dict(path: str) -> dict:
    """Converte o XML PUG View (mesma árvore do JSON) para o formato do JSON."""
    ns = {"p": "http://pubchem.ncbi.nlm.nih.gov/pug_view"}

    def sec(el):
        d = {"TOCHeading": (el.findtext("p:TOCHeading", default="", namespaces=ns) or None),
             "Information": [], "Section": [sec(s) for s in el.findall("p:Section", ns)]}
        for inf in el.findall("p:Information", ns):
            strings = [s.text for s in inf.findall("p:Value/p:StringWithMarkup/p:String", ns) if s.text]
            d["Information"].append({"Value": {"StringWithMarkup": [{"String": s} for s in strings]}})
        return d

    root = ET.parse(path).getroot()
    return {"Record": {"RecordType": root.findtext("p:RecordType", namespaces=ns),
                       "RecordNumber": int(root.findtext("p:RecordNumber", namespaces=ns)),
                       "RecordTitle": root.findtext("p:RecordTitle", namespaces=ns),
                       "Section": [sec(s) for s in root.findall("p:Section", ns)]}}


def _first(out: dict[str, list[str]], suffix: str) -> str:
    for k, v in out.items():
        if k.endswith(suffix) and v:
            return v[0]
    return ""


def _all(out: dict[str, list[str]], suffix: str) -> list[str]:
    vals: list[str] = []
    for k, v in out.items():
        if k.endswith(suffix):
            vals += [x for x in v if x not in vals]
    return vals


def load_pubchem_records(pubchem_dir: str = PUBCHEM_DIR) -> list[dict]:
    """Lê as fichas completas (COMPOUND_CID_*, REFCHEM_*) e as estruturas soltas (Structure2D/Conformer3D)."""
    recs: dict[tuple[str, int], dict] = {}
    files = sorted(glob.glob(os.path.join(pubchem_dir, "COMPOUND_CID_*.json")) +
                   glob.glob(os.path.join(pubchem_dir, "COMPOUND_CID_*.xml")) +
                   glob.glob(os.path.join(pubchem_dir, "REFCHEM_*.json")))
    for f in files:
        d = _pugview_xml_to_dict(f) if f.endswith(".xml") else json.load(open(f, encoding="utf-8"))
        r = d["Record"]
        out: dict[str, list[str]] = {}
        for s in r.get("Section", []):
            _walk_pugview(s, [], out)
        rtype = "refchem" if os.path.basename(f).startswith("REFCHEM") else "cid"
        num = int(r.get("RecordNumber") or re.findall(r"\d+", os.path.basename(f))[-1])
        syn = _all(out, "Depositor-Supplied Synonyms") or _all(out, "Synonyms")
        recs[(rtype, num)] = {
            "record_type": rtype, "id": num, "title": r.get("RecordTitle", ""),
            "molecular_formula": _first(out, "Molecular Formula"),
            "molecular_weight": _first(out, "Molecular Weight"),
            "iupac_name": _first(out, "IUPAC Name"),
            "smiles": _first(out, "Computed Descriptors > SMILES") or _first(out, "Canonical SMILES"),
            "inchi": _first(out, "Computed Descriptors > InChI"),
            "inchikey": _first(out, "Computed Descriptors > InChIKey") or _first(out, "Preferred InChI Key"),
            "cas": "|".join(dict.fromkeys(_all(out, "Other Identifiers > CAS"))),
            "synonyms": syn, "removed_synonyms": _all(out, "Removed Synonyms"),
            "source_file": os.path.relpath(f, ROOT),
        }
    # CIDs que só têm estrutura 2D/3D local (ex.: 311 ácido cítrico, 2681 cetrimônio, 20012)
    for f in sorted(glob.glob(os.path.join(pubchem_dir, "*_COMPOUND_CID_*.json"))):
        cid = int(re.findall(r"\d+", os.path.basename(f))[-1])
        if ("cid", cid) in recs:
            continue
        recs[("cid", cid)] = {"record_type": "cid", "id": cid, "title": "", "molecular_formula": "",
                              "molecular_weight": "", "iupac_name": "", "smiles": "", "inchi": "", "inchikey": "",
                              "cas": "", "synonyms": [], "removed_synonyms": [],
                              "source_file": os.path.relpath(f, ROOT) + " (só estrutura)"}
    return list(recs.values())


# ---------------------------------------------------------------------------------------------- dicionário

def _split(v: str) -> list[str]:
    return [x.strip() for x in (v or "").split("|") if x.strip()]


def load_aliases(path: str = ALIASES) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        rows = [l for l in fh if not l.startswith("#")]
    return list(csv.DictReader(rows, delimiter="\t"))


class Normalizer:
    """Converte nomes de reagentes (listas de materiais ou texto livre) em entidades canônicas."""

    def __init__(self, aliases_path: str = ALIASES):
        self.entities = load_aliases(aliases_path)
        self.by_id = {e["entity_id"]: e for e in self.entities}
        self.alias_map: dict[str, str] = {}
        self.abbrev_map: dict[str, str] = {}
        self.patterns: list[tuple[str, re.Pattern]] = []
        for e in self.entities:
            eid = e["entity_id"]
            for a in _split(e["aliases"]) + [e["canonical_name"], e["entity_id"]]:
                self.alias_map.setdefault(key_of(a), eid)
            for a in _split(e["abbrev"]):
                self.abbrev_map.setdefault(a, eid)
            if e["patterns"].strip():  # uma única regex por entidade (alternativas com "|")
                self.patterns.append((eid, re.compile(e["patterns"].strip())))
        self._abbrev_re = re.compile(r"(?<![A-Za-z0-9])(" + "|".join(
            re.escape(a) for a in sorted(self.abbrev_map, key=len, reverse=True)) + r")(?![A-Za-z0-9])") \
            if self.abbrev_map else None

    def normalize(self, name: str) -> dict | None:
        """Nome de material -> entidade (ou None). Ordem: sigla exata, alias exato, padrão regex."""
        if not name or not name.strip():
            return None
        raw = name.strip()
        base, form = split_form(raw)
        key = re.sub(r"[\s\-_]+", "", base).strip(" ,;:.")
        how, eid = "", None
        if raw in self.abbrev_map:
            eid, how = self.abbrev_map[raw], "abbrev"
        elif key in self.alias_map:
            eid, how = self.alias_map[key], "alias"
        else:
            for pid, pat in self.patterns:
                if pat.search(key) or pat.search(base):
                    eid, how = pid, "pattern"
                    break
        if eid is None:
            return None
        e = self.by_id[eid]
        ambiguous = eid == "HAuCl4" and not form and re.fullmatch(r"gold(\(iii\))?chloride", key) is not None
        return {"entity_id": eid, "canonical_name": e["canonical_name"], "role": e["role"],
                "pubchem_cid": e.get("pubchem_cid", ""), "form": form, "match": how, "ambiguous": ambiguous}

    def find_in_text(self, text: str) -> set[str]:
        """Entidades citadas em texto livre (passos de síntese, parágrafos)."""
        found: set[str] = set()
        if not text:
            return found
        low = clean_text(text)
        for eid, pat in self.patterns:
            if pat.search(low):
                found.add(eid)
        if self._abbrev_re:
            found.update(self.abbrev_map[m.group(1)] for m in self._abbrev_re.finditer(text))
        return found


DICT_FIELDS = ["entity_id", "role", "canonical_name", "chemical_name_pubchem", "formula", "molecular_formula",
               "molecular_weight", "pubchem_cid", "related_cids", "refchem_ids", "iupac_name", "smiles", "inchi",
               "inchikey", "cas", "synonyms", "alias_keys", "abbrev", "resolved_by", "notes"]


def _pug_rest_lookup(name: str) -> dict:
    """Consulta o PubChem por nome (requer rede). Retorna CID + propriedades ou {}."""
    import urllib.parse
    import urllib.request
    q = urllib.parse.quote(name)
    url = (f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{q}/property/"
           "Title,MolecularFormula,MolecularWeight,IUPACName,SMILES,InChI,InChIKey/JSON")
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            p = json.load(r)["PropertyTable"]["Properties"][0]
    except Exception as exc:  # noqa: BLE001 — rede bloqueada, nome não encontrado etc.
        print(f"   PubChem sem resposta para {name!r}: {exc}", file=sys.stderr)
        return {}
    return {"pubchem_cid": str(p.get("CID", "")), "chemical_name_pubchem": p.get("Title", ""),
            "molecular_formula": p.get("MolecularFormula", ""), "molecular_weight": str(p.get("MolecularWeight", "")),
            "iupac_name": p.get("IUPACName", ""), "smiles": p.get("SMILES") or p.get("CanonicalSMILES", ""),
            "inchi": p.get("InChI", ""), "inchikey": p.get("InChIKey", "")}


def build(online: bool = False, out_dir: str = REAGENTS_DIR) -> None:
    recs = load_pubchem_records()
    by_cid = {r["id"]: r for r in recs if r["record_type"] == "cid"}
    by_ref = {r["id"]: r for r in recs if r["record_type"] == "refchem"}
    used: set[tuple[str, int]] = set()

    rows = []
    for e in load_aliases():
        row = {k: "" for k in DICT_FIELDS}
        row.update({k: e.get(k, "") for k in ("entity_id", "role", "canonical_name", "formula", "pubchem_cid",
                                               "related_cids", "refchem_ids", "abbrev", "notes")})
        syn: list[str] = []
        src = []
        cids = [int(c) for c in _split(e["pubchem_cid"]) + _split(e["related_cids"])]
        for i, cid in enumerate(cids):
            r = by_cid.get(cid)
            if not r:
                continue
            used.add(("cid", cid))
            if i == 0:  # CID canônico preenche os identificadores
                row.update({"chemical_name_pubchem": r["title"], "molecular_formula": r["molecular_formula"],
                            "molecular_weight": r["molecular_weight"], "iupac_name": r["iupac_name"],
                            "smiles": r["smiles"], "inchi": r["inchi"], "inchikey": r["inchikey"], "cas": r["cas"]})
                src.append(f"pubchem_local:CID{cid}")
            syn += r["synonyms"][:MAX_PUBCHEM_SYNONYMS] + r["removed_synonyms"][:MAX_PUBCHEM_SYNONYMS]
        for ref in [int(x) for x in _split(e["refchem_ids"])]:
            r = by_ref.get(ref)
            if r:
                used.add(("refchem", ref))
                syn += r["synonyms"][:MAX_PUBCHEM_SYNONYMS]
                row["cas"] = row["cas"] or r["cas"]
                row["inchikey"] = row["inchikey"] or r["inchikey"]
                src.append(f"pubchem_local:RefChem{ref}")
        if online and not row["pubchem_cid"] and e["role"] not in ("product_or_element", "irrelevant"):
            got = _pug_rest_lookup(e["canonical_name"])
            if got:
                row.update(got)
                src.append("pubchem_online")
        row["synonyms"] = "|".join(dict.fromkeys(s for s in syn if s))   # sinônimos PubChem (fichas locais)
        row["alias_keys"] = e["aliases"]                                    # chaves curadas (normalizadas)
        row["resolved_by"] = "+".join(src) or "curado (sem ficha PubChem local)"
        rows.append(row)

    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "reagent_dictionary.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=DICT_FIELDS)
        w.writeheader()
        w.writerows(rows)

    rec_fields = ["record_type", "id", "title", "entity_id", "molecular_formula", "molecular_weight", "iupac_name",
                  "smiles", "inchi", "inchikey", "cas", "n_synonyms", "source_file"]
    cid2ent = {}
    for e in load_aliases():
        for c in _split(e["pubchem_cid"]) + _split(e["related_cids"]):
            cid2ent[("cid", int(c))] = e["entity_id"]
        for c in _split(e["refchem_ids"]):
            cid2ent[("refchem", int(c))] = e["entity_id"]
    with open(os.path.join(out_dir, "pubchem_records.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=rec_fields, extrasaction="ignore")
        w.writeheader()
        for r in sorted(recs, key=lambda r: (r["record_type"], r["id"])):
            w.writerow({**r, "entity_id": cid2ent.get((r["record_type"], r["id"]), ""),
                        "n_synonyms": len(r["synonyms"])})
    orphan = [r for r in recs if (r["record_type"], r["id"]) not in used]
    print(f"reagent_dictionary.csv: {len(rows)} entidades | pubchem_records.csv: {len(recs)} fichas"
          + (f" | sem entidade: {[(r['record_type'], r['id']) for r in orphan]}" if orphan else ""))


# ---------------------------------------------------------------------------------------------- Cruse et al.

def load_cruse_regex() -> tuple[list[tuple[str, re.Pattern]], set[str]]:
    """Regex de precursores e lista de "lixo" publicados com o dataset de Cruse et al. (pasta rsc/)."""
    path = os.path.join(CRUSE_RSC, "aunp_precursor_syns_regex.json")
    if not os.path.exists(path):
        return [], set()
    pats = [(label, re.compile("|".join(f"(?:{p})" for p in ps)))
            for label, ps in json.load(open(path, encoding="utf-8")).items()]
    garbage = set(json.load(open(os.path.join(CRUSE_RSC, "aunp_garbage_precs.json"), encoding="utf-8")))
    return pats, garbage


def cruse_label(pats, name: str) -> str:
    """Rótulo de Cruse cujo regex cobre o nome inteiro (mais longo vence), ou ''."""
    best, size = "", 0
    for label, pat in pats:
        for m in pat.finditer(name):
            if m.end() - m.start() > size and m.end() - m.start() >= 0.6 * len(name.strip()):
                best, size = label, m.end() - m.start()
    return best


def apply_cruse(out_dir: str = REAGENTS_DIR, top_unresolved: int = 300) -> None:
    n = Normalizer()
    pats, garbage = load_cruse_regex()
    data = json.load(open(CRUSE_JSON, encoding="utf-8"))
    counts: collections.Counter = collections.Counter()
    for art in data:
        for p in art["paragraphs"]:
            for m in p.get("materials_and_quantities") or []:
                counts[m["material"].strip()] += 1
    rows, ent_mentions, resolved_mentions = [], collections.Counter(), 0
    agree = collections.Counter()
    garbage_mentions = sum(c for name, c in counts.items() if name in garbage)
    total = sum(counts.values()) - garbage_mentions
    for name, c in counts.most_common():
        if name in garbage:
            continue
        r = n.normalize(name)
        if r:
            resolved_mentions += c
            ent_mentions[r["entity_id"]] += c
        lab = cruse_label(pats, name) if pats else ""
        if lab:
            ok = bool(r) and r["entity_id"] in CRUSE_LABEL_TO_ENTITIES.get(lab, set())
            agree["concorda" if ok else ("só Cruse" if not r else "diverge")] += c
        rows.append({"material_raw": name, "mentions": c, "entity_id": r["entity_id"] if r else "",
                     "canonical_name": r["canonical_name"] if r else "", "form": r["form"] if r else "",
                     "match": r["match"] if r else "", "ambiguous": int(r["ambiguous"]) if r else "",
                     "cruse_regex_label": lab})
    path = os.path.join(out_dir, "cruse_material_normalization.csv")
    resolved = [x for x in rows if x["entity_id"]]
    unresolved = [x for x in rows if not x["entity_id"]][:top_unresolved]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(resolved + unresolved)
    print(f"{len(counts)} nomes distintos, {total} menções; resolvidas {resolved_mentions} "
          f"({100 * resolved_mentions / total:.1f} %) por {len(resolved)} nomes → {len(ent_mentions)} entidades")
    print("HAuCl4: %d menções de %d grafias" % (ent_mentions["HAuCl4"],
                                               sum(1 for x in resolved if x["entity_id"] == "HAuCl4")))
    print(f"-> {os.path.relpath(path, ROOT)} (todas as resolvidas + {len(unresolved)} não resolvidas mais citadas)")
    if agree:
        tot = sum(agree.values())
        print(f"validação contra os regex de Cruse (rsc/, {len(pats)} rótulos; {garbage_mentions} menções-lixo excluídas): "
              + ", ".join(f"{k} {v} ({100 * v / tot:.1f} %)" for k, v in agree.most_common()))
        div = collections.Counter()
        for x in rows:
            if x["cruse_regex_label"] and x["entity_id"] and \
                    x["entity_id"] not in CRUSE_LABEL_TO_ENTITIES.get(x["cruse_regex_label"], set()):
                div[(x["cruse_regex_label"], x["entity_id"])] += x["mentions"]
        if div:
            print("  maiores divergências (rótulo Cruse -> entidade aqui):", div.most_common(8))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="gera reagent_dictionary.csv e pubchem_records.csv")
    b.add_argument("--online", action="store_true", help="resolve no PubChem as entidades sem CID local")
    nz = sub.add_parser("normalize", help="normaliza nomes passados na linha de comando")
    nz.add_argument("names", nargs="+")
    sub.add_parser("cruse", help="aplica ao dataset de Cruse et al. e gera o relatório de cobertura")
    a = ap.parse_args()
    if a.cmd == "build":
        build(online=a.online)
    elif a.cmd == "normalize":
        n = Normalizer()
        for name in a.names:
            print(f"{name!r:45} -> {n.normalize(name)}")
    else:
        apply_cruse()


if __name__ == "__main__":
    main()
