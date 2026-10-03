# SOP-DLS-01 — DLS e potencial zeta (v0.1, RASCUNHO)

1. Equilibrar 2 min a 25 °C; 3 medidas × 10 corridas; registrar ângulo, comprimento de onda, viscosidade e índice
   do meio (o processamento usa esses valores).
2. Exportar a **função de correlação** g2(τ) (preferível) ou a tabela de resultados do instrumento.
3. `python code/characterization/dls.py arquivo.csv --angle 173 --wavelength 633 --temperature 25` → Z-average e
   PDI pelo método dos cumulantes (ISO 22412), com a média ± sd das medidas.
4. Para GO, o tamanho por DLS é um diâmetro hidrodinâmico **aparente** (folhas não são esferas): use como descritor
   relativo entre lotes, não como tamanho lateral.
