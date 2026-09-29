# Ambientes isolados por subprojeto

Os subprojetos de `Data/` exigem versões de Python/PyTorch incompatíveis entre si (torch 1.7 no MatDesINNe,
2.2 no chem-MFBO, 2.8 no RAMBOAU, 2.14 no restante; Python 3.8 a 3.12). Por isso cada um tem o seu ambiente.

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
| `core` | 3.12 | **projeto GO–AuNP**: BoTorch, GPyTorch, Ax, BayBE, BoFire, Optuna, Bgolearn, SHAP, DoWhy, EconML, lmfit, pyFAI, fabio, sasmodels, miepython, PyMieScatt, RamanSPy, ASE | `core.in`, `core.lock.txt` | resolve ✓ |
| `go-mace` | 3.11 | `Data/GO-MACE-23-main` (gerador, potencial, `make_amorphous_db.py`) | `go-mace.*` | instalado e executado ✓ |
| `sdl` | 3.11 | `Data/SDL-main` | `sdl.*` | instalado e executado ✓ |
| `text-mined` | 3.11 | notebook de `Data/text-mined-aunp-synthesis_public-main` | `text-mined.*` | notebook executado ✓ |
| `qubot-scripts` | 3.11 | `Data/scripts` (versões fixadas pelos autores + openpyxl, pyserial) | `qubot-scripts.*` | análises executadas ✓ |
| `bgolearn` | 3.11 | `Data/Bgolearn-main` | `bgolearn.*` | instalado e executado ✓ |
| `chem-mfbo` | 3.10 | `Data/chem-MFBO-main` (pins do `setup.py`) | `chem-mfbo.*` | resolve ✓ |
| `bocode` | 3.12 | `Data/BOCoDe-main` (+ extras `hpo`, `viz`) | `bocode.*` | resolve ✓ |
| `ramboau` | 3.9 | `Data/RAMBOAU-main` (espelha `install_help/env_man.yml`) | `ramboau.*` | instalado e executado ✓ |
| `matdesinne` | 3.8 | `Data/MatDesINNe-main` (torch 1.7.1, FrEIA do commit do artigo) | `matdesinne.*` | resolve ✓ |
| `qwen-llm` | 3.12 | `Data/Synthesis-Properties-…` (LLaMA-Factory; **GPU ≥ 24 GB**) | `qwen-llm.*` | resolve ✓ |
| `m2hub` | 3.9 | `Data/M2Hub-master` (PyG/DGL via conda) | `../Data/M2Hub-master/environment.yml` | — (conda) |
| `ambergo` | 3.11 | `Data/AmberGO-main` (AmberTools; VMD e Discovery Studio à parte) | `ambergo.yml` | — (conda) |

"Resolve ✓" = `uv pip compile` encontrou um conjunto consistente de versões para Linux x86-64 (o
`.lock.txt`); "instalado e executado ✓" = ambiente criado e código do subprojeto rodado com sucesso.

Observações:
- O PyTorch do PyPI para Linux vem com CUDA (vários GB). Em máquina sem GPU funciona igual (usa CPU).
- `bocode` usa `setuptools-scm`; como a cópia não tem `.git`, o script define
  `SETUPTOOLS_SCM_PRETEND_VERSION_FOR_BOCODE=0.0.0`.
- Os repositórios em `Data/external/` trazem seus próprios `requirements`/`pyproject`; a maior parte das
  bibliotecas deles já está no ambiente `core`.
- Para regenerar um lock: `cd environments && uv pip compile <nome>.in --python-version <py> -o <nome>.lock.txt`.
