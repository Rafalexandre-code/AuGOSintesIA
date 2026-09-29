#!/usr/bin/env bash
# Cria um ambiente isolado por subprojeto (as dependências são incompatíveis entre si).
#
# Uso:
#   tools/setup_env.sh --list            # lista os ambientes (environments/envs.tsv)
#   tools/setup_env.sh sdl               # cria .venvs/sdl com as versões fixadas (environments/sdl.lock.txt)
#   tools/setup_env.sh core --latest     # usa environments/core.in (versões mais recentes do PyPI)
#   source .venvs/sdl/bin/activate       # ativa (ou: conda activate <nome> para os de tipo conda)
#
# Requer uv (https://docs.astral.sh/uv/, recomendado: também baixa a versão de Python certa)
# ou, na falta dele, o python3.X correspondente + venv/pip. Ambientes "conda" usam mamba/conda.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENVDIR="$ROOT/environments"
TABLE="$ENVDIR/envs.tsv"
export SETUPTOOLS_SCM_PRETEND_VERSION_FOR_BOCODE="${SETUPTOOLS_SCM_PRETEND_VERSION_FOR_BOCODE:-0.0.0}"

if [ $# -eq 0 ] || [ "$1" = "-h" ] || [ "$1" = "--help" ]; then sed -n '2,12p' "$0"; exit 0; fi
if [ "$1" = "--list" ]; then
  grep -v '^#' "$TABLE" | awk -F'\t' '{printf "%-14s %-6s py%-5s %s\n", $1, $2, $3, $5}'; exit 0
fi

name="$1"; latest=0; [ "${2:-}" = "--latest" ] && latest=1
line="$(grep -v '^#' "$TABLE" | awk -F'\t' -v n="$name" '$1==n')"
[ -n "$line" ] || { echo "Ambiente desconhecido: $name (veja --list)"; exit 1; }
IFS=$'\t' read -r _ typ py spec desc <<< "$line"
cd "$ENVDIR"   # caminhos relativos (-r/-e ../Data/...) são resolvidos a partir daqui

if [ "$typ" = "conda" ]; then
  tool="$(command -v mamba || command -v micromamba || command -v conda || true)"
  [ -n "$tool" ] || { echo "Precisa de conda/mamba para '$name' ($spec)"; exit 1; }
  "$tool" env create -n "$name" -f "$spec"
  echo "Pronto: conda activate $name"; exit 0
fi

req="$name.lock.txt"; [ "$latest" = 1 ] && req="$spec"
venv="$ROOT/.venvs/$name"
if command -v uv >/dev/null; then
  uv venv -p "$py" "$venv"
  uv pip install --python "$venv/bin/python" -r "$req"
else
  pybin="$(command -v "python$py" || true)"
  [ -n "$pybin" ] || { echo "Instale uv ou python$py"; exit 1; }
  "$pybin" -m venv "$venv"
  "$venv/bin/pip" install -U pip
  "$venv/bin/pip" install -r "$req"
fi
echo "Pronto ($desc): source .venvs/$name/bin/activate"
