"""Build a SURROGATE amorphous-graphene database for run_amorphpus.py / amorphous.select_disordered.

The original database used in the paper (../structures/aG_p6.xyz) is not distributed with the code.
This script produces a stand-in with the format that `amorphous.select_disordered` expects: an extended-XYZ
trajectory of flat carbon sheets, each frame carrying `atoms.info["p6"]` = fraction of 6-membered rings.

Method (not the paper's ML-driven melt-quench): start from periodic graphene and apply random
Wooten-Winer-Weaire / Stone-Wales bond switches. After every switch the sheet is relaxed with a planar
Keating-type spring model (bonds -> 1.42 A, angles -> 120 deg, soft non-bonded repulsion). A switch is
accepted only if every atom stays 3-coordinated, no 3-/4-membered rings appear, all C-C bonds stay within
1.25-1.65 A and the 1.85 A cutoff used by generate_GO.py recovers exactly the intended bond network. Snapshots are stored as p6 decreases from 1 to
`--p6-min`. Optionally, each stored frame can be refined with the GO-MACE-23 potential (`--mace-steps`).

Usage (from this folder; needs ase, numpy, torch):
    python make_amorphous_db.py                          # -> ../structures/aG_p6_surrogate.xyz
    python make_amorphous_db.py --nx 12 --nz 7 --n-runs 4 --p6-min 0.3 --out ../structures/aG_p6.xyz
"""
import argparse
import os
from collections import deque

import numpy as np
import torch
from ase import neighborlist
from ase.build import graphene_nanoribbon
from ase.io import write

D0 = 1.42          # target C-C bond length (A)
COS0 = -0.5        # cos(120 deg)
R_REP = 2.1        # non-bonded pairs closer than this are pushed apart (A)
CUTOFF = 1.85      # bond cutoff used by generate_GO.py
K_BOND = 10.0      # bond-stretch stiffness relative to the angle term
BOND_RANGE = (1.25, 1.65)  # switches leaving any C-C bond outside this range are rejected


def make_sheet(nx, nz, vacuum=10.0):
    """Periodic graphene in the xz plane (same convention as run.py: pbc = T F T)."""
    return graphene_nanoribbon(nx, nz, type="armchair", saturated=False, sheet=True, vacuum=vacuum)


def min_image(dv, L):
    """Minimum image along x and z (y is non-periodic)."""
    dv = dv.clone()
    for k in (0, 2):
        dv[..., k] = dv[..., k] - L[k] * torch.round(dv[..., k] / L[k])
    return dv


def bonds_from_geometry(atoms, cutoff=CUTOFF):
    i, j = neighborlist.neighbor_list("ij", atoms, cutoff)
    adj = [set() for _ in range(len(atoms))]
    for a, b in zip(i, j):
        adj[a].add(b)
    return adj


def relax(pos, adj, L, steps=200):
    """Planar Keating-like relaxation of x,z coordinates for a fixed bond graph."""
    n = len(pos)
    bonds = np.array(sorted({(min(a, b), max(a, b)) for a in range(n) for b in adj[a]}))
    angles = np.array([(b, a, c) for a in range(n) for b in adj[a] for c in adj[a] if b < c])
    bonded = set(map(tuple, bonds))
    x = torch.tensor(pos, dtype=torch.float64)
    y0 = x[:, 1].clone()
    xz = x[:, [0, 2]].clone().requires_grad_(True)
    Lt = torch.tensor(L, dtype=torch.float64)

    # non-bonded candidate pairs (within 3.2 A now); 1-3 neighbours are handled by the angle term
    with torch.no_grad():
        dv = min_image(x[None, :, :] - x[:, None, :], Lt)
        d = dv.norm(dim=-1)
    second = {(min(b, c), max(b, c)) for (b, _, c) in angles}
    ii, jj = torch.where(torch.triu(d < 3.2, diagonal=1))
    rep = np.array([(p, q) for p, q in zip(ii.tolist(), jj.tolist())
                    if (p, q) not in bonded and (p, q) not in second]).reshape(-1, 2)

    def full(xz):
        return torch.stack([xz[:, 0], y0, xz[:, 1]], dim=1)

    def energy(xz):
        r = full(xz)
        db = min_image(r[bonds[:, 1]] - r[bonds[:, 0]], Lt)
        e = K_BOND * ((db.norm(dim=1) - D0) ** 2).sum()
        v1 = min_image(r[angles[:, 0]] - r[angles[:, 1]], Lt)
        v2 = min_image(r[angles[:, 2]] - r[angles[:, 1]], Lt)
        cos = (v1 * v2).sum(1) / (v1.norm(dim=1) * v2.norm(dim=1))
        e = e + 0.5 * D0 ** 2 * ((cos - COS0) ** 2).sum()
        if len(rep):
            dr = min_image(r[rep[:, 1]] - r[rep[:, 0]], Lt).norm(dim=1)
            e = e + (torch.clamp(R_REP - dr, min=0) ** 2).sum()
        return e

    opt = torch.optim.LBFGS([xz], max_iter=steps, line_search_fn="strong_wolfe", tolerance_grad=1e-6)

    def closure():
        opt.zero_grad()
        e = energy(xz)
        e.backward()
        return e

    opt.step(closure)
    with torch.no_grad():
        out = full(xz).numpy().copy()
    for k in (0, 2):  # wrap back into the cell
        out[:, k] %= L[k]
    return out


