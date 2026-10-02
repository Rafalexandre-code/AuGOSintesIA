# SOP-GO-CHAR-01 — Caracterização dos lotes de GO (GO Navigator, §4.2) (v0.1, RASCUNHO)

Interpretação conservadora, seguindo Dimiev, Halbig & Talyzin (2026): cautela com atribuições espectrais, overfitting
de deconvoluções e efeitos de umidade/solvente. Cada descritor com incerteza e nº de réplicas.

| Técnica | Amostra | Réplicas mínimas | Descritores (go_characterization.quantity) | Processamento |
|---|---|---|---|---|
| XPS C 1s + survey | filme seco | 3 regiões | C_O_ratio, C-C_fraction, C-O_fraction, C=O_fraction, O-C=O_fraction | `code/characterization/xps.py` (Shirley) |
| Raman (mapa) | filme drop-cast | ≥ 25 pontos | ID_IG, FWHM_D, FWHM_G (larguras priorizadas, não só ID/IG) | `code/characterization/raman.py` |
| FTIR (ATR) | filme seco **e** após 24 h em dessecador | 3 | FTIR_CO_CC, FTIR_COC_CC, FTIR_OH_CC + flag de água | `code/characterization/ftir.py` |
| XRD | filme/pó | 1 (+ réplica de preparo) | d001_nm, Lc_nm, n_layers, frac_graphitic | `code/characterization/xrd.py` |
| DLS + zeta | dispersão 0,1 mg/mL | 3 | hydrodynamic_nm, PDI, zeta_mV (tamanho de GO por DLS é aparente) | `code/characterization/dls.py` |
| AFM (se disponível) | Si/SiO₂ | ≥ 50 folhas | thickness_nm, lateral_size_um | — |

Depois: `python code/go_navigator/batch_descriptors.py datasets/lab --write --force` (média ± sd por lote).
Lotes reservados (L4–L6) também são caracterizados **antes** da confirmação, sem olhar resultados de síntese.
