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
| `assets/guide.js` | textos da aba **Guia completo** (cópia de `code/webapp/guide.js`): cada aba, indicador, figura, controle, conceito, fórmula, pergunta e termo |
| `data/<seção>.js` | resultados das análises (`window.AUGO.<seção>`), gerados por `code/webapp/analyses.py` |
| `assets/nano3d.js` | cópia de `code/webapp/nano3d.js`: geometria, síntese e cena da aba **Nanocompósito 3D** |
| `vendor/plotly.min.js` | Plotly (do pacote `plotly` do ambiente `core`, licença MIT) |
| `vendor/three.min.js`, `vendor/OrbitControls.js`, `vendor/RoomEnvironment.js` | three.js r147 (licença MIT, `vendor/LICENSE-three.txt`), cópias de `code/webapp/vendor/` |

## Abas e dados

| Aba | Seções | Dados (todos medidos ou publicados) | Gráficos |
|---|---|---|---|
| Visão geral | todas | volume de dados, os 8 achados principais, a conferência de cada resultado com a literatura e o estado das 18 seções | superfície de Mie 3D, experimentos até o top 5 %, bases |
| Literatura | §4.1, §4.3, §4.14 | 15 928 sínteses de Au (Cruse 2022, NSP 2026, AuNC 2025), 312 GO–AuNP | dispersão 3D T × tamanho × pico com filtros, histograma, morfologias, redutor por ano, tabela GO buscável |
| Óptica e J | §4.4, §4.6, §4.10 | n, k medidos do Au (Johnson & Christy) + 798 pares tamanho–pico da literatura | espectro e **perda J (Eq. 1) ao vivo** com controles e cubeta colorida, superfície de Mie 3D, validação, Mie × Haiss et al. 2007, índice do meio, **inversão bayesiana pico → tamanho**, superfície 3D de log J |
| Nanocompósito 3D | §4.10 | modelo ilustrativo com parâmetros medidos: 3 folhas de GO de simulação publicada (El-Machachi et al. 2024, `data/gostruct.js`), redes do grafeno e do ouro, ligações C–O, Mie, 184 tamanhos GO–AuNP relatados | cena 3D (WebGL) com as folhas de GO publicadas (900/1200/1500 K, cada grupo oxigenado colorido) ou a folha-modelo e AuNP metálica de Wulff–Winterbottom colorida por coordenação, **síntese ao vivo** (LaMer), **plásmon** com a amplitude de Mie, escala de partículas e vista TEM, roteiro de 9 passos; gráficos de sítios × diâmetro, espectro, LaMer, tamanhos × literatura, composição das folhas e **experimento de lotes** (O/C → partículas, calculado no navegador) |
| AuNP Designer | §4.5, §4.18 | campanha AgNP em microfluídica (Mekki-Berrada 2021): 3 295 medidas, 164 condições | **GP do Designer no navegador** (5 controles), superfície 3D de perda/incerteza/EI, validação cruzada, comparação de núcleos (NLPD), calibração probabilística (confiabilidade, PIT, CRPS), efeitos com IC 95 %, 5 sugestões por EI |
| Preditor | §4.18 | 10 993 sínteses de 6 792 artigos (Cruse, NSP, AuNC), 625 receitas distintas | **monte a receita e veja o tamanho previsto** com intervalos conformais por artigo (CQR), P(alvo ± 20 %), cor e LSPR por Mie, "o que mudar", tamanho × temperatura, receitas publicadas parecidas com DOI, **design inverso** (receitas publicadas com mais chance de acertar o alvo) |
| Aprendizado ativo | §4.15, §4.16 | AgNP, P3HT/CNT, perovskitas, crossed barrel, AutoAM (Liang 2021) | curvas com quartis (40 campanhas por estratégia), experimentos até o top 5 %, comparação pareada com o aleatório (Wilcoxon), **sobrevivência** (Kaplan–Meier com censura, RMST pareado com IC e P bayesiana, log-rank), Holm nas 15 comparações |
| Interpretabilidade | §4.13 | GP AgNP (SHAP exato), deslocamento de Stokes de AuNC e tamanho na literatura (TreeSHAP, 28 variáveis, validação por artigo) | enxame SHAP, importância, dependência, H², índices de Sobol (S1, ST) |
| Variabilidade | §4.7, §4.17 | réplicas AgNP, Turkevich (citrato como único redutor) em 1 521 artigos, AuNC por artigo (IC por bootstrap de artigos) | desvio × média, CV em 3D, histograma por artigo, artigo novo × síntese nova |
| Causalidade | §4.9 | 13 633 sínteses de Cruse 2022 e NSP 2026; campanha AgNP | DAG mecanístico, 4 efeitos × literatura (AIPW, IPW, entropia, bootstrap de artigos, E-value), estimadores, balanço (SMD), propensão, cadeia NaBH₄ → tamanho → LSPR × Mie, replicação em Cruse × NSP (efeitos aleatórios, I²), efeitos do(x) das vazões |
| Caracterização | §4.2 | quadros GE de CeO₂ (5 + dark), 207 AuNC | imagem do detector, relevo 3D, perfil radial com 14 anéis indexados, AuNC em 3D |
| Guia completo | — | os mesmos dados do site (cada número citado é lido dos dados) | documentação para leigos em sete partes: comece aqui (roteiro de 10 min, navegação, como ler gráficos, cores e símbolos, atalhos), 24 conceitos com 20 demonstrações interativas usando dados reais, cada aba (pergunta, dados, roteiro, controles, os 13 conjuntos de indicadores, resultados, limites) e cada uma das 75 figuras e tabelas (pergunta, elementos, passo a passo, interação, exemplo com os números atuais, cuidados, erros comuns, cálculo), 30 fórmulas, como foi feito (decisões, mapa do código, linha do tempo), 24 perguntas frequentes, glossário (136 termos) e referências; busca, nível básico/completo, figuras recolhíveis; botão **como ler** em cada gráfico do site leva à explicação |
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
gráfico em tela cheia (`Esc` fecha); **dados** mostra a tabela do gráfico, copia ou baixa o CSV (`;`, vírgula
decimal) e baixa a figura em PNG (2×); `Ctrl P` imprime só a aba aberta; o rótulo **Fig. 4.9e** é o endereço da figura (`#fig-4.9e`); a legenda esconde/isola séries; cada aba tem endereço próprio (`#designer`…).
Trocar o tema mantém filtros e controles.

