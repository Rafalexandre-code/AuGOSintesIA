# code — código do projeto GO–AuNP

Código próprio da proposta, organizado pelas seções do projeto FAPESP. `tools/data_sources/build_deposit.py` copia
estas pastas para o depósito [`GO-AuNP-Autonomous-Design`](../deposit/GO-AuNP-Autonomous-Design/README.md).
Ambiente: `tools/setup_env.sh core && source .venvs/core/bin/activate` (Windows: `tools\setup_env.ps1 core` e
`.\.venvs\core\Scripts\Activate.ps1`). Testes: `python -m pytest code/tests -q` (92 testes no `core`: sinais com
parâmetros conhecidos, soluções analíticas, laço completo simulado e regressões dos bugs corrigidos). O módulo
`atomistic/` usa o ambiente `jarvis` (10 testes em `code/tests/test_atomistic.py`, pulados no `core`).
Os valores do plano (alvo E\*, faixa, normalização, sₘ, ε, restrições, orçamento, custos) vêm de
[`config/preregistration.yaml`](../config/preregistration.yaml), lido por `campaign/prereg.py`.

| Pasta | Seção | O que faz |
|---|---|---|
| [`campaign/`](campaign) | §4.9, §4.11, §4.16, §4.18 | `prereg.py`: **plano pré-registrado** (validação, selo sha256, `freeze`/`check`, emendas; sₘ e ε pelas regras do piloto). `plan.py`: **plano 8/12/24/16** — LHS maximin × lotes, dias balanceados, ordem aleatória, controles, **2 braços prospectivos pareados por rodada** (`--arm`), **confirmação em pares** com os braços congelados e **previsões gravadas antes de sintetizar**, subconjunto de **TEM** (~30), volumes e fichas. `analysis.py`: **análise pré-registrada** — primário = valor preditivo do contexto com o **lote** como unidade (6 lotes fora do treino: LBO em L1–L3 + previsões congeladas em L4–L6; troca de sinais exata, Hodges–Lehmann); por síntese, otimização nos pares de confirmação e fase adaptativa = descritivos. `ingest.py`: **ingestão** — dos arquivos brutos (`spectra.csv`, saídas de `tem.py`/`dls.py`) a `outcomes.csv`: J pelas regras do pré-registro, LSPR, tamanho da TEM ou, sem TEM, do UV-Vis (ajuste de Mie) **calibrado na TEM** do laboratório com a incerteza da calibração; CV só da TEM; `check` confere os desfechos com os brutos. `factorial.py`: **fatorial 2×2** GO (C/O) × impureza em blocos completos (4 réplicas), efeitos principais por randomização restrita exata com Holm, interação por OLS com bloco |
| [`spectral/`](spectral) | §4.4, §4.6 | `uvvis.py`: branco, diluição, caminho óptico; λ_LSPR, A_LSPR, FWHM; Haiss; **perda J (Eq. 1)** e log(J + ε) (`--prereg`). `mie.py`: Mie com Johnson & Christy, amortecimento por tamanho, população log-normal. `neural_process.py`: **modelo espectral diferenciável** (Neural Process latente sobre A(λ) + GP condições → z): previsão com banda calibrada, LBO, design inverso pelo J esperado (exploratório; aviso < 200 espectros); `mie.py fit_size_distribution`: tamanho pelo espectro inteiro (ensemble log-normal + fundo do GO); `neural_process.py design --rank-with-gp`: candidatos do design inverso ordenados pela aquisição do Designer, ao lado da proposta dele |
| [`characterization/`](characterization) | §4.2, §4.4, §4.12 | `raman.py` (larguras, ID/IG; `--per-spectrum`) e `raman_map.py` (**distribuição espacial**: sd espacial, I de Moran), `xps.py` (Shirley + C 1s; `--survey`: at%, O/C, **S/C**), `ftir.py` (C=O/H₂O/C=C deconvoluídas), `xrd.py` (d001, Scherrer, cristalito de Au), `dls.py` (cumulantes ISO 22412), `tem.py` (tamanhos; `--go-association`), `afm.py` (espessura, tamanho lateral, monocamadas), `zeta.py` (Smoluchowski/Henry), `icp.py` (**balanço de Au**: recuperação, conversão, carga), `ocp.py` (OCP como variável de processo), `sers.py` (EF analítico, uniformidade), `saxs.py` (Guinier + esferas polidispersas). Todos geram linhas das tabelas de caracterização |
| [`qc/`](qc/qc_check.py) | §4.12 | **QC automático** pelos critérios de `config/qc_criteria.yaml` (faixa de absorbância, réplicas de leitura, contagem de partículas na TEM, idade da dispersão de GO, preparação independente) e **cartas de controle** Shewhart + EWMA nos controles sem GO; sínteses reprovadas saem do treino do Designer |
| [`go_navigator/`](go_navigator) | §4.2 | `batch_descriptors.py`: descritores por **lote de GO** (média ± sd, desvio entre lotes) e contexto padronizado. `fingerprint.py`: **Batch Fingerprint** (autoencoder com aumento pela incerteza; PCA com aviso se há poucos lotes), utilidade por LBO e **Active Subspace** por gradientes do GP |
| [`aunp_designer/`](aunp_designer) | §4.5, §4.7, §4.13, §4.17, §4.18 | `designer.py`: **AuNP Designer** — GP Matérn-5/2 + ARD (prior de comprimento escalado pela dimensão); 4 braços + `hierarchical`; **qNEHVI** padrão e qLogNEHVI pela regra `noise-check`; **restrições** com P(viável); `--arm` (trajetória própria do braço); novelty-aware; **LBO**; **SHAP** + **interações** (H² de Friedman, `explain --interactions`); `run_metadata.json`. `autopilot.py`: **seleção dinâmica do modelo** por erro prequencial + calibração (inspirado no SPACESHIP) |
| [`transfer_learning/`](transfer_learning) | §4.7 | `hierarchical.py`: **GP hierárquico** global + fornecedor + lote, frações de variância, experimentos até igualar o do-zero (RMST). `hardware.py`: **correção linear entre plataformas** (GP na referência + ridge por plataforma; deslocamento com IC e RMSE leave-one-out com e sem correção) |
| [`miso/`](miso/miso.py) | §4.8 | **MISO** UV-Vis/DLS/TEM (alvo TEM; SAXS condicional) com **MGP, ICM e PCM** e **gradiente do conhecimento discreto exato por custo**; `propose` lê as tabelas do laboratório e sugere (receita, técnica) + a recomendação **confirmada** pela TEM (regra pré-registrada); `benchmark` em simulação contra só-TEM |
| [`decision/`](decision/voi.py) | §4.14 | **EVPI/EVSI** de caracterizar um lote novo de GO antes de sintetizar (pesos de importância + estimador de diferenças), todos os subconjuntos de técnicas, valor líquido com o valor da informação pré-registrado |
| [`kinetics/`](kinetics/kinetics.py) | §4.10 | **cinética reduzida (Finke–Watzky) condicional**: conservação/positividade por integração numérica, recuperação de parâmetros em dados sintéticos, **perfis de verossimilhança**, resíduos e a **regra de parada** da proposta |
| [`sdl/`](sdl/loop.py) | §4.16 | **laço fechado** (ingestão → conferência → QC → proposta → **fila de trabalhos** em JSON neutro com volumes, passos e medidas) com executores **manual** (fila + ficha; a bancada executa) e **simulado** (devolve só brutos; `demo`). Robô de pipetagem ou cloud lab = outro executor lendo a mesma fila |
| [`benchmarking/`](benchmarking) | §4.11, §4.15, §4.18 | `simulator.py` + `sim_lab.py`: laboratório **simulado**. `strategies.py`: GP+qLogNEI, RF+qNEHVI, **DNN ensemble + qNEHVI**, **EGBO**, **TPE (Optuna)**, Sobol. `campaign_sim.py`: cenários `main` (todos os braços, inclusive novelty w de 0 a 1 e autopilot; HV/IGD/spread), `transfer` (lote reservado), **`prospective`** (o desenho real com placebo e nulo para o erro tipo I), **`batches`** (poder × nº de lotes de GO com as mesmas 60 sínteses) e **`factorial`** (poder do 2×2 por réplicas); `--resume` reaproveita campanhas; `calibrate.py`: **calibração do simulador pelo piloto** (momentos simulados: ruído entre preparações e efeito de lote, com faixa plausível; ruído do instrumento pelas duplicatas) → `campaign_sim.py --calibration`; `report` gera [`docs/SIMULACOES.md`](../docs/SIMULACOES.md). `stats.py`: Friedman, Wilcoxon + Holm, bootstrap, redução geométrica, poder, experimentos até o critério (RMST + log-rank) |
| [`causal/`](causal/causal_analysis.py) | §4.9 | DAG GO–AuNP explícito, backdoor no DoWhy com refutações, **E-value**; **IPW por balanceamento de entropia** (balanço exato; ou propensão clássica) com SMD/correlação antes e depois; **mediação** (NDE/NIE com interação T×M, avisando confundidores induzidos pelo tratamento); PC (causal-learn) exploratório |
| [`sustainability/`](sustainability/metrics.py) | §4.14 | E-factor (sEF/cEF), EcoScale, **CPU** a partir das tabelas (`from-lab`, decisão ligada ao EVSI); extensões condicionais **CAPEX/OPEX** por análise e **ComplexGAPI** (síntese) com regras configuráveis |
| [`webapp/`](webapp/build_site.py) | §4.1–4.18 | **site com a proposta executada só com dados experimentais** ([`site/`](../site/README.md)): `expdata.py` (literatura, AgNP, AuNC, campanhas de Liang 2021, constantes ópticas, difração), `analyses.py` (Mie validado contra a literatura + perda J, GP do Designer com validação cruzada e EI, reexecução das campanhas por estratégia, SHAP/H², ruído de réplica e generalização por artigo, IPW, indexação dos anéis de CeO₂), `build_site.py` (gera `site/`; `--reuse`, `--artifact` para página única), `app.js` (gráficos Plotly; GP e Mie/J no navegador com a mesma conta do Python) |
| [`atomistic/`](atomistic/README.md) | §4.2, §4.5 | **design inverso atomístico GO–Au com o ecossistema JARVIS** (ambiente `jarvis`) |

