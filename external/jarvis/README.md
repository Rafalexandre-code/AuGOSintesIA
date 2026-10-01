# external/jarvis — ecossistema JARVIS (NIST) completo

O JARVIS (*Joint Automated Repository for Various Integrated Simulations*, NIST) tem módulos complementares:
DFT (dados), FF (campos de força clássicos), ML (modelos), Tools (pacote Python), Leaderboard (benchmarks) e as
ferramentas mais novas do grupo (AtomGPT, CHIPS-FF, InterMat, SlaKoNet…). As 15 pastas abaixo são cópias sem `.git`
dos repositórios oficiais (commits em [`tools/external_repos.lock.tsv`](../../tools/external_repos.lock.tsv),
atualização com `tools/fetch_external.sh --latest <nome>`; não editar à mão). O código do projeto que as usa está em
[`code/atomistic/`](../../code/atomistic/README.md).

```bash
tools/setup_env.sh jarvis && source .venvs/jarvis/bin/activate     # instala TODAS a partir destas cópias
tools/smoke_test.sh jarvis                                          # verifica cada módulo (~2,5 min)
```

## Módulo por módulo

| Módulo JARVIS | Pasta(s) | O que tem aqui | Como usar no projeto | Funciona sem rede? |
|---|---|---|---|---|
| **JARVIS-DFT** (76 mil materiais 3D, 2D, moléculas; bandgap, esfoliação, elásticas, transporte…) | dados via `jarvis-tools` (`jarvis.db.figshare`) | estruturas do dft_3d (texto, `atomgpt/atomgpt/data`) + 36 propriedades dos benchmarks `dft_3d_*` do Leaderboard; vacâncias e superfícies (`vacancydb_*`, `dft_3d_chipsff_surf_en`) | `code/atomistic/jarvis_data.py search/build-offline`; arquivo original: `jarvis_data.py download --datasets dft_3d dft_2d …` | sim (reconstrução offline, precisão de rede 0,01 Å); o original vem do figshare |
| **JARVIS-FF** (dinâmica clássica/LAMMPS, superfícies e defeitos vs. DFT) | `JARVIS-FF` (dados e scripts originais), `jarvis-tools/jarvis/{io,tasks}/lammps`, `jarvis-tools/jarvis/examples/lammps` | 3 291 cálculos LAMMPS (`data.json`), fluxo `LammpsJob`/`JobFactory`, `inelast.mod` | `code/atomistic/jarvis_ff.py` (Au: EOS, C11/C12/C44, γ(111)/γ(100), vacância vs. JARVIS-DFT); banco atual `jff` por `download` | sim (LAMMPS do PyPI, `lammps[mpi]`, com potenciais EAM/ReaxFF/AIREBO/ILP) |
| **JARVIS-ML** (GNNs/transformers para triagem) | `alignn`, `atomgpt`, `atomvision`, `chemnlp`, `slakonet`, `tb3py` | ALIGNN/ALIGNN-FF (treino e inferência), AtomGPT (direto/inverso), visão para STEM, tight-binding aprendido | `code/atomistic/go_au.py train-alignn / train-alignn-ff / predict`; `calculators.py --calc alignn-ff` | treino: sim; modelos pré-treinados: figshare/HF (`jarvis_data.py download`) |
| **JARVIS-Tools** (pacote Python: acesso, workflows, modelos) | `jarvis-tools`, `jarvis-tools-notebooks` (160 tutoriais) | `Atoms`, CFID, `Surface`/`Vacancy`, interfaces (ZSL), I/O VASP/QE/LAMMPS/Wannier, OPTIMADE | em todos os scripts de `code/atomistic/` | sim |
| **JARVIS-Leaderboard** | `jarvis_leaderboard` | 346 conjuntos com divisões fixas (AI, ES, EXP) | `jarvis_data.py leaderboard <nome>`; enviar um modelo novo = `contributions/` no repositório oficial | sim |
| **CHIPS-FF / CHIPS-TB** (avaliação de MLFF e TB contra o DFT) | `chipsff`, `chipstb` | relaxação, EOS, elásticas, superfícies, vacâncias, fônons, MD, interfaces | `code/atomistic/chipsff_run.py --jid JVASP-825 --calculators mace chgnet sevennet` | sim (MACE-MP do GitHub, CHGNet/SevenNet com pesos no pacote) |
| **InterMat** (interfaces) | `intermat` | geração de interfaces (ZSL), W_ad, alinhamento de bandas | `code/atomistic/go_au.py interface` (Au(111)/grafite(001)) | sim |
| **Design inverso generativo** | `atomgpt`, `atombench` | AtomGPT inverso (propriedade → estrutura, LLM + LoRA), DiffractGPT (DRX → estrutura); métricas do AtomBench | ambiente `atomgpt` (GPU); `atombench <pasta_csv> <saida>` | AtomBench sim; AtomGPT exige GPU e pesos do Hugging Face |
| AtomGPT.org (agentes) | `agapi` | cliente da API | — | não (serviço remoto) |

