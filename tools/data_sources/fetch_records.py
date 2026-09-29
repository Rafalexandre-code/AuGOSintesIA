#!/usr/bin/env python3
"""Confere e baixa registros de Zenodo, Figshare e Hugging Face listados em tools/data_sources/sources.tsv.

Sem dependências além da biblioteca padrão. Precisa de rede para zenodo.org / api.figshare.com / huggingface.co
(o contêiner de desenvolvimento deste repositório só alcança GitHub e PyPI — rode na sua máquina).

Uso:
    python tools/data_sources/fetch_records.py list                         # registro de fontes e status
    python tools/data_sources/fetch_records.py check aunc-zenodo            # lista remota × cópia local (nome, tamanho, md5/sha256)
    python tools/data_sources/fetch_records.py check --all                  # todas as fontes zenodo/figshare/hf
    python tools/data_sources/fetch_records.py download gomace-zenodo       # baixa para outputs/records/<id>/ (não sobrescreve o repo)
    python tools/data_sources/fetch_records.py download zenodo:14066557 --dest /tmp/gomace --only aG_p6
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import urllib.parse
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
REGISTRY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sources.tsv")
UA = {"User-Agent": "AuGOSintesIA-fetch/1.0 (+https://github.com/Rafalexandre-code/AuGOSintesIA)"}


def load_registry() -> list[dict]:
    with open(REGISTRY, encoding="utf-8") as fh:
        return list(csv.DictReader([l for l in fh if not l.startswith("#")], delimiter="\t"))


def _get_json(url: str) -> dict | list:
    req = urllib.request.Request(url, headers={**UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def remote_files(kind: str, ident: str) -> list[dict]:
    """[{name, size, hash_type, hash, url}] do registro remoto."""
    if kind == "zenodo":
        rec = _get_json(f"https://zenodo.org/api/records/{ident}")
        out = []
        for f in rec.get("files", []):
            algo, _, h = (f.get("checksum") or ":").partition(":")
            out.append({"name": f["key"], "size": f.get("size"), "hash_type": algo, "hash": h,
                        "url": f["links"].get("self") or f["links"].get("content")})
        return out
    if kind == "figshare":
        rec = _get_json(f"https://api.figshare.com/v2/articles/{ident}")
        return [{"name": f["name"], "size": f.get("size"), "hash_type": "md5", "hash": f.get("computed_md5", ""),
                 "url": f["download_url"]} for f in rec.get("files", [])]
    if kind == "hf":
        out, stack = [], [""]
        while stack:
            sub = stack.pop()
            path = f"/{urllib.parse.quote(sub)}" if sub else ""
            for f in _get_json(f"https://huggingface.co/api/datasets/{ident}/tree/main{path}"):
                if f["type"] == "directory":
                    stack.append(f["path"])
                    continue
                lfs = f.get("lfs") or {}
                out.append({"name": f["path"], "size": lfs.get("size", f.get("size")),
                            "hash_type": "sha256" if lfs else "", "hash": lfs.get("oid", ""),
                            "url": f"https://huggingface.co/datasets/{ident}/resolve/main/{urllib.parse.quote(f['path'])}"})
        return out
    raise ValueError(f"tipo sem API de arquivos: {kind}")


def _digest(path: str, algo: str) -> str:
    h = hashlib.new(algo)
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _local_index(paths: list[str]) -> dict[str, list[str]]:
    idx: dict[str, list[str]] = {}
    for p in paths:
        full = os.path.join(ROOT, p)
        for dirpath, _dirs, files in os.walk(full):
            for f in files:
                idx.setdefault(f, []).append(os.path.join(dirpath, f))
    return idx


def resolve(spec: str) -> tuple[str, str, list[str], str]:
    """'aunc-zenodo' (id do registro) ou 'zenodo:15739032' -> (tipo, identificador, caminhos locais, rótulo)."""
    if ":" in spec and spec.split(":", 1)[0] in ("zenodo", "figshare", "hf"):
        kind, ident = spec.split(":", 1)
        return kind, ident, [], spec
    for r in load_registry():
        if r["id"] == spec:
            local = [] if r["caminho_local"] in ("-", "") else r["caminho_local"].split("|")
            return r["tipo"], r["identificador"], local, r["id"]
    sys.exit(f"fonte desconhecida: {spec} (veja 'list')")


def check(spec: str, hash_check: bool) -> int:
    kind, ident, local, label = resolve(spec)
    try:
        files = remote_files(kind, ident)
    except Exception as exc:  # noqa: BLE001
        print(f"[{label}] sem acesso a {kind}:{ident} — {exc}")
        return 2
    idx = _local_index(local)
    missing = 0
    print(f"[{label}] {kind}:{ident} — {len(files)} arquivo(s) remoto(s); local: {', '.join(local) or '-'}")
    for f in files:
        base = os.path.basename(f["name"])
        cands = idx.get(base, [])
        status = "AUSENTE localmente"
        for c in cands:
            if f["size"] is not None and os.path.getsize(c) != f["size"]:
                status = f"tamanho difere ({os.path.getsize(c)} ≠ {f['size']}): {os.path.relpath(c, ROOT)}"
                continue
            status = f"ok (tamanho) {os.path.relpath(c, ROOT)}"
            if hash_check and f["hash_type"] in ("md5", "sha256") and f["hash"]:
                ok = _digest(c, f["hash_type"]) == f["hash"]
                status = ("ok (" + f["hash_type"] + ") " if ok else "HASH DIFERE ") + os.path.relpath(c, ROOT)
            break
        missing += status.startswith("AUSENTE")
        print(f"  {f['name']:60} {f['size'] or '?':>12}  {status}")
    if missing:
        print(f"  -> {missing} arquivo(s) sem cópia local com o mesmo nome (podem estar extraídos de um .zip). "
              f"Baixe com: python tools/data_sources/fetch_records.py download {label}")
    return 0


def download(spec: str, dest: str | None, only: str | None) -> None:
    kind, ident, _local, label = resolve(spec)
    dest = dest or os.path.join(ROOT, "outputs", "records", label.replace(":", "_"))
    os.makedirs(dest, exist_ok=True)
    for f in remote_files(kind, ident):
        if only and only not in f["name"]:
            continue
        out = os.path.join(dest, f["name"])
        os.makedirs(os.path.dirname(out), exist_ok=True)
        if os.path.exists(out) and f["size"] is not None and os.path.getsize(out) == f["size"]:
            print(f"já existe: {out}")
            continue
        print(f"baixando {f['name']} ({f['size']} bytes) ...")
        req = urllib.request.Request(f["url"], headers=UA)
        with urllib.request.urlopen(req, timeout=600) as r, open(out + ".part", "wb") as fh:
            for chunk in iter(lambda: r.read(1 << 20), b""):
                fh.write(chunk)
        os.replace(out + ".part", out)
        if f["hash_type"] in ("md5", "sha256") and f["hash"] and _digest(out, f["hash_type"]) != f["hash"]:
            print(f"  ATENÇÃO: {f['hash_type']} não confere para {out}")
    print(f"pronto -> {dest}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    c = sub.add_parser("check")
    c.add_argument("source", nargs="?")
    c.add_argument("--all", action="store_true")
    c.add_argument("--hash", action="store_true", help="também compara md5/sha256 (lento para arquivos grandes)")
    d = sub.add_parser("download")
    d.add_argument("source")
    d.add_argument("--dest")
    d.add_argument("--only", help="baixa só arquivos cujo nome contém este texto")
    a = ap.parse_args()
    if a.cmd == "list":
        for r in load_registry():
            print(f"{r['id']:22} {r['tipo']:9} {r['status']:22} {r['caminho_local'][:60]}")
    elif a.cmd == "check":
        specs = [r["id"] for r in load_registry() if r["tipo"] in ("zenodo", "figshare", "hf")
                 and r["identificador"] not in ("", "-")] if a.all else [a.source]
        if not specs or specs == [None]:
            sys.exit("informe uma fonte ou --all")
        rc = max(check(s, a.hash) for s in specs)
        sys.exit(rc)
    else:
        download(a.source, a.dest, a.only)


if __name__ == "__main__":
    main()
