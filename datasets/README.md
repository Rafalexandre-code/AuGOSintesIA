# datasets — dados avulsos do projeto

Dados que não pertencem a um subprojeto específico. Os datasets que acompanham o código de um
subprojeto continuam dentro dele (ex.: `projects/multi-fidelity/chem-MFBO/data/`,
`projects/self-driving-lab/qubot/data/`). Arquivos marcados com **LFS** exigem `git lfs install && git lfs pull`.

| Pasta | Conteúdo | Tamanho | Origem / referência |
|---|---|---|---|
| [`aunc-fluorescence/`](aunc-fluorescence) | 207 nanoclusters de Au: tamanho, λexc, λem, ligante, T, pH e tempo de síntese, DOI. CSV com `;` e codificação latin-1 (a `.xlsx` tem o mesmo conteúdo) | 64 KB | compilação da literatura (provável base de Sánchez-Dueñez et al., ACS Omega 2025) |
| [`nanocrystal-synthesis-db/`](nanocrystal-synthesis-db) | Base síntese→propriedade de nanocristais extraída por LLM: `dataset.json` (100 731 registros, bruto) e `dataset_low_conf_skip-clean.json` (47 023, limpo) — **LFS**; `statistics_of_product_names.xlsx` (frequência dos nomes de produtos); `README.md`/`gitattributes` = cartão original do HuggingFace | 698 MB | Gu et al., ACS Nano 2026 ([código](../projects/literature-llm/Synthesis-Properties-Database-for-Nanomaterials)) |
| [`aunp-text-mined/`](aunp-text-mined) | 5 154 artigos de síntese de AuNP minerados (precursores, quantidades, ações, morfologias, tamanhos) — **LFS**; é o mesmo conteúdo do `.zip` em [`projects/literature-llm/text-mined-aunp-synthesis`](../projects/literature-llm/text-mined-aunp-synthesis) | 49 MB | Cruse et al., Sci. Data 2022 |
| [`cofs-methane/`](cofs-methane) | `dataset_v1.csv`: 69 839 COFs com descritores geométricos e capacidade de entrega de CH₄ (GCMC) | 20 MB | Mercado et al. (benchmark de BO/triagem) |
| [`pressure-vessel/`](pressure-vessel) | `pressure_vessel_DS.csv`: 52 272 projetos de laminado compósito (ângulo, nº de camadas, rigidez, critério mínimo) | 2,7 MB | problema de engenharia para BO em tabela |
| [`pubchem/`](pubchem) | 53 fichas PubChem (JSON/XML) dos reagentes: HAuCl₄ (várias formas), NaBH₄, ác. ascórbico, citrato, CTAB, PVP, óxido de grafeno, NaOH, HCl, etanol, água; estruturas 2D/3D | 12 MB | pubchem.ncbi.nlm.nih.gov |
| [`xrd-ceo2-calibration/`](xrd-ceo2-calibration) | Frames de detector de área GE (`.ge3`: 5 × 2048×2048, uint16, cabeçalho de 8 192 bytes) de CeO₂ (padrão de calibração) e de escuro; `dark_after_000413.ge3` é **LFS** | 201 MB | difração de raios X (APS); leitura com `fabio`/`pyFAI` |

Detalhes, colunas e exemplos de leitura: [`docs/ANALISE_REPOSITORIO.md`](../docs/ANALISE_REPOSITORIO.md) §4–§5.

```python
import pandas as pd, fabio
aunc = pd.read_csv("datasets/aunc-fluorescence/DATASET_AuNCs.csv", sep=";", encoding="latin-1")
ge = fabio.open("datasets/xrd-ceo2-calibration/CeO2_1s_000012.ge3")   # ge.nframes == 5
```
