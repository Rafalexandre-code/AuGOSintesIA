# AuGOSintesIA

Repositório de apoio ao projeto de Iniciação Científica (FAPESP/UNESP-IQ Araraquara) *"Desenvolvimento de uma
plataforma de aprendizado ativo para o design de nanocompósitos GO–AuNP sob variabilidade multi-fonte de
matéria-prima"*.

Reúne o projeto de pesquisa, o corpus dos artigos citados, datasets de síntese de nanopartículas e de
reagentes, 13 subprojetos de referência já adaptados (óxido de grafeno, otimização bayesiana, design inverso,
extração de sínteses com LLM, robô de laboratório), 89 repositórios de ferramentas atuais (inclusive o ecossistema
JARVIS completo do NIST, integrado ao design inverso atomístico GO–Au) e a camada de fontes de
dados (dicionário de reagentes PubChem, semente GO–AuNP da literatura, modelo de dados do laboratório, depósito Zenodo).

🌐 **Painel interativo da proposta com os dados experimentais (abre no navegador):** [`site/index.html`](site/README.md)
📘 **Guia completo (o que é cada coisa, como usar, o que foi corrigido):** [docs/ANALISE_REPOSITORIO.md](docs/ANALISE_REPOSITORIO.md)
🗂 **Fontes de dados (auditoria das 16 fontes da proposta + integração):** [docs/FONTES_DE_DADOS.md](docs/FONTES_DE_DADOS.md)

## Estrutura

| Pasta | Conteúdo | Índice |
|---|---|---|
| [`docs/`](docs) | análise do repositório, auditoria das fontes de dados, plano de gestão de dados, simulações registradas (SIMULADO); `projeto/` com o projeto FAPESP (.docx) | [ANALISE_REPOSITORIO.md](docs/ANALISE_REPOSITORIO.md) · [FONTES_DE_DADOS.md](docs/FONTES_DE_DADOS.md) · [DMP.md](docs/DMP.md) · [SIMULACOES.md](docs/SIMULACOES.md) |
| [`config/`](config) | **plano pré-registrado** (alvo, sₘ/ε, restrições, orçamento 8/12/24/16, controles, MISO, valor da informação) e critérios de QC | [preregistration.yaml](config/preregistration.yaml) |
| [`literature/`](literature) | 65 artigos em texto (Markdown combinado, trechos para busca/RAG, relatório) | [README](literature/README.md) |
| [`datasets/`](datasets) | dados avulsos: nanoclusters de Au, base síntese→propriedade (Gu et al.), AuNP minerado, COFs, PubChem, calibração de XRD; **reagentes normalizados**, **semente GO–AuNP**, **modelo de dados do laboratório** | [README](datasets/README.md) |
| [`code/`](code) | **código do projeto**: pré-registro e gerador do plano experimental, UV-Vis/perda J/Mie, Raman/XPS/FTIR/XRD/DLS/TEM, QC com cartas de controle, GO Navigator, AuNP Designer (braços, qNEHVI com regra para qLogNEHVI, restrições, GP hierárquico, LBO, novelty, SHAP), MISO (MGP/ICM/PCM + KG por custo), EVPI/EVSI, benchmark e poder, causalidade (DoWhy, IPW, mediação), sustentabilidade, **design inverso atomístico GO–Au com o JARVIS** (`atomistic/`), gerador do site (`webapp/`) — com testes | [README](code/README.md) |
| [`site/`](site) | **painel interativo** (abra `site/index.html`): a proposta executada com os dados experimentais disponíveis — literatura, Mie e perda J, AuNP Designer (GP no navegador), aprendizado ativo, SHAP, variabilidade, causalidade, difração; gráficos 2D e 3D. Gerado por `code/webapp/build_site.py` | [README](site/README.md) |
| [`projects/`](projects) | 13 subprojetos base por módulo: `atomistic`, `literature-llm`, `bayesian-optimization`, `multi-fidelity`, `inverse-design`, `materials-ml`, `self-driving-lab` | [README](projects/README.md) |
| [`external/`](external) | 89 repositórios de referência (BoTorch, Ax, BayBE, HEAD, SPACESHIP, misoKG, DoWhy, MACE, pyFAI…; `data-access/`: OpenAlex, Crossref, Unpaywall, PubChem, OPTIMADE, MP, MDF, eNanoMapper; [`jarvis/`](external/jarvis/README.md): JARVIS-Tools, ALIGNN/ALIGNN-FF, AtomGPT, CHIPS-FF, InterMat, Leaderboard, JARVIS-FF…) | [README](external/README.md) |
| [`environments/`](environments) | especificação e versões fixadas de um ambiente Python por subprojeto | [README](environments/README.md) |
| [`deposit/`](deposit/GO-AuNP-Autonomous-Design) | estrutura do depósito **GO-AuNP-Autonomous-Design** (Zenodo/MDF, DOI por versão) | [README](deposit/GO-AuNP-Autonomous-Design/README.md) |
| [`tools/`](tools) | `setup_env.sh` / `setup_env.ps1` (cria ambientes no Linux/macOS / Windows; `lock_windows.sh` gera os locks de Windows), `fetch_external.sh` (atualiza `external/`), `check_repo.py` e `smoke_test.sh` (verificação), `search_literature.py`, `data_sources/` (fontes, curadoria, Instance Maps, auditoria da extração, depósito) | [data_sources](tools/data_sources/README.md) |

```
docs/  config/  literature/  datasets/  code/  site/  projects/<módulo>/<subprojeto>  external/<módulo>/<repositório>  environments/  deposit/  tools/
```

## Primeiros passos

```bash
git lfs install                                   # alguns datasets e estruturas usam Git LFS
git clone https://github.com/Rafalexandre-code/AuGOSintesIA && cd AuGOSintesIA
tools/setup_env.sh --list                         # um ambiente isolado por subprojeto
tools/setup_env.sh core && source .venvs/core/bin/activate   # ambiente principal do projeto GO–AuNP
python code/webapp/build_site.py --reuse         # painel site/index.html (só dados experimentais)
python code/aunp_designer/designer.py demo       # laço GO Navigator → AuNP Designer (simulado)
python tools/search_literature.py "gold nucleation graphene oxide"   # busca nos 65 artigos
python tools/check_repo.py && tools/smoke_test.sh  # verificação estrutural + execução de cada subprojeto
```

No Windows (PowerShell): `git config --global core.longpaths true`, depois
`powershell -ExecutionPolicy Bypass -File tools\setup_env.ps1 core` e `.\.venvs\core\Scripts\Activate.ps1`
(detalhes e ambientes que exigem WSL2 em [environments/README.md](environments/README.md#windows-powershell)).

Mapa do projeto → recursos (curadoria, GO Navigator, AuNP Designer, MISO, benchmark…): §2 e §8 do
[guia](docs/ANALISE_REPOSITORIO.md).
