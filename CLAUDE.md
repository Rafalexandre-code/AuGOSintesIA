# AuGOSintesIA — guia rápido para agentes

Repositório de apoio à IC FAPESP (UNESP-IQ Araraquara) "Plataforma de aprendizado ativo para o design de
nanocompósitos GO–AuNP sob variabilidade multi-fonte de matéria-prima". Não é um software único: é uma
coleção de documentos, datasets e repositórios de terceiros.

**Análise completa (o que cada pasta faz, como usar, pegadinhas): [docs/ANALISE_REPOSITORIO.md](docs/ANALISE_REPOSITORIO.md).**
**Fontes de dados (auditoria + integração): [docs/FONTES_DE_DADOS.md](docs/FONTES_DE_DADOS.md); registro `tools/data_sources/sources.tsv`.**
Cada pasta de primeiro nível tem um `README.md` com o seu índice.

## Mapa
- `docs/` — `ANALISE_REPOSITORIO.md`; `DMP.md` (plano de gestão de dados); `SIMULACOES.md` (resumos SIMULADOS
  registrados, gerados por `campaign_sim.py report`); `projeto/Projeto_FAPESP_Iniciação_Rafael_Lopes.docx` (objetivos:
  GO Navigator, AuNP Designer com GP Matérn-5/2+ARD e qNEHVI, MISO, transfer learning entre lotes, causalidade, benchmark).
- `config/` — `preregistration.yaml` (plano a priori: alvo E*, faixa, normalização, sₘ/ε pelo piloto, restrições,
  orçamento 8/12/24/16, braços pareados, desfecho primário por lote (LBO + confirmação), TEM, fatorial, MISO, valor da informação;
  RASCUNHO até `prereg.py freeze`), `qc_criteria.yaml` e `sustainability_extensions.yaml` (CAPEX/OPEX, ComplexGAPI).
- `literature/` — 65 artigos citados em texto: `artigos_combinados.md`, `chunks.jsonl` (5 227 trechos p/ RAG),
  `relatorio.{csv,json}` (CSV com `;`).
- `datasets/` — `aunc-fluorescence/` (CSV `;`, latin-1), `nanocrystal-synthesis-db/` (Gu et al., LFS),
  `aunp-text-mined/` (LFS), `cofs-methane/`, `pressure-vessel/`, `pubchem/`, `xrd-ceo2-calibration/`
  (.ge3: 5 frames 2048×2048 uint16, offset 8192). Gerados por `tools/data_sources/` (regeráveis): `reagents/`
  (dicionário PubChem; editar só `aliases.tsv`), `literature-seed/` (Cruse+NSP+AuNCs; `go_aunp_subset.csv`),
  `data-model/` (13 tabelas + validador, inclusive `resources` e `qc_results`), `optical-constants/` (n, k de Au/Ag para Mie). `lab/` = dados medidos (a preencher; validar com `lab_data_model.py validate`; SOPs em `lab/protocols/`).
