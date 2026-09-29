#!/usr/bin/env bash
# Clona/atualiza os repositórios de Data/external a partir de tools/external_repos.lock.tsv.
#
# Uso:
#   tools/fetch_external.sh                 # reclona todos na versão fixada (coluna "commit")
#   tools/fetch_external.sh --latest        # pega a versão mais recente e atualiza o lock
#   tools/fetch_external.sh --full botorch  # sem poda (inclui arquivos grandes/estudos de caso)
#   tools/fetch_external.sh --list          # só lista o que está no lock
#
# Poda padrão (reproduz o que está versionado): arquivos > 50 MB, olympus/case_studies,
# olympus/__dev_, shap/docs, shap/data. Os .gitattributes aninhados com LFS são renomeados
# para .gitattributes.upstream para não quebrar o clone deste repositório.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCK="$ROOT/tools/external_repos.lock.tsv"
DEST="$ROOT/Data/external"

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
    esac
    find "$src" -path "$src/.git" -prune -o -type f -size +50M -print -exec rm -f {} +
  fi
  find "$src" -path "$src/.git" -prune -o -name .gitattributes -print | while read -r ga; do
    grep -q lfs "$ga" && mv "$ga" "$ga.upstream"
  done
  rm -rf "$src/.git" "$DEST/$cat/$name"; mkdir -p "$DEST/$cat"; mv "$src" "$DEST/$cat/$name"
  printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$cat" "$name" "$repo" "$branch" "$commit" "$date" >> "$newlock"
done

cp "$newlock" "$LOCK"
echo "Pronto. Lock atualizado em $LOCK"
