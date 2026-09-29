# data-model — modelo de dados do laboratório GO–AuNP

Inspirado no NanoCommons KnowledgeBase / eNanoMapper / ACEnano (substância → protocolo → medida com incerteza).
Cadeia: **lote de reagente → lote de GO → preparo da amostra → XPS/Raman/AFM → descritores com incerteza →
síntese de AuNP → UV-Vis/TEM → desfecho**. A fonte única é `tools/data_sources/lab_data_model.py`.

| Arquivo | Conteúdo |
|---|---|
| `templates/*.csv` | cabeçalhos das 9 tabelas: `protocols`, `reagent_lots`, `go_batches`, `go_samples`, `go_characterization`, `go_descriptors`, `aunp_syntheses`, `aunp_characterization`, `outcomes` |
| `data_dictionary.csv` | 137 colunas: tabela, tipo, obrigatória, unidade, valores permitidos, descrição |
| `go_aunp.schema.json` | JSON Schema (draft 2020-12) do registro completo, para exportar a MDF/Zenodo |

Fluxo: copie os modelos para `datasets/lab/`, preencha (uma linha por grandeza medida, sempre com `unit`,
`uncertainty` e `uncertainty_type`) e valide com
`python tools/data_sources/lab_data_model.py validate datasets/lab`. O validador confere chaves únicas e
estrangeiras (inclusive `entity_id` contra `datasets/reagents/reagent_dictionary.csv`), números, vocabulários
e incertezas negativas. `aunp_syntheses.design_id`/`fidelity` ligam cada experimento ao otimizador (qNEHVI/MISO),
e `go_descriptors` guarda média ± sd por lote e o desvio entre lotes, que o GO Navigator e a transferência entre lotes usam.
