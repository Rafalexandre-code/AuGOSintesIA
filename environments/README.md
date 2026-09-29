# Ambientes isolados por subprojeto

Os subprojetos de `projects/` exigem versões de Python/PyTorch incompatíveis entre si (torch 1.7 no MatDesINNe,
2.8 no RAMBOAU e no chem-MFBO (que pede 2.2), 2.14 no restante; Python 3.8 a 3.12). Por isso cada um tem o seu ambiente.

```bash
tools/setup_env.sh --list          # tabela abaixo
tools/setup_env.sh core            # cria .venvs/core com as versões fixadas em core.lock.txt
tools/setup_env.sh core --latest   # idem, mas resolvendo core.in com as versões mais novas do PyPI
source .venvs/core/bin/activate
```

O script usa [uv](https://docs.astral.sh/uv/) (instala até a versão de Python certa); sem uv, usa
`python3.X -m venv` + pip. Os ambientes `conda` usam mamba/conda. `.venvs/` está no `.gitignore`.

| Nome | Python | Para | Arquivos | Testado aqui |
|---|---|---|---|---|
| `core` | 3.12 | **projeto GO–AuNP** (`code/`): BoTorch, GPyTorch, Ax, BayBE, BoFire, Optuna, Bgolearn, SHAP, DoWhy, EconML, causal-learn, MAPIE, lmfit, pybaselines, scikit-image, RosettaSciIO, pyFAI, fabio, sasmodels, miepython, PyMieScatt, RamanSPy, pymoo, statsmodels, ASE, pytest | `core.in`, `core.lock.txt` | instalado e executado ✓ |
| `go-mace` | 3.11 | `projects/atomistic/GO-MACE-23` (gerador, potencial, `make_amorphous_db.py`) | `go-mace.*` | instalado e executado ✓ |
| `sdl` | 3.11 | `projects/bayesian-optimization/SDL` | `sdl.*` | instalado e executado ✓ |
| `text-mined` | 3.11 | notebook de `projects/literature-llm/text-mined-aunp-synthesis` | `text-mined.*` | notebook executado ✓ |
| `qubot-scripts` | 3.11 | `projects/self-driving-lab/qubot/scripts` (versões fixadas pelos autores + openpyxl, pyserial) | `qubot-scripts.*` | análises executadas ✓ |
| `bgolearn` | 3.11 | `projects/bayesian-optimization/Bgolearn` | `bgolearn.*` | instalado e executado ✓ |
| `chem-mfbo` | 3.9 | `projects/multi-fidelity/chem-MFBO` (pins do `setup.py`, exceto torch: `chem-mfbo.override.txt` usa 2.8, o mesmo do `ramboau`) | `chem-mfbo.*` | instalado e executado ✓ |
| `bocode` | 3.12 | `projects/bayesian-optimization/BOCoDe` (+ extras `hpo`, `viz`) | `bocode.*` | instalado e executado ✓ |
| `ramboau` | 3.9 | `projects/bayesian-optimization/RAMBOAU` (espelha `install_help/env_man.yml`) | `ramboau.*` | instalado e executado ✓ |
| `matdesinne` | 3.8 | `projects/inverse-design/MatDesINNe` (torch 1.7.1, FrEIA do commit do artigo) | `matdesinne.*` | instalado e executado ✓ |
| `qwen-llm` | 3.12 | `projects/literature-llm/Synthesis-Properties-…` (LLaMA-Factory; **GPU ≥ 24 GB**) | `qwen-llm.*` | resolve ✓ (sem GPU aqui) |
| `data-sources` | 3.12 | `tools/data_sources/` — clientes OPTIMADE, mp-api, jarvis-tools, pyalex, habanero, unpywall, PubChemPy, zenodo_get, huggingface_hub, foundry-ml, pynanomapper | `data-sources.*` | instalado e executado ✓ (APIs exigem rede) |
| `m2hub` | 3.9 | `projects/materials-ml/M2Hub` (PyG/DGL via conda) | `../projects/materials-ml/M2Hub/environment.yml` | — (conda) |
| `ambergo` | 3.11 | `projects/atomistic/AmberGO` (AmberTools; VMD e Discovery Studio à parte) | `ambergo.yml` | — (conda) |

**Teste de execução de todos os ambientes:** `tools/smoke_test.sh` (cada subprojeto roda numa cópia
temporária; `--install` cria o ambiente antes; resultado de 2026-09-29: 11/11 OK).

"Resolve ✓" = `uv pip compile` encontrou um conjunto consistente de versões para Linux x86-64 (o
`.lock.txt`); "instalado e executado ✓" = ambiente criado e código do subprojeto rodado com sucesso.

Observações:
- O PyTorch do PyPI para Linux vem com CUDA (vários GB). Em máquina sem GPU funciona igual (usa CPU).
- `bocode` usa `setuptools-scm`; como a cópia não tem `.git`, o script define
  `SETUPTOOLS_SCM_PRETEND_VERSION_FOR_BOCODE=0.0.0`.
- Os repositórios em `external/` trazem seus próprios `requirements`/`pyproject`; a maior parte das
  bibliotecas deles já está no ambiente `core`.
- Para regenerar um lock: `cd environments && uv pip compile <nome>.in --python-version <py> -o <nome>.lock.txt`
  (se existir `<nome>.override.txt`, acrescente `--override <nome>.override.txt`; o `setup_env.sh` já o aplica).
