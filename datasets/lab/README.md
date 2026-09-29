# lab — dados experimentais do projeto (a preencher)

Coloque aqui os CSVs do laboratório no formato de `../data-model/templates/` (mesmos nomes de arquivo),
`raw_data/` com os arquivos brutos dos instrumentos e `protocols/` com os SOPs. Valide antes de cada commit:

```bash
python tools/data_sources/lab_data_model.py validate datasets/lab
```
Estes são os únicos dados **medidos** do projeto; tudo em `literature-seed/` é minerado da literatura.
