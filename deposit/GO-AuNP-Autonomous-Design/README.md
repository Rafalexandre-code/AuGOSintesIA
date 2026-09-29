# GO-AuNP-Autonomous-Design — estrutura do depósito (Zenodo / MDF / NIST MDR)

Esqueleto do conjunto de dados e código que será publicado com DOI. **Não é uma cópia dos dados**: a versão é
montada a partir do repositório com

```bash
python tools/data_sources/build_deposit.py --version 0.1.0     # -> outputs/deposit/GO-AuNP-Autonomous-Design-v0.1.0/ + .zip
```

```
GO-AuNP-Autonomous-Design/
├── dataset/
│   ├── literature/          semente da literatura + dicionário de reagentes + busca OpenAlex
│   ├── go_batches/          reagent_lots, go_batches, go_samples, go_descriptors (lote → incerteza)
│   ├── synthesis/           aunp_syntheses, outcomes
│   ├── characterization/    go_characterization (XPS/Raman/AFM…), aunp_characterization (UV-Vis/TEM…)
│   └── raw_data/            arquivos brutos dos instrumentos
├── code/
│   ├── go_navigator/
│   ├── aunp_designer/
│   ├── transfer_learning/
│   └── benchmarking/
├── models/
├── protocols/
├── metadata/                data_dictionary.csv, go_aunp.schema.json, sources.tsv, .zenodo.json, CITATION.cff
├── documentation/
└── MANIFEST.tsv             caminho, tamanho e sha256 de cada arquivo
```

## De onde vem cada pasta

| Pasta do depósito | Origem no repositório | Estado |
|---|---|---|
| `dataset/literature` | `datasets/literature-seed/` (`build_literature_seed.py`), `datasets/reagents/`, `outputs/literature_pipeline/works.csv` (`literature_pipeline.py`) | pronto (semente); busca OpenAlex a rodar com rede |
| `dataset/go_batches`, `synthesis`, `characterization` | `datasets/lab/*.csv`, preenchidos a partir de `datasets/data-model/templates/` e validados por `lab_data_model.py validate` | a preencher com os experimentos |
| `dataset/raw_data`, `protocols` | `datasets/lab/raw_data/`, `datasets/lab/protocols/` | a preencher |
| `code/*`, `models` | pasta `code/` (passe outra com `--code`) — ponto de partida: `external/bayesian-optimization/{botorch,Ax,baybe}`, `projects/bayesian-optimization/RAMBOAU` (qNEHVI/MVaR), `projects/multi-fidelity/chem-MFBO` + `external/multi-fidelity/misoKG-NIPS2017` (MISO), `projects/bayesian-optimization/BOCoDe` e `datasets/{pressure-vessel,cofs-methane}` (benchmark) | a desenvolver |
| `metadata`, `documentation` | `datasets/data-model/`, `tools/data_sources/sources.tsv`, este README, `docs/FONTES_DE_DADOS.md` | pronto |

## Publicação e DOI por versão

1. **Zenodo** (principal): crie o registro uma vez (upload do `.zip` ou integração GitHub → Zenodo com
   `.zenodo.json`). Cada nova versão ("New version") recebe um DOI próprio; o *concept DOI* aponta sempre para a
   mais recente — cite o DOI da versão usada nos resultados. Preencha `CITATION.cff` com o concept DOI e o ORCID.
2. **Materials Data Facility**: publique a mesma versão para torná-la localizável em buscas de materiais
   (cliente Foundry em `external/data-access/foundry`); use o DOI do Zenodo como identificador relacionado.
3. **NIST Materials Data Repository**: alternativa/espelho institucional para dados experimentais.
4. Antes de publicar: `lab_data_model.py validate datasets/lab` sem erros; conferir licenças de terceiros (a semente
   deriva de Cruse et al. — figshare, CC BY 4.0 (confirme na página do registro) — e do NSP — MIT, conforme o cartão do Hugging Face; os textos integrais baixados pelo pipeline **não** entram no
   depósito, só metadados e registros extraídos).

`re3data.org` lista outros repositórios certificados caso a agência ou a revista peça um específico.