```bash
source .venvs/core/bin/activate
python code/campaign/prereg.py check                                          # plano pré-registrado íntegro?
python code/campaign/plan.py generate --out outputs/plano --lot gold=LOT-AU-01 # plano 8/12/24/16 + fichas
python code/campaign/ingest.py add datasets/lab tem.csv                       # saídas de tem.py/dls.py → tabelas
python code/campaign/ingest.py derive datasets/lab --write                    # brutos → outcomes.csv
python code/campaign/ingest.py check datasets/lab                             # desfechos conferem com os brutos?
python code/sdl/loop.py step datasets/lab --batch L2 --arm go+impurities --q 1 --lot reductant=RED-A   # rodada
python code/benchmarking/calibrate.py datasets/lab                            # simulador calibrado pelo piloto
python code/aunp_designer/designer.py demo                                    # laço completo (dados SIMULADOS)
python code/aunp_designer/designer.py noise-check datasets/lab                # qNEHVI ou qLogNEHVI?
python code/aunp_designer/designer.py propose datasets/lab --batch L2 --representation go+impurities \
       --lot reductant=RED-A --q 2                                            # próxima rodada real
python code/qc/qc_check.py datasets/lab                                       # QC + cartas de controle
python code/characterization/ftir.py esp1.csv esp2.csv --sample GO-B01-S01 --out ftir.csv
python code/characterization/xrd.py go.xy --instrument-fwhm 0.08 --sample GO-B01-S01 --out xrd.csv
python code/characterization/dls.py g2_*.csv --angle 173 --wavelength 633 --temperature 25 --synthesis SYN-0001
python code/characterization/tem.py img.dm4 --go-association --synthesis SYN-0001 --out tem.csv
python code/decision/voi.py datasets/lab --out outputs/voi.json               # EVSI por técnica
python code/sustainability/metrics.py from-lab datasets/lab --voi outputs/voi.json
python code/causal/causal_analysis.py datasets/lab --ipw --treatment GO_mg_mL --outcome size_mean_nm
python code/causal/causal_analysis.py datasets/lab --mediation --treatment C_O_ratio --mediator size_mean_nm
python code/aunp_designer/designer.py propose datasets/lab --arm go+impurities --batch L2 --q 1
python code/campaign/plan.py confirm datasets/lab --lot reductant=RED-A      # pares + previsões congeladas
python code/campaign/analysis.py datasets/lab                                 # análise pré-registrada
python code/campaign/factorial.py plan --go-high L1 --go-low L3 --clean LOT-A --contaminated LOT-B
python code/miso/miso.py propose datasets/lab --model PCM                      # próxima (receita, técnica)
python code/spectral/neural_process.py lbo datasets/lab                       # NP espectral entre lotes
python code/spectral/neural_process.py design datasets/lab --batch L2 --rank-with-gp   # NP gera, GP decide
python code/transfer_learning/hardware.py datasets/lab                        # correção entre plataformas
python code/kinetics/kinetics.py curva_A400.csv                               # cinética + identificabilidade
python code/benchmarking/campaign_sim.py --seeds 10 --rounds 12 --workers 4   # benchmark + poder (SIMULADO)
python code/benchmarking/campaign_sim.py --scenario prospective --seeds 40 --workers 4   # desenho real
python code/benchmarking/campaign_sim.py --scenario batches --seeds 40 --workers 4       # quantos lotes
python code/benchmarking/campaign_sim.py --scenario factorial --seeds 100 --workers 4    # fatorial 2×2
python code/benchmarking/campaign_sim.py --scenario prospective --seeds 40 --workers 4 \
       --calibration config/simulator_calibration.json                       # poder com o simulador calibrado
python code/sdl/loop.py demo --rounds 4                                       # laço autônomo (SIMULADO)
python code/miso/miso.py benchmark --seeds 8 --workers 4                      # MISO (SIMULADO)
```

