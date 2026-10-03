# SOP-DATA-01 — Registro, validação e versionamento dos dados (§4.17, DMP) (v0.1, RASCUNHO)

1. No mesmo dia: preencher as tabelas de `datasets/lab/` (modelos em `datasets/data-model/templates/`), salvar como
   **CSV UTF-8 com vírgula** (não o "CSV (separado por ;)" do Excel em português) e ponto decimal.
   Em `spectra.csv` basta registrar cada leitura (arquivo bruto em `raw_data/`, branco, diluição, caminho óptico):
   **não digite J, LSPR nem tamanho** — são derivados no passo 3.
2. Saídas das ferramentas de caracterização (`tem.py --out`, `dls.py --out`, …):
   `python code/campaign/ingest.py add datasets/lab saida_tem.csv` (recusa `measurement_id` repetido com outro valor).
3. Derivar os desfechos: `python code/campaign/ingest.py derive datasets/lab --write` — J (Eq. 1, regras do
   pré-registro), LSPR, A_LSPR e tamanho (TEM; sem TEM, ajuste de Mie do UV-Vis calibrado na TEM do laboratório,
   com a incerteza da calibração); CV só da TEM. Valores digitados que divergem dos brutos param a gravação.
   Antes de cada rodada: `python code/campaign/ingest.py check datasets/lab` (código 1 se algo diverge).
4. Validar: `python tools/data_sources/lab_data_model.py validate datasets/lab` (0 erros).
5. QC: `python code/qc/qc_check.py datasets/lab` → `qc_results.csv` (sínteses com `fail` não entram no modelo).
6. Instance Map: `python tools/data_sources/instance_map.py build datasets/lab` (proveniência e arquivos ausentes).
7. Commit com mensagem "dados: dia XX (<n> sínteses)"; nunca editar um arquivo bruto — correções vão em `notes`.
8. Antes da 1ª rodada adaptativa: `python code/campaign/prereg.py freeze`.
