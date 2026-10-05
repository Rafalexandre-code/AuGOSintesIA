# site — painel interativo da proposta (só dados experimentais)

Abra **`site/index.html`** com duplo clique: funciona sem servidor e sem internet (o Plotly fica em `vendor/`; sem
internet, só as fontes tipográficas caem para as do sistema). Os arquivos são gerados por
[`code/webapp/build_site.py`](../code/webapp/build_site.py); não edite à mão.

```bash
source .venvs/core/bin/activate
python code/webapp/build_site.py              # refaz todas as análises e o site (~5 min; o benchmark é a parte longa)
python code/webapp/build_site.py --reuse      # só remonta a página, reaproveitando site/data/
python code/webapp/build_site.py --reuse --artifact outputs/augosintesia.html   # página única, tudo embutido
python -m pytest code/tests/test_webapp.py    # GP do navegador = GPyTorch, J = pré-registro, dados completos
```

| Arquivo | Conteúdo |
|---|---|
| `index.html` | página (abas = seções da proposta) |
| `assets/app.js`, `assets/app.css` | cópias de `code/webapp/app.js` e `app.css` (gráficos, GP e Mie no navegador, temas claro/escuro) |
| `data/<seção>.js` | resultados das análises (`window.AUGO.<seção>`), gerados por `code/webapp/analyses.py` |
| `vendor/plotly.min.js` | Plotly (do pacote `plotly` do ambiente `core`, licença MIT) |

## Abas e dados

| Aba | Seções | Dados (todos medidos ou publicados) | Gráficos |
|---|---|---|---|
| Visão geral | todas | volume de dados, os 8 achados principais e o estado de cada uma das 18 seções | superfície de Mie 3D, experimentos até o top 5 %, bases |
| Literatura | §4.1, §4.3, §4.14 | 15 928 sínteses de Au (Cruse 2022, NSP 2026, AuNC 2025), 312 GO–AuNP | dispersão 3D T × tamanho × pico com filtros, histograma, morfologias, redutor por ano, tabela GO buscável |
| Óptica e J | §4.4, §4.6, §4.10 | n, k medidos do Au (Johnson & Christy) + 798 pares tamanho–pico da literatura | espectro e **perda J (Eq. 1) ao vivo** com controles, superfície de Mie 3D, validação, superfície 3D de log J |
| AuNP Designer | §4.5, §4.18 | campanha AgNP em microfluídica (Mekki-Berrada 2021): 3 295 medidas, 164 condições | **GP do Designer no navegador** (5 controles), superfície 3D de perda/incerteza/EI, validação cruzada, efeitos com IC 95 %, 5 sugestões por EI |
| Aprendizado ativo | §4.15, §4.16 | AgNP, P3HT/CNT, perovskitas, crossed barrel, AutoAM (Liang 2021) | curvas com quartis (20 campanhas por estratégia), experimentos até o top 5 %, comparação pareada com o aleatório (Wilcoxon) |
| Interpretabilidade | §4.13 | GP AgNP (SHAP exato), AuNC e literatura (TreeSHAP) | enxame SHAP, importância, dependência, H² |
| Variabilidade | §4.7, §4.17 | réplicas AgNP, Turkevich em 1 746 artigos, AuNC por artigo | desvio × média, CV em 3D, histograma por artigo, artigo novo × síntese nova |
| Causalidade | §4.9 | 5 933 sínteses NaBH₄ × citrato | DAG, balanço (SMD), sobreposição da propensão |
| Caracterização | §4.2 | quadros GE de CeO₂ (5 + dark), 207 AuNC | imagem do detector, relevo 3D, perfil radial com 14 anéis indexados, AuNC em 3D |
| Sobre e dados | — | fontes, licenças, limites, o que aguarda o laboratório, glossário, como usar | — |

Nada do simulador (`code/benchmarking/`, `miso.py`, `designer.py demo`) entra no site; o teste
`test_so_dados_experimentais` confere isso. As seções que dependem das sínteses GO–AuNP do projeto (lotes de GO,
MISO, campanha prospectiva, TEM) aparecem como "aguarda o laboratório".

Desenho: trilho lateral com as etapas da proposta (Panorama, Dados, Modelos, Decisão, Projeto) e o estado de cada
seção; ficha Dados · Método · Achado no topo de cada aba; figuras numeradas pela seção (Fig. 4.5a…); busca rápida por
qualquer gráfico (`Ctrl K` ou `/`). A abertura mostra a **cor real do ouro coloidal** por tamanho, calculada por Mie
com n e k medidos e colorimetria CIE 1931 sob D65 (mesma massa de ouro em todos os tamanhos); a mesma conta colore a
superfície de Mie em 3D e a cubeta da aba Óptica, que muda de cor ao mover diâmetro, dispersão e concentração.

Uso: passe o mouse para ver valores; arraste para girar (3D) ou dar zoom (2D; duplo clique volta); **ampliar** abre o
gráfico em tela cheia (`Esc` fecha); a legenda esconde/isola séries; cada aba tem endereço próprio (`#designer`…).
Trocar o tema mantém filtros e controles.

