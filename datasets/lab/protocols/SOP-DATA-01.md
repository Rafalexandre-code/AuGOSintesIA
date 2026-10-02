# SOP-DATA-01 — Registro, validação e versionamento dos dados (§4.17, DMP) (v0.1, RASCUNHO)

1. No mesmo dia: preencher as tabelas de `datasets/lab/` (modelos em `datasets/data-model/templates/`), salvar como
   **CSV UTF-8 com vírgula** (não o "CSV (separado por ;)" do Excel em português) e ponto decimal.
2. Validar: `python tools/data_sources/lab_data_model.py validate datasets/lab` (0 erros).
3. QC: `python code/qc/qc_check.py datasets/lab` → `qc_results.csv` (sínteses com `fail` não entram no modelo).
4. Instance Map: `python tools/data_sources/instance_map.py datasets/lab` (proveniência e arquivos ausentes).
5. Commit com mensagem "dados: dia XX (<n> sínteses)"; nunca editar um arquivo bruto — correções vão em `notes`.
6. Antes da 1ª rodada adaptativa: `python code/campaign/prereg.py freeze`.
