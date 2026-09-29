# code — código do projeto GO–AuNP

Código próprio da proposta, organizado pelas seções do projeto FAPESP. `tools/data_sources/build_deposit.py` copia
estas pastas para o depósito [`GO-AuNP-Autonomous-Design`](../deposit/GO-AuNP-Autonomous-Design/README.md).
Ambiente: `tools/setup_env.sh core && source .venvs/core/bin/activate`. Testes: `python -m pytest code/tests -q`
(21 testes; sinais com parâmetros conhecidos, laço completo simulado e regressões dos bugs corrigidos). O módulo
`atomistic/` usa o ambiente `jarvis` (10 testes em `code/tests/test_atomistic.py`, pulados no `core`).

| Pasta | Seção | O que faz |
|---|---|---|
| [`spectral/`](spectral) | §4.4, §4.6 | `uvvis.py` (lê CSV com `,`/`;`/TAB/espaços e vírgula decimal): branco, diluição e caminho óptico; λ_LSPR, A_LSPR, FWHM, A_LSPR/A450; diâmetro pelas relações de Haiss et al. (2007); **perda espectral J da Eq. (1)** e log(J + ε). `mie.py`: espectros de AuNP/AgNP por Mie com as constantes ópticas de Johnson & Christy (`datasets/optical-constants/`), correção de amortecimento por tamanho e população log-normal |
| [`characterization/`](characterization) | §4.2, §4.12 | `raman.py`: bandas D/G (e D*, D'', D') com **larguras** e ID/IG com incerteza; fundo linear ajustado junto (linhas de base flexíveis subestimam as larguras do GO). `xps.py`: Shirley + C 1s (C–C, C–O, C=O, O–C=O) e C/O pelo survey com RSF. `tem.py`: distribuição de tamanho por limiar + watershed (lê .dm3/.dm4/.emd com RosettaSciIO). Todos geram linhas no formato das tabelas de caracterização |
| [`go_navigator/`](go_navigator/batch_descriptors.py) | §4.2 | descritores por **lote de GO** (média ± sd, desvio entre lotes) e contexto padronizado para o GP |
| [`aunp_designer/`](aunp_designer/designer.py) | §4.5, §4.7, §4.13, §4.17, §4.18 | **AuNP Designer**: GP Matérn-5/2 + ARD por objetivo; os **4 braços** da proposta (`recipe`, `batch` = GP multitarefa com o lote como tarefa, `go` = descritores do GO, `go+impurities` = + impurezas dos reagentes); qLogNEHVI ou qNEHVI; incerteza medida como ruído heteroscedástico; log(J + ε); seleção **novelty-aware** (w·a + (1−w)·n); **leave-one-batch-out** (RMSE, cobertura do IC 95 %); **SHAP** com estabilidade por bootstrap; propostas com bloco e ordem aleatorizada; `run_metadata.json` com commit, pacotes, semente e hash das tabelas |
| [`benchmarking/`](benchmarking) | §4.11, §4.15, §4.18 | `simulator.py` + `sim_lab.py`: laboratório **simulado** (lotes de GO, impurezas, hardware; espectros por Mie; J pelo mesmo `uvvis.py`) gravado no modelo de dados. `campaign_sim.py`: campanha com os braços + aleatório, mesma inicialização (4 receitas × L1–L3) e orçamento; desfecho primário = melhor perda acumulada por rodada, média entre lotes. `stats.py`: HV/IGD/spread (pymoo), Friedman, Wilcoxon + Holm, bootstrap pareado, poder por reamostragem |
| [`causal/`](causal/causal_analysis.py) | §4.9 | DAG GO–AuNP explícito (editável; exporta DOT/GML), estimação por backdoor no DoWhy com IC e 3 refutações, **E-value** (VanderWeele & Ding), descoberta exploratória por PC (causal-learn) |
| [`atomistic/`](atomistic/README.md) | §4.2, §4.5 | **design inverso atomístico GO–Au com o ecossistema JARVIS**: JARVIS-DFT (inclusive reconstrução offline), JARVIS-FF (LAMMPS), CHIPS-FF, ALIGNN/ALIGNN-FF, InterMat; E_ads(Au_n) × química do GO (O/C, f_OH) por MLFF e BO até um alvo (ambiente `jarvis`) |
| [`sustainability/`](sustainability/metrics.py) | §4.14 | E-factor, EcoScale (penalidade de rendimento calculada; as demais vêm da tabela de Van Aken et al. 2006) e **custo por informação útil** (CPU) |

```bash
source .venvs/core/bin/activate
python code/aunp_designer/designer.py demo                                    # laço completo (dados SIMULADOS, em outputs/)
python code/aunp_designer/designer.py propose datasets/lab --batch L2 --representation go+impurities \
       --lot reductant=RED-A --log-objectives spectral_loss_J --q 4           # próxima rodada real
python code/aunp_designer/designer.py validate datasets/lab --log-objectives spectral_loss_J   # LBO dos 4 braços
python code/aunp_designer/designer.py explain datasets/lab --representation go                 # SHAP
python code/spectral/uvvis.py amostra.csv --blank branco.csv --target alvo.csv --sd-const 0.01  # J de um espectro
python code/characterization/raman.py mapa_*.csv --model 5band --sample L1-S01 --out raman.csv
python code/benchmarking/campaign_sim.py --seeds 10 --rounds 12               # simulação de poder (~1 h em CPU)
python code/causal/causal_analysis.py datasets/lab --treatment C_O_ratio --outcome spectral_loss_J
```

## Validação feita (2026-09-29)
- **Mie:** λ_LSPR = 521 nm (20 nm), 536 nm (60 nm) e 571 nm (100 nm) em água, como na literatura.
- **UV-Vis:** em 23 espectros **reais** do KIST (Bespoke; AgNP), λmax difere do valor publicado pelos autores em
  0,26 nm (mediana; 90 % < 0,8 nm). A FWHM difere ~17 nm porque o método deles não foi publicado.
- **Raman:** recupera larguras de D/G e ID/IG de sinais conhecidos com erro < 1 %.
- **XPS:** recupera frações do C 1s com erro < 1 ponto percentual.
- **TEM:** recupera 20 ± 2 nm (19,5 ± 2,6 nm com partículas encostadas).
- **Designer:** os 4 braços, a seleção novelty-aware, o LBO e o SHAP rodam no laboratório simulado, e as tabelas
  geradas passam no validador. No simulador, o SHAP recupera os fatores que o geraram (razão redutor/Au, iodeto, C/O).

## Notas técnicas sobre a proposta
- **qNEHVI × qLogNEHVI:** o qLogNEHVI (Ament et al., NeurIPS 2023) é a reformulação numericamente estável do qNEHVI
  (Daulton et al., 2021): o alvo é o mesmo, mas os gradientes não se anulam. O próprio BoTorch recomenda trocar, e a
  escolha não depende de ruído heteroscedástico. Heteroscedasticidade se trata no **modelo**: aqui, a incerteza medida
  entra como variância de observação. O padrão é qLogNEHVI; `--acq qnehvi` reproduz a formulação original do texto.
- **Tamanho por UV-Vis (Haiss):** a relação A_LSPR/A450 vale para AuNP pequenas (≈ 5–25 nm neste teste) e a de
  λ_LSPR para d > 25–40 nm. Nos compósitos, o fundo de absorção do GO altera A450: use o branco de GO tratado (§4.17).
- **Raman de GO:** as bandas são largas, e linhas de base flexíveis (arPLS/polinômios) "comem" as caudas, subestimando
  as larguras em até 45 % no teste. O padrão é fundo linear ajustado junto com as bandas.
- **Simulação de poder:** use ≥ 8–10 sementes. Com poucas campanhas, a reamostragem é degenerada (poder ≈ 0 ou 1), e o
  script se recusa a estimar. Os números valem para o simulador, não para a química real.
- **Causalidade:** com dados de uma campanha adaptativa, a receita depende do lote (o otimizador escolhe olhando o
  contexto). Por isso essas arestas estão no DAG e o ajuste de backdoor é necessário; a randomização e os blocos em
  `aunp_syntheses` são a proteção principal.

## Pontos de partida para o que ainda é exploratório
- Batch Fingerprint por autoencoder + Active Subspaces: `external/causal-interpretability/ATHENA`, PyTorch (`core`).
- Neural Processes e modelos diferenciáveis de forma espectral: `external/inverse-design/{neuralprocesses,TNP-pytorch}`,
  `external/aunp-spectral/{activephasemap,HEAD}`.
- MISO/multi-fidelidade: `projects/multi-fidelity/chem-MFBO`, `external/multi-fidelity/{misoKG-NIPS2017,emukit,ClancyLab-PAL}`.
- Intervalos com cobertura garantida (§4.18): `external/causal-interpretability/MAPIE` (predição conformal).
- SDL: `external/self-driving-lab/{pylabrobot,MADSci,ivoryos,alabos,Robochem_Flex}`.
