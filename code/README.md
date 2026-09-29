# code — código do projeto GO–AuNP

Código próprio da proposta, na mesma organização do depósito
[`deposit/GO-AuNP-Autonomous-Design`](../deposit/GO-AuNP-Autonomous-Design/README.md) (`build_deposit.py`
copia estas pastas para `code/` da versão publicada). Ambiente: `tools/setup_env.sh core`.

| Pasta | O que faz | Usa |
|---|---|---|
| [`go_navigator/`](go_navigator/batch_descriptors.py) | descritores por **lote de GO** com incerteza (média ± sd de C/O, ID/IG, espessura…), agregados de `go_characterization` ou lidos de `go_descriptors`; versão padronizada = contexto do GP | tabelas de `datasets/data-model/` |
| [`aunp_designer/`](aunp_designer/designer.py) | **AuNP Designer**: um GP Matérn-5/2 + ARD por objetivo, qLogNEHVI (BoTorch), objetivos `maximize`/`minimize`/`target` lidos de `outcomes.csv`; propostas no formato de `aunp_syntheses.csv` com `campaign_id`/`design_id`. A **transferência entre lotes** é contextual: os descritores do GO Navigator entram no GP e ficam fixos no lote-alvo | BoTorch/GPyTorch (`external/bayesian-optimization/`), GO Navigator, modelo de dados, semente da literatura (`designer.py literature`) |

```bash
source .venvs/core/bin/activate
python code/aunp_designer/designer.py demo                       # laço completo com simulador (dados SIMULADOS, em outputs/)
python code/aunp_designer/designer.py literature                 # faixas de condições na literatura (semente GO–AuNP)
python code/go_navigator/batch_descriptors.py datasets/lab       # descritores por lote
python code/aunp_designer/designer.py propose datasets/lab --batch GO-B02 --q 4 --campaign C01 --iteration 3
```

O `demo` cria dois lotes de GO (um antigo, bem explorado, e um novo com 3 sínteses), roda 4 rodadas de qLogNEHVI
no lote novo e valida todas as tabelas com `lab_data_model.py`. O simulador é **de brinquedo**: tamanho por
nucleação, LSPR pela relação empírica de Haiss et al. (Anal. Chem. 2007), rendimento com ótimo de pH dependente do
lote. Ele serve para testar o encadeamento, não para prever química.

Próximos módulos da proposta, com pontos de partida já no repositório:
- `transfer_learning/` — além do contexto do GP: `MultiTaskGP` (BoTorch) ou `TaskParameter` do BayBE
  (`external/bayesian-optimization/baybe`), com o lote como tarefa.
- MISO / multi-fidelidade — `projects/multi-fidelity/chem-MFBO` (MF-EI/MF-KG com custo),
  `external/multi-fidelity/misoKG-NIPS2017`; a coluna `fidelity` de `aunp_syntheses` já separa as fontes.
- `benchmarking/` — `projects/bayesian-optimization/BOCoDe` (AgNP, vaso de pressão), `datasets/{pressure-vessel,cofs-methane}`,
  RAMBOAU (qNEHVI × MVaR com ruído).
- Espectro completo em vez de só a LSPR — `external/aunp-spectral/{HEAD,miepython}` (perda de forma espectral).
