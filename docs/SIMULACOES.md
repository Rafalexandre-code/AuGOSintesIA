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
| egbo | 1.084 | 56 % (12; 78) | 80 % | 26.6 | 90 % | 0.0952 |
| novelty-w1 | 1.416 | 36 % (-25; 67) | 60 % | 31.4 | 60 % | 0.861 |
| batch | 1.462 | 10 % (-93; 53) | 60 % | 32.0 | 60 % | 0.968 |
| novelty-w0.75 | 1.794 | 13 % (-126; 63) | 70 % | 32.0 | 60 % | 0.952 |
| autopilot | 1.938 | 23 % (-62; 69) | 50 % | 31.0 | 70 % | 0.625 |
| recipe | 2.174 | — | — | 30.4 | 50 % | — |
| go | 2.429 | 30 % (-38; 65) | 60 % | 32.0 | 40 % | 0.626 |
| novelty-w0.5 | 2.445 | -13 % (-177; 49) | 60 % | 33.6 | 50 % | 0.695 |
| optuna-tpe | 2.675 | -37 % (-266; 43) | 40 % | 33.4 | 30 % | 0.307 |
| gp-ei | 3.192 | -9 % (-100; 47) | 30 % | 32.6 | 30 % | 0.359 |
| rf-qnehvi | 5.373 | -105 % (-267; -13) | 30 % | 35.0 | 20 % | 0.109 |
| dnn-qnehvi | 5.642 | -167 % (-431; -35) | 20 % | 36.0 | 0 % | 0.0115 |
| random | 6.804 | -157 % (-335; -69) | 0 % | 35.6 | 10 % | 0.0406 |
| novelty-w0.25 | 12.710 | -384 % (-727; -189) | 0 % | 36.0 | 0 % | 0.0115 |
| novelty-w0 | 13.622 | -418 % (-841; -194) | 0 % | 36.0 | 0 % | 0.0115 |

Critério: melhor perda balanceada ≤ 2.174 (mediana final do braço recipe). Tempo = nº total de sínteses (inclui as 12 iniciais, iguais em todos os braços); censura no orçamento (36 sínteses).

Frente de Pareto (log J × |d − 20 nm|; mediana entre campanhas; referência e frente comuns a todos os braços):

| braço | hipervolume ↑ | IGD ↓ | spread ↓ |
|---|---|---|---|
| go | 387.79 | 2.929 | 0.17 |
| hierarchical | 375.29 | 2.550 | 0.39 |
| novelty-w1 | 363.65 | 1.762 | 0.52 |
| egbo | 353.94 | 2.093 | 0.43 |
| novelty-w0.75 | 346.56 | 2.120 | 0.24 |
| novelty-w0.5 | 346.03 | 2.232 | 0.11 |
| autopilot | 342.37 | 2.820 | 0.36 |
| go+impurities | 336.44 | 3.099 | 0.22 |
| batch | 327.89 | 2.808 | 0.56 |
| recipe | 315.78 | 2.664 | 0.57 |
| optuna-tpe | 305.08 | 2.938 | 0.21 |
| dnn-qnehvi | 298.38 | 3.776 | 0.58 |
| gp-ei | 292.13 | 3.622 | 0.47 |
| rf-qnehvi | 284.25 | 3.537 | 0.48 |
| random | 277.74 | 3.396 | 0.54 |
| novelty-w0.25 | 263.82 | 3.289 | 0.36 |
| novelty-w0 | 234.88 | 3.661 | 0.45 |

Poder (Wilcoxon unilateral, α = 0,05) por nº de campanhas:

| braço | n=5 | n=10 | n=20 | n=40 |
|---|---|---|---|---|
| autopilot | 0.03 | 0.06 | 0.11 | 0.14 |
| batch | 0.08 | 0.16 | 0.24 | 0.38 |
| dnn-qnehvi | 0.00 | 0.00 | 0.00 | 0.00 |
| egbo | 0.32 | 0.72 | 0.94 | 1.00 |
| go | 0.08 | 0.19 | 0.36 | 0.56 |
| go+impurities | 0.16 | 0.43 | 0.71 | 0.93 |
| gp-ei | 0.00 | 0.01 | 0.02 | 0.00 |
| hierarchical | 0.17 | 0.67 | 0.92 | 1.00 |
| novelty-w0 | 0.00 | 0.00 | 0.00 | 0.00 |
| novelty-w0.25 | 0.00 | 0.00 | 0.00 | 0.00 |
| novelty-w0.5 | 0.08 | 0.08 | 0.06 | 0.05 |
| novelty-w0.75 | 0.18 | 0.16 | 0.20 | 0.31 |
| novelty-w1 | 0.08 | 0.31 | 0.52 | 0.79 |
| optuna-tpe | 0.02 | 0.01 | 0.01 | 0.01 |
| random | 0.00 | 0.00 | 0.00 | 0.00 |
| rf-qnehvi | 0.00 | 0.00 | 0.00 | 0.00 |

Friedman p = 1.57e-09 (todos os braços); Wilcoxon pareados com Holm em summary.json.

## Desenho real pré-registrado: 8 + 12 compartilhadas, 12 rodadas pareadas (1 síntese de cada braço por rodada, mesmo lote e dia)

