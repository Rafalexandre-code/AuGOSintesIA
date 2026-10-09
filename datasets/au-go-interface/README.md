# au-go-interface — interface Au–GO calculada (CÁLCULO, não é medida)

Átomos e uma nanopartícula de ouro relaxados sobre as três folhas de óxido de grafeno (GO) **publicadas** por
El-Machachi et al. (Angew. Chem. Int. Ed. 2024, e202410088; dados Zenodo 10.5281/zenodo.14066557; arquivos em
[`projects/atomistic/GO-MACE-23/structures`](../../projects/atomistic/GO-MACE-23/structures)) e sobre grafeno perfeito.
Gerado por [`code/atomistic/au_go_interface.py`](../../code/atomistic/au_go_interface.py); lido por
`code/webapp/analyses.py` (`_au_go_interface`) para a aba **Nanocompósito 3D** do site (opção "interface relaxada",
cartões "Onde um átomo de ouro se prende ao GO" e "Adesão da nanopartícula a cada folha").

## Potencial

Embutimento subtrativo (como no ONIOM):

    E(GO + Au) = E_GO-MACE-23(GO) + E_MP(GO + Au) − E_MP(GO),    E_MP = MACE-MP-0 small (2023-12-10) + D3(BJ)

- **GO-MACE-23** (El-Machachi et al. 2024; PBE, CASTEP 550 eV, sem dispersão) descreve as ligações do próprio GO.
- **MACE-MP-0 small** (Batatia et al., modelo universal treinado no MPtrj, PBE/PBE+U) + **D3(BJ)** (torch-dftd)
  entra só pela diferença: Au–O, Au–C, Au–H, Au–Au e a dispersão com o ouro.
- Motivo (medido antes do cálculo, em `outputs/`): na geometria otimizada da folha de 900 K o GO-MACE-23 dá forças de
  ~0,001 eV/Å nos átomos internos e o MACE-MP-0 sozinho, ~0,9 eV/Å (mediana; C 0,89, O 1,15 eV/Å) — usado puro, o
  modelo universal deformaria o GO. Os dois potenciais têm o mesmo funcional de referência (PBE).
- Relaxações em float32; todas as energias finais reavaliadas em float64.

Referências no mesmo potencial (`particles.json` → `refs`): ouro fcc com a₀ = 4,111 Å (experimental 4,078 Å),
B = 156 GPa, μ(Au) = −3,906 eV/átomo e γ(111) = 1,40 J/m² (placa de 8 camadas, 2 de cada lado relaxadas).

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `sites.csv` | um átomo de Au por linha: folha (`900K`, `1200K`, `1500K` ou `graphene`), tipo do sítio (classificado por `code/atomistic/go_sites.py`, a mesma regra do site), índice do átomo do sítio na folha publicada (base 0), lado da folha, `E_ads_eV` = energia de adsorção (átomo livre do modelo = 0; é a que o site mostra), `E_site_eV` = E(GO+Au) − E(GO) − μ(Au) (ouro maciço = 0; negativo = o sítio prende o átomo melhor que o ouro maciço; `E_ads_eV` = `E_site_eV` − `refs.E_free_atom_model_eV`), `go_prerelax_eV` = quanto o GO sem ouro baixou ao relaxar (≈ 0 nas regiões em equilíbrio), o mesmo com o GO parado (`E_site_rigid_eV`), as ligações do Au (elemento(tipo):distância Å, até 2,6 Å para O e C e 2,2 Å para H), ligações do GO rompidas (par:antes->depois), deslocamento do átomo do sítio, altura do Au, convergência (fmax em eV/Å), passos, átomos no recorte e livres, segundos |
| `particles.json` | `refs` (com `au_graphene`, o contato Au(111)/grafeno), `equilibrium` (forças do GO-MACE-23 nas folhas publicadas), `validation_medium` (com o `au_graphene` do medium) e, por folha, a nanopartícula de 119 átomos (a mesma da cena: `AUGO_N3CORE.buildParticle(1.5, 0.35)` de `code/webapp/nano3d.js`, d equivalente 1,57 nm) relaxada no centro do recorte da cena: `E_adh_eV` = E(GO+Au₁₁₉) − E(GO) − E(Au₁₁₉ isolada e relaxada), `W_adh_J_m2` = −E_adh / (átomos de Au no primeiro plano × 7,2 Å²) — a face de contato; como a atração de van der Waals vem da partícula inteira, isso superestima W, e o site usa a área projetada π (r_max + 1,44 Å)² (~3,3 nm²) e compara as folhas pela energia por partícula, o mesmo com o GO parado, ligações Au–GO, ligações do GO rompidas, convergência, as posições (Å) antes e depois da relaxação do ouro e do recorte de GO (`go_index` = índices na folha publicada; referencial do recorte da cena: x e z em relação ao centro do recorte, y em relação à mediana dos C) e `interaction` (`small`, `medium`: a interação partícula–folha na geometria relaxada, com a altura varrida — `h_A`, `E_eV`, `h_min_A`, `E_min_eV`, `E_at_relaxed_eV`) |

## Como foi calculado

