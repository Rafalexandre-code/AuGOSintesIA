# code/atomistic — design inverso atomístico GO–Au com o ecossistema JARVIS

Liga as ferramentas do JARVIS ([`external/jarvis/`](../../external/jarvis/README.md)) ao projeto: a química do GO
(razão O/C, hidroxilas × epóxidos) → ancoragem do Au → descritores físicos do lote para o GO Navigator e o AuNP
Designer. Ambiente: `tools/setup_env.sh jarvis && source .venvs/jarvis/bin/activate`.
Testes: `python -m pytest code/tests/test_atomistic.py -q` (10 testes); execução completa: `tools/smoke_test.sh jarvis`.

| Arquivo | Módulos JARVIS | O que faz |
|---|---|---|
| [`jarvis_data.py`](jarvis_data.py) | JARVIS-DFT, JARVIS-FF, Leaderboard, figshare | acesso aos dados; **reconstrução offline do JARVIS-DFT 3D** (75 993 estruturas + 36 propriedades, `vacancydb`, `surfacedb`) lida pelo próprio `jarvis.db.figshare`; busca por elementos; benchmarks do Leaderboard; dados LAMMPS do JARVIS-FF; `download` dos conjuntos e modelos pré-treinados (ALIGNN, ALIGNN-FF, SlaKoNet, AtomGPT) numa máquina com rede |
| [`calculators.py`](calculators.py) | ALIGNN-FF, JARVIS-FF | calculadoras ASE com uma interface única: `alignn-ff` (pré-treinado ou treinado aqui), `mace-mp`, `mace-mp-d3`, **`hybrid`** (GO-MACE-23 no GO + MACE-MP-0 + D3 no que envolve o metal; recomendado para GO–Au), `chgnet`, `sevennet`, `go-mace-23` (C/H/O), `lammps-eam` (Au, EAM convertido para setfl), `emt` (testes) |
| [`jarvis_ff.py`](jarvis_ff.py) | JARVIS-FF, JARVIS-DFT | valida campos de força para o Au: a₀ e B (EOS), γ(111), γ(100), energia de vacância e, no EAM, C11/C12/C44 pelo fluxo LAMMPS do jarvis-tools; compara com o JARVIS-DFT (JVASP-825) e com o JARVIS-FF |
| [`chipsff_run.py`](chipsff_run.py) | CHIPS-FF, JARVIS-DFT | roda o CHIPS-FF (MLFF × DFT: EOS, formação, elásticas, superfícies, vacâncias, fônons) sem rede e com referência do JARVIS-DFT também para arquivos locais |
| [`go_sites.py`](go_sites.py) | — | química das folhas de GO publicadas (El-Machachi et al. 2024): leitura, ligações, **tipo de cada átomo** (epóxi, hidroxila, éter, carbonila, carboxila, lactona; C sp²/sp³/borda) e o recorte da cena 3D; usado também pelo site (`code/webapp/analyses.py`) |
| [`au_go_interface.py`](au_go_interface.py) | MACE-MP-0, torch-dftd | **interface Au–GO nas folhas publicadas** com potencial híbrido (GO-MACE-23 para o GO + MACE-MP-0 + D3 para o ouro, embutimento subtrativo): `refs` (μ, a₀, γ(111) do Au), `sites` (Au₁ por tipo de sítio), `particle` (a nanopartícula de 119 átomos da cena relaxada sobre cada folha e sobre grafeno: adesão, ligações Au–O), `collect` → [`datasets/au-go-interface/`](../../datasets/au-go-interface/README.md) |
| [`go_au.py`](go_au.py) | JARVIS-Tools, ALIGNN, ALIGNN-FF, InterMat, BoTorch | **design inverso**: `screen` (GO do GO-MACE-23 + E_ads(Au_n) por MLFF, CFID), `design` (BO: GP com ruído das réplicas + qLogNEI em O/C × f_OH até um E_ads alvo), `train-alignn` (estrutura → E_ads), `train-alignn-ff` (FF específico de GO–Au com os quadros das relaxações), `predict` (triagem rápida com o ALIGNN), `interface` (Au(111)/grafite pelo InterMat, W_ad) |