`python code/benchmarking/campaign_sim.py --scenario prospective --seeds 40 --workers 4`

Cada linha é um par de braços simulado muitas vezes com o orçamento real; a análise é a de `code/campaign/analysis.py` (randomização por troca de sinais, unilateral, α = 0.05), incluindo a confirmação: 8 pares nos lotes reservados L4–L6 com os braços congelados e as previsões dos modelos congelados gravadas antes de sintetizar.

| par | campanhas | **primário**: rejeição — valor preditivo, unidade = lote (IC 95 %) | razão de RMSE (HL, mediana) | descritivo: rejeição por síntese | secundário: rejeição — otimização nos pares de confirmação | exploratório: rejeição — rodadas adaptativas | P(melhor perda final do tratamento < referência) |
|---|---|---|---|---|---|---|---|
| contextual | 40 | 15 % (7–29) | 1.00 | 12 % (5–26) | 18 % (9–32) | 5 % (1–17) | 50 % |
| null | 40 | 0 % (0–9) | 1.00 | 0 % (0–9) | 12 % (5–26) | 12 % (5–26) | 57 % |
| placebo | 40 | 0 % (0–9) | 1.07 | 10 % (4–23) | 18 % (9–32) | 5 % (1–17) | 50 % |

Rejeição no par **contextual** = poder; nos pares **placebo** (contexto registrado sem informação: descritores trocados entre lotes e lote de redutor registrado sorteado) e **null** (braços idênticos) = erro tipo I. O valor preditivo não existe no null (mesma representação → previsões idênticas). O primário usa o **lote** como unidade: os 3 lotes de desenvolvimento por leave-one-batch-out e os 3 reservados pelas previsões congeladas (troca de sinais exata, p mínimo 1/64); a versão por síntese trata sínteses do mesmo lote como independentes e é anticonservadora (ver o placebo), por isso só descritiva.

No cenário contextual, d_b = ln(RMSE_contexto/RMSE_receita) tem média -0.016 (razão 0.984) e dp entre lotes 0.365: o ganho preditivo do contexto é pequeno diante da variação entre lotes. Mais lotes com o mesmo orçamento: seção seguinte (simulação direta com K lotes — reamostrar os d_b daqui ignoraria a correlação dentro da campanha e o aprendizado que mais lotes trazem).

## Mais lotes de GO com o mesmo orçamento (60 sínteses repartidas entre K lotes)

`python code/benchmarking/campaign_sim.py --scenario batches --seeds 40 --workers 4`

Receitas LHS em cada lote (metade com cada lote de redutor); desfecho primário por lote (leave-one-batch-out do modelo agrupado, recipe × go+impurities, troca de sinais exata, α = 0.05). Lotes extras do simulador com C/O sorteado na faixa de L1–L6; todo lote é avaliado com os outros K − 1 no treino.

| lotes (K) | sínteses por lote | poder (contextual) | razão de RMSE mediana | erro tipo I (placebo) |
|---|---|---|---|---|
| 6 | 10.0 | 10 % (4–23) | 1.01 | 5 % (1–17) |
| 9 | 6.7 | 12 % (5–26) | 0.99 | 10 % (4–23) |
| 12 | 5.0 | 10 % (4–23) | 1.01 | 10 % (4–23) |
| 16 | 3.8 | 12 % (5–26) | 1.02 | 10 % (4–23) |

Somando os K: rejeição 11 % com efeito real × 9 % sob o placebo. Se as duas forem parecidas, repartir o orçamento em mais lotes não dá poder ao teste (as dobras do leave-one-batch-out compartilham o treino).

## Fatorial 2×2 (§4.9): poder por nº de réplicas (blocos completos)

`python code/benchmarking/campaign_sim.py --scenario factorial --seeds 100 --workers 4`

Receita fixa (centro do espaço); GO C/O 2,2 × 1,5 (L1 × L3) e redutor com 2 × 45 ppm de iodeto. Efeitos principais por randomização restrita exata com Holm entre os dois (`factorial.py`; com 3 réplicas o menor p possível, 2/64, dobra para 0,0625 e nada é rejeitado), interação por OLS com bloco (HC3); α = 0.05. "null": o mesmo lote nos dois níveis (erro tipo I).

| cenário | réplicas | sínteses | rejeição — impureza | rejeição — GO | rejeição — interação | efeito mediano GO (log J) | efeito mediano impureza (log J) |
|---|---|---|---|---|---|---|---|
| effect | 3 | 12 | 0 % (0–4) | 0 % (0–4) | 6 % (3–12) | +0.27 | +0.07 |
| effect | 4 | 16 | 82 % (73–88) | 100 % (96–100) | 7 % (3–14) | +0.27 | +0.07 |
| effect | 6 | 24 | 95 % (89–98) | 100 % (96–100) | 9 % (5–16) | +0.27 | +0.07 |
| null | 3 | 12 | 0 % (0–4) | 0 % (0–4) | 5 % (2–11) | -0.00 | -0.00 |
| null | 4 | 16 | 2 % (1–7) | 2 % (1–7) | 2 % (1–7) | +0.00 | +0.00 |
| null | 6 | 24 | 1 % (0–5) | 2 % (1–7) | 0 % (0–4) | +0.00 | +0.00 |

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

