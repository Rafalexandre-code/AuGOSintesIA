# data-model — modelo de dados do laboratório GO–AuNP

Inspirado no NanoCommons KnowledgeBase / eNanoMapper / ACEnano (substância → protocolo → medida com incerteza).
Cadeia: **lote de reagente (+ análises de impurezas) → lote de GO → preparo da amostra → XPS/Raman/AFM → descritores com incerteza →
síntese de AuNP → UV-Vis/TEM → desfecho**. A fonte única é `tools/data_sources/lab_data_model.py`.

| Arquivo | Conteúdo |
|---|---|
| `templates/*.csv` | cabeçalhos das 13 tabelas: `protocols`, `reagent_lots`, `reagent_analyses` (impurezas por lote — §4.3), `spectra` (arquivo bruto + diluição, caminho óptico, branco, tempo após o preparo — §4.4/§4.17), `go_batches`, `go_samples`, `go_characterization`, `go_descriptors`, `aunp_syntheses` (+ `hardware`, `is_control`, `preparation_id`, `block`, `run_order`, `status`), `aunp_characterization`, `outcomes`, `resources` (massas, custos, horas de instrumento e energia por síntese/técnica — §4.14) e `qc_results` (verificações de `code/qc/qc_check.py`: pass/warn/fail) |
| `data_dictionary.csv` | 198 colunas: tabela, tipo, obrigatória, unidade, valores permitidos, descrição |
| `go_aunp.schema.json` | JSON Schema (draft 2020-12) do registro completo, para exportar a MDF/Zenodo |

Fluxo: copie os modelos para `datasets/lab/`, preencha (uma linha por grandeza medida, sempre com `unit`,
`uncertainty` e `uncertainty_type`) e valide com
`python tools/data_sources/lab_data_model.py validate datasets/lab`. O validador confere chaves únicas e
estrangeiras (inclusive `entity_id` contra `datasets/reagents/reagent_dictionary.csv`), números, vocabulários
e incertezas negativas,
datas fora do formato AAAA-MM-DD e vírgula decimal. CSV salvo pelo Excel em português (separado por `;`) é recusado
com a instrução de salvar como "CSV UTF-8 (delimitado por vírgulas)" com ponto decimal. Inteiros como `3.0` são aceitos. `aunp_syntheses.design_id`/`fidelity` ligam cada experimento ao otimizador (qNEHVI/MISO),
e `go_descriptors` guarda média ± sd por lote e o desvio entre lotes, que o GO Navigator e a transferência entre lotes usam.
