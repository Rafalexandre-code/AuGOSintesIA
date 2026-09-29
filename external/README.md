# external — repositórios de referência para a proposta FAPESP GO–AuNP

Cópias *shallow* (sem `.git`) de 75 repositórios do GitHub, clonadas em 2026-09-29 (17 adicionados na revisão de
atualidade da proposta — marcados 🆕).
Commit exato de cada um: [`tools/external_repos.lock.tsv`](../tools/external_repos.lock.tsv).

```bash
tools/fetch_external.sh --list            # lista o que está aqui
tools/fetch_external.sh --latest          # atualiza TODOS para a versão mais recente (e o lock)
tools/fetch_external.sh --latest botorch  # atualiza só um
tools/fetch_external.sh --full olympus    # reclona sem poda (ver "O que foi podado")
```

Cada repositório mantém sua própria licença. **Nove não têm licença explícita**
(marcados com ⚠) — uso acadêmico/privado apenas; não torne este repositório público sem
checar com os autores.

## Mapa por módulo do projeto

### `bayesian-optimization/` — AuNP Designer (§4.5) e benchmark (§4.15)
| Pasta | Origem | Licença | Para quê |
|---|---|---|---|
| `botorch` | pytorch/botorch | MIT | GP Matérn 5/2+ARD, qNEHVI/qLogNEHVI, `MultiTaskGP`, MF-KG, custo — base do AuNP Designer |
| `gpytorch` | cornellius-gp/gpytorch | MIT | kernels/likelihoods; GPs hierárquicos |
| `Ax` | facebook/Ax | MIT | gerenciamento de experimentos sobre BoTorch (rodadas, lotes, histórico) |
| `baybe` | emdgroup/baybe | Apache-2.0 | BO para experimentos com **transfer learning** (`TaskParameter` = lote de GO) |
| `bofire` | experimental-design/bofire | BSD-3 | BO + DoE para experimentos reais, restrições, multiobjetivo |
| `honegumi` | sgbaird/honegumi | MIT | gera scripts Ax/BoTorch prontos (npj Comput. Mater. 2026) |
| `obsidian` | MSDLLCpapers/obsidian | GPL-3.0 | BO para processos químicos (MSD), com app |
| `olympus` | aspuru-guzik-group/olympus | MIT | benchmark de planejadores (citado no projeto) — podado |
| `atlas` | aspuru-guzik-group/atlas | MIT | BO com multi-fidelidade, restrições desconhecidas, robustez |
| `summit` | sustainable-processes/summit | MIT | otimização de reações; TSEMO; **MTBO** (transfer learning) |
| `optuna` | optuna/optuna | MIT | um dos algoritmos do benchmark (§4.15) |
| `Aqeeli_NoveltyAware_EGBO` | shorthouse-lab | MIT | **novelty-aware EGBO** (Aqeeli 2026) — comparação metodológica |
| `PV-Lab-Benchmarking` | PV-Lab/Benchmarking | MIT | protocolo de Liang et al. 2021 (citado) + datasets AgNP etc. |
| `awesome-bayesian-optimization` | materials-data-facility | MIT | índice de ferramentas/papers de BO em materiais |
| `pymoo` 🆕 | anyoptimization/pymoo | Apache-2.0 | NSGA-II/III e indicadores HV, IGD, spread para o benchmark (§4.15) |
| `LLAMBO` 🆕 | tennisonliu/LLAMBO | MIT | BO aumentada por LLM (ICLR 2024): aquecimento *zero-shot* e amostragem de candidatos — comparação exploratória |

### `multi-fidelity/` — MISO (§4.8)
| Pasta | Origem | Licença | Para quê |
|---|---|---|---|
| `misoKG-NIPS2017` | misokg/NIPS2017 | Apache-2.0 | misoKG original (Poloczek, Wang, Frazier 2017) |
| `ClancyLab-PAL` ⚠ | ClancyLab/PAL | — | pipeline do grupo Clancy (Herbol et al. 2020: MGP/ICM/PCM) |
| `ClancyLab-PAL2` | ClancyLab/PAL2 | MIT | PAL 2.0: BO com física embutida (2024) |
| `kernelCruncher-MFBO` ⚠ | kernelCruncher/MFBO | — | MFBO aplicado a datasets de materiais |
| `emukit` 🆕 | EmuKit/emukit | Apache-2.0 | multi-fidelidade (AR1/NARGP), planejamento experimental e sensibilidade — alternativa a MF-KG para o MISO |

