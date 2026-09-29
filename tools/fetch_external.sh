#!/usr/bin/env bash
# Clona/atualiza os repositórios de external a partir de tools/external_repos.lock.tsv.
#
# Uso:
#   tools/fetch_external.sh                 # reclona todos na versão fixada (coluna "commit")
#   tools/fetch_external.sh --latest        # pega a versão mais recente e atualiza o lock
#   tools/fetch_external.sh --full botorch  # sem poda (inclui arquivos grandes/estudos de caso)
#   tools/fetch_external.sh --list          # só lista o que está no lock
#
# Poda padrão (reproduz o que está versionado): arquivos > 50 MB, olympus/case_studies,
# olympus/__dev_, shap/docs, shap/data, jarvis-tools/jarvis/{tests,examples}. Os .gitattributes aninhados com LFS são renomeados
# para .gitattributes.upstream para não quebrar o clone deste repositório.
set -euo pipefail
export GIT_LFS_SKIP_SMUDGE=1   # objetos LFS de terceiros não são baixados (ver LFS_OBJECTS_NOT_INCLUDED.txt)

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCK="$ROOT/tools/external_repos.lock.tsv"
DEST="$ROOT/external"

latest=0; full=0; list=0; names=()
for a in "$@"; do
  case "$a" in
    --latest) latest=1 ;;
    --full) full=1 ;;
    --list) list=1 ;;
    -h|--help) sed -n '2,13p' "$0"; exit 0 ;;
    *) names+=("$a") ;;
  esac
done

if [ "$list" = 1 ]; then grep -v '^#' "$LOCK" | cut -f1-3,6; exit 0; fi

tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
newlock="$tmp/lock.tsv"; head -1 "$LOCK" > "$newlock"

grep -v '^#' "$LOCK" | while IFS=$'\t' read -r cat name repo branch commit date; do
  if [ "${#names[@]}" -gt 0 ] && [[ ! " ${names[*]} " =~ " $name " ]]; then
    printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$cat" "$name" "$repo" "$branch" "$commit" "$date" >> "$newlock"; continue
  fi
  echo ">> $cat/$name ($repo)"
  src="$tmp/$name"
  bopt=(); [ "$branch" != "default" ] && bopt=(--branch "$branch")
  if [ "$latest" = 1 ]; then
    git clone -q --depth 1 "${bopt[@]}" "https://github.com/$repo" "$src"
  else
    git init -q "$src"
    git -C "$src" fetch -q --depth 1 "https://github.com/$repo" "$commit"
    git -C "$src" checkout -q FETCH_HEAD
  fi
  commit="$(git -C "$src" rev-parse HEAD)"; date="$(git -C "$src" log -1 --format=%cs)"
  if [ "$full" = 0 ]; then
    case "$name" in
      olympus) rm -rf "$src/case_studies" "$src/__dev_" ;;
      shap) rm -rf "$src/docs" "$src/data" ;;
      jarvis-tools) rm -rf "$src/jarvis/tests" "$src/jarvis/examples" ;;
    esac
    find "$src" -path "$src/.git" -prune -o -type f -size +50M -print -exec rm -f {} +
  fi
  find "$src" -path "$src/.git" -prune -o -name .gitattributes -print | while read -r ga; do
    if grep -q lfs "$ga"; then mv "$ga" "$ga.upstream"; fi
  done
  ptrs="$(grep -rl --exclude-dir=.git "^version https://git-lfs" "$src" 2>/dev/null | sort || true)"
  if [ -n "$ptrs" ]; then
    list="$src/LFS_OBJECTS_NOT_INCLUDED.txt"
    { echo "# Arquivos Git LFS do repositório original NÃO incluídos aqui (grandes demais)."
      echo "# Para obtê-los: git clone https://github.com/$repo && cd $(basename "$repo") && git lfs pull"
      echo "# caminho<TAB>tamanho_bytes<TAB>oid_sha256"; } > "$list"
    while read -r ptr; do
      printf '%s\t%s\t%s\n' "${ptr#$src/}" "$(grep '^size' "$ptr" | cut -d' ' -f2)" "$(grep '^oid' "$ptr" | cut -d: -f2)" >> "$list"
      rm -f "$ptr"
    done <<< "$ptrs"
  fi
  rm -rf "$src/.git" "$DEST/$cat/$name"; mkdir -p "$DEST/$cat"; mv "$src" "$DEST/$cat/$name"
  printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$cat" "$name" "$repo" "$branch" "$commit" "$date" >> "$newlock"
done

cp "$newlock" "$LOCK"
echo "Pronto. Lock atualizado em $LOCK"
