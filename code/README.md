# code — código do projeto GO–AuNP

Código próprio da proposta, organizado pelas seções do projeto FAPESP. `tools/data_sources/build_deposit.py` copia
estas pastas para o depósito [`GO-AuNP-Autonomous-Design`](../deposit/GO-AuNP-Autonomous-Design/README.md).
Ambiente: `tools/setup_env.sh core && source .venvs/core/bin/activate` (Windows: `tools\setup_env.ps1 core` e
`.\.venvs\core\Scripts\Activate.ps1`). Testes: `python -m pytest code/tests -q` (53 testes no `core`: sinais com
parâmetros conhecidos, soluções analíticas, laço completo simulado e regressões dos bugs corrigidos). O módulo
`atomistic/` usa o ambiente `jarvis` (10 testes em `code/tests/test_atomistic.py`, pulados no `core`).
Os valores do plano (alvo E\*, faixa, normalização, sₘ, ε, restrições, orçamento, custos) vêm de
[`config/preregistration.yaml`](../config/preregistration.yaml), lido por `campaign/prereg.py`.

| Pasta | Seção | O que faz |
|---|---|---|
| [`campaign/`](campaign) | §4.11, §4.16 | `prereg.py`: **plano pré-registrado** (validação, selo sha256, `freeze`/`check`, emendas; sₘ e ε pelas regras do piloto). `plan.py`: **gerador do plano experimental** 8/12/24/16 (piloto, LHS maximin × lotes, rodadas adaptativas, confirmação nos lotes reservados com modelo congelado), dias em blocos balanceados, ordem aleatorizada, controles sem GO e brancos de GO, volumes de pipetagem e fichas de bancada |
| [`spectral/`](spectral) | §4.4, §4.6 | `uvvis.py` (lê CSV com `,`/`;`/TAB/espaços e vírgula decimal): branco, diluição e caminho óptico; λ_LSPR, A_LSPR, FWHM, A_LSPR/A450; diâmetro pelas relações de Haiss et al. (2007); **perda espectral J da Eq. (1)** e log(J + ε) (`--prereg` usa alvo/sₘ/ε pré-registrados). `mie.py`: espectros de AuNP/AgNP por Mie com as constantes ópticas de Johnson & Christy, amortecimento por tamanho e população log-normal |
| [`characterization/`](characterization) | §4.2, §4.4, §4.12 | `raman.py` (D/G com **larguras**, ID/IG), `xps.py` (Shirley + C 1s, C/O), `ftir.py` (**deconvolução C=O/H₂O/C=C** — a água em ~1620 cm⁻¹ não é tomada por C=C —, razões de grupos oxigenados e alerta de umidade), `xrd.py` (**d001** por Bragg, Lc por Scherrer, nº de camadas, fração grafítica, **cristalito de Au(111)**), `dls.py` (**cumulantes ISO 22412** a partir de g2(τ): Z-average e PDI, ou repasse da tabela do instrumento), `tem.py` (tamanhos por limiar + watershed; `--go-association`: **fração de AuNP sobre o GO** com IC de Wilson e seletividade de nucleação, por Otsu em 3 classes). Todos geram linhas no formato das tabelas de caracterização |
| [`qc/`](qc/qc_check.py) | §4.12 | **QC automático** pelos critérios de `config/qc_criteria.yaml` (faixa de absorbância, réplicas de leitura, contagem de partículas na TEM, idade da dispersão de GO, preparação independente) e **cartas de controle** Shewhart + EWMA nos controles sem GO; sínteses reprovadas saem do treino do Designer |
| [`go_navigator/`](go_navigator/batch_descriptors.py) | §4.2 | descritores por **lote de GO** (média ± sd, desvio entre lotes) e contexto padronizado para o GP |
| [`aunp_designer/`](aunp_designer/designer.py) | §4.5, §4.7, §4.13, §4.17, §4.18 | **AuNP Designer**: GP Matérn-5/2 + ARD (prior de comprimento escalado pela dimensão) por objetivo; os 4 braços da proposta + `hierarchical`; **qNEHVI** por padrão e qLogNEHVI só se o `noise-check` (Brown–Forsythe entre réplicas + Breusch–Pagan nos resíduos, Holm) indicar heteroscedasticidade; **restrições** (CV de tamanho, A_LSPR) com P(viável); tempo de reação no espaço de busca; ruído medido como variância de observação; seleção **novelty-aware**; **LBO**; **SHAP**; `run_metadata.json` |
| [`transfer_learning/`](transfer_learning/hierarchical.py) | §4.7 | **GP hierárquico** global + fornecedor + lote (um lote novo é previsto com a incerteza honesta de "não visto"), frações de variância por nível, **experimentos até igualar o do-zero** com censura (RMST de Kaplan–Meier) |
| [`miso/`](miso/miso.py) | §4.8 | **MISO** UV-Vis/DLS/TEM (alvo TEM) com os modelos **MGP, ICM e PCM** (como no ClancyLab-PAL) e **gradiente do conhecimento discreto exato por unidade de custo**; fontes simuladas fisicamente (UV-Vis por inversão de Mie, cega perto de 20 nm); benchmark contra só-TEM |
| [`decision/`](decision/voi.py) | §4.14 | **EVPI/EVSI** de caracterizar um lote novo de GO antes de sintetizar (pesos de importância + estimador de diferenças), todos os subconjuntos de técnicas, valor líquido com o valor da informação pré-registrado |
| [`benchmarking/`](benchmarking) | §4.11, §4.15, §4.18 | `simulator.py` + `sim_lab.py`: laboratório **simulado** gravado no modelo de dados (inclui restrições, leitura duplicada e recursos). `strategies.py`: GP+qLogNEI, **RF + qNEHVI** (ensemble), Sobol. `campaign_sim.py`: braços (representações, GP+EI, RF+qNEHVI, novelty w de 0 a 1), cenário de **transferência** para lote reservado, paralelo e retomável; `report` gera [`docs/SIMULACOES.md`](../docs/SIMULACOES.md). `stats.py`: HV/IGD/spread, Friedman, Wilcoxon + Holm, bootstrap pareado, poder por reamostragem, **experimentos até o critério** (RMST + log-rank) |
| [`causal/`](causal/causal_analysis.py) | §4.9 | DAG GO–AuNP explícito, backdoor no DoWhy com refutações, **E-value**; **IPW por balanceamento de entropia** (balanço exato; ou propensão clássica) com SMD/correlação antes e depois; **mediação** (NDE/NIE com interação T×M, avisando confundidores induzidos pelo tratamento); PC (causal-learn) exploratório |
| [`sustainability/`](sustainability/metrics.py) | §4.14 | E-factor (sEF sem água e cEF), EcoScale e **custo por informação útil** a partir das tabelas `resources`/`aunp_syntheses` (`from-lab`), com a decisão "caracterização adicional compensa?" ligada ao EVSI (`--voi`) |
| [`atomistic/`](atomistic/README.md) | §4.2, §4.5 | **design inverso atomístico GO–Au com o ecossistema JARVIS** (ambiente `jarvis`) |

