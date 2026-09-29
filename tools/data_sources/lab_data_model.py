#!/usr/bin/env python3
"""Modelo de dados do laboratório GO–AuNP (inspirado no NanoCommons KnowledgeBase / eNanoMapper / ACEnano).

Cadeia: lote de reagente (+ análises de impurezas) → lote de GO → preparo da amostra → XPS/Raman/AFM… → descritores com incerteza por lote
→ síntese de AuNP (condições + id do experimento do otimizador) → UV-Vis/TEM… → desfecho (objetivos/restrições).
Cada medida guarda valor, incerteza, tipo de incerteza, nº de réplicas, unidade, instrumento, protocolo e arquivo bruto
— o equivalente ao "effect record" do eNanoMapper (substância → protocolo → resultado).

Este arquivo é a fonte única do modelo: gera os modelos de planilha, o dicionário de dados e o JSON Schema, e valida
uma pasta de CSVs preenchidos (chaves únicas, chaves estrangeiras, números, vocabulários, incertezas).

Uso:
    python tools/data_sources/lab_data_model.py templates            # -> datasets/data-model/{templates/,data_dictionary.csv,go_aunp.schema.json}
    python tools/data_sources/lab_data_model.py validate <pasta>     # valida <pasta>/<tabela>.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "datasets", "data-model")
REAGENT_DICT = os.path.join(ROOT, "datasets", "reagents", "reagent_dictionary.csv")

# (coluna, tipo, obrigatória, unidade, descrição, vocabulário/FK)
# tipo: id | fk:<tabela> | str | float | int | date | enum | list
S, F, I, D, E, L = "str", "float", "int", "date", "enum", "list"
UNC = ["sd", "sem", "ci95", "range", "instrument", "none"]
MEAS_TAIL = [
    ("value", F, True, "", "valor medido/derivado", None),
    ("uncertainty", F, False, "", "incerteza do valor (mesma unidade)", None),
    ("uncertainty_type", E, False, "", "tipo de incerteza", UNC),
    ("n_replicates", I, False, "", "nº de réplicas/regiões/partículas usadas", None),
    ("unit", S, True, "", "unidade (UO/SI): nm, eV, %, at%, mg/mL, mV, a.u. …", None),
    ("instrument", S, False, "", "equipamento/modelo", None),
    ("method_details", S, False, "", "modelo de ajuste, fonte de excitação, faixa, deconvolução…", None),
    ("raw_data_file", S, False, "", "caminho relativo em dataset/raw_data/", None),
    ("date", D, False, "", "AAAA-MM-DD", None),
    ("operator", S, False, "", "quem mediu", None),
    ("protocol_id", "fk:protocols", False, "", "protocolo (SOP) usado", None),
    ("ontology_term", S, False, "", "termo de ontologia (eNanoMapper/CHMO/BAO) para a técnica ou grandeza", None),
    ("notes", S, False, "", "", None),
]

TABLES: dict[str, dict] = {
    "protocols": {"key": "protocol_id", "doc": "Procedimentos operacionais (SOPs) versionados em protocols/.", "cols": [
        ("protocol_id", "id", True, "", "ex.: SOP-GO-DISP-01", None),
        ("title", S, True, "", "", None), ("version", S, True, "", "", None),
        ("file", S, False, "", "caminho em protocols/", None), ("doi", S, False, "", "DOI (protocols.io/Zenodo)", None),
        ("description", S, False, "", "", None)]},
    "reagent_lots": {"key": "lot_id", "doc": "Frascos/lotes de reagente, normalizados pelo dicionário PubChem.", "cols": [
        ("lot_id", "id", True, "", "ex.: LOT-HAuCl4-2026-01", None),
        ("entity_id", "fk:reagent_dictionary", True, "", "entidade de datasets/reagents/reagent_dictionary.csv", None),
        ("chemical_name", S, True, "", "nome como no rótulo (ex.: Gold(III) chloride trihydrate)", None),
        ("canonical_name", S, False, "", "nome canônico (copiado do dicionário)", None),
        ("pubchem_cid", I, False, "", "CID PubChem", None), ("smiles", S, False, "", "", None),
        ("inchi", S, False, "", "", None), ("supplier", S, True, "", "fornecedor", None),
        ("catalog_number", S, False, "", "", None), ("lot_number", S, True, "", "lote do fabricante", None),
        ("purity", F, False, "%", "pureza declarada", None),
        ("purity_basis", S, False, "", "ex.: trace metals basis, ACS reagent", None),
        ("hydrate_form", E, False, "", "forma", ["anhydrous", "monohydrate", "dihydrate", "trihydrate",
                                                  "tetrahydrate", "hydrate", "solution", ""]),
        ("received_date", D, False, "", "", None), ("opened_date", D, False, "", "", None),
        ("storage", S, False, "", "ex.: 4 °C, escuro, dessecador", None),
        ("coa_file", S, False, "", "certificado de análise (metadata/)", None), ("notes", S, False, "", "", None)]},
    "reagent_analyses": {"key": "analysis_id", "doc": "Módulo de impurezas (§4.3): análises de cada lote de reagente (iodeto no CTAB, metais por ICP-MS, água por KF, solventes residuais…).", "cols": [
        ("analysis_id", "id", True, "", "ex.: RA-0001", None),
        ("lot_id", "fk:reagent_lots", True, "", "lote analisado", None),
        ("analyte", S, True, "", "iodide, Fe, Cu, Ag, water, residual_solvent, assay…", None),
        ("method", S, False, "", "IC, ICP-MS, ICP-OES, KF, GC, titulação, CoA…", None),
    ] + MEAS_TAIL},
    "spectra": {"key": "spectrum_id", "doc": "Espectros brutos e metadados de aquisição padronizados (§4.4/§4.17): diluição, caminho óptico, branco, tempo após o preparo.", "cols": [
        ("spectrum_id", "id", True, "", "ex.: UV-0001", None),
        ("synthesis_id", "fk:aunp_syntheses", False, "", "síntese (vazio se for do GO)", None),
        ("go_sample_id", "fk:go_samples", False, "", "amostra de GO (brancos de GO, Raman/XPS)", None),
        ("technique", E, True, "", "técnica", ["UV-Vis", "Raman", "XPS", "FTIR", "XRD", "DLS", "SAXS", "other"]),
        ("file", S, True, "", "arquivo bruto em dataset/raw_data/ (CSV: eixo, intensidade)", None),
        ("blank_spectrum_id", "fk:spectra", False, "", "espectro do branco usado na subtração", None),
        ("dilution_factor", F, False, "", "fator de diluição (≥ 1)", None),
        ("path_length_mm", F, False, "mm", "caminho óptico da cubeta", None),
        ("time_after_prep_min", F, False, "min", "tempo entre o preparo e a leitura", None),
        ("instrument", S, False, "", "", None), ("date", D, False, "", "", None),
        ("operator", S, False, "", "", None), ("protocol_id", "fk:protocols", False, "", "", None),
        ("notes", S, False, "", "", None)]},
    "go_batches": {"key": "go_batch_id", "doc": "Lote de óxido de grafeno (comercial ou sintetizado) — a fonte de variabilidade.", "cols": [
        ("go_batch_id", "id", True, "", "ex.: GO-B01", None),
        ("source_type", E, True, "", "origem", ["commercial", "lab_synthesized"]),
        ("supplier", S, False, "", "fornecedor (se comercial)", None), ("product_code", S, False, "", "", None),
        ("lot_number", S, False, "", "", None),
        ("synthesis_method", E, False, "", "rota de oxidação", ["Hummers", "modified_Hummers", "improved_Hummers_Tour",
                                                                "Brodie", "Staudenmaier", "electrochemical", "other", ""]),
        ("graphite_lot_id", "fk:reagent_lots", False, "", "lote do grafite precursor", None),
        ("oxidant_to_graphite_ratio", F, False, "g/g", "KMnO4:grafite (m/m)", None),
        ("oxidation_time_h", F, False, "h", "", None), ("oxidation_temperature_C", F, False, "°C", "", None),
        ("purification", S, False, "", "lavagens, diálise, centrifugação", None),
        ("stock_concentration_mg_mL", F, False, "mg/mL", "concentração do estoque", None),
        ("dispersion_medium", S, False, "", "", None), ("date_prepared", D, False, "", "", None),
        ("operator", S, False, "", "", None), ("protocol_id", "fk:protocols", False, "", "", None),
        ("notes", S, False, "", "", None)]},
    "go_samples": {"key": "go_sample_id", "doc": "Preparo da amostra de GO usada na caracterização e/ou na síntese.", "cols": [
        ("go_sample_id", "id", True, "", "ex.: GO-B01-S03", None),
        ("go_batch_id", "fk:go_batches", True, "", "", None),
        ("prep_type", E, True, "", "forma da amostra", ["dispersion", "film_dropcast", "film_spincoat", "powder",
                                                          "freeze_dried", "on_substrate", "other"]),
        ("concentration_mg_mL", F, False, "mg/mL", "", None), ("sonication_time_min", F, False, "min", "", None),
        ("sonication_power_W", F, False, "W", "", None), ("centrifugation_rcf_g", F, False, "g", "", None),
        ("centrifugation_time_min", F, False, "min", "", None), ("pH", F, False, "", "", None),
        ("substrate", S, False, "", "Si/SiO2, mica, grade de TEM…", None),
        ("age_days", F, False, "d", "idade da dispersão no uso", None), ("date", D, False, "", "", None),
        ("operator", S, False, "", "", None), ("protocol_id", "fk:protocols", False, "", "", None),
        ("notes", S, False, "", "", None)]},
    "go_characterization": {"key": "measurement_id", "doc": "Medidas do GO (uma linha por grandeza medida).", "cols": [
        ("measurement_id", "id", True, "", "ex.: M-GO-0001", None),
        ("go_sample_id", "fk:go_samples", True, "", "", None),
        ("technique", E, True, "", "técnica", ["XPS", "Raman", "AFM", "UV-Vis", "FTIR", "TGA", "XRD", "DLS", "zeta",
                                               "elemental_analysis", "SEM", "TEM", "other"]),
        ("quantity", S, True, "", "C_O_ratio, sp2_fraction, C-O_fraction, C=O_fraction, O-C=O_fraction, ID_IG, "
                                  "I2D_IG, La_nm, thickness_nm, lateral_size_um, n_layers, abs_230nm …", None),
        ("spectrum_id", "fk:spectra", False, "", "espectro de origem (proveniência)", None),
    ] + MEAS_TAIL},
    "go_descriptors": {"key": ("go_batch_id", "descriptor"), "doc": "Descritores por lote com incerteza (entrada do GO Navigator / transferência entre lotes).", "cols": [
        ("go_batch_id", "fk:go_batches", True, "", "", None),
        ("descriptor", S, True, "", "mesmo nome de go_characterization.quantity", None),
        ("mean", F, True, "", "estimativa do lote", None), ("sd", F, False, "", "desvio dentro do lote", None),
        ("n", I, False, "", "nº de medidas agregadas", None), ("unit", S, False, "", "", None),
        ("method", E, False, "", "como foi agregado", ["pooled", "hierarchical_bayes", "bootstrap", "single"]),
        ("between_batch_sd", F, False, "", "desvio entre lotes (efeito de lote), se estimado", None),
        ("source_measurements", L, False, "", "measurement_id separados por |", None),
        ("notes", S, False, "", "", None)]},
    "aunp_syntheses": {"key": "synthesis_id", "doc": "Síntese de AuNP (com ou sem GO): condições = variáveis de projeto do otimizador.", "cols": [
        ("synthesis_id", "id", True, "", "ex.: SYN-0001", None),
        ("go_batch_id", "fk:go_batches", False, "", "vazio = controle sem GO", None),
        ("go_sample_id", "fk:go_samples", False, "", "", None),
        ("gold_precursor_lot_id", "fk:reagent_lots", True, "", "lote de HAuCl4", None),
        ("reductant_lot_id", "fk:reagent_lots", False, "", "", None),
        ("stabilizer_lot_id", "fk:reagent_lots", False, "", "", None),
        ("method", E, True, "", "rota", ["in_situ_reduction_on_GO", "ex_situ_assembly", "one_pot", "seed_mediated",
                                          "other"]),
        ("HAuCl4_mM", F, True, "mM", "concentração final de Au(III)", None),
        ("reductant_mM", F, False, "mM", "", None), ("reductant_to_Au_ratio", F, False, "mol/mol", "", None),
        ("stabilizer_mM", F, False, "mM", "", None), ("GO_mg_mL", F, False, "mg/mL", "", None),
        ("pH", F, False, "", "", None), ("temperature_C", F, False, "°C", "", None),
        ("time_min", F, False, "min", "", None), ("addition_order", S, False, "", "ex.: GO>HAuCl4>NaBH4", None),
        ("addition_rate_mL_min", F, False, "mL/min", "", None), ("stirring_rpm", F, False, "rpm", "", None),
        ("total_volume_mL", F, False, "mL", "", None),
        ("campaign_id", S, False, "", "campanha de otimização", None),
        ("design_id", S, False, "", "id do candidato proposto pelo otimizador (iteração/lote)", None),
        ("fidelity", E, False, "", "fidelidade (MISO/multi-fidelidade)", ["high", "low", "simulation", ""]),
        ("platform", E, False, "", "", ["manual", "robot", "flow", ""]),
        ("hardware", S, False, "", "equipamento de aquecimento/mistura (hot plate, banho-maria, reator de fluxo…) — §4.7", None),
        ("is_control", E, False, "", "controle: sem GO / branco de GO tratado / réplica de referência (§4.17)",
         ["none", "no_GO", "GO_blank", "reference", ""]),
        ("preparation_id", S, False, "", "preparação física (alíquotas da mesma preparação NÃO são sínteses novas)", None),
        ("block", S, False, "", "bloco de randomização (dia/operador) — §4.9, §4.11", None),
        ("run_order", I, False, "", "ordem de execução dentro do bloco (randomizada)", None),
        ("status", E, False, "", "resultado da execução (falhas ficam no registro — §4.17)",
         ["done", "failed", "repeated", "planned", ""]),
        ("date", D, False, "", "", None),
        ("operator", S, False, "", "", None), ("protocol_id", "fk:protocols", False, "", "", None),
        ("notes", S, False, "", "", None)]},
    "aunp_characterization": {"key": "measurement_id", "doc": "Medidas do produto (UV-Vis, TEM, DLS, zeta, XRD, XPS, ICP…).", "cols": [
        ("measurement_id", "id", True, "", "ex.: M-AU-0001", None),
        ("synthesis_id", "fk:aunp_syntheses", True, "", "", None),
        ("technique", E, True, "", "técnica", ["UV-Vis", "TEM", "SEM", "DLS", "zeta", "XRD", "XPS", "ICP-OES",
                                               "ICP-MS", "SERS", "catalysis", "other"]),
        ("quantity", S, True, "", "LSPR_nm, LSPR_FWHM_nm, A_LSPR, A400, size_mean_nm, size_sd_nm, n_particles, "
                                  "aspect_ratio, hydrodynamic_nm, PDI, zeta_mV, Au_loading_wt, yield_pct, k_app_s-1, spectral_loss_J, "
                                  "GO_associated_fraction …", None),
        ("spectrum_id", "fk:spectra", False, "", "espectro de origem (proveniência)", None),
    ] + MEAS_TAIL},
    "outcomes": {"key": ("synthesis_id", "objective"), "doc": "Objetivos/restrições usados pelo otimizador (derivados das medidas).", "cols": [
        ("synthesis_id", "fk:aunp_syntheses", True, "", "", None),
        ("objective", S, True, "", "ex.: LSPR_nm, size_sd_nm, yield_pct, k_app", None),
        ("value", F, True, "", "", None), ("uncertainty", F, False, "", "", None),
        ("direction", E, True, "", "", ["maximize", "minimize", "target", "constraint"]),
        ("target_value", F, False, "", "alvo ou limite", None),
        ("feasible", I, False, "", "1/0 (restrições satisfeitas)", None),
        ("derived_from", L, False, "", "measurement_id separados por |", None),
        ("model_version", S, False, "", "versão do modelo/otimizador que usou o dado", None),
        ("notes", S, False, "", "", None)]},
}
ORDER = list(TABLES)


def write_templates(out: str = OUT) -> None:
    tdir = os.path.join(out, "templates")
    os.makedirs(tdir, exist_ok=True)
    rows = []
    schema = {"$schema": "https://json-schema.org/draft/2020-12/schema",
              "$id": "https://github.com/Rafalexandre-code/AuGOSintesIA/datasets/data-model/go_aunp.schema.json",
              "title": "GO–AuNP laboratory record", "type": "object", "properties": {}, "$defs": {}}
    tmap = {"id": "string", S: "string", F: "number", I: "integer", D: "string", E: "string", L: "string"}
    for t in ORDER:
        spec = TABLES[t]
        with open(os.path.join(tdir, f"{t}.csv"), "w", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerow([c[0] for c in spec["cols"]])
        props, req = {}, []
        for name, typ, required, unit, desc, vocab in spec["cols"]:
            rows.append({"table": t, "column": name, "type": typ, "required": int(required), "unit": unit,
                         "allowed_values": "|".join(v for v in vocab if v) if vocab else "", "description": desc})
            p = {"type": tmap.get(typ, "string"), "description": desc}
            if typ == D:
                p["format"] = "date"
            if typ == E and vocab:
                p["enum"] = vocab
            if unit:
                p["x-unit"] = unit
            if typ.startswith("fk:"):
                p["x-foreign-key"] = typ[3:]
            props[name] = p
            if required:
                req.append(name)
        schema["$defs"][t] = {"type": "object", "description": spec["doc"], "properties": props, "required": req}
        schema["properties"][t] = {"type": "array", "items": {"$ref": f"#/$defs/{t}"}}
    with open(os.path.join(out, "data_dictionary.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    with open(os.path.join(out, "go_aunp.schema.json"), "w", encoding="utf-8") as fh:
        json.dump(schema, fh, ensure_ascii=False, indent=2)
    print(f"{len(ORDER)} tabelas, {len(rows)} colunas -> {os.path.relpath(out, ROOT)}/")


def _read(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def validate(folder: str) -> int:
    errors, warns = [], []
    data = {t: _read(os.path.join(folder, f"{t}.csv")) for t in ORDER if os.path.exists(os.path.join(folder, f"{t}.csv"))}
    keys: dict[str, set] = {}
    if os.path.exists(REAGENT_DICT):
        keys["reagent_dictionary"] = {r["entity_id"] for r in _read(REAGENT_DICT)}
    for t, rows in data.items():
        k = TABLES[t]["key"]
        keys[t] = {tuple(r.get(c, "") for c in k) if isinstance(k, tuple) else r.get(k, "") for r in rows}
        if len(keys[t]) != len(rows):
            errors.append(f"{t}: chave {k} repetida")
    for t, rows in data.items():
        cols = {c[0]: c for c in TABLES[t]["cols"]}
        missing = [c for c, spec in cols.items() if spec[2] and rows and c not in rows[0]]
        if missing:
            errors.append(f"{t}: colunas obrigatórias ausentes {missing}")
        extra = [c for c in (rows[0] if rows else {}) if c not in cols]
        if extra:
            warns.append(f"{t}: colunas fora do modelo {extra}")
        for i, r in enumerate(rows, start=2):
            for name, typ, required, _u, _d, vocab in cols.values():
                v = (r.get(name) or "").strip()
                where = f"{t}.csv:{i} {name}"
                if not v:
                    if required:
                        errors.append(f"{where}: obrigatório vazio")
                    continue
                if typ in (F, I):
                    try:
                        x = float(v) if typ == F else int(v)
                        if name in ("uncertainty", "sd", "between_batch_sd") and x < 0:
                            errors.append(f"{where}: incerteza negativa")
                    except ValueError:
                        errors.append(f"{where}: não numérico {v!r}")
                elif typ == E and vocab and v not in vocab:
                    warns.append(f"{where}: {v!r} fora do vocabulário {[x for x in vocab if x]}")
                elif typ.startswith("fk:"):
                    ref = typ[3:]
                    if ref in keys and v not in keys[ref]:
                        errors.append(f"{where}: {v!r} não existe em {ref}")
                    elif ref not in keys:
                        warns.append(f"{where}: tabela {ref} ausente, chave não conferida")
            if t.endswith("characterization") and r.get("uncertainty") and not r.get("uncertainty_type"):
                warns.append(f"{t}.csv:{i}: incerteza sem uncertainty_type")
    for w in warns:
        print("AVISO ", w)
    for e in errors:
        print("ERRO  ", e)
    print(f"{sum(len(v) for v in data.values())} linhas em {len(data)} tabelas: {len(errors)} erro(s), {len(warns)} aviso(s)")
    return 1 if errors else 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("templates")
    v = sub.add_parser("validate")
    v.add_argument("folder")
    a = ap.parse_args()
    if a.cmd == "templates":
        write_templates()
    else:
        sys.exit(validate(a.folder))


if __name__ == "__main__":
    main()
