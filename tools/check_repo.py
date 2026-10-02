#!/usr/bin/env python3
"""Verificação estrutural do repositório (rápida, só biblioteca padrão). Complementa tools/smoke_test.sh.

Confere: arquivos Git LFS baixados (não ponteiros); links relativos dos .md; sintaxe dos .py e das células dos
notebooks em projects/, tools/ e code/; caminhos absolutos de máquina; especificações de environments/; external/
× tools/external_repos.lock.tsv; .git aninhado; caminhos de tools/data_sources/sources.tsv; e, com --regen, se os
arquivos gerados de datasets/ (reagentes, semente, modelo de dados) são reproduzíveis.

Uso:
    python tools/check_repo.py            # sai com código 1 se houver problema
    python tools/check_repo.py --regen    # também regenera e compara os dados gerados (~30 s)
"""
from __future__ import annotations

import argparse
import ast
import glob
import json
import os
import re
import subprocess
import sys
import urllib.parse
import warnings

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
problems: list[str] = []


def check(name: str, found: list[str]) -> None:
    print(f"{'OK ' if not found else 'ERR'} {name}" + (f": {len(found)}" if found else ""))
    for f in found[:15]:
        print("      ", f)
    problems.extend(found)


def lfs() -> list[str]:
    out = []
    for line in open(os.path.join(ROOT, ".gitattributes"), encoding="utf-8"):
        if "filter=lfs" not in line:
            continue
        p = os.path.join(ROOT, line.split()[0].lstrip("/"))
        if not os.path.exists(p):
            out.append(f"ausente: {p}")
        elif open(p, "rb").read(40).startswith(b"version https://git-lfs"):
            out.append(f"ponteiro LFS (rode git lfs pull): {os.path.relpath(p, ROOT)}")
    return out


def md_links() -> list[str]:
    out = []
    for f in glob.glob(os.path.join(ROOT, "**", "*.md"), recursive=True):
        rel = os.path.relpath(f, ROOT)
        if rel.startswith(("external/", ".venvs/", "outputs/")):
            continue
        for m in re.finditer(r"\]\(([^)\s]+)\)", open(f, encoding="utf-8", errors="replace").read()):
            t = m.group(1)
            if t.startswith(("http", "mailto:", "#")):
                continue
            t = urllib.parse.unquote(t.split("#")[0])
            if t and not os.path.exists(os.path.normpath(os.path.join(os.path.dirname(f), t))):
                out.append(f"{rel} -> {t}")
    return out


def py_syntax() -> list[str]:
    out = []
    warnings.simplefilter("ignore")
    for d in ("projects", "tools", "code"):
        for f in glob.glob(os.path.join(ROOT, d, "**", "*.py"), recursive=True):
            try:
                ast.parse(open(f, encoding="utf-8", errors="replace").read())
            except SyntaxError as e:
                out.append(f"{os.path.relpath(f, ROOT)}: {e}")
        for f in glob.glob(os.path.join(ROOT, d, "**", "*.ipynb"), recursive=True):
            try:
                nb = json.load(open(f, encoding="utf-8"))
            except ValueError as e:
                out.append(f"{os.path.relpath(f, ROOT)}: JSON inválido ({e})")
                continue
            for i, c in enumerate(nb.get("cells", [])):
                if c.get("cell_type") != "code":
                    continue
                src = "\n".join(l for l in "".join(c["source"]).split("\n") if not l.lstrip().startswith(("%", "!")))
                if re.fullmatch(r"\s*pip .*", src or ""):
                    continue
                try:
                    ast.parse(src)
                except SyntaxError as e:
                    out.append(f"{os.path.relpath(f, ROOT)} célula {i}: {e.msg}")
    return out


def abs_paths() -> list[str]:
    pat = re.compile(r"(/home/(?!user/AuGOSintesIA)[a-z_]+/|/Users/[A-Za-z]|[A-Z]:\\\\Users|/u/vld/)")
    out = []
    for d in ("projects", "tools", "code", "environments"):
        for f in glob.glob(os.path.join(ROOT, d, "**", "*"), recursive=True):
            if f.endswith((".py", ".sh", ".yaml", ".yml", ".cfg", ".in", ".txt", ".json")) and os.path.isfile(f) \
                    and os.path.getsize(f) < 2_000_000 and "/data/" not in f and f != os.path.abspath(__file__):
                for n, line in enumerate(open(f, encoding="utf-8", errors="replace"), 1):
                    if pat.search(line) and not line.lstrip().startswith("#"):
                        out.append(f"{os.path.relpath(f, ROOT)}:{n}: {line.strip()[:100]}")
    return out