- **Equilíbrio das folhas publicadas** (`force_map`): as forças do GO-MACE-23 em cada átomo, calculadas em ladrilhos de
  19 Å (vale o miolo de 11 Å; ladrilhos extras cobrem a costura periódica). A mediana é ~0,001 eV/Å, mas 1,4–2,5 % dos
  átomos (204 a 300 por folha, sobretudo C nas bordas de buracos) têm forças acima de 1 eV/Å e chegam a ~16 eV/Å: a
  estrutura "otimizada" não está em equilíbrio nesse potencial ali. Os sítios a menos de 8 Å desses átomos ficam fora do sorteio (`particles.json` → `equilibrium`).
- **Sítios** (`sites`): recorte de 13 Å de raio em torno do átomo do sítio, borda fixa; até 3 sítios por tipo e por
  folha, sorteados (semente fixa por folha) a mais de 12 Å uns dos outros e longe das regiões fora do equilíbrio. "C sp²" = os C sp² mais distantes de
  qualquer O (ilhas de grafeno); "C de borda" = de preferência C com só 2 vizinhos C e nada ligado (ligação pendente).
  O Au parte de 3 direções livres a ~2,2 Å do átomo do sítio (do lado do grupo) e relaxa com o GO parado (BFGS, 0,05
  eV/Å); o melhor ponto de partida segue para a relaxação com o Au e os átomos do GO a até 5,5 Å livres. A referência
  E(GO) é o recorte **sem ouro relaxado com os mesmos átomos livres** (só GO-MACE-23), e o Au parte desse GO: em 6
  sítios dos primeiros cálculos a estrutura publicada não estava num mínimo local do recorte (o próprio GO baixava
  0,06–3,5 eV), o que seria contado como adsorção; `au_go_interface.py recheck` refaz essa conferência em resultados
  antigos (diferença ≤ 0,01 eV: mantém; senão, recalcula) e `prune` tira os sítios que saíram do sorteio. Nos 70
  sítios finais, o GO sem ouro baixa menos de 0,006 eV (`go_prerelax_eV`).
- **Conferência do modelo** (`sites --mp-size medium`): parte dos sítios refeita com o MACE-MP-0 medium (~3× mais
  parâmetros), com a referência e o átomo livre do próprio medium (`refs_medium`): `particles.json` →
  `validation_medium` (folha, tipo, átomo, E_ads small, E_ads medium, ligações small, ligações medium).
- **Partícula** (`particle`): pousada pela mesma regra da cena (primeiro plano 3,25 Å acima do C mais alto, 2,15 Å do
  O, 2,0 Å do H sob a pegada) no centro do recorte da cena (o quadrado de 9,6 nm mais plano, `go_sites.flattest_crop`),
  recorte de 20 Å com a borda fixa, GO livre até 6 Å além da pegada; a altura do corpo rígido é varrida antes (o
  critério de força por átomo não percebe a atração de van der Waals espalhada pela partícula); GO parado (LBFGS) e
  depois GO livre, a partir do GO sem ouro relaxado (a referência), até 0,03 eV/Å.
- **Contato Au(111)/grafeno** (`contact`): grafeno 2×2 sobre Au(111) √3×√3R30° (4 camadas; o ouro comprimido 2,3 %
  no plano para casar as redes), os dois rígidos, com a distância varrida de 2,2 a 5,0 Å em duas posições laterais:
  distância de equilíbrio e energia de ligação por C, com e sem D3. Referências: o vdW-DF dá ligação fraca a
  3,40–3,72 Å nos oito metais estudados, inclusive o Au (Vanin et al., Phys. Rev. B 81, 081408, 2010), e o STM limita
  a atração grafeno–Au a menos de 13 meV por C (Nie et al., Phys. Rev. B 85, 205406, 2012).
- **Conferência da partícula** (`crosscheck`): com a folha e a partícula paradas na geometria relaxada, a altura da
  partícula varre −0,4 a +1,6 Å e a interação E_MP(GO+Au) − E_MP(GO) − E_MP(Au) é calculada no small e no medium (a
  parcela do GO-MACE-23 se cancela). Não inclui a deformação da folha e da partícula, que entra na adesão relaxada.
- Regerar (ambiente com mace-torch, torch-dftd e ase — `tools/setup_env.sh jarvis` — e node; ~1 núcleo-hora por
  folha nos sítios e ~1–2 h por partícula em CPU):

```bash
python code/atomistic/au_go_interface.py refs                                # e --mp-size medium (conferência)
python code/atomistic/au_go_interface.py sites --structure 900K --part 0/2   # e --part 1/2; 1200K, 1500K
python code/atomistic/au_go_interface.py sites --structure graphene
python code/atomistic/au_go_interface.py particle --structure 900K           # 1200K, 1500K, graphene
python code/atomistic/au_go_interface.py contact                             # e --mp-size medium (depois de refs --mp-size medium)
python code/atomistic/au_go_interface.py crosscheck --pattern 900K           # e --mp-size medium; uma folha terminada por vez
python code/atomistic/au_go_interface.py collect                             # → este diretório
```

## Resultados (CÁLCULO; de `sites.csv` e `particles.json`)

