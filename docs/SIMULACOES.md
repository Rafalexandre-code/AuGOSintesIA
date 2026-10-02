# Simulações registradas (SIMULADO)

> **SIMULADO** — gerado por `code/benchmarking/campaign_sim.py report` a partir do laboratório simulado
> (`code/benchmarking/simulator.py`). Os números dimensionam e testam o protocolo; não são medidas nem
> previsões do ganho real. Regenerar: ver os comandos em cada seção.

## Cenário principal (L1–L3): 10 sementes × 12 rodadas

`python code/benchmarking/campaign_sim.py --seeds 10 --rounds 12 --q 2 --workers 4`

| braço | mediana da melhor perda final | redução geométrica vs recipe (IC 95 %) | campanhas melhores | experimentos até o critério (RMST) | atingiram | log-rank p |
|---|---|---|---|---|---|---|
| hierarchical | 0.946 | 55 % (9; 80) | 70 % | 27.2 | 90 % | 0.134 |
| go+impurities | 1.067 | 50 % (-8; 81) | 70 % | 26.6 | 80 % | 0.153 |
| novelty-w1 | 1.416 | 36 % (-25; 67) | 60 % | 31.4 | 60 % | 0.861 |
| batch | 1.462 | 10 % (-93; 53) | 60 % | 32.0 | 60 % | 0.968 |
| novelty-w0.75 | 1.794 | 13 % (-126; 63) | 70 % | 32.0 | 60 % | 0.952 |
| recipe | 2.174 | — | — | 30.4 | 50 % | — |
| go | 2.429 | 30 % (-38; 65) | 60 % | 32.0 | 40 % | 0.626 |
| novelty-w0.5 | 2.445 | -13 % (-177; 49) | 60 % | 33.6 | 50 % | 0.695 |
| gp-ei | 3.192 | -9 % (-100; 47) | 30 % | 32.6 | 30 % | 0.359 |
| rf-qnehvi | 5.373 | -105 % (-267; -13) | 30 % | 35.0 | 20 % | 0.109 |
| random | 6.804 | -157 % (-335; -69) | 0 % | 35.6 | 10 % | 0.0406 |
| novelty-w0.25 | 12.710 | -384 % (-727; -189) | 0 % | 36.0 | 0 % | 0.0115 |
| novelty-w0 | 13.622 | -418 % (-841; -194) | 0 % | 36.0 | 0 % | 0.0115 |

Critério: melhor perda balanceada ≤ 2.174 (mediana final do braço recipe). Tempo = nº total de sínteses (inclui as 12 iniciais, iguais em todos os braços); censura no orçamento (36 sínteses).

Poder (Wilcoxon unilateral, α = 0,05) por nº de campanhas:

| braço | n=5 | n=10 | n=20 | n=40 |
|---|---|---|---|---|
| batch | 0.08 | 0.16 | 0.24 | 0.38 |
| go | 0.08 | 0.19 | 0.36 | 0.56 |
| go+impurities | 0.16 | 0.43 | 0.71 | 0.93 |
| gp-ei | 0.00 | 0.01 | 0.02 | 0.00 |
| hierarchical | 0.17 | 0.67 | 0.92 | 1.00 |
| novelty-w0 | 0.00 | 0.00 | 0.00 | 0.00 |
| novelty-w0.25 | 0.00 | 0.00 | 0.00 | 0.00 |
| novelty-w0.5 | 0.08 | 0.08 | 0.06 | 0.05 |
| novelty-w0.75 | 0.18 | 0.16 | 0.20 | 0.31 |
| novelty-w1 | 0.08 | 0.31 | 0.52 | 0.79 |
| random | 0.00 | 0.00 | 0.00 | 0.00 |
| rf-qnehvi | 0.00 | 0.00 | 0.00 | 0.00 |

Friedman p = 3.16e-08 (todos os braços); Wilcoxon pareados com Holm em summary.json.

## Transferência para o lote reservado L4: 10 sementes, 16 sínteses no lote novo

`python code/benchmarking/campaign_sim.py --scenario transfer --seeds 10 --workers 4`

| braço | mediana da melhor perda final | experimentos até o desempenho final do do-zero (RMST) | atingiram | economia relativa |
|---|---|---|---|---|
| scratch | 1.214 | — | — | — |
| transfer-go | 0.605 | 9.2 (do-zero: 13.5) | 60 % | 32 % |
| transfer-hierarchical | 0.678 | 9.3 (do-zero: 13.5) | 80 % | 31 % |

## MISO (UV-Vis/DLS/TEM, alvo TEM): 8 sementes, orçamento 160

`python code/miso/miso.py benchmark --seeds 8 --workers 4`

| modelo | consultas médias (TEM / UV-Vis / DLS) | recomendação pelo modelo: arrependimento final média (mediana) | atingiram | custo até o critério (RMST) | recomendação CONFIRMADA por TEM: arrependimento final média (mediana) | atingiram | custo até o critério (RMST) |
|---|---|---|---|---|---|---|---|
| MGP | 4.1 / 44.2 / 16.6 | 0.0873 (0.0313) | 75 % | 100.6 | 0.0681 (0.0169) | 50 % | 119.9 |
| ICM | 3.5 / 53.8 / 18.1 | 0.3597 (0.3101) | 50 % | 131.4 | 0.0686 (0.0125) | 50 % | 121.5 |
| PCM | 6.0 / 14.0 / 13.0 | 0.2984 (0.2223) | 88 % | 96.0 | 0.0042 (0.0013) | 88 % | 108.5 |
| TEM-only | 8.0 / 0.0 / 0.0 | 0.0426 (0.0128) | 75 % | 120.0 | 0.0168 (0.0058) | 75 % | 112.5 |

Critério: arrependimento simples ≤ 0.01 (objetivo −[ln(d/20)]²). Recomendação pelo modelo = argmax da média a posteriori da TEM no conjunto de candidatos; confirmada = o melhor (pela média a posteriori) entre os pontos já medidos por TEM.