- `code/` — código do projeto (ambiente `core`; testes `python -m pytest code/tests`, 104): `campaign/` (`prereg.py` lê/sela
  o pré-registro; `plan.py` gera o plano 8/12/24/16 — braços pareados por rodada, confirmação em pares com previsões
  congeladas, TEM, controles, fichas; `ingest.py` = brutos → `outcomes.csv` (J, tamanho da TEM ou do UV-Vis/Mie calibrado
  na TEM; `check`); `analysis.py` = análise pré-registrada; `factorial.py` = fatorial 2×2), `spectral/`
  (UV-Vis, perda J, Mie + ajuste de tamanho, Neural Process espectral; `design --rank-with-gp`), `characterization/` (Raman + mapa espacial, XPS + survey S/C, FTIR, XRD,
  DLS, TEM + associação AuNP–GO, AFM, zeta, ICP, OCP, SERS, SAXS), `qc/` (critérios + cartas de controle; reprovadas saem
  do treino), `go_navigator/` (descritores; Batch Fingerprint + Active Subspace), `aunp_designer/` (`designer.py`: braços
  recipe/batch/go/go+impurities/hierarchical, `--arm`, qNEHVI padrão e qLogNEHVI pela regra `noise-check`, restrições,
  LBO, novelty, SHAP + interações, `demo`; `autopilot.py`), `transfer_learning/` (GP hierárquico, correção de hardware),
  `miso/` (MGP/ICM/PCM + KG exato por custo; `propose` com dados reais), `decision/` (EVPI/EVSI), `kinetics/`
  (Finke–Watzky + identificabilidade), `sdl/loop.py` (laço fechado: ingestão → QC → proposta → fila de trabalhos
  neutra; executores manual/simulado), `benchmarking/` (laboratório SIMULADO, `calibrate.py` = simulador calibrado
  pelo piloto, braços GP+EI/RF/DNN/EGBO/TPE/novelty/
  autopilot, transferência, cenário prospectivo com placebo e nulo, nº de lotes, fatorial, poder, HV/IGD), `causal/` (DAG, DoWhy, E-value,
  IPW por entropia, mediação, causal-learn), `sustainability/` (E-factor, EcoScale, CPU, CAPEX/OPEX, ComplexGAPI),
  `webapp/` (site só com dados experimentais: `expdata.py` → `analyses.py` → `build_site.py` gera `site/`; `app.js` roda o GP e
  o Mie/J no navegador; `guide.js` = textos da aba Guia por aba, indicador, figura e conceito, executado no node por teste), `atomistic/` (ambiente
  `jarvis`: design inverso GO–Au com JARVIS-DFT/FF/ML/Tools, CHIPS-FF, InterMat; `test_atomistic.py`).
- `site/` — painel interativo (abrir `site/index.html`; gerado, não editar: `python code/webapp/build_site.py [--reuse]`;
  `--artifact <arquivo>` = página única). Só dados experimentais; GO-específico aparece como "aguarda o laboratório".
- `projects/<módulo>/` — 13 subprojetos base (modificados aqui: caminhos portáveis, bugs corrigidos):
  - `atomistic/GO-MACE-23` (gerador de GO em `code/`, potencial `models/fitting/potential/iter-12-final-model/go-mace-23.pt`,
    C/H/O, sem Au), `atomistic/AmberGO` (GO 5–68 % para AMBER/GAFF; depende do HierGO)
  - `literature-llm/text-mined-aunp-synthesis` (ler o `.json.zip`),
    `literature-llm/Synthesis-Properties-Database-for-Nanomaterials` (LoRA Qwen3-14B via LLaMA-Factory; GPU)
  - `bayesian-optimization/{SDL,Bgolearn,RAMBOAU,BOCoDe}` (BOCoDe: **maximização**, restrição viável `g<=0`)
  - `multi-fidelity/chem-MFBO`, `inverse-design/MatDesINNe`, `materials-ml/M2Hub`
  - `self-driving-lab/qubot/{hardware,data,scripts,README.pdf}` — `data/` e `scripts/` devem ficar lado a lado
- `external/<módulo>/` — 89 repositórios de referência (`data-access/` = clientes OpenAlex/Crossref/Unpaywall/PubChem/
  OPTIMADE/MP/MDF/eNanoMapper; `jarvis/` = 15 do ecossistema JARVIS, índice e contornos em `external/jarvis/README.md`),
  cópias sem `.git` (manifesto `external/README.md`; commits `tools/external_repos.lock.tsv`; atualizar com
  `tools/fetch_external.sh --latest`). Não editar à mão: defeitos upstream são contornados em `code/`/`environments/`.
- `environments/` + `tools/setup_env.sh <nome>` — um ambiente por subprojeto (`--list`); `core` = projeto GO–AuNP;
  `<nome>.override.txt` substitui pinos do subprojeto (chem-mfbo: torch 2.8 em vez de 2.2.1); Windows:
  `tools\setup_env.ps1 <nome>` usa `<nome>.windows.lock.txt` (mesmas versões; regenerar com `tools/lock_windows.sh`;
  jarvis/atomgpt/qwen-llm só no WSL2);
  `data-sources` = clientes de API; `jarvis` = JARVIS instalado de `external/jarvis/` (+ MACE-MP, CHGNet, SevenNet,
  LAMMPS); `atomgpt` = AtomGPT (inverso exige GPU; testado em CPU).
