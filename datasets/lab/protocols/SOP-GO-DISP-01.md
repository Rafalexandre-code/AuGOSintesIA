# SOP-GO-DISP-01 — Preparo da dispersão de GO (v0.1, RASCUNHO)

1. Pesar o GO (registrar massa e balança) ou pipetar do estoque (`stock_concentration_mg_mL` do lote).
2. Diluir em água ultrapura até 2,0 mg/mL (estoque do pré-registro).
3. Sonicar em banho por **30 min** (registrar `sonication_time_min`, `sonication_power_W`, temperatura final).
4. Centrifugar a 3000 g por 10 min para remover agregados (registrar rcf e tempo); usar o sobrenadante.
5. Medir pH e, quando possível, potencial zeta e DLS (SOP-DLS-01).
6. Registrar em `go_samples` (prep_type=dispersion) a data e a **idade** em dias ao ser usada (`age_days`);
   usar dispersões com ≤ 7 dias (critério de QC).
