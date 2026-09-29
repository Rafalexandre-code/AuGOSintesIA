# AuGOSintesIA — guia rápido para agentes

Repositório de apoio à IC FAPESP (UNESP-IQ Araraquara) "Plataforma de aprendizado ativo para o design de
nanocompósitos GO–AuNP sob variabilidade multi-fonte de matéria-prima". Não é um software único: é uma
coleção de datasets + repositórios de terceiros descompactados em `Data/`.

**Análise completa (o que cada pasta faz, como usar, pegadinhas): [docs/ANALISE_REPOSITORIO.md](docs/ANALISE_REPOSITORIO.md).**

## Mapa
- `Projeto_FAPESP_Iniciação_Rafael_Lopes.docx` — projeto (objetivos: GO Navigator, AuNP Designer com GP
  Matérn-5/2+ARD e qNEHVI, MISO, transfer learning entre lotes, causalidade, benchmark).
- `PubChem/` — fichas JSON dos reagentes (HAuCl₄, NaBH₄, ác. ascórbico, citrato, CTAB, PVP, GO…).
- `Data/GO-MACE-23-main` — gerador de estruturas de GO (`code/run*.py`, só precisa de `ase`) + potencial
  MACE final `models/fitting/potential/iter-12-final-model/go-mace-23.pt` (C/H/O, sem Au).
- `Data/AmberGO-main` — GO 5–68 % para AMBER/GAFF (zips + tutorial PDF; depende do HierGO).
- `Data/text-mined-aunp-synthesis_public-main` — 5 154 artigos de síntese de AuNP (ler o `.json.zip`).
- `Data/Synthesis-Properties-Database-for-Nanomaterials-main` — LoRA Qwen3-14B (LLaMA-Factory) para extrair
  síntese→propriedade; caminhos fixos `/root/autodl-tmp`.
- `Data/SDL-main` (BO didático), `Data/Bgolearn-main` (BO sobre candidatos, `pip install Bgolearn`),
  `Data/RAMBOAU-main` (MOBO avesso a risco, qNEHVI/MVaR), `Data/chem-MFBO-main` (BO multi-fidelidade),
  `Data/BOCoDe-main` (307 benchmarks + 31 algoritmos; tem dataset `AgNP` com perda espectral; convenção:
  **maximização**, restrição viável `g<=0`).
- `Data/MatDesINNe-main` (design inverso cINN/cVAE/MDN, MoS₂), `Data/M2Hub-master` (GNNs de cristais).
- `Data/qubot`, `Data/data`, `Data/scripts`, `Data/README.pdf` — robô Qubot (CAD/BOM), dados e scripts
  (eletrólitos/EIS, shampoo, repetibilidade); controle via `control-lab-ly`.
- `Data/repo/*.ge3` — frames GE 2048×2048 uint16 (offset 8192) de CeO₂ e dark.
- Soltos: `DATASET_AuNCs.csv` (`;`, latin-1), `dataset_v1.csv` (69 839 COFs), `pressure_vessel_DS.csv`,
  `Statistics%20of%20Product%20Names.xlsx`.

## Cuidados
- 13 arquivos são **ponteiros Git LFS** (ver `.gitattributes`): `Data/dataset*.json`,
  `Data/aunp-synthesis_dataset_2021-9-14.json`, `Data/repo/dark_after_000413.ge3` e 9 `iter-*-train.xyz`
  do GO-MACE. Use `git lfs pull` ou as fontes originais (HuggingFace/Zenodo).
- Cada subprojeto tem dependências conflitantes (torch 1.7 … ≥ 2.8, Python 3.6 … 3.12): um ambiente
  virtual por subprojeto. Não "consertar" código de terceiros sem necessidade; preferir wrappers novos.
- Rodar código de `Data/` gera `__pycache__/`; não commitar esses artefatos.
