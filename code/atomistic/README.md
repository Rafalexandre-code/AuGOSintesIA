# code/atomistic — design inverso atomístico GO–Au com o ecossistema JARVIS

Liga as ferramentas do JARVIS ([`external/jarvis/`](../../external/jarvis/README.md)) ao projeto: a química do GO
(razão O/C, hidroxilas × epóxidos) → ancoragem do Au → descritores físicos do lote para o GO Navigator e o AuNP
Designer. Ambiente: `tools/setup_env.sh jarvis && source .venvs/jarvis/bin/activate`.
Testes: `python -m pytest code/tests/test_atomistic.py -q` (10 testes); execução completa: `tools/smoke_test.sh jarvis`.

| Arquivo | Módulos JARVIS | O que faz |
|---|---|---|
| [`jarvis_data.py`](jarvis_data.py) | JARVIS-DFT, JARVIS-FF, Leaderboard, figshare | acesso aos dados; **reconstrução offline do JARVIS-DFT 3D** (75 993 estruturas + 36 propriedades, `vacancydb`, `surfacedb`) lida pelo próprio `jarvis.db.figshare`; busca por elementos; benchmarks do Leaderboard; dados LAMMPS do JARVIS-FF; `download` dos conjuntos e modelos pré-treinados (ALIGNN, ALIGNN-FF, SlaKoNet, AtomGPT) numa máquina com rede |
| [`calculators.py`](calculators.py) | ALIGNN-FF, JARVIS-FF | calculadoras ASE com uma interface única: `alignn-ff` (pré-treinado ou treinado aqui), `mace-mp`, `mace-mp-d3`, `chgnet`, `sevennet`, `go-mace-23` (C/H/O), `lammps-eam` (Au, EAM convertido para setfl), `emt` (testes) |
| [`jarvis_ff.py`](jarvis_ff.py) | JARVIS-FF, JARVIS-DFT | valida campos de força para o Au: a₀ e B (EOS), γ(111), γ(100), energia de vacância e, no EAM, C11/C12/C44 pelo fluxo LAMMPS do jarvis-tools; compara com o JARVIS-DFT (JVASP-825) e com o JARVIS-FF |
| [`chipsff_run.py`](chipsff_run.py) | CHIPS-FF, JARVIS-DFT | roda o CHIPS-FF (MLFF × DFT: EOS, formação, elásticas, superfícies, vacâncias, fônons) sem rede e com referência do JARVIS-DFT também para arquivos locais |
| [`go_au.py`](go_au.py) | JARVIS-Tools, ALIGNN, ALIGNN-FF, InterMat, BoTorch | **design inverso**: `screen` (GO do GO-MACE-23 + E_ads(Au_n) por MLFF, CFID), `design` (BO: GP com ruído das réplicas + qLogNEI em O/C × f_OH até um E_ads alvo), `train-alignn` (estrutura → E_ads), `train-alignn-ff` (FF específico de GO–Au com os quadros das relaxações), `predict` (triagem rápida com o ALIGNN), `interface` (Au(111)/grafite pelo InterMat, W_ad) |

```bash
source .venvs/jarvis/bin/activate
python code/atomistic/jarvis_data.py status                         # o que está disponível (rede, caches, dados)
python code/atomistic/jarvis_data.py search --elements Au C O --max-atoms 20
python code/atomistic/jarvis_ff.py --calculators lammps-eam mace-mp chgnet sevennet
python code/atomistic/chipsff_run.py --jid JVASP-825 --calculators mace chgnet sevennet
python code/atomistic/go_au.py screen --oc 0.1 0.2 0.3 0.4 --foh 0 0.5 1 --reps 3 --save-frames --cfid
python code/atomistic/go_au.py design --target -1.0 --n-init 8 --n-iter 16 --reps 3        # E_ads alvo (eV)
python code/atomistic/go_au.py train-alignn outputs/atomistic/screen_<data> --epochs 100
python code/atomistic/go_au.py train-alignn-ff outputs/atomistic/screen_<data> --epochs 100
python code/atomistic/go_au.py screen --calc alignn-ff --model-path outputs/atomistic/screen_<data>/alignn_ff ...
python code/atomistic/go_au.py interface --calc mace-mp-d3
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
- **GO–Au:** E_ads(Au₁) de −0,1 a −1,2 eV conforme O/C e f_OH (MACE-MP-0); Au(111)/grafite: W_ad ≈ 0 sem dispersão
  e 0,23 J/m² com D3 (`mace-mp-d3`, separação 3,7 Å) — a adesão Au/grafeno é van der Waals, por isso `mace-mp-d3` é o
  padrão do `go_au.py`.
- ALIGNN, ALIGNN-FF, a predição e o BO rodam de ponta a ponta (dados pequenos; os números só valem com dados maiores).

## Limites (leia antes de usar os números)
- MLFFs universais foram treinados em cristais (DFT-PBE); para GO–Au use-os para **ordenar** composições e confirme
  os finalistas com DFT (Quantum ESPRESSO/VASP pelos workflows `jarvis.tasks`, ou o JARVIS-DFT se o material existir).
- O GO do GO-MACE-23 é uma folha periódica pequena (padrão 4×3: ~50 C): sem bordas/carboxilas por padrão e com
  réplicas estocásticas — por isso o BO usa a variância entre réplicas como ruído.
- A reconstrução offline não substitui o arquivo do figshare (faltam propriedades e precisão); ela serve para rodar
  o fluxo sem rede e é sempre marcada (`reconstrucao_offline=True`).
