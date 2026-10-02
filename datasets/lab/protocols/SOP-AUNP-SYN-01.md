# SOP-AUNP-SYN-01 — Síntese de AuNP in situ sobre GO (v0.1, RASCUNHO)

**Objetivo.** Executar uma vaga do plano (`outputs/plano/fichas/dia_XX.md`) como **síntese independente**
(preparação própria), na ordem aleatorizada do dia (§4.9, §4.11, §4.17).

## Antes do dia
- Conferir os lotes de reagentes da ficha (HAuCl₄, redutor, estabilizante) e de GO; anotar em `aunp_syntheses`:
  `gold_precursor_lot_id`, `reductant_lot_id`, `stabilizer_lot_id`, `go_batch_id`, `go_sample_id`.
- Estoques conforme `config/preregistration.yaml` (stock_solutions); estoque de redutor preparado **no dia**
  (NaBH₄/ácido ascórbico degradam) — registrar horário.

## Procedimento (volume total da ficha, padrão 10 mL)
1. Dispersão de GO (SOP-GO-DISP-01) + água no frasco; ajustar pH (registrar valor medido, não só o nominal).
2. Equilibrar na temperatura da ficha no equipamento registrado em `hardware` (hot_plate, water_bath…), agitação
   em rpm fixa (`stirring_rpm`).
3. Adicionar HAuCl₄ (volume da ficha); aguardar 2 min.
4. Adicionar o redutor de uma vez (ou na vazão `addition_rate_mL_min`); a ordem de adição vai em `addition_order`.
5. Manter pelo `time_min` da ficha; resfriar em banho de gelo 2 min; seguir para o SOP-UVVIS-01.
6. Falhas (precipitado, cor inesperada, derramamento): **não descartar o registro** — `status=failed` e descrição em
   `notes` (§4.17). Repetições usam nova `synthesis_id` e `status=repeated` na anterior.

## Controles do plano
- `is_control=no_GO`: receita de referência sem GO (deriva do dia; entra na carta de controle do QC).
- `is_control=GO_blank`: GO + redutor sem Au (fundo óptico para o branco do UV-Vis).

## Segurança e descarte
Seguir as normas do IQ/UNESP; resíduos com Au em frasco próprio (recuperação). Registrar massas de resíduo na
tabela `resources` (E-factor, §4.14).
