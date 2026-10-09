/* Executa code/webapp/guide.js com os dados de site/data (como o navegador faz) e imprime um resumo em JSON:
   chaves, campos de cada figura e texto completo, para o teste test_guia_* conferir cobertura e números. */
const fs = require("fs"), path = require("path"), vm = require("vm");
const root = path.resolve(__dirname, "..", "..");
const ctx = { window: { AUGO: {} }, console };
ctx.window.window = ctx.window;
vm.createContext(ctx);
const data = path.join(root, "site", "data");
for (const f of fs.readdirSync(data).filter((x) => x.endsWith(".js"))) vm.runInContext(fs.readFileSync(path.join(data, f), "utf8"), ctx);
vm.runInContext(fs.readFileSync(path.join(root, "code", "webapp", "guide.js"), "utf8"), ctx);
const NB = " ";
const nf = (x, d = 1) => (x == null || !isFinite(x) ? "—" : Number(x).toFixed(d).replace(".", ",").replace(/\B(?=(\d{3})+(?!\d))/g, NB));
const ni = (x) => nf(x, 0);
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const pf = (p) => (p < 0.001 ? "p < 0,001" : "p = " + nf(p, 3));
const G = ctx.window.AUGO_GUIDE(ctx.window.AUGO, { nf, ni, esc, pf });
const figs = {};
for (const [k, F] of Object.entries(G.FIG)) figs[k] = Object.keys(F).filter((f) => F[f] != null && (typeof F[f] !== "string" || F[f].length) && (!Array.isArray(F[f]) || F[f].length));
console.log(JSON.stringify({ sections: Object.keys(G), tabs: Object.keys(G.TABS), tabFields: Object.fromEntries(Object.entries(G.TABS).map(([k, T]) => [k, Object.keys(T)])),
  kpi: Object.fromEntries(Object.entries(G.KPI || {}).map(([k, K]) => [k, K.items.length])), figs,
  concepts: (G.CONCEPTS || []).map((c) => ({ id: c.id, demo: c.demo, where: c.where || [] })), tour: (G.TOUR || []).map((t) => t[1]),
  text: JSON.stringify(G) }));