```bash
source .venvs/core/bin/activate
python code/campaign/prereg.py check                                          # plano pré-registrado íntegro?
python code/campaign/plan.py generate --out outputs/plano --lot gold=LOT-AU-01 # plano 8/12/24/16 + fichas
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
python code/benchmarking/campaign_sim.py --seeds 10 --rounds 12 --workers 4   # benchmark + poder (SIMULADO)
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
- **qNEHVI × qLogNEHVI:** o qLogNEHVI (Ament et al., NeurIPS 2023) é a reformulação numericamente estável do qNEHVI
  (Daulton et al., 2021). O padrão segue a proposta (qNEHVI) e a troca é decidida por regra pré-registrada
  (`designer.py noise-check` / `--acq auto`); `--acq qlognehvi` força a versão estável.
- **Prior de comprimento:** sem ele, com poucas dezenas de pontos a máxima verossimilhança leva os comprimentos a ~0
  e o GP vira ruído branco (média constante longe dos dados) — o Designer usa o prior LogNormal escalado pela
  dimensão (Hvarfner et al., ICML 2024; padrão do BoTorch).
- **Tamanho por UV-Vis:** A_LSPR/A450 vale para AuNP pequenas e λ_LSPR para d > 25–40 nm; abaixo de ~30 nm o LSPR
  anda < 1 nm e nem é monótono — por isso a TEM é a fonte-alvo do MISO.
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
- SDL: `external/self-driving-lab/{pylabrobot,MADSci,ivoryos,alabos,Robochem_Flex}`.
