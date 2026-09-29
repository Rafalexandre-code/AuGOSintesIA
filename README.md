# AuGOSintesIA

Repositório de apoio ao projeto de Iniciação Científica (FAPESP/UNESP-IQ Araraquara) *"Desenvolvimento de uma
plataforma de aprendizado ativo para o design de nanocompósitos GO–AuNP sob variabilidade multi-fonte de
matéria-prima"*.

Reúne o projeto de pesquisa, o corpus dos artigos citados, datasets de síntese de nanopartículas e de
reagentes, 13 subprojetos de referência já adaptados (óxido de grafeno, otimização bayesiana, design inverso,
extração de sínteses com LLM, robô de laboratório), 58 repositórios de ferramentas atuais e a camada de fontes de
dados (dicionário de reagentes PubChem, semente GO–AuNP da literatura, modelo de dados do laboratório, depósito Zenodo).

📘 **Guia completo (o que é cada coisa, como usar, o que foi corrigido):** [docs/ANALISE_REPOSITORIO.md](docs/ANALISE_REPOSITORIO.md)
🗂 **Fontes de dados (auditoria das 16 fontes da proposta + integração):** [docs/FONTES_DE_DADOS.md](docs/FONTES_DE_DADOS.md)

## Estrutura

| Pasta | Conteúdo | Índice |
|---|---|---|
| [`docs/`](docs) | análise do repositório, auditoria das fontes de dados; `projeto/` com o projeto FAPESP (.docx) | [ANALISE_REPOSITORIO.md](docs/ANALISE_REPOSITORIO.md) · [FONTES_DE_DADOS.md](docs/FONTES_DE_DADOS.md) |
| [`literature/`](literature) | 65 artigos em texto (Markdown combinado, trechos para busca/RAG, relatório) | [README](literature/README.md) |
| [`datasets/`](datasets) | dados avulsos: nanoclusters de Au, base síntese→propriedade (Gu et al.), AuNP minerado, COFs, PubChem, calibração de XRD; **reagentes normalizados**, **semente GO–AuNP**, **modelo de dados do laboratório** | [README](datasets/README.md) |
| [`code/`](code) | **código do projeto**: GO Navigator (descritores por lote de GO) e AuNP Designer (GP Matérn-5/2+ARD + qLogNEHVI, transferência entre lotes) | [README](code/README.md) |
| [`projects/`](projects) | 13 subprojetos base por módulo: `atomistic`, `literature-llm`, `bayesian-optimization`, `multi-fidelity`, `inverse-design`, `materials-ml`, `self-driving-lab` | [README](projects/README.md) |
| [`external/`](external) | 58 repositórios de referência (BoTorch, Ax, BayBE, HEAD, SPACESHIP, misoKG, DoWhy, MACE, pyFAI…; `data-access/`: OpenAlex, Crossref, Unpaywall, PubChem, OPTIMADE, MP, JARVIS, MDF, eNanoMapper) | [README](external/README.md) |
| [`environments/`](environments) | especificação e versões fixadas de um ambiente Python por subprojeto | [README](environments/README.md) |
| [`deposit/`](deposit/GO-AuNP-Autonomous-Design) | estrutura do depósito **GO-AuNP-Autonomous-Design** (Zenodo/MDF, DOI por versão) | [README](deposit/GO-AuNP-Autonomous-Design/README.md) |
| [`tools/`](tools) | `setup_env.sh` (cria ambientes), `fetch_external.sh` (atualiza `external/`), `check_repo.py` e `smoke_test.sh` (verificação), `search_literature.py`, `data_sources/` (fontes, curadoria, depósito) | [data_sources](tools/data_sources/README.md) |

```
docs/  literature/  datasets/  code/  projects/<módulo>/<subprojeto>  external/<módulo>/<repositório>  environments/  deposit/  tools/
```

## Primeiros passos

```bash
git lfs install                                   # alguns datasets e estruturas usam Git LFS
git clone https://github.com/Rafalexandre-code/AuGOSintesIA && cd AuGOSintesIA
tools/setup_env.sh --list                         # um ambiente isolado por subprojeto
tools/setup_env.sh core && source .venvs/core/bin/activate   # ambiente principal do projeto GO–AuNP
python code/aunp_designer/designer.py demo       # laço GO Navigator → AuNP Designer (simulado)
python tools/search_literature.py "gold nucleation graphene oxide"   # busca nos 65 artigos
python tools/check_repo.py && tools/smoke_test.sh  # verificação estrutural + execução de cada subprojeto
```

Mapa do projeto → recursos (curadoria, GO Navigator, AuNP Designer, MISO, benchmark…): §2 e §8 do
[guia](docs/ANALISE_REPOSITORIO.md).