## Validação feita
- **Mie:** λ_LSPR = 521 nm (20 nm), 536 nm (60 nm) e 571 nm (100 nm) em água, como na literatura.
- **UV-Vis:** em 23 espectros **reais** do KIST (Bespoke; AgNP), λmax difere do valor publicado em 0,26 nm (mediana).
- **Raman / XPS / TEM:** recuperam larguras e ID/IG (< 1 %), frações do C 1s (< 1 p.p.) e 20 ± 2 nm.
- **FTIR / XRD / DLS:** razões de área com erro < 10 % mesmo com a banda da água sobreposta à C=C; d001 = 0,842 nm
  e cristalito de Au por Scherrer (< 5 %); Z-average de 50 nm (< 3 %) e PDI que cresce com a polidispersão.
- **TEM (associação):** fração de partículas sobre o GO dentro de ±0,06 do valor real numa imagem sintética.
- **KG exato do MISO:** coincide com Monte Carlo (300 mil amostras) em ±0,01; o MGP aprende a fonte-alvo com 3
  pontos dela + 40 de uma fonte barata correlacionada melhor que o GP só-alvo.
- **EVPI/EVSI:** no problema quadrático gaussiano (EVPI = 1, EVSI = 1/(1 + σ²)) dá 0,997 e 0,81/0,49/0,20 para
  σ = 0,5/1/2 (analítico 0,8/0,5/0,2).