```bash
source .venvs/jarvis/bin/activate
python code/atomistic/jarvis_data.py status                         # o que está disponível (rede, caches, dados)
python code/atomistic/jarvis_data.py search --elements Au C O --max-atoms 20
python code/atomistic/jarvis_ff.py --calculators lammps-eam mace-mp chgnet sevennet
python code/atomistic/chipsff_run.py --jid JVASP-825 --calculators mace chgnet sevennet
python code/atomistic/go_au.py screen --oc 0.1 0.2 0.3 0.4 --foh 0 0.5 1 --reps 3 --save-frames --cfid --calc hybrid
python code/atomistic/go_au.py design --target -1.0 --n-init 8 --n-iter 16 --reps 3        # E_ads alvo (eV)
python code/atomistic/go_au.py train-alignn outputs/atomistic/screen_<data> --epochs 100
python code/atomistic/go_au.py train-alignn-ff outputs/atomistic/screen_<data> --epochs 100
python code/atomistic/go_au.py screen --calc alignn-ff --model-path outputs/atomistic/screen_<data>/alignn_ff ...
python code/atomistic/go_au.py interface --calc mace-mp-d3
python code/atomistic/au_go_interface.py refs && python code/atomistic/au_go_interface.py sites --structure 900K
python code/atomistic/au_go_interface.py particle --structure 900K && python code/atomistic/au_go_interface.py collect
```

Dados e modelos pré-treinados: `jarvis_data.py download --project …` grava em `<repo>/.cache/` (ignorado pelo git) e
os scripts usam essa pasta automaticamente; sem ela, usam `~/.cache/atomgptlab` (ver `external/jarvis/README.md`).

## Validação feita (2026-09-29, CPU)
- **Reconstrução do JARVIS-DFT:** 50 estruturas comparadas com os POSCAR completos do ALIGNN: |ΔV/V| mediana 0,15 %
  (máx. 2,5 %), menor distância interatômica com erro ≤ 0,03 Å. Au fcc (JVASP-825): B = 148,6 GPa.
- **JARVIS-FF (EAM Au_u3 via LAMMPS):** −3,93 eV/átomo, C11/C12/C44 = 183/159/45 GPa (Foiles et al. 1986),
  B = 167 GPa (JARVIS-FF: 167,8 GPa), E_vac = 1,03 eV.
- **CHIPS-FF (MACE-MP-0) × JARVIS-DFT para o Au:** γ(111) 0,88 × 0,90 J/m², γ(100) 0,86 × 0,90 J/m², vacância
  0,48 × 0,46 eV, B 132 × 149 GPa. CHGNet subestima γ (0,44 J/m²): a escolha do MLFF importa e deve ser validada.
- **GO–Au:** E_ads(Au₁) de −0,1 a −1,2 eV conforme O/C e f_OH (MACE-MP-0 puro, que deforma o GO — ver abaixo; refaça com
  `--calc hybrid`). Au(111)/grafite com o InterMat (`go_au.py interface`): o W_ad ≈ 0,23 J/m² (D3, separação 3,7 Å)
  registrado antes **não vale** — o filme de "Au(111)" que o InterMat montou tinha 8 átomos em 2 planos a 1,4 Å, com
  13 Å² por átomo (Au(111): 7,2 Å² e 2,35 Å), isto é, ouro esticado ~35 % para casar com a rede do grafite;
  `interface` agora confere o filme (`au_film_check`) e avisa. A adesão Au/grafeno é van der Waals (sem D3, quase zero),
  por isso `mace-mp-d3` é o padrão do `go_au.py`.
