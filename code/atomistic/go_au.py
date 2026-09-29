#!/usr/bin/env python3
"""Design inverso atomístico GO–Au com as ferramentas do JARVIS (e o gerador de GO do GO-MACE-23).

Pergunta: que química de GO (razão O/C e fração de hidroxilas vs. epóxidos) ancora o Au com a força desejada?
A energia de adsorção de Au_n no GO controla a nucleação e o crescimento das AuNPs sobre a folha (sítios de ancoragem ×
coalescência), e o resultado entra como descritor físico do lote de GO no AuNP Designer (go_navigator).

Fluxo no estilo JARVIS (gerar → triar com ML → validar com FF/DFT):
  1. `screen`  — gera GO (GO-MACE-23: O/C, fração OH) e calcula E_ads(Au_n) com um MLFF universal (ALIGNN-FF do
                 JARVIS-ML, MACE-MP-0, CHGNet, SevenNet), com réplicas por composição; grava estruturas (POSCAR),
                 descritores CFID (JARVIS-Tools) e, opcionalmente, os quadros das relaxações (para treinar ALIGNN-FF).
  2. `design`  — otimização bayesiana (BoTorch, GP com ruído das réplicas + qLogNEI) no espaço (O/C, f_OH) até
                 E_ads alvo (--target) ou ancoragem máxima.
  3. `train-alignn`    — treina o ALIGNN (JARVIS-ML) estrutura → E_ads com os dados do `screen` (modelo direto).
     `train-alignn-ff` — treina um ALIGNN-FF específico de GO–Au com os quadros das relaxações.
  4. `predict` — triagem rápida de composições novas com o ALIGNN treinado (sem MLFF); os melhores seguem para o MLFF.
  5. `interface` — interface Au(111)/grafite(001) com o InterMat (JARVIS) e energia de adesão W_ad.
Validação do próprio MLFF contra DFT: jarvis_ff.py (Au) e chipsff_run.py (CHIPS-FF).

As energias vêm de MLFFs universais (DFT de cristais): servem para ordenar composições; confirme os finalistas com DFT
(Quantum ESPRESSO/VASP via jarvis.tasks) antes de usá-las como número. Saídas em outputs/atomistic/.

Uso:
    python code/atomistic/go_au.py screen --oc 0.1 0.2 0.3 --foh 0.0 0.5 1.0 --reps 2 --calc mace-mp-d3
    python code/atomistic/go_au.py design --target -1.5 --n-init 6 --n-iter 10 --calc mace-mp-d3
    python code/atomistic/go_au.py train-alignn outputs/atomistic/screen_<data>
    python code/atomistic/go_au.py predict outputs/atomistic/screen_<data>/alignn --oc 0.15 0.25 --foh 0.3 0.7
    python code/atomistic/go_au.py interface --calc mace-mp-d3
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import calculators as C  # noqa: E402

ROOT = C.ROOT
GO_MACE_CODE = os.path.join(ROOT, "projects", "atomistic", "GO-MACE-23", "code")
OUT = os.path.join(ROOT, "outputs", "atomistic")
BOUNDS = {"O_C": (0.05, 0.45), "f_OH": (0.0, 1.0)}


# ------------------------------------------------------------------------------------------ estruturas
def make_go(o_c: float, f_oh: float, seed: int, nx: int = 4, nz: int = 3, vacuum: float = 10.0):
    """GO periódico no plano xz (normal = y) pelo gerador do GO-MACE-23 (epóxidos + hidroxilas nas duas faces)."""
    sys.path.insert(0, GO_MACE_CODE)
    from ase.build import graphene_nanoribbon
    from ase.io import read
    from generate_GO import build

    g = graphene_nanoribbon(nx, nz, type="armchair", saturated=False, sheet=True, vacuum=vacuum)
    state = np.random.get_state()
    np.random.seed(seed)
    try:
        with tempfile.TemporaryDirectory() as td, contextlib.redirect_stdout(io.StringIO()):
            path = os.path.join(td, "go.xyz")
            build().main(g, o_c, f_oh, False, 1, False, 0, (), vacuum, 200, path)
            go = read(path)
    finally:
        np.random.set_state(state)
    go.pbc = True          # vácuo de 2×vacuum ao longo de y: MLFFs tratam como slab periódico
    return go


def composition(atoms) -> dict:
    s = atoms.get_chemical_symbols()
    n = {e: s.count(e) for e in ("C", "O", "H", "Au")}
    return {"O_C_real": n["O"] / max(n["C"], 1), "f_OH_real": n["H"] / max(n["O"], 1), **{f"n_{k}": v for k, v in n.items()}}


def au_cluster(n: int):
    from ase import Atoms

    if n == 1:
        return Atoms("Au", positions=[[0, 0, 0]])
    if n == 4:   # tetraedro (Au4 3D) com d(Au–Au) = 2,7 Å
        d = 2.7
        return Atoms("Au4", positions=[[0, 0, 0], [d, 0, 0], [d / 2, d * np.sqrt(3) / 2, 0],
                                       [d / 2, d * np.sqrt(3) / 6, d * np.sqrt(2 / 3)]])
    raise ValueError("clusters suportados: Au1, Au4")


def place_au(go, n_au: int, rng, normal: int = 1, height: float = 2.3):
    """Coloca Au_n sobre um ponto aleatório da face superior, a `height` Å do átomo mais alto por perto."""
    cl = au_cluster(n_au)
    cl.positions -= cl.positions.mean(0)
    if normal == 1:   # cluster com a base no plano xz
        cl.positions = cl.positions[:, [0, 2, 1]]
    lat = [i for i in range(3) if i != normal]
    p = go.positions
    top = p[:, normal] > np.median(p[:, normal])
    xy = np.array([rng.uniform(0, go.cell[i, i]) for i in lat])   # célula ortogonal (graphene_nanoribbon)
    d = p[top][:, lat] - xy
    for k, i in enumerate(lat):
        L = go.cell[i, i]
        d[:, k] -= L * np.round(d[:, k] / L)
    near = np.hypot(d[:, 0], d[:, 1]) < 3.0
    zmax = (p[top][near, normal] if near.any() else p[top][:, normal]).max()
    shift = np.zeros(3)
    shift[lat] = xy
    shift[normal] = zmax + height - cl.positions[:, normal].min()
    cl.positions += shift
    out = go.copy()
    out += cl
    return out


def relax(atoms, calc, fmax: float, steps: int, frames: list | None = None):
    from ase.optimize import FIRE

    atoms.calc = calc
    opt = FIRE(atoms, logfile=None)
    if frames is not None:
        def grab(a=atoms):
            frames.append(a.copy())
            frames[-1].info["E_ref"] = float(a.get_potential_energy())   # "energy" o extxyz troca por calculadora
            frames[-1].arrays["forces_ref"] = a.get_forces().copy()
        opt.attach(grab, interval=5)
    opt.run(fmax=fmax, steps=steps)
    return float(atoms.get_potential_energy())


def adsorption_energy(o_c, f_oh, seed, calc, n_au=1, fmax=0.05, steps=150, nx=4, nz=3, frames=None):
    """E_ads = E(GO+Au_n) − E(GO) − E(Au_n) (eV; negativo = ligado) e as estruturas relaxadas."""
    rng = np.random.default_rng(seed)
    go = make_go(o_c, f_oh, seed, nx, nz)
    e_go = relax(go, calc, fmax, steps, frames)
    cl = au_cluster(n_au)
    cl.cell = [15, 15, 15]
    cl.pbc = True
    cl.center()
    if n_au > 1:
        e_au = relax(cl, calc, fmax, steps)
    else:
        cl.calc = calc
        e_au = float(cl.get_potential_energy())
    sys_ = place_au(go, n_au, rng)
    e_sys = relax(sys_, calc, fmax, steps, frames)
    return e_sys - e_go - e_au, go, sys_


def cfid(atoms) -> np.ndarray:
    """Descritores CFID do JARVIS-Tools (1557: químicos, célula, RDF/ADF/DDF, carga) — entrada p/ ML clássico."""
    from jarvis.ai.descriptors.cfid import CFID
    from jarvis.core.atoms import ase_to_atoms

    return np.asarray(CFID(ase_to_atoms(atoms)).get_comp_descp(), dtype=float)


# ---------------------------------------------------------------------------------------------- screen
def evaluate(points, reps, calc_name, n_au, fmax, steps, nx, nz, outdir, model_path=None, save_frames=False,
             do_cfid=False, seed0=0, log=print):
    import pandas as pd
    from ase.io import write
    from jarvis.core.atoms import ase_to_atoms

    calc = C.get_calculator(calc_name, model_path=model_path, elements={"C", "H", "O", "Au"})
    os.makedirs(os.path.join(outdir, "structures"), exist_ok=True)
    rows, frames, feats = [], [], []
    for (o_c, f_oh) in points:
        for r in range(reps):
            seed = seed0 + int(1e4 * o_c) * 1000 + int(100 * f_oh) * 10 + r
            t = time.time()
            fr = [] if save_frames else None
            e, go, sys_ = adsorption_energy(o_c, f_oh, seed, calc, n_au, fmax, steps, nx, nz, fr)
            sid = f"GO_OC{o_c:.3f}_fOH{f_oh:.2f}_r{r}_Au{n_au}"
            ase_to_atoms(sys_).write_poscar(os.path.join(outdir, "structures", sid + ".vasp"))
            if fr:
                frames += fr
            row = {"id": sid, "O_C": o_c, "f_OH": f_oh, "rep": r, "seed": seed, "n_Au": n_au, "E_ads_eV": e,
                   "calc": calc_name, "tempo_s": time.time() - t, **composition(go)}
            rows.append(row)
            if do_cfid:
                feats.append(cfid(sys_))
            log(f"  O/C={o_c:.3f} f_OH={f_oh:.2f} rep={r}: E_ads = {e:+.3f} eV ({row['tempo_s']:.0f} s)")
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(outdir, "results.csv"), mode="a", header=not os.path.exists(os.path.join(outdir, "results.csv")),
              index=False)
    if frames:
        write(os.path.join(outdir, "frames.extxyz"), frames, append=True)
    if feats:
        np.save(os.path.join(outdir, f"cfid_{int(time.time())}.npy"), np.vstack(feats))
    return df


def new_outdir(kind):
    d = os.path.join(OUT, f"{kind}_{time.strftime('%Y%m%d-%H%M%S')}")
    os.makedirs(d, exist_ok=True)
    return d


# ---------------------------------------------------------------------------------------------- design
def design(a):
    import pandas as pd
    import torch
    from botorch.acquisition.logei import qLogNoisyExpectedImprovement
    from botorch.fit import fit_gpytorch_mll
    from botorch.models import SingleTaskGP
    from botorch.models.transforms import Normalize, Standardize
    from botorch.optim import optimize_acqf
    from gpytorch.mlls import ExactMarginalLogLikelihood
    from torch.quasirandom import SobolEngine

    torch.manual_seed(a.seed)
    outdir = a.outdir or new_outdir("design")
    lo = torch.tensor([BOUNDS["O_C"][0], BOUNDS["f_OH"][0]], dtype=torch.double)
    hi = torch.tensor([BOUNDS["O_C"][1], BOUNDS["f_OH"][1]], dtype=torch.double)
    bounds = torch.stack([lo, hi])

    def score(e):   # maior é melhor
        return -abs(e - a.target) if a.target is not None else -e

    x0 = lo + (hi - lo) * SobolEngine(2, scramble=True, seed=a.seed).draw(a.n_init, dtype=torch.double)
    pts = [tuple(np.round(x.tolist(), 3)) for x in x0]
    hist = evaluate(pts, a.reps, a.calc, a.n_au, a.fmax, a.steps, a.nx, a.nz, outdir, a.model_path, a.save_frames)
    for it in range(a.n_iter):
        agg = hist.groupby(["O_C", "f_OH"])["E_ads_eV"].agg(["mean", "var", "count"]).reset_index()
        X = torch.tensor(agg[["O_C", "f_OH"]].values, dtype=torch.double)
        Y = torch.tensor([score(e) for e in agg["mean"]], dtype=torch.double).unsqueeze(-1)
        # ruído observado = variância entre réplicas / n (piso para réplicas únicas)
        yvar = torch.tensor(np.nan_to_num(agg["var"].values, nan=0.01), dtype=torch.double).clamp_min(1e-4)
        yvar = (yvar / torch.tensor(agg["count"].values, dtype=torch.double)).unsqueeze(-1)
        gp = SingleTaskGP(X, Y, train_Yvar=yvar, input_transform=Normalize(2, bounds=bounds),
                          outcome_transform=Standardize(1))
        fit_gpytorch_mll(ExactMarginalLogLikelihood(gp.likelihood, gp))
        acq = qLogNoisyExpectedImprovement(gp, X_baseline=X)
        cand, _ = optimize_acqf(acq, bounds, q=1, num_restarts=8, raw_samples=128)
        p = tuple(np.round(cand[0].tolist(), 3))
        print(f"[BO {it + 1}/{a.n_iter}] propõe O/C={p[0]:.3f}, f_OH={p[1]:.2f}")
        hist = pd.concat([hist, evaluate([p], a.reps, a.calc, a.n_au, a.fmax, a.steps, a.nx, a.nz, outdir,
                                         a.model_path, a.save_frames)], ignore_index=True)
    agg = hist.groupby(["O_C", "f_OH"])["E_ads_eV"].agg(["mean", "std", "count"]).reset_index()
    agg["score"] = [score(e) for e in agg["mean"]]
    best = agg.sort_values("score", ascending=False).iloc[0]
    res = {"objetivo": f"E_ads alvo {a.target} eV" if a.target is not None else "ancoragem máxima (E_ads mínima)",
           "melhor": {k: (None if pd.isna(best[k]) else float(best[k])) for k in ("O_C", "f_OH", "mean", "std")},
           "avaliacoes": int(len(hist)),
           "calc": a.calc, "n_Au": a.n_au, "pasta": os.path.relpath(outdir, ROOT)}
    json.dump(res, open(os.path.join(outdir, "design_summary.json"), "w"), indent=2, ensure_ascii=False)
    print(agg.sort_values("score", ascending=False).round(3).to_string(index=False))
    print(json.dumps(res, indent=2, ensure_ascii=False))
    return res


# ------------------------------------------------------------------------------------------------ ALIGNN
def _alignn_config(epochs, batch_size, forces=False):
    cfg_path = os.path.join(ROOT, "external", "jarvis", "alignn", "alignn", "examples",
                            "sample_data_ff" if forces else "sample_data",
                            "config_example_atomwise.json" if forces else "config_example.json")
    cfg = json.load(open(cfg_path))
    cfg.update({"epochs": epochs, "batch_size": batch_size, "n_early_stopping": None, "use_lmdb": True})
    if not forces:
        cfg["train_ratio"], cfg["val_ratio"], cfg["test_ratio"] = 0.7, 0.15, 0.15
    return cfg


def _train_alignn(root_dir, cfg, outdir):
    exe = os.path.join(os.path.dirname(sys.executable), "train_alignn.py")
    json.dump(cfg, open(os.path.join(root_dir, "config.json"), "w"), indent=1)
    cmd = [exe if os.path.exists(exe) else "train_alignn.py", "--root_dir", root_dir, "--config",
           os.path.join(root_dir, "config.json"), "--output_dir", outdir]
    r = subprocess.run(cmd, cwd=root_dir, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stdout[-2000:] + r.stderr[-2000:])
    return outdir


def train_alignn(a):
    """ALIGNN (JARVIS-ML) estrutura → E_ads com os POSCARs e results.csv de um `screen`/`design`."""
    import pandas as pd

    df = pd.read_csv(os.path.join(a.data, "results.csv"))
    root = tempfile.mkdtemp(prefix="alignn_data_")
    for sid in df["id"]:
        os.symlink(os.path.join(a.data, "structures", sid + ".vasp"), os.path.join(root, sid + ".vasp"))
    df[["id", "E_ads_eV"]].assign(id=lambda d: d["id"] + ".vasp").to_csv(os.path.join(root, "id_prop.csv"),
                                                                        header=False, index=False)
    n = len(df)
    if n < 4:
        raise SystemExit(f"só {n} estruturas: rode um screen/design maior (>= 4; recomendado >= 50)")
    cfg = _alignn_config(a.epochs, max(1, min(a.batch_size, n // 4)))
    n_val = max(1, round(0.15 * n))
    cfg["n_train"], cfg["n_val"], cfg["n_test"] = n - 2 * n_val, n_val, n_val
    out = _train_alignn(root, cfg, os.path.abspath(a.out or os.path.join(a.data, "alignn")))
    hist = json.load(open(os.path.join(out, "history_val.json")))   # [[total, grafo, átomo, …] por época]
    print(f"ALIGNN treinado em {n} estruturas -> {os.path.relpath(out, ROOT)} "
          f"(perda de validação na última época: {hist[-1][0]:.4g})")
    return out


def train_alignn_ff(a):
    """ALIGNN-FF (JARVIS-ML) específico de GO–Au a partir dos quadros (energia/forças) salvos com --save-frames."""
    from ase.io import read
    from jarvis.core.atoms import ase_to_atoms

    frames = read(os.path.join(a.data, "frames.extxyz"), index=":")
    root = tempfile.mkdtemp(prefix="alignn_ff_data_")
    data = [{"jid": f"f{i}", "atoms": ase_to_atoms(f).to_dict(), "total_energy": f.info["E_ref"],
             "forces": f.arrays["forces_ref"].tolist(), "stresses": np.zeros((3, 3)).tolist()} for i, f in enumerate(frames)]
    json.dump(data, open(os.path.join(root, "id_prop.json"), "w"))
    n = len(data)
    cfg = _alignn_config(a.epochs, max(1, min(a.batch_size, n // 4)), forces=True)
    n_val = max(1, round(0.1 * n))
    cfg["n_train"], cfg["n_val"], cfg["n_test"] = n - 2 * n_val, n_val, n_val
    cfg["model"]["stresswise_weight"] = 0.0
    out = _train_alignn(root, cfg, os.path.abspath(a.out or os.path.join(a.data, "alignn_ff")))
    print(f"ALIGNN-FF treinado em {len(data)} quadros -> {os.path.relpath(out, ROOT)} "
          "(use: --calc alignn-ff --model-path <pasta>)")
    return out


def predict(a):
    """Triagem com o ALIGNN treinado: gera GO+Au (sem relaxar) para cada composição e prevê E_ads."""
    import pandas as pd
    from alignn.ff.ff import AlignnAtomwiseCalculator

    # a calculadora do ALIGNN carrega qualquer modelo treinado (config.json + best_model.pt); com intensive=False e
    # sem gradiente, a "energia" devolvida é a saída escalar do modelo (aqui, E_ads)
    model = AlignnAtomwiseCalculator(path=a.model, device="cpu", intensive=False, include_stress=False)
    rows = []
    for o_c in a.oc:
        for f_oh in a.foh:
            preds = []
            for r in range(a.reps):
                seed = 777 + int(1e4 * o_c) * 1000 + int(100 * f_oh) * 10 + r
                s = place_au(make_go(o_c, f_oh, seed, a.nx, a.nz), a.n_au, np.random.default_rng(seed))
                model.results = {}
                preds.append(float(model.get_property("energy", s)))
            rows.append({"O_C": o_c, "f_OH": f_oh, "E_ads_pred_eV": np.mean(preds), "sd_entre_estruturas": np.std(preds)})
    df = pd.DataFrame(rows).sort_values("E_ads_pred_eV")
    print(df.round(3).to_string(index=False))
    return df


# --------------------------------------------------------------------------------------------- interface
def interface(a):
    """Au(111)/grafite(001) com o InterMat (JARVIS) e W_ad = (E_filme + E_substrato − E_interface)/A, com filme e
    substrato isolados na célula da própria interface."""
    from intermat.generate import InterfaceCombi
    from jarvis.core.atoms import Atoms, ase_to_atoms

    import jarvis_data as JD

    recs = {r["jid"]: r for r in JD.dft3d() if r["jid"] in ("JVASP-825", "JVASP-48")}
    au = Atoms.from_dict(recs["JVASP-825"]["atoms"])
    gr = Atoms.from_dict(recs["JVASP-48"]["atoms"])
    ic = InterfaceCombi(film_mats=[au], subs_mats=[gr], film_indices=[[1, 1, 1]], subs_indices=[[0, 0, 1]],
                        film_ids=["JVASP-825"], subs_ids=["JVASP-48"], seperations=[3.0],
                        film_thicknesses=[a.film_thickness], subs_thicknesses=[a.subs_thickness], max_area=a.max_area,
                        dataset=[recs["JVASP-825"]], working_dir=tempfile.mkdtemp())
    calc = C.get_calculator(a.calc, model_path=a.model_path, elements={"Au", "C"})

    def to_ase(x):   # o InterMat devolve ora Atoms, ora dicionário
        return (x if isinstance(x, Atoms) else Atoms.from_dict(x)).ase_converter()

    def energy(at):
        at.pbc = True
        at.calc = calc
        return float(at.get_potential_energy())

    scan = []
    for sep in a.separations:   # varredura da separação (como o InterMat faz com `seperations`)
        het = ic.get_interface(film_atoms=au, subs_atoms=gr, film_index=[1, 1, 1], subs_index=[0, 0, 1],
                               film_thickness=a.film_thickness, subs_thickness=a.subs_thickness, seperation=sep)
        intf = to_ase(het["interface"])
        # filme e substrato na MESMA célula (deformada) da interface: W_ad mede só a ligação, sem a energia de
        # deformação do descasamento (film_sl/subs_sl do InterMat estão sem deformação)
        au_mask = np.array(intf.get_chemical_symbols()) == "Au"
        e_i, e_f, e_s = energy(intf), energy(intf[au_mask]), energy(intf[~au_mask])
        area = np.linalg.norm(np.cross(intf.cell[0], intf.cell[1]))
        scan.append({"sep_A": sep, "W_ad_J_m2": (e_f + e_s - e_i) / area * 16.0217663, "het": het, "intf": intf})
        print(f"  separação {sep:.2f} Å: W_ad = {scan[-1]['W_ad_J_m2']:+.3f} J/m²")
    best = max(scan, key=lambda r: r["W_ad_J_m2"])
    het = best["het"]
    res = {"n_atomos_interface": len(best["intf"]), "descasamento_u": het.get("mismatch_u"),
           "descasamento_v": het.get("mismatch_v"), "separacao_otima_A": best["sep_A"],
           "W_ad_J_m2": best["W_ad_J_m2"], "calc": a.calc,
           "nota": "pontos únicos (sem relaxar), filme/substrato na célula da interface"}
    os.makedirs(OUT, exist_ok=True)
    ase_to_atoms(best["intf"]).write_poscar(os.path.join(OUT, "Au111_grafite001_interface.vasp"))
    print(json.dumps(res, indent=2, ensure_ascii=False, default=float))
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--calc", default="mace-mp-d3", choices=C.NAMES)
        p.add_argument("--model-path", help="ALIGNN-FF treinado (com --calc alignn-ff)")
        p.add_argument("--n-au", type=int, default=1, choices=[1, 4])
        p.add_argument("--reps", type=int, default=2, help="estruturas GO independentes por composição")
        p.add_argument("--fmax", type=float, default=0.05)
        p.add_argument("--steps", type=int, default=150)
        p.add_argument("--nx", type=int, default=4, help="tamanho da folha (graphene_nanoribbon nx × nz)")
        p.add_argument("--nz", type=int, default=3)
        p.add_argument("--save-frames", action="store_true", help="grava quadros das relaxações (train-alignn-ff)")
        p.add_argument("--outdir")

    s = sub.add_parser("screen")
    common(s)
    s.add_argument("--oc", type=float, nargs="+", default=[0.1, 0.25, 0.4])
    s.add_argument("--foh", type=float, nargs="+", default=[0.0, 0.5, 1.0])
    s.add_argument("--cfid", action="store_true", help="salva descritores CFID (JARVIS-Tools)")
    d = sub.add_parser("design")
    common(d)
    d.add_argument("--target", type=float, help="E_ads alvo (eV); sem alvo = ancoragem máxima")
    d.add_argument("--n-init", type=int, default=6)
    d.add_argument("--n-iter", type=int, default=10)
    d.add_argument("--seed", type=int, default=0)
    for name in ("train-alignn", "train-alignn-ff"):
        t = sub.add_parser(name)
        t.add_argument("data", help="pasta de um screen/design")
        t.add_argument("--epochs", type=int, default=50)
        t.add_argument("--batch-size", type=int, default=8)
        t.add_argument("--out")
    pr = sub.add_parser("predict")
    pr.add_argument("model", help="pasta do ALIGNN treinado")
    pr.add_argument("--oc", type=float, nargs="+", required=True)
    pr.add_argument("--foh", type=float, nargs="+", required=True)
    pr.add_argument("--reps", type=int, default=3)
    pr.add_argument("--n-au", type=int, default=1)
    pr.add_argument("--nx", type=int, default=4)
    pr.add_argument("--nz", type=int, default=3)
    it = sub.add_parser("interface")
    it.add_argument("--calc", default="mace-mp-d3", choices=C.NAMES)
    it.add_argument("--model-path")
    it.add_argument("--film-thickness", type=float, default=7.0)
    it.add_argument("--subs-thickness", type=float, default=7.0)
    it.add_argument("--max-area", type=float, default=120.0)
    it.add_argument("--separations", type=float, nargs="+", default=[2.8, 3.1, 3.4, 3.7, 4.0])
    a = ap.parse_args(argv)

    if a.cmd == "screen":
        outdir = a.outdir or new_outdir("screen")
        pts = [(o, f) for o in a.oc for f in a.foh]
        df = evaluate(pts, a.reps, a.calc, a.n_au, a.fmax, a.steps, a.nx, a.nz, outdir, a.model_path, a.save_frames,
                      a.cfid)
        print(df.groupby(["O_C", "f_OH"])["E_ads_eV"].agg(["mean", "std"]).round(3).to_string())
        print("->", os.path.relpath(outdir, ROOT))
        return df
    if a.cmd == "design":
        return design(a)
    if a.cmd == "train-alignn":
        return train_alignn(a)
    if a.cmd == "train-alignn-ff":
        return train_alignn_ff(a)
    if a.cmd == "predict":
        return predict(a)
    if a.cmd == "interface":
        return interface(a)


if __name__ == "__main__":
    main()