- **IPW e mediação:** com confundimento forte (ingênuo 4,4 para efeito real 2), o balanceamento por entropia
  recupera 2 com balanço exato; a mediação recupera NDE/NIE, inclusive com interação T×M.
- **Simulações registradas** (SIMULADO, [`docs/SIMULACOES.md`](../docs/SIMULACOES.md); leitura em §17.1 da
  análise): braço hierárquico −55 % de perda × receita (poder 0,67 com 10 campanhas), transferência para lote novo
  com ~31 % menos experimentos, e MISO com PCM + recomendação confirmada por TEM 4× melhor que só-TEM.

## Notas técnicas sobre a proposta
- **Onde a inferência é válida (desenho, §4.18):** a simulação do desenho real mostrou que comparar braços rodada a
  rodada na fase adaptativa não tem poder e infla o erro tipo I (a vantagem de uma trajetória se arrasta). O desfecho
  confirmatório passou a ser o valor preditivo do contexto em lotes nunca vistos, com o **lote** como unidade
  (sínteses do mesmo lote compartilham o erro do lote; pareadas por síntese, o teste rejeitou 10 % sob o placebo e 12 % com efeito real).
  Com 6 lotes o p mínimo é 1/64 e o poder depende do efeito real por lote: `docs/SIMULACOES.md` diz quantos lotes
  o simulador exige — `campaign/analysis.py`. A mudança é do pré-registro (em rascunho) e deve ser validada com o
  orientador antes do `freeze`.
