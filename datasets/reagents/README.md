# reagents — dicionário de reagentes normalizado com PubChem

Uma entidade por substância, qualquer que seja a grafia: "HAuCl4·3H2O", "chloroauric acid", "tetrachloroauric
acid", "gold chloride" e "hydrogen tetrachloroaurate" → `HAuCl4` (CID 28133), com a hidratação separada em `form`.

| Arquivo | Conteúdo | Origem |
|---|---|---|
| `aliases.tsv` | **curado à mão**: entidade, papel (precursor, redutor, estabilizante, solvente, suporte…), nome canônico, CIDs, sinônimos, siglas, regex | edite aqui |
| `reagent_dictionary.csv` | 67 entidades: `entity_id, role, canonical_name, chemical_name_pubchem, formula, molecular_formula, molecular_weight, pubchem_cid, related_cids, refchem_ids, iupac_name, smiles, inchi, inchikey, cas, synonyms, alias_keys, abbrev, resolved_by, notes` | `reagents.py build` (fichas de `../pubchem/`) |
| `pubchem_records.csv` | as 23 fichas locais (CID/RefChem) com identificadores extraídos e a entidade a que pertencem | idem |
| `cruse_material_normalization.csv` | grafias de materiais de Cruse et al. → entidade (1 092 grafias resolvidas = 79,0 % das menções, sem o "lixo" listado pelos autores; + as 300 sem entidade mais citadas); coluna `cruse_regex_label` = rótulo dos regex de Cruse (`projects/literature-llm/text-mined-aunp-synthesis/rsc/`) — concordância de 99,1 % | `reagents.py cruse` |

Fornecedor, lote, pureza e forma do frasco **não** são propriedades da substância: vão em
`datasets/data-model/templates/reagent_lots.csv`, ligados a `entity_id`.

```bash
python tools/data_sources/reagents.py normalize "Gold(III) chloride trihydrate" "tri-sodium citrate"
python tools/data_sources/reagents.py build --online     # completa CIDs das entidades sem ficha local (rede)
```
```python
import sys; sys.path.insert(0, "tools/data_sources")
from reagents import Normalizer
Normalizer().normalize("HAuCl4.3H2O")   # {'entity_id': 'HAuCl4', 'form': 'trihydrate', 'pubchem_cid': '28133', ...}
```