- `deposit/GO-AuNP-Autonomous-Design/` — esqueleto do depósito Zenodo/MDF; montar com `tools/data_sources/build_deposit.py`
  e enviar (localmente, `ZENODO_TOKEN`) com `tools/data_sources/zenodo_upload.py` (ensaio por padrão; `--publish` gera o DOI).

## Verificar antes de commitar
- `python tools/check_repo.py --regen` (estrutura + dados gerados reproduzíveis), `ruff check code tools` (config em
  `ruff.toml`) e `tools/smoke_test.sh <ambiente>` (roda cada subprojeto numa cópia temporária; `--install` cria o
  ambiente). CI: `.github/workflows/testes.yml` (ruff, `check_repo --no-lfs`, pytest no `core` com torch de CPU; sem
  LFS nem `--regen`). Busca nos artigos: `tools/search_literature.py`.
- Dados medidos: nunca digitar J/LSPR/tamanho — `code/campaign/ingest.py derive --write` deriva dos brutos e `check`
  confere (SOP-DATA-01).

## Cuidados
- 13 arquivos usam **Git LFS** (caminhos exatos em `.gitattributes`; ao mover um deles, atualize o
  `.gitattributes` no mesmo commit): `git lfs install && git lfs pull`.
- Dependências conflitantes (torch 1.7 … 2.14, Python 3.8 … 3.12): use `tools/setup_env.sh <nome>` (`.venvs/`, ignorado).
- Caminhos devem ser relativos ao script ou vir de variável de ambiente (`QUBOT_DATA_DIR`, `QWEN_*`,
  `RAMBOAU_EXP_DATA`, `GO_AMORPHOUS_DB`, `GO_ALLOW_LARGE`, `SDL_BELIEF_MODEL`, `MACE_RUN_TRAIN`, `GAUGE_PORT`…).
  Os `.in`/`.lock.txt` de `environments/` referenciam `../projects/...`: atualize-os se mover um subprojeto.
- `code/benchmarking/{simulator,sim_lab,campaign_sim}.py`, `code/miso/miso.py` e `designer.py demo` geram dados SIMULADOS
  (marcados "SIMULADO"; só em `outputs/`). O único resumo versionado é `docs/SIMULACOES.md` (`campaign_sim.py report`).
- `config/preregistration.yaml` congelado (`prereg.py freeze`) não se edita: mudanças entram em `amendments`.
- Dados sintéticos/substitutos, NÃO medidos: `projects/atomistic/GO-MACE-23/structures/aG_p6_surrogate.xyz`
  (de `code/make_amorphous_db.py`) e o gerador `projects/bayesian-optimization/RAMBOAU/problems/data/make_synthetic_experiment.py`.
- Não versionar `.git` aninhado nem ponteiros LFS de terceiros em `external/` (use o script).
- Rodar código gera `__pycache__/`, `result/`, `Bgolearn/`, `outputs/` etc.; não commitar esses artefatos
  (`/outputs/` está no `.gitignore`; os scripts de rede de `tools/data_sources/` gravam lá).
- Rede do contêiner de nuvem: só GitHub e PyPI. Zenodo/HF/figshare/OpenAlex/PubChem etc. ficam bloqueados; os scripts
  de `tools/data_sources/` que usam rede devem rodar localmente. JARVIS sem figshare: `code/atomistic/jarvis_data.py`
  monta uma reconstrução offline do dft_3d (marcada `reconstrucao_offline`, em `outputs/jarvis_offline_cache`); os
  modelos pré-treinados (ALIGNN/ALIGNN-FF, SlaKoNet, AtomGPT) vêm por `jarvis_data.py download [--project]` numa máquina
  com rede. `<repo>/.cache/` (ignorado) é o cache do projeto: se existir, os scripts de `code/atomistic/` o usam.
- `qubot/data/*/summary.csv` são regravados pelas análises; teste com `QUBOT_DATA_DIR=<cópia>`.
