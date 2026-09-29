# Qubot — robô modular para laboratório autônomo

Material da publicação *"Open-Source Modular Laboratory Robots as Building Blocks for Flexible Assembly of
Self-Driving Labs"* (Qubot-Publication v1.0.1; repositório mat-fox/qubot). Descrição original: `README.pdf`.

| Pasta | Conteúdo |
|---|---|
| `hardware/` | gantry Qubot V4: `CAD/` (zip do CAD, `STL/` para impressão, desenhos técnicos em PDF), `Manuals/` (guia de montagem, BOM em .xlsx), licença |
| `data/` | `electrolytes/` (12 corridas: transferências, espessura, digestão, EIS), `shampoo/` (12 corridas: transferências, pH, estabilidade), `nominal_testing/` (repetibilidade e menor incremento de Qubot, OT-2, Ender 3, Genmitsu) |
| `scripts/` | análise e figuras de `electrolytes/` e `shampoo/`, protocolos de `nominal_testing/`, `tutorial/` de controle do gantry com `control-lab-ly`; `requirements.txt` |

`data/` e `scripts/` precisam continuar lado a lado (os scripts localizam os dados a partir da pasta
`scripts`); para usar outra pasta de dados, defina `QUBOT_DATA_DIR`.

```bash
tools/setup_env.sh qubot-scripts && source .venvs/qubot-scripts/bin/activate
cd projects/self-driving-lab/qubot/scripts/shampoo && python data_analysis.py      # regrava data/shampoo/summary.csv
cd ../electrolytes && EIS_INTERACTIVE=0 python data_analysis.py                     # ajuste automático de EIS
```
