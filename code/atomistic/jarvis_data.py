#!/usr/bin/env python3
"""Acesso aos dados e modelos do JARVIS (NIST): JARVIS-DFT, JARVIS-FF, JARVIS-Leaderboard e modelos ALIGNN/ALIGNN-FF.

Onde há rede para o figshare, usa o próprio jarvis-tools (`jarvis.db.figshare.data`), com o cache em
$ATOMGPTLAB_CACHE (padrão ~/.cache/atomgptlab). Sem rede (ex.: o contêiner de nuvem deste projeto, que só alcança
GitHub e PyPI), monta uma **reconstrução offline do JARVIS-DFT 3D** a partir do que está versionado em
external/jarvis/:
  - estruturas: as 75 993 entradas de jdft_3d-12-12-2022 em texto (external/jarvis/atomgpt/atomgpt/data/
    chemnlp_new_desc.json.zip; parâmetros de rede com 0,01 Å e coordenadas fracionárias com 0,001);
  - propriedades: os alvos dos benchmarks dft_3d_* do JARVIS-Leaderboard (divisões train/val/test juntas).
A reconstrução é marcada em cada registro (`reconstrucao_offline=True`), fica numa pasta própria
(outputs/jarvis_offline_cache, ou $JARVIS_OFFLINE_CACHE) e só é usada por quem chama `use_offline_cache()`. Ela não
substitui o arquivo original: faltam propriedades sem benchmark (ficam "na", como no próprio JARVIS) e a precisão
geométrica é menor. Para produção, rode `download` numa máquina com acesso ao figshare.

Uso:
    python code/atomistic/jarvis_data.py status
    python code/atomistic/jarvis_data.py build-offline                 # dft_3d + vacancydb + surfacedb (≈1 min)
    python code/atomistic/jarvis_data.py search --elements Au          # entradas com as propriedades disponíveis
    python code/atomistic/jarvis_data.py leaderboard dft_3d_formation_energy_peratom --out fe.csv
    python code/atomistic/jarvis_data.py jff --elements Au             # JARVIS-FF (dados LAMMPS versionados)
    python code/atomistic/jarvis_data.py download --datasets dft_3d dft_2d jff vacancydb surfacedb \
           --alignn-ff v12.2.2024_dft_3d_307k --slakonet slakonet_v1a --hf knc6/atomgpt_mistral_tc_supercon
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import socket
import sys
import zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
JARVIS_EXT = os.path.join(ROOT, "external", "jarvis")
LEADERBOARD = os.path.join(JARVIS_EXT, "jarvis_leaderboard", "jarvis_leaderboard", "benchmarks")
ATOMGPT_STRUCTS = os.path.join(JARVIS_EXT, "atomgpt", "atomgpt", "data", "chemnlp_new_desc.json.zip")
JFF_LEGACY = os.path.join(JARVIS_EXT, "JARVIS-FF", "data.json")
DFT3D_TAG = "jdft_3d-12-12-2022.json"   # mesmo nome do arquivo do figshare (jarvis.db.figshare.get_db_info)


def offline_cache_dir() -> str:
    return os.environ.get("JARVIS_OFFLINE_CACHE", os.path.join(ROOT, "outputs", "jarvis_offline_cache"))


def use_offline_cache() -> str:
    """Aponta o jarvis-tools (e quem o usa: CHIPS-FF, ALIGNN…) para a reconstrução offline; devolve a pasta."""
    d = offline_cache_dir()
    os.environ["ATOMGPTLAB_CACHE"] = d
    return d


def figshare_reachable(timeout: float = 4.0) -> bool:
    """True se o figshare responde (TCP pelo proxy/rede); usado para decidir entre dados reais e reconstrução."""
    import requests

    try:
        requests.head("https://ndownloader.figshare.com", timeout=timeout)
        return True
    except (requests.RequestException, socket.error):
        return False


# ----------------------------------------------------------------------------------------------- Leaderboard
def leaderboard_files(prefix: str = "") -> dict[str, str]:
    """{"<Categoria>/<Tarefa>/<nome>": caminho do .json.zip} dos benchmarks versionados (podados: > 5 MB ficam de
    fora). O mesmo nome pode existir em tarefas diferentes (ex.: dft_3d_optb88vdw_bandgap em regressão e em
    classificação), por isso a chave inclui a tarefa."""
    out = {}
    for p in glob.glob(os.path.join(LEADERBOARD, "*", "*", "*.json.zip")):
        key = os.path.relpath(p, LEADERBOARD)[: -len(".json.zip")]
        if os.path.basename(key).startswith(prefix):
            out[key] = p
    return dict(sorted(out.items()))


def resolve_leaderboard(name: str) -> str:
    """Aceita a chave completa ou só o nome; havendo mais de um, prefere AI/SinglePropertyPrediction."""
    files = leaderboard_files()
    if name in files:
        return files[name]
    hits = [k for k in files if os.path.basename(k) == name]
    if not hits:
        raise KeyError(f"benchmark '{name}' não está em {LEADERBOARD} (podado ou inexistente)")
    hits.sort(key=lambda k: not k.startswith("AI/SinglePropertyPrediction/"))
    return files[hits[0]]


def load_leaderboard(name: str) -> dict[str, dict]:
    """{'train': {id: alvo}, 'val': …, 'test': …} de um benchmark do JARVIS-Leaderboard."""
    with zipfile.ZipFile(resolve_leaderboard(name)) as z:
        return json.loads(z.read(z.namelist()[0]))


def leaderboard_frame(name: str):
    import pandas as pd

    rows = [(split, i, v) for split, d in load_leaderboard(name).items() for i, v in d.items()]
    return pd.DataFrame(rows, columns=["split", "id", "target"])


# ------------------------------------------------------------------------------- reconstrução do JARVIS-DFT
def parse_atomgpt_structure(text: str):
    """Converte o bloco de estrutura do AtomGPT ("a b c#\\nα β γ@\\nEl x y z&…") num jarvis Atoms."""
    from jarvis.core.atoms import Atoms
    from jarvis.core.lattice import Lattice

    block = text.split("\n*\n")[-1].strip()
    abc, rest = block.split("#", 1)
    ang, sites = rest.split("@", 1)
    a, b, c = (float(x) for x in abc.split())
    al, be, ga = (float(x) for x in ang.split())
    elements, coords = [], []
    for s in sites.split("&"):
        f = s.split()
        if len(f) == 4:
            elements.append(f[0])
            coords.append([float(x) for x in f[1:]])
    lat = Lattice.from_parameters(a, b, c, al, be, ga).matrix
    return Atoms(lattice_mat=lat, coords=coords, elements=elements, cartesian=False)


def _to_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return v


def build_offline_dft3d(cache: str | None = None, limit: int | None = None) -> str:
    """Grava <cache>/jarvis_data/jdft_3d-12-12-2022.json.zip com a reconstrução; devolve o caminho."""
    cache = cache or offline_cache_dir()
    props: dict[str, dict[str, object]] = {}
    # só regressão sobre o dft_3d (ES/EXP comparam métodos; SinglePropertyClass são rótulos derivados)
    for name in leaderboard_files("dft_3d_"):
        if not name.startswith("AI/SinglePropertyPrediction/"):
            continue
        key = os.path.basename(name)[len("dft_3d_"):]
        try:
            d = load_leaderboard(name)
        except (KeyError, ValueError):
            continue
        if not all(isinstance(v, (int, float, str)) for split in d.values() for v in list(split.values())[:3]):
            continue   # conjuntos com estruturas/espectros como alvo (ex.: AtomGen) não são propriedades escalares
        for split in d.values():
            for jid, v in split.items():
                props.setdefault(jid, {})[key] = _to_float(v)
    with zipfile.ZipFile(ATOMGPT_STRUCTS) as z:
        entries = json.loads(z.read(z.namelist()[0]))
    ids = {e["id"] for e in entries}
    # só propriedades indexadas pelos JVASP do dft_3d (os benchmarks chipsff_* usam outros identificadores)
    keys = sorted({k for jid, p in props.items() if jid in ids for k in p})
    out = []
    for e in entries[:limit]:
        at = parse_atomgpt_structure(e["desc"])
        p = props.get(e["id"], {})
        rec = {"jid": e["id"], "atoms": at.to_dict(), "formula": at.composition.reduced_formula,
               "nelements": len(set(at.elements)), "reconstrucao_offline": True}
        rec.update({k: p.get(k, "na") for k in keys})
        out.append(rec)
    dest = os.path.join(cache, "jarvis_data")
    os.makedirs(dest, exist_ok=True)
    path = os.path.join(dest, DFT3D_TAG + ".zip")
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(DFT3D_TAG, json.dumps(out))
    with open(os.path.join(dest, "LEIA-ME.txt"), "w", encoding="utf-8") as fh:
        fh.write("Reconstrução OFFLINE do JARVIS-DFT 3D (jdft_3d-12-12-2022), feita por code/atomistic/jarvis_data.py\n"
                 "a partir de external/jarvis/{atomgpt (estruturas), jarvis_leaderboard (propriedades)}.\n"
                 f"{len(out)} estruturas; propriedades: {', '.join(keys)}.\n"
                 "NÃO é o arquivo original do figshare: use-o só sem rede. Original: "
                 "python code/atomistic/jarvis_data.py download --datasets dft_3d\n")
    return path


def build_offline_defects(cache: str | None = None) -> list[str]:
    """vacancydb e surfacedb offline (usados pelo CHIPS-FF para comparar vacâncias e superfícies com DFT), a partir
    dos benchmarks vacancydb_* e dft_3d_chipsff_surf_en do Leaderboard (mesmos identificadores do figshare)."""
    from jarvis.db.figshare import get_db_info

    info = get_db_info()
    dest = os.path.join(cache or offline_cache_dir(), "jarvis_data")
    os.makedirs(dest, exist_ok=True)
    vac, seen = [], set()
    for name in leaderboard_files("vacancydb_"):
        if "train_test" in name:
            continue
        for split in load_leaderboard(name).values():
            for vid, ef in split.items():
                if vid not in seen and vid.startswith("JVASP-"):
                    seen.add(vid)
                    vac.append({"id": vid, "jid": vid.split("_")[0], "ef": float(ef), "reconstrucao_offline": True})
    surf = [{"name": sid, "surf_en": float(v), "reconstrucao_offline": True}
            for split in load_leaderboard("dft_3d_chipsff_surf_en").values() for sid, v in split.items()]
    out = []
    for key, recs in (("vacancydb", vac), ("surfacedb", surf)):
        tag = info[key][1]
        path = os.path.join(dest, tag + ".zip")
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr(tag, json.dumps(recs))
        out.append(path)
    return out


def real_cache_dir() -> str:
    """Cache do jarvis-tools para os arquivos ORIGINAIS (ignora a pasta da reconstrução offline)."""
    d = os.environ.get("ATOMGPTLAB_CACHE", "")
    if not d or os.path.abspath(d) == os.path.abspath(offline_cache_dir()):
        d = os.path.join(os.path.expanduser("~"), ".cache", "atomgptlab")
    return d


def dft3d(prefer: str = "auto"):
    """Lista de registros do JARVIS-DFT 3D. prefer: 'auto' (original se estiver no cache ou o figshare responder;
    senão a reconstrução offline), 'original' ou 'offline'."""
    real = os.path.join(real_cache_dir(), "jarvis_data")
    if prefer == "original" or (prefer == "auto" and (os.path.isfile(os.path.join(real, DFT3D_TAG + ".zip"))
                                                      or figshare_reachable())):
        from jarvis.db.figshare import data

        os.makedirs(real, exist_ok=True)
        return data("dft_3d", store_dir=real)
    path = os.path.join(offline_cache_dir(), "jarvis_data", DFT3D_TAG + ".zip")
    if not os.path.isfile(path):
        print("figshare inacessível: montando a reconstrução offline do dft_3d…", file=sys.stderr)
        build_offline_dft3d()
    with zipfile.ZipFile(path) as z:
        return json.loads(z.read(DFT3D_TAG))


def search(records, elements=(), only=False, max_atoms=None, require=()):
    """Filtra registros por elementos (todos presentes; only=True: nenhum outro), tamanho e propriedades não-'na'."""
    els = set(elements)
    out = []
    for r in records:
        e = set(r["atoms"]["elements"])
        if (els and not els <= e) or (only and e != els):
            continue
        if max_atoms and len(r["atoms"]["elements"]) > max_atoms:
            continue
        if any(r.get(k, "na") == "na" for k in require):
            continue
        out.append(r)
    return out


# ------------------------------------------------------------------------------------------------ JARVIS-FF
def jff_legacy():
    """Dados LAMMPS do JARVIS-FF versionados (knc6/JARVIS-FF/data.json): energia, Bv, Gv, matriz elástica por
    potencial. O banco atual (jff-7-24-2021, com fônons/superfícies/vacâncias) vem por `download --datasets jff`."""
    import pandas as pd

    with open(JFF_LEGACY, encoding="utf-8") as fh:
        rows = json.load(fh)
    df = pd.DataFrame(rows)
    for c in ("energy", "totenergy", "Bv", "Gv", "ehull"):
        if c in df:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


# ---------------------------------------------------------------------------------------- download (com rede)
def download(datasets=(), alignn=(), alignn_ff=(), slakonet=(), hf=()):
    """Baixa conjuntos do figshare e modelos pré-treinados para os caches do jarvis-tools/ALIGNN/SlaKoNet e do
    Hugging Face (AtomGPT). Rodar numa máquina com rede; depois os scripts funcionam offline."""
    from jarvis.db.figshare import data

    for name in datasets:
        print(f"[dados] {name}: {len(data(name))} registros")
    if alignn:
        from alignn.pretrained import get_figshare_model

        for name in alignn:
            get_figshare_model(name)
            print(f"[ALIGNN] {name} ok")
    if alignn_ff:
        from alignn.ff.ff import get_figshare_model_ff

        for name in alignn_ff:
            print(f"[ALIGNN-FF] {name}: {get_figshare_model_ff(model_name=name)}")
    for name in slakonet:
        from slakonet.optim import default_model

        default_model(model_name=name)
        print(f"[SlaKoNet] {name} ok")
    for repo in hf:
        from huggingface_hub import snapshot_download

        print(f"[Hugging Face] {repo}: {snapshot_download(repo)}")


def status() -> dict:
    real = real_cache_dir()
    st = {
        "figshare_acessivel": figshare_reachable(),
        "cache_jarvis": real,
        "conjuntos_no_cache": sorted(os.path.basename(p)[:-4] for p in glob.glob(os.path.join(real, "jarvis_data", "*.zip"))),
        "modelos_alignn_ff": sorted(os.path.basename(p) for p in glob.glob(os.path.join(real, "alignn_ff", "*"))),
        "reconstrucao_offline": os.path.isfile(os.path.join(offline_cache_dir(), "jarvis_data", DFT3D_TAG + ".zip")),
        "benchmarks_leaderboard_versionados": len(leaderboard_files()),
        "estruturas_atomgpt": os.path.isfile(ATOMGPT_STRUCTS),
        "jarvis_ff_legado": os.path.isfile(JFF_LEGACY),
    }
    return st


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    b = sub.add_parser("build-offline")
    b.add_argument("--limit", type=int)
    s = sub.add_parser("search")
    s.add_argument("--elements", nargs="*", default=[])
    s.add_argument("--only", action="store_true", help="só esses elementos")
    s.add_argument("--max-atoms", type=int)
    s.add_argument("--require", nargs="*", default=[], help="propriedades que não podem ser 'na'")
    s.add_argument("--prefer", choices=["auto", "original", "offline"], default="auto")
    s.add_argument("--out")
    lb = sub.add_parser("leaderboard")
    lb.add_argument("name", nargs="?")
    lb.add_argument("--out")
    j = sub.add_parser("jff")
    j.add_argument("--elements", nargs="*", default=[])
    d = sub.add_parser("download")
    d.add_argument("--datasets", nargs="*", default=[])
    d.add_argument("--alignn", nargs="*", default=[], help="ex.: jv_formation_energy_peratom_alignn")
    d.add_argument("--alignn-ff", nargs="*", default=[], help="ex.: v12.2.2024_dft_3d_307k")
    d.add_argument("--slakonet", nargs="*", default=[], help="ex.: slakonet_v1a (parâmetros TB da tabela periódica)")
    d.add_argument("--hf", nargs="*", default=[], help="modelos AtomGPT, ex.: knc6/atomgpt_mistral_tc_supercon")
    a = ap.parse_args(argv)

    if a.cmd == "status":
        print(json.dumps(status(), indent=2, ensure_ascii=False))
    elif a.cmd == "build-offline":
        print(build_offline_dft3d(limit=a.limit))
        print("\n".join(build_offline_defects()))
    elif a.cmd == "search":
        import pandas as pd

        recs = search(dft3d(a.prefer), a.elements, a.only, a.max_atoms, a.require)
        cols = ["jid", "formula", "formation_energy_peratom", "optb88vdw_bandgap", "ehull", "bulk_modulus_kv",
                "exfoliation_energy"]
        df = pd.DataFrame([{c: r.get(c, "na") for c in cols} | {"natoms": len(r["atoms"]["elements"])} for r in recs])
        print(f"{len(df)} entradas")
        print(df.head(30).to_string(index=False))
        if a.out:
            df.to_csv(a.out, index=False)
    elif a.cmd == "leaderboard":
        if not a.name:
            for n, p in leaderboard_files().items():
                print(f"{n}\t{os.path.relpath(p, LEADERBOARD)}")
            return
        df = leaderboard_frame(a.name)
        print(df.groupby("split").size().to_string())
        if a.out:
            df.to_csv(a.out, index=False)
    elif a.cmd == "jff":
        df = jff_legacy()
        if a.elements:
            df = df[df["composition"].str.contains("|".join(a.elements))]
        print(df[["composition", "forcefield", "energy", "Bv", "Gv", "mpid"]].to_string(index=False, max_rows=40))
    elif a.cmd == "download":
        download(a.datasets, a.alignn, a.alignn_ff, a.slakonet, a.hf)


if __name__ == "__main__":
    main()