### `aunp-spectral/` — perda espectral J (§4.4), dados reais de AuNP
| Pasta | Origem | Licença | Para quê |
|---|---|---|---|
| `HEAD` | pozzo-research-group/HEAD | MIT | Vaddi et al. 2022/2025: casamento de **forma espectral**, modelos diferenciáveis (branch BO = default) |
| `SPACESHIP` ⚠ | KIST-CSRC/SPACESHIP | "academic use only" | Autopilot, espaço sintetizável dependente do hardware (Kim 2026) |
| `BespokeSynthesisPlatform` ⚠ | KIST-CSRC | — | Yoo et al. 2024: código + **Result/** com receitas e espectros UV-Vis brutos de AuNP |
| `NanoChef` ⚠ | KIST-CSRC | — | otimização simultânea de ordem e condições de síntese |
| `BatchSynthesisModule` ⚠ | KIST-CSRC | — | módulo de síntese em lote (inclui SDK do robô Doosan) |
| `UV-VisModule` ⚠ | KIST-CSRC | — | módulo UV-Vis automatizado + `Dataset/` |
| `miepython` | scottprahl/miepython | MIT | teoria de Mie → **espectros sintéticos** de AuNP por diâmetro |
| `PyMieScatt` | bsumlin/PyMieScatt | MIT | Mie (alternativa, distribuições de tamanho) |
| `activephasemap` 🆕 | pozzo-research-group/activephasemap | GPL-2.0 | Vaddi et al. 2025 (npj Comput. Mater.): mapeamento de fases de síntese de AuNP com modelos **diferenciáveis de forma espectral** (§4.6) |

### `inverse-design/` — modelos diferenciáveis/generativos (§4.6)
| `neural-processes` | google-deepmind | Apache-2.0 | Neural Processes de referência (Garnelo 2018) |
|---|---|---|---|
| `TNP-pytorch` | tung-nd | MIT | Transformer Neural Processes (PyTorch) |
| `neuralprocesses` 🆕 | wesselb/neuralprocesses | MIT | biblioteca moderna de Neural Processes (CNP, GNP, ConvNP; PyTorch/JAX) para §4.6/§4.7 |

### `causal-interpretability/` — causalidade (§4.9), SHAP (§4.13), identificabilidade (§4.10)
| `dowhy` | py-why | MIT | DAGs, estimandos, propensity score, refutação/sensibilidade |
|---|---|---|---|
| `EconML` | py-why | MIT | efeitos heterogêneos (DML, causal forests) |
| `shap` | shap/shap | MIT | interpretabilidade — podado (sem `docs/`, `data/`, notebooks sem saídas) |
| `pyPESTO` | ICB-DCM | BSD-3 | **perfil de verossimilhança** (Raue 2009) p/ modelo cinético |
| `causal-learn` 🆕 | py-why/causal-learn | MIT | **descoberta causal** (PC, FCI, GES, LiNGAM) — usado em `code/causal` (podado: sem testes/docs) |
| `MAPIE` 🆕 | scikit-learn-contrib/MAPIE | BSD-3 | **predição conformal**: intervalos com cobertura garantida (§4.18) |
| `ATHENA` 🆕 | mathLab/ATHENA | MIT | **Active Subspaces** e redução de parâmetros — Batch Fingerprint do GO Navigator (§4.2) |

### `atomistic/` — GO Navigator (§4.2)
| `mace` | ACEsuit/mace | MIT | necessário para rodar `go-mace-23.pt`; traz MACE-MP-0 (com **Au**) |
|---|---|---|---|
| `mace-foundations` | ACEsuit | MIT | catálogo/links dos modelos fundacionais MACE |
| `fairchem` | facebookresearch | MIT | UMA (Meta) — potencial universal para GO+Au+água |
| `HierGO` | IFM-molecular-simulation-group | GPL-3.0 | gerador de tiles de GO (pré-requisito do AmberGO) |

### `characterization/` — dados de caracterização
| `pyFAI` + `fabio` | silx-kit | MIT | ler `.ge3` (`datasets/xrd-ceo2-calibration/`) e integrar SAXS/WAXS |
|---|---|---|---|
| `sasmodels` | SasView | BSD-3 | ajuste de curvas SAXS (tamanho/polidispersidade) |
| `lmfit-py` | lmfit | BSD-3 | ajuste de picos (XPS C 1s, bandas Raman, plasmon) |
| `RamanSPy` | barahona-research-group | BSD-3 | pré-processamento/análise de Raman |
| `pybaselines` 🆕 | derb12/pybaselines | BSD-3 | linhas de base (arPLS, polinômios…) para Raman/XPS/UV-Vis — usado em `code/characterization` |

### `literature-llm/` — curadoria (§4.1)
| `LLaMA-Factory` | hiyouga | Apache-2.0 | treino/inferência do LoRA Qwen3 (`Synthesis-Properties…`) |
|---|---|---|---|
| `lematerial-llm-synthesis` | LeMaterial | Apache-2.0 | LeMat-Synth: extração multimodal de sínteses (2025) |
| `MatEntityRecognition` | CederGroupHub | MIT (setup.py) | submódulo do text-mined AuNP — ⚠ modelos (2×780 MB) não incluídos |
| `MaterialParser` | CederGroupHub | MIT | submódulo do text-mined AuNP |
| `MaterialAmountExtractor` ⚠ | CederGroupHub | — | submódulo — ⚠ Stanford Parser (833 MB) não incluído |
| `marker` 🆕 | datalab-to/marker | Apache-2.0 (código; pesos dos modelos têm licença própria) | PDF → Markdown/JSON com layout, tabelas e equações (etapa PDF→texto do pipeline de literatura) |
| `paper-qa` 🆕 | Future-House/paper-qa | Apache-2.0 | perguntas e respostas com citação sobre PDFs (RAG de artigos científicos) |
| `chemdataextractor2` 🆕 | CambridgeMolecularEngineering | MIT | extração de entidades/propriedades químicas de texto (alternativa sem LLM) |

### `self-driving-lab/` — extensão SDL (§4.16)
| `Robochem_Flex` | Noel-Research-Group | Apache-2.0 | SDL de ~US$ 5 mil: software, firmware, CAD (Pilon 2026) |
|---|---|---|---|
| `Octopus` ⚠ | KIST-CSRC | — | orquestração de tarefas de laboratório autônomo |
| `pylabrobot` 🆕 | PyLabRobot/pylabrobot | MIT | SDK **agnóstico de hardware** para robôs de pipetagem (Hamilton, Tecan, Opentrons…) e acessórios |
| `MADSci` 🆕 | AD-SDL/MADSci | MIT (Argonne) | toolkit modular de laboratório autônomo (nós, workflows, dados, recursos) |
| `alabos` 🆕 | CederGroupHub/alabos | MIT | gerenciador de workflows do A-Lab (Szymanski et al. 2023) |
| `ivoryos` 🆕 | ivoryos-ai/ivoryos | MIT | gera interface web e orquestra SDLs em Python (Nat. Commun. 2025) |

### `data-access/` — clientes das fontes de dados (curadoria §4.1, camada computacional, depósito)
Usados por `tools/data_sources/` (ambiente `data-sources`); o inventário das fontes está em
[`docs/FONTES_DE_DADOS.md`](../docs/FONTES_DE_DADOS.md).
| Pasta | Origem | Licença | Para quê |
|---|---|---|---|
| `pyalex` | J535D165/pyalex | MIT | OpenAlex (busca bibliográfica, filtros, paginação por cursor) |
| `habanero` | sckott/habanero | MIT | Crossref (metadados por DOI, deduplicação) |
| `unpywall` | unpywall/unpywall | MIT | Unpaywall (localizar PDF de acesso aberto) |
| `PubChemPy` | mcs07/PubChemPy | MIT | PubChem (CID, SMILES, InChI, sinônimos) |
| `zenodo_get` | dvolgyes/zenodo_get | AGPL-3.0 | baixar registros inteiros do Zenodo |
| `foundry` | MLMI2-CSSI/foundry | MIT-like (U. Chicago) | Materials Data Facility / Foundry-ML (publicar e ler datasets prontos para ML) |
| `optimade-python-tools` | Materials-Consortia | MIT | cliente OPTIMADE: NOMAD, Materials Cloud, Materials Project, OQMD, AFLOW, JARVIS numa só consulta |
| `mp-api` | materialsproject/api | BSD-3 (LBNL) | Materials Project nativo (exige `MP_API_KEY`) |
| `jarvis-tools` | usnistgov/jarvis | NIST (termos de uso) | JARVIS-DFT/ML; baixa os conjuntos sob demanda — podado (sem `jarvis/tests`, `jarvis/examples`) |
| `pynanomapper` | ideaconsult/pynanomapper | MIT | eNanoMapper / NanoCommons (modelo substância→protocolo→medida) |
| `ro-crate-py` 🆕 | ResearchObject/ro-crate-py | Apache-2.0 | empacotamento FAIR (RO-Crate) de dados + código + proveniência para o depósito |

## O que foi podado (recuperável com `--full`)
| Caminho | Tamanho | Motivo |
|---|---|---|
| `olympus/case_studies`, `olympus/__dev_` | 937 MB + 44 MB | reproduções do paper; o pacote e datasets estão em `src/` |
| `shap/docs`, `shap/data` | 188 MB + 57 MB | apresentações/datasets de exemplo (baixados por `shap.datasets`) |
| `BespokeSynthesisPlatform/Result/1_Chemistry_discovery/AI_decision_process/{513,573,667}nm.gif` | 96–97 MB cada | animações; os dados numéricos permanecem |
| `mace/mace/calculators/foundations_models/mace-mpa-0-medium.model` | 76 MB | baixado automaticamente por `mace_mp(model="medium-mpa-0")` |
| `jarvis-tools/jarvis/tests`, `jarvis-tools/jarvis/examples` | 198 MB + 30 MB | arquivos de teste VASP/Wannier e exemplos; o pacote fica completo |
| testes/docs/tutoriais de `causal-learn`, `MAPIE`, `ATHENA`, `pylabrobot`, `alabos`, `paper-qa`, `ivoryos`; `marker/data` | ~400 MB | só documentação, notebooks e dados de teste; os pacotes ficam completos |

## Arquivos LFS não incluídos (grandes demais para versionar aqui)
- `literature-llm/MatEntityRecognition`: 8 arquivos (2 checkpoints de ~780 MB)
- `literature-llm/MaterialAmountExtractor`: 118 arquivos do Stanford Parser (833 MB)

A lista exata (caminho, tamanho, sha256) está em `LFS_OBJECTS_NOT_INCLUDED.txt` dentro de cada pasta.
Para obtê-los: `git clone https://github.com/CederGroupHub/<repo> && cd <repo> && git lfs pull`.

## Ferramentas avaliadas e não clonadas (usar pelo PyPI ou pelo link)
- `docling` (IBM, PDF → estrutura; 185 MB com testes): `pip install docling` — alternativa ao `marker`.
- `rosettasciio` (leitura de .dm3/.dm4/.emd/.ser de TEM): no ambiente `core`; usado por `code/characterization/tem.py`.
- `atomai` (pycroscopy, deep learning para microscopia; 147 MB): `pip install atomai`.
- Segmentação de nanopartículas por SAM: NP-SAM (GitLab, Larsen et al.) e
  github.com/brunoaugustoam/AnalysisOfNanoparticlesUsingSAM (Sci. Rep. 2025; sem licença, 111 MB).
- ScatterLab (github.com/AndySAnker/scatterlab-2026-tspdf-target-scattering, 224 MB): SDL de nanopartículas com
  BO sobre padrões de espalhamento-alvo (ACS Nano 2026) — referência para a extensão SAXS/WAXS (§4.4, §4.12).
- Rainbow (Xu et al., Nat. Commun. 2025): código não publicado no GitHub.

## Trabalhos citados sem código no GitHub
- Gao et al. 2025 (GPT + A*): Zenodo 10.5281/zenodo.15861068
- Montoya-Gonzalez et al. 2025 (cloud lab): KiltHub 10.1184/R1/30062662
- Instance Maps (Punz et al. 2025): ferramenta web + figshare
- Kim et al. 2026 JACS (SAXS/WAXS in situ), AFION (Wu 2025), Mekki-Berrada 2021: sem código público
  encontrado (os dados de AgNP do Mekki-Berrada estão em `PV-Lab-Benchmarking` e no BOCoDe)
