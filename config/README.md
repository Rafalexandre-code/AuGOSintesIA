# config — plano pré-registrado e critérios de qualidade

| Arquivo | Conteúdo | Lido por |
|---|---|---|
| [`preregistration.yaml`](preregistration.yaml) | **plano a priori** (§4.11, §4.16): hipótese primária; espectro-alvo E\* (Mie, faixa, passo, normalização); perda J com sₘ e ε definidos pelas regras do piloto; objetivos e **restrições** (CV de tamanho, A_LSPR mínima); aquisição padrão (qNEHVI) e a regra pré-registrada para qLogNEHVI; pesos de novelty investigados; espaço de busca (inclui tempo de reação); lotes de desenvolvimento (L1–L3) e reservados (L4–L6); orçamento 8/12/24/16; **braços prospectivos** (recipe × go+impurities, pareados por rodada e na confirmação); subconjunto de TEM; fatorial 2×2 (condicional, 4 réplicas); controles; **desfecho primário** (valor preditivo do contexto, unidade = lote: LBO + previsões congeladas da confirmação) e secundários descritivos, limiar de relevância de 20 %, poder; sustentabilidade e valor da informação; fontes e custos do MISO; semente; emendas | `code/campaign/prereg.py` e, por ele, Designer, plano, UV-Vis (`--prereg`), MISO, valor da informação, sustentabilidade, benchmark |
| [`qc_criteria.yaml`](qc_criteria.yaml) | critérios de aceitação por técnica (UV-Vis, TEM, dispersão de GO, síntese) e parâmetros das cartas de controle | `code/qc/qc_check.py` |
| [`sustainability_extensions.yaml`](sustainability_extensions.yaml) | extensões condicionais da §4.14: CAPEX/OPEX por técnica e regras do ComplexGAPI (síntese) — RASCUNHO | `code/sustainability/metrics.py capex-opex / complexgapi` |

Os valores marcados **RASCUNHO** são propostas a ajustar com o laboratório **antes** de congelar:

```bash
python code/campaign/prereg.py show                 # resumo e sha256 (status, emendas e o valor de ε ficam fora do selo)
python code/campaign/prereg.py s-m réplica_*.csv    # sₘ(λ) a partir de ≥ 5 réplicas do piloto -> config/s_m.csv
python code/campaign/prereg.py epsilon datasets/lab # ε = 1 % da mediana de J no piloto
python code/campaign/prereg.py freeze               # grava config/preregistration.lock.json (sha256 + commit)
python code/campaign/prereg.py check                # draft | frozen_ok | amended | violated
```

Depois do `freeze`, qualquer mudança vai para `amendments` (data, mudança, motivo, se foi antes de ver os dados);
`check` devolve `violated` se o arquivo mudar sem emenda, e as ferramentas que usam o plano avisam.
