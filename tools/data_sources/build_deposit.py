#!/usr/bin/env python3
"""Monta uma versão do depósito GO-AuNP-Autonomous-Design (Zenodo / MDF / NIST MDR) a partir do repositório.

Estrutura gerada (proposta do projeto; cada versão recebe um DOI próprio no Zenodo, sob um "concept DOI" comum):
  GO-AuNP-Autonomous-Design/
    dataset/{literature,go_batches,synthesis,characterization,raw_data}
    code/{go_navigator,aunp_designer,transfer_learning,benchmarking}
    models/  protocols/  metadata/  documentation/
Os dados de laboratório são lidos de datasets/lab/ (preencha a partir de datasets/data-model/templates/) e validados
antes da cópia; o que não existir ainda fica só com o README da pasta. Gera MANIFEST.tsv (sha256 de cada arquivo)
e um .zip pronto para upload.

Uso:
    python tools/data_sources/build_deposit.py --version 0.1.0              # -> outputs/deposit/GO-AuNP-Autonomous-Design-v0.1.0{/,.zip}
    python tools/data_sources/build_deposit.py --version 0.1.0 --lab /caminho/para/csvs --code /caminho/do/codigo
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SKELETON = os.path.join(ROOT, "deposit", "GO-AuNP-Autonomous-Design")
NAME = "GO-AuNP-Autonomous-Design"

# destino no depósito -> lista de origens (glob relativo ao repositório; "{lab}" = pasta de dados de laboratório)
MAPPING = {
    "dataset/literature": ["datasets/literature-seed/*.csv", "datasets/literature-seed/summary.json",
                           "datasets/reagents/reagent_dictionary.csv", "datasets/reagents/cruse_material_normalization.csv",
                           "outputs/literature_pipeline/works.csv", "outputs/literature_pipeline/query.json"],
    "dataset/go_batches": ["{lab}/reagent_lots.csv", "{lab}/go_batches.csv", "{lab}/go_samples.csv",
                           "{lab}/go_descriptors.csv"],
    "dataset/synthesis": ["{lab}/aunp_syntheses.csv", "{lab}/outcomes.csv"],
    "dataset/characterization": ["{lab}/go_characterization.csv", "{lab}/aunp_characterization.csv"],
    "dataset/raw_data": ["{lab}/raw_data/**/*"],
    "protocols": ["{lab}/protocols.csv", "{lab}/protocols/**/*"],
    "metadata": ["datasets/data-model/data_dictionary.csv", "datasets/data-model/go_aunp.schema.json",
                 "tools/data_sources/sources.tsv", "deposit/GO-AuNP-Autonomous-Design/.zenodo.json",
                 "deposit/GO-AuNP-Autonomous-Design/CITATION.cff"],
    "documentation": ["deposit/GO-AuNP-Autonomous-Design/README.md", "docs/FONTES_DE_DADOS.md"],
    "code/go_navigator": ["{code}/go_navigator/**/*"],
    "code/aunp_designer": ["{code}/aunp_designer/**/*"],
    "code/transfer_learning": ["{code}/transfer_learning/**/*"],
    "code/benchmarking": ["{code}/benchmarking/**/*"],
    "models": ["{code}/models/**/*"],
}

FOLDER_DOCS = {
    "dataset/literature": "Semente da literatura (Cruse + NSP + AuNCs normalizados), dicionário de reagentes e busca OpenAlex.",
    "dataset/go_batches": "Lotes de reagentes e de GO, preparo das amostras e descritores por lote com incerteza.",
    "dataset/synthesis": "Sínteses de AuNP (condições = variáveis do otimizador) e desfechos/objetivos.",
    "dataset/characterization": "Medidas de GO (XPS, Raman, AFM…) e de AuNP (UV-Vis, TEM, DLS…) com incerteza.",
    "dataset/raw_data": "Arquivos brutos dos instrumentos (espectros, imagens), referenciados em raw_data_file.",
    "code/go_navigator": "Código do GO Navigator (descritores de lote, espaço latente de GO).",
    "code/aunp_designer": "Código do AuNP Designer (GP Matérn-5/2+ARD, qNEHVI, MISO).",
    "code/transfer_learning": "Transferência entre lotes/fontes de GO.",
    "code/benchmarking": "Benchmarks (BOCoDe, vaso de pressão, COFs) e scripts de avaliação.",
    "models": "Modelos treinados (GPs, redes) com a versão do código e dos dados usados.",
    "protocols": "SOPs versionados (protocols.csv + PDFs).",
    "metadata": "Dicionário de dados, JSON Schema, registro de fontes, .zenodo.json, CITATION.cff.",
    "documentation": "README do depósito e documentação das fontes.",
}


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", required=True)
    ap.add_argument("--lab", default=os.path.join(ROOT, "datasets", "lab"))
    ap.add_argument("--code", default=os.path.join(ROOT, "code"), help="pasta com go_navigator/, aunp_designer/…")
    ap.add_argument("--out", default=os.path.join(ROOT, "outputs", "deposit"))
    ap.add_argument("--no-validate", action="store_true")
    a = ap.parse_args()

    if os.path.isdir(a.lab) and not a.no_validate:
        rc = subprocess.call([sys.executable, os.path.join(os.path.dirname(__file__), "lab_data_model.py"),
                              "validate", a.lab])
        if rc:
            sys.exit("dados de laboratório com erros — corrija ou use --no-validate")

    dest = os.path.join(a.out, f"{NAME}-v{a.version}")
    if os.path.exists(dest):
        shutil.rmtree(dest)
    copied = []
    for sub, patterns in MAPPING.items():
        os.makedirs(os.path.join(dest, sub), exist_ok=True)
        for pat in patterns:
            base = ROOT
            if pat.startswith("{lab}"):
                base, pat = a.lab, pat[len("{lab}/"):]
            elif pat.startswith("{code}"):
                base, pat = a.code, pat[len("{code}/"):]
            for src in glob.glob(os.path.join(base, pat), recursive=True):
                if not os.path.isfile(src) or "__pycache__" in src:
                    continue
                rel = os.path.relpath(src, base)
                # mantém subpastas de raw_data/protocols/code; arquivos avulsos vão direto
                keep = any(pat.startswith(p) for p in ("raw_data", "protocols/", "go_navigator", "aunp_designer",
                                                       "transfer_learning", "benchmarking", "models"))
                tail = rel.split(os.sep, 1)[1] if keep and os.sep in rel else os.path.basename(src)
                out = os.path.join(dest, sub, tail)
                os.makedirs(os.path.dirname(out), exist_ok=True)
                shutil.copy2(src, out)
                copied.append(out)
    for sub, doc in FOLDER_DOCS.items():
        if not os.listdir(os.path.join(dest, sub)):
            with open(os.path.join(dest, sub, "README.txt"), "w", encoding="utf-8") as fh:
                fh.write(f"PENDENTE nesta versão. Conteúdo previsto: {doc}\n")
    # README da estrutura na raiz e versão no .zenodo.json
    shutil.copy2(os.path.join(SKELETON, "README.md"), os.path.join(dest, "README.md"))
    zj = os.path.join(dest, "metadata", ".zenodo.json")
    if os.path.exists(zj):
        meta = json.load(open(zj, encoding="utf-8"))
        meta["version"] = a.version
        json.dump(meta, open(os.path.join(dest, ".zenodo.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    with open(os.path.join(dest, "MANIFEST.tsv"), "w", encoding="utf-8") as fh:
        fh.write("path\tbytes\tsha256\n")
        for root, _d, files in os.walk(dest):
            for f in sorted(files):
                p = os.path.join(root, f)
                if f != "MANIFEST.tsv":
                    fh.write(f"{os.path.relpath(p, dest)}\t{os.path.getsize(p)}\t{sha256(p)}\n")
    archive = shutil.make_archive(dest, "zip", root_dir=a.out, base_dir=os.path.basename(dest))
    empty = [s for s in MAPPING if os.listdir(os.path.join(dest, s)) == ["README.txt"]]
    print(f"{len(copied)} arquivos -> {os.path.relpath(dest, ROOT)}/ e {os.path.relpath(archive, ROOT)}")
    if empty:
        print("pastas ainda vazias (preencher antes de publicar):", ", ".join(empty))


if __name__ == "__main__":
    main()
