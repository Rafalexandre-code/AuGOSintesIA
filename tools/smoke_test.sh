#!/usr/bin/env bash
# Testes rápidos de execução: roda cada subprojeto no seu ambiente (.venvs/<nome>), numa CÓPIA temporária,
# para não regravar resultados versionados (ex.: qubot/data/*/summary.csv).
#
# Uso:
#   tools/smoke_test.sh                  # testa todos os ambientes já criados (pula os ausentes)
#   tools/smoke_test.sh sdl bocode       # só estes
#   tools/smoke_test.sh --install go-mace  # cria o ambiente (tools/setup_env.sh) antes de testar
#   SMOKE_FULL=1 tools/smoke_test.sh qubot-scripts   # inclui a análise completa de EIS (~20 min)
# Saída: uma linha OK/FALHOU/PULADO por ambiente; log completo em $SMOKE_LOG (padrão: outputs/smoke_test.log).
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG="${SMOKE_LOG:-$ROOT/outputs/smoke_test.log}"; mkdir -p "$(dirname "$LOG")"; : > "$LOG"
export WANDB_MODE=disabled MPLBACKEND=Agg PYTHONDONTWRITEBYTECODE=1 EIS_INTERACTIVE=0
install=0; names=()
for a in "$@"; do case "$a" in --install) install=1 ;; -h|--help) sed -n '2,9p' "$0"; exit 0 ;; *) names+=("$a") ;; esac; done
ALL=(data-sources core sdl bgolearn ramboau chem-mfbo bocode go-mace text-mined qubot-scripts matdesinne)
[ "${#names[@]}" -eq 0 ] && names=("${ALL[@]}")

copy() { local t; t="$(mktemp -d)"; cp -r "$ROOT/$1" "$t/"; echo "$t/$(basename "$1")"; }
py() { "$ROOT/.venvs/$ENV/bin/python" "$@"; }

t_data-sources() {
  cd "$ROOT"
  py tools/data_sources/reagents.py normalize "HAuCl4·3H2O" "Gold(III) chloride trihydrate" | grep -q "'HAuCl4'"
  py - <<'EOF'
import json, jsonschema
from optimade.filterparser import LarkParser
import sys; sys.path.insert(0, "tools/data_sources"); import optimade_query as q
for f in q.DEFAULT_FILTERS.values(): LarkParser().parse(f)
jsonschema.Draft202012Validator.check_schema(json.load(open("datasets/data-model/go_aunp.schema.json")))
import pyalex, habanero, pubchempy, jarvis, zenodo_get, huggingface_hub, mp_api  # noqa
print("clientes e filtros ok")
EOF
  py tools/data_sources/lab_data_model.py validate datasets/lab
}

t_core() {
  cd "$ROOT"
  py - <<'EOF'
import numpy as np, torch, fabio, miepython
from botorch.models import SingleTaskGP
from botorch.models.transforms import Normalize, Standardize
from botorch.fit import fit_gpytorch_mll
from botorch.acquisition.multi_objective.logei import qLogNoisyExpectedHypervolumeImprovement
from botorch.optim import optimize_acqf
from botorch.models.model_list_gp_regression import ModelListGP
from gpytorch.mlls import SumMarginalLogLikelihood
import ax, baybe, bofire, shap, dowhy, lmfit, pyFAI, ramanspy, Bgolearn  # noqa
torch.manual_seed(0)
X = torch.rand(8, 3, dtype=torch.double); Y = torch.stack([-(X - .3).pow(2).sum(-1), -(X - .7).pow(2).sum(-1)], -1)
m = ModelListGP(*[SingleTaskGP(X, Y[:, i:i+1], input_transform=Normalize(3), outcome_transform=Standardize(1)) for i in range(2)])
fit_gpytorch_mll(SumMarginalLogLikelihood(m.likelihood, m))
acq = qLogNoisyExpectedHypervolumeImprovement(m, ref_point=Y.min(0).values - .1, X_baseline=X)
cand, _ = optimize_acqf(acq, torch.tensor([[0.]*3, [1.]*3], dtype=torch.double), q=2, num_restarts=2, raw_samples=32)
img = fabio.open("datasets/xrd-ceo2-calibration/CeO2_1s_000012.ge3"); assert img.nframes == 5
q = miepython.efficiencies(complex(0.2, 3.3), 40, 0.52)  # AuNP ~40 nm em 520 nm
print("qLogNEHVI ok:", tuple(cand.shape), "| .ge3 frames:", img.nframes, "| Mie ok")
EOF
  # código do projeto (code/): espectral, caracterização, Designer (4 braços, LBO, novelty), causal, estatística;
  # inclui o laço completo com o laboratório simulado e as tabelas validadas
  py -m pytest code/tests -q -p no:cacheprovider -W ignore 2>&1 | tail -1
}

t_sdl() {
  local d; d="$(copy projects/bayesian-optimization/SDL)"; cd "$d"
  py - <<'EOF'
import os
from Functions import BayesianOptimization as BO
os.makedirs("save data", exist_ok=True)
for m in ("GPR", "BRMLPR_EGS"):
    r = BO.run(modeltype=m, policy="UCB", surrogate="levy", noise=0.1, runlength=6, folderpath=os.getcwd(),
               startRandSamples=3, dimensions=2).singleOptimization()
    print(m, "melhor Y:", min(r.Y))
EOF
}

