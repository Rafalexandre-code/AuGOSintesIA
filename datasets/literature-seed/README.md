# literature-seed — semente GO–AuNP da literatura

Tabela única de sínteses de ouro reunindo as três bases do repositório, com reagentes normalizados pelo
dicionário PubChem (`../reagents/`). Gerada por `python tools/data_sources/build_literature_seed.py`
(requer `git lfs pull`).

| Arquivo | Linhas | Conteúdo |
|---|---|---|
| `aunp_literature_seed.csv` | 15 928 | Cruse et al. 2022 (7 183 parágrafos de receita) + NSP 2026 (8 538 rotas com produto de Au, versão limpa) + AuNCs (207) — 5 131 DOIs |
| `go_aunp_subset.csv` | 312 | registros que citam óxido de grafeno / rGO (120 DOIs) — ponto de partida da curadoria GO–AuNP |
| `summary.json` | — | contagens e reagentes/morfologias mais frequentes |

`morphology_class` usa os regex de morfologia publicados por Cruse et al.
(`projects/literature-llm/text-mined-aunp-synthesis/rsc/aunp_morph_syns_regex.json`: rod, sphere, cube, octahedra,
hexagon, star, wire, triangle, plate, tube, prismatic, pyramid) mais `cluster`, `shell/cage` e `particle`.

Colunas: `seed_id, source, source_ref, doi, title, year, citations, product, morphology_raw, morphology_class,
size_text, size_nm, abs_peak_text, abs_peak_nm, em_peak_nm, exc_nm, seed_mediated, gold_precursor,
gold_precursor_form, gold_precursor_amount, reductants, capping_ligands, solvents, pH_adjusters, additives,
supports, other_reagents, unresolved_materials, temperature_C, time_text, pH, actions, mentions_graphene_oxide,
confidence`. Listas usam `|` e contêm `entity_id` do dicionário.

Cuidados: são dados **minerados por NLP/LLM** (não medidos aqui). `size_nm` e `abs_peak_nm` são medianas dos
valores em nm encontrados em texto livre, e os textos de Cruse vêm truncados na fonte. Em Cruse, o tamanho e a
morfologia são do artigo, não do parágrafo. Licenças: Cruse et al. (figshare) e NSP (MIT) — cite as duas.
