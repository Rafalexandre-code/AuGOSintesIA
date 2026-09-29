# tools/data_sources — fontes de dados, curadoria e depósito

Inventário e auditoria das fontes: [`docs/FONTES_DE_DADOS.md`](../../docs/FONTES_DE_DADOS.md).
Scripts offline só usam a biblioteca padrão; os clientes opcionais ficam no ambiente `data-sources`
(`tools/setup_env.sh data-sources`).

| Script | Rede? | O que faz | Saída |
|---|---|---|---|
| `sources.tsv` | — | registro das 37 fontes (tipo, identificador, URL, pasta local, status, papel) | — |
| `reagents.py` | não (`--online` opcional) | dicionário de reagentes PubChem (`build`), normalização de nomes (`normalize`), cobertura em Cruse et al. (`cruse`) | `datasets/reagents/` |
| `build_literature_seed.py` | não | semente GO–AuNP: Cruse + NSP (produtos de Au) + AuNCs, reagentes normalizados | `datasets/literature-seed/` |
| `lab_data_model.py` | não | modelo de dados do laboratório (`templates`) e validação de CSVs preenchidos (`validate`) | `datasets/data-model/` |
| `fetch_records.py` | sim | confere (`check`) ou baixa (`download`) registros de Zenodo, Figshare e Hugging Face | `outputs/records/` |
| `literature_pipeline.py` | sim | OpenAlex → Crossref → Unpaywall → PDF/XML do PMC → fila para o extrator LLM | `outputs/literature_pipeline/` |
| `optimade_query.py` | sim | camada computacional: NOMAD, Materials Cloud, MP, OQMD, AFLOW, JARVIS via OPTIMADE | `outputs/optimade/` |
| `build_deposit.py` | não | monta a versão do depósito GO-AuNP-Autonomous-Design (+ MANIFEST sha256 + .zip) | `outputs/deposit/` |

`outputs/` está no `.gitignore`. As saídas em `datasets/` são regeneráveis e versionadas por serem
entregáveis (dicionário, semente, modelo de dados).
