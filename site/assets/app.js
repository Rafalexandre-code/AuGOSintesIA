/* AuGOSintesIA — painel interativo (Plotly). Dados em window.AUGO, gerados por code/webapp/build_site.py.
   Cada aba é montada uma vez (controles e estado do usuário); a troca de tema só redesenha os gráficos. */
(function () {
  "use strict";
  const A = window.AUGO || {};
  const $ = (s, r) => (r || document).querySelector(s);
  const NB = " ";                                   // agrupamento de milhar com espaço, como no texto ("15 928")
  const nf = (x, d = 1) => (x == null || !isFinite(x)) ? "—" :
    Number(x).toLocaleString("pt-BR", { minimumFractionDigits: d, maximumFractionDigits: d }).replace(/\./g, NB);
  const ni = (x) => (x == null || !isFinite(x)) ? "—" : Math.round(x).toLocaleString("pt-BR").replace(/\./g, NB);
  const pf = (p) => p < 0.001 ? "p < 0,001" : "p = " + nf(p, 3);
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  // redesenho no máximo uma vez por quadro (arrastar um controle dispara dezenas de eventos)
  const perFrame = (fn) => { let q = false; return () => { if (q) return; q = true; requestAnimationFrame(() => { q = false; fn(); }); }; };
  // no máximo uma chamada a cada ms (a primeira na hora, a última garantida): gráficos 3D enquanto um controle é arrastado
  const throttle = (fn, ms) => { let last = -1e9, tm = 0; return () => { const now = performance.now(), wait = ms - (now - last);
    if (wait <= 0) { clearTimeout(tm); tm = 0; last = now; fn(); } else if (!tm) tm = setTimeout(() => { tm = 0; last = performance.now(); fn(); }, wait); }; };
  // gráfico fora da tela não é redesenhado: a atualização fica guardada e roda quando ele aparece
  const VIS = new WeakMap(), PEND = new WeakMap();
  const IO = "IntersectionObserver" in window ? new IntersectionObserver((es) => es.forEach((e) => {
    VIS.set(e.target, e.isIntersecting);
    if (e.isIntersecting && PEND.has(e.target)) { const f = PEND.get(e.target); PEND.delete(e.target); f(); } }), { rootMargin: "120px" }) : null;
  function whenVisible(el, fn) {
    if (!IO || !el) return fn();
    if (!VIS.has(el)) { VIS.set(el, true); IO.observe(el); }
    if (VIS.get(el)) { PEND.delete(el); fn(); } else PEND.set(el, fn);
  }

  /* ------------------------------------------------------------------ tema e paleta (validada: dataviz) */
  const CAT = {
    light: ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"],
    dark: ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"],
  };
  const SEQ = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5", "#2a78d6", "#256abf",
    "#1c5cab", "#184f95", "#104281", "#0d366b"];
  function isDark() {
    const t = document.documentElement.getAttribute("data-theme");
    if (t) return t === "dark";
    return !!(window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches);
  }
  function tok(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }
  function T() {
    const dark = isDark();
    const seq = dark ? SEQ.slice().reverse() : SEQ;     // no escuro, "perto de zero" recua para a superfície escura
    return {
      dark, cat: dark ? CAT.dark : CAT.light,
      seqScale: seq.map((c, i) => [i / (seq.length - 1), c]),
      surface: tok("--surface"), ink: tok("--ink"), ink2: tok("--ink-2"), muted: tok("--muted"),
      line: tok("--line"), lineStrong: tok("--line-strong"), ruby: tok("--ruby"), gold: tok("--gold"),
      other: dark ? "#6b6870" : "#a9a5ad",
    };
  }
  function deepMerge(a, b) {
    const o = Array.isArray(a) ? a.slice() : Object.assign({}, a);
    for (const k of Object.keys(b)) {
      if (b[k] && typeof b[k] === "object" && !Array.isArray(b[k]) && a[k] && typeof a[k] === "object") o[k] = deepMerge(a[k], b[k]);
      else o[k] = b[k];
    }
    return o;
  }
  function layout(extra) {
    const t = T();
    const ax = { gridcolor: t.line, linecolor: t.lineStrong, zeroline: false, tickfont: { color: t.muted, size: 11 },
      title: { font: { color: t.ink2, size: 12 } }, automargin: true };
    return deepMerge({
      paper_bgcolor: t.surface, plot_bgcolor: t.surface, separators: "," + NB,           // vírgula decimal nos eixos
      font: { family: '"IBM Plex Sans", system-ui, sans-serif', color: t.ink2, size: 12 },
      margin: { l: 56, r: 18, t: 12, b: 48 }, hovermode: "closest",
      hoverlabel: { bgcolor: t.surface, bordercolor: t.lineStrong, font: { color: t.ink, family: '"IBM Plex Sans", sans-serif' } },
      legend: { orientation: "h", y: 1.08, x: 0, font: { color: t.ink2, size: 11 }, bgcolor: "rgba(0,0,0,0)" },
      xaxis: Object.assign({}, ax), yaxis: Object.assign({}, ax),
    }, extra || {});
  }
  function scene(x, y, z, extra) {
    const t = T();
    const ax = (title) => ({ title: { text: title, font: { color: t.ink2, size: 12 } }, gridcolor: t.line,
      linecolor: t.lineStrong, zerolinecolor: t.line, backgroundcolor: t.surface, showbackground: true,
      tickfont: { color: t.muted, size: 10 } });
    return deepMerge({ xaxis: ax(x), yaxis: ax(y), zaxis: ax(z), bgcolor: t.surface,
      camera: { eye: { x: 1.55, y: -1.55, z: 0.95 } }, aspectmode: "cube" }, extra || {});
  }
  // scrollZoom desligado: a roda do mouse rola a página em vez de prender o leitor num gráfico 3D.
  // Na página única publicada o visualizador não permite downloads, então o botão "baixar PNG" sai.
  const CFG = { displaylogo: false, responsive: true, scrollZoom: false,
    modeBarButtonsToRemove: ["lasso2d", "select2d", "autoScale2d"].concat(window.AUGO_EMBED ? ["toImage"] : []) };
  function plot(id, data, lay) {
    const el = document.getElementById(id);
    if (!el || !window.Plotly) return null;
    Plotly.react(el, data, layout(lay), CFG);
    if (!el.hasAttribute("aria-label")) {
      const h = el.closest(".card") && el.closest(".card").querySelector("h2, h3");
      el.setAttribute("role", "figure"); el.setAttribute("aria-label", "Gráfico: " + (h ? h.textContent : id));
    }
    return el;
  }
  function kpis(id, items) {
    $(id).innerHTML = items.map((k) => `<div class="kpi${k.key ? " key" : ""}"><span class="k">${k.k}</span>` +
      `<span class="v">${k.v}${k.u ? `<span class="u">${k.u}</span>` : ""}</span>${k.s ? `<span class="s">${k.s}</span>` : ""}</div>`).join("");
  }
  function segmented(id, onPick) {
    $(id).addEventListener("click", (e) => { const b = e.target.closest("button"); if (!b) return;
      $(id).querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", x === b ? "true" : "false")); onPick(b.dataset.v); });
  }
  const lin = (a, b, n) => Array.from({ length: n }, (_, i) => a + (b - a) * i / (n - 1));
  const finite = (v) => v.filter((x) => x != null && isFinite(x));
  const median = (v) => { const s = finite(v).sort((a, b) => a - b); if (!s.length) return NaN; const m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };
  const quant = (v, q) => { const s = finite(v).sort((a, b) => a - b); if (!s.length) return NaN; const p = (s.length - 1) * q, i = Math.floor(p); return s[i] + (s[Math.min(i + 1, s.length - 1)] - s[i]) * (p - i); };
  function interp(x, xs, ys) {
    if (x <= xs[0]) return ys[0];
    if (x >= xs[xs.length - 1]) return ys[ys.length - 1];
    let lo = 0, hi = xs.length - 1;
    while (hi - lo > 1) { const m = (lo + hi) >> 1; if (xs[m] <= x) lo = m; else hi = m; }
    return ys[lo] + (x - xs[lo]) / (xs[hi] - xs[lo]) * (ys[hi] - ys[lo]);
  }
  function peakOf(w, e, lo = 480) {                           // máximo acima de lo, refinado por parábola (= analyses._peak)
    let i = -1; for (let j = 0; j < w.length; j++) if (w[j] >= lo && (i < 0 || e[j] > e[i])) i = j;
    if (i <= 0 || i >= w.length - 1 || w[i - 1] < lo) return w[i];
    const den = e[i - 1] - 2 * e[i] + e[i + 1];
    return w[i] + (den ? 0.5 * (e[i - 1] - e[i + 1]) / den : 0) * (w[i + 1] - w[i]);
  }
  const npdf = (z) => Math.exp(-0.5 * z * z) / Math.sqrt(2 * Math.PI);
  function ncdf(z) { const t = 1 / (1 + 0.2316419 * Math.abs(z));
    const p = npdf(z) * t * (0.319381530 + t * (-0.356563782 + t * (1.781477937 + t * (-1.821255978 + t * 1.330274429))));
    return z > 0 ? 1 - p : p; }
  function hexA(hex, a) { const n = parseInt(hex.slice(1), 16); return `rgba(${n >> 16},${(n >> 8) & 255},${n & 255},${a})`; }
  // superfície de Mie para exibição: metade das linhas e colunas (a tela não resolve mais que isso; a conta usa a grade inteira)
  function mieView() {
    const O = A.optics, ri = O.d.map((_, i) => i).filter((i) => i % 2 === 0), cj = O.wl.map((_, j) => j).filter((j) => j % 2 === 0);
    return { ri, cj, wl: cj.map((j) => O.wl[j]), ld: ri.map((i) => Math.log10(O.d[i])), z: ri.map((i) => cj.map((j) => O.C_ext[i][j])) };
  }
  /* ---- cor real do ouro coloidal: espectro de extinção (Mie) → transmitância → XYZ (CIE 1931, ajuste de Wyman et al.
     2013) sob D65 → sRGB. A0 = absorbância no pico de uma dispersão de AuNP de 20 nm com a mesma massa de ouro. */
  const D65 = [82.75, 91.49, 93.43, 86.68, 104.86, 117.01, 117.81, 114.86, 115.92, 108.81, 109.35, 107.80, 104.79, 107.69,
    104.41, 104.05, 100.0, 96.33, 95.79, 88.69, 90.01, 89.60, 87.70, 83.29, 83.70, 80.03, 80.21, 82.28, 78.28, 69.72, 71.61];
  const gpw = (x, m, s1, s2) => { const s = x < m ? s1 : s2; return Math.exp(-0.5 * ((x - m) / s) ** 2); };
  const CIE = []; for (let l = 400; l <= 700; l += 5) {
    const S = interp(l, D65.map((_, i) => 400 + 10 * i), D65);
    CIE.push([l, S, 1.056 * gpw(l, 599.8, 37.9, 31.0) + 0.362 * gpw(l, 442.0, 16.0, 26.7) - 0.065 * gpw(l, 501.1, 20.4, 26.2),
      0.821 * gpw(l, 568.8, 46.9, 40.5) + 0.286 * gpw(l, 530.9, 16.3, 31.1), 1.217 * gpw(l, 437.0, 11.8, 36.0) + 0.681 * gpw(l, 459.0, 26.0, 13.8)]);
  }
  const YW = CIE.reduce((a, c) => a + c[1] * c[3], 0);
  function colloidRGB(wl, ePV, A0) {                       // ePV: extinção por volume de Au, já dividida pela referência
    let X = 0, Y = 0, Z = 0;
    for (const [l, S, xb, yb, zb] of CIE) { const T = Math.pow(10, -A0 * interp(l, wl, ePV)); X += S * T * xb; Y += S * T * yb; Z += S * T * zb; }
    X /= YW; Y /= YW; Z /= YW;
    const lin2 = [3.2406 * X - 1.5372 * Y - 0.4986 * Z, -0.9689 * X + 1.8758 * Y + 0.0415 * Z, 0.0557 * X - 0.2040 * Y + 1.0570 * Z];
    return lin2.map((u) => { u = Math.max(0, u); const v = u <= 0.0031308 ? 12.92 * u : 1.055 * Math.pow(u, 1 / 2.4) - 0.055; return Math.round(255 * Math.min(1, v)); });
  }
  const rgbHex = (c) => "#" + c.map((v) => v.toString(16).padStart(2, "0")).join("");
  let GOLD = null;                                           // cores por diâmetro da grade de Mie (cache)
  function goldColors(A0 = 1.5) {
    if (GOLD && GOLD.A0 === A0) return GOLD;
    const O = A.optics, d = O.d, wl = O.wl;
    const pv = O.C_ext.map((row, i) => { const v = Math.PI * d[i] ** 3 / 6; return row.map((x) => x * O.C_ext_max[i] / v); });
    const i20 = d.reduce((b, x, i) => (Math.abs(x - 20) < Math.abs(d[b] - 20) ? i : b), 0), ref = Math.max(...pv[i20]);
    const cols = pv.map((row) => rgbHex(colloidRGB(wl, row.map((x) => x / ref), A0)));
    const lmin = Math.log10(d[0]), lmax = Math.log10(d[d.length - 1]);
    GOLD = { A0, ref, cols, pos: d.map((x) => (Math.log10(x) - lmin) / (lmax - lmin)), lmin, lmax };
    GOLD.scale = GOLD.pos.filter((_, i) => i % 3 === 0 || i === d.length - 1).map((p, k, arr) => [p, cols[GOLD.pos.indexOf(p)]]);
    return GOLD;
  }
  window.AUGO_UTIL = { colloidRGB, goldColors };            // usado nos testes do navegador
  const hashJitter = (i, j) => { const x = Math.sin(i * 12.9898 + j * 78.233) * 43758.5453; return x - Math.floor(x) - 0.5; };  // estável

  /* ------------------------------------------------------------------ abas: montagem única + redesenho por tema */
  const IC = {   // ícones de traço (24 × 24)
    visao: '<rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/>',
    literatura: '<path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v15H6.5A2.5 2.5 0 0 0 4 20.5z"/><path d="M4 20.5A2.5 2.5 0 0 0 6.5 23H20v-5"/><path d="M8 7h8M8 11h6"/>',
    caracterizacao: '<circle cx="12" cy="12" r="2"/><circle cx="12" cy="12" r="5.5"/><circle cx="12" cy="12" r="9"/>',
    optica: '<path d="M2 14c2.5 0 3-8 5.5-8S10 18 12.5 18 15 9 17 9s2.5 5 5 5"/>',
    designer: '<path d="M4 6h16M4 12h16M4 18h16"/><circle cx="9" cy="6" r="2" fill="currentColor"/><circle cx="15" cy="12" r="2" fill="currentColor"/><circle cx="7" cy="18" r="2" fill="currentColor"/>',
    interpretabilidade: '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
    aprendizado: '<path d="M20 11a8 8 0 1 0-2.3 5.7"/><path d="M20 5v6h-6"/><circle cx="12" cy="12" r="2" fill="currentColor"/>',
    variabilidade: '<circle cx="6" cy="16" r="1.6"/><circle cx="10" cy="9" r="1.6"/><circle cx="14" cy="14" r="1.6"/><circle cx="18" cy="6" r="1.6"/><circle cx="17" cy="18" r="1.6"/><path d="M3 21h18"/>',
    causal: '<circle cx="5" cy="12" r="2.5"/><circle cx="19" cy="12" r="2.5"/><circle cx="12" cy="4.5" r="2.5"/><path d="M7.5 12h9M7 10.5l3.4-4M17 10.5l-3.4-4"/>',
    sobre: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5v.5"/>',
  };
  const ico = (id, cls) => `<svg viewBox="0 0 24 24" aria-hidden="true"${cls ? ` class="${cls}"` : ""} fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">${IC[id]}</svg>`;
  const NAV = [["Panorama", [["visao", "Visão geral", ""]]],
    ["Dados", [["literatura", "Literatura", "4.1"], ["caracterizacao", "Caracterização", "4.2"]]],
    ["Modelos", [["optica", "Óptica e J", "4.4"], ["designer", "AuNP Designer", "4.5"], ["interpretabilidade", "Interpretabilidade", "4.13"]]],
    ["Decisão", [["aprendizado", "Aprendizado ativo", "4.15"], ["variabilidade", "Variabilidade", "4.17"], ["causal", "Causalidade", "4.9"]]],
    ["Projeto", [["sobre", "Sobre e dados", ""]]]];
  const TABS = [].concat(...NAV.map((g) => g[1]));
  const INIT = {}, REDRAW = {}, built = {}, stale = {};
  let building = null, current = null;
  // registra uma função de desenho da aba em montagem e a executa; a troca de tema chama todas de novo
  function drawer(fn) { (REDRAW[building] = REDRAW[building] || []).push(fn); fn(); return fn; }
  function show(id) {
    if (!TABS.some((t) => t[0] === id)) id = "visao";
    const changed = current !== id;
    current = id;
    for (const [t] of TABS) {
      const p = document.getElementById("p-" + t), b = document.getElementById("t-" + t);
      p.hidden = t !== id;
      if (t === id) b.setAttribute("aria-current", "page"); else b.removeAttribute("aria-current");
    }
    const tb = document.getElementById("t-" + id), bar = $("#tabs");
    if (bar.scrollWidth > bar.clientWidth + 4) bar.scrollTo({ left: tb.offsetLeft - bar.clientWidth / 2 + tb.offsetWidth / 2, behavior: "smooth" });
    if (!built[id]) { building = id; INIT[id](); building = null; built[id] = true; stale[id] = false; }
    else if (stale[id]) { (REDRAW[id] || []).forEach((f) => f()); stale[id] = false; }
    else document.querySelectorAll(`#p-${id} .js-plotly-plot`).forEach((el) => Plotly.Plots.resize(el));
    try { localStorage.setItem("augo-tab", id); } catch (e) { /* armazenamento indisponível */ }
    return changed;
  }
  // #aba abre a aba; #algum-elemento abre a aba que o contém e rola até ele
  function route(h) {
    if (TABS.some((t) => t[0] === h)) { if (show(h)) window.scrollTo({ top: 0 }); return; }
    const el = h && document.getElementById(h), panel = el && el.closest(".panel");
    show(panel ? panel.id.slice(2) : "visao");
    if (el) requestAnimationFrame(() => { el.scrollIntoView({ block: "start", behavior: "smooth" });
      if (el.classList.contains("card")) { el.classList.remove("flash"); void el.offsetWidth; el.classList.add("flash"); } });
  }
  function themeChanged() {
    $("#themeLbl").textContent = isDark() ? "Tema claro" : "Tema escuro";
    $("#themeBtn").setAttribute("aria-pressed", isDark() ? "true" : "false");
    for (const k of Object.keys(built)) stale[k] = true;
    if (current) show(current);
  }
  function tabStatus(id) {
    if (id === "visao") return "exp";
    const st = A.overview.map.filter((m) => m.tab === id).map((m) => m.status);
    if (!st.length || id === "sobre") return "lab";
    return st.every((x) => x === "experimental") ? "exp" : st.every((x) => x === "laboratorio") ? "lab" : "par";
  }
  function buildTabs() {
    const M = A.overview.map, n = M.length, c = (k) => M.filter((m) => m.status === k).length, T = { exp: "dados experimentais", par: "parcial", lab: "aguarda o laboratório" };
    $("#tabs").innerHTML = NAV.map(([g, items]) => `<div class="grp">${g}</div>` + items.map(([id, label, sec]) => {
      const st = tabStatus(id);
      return `<a class="nav" id="t-${id}" href="#${id}" aria-controls="p-${id}">${ico(id)}<span>${label}</span>` +
        `<span class="sec">${sec ? "§" + sec : ""}<span class="dot ${st}" title="${T[st]}"></span></span></a>`; }).join("")).join("") +
      `<div class="rail-foot"><b>${c("experimental")} de ${n}</b> seções da proposta já com dados experimentais` +
      `<div class="bar" aria-hidden="true"><i style="flex:${c("experimental")};background:var(--ok)"></i><i style="flex:${c("parcial")};background:var(--warn)"></i><i style="flex:${c("laboratorio")};background:var(--line-strong)"></i></div>` +
      `${c("parcial")} parciais · ${c("laboratorio")} aguardam o laboratório</div>`;
    $("#tabs").addEventListener("keydown", (e) => {
      const ids = TABS.map((t) => t[0]), cur = ids.indexOf(current);
      const nxt = { ArrowDown: ids[(cur + 1) % ids.length], ArrowRight: ids[(cur + 1) % ids.length], ArrowUp: ids[(cur + ids.length - 1) % ids.length],
        ArrowLeft: ids[(cur + ids.length - 1) % ids.length], Home: ids[0], End: ids[ids.length - 1] }[e.key];
      if (!nxt) return;
      e.preventDefault(); location.hash = nxt; document.getElementById("t-" + nxt).focus();
    });
    window.addEventListener("hashchange", () => route(location.hash.slice(1)));
  }
  // botão "ampliar" em todo cartão com gráfico
  // download no visualizador de Artifacts (capacidade "downloads"); fora dele, link comum
  const DL = window.claude && typeof window.claude.use === "function" ? window.claude.use("downloads").catch(() => null) : null;
  // dados de cada gráfico: tabela + CSV (separador ";" e vírgula decimal, como os CSV do repositório)
  function plotRows(card) {
    const head = ["série", "x", "y", "z"], rows = [];
    let xt = "x", yt = "y", zt = "z";
    card.querySelectorAll(".js-plotly-plot").forEach((el) => {
      const L = el.layout || {}, sc = L.scene, tt = (ax) => (!ax || !ax.title ? "" : typeof ax.title === "string" ? ax.title : ax.title.text || "").replace(/<[^>]+>/g, "");
      xt = tt(sc ? sc.xaxis : L.xaxis) || xt; yt = tt(sc ? sc.yaxis : L.yaxis) || yt; zt = tt(sc && sc.zaxis) || zt;
      (el.data || []).forEach((tr, i) => {
        if (tr.hoverinfo === "skip" && !tr.name) return;                       // linhas de referência
        const nm = String(tr.name || (el.data.length > 1 ? `série ${i + 1}` : "")).replace(/<[^>]+>/g, "");
        const A_ = (v) => (v == null ? null : Array.from(v)), x = A_(tr.x || tr.labels), y = A_(tr.y || tr.values), z = A_(tr.z);
        if (z && Array.isArray(z[0])) {                                          // matriz (superfície, mapa de calor)
          z.forEach((row, r) => Array.from(row).forEach((v, c) => rows.push([nm, x ? (Array.isArray(x[0]) ? x[r][c] : x[c]) : c, y ? (Array.isArray(y[0]) ? y[r][c] : y[r]) : r, v])));
        } else {
          const n = Math.max((x || []).length, (y || []).length, (z || []).length);
          for (let k = 0; k < n; k++) rows.push([nm, x ? x[k] : k, y ? y[k] : "", z ? z[k] : ""]);
        }
      });
    });
    head[1] = xt; head[2] = yt; head[3] = zt;
    [1, 2].forEach((j) => { if (head[j] === "xy"[j - 1] && rows.some((r) => typeof r[j] === "string")) head[j] = "categoria"; });
    const useZ = rows.some((r) => r[3] !== "" && r[3] != null), useS = rows.some((r) => r[0]);
    const keep = [useS, true, true, useZ];
    return { head: head.filter((_, j) => keep[j]), rows: rows.map((r) => r.filter((_, j) => keep[j])) };
  }
  function dataView(card, opener) {
    const dlg = $("#dataDlg"), { head, rows } = plotRows(card), h = card.querySelector("h3, h2");
    const title = h ? h.textContent.trim() : "dados";
    const cell = (v) => (v == null ? "" : typeof v === "number" ? String(+v.toPrecision(7)).replace(".", ",") : String(v));
    const csv = [head, ...rows].map((r) => r.map((v) => { const c = cell(v); return /[;"\n]/.test(c) ? `"${c.replace(/"/g, '""')}"` : c; }).join(";")).join("\n");
    $("#dataT").textContent = title;
    $("#dataN").textContent = `${ni(rows.length)} linhas${rows.length > 300 ? " (a tabela mostra as 300 primeiras; o CSV leva todas)" : ""}`;
    $("#dataTbl").innerHTML = `<table><thead><tr>${head.map((c) => `<th scope="col">${esc(c)}</th>`).join("")}</tr></thead><tbody>` +
      rows.slice(0, 300).map((r) => "<tr>" + r.map((v) => `<td${typeof v === "number" ? ' class="num"' : ""}>${esc(typeof v === "number" ? nf(v, Math.abs(v) >= 100 ? 1 : 3) : cell(v))}</td>`).join("") + "</tr>").join("") + "</tbody></table>";
    const msg = $("#dataMsg"); msg.textContent = "";
    $("#dataCopy").onclick = async () => {
      try { await navigator.clipboard.writeText(csv); msg.textContent = "copiado"; }
      catch (e) { const ta = document.createElement("textarea"); ta.value = csv; document.body.appendChild(ta); ta.select();
        let ok = false; try { ok = document.execCommand("copy"); } catch (e2) { /* sem área de transferência */ } ta.remove();
        msg.textContent = ok ? "copiado" : "o navegador bloqueou a cópia; use baixar"; }
    };
    const sv = $("#dataSave"), sp = $("#dataPng"), base = card.id || "grafico", gd = card.querySelector(".js-plotly-plot");
    sv.hidden = false; sp.hidden = !gd;
    if (DL) DL.then((d) => { if (!d) sv.hidden = sp.hidden = true; });   // visualizador sem permissão de download: só copiar
    async function offer(fn, data, mime) {
      if (DL) {                                                       // dentro do visualizador: o download passa pela plataforma
        const d = await DL; if (!d) { sv.hidden = sp.hidden = true; return; }
        try { await d.save({ filename: fn, data }); msg.textContent = "arquivo salvo"; }
        catch (e) { const c = e && e.code;
          if (c === "declined") msg.textContent = "download cancelado";
          else if (c === "rate_limited") msg.textContent = "aguarde e tente de novo";
          else { msg.textContent = "download indisponível aqui; use copiar"; sv.hidden = sp.hidden = true; } }
        return;
      }
      const a = document.createElement("a");
      a.href = URL.createObjectURL(new Blob([data], { type: mime })); a.download = fn;
      document.body.appendChild(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 500);
    }
    sv.onclick = () => offer(base + ".csv", "\ufeff" + csv, "text/csv;charset=utf-8");
    sp.onclick = async () => {                                        // figura em 2× (boa para relatório), nas cores do tema
      msg.textContent = "gerando a figura…";
      try {
        const url = await Plotly.toImage(gd, { format: "png", scale: 2, width: gd.clientWidth, height: gd.clientHeight });
        const bin = atob(url.slice(url.indexOf(",") + 1)), u8 = new Uint8Array(bin.length);
        for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
        msg.textContent = ""; await offer(base + ".png", u8, "image/png");
      } catch (e) { msg.textContent = "não foi possível gerar a figura"; }
    };
    const close = () => { dlg.hidden = true; if (!$(".card.full")) $("#backdrop").hidden = true; document.removeEventListener("keydown", esc_, true); opener.focus(); };
    const esc_ = (e) => { if (e.key === "Escape") { e.stopPropagation(); e.preventDefault(); close(); } };
    $("#dataClose").onclick = close;
    document.addEventListener("keydown", esc_, true);
    dlg.hidden = false; $("#backdrop").hidden = false; $("#dataCopy").focus();
  }
  function addExpanders() {
    const icoT = '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M2 3h12v10H2zM2 7h12M6 3v10" fill="none" stroke="currentColor" stroke-width="1.5"/></svg>';
    const ico = '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M2 6V2h4M10 2h4v4M14 10v4h-4M6 14H2v-4" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>';
    document.querySelectorAll(".card").forEach((card) => {
      if (!card.querySelector(".plot") || card.classList.contains("hero-vis")) return;
      const head = card.querySelector(".card-h"); if (!head) return;
      const dB = document.createElement("button");
      dB.type = "button"; dB.className = "icon-btn"; dB.innerHTML = icoT + "<span>dados</span>"; dB.setAttribute("aria-label", "Ver e copiar os dados do gráfico");
      dB.addEventListener("click", () => dataView(card, dB));
      const b = document.createElement("button");
      b.type = "button"; b.className = "icon-btn"; b.innerHTML = ico + "<span>ampliar</span>"; b.setAttribute("aria-label", "Ampliar o gráfico");
      b.addEventListener("click", () => toggleFull(card, b));
      const g = document.createElement("div"); g.className = "btns"; g.append(dB, b);
      head.appendChild(g);
    });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape" && $("#dataDlg").hidden) { const f = $(".card.full"); if (f) toggleFull(f, f.querySelector(".btns .icon-btn:last-child")); } });
    $("#backdrop").addEventListener("click", () => {
      if (!$("#dataDlg").hidden) { $("#dataClose").click(); return; }
      const f = $(".card.full"); if (f) toggleFull(f, f.querySelector(".btns .icon-btn:last-child")); });
  }
  function toggleFull(card, btn) {
    const on = !card.classList.contains("full");
    card.classList.toggle("full", on); document.body.classList.toggle("has-full", on); $("#backdrop").hidden = !on;
    btn.querySelector("span").textContent = on ? "fechar" : "ampliar"; btn.setAttribute("aria-label", on ? "Fechar o gráfico ampliado" : "Ampliar o gráfico");
    requestAnimationFrame(() => card.querySelectorAll(".js-plotly-plot").forEach((el) => Plotly.Plots.resize(el)));
    if (on) btn.focus();
  }

  /* ================================================================== visão geral */
  INIT.visao = function () {
    const O = A.overview, op = A.optics, k = O.kpis, B = A.benchmark, V = A.variability, I = A.interpret;
    const bm = O.benchmark_measurements, campaignMeas = Object.values(bm).reduce((a, b) => a + b, 0);
    // contadores da abertura (sobem de zero na primeira vez)
    const C = [[k.literature_records, "sínteses de ouro relatadas"], [campaignMeas, "medidas de laboratório autônomo"],
      [k.literature_dois, "artigos com DOI"], [k.mie_validation_n, "esferas para validar o Mie"]];
    $("#ov-count").innerHTML = C.map(([v, l]) => `<div><b data-v="${v}">${ni(v)}</b><span>${l}</span></div>`).join("");
    if (!(window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches)) {
      const els = [...document.querySelectorAll("#ov-count b")], t0 = performance.now();
      const tick = (t) => { const f = Math.min(1, (t - t0) / 1100), e = 1 - Math.pow(1 - f, 3);
        els.forEach((el) => { el.textContent = ni(+el.dataset.v * e); }); if (f < 1) requestAnimationFrame(tick); };
      requestAnimationFrame(tick);
    }
    // faixa de cores do ouro coloidal por tamanho
    const G = goldColors(), d = op.d, strip = $("#ov-strip");
    strip.style.background = `linear-gradient(90deg, ${G.cols.map((c, i) => `${c} ${(100 * G.pos[i]).toFixed(1)}%`).join(", ")})`;
    $("#ov-ticks").innerHTML = [2, 5, 10, 20, 50, 100, 200].map((x) => `<span style="left:${(100 * (Math.log10(x) - G.lmin) / (G.lmax - G.lmin)).toFixed(1)}%">${x} nm</span>`).join("");
    const lam = (dd) => interp(Math.log(dd), op.lspr_curve.d.map(Math.log), op.lspr_curve.lambda);
    strip.addEventListener("mousemove", (e) => {
      const r = strip.getBoundingClientRect(), f = Math.min(1, Math.max(0, (e.clientX - r.left) / r.width)), dd = Math.pow(10, G.lmin + f * (G.lmax - G.lmin));
      const i = G.pos.reduce((b, p, j) => (Math.abs(p - f) < Math.abs(G.pos[b] - f) ? j : b), 0), tip = $("#ov-strip-tip");
      tip.style.left = (100 * f) + "%"; tip.textContent = `${nf(dd, dd < 10 ? 1 : 0)} nm · LSPR ${nf(lam(dd), 0)} nm · ${G.cols[i]}`;
    });
    // achados: números calculados dos dados
    const wins = Object.values(B.datasets).filter((x) => x.paired["GP-EI"].p < 0.05 && x.paired["GP-EI"].wins > x.paired["GP-EI"].losses).length;
    const ag = I.agnp, imp = ag.features.map((_, j) => ag.values.reduce((a, r) => a + Math.abs(r[j] || 0), 0));
    const topF = ag.features[imp.indexOf(Math.max(...imp))];
    const F = [
      ["optica", nf(k.mie_median_abs_residual, 1) + " nm", `erro mediano do Mie, sem ajuste, ao prever o pico de absorção de ${ni(k.mie_validation_n)} esferas relatadas.`, "§4.4 · §4.10"],
      ["designer", "R² " + nf(k.designer_cv_r2, 2), `do GP do Designer em validação cruzada na campanha AgNP real; ${nf(100 * k.designer_coverage, 0)} % das medidas caem no IC 95 %.`, "§4.5 · §4.18"],
      ["aprendizado", `${wins} de ${Object.keys(B.datasets).length}`, "campanhas em que o GP-EI chega ao top 5 % antes do acaso com significância (Wilcoxon pareado); nas demais, empate.", "§4.15"],
      ["variabilidade", `${nf(V.turkevich.q10_q90[0], 1)}–${nf(V.turkevich.q10_q90[1], 1)} nm`, `tamanho da mesma rota de Turkevich em ${ni(V.turkevich.n_papers)} artigos (10–90 %): a premissa da variabilidade multi-fonte.`, "§4.7 · §4.17"],
      ["variabilidade", `R² ${nf(V.aunc_generalization.r2_random, 2)} → ${nf(V.aunc_generalization.r2_new_paper, 2)}`, "ao prever a emissão de AuNC para um artigo nunca visto em vez de uma síntese nova: o contexto da fonte pesa.", "§4.7"],
      ["causal", `${A.causal.effects.filter((e) => e.verdict.startsWith("confirma")).length} de ${A.causal.effects.length}`, `efeitos causais estimados concordam com a literatura (NaBH₄ ×${nf(A.causal.effects[0].estimate, 2)}, sementes ×${nf(A.causal.effects[1].estimate, 2)}, CTAB → forma, tiol), por AIPW com bootstrap de artigos.`, "§4.9"],
      ["interpretabilidade", topF, "é a variável que mais move a perda espectral na campanha AgNP (SHAP exato sobre o GP).", "§4.13"],
      ["caracterizacao", `${ni(A.xrd.geometry.n_rings)} anéis`, `do CeO₂ indexados com resíduo de ${nf(A.xrd.geometry.rms_residual_px, 2)} px: feixe de ${nf(A.xrd.geometry.energy_keV, 1)} keV.`, "§4.2"],
    ];
    $("#ov-find").innerHTML = F.map(([tab, v, txt, sec]) => `<a href="#${tab}"><span class="fi">${ico(tab)}</span><span class="fv">${esc(v)}</span><span class="ft">${esc(txt)}</span><span class="fs">${sec} · abrir →</span></a>`).join("");
    // conferência com a literatura
    const CE = A.causal.effects, Hs = op.haiss, Tk = V.turkevich, XR = A.xrd.geometry;
    const chk = (cond, warn) => (cond ? `<span class="ok-ico y" aria-label="confere">✓</span>` : warn ? `<span class="ok-ico w" aria-label="parcial">!</span>` : `<span class="ok-ico w" aria-label="não confere">✗</span>`);
    const CK = [
      ["optica", "LSPR de AuNP de 20 nm em água", `${nf(Hs.mie_20nm, 0)} nm (Mie)`, "≈ 520–522 nm (Link & El-Sayed 1999; Haiss et al. 2007)", Hs.mie_20nm > 517 && Hs.mie_20nm < 526],
      ["optica", "Deslocamento do LSPR com o tamanho, 25–100 nm", `máx. ${nf(Hs.max_abs_diff, 1)} nm de diferença`, "curva empírica de Haiss et al. (2007)", Hs.max_abs_diff < 5],
      ["optica", "Pico previsto × pico relatado (798 esferas)", `erro mediano ${nf(k.mie_median_abs_residual, 1)} nm`, "dentro da resolução típica dos relatos (pico lido no espectro, tamanho por TEM)", k.mie_median_abs_residual < 5],
      ["variabilidade", "Tamanho na rota de Turkevich (mediana)", `${nf(Tk.median, 1)} nm`, "12–20 nm no protocolo padrão (Turkevich et al. 1951; Frens 1973: 16 nm)", Tk.median > 12 && Tk.median < 20],
    ].concat(CE.map((e) => ["causal", e.name, `${e.binary ? "RR " : "×"}${nf(e.estimate, 2)} (${nf(e.estimate_ci95[0], 2)}–${nf(e.estimate_ci95[1], 2)})`,
      `${e.expected.dir === "<1" ? "deve diminuir" : "deve aumentar"} (${e.expected.ref})`, e.verdict === "confirma", e.verdict.startsWith("confirma")]))
      .concat([["caracterizacao", "Reflexos do padrão CeO₂", `${ni(XR.n_rings)} anéis, resíduo ${nf(XR.rms_residual_px, 2)} px`, "fluorita Fm-3m: só hkl todos pares ou todos ímpares; a = 5,4116 Å (NIST SRM 674b)", XR.n_rings >= 10 && XR.rms_residual_px < 0.5]]);
    $("#ov-check").innerHTML = "<thead><tr><th><span class=\"sr\">Situação</span></th><th>Verificação</th><th>Resultado deste painel</th><th>Literatura</th></tr></thead><tbody>" +
      CK.map(([tab, what, res, lit, good, warn]) => `<tr><td>${chk(good, warn)}</td><td><a href="#${tab}">${esc(what)}</a></td><td class="num" style="text-align:left">${esc(res)}</td><td>${esc(lit)}</td></tr>`).join("") + "</tbody>";
    // progresso das 18 seções + mapa
    const M = O.map, cnt = (x) => M.filter((m) => m.status === x).length;
    $("#ov-prog").innerHTML = `<div class="big">${cnt("experimental")}<span>de ${M.length} seções com dados experimentais</span></div>` +
      `<div class="bar" role="img" aria-label="${cnt("experimental")} experimentais, ${cnt("parcial")} parciais, ${cnt("laboratorio")} aguardam o laboratório">` +
      `<i style="flex:${cnt("experimental")};background:var(--ok)"></i><i style="flex:${cnt("parcial")};background:var(--warn)"></i><i style="flex:${cnt("laboratorio")};background:var(--line-strong)"></i></div>` +
      `<div class="legend-row"><span><span class="dot exp" style="display:inline-block;width:8px;height:8px;border-radius:50%"></span> ${cnt("experimental")} com dados experimentais</span>` +
      `<span><span class="dot par" style="display:inline-block;width:8px;height:8px;border-radius:50%"></span> ${cnt("parcial")} parciais</span>` +
      `<span><span class="dot lab" style="display:inline-block;width:8px;height:8px;border-radius:50%"></span> ${cnt("laboratorio")} aguardam o laboratório</span></div>`;
    const st = { experimental: ["exp", "dados experimentais"], parcial: ["par", "parcial"], laboratorio: ["lab", "aguarda o laboratório"] };
    $("#ov-map").innerHTML = M.map((m) => `<a href="#${m.tab}"><span class="n">§${m.sec}</span>` +
      `<span class="t">${esc(m.title)}</span><span class="st ${st[m.status][0]}">● ${st[m.status][1]}${m.note ? ": " + esc(m.note) : ""}</span></a>`).join("");
    heroFx();
    drawer(() => {
      const t = T(), mv = mieView(), G2 = goldColors();
      const sc = mv.ld.map((l) => mv.wl.map(() => l));          // cor da superfície = diâmetro → cor real da dispersão
      const dk = { color: "rgba(245,242,244,.72)", size: 10 };
      const ax = (title) => ({ title: { text: title, font: { color: "rgba(245,242,244,.82)", size: 12 } }, tickfont: dk, gridcolor: "rgba(255,255,255,.10)",
        linecolor: "rgba(255,255,255,.25)", zerolinecolor: "rgba(255,255,255,.1)", showbackground: false });
      Plotly.react("ov-hero", [{ type: "surface", x: mv.wl, y: mv.ld, z: mv.z, surfacecolor: sc, cmin: G2.lmin, cmax: G2.lmax,
        colorscale: G2.scale, showscale: false, contours: { z: { show: false } },
        lighting: { ambient: 0.62, diffuse: 0.75, specular: 0.35, roughness: 0.45, fresnel: 0.2 }, lightposition: { x: -1e4, y: -1e4, z: 2e4 },
        customdata: sc.map((r) => r.map((l) => Math.pow(10, l))),
        hovertemplate: "λ = %{x} nm<br>d = %{customdata:.1f} nm<br>extinção rel. %{z:.2f}<extra></extra>" }],
      { paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)", separators: "," + NB, margin: { l: 0, r: 0, t: 18, b: 0 },
        font: { family: '"IBM Plex Sans", sans-serif', color: "#f5f2f4" }, uirevision: "hero",
        hoverlabel: { bgcolor: "#1d1a22", bordercolor: "rgba(255,255,255,.2)", font: { color: "#fff" } },
        scene: { xaxis: ax("λ (nm)"), yaxis: ax("log₁₀ d (nm)"), zaxis: ax("extinção"), bgcolor: "rgba(0,0,0,0)", aspectmode: "cube",
          camera: { eye: { x: -1.55, y: -1.4, z: 0.8 } } } }, CFG);
      $("#ov-hero").setAttribute("role", "figure"); $("#ov-hero").setAttribute("aria-label", "Gráfico 3D: extinção de nanopartículas de ouro por comprimento de onda e diâmetro, colorida pela cor real da dispersão");
      const names = Object.keys(B.datasets);
      plot("ov-bench", B.arms.map((arm, i) => ({ type: "scatter", mode: "markers", name: arm, y: names,
        x: names.map((n) => B.datasets[n].median_censored[arm]),
        marker: { size: 12, color: t.cat[i], line: { width: 2, color: t.surface } },
        hovertemplate: `${arm}<br>%{y}: %{x:.1f} experimentos<extra></extra>` })),
      { xaxis: { title: { text: "experimentos até o top 5 % (mediana)" }, rangemode: "tozero" }, margin: { l: 110 }, legend: { y: 1.18 } });
      const src = Object.entries(A.literature.n_by_source).filter((x) => x[0] !== "AuNCs 2025").concat([["AuNC (fluorescência)", k.aunc_entries]])
        .concat(Object.entries(bm)).sort((a, b) => b[1] - a[1]);
      plot("ov-sources", [{ type: "bar", orientation: "h", y: src.map((x) => x[0]), x: src.map((x) => x[1]),
        marker: { color: t.cat[0] }, hovertemplate: "%{y}: %{x:,} registros<extra></extra>" }],
      { xaxis: { type: "log", title: { text: "registros" }, dtick: 1 }, yaxis: { autorange: "reversed" }, margin: { l: 150 } });
    });
  };

  // fundo animado da abertura: AuNP com a cor real de cada tamanho em movimento browniano sobre a rede hexagonal do GO
  function heroFx() {
    const cv = $("#fx"); if (!cv || !cv.getContext) return;
    const ctx = cv.getContext("2d"), G = goldColors(), reduce = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
    let W = 0, H = 0, P = [], lattice = null, raf = 0, visible = true;
    function resize() {
      const r = cv.getBoundingClientRect(), dpr = Math.min(2, window.devicePixelRatio || 1);
      W = r.width; H = r.height; if (!W || !H) return;
      cv.width = W * dpr; cv.height = H * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      lattice = document.createElement("canvas"); lattice.width = W * dpr; lattice.height = H * dpr;
      const lc = lattice.getContext("2d"); lc.setTransform(dpr, 0, 0, dpr, 0, 0); lc.strokeStyle = "rgba(255,255,255,.055)"; lc.lineWidth = 1;
      const a = 18, h = a * Math.sqrt(3);
      for (let y = -h, row = 0; y < H + h; y += h / 2, row++) for (let x = (row % 2) * 1.5 * a - a; x < W + 2 * a; x += 3 * a) {
        lc.beginPath(); for (let k = 0; k <= 6; k++) { const an = Math.PI / 3 * k; lc.lineTo(x + a * Math.cos(an), y + a * Math.sin(an)); } lc.stroke(); }
      const n = Math.round(Math.min(90, Math.max(28, W * H / 14000)));
      P = Array.from({ length: n }, (_, i) => { const f = 0.25 + 0.6 * ((i * 0.618) % 1), j = Math.round(f * (G.cols.length - 1));
        return { x: Math.random() * W, y: Math.random() * H, r: 2 + 7 * Math.pow((i * 0.37) % 1, 2), vx: (Math.random() - 0.5) * 0.25, vy: (Math.random() - 0.5) * 0.25, c: G.cols[j] }; });
    }
    function frame() {
      if (!W) return;
      ctx.clearRect(0, 0, W, H); if (lattice) ctx.drawImage(lattice, 0, 0, W, H);
      for (const p of P) {
        if (!reduce) { p.vx += (Math.random() - 0.5) * 0.05; p.vy += (Math.random() - 0.5) * 0.05; p.vx *= 0.985; p.vy *= 0.985; p.x += p.vx; p.y += p.vy;
          if (p.x < -10) p.x = W + 10; if (p.x > W + 10) p.x = -10; if (p.y < -10) p.y = H + 10; if (p.y > H + 10) p.y = -10; }
        const g = ctx.createRadialGradient(p.x - p.r * 0.35, p.y - p.r * 0.35, p.r * 0.1, p.x, p.y, p.r * 2.6);
        g.addColorStop(0, "rgba(255,240,220,.95)"); g.addColorStop(0.28, p.c); g.addColorStop(1, "rgba(0,0,0,0)");
        ctx.globalAlpha = 0.55; ctx.fillStyle = g; ctx.beginPath(); ctx.arc(p.x, p.y, p.r * 2.6, 0, 2 * Math.PI); ctx.fill();
      }
      ctx.globalAlpha = 1;
      if (!reduce && visible && !document.hidden && current === "visao") raf = requestAnimationFrame(frame); else raf = 0;
    }
    const kick = () => { if (!raf) raf = requestAnimationFrame(frame); };
    resize(); frame();
    window.addEventListener("resize", () => { resize(); frame(); });
    if ("IntersectionObserver" in window) new IntersectionObserver((es) => { visible = es[0].isIntersecting; if (visible) kick(); }).observe(cv);
    document.addEventListener("visibilitychange", kick);
    window.addEventListener("hashchange", () => setTimeout(() => { if (current === "visao") { resize(); kick(); } }, 30));
  }

  /* ================================================================== literatura */
  INIT.literatura = function () {
    const L = A.literature, R = L.records, n = R.size.length;
    const tri = new Map(L.tri_ref.idx.map((i, k) => [i, k]));
    const opt = (pairs) => pairs.map(([v, l]) => `<option value="${v}">${esc(l)}</option>`).join("");
    $("#lit-src").innerHTML = '<option value="-1">Todas</option>' + opt(L.sources.map((s, i) => [i, s]));
    $("#lit-red").innerHTML = '<option value="-2">Todos</option><option value="-1">não citado</option>' + opt(L.reductants.map((s, i) => [i, s.replace(/_/g, " ")]));
    $("#lit-cap").innerHTML = '<option value="-2">Todos</option><option value="-1">não citado</option>' + opt(L.capping.map((s, i) => [i, s.replace(/_/g, " ")]));
    $("#lit-morph").innerHTML = '<option value="-2">Todas</option>' + opt(L.morph.map((s, i) => [i, s]));
    const RED3 = ["citrato", "NaBH₄", "ácido ascórbico"];
    const F = ["#lit-src", "#lit-red", "#lit-cap", "#lit-morph", "#lit-seed"];
    let I = [];
    function select() {
      const s = +$("#lit-src").value, r = +$("#lit-red").value, c = +$("#lit-cap").value, m = +$("#lit-morph").value,
        sd = +$("#lit-seed").value, go = $("#lit-go").checked;
      const out = [];
      for (let i = 0; i < n; i++) {
        if (s >= 0 && R.source[i] !== s) continue;
        if (r !== -2 && R.red[i] !== r) continue;
        if (c !== -2 && R.cap[i] !== c) continue;
        if (m !== -2 && R.morph[i] !== m) continue;
        if (sd >= 0 && R.seed[i] !== sd) continue;
        if (go && !R.go[i]) continue;
        out.push(i);
      }
      I = out;
    }
    const draw = () => {
      const t = T();
      const sizes = finite(I.map((i) => R.size[i])), peaks = finite(I.map((i) => R.peak[i]));
      kpis("#lit-kpis", [
        { k: "Registros na seleção", v: ni(I.length), s: `${ni(sizes.length)} com tamanho` },
        { k: "Tamanho mediano", v: nf(median(sizes), 1), u: "nm", s: sizes.length ? `quartis ${nf(quant(sizes, .25), 0)}–${nf(quant(sizes, .75), 0)} nm` : "sem tamanho na seleção" },
        { k: "Pico de absorção mediano", v: nf(median(peaks), 0), u: "nm", s: `${ni(peaks.length)} registros` },
        { k: "Rota mediada por sementes", v: nf(100 * I.filter((i) => R.seed[i]).length / Math.max(I.length, 1), 1), u: "%" },
      ]);
      const pts = I.filter((i) => R.size[i] != null && R.peak[i] != null && R.T[i] != null);
      const groups = [0, 1, 2, -9].map((g) => pts.filter((i) => g === -9 ? !(R.red[i] >= 0 && R.red[i] <= 2) : R.red[i] === g));
      plot("lit-3d", groups.map((g, k) => ({ type: "scatter3d", mode: "markers", name: k < 3 ? RED3[k] : "outros",
        x: g.map((i) => R.T[i]), y: g.map((i) => Math.log10(R.size[i])), z: g.map((i) => R.peak[i]),
        customdata: g.map((i) => [R.size[i], L.sources[R.source[i]], i]),
        marker: { size: 3.8, color: k < 3 ? t.cat[k] : t.other, opacity: 0.85, line: { width: 0 } },
        hovertemplate: "T = %{x:.0f} °C<br>d = %{customdata[0]:.1f} nm<br>pico = %{z:.0f} nm<br>%{customdata[1]} · clique para detalhes<extra></extra>" })),
      { margin: { l: 0, r: 0, t: 30, b: 0 }, uirevision: "lit3d",
        scene: scene("T (°C)", "log₁₀ tamanho (nm)", "pico (nm)", { camera: { eye: { x: 1.25, y: -1.3, z: 0.7 } } }),
        annotations: pts.length ? [] : [{ text: "Nenhum registro da seleção tem tamanho, pico e temperatura.", showarrow: false, xref: "paper", yref: "paper", x: 0.5, y: 0.5, font: { color: t.muted } }] });
      const lv = sizes.filter((x) => x > 0).map(Math.log10), edges = lin(-0.3, 3, 45), cnt = new Array(44).fill(0);
      for (const v of lv) { const j = Math.floor((v - edges[0]) / (edges[1] - edges[0])); if (j >= 0 && j < 44) cnt[j]++; }
      const mid = edges.slice(0, -1).map((e) => e + (edges[1] - edges[0]) / 2), md = median(sizes);
      plot("lit-hist", [{ type: "bar", x: mid, y: cnt, marker: { color: t.cat[0] }, width: (edges[1] - edges[0]) * 0.92,
        customdata: mid.map((m) => Math.pow(10, m)), hovertemplate: "≈ %{customdata:.1f} nm: %{y} registros<extra></extra>" }],
      { xaxis: { title: { text: "tamanho (nm)" }, tickvals: [0, 0.477, 1, 1.477, 2, 2.477, 3], ticktext: ["1", "3", "10", "30", "100", "300", "1000"] },
        yaxis: { title: { text: "registros" } }, bargap: 0,
        shapes: sizes.length ? [{ type: "line", x0: Math.log10(md), x1: Math.log10(md), y0: 0, y1: 1, yref: "paper", line: { color: t.ink, width: 1.5 } }] : [],
        annotations: sizes.length ? [{ x: Math.log10(md), y: 1, yref: "paper", text: `mediana ${nf(md, 1)} nm`, showarrow: false, xanchor: "left", xshift: 6, font: { color: t.ink, size: 11 } }] : [] });
      const mc = L.morph.map((_, j) => I.filter((i) => R.morph[i] === j).length);
      const ord = mc.map((c, j) => [c, j]).filter((x) => x[0] > 0).sort((a, b) => b[0] - a[0]).slice(0, 8);
      plot("lit-morph-bar", [{ type: "bar", orientation: "h", y: ord.map((o) => L.morph[o[1]]), x: ord.map((o) => o[0]),
        marker: { color: t.cat[0] }, hovertemplate: "%{y}: %{x:,} registros<extra></extra>" }],
      { yaxis: { autorange: "reversed" }, margin: { l: 80, t: 4, b: 30 } });
    };
    const update = () => { select(); draw(); };
    F.concat(["#lit-go"]).forEach((s) => $(s).addEventListener("change", update));
    $("#lit-reset").addEventListener("click", () => { F.forEach((s) => { $(s).selectedIndex = 0; }); $("#lit-go").checked = false; update(); });
    select(); drawer(draw);
    $("#lit-3d").on("plotly_click", (ev) => {
      const pt = ev.points && ev.points[0]; if (!pt || !pt.customdata) return;
      const i = pt.customdata[2], k = tri.get(i), title = k == null ? "" : L.tri_ref.title[k], doi = k == null ? "" : L.tri_ref.doi[k];
      const link = doi ? `<a href="https://doi.org/${esc(doi)}" target="_blank" rel="noopener">doi.org/${esc(doi)}</a>`
        : title ? `<a href="https://scholar.google.com/scholar?q=${encodeURIComponent(title)}" target="_blank" rel="noopener">buscar o artigo</a>` : "";
      const lab = (arr, v) => v >= 0 ? arr[v].replace(/_/g, " ") : "não citado";
      $("#lit-pick").innerHTML = `<b>${esc(title || "Registro sem título")}</b> ${link}<dl>` +
        `<div><dt>Base</dt><dd>${esc(L.sources[R.source[i]])}</dd></div><div><dt>Tamanho</dt><dd>${nf(R.size[i], 1)} nm</dd></div>` +
        `<div><dt>Pico</dt><dd>${nf(R.peak[i], 0)} nm</dd></div><div><dt>Temperatura</dt><dd>${nf(R.T[i], 0)} °C</dd></div>` +
        `<div><dt>Redutor</dt><dd>${esc(lab(L.reductants, R.red[i]))}</dd></div><div><dt>Ligante</dt><dd>${esc(lab(L.capping, R.cap[i]))}</dd></div>` +
        `<div><dt>Morfologia</dt><dd>${esc(R.morph[i] >= 0 ? L.morph[R.morph[i]] : "—")}</dd></div><div><dt>Rota</dt><dd>${R.seed[i] ? "com sementes" : "direta"}</dd></div></dl>`;
    });
    drawer(() => {
      const t = T(), Y = L.reductant_by_year, years = Y.years, tot = years.map((_, i) => Object.values(Y.series).reduce((s, v) => s + v[i], 0));
      const keep = years.map((_, i) => tot[i] >= 40);
      const names = [["trisodium_citrate", "citrato"], ["NaBH4", "NaBH₄"], ["ascorbic_acid", "ácido ascórbico"]];
      plot("lit-years", names.map(([key, lab], k) => ({ type: "scatter", mode: "lines+markers", name: lab,
        x: years.filter((_, i) => keep[i]), y: years.map((_, i) => 100 * (Y.series[key] || [])[i] / tot[i]).filter((_, i) => keep[i]),
        customdata: years.map((_, i) => tot[i]).filter((_, i) => keep[i]),
        line: { color: t.cat[k], width: 2 }, marker: { size: 6, color: t.cat[k] }, hovertemplate: `${lab}: %{y:.1f} % de %{customdata} sínteses (%{x})<extra></extra>` })),
      { yaxis: { title: { text: "% das sínteses do ano" }, rangemode: "tozero" }, xaxis: { title: { text: "ano de publicação" } }, hovermode: "x unified" });
    });
    const rows = L.go_rows;
    function table(q) {
      q = (q || "").toLowerCase();
      const f = rows.filter((r) => !q || [r.doi, r.title, r.reductants, r.supports, r.morph].join(" ").toLowerCase().includes(q));
      $("#go-n").textContent = q ? `${f.length} de ${rows.length} na busca.` : "";
      $("#go-tbl").innerHTML = "<thead><tr><th>Ano</th><th>Artigo / DOI</th><th>Redutores</th><th>Suporte</th><th>Morfologia</th><th class='num'>Tamanho (nm)</th><th class='num'>T (°C)</th></tr></thead><tbody>" +
        f.map((r) => `<tr><td class="num">${r.year || "—"}</td><td>${esc(r.title || r.source)}${r.doi ? `<br><a href="https://doi.org/${esc(r.doi)}" target="_blank" rel="noopener">${esc(r.doi)}</a>` : ""}</td>` +
          `<td>${esc(r.reductants.replace(/\|/g, ", ").replace(/_/g, " ")) || "—"}</td><td>${esc(r.supports.replace(/\|/g, ", ").replace(/_/g, " ")) || "—"}</td>` +
          `<td>${esc(r.morph.replace(/\|/g, ", ")) || "—"}</td><td class="num">${r.size == null ? "—" : nf(r.size, 1)}</td><td class="num">${r.T == null ? "—" : nf(r.T, 0)}</td></tr>`).join("") +
        (f.length ? "" : `<tr><td colspan="7">Nada encontrado para "${esc(q)}".</td></tr>`) + "</tbody>";
    }
    $("#go-q").addEventListener("input", (e) => table(e.target.value));
    table("");
  };

  /* ================================================================== óptica e J */
  INIT.optica = function () {
    const O = A.optics, wl = O.wl, dg = O.d, ld = dg.map(Math.log);
    const C = O.C_ext.map((row, i) => row.map((v) => v * O.C_ext_max[i]));      // nm² por partícula
    const vol = dg.map((d) => Math.PI * d * d * d / 6);
    const tg = O.target, gridW = []; for (let w = tg.grid[0]; w <= tg.grid[1] + 1e-9; w += tg.grid[2]) gridW.push(w);
    const tgOnGrid = gridW.map((w) => interp(w, tg.wl, tg.E)), tmax = Math.max(...tgOnGrid), tN = tgOnGrid.map((v) => v / tmax);
    const gi = gridW.map((w) => wl.indexOf(w));
    const MV = mieView();          // a grade de 2 nm de J coincide com a de Mie
    let mode = "max";
    const dOf = () => 2 * Math.exp(+$("#op-d").value / 1000 * Math.log(75)), sOf = () => +$("#op-s").value / 100;
    const setD = (d) => { $("#op-d").value = Math.round(Math.log(d / 2) / Math.log(75) * 1000); };
    function ensemble(d, s) {
      const w = new Float64Array(dg.length);
      if (s <= 0.005) {                                         // monodisperso: interpola em log d entre os vizinhos
        let j = 0; while (j < ld.length - 2 && ld[j + 1] < Math.log(d)) j++;
        const f = Math.min(1, Math.max(0, (Math.log(d) - ld[j]) / (ld[j + 1] - ld[j]))); w[j] = 1 - f; w[j + 1] = f;
      } else {
        const sl = Math.sqrt(Math.log(1 + s * s)), mu = Math.log(d) - sl * sl / 2; let tot = 0;
        for (let i = 0; i < ld.length; i++) { w[i] = Math.exp(-0.5 * ((ld[i] - mu) / sl) ** 2); tot += w[i]; }
        for (let i = 0; i < ld.length; i++) w[i] /= tot;
      }
      const E = new Array(wl.length).fill(0); let V = 0;
      for (let i = 0; i < dg.length; i++) { if (w[i] < 1e-9) continue; const Ci = C[i]; for (let j = 0; j < wl.length; j++) E[j] += w[i] * Ci[j]; V += w[i] * vol[i]; }
      return { E, V };
    }
    function J(E) {
      const e = gi.map((k, i) => (k >= 0 ? E[k] : interp(gridW[i], wl, E))), m = Math.max(...e);
      let acc = 0; for (let i = 0; i < e.length; i++) acc += ((e[i] / m - tN[i]) / tg.s_m) ** 2;
      return acc / e.length;
    }
    const PRE = [["alvo do pré-registro", tg.diameter, 100 * tg.sigma], ["mais largo (σ = 20 %)", tg.diameter, 20],
      ["Turkevich típico", 15, 15], ["sementes grandes", 45, 10], ["agregado / grande", 90, 15], ["aglomerado pequeno", 4, 20]];
    const G = goldColors(), A0 = () => +$("#op-a").value / 100;
    const colorOf = (d, s, a0) => { const { E, V } = ensemble(d, s); return rgbHex(colloidRGB(wl, E.map((x) => x / V / G.ref), a0)); };
    $("#op-presets").insertAdjacentHTML("beforeend", PRE.map(([l, d, s], i) =>
      `<button type="button" data-i="${i}" aria-pressed="${i === 0}"><i style="background:${colorOf(d, s / 100, 1.5)}"></i>${esc(l)} <span class="muted">${nf(d, 0)} nm · ${nf(s, 0)} %</span></button>`).join(""));
    $("#op-presets").addEventListener("click", (e) => { const b = e.target.closest("button"); if (!b) return;
      const [, d, s] = PRE[+b.dataset.i]; setD(d); $("#op-s").value = s; mark(b); dyn(); });
    const mark = (b) => $("#op-presets").querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", x === b ? "true" : "false"));
    function dyn() {                                           // só o que muda com os controles
      const t = T(), d = dOf(), s = sOf(), { E, V } = ensemble(d, s), j = J(E), mx = Math.max(...E);
      $("#op-d-o").textContent = nf(d, d < 10 ? 1 : 0) + " nm"; $("#op-s-o").textContent = nf(100 * s, 0) + " %";
      const a0 = A0(), col = rgbHex(colloidRGB(wl, E.map((x) => x / V / G.ref), a0));
      $("#op-a-o").textContent = nf(a0, 2); $("#op-cuv").style.setProperty("--col", col);
      $("#op-cuv-h").textContent = `${col} · mesma massa de ouro que uma dispersão de 20 nm com A = ${nf(a0, 2)} no pico`;
      $("#op-cuv-t").textContent = d < 3.5 ? "Aglomerados muito pequenos: sem plásmon definido, cor pálida e amarronzada."
        : d < 55 ? "Vermelho-rubi típico do ouro coloidal: o plásmon absorve o verde (~520 nm)."
          : d < 95 ? "Partículas maiores: o pico se desloca e alarga, a dispersão fica púrpura."
            : "Partículas grandes: espalhamento forte e pico largo, a dispersão fica azul-acinzentada.";
      kpis("#op-kpis", [
        { k: "λ do LSPR previsto", v: nf(peakOf(wl, E), 0), u: "nm", s: "máximo acima de 480 nm" },
        { k: "Perda J (Eq. 1)", v: j < 0.01 ? "< 0,01" : nf(j, j < 10 ? 2 : j < 100 ? 1 : 0), s: `log₁₀ J = ${nf(Math.log10(j), 2)}`, key: true },
        { k: "Especificação (rascunho)", v: j <= 1 ? "atende" : "não atende", s: "J ≤ 1 no pré-registro (sₘ = 0,002)" },
        { k: "Extinção por volume de Au", v: nf(mx / V, 3), u: "nm⁻¹", s: "Cext,máx / V: partículas pequenas absorvem menos por átomo" },
      ]);
      const y = mode === "max" ? E.map((v) => v / mx) : E.map((v) => v / V);
      const tr = [];
      if (mode === "max") {
        tr.push({ type: "scatter", mode: "lines", name: `alvo do pré-registro (${nf(tg.diameter, 0)} nm, σ = ${nf(100 * tg.sigma, 0)} %)`, x: gridW, y: tN,
          line: { color: t.ink, width: 1.6, dash: "dash" }, hovertemplate: "λ = %{x} nm: %{y:.3f}<extra>alvo</extra>" });
        tr.push({ type: "scatter", mode: "lines", x: gridW, y: gi.map((k) => y[k]), fill: "tonexty", fillcolor: hexA(t.dark ? "#e0567a" : "#9b1b3a", 0.16),
          line: { width: 0 }, hoverinfo: "skip", showlegend: false });
      }
      tr.push({ type: "scatter", mode: "lines", name: `previsto (d = ${nf(d, 0)} nm, σ = ${nf(100 * s, 0)} %)`, x: wl, y,
        line: { color: t.cat[0], width: 2.4 }, hovertemplate: "λ = %{x} nm: %{y:.3f}<extra>previsto</extra>" });
      plot("op-spec", tr, { xaxis: { title: { text: "λ (nm)" } }, yaxis: { title: { text: mode === "max" ? "extinção normalizada" : "Cext / V (nm⁻¹)" }, rangemode: "tozero" } });
      now3 = { d, s, j }; mark3();
    }
    let now3 = null;
    const mark3 = throttle(() => {
      const { d, s, j } = now3, k = ld.reduce((b, l, i) => (Math.abs(l - Math.log(d)) < Math.abs(ld[b] - Math.log(d)) ? i : b), 0);
      const es = $("#op-surf"), ej = $("#op-J");
      whenVisible(es, () => { if (es.data) Plotly.restyle(es, { y: [MV.cj.map(() => Math.log10(dg[k]))], z: [MV.cj.map((jj) => O.C_ext[k][jj] + 0.01)] }, [1]); });
      whenVisible(ej, () => { if (ej.data) Plotly.restyle(ej, { x: [[Math.log10(d)]], y: [[s]], z: [[Math.log10(Math.max(j, 1e-4))]] }, [1]); });
    }, 120);
    function full() {                                          // superfícies e validação: só na montagem e no tema
      const t = T(), d = dOf(), k = ld.reduce((b, l, i) => (Math.abs(l - Math.log(d)) < Math.abs(ld[b] - Math.log(d)) ? i : b), 0);
      plot("op-surf", [{ type: "surface", x: MV.wl, y: MV.ld, z: MV.z, surfacecolor: MV.ld.map((l) => MV.wl.map(() => l)), cmin: G.lmin, cmax: G.lmax,
        colorscale: G.scale, showscale: false, opacity: 0.97, lighting: { ambient: 0.65, diffuse: 0.7, specular: 0.3, roughness: 0.5 },
        hovertemplate: "λ = %{x} nm<br>log₁₀ d = %{y:.2f}<br>%{z:.2f}<extra></extra>" },
      { type: "scatter3d", mode: "lines", x: MV.wl, y: MV.cj.map(() => Math.log10(dg[k])), z: MV.cj.map((jj) => O.C_ext[k][jj] + 0.01), line: { color: t.ruby, width: 7 }, hoverinfo: "skip", showlegend: false }],
      { margin: { l: 0, r: 0, t: 0, b: 0 }, uirevision: "s", scene: scene("λ (nm)", "log₁₀ d (nm)", "extinção", { camera: { eye: { x: -1.5, y: -1.5, z: 0.9 } } }) });
      const JS = O.J_surface;
      plot("op-J", [{ type: "surface", x: JS.d.map(Math.log10), y: JS.sigma, z: JS.log10J, colorscale: t.seqScale, reversescale: true, showscale: false,
        hovertemplate: "d = %{customdata:.1f} nm<br>σ = %{y:.2f}<br>log₁₀ J = %{z:.2f}<extra></extra>", customdata: JS.sigma.map(() => JS.d) },
      { type: "scatter3d", mode: "markers", x: [0], y: [0], z: [0], marker: { size: 7, color: t.ruby, line: { width: 2, color: t.surface } },
        hovertemplate: "escolha atual<br>log₁₀ J = %{z:.2f}<extra></extra>", showlegend: false }],
      { margin: { l: 0, r: 0, t: 0, b: 0 }, uirevision: "j", scene: scene("log₁₀ d (nm)", "σ", "log₁₀ J") });
      const V = O.lit_spheres, srcs = [...new Set(V.source)];
      plot("op-valid", srcs.map((s, kk) => {
        const I = V.source.map((x, i) => (x === s ? i : -1)).filter((i) => i >= 0);
        return { type: "scattergl", mode: "markers", name: `relatado (${s})`, x: I.map((i) => V.size[i]), y: I.map((i) => V.peak[i]),
          customdata: I.map((i) => (V.title && V.title[i]) || V.doi[i] || "—"), marker: { size: 6, color: t.cat[kk], opacity: 0.7, line: { width: 1, color: t.surface } },
          hovertemplate: "d = %{x:.1f} nm · pico %{y:.0f} nm<br>%{customdata}<extra></extra>" };
      }).concat([{ type: "scatter", mode: "lines", name: "Mie (Johnson & Christy, σ = 10 %)", x: O.lspr_curve.d, y: O.lspr_curve.lambda,
        line: { color: t.ink, width: 2.2 }, hovertemplate: "Mie: d = %{x:.1f} nm → %{y:.0f} nm<extra></extra>" },
      { type: "scatter", mode: "lines", name: "Haiss et al. 2007 (empírica)", x: O.haiss.d, y: O.haiss.lambda,
        line: { color: t.cat[1], width: 2, dash: "dash" }, hovertemplate: "Haiss: d = %{x:.0f} nm → %{y:.0f} nm<extra></extra>" }]),
      { xaxis: { type: "log", title: { text: "tamanho relatado (nm)" }, range: [Math.log10(2.5), Math.log10(160)], tickvals: [3, 5, 10, 20, 50, 100, 150] },
        yaxis: { title: { text: "pico de absorção relatado (nm)" }, range: [495, 620] } });
      dyn();
    }
    setD(tg.diameter); $("#op-s").value = Math.round(100 * tg.sigma);          // começa no alvo: J ≈ 0
    const dynF = perFrame(dyn);
    ["#op-d", "#op-s"].forEach((s) => $(s).addEventListener("input", () => { mark(null); dynF(); }));
    $("#op-a").addEventListener("input", dynF);
    segmented("#op-norm", (v) => { mode = v; dyn(); });
    drawer(full);
    drawer(() => {
      const t = T(), H = O.haiss;
      plot("op-haiss", [
        { type: "scatter", mode: "lines", name: "Mie (este painel)", x: H.d, y: H.mie, line: { color: t.cat[0], width: 2.4 }, hovertemplate: "Mie: %{x} nm → %{y:.1f} nm<extra></extra>" },
        { type: "scatter", mode: "lines", name: "Haiss et al. 2007", x: H.d, y: H.lambda, line: { color: t.cat[1], width: 2, dash: "dash" }, hovertemplate: "Haiss: %{x} nm → %{y:.1f} nm<extra></extra>" }],
      { xaxis: { title: { text: "diâmetro (nm)" } }, yaxis: { title: { text: "λ do LSPR (nm)" } },
        annotations: [{ xref: "paper", yref: "paper", x: 0.02, y: 0.96, xanchor: "left", showarrow: false, font: { color: t.ink, size: 12 },
          text: `diferença máxima ${nf(H.max_abs_diff, 1)} nm em 25–100 nm` }] });
    });
    const NE = O.n_eff_test, best = NE.reduce((b, x) => (x.val < b.val ? x : b), NE[0]), water = NE[0];
    $("#op-neff").innerHTML = "<thead><tr><th class='num'>n do meio</th><th class='num'>erro (ajuste)</th><th class='num'>erro (validação)</th><th class='num'>viés (validação)</th><th class='num'>máx. |Mie − Haiss|</th></tr></thead><tbody>" +
      NE.map((x) => `<tr><td class="num">${nf(x.n, 3)}${x.n === 1.333 ? " (água)" : ""}</td><td class="num">${nf(x.cal, 2)} nm</td><td class="num">${x === best ? "<b>" : ""}${nf(x.val, 2)} nm${x === best ? "</b>" : ""}</td><td class="num">${nf(x.bias_val, 2)} nm</td><td class="num">${nf(x.haiss_max, 1)} nm</td></tr>`).join("") + "</tbody>";
    $("#op-neff-txt").innerHTML = `<p>O melhor índice na validação (n = ${nf(best.n, 3)}) ganha só ${nf(water.val - best.val, 2)} nm sobre a água e se afasta da curva de Haiss (${nf(best.haiss_max, 1)} contra ${nf(water.haiss_max, 1)} nm). ` +
      "O ganho está dentro da incerteza dos relatos (pico lido no espectro, tamanho por TEM), então o painel mantém a água, sem ajuste: o modelo continua sendo física pura, validada.</p>";
    const V = O.lit_spheres;
    $("#op-bins").innerHTML = "<thead><tr><th>Faixa de tamanho</th><th class='num'>Registros</th><th class='num'>Resíduo mediano (nm)</th><th class='num'>Desvio absoluto mediano (nm)</th></tr></thead><tbody>" +
      V.by_bin.map((b) => `<tr><td>${b.range}</td><td class="num">${b.n}</td><td class="num">${nf(b.median_residual, 1)}</td><td class="num">${nf(b.mad, 1)}</td></tr>`).join("") +
      `<tr><td><b>Todas</b></td><td class="num">${V.n}</td><td class="num">—</td><td class="num">${nf(V.median_abs_residual, 1)} (|resíduo| mediano; ${nf(100 * V.within_5nm, 0)} % até 5 nm)</td></tr></tbody>`;
  };

  /* ================================================================== AuNP Designer (GP no navegador) */
  function gpPredict(gp, xn, withSd = true) {
    const X = gp.X, ls = gp.ls, n = X.length, k = new Float64Array(n);
    for (let i = 0; i < n; i++) {
      let r2 = 0; const Xi = X[i]; for (let j = 0; j < ls.length; j++) { const d = (xn[j] - Xi[j]) / ls[j]; r2 += d * d; }
      const r = Math.sqrt(r2), s5 = Math.sqrt(5) * r;
      k[i] = gp.outputscale * (1 + s5 + 5 / 3 * r2) * Math.exp(-s5);
    }
    let mu = gp.const; for (let i = 0; i < n; i++) mu += k[i] * gp.alpha[i];
    if (!withSd) return [gp.y_mean + gp.y_std * mu, NaN];
    const L = gp.L, v = new Float64Array(n);                  // L v = k (substituição direta)
    let vv = 0;
    for (let i = 0; i < n; i++) { let s = k[i]; const Li = L[i]; for (let j = 0; j < i; j++) s -= Li[j] * v[j]; v[i] = s / Li[i]; vv += v[i] * v[i]; }
    return [gp.y_mean + gp.y_std * mu, gp.y_std * Math.sqrt(Math.max(gp.outputscale - vv, 1e-12))];
  }
  INIT.designer = function () {
    const D = A.designer, gp = D.gp, p = D.columns.length, lo = D.lo, hi = D.hi, P = D.points;
    const bestLn = Math.min(...D.cv.obs), dec = (j) => (hi[j] - lo[j] > 100 ? 0 : 1);
    $("#ds-sliders").innerHTML = D.labels.map((lab, j) => `<div class="ctl"><label for="ds-v${j}">${esc(lab)} <output id="ds-o${j}"></output></label>` +
      `<input type="range" id="ds-v${j}" min="${lo[j]}" max="${hi[j]}" step="${(hi[j] - lo[j]) / 200}" value="${D.best_measured.x[j]}"></div>`).join("");
    const opts = D.labels.map((l, j) => `<option value="${j}">${esc(l)}</option>`).join("");
    $("#ds-x").innerHTML = opts; $("#ds-y").innerHTML = opts; $("#ds-x").value = "3"; $("#ds-y").value = "0";
    let mode = "mean";
    const cur = () => D.labels.map((_, j) => +$("#ds-v" + j).value);
    const norm = (x) => x.map((v, j) => (v - lo[j]) / (hi[j] - lo[j]));
    const Pn = P.X.map(norm);
    function ei(mu, sd) { const z = (bestLn - mu) / sd; return (bestLn - mu) * ncdf(z) + sd * npdf(z); }
    function draw() {
      const t = T(), x = cur(), xn = norm(x);
      x.forEach((v, j) => { $("#ds-o" + j).textContent = nf(v, dec(j)); });
      const [mu, sd] = gpPredict(gp, xn);
      let bi = 0, bd = 1e9;
      Pn.forEach((r, i) => { const dd = Math.hypot(...r.map((v, j) => v - xn[j])); if (dd < bd) { bd = dd; bi = i; } });
      kpis("#ds-kpis", [
        { k: "Perda prevista no ponto", v: nf(Math.exp(mu), 3), s: `IC 95 % ${nf(Math.exp(mu - 1.96 * sd), 3)}–${nf(Math.exp(mu + 1.96 * sd), 3)}`, key: true },
        { k: "Melhor condição medida", v: nf(D.best_measured.loss, 3), s: `dp das réplicas ${nf(D.best_measured.sd, 3)}` },
        { k: "Condição medida mais próxima", v: nf(P.mean[bi], 3), s: `${P.n[bi]} réplicas · distância ${nf(bd, 2)} (escala 0–1)` },
        { k: "Validação cruzada", v: "R² " + nf(D.cv.r2, 2), s: `RMSE em ln ${nf(D.cv.rmse, 3)} · cobertura ${nf(100 * D.cv.coverage95, 0)} %` },
        { k: "Melhoria esperada (EI)", v: nf(ei(mu, sd), 4), s: "em ln(perda), sobre a melhor medida" },
      ]);
      surfAt = x; surfT();
      pdPlot(t, x, xn, mu);
    }
    let surfAt = null;
    const surfT = throttle(() => whenVisible($("#ds-surf"), () => surf(T(), surfAt, norm(surfAt))), 180);
    function surf(t, x, xn) {
      const ix = +$("#ds-x").value, iy = +$("#ds-y").value;
      const gx = lin(lo[ix], hi[ix], 32), gy = lin(lo[iy], hi[iy], 32);
      const Z = gy.map((yv) => gx.map((xv) => { const q = xn.slice(); q[ix] = (xv - lo[ix]) / (hi[ix] - lo[ix]); q[iy] = (yv - lo[iy]) / (hi[iy] - lo[iy]);
        const [m, s] = gpPredict(gp, q, mode !== "mean"); return mode === "mean" ? Math.exp(m) : mode === "sd" ? s : ei(m, s); }));
      const ztitle = mode === "mean" ? "perda prevista" : mode === "sd" ? "dp de ln(perda)" : "EI";
      const tr = [{ type: "surface", x: gx, y: gy, z: Z, colorscale: t.seqScale, reversescale: mode === "mean", opacity: 0.95, showlegend: false,
        colorbar: { title: { text: ztitle, side: "right", font: { color: t.ink2 } }, thickness: 12, len: 0.6, tickfont: { color: t.muted } },
        hovertemplate: `${D.labels[ix]} = %{x:.1f}<br>${D.labels[iy]} = %{y:.1f}<br>${ztitle} = %{z:.3f}<extra>GP</extra>` }];
      if (mode === "mean") {
        const near = [], far = [];
        Pn.forEach((r, i) => { let d2 = 0; r.forEach((v, j) => { if (j !== ix && j !== iy) d2 += (v - xn[j]) ** 2; }); (Math.sqrt(d2) < 0.25 ? near : far).push(i); });
        const pts = (I, name, col, size, op) => ({ type: "scatter3d", mode: "markers", name, x: I.map((i) => P.X[i][ix]), y: I.map((i) => P.X[i][iy]),
          z: I.map((i) => P.mean[i]), customdata: I.map((i) => P.n[i]), marker: { size, color: col, opacity: op, line: { width: 0 } },
          hovertemplate: `medida: perda %{z:.3f} (%{customdata} réplicas)<extra>${name}</extra>` });
        tr.push(pts(near, `medidas perto do corte (${near.length})`, t.ruby, 4.6, 0.95), pts(far, "demais medidas", t.other, 2.4, 0.4));
      }
      plot("ds-surf", tr, { margin: { l: 0, r: 0, t: 30, b: 0 }, uirevision: "ds", legend: { y: 1.02 }, scene: scene(D.labels[ix], D.labels[iy], ztitle) });
    }
    function pdPlot(t, x, xn, mu) {
      let ytop = 0;
      const traces = [], lay = { grid: { rows: 1, columns: p, pattern: "independent" }, showlegend: false, margin: { l: 50, r: 10, t: 16, b: 44 } };
      D.labels.forEach((lab, j) => {
        const g = lin(lo[j], hi[j], 40), m = [], u = [], l2 = [];
        g.forEach((v) => { const q = xn.slice(); q[j] = (v - lo[j]) / (hi[j] - lo[j]); const [mm, ss] = gpPredict(gp, q); m.push(Math.exp(mm)); u.push(Math.exp(mm + 1.96 * ss)); l2.push(Math.exp(mm - 1.96 * ss)); });
        const ax = j === 0 ? "" : String(j + 1);
        traces.push({ type: "scatter", mode: "lines", x: g, y: u, line: { width: 0 }, xaxis: "x" + ax, yaxis: "y" + ax, hoverinfo: "skip" });
        traces.push({ type: "scatter", mode: "lines", x: g, y: l2, fill: "tonexty", fillcolor: hexA(t.cat[0], t.dark ? 0.18 : 0.14), line: { width: 0 }, xaxis: "x" + ax, yaxis: "y" + ax, hoverinfo: "skip" });
        traces.push({ type: "scatter", mode: "lines", x: g, y: m, line: { color: t.cat[0], width: 2 }, xaxis: "x" + ax, yaxis: "y" + ax,
          customdata: g.map((_, i) => [l2[i], u[i]]), hovertemplate: `${lab} = %{x:.1f}<br>perda %{y:.3f} (%{customdata[0]:.3f}–%{customdata[1]:.3f})<extra></extra>` });
        traces.push({ type: "scatter", mode: "markers", x: [x[j]], y: [Math.exp(mu)], marker: { size: 8, color: t.ruby, line: { width: 2, color: t.surface } }, xaxis: "x" + ax, yaxis: "y" + ax, hoverinfo: "skip" });
        lay["xaxis" + ax] = { title: { text: lab, font: { size: 11, color: t.ink2 } }, gridcolor: t.line, linecolor: t.lineStrong, tickfont: { color: t.muted, size: 10 } };
        lay["yaxis" + ax] = { gridcolor: t.line, linecolor: t.lineStrong, tickfont: { color: t.muted, size: 10 }, title: j === 0 ? { text: "perda prevista", font: { color: t.ink2 } } : undefined };
        ytop = Math.max(ytop, ...u);
      });
      D.labels.forEach((_, j) => { lay["yaxis" + (j === 0 ? "" : String(j + 1))].range = [0, Math.min(ytop * 1.04, 2)]; });   // mesma escala nos 5
      plot("ds-pd", traces, lay);
    }
    const drawF = perFrame(draw);
    D.labels.forEach((_, j) => $("#ds-v" + j).addEventListener("input", drawF));
    ["#ds-x", "#ds-y"].forEach((s) => $(s).addEventListener("change", draw));
    segmented("#ds-mode", (v) => { mode = v; draw(); });
    const load = (xv) => { xv.forEach((v, j) => { $("#ds-v" + j).value = v; }); draw(); };
    $("#ds-reset").addEventListener("click", () => load(D.best_measured.x));
    drawer(draw);
    drawer(() => {
      const t = T(), cv = D.cv, mn = Math.min(...cv.obs, ...cv.pred) - 0.1, mx = Math.max(...cv.obs, ...cv.pred) + 0.1;
      plot("ds-cv", [{ type: "scatter", mode: "markers", x: cv.pred, y: cv.obs, error_x: { type: "data", array: cv.sd.map((s) => 1.96 * s), color: t.lineStrong, thickness: 1, width: 0 },
        marker: { size: 7, color: t.cat[0], line: { width: 1.5, color: t.surface } }, hovertemplate: "previsto %{x:.2f} · medido %{y:.2f}<extra></extra>" },
      { type: "scatter", mode: "lines", x: [mn, mx], y: [mn, mx], line: { color: t.muted, width: 1 }, hoverinfo: "skip" }],
      { showlegend: false, xaxis: { title: { text: "ln(perda) prevista" } }, yaxis: { title: { text: "ln(perda) medida" } },
        annotations: [{ x: 0.02, y: 0.98, xref: "paper", yref: "paper", xanchor: "left", text: `R² = ${nf(cv.r2, 2)} · IC 95 % cobre ${nf(100 * cv.coverage95, 0)} %`, showarrow: false, font: { color: t.ink, size: 12 } }] });
    });
    const MC = D.model_comparison, bestM = MC.reduce((b, x) => (x.nlpd < b.nlpd ? x : b), MC[0]);
    $("#ds-models").innerHTML = "<thead><tr><th>Modelo</th><th class='num'>R²</th><th class='num'>RMSE (ln)</th><th class='num'>cobertura IC 95 %</th><th class='num'>NLPD</th></tr></thead><tbody>" +
      MC.map((x) => `<tr><td>${esc(x.model)}${x === bestM ? " <span class='chip exp'>melhor NLPD</span>" : ""}</td><td class="num">${nf(x.r2, 3)}</td><td class="num">${nf(x.rmse, 3)}</td><td class="num">${nf(100 * x.coverage95, 0)} %</td><td class="num">${nf(x.nlpd, 3)}</td></tr>`).join("") + "</tbody>";
    const het = MC[MC.length - 1], prop = MC[0];
    $("#ds-models-txt").innerHTML = `<p>Os quatro núcleos empatam (NLPD entre ${nf(Math.min(...MC.slice(0, 4).map((x) => x.nlpd)), 3)} e ${nf(Math.max(...MC.slice(0, 4).map((x) => x.nlpd)), 3)}; diferença menor que 0,05 nat), então o painel mantém o Matérn-5/2 pré-registrado na proposta: a conclusão não depende dessa escolha.</p>` +
      `<p>Usar o ruído medido das réplicas piora muito (R² ${nf(het.r2, 2)}, NLPD ${nf(het.nlpd, 2)}): o erro-padrão da média das réplicas (mediana ${nf(prop.replicate_se_median, 3)} em ln) é cerca de ${ni(prop.rmse / prop.replicate_se_median)}× menor que o erro do modelo. ` +
      "A variação que sobra não é ruído de pipetagem: é algo que as cinco vazões não descrevem (dia, lote, temperatura do chip). É exatamente a variabilidade não medida que o projeto quer capturar com o contexto do lote.</p>";
    $("#ds-sugg").innerHTML = "<thead><tr><th>#</th>" + D.labels.map((l) => `<th class="num">${esc(l)}</th>`).join("") +
      "<th class='num'>Perda prevista</th><th class='num'>IC 95 %</th><th class='num'>EI</th><th><span class='sr'>Ação</span></th></tr></thead><tbody>" +
      D.suggestions.map((s, i) => `<tr><td>${i + 1}</td>${s.x.map((v, j) => `<td class="num">${nf(v, dec(j))}</td>`).join("")}` +
        `<td class="num">${nf(s.pred_loss, 3)}</td><td class="num">${nf(s.lo, 3)}–${nf(s.hi, 3)}</td><td class="num">${nf(s.ei, 4)}</td>` +
        `<td><button class="btn" type="button" data-s="${i}">Carregar</button></td></tr>`).join("") + "</tbody>";
    $("#ds-sugg").addEventListener("click", (e) => { const b = e.target.closest("button[data-s]"); if (!b) return;
      load(D.suggestions[+b.dataset.s].x); $("#ds-surf").scrollIntoView({ block: "center", behavior: "smooth" }); });
  };

  /* ================================================================== aprendizado ativo */
  INIT.aprendizado = function () {
    const B = A.benchmark, names = Object.keys(B.datasets), others = B.arms.filter((a) => a !== "Aleatório");
    $("#bo-ds").innerHTML = names.map((n) => `<option>${esc(n)}</option>`).join("");
    $("#bo-arm").innerHTML = others.map((a) => `<option>${esc(a)}</option>`).join("");
    const draw = () => {
      const t = T(), ds = B.datasets[$("#bo-ds").value], arm = $("#bo-arm").value, x = ds.curves[B.arms[0]].median.map((_, i) => i + 1);
      const R = ds.reach_top5, mc = ds.median_censored, pr = ds.paired[arm];
      const verdict = pr.p < 0.05 ? (pr.wins > pr.losses ? "melhor que o acaso" : "pior que o acaso") : "empate estatístico";
      kpis("#bo-kpis", [
        { k: "Condições distintas medidas", v: ni(ds.n_pool), s: `${ds.features.length} variáveis · ${esc(ds.reference)}` },
        { k: "Objetivo", v: ds.minimize ? "minimizar" : "maximizar", s: esc(ds.objective) },
        { k: `${esc(arm)} até o top 5 %`, v: nf(mc[arm], mc[arm] % 1 ? 1 : 0), u: "experimentos", s: `${nf(100 * R[arm].fraction, 0)} % das campanhas chegaram (mediana)`, key: true },
        { k: "Aleatório até o top 5 %", v: nf(mc["Aleatório"], mc["Aleatório"] % 1 ? 1 : 0), u: "experimentos", s: `${nf(100 * R["Aleatório"].fraction, 0)} % chegaram` },
        { k: `${esc(arm)} × aleatório (pareado)`, v: verdict, s: `${pr.wins} vitórias, ${pr.ties} empates, ${pr.losses} derrotas · Wilcoxon ${pf(pr.p)}` },
      ]);
      const tr = [];
      B.arms.forEach((a, k) => {
        const c = ds.curves[a], col = t.cat[k];
        tr.push({ type: "scatter", mode: "lines", x, y: c.q75, line: { width: 0 }, hoverinfo: "skip", showlegend: false, legendgroup: a });
        tr.push({ type: "scatter", mode: "lines", x, y: c.q25, fill: "tonexty", fillcolor: hexA(col, t.dark ? 0.16 : 0.12), line: { width: 0 }, hoverinfo: "skip", showlegend: false, legendgroup: a });
        tr.push({ type: "scatter", mode: "lines", name: a, x, y: c.median, line: { color: col, width: a === arm || a === "Aleatório" ? 2.6 : 1.4 }, legendgroup: a,
          hovertemplate: `${a}: %{y:.2f}<extra></extra>` });
      });
      const ylo = Math.min(...B.arms.map((a) => Math.min(...ds.curves[a].q25)));
      plot("bo-curves", tr, { xaxis: { title: { text: "experimentos" } }, yaxis: { title: { text: "melhor resultado (normalizado)" }, range: [Math.max(0, ylo - 0.03), 1.01] }, hovermode: "x unified" });
      plot("bo-reach", B.arms.map((a, k) => ({ type: "box", name: a, y: R[a].per_seed.map((h) => (h == null ? ds.budget + 3 : h)),
        boxpoints: "all", jitter: 0.45, pointpos: 0, fillcolor: "rgba(0,0,0,0)", line: { color: t.cat[k], width: 1.5 },
        marker: { color: t.cat[k], size: 6, opacity: 0.8 }, hovertemplate: `${a}: %{y} experimentos<extra></extra>` })),
      { showlegend: false, yaxis: { title: { text: "experimentos até o top 5 %" }, rangemode: "tozero" },
        shapes: [{ type: "line", xref: "paper", x0: 0, x1: 1, y0: ds.budget + 1.5, y1: ds.budget + 1.5, line: { color: t.lineStrong, width: 1 } }],
        annotations: [{ xref: "paper", x: 1, y: ds.budget + 3, text: "não chegou", showarrow: false, xanchor: "right", font: { size: 10, color: t.muted } }] });
      const cap = ds.budget + 1, hr = R["Aleatório"].per_seed.map((h) => (h == null ? cap : h));
      const dd = R[arm].per_seed.map((h, i) => (h == null ? cap : h) - hr[i]);
      const col = dd.map((v) => (v < 0 ? t.cat[2] : v > 0 ? t.cat[1] : t.other));
      plot("bo-pair", [{ type: "bar", x: dd.map((_, i) => "rep. " + (i + 1)), y: dd, marker: { color: col },
        hovertemplate: `%{x}: ${esc(arm)} − aleatório = %{y} experimentos<extra></extra>` }],
      { xaxis: { title: { text: "repetição (mesma partida de 5 condições)" }, tickangle: -45, tickfont: { size: 9 } },
        yaxis: { title: { text: "diferença de experimentos" }, zeroline: true, zerolinecolor: t.ink }, margin: { t: 34 },
        annotations: [{ xref: "paper", yref: "paper", x: 0, y: 1.02, xanchor: "left", yanchor: "bottom", showarrow: false, font: { color: t.ink2, size: 11 },
          text: `verde: ${esc(arm)} chegou antes · laranja: o aleatório chegou antes · ${pf(pr.p)}` }] });
    };
    const wonBy = names.filter((n) => { const pr = B.datasets[n].paired["GP-EI"]; return pr.p < 0.05 && pr.wins > pr.losses; });
    $("#bo-insight").innerHTML = `<b>Leitura.</b> O GP-EI chega antes do acaso com significância em ${wonBy.join(", ")} e empata nas demais. ` +
      `O ganho cresce com o espaço de busca: com cerca de 100 condições (${names.filter((n) => B.datasets[n].n_pool <= 110).join(", ")}), o top 5 % tem só 5 condições e a partida aleatória já cobre boa parte dele. ` +
      "É o mesmo quadro de Liang et al. (npj Comput. Mater. 2021), de onde vêm essas bases: GP com ARD e floresta aleatória superam o acaso, com vantagem maior nos espaços grandes.";
    $("#bo-ds").addEventListener("change", draw); $("#bo-arm").addEventListener("change", draw);
    drawer(draw);
    $("#bo-tbl").innerHTML = "<thead><tr><th>Campanha</th><th class='num'>Condições</th>" + B.arms.map((a) => `<th class="num">${a}</th>`).join("") + "</tr></thead><tbody>" +
      names.map((n) => { const ds = B.datasets[n]; return `<tr><td>${esc(n)} <span class="muted">(${esc(ds.objective)})</span></td><td class="num">${ds.n_pool}</td>` +
        B.arms.map((a) => { const m = ds.median_censored[a]; if (a === "Aleatório") return `<td class="num">${nf(m, m % 1 ? 1 : 0)}</td>`;
          const pr = ds.paired[a], sig = pr.p < 0.05;
          return `<td class="num">${sig ? "<b>" : ""}${nf(m, m % 1 ? 1 : 0)}${sig ? "</b>" : ""} <span class="muted">(${pr.wins}–${pr.ties}–${pr.losses}; ${pf(pr.p)})</span></td>`; }).join("") + "</tr>"; }).join("") + "</tbody>";
  };

  /* ================================================================== interpretabilidade */
  INIT.interpretabilidade = function () {
    const S = A.interpret;
    function fillFeatures() {
      const m = S[$("#sh-m").value], imp = m.features.map((_, j) => m.values.reduce((a, r) => a + Math.abs(r[j] || 0), 0));
      $("#sh-f").innerHTML = imp.map((v, j) => [v, j]).sort((a, b) => b[0] - a[0]).map(([, j]) => `<option value="${j}">${esc(m.features[j])}</option>`).join("");
    }
    const draw = () => {
      const t = T(), key = $("#sh-m").value, m = S[key], V = m.values, X = m.X;
      const imp = m.features.map((_, j) => V.reduce((a, r) => a + Math.abs(r[j] || 0), 0) / V.length);
      const ord = imp.map((v, j) => [v, j]).sort((a, b) => a[0] - b[0]).map((x) => x[1]);   // menor → maior (de baixo p/ cima)
      const top = ord[ord.length - 1];
      const extra = m.cv_r2 != null ? `R² (validação) ${nf(m.cv_r2, 2)}` : m.cv_r2_by_paper != null ? `R² por artigo ${nf(m.cv_r2_by_paper, 2)} (IC 95 % ${nf(m.boot["28 variáveis"].ci95[0], 2)}–${nf(m.boot["28 variáveis"].ci95[1], 2)}; +${nf(m.boot.diff.value, 2)} sobre o modelo de 9 variáveis)` : `R² do GP em CV ${nf(A.designer.cv.r2, 2)}`;
      kpis("#sh-kpis", [{ k: "Modelo e alvo", v: key === "agnp" ? "GP · SHAP exato" : "árvores · TreeSHAP", s: `${esc(m.target)} · ${extra}` },
        { k: "Sínteses explicadas", v: ni(V.length), s: m.n ? `amostra de ${ni(m.n)} registros de ${ni(m.n_articles)} artigos; as ${ni(m.features.length)} mais influentes de ${ni(m.n_features)} variáveis` : "todas as condições medidas" },
        { k: "Variável mais influente", v: esc(m.features[top]), s: `|SHAP| médio ${nf(imp[top], 3)}`, key: true }]);
      const xs = [], ys = [], cs = [], cd = [];
      ord.forEach((j, row) => {
        const fin = finite(X.map((r) => r[j])), mn = Math.min(...fin), mx = Math.max(...fin);
        V.forEach((r, i) => { if (r[j] == null) return; xs.push(r[j]); ys.push(row + hashJitter(i, j) * 0.55);
          cs.push(X[i][j] == null ? 0.5 : (mx > mn ? (X[i][j] - mn) / (mx - mn) : 0.5)); cd.push([m.features[j], X[i][j] == null ? "—" : X[i][j]]); });
      });
      plot("sh-bees", [{ type: "scattergl", mode: "markers", x: xs, y: ys, customdata: cd,
        marker: { size: 5, color: cs, colorscale: t.seqScale, cmin: 0, cmax: 1, opacity: 0.85,
          colorbar: { title: { text: "valor", side: "right", font: { color: t.ink2 } }, tickvals: [0, 1], ticktext: ["baixo", "alto"], thickness: 10, len: 0.5, tickfont: { color: t.muted } } },
        hovertemplate: "%{customdata[0]} = %{customdata[1]}<br>SHAP %{x:.3f}<extra></extra>" }],
      { yaxis: { tickvals: ord.map((_, i) => i), ticktext: ord.map((j) => m.features[j]), zeroline: false }, margin: { l: 150 },
        xaxis: { title: { text: "contribuição para " + m.target }, zeroline: true, zerolinecolor: t.lineStrong } });
      plot("sh-bar", [{ type: "bar", orientation: "h", y: ord.map((j) => m.features[j]), x: ord.map((j) => imp[j]), marker: { color: t.cat[0] },
        hovertemplate: "%{y}: %{x:.3f}<extra></extra>" }], { margin: { l: 150 }, xaxis: { title: { text: "|SHAP| médio" } } });
      // dependência colorida pela parceira de interação (H² no AgNP; senão a segunda mais importante)
      const f = +$("#sh-f").value;
      let partner;
      if (key === "agnp") { const h = S.agnp.H2[f].map((v, j) => (j === f ? -1 : v)); partner = h.indexOf(Math.max(...h)); }
      else partner = ord.slice().reverse().find((j) => j !== f);
      const pc = X.map((r) => r[partner]), pf2 = finite(pc), pmn = Math.min(...pf2), pmx = Math.max(...pf2);
      $("#sh-dep-cap").textContent = `Valor de ${m.features[f]} × contribuição dele; cor = ${m.features[partner]}${key === "agnp" ? " (maior H² com ela)" : ""}.`;
      plot("sh-dep", [{ type: "scattergl", mode: "markers", x: X.map((r) => r[f]), y: V.map((r) => r[f]), customdata: pc.map((v) => (v == null ? "—" : v)),
        marker: { size: 6, color: pc.map((v) => (v == null ? (pmn + pmx) / 2 : v)), colorscale: t.seqScale, cmin: pmn, cmax: pmx, opacity: 0.8, line: { width: 0.5, color: t.surface },
          colorbar: { title: { text: m.features[partner], side: "right", font: { color: t.ink2, size: 11 } }, thickness: 10, len: 0.7, tickfont: { color: t.muted } } },
        hovertemplate: `${m.features[f]} = %{x}<br>SHAP %{y:.3f}<br>${m.features[partner]} = %{customdata}<extra></extra>` }],
      { xaxis: { title: { text: m.features[f] } }, yaxis: { title: { text: "SHAP" }, zeroline: true, zerolinecolor: t.lineStrong } });
      const fl = S.agnp.features, H = S.agnp.H2.map((row, i) => row.map((v, j) => (i === j ? null : v)));
      plot("sh-h2", [{ type: "heatmap", z: H, x: fl, y: fl, colorscale: t.seqScale, zmin: 0, xgap: 2, ygap: 2,
        text: H.map((r) => r.map((v) => (v == null ? "" : nf(v, 2)))), texttemplate: "%{text}", textfont: { size: 10 },
        colorbar: { title: { text: "H²", font: { color: t.ink2 } }, thickness: 10, tickfont: { color: t.muted } },
        hovertemplate: "%{x} × %{y}: H² = %{z:.3f}<extra></extra>" }], { margin: { l: 120, b: 90 }, yaxis: { autorange: "reversed" } });
    };
    fillFeatures();
    $("#sh-m").addEventListener("change", () => { fillFeatures(); draw(); }); $("#sh-f").addEventListener("change", draw);
    drawer(draw);
  };

  /* ================================================================== variabilidade */
  INIT.variabilidade = function () {
    const Va = A.variability, ag = Va.agnp, tk = Va.turkevich, ge = Va.aunc_generalization;
    kpis("#va-kpis", [
      { k: "CV mediano das réplicas (AgNP)", v: nf(100 * ag.median_cv, 1), u: "%", s: `${ni(ag.n_measurements)} medidas, ${ni(ag.mean.length)} condições` },
      { k: "Fração da variância entre condições", v: nf(ag.icc, 2), s: "ICC: o resto é ruído de réplica" },
      { k: "Ruído heteroscedástico?", v: ag.levene_p < 0.05 ? "sim" : "não", s: `Brown–Forsythe W = ${nf(ag.levene_W, 1)}, ${pf(ag.levene_p)}: justifica o GP com ruído por condição`, key: true },
      { k: `Turkevich em ${ni(tk.n_papers)} artigos`, v: nf(tk.median, 1), u: "nm", s: `10–90 %: ${nf(tk.q10_q90[0], 1)}–${nf(tk.q10_q90[1], 1)} nm · fator ×${nf(tk.fold_1sd, 2)}` },
      { k: "AuNC: R² para artigo novo", v: nf(ge.r2_new_paper, 2), s: `IC 95 % ${nf(ge.boot_new_paper.stokes.ci95[0], 2)} a ${nf(ge.boot_new_paper.stokes.ci95[1], 2)} · síntese nova: ${nf(ge.r2_random, 2)} · ${ni(ge.n_papers)} artigos` },
    ]);
    drawer(() => {
      const t = T();
      plot("va-noise", [{ type: "scatter", mode: "markers", x: ag.mean, y: ag.sd, customdata: ag.n,
        marker: { size: ag.n.map((n) => 4 + Math.sqrt(n) * 1.4), color: t.cat[0], opacity: 0.75, line: { width: 1.5, color: t.surface } },
        hovertemplate: "média %{x:.3f} · dp %{y:.3f}<br>%{customdata} réplicas<extra></extra>" }],
      { xaxis: { title: { text: "perda média da condição" } }, yaxis: { title: { text: "dp entre réplicas" }, rangemode: "tozero" } });
      const D = A.designer, P = D.points, cv = ag.sd.map((s, i) => s / ag.mean[i]);
      plot("va-3d", [{ type: "scatter3d", mode: "markers", x: P.X.map((r) => r[0]), y: P.X.map((r) => r[3]), z: P.X.map((r) => r[2]),
        marker: { size: 5, color: cv, colorscale: t.seqScale, opacity: 0.95, colorbar: { title: { text: "CV", font: { color: t.ink2 } }, thickness: 10, len: 0.6, tickformat: ".0%", tickfont: { color: t.muted } } },
        customdata: cv, hovertemplate: `${D.labels[0]} = %{x:.1f}<br>${D.labels[3]} = %{y:.1f}<br>${D.labels[2]} = %{z:.1f}<br>CV = %{customdata:.1%}<extra></extra>` }],
      { margin: { l: 0, r: 0, t: 0, b: 0 }, uirevision: "va", scene: scene(D.labels[0], D.labels[3], D.labels[2]) });
      const lv = tk.sizes_per_paper.map(Math.log10), edges = lin(0.3, 2.2, 40), cnt = new Array(39).fill(0);
      lv.forEach((v) => { const j = Math.floor((v - edges[0]) / (edges[1] - edges[0])); if (j >= 0 && j < 39) cnt[j]++; });
      const mid = edges.slice(0, -1).map((e) => e + (edges[1] - edges[0]) / 2);
      const vline = (v, w, dash) => ({ type: "line", x0: Math.log10(v), x1: Math.log10(v), y0: 0, y1: 1, yref: "paper", line: { color: t.ink, width: w, dash } });
      plot("va-turk", [{ type: "bar", x: mid, y: cnt, width: (edges[1] - edges[0]) * 0.92, marker: { color: t.cat[0] }, customdata: mid.map((m) => Math.pow(10, m)),
        hovertemplate: "≈ %{customdata:.1f} nm: %{y} artigos<extra></extra>" }],
      { bargap: 0, xaxis: { title: { text: "tamanho relatado (nm)" }, tickvals: [0.477, 0.699, 1, 1.301, 1.699, 2], ticktext: ["3", "5", "10", "20", "50", "100"] },
        yaxis: { title: { text: "artigos" } }, shapes: [vline(tk.median, 1.6, "solid"), vline(tk.q10_q90[0], 1, "dot"), vline(tk.q10_q90[1], 1, "dot")],
        annotations: [{ x: Math.log10(tk.median), y: 1, yref: "paper", text: `mediana ${nf(tk.median, 1)} nm`, showarrow: false, xanchor: "left", xshift: 5, font: { color: t.ink, size: 11 } },
          { x: Math.log10(tk.q10_q90[1]), y: 0.85, yref: "paper", text: "90 %", showarrow: false, xanchor: "left", xshift: 4, font: { color: t.muted, size: 10 } },
          { x: Math.log10(tk.q10_q90[0]), y: 0.85, yref: "paper", text: "10 %", showarrow: false, xanchor: "right", xshift: -4, font: { color: t.muted, size: 10 } }] });
      const bn = ge.boot_new_paper, br = ge.boot_random, sg = (d) => (d.ci95[0] > 0 ? "significativo" : "dentro do ruído: o IC inclui zero");
      $("#va-gen-txt").innerHTML = `<p>Alvo = deslocamento de Stokes, comparado com prever a emissão direto nas mesmas ${ni(ge.obs.length)} sínteses. ` +
        `Ganho no R²: síntese nova +${nf(br.diff.value, 2)} (IC 95 % ${nf(br.diff.ci95[0], 2)} a ${nf(br.diff.ci95[1], 2)}), artigo novo +${nf(bn.diff.value, 2)} ` +
        `(IC 95 % ${nf(bn.diff.ci95[0], 2)} a ${nf(bn.diff.ci95[1], 2)}): ${sg(bn.diff)}. Intervalos por bootstrap de artigos.</p>`;
      const mn = Math.min(...ge.obs), mx = Math.max(...ge.obs);
      plot("va-gen", [
        { type: "scatter", mode: "markers", name: `síntese nova (R² ${nf(ge.r2_random, 2)})`, x: ge.obs, y: ge.pred_random, marker: { size: 7, color: t.cat[0], opacity: 0.8, line: { width: 1, color: t.surface } }, hovertemplate: "medido %{x} · previsto %{y:.0f} nm<extra>síntese nova</extra>" },
        { type: "scatter", mode: "markers", name: `artigo novo (R² ${nf(ge.r2_new_paper, 2)})`, x: ge.obs, y: ge.pred_new_paper, marker: { size: 7, color: t.cat[1], opacity: 0.8, symbol: "diamond", line: { width: 1, color: t.surface } }, hovertemplate: "medido %{x} · previsto %{y:.0f} nm<extra>artigo novo</extra>" },
        { type: "scatter", mode: "lines", x: [mn, mx], y: [mn, mx], line: { color: t.muted, width: 1 }, hoverinfo: "skip", showlegend: false }],
      { xaxis: { title: { text: "λ de emissão medido (nm)" } }, yaxis: { title: { text: "λ de emissão previsto (nm)" } } });
    });
  };

  /* ================================================================== causal */
  INIT.causal = function () {
    const C = A.causal, E = C.effects, D = A.designer;
    const fmtE = (e) => e.binary ? `RR ${nf(e.estimate, 2)}` : `×${nf(e.estimate, 2)}`;
    const ciE = (e) => `${nf(e.estimate_ci95[0], 2)}–${nf(e.estimate_ci95[1], 2)}`;
    const ok = E.filter((e) => e.verdict.startsWith("confirma")).length, rob = E.filter((e) => e.robust).length;
    kpis("#ca-kpis", [
      { k: "Efeitos estimados", v: ni(E.length), s: "tamanho e forma, nos registros da literatura" },
      { k: "Concordam com a literatura", v: `${ok} de ${E.length}`, s: `direção prevista e IC 95 % sem o nulo; ${rob} robustos a todos os estimadores`, key: true },
      { k: "NaBH₄ × citrato (rota direta)", v: fmtE(E[0]), s: `IC 95 % ${ciE(E[0])} · E-value ${nf(E[0].e_value, 1)}` },
      { k: "Com sementes × direta", v: fmtE(E[1]), s: `IC 95 % ${ciE(E[1])} · E-value ${nf(E[1].e_value, 1)}` },
      { k: "CTAB → forma não esférica", v: fmtE(E[2]), s: `${nf(100 * E[2].p0, 0)} % → ${nf(100 * E[2].p1, 0)} % · E-value ${nf(E[2].e_value, 1)}` },
    ]);
    const byKey = Object.fromEntries(E.map((e) => [e.key, e]));
    const estOn = { "redutor>nucleacao": "redutor", "sementes>tamanho": "sementes", "ligante>forma": "ctab", "ligante>tamanho": "tiol" };
    const pathOn = new Set(["nucleacao>tamanho"]);
    drawer(() => {
      const t = T();
      const pos = { base: [90, 195], temperatura: [340, 46], redutor: [340, 142], sementes: [340, 248], ligante: [340, 344],
        nucleacao: [610, 76], tamanho: [800, 176], forma: [800, 316], lspr: [950, 246] };
      const W = 1030, H = 380, HW = 74, HH = 19;
      const clip = (dx, dy, pad) => { const k = Math.min(dx ? (HW + pad) / Math.abs(dx) : Infinity, dy ? (HH + pad) / Math.abs(dy) : Infinity); return [dx * k, dy * k]; };
      const edges = C.dag.edges.map(([a, b, lab]) => {
        const [x1, y1] = pos[a], [x2, y2] = pos[b], dx = x2 - x1, dy = y2 - y1, [ox, oy] = clip(dx, dy, 2), [ix, iy] = clip(dx, dy, 6);
        const k = a + ">" + b, eff = estOn[k] && byKey[estOn[k]], main = !!eff || pathOn.has(k);
        const txt = [lab, eff ? fmtE(eff) : ""].filter(Boolean).join(" · ");
        const sx = x1 + ox, sy = y1 + oy, ex = x2 - ix, ey = y2 - iy, L2 = Math.hypot(ex - sx, ey - sy) || 1;
        const nx = (ey - sy) / L2, ny = -(ex - sx) / L2, side = ny > 0 ? -1 : 1;     // rótulo do lado de cima da seta
        const f = 0.42, mx = sx + (ex - sx) * f + side * nx * 10, my = sy + (ey - sy) * f + side * ny * 10 + 4;
        return `<path class="edge${main ? " main" : ""}" d="M${x1 + ox},${y1 + oy} L${x2 - ix},${y2 - iy}" marker-end="url(#ah${main ? "m" : ""})"/>` +
          (txt ? `<text class="elab${eff ? " eff" : ""}" x="${mx}" y="${my}" text-anchor="middle">${esc(txt)}</text>` : "");
      }).join("");
      const nodes = C.dag.nodes.map(([id, lab]) => { const [x, y] = pos[id];
        const cls = id === "nucleacao" ? " latent" : ["tamanho", "forma", "lspr"].includes(id) ? " y" : ["redutor", "sementes", "ligante"].includes(id) ? " t" : "";
        return `<g class="node${cls}"><rect x="${x - HW}" y="${y - HH}" width="${2 * HW}" height="${2 * HH}" rx="10"/><text x="${x}" y="${y + 4}" text-anchor="middle">${esc(lab)}</text></g>`; }).join("");
      $("#ca-dag").innerHTML = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Grafo causal: base e época influenciam temperatura, redutor, sementes e ligante; temperatura e redutor controlam a nucleação, que define o número de núcleos e o tamanho; sementes e ligante agem no crescimento e na forma; tamanho e forma determinam o LSPR.">
        <defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="${t.muted}"/></marker>
        <marker id="ahm" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="${t.ruby}"/></marker></defs>
        ${edges}${nodes}</svg>`;
      // forest
      const rows = E.map((e) => e.name), lo = E.map((e) => e.estimate - e.estimate_ci95[0]), hi = E.map((e) => e.estimate_ci95[1] - e.estimate);
      plot("ca-forest", [{ type: "scatter", mode: "markers", x: E.map((e) => e.estimate), y: rows,
        error_x: { type: "data", symmetric: false, array: hi, arrayminus: lo, color: t.ink2, thickness: 1.6, width: 6 },
        marker: { size: 12, color: E.map((e) => (e.robust ? t.ruby : t.surface)), line: { width: 2, color: t.ruby } },
        customdata: E.map((e) => [e.outcome, e.verdict, e.n, e.n_articles]),
        hovertemplate: "%{y}<br>%{x:.2f} (%{customdata[0]})<br>%{customdata[1]}<br>%{customdata[2]} registros, %{customdata[3]} artigos<extra></extra>" }],
      { xaxis: { type: "log", title: { text: "efeito (razão; 1 = nenhum efeito)" }, tickvals: [0.1, 0.2, 0.5, 1, 2, 5], range: [Math.log10(0.08), Math.log10(6)] },
        yaxis: { autorange: "reversed", automargin: true }, margin: { l: 220, t: 34 }, showlegend: false,
        shapes: [{ type: "line", x0: 1, x1: 1, y0: -0.5, y1: E.length - 0.5, line: { color: t.ink, width: 1, dash: "dot" } }].concat(
          E.map((e, i) => ({ type: "rect", x0: e.expected.range[0], x1: e.expected.range[1], y0: i - 0.32, y1: i + 0.32, fillcolor: hexA(t.dark ? "#e0b45c" : "#b8862a", 0.22), line: { width: 0 }, layer: "below" }))),
        annotations: [{ xref: "paper", yref: "paper", x: 0, y: 1.06, xanchor: "left", showarrow: false, font: { size: 11, color: t.ink2 }, text: "cheio = robusto a todos os estimadores · vazado = magnitude frágil" }] });
      // cadeia redutor → tamanho → LSPR
      const K = C.chain;
      plot("ca-chain", [{ type: "scatter", mode: "markers", y: ["observado (AIPW)", "previsto por Mie"], x: [K.peak_shift, K.mie_shift],
        error_x: { type: "data", symmetric: false, array: [K.peak_shift_ci95[1] - K.peak_shift, K.mie_shift_ci95[1] - K.mie_shift],
          arrayminus: [K.peak_shift - K.peak_shift_ci95[0], K.mie_shift - K.mie_shift_ci95[0]], color: t.ink2, thickness: 1.6, width: 6 },
        marker: { size: 12, color: [t.ruby, t.cat[0]], line: { width: 2, color: t.surface } },
        hovertemplate: "%{y}: %{x:.1f} nm<extra></extra>" }],
      { xaxis: { title: { text: "efeito no pico LSPR (nm; < 0 = para o azul)" }, zeroline: false }, yaxis: { autorange: "reversed", automargin: true },
        margin: { l: 130 }, showlegend: false,
        shapes: [{ type: "line", x0: 0, x1: 0, y0: -0.5, y1: 1.5, line: { color: t.ink, width: 1, dash: "dot" } }] });
      const mc = K.mie_curve, d0 = K.median_size_citrate, d1 = d0 * K.size_ratio, lamAt = (x) => interp(Math.log(x), mc.d.map(Math.log), mc.lambda);
      plot("ca-mie", [{ type: "scatter", mode: "lines", name: "Mie (σ = 10 %)", x: mc.d, y: mc.lambda, line: { color: t.cat[0], width: 2 }, hovertemplate: "%{x:.1f} nm → %{y:.1f} nm<extra>Mie</extra>" },
        { type: "scatter", mode: "markers+text", name: "tamanhos", x: [d1, d0], y: [lamAt(d1), lamAt(d0)], text: ["NaBH₄", "citrato"], textposition: ["top center", "top center"],
          textfont: { color: t.ink2, size: 11 }, marker: { size: 10, color: [t.ruby, t.ink2], line: { width: 2, color: t.surface } }, hovertemplate: "%{text}: %{x:.1f} nm → λ %{y:.1f} nm<extra></extra>" }],
      { xaxis: { type: "log", title: { text: "diâmetro (nm)" }, tickvals: [2, 5, 10, 20, 50, 100] }, yaxis: { title: { text: "λ LSPR (nm)" } }, showlegend: false,
        shapes: [{ type: "rect", xref: "x", yref: "paper", x0: 2, x1: 25, y0: 0, y1: 1, fillcolor: hexA(t.dark ? "#e0b45c" : "#b8862a", 0.12), line: { width: 0 }, layer: "below" }],
        annotations: [{ x: Math.log10(7), y: 0.95, yref: "paper", text: "faixa plana (< 25 nm)", showarrow: false, font: { size: 10, color: t.muted } }] });
      // efeitos intervencionais AgNP
      const DE = D.do_effects;
      plot("ca-do", [{ type: "scatter", mode: "markers", y: DE.map((e) => e.var), x: DE.map((e) => e.ratio),
        error_x: { type: "data", symmetric: false, array: DE.map((e) => e.ratio_ci95[1] - e.ratio), arrayminus: DE.map((e) => e.ratio - e.ratio_ci95[0]), color: t.ink2, thickness: 1.6, width: 6 },
        marker: { size: 11, color: t.cat[0], line: { width: 2, color: t.surface } }, customdata: DE.map((e) => [e.step, e.frac_improve * 100]),
        hovertemplate: "%{y}: +%{customdata[0]:.1f} → perda ×%{x:.3f}<br>melhora em %{customdata[1]:.0f} % das condições<extra></extra>" }],
      { xaxis: { title: { text: "efeito na perda espectral (×; < 1 aproxima do alvo)" } }, yaxis: { autorange: "reversed" }, margin: { l: 130 }, showlegend: false,
        shapes: [{ type: "line", x0: 1, x1: 1, y0: -0.5, y1: DE.length - 0.5, line: { color: t.ink, width: 1, dash: "dot" } }] });
    });
    // o modelo preditivo (árvores + SHAP) aponta a mesma direção? (associação condicional, não efeito causal)
    const SL = A.interpret.literature, fmap = { redutor: "NaBH₄", sementes: "mediada por sementes", tiol: "tiol (GSH/dodecanotiol)" };
    function shapLine(e) {
      const f = SL.features.indexOf(fmap[e.key]); if (f < 0) return "";
      const on = [], off = []; SL.X.forEach((r, i) => { const v = SL.values[i][f]; if (v == null) return; (r[f] ? on : off).push(v); });
      if (!on.length || !off.length) return "";
      const dlt = Math.exp(on.reduce((a, b) => a + b, 0) / on.length - off.reduce((a, b) => a + b, 0) / off.length);
      const same = (dlt < 1) === (e.estimate < 1);
      return `<p class="muted">Modelo preditivo (SHAP): ×${nf(dlt, 2)}, ${same ? "mesma direção do efeito causal estimado" : "direção oposta à do efeito causal: a associação condicional engana aqui"}.</p>`;
    }
    // vereditos
    $("#ca-verdicts").innerHTML = E.map((e) => {
      const cls = e.verdict === "confirma" ? "exp" : e.verdict.startsWith("confirma") ? "par" : "lab";
      return `<div class="verdict"><div class="vh"><b>${esc(e.name)}</b><span class="chip ${cls}"><span class="dot"></span>${esc(e.verdict)}</span></div>` +
        `<div class="vn">${fmtE(e)} <span class="muted">(IC 95 % ${ciE(e)}) · ${esc(e.outcome)} · ${esc(e.population)}</span></div>` +
        `<p>${esc(e.expected.txt)}</p>${shapLine(e)}</div>`; }).join("");
    // diagnóstico por efeito
    $("#ca-sel").innerHTML = E.map((e, i) => `<option value="${i}">${esc(e.name)}</option>`).join("");
    const diag = () => {
      const t = T(), e = E[+$("#ca-sel").value];
      kpis("#ca-sel-kpis", [
        { k: "Registros (artigos)", v: ni(e.n), s: `${ni(e.n_articles)} artigos · ${ni(e.n_treated)} tratados` },
        { k: "Estimativa AIPW", v: fmtE(e), s: `IC 95 % ${ciE(e)} (bootstrap de artigos)`, key: true },
        { k: "Sem ajuste", v: e.binary ? `RD ${nf(100 * e.naive_rd, 1)} pp` : `×${nf(e.naive_ratio, 2)}`, s: e.binary ? `ajustado: ${nf(100 * e.rd, 1)} pp` : "razão bruta das médias geométricas" },
        { k: "E-value (ponto / IC)", v: `${nf(e.e_value, 2)} / ${nf(e.e_value_ci, 2)}`, s: "força de um confundidor oculto para anular o efeito / o limite do IC" },
        { k: "Robustez", v: e.robust ? "robusto" : "frágil", s: e.robust ? "estimadores concordam (±25 %) e balanço exato" : "pouca sobreposição: estimadores discordam" },
      ]);
      const est = Object.entries(e.estimators);
      plot("ca-est", [{ type: "scatter", mode: "markers", y: est.map((x) => x[0]), x: est.map((x) => x[1]),
        marker: { size: 12, color: est.map((x) => (x[0] === "AIPW" ? t.ruby : x[0] === "sem ajuste" ? t.other : t.cat[0])), line: { width: 2, color: t.surface } },
        hovertemplate: "%{y}: %{x:.3f}<extra></extra>" }],
      { xaxis: { type: "log", title: { text: e.binary ? "razão de riscos" : "razão de médias geométricas" } }, yaxis: { autorange: "reversed" }, margin: { l: 100 }, showlegend: false,
        shapes: [{ type: "rect", x0: e.estimate_ci95[0], x1: e.estimate_ci95[1], y0: 0, y1: 1, yref: "paper", fillcolor: hexA(t.cat[0], 0.1), line: { width: 0 } },
          { type: "line", x0: 1, x1: 1, y0: 0, y1: 1, yref: "paper", line: { color: t.ink, width: 1, dash: "dot" } }] });
      const covs = e.covariates;
      plot("ca-smd", [
        { type: "scatter", mode: "markers", name: "antes", y: covs, x: e.smd_before, marker: { size: 10, color: t.cat[1], line: { width: 2, color: t.surface } }, hovertemplate: "%{y}: %{x:.2f}<extra>antes</extra>" },
        { type: "scatter", mode: "markers", name: "IPW", y: covs, x: e.smd_after, marker: { size: 10, color: t.cat[0], symbol: "diamond", line: { width: 2, color: t.surface } }, hovertemplate: "%{y}: %{x:.2f}<extra>IPW</extra>" },
        { type: "scatter", mode: "markers", name: "entropia", y: covs, x: e.smd_ebal, marker: { size: 9, color: t.cat[2], symbol: "square", line: { width: 2, color: t.surface } }, hovertemplate: "%{y}: %{x:.2f}<extra>entropia</extra>" }],
      { margin: { l: 190 }, xaxis: { title: { text: "diferença média padronizada" }, zeroline: true, zerolinecolor: t.lineStrong },
        shapes: [{ type: "rect", x0: -0.1, x1: 0.1, y0: 0, y1: 1, yref: "paper", fillcolor: hexA(t.cat[0], 0.08), line: { width: 0 } }] });
      plot("ca-ps", [
        { type: "histogram", name: "controle", x: e.propensity.control, opacity: 0.65, marker: { color: t.cat[1] }, xbins: { start: 0, end: 1, size: 0.025 }, histnorm: "probability density", hovertemplate: "e = %{x}: %{y:.2f}<extra>controle</extra>" },
        { type: "histogram", name: "tratado", x: e.propensity.treated, opacity: 0.65, marker: { color: t.cat[0] }, xbins: { start: 0, end: 1, size: 0.025 }, histnorm: "probability density", hovertemplate: "e = %{x}: %{y:.2f}<extra>tratado</extra>" }],
      { barmode: "overlay", xaxis: { title: { text: "escore de propensão (probabilidade do tratamento dadas as covariáveis)" }, range: [0, 1] }, yaxis: { title: { text: "densidade" } } });
    };
    $("#ca-sel").addEventListener("change", diag);
    drawer(diag);
    // interpretação química dos efeitos intervencionais
    const sig = (e) => e.ratio_ci95[1] < 1 ? "reduz" : e.ratio_ci95[0] > 1 ? "aumenta" : "nulo";
    const why = {
      "Q AgNO₃ (%)": "mais prata disponível por semente: as sementes crescem mais (crescimento mediado por sementes), o que desloca o plásmon",
      "Q citrato (%)": "o citrato estabiliza a prata e direciona a forma (adsorve nas faces {111}, favorecendo prismas); além do ótimo, afasta o espectro do alvo",
      "Q sementes (%)": "mais sementes dividem a mesma prata entre mais partículas (menores); o efeito é não monotônico (Fig. 4.5c) e a média quase se anula",
      "Q PVA (%)": "o PVA é estabilizante estérico: segura a dispersão, mas pouco muda o espectro",
      "Q total (µL/min)": "a vazão total muda o tempo de residência; na faixa medida o efeito é pequeno",
    };
    {
      const K = C.chain, inside = K.consistent, fl = K.mie_curve.lambda.filter((_, i) => K.mie_curve.d[i] <= 25);
      const flat = `${nf(Math.min(...fl), 0)}–${nf(Math.max(...fl), 0)} nm por Mie`;
      $("#ca-chain-txt").innerHTML = `<p>Em ${ni(K.n)} registros (${ni(K.n_treated)} com NaBH₄, ${ni(K.n_articles)} artigos), o NaBH₄ reduz o tamanho ×${nf(K.size_ratio, 2)} ` +
        `(IC 95 % ${nf(K.size_ratio_ci95[0], 2)}–${nf(K.size_ratio_ci95[1], 2)}). Por Mie, isso desloca o pico em ${nf(K.mie_shift, 1)} nm; o observado é ` +
        `${nf(K.peak_shift, 1)} nm (IC 95 % ${nf(K.peak_shift_ci95[0], 1)} a ${nf(K.peak_shift_ci95[1], 1)}). <b>${inside ? "A previsão cai dentro do intervalo: a cadeia é coerente." : "A previsão cai fora do intervalo: há um caminho além do tamanho."}</b></p>` +
        `<p class="muted">Abaixo de ~25 nm o λ<sub>LSPR</sub> do ouro é quase plano (${flat}), então nem um efeito grande no tamanho aparece no pico. Por isso Haiss et al. (2007) usam a razão A<sub>LSPR</sub>/A<sub>450</sub> para partículas pequenas, e o projeto usa o espectro inteiro (perda J) e a TEM em vez do pico sozinho.</p>`;
    }
    $("#ca-do-txt").innerHTML = D.do_effects.map((e) => `<p><b>${esc(e.var)}</b> (+${nf(e.step, 1)}): perda ×${nf(e.ratio, 3)} (IC 95 % ${nf(e.ratio_ci95[0], 3)}–${nf(e.ratio_ci95[1], 3)}), ` +
      `${sig(e) === "nulo" ? "efeito médio indistinguível de zero" : sig(e) === "reduz" ? "aproxima do alvo" : "afasta do alvo"}. ${esc(why[e.var] || "")}.</p>`).join("");
  };

  /* ================================================================== caracterização */
  INIT.caracterizacao = function () {
    const X = A.xrd, g = X.geometry || {};
    kpis("#xr-kpis", [
      { k: "Energia do feixe", v: nf(g.energy_keV, 1), u: "keV", s: `λ = ${nf(g.wavelength_A, 4)} Å (a CeO₂ = 5,4116 Å)`, key: true },
      { k: "Distância amostra–detector", v: ni(g.distance_px), u: "px", s: `≈ ${ni(g.distance_mm_if_200um)} mm com pixel de 200 µm` },
      { k: "Anéis indexados", v: ni(g.n_rings), u: `de ${ni(g.n_predicted)}`, s: `resíduo RMS ${nf(g.rms_residual_px, 2)} px no raio` },
      { k: "Quadros médios", v: ni(X.n_frames), s: `${X.shape[0]} × ${X.shape[1]} px, dark subtraído` },
    ]);
    const n = X.image_log10.length, sc = X.shape[0] / n, flat = [].concat(...X.image_log10), zlo = quant(flat, 0.03), zhi = quant(flat, 0.997);
    const drawImg = () => {
      const t = T(), cx = X.center[1] / sc, cy = X.center[0] / sc;
      const rings = $("#xr-rings").checked ? X.rings.filter((m) => m.r_obs != null).map((m) => ({ type: "circle", xref: "x", yref: "y",
        x0: cx - m.r_pred / sc, x1: cx + m.r_pred / sc, y0: cy - m.r_pred / sc, y1: cy + m.r_pred / sc, line: { color: t.ruby, width: 1 }, opacity: 0.75 })) : [];
      plot("xr-img", [{ type: "heatmap", z: X.image_log10, colorscale: t.seqScale, showscale: false, zmin: zlo, zmax: zhi,
        hovertemplate: "(%{x}, %{y}): log₁₀ I = %{z:.2f}<extra></extra>" },
      { type: "scatter", mode: "markers", x: [cx], y: [cy], marker: { symbol: "cross-thin", size: 14, line: { width: 2, color: t.ruby } }, hoverinfo: "skip" }],
      { showlegend: false, shapes: rings, xaxis: { showgrid: false, title: { text: "pixel / " + sc }, range: [0, n], constrain: "domain" },
        yaxis: { showgrid: false, range: [n, 0], scaleanchor: "x", constrain: "domain" }, margin: { l: 40, r: 10 } });
    };
    $("#xr-rings").addEventListener("change", drawImg);
    drawer(drawImg);
    drawer(() => {
      const t = T();
      plot("xr-3d", [{ type: "surface", z: X.surface_log10, colorscale: t.seqScale, showscale: false, hovertemplate: "log₁₀ I = %{z:.2f}<extra></extra>" }],
        { margin: { l: 0, r: 0, t: 0, b: 0 }, uirevision: "xr", scene: scene("x (bloco)", "y (bloco)", "log₁₀ I", { camera: { eye: { x: 1.3, y: -1.6, z: 1.1 } }, aspectratio: { x: 1, y: 1, z: 0.5 }, aspectmode: "manual" }) });
      const r = X.profile.map((_, i) => i), matched = X.rings.filter((m) => m.r_obs != null);
      plot("xr-prof", [{ type: "scatter", mode: "lines", name: "perfil radial", x: r, y: X.profile, line: { color: t.cat[0], width: 1.6 }, hovertemplate: "r = %{x} px: %{y:.0f}<extra></extra>" },
        { type: "scatter", mode: "markers+text", name: "anéis indexados (fluorita)", x: matched.map((m) => m.r_obs), y: matched.map((m) => X.profile[Math.round(m.r_obs)] * 1.25),
          text: matched.map((m) => m.hkl), textposition: "top center", textfont: { color: t.ink, size: 10 },
          marker: { size: 7, symbol: "triangle-down", color: t.ruby }, customdata: matched.map((m) => [m.two_theta, m.resid_px]),
          hovertemplate: "(%{text}) r = %{x:.2f} px<br>2θ = %{customdata[0]:.3f}° · resíduo %{customdata[1]:.2f} px<extra></extra>" }],
      { xaxis: { title: { text: "raio a partir do centro (px)" }, range: [150, X.profile.length] }, yaxis: { title: { text: "intensidade média (contagens)" }, type: "log" } });
      const U = A.aunc, groups = ["GSH", "outros tióis", "outros"];
      plot("au-3d", groups.map((gname, k) => { const I = U.ligand.map((l, i) => (l === gname ? i : -1)).filter((i) => i >= 0);
        return { type: "scatter3d", mode: "markers", name: `${gname} (${I.length})`, x: I.map((i) => U.size[i]), y: I.map((i) => U.exc[i]), z: I.map((i) => U.em[i]),
          customdata: I.map((i) => U.doi[i]), marker: { size: 4.5, color: t.cat[k], opacity: 0.9, line: { width: 0 } },
          hovertemplate: "tamanho %{x} nm · exc %{y} nm · em %{z} nm<br>%{customdata}<extra>" + gname + "</extra>" }; }),
      { margin: { l: 0, r: 0, t: 30, b: 0 }, uirevision: "au", scene: scene("tamanho (nm)", "λ exc (nm)", "λ em (nm)") });
      plot("au-T", groups.map((gname, k) => { const I = U.ligand.map((l, i) => (l === gname ? i : -1)).filter((i) => i >= 0 && U.T[i] != null);
        return { type: "scatter", mode: "markers", name: gname, x: I.map((i) => U.T[i]), y: I.map((i) => U.em[i]), customdata: I.map((i) => U.doi[i]),
          marker: { size: 7, color: t.cat[k], opacity: 0.8, line: { width: 1, color: t.surface } }, hovertemplate: "%{x} °C → %{y} nm<br>%{customdata}<extra>" + gname + "</extra>" }; }),
      { xaxis: { title: { text: "temperatura de síntese (°C)" } }, yaxis: { title: { text: "λ de emissão (nm)" } } });
    });
    $("#xr-tbl").innerHTML = "<thead><tr><th>hkl</th><th class='num'>2θ (°)</th><th class='num'>r previsto</th><th class='num'>r medido</th><th class='num'>resíduo (px)</th></tr></thead><tbody>" +
      X.rings.map((m) => `<tr><td>(${m.hkl})</td><td class="num">${nf(m.two_theta, 3)}</td><td class="num">${nf(m.r_pred, 1)}</td><td class="num">${m.r_obs == null ? "não resolvido" : nf(m.r_obs, 1)}</td><td class="num">${m.resid_px == null ? "—" : nf(m.resid_px, 2)}</td></tr>`).join("") + "</tbody>";
  };

  /* ================================================================== sobre */
  INIT.sobre = function () {
    const k = A.overview.kpis, bm = A.overview.benchmark_measurements, ns = A.literature.n_by_source;
    const liang = ["P3HT/CNT", "Perovskita", "Crossed barrel", "AutoAM"].reduce((s, n) => s + (bm[n] || 0), 0);
    const src = [
      ["Sínteses de AuNP (texto minerado)", "Cruse et al., Sci. Data 9:234 (2022)", "10.6084/m9.figshare.16614262", `${ni(ns["Cruse et al. 2022"])} receitas`, "CC BY 4.0"],
      ["Rotas de nanocristais de Au", "Nanocrystal Synthesis Platform (NSP, 2026)", "—", `${ni(ns["NSP 2026"])} rotas`, "MIT"],
      ["Fluorescência de AuNC", "compilação por DOI (datasets/aunc-fluorescence)", "—", `${ni(k.aunc_entries)} entradas, ${ni(A.aunc.n_doi)} artigos`, "ver DOIs"],
      ["Campanha AgNP em microfluídica", "Mekki-Berrada et al., npj Comput. Mater. 7:55 (2021)", "10.1038/s41524-021-00520-w", `${ni(k.agnp_measurements)} medidas`, "MIT (PV-Lab)"],
      ["P3HT/CNT, perovskitas, crossed barrel, AutoAM", "Liang et al., npj Comput. Mater. 7:188 (2021)", "10.1038/s41524-021-00656-9", `${ni(liang)} medidas`, "MIT (PV-Lab)"],
      ["Constantes ópticas do Au", "Johnson & Christy, Phys. Rev. B 6:4370 (1972)", "10.1103/PhysRevB.6.4370", "n, k medidos", "CC0 (refractiveindex.info)"],
      ["Difração do padrão CeO₂", "quadros do detector GE (datasets/xrd-ceo2-calibration)", "—", `${ni(A.xrd.n_frames)} + ${ni(A.xrd.n_frames)} quadros`, "ver origem"],
    ];
    $("#ab-src").innerHTML = "<thead><tr><th>Dados</th><th>Origem</th><th>DOI</th><th>Volume</th><th>Licença</th></tr></thead><tbody>" +
      src.map((s) => `<tr><td>${esc(s[0])}</td><td>${esc(s[1])}</td><td>${s[2] !== "—" ? `<a href="https://doi.org/${esc(s[2])}" target="_blank" rel="noopener">${esc(s[2])}</a>` : "—"}</td><td>${esc(s[3])}</td><td>${esc(s[4])}</td></tr>`).join("") + "</tbody>";
    $("#ab-methods").innerHTML = [
      "<b>Medidas</b>: perdas espectrais e réplicas (AgNP e demais campanhas), emissões de AuNC, quadros de difração, n e k do ouro.",
      "<b>Relatos minerados</b>: tamanho, pico e temperatura da literatura vêm de texto extraído por NLP/LLM. Em Cruse et al., o tamanho é do artigo, não do parágrafo; erros de extração existem e os filtros físicos removem os grosseiros.",
      "<b>Modelos</b>: Mie (física, sem ajuste); GP do AuNP Designer (Matérn-5/2 + ARD, prior de comprimento, BoTorch), executado no navegador com os parâmetros ajustados; árvores de gradiente para SHAP; regressão logística para o escore de propensão.",
      "<b>Inferência</b>: a análise causal é observacional; o E-value diz o tamanho do confundimento oculto que a anularia. As campanhas de aprendizado ativo usam as medidas reais como oráculo, então as estratégias só escolhem entre condições que foram medidas.",
    ].map((p) => `<p>${p}</p>`).join("");
    $("#ab-pending").innerHTML = [
      "<b>Lotes de GO</b> (§4.2–4.3): XPS, Raman, AFM e impurezas por lote, e o GO Navigator com esses descritores.",
      "<b>Representações contextuais do Designer</b> (§4.5) e <b>transferência entre lotes</b> (§4.7): precisam de sínteses GO–AuNP em lotes diferentes.",
      "<b>MISO</b> (§4.8): UV-Vis, DLS e TEM das mesmas sínteses.",
      "<b>Campanha prospectiva</b> (§4.11) e <b>confirmação por TEM</b> (§4.12): piloto, 12 + 24 + 16 sínteses e o plano pré-registrado congelado.",
      "O código para tudo isso já está no repositório (code/, ver docs/ANALISE_REPOSITORIO.md); este painel recebe essas seções quando as medidas existirem.",
    ].map((p) => `<p>${p}</p>`).join("");
    const G = [
      ["LSPR", "ressonância de plásmon de superfície localizada: o pico de absorção das nanopartículas de ouro (~520 nm para 20 nm)."],
      ["Teoria de Mie", "solução exata do espalhamento de luz por uma esfera; com n e k medidos do ouro, prevê o espectro a partir do tamanho."],
      ["Perda J (Eq. 1)", "média de ((E − E*)/sₘ)² entre o espectro medido E e o alvo E*, ambos normalizados; J ≤ 1 significa diferença dentro do ruído sₘ."],
      ["GP (processo gaussiano)", "modelo que prevê média e incerteza; o Designer usa núcleo Matérn-5/2 com um comprimento por variável (ARD)."],
      ["EI (melhoria esperada)", "quanto se espera melhorar sobre a melhor medida ao testar uma condição; equilibra explorar e aproveitar."],
      ["UCB", "limite superior de confiança, μ + 2σ: escolhe onde o resultado pode ser alto, favorecendo a exploração."],
      ["Validação cruzada", "o modelo é reajustado sem uma parte dos dados e avaliado nela; R² e cobertura do IC 95 % medem acerto e calibração."],
      ["SHAP", "valores de Shapley: quanto cada variável empurra a previsão de uma síntese para cima ou para baixo."],
      ["H² de Friedman", "fração do efeito conjunto de duas variáveis que não se explica pelos efeitos separados (interação)."],
      ["CV e ICC", "CV = dp/média das réplicas; ICC = fração da variância total que vem de diferenças reais entre condições."],
      ["IPW e SMD", "ponderação pelo inverso do escore de propensão para comparar grupos parecidos; SMD < 0,1 indica covariáveis balanceadas."],
      ["E-value", "força mínima que um confundidor não medido precisaria ter, com tratamento e desfecho, para anular o efeito estimado."],
      ["Wilcoxon pareado", "teste não paramétrico das diferenças dentro de cada repetição (mesma partida para as estratégias)."],
      ["hkl e r = D·tan 2θ", "índices de Miller do plano cristalino; o raio do anel no detector depende do ângulo de difração 2θ e da distância D."],
    ];
    $("#ab-gloss").innerHTML = G.map(([a, b]) => `<div><dt>${esc(a)}</dt><dd>${esc(b)}</dd></div>`).join("");
  };

  /* ------------------------------------------------------------------ fichas Dados · Método · Achado */
  function fichas() {
    const k = A.overview.kpis, L = A.literature, X = A.xrd.geometry, D = A.designer, B = A.benchmark, V = A.variability, C = A.causal, S = A.interpret;
    const wins = Object.values(B.datasets).filter((x) => x.paired["GP-EI"].p < 0.05 && x.paired["GP-EI"].wins > x.paired["GP-EI"].losses).length;
    const H = S.agnp.H2; let hi = [0, 1]; H.forEach((r, i) => r.forEach((v, j) => { if (i < j && v > H[hi[0]][hi[1]]) hi = [i, j]; }));
    const ag = S.agnp, imp = ag.features.map((_, j) => ag.values.reduce((a, r) => a + Math.abs(r[j] || 0), 0)), topF = ag.features[imp.indexOf(Math.max(...imp))];
    const M = A.overview.map, nexp = M.filter((m) => m.status === "experimental").length;
    const sizes = finite(L.records.size);
    const F = {
      literatura: [`${ni(L.n)} sínteses de ${ni(L.n_doi)} DOIs (Cruse 2022, NSP 2026, AuNCs 2025); ${ni(L.n_go)} com GO/rGO`,
        "mineração de texto, reagentes normalizados pelo dicionário PubChem, filtros físicos de plausibilidade",
        `tamanho mediano <b>${nf(median(sizes), 1)} nm</b>; o citrato segue como o redutor mais usado ano a ano`],
      caracterizacao: [`${ni(A.xrd.n_frames)} quadros GE 2048 × 2048 de CeO₂ + dark; ${ni(A.aunc.n)} AuNC de ${ni(A.aunc.n_doi)} artigos`,
        "centro pelo contraste do perfil radial, indexação da fluorita, ajuste r = D·tan 2θ",
        `<b>${ni(X.n_rings)} anéis</b> indexados, λ = ${nf(X.wavelength_A, 4)} Å (${nf(X.energy_keV, 1)} keV), RMS ${nf(X.rms_residual_px, 2)} px`],
      optica: [`n e k medidos do Au (Johnson & Christy) e ${ni(k.mie_validation_n)} pares tamanho–pico relatados`,
        "Mie com amortecimento de superfície, ensemble log-normal, perda J (Eq. 1) do pré-registro, cor por colorimetria CIE",
        `erro mediano de <b>${nf(k.mie_median_abs_residual, 1)} nm</b> no LSPR, sem nenhum ajuste`],
      designer: [`${ni(D.n_measurements)} medidas em ${ni(D.n_conditions)} condições (Mekki-Berrada 2021)`,
        "GP Matérn-5/2 + ARD em ln(perda), validação cruzada em 10 dobras, melhoria esperada (EI)",
        `R² <b>${nf(D.cv.r2, 2)}</b> e cobertura de ${nf(100 * D.cv.coverage95, 0)} % do IC 95 %`],
      interpretabilidade: ["GP da campanha AgNP; árvores para AuNC e para o tamanho na literatura",
        "valores de Shapley (exatos e TreeSHAP) e estatística H² de Friedman",
        `<b>${esc(topF)}</b> é a mais influente; maior interação: ${esc(ag.features[hi[0]])} × ${esc(ag.features[hi[1]])} (H² ${nf(H[hi[0]][hi[1]], 2)})`],
      aprendizado: [`${Object.keys(B.datasets).length} campanhas experimentais, ${B.seeds} repetições × ${B.arms.length} estratégias`,
        "reexecução com as medidas reais como oráculo; Wilcoxon pareado pela partida comum",
        `GP-EI melhor que o acaso em <b>${wins} de ${Object.keys(B.datasets).length}</b> campanhas; nas demais, empate estatístico`],
      variabilidade: [`${ni(V.agnp.n_measurements)} réplicas AgNP, ${ni(V.turkevich.n_papers)} artigos de Turkevich, ${ni(V.aunc_generalization.n_papers)} artigos de AuNC`,
        "Brown–Forsythe, ICC, um valor por artigo, validação agrupada por artigo",
        `mesma rota: <b>${nf(V.turkevich.q10_q90[0], 1)}–${nf(V.turkevich.q10_q90[1], 1)} nm</b>; R² cai de ${nf(V.aunc_generalization.r2_random, 2)} para ${nf(V.aunc_generalization.r2_new_paper, 2)} em artigo novo`],
      causal: [`${ni(Math.max(...C.effects.map((e) => e.n)))} sínteses de Cruse 2022 e NSP 2026 (a base de AuNC, selecionada pelo produto, fica fora)`,
        "grafo mecanístico; AIPW duplamente robusto, conferido por IPW, entropia e aparo; bootstrap de artigos; E-value",
        `<b>${C.effects.filter((e) => e.verdict.startsWith("confirma")).length} de ${C.effects.length}</b> efeitos na direção da literatura; ${C.effects.filter((e) => e.robust).length} robustos`],
      sobre: ["7 bases experimentais públicas, com DOI e licença",
        "tudo regenerável por code/webapp/build_site.py e conferido por testes automáticos",
        `<b>${nexp} de ${M.length}</b> seções da proposta já com dados experimentais`],
    };
    for (const [id, [d, m, a]] of Object.entries(F)) {
      const el = document.getElementById("fi-" + id);
      if (el) el.innerHTML = `<div><dt>Dados</dt><dd>${d}</dd></div><div><dt>Método</dt><dd>${m}</dd></div><div><dt>Achado</dt><dd>${a}</dd></div>`;
    }
  }
  // "Fig. 4.5a": figuras numeradas pela seção da proposta de cada aba
  function numberFigures() {
    for (const [id, , sec] of TABS) {
      if (!sec) continue;
      let k = 0;
      document.querySelectorAll(`#p-${id} .card`).forEach((card) => {
        const h = card.querySelector(".card-h h3"); if (!h || !card.querySelector(".plot, table")) return;
        const n = `${sec}${String.fromCharCode(97 + k++)}`;
        if (!card.id) card.id = "fig-" + n;
        h.insertAdjacentHTML("afterbegin", `<a class="fig" href="#${card.id}" title="Endereço desta figura">Fig. ${n}</a>`);
      });
    }
  }
  // busca rápida (Ctrl K): abas e gráficos
  function palette() {
    const box = $("#palette"), q = $("#palQ"), ul = $("#palL"), norm = (x) => x.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
    let items = [], sel = 0, last = null;
    function index() {
      items = TABS.map(([id, label, sec]) => ({ id, label, where: "aba" + (sec ? ` · §${sec}` : ""), el: null }));
      document.querySelectorAll(".panel").forEach((p) => {
        const id = p.id.slice(2), tab = TABS.find((t) => t[0] === id);
        p.querySelectorAll(".card").forEach((c) => { const h = c.querySelector("h3, h2"); if (!h) return;
          const fig = h.querySelector(".fig"), txt = h.textContent.replace(fig ? fig.textContent : "", "").trim();
          items.push({ id, label: txt, where: `${tab[1]}${fig ? " · " + fig.textContent : ""}`, el: c }); });
      });
    }
    function render() {
      const w = norm(q.value).split(/\s+/).filter(Boolean);
      const hits = items.filter((it) => w.every((x) => norm(it.label + " " + it.where).includes(x))).slice(0, 40);
      sel = Math.min(sel, Math.max(0, hits.length - 1));
      ul.innerHTML = hits.map((it, i) => `<li role="option" id="pal-${i}" aria-selected="${i === sel}" data-i="${items.indexOf(it)}"><span>${esc(it.label)}</span><small>${esc(it.where)}</small></li>`).join("") ||
        `<li aria-disabled="true"><span>Nada encontrado para "${esc(q.value)}"</span></li>`;
      q.setAttribute("aria-activedescendant", hits.length ? "pal-" + sel : "");
    }
    function go(i) {
      const it = items[i]; if (!it) return;
      close(); location.hash = it.id; show(it.id);
      if (it.el) requestAnimationFrame(() => { it.el.scrollIntoView({ block: "start", behavior: "smooth" }); it.el.classList.remove("flash"); void it.el.offsetWidth; it.el.classList.add("flash"); });
    }
    function open() { last = document.activeElement; index(); q.value = ""; sel = 0; render(); box.hidden = false; $("#backdrop").hidden = false; q.focus(); }
    function close() { box.hidden = true; if (!$(".card.full")) $("#backdrop").hidden = true; if (last && last.focus) last.focus(); }
    $("#findBtn").addEventListener("click", open);
    q.addEventListener("input", () => { sel = 0; render(); });
    q.addEventListener("keydown", (e) => {
      const n = ul.querySelectorAll("li[data-i]").length;
      if (e.key === "ArrowDown") { e.preventDefault(); sel = Math.min(n - 1, sel + 1); render(); }
      else if (e.key === "ArrowUp") { e.preventDefault(); sel = Math.max(0, sel - 1); render(); }
      else if (e.key === "Enter") { e.preventDefault(); const li = ul.querySelectorAll("li[data-i]")[sel]; if (li) go(+li.dataset.i); }
      else if (e.key === "Escape") { e.preventDefault(); close(); }
    });
    ul.addEventListener("click", (e) => { const li = e.target.closest("li[data-i]"); if (li) go(+li.dataset.i); });
    $("#backdrop").addEventListener("click", () => { if (!box.hidden) close(); });
    document.addEventListener("keydown", (e) => {
      const typing = /INPUT|SELECT|TEXTAREA/.test((document.activeElement || {}).tagName || "");
      if ((e.key === "k" || e.key === "K") && (e.ctrlKey || e.metaKey)) { e.preventDefault(); box.hidden ? open() : close(); }
      else if (e.key === "/" && !typing && box.hidden) { e.preventDefault(); open(); }
    });
  }

  function trapFocus() {
    document.addEventListener("keydown", (e) => {
      if (e.key !== "Tab") return;
      const m = [$("#dataDlg"), $("#palette")].find((x) => x && !x.hidden) || $(".card.full");
      if (!m) return;
      const f = [...m.querySelectorAll('a[href], button:not([disabled]), input, select, textarea, [tabindex]:not([tabindex="-1"])')]
        .filter((x) => !x.hidden && x.getClientRects().length);
      if (!f.length) return;
      const i = f.indexOf(document.activeElement);
      if (e.shiftKey ? i <= 0 : i < 0 || i === f.length - 1) { e.preventDefault(); f[e.shiftKey ? f.length - 1 : 0].focus(); }
    });
  }
  // impressão (Ctrl P → PDF): os gráficos se ajustam à largura da página e voltam depois
  function printFit() {
    const fit = () => document.querySelectorAll(".panel:not([hidden]) .js-plotly-plot").forEach((el) => { try { Plotly.Plots.resize(el); } catch (e) { /* oculto */ } });
    window.addEventListener("beforeprint", fit); window.addEventListener("afterprint", () => setTimeout(fit, 50));
  }

  /* ------------------------------------------------------------------ início */
  function start() {
    trapFocus(); printFit();
    buildTabs();
    addExpanders();
    document.querySelectorAll(".nseeds").forEach((el) => { el.textContent = ni(A.benchmark.seeds); });
    document.querySelectorAll(".nturk").forEach((el) => { el.textContent = ni(A.variability.turkevich.n_papers); });
    fichas(); numberFigures(); palette();
    $("#foot").innerHTML = `<div><b>AuGOSintesIA</b> · plataforma de aprendizado ativo para nanocompósitos GO–AuNP · IC FAPESP · UNESP-IQ Araraquara</div>` +
      `<div>Gerado em ${esc(A.overview.generated)} por <span class="mono">code/webapp/build_site.py</span> · só dados experimentais; modelos e previsões marcados como tal</div>`;
    const tt = $("#toTop");
    window.addEventListener("scroll", perFrame(() => tt.classList.toggle("on", window.scrollY > 700)), { passive: true });
    tt.addEventListener("click", () => window.scrollTo({ top: 0, behavior: "smooth" }));
    try { const th = localStorage.getItem("augo-theme"); if (th) document.documentElement.setAttribute("data-theme", th); } catch (e) { /* sem armazenamento */ }
    $("#themeBtn").addEventListener("click", () => {
      const next = isDark() ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      try { localStorage.setItem("augo-theme", next); } catch (e) { /* sem armazenamento */ }
    });
    // qualquer troca de tema (botão, visualizador ou sistema) redesenha os gráficos com as cores do tema
    let pend = 0;
    const redraw = () => { clearTimeout(pend); pend = setTimeout(themeChanged, 60); };
    new MutationObserver(redraw).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    if (window.matchMedia) window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
      if (!document.documentElement.getAttribute("data-theme")) redraw(); });
    $("#themeLbl").textContent = isDark() ? "Tema claro" : "Tema escuro";
    $("#themeBtn").setAttribute("aria-pressed", isDark() ? "true" : "false");
    let first = (location.hash || "").slice(1);
    if (!first) { try { first = localStorage.getItem("augo-tab") || "visao"; } catch (e) { first = "visao"; } }
    route(first);
    requestAnimationFrame(() => setTimeout(() => $("#boot").classList.add("done"), 120));
  }
  if (!window.Plotly) {
    document.getElementById("boot").classList.add("done");
    document.getElementById("main").insertAdjacentHTML("afterbegin",
      '<p class="note">A biblioteca de gráficos (Plotly) não carregou. Abra o arquivo site/index.html da pasta do repositório, com a pasta vendor/ ao lado.</p>');
    return;
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
})();
