# optical-constants — constantes ópticas (n, k) de metais

Arquivos copiados sem alteração do banco **refractiveindex.info** (domínio público, CC0 1.0;
github.com/polyanskiy/refractiveindex.info-database, commit `c5c2f188`, 2026-09-04). Formato YAML: colunas
`λ (µm)  n  k`.

| Arquivo | Material | Referência | Uso |
|---|---|---|---|
| `Au_Johnson-Christy_1972.yml` | Au | Johnson & Christy, Phys. Rev. B 6, 4370 (1972) | padrão da literatura para espectros de AuNP por Mie |
| `Au_McPeak_2015.yml` | Au | McPeak et al., ACS Photonics 2, 326 (2015) | filmes modernos; comparação/sensibilidade |
| `Ag_Johnson-Christy_1972.yml` | Ag | Johnson & Christy (1972) | AgNP (BOCoDe/AgNP, núcleo-casca Au@Ag) |

Lidos por `code/spectral/mie.py` (extinção de AuNP em água, com correção de amortecimento por tamanho).
