# Fontes de dados e repositórios do projeto — auditoria e integração

Auditoria feita em 2026-09-29 sobre as 16 fontes da proposta e as 16 infraestruturas de dados indicadas para a
curadoria. Cada repositório do GitHub foi **reclonado e comparado arquivo a arquivo** (`diff -r`, ignorando
quebras de linha) com a cópia local. Os registros do Zenodo, Figshare e Hugging Face foram conferidos pelas
descrições oficiais (contagens, conteúdo, DOI) e pelas contagens dos arquivos locais. O contêiner em que a
auditoria rodou só alcança GitHub e PyPI, por isso a comparação byte a byte com esses registros fica para
`tools/data_sources/fetch_records.py check --all`, a ser rodado numa máquina com acesso à internet.

Registro legível por máquina: [`tools/data_sources/sources.tsv`](../tools/data_sources/sources.tsv).
Ferramentas: [`tools/data_sources/`](../tools/data_sources/README.md).

## 1. As 16 fontes da proposta

| # | Fonte | Onde está | Verificação | Resultado |
|---|---|---|---|---|
| 1 | **NSP Database** — HF `Kai-gu/Synthesis-Properties-Database-for-Nanomaterials` + GitHub `ime1452/…` | dados: `datasets/nanocrystal-synthesis-db/` (LFS); código: `projects/literature-llm/Synthesis-Properties-Database-for-Nanomaterials/` | código = upstream `74665a8` (2026-06-26), só diferem os 5 arquivos com caminhos portáveis + `inverse_design/dataset_info.json`, que foi criado aqui. Dados: `dataset.json` 100 731 parágrafos (bruto); `dataset_low_conf_skip-clean.json` 47 023 parágrafos, **159 939 rotas** e 118 121 propriedades — os "~160 mil registros" do artigo (ACS Nano 2026, 10.1021/acsnano.6c03070). `README.md` = cartão do HF (MIT) | ✅ completo |
| 2 | **Text-mined AuNP** (Cruse et al., Sci. Data 2022; figshare 10.6084/m9.figshare.16614262) | `datasets/aunp-text-mined/` (LFS) e `projects/literature-llm/text-mined-aunp-synthesis/` | 5 154 artigos, 7 608 parágrafos de síntese, 12 519 de caracterização = descrição oficial. Código = upstream `1756f51`; os 3 submódulos (MatEntityRecognition, MaterialParser, MaterialAmountExtractor) estão em `external/literature-llm/`, e os modelos grandes não estão incluídos (ver `external/README.md`) | ✅ completo |
| 3 | **Thiolate-capped AuNC DB** (Zenodo 15739032) | `datasets/aunc-fluorescence/DATASET_AuNCs.{csv,xlsx}` | 207 entradas com tamanho, ligante, nº de átomos de Au, solvente, λexc/λem, T, pH, tempo e DOI = descrição do Zenodo. O CSV é latin-1 com `;`: os cabeçalhos "λ" e "°" aparecem como `?`/`§` | ✅ completo |
| 4 | **GO-MACE research data** (Zenodo 14066557) | `projects/atomistic/GO-MACE-23/` | = GitHub `zakmachachi/GO-MACE-23` `12c9764`: código de funcionalização (p1–p4), modelos MACE e checkpoints de cada iteração (13 `.xyz` de treino via LFS) e estruturas recozidas a 900/1200/1500 K. As diferenças locais são as correções documentadas (`MACE_RUN_TRAIN`, `GO_ALLOW_LARGE`, `make_amorphous_db.py`). O Zenodo pode ter arquivos que o GitHub não tem, como o banco amorfo `aG_p6.xyz` (aqui existe só o **substituto sintético** `aG_p6_surrogate.xyz`) — confira com `fetch_records.py check gomace-zenodo` | ✅ código/modelos · ⚠ conferir arquivos exclusivos do Zenodo |
| 5 | **Highly oxidized GO models, 15 estruturas** (Zenodo 10.5281/zenodo.17863270) | `projects/atomistic/AmberGO/` | = GitHub `yingling-group/AmberGO` `448622e`, sem nenhuma diferença; os 15 `.mol2` (0–68 %, 20×20 nm²) estão em `Data/All_final_models.zip` | ✅ completo |
| 6 | **2DMat.ChemDX.org** | — | plataforma web (Digital Discovery 2024, 10.1039/D3DD00243H) de dados experimentais de materiais 2D (RHEED, PL, Raman), sem dump público nem API aberta. Serve de referência para o modelo de dados e os espectros Raman de grafeno | 🌐 só na web (sem cópia possível) |
| 7 | **Benchmark AL + MOBO** (Zenodo 21389978) | `datasets/pressure-vessel/pressure_vessel_DS.csv`, `datasets/cofs-methane/dataset_v1.csv` | vaso de pressão: 52 272 configurações (3 objetivos: S11, S22, espessura) = Zenodo. COFs: **69 839** linhas (`Number` 0…69 838), enquanto o Zenodo descreve 69 840 COFs da base de Mercado et al. — confira se falta uma linha com `fetch_records.py check mobo-benchmark-zenodo --hash` | ✅ (⚠ diferença de 1 COF a confirmar) |
| 8 | **BOCoDe** (rosenyu304/BOCoDe) | `projects/bayesian-optimization/BOCoDe/` | = upstream `7d102e2` (2026-09-02). **Faltava** `control/mujoco/mujoco_policies/`, referenciada por `MujocoFuncs.py` (problemas Swimmer/Ant/HalfCheetah/Hopper/Humanoid/Walker2d); foi restaurada | ✅ corrigido |
| 9 | **chem-MFBO** (Atinary-technologies/chem-MFBO) | `projects/multi-fidelity/chem-MFBO/` | = upstream `1c24c08`, com o README corrigido aqui | ✅ completo |
| 10 | **nanoPharos** / EUON (ECHA) | — | base FAIR de nanomateriais (físico-química, toxicidade, descritores); acesso pela interface web. Serve de referência de metadados; o projeto usa o mesmo padrão eNanoMapper (ver #22) | 🌐 só na web |
| 11 | **Zenodo / Figshare** | `tools/data_sources/fetch_records.py` | confere e baixa qualquer registro (`check`, `download`); depósito: `deposit/GO-AuNP-Autonomous-Design/` | 🛠 ferramenta |
| 12 | **Qubots** (Zenodo 21530328) | `projects/self-driving-lab/qubot/` | é o Qubot-Publication v1.0.1 (dados, scripts de análise, hardware). `hardware/CAD` e `hardware/Manuals` são idênticos ao GitHub `mat-fox/qubot` `27fcb41` | ✅ completo |
| 13 | **AbolhasaniLab/SDL** | `projects/bayesian-optimization/SDL/` | = upstream `29f6593`; os 5 arquivos que diferem são as correções já documentadas (caminhos com `os.path.join`, `dimensionScreen`, `levy`, `SDL_BELIEF_MODEL`) | ✅ completo |
| 14 | **M²Hub** (o dono correto é `yuanqidu/M2Hub`, não `yuangidu`) | `projects/materials-ml/M2Hub/` | = upstream `c59b090`, com o README corrigido aqui | ✅ completo |
| 15 | **JARVIS** (jarvis.nist.gov) | `external/jarvis/` (15 repositórios: jarvis-tools, ALIGNN, AtomGPT, Leaderboard, CHIPS-FF, InterMat, JARVIS-FF…) | ecossistema completo no ambiente `jarvis`. Dados: `code/atomistic/jarvis_data.py` (figshare quando há rede; sem rede, **reconstrução offline** do dft_3d com 75 993 estruturas e 36 propriedades, mais vacancydb/surfacedb, marcada `reconstrucao_offline`), benchmarks do Leaderboard e dados LAMMPS do JARVIS-FF; também via OPTIMADE (`optimade_query.py --providers jarvis`). Uso no projeto: design inverso atomístico GO–Au (§16 da análise). O M²Hub já usa tarefas do JARVIS | ✅ integrado · offline parcial · original via `download` |
| 16 | **MatDesINNe** (jxzhangjhu/MatDesINNe) | `projects/inverse-design/MatDesINNe/` | = upstream `2c7ab5e`. Aqui há notebooks a mais, e as diferenças em `data_x/y.csv` são só de fim de linha | ✅ completo |

Achados paralelos: `projects/bayesian-optimization/Bgolearn` = upstream `9006fdf` menos a pasta `Example/`
(325 MB de estudos de ruído, que nunca esteve no repositório; para obtê-la, `git clone https://github.com/Bin-Cao/Bgolearn`),
e `RAMBOAU` = upstream `91cea5f` + dados/correções documentados.

## 2. Infraestruturas de dados — o que foi integrado

| # | Fonte | Papel no projeto | O que existe agora no repositório |
|---|---|---|---|
| 17 | **Cruse et al.** (figshare + CederGroupHub) | **semente** da curadoria | [`datasets/literature-seed/`](../datasets/literature-seed): 7 183 parágrafos de receita com reagentes normalizados, morfologia e tamanho, junto com o NSP (8 538 rotas de produtos de Au) e os 207 AuNCs → **15 928 registros, 5 131 DOIs**; `go_aunp_subset.csv` = 312 registros (120 DOIs) que citam GO/rGO |
| 18 | **NanoCommons KB / eNanoMapper / ACEnano** | **modelo de dados** | [`datasets/data-model/`](../datasets/data-model): 13 tabelas (lote de reagente + impurezas → lote de GO → preparo → XPS/Raman/AFM → descritores com incerteza → síntese de AuNP → UV-Vis/TEM → desfecho), `data_dictionary.csv`, JSON Schema e validador (`lab_data_model.py`); cliente `pynanomapper` em `external/data-access/` |
| 19 | **NIST Materials Data Repository** | depósito institucional / espelho | descrito em `deposit/GO-AuNP-Autonomous-Design/README.md` |
| 20 | **Materials Data Facility** | publicação do dataset final | `external/data-access/foundry` (Foundry-ML) + passo no README do depósito |
| 21 | **Zenodo** | DOI por versão | [`deposit/GO-AuNP-Autonomous-Design/`](../deposit/GO-AuNP-Autonomous-Design): estrutura proposta, `.zenodo.json`, `CITATION.cff` e `build_deposit.py` (monta a versão, gera MANIFEST com sha256 e .zip) |
| 22 | **PubChem** | identidade química dos reagentes | [`datasets/reagents/`](../datasets/reagents): `reagent_dictionary.csv` (67 entidades com chemical_name, canonical_name, CID, SMILES, InChI, InChIKey, CAS e sinônimos) montado das 23 fichas locais. **HAuCl4**: 244 grafias (gold chloride, chloroauric acid, tetrachloroauric acid, hydrogen tetrachloroaurate, HAuCl4·3H2O…) → uma entidade (CID 28133) com a hidratação em `form`. Fornecedor, lote e pureza ficam em `reagent_lots` (são propriedades do frasco, não da substância) |
| 23 | **PubMed Central** | texto integral OA (XML JATS) | etapa `fetch` do `literature_pipeline.py` (E-utilities `efetch db=pmc`) |
| 24 | **OpenAlex** | busca bibliográfica | `literature_pipeline.py search`: consulta `("gold nanoparticle" OR AuNP) AND ("graphene oxide" OR GO OR rGO) AND (synthesis OR reduction OR nucleation)` em título+resumo, com filtros de ano, citações, DOI e OA, ordenada por relevância, e também registra os datasets ligados; cliente `pyalex` |
| 25 | **Crossref** | metadados por DOI e deduplicação | `literature_pipeline.py crossref`: editora, licenças, links de texto integral, indício de material suplementar, retratações/atualizações; cliente `habanero` |
| 26 | **Unpaywall** | localizar a versão OA | `literature_pipeline.py oa`; cliente `unpywall` |
| — | pipeline completo | OpenAlex → Crossref → Unpaywall → PDF/XML → LLM/NLP → receitas | `literature_pipeline.py all` gera `works.csv` (já marcado se o DOI está no corpus, em Cruse ou na semente) e `to_extract.jsonl` para o NanoExtractor (`projects/literature-llm/Synthesis-…`) ou o LeMat-Synth; os reagentes extraídos passam por `reagents.py` |
| 27–31 | **NOMAD, Materials Cloud (AiiDA), Materials Project, OQMD, AFLOW** | **só camada computacional** (descritores/estruturas de referência) | `optimade_query.py`: uma consulta OPTIMADE aos seis provedores, incluindo JARVIS (consultas padrão: Au, óxidos/cloretos de Au, Au–C, C–O–H); clientes `optimade-python-tools` e `mp-api` |
| 32 | **re3data** | mapa de repositórios | citado no README do depósito para escolher repositórios certificados |

## 3. Como usar

```bash
tools/setup_env.sh data-sources && source .venvs/data-sources/bin/activate   # clientes (opcional p/ os scripts offline)

# offline (rodam neste repositório já clonado; requerem git lfs pull para os JSON grandes)
python tools/data_sources/reagents.py build                 # dicionário de reagentes (PubChem local)
python tools/data_sources/reagents.py cruse                 # cobertura da normalização em Cruse et al.
python tools/data_sources/build_literature_seed.py          # semente GO–AuNP (Cruse + NSP + AuNCs)
python tools/data_sources/lab_data_model.py templates       # planilhas do laboratório
python tools/data_sources/lab_data_model.py validate datasets/lab

# com internet
python tools/data_sources/fetch_records.py check --all --hash       # prova que as cópias locais = registros oficiais
python tools/data_sources/reagents.py build --online                # completa CIDs das entidades sem ficha local
LIT_MAILTO=voce@unesp.br python tools/data_sources/literature_pipeline.py all --from-year 2010
python tools/data_sources/optimade_query.py --count
python tools/data_sources/build_deposit.py --version 0.1.0
```

## 4. Limitações conhecidas
- A normalização de reagentes concorda em 99,1 % com os regex de precursores dos próprios autores de Cruse et al.
  (`rsc/aunp_precursor_syns_regex.json`) e cobre 79,0 % das menções de materiais em Cruse et al.; o restante é cauda longa
  (ligantes específicos, biomoléculas, substratos). A lista das 300 grafias sem entidade mais frequentes está em
  `datasets/reagents/cruse_material_normalization.csv`: acrescente-as em `aliases.tsv` e rode `build` de novo.
- "gold chloride"/"gold(III) chloride" sem hidratação é, a rigor, ambíguo (AuCl3 × HAuCl4). Esses casos são
  mapeados para HAuCl4, como a proposta pede, com `ambiguous=True`.
- Na semente, os textos de Cruse vêm truncados na fonte (direitos autorais). A marcação de GO usa o texto
  disponível e as listas de materiais. No NSP, tamanhos e λ são extraídos por expressão regular de campos
  livres (`size_nm`, `abs_peak_nm` = mediana dos valores em nm).
- Os scripts que dependem de rede foram testados com respostas simuladas e com o validador de filtros OPTIMADE,
  mas não contra as APIs reais (bloqueadas no contêiner).
