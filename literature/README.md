# literature — corpus de artigos do projeto

Texto integral de **65 artigos** citados na proposta FAPESP (2009–2026, a maioria de 2024–2026: otimização
bayesiana, laboratórios autônomos, síntese de AuNP, caracterização de GO, MISO, causalidade…), extraídos
de PDF para texto pesquisável. Os PDFs em si não estão no repositório.

| Arquivo | Conteúdo | Uso |
|---|---|---|
| `artigos_combinados.md` | Os 65 artigos em um único Markdown (≈1,36 M tokens), cada um em `<document index="N">` com `<metadata>` e `<document_content>`; `<!-- p. N -->` marca as páginas; tabelas em Markdown; índice no topo | leitura/busca manual, citar página |
| `chunks.jsonl` | 5 227 trechos (≈255 tokens cada) com `id, documento, arquivo, titulo, autores, ano, doi, secao, tipo, paginas, tokens, contexto, texto` (`tipo`: texto, misto, referência, figura…) | busca semântica / RAG com LLM |
| `relatorio.csv` (`;`) / `relatorio.json` | relatório da extração por PDF: status (65/65 ok), páginas, palavras, tokens, qualidade, título, autores, ano, DOI, revista, palavras-chave | inventário da bibliografia |

```python
import json
chunks = [json.loads(l) for l in open("literature/chunks.jsonl", encoding="utf-8")]
hits = [c for c in chunks if "graphene oxide" in c["texto"].lower()]
print(len(hits), hits[0]["titulo"], "p.", hits[0]["paginas"])
```

Busca por palavras-chave (BM25, sem dependências): `python tools/search_literature.py "oxygen groups gold nucleation" -k 5`
(`--json` para alimentar um LLM). Para busca semântica, gere embeddings de `contexto + texto` de cada trecho (ex.: com `sentence-transformers`)
e recupere os trechos mais próximos da pergunta; cite sempre `titulo` + `paginas`.