def rings(adj, max_size=12):
    """Set of smallest rings through each atom (shortest-path rings)."""
    found = set()
    for a in range(len(adj)):
        nb = sorted(adj[a])
        for p in range(len(nb)):
            for q in range(p + 1, len(nb)):
                b, c = nb[p], nb[q]
                prev = {b: None}
                dq = deque([b])
                while dq:
                    u = dq.popleft()
                    if u == c:
                        break
                    for w in adj[u]:
                        if w != a and w not in prev:
                            prev[w] = u
                            dq.append(w)
                if c not in prev:
                    continue
                path, u = [], c
                while u is not None:
                    path.append(u)
                    u = prev[u]
                if len(path) + 1 <= max_size:
                    found.add(frozenset(path + [a]))
    return found


def ring_stats(adj):
    sizes = np.array([len(r) for r in rings(adj)])
    return sizes, float(np.mean(sizes == 6)) if len(sizes) else 0.0


def try_switch(atoms, adj, L, rng):
    """One Stone-Wales / WWW bond switch; returns (new_positions, new_adj) or None if rejected."""
    n = len(atoms)
    a = int(rng.integers(n))
    b = int(rng.choice(sorted(adj[a])))
    ka = [k for k in adj[a] if k != b]
    kb = [k for k in adj[b] if k != a]
    if len(ka) != 2 or len(kb) != 2:
        return None
    pos = atoms.get_positions().copy()
    Lt = torch.tensor(L, dtype=torch.float64)
    # rotate the a-b bond by 90 deg about its midpoint (in the xz plane)
    dv = min_image(torch.tensor(pos[b] - pos[a]), Lt).numpy()
    mid = pos[a] + dv / 2
    rot = np.array([-dv[2], 0.0, dv[0]]) / 2
    pos[a], pos[b] = mid - rot, mid + rot
    # a keeps the 2 closest of {ka, kb}; b takes the other 2 -> must be one of each
    cand = ka + kb
    da = [np.linalg.norm(min_image(torch.tensor(pos[c] - pos[a]), Lt).numpy()) for c in cand]
    near_a = [cand[i] for i in np.argsort(da)[:2]]
    if len(set(near_a) & set(ka)) != 1:
        return None
    new = [set(s) for s in adj]
    lose_a = [k for k in ka if k not in near_a][0]
    gain_a = [k for k in kb if k in near_a][0]
    new[a].discard(lose_a); new[lose_a].discard(a)
    new[b].discard(gain_a); new[gain_a].discard(b)
    new[a].add(gain_a); new[gain_a].add(a)
    new[b].add(lose_a); new[lose_a].add(b)
    pos = relax(pos, new, L)
    test = atoms.copy()
    test.set_positions(pos)
    if bonds_from_geometry(test) != new:          # generate_GO's 1.85 A cutoff must see this network
        return None
    d = neighborlist.neighbor_list("d", test, CUTOFF)
    if d.min() < BOND_RANGE[0] or d.max() > BOND_RANGE[1]:
        return None
    sizes, _ = ring_stats(new)
    if (sizes < 5).any():
        return None
    return pos, new


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--nx", type=int, default=10, help="armchair repeats along x (sheet width)")
    ap.add_argument("--nz", type=int, default=6, help="repeats along z (sheet length)")
    ap.add_argument("--n-runs", type=int, default=3, help="independent disordering trajectories")
    ap.add_argument("--p6-min", type=float, default=0.3, help="stop a run when p6 drops below this")
    ap.add_argument("--max-switches", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--mace-steps", type=int, default=0,
                    help="optional FIRE steps with GO-MACE-23 on each stored frame (slow on CPU)")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                   "..", "structures", "aG_p6_surrogate.xyz"))
    args = ap.parse_args()
    torch.set_num_threads(max(1, os.cpu_count() or 1))

    calc = None
    if args.mace_steps:
        from mace.calculators import MACECalculator
        model = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models", "fitting",
                             "potential", "iter-12-final-model", "go-mace-23.pt")
        calc = MACECalculator(model_paths=model, device="cuda" if torch.cuda.is_available() else "cpu",
                              default_dtype="float32")

    frames = []
    for run in range(args.n_runs):
        rng = np.random.default_rng(args.seed + run)
        atoms = make_sheet(args.nx, args.nz)
        L = atoms.get_cell().diagonal().copy()
        adj = bonds_from_geometry(atoms)
        _, p6 = ring_stats(adj)
        accepted = 0
        for it in range(args.max_switches):
            res = try_switch(atoms, adj, L, rng)
            if res is None:
                continue
            pos, adj = res
            atoms.set_positions(pos)
            accepted += 1
            _, p6 = ring_stats(adj)
            frame = atoms.copy()
            frame.info["p6"] = p6
            frame.info["n_switches"] = accepted
            frame.info["run"] = run
            frame.info["method"] = "WWW/Stone-Wales switches + planar Keating relaxation (surrogate)"
            if calc is not None:
                from ase.optimize import FIRE
                frame.calc = calc
                FIRE(frame, logfile=None).run(fmax=0.1, steps=args.mace_steps)
                frame.calc = None
                frame.info["p6"] = ring_stats(bonds_from_geometry(frame))[1]
            frames.append(frame)
            print(f"run {run} switch {accepted:4d} (try {it + 1}) p6 = {p6:.3f}", flush=True)
            if p6 < args.p6_min:
                break
        # save after every run so partial progress is kept
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        write(args.out, frames)

    p6s = np.array([f.info["p6"] for f in frames])
    print(f"wrote {len(frames)} frames to {args.out}; p6 range {p6s.min():.3f}-{p6s.max():.3f}")


if __name__ == "__main__":
    main()
