# AuGOSintesIA

Repositório de apoio ao projeto de Iniciação Científica (FAPESP/UNESP-IQ Araraquara) *"Desenvolvimento de uma
plataforma de aprendizado ativo para o design de nanocompósitos GO–AuNP sob variabilidade multi-fonte de
matéria-prima"*.

Reúne o projeto de pesquisa, o corpus dos artigos citados, datasets de síntese de nanopartículas e de
reagentes, 13 subprojetos de referência já adaptados (óxido de grafeno, otimização bayesiana, design inverso,
extração de sínteses com LLM, robô de laboratório) e 48 repositórios de ferramentas atuais.

📘 **Guia completo (o que é cada coisa, como usar, o que foi corrigido):** [docs/ANALISE_REPOSITORIO.md](docs/ANALISE_REPOSITORIO.md)

## Estrutura

| Pasta | Conteúdo | Índice |
|---|---|---|
| [`docs/`](docs) | análise do repositório; `projeto/` com o projeto FAPESP (.docx) | [ANALISE_REPOSITORIO.md](docs/ANALISE_REPOSITORIO.md) |
| [`literature/`](literature) | 65 artigos em texto (Markdown combinado, trechos para busca/RAG, relatório) | [README](literature/README.md) |
| [`datasets/`](datasets) | dados avulsos: nanoclusters de Au, base síntese→propriedade (Gu et al.), AuNP minerado, COFs, PubChem, calibração de XRD | [README](datasets/README.md) |
| [`projects/`](projects) | 13 subprojetos base por módulo: `atomistic`, `literature-llm`, `bayesian-optimization`, `multi-fidelity`, `inverse-design`, `materials-ml`, `self-driving-lab` | [README](projects/README.md) |
| [`external/`](external) | 48 repositórios de referência (BoTorch, Ax, BayBE, HEAD, SPACESHIP, misoKG, DoWhy, MACE, pyFAI…) nas mesmas categorias | [README](external/README.md) |
| [`environments/`](environments) | especificação e versões fixadas de um ambiente Python por subprojeto | [README](environments/README.md) |
| [`tools/`](tools) | `setup_env.sh` (cria ambientes), `fetch_external.sh` (atualiza `external/`) | — |

```
docs/  literature/  datasets/  projects/<módulo>/<subprojeto>  external/<módulo>/<repositório>  environments/  tools/
```

## Primeiros passos

```bash
git lfs install                                   # alguns datasets e estruturas usam Git LFS
git clone https://github.com/Rafalexandre-code/AuGOSintesIA && cd AuGOSintesIA
tools/setup_env.sh --list                         # um ambiente isolado por subprojeto
tools/setup_env.sh core && source .venvs/core/bin/activate   # ambiente principal do projeto GO–AuNP
```

Mapa do projeto → recursos (curadoria, GO Navigator, AuNP Designer, MISO, benchmark…): §2 e §8 do
[guia](docs/ANALISE_REPOSITORIO.md).
