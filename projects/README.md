# projects — subprojetos base (código + dados), organizados por módulo

Os 13 repositórios de terceiros que formavam a base original do repositório (antes em `Data/`, com
sufixos `-main`/`-master`). Diferente de [`external/`](../external), estes **foram modificados aqui**
(caminhos portáveis, bugs corrigidos, dados restaurados — ver `docs/ANALISE_REPOSITORIO.md` §7) e não são
sobrescritos pelo `tools/fetch_external.sh`. Cada um tem o seu ambiente: `tools/setup_env.sh <nome>`.

| Módulo | Subprojeto | O que é | Ambiente |
|---|---|---|---|
| `atomistic/` | [`GO-MACE-23`](atomistic/GO-MACE-23) | gerador de estruturas de óxido de grafeno + potencial MACE (DFT) + banco amorfo substituto | `go-mace` |
| | [`AmberGO`](atomistic/AmberGO) | modelos de GO 5–68 % para AMBER/GAFF + tutorial | `ambergo` (conda) |
| `literature-llm/` | [`text-mined-aunp-synthesis`](literature-llm/text-mined-aunp-synthesis) | 5 154 artigos de síntese de AuNP minerados + notebook de análise | `text-mined` |
| | [`Synthesis-Properties-Database-for-Nanomaterials`](literature-llm/Synthesis-Properties-Database-for-Nanomaterials) | LoRA Qwen3-14B que extrai síntese→propriedade; design inverso com LLM | `qwen-llm` (GPU) |
| `bayesian-optimization/` | [`SDL`](bayesian-optimization/SDL) | laço de BO didático (GP / ensemble de MLP + UCB) com ruído | `sdl` |
| | [`Bgolearn`](bayesian-optimization/Bgolearn) | BO sobre candidatos (EI, EQI, KG, PES…) + interface web local | `bgolearn` |
| | [`RAMBOAU`](bayesian-optimization/RAMBOAU) | BO multiobjetivo avesso a risco (qNEHVI, MVaR) para síntese de nanomateriais | `ramboau` |
| | [`BOCoDe`](bayesian-optimization/BOCoDe) | 307 problemas de benchmark (inclui AgNP com perda espectral) + 31 algoritmos | `bocode` |
| `multi-fidelity/` | [`chem-MFBO`](multi-fidelity/chem-MFBO) | BO multi-fidelidade com custo (MF-EI, MF-KG, MES) — base do MISO | `chem-mfbo` |
| `inverse-design/` | [`MatDesINNe`](inverse-design/MatDesINNe) | design inverso com redes invertíveis (INN/cINN/cVAE/MDN), MoS₂ | `matdesinne` |
| `materials-ml/` | [`M2Hub`](materials-ml/M2Hub) | GNNs de propriedades de cristais + métricas para modelos generativos | `m2hub` (conda) |
| `self-driving-lab/` | [`qubot`](self-driving-lab/qubot) | robô modular Qubot: `hardware/` (CAD, STL, BOM, manual), `data/` e `scripts/` (eletrólitos/EIS, shampoo, testes de repetibilidade), `README.pdf` | `qubot-scripts` |

As mesmas categorias são usadas em [`external/`](../external), onde ficam os repositórios de referência
complementares (BoTorch, Ax, BayBE, HEAD, SPACESHIP, misoKG, DoWhy, MACE, pyFAI…).
