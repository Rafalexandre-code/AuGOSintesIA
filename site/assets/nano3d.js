/* Nanocompósito 3D (aba "Nanocompósito 3D"): óxido de grafeno com nanopartículas de ouro, em three.js.

   É um MODELO FÍSICO ILUSTRATIVO montado com parâmetros medidos, não uma medida: rede do grafeno (C–C 1,42 Å), grupos
   oxigenados do modelo de Lerf–Klinowski (epóxi e hidroxila no plano basal, carboxila nas bordas, em domínios), rede
   cúbica de face centrada do ouro (a = 4,078 Å), forma de equilíbrio de Wulff (faces {111} e {100}) truncada pela adesão
   ao suporte (Winterbottom), número de coordenação de cada átomo e, na escala de partículas, tamanhos log-normais com a
   cor calculada por Mie (a mesma conta da aba Óptica). A síntese é um Monte Carlo cinético QUALITATIVO: redução do Au³⁺,
   supersaturação, nucleação nos sítios oxigenados com a taxa da teoria clássica, exp(−B/ln²S), e crescimento átomo a
   átomo nos sítios da rede fcc de maior coordenação.

   AUGO_N3CORE  = geometria e simulação (sem three.js; os testes rodam no node)
   AUGO_NANO3D  = cena, controles de câmera, modos e roteiro (usa window.THREE r147 + OrbitControls) */
