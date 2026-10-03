#!/usr/bin/env python3
"""Envia uma versão do depósito (build_deposit.py) ao Zenodo e obtém o DOI (§4.17, Atividade 5.1).

RODAR LOCALMENTE: o contêiner de nuvem não alcança zenodo.org. Fluxo da API REST do Zenodo:
  1. cria o depósito (ou, com --concept, uma NOVA VERSÃO do registro existente — o "concept DOI" fica o mesmo);
  2. envia os arquivos para o bucket do depósito;
  3. grava os metadados do .zenodo.json da versão (título, autores, licença, identificadores relacionados);
  4. só com --publish, publica (irreversível: um DOI publicado não se apaga) e grava o DOI em
     outputs/deposit/zenodo_<versão>.json.
Por padrão é um ENSAIO (--dry-run implícito): valida os metadados e lista o que seria enviado, sem rede.
Teste antes no sandbox (--sandbox, token de sandbox.zenodo.org). O token vem SÓ de ZENODO_TOKEN (nunca de
argumento, para não ficar no histórico do shell); escopos: deposit:write e deposit:actions.

Uso:
    python tools/data_sources/build_deposit.py --version 0.1.0
    python tools/data_sources/zenodo_upload.py outputs/deposit/GO-AuNP-Autonomous-Design-v0.1.0      # ensaio
    ZENODO_TOKEN=... python tools/data_sources/zenodo_upload.py <pasta> --sandbox --send               # rascunho
    ZENODO_TOKEN=... python tools/data_sources/zenodo_upload.py <pasta> --send --publish [--concept 123456]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
REQUIRED = ("title", "upload_type", "description", "creators", "license", "access_right")
HOSTS = {False: "https://zenodo.org", True: "https://sandbox.zenodo.org"}


def load_metadata(folder: str) -> dict:
    p = os.path.join(folder, ".zenodo.json")
    if not os.path.exists(p):
        raise SystemExit(f"{folder}: sem .zenodo.json — gere a pasta com build_deposit.py")
    meta = json.load(open(p, encoding="utf-8"))
    missing = [k for k in REQUIRED if not meta.get(k)]
    if missing:
        raise SystemExit(f".zenodo.json sem {missing}")
    bad = [c for c in meta["creators"] if "," not in c.get("name", "")]
    if bad:
        raise SystemExit(f"creators no formato 'Sobrenome, Nome': {bad}")
    if not meta.get("version"):
        raise SystemExit(".zenodo.json sem version (build_deposit.py --version grava)")
    return meta


def files_to_send(folder: str) -> list[str]:
    """O .zip da versão (uma pasta vira um arquivo; o Zenodo não guarda árvore de diretórios) e o MANIFEST."""
    z = folder.rstrip("/") + ".zip"
    out = [z] if os.path.exists(z) else []
    man = os.path.join(folder, "MANIFEST.tsv")
    if os.path.exists(man):
        out.append(man)
    if not out:
        raise SystemExit(f"nada a enviar: falta {z}")
    return out


def _call(method: str, url: str, token: str, body=None, data: bytes | None = None, ctype: str = "application/json"):
    """Uma chamada à API; isolada para os testes trocarem por um falso."""
    sep = "&" if "?" in url else "?"
    req = urllib.request.Request(f"{url}{sep}access_token={urllib.parse.quote(token)}", method=method,
                                 data=data if data is not None else (json.dumps(body).encode() if body is not None
                                                                     else None),
                                 headers={"Content-Type": ctype})
    with urllib.request.urlopen(req, timeout=600) as r:
        txt = r.read().decode() or "{}"
    return json.loads(txt)


def upload(folder: str, token: str, sandbox: bool = False, concept: str | None = None, publish: bool = False,
           call=_call) -> dict:
    meta = load_metadata(folder)
    api = HOSTS[sandbox] + "/api/deposit/depositions"
    if concept:
        r = call("POST", f"{api}/{concept}/actions/newversion", token, body={})
        draft_url = r["links"]["latest_draft"]
        dep = call("GET", draft_url, token)
        for f in dep.get("files", []):                         # a nova versão herda os arquivos da anterior
            call("DELETE", f"{draft_url}/files/{f['id']}", token)
    else:
        dep = call("POST", api, token, body={})
    dep_id, bucket = dep["id"], dep["links"]["bucket"]
    for path in files_to_send(folder):
        with open(path, "rb") as fh:
            call("PUT", f"{bucket}/{urllib.parse.quote(os.path.basename(path))}", token, data=fh.read(),
                 ctype="application/octet-stream")
    call("PUT", f"{api}/{dep_id}", token, body={"metadata": meta})
    out = {"id": dep_id, "sandbox": sandbox, "version": meta["version"], "published": False,
           "html": dep.get("links", {}).get("html", "")}
    if publish:
        pub = call("POST", f"{api}/{dep_id}/actions/publish", token, body={})
        out.update({"published": True, "doi": pub.get("doi"), "conceptdoi": pub.get("conceptdoi"),
                    "html": pub.get("links", {}).get("html", out["html"])})
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder", help="pasta gerada por build_deposit.py (o .zip ao lado é o que sobe)")
    ap.add_argument("--send", action="store_true", help="envia de fato (sem isto: só o ensaio)")
    ap.add_argument("--sandbox", action="store_true", help="sandbox.zenodo.org (teste)")
    ap.add_argument("--concept", help="id do registro existente: cria uma nova versão dele")
    ap.add_argument("--publish", action="store_true", help="publica (irreversível) e devolve o DOI")
    a = ap.parse_args()
    meta = load_metadata(a.folder)
    files = files_to_send(a.folder)
    print(f"{meta['title'][:90]}… v{meta['version']} ({meta['license']}, {meta['access_right']})")
    for f in files:
        print(f"  {os.path.basename(f)}  {os.path.getsize(f) / 1e6:.1f} MB")
    if not a.send:
        print("ENSAIO: nada enviado. Use --send (e --sandbox para testar).")
        return
    token = os.environ.get("ZENODO_TOKEN")
    if not token:
        raise SystemExit("defina ZENODO_TOKEN (zenodo.org → Applications → Personal access tokens)")
    if a.publish and not a.sandbox:
        print("ATENÇÃO: publicar no Zenodo é irreversível (o DOI fica para sempre).")
    r = upload(a.folder, token, a.sandbox, a.concept, a.publish)
    dest = os.path.join(ROOT, "outputs", "deposit", f"zenodo_{meta['version']}{'_sandbox' * a.sandbox}.json")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    json.dump(r, open(dest, "w", encoding="utf-8"), indent=1)
    print(json.dumps(r, indent=1))
    if r.get("doi"):
        print(f"DOI {r['doi']} — acrescente ao CITATION.cff (campo doi) e ao README do depósito.")


if __name__ == "__main__":
    sys.exit(main())