- **Design inverso pelo NP:** prevê espectros entre lotes bem melhor que a referência, mas a otimização por gradiente
  ainda propõe receitas ruins em simulação (mesmo com 300 espectros, muitas no canto do espaço). Por isso o NP só
  GERA candidatos: `neural_process.py design --rank-with-gp` os ordena pela aquisição do Designer junto com a
  proposta do próprio Designer (`designer.acquisition_values`), e um candidato do NP só passa se vencer o GP pelo
  critério do GP.
- **Sínteses sem TEM:** a TEM cobre ~30 das 60 sínteses. O Designer exige todos os objetivos; por isso a ingestão
  deriva o tamanho do UV-Vis calibrado na TEM (com a incerteza da calibração, que o GP usa como ruído conhecido) e
  as restrições sem valor (CV, só da TEM) não descartam a síntese: o GP de cada restrição usa só as medidas.
- **qNEHVI × qLogNEHVI:** o qLogNEHVI (Ament et al., NeurIPS 2023) é a reformulação numericamente estável do qNEHVI
  (Daulton et al., 2021). O padrão segue a proposta (qNEHVI) e a troca é decidida por regra pré-registrada
  (`designer.py noise-check` / `--acq auto`); `--acq qlognehvi` força a versão estável.
- **Prior de comprimento:** sem ele, com poucas dezenas de pontos a máxima verossimilhança leva os comprimentos a ~0
  e o GP vira ruído branco (média constante longe dos dados) — o Designer usa o prior LogNormal escalado pela
  dimensão (Hvarfner et al., ICML 2024; padrão do BoTorch).
- **Tamanho por UV-Vis:** A_LSPR/A450 vale para AuNP pequenas e λ_LSPR para d > 25–40 nm; abaixo de ~30 nm o LSPR
  anda < 1 nm e nem é monótono — por isso a TEM é a fonte-alvo do MISO. Com fundo de GO, Haiss e LSPR quase não
  informam o tamanho (R² LOO ≈ 0 no simulador); o ajuste do espectro inteiro por Mie, calibrado na TEM, chega a
  R² 0,93 e erro de ~10 % em d (otimista: o simulador usa o mesmo Mie). A dispersão (CV) não é identificável pelo
  UV-Vis.
- **Raman de GO:** linhas de base flexíveis "comem" as caudas das bandas largas; o padrão é fundo linear ajustado junto.
- **Simulação de poder:** ≥ 10 sementes (pré-registro). Com poucas campanhas, a reamostragem é degenerada e o script
  se recusa a estimar. Os números valem para o simulador, não para a química real.
- **Causalidade:** numa campanha adaptativa a receita depende do lote (o otimizador escolhe olhando o contexto): o
  efeito de uma variável da receita é confundido pelo lote — daí o IPW com os pais do tratamento no DAG — e a
  receita é um confundidor mediador–desfecho induzido pelo tratamento na mediação (a saída avisa).

## Pontos de partida para o que ainda é exploratório
- Batch Fingerprint por autoencoder + Active Subspaces: `external/causal-interpretability/ATHENA`, PyTorch (`core`).
- Neural Processes e modelos diferenciáveis de forma espectral: `external/inverse-design/{neuralprocesses,TNP-pytorch}`,
  `external/aunp-spectral/{activephasemap,HEAD}`.
- Multi-fidelidade contínua: `projects/multi-fidelity/chem-MFBO`, `external/multi-fidelity/{misoKG-NIPS2017,emukit}`.
- Intervalos com cobertura garantida (§4.18): `external/causal-interpretability/MAPIE` (predição conformal).
- SDL: a fila de `sdl/loop.py` é o ponto de entrada; executores para robôs a partir de `external/self-driving-lab/{pylabrobot,MADSci,ivoryos,alabos,Robochem_Flex}`.
