# SOP-UVVIS-01 — UV-Vis padronizado das sínteses GO–AuNP (v0.1, RASCUNHO para revisão do orientador)

**Objetivo.** Medir E(λ) de forma comparável entre dias, lotes e operadores, pois a perda espectral J (Eq. 1) é a
resposta primária da campanha (§4.4, §4.17). Critérios numéricos: `config/qc_criteria.yaml` (verificados por
`code/qc/qc_check.py`).

## Materiais
Espectrofotômetro (registrar modelo/nº de série), cubeta de quartzo com **caminho de 10 mm** (registrar se outro),
água ultrapura, pipetas calibradas.

## Procedimento
1. **Aquecimento e linha de base**: lâmpada ligada ≥ 20 min; linha de base com água na faixa **400–800 nm** (passo
   ≤ 2 nm), a mesma faixa do pré-registro.
2. **Branco**: para sínteses com GO, medir o **branco de GO tratado** do mesmo lote (síntese sem Au, mesmo redutor,
   mesma diluição) e registrar o `spectrum_id` dele em `blank_spectrum_id`. Sem GO: branco = água/meio.
3. **Tempo**: ler entre **15 e 60 min** após o término da síntese (registrar `time_after_prep_min`). Fora da janela,
   registrar mesmo assim — o QC marca.
4. **Diluição**: se A_máx > 1,5, diluir (fator inteiro, mesma água) e registrar `dilution_factor`; alvo 0,2–1,2.
5. **Duplicata de leitura**: duas leituras da MESMA alíquota, removendo e recolocando a cubeta. As duas vão para
   `spectra.csv` (dois `spectrum_id`, mesma `synthesis_id`). Duplicata de leitura ≠ síntese nova (§4.17).
6. **Arquivo bruto**: exportar CSV (λ, absorbância) sem processamento para `raw_data/` e apontar em `spectra.file`.
7. **Processamento**: `python code/spectral/uvvis.py <arquivo> --blank <branco> --dilution <f> --path-mm <mm> --prereg`
   (J com o alvo, sₘ e normalização do pré-registro).

## Registro mínimo (spectra.csv)
spectrum_id, synthesis_id, technique=UV-Vis, file, blank_spectrum_id, dilution_factor, path_length_mm,
time_after_prep_min, instrument, date, operator, protocol_id=SOP-UVVIS-01.

## Piloto
Nas 4 preparações do L1 com a receita de referência, fazer **5 leituras repetidas** de uma delas para estimar sₘ
(`python code/campaign/prereg.py s-m <leituras>`), regra pré-registrada.
