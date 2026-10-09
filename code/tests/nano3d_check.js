/* Executa o núcleo de code/webapp/nano3d.js (AUGO_N3CORE: geometria e síntese, sem three.js) e imprime em JSON as
   grandezas que test_nanocomposito_3d confere: distâncias das redes, coordenação, fração de superfície e as tendências
   da síntese simulada (redutor forte e GO mais oxidado → mais núcleos, partículas menores). */
const fs = require("fs"), path = require("path"), vm = require("vm");
const ctx = { window: {} }; vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.resolve(__dirname, "..", "webapp", "nano3d.js"), "utf8"), ctx);
const K = ctx.window.AUGO_N3CORE;
const minDist = (P) => { let m = Infinity; for (let i = 0; i < P.length; i++) for (let j = i + 1; j < P.length; j++) m = Math.min(m, Math.hypot(P[i][0] - P[j][0], P[i][1] - P[j][1], P[i][2] - P[j][2])); return m; };
const sh = K.buildSheet(110, 0.3), flat = K.buildSheet(40, 0);
const cc = flat.bonds.map(([i, j]) => Math.hypot(flat.C[i].x - flat.C[j].x, flat.C[i].z - flat.C[j].z));
const inner = flat.C.filter((c) => Math.abs(c.x) < 15 && Math.abs(c.z) < 15);
const p2 = K.buildParticle(2, 0.35), p6 = K.buildParticle(6, 0.35);
const run = (red, ox) => { const S = K.Synthesis(K.buildSheet(90, ox), { red: K.REDUCERS[red], T: 25 }); let s;
  for (let i = 0; i < 20000; i++) { S.step(); if (i % 50 === 0 && (s = S.stats()).done) break; } s = S.stats(); return { nuclei: s.nuclei, n: s.n, d: s.d, att: s.att, done: s.done, t: s.t }; };
console.log(JSON.stringify({
  cc: [Math.min(...cc), Math.max(...cc)], innerNb: [...new Set(inner.map((c) => c.nb.length))],
  CO: sh.CO, groups: sh.count, sp3: sh.sp3frac,
  au: { nn: minDist(p2.P), N2: p2.N, d2: p2.d, surf2: p2.surfFrac, surf6: p6.surfFrac, count2: p2.count, low2: p2.lowCN, low6: p6.lowCN,
    base: Math.min(...p2.P.map((q) => q[1])), cnMax: Math.max(...p2.cls.map((c) => c.cn)) },
  syn: { citrato: run("citrato", 0.3), nabh4: run("nabh4", 0.3), nabh4Low: run("nabh4", 0.08) },
}));
