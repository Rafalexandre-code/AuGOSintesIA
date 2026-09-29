# AuGOSintesIA

Repositório de apoio ao projeto de Iniciação Científica (FAPESP/UNESP) *"Desenvolvimento de uma plataforma de
aprendizado ativo para o design de nanocompósitos GO–AuNP sob variabilidade multi-fonte de matéria-prima"*.

Reúne o projeto de pesquisa, fichas PubChem dos reagentes, datasets de síntese de nanopartículas e
repositórios de referência (potenciais de ML para óxido de grafeno, otimização bayesiana, design inverso,
extração de sínteses com LLM, caracterização e automação de laboratório).

📘 **Guia detalhado de cada pasta, arquivo e como usar:** [docs/ANALISE_REPOSITORIO.md](docs/ANALISE_REPOSITORIO.md)

## Primeiros passos

```bash
git lfs install                                   # arquivos grandes (datasets, estruturas) usam Git LFS
git clone https://github.com/Rafalexandre-code/AuGOSintesIA && cd AuGOSintesIA
tools/setup_env.sh --list                         # um ambiente isolado por subprojeto
tools/setup_env.sh core && source .venvs/core/bin/activate   # ambiente principal do projeto
```

- `Data/` — datasets e 13 subprojetos originais (com caminhos e bugs corrigidos para rodar em qualquer SO)
- `Data/external/` — 48 repositórios de referência ([lista](Data/external/README.md));
  `tools/fetch_external.sh --latest` atualiza todos
- `environments/` — especificações e versões fixadas de cada ambiente ([detalhes](environments/README.md))