t_bgolearn() {
  local d; d="$(copy projects/bayesian-optimization/Bgolearn/Template)"; cd "$d"
  py - <<'EOF'
import numpy as np, pandas as pd
from Bgolearn.BGOsampling import Bgolearn
d = pd.read_csv("data.csv"); grid = pd.DataFrame({"x": np.linspace(d.x.min(), d.x.max(), 50)})
m = Bgolearn().fit(d[["x"]], d["y"], grid, min_search=True, noise_std=0.05)
scores, x = m.EI(); print("EI ok, proposta:", np.ravel(x)[:3])
EOF
}

t_ramboau() {
  local d; d="$(copy projects/bayesian-optimization/RAMBOAU)"; cd "$d"
  py main.py --problem bstdiag --algo raqneirs --n-iter 1 --n-init-sample 6 --pop-size 20 --n-gen 3 --n-process 1 | tail -2
}

t_chem-mfbo() {
  local d; d="$(copy projects/multi-fidelity/chem-MFBO)"; cd "$d"
  py src/chem_mfbo/benchmark/real_problems.py --config-dir "$d/config_bench" --config-name cofs \
     seeds=1 budget=10 parallel=False >/dev/null 2>&1
  n=$(find benchmark -name "*.csv" | wc -l); [ "$n" -gt 0 ] && echo "cofs (MF/SF/random × EI/MES): $n CSVs de resultado"
}

t_bocode() {
  cd "$ROOT"
  py - <<'EOF2'
import torch, bocode
p = bocode.PressureVessel()
v, c = p.evaluate(p.scale(torch.rand(4, p.dim)))
a = bocode.AgNP()
va, _ = a.evaluate(a.candidates[:10])
print(f"PressureVessel ok {tuple(v.shape)}, viáveis {(c <= 0).all(1).sum().item()}/4 | AgNP ok, melhor dos 10: {va.max().item():.3f}")
EOF2
}

t_go-mace() {
  local d; d="$(copy projects/atomistic/GO-MACE-23/code)"; cd "$d"
  py - <<EOF
import numpy as np
from ase.build import graphene
from mace.calculators import MACECalculator
at = graphene(size=(3, 3, 1), vacuum=8.0)
at.calc = MACECalculator(model_paths="$ROOT/projects/atomistic/GO-MACE-23/models/fitting/potential/iter-12-final-model/go-mace-23.pt", device="cpu", default_dtype="float64")
e = at.get_potential_energy(); f = at.get_forces()
print(f"GO-MACE-23 ok: {len(at)} átomos, E/átomo = {e/len(at):.3f} eV, |F|max = {np.abs(f).max():.2e}")
EOF
}

t_text-mined() {
  local d; d="$(copy projects/literature-llm/text-mined-aunp-synthesis)"; cd "$d"
  "$ROOT/.venvs/$ENV/bin/jupyter" nbconvert --to notebook --execute --ExecutePreprocessor.timeout=900 \
     --output /tmp/aunp_nb_out.ipynb aunp_dataset_analysis.ipynb 2>&1 | tail -1
}

t_qubot-scripts() {
  local d; d="$(copy projects/self-driving-lab/qubot)"; cd "$d/scripts/shampoo"
  py data_analysis.py >/dev/null && echo "shampoo ok"
  if [ "${SMOKE_FULL:-0}" = 1 ]; then   # ajuste de todos os espectros de EIS: ~20 min
    cd "$d/scripts/electrolytes" && py data_analysis.py >/dev/null && echo "shampoo + electrolytes/EIS ok"
  fi
}

t_matdesinne() {
  # gerador cINN pré-treinado (MoS2_cinn.pkl): 1000 candidatos para gap alvo y0 = 0.5
  local d; d="$(copy projects/inverse-design/MatDesINNe/MatDesINNe_cINN)"; cd "$d/generation"
  py generator.py
  py -c "import numpy as np; x = np.loadtxt('gen_samps.csv', delimiter=','); assert x.shape[0] == 1000 and np.isfinite(x).all(); print('cINN ok:', x.shape, 'candidatos gerados')"
  cd "$d/localization" && py localization.py >/dev/null 2>&1
  py -c "import numpy as np; y = np.loadtxt('effective_samples_y_loc.csv', delimiter=','); print(f'cINN + localização ok: {len(y)} candidatos, gap previsto {y.mean():.3f} ± {y.std():.3f} (alvo 0.5)')"
}

rc=0
for ENV in "${names[@]}"; do
  if [ ! -x "$ROOT/.venvs/$ENV/bin/python" ]; then
    if [ "$install" = 1 ]; then "$ROOT/tools/setup_env.sh" "$ENV" >>"$LOG" 2>&1 || { echo "FALHOU  $ENV (instalação)"; rc=1; continue; }
    else echo "PULADO  $ENV (sem .venvs/$ENV; use --install)"; continue; fi
  fi
  start=$(date +%s)
  echo "=== $ENV" >>"$LOG"
  if out="$( (set -e; "t_$ENV") 2>>"$LOG")"; then
    echo "$out" >>"$LOG"; echo "OK      $ENV ($(( $(date +%s) - start )) s): $(echo "$out" | tail -1)"
  else
    echo "$out" >>"$LOG"; echo "FALHOU  $ENV — ver $LOG"; rc=1
  fi
done
exit $rc