- **Sítios** (70 relaxações, todas convergidas; em 30 o Au se liga a O ou C a até 2,6 Å): mediana da energia de
  adsorção por tipo — C de borda −0,82 eV · carbonila −0,34 · lactona −0,20 · grafeno perfeito −0,10 · C sp² −0,10 ·
  epóxi −0,07 · éter −0,04 · hidroxila −0,04 · carboxila −0,03. Os oxigênios mais fortes (até −1,4 eV) são aqueles em
  que o ouro alcança também um C de borda vizinho ou em que o epóxi se abre (1 200 K, átomo 10063: C–O 1,48 → 2,53 Å).
- **Conferência com o MACE-MP-0 medium** (18 sítios: os mais fortes e um de cada tipo): diferença média 0,31 eV (máx.
  0,95), Spearman 0,59. Os 4 C de borda conferidos prendem forte nos dois modelos (small −0,45 a −1,40; medium −0,93
  a −1,57 eV); os oxigênios fortes no small enfraquecem no medium (carbonila −1,41 → −0,46; epóxi −0,95 → −0,25;
  lactona −0,70 → −0,20), exceto o éter preso a C de borda (−0,61 → −0,89). O que se repete nos dois: a ligação
  pendente do C de borda é o sítio de ancoragem; o valor de cada oxigênio depende do modelo.
- **Contato Au(111)/grafeno:** small + D3 a 2,94 Å e −121 meV por C (0,74 J/m²; quase tudo do D3); medium + D3 a
  4,00 Å e −51 meV/C (0,31 J/m²); vdW-DF 3,40–3,72 Å (Vanin et al. 2010); STM < 13 meV/C (Nie et al. 2012). O small
  aproxima demais o ouro do carbono e exagera a atração.
- **Partícula** (119 átomos, uma posição por folha, no centro do recorte da cena):

  | folha | adesão relaxada | GO parado | contatos a até 2,6 Å | afunda | interação na mesma geometria, small → medium |
  |---|---|---|---|---|---|
  | 900 K | −2,10 eV | −1,89 eV | 2 O (carbonila, hidroxila) | 1,8 Å | −2,81 → −1,98 eV |
  | 1 200 K | −8,88 eV | −7,74 eV | 6 O (lactona, carbonila), 3 C (2 de borda) | 2,3 Å | −10,57 → −5,40 eV |
  | 1 500 K | −5,92 eV | −1,80 eV | 3 O (carbonila, lactona), 8 C (4 de borda) | 4,5 Å | −9,79 → −5,56 eV |
  | grafeno | −6,64 eV | −6,40 eV | 2 C sp² a 2,5 Å (sem ligação química) | 0,8 Å | −7,20 → −2,50 eV |

  Nas folhas de 1 200 e 1 500 K há um buraco sob a partícula: ela afunda, se deforma (1,3 e 1,8 Å de desvio médio
  da forma) e se prende a carbonos de borda e a oxigênios de lactona e carbonila; na de 900 K fica apoiada em
  hidroxilas e carbonilas do plano, longe do carbono, e adere pouco. A ordem "folhas com buraco > grafeno > folha de
  900 K" se mantém nos dois modelos (só 1 200 e 1 500 K trocam de lugar, a 0,2 eV uma da outra no medium), mas o
  medium tira de 29 % (900 K) a 65 % (grafeno) da interação. A partícula de 1 500 K parou no limite de 600 passos do
  LBFGS (fmax 2,1 eV/Å, presa em modos duros C=O de lactonas) e foi continuada com FIRE (`particle --resume`, 159
  passos até 0,03 eV/Å).

## Limites (leia antes de usar os números)

- São potenciais de aprendizado de máquina, não DFT: servem para separar os sítios que prendem o ouro dos que não
  prendem e para comparar folhas; cada valor pode errar por alguns décimos de eV (até ~1 eV entre os dois tamanhos do
  MACE-MP-0). Confirme com DFT (por exemplo, pelos fluxos `jarvis.tasks` de `code/atomistic/`).
- O MACE-MP-0 foi treinado em cristais: o átomo de ouro isolado, pouco coordenado, é o que ele descreve pior — o átomo
  livre do modelo fica 2,34 eV acima do ouro maciço (PBE ≈ 3,0 eV; experimental 3,81 eV). As energias de adsorção
  (átomo livre = 0) e as diferenças entre sítios são consistentes dentro do modelo; valores absolutos, os menos confiáveis.
- O MACE-MP-0 small + D3 exagera o contato ouro–carbono (Au(111)/grafeno a 2,94 Å e 121 meV por C, contra 3,40–3,72 Å no
  vdW-DF e menos de 13 meV/C pelo STM): a adesão das partículas, sobretudo ao grafeno, sai inflada; o medium reduz a
  interação em 29–65 % (`interaction`). Use as adesões para comparar folhas, não como valor.
- Poucos sítios por tipo e **uma posição de partícula por folha**: a adesão compara as folhas, sem barra de erro.
- O recorte com borda fixa limita a resposta da folha longe do ouro; o GO não tem água, íons nem ligantes (citrato).
