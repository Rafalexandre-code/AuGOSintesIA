# SOP-TEM-01 — TEM para tamanho e associação ao GO (§4.12) (v0.1, RASCUNHO)

1. Grade de Cu com carbono; 5 µL da dispersão diluída; secar ao ar; registrar a diluição.
2. Aquisição **sistemática**: 10 campos escolhidos por coordenada predefinida na grade (não "os bonitos"), mesma
   magnificação (escala registrada no arquivo .dm3/.dm4/.tif).
3. Meta: **≥ 300 partículas** por síntese (mínimo de QC: 200).
4. Processamento: `python code/characterization/tem.py campos/*.dm4 --synthesis <id> --go-association --out m.csv`
   (tamanho, distribuição e fração de partículas sobre o GO por segmentação em 3 níveis: vácuo / GO / Au).
5. Arquivos brutos em `raw_data/`, listados em `raw_data_file`.