(function () {
  "use strict";
  const A_AU = 4.078, NN_AU = A_AU / Math.SQRT2, RHO_AU = 4 / (A_AU * A_AU * A_AU), CC = 1.42, A_GR = CC * Math.sqrt(3);
  const WULFF = 1.15;            // γ(100)/γ(111) do ouro: 1,1–1,3 conforme a fonte (DFT e medidas); a forma muda pouco nessa faixa
  const Y_AU = 3.4;              // altura do primeiro plano de ouro acima do plano do carbono (O a ~1,3 Å + ligação Au–O ~2,1 Å)

  function rng(seed) {           // mulberry32: mesmos sorteios a cada visita
    let s = seed >>> 0;
    return () => { s = (s + 0x6D2B79F5) >>> 0; let t = Math.imul(s ^ (s >>> 15), 1 | s); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  }
  const gauss = (r) => { let u = 0, v = 0; while (u === 0) u = r(); while (v === 0) v = r(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v); };
  const deq = (n) => Math.cbrt(6 * n / (Math.PI * RHO_AU)) / 10;              // diâmetro de volume equivalente (nm)
  const ripple = (x, z) => 0.8 * Math.sin(2 * Math.PI * x / 55) * Math.cos(2 * Math.PI * z / 70);   // ondulação do grafeno (Å)

  // rotação que leva a direção cristalina [111] ao eixo vertical (+y) e depois gira φ em torno de y
  function rot111(phi) {
    const n = [1 / Math.sqrt(3), 1 / Math.sqrt(3), 1 / Math.sqrt(3)], kx = n[2], kz = -n[0], kn = Math.hypot(kx, kz);   // eixo = n × ŷ
    const ux = kx / kn, uz = kz / kn, c = n[1], s = Math.sqrt(1 - c * c);
    // Rodrigues com eixo (ux, 0, uz)
    const R0 = [[c + ux * ux * (1 - c), -uz * s, ux * uz * (1 - c)], [uz * s, c, -ux * s], [uz * ux * (1 - c), ux * s, c + uz * uz * (1 - c)]];
    const cp = Math.cos(phi), sp = Math.sin(phi), Ry = [[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]];
    return Ry.map((r) => [0, 1, 2].map((j) => r[0] * R0[0][j] + r[1] * R0[1][j] + r[2] * R0[2][j]));
  }
  const apply = (M, v) => [M[0][0] * v[0] + M[0][1] * v[1] + M[0][2] * v[2], M[1][0] * v[0] + M[1][1] * v[1] + M[1][2] * v[2], M[2][0] * v[0] + M[2][1] * v[1] + M[2][2] * v[2]];
  const NB12 = [];
  for (const a of [-1, 1]) for (const b of [-1, 1]) NB12.push([a, b, 0], [a, 0, b], [0, a, b]);
  const key = (i, j, k) => (i + 512) * 1048576 + (j + 512) * 1024 + (k + 512);

  /* ------------------------------------------------------------------ folha de óxido de grafeno */
  // oxid = razão O/C (0 = grafeno; ~0,4–0,5 = GO de Hummers; 0,05–0,12 = GO reduzido)
  function buildSheet(L, oxid, seed = 7) {
    const r = rng(seed), C = [], half = L / 2;
    const a1 = [A_GR, 0], a2 = [A_GR / 2, A_GR * Math.sqrt(3) / 2], b1 = [A_GR / 2, A_GR / (2 * Math.sqrt(3))];
    const n = Math.ceil(L / A_GR) + 4;
    for (let i = -n; i <= n; i++) for (let j = -n; j <= n; j++) for (const b of [[0, 0], b1]) {
      const x = i * a1[0] + j * a2[0] + b[0], z = i * a1[1] + j * a2[1] + b[1];
      if (Math.abs(x) <= half && Math.abs(z) <= half) C.push({ x, z, y: ripple(x, z), nb: [], sp3: 0, edge: false, used: false });
    }
    const cell = 1.7, grid = new Map(), gk = (x, z) => `${Math.floor(x / cell)},${Math.floor(z / cell)}`;
    C.forEach((c, i) => { const k = gk(c.x, c.z); (grid.get(k) || grid.set(k, []).get(k)).push(i); });
    const bonds = [];
    C.forEach((c, i) => { const cx = Math.floor(c.x / cell), cz = Math.floor(c.z / cell);
      for (let dx = -1; dx <= 1; dx++) for (let dz = -1; dz <= 1; dz++) for (const j of grid.get(`${cx + dx},${cz + dz}`) || []) {
        if (j <= i) continue; const d = Math.hypot(C[j].x - c.x, C[j].z - c.z);
        if (d < 1.6) { c.nb.push(j); C[j].nb.push(i); bonds.push([i, j]); } } });
    C.forEach((c) => { c.edge = c.nb.length < 3; });
    // domínios oxidados (o GO real alterna ilhas sp² e regiões oxidadas): campo de gaussianas + um domínio no centro,
    // onde a partícula ancora
    const dom = [[0, 0, 16]]; for (let k = 0; k < 7; k++) dom.push([(r() - 0.5) * L, (r() - 0.5) * L, 9 + 12 * r()]);
    const w = C.map((c) => 0.12 + dom.reduce((s, [x, z, sg]) => s + Math.exp(-((c.x - x) ** 2 + (c.z - z) ** 2) / (2 * sg * sg)), 0));
    const O = [], H = [], extraC = [], wsum = w.reduce((a, b) => a + b, 0), target = Math.round(oxid * C.length);
    let nO = 0, tries = 0;
    const pick = () => { let u = r() * wsum; for (let i = 0; i < w.length; i++) { u -= w[i]; if (u <= 0) return i; } return w.length - 1; };
    while (nO < target * 0.9 && tries < target * 30) {
      tries++;
      const i = pick(), c = C[i];
      if (c.used || c.edge || c.nb.some((j) => C[j].used)) continue;
      const side = r() < 0.5 ? 1 : -1;
      const partner = c.nb.filter((j) => !C[j].used && !C[j].edge && !C[j].nb.some((q) => q !== i && C[q].used));
      if (r() < 0.55 && partner.length) {                     // epóxi: O em ponte sobre a ligação C–C (C–O 1,46 Å)
        const j = partner[Math.floor(r() * partner.length)];
        c.used = C[j].used = true; c.sp3 = C[j].sp3 = side;
        O.push({ x: (c.x + C[j].x) / 2, z: (c.z + C[j].z) / 2, c: [i, j], side, type: "epoxi" });
      } else {                                                 // hidroxila: C–O 1,43 Å, O–H 0,97 Å
        c.used = true; c.sp3 = side;
        const th = r() * 2 * Math.PI;
        O.push({ x: c.x, z: c.z, c: [i], side, type: "hidroxila", hx: 0.32 * Math.cos(th), hz: 0.32 * Math.sin(th) });
      }
      nO++;
    }
    // carboxilas nas bordas (C–C 1,50 Å; C=O 1,21 Å; C–OH 1,34 Å), em número proporcional à oxidação
    const edges = C.map((c, i) => [c, i]).filter(([c]) => c.edge && c.nb.length === 2);
    const nCOOH = Math.round(edges.length * Math.min(0.6, oxid * 1.3));
    for (let k = 0; k < nCOOH && edges.length; k++) {
      const [c, i] = edges.splice(Math.floor(r() * edges.length), 1)[0];
      if (c.used) continue;
      const mx = c.nb.reduce((s, j) => s + C[j].x, 0) / c.nb.length, mz = c.nb.reduce((s, j) => s + C[j].z, 0) / c.nb.length;
      let ux = c.x - mx, uz = c.z - mz; const un = Math.hypot(ux, uz) || 1; ux /= un; uz /= un;
      c.used = true; c.sp3 = 0; const side = r() < 0.5 ? 1 : -1;
      O.push({ x: c.x, z: c.z, c: [i], side, type: "carboxila", ux, uz });
    }
    // posições finais: carbonos sp³ saem ~0,3 Å do plano para o lado do grupo
    C.forEach((c) => { c.y = ripple(c.x, c.z) + 0.3 * (c.sp3 || 0); });
    const atomsO = [];
    for (const g of O) {
      const cy = g.c.reduce((s, i) => s + C[i].y, 0) / g.c.length;
      if (g.type === "epoxi") { g.y = cy + g.side * 1.25; atomsO.push({ x: g.x, y: g.y, z: g.z, g }); }
      else if (g.type === "hidroxila") { g.y = cy + g.side * 1.43; atomsO.push({ x: g.x, y: g.y, z: g.z, g }); H.push({ x: g.x + g.hx, y: g.y + g.side * 0.92, z: g.z + g.hz, g }); }
      else {
        const c = C[g.c[0]], cx = c.x + 1.5 * g.ux, cz = c.z + 1.5 * g.uz, cyy = c.y + 0.25 * g.side;
        extraC.push({ x: cx, y: cyy, z: cz, g, from: g.c[0] });
        const o1 = [cx + 0.6 * g.ux, cyy + g.side * 1.05, cz + 0.6 * g.uz], o2 = [cx + 0.75 * g.ux, cyy - g.side * 1.1, cz + 0.75 * g.uz];
        atomsO.push({ x: o1[0], y: o1[1], z: o1[2], g, dbl: true }, { x: o2[0], y: o2[1], z: o2[2], g });
        H.push({ x: o2[0] + 0.95 * g.ux, y: o2[1] - g.side * 0.2, z: o2[2] + 0.95 * g.uz, g });
        g.x = o1[0]; g.y = o1[1]; g.z = o1[2];
      }
    }
    const count = { epoxi: 0, hidroxila: 0, carboxila: 0 }; O.forEach((g) => count[g.type]++);
    const nOat = atomsO.length, sp3 = C.filter((c) => c.sp3).length;
    return { L, C, bonds, groups: O, O: atomsO, H, Cx: extraC, count, nC: C.length + extraC.length, nO: nOat,
      CO: nOat ? (C.length + extraC.length) / nOat : Infinity, sp3frac: sp3 / C.length };
  }

  /* ------------------------------------------------------------------ nanopartícula de ouro (Wulff + Winterbottom) */
  // adh = E_adesão / γ(111), de 0 (não molha: partícula inteira, apoiada num vértice/face) a ~0,8 (bem achatada)
  function shapeAtoms(R, adh) {
    const u = A_AU / 2, s111 = Math.sqrt(3) * R / u, s100 = WULFF * R / u, cut = (1 - adh) * R * Math.sqrt(3) / u, m = Math.ceil(s100) + 1;
    const out = [];
    for (let i = -m; i <= m; i++) for (let j = -m; j <= m; j++) for (let k = -m; k <= m; k++) {
      if ((i + j + k) & 1) continue;
      if (Math.abs(i) + Math.abs(j) + Math.abs(k) > s111 + 1e-9) continue;
      if (Math.max(Math.abs(i), Math.abs(j), Math.abs(k)) > s100 + 1e-9) continue;
      if (i + j + k < -cut - 1e-9) continue;
      out.push([i, j, k]);
    }
    return out;
  }
  function classify(sites) {
    const set = new Set(sites.map(([i, j, k]) => key(i, j, k)));
    const low = Math.min(...sites.map(([i, j, k]) => i + j + k));
    return sites.map(([i, j, k]) => {
      let cn = 0; for (const [a, b, c] of NB12) if (set.has(key(i + a, j + b, k + c))) cn++;
      const cls = i + j + k === low ? "interface" : cn >= 12 ? "interior" : cn >= 9 ? "f111" : cn === 8 ? "f100" : cn === 7 ? "aresta" : "vertice";
      return { cn, cls };
    });
  }
  function buildParticle(dnm, adh, phi = 0.35) {
    const target = RHO_AU * Math.PI / 6 * Math.pow(dnm * 10, 3);
    let lo = 1, hi = 8 + 7 * dnm, sites = null;
    for (let it = 0; it < 15; it++) { const R = (lo + hi) / 2, s = shapeAtoms(R, adh); if (s.length < target) lo = R; else { hi = R; sites = s; } }
    if (!sites) sites = shapeAtoms(hi, adh);
    const M = rot111(phi), u = A_AU / 2, cls = classify(sites);
    const P = sites.map(([i, j, k]) => apply(M, [i * u, j * u, k * u]));
    const ymin = Math.min(...P.map((p) => p[1]));
    P.forEach((p) => { p[1] += Y_AU - ymin; });
    const count = { interior: 0, f111: 0, f100: 0, aresta: 0, vertice: 0, interface: 0 }; cls.forEach((c) => count[c.cls]++);
    const base = P.filter((p) => p[1] < Y_AU + 0.3), foot = Math.max(...base.map((p) => Math.hypot(p[0], p[2]))) + 1.44;
    const N = sites.length, surf = N - count.interior;
    const top = Math.max(...P.map((p) => p[1]));
    return { N, d: deq(N), sites, P, cls, count, surf, surfFrac: surf / N, lowCN: (count.aresta + count.vertice) / N, foot,
      height: top - Y_AU + 2 * 1.44, center: [0, (Y_AU + top) / 2, 0], width: 2 * Math.max(...P.map((p) => Math.hypot(p[0], p[2]))) + 2.88 };
  }
  function siteCurve(adh) {          // fração de átomos em cada tipo de sítio, de ~1 a ~8 nm (um ponto por "raio" da forma)
    const out = [];
    for (let R = 4; R <= 36; R += R < 12 ? 0.7 : 1.4) {
      const sites = shapeAtoms(R, adh), N = sites.length; if (out.length && N === out[out.length - 1].N) continue;
      const c = { interior: 0, f111: 0, f100: 0, aresta: 0, vertice: 0, interface: 0 }; classify(sites).forEach((x) => c[x.cls]++);
      out.push({ d: deq(N), N, surf: 1 - c.interior / N, f111: c.f111 / N, f100: c.f100 / N, low: (c.aresta + c.vertice) / N, inter: c.interface / N });
    }
    return out;
  }

  /* ------------------------------------------------------------------ síntese: Monte Carlo cinético qualitativo */
  // red: probabilidade de redução por passo (NaBH₄ ≫ citrato); T em °C acelera a difusão (∝ √T) e a redução (Arrhenius)
  function Synthesis(sheet, opt) {
    const r = rng(opt.seed || 11), L = sheet.L, half = L / 2, H = opt.height || 36, n = opt.nAu || 1400;
    const Tk = (opt.T || 25) + 273.15, fT = Math.sqrt(Tk / 298.15), kred = opt.red * Math.exp(4.5 * (1 - 298.15 / Tk));
    const cSat = opt.cSat || 10, B = opt.B || 80, p0 = opt.p0 || 0.3, dIon = opt.dIon || 1.0, dMon = opt.dMon || 1.8;
    const adhB = opt.adhB == null ? 1.5 : opt.adhB;           // vizinho "extra" que o suporte oferece a um átomo do primeiro plano
    const pos = new Float32Array(3 * n), st = new Uint8Array(n), owner = new Int32Array(n).fill(-1);
    for (let i = 0; i < n; i++) { pos[3 * i] = (r() - 0.5) * L; pos[3 * i + 1] = 8 + r() * (H - 8); pos[3 * i + 2] = (r() - 0.5) * L; }
    const sites = sheet.groups.filter((g) => g.side === 1 && g.type !== "carboxila").map((g) => ({ x: g.x, y: g.y, z: g.z, free: true }));
    const sg = new Map(), sk = (x, z) => `${Math.floor(x / 3)},${Math.floor(z / 3)}`;
    sites.forEach((s, i) => { const k = sk(s.x, s.z); (sg.get(k) || sg.set(k, []).get(k)).push(i); });
    const ag = new Map(), ak = (x, y, z) => `${Math.floor(x / 4)},${Math.floor(y / 4)},${Math.floor(z / 4)}`;
    const clusters = [], u = A_AU / 2;
    let t = 0, nMon = 0, nIon = n, nAtt = 0, nNuc = 0;
    const hist = [];
    const wpos = (cl, i, j, k) => { const p = apply(cl.M, [i * u, j * u, k * u]); return [p[0] + cl.o[0], p[1] + cl.o[1], p[2] + cl.o[2]]; };
    function occupy(cl, kk, ijk, atom) {
      cl.occ.set(kk, atom); cl.cand.delete(kk);
      const [i, j, k] = ijk, p = wpos(cl, i, j, k);
      pos[3 * atom] = p[0]; pos[3 * atom + 1] = p[1]; pos[3 * atom + 2] = p[2]; st[atom] = 2; owner[atom] = cl.id; nAtt++;
      const g = ak(p[0], p[1], p[2]); (ag.get(g) || ag.set(g, []).get(g)).push(atom);
      if (i + j + k === 0) {                                   // primeiro plano: cobre os sítios oxigenados embaixo dele
        const cx = Math.floor(p[0] / 3), cz = Math.floor(p[2] / 3);
        for (let dx = -1; dx <= 1; dx++) for (let dz = -1; dz <= 1; dz++) for (const q of sg.get(`${cx + dx},${cz + dz}`) || []) if (Math.hypot(sites[q].x - p[0], sites[q].z - p[2]) < 2.6) sites[q].free = false;
      }
      for (const [a, b, c] of NB12) { const ni = i + a, nj = j + b, nk = k + c; if (ni + nj + nk < 0) continue; const k2 = key(ni, nj, nk);
        if (!cl.occ.has(k2)) { const e = cl.cand.get(k2); if (e) e.cn++; else cl.cand.set(k2, { ijk: [ni, nj, nk], cn: 1 }); } }
    }
    function nucleate(si, atom) {
      const s = sites[si], cl = { id: clusters.length, o: [s.x, s.y + 2.1, s.z], M: rot111(r() * 2 * Math.PI), occ: new Map(), cand: new Map() };
      clusters.push(cl); s.free = false; nNuc++;
      occupy(cl, key(0, 0, 0), [0, 0, 0], atom);
    }
    // o átomo que chega se difunde pela superfície até o sítio vago de maior coordenação do aglomerado (crescimento
    // perto do equilíbrio: formas compactas e facetadas); sítios do primeiro plano ganham um bônus de adesão ao GO
    function attach(cl, atom) {
      const x = pos[3 * atom], y = pos[3 * atom + 1], z = pos[3 * atom + 2];
      let best = null, bs = -1e9;
      for (const [kk, c] of cl.cand) {
        const p = wpos(cl, ...c.ijk), sc = c.cn + (c.ijk[0] + c.ijk[1] + c.ijk[2] === 0 ? adhB : 0) - 0.015 * Math.hypot(p[0] - x, p[1] - y, p[2] - z);
        if (sc > bs) { bs = sc; best = kk; }
      }
      if (best !== null) occupy(cl, best, cl.cand.get(best).ijk, atom);
    }
    function step() {
      t++;
      const S = nMon / cSat, pn = S > 1 ? p0 * Math.exp(-B / Math.pow(Math.log(S), 2)) : 0;
      for (let i = 0; i < n; i++) {
        const s = st[i]; if (s === 2) continue;
        const sig = (s === 0 ? dIon : dMon) * fT;
        let x = pos[3 * i] + gauss(r) * sig, y = pos[3 * i + 1] + gauss(r) * sig, z = pos[3 * i + 2] + gauss(r) * sig;
        if (x > half) x -= L; else if (x < -half) x += L;
        if (z > half) z -= L; else if (z < -half) z += L;
        const ymin = s === 0 ? 5 : 3.2;
        if (y < ymin) y = 2 * ymin - y; if (y > H) y = 2 * H - y;
        pos[3 * i] = x; pos[3 * i + 1] = y; pos[3 * i + 2] = z;
        if (s === 0) { if (r() < kred) { st[i] = 1; nIon--; nMon++; } continue; }
        // monômero Au⁰: encosta num aglomerado? (cresce) — senão, perto de um sítio oxigenado livre? (pode nuclear)
        const gx = Math.floor(x / 4), gy = Math.floor(y / 4), gz = Math.floor(z / 4);
        let hit = -1;
        for (let dx = -1; dx <= 1 && hit < 0; dx++) for (let dy = -1; dy <= 1 && hit < 0; dy++) for (let dz = -1; dz <= 1 && hit < 0; dz++)
          for (const a of ag.get(`${gx + dx},${gy + dy},${gz + dz}`) || []) { if (Math.hypot(pos[3 * a] - x, pos[3 * a + 1] - y, pos[3 * a + 2] - z) < 3.6) { hit = owner[a]; break; } }
        if (hit >= 0) { nMon--; attach(clusters[hit], i); continue; }
        if (y < 5.6 && pn > 0) {
          const cx = Math.floor(x / 3), cz = Math.floor(z / 3);
          for (let dx = -1; dx <= 1; dx++) for (let dz = -1; dz <= 1; dz++) for (const q of sg.get(`${cx + dx},${cz + dz}`) || []) {
            if (st[i] !== 1 || !sites[q].free) continue;
            if (Math.hypot(sites[q].x - x, sites[q].z - z) < 2.6 && r() < pn) { nMon--; nucleate(q, i); }
          }
        }
      }
      if (t % 5 === 0) hist.push(stats());
    }
    function stats() {
      const sz = clusters.map((c) => c.occ.size), big = sz.filter((x) => x >= 4);
      const ds = big.map(deq), md = ds.length ? ds.reduce((a, b) => a + b, 0) / ds.length : 0;
      const sd = ds.length > 1 ? Math.sqrt(ds.reduce((a, b) => a + (b - md) ** 2, 0) / (ds.length - 1)) : 0;
      return { t, S: nMon / cSat, ions: nIon, mon: nMon, att: nAtt, nuclei: nNuc, n: big.length, d: md, cv: md ? sd / md : 0,
        freeSites: sites.filter((s) => s.free).length, done: nIon === 0 && nMon === 0 };
    }
    const Sstar = Math.exp(Math.sqrt(B / Math.log(1000)));   // acima disto a nucleação deixa de ser rara (taxa ≥ 10⁻³ do máximo)
    return { n, pos, st, owner, clusters, sites, step, stats, hist, Sstar, cSat, get t() { return t; } };
  }

  // experimento de lotes: a mesma síntese em folhas com O/C diferentes, várias sementes cada; roda em fatias de ~25 ms
  // (setTimeout) para não travar a página. onProgress(resultados parciais), onDone(resultados). Devolve { cancel }.
  function batch(o, onProgress, onDone) {
    const oxs = o.ox || [0.05, 0.1, 0.2, 0.3, 0.4], reps = o.reps || 3, red = REDUCERS[o.red] || REDUCERS.nabh4, nAu = o.nAu || 1000;
    const res = oxs.map((ox) => ({ ox, runs: [] })), jobs = [];
    oxs.forEach((ox, i) => { for (let r = 0; r < reps; r++) jobs.push([i, 11 + r]); });
    let j = 0, sim = null, cancel = false, sheets = {};
    const tick = () => {
      if (cancel) return;
      if (o.paused && o.paused()) { setTimeout(tick, 400); return; }
      const t0 = Date.now();
      while (Date.now() - t0 < 25) {
        if (!sim) { if (j >= jobs.length) { onDone && onDone(res); return; }
          const [i, seed] = jobs[j], ox = oxs[i]; sheets[ox] = sheets[ox] || buildSheet(90, ox); sim = Synthesis(sheets[ox], { red, T: o.T || 25, nAu, seed }); }
        for (let k = 0; k < 10; k++) sim.step();
        const s = sim.stats();
        if (s.done || sim.t > 30000) { res[jobs[j][0]].runs.push({ n: s.n, d: s.d, cv: s.cv, nuclei: s.nuclei, t: s.t }); j++; sim = null;
          onProgress && onProgress(res, j / jobs.length); break; }
      }
      setTimeout(tick, 0);
    };
    setTimeout(tick, 0);
    return { cancel() { cancel = true; } };
  }
  // redutores: probabilidade de redução por passo (escala relativa; NaBH₄ reduz em segundos, citrato em minutos)
  const REDUCERS = { citrato: 0.001, ascorbico: 0.006, nabh4: 0.05 };
  window.AUGO_N3CORE = { batch, REDUCERS, A_AU, NN_AU, RHO_AU, CC, WULFF, Y_AU, rng, deq, ripple, rot111, apply, buildSheet, buildParticle, siteCurve, Synthesis };
})();


(function () {
  "use strict";
  const K = window.AUGO_N3CORE;
  // comprimento de onda (nm) → cor aproximada da luz (para desenhar a onda incidente)
  function waveRGB(l) {
    let r = 0, g = 0, b = 0;
    if (l < 440) { r = -(l - 440) / 60; b = 1; } else if (l < 490) { g = (l - 440) / 50; b = 1; } else if (l < 510) { g = 1; b = -(l - 510) / 20; }
    else if (l < 580) { r = (l - 510) / 70; g = 1; } else if (l < 645) { r = 1; g = -(l - 645) / 65; } else { r = 1; }
    const f = l < 420 ? 0.3 + 0.7 * (l - 380) / 40 : l > 700 ? 0.3 + 0.7 * (780 - l) / 80 : 1;
    return [r, g, b].map((x) => Math.max(0, Math.min(1, x * Math.max(0.35, f))));
  }
  const colorName = (l) => (l < 450 ? "violeta" : l < 490 ? "azul" : l < 520 ? "verde-azulado" : l < 565 ? "verde" : l < 590 ? "amarelo" : l < 625 ? "laranja" : l < 700 ? "vermelho" : "vermelho profundo");
  const CLS = { f111: "face (111)", f100: "face (100)", aresta: "aresta", vertice: "vértice", interface: "interface com o GO", interior: "interior" };
  const GRP = { epoxi: "epóxi (C–O–C)", hidroxila: "hidroxila (C–OH)", carboxila: "carboxila (–COOH)" };

  window.AUGO_NANO3D = function (host, opt) {
    const THREE = window.THREE;
    const okGL = (() => { try { const c = document.createElement("canvas"); return !!(window.WebGLRenderingContext && (c.getContext("webgl2") || c.getContext("webgl"))); } catch (e) { return false; } })();
    if (!THREE || !THREE.OrbitControls || !okGL) {
      host.insertAdjacentHTML("afterbegin", `<div class="n3-nogl"><b>O navegador não abriu o WebGL.</b> A cena 3D precisa de aceleração gráfica; os gráficos e a tabela abaixo continuam funcionando.</div>`);
      return null;
    }
    const O = opt.optics;
    const P = { scale: "atom", mode: "explore", sheet: "900K", color: "element", d: 2.6, adh: 0.35, ox: 0.3, labels: true, clip: false, hyd: true,
      lam: 520, red: "citrato", T: 25, speed: 10, md: 18, msig: 0.25, cov: 0.2, mcolor: "gold", tem: false, relax: false };
    let theme = opt.theme, themeV = 0;

    /* ---------- renderizador, câmeras, luzes */
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2)); renderer.localClippingEnabled = true;
    const cv = renderer.domElement; cv.setAttribute("role", "img"); cv.tabIndex = 0;
    cv.setAttribute("aria-label", "Cena 3D interativa: folha de óxido de grafeno com nanopartículas de ouro. Arraste para girar; com a cena em foco, as setas do teclado movem a vista.");
    host.prepend(cv);
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(36, 1, 0.5, 6000), ortho = new THREE.OrthographicCamera(-200, 200, 200, -200, 0.1, 4000);
    let cam = camera;
    const controls = new THREE.OrbitControls(camera, cv);
    controls.enableDamping = true; controls.dampingFactor = 0.08; controls.enableZoom = false; controls.screenSpacePanning = true;
    controls.listenToKeyEvents(cv); controls.keyPanSpeed = 12;
    scene.add(new THREE.HemisphereLight(0xffffff, 0x3a3a44, 0.62));
    const sun = new THREE.DirectionalLight(0xffffff, 0.78); sun.position.set(60, 140, 90); scene.add(sun);
    const fill = new THREE.DirectionalLight(0xffffff, 0.28); fill.position.set(-90, 40, -70); scene.add(fill);

    /* ---------- utilidades de malha */
    const SPH = (seg) => new THREE.SphereGeometry(1, seg, Math.max(6, Math.round(seg * 0.7)));
    const CYL = new THREE.CylinderGeometry(1, 1, 1, 8, 1, true), CONE = new THREE.ConeGeometry(1, 1, 10);
    const M4 = new THREE.Matrix4(), Q = new THREE.Quaternion(), V = new THREE.Vector3(), V2 = new THREE.Vector3(), S3 = new THREE.Vector3(), UP = new THREE.Vector3(0, 1, 0), COL = new THREE.Color();
    const matAtom = () => new THREE.MeshPhongMaterial({ color: 0xffffff, shininess: 38, specular: 0x2a2a2a });
    const matGold = new THREE.MeshPhongMaterial({ color: 0xffffff, shininess: 85, specular: 0xb89a55 });
    // ouro metálico (PBR): reflete um "estúdio" virtual (RoomEnvironment), como o metal real; sem ele, cai no Phong
    let matMetal = matGold;
    if (THREE.RoomEnvironment && THREE.PMREMGenerator) {
      try { const pm = new THREE.PMREMGenerator(renderer); scene.environment = pm.fromScene(new THREE.RoomEnvironment(), 0.04).texture; pm.dispose();
        matMetal = new THREE.MeshStandardMaterial({ color: 0xffffff, metalness: 1, roughness: 0.3, envMapIntensity: 1.05 }); } catch (e) { matMetal = matGold; }
    }
    const clipPlane = new THREE.Plane(new THREE.Vector3(0, 0, -1), 0);
    function inst(geo, mat, n) { const m = new THREE.InstancedMesh(geo, mat, Math.max(1, n)); m.count = 0; m.instanceMatrix.setUsage(THREE.DynamicDrawUsage); return m; }
    function put(m, i, x, y, z, r, col) { M4.makeScale(r, r, r); M4.setPosition(x, y, z); m.setMatrixAt(i, M4); if (col) m.setColorAt(i, COL.set(col)); }
    function bond(m, i, a, b, r, col) {
      V.set(a[0], a[1], a[2]); V2.set(b[0], b[1], b[2]); const len = V.distanceTo(V2);
      Q.setFromUnitVectors(UP, V2.clone().sub(V).normalize()); S3.set(r, len, r);
      M4.compose(V.add(V2).multiplyScalar(0.5), Q, S3); m.setMatrixAt(i, M4); if (col) m.setColorAt(i, COL.set(col));
    }
    function finish(m, n) { m.count = n; m.instanceMatrix.needsUpdate = true; if (m.instanceColor) m.instanceColor.needsUpdate = true; }
    const meta = new Map();
    function dispose(obj) {
      obj.traverse((o) => { meta.delete(o); if (o.geometry && o.geometry !== CYL && o.geometry !== CONE) o.geometry.dispose();
        if (o.material && o.material !== matGold) { if (o.material.map) o.material.map.dispose(); o.material.dispose(); } });
    }
    const fmt = (x, d) => x.toFixed(d).replace(".", ",");
    function label(text, x, y, z, size, color, front) {
      const c = document.createElement("canvas"), g = c.getContext("2d"), fs = 46, font = `600 ${fs}px "IBM Plex Sans", system-ui, sans-serif`;
      g.font = font; const w = Math.ceil(g.measureText(text).width) + 28; c.width = w; c.height = fs + 22; g.font = font;
      g.fillStyle = theme.dark ? "rgba(20,20,24,0.8)" : "rgba(255,255,255,0.85)"; const rr = 14;
      g.beginPath(); g.moveTo(rr, 0); g.arcTo(w, 0, w, c.height, rr); g.arcTo(w, c.height, 0, c.height, rr); g.arcTo(0, c.height, 0, 0, rr); g.arcTo(0, 0, w, 0, rr); g.fill();
      g.fillStyle = color || theme.ink; g.textBaseline = "middle"; g.fillText(text, 14, c.height / 2 + 2);
      const tex = new THREE.CanvasTexture(c); tex.anisotropy = 4;
      // rótulos ficam atrás dos átomos quando a câmera gira (depthTest); só os títulos ("front") ficam sempre visíveis
      const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, depthTest: !front, depthWrite: false, transparent: true }));
      sp.scale.set(size * w / c.height, size, 1); sp.position.set(x, y, z); sp.renderOrder = 10; return sp;
    }
    function scaleBar(len, y, z, text, w) {
      const g = new THREE.Group(), mat = new THREE.MeshBasicMaterial({ color: new THREE.Color(theme.ink) }), m = new THREE.Mesh(new THREE.BoxGeometry(len, w, w), mat);
      m.position.set(0, y, z); g.add(m);
      [-len / 2, len / 2].forEach((x) => { const t = new THREE.Mesh(new THREE.BoxGeometry(w, w * 4, w), mat); t.position.set(x, y, z); g.add(t); });
      g.add(label(text, 0, y + w * 7, z, w * 7, null, true)); return g;
    }
    const pal = () => { const c = theme.cat; return { C: theme.dark ? "#9aa0aa" : "#5d626b", Csp3: c[4], O: "#e0473c", H: theme.dark ? "#e8e8ea" : "#f4f4f6", Au: "#e9b949",
      ion: "#f6d77a", mon: "#d9a52f", bond: theme.dark ? "#7c818b" : "#a7abb3", f111: c[0], f100: c[2], aresta: c[1], vertice: c[7], interface: c[6], interior: c[3],
      AuM: matMetal === matGold ? "#e9b949" : "#ffcf6e",
      // modo "grupos do GO": carbono pelo tipo e oxigênio pelo grupo funcional
      sp3: c[4], edge: c[5], cx: c[5], epoxi: c[1], hidroxila: c[0], eter: c[2], carbonila: c[7], carboxila: c[6], lactona: c[3], outro: "#9a9a9a" }; };
    const newGroup = (labels) => { const g = new THREE.Group(); g.userData.tv = themeV; g.userData.pick = []; if (labels) { const l = new THREE.Group(); l.name = "labels"; g.add(l); g.userData.labels = l; } root.add(g); return g; };

    /* ---------- cena */
    const root = new THREE.Group(); scene.add(root);
    let gAtom = null, gSyn = null, gMeso = null, gPl = null, sheet = null, part = null, sim = null, simRun = false, meso = null, plState = null;
    const halo = new THREE.Mesh(SPH(20), new THREE.MeshBasicMaterial({ color: 0xff3366, transparent: true, opacity: 0.35, depthWrite: false })); halo.visible = false; scene.add(halo);
    // folha de GO em formato único: átomos {e, x, y, z, k (tipo), side, g} + ligações; vem do modelo geométrico
    // (AUGO_N3CORE.buildSheet, O/C ajustável) ou de uma estrutura publicada (El-Machachi et al. 2024, site/data/gostruct)
    const KIND = ["sp2", "sp3", "edge", "epoxi", "hidroxila", "eter", "carbonila", "carboxila", "lactona", "outro", "H"];
    let cacheM = { key: "", raw: null, sh: null }; const cacheP = {};
    function modelSheet(L, ox) {
      const key = `${L}|${ox.toFixed(3)}`; if (cacheM.key === key) return cacheM.sh;
      const raw = K.buildSheet(L, ox), at = [], bonds = [];
      raw.C.forEach((c) => at.push({ e: "C", x: c.x, y: c.y, z: c.z, k: c.sp3 ? "sp3" : c.edge ? "edge" : "sp2", side: c.sp3 || 0 }));
      raw.bonds.forEach(([a, b]) => bonds.push([a, b]));
      const oIdx = new Map();
      raw.O.forEach((o) => { const i = at.length; at.push({ e: "O", x: o.x, y: o.y, z: o.z, k: o.g.type, side: o.g.side, g: o.g, dbl: o.dbl });
        if (o.g.type !== "carboxila") o.g.c.forEach((ci) => bonds.push([ci, i])); if (!o.dbl) oIdx.set(o.g, i); });
      raw.Cx.forEach((c) => { const i = at.length; at.push({ e: "C", x: c.x, y: c.y, z: c.z, k: "cx", side: 0, g: c.g }); bonds.push([c.from, i]);
        at.forEach((o, q) => { if (o.e === "O" && o.g === c.g) bonds.push([i, q]); }); });
      raw.H.forEach((h) => { const i = at.length; at.push({ e: "H", x: h.x, y: h.y, z: h.z, k: "H", side: h.g.side, g: h.g }); if (oIdx.has(h.g)) bonds.push([oIdx.get(h.g), i]); });
      const sh = { pub: false, raw, L, at, bonds, CO: raw.CO, sp3: raw.sp3frac, groups: raw.count, nC: raw.C.length + raw.Cx.length };
      cacheM = { key, raw, sh }; return sh;
    }
    // interface CALCULADA (code/atomistic/au_go_interface.py: GO-MACE-23 + MACE-MP-0 + D3): ouro antes/depois de relaxar,
    // átomos do GO que se moveram e as ligações Au–GO; só nas folhas publicadas, fora da síntese
    const MX = (opt.gostruct && opt.gostruct.mace) || null;
    const relaxData = (T) => (MX && MX.particles[T] && MX.particles[T].au ? MX.particles[T] : null);
    const relaxOn = () => !!(P.relax && P.scale === "atom" && P.mode !== "synth" && P.sheet !== "model" && relaxData(P.sheet));
    // modo "afinidade pelo ouro": cada tipo de sítio pela mediana da energia de adsorção de um Au calculada (mais intenso =
    // prende mais); só grupos de O e C de borda, onde há dado
    const AFF_K = { "O epóxi": "epoxi", "O hidroxila": "hidroxila", "O éter": "eter", "O carbonila": "carbonila", "O carboxila": "carboxila", "O lactona": "lactona", "C de borda": "edge", "C sp²": "sp2" };
    function affinity() {
      if (!MX || !MX.sites) return null;
      const S = MX.sites, Y = S.E_ads || S.E, med = {};
      for (const [ty, k] of Object.entries(AFF_K)) {
        const v = S.type.map((x, i) => (x === ty ? Y[i] : null)).filter((x) => x != null).sort((a, b) => a - b);
        if (v.length) med[k] = v.length % 2 ? v[(v.length - 1) / 2] : (v[v.length / 2 - 1] + v[v.length / 2]) / 2;
      }
      const lo = Math.min(...Object.values(med), -0.05), ramp = theme.seq && theme.seq.length > 1 ? theme.seq : ["#cde2fb", "#0d366b"];
      const col = (v) => { const t = Math.max(0, Math.min(1, v / lo)) * (ramp.length - 1), i = Math.min(ramp.length - 2, Math.floor(t));
        return "#" + new THREE.Color(ramp[i]).lerp(new THREE.Color(ramp[i + 1]), t - i).getHexString(); };
      const colors = {}; for (const [k, v] of Object.entries(med)) if (k !== "sp2") colors[k] = col(v);
      return { med, colors };
    }
    function pubSheet(T, rel) {
      const ck = T + (rel ? "|relaxada" : "");
      if (cacheP[ck]) return cacheP[ck];
      const sd = (opt.gostruct || { structures: [] }).structures.find((q) => q.T.replace(" ", "") === T); if (!sd) return modelSheet(110, P.ox);
      const c = sd.crop, at = [];
      for (let i = 0; i < c.n; i++) { const k = KIND[c.t[i]]; at.push({ e: k === "H" ? "H" : c.t[i] >= 3 ? "O" : "C", x: c.x[i] / 100, y: c.y[i] / 100, z: c.z[i] / 100, k, side: c.s[i] }); }
      const RX = rel ? relaxData(T) : null;
      if (RX) for (const [k, dx, dy, dz] of RX.moved) { at[k].x += dx / 100; at[k].y += dy / 100; at[k].z += dz / 100; at[k].moved = Math.hypot(dx, dy, dz) / 100; }
      const cut = { CC: 1.85, CO: 1.75, OC: 1.75, CH: 1.25, HC: 1.25, OH: 1.2, HO: 1.2 }, grid = new Map(), cell = 1.9, gk = (x, z) => `${Math.floor(x / cell)},${Math.floor(z / cell)}`, bonds = [];
      at.forEach((a, i) => { const k = gk(a.x, a.z); (grid.get(k) || grid.set(k, []).get(k)).push(i); });
      at.forEach((a, i) => { const cx = Math.floor(a.x / cell), cz = Math.floor(a.z / cell);
        for (let dx = -1; dx <= 1; dx++) for (let dz = -1; dz <= 1; dz++) for (const j of grid.get(`${cx + dx},${cz + dz}`) || []) {
          if (j <= i) continue; const b = at[j], lim = cut[a.e + b.e]; if (!lim) continue;
          if (Math.hypot(a.x - b.x, a.y - b.y, a.z - b.z) < lim) bonds.push([i, j]); } });
      const sh = { pub: true, sd, L: c.L, at, bonds, CO: 1 / sd.OC, sp3: sd.sp3_frac, edge: sd.edge_frac };
      cacheP[ck] = sh; return sh;
    }
    const sheetNow = (L) => (P.sheet === "model" ? modelSheet(L, P.ox) : pubSheet(P.sheet, relaxOn()));
    const oxSyn = () => { if (P.sheet === "model") return P.ox; const sd = (opt.gostruct || { structures: [] }).structures.find((q) => q.T.replace(" ", "") === P.sheet); return sd ? sd.OC : P.ox; };
    const INFO = {
      sp2: ["Carbono sp² do grafeno", "Três vizinhos a ~1,42 Å, rede em favo de mel; os elétrons π deslocalizados conduzem eletricidade."],
      sp3: ["Carbono sp³ (ligado a um grupo oxigenado)", "Sai do plano: a ligação com o O desfaz a ligação π e a folha deixa de conduzir ali."],
      edge: ["Carbono de borda", "Tem menos de três vizinhos de carbono: fica na borda da folha ou de um buraco, onde costuma carregar C=O, éter ou OH."],
      cx: ["Carbono da carboxila", "Carbono do grupo –COOH na borda da folha (C–C 1,50 Å)."],
      epoxi: ["Oxigênio · epóxi (C–O–C)", "Ponte entre dois carbonos vizinhos (C–O 1,46 Å); abundante no plano basal e o primeiro grupo a sair quando o GO é aquecido ou reduzido."],
      hidroxila: ["Oxigênio · hidroxila (C–OH)", "C–O 1,43 Å e O–H 0,97 Å; deixa o GO hidrofílico, ancora íons de ouro e é sítio de nucleação."],
      eter: ["Oxigênio · éter cíclico", "Ponte entre dois carbonos que não estão ligados entre si (anel com O), típica das bordas de buracos depois que o GO é aquecido."],
      carbonila: ["Oxigênio · carbonila (C=O)", "Dupla ligação C=O (~1,22 Å) nas bordas de buracos; cresce quando o GO perde epóxis no aquecimento."],
      carboxila: ["Oxigênio · carboxila (–COOH)", "Grupo ácido de borda: em água vira –COO⁻ e mantém as folhas dispersas pela repulsão de cargas."],
      lactona: ["Oxigênio · lactona / anidrido", "Éster cíclico na borda (O=C–O–C), formado quando grupos vizinhos se condensam."],
      outro: ["Oxigênio · outro arranjo", "Oxigênio fora dos grupos acima (por exemplo, água presa ou um O ligado a três átomos)."],
      H: ["Hidrogênio", "Do grupo hidroxila ou do ácido carboxílico (O–H ~0,97 Å)."],
    };
    // desenha a folha; skip(átomo) remove átomos (os grupos sob a partícula, no modelo)
    function sheetMeshes(g, sh, skip) {
      const p = pal(), grp = P.color === "groups", af = P.color === "affinity" ? affinity() : null, keep = sh.at.map((a) => !(skip && skip(a))), idx = new Int32Array(sh.at.length).fill(-1);
      const by = { C: [], O: [], H: [] }; sh.at.forEach((a, i) => { if (keep[i]) by[a.e].push(i); });
      const mk = (e, r, seg) => { const m = inst(SPH(seg), matAtom(), by[e].length), md = [];
        by[e].forEach((i, q) => { const a = sh.at[i]; idx[i] = q; put(m, q, a.x, a.y, a.z, r, af && af.colors[a.k] ? af.colors[a.k] : grp ? p[a.k] || p.C : e === "C" ? p.C : e === "O" ? (af ? "#9a9a9a" : p.O) : p.H);
          const inf = INFO[a.k] || INFO.sp2; md.push({ t: inf[0], p: [a.x, a.y, a.z], r, l: [inf[1], e === "O" ? `face ${a.side > 0 ? "de cima" : "de baixo"} da folha` : `posição (${(a.x / 10).toFixed(2)}; ${(a.z / 10).toFixed(2)}) nm`] }); });
        finish(m, by[e].length); meta.set(m, md); g.userData.pick.push(m); g.add(m); return m; };
      mk("C", 0.42, 12); mk("O", 0.55, 14); const mH = mk("H", 0.3, 10);
      const ok = sh.bonds.filter(([a, b]) => keep[a] && keep[b]), mB = inst(CYL, matAtom(), ok.length);
      ok.forEach(([a, b], k) => { const A = sh.at[a], Bb = sh.at[b]; bond(mB, k, [A.x, A.y, A.z], [Bb.x, Bb.y, Bb.z], A.e === "H" || Bb.e === "H" ? 0.1 : (A.dbl || Bb.dbl) ? 0.17 : 0.13, p.bond); });
      finish(mB, ok.length); g.add(mB);
      mH.visible = P.hyd; mH.userData.hyd = true;
      return sh.at.filter((a, i) => keep[i] && a.e === "O");
    }

    /* ---------- escala atômica: GO + uma AuNP (modos explorar e plásmon) */
    function buildAtomic() {
      if (gAtom) { root.remove(gAtom); dispose(gAtom); }
      gAtom = newGroup(true); clearSel();
      sheet = sheetNow(110); const RX = relaxOn() ? relaxData(P.sheet) : null;
      part = K.buildParticle(RX ? RX.d_input : P.d, RX ? RX.adh_input : P.adh); part.relax = RX;
      const foot = part.foot;
      // na estrutura publicada a folha é ondulada: a partícula pousa nos átomos mais altos sob ela (Au–C ~3,3 Å, Au–O ~2,2 Å);
      // no modelo, os grupos da face de cima sob a partícula saem (foi ali que ela nucleou)
      let shift = 0;
      if (RX) {                                         // a mesma partícula, pousada pela mesma regra; depois anima até a relaxada
        shift = Math.min(...RX.au.map((q) => q[1])) / 100 - K.Y_AU;                 // alturas e centro: geometria relaxada
        part.P.forEach((q, i) => { q[0] = RX.au0[i][0] / 100; q[1] = RX.au0[i][1] / 100; q[2] = RX.au0[i][2] / 100; });
        part.center = [0, 1, 2].map((k) => RX.au.reduce((a, q) => a + q[k], 0) / RX.au.length / 100);
      } else if (sheet.pub) { const off = { C: 3.25, O: 2.15, H: 2.0 }; let top = -1e9;
        for (const a of sheet.at) if (Math.hypot(a.x, a.z) < foot + 1) top = Math.max(top, a.y + off[a.e]);
        shift = top - K.Y_AU; part.P.forEach((q) => { q[1] += shift; }); part.center[1] += shift; }
      part.shift = shift;
      const skip = sheet.pub ? null : (a) => a.g && a.g.side > 0 && Math.hypot(a.g.x, a.g.z) < foot + 0.8;
      const Oat = sheetMeshes(gAtom, sheet, skip);
      const p = pal(), mAu = inst(SPH(part.N > 3000 ? 12 : 16), P.color === "site" ? matGold : matMetal, part.N), md = [];
      part.P.forEach((q, i) => { const c = part.cls[i]; put(mAu, i, q[0], q[1], q[2], 1.36, P.color === "site" ? p[c.cls] : p.AuM);
        md.push({ t: `Ouro · ${CLS[c.cls]}`, p: q, au: true, r: 1.36, l: [`Número de coordenação ${c.cn}: vizinhos a 2,88 Å (no interior do cristal são 12).`,
          c.cls === "interior" ? "Átomo do volume: tem todos os vizinhos; só aparece com o corte." : c.cn <= 7 ? "Sítio de baixa coordenação: o mais reativo (catálise, adsorção de tióis)." : "Átomo de superfície: onde ligantes e moléculas se prendem.",
          `altura ${((q[1] - K.Y_AU - shift) / 10).toFixed(2)} nm acima do primeiro plano`] }); });
      finish(mAu, part.N); [matGold, matMetal].forEach((m) => { m.clippingPlanes = P.clip ? [clipPlane] : []; m.needsUpdate = true; });
      gAtom.add(mAu); meta.set(mAu, md); gAtom.userData.pick.push(mAu); part.mesh = mAu;
      // âncoras Au–O: oxigênios da face de cima junto ao perímetro de contato (ou logo abaixo do primeiro plano);
      // na interface calculada, as ligações Au–O e Au–C que o cálculo formou (aparecem quando a relaxação termina)
      const yb = K.Y_AU + shift, base = part.P.filter((q) => q[1] < yb + 0.3), anc = [];
      relaxAnim = null; relaxExtra = null;
      if (RX) {
        // as ligações vão na cena; o rótulo, no grupo de rótulos (que o controle "rótulos" esconde); os dois aparecem no fim
        const mB = inst(CYL, new THREE.MeshPhongMaterial({ color: new THREE.Color(theme.ink), shininess: 25 }), RX.bonds.length);
        RX.bonds.forEach(([k, gi], j) => { const a = sheet.at[gi], q = RX.au[k]; bond(mB, j, [q[0] / 100, q[1] / 100, q[2] / 100], [a.x, a.y, a.z], 0.15); });
        finish(mB, RX.bonds.length); mB.visible = false; gAtom.add(mB); relaxExtra = [mB];
        const bo = RX.bonds.filter(([, gi]) => sheet.at[gi].e === "O").sort((a, b) => a[2] - b[2])[0];
        if (bo) { const a = sheet.at[bo[1]], q = RX.au[bo[0]];
          const lb = label(`ligação Au–O ${fmt(bo[2], 2)} Å (${INFO[a.k] ? INFO[a.k][0].replace("Oxigênio · ", "") : "O"})`, (a.x + q[0] / 100) / 2, Math.max(a.y, q[1] / 100) + 4.2, (a.z + q[2] / 100) / 2, 1.7, theme.ink);
          lb.visible = false; gAtom.userData.labels.add(lb); relaxExtra.push(lb); }
        relaxAnim = { from: RX.au0.map((q) => q.map((v) => v / 100)), to: RX.au.map((q) => q.map((v) => v / 100)), t0: performance.now() + 500, dur: 2600, mesh: mAu };
        part.anchors = RX.bonds.filter(([, gi]) => sheet.at[gi].e === "O").length;
      }
      for (const o of RX ? [] : Oat) { if (o.side < 0 || o.k === "carboxila") continue; const rr = Math.hypot(o.x, o.z); if (rr > foot + 3.5 || (!sheet.pub && rr < foot - 2)) continue;
        let best = null, bd = 9; for (const b of base) { const d = Math.hypot(b[0] - o.x, b[1] - o.y, b[2] - o.z); if (d < bd) { bd = d; best = b; } }
        if (best && bd < (sheet.pub ? 3.6 : 5.2)) anc.push([o, best, bd]); }
      anc.sort((a, b) => a[2] - b[2]);
      const lineMat = new THREE.LineDashedMaterial({ color: new THREE.Color(theme.ink), dashSize: 0.4, gapSize: 0.3 });
      anc.slice(0, 10).forEach(([o, b]) => { const ln = new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(o.x, o.y, o.z), new THREE.Vector3(...b)]), lineMat); ln.computeLineDistances(); gAtom.add(ln); });
      if (!RX) part.anchors = Math.min(10, anc.length);
      // rótulos e barra de escala
      const gl = gAtom.userData.labels, top = part.P.reduce((a, q) => (q[1] > a[1] ? q : a));
      gl.add(label(RX ? `AuNP relaxada (cálculo) · ${part.N} átomos · adesão ${fmt(-RX.E_adh_eV, 1)} eV` : `AuNP ≈ ${fmt(part.d, 1)} nm · ${part.N} átomos de Au`, 0, top[1] + 7, 0, 2.6, null, true));
      const fa = part.P.findIndex((q, i) => part.cls[i].cls === "f111" && q[1] > top[1] - 0.5);
      if (fa >= 0) gl.add(label("face (111)", part.P[fa][0], part.P[fa][1] + 3.2, part.P[fa][2], 1.9, p.f111));
      const f1 = part.P.findIndex((q, i) => part.cls[i].cls === "f100");
      if (f1 >= 0) { const q = part.P[f1], u = Math.hypot(q[0], q[2]) || 1; gl.add(label("face (100)", q[0] + 4 * q[0] / u, q[1] + 1, q[2] + 4 * q[2] / u, 1.9, p.f100)); }
      const shown = new Set();
      for (const o of Oat) { if (shown.has(o.k) || o.side < 0 || Math.hypot(o.x, o.z) < foot + 8 || o.z < -10 || Math.abs(o.x) > 42 || o.k === "outro") continue;
        shown.add(o.k); gl.add(label(INFO[o.k][0].replace("Oxigênio · ", ""), o.x, o.y + 3.2, o.z, 1.7, P.color === "groups" ? p[o.k] : "#e0473c")); }
      if (sheet.pub) { const e = sheet.at.find((a) => a.k === "edge" && a.z > 8 && Math.abs(a.x) < 38 && Math.hypot(a.x, a.z) > foot + 10);
        if (e) gl.add(label("borda de buraco", e.x, e.y + 3.4, e.z, 1.7, P.color === "groups" ? p.edge : null)); }
      const sp2 = sheet.at.find((c) => c.e === "C" && c.k === "sp2" && c.x > 18 && c.x < 40 && c.z > 18 && c.z < 40 && !sheet.at.some((q) => q.e === "O" && Math.hypot(q.x - c.x, q.z - c.z) < 6));
      if (sp2) gl.add(label("ilha sp² (grafeno intacto)", sp2.x, sp2.y + 3, sp2.z, 1.7));
      if (anc.length) { const [o] = anc[0]; gl.add(label("ancoragem Au–O", o.x, o.y + 4.6, o.z, 1.6, theme.ink)); }
      const sb = scaleBar(10, 0.2, 26, "1 nm", 0.35); sb.position.x = 30; if (sheet.pub) sb.position.y = Math.max(...sheet.at.filter((a) => Math.abs(a.x - 30) < 6 && Math.abs(a.z - 26) < 3).map((a) => a.y), 0) + 0.6; gAtom.add(sb);
      buildPlasmon(); applyMode(); emit();
    }

    /* ---------- plásmon: a nuvem de elétrons oscila com o campo elétrico da luz */
    let pl = null;
    function buildPlasmon() {
      gPl = new THREE.Group(); const R = Math.max(part.width, part.height) / 2 * 0.96, c = part.center;
      // nuvem desenhada só pelo lado de trás: aparece como um halo em volta da partícula sem tingir o ouro
      const cloud = new THREE.Mesh(SPH(28), new THREE.MeshPhongMaterial({ color: 0x4f8dff, transparent: true, opacity: 0.34, depthWrite: false, shininess: 10, side: THREE.BackSide }));
      cloud.scale.set(R, R, R); cloud.position.set(...c); gPl.add(cloud);
      const minus = label("− elétrons", 0, 0, 0, 2.4, "#2a78d6"), plus = label("+ íons de Au", 0, 0, 0, 2.4, "#e34948"); gPl.add(minus, plus);
      const n = 34, arrows = inst(CYL, new THREE.MeshBasicMaterial({ color: 0xffffff }), n), heads = inst(CONE, new THREE.MeshBasicMaterial({ color: 0xffffff }), n), NP = 240;
      const cg = new THREE.BufferGeometry(); cg.setAttribute("position", new THREE.BufferAttribute(new Float32Array(NP * 3), 3));
      const curve = new THREE.Line(cg, new THREE.LineBasicMaterial({ color: 0xffffff }));
      gPl.add(arrows, heads, curve);
      pl = { cloud, minus, plus, arrows, heads, curve, R, c, n, NP, txt: null, t: 0, lamShown: -1 };
      gPl.visible = false; gAtom.add(gPl);
    }
    function extAt(d, lam) {                       // extinção de Mie relativa ao pico para o diâmetro d (nm), em λ (nm)
      let bi = 0; O.d.forEach((x, i) => { if (Math.abs(Math.log(x / d)) < Math.abs(Math.log(O.d[bi] / d))) bi = i; });
      const row = O.C_ext[bi]; let j = 0; while (j < O.wl.length - 2 && O.wl[j + 1] < lam) j++;
      const f = (lam - O.wl[j]) / (O.wl[j + 1] - O.wl[j]), v = row[j] + f * (row[j + 1] - row[j]);
      let mx = 0, lpk = O.wl[0]; row.forEach((x, i) => { if (O.wl[i] >= 450 && x > mx) { mx = x; lpk = O.wl[i]; } });
      return { rel: Math.max(0, v / mx), peak: lpk };
    }
    function stepPlasmon(dt) {
      if (!pl || !gPl.visible) return;
      // onda plana viajando da esquerda para a direita (+x), com o campo elétrico na vertical (y); a nuvem de elétrons
      // oscila na mesma direção do campo. Depois da partícula a onda sai mais fraca: parte foi absorvida ou espalhada.
      pl.t += dt; const lam = P.lam, { rel, peak } = extAt(part.d, lam), rgb = waveRGB(lam), w = 2 * Math.PI * 0.75, ph = Math.sin(w * pl.t), c = pl.c;
      const dy = 0.3 * pl.R * Math.max(0.04, rel) * ph;
      pl.cloud.position.set(c[0], c[1] + dy, c[2]);
      const sg = Math.sign(dy) || 1, op = Math.min(1, Math.abs(ph) * 1.4) * Math.max(0.25, rel);
      pl.minus.position.set(c[0] + pl.R + 9, c[1] + sg * pl.R * 0.62, c[2]); pl.plus.position.set(c[0] + pl.R + 9, c[1] - sg * pl.R * 0.62, c[2]);
      pl.minus.material.opacity = pl.plus.material.opacity = op;
      const k = 2 * Math.PI / 26, A0 = 8, x0 = c[0] - 80, x1 = c[0] + 80, zw = c[2] - pl.R - 10, arr = pl.curve.geometry.attributes.position.array;
      const amp = (x) => (x < c[0] ? A0 : A0 * (1 - 0.55 * rel)) * Math.sin(k * x - w * pl.t);
      for (let i = 0; i < pl.NP; i++) { const x = x0 + (x1 - x0) * i / (pl.NP - 1); arr[3 * i] = x; arr[3 * i + 1] = c[1] + amp(x); arr[3 * i + 2] = zw; }
      pl.curve.geometry.attributes.position.needsUpdate = true; pl.curve.material.color.setRGB(...rgb);
      for (let i = 0; i < pl.n; i++) {
        const x = x0 + (x1 - x0) * (i + 0.5) / pl.n, A = amp(x);
        if (Math.abs(A) < 0.5) { M4.makeScale(0, 0, 0); pl.arrows.setMatrixAt(i, M4); pl.heads.setMatrixAt(i, M4); continue; }
        bond(pl.arrows, i, [x, c[1], zw], [x, c[1] + A * 0.82, zw], 0.16);
        V.set(0, Math.sign(A), 0); Q.setFromUnitVectors(UP, V); S3.set(0.5, 1.2, 0.5); V2.set(x, c[1] + A * 0.9, zw); M4.compose(V2, Q, S3); pl.heads.setMatrixAt(i, M4);
      }
      finish(pl.arrows, pl.n); finish(pl.heads, pl.n); pl.arrows.material.color.setRGB(...rgb); pl.heads.material.color.setRGB(...rgb);
      if (Math.abs(pl.lamShown - lam) >= 1) {
        pl.lamShown = lam;
        if (pl.txt) { gPl.remove(pl.txt); pl.txt.material.map.dispose(); pl.txt.material.dispose(); }
        pl.txt = label(`luz de ${Math.round(lam)} nm (${colorName(lam)}) →`, x0 + 22, c[1] + A0 + 5, zw, 2.4, null, true); gPl.add(pl.txt);
        plState = { lam, rel, peak }; opt.onPlasmon && opt.onPlasmon(plState);
      }
    }

    /* ---------- síntese ao vivo */
    let simMesh = null, simFrame = 0, synSheet = null;
    function buildSynthesis(keep) {
      if (gSyn) { root.remove(gSyn); dispose(gSyn); }
      gSyn = newGroup(true); clearSel();
      const sh = modelSheet(90, oxSyn()); synSheet = sh; sheetMeshes(gSyn, sh, null);
      if (!keep || !sim) { sim = K.Synthesis(sh.raw, { red: K.REDUCERS[P.red], T: P.T, nAu: 1400, seed: 11 }); simFrame = 0; }
      const p = pal(), n = sim.n;
      const ions = inst(SPH(8), new THREE.MeshPhongMaterial({ color: new THREE.Color(p.ion), transparent: true, opacity: 0.55, shininess: 20 }), n);
      const mons = inst(SPH(10), new THREE.MeshPhongMaterial({ color: new THREE.Color(p.mon), shininess: 60, specular: 0x886622 }), n);
      const atoms = inst(SPH(12), matMetal, n); matGold.clippingPlanes = []; matMetal.clippingPlanes = [];
      gSyn.add(ions, mons, atoms); simMesh = { ions, mons, atoms };
      const box = new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.BoxGeometry(90, 36, 90)), new THREE.LineBasicMaterial({ color: new THREE.Color(theme.muted), transparent: true, opacity: 0.4 }));
      box.position.set(0, 18, 0); gSyn.add(box);
      const gl = gSyn.userData.labels;
      gl.add(label("solução: Au³⁺ (íons, amarelo claro) e Au⁰ (átomos livres, dourado)", 0, 42, -45, 2.4, null, true));
      gl.add(label("os oxigênios da face de cima do GO são sítios de nucleação", 0, -5, 49, 2.2));
      const sb = scaleBar(10, 0.2, 30, "1 nm", 0.35); sb.position.x = 26; gSyn.add(sb);
      drawSim(); applyMode(); emit();
    }
    function drawSim() {
      if (!sim || !simMesh) return; const au = pal().AuM; let a = 0, b = 0, c = 0;
      for (let i = 0; i < sim.n; i++) { const x = sim.pos[3 * i], y = sim.pos[3 * i + 1], z = sim.pos[3 * i + 2], s = sim.st[i];
        if (s === 0) put(simMesh.ions, a++, x, y, z, 0.8); else if (s === 1) put(simMesh.mons, b++, x, y, z, 1.0); else put(simMesh.atoms, c++, x, y, z, 1.36, au); }
      finish(simMesh.ions, a); finish(simMesh.mons, b); finish(simMesh.atoms, c);
    }

    /* ---------- escala de partículas (nm): flocos de GO com muitas AuNP; vista 3D ou "TEM" */
    function flake(cx, cz, rad, seed, dy) {
      const r = K.rng(seed), nv = 9, poly = Array.from({ length: nv }, (_, i) => { const a = 2 * Math.PI * i / nv, rr = rad * (0.72 + 0.4 * r()); return [cx + rr * Math.cos(a), cz + rr * Math.sin(a)]; });
      const inside = (x, z) => { let c = false; for (let i = 0, j = nv - 1; i < nv; j = i++) { const [xi, zi] = poly[i], [xj, zj] = poly[j]; if ((zi > z) !== (zj > z) && x < (xj - xi) * (z - zi) / (zj - zi) + xi) c = !c; } return c; };
      const h = (x, z) => dy + 3.2 * Math.sin(x / 23 + seed) * Math.cos(z / 31) + 1.8 * Math.sin((x + z) / 13 + seed * 0.7) + 9 * Math.exp(-(((x - cx) * 0.6 + (z - cz) * 0.8 - rad * 0.2) ** 2) / 120);
      const N = 200, x0 = cx - rad * 1.2, z0 = cz - rad * 1.2, st = rad * 2.4 / N, pos = [], idx = [];
      for (let i = 0; i <= N; i++) for (let j = 0; j <= N; j++) { const x = x0 + i * st, z = z0 + j * st; pos.push(x, h(x, z), z); }
      for (let i = 0; i < N; i++) for (let j = 0; j < N; j++) { const a = i * (N + 1) + j, b = a + N + 1;
        if (inside(x0 + (i + 0.5) * st, z0 + (j + 0.5) * st)) idx.push(a, a + 1, b, b, a + 1, b + 1); }
      const geo = new THREE.BufferGeometry(); geo.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3)); geo.setIndex(idx); geo.computeVertexNormals();
      let area = 0; for (let k = 0; k < idx.length; k += 3) area += st * st / 2;
      return { geo, inside, h, area };
    }
    function buildMeso() {
      if (gMeso) { root.remove(gMeso); dispose(gMeso); }
      gMeso = newGroup(true); clearSel();
      const fl = [flake(-30, -10, 170, 3, 0), flake(95, 80, 110, 5, 4)];
      fl.forEach((f, i) => { const mat = P.tem ? new THREE.MeshBasicMaterial({ color: i ? 0xa6a6a6 : 0xbdbdbd, side: THREE.DoubleSide })
        : new THREE.MeshPhongMaterial({ color: new THREE.Color(theme.dark ? "#6f6253" : "#8c7a66"), side: THREE.DoubleSide, shininess: 12, transparent: true, opacity: 0.93 });
        gMeso.add(new THREE.Mesh(f.geo, mat)); });
      // diâmetros log-normais (mediana P.md, desvio relativo P.msig), sem sobreposição, até cobrir a fração P.cov da área
      const r = K.rng(21), sl = Math.sqrt(Math.log(1 + P.msig * P.msig)), area = fl[0].area + fl[1].area * 0.6, list = [], grid = new Map();
      let covered = 0, tries = 0;
      while (covered < P.cov * area && tries < 60000 && list.length < 5000) {
        tries++;
        const z0 = Math.sqrt(-2 * Math.log(r() || 1e-9)) * Math.cos(2 * Math.PI * r()), d = Math.min(150, Math.max(1.5, P.md * Math.exp(sl * z0)));
        const x = (r() - 0.5) * 440 + 20, z = (r() - 0.5) * 440 + 20, f = fl[1].inside(x, z) ? fl[1] : fl[0].inside(x, z) ? fl[0] : null;
        if (!f) continue;
        const cx = Math.floor(x / 20), cz = Math.floor(z / 20); let ok = true;
        for (let dx = -3; dx <= 3 && ok; dx++) for (let dz = -3; dz <= 3 && ok; dz++) for (const q of grid.get(`${cx + dx},${cz + dz}`) || []) if (Math.hypot(q.x - x, q.z - z) < (q.d + d) / 2 + 0.8) { ok = false; break; }
        if (!ok) continue;
        const it = { x, y: f.h(x, z) + d / 2 + 0.4, z, d }, gk = `${cx},${cz}`; list.push(it); (grid.get(gk) || grid.set(gk, []).get(gk)).push(it); covered += Math.PI * d * d / 4;
      }
      const mP = inst(SPH(18), P.tem ? new THREE.MeshBasicMaterial({ color: 0xffffff }) : P.mcolor === "mie" ? matGold : matMetal, list.length), md = [];
      matGold.clippingPlanes = []; matMetal.clippingPlanes = [];
      list.forEach((q, i) => { put(mP, i, q.x, q.y, q.z, q.d / 2, P.tem ? "#161616" : P.mcolor === "mie" ? opt.colorOf(q.d) : pal().AuM);
        md.push({ t: `Nanopartícula de ouro · ${fmt(q.d, 1)} nm`, p: [q.x, q.y, q.z], au: true, r: q.d / 2, l: [`≈ ${Math.round(K.RHO_AU * 1000 * Math.PI / 6 * q.d ** 3).toLocaleString("pt-BR")} átomos de Au`,
          `pico do plásmon ≈ ${Math.round(opt.lsprOf(q.d))} nm (Mie)`, `cor de uma dispersão deste tamanho: ${opt.colorOf(q.d)}`] }); });
      finish(mP, list.length); gMeso.add(mP); meta.set(mP, md); gMeso.userData.pick.push(mP);
      meso = { list, covered: covered / area };
      const gl = gMeso.userData.labels;
      gl.add(label("folha de GO: ~1 nm de espessura e centenas de nm de largura", -30, 26, -150, 9));
      gl.add(label("dobras e rugas: a folha não é plana", 95, 30, 150, 8));
      const sb = scaleBar(50, 2, 150, "50 nm", 1.6); sb.position.x = 90; gMeso.add(sb);
      applyMode(); emit();
    }

    /* ---------- modos, câmera e estado */
    let tween = null;
    function camTo(pos, tgt, ms = 1100) { tween = { p0: camera.position.clone(), t0: controls.target.clone(), p1: new THREE.Vector3(...pos), t1: new THREE.Vector3(...tgt), s: performance.now(), ms }; ensureLoop(); }
    const HOME = { explore: [[78, 58, 102], [0, 9, 0]], plasmon: [[6, 30, 112], [0, 13, 0]], synth: [[70, 66, 108], [0, 12, 0]], meso: [[250, 230, 330], [10, 0, 10]] };
    const homeOf = () => (P.scale === "meso" ? HOME.meso : HOME[P.mode]);
    function applyMode() {
      const atom = P.scale === "atom", syn = atom && P.mode === "synth", tem = !atom && P.tem;
      if (gAtom) gAtom.visible = atom && !syn; if (gSyn) gSyn.visible = syn; if (gMeso) gMeso.visible = !atom;
      if (gPl) gPl.visible = atom && P.mode === "plasmon";
      [gAtom, gSyn, gMeso].forEach((g) => { if (g && g.userData.labels) g.userData.labels.visible = P.labels && !tem; });
      cam = tem ? ortho : camera; controls.enabled = !tem;
      scene.background = new THREE.Color(tem ? "#e4e4e4" : theme.surface);
      scene.fog = atom ? new THREE.Fog(new THREE.Color(theme.surface), 230, 430) : null;
      halo.visible = halo.visible && !!sel; resize();
    }
    function rebuild(ch) {
      if (P.scale === "meso") { if (!gMeso || gMeso.userData.tv !== themeV || ch.meso || ch.tem || ch.mcolor) buildMeso(); else applyMode(); return; }
      if (P.mode === "synth") {
        if (ch.synth || ch.ox || ch.sheet || !sim) buildSynthesis(false); else if (!gSyn || gSyn.userData.tv !== themeV || ch.color) buildSynthesis(true); else applyMode(); return;
      }
      if (!gAtom || gAtom.userData.tv !== themeV || ch.d || ch.adh || ch.ox || ch.color || ch.sheet || ch.relax || (ch.mode && part && !!part.relax !== relaxOn())) buildAtomic(); else applyMode();
    }
    function emit() { opt.onStats && opt.onStats(stats()); }
    function stats() {
      const s = { P: { ...P } };
      if (part) Object.assign(s, { d: part.d, N: part.N, surfFrac: part.surfFrac, lowCN: part.lowCN, count: part.count, anchors: part.anchors, foot: part.foot, height: part.height });
      const sh = P.scale === "atom" && P.mode === "synth" && synSheet ? synSheet : sheet;      // a síntese usa a folha-modelo (com o O/C da publicada)
      if (sh) Object.assign(s, { CO: sh.CO, sp3: sh.sp3, groups: sh.groups, nC: sh.nC, pub: sh.pub ? sh.sd : null, synFrom: sh === synSheet && P.sheet !== "model" ? P.sheet : null });
      if (sim) Object.assign(s, { sim: sim.stats(), hist: sim.hist, Sstar: sim.Sstar, running: simRun, sizes: sim.clusters.map((c) => c.occ.size).filter((x) => x >= 4).map(K.deq) });
      if (meso) Object.assign(s, { meso: meso.list.map((q) => q.d), coverage: meso.covered });
      if (plState) s.plasmon = plState;
      if (part && part.relax && P.mode !== "synth" && P.scale === "atom") s.relax = { ...part.relax, au0: undefined, au: undefined, moved: undefined, bonds: undefined, anim: !!relaxAnim };
      return s;
    }

    /* ---------- seleção e informação */
    const ray = new THREE.Raycaster(), ptr = new THREE.Vector2(); let sel = null, hoverT = 0;
    const tip = document.createElement("div"); tip.className = "n3-tip"; tip.hidden = true; host.appendChild(tip);
    const shown = (o) => { while (o) { if (!o.visible) return false; o = o.parent; } return true; };
    function clearSel() { sel = null; halo.visible = false; opt.onPick && opt.onPick(null); ensureLoop(); }
    function pick(ev) {
      const rc = cv.getBoundingClientRect(); ptr.set(((ev.clientX - rc.left) / rc.width) * 2 - 1, -((ev.clientY - rc.top) / rc.height) * 2 + 1);
      ray.setFromCamera(ptr, cam);
      const vis = [gAtom, gSyn, gMeso].filter((g) => g && g.visible).flatMap((g) => g.userData.pick).filter(shown);
      const hit = ray.intersectObjects(vis, false).find((h) => h.instanceId != null);
      const md = hit && meta.get(hit.object); return md ? md[hit.instanceId] : null;
    }
    cv.addEventListener("pointermove", (ev) => {
      const now = performance.now(); if (now - hoverT < 70 || ev.buttons) return; hoverT = now;
      const m = pick(ev); if (!m) { tip.hidden = true; cv.style.cursor = ""; return; }
      cv.style.cursor = "pointer"; const rc = host.getBoundingClientRect();
      tip.textContent = m.t; tip.hidden = false; tip.style.left = `${Math.min(ev.clientX - rc.left + 14, rc.width - 250)}px`; tip.style.top = `${ev.clientY - rc.top + 14}px`;
    });
    let downAt = null;
    cv.addEventListener("pointerdown", (ev) => { downAt = [ev.clientX, ev.clientY]; controls.enableZoom = true; });
    cv.addEventListener("pointerleave", () => { tip.hidden = true; controls.enableZoom = false; });
    cv.addEventListener("pointerup", (ev) => {
      if (!downAt || Math.hypot(ev.clientX - downAt[0], ev.clientY - downAt[1]) > 4) return;
      const m = pick(ev); if (!m) { clearSel(); return; }
      const dist = sel && sel !== m ? Math.hypot(m.p[0] - sel.p[0], m.p[1] - sel.p[1], m.p[2] - sel.p[2]) : null, prev = sel;
      sel = m; halo.position.set(...m.p); halo.scale.setScalar((m.r || 1) * 1.6); halo.visible = true; ensureLoop();
      opt.onPick && opt.onPick({ ...m, dist, prev: prev && prev.t, scale: P.scale });
    });
    // a roda do mouse rola a página; aproxima com Ctrl/Shift + roda ou depois de clicar na cena
    const hint = document.createElement("div"); hint.className = "n3-hint"; hint.textContent = "Ctrl + roda do mouse (ou clique na cena) para aproximar"; hint.hidden = true; host.appendChild(hint);
    let hintT = 0;
    cv.addEventListener("wheel", (ev) => {
      if (controls.enableZoom && cam === camera) return;
      if (ev.ctrlKey || ev.shiftKey || ev.metaKey || cam === ortho) { ev.preventDefault(); zoom(ev.deltaY > 0 ? 1.12 : 1 / 1.12); return; }
      hint.hidden = false; clearTimeout(hintT); hintT = setTimeout(() => { hint.hidden = true; }, 1500);
    }, { passive: false });
    function zoom(f) {
      if (cam === ortho) { ortho.zoom = Math.max(0.3, Math.min(10, ortho.zoom / f)); ortho.updateProjectionMatrix(); ensureLoop(); return; }
      camera.position.copy(controls.target).add(camera.position.clone().sub(controls.target).multiplyScalar(f)); ensureLoop();
    }

    /* ---------- interface calculada: o ouro sai da posição "pousada" e vai até a relaxada; as ligações aparecem no fim */
    let relaxAnim = null, relaxExtra = null;
    function stepRelax(now) {
      const A = relaxAnim, f = Math.max(0, Math.min(1, (now - A.t0) / A.dur)), e = 1 - Math.pow(1 - f, 3);
      part.P.forEach((q, i) => { const a = A.from[i], b = A.to[i]; q[0] = a[0] + (b[0] - a[0]) * e; q[1] = a[1] + (b[1] - a[1]) * e; q[2] = a[2] + (b[2] - a[2]) * e;
        put(A.mesh, i, q[0], q[1], q[2], 1.36); });
      finish(A.mesh, part.N);
      if (f >= 1) { relaxAnim = null; if (relaxExtra) relaxExtra.forEach((o) => { o.visible = true; }); emit(); }
    }

    /* ---------- laço de desenho: só roda com a cena visível na tela */
    let active = false, last = performance.now(), raf = 0, sweep = false;
    let dirty = true;                                    // há algo novo para desenhar
    const ensureLoop = () => { dirty = true; if (active && !raf) { last = performance.now(); raf = requestAnimationFrame(loop); } };
    new IntersectionObserver((es) => { active = es.some((e) => e.isIntersecting); ensureLoop(); }, { threshold: 0.01 }).observe(host);
    // desenha sob demanda: com a câmera parada e nada animando, o laço dorme (poupa bateria e GPU)
    controls.addEventListener("change", () => ensureLoop());
    function loop(now) {
      raf = 0; if (!active) return;
      const dt = Math.min(0.05, (now - last) / 1000); last = now;
      if (tween) { const f = Math.min(1, (now - tween.s) / tween.ms), e = f < 0.5 ? 2 * f * f : 1 - Math.pow(-2 * f + 2, 2) / 2;
        camera.position.lerpVectors(tween.p0, tween.p1, e); controls.target.lerpVectors(tween.t0, tween.t1, e); if (f >= 1) tween = null; dirty = true; }
      if (controls.update()) dirty = true;
      const anim = (P.scale === "atom" && ((P.mode === "synth" && simRun) || P.mode === "plasmon" || (relaxAnim && P.mode !== "synth"))) || sweep;
      if (!dirty && !anim) return;                         // nada mudou: não pede outro quadro
      dirty = false;
      if (P.scale === "atom" && P.mode === "synth" && sim && simRun) {
        for (let k = 0; k < P.speed; k++) sim.step();
        drawSim(); simFrame++;
        const s = sim.stats(); if (simFrame % 8 === 0 || s.done) emit();
        if (s.done) { simRun = false; emit(); }
      }
      if (P.scale === "atom" && P.mode === "plasmon") stepPlasmon(dt);
      if (relaxAnim && P.scale === "atom" && P.mode !== "synth") stepRelax(now);
      if (sweep) { P.lam = Math.min(780, P.lam + dt * 55); opt.onLam && opt.onLam(P.lam); if (P.lam >= 780) sweep = false; }
      renderer.render(scene, cam);
      raf = requestAnimationFrame(loop);
    }
    function resize() {
      const w = host.clientWidth || 800, h = host.clientHeight || 520; renderer.setSize(w, h, false);
      camera.aspect = w / h; camera.updateProjectionMatrix();
      const half = 235; ortho.left = -half * w / h; ortho.right = half * w / h; ortho.top = half; ortho.bottom = -half;
      ortho.position.set(15, 800, 15); ortho.up.set(0, 0, -1); ortho.lookAt(15, 0, 15); ortho.updateProjectionMatrix(); ensureLoop();
    }
    new ResizeObserver(resize).observe(host);

    /* ---------- roteiro guiado */
    const TOUR = [
      { t: "A folha de grafeno", x: "Cada bolinha cinza é um átomo de carbono, ligado a três vizinhos a 1,42 Å: a rede em favo de mel. A folha tem um átomo de espessura (0,34 nm) e conduz eletricidade pelos elétrons π, espalhados por toda a rede. Aqui, a folha-modelo quase sem oxigênio.", s: { scale: "atom", mode: "explore", sheet: "model", ox: 0.05, color: "element", clip: false, relax: false }, cam: [[44, 34, 76], [18, 8, 18]] },
      { t: "Oxidação: o óxido de grafeno (GO)", x: "Agora uma estrutura publicada de GO (El-Machachi et al. 2024): 2 ns de dinâmica molecular a 900 K com um potencial de aprendizado de máquina treinado em DFT (GO-MACE-23), depois otimizada. Epóxi (laranja) e hidroxila (azul) cobrem o plano basal; os carbonos ligados ao O viram sp³ (rosa) e a folha ondula. Este GO tem O/C ≈ 0,35: um oxigênio para cada três carbonos.", s: { sheet: "900K", color: "groups" }, cam: [[-46, 40, 72], [-12, 8, 8]] },
      { t: "Lotes diferentes: GO mais aquecido", x: "A estrutura recozida a 1 500 K no mesmo estudo: os epóxis somem, surgem buracos com bordas de carbonila (vermelho), éter (verde-azulado) e lactona (âmbar), quase não sobra carbono sp³ e o O/C cai para ~0,21. Lotes de GO diferem assim, em quantidade e em tipo de oxigênio; é a variabilidade que o projeto mede.", s: { sheet: "1500K", color: "groups" }, cam: [[-40, 46, 70], [-8, 6, 10]] },
      { t: "O ouro é um cristal", x: "A nanopartícula é um pedaço de cristal cúbico de face centrada (aresta 4,078 Å; vizinhos a 2,88 Å), aqui com o brilho metálico do ouro. O corte mostra os planos atômicos empilhados por dentro dela.", s: { color: "element", clip: true }, cam: [[0, 30, 74], [0, 18, 0]] },
      { t: "Faces, arestas e vértices", x: "Cores pelo número de vizinhos: faces (111) com 9, faces (100) com 8, arestas com 7 e vértices com 6. Quanto menor a partícula, maior a fração de átomos na superfície e em sítios de baixa coordenação, os mais reativos (veja o gráfico de sítios).", s: { color: "site", clip: false }, cam: [[40, 44, 60], [0, 18, 0]] },
      { t: "A interface com o GO", x: "A partícula se apoia numa face (111) e é achatada pela adesão ao suporte (construção de Winterbottom; controle \"Adesão\"). Na folha publicada ela pousa sobre os átomos mais altos; as linhas tracejadas ligam oxigênios do GO ao primeiro plano de ouro: os grupos oxigenados ancoram a partícula e são onde ela começa a crescer.", s: { color: "site", clip: false }, cam: [[50, 16, 40], [0, 11, 0]] },
      ...(MX && MX.particles["900K"] && MX.particles["900K"].au ? [{ t: "A interface calculada", x: `Agora a mesma partícula (${MX.particles["900K"].N_Au} átomos, ~${fmt(MX.particles["900K"].d_nm, 1)} nm), pousada na folha de 900 K, é relaxada por um cálculo atomístico: o potencial GO-MACE-23 descreve o GO e o MACE-MP-0 (+ dispersão D3) acrescenta o ouro. Veja os átomos se acomodarem e, no fim, as ligações Au–O e Au–C (traços escuros) que o cálculo formou com os grupos de verdade. A adesão calculada aparece no título.`, s: { sheet: "900K", relax: true, color: "groups", clip: false }, cam: [[30, 20, 40], [0, 8, 0]] }] : []),
      { t: "A síntese, ao vivo", x: "Íons Au³⁺ (amarelo claro) são reduzidos a Au⁰ (dourado). Quando há átomos livres demais (supersaturação), surgem núcleos nos oxigênios do GO; depois eles só crescem, átomo por átomo, nos sítios da rede de maior coordenação. Compare o citrato (brando: poucos núcleos, partículas maiores) com o NaBH₄ (forte: muitos núcleos, partículas menores).", s: { mode: "synth", run: true }, cam: HOME.synth },
      { t: "Por que o ouro é vermelho", x: "O campo elétrico da luz empurra os elétrons livres do ouro, que oscilam juntos: o plásmon. Perto de 520 nm (verde) a oscilação é máxima e essa cor é absorvida; por isso a dispersão parece vermelha. A amplitude segue o espectro de Mie desta partícula, o mesmo cálculo da aba Óptica. Use \"varrer as cores\" para passar por todas as cores.", s: { mode: "plasmon", lam: 520 }, cam: HOME.plasmon },
      { t: "Do átomo ao filme", x: "A câmera se afasta mil vezes: flocos de GO com dezenas a centenas de nanopartículas de vários tamanhos (distribuição log-normal). A vista TEM imita a imagem do microscópio eletrônico, que é como o projeto vai medir o tamanho de verdade.", s: { scale: "meso", tem: false }, cam: HOME.meso },
    ];
    let tourI = -1;
    function tourGo(i) {
      if (i < 0 || i >= TOUR.length) { tourI = -1; opt.onTour && opt.onTour(null); return; }
      tourI = i; const st = TOUR[i], s = st.s, ch = {};
      for (const k of ["scale", "mode", "sheet", "ox", "color", "clip", "lam", "tem", "relax"]) if (s[k] !== undefined && P[k] !== s[k]) { P[k] = s[k]; ch[k] = 1; }
      if (ch.clip && !ch.color) [matGold, matMetal].forEach((m) => { m.clippingPlanes = P.clip ? [clipPlane] : []; m.needsUpdate = true; });
      rebuild(ch);
      if (s.run) { if (!sim || sim.stats().done) buildSynthesis(false); simRun = true; }
      camTo(st.cam[0], st.cam[1], 1300);
      opt.onTour && opt.onTour({ i, n: TOUR.length, t: st.t, x: st.x, P: { ...P } }); emit();
    }

    buildAtomic(); camera.position.set(...HOME.explore[0]); controls.target.set(...HOME.explore[1]); controls.update(); resize();

    return {
      P, stats, tour: TOUR, tourGo, get tourI() { return tourI; }, zoom, resize,
      set(k, v) {
        if (P[k] === v) return; P[k] = v;
        if (k === "labels") { applyMode(); return; }
        if (k === "hyd") { [gAtom, gSyn].forEach((g) => g && g.traverse((o) => { if (o.userData.hyd) o.visible = v; })); ensureLoop(); return; }
        if (k === "clip") { [matGold, matMetal].forEach((m) => { m.clippingPlanes = v ? [clipPlane] : []; m.needsUpdate = true; }); ensureLoop(); return; }
        if (k === "lam" || k === "speed") return;
        const ch = { [k]: 1 }; if (["md", "msig", "cov"].includes(k)) ch.meso = 1; if (["red", "T"].includes(k)) ch.synth = 1;
        rebuild(ch);
        if (k === "scale" || k === "mode" || k === "tem") { const h = homeOf(); camTo(h[0], h[1]); }
        ensureLoop();
      },
      relaxable: (T) => !!relaxData(T || P.sheet),
      replayRelax() { if (part && part.relax && relaxExtra) { const R = part.relax; relaxExtra.forEach((o) => { o.visible = false; });
        relaxAnim = { from: R.au0.map((q) => q.map((v) => v / 100)), to: R.au.map((q) => q.map((v) => v / 100)), t0: performance.now() + 150, dur: 2600, mesh: part.mesh }; emit(); ensureLoop(); } },
      play(on) { if (P.mode !== "synth") return; if (on && sim && sim.stats().done) buildSynthesis(false); simRun = on; emit(); ensureLoop(); },
      restart() { if (P.mode === "synth") { buildSynthesis(false); simRun = true; emit(); ensureLoop(); } },
      sweep() { P.lam = 400; sweep = true; ensureLoop(); },
      home() { const h = homeOf(); camTo(h[0], h[1]); ortho.zoom = 1; ortho.updateProjectionMatrix(); },
      theme(t) {
        theme = t; themeV++;
        if (P.scale === "meso") buildMeso(); else if (P.mode === "synth") buildSynthesis(true); else buildAtomic();
      },
      png() { renderer.render(scene, cam); return cv.toDataURL("image/png"); },
      legend() {                                       // [cor, rótulo] do que está na tela, nas mesmas cores da cena
        const p = pal();
        if (P.scale === "meso") return P.tem ? [["#bdbdbd", "folha de GO (pouco contraste no TEM)"], ["#161616", "nanopartícula de ouro (muito contraste)"]]
          : [[theme.dark ? "#6f6253" : "#8c7a66", "folha de óxido de grafeno"], [P.mcolor === "mie" ? opt.colorOf(P.md) : p.AuM, P.mcolor === "mie" ? "AuNP na cor da sua dispersão (Mie)" : "nanopartícula de ouro"]];
        if (P.mode === "synth") return [[p.ion, "Au³⁺ em solução (íon, ainda não reduzido)"], [p.mon, "Au⁰ livre (átomo reduzido, procurando onde ficar)"], [p.AuM, "Au em partícula (rede fcc)"], [p.O, "O do GO (sítio de nucleação)"], [p.C, "C do grafeno"]];
        const have = new Set(sheet ? sheet.at.map((a) => a.k) : []), G = [["sp2", "C sp² (grafeno intacto)"], ["sp3", "C sp³ (ligado a O)"], ["edge", "C de borda (folha ou buraco)"],
          ["epoxi", "O epóxi"], ["hidroxila", "O hidroxila"], ["eter", "O éter cíclico"], ["carbonila", "O carbonila (C=O)"], ["carboxila", "O carboxila"], ["lactona", "O lactona / anidrido"]];
        const af = P.color === "affinity" ? affinity() : null, nm = { epoxi: "epóxi", hidroxila: "hidroxila", eter: "éter", carbonila: "carbonila (C=O)", carboxila: "carboxila", lactona: "lactona", edge: "C de borda" };
        if (af) {
          const L = Object.entries(af.colors).sort((a, b) => af.med[a[0]] - af.med[b[0]]).map(([k, c]) => [c, `${nm[k]}: ${fmt(af.med[k], 2)} eV`]);
          return L.concat([[p.C, `outros C${af.med.sp2 != null ? ` (ilha sp²: ${fmt(af.med.sp2, 2)} eV)` : ""}`], ["#9a9a9a", "O sem dado"], [p.H, "hidrogênio"], [p.AuM, "ouro"],
            [theme.muted, "medianas do MACE-MP-0 small; ordem incerta"]]);
        }
        const at = P.color === "element" ? [[p.C, "carbono"], [p.O, "oxigênio"], [p.H, "hidrogênio"], [p.AuM, "ouro"]]
          : P.color === "groups" ? G.filter(([k]) => have.has(k) || (k === "edge" && have.has("cx"))).map(([k, l]) => [p[k] || p.C, l]).concat([[p.H, "hidrogênio"], [p.AuM, "ouro"]])
            : [[p.C, "carbono"], [p.O, "oxigênio"], [p.f111, "Au face (111) · CN 9"], [p.f100, "Au face (100) · CN 8"], [p.aresta, "Au aresta · CN 7"], [p.vertice, "Au vértice · CN ≤ 6"], [p.interface, "Au na interface"], [p.interior, "Au interior · CN 12"]];
        if (P.mode === "plasmon") at.push(["#4f8dff", "nuvem de elétrons livres"], ["rgb(" + waveRGB(P.lam).map((x) => Math.round(255 * x)).join(",") + ")", "campo elétrico da luz"]);
        else at.push(part && part.relax ? [theme.ink, "— ligação Au–O / Au–C (calculada)"] : [theme.ink, "- - interação Au–O"]);
        return at;
      },
    };
  };
})();