def environments() -> list[str]:
    out, envdir = [], os.path.join(ROOT, "environments")
    for line in open(os.path.join(envdir, "envs.tsv"), encoding="utf-8"):
        if line.startswith("#") or not line.strip():
            continue
        name, typ, _py, spec, _d = line.rstrip("\n").split("\t")
        if not os.path.exists(os.path.join(envdir, spec)):
            out.append(f"{name}: especificação ausente {spec}")
        if typ == "uv" and not os.path.exists(os.path.join(envdir, f"{name}.lock.txt")):
            out.append(f"{name}: lock ausente")
        for f in (spec, f"{name}.lock.txt", f"{name}.windows.lock.txt"):
            p = os.path.join(envdir, f)
            if os.path.exists(p):
                for m in re.finditer(r"^(?:-e|-r)\s+(\S+)", open(p, encoding="utf-8").read(), re.M):
                    target = re.sub(r"\[.*\]$", "", m.group(1))
                    if not os.path.exists(os.path.join(envdir, target)):
                        out.append(f"{name}: {f} referencia {target}, que não existe")
        win = os.path.join(envdir, f"{name}.windows.lock.txt")
        if os.path.exists(win):        # o lock de Windows tem de fixar as MESMAS versões (tools/lock_windows.sh)
            pins = lambda f: dict(re.findall(r"^([A-Za-z0-9_.\-]+)==(\S+)", open(f, encoding="utf-8").read(), re.M))  # noqa: E731
            lin, w = pins(os.path.join(envdir, f"{name}.lock.txt")), pins(win)
            diff = sorted(k for k in set(lin) & set(w) if lin[k] != w[k])
            if diff:
                out.append(f"{name}: windows.lock.txt difere do lock de Linux em {diff[:5]} (rode tools/lock_windows.sh)")
    return out


def external() -> list[str]:
    out = []
    lock = [l.split("\t")[:2] for l in open(os.path.join(ROOT, "tools", "external_repos.lock.tsv"), encoding="utf-8")
            if not l.startswith("#") and l.strip()]
    want = {f"{c}/{n}" for c, n in lock}
    have = {os.path.relpath(p, os.path.join(ROOT, "external")) for p in glob.glob(os.path.join(ROOT, "external", "*", "*"))
            if os.path.isdir(p)}
    out += [f"no lock mas sem pasta: {x}" for x in sorted(want - have)]
    out += [f"pasta fora do lock: {x}" for x in sorted(have - want)]
    for dirpath, dirs, _f in os.walk(ROOT):
        if dirpath == ROOT:
            dirs[:] = [d for d in dirs if d not in (".git", ".venvs", "outputs")]
        if ".git" in dirs:
            out.append(f".git aninhado: {os.path.relpath(dirpath, ROOT)}")
            dirs.remove(".git")
    return out


def sources() -> list[str]:
    out = []
    lines = [l for l in open(os.path.join(ROOT, "tools", "data_sources", "sources.tsv"), encoding="utf-8")
             if not l.startswith("#")][1:]
    for l in lines:
        cols = l.rstrip("\n").split("\t")
        for p in cols[5].split("|"):
            if p not in ("-", "") and not os.path.exists(os.path.join(ROOT, p)):
                out.append(f"{cols[0]}: caminho local inexistente {p}")
    return out


def regen() -> list[str]:
    import hashlib
    targets = [f for d in ("datasets/reagents", "datasets/literature-seed", "datasets/data-model")
               for f in glob.glob(os.path.join(ROOT, d, "**", "*"), recursive=True)
               if os.path.isfile(f) and not f.endswith(("aliases.tsv", "README.md"))]
    digest = lambda: {f: hashlib.sha256(open(f, "rb").read()).hexdigest() for f in targets}  # noqa: E731
    before = digest()
    cmds = [["tools/data_sources/reagents.py", "build"], ["tools/data_sources/reagents.py", "cruse"],
            ["tools/data_sources/build_literature_seed.py"], ["tools/data_sources/lab_data_model.py", "templates"]]
    for c in cmds:
        subprocess.run([sys.executable, *c], cwd=ROOT, check=True, stdout=subprocess.DEVNULL,
                       env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    after = digest()
    return [f"regenerado difere do arquivo atual: {os.path.relpath(f, ROOT)}" for f in targets if before[f] != after[f]]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--regen", action="store_true")
    a = ap.parse_args()
    check("arquivos Git LFS presentes", lfs())
    check("links relativos dos .md", md_links())
    check("sintaxe Python (.py e notebooks)", py_syntax())
    check("caminhos absolutos de máquina", abs_paths())
    check("environments/ (especificações, locks, -e/-r)", environments())
    check("external/ × lock, .git aninhado", external())
    check("caminhos de tools/data_sources/sources.tsv", sources())
    if a.regen:
        check("dados gerados reproduzíveis", regen())
    print(f"\n{len(problems)} problema(s)")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