- **Contato Au(111)/grafeno bem casado** (`au_go_interface.py contact`: grafeno 2×2 sobre Au(111) √3×√3R30°, ouro
  2,3 % comprimido, 2026-10-09): MACE-MP-0 small + D3 liga a 2,94 Å com 121 meV por C (0,74 J/m²), quase tudo D3; o
  medium + D3 liga a 4,00 Å com 51 meV/C (0,31 J/m²). Referências: vdW-DF 3,40–3,72 Å (Vanin et al., PRB 81, 081408,
  2010); STM < 13 meV/C (< 0,08 J/m²; Nie et al., PRB 85, 205406, 2012). O small aproxima demais o ouro do carbono e
  exagera a atração (o MACE sozinho é mole demais a curta distância e deixa o D3 puxar); o medium fica mais perto. Por
  isso `au_go_interface.py crosscheck` refaz no medium a interação de cada partícula: na mesma geometria, o medium
  tira 29 % (900 K) a 65 % (grafeno) dela e mantém "folhas com buraco (1 200, 1 500 K) > grafeno > 900 K". Nos sítios,
  18 refeitos com o medium mudam 0,31 eV em média (Spearman 0,59); os 4 C de borda prendem forte nos dois.
- **Relaxação da partícula:** o LBFGS travou na de 1 500 K (600 passos, fmax 2,1 eV/Å, toda do GO-MACE-23 em C=O de
  lactonas, que tinham saído do mínimo); `particle --resume` continua da geometria salva com FIRE (159 passos até
  0,03 eV/Å; `--opt BFGS` é a alternativa).
- ALIGNN, ALIGNN-FF, a predição e o BO rodam de ponta a ponta (dados pequenos; os números só valem com dados maiores).
- **MACE-MP-0 × GO-MACE-23 no GO publicado (2026-10-09):** na folha otimizada de 900 K (recorte de 13 Å), forças nos
  átomos internos de ~0,001 eV/Å com o GO-MACE-23 e ~0,9 eV/Å (mediana; C 0,89, O 1,15, H 0,20 eV/Å) com o MACE-MP-0
  small — o universal não reproduz o GO. Por isso `au_go_interface.py` usa o potencial híbrido (GO-MACE-23 para o GO,
  MACE-MP-0 + D3 só para o que envolve o ouro). Ouro no MACE-MP-0 small + D3: a₀ = 4,111 Å, B = 156 GPa,
  γ(111) = 1,40 J/m²; o "átomo livre" do modelo fica 2,34 eV acima do ouro maciço (E0 de regressão; PBE ≈ 3,0 eV,
  experimental 3,81 eV), por isso as energias de sítio usam o ouro maciço como referência.
- **Partícula sobre GO:** o critério de força por átomo (0,05 eV/Å) não basta para uma partícula de 119 átomos sobre a
  folha — a atração de van der Waals se espalha por todos (~0,02 eV/Å cada) e o otimizador parava com a partícula
  ~1,5 Å alta demais; `particle` varre antes a altura do corpo rígido e relaxa até 0,03 eV/Å.
- **Referência do GO:** as folhas publicadas não estão em equilíbrio em todo lugar no próprio GO-MACE-23 (1,4–2,5 %
  dos átomos com |F| > 1 eV/Å, até ~16 eV/Å, sobretudo C nas bordas de buracos). Nos primeiros cálculos, 6 sítios
  perto dessas regiões deram "adsorção" (o próprio GO baixava 0,06–3,5 eV ao relaxar, sem nenhuma ligação Au–GO). O
  protocolo relaxa antes o GO sem ouro com os mesmos átomos livres e usa essa energia como referência (`recheck`
  confere resultados antigos), e o sorteio pula sítios a menos de 8 Å de átomos com |F| > 1 eV/Å (`force_map`, em
  ladrilhos; `prune` tira os que saíram do sorteio). Nos 70 sítios finais o GO sem ouro baixa menos de 0,006 eV.

## Limites (leia antes de usar os números)
- MLFFs universais foram treinados em cristais (DFT-PBE); para GO–Au use-os para **ordenar** composições e confirme
  os finalistas com DFT (Quantum ESPRESSO/VASP pelos workflows `jarvis.tasks`, ou o JARVIS-DFT se o material existir).
- O GO do GO-MACE-23 é uma folha periódica pequena (padrão 4×3: ~50 C): sem bordas/carboxilas por padrão e com
  réplicas estocásticas — por isso o BO usa a variância entre réplicas como ruído.
- A reconstrução offline não substitui o arquivo do figshare (faltam propriedades e precisão); ela serve para rodar
  o fluxo sem rede e é sempre marcada (`reconstrucao_offline=True`).
