# SOP-REAG-01 — Recebimento e análise de lotes de reagentes (módulo de impurezas, §4.3) (v0.1, RASCUNHO)

1. Ao receber: criar `reagent_lots` (entity_id do dicionário `datasets/reagents`, fornecedor, nº de lote, pureza,
   CoA em `metadata/`), anotar `received_date`; ao abrir, `opened_date`.
2. Análises por lote (`reagent_analyses`), conforme acesso e custo (prioridade do pré-registro):
   - CTAB: **iodeto** (cromatografia iônica), solventes residuais (GC), metais (ICP-MS);
   - HAuCl₄, citrato, NaBH₄, ácido ascórbico: pureza (titulação/CoA), metais traço (Ag, Fe, Cu por ICP-MS), água (KF).
3. Cada análise com valor, incerteza, nº de réplicas, método e instrumento. Valores abaixo do LOD: registrar o LOD em
   `value` e `notes="<LOD"`.
4. Fatorial 2×2 (exploratório): lote "contaminado" de CTAB por adição controlada de KI (registrar a dose).
5. OCP (quando disponível): registrar como medida de processo em `aunp_characterization` (technique=other,
   quantity=OCP_mV) — diagnóstico, não prova causal.