## Defeitos das versões atuais e como foram contornados (sem editar as cópias)
| Onde | Problema | Contorno |
|---|---|---|
| `jarvis-tools/jarvis/tasks/lammps/templates/inelast.mod` | inclui `/users/knc6/displace.mod` (caminho da máquina do autor) | `jarvis_ff.py` grava uma cópia com o caminho do `displace.mod` do pacote |
| `jarvis.tasks.lammps.LammpsJob` | escreve `pair_coeff * * arquivo Elemento` (só vale para `eam/alloy`); o Au do LAMMPS é `funcfl` | `calculators.funcfl_to_setfl` converte `Au_u3.eam` para setfl (energia −3,93 eV/átomo e C11/C12/C44 = 183/159/45 GPa, como em Foiles et al. 1986) |
| `chipsff` | importa `ase.constraints.ExpCellFilter` (removido no ASE 3.27) | `environments/jarvis.in`: `ase<3.27` |
| `chipsff` (arquivo local) | sem tensor elástico de referência, `[[0,0,0,[0,0,0,0]]][3][3]` gera `IndexError` | `chipsff_run.py` preenche a referência e omite os erros de C11/C44 |
| `chipsff` | carrega `dft_3d`, `vacancydb` e `surfacedb` do figshare mesmo para um arquivo local | `jarvis_data.build_offline_dft3d/build_offline_defects` (mesmos nomes de arquivo, pasta de cache própria) |
| `chipsff` | exporta PNG com plotly 6 + kaleido 1 (exige Chrome) | `plotly<6` + `kaleido==0.2.1` |
| `atombench` | declara a dependência `amd` (outro pacote no PyPI); o código usa `average-minimum-distance` | ambos em `jarvis.in` |
| `atomvision` | fixa `pydantic==1.8.1` e `pyparsing==2.2.1` (2022) | `environments/jarvis.override.txt` (pydantic 2, pyparsing 3) |
| `lammps` (PyPI) | `liblammps` precisa de `libmpi.so.12` | `lammps[mpi]` (MPICH do PyPI); o executável `lmp` funciona direto |

## O que só funciona com rede para figshare / Hugging Face
**Cache do projeto:** com `download --project` (ou movendo `~/.cache/atomgptlab` para `<repo>/.cache/atomgptlab`), os
arquivos ficam dentro do repositório, numa pasta ignorada pelo git, e todos os scripts de `code/atomistic/` passam a
usá-la; `.cache/huggingface` e `.cache/alignn2_models` funcionam do mesmo jeito. Nada disso vai para o GitHub.
Rode uma vez numa máquina com acesso. Os arquivos ficam em `~/.cache/atomgptlab` (conjuntos, ALIGNN-FF, SlaKoNet) e
`~/.alignn2_models` (ALIGNN 2.0); `jarvis_data.py models` lista os nomes aceitos e `status` mostra o que já está lá.
```bash
python code/atomistic/jarvis_data.py download --datasets dft_3d dft_2d jff vacancydb surfacedb alignn_ff_db \
       --alignn formation_energy_peratom_radius optb88vdw_bandgap_radius \
       --alignn-ff matpes_r2scan --slakonet slakonet_v1a --hf knc6/atomgpt_mistral_tc_supercon
```
No Windows (PowerShell) basta um ambiente mínimo, sem LAMMPS/MPI:
```powershell
python -m venv .venvs\jarvis-dl
.venvs\jarvis-dl\Scripts\python.exe -m pip install jarvis-tools alignn slakonet huggingface_hub
.venvs\jarvis-dl\Scripts\python.exe code\atomistic\jarvis_data.py download --datasets dft_3d dft_2d jff vacancydb surfacedb --alignn formation_energy_peratom_radius optb88vdw_bandgap_radius --alignn-ff matpes_r2scan --slakonet slakonet_v1a
```
Os modelos antigos `jv_*_alignn` usam o carregador DGL (quebra sem o DGL); o `download` troca-os pelo equivalente
ALIGNN 2.0 (`*_radius`). No ALIGNN-FF, `matpes_r2scan` (padrão atual, r²SCAN) e `matpes_pbe` são PyTorch puro; os
modelos `v*.2024` (ex.: `v12.2.2024_dft_3d_307k`) são do formato antigo e exigem DGL para rodar. O nome do arquivo do dft_3d depende da versão do jarvis-tools (`jdft_3d-12-12-2022` na cópia
de `external/jarvis`, `jdft_3d-9-24-2025` no PyPI 2026.6); `jarvis_data.py` pergunta ao jarvis-tools instalado.
