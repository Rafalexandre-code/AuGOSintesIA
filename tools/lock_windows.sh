#!/usr/bin/env bash
# Gera environments/<nome>.windows.lock.txt: as MESMAS versões do lock de Linux (<nome>.lock.txt usado como
# restrição), resolvidas para Windows x86-64 — usado por tools/setup_env.ps1. Rode depois de atualizar um lock.
#
# Uso:
#   tools/lock_windows.sh            # todos os ambientes uv
#   tools/lock_windows.sh core sdl   # só esses
# Ambientes que não resolvem para win_amd64 (GPU/triton, LAMMPS com MPI) ficam sem lock: no Windows, use WSL2.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/environments"
export SETUPTOOLS_SCM_PRETEND_VERSION_FOR_BOCODE="${SETUPTOOLS_SCM_PRETEND_VERSION_FOR_BOCODE:-0.0.0}"
command -v uv >/dev/null || { echo "precisa do uv (https://docs.astral.sh/uv/)"; exit 1; }

names=("$@")
[ ${#names[@]} -gt 0 ] || mapfile -t names < <(grep -v '^#' envs.tsv | awk -F'\t' '$2=="uv"{print $1}')
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
for n in "${names[@]}"; do
  py="$(grep -v '^#' envs.tsv | awk -F'\t' -v n="$n" '$1==n{print $3}')"
  [ -n "$py" ] || { echo "$n: ambiente desconhecido"; continue; }
  # linhas -e/caminhos locais não podem ser restrições: ficam só no .in
  grep -v -e '^-e ' -e 'file:' "$n.lock.txt" > "$tmp/$n.constraints.txt"
  ovr=(); [ -f "$n.override.txt" ] && ovr=(--override "$n.override.txt")
  if uv pip compile -q --python-platform x86_64-pc-windows-msvc --python-version "$py" "$n.in" \
       -c "$tmp/$n.constraints.txt" "${ovr[@]}" -o "$n.windows.lock.txt" 2> "$tmp/$n.log"; then
    sed -i "s#$tmp/$n.constraints.txt#$n.lock.txt (sem as linhas -e)#g" "$n.windows.lock.txt"
    echo "$n: ok"
  else
    rm -f "$n.windows.lock.txt"
    echo "$n: sem lock para Windows — $(grep -m1 -e 'Because' -e 'error' "$tmp/$n.log" | cut -c1-140)"
  fi
done
