# AuGOSintesIA — guia rápido para agentes

Repositório de apoio à IC FAPESP (UNESP-IQ Araraquara) "Plataforma de aprendizado ativo para o design de
nanocompósitos GO–AuNP sob variabilidade multi-fonte de matéria-prima". Não é um software único: é uma
coleção de documentos, datasets e repositórios de terceiros.

**Análise completa (o que cada pasta faz, como usar, pegadinhas): [docs/ANALISE_REPOSITORIO.md](docs/ANALISE_REPOSITORIO.md).**
**Fontes de dados (auditoria + integração): [docs/FONTES_DE_DADOS.md](docs/FONTES_DE_DADOS.md); registro `tools/data_sources/sources.tsv`.**
Cada pasta de primeiro nível tem um `README.md` com o seu índice.

## Mapa
- `docs/` — `ANALISE_REPOSITORIO.md`; `projeto/Projeto_FAPESP_Iniciação_Rafael_Lopes.docx` (objetivos: GO Navigator,
  AuNP Designer com GP Matérn-5/2+ARD e qNEHVI, MISO, transfer learning entre lotes, causalidade, benchmark).
- `literature/` — 65 artigos citados em texto: `artigos_combinados.md`, `chunks.jsonl` (5 227 trechos p/ RAG),
  `relatorio.{csv,json}` (CSV com `;`).
- `datasets/` — `aunc-fluorescence/` (CSV `;`, latin-1), `nanocrystal-synthesis-db/` (Gu et al., LFS),
  `aunp-text-mined/` (LFS), `cofs-methane/`, `pressure-vessel/`, `pubchem/`, `xrd-ceo2-calibration/`
  (.ge3: 5 frames 2048×2048 uint16, offset 8192). Gerados por `tools/data_sources/` (regeráveis): `reagents/`
  (dicionário PubChem; editar só `aliases.tsv`), `literature-seed/` (Cruse+NSP+AuNCs; `go_aunp_subset.csv`),
  `data-model/` (9 tabelas + validador). `lab/` = dados medidos (a preencher; validar com `lab_data_model.py validate`).
- `code/` — código do projeto: `go_navigator/batch_descriptors.py` (descritores por lote de GO) e
  `aunp_designer/designer.py` (GP Matérn-5/2+ARD + qLogNEHVI, contexto = lote; `demo` = laço simulado). Ambiente `core`.
- `projects/<módulo>/` — 13 subprojetos base (modificados aqui: caminhos portáveis, bugs corrigidos):
  - `atomistic/GO-MACE-23` (gerador de GO em `code/`, potencial `models/fitting/potential/iter-12-final-model/go-mace-23.pt`,
    C/H/O, sem Au), `atomistic/AmberGO` (GO 5–68 % para AMBER/GAFF; depende do HierGO)
  - `literature-llm/text-mined-aunp-synthesis` (ler o `.json.zip`),
    `literature-llm/Synthesis-Properties-Database-for-Nanomaterials` (LoRA Qwen3-14B via LLaMA-Factory; GPU)
  - `bayesian-optimization/{SDL,Bgolearn,RAMBOAU,BOCoDe}` (BOCoDe: **maximização**, restrição viável `g<=0`)
  - `multi-fidelity/chem-MFBO`, `inverse-design/MatDesINNe`, `materials-ml/M2Hub`
  - `self-driving-lab/qubot/{hardware,data,scripts,README.pdf}` — `data/` e `scripts/` devem ficar lado a lado
- `external/<módulo>/` — 58 repositórios de referência (`data-access/` = clientes OpenAlex/Crossref/Unpaywall/PubChem/
  OPTIMADE/MP/JARVIS/MDF/eNanoMapper), cópias sem `.git` (manifesto `external/README.md`;
  commits `tools/external_repos.lock.tsv`; atualizar com `tools/fetch_external.sh --latest`). Não editar à mão.
- `environments/` + `tools/setup_env.sh <nome>` — um ambiente por subprojeto (`--list`); `core` = projeto GO–AuNP;
  `<nome>.override.txt` substitui pinos do subprojeto (chem-mfbo: torch 2.8 em vez de 2.2.1);
  `data-sources` = clientes de API.
- `deposit/GO-AuNP-Autonomous-Design/` — esqueleto do depósito Zenodo/MDF; montar com `tools/data_sources/build_deposit.py`.

## Verificar antes de commitar
- `python tools/check_repo.py --regen` (estrutura + dados gerados reproduzíveis) e `tools/smoke_test.sh <ambiente>`
  (roda cada subprojeto numa cópia temporária; `--install` cria o ambiente). Busca nos artigos: `tools/search_literature.py`.

## Cuidados
- 13 arquivos usam **Git LFS** (caminhos exatos em `.gitattributes`; ao mover um deles, atualize o
  `.gitattributes` no mesmo commit): `git lfs install && git lfs pull`.
- Dependências conflitantes (torch 1.7 … 2.14, Python 3.8 … 3.12): use `tools/setup_env.sh <nome>` (`.venvs/`, ignorado).
- Caminhos devem ser relativos ao script ou vir de variável de ambiente (`QUBOT_DATA_DIR`, `QWEN_*`,
  `RAMBOAU_EXP_DATA`, `GO_AMORPHOUS_DB`, `GO_ALLOW_LARGE`, `SDL_BELIEF_MODEL`, `MACE_RUN_TRAIN`, `GAUGE_PORT`…).
  Os `.in`/`.lock.txt` de `environments/` referenciam `../projects/...`: atualize-os se mover um subprojeto.
- Dados sintéticos/substitutos, NÃO medidos: `projects/atomistic/GO-MACE-23/structures/aG_p6_surrogate.xyz`
  (de `code/make_amorphous_db.py`) e o gerador `projects/bayesian-optimization/RAMBOAU/problems/data/make_synthetic_experiment.py`.
- Não versionar `.git` aninhado nem ponteiros LFS de terceiros em `external/` (use o script).
- Rodar código gera `__pycache__/`, `result/`, `Bgolearn/`, `outputs/` etc.; não commitar esses artefatos
  (`/outputs/` está no `.gitignore`; os scripts de rede de `tools/data_sources/` gravam lá).
- Rede do contêiner de nuvem: só GitHub e PyPI. Zenodo/HF/figshare/OpenAlex/PubChem etc. ficam bloqueados; os scripts
  de `tools/data_sources/` que usam rede devem rodar localmente.
- `qubot/data/*/summary.csv` são regravados pelas análises; teste com `QUBOT_DATA_DIR=<cópia>`.
