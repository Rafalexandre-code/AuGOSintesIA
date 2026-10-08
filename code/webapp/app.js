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
    preditor: '<path d="M4 20h16"/><path d="M6 20V9M10 20V5M14 20v-8M18 20v-5"/><path d="M5 9l5-4 4 7 4-2" stroke-dasharray="2 2"/>',
    aprendizado: '<path d="M20 11a8 8 0 1 0-2.3 5.7"/><path d="M20 5v6h-6"/><circle cx="12" cy="12" r="2" fill="currentColor"/>',
    variabilidade: '<circle cx="6" cy="16" r="1.6"/><circle cx="10" cy="9" r="1.6"/><circle cx="14" cy="14" r="1.6"/><circle cx="18" cy="6" r="1.6"/><circle cx="17" cy="18" r="1.6"/><path d="M3 21h18"/>',
    causal: '<circle cx="5" cy="12" r="2.5"/><circle cx="19" cy="12" r="2.5"/><circle cx="12" cy="4.5" r="2.5"/><path d="M7.5 12h9M7 10.5l3.4-4M17 10.5l-3.4-4"/>',
    guia: '<path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v15H6.5A2.5 2.5 0 0 0 4 20.5z"/><path d="M4 20.5A2.5 2.5 0 0 0 6.5 23H20v-5"/><path d="M8 7h8M8 11h6"/>',
    sobre: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5v.5"/>',
  };
  const ico = (id, cls) => `<svg viewBox="0 0 24 24" aria-hidden="true"${cls ? ` class="${cls}"` : ""} fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">${IC[id]}</svg>`;
  const NAV = [["Panorama", [["visao", "Visão geral", ""]]],
    ["Dados", [["literatura", "Literatura", "4.1"], ["caracterizacao", "Caracterização", "4.2"]]],
    ["Modelos", [["optica", "Óptica e J", "4.4"], ["designer", "AuNP Designer", "4.5"], ["interpretabilidade", "Interpretabilidade", "4.13"]]],
    ["Decisão", [["preditor", "Preditor", "4.18"], ["aprendizado", "Aprendizado ativo", "4.15"], ["variabilidade", "Variabilidade", "4.17"], ["causal", "Causalidade", "4.9"]]],
    ["Projeto", [["guia", "Guia completo", ""], ["sobre", "Sobre e dados", ""]]]];
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
    if (h && h.startsWith("doc-") && !document.getElementById(h)) show("guia");      // o guia é montado na primeira visita
    const el = h && document.getElementById(h), panel = el && el.closest(".panel");
    show(panel ? panel.id.slice(2) : "visao");
    if (el && guideReveal && el.closest("#gd-main")) guideReveal(el);
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
  function addExpanders(root = document) {
    const icoT = '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M2 3h12v10H2zM2 7h12M6 3v10" fill="none" stroke="currentColor" stroke-width="1.5"/></svg>';
    const ico = '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M2 6V2h4M10 2h4v4M14 10v4h-4M6 14H2v-4" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>';
    root.querySelectorAll(".card").forEach((card) => {
      if (!card.querySelector(".plot") || card.classList.contains("hero-vis") || card.querySelector(".card-h .btns")) return;
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
    if (root !== document) return;                                   // ouvintes globais: só na primeira chamada
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
    const winsHolm = Object.values(B.datasets).filter((x) => x.paired["GP-EI"].p_holm < 0.05 && x.paired["GP-EI"].wins > x.paired["GP-EI"].losses).length;
    const ag = I.agnp, imp = ag.features.map((_, j) => ag.values.reduce((a, r) => a + Math.abs(r[j] || 0), 0));
    const topF = ag.features[imp.indexOf(Math.max(...imp))];
    const F = [
      ["optica", nf(k.mie_median_abs_residual, 1) + " nm", `erro mediano do Mie, sem ajuste, ao prever o pico de absorção de ${ni(k.mie_validation_n)} esferas relatadas.`, "§4.4 · §4.10"],
      ["designer", "R² " + nf(k.designer_cv_r2, 2), `do GP do Designer em validação cruzada na campanha AgNP real; ${nf(100 * k.designer_coverage, 0)} % das medidas caem no IC 95 %.`, "§4.5 · §4.18"],
      ["aprendizado", `−${nf(-B.datasets.AgNP.survival.vs_random["GP-EI"].rmst_diff, 1)} exp.`, `que o GP-EI economiza até o top 5 % na campanha AgNP (RMST pareado, IC 95 % ${nf(-B.datasets.AgNP.survival.vs_random["GP-EI"].ci95[1], 1)}–${nf(-B.datasets.AgNP.survival.vs_random["GP-EI"].ci95[0], 1)}); vence o acaso em ${wins} de ${Object.keys(B.datasets).length} campanhas (${winsHolm} após Holm).`, "§4.15"],
      ["variabilidade", `${nf(V.turkevich.q10_q90[0], 1)}–${nf(V.turkevich.q10_q90[1], 1)} nm`, `tamanho da mesma rota de Turkevich em ${ni(V.turkevich.n_papers)} artigos (10–90 %): a premissa da variabilidade multi-fonte.`, "§4.7 · §4.17"],
      ["preditor", `×${nf(A.predictor.bands["90"].median_fold_width, 0)}`, `é a largura típica do intervalo de 90 % do tamanho só pela receita (cobertura de ${nf(100 * A.predictor.bands["90"].coverage_articles, 0)} % em artigos novos): a fonte importa.`, "§4.18 · §4.7"],
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
    // inversão bayesiana pico → tamanho
    const IV = O.inversion; let prior = "lit";
    function inv() {
      const t = T(), pk = +$("#op-pk").value, nu = IV.nu, g = IV.d;
      $("#op-pk-o").textContent = `${nf(pk, 1)} nm`;
      const lik = g.map((_, i) => { const z = (pk - IV.lam[i] - IV.bias[i]) / IV.sd[i]; return (nu > 0 ? Math.pow(1 + z * z / nu, -(nu + 1) / 2) : Math.exp(-0.5 * z * z)) / IV.sd[i]; });
      const raw = lik.map((v, i) => v * (prior === "lit" ? IV.prior[i] : 1)), Z = raw.reduce((a, b) => a + b, 0), post = raw.map((v) => v / Z);
      let c = 0; const cdf = post.map((v) => (c += v));
      const at = (q) => g[Math.min(cdf.findIndex((v) => v >= q), g.length - 1)];
      const lo = at(0.05), md = at(0.5), hi = at(0.95), p25 = cdf[g.findIndex((x) => x >= 25)] || 0, mode = g[post.indexOf(Math.max(...post))];
      kpis("#op-inv-kpis", [
        { k: "Diâmetro mais provável", v: nf(mode, mode < 10 ? 1 : 0), u: "nm", s: `mediana posterior ${nf(md, md < 10 ? 1 : 0)} nm`, key: true },
        { k: "Intervalo de credibilidade 90 %", v: `${nf(lo, lo < 10 ? 1 : 0)}–${nf(hi, 0)}`, u: "nm", s: `fator ×${nf(hi / lo, 1)}` },
        { k: "P(d < 25 nm)", v: nf(100 * p25, 0), u: "%", s: "abaixo de 25 nm o pico quase não muda" },
        { k: "Validação (artigos novos)", v: nf(100 * IV.coverage90, 0), u: "%", s: `do IC 90 % contém o tamanho real (${ni(IV.n)} esferas, ${ni(IV.n_articles)} artigos)` },
      ]);
      const pn = (arr) => { const m = Math.max(...arr); return arr.map((v) => v / m); }, pr = prior === "lit" ? pn(IV.prior) : g.map(() => 1);
      plot("op-inv", [
        { type: "scatter", mode: "lines", name: "a priori", x: g, y: pr, line: { color: t.muted, width: 1.4, dash: "dot" }, hoverinfo: "skip" },
        { type: "scatter", mode: "lines", name: "verossimilhança (só o pico)", x: g, y: pn(lik), line: { color: t.cat[1], width: 1.6, dash: "dash" }, hoverinfo: "skip" },
        { type: "scatter", mode: "lines", name: "posterior", x: g, y: pn(post), fill: "tozeroy", fillcolor: hexA(t.cat[0], t.dark ? 0.22 : 0.16), line: { color: t.cat[0], width: 2.4 },
          hovertemplate: "d = %{x:.1f} nm<extra>posterior</extra>" }],
      { xaxis: { type: "log", title: { text: "diâmetro (nm)" }, tickvals: [2, 5, 10, 20, 50, 100, 200] }, yaxis: { title: { text: "densidade (máx. = 1)" }, range: [0, 1.05] },
        shapes: [{ type: "rect", xref: "x", yref: "paper", x0: lo, x1: hi, y0: 0, y1: 1, fillcolor: hexA(t.dark ? "#e0b45c" : "#b8862a", 0.14), line: { width: 0 }, layer: "below" }] });
    }
    $("#op-pk").addEventListener("input", perFrame(inv));
    segmented("#op-pri", (v) => { prior = v; inv(); });
    drawer(inv);
    $("#op-inv-txt").innerHTML = `<p>Com o pico em 518–522 nm, a posterior se espalha de poucos nanômetros até ~30 nm: o UV-Vis sozinho não identifica o tamanho na faixa do alvo do projeto, e por isso a TEM confirma (e o MISO decide quando vale pagá-la). ` +
      `Acima de ~530 nm o pico desloca o diâmetro mais provável para dezenas de nanômetros, mas o intervalo segue largo: o par pico–tamanho dos relatos erra muito (caudas pesadas: pico lido no olho, tamanho de outra técnica ou de outra síntese do artigo). Validação em 5 dobras por artigo: o IC de 90 % contém o tamanho real em ${nf(100 * IV.coverage90, 0)} % dos casos ` +
      `(gaussiana: ${nf(100 * IV.scan[0].coverage90, 0)} %; a t de Student com ν = ${IV.nu} foi escolhida pela cobertura mais próxima de 90 %; a priori uniforme: ${nf(100 * IV.coverage90_uniform, 0)} %).</p>`;
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
    const CB = D.calibration;
    drawer(() => {
      const t = T(), L = CB.levels;
      plot("ds-rel", [
        { type: "scatter", mode: "lines", x: [0, 1], y: [0, 1], line: { color: t.muted, width: 1, dash: "dot" }, hoverinfo: "skip", showlegend: false },
        { type: "scatter", mode: "lines+markers", name: "GP (σ por condição)", x: L, y: CB.coverage, line: { color: t.cat[0], width: 2.4 }, marker: { size: 8, line: { width: 2, color: t.surface } },
          hovertemplate: "nominal %{x:.0%} → observado %{y:.1%}<extra>GP</extra>" },
        { type: "scatter", mode: "lines+markers", name: "σ constante (RMSE)", x: L, y: CB.coverage_const, line: { color: t.cat[1], width: 1.8, dash: "dash" }, marker: { size: 6 },
          hovertemplate: "nominal %{x:.0%} → observado %{y:.1%}<extra>σ constante</extra>" }],
      { xaxis: { title: { text: "nível nominal do intervalo" }, tickformat: ".0%", range: [0, 1] }, yaxis: { title: { text: "cobertura observada" }, tickformat: ".0%", range: [0, 1] } });
      const n = CB.pit_hist.reduce((a, b) => a + b, 0);
      plot("ds-pit", [{ type: "bar", x: CB.pit_hist.map((_, i) => (i + 0.5) / 10), y: CB.pit_hist, width: 0.092, marker: { color: t.cat[0] },
        hovertemplate: "PIT %{x:.2f}: %{y} previsões<extra></extra>" }],
      { xaxis: { title: { text: "PIT" }, range: [0, 1] }, yaxis: { title: { text: "previsões" }, rangemode: "tozero" }, showlegend: false,
        shapes: [{ type: "line", xref: "paper", x0: 0, x1: 1, y0: n / 10, y1: n / 10, line: { color: t.ink, width: 1, dash: "dot" } }] });
    });
    $("#ds-cal-txt").innerHTML = `<p>O GP está calibrado no conjunto (desvio dos resíduos padronizados ${nf(CB.z_sd, 2)}, ideal 1; PIT contra uniforme: Kolmogorov–Smirnov ${pf(CB.pit_ks_p)}), ` +
      `com intervalos um pouco largos no centro e caudas um pouco curtas (99 % nominal cobre ${nf(100 * CB.coverage[CB.coverage.length - 1], 0)} %). ` +
      `O CRPS do GP (${nf(CB.crps, 4)}) não supera o de um σ constante (${nf(CB.crps_const, 4)}): a incerteza por condição não ordena bem quais medidas erram mais, ` +
      "o mesmo recado da tabela de modelos abaixo — o erro vem de algo que as vazões não descrevem.</p>";
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
        { k: `${esc(arm)} × aleatório (pareado)`, v: verdict, s: `${pr.wins} vitórias, ${pr.ties} empates, ${pr.losses} derrotas · Wilcoxon ${pf(pr.p)} · Holm ${nf(pr.p_holm, 3)}` },
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
    const drawSurv = () => {
      const t = T(), ds = B.datasets[$("#bo-ds").value], arm = $("#bo-arm").value, Sv = ds.survival, tt = Sv.t, tr = [];
      B.arms.forEach((a, k) => {
        const km = Sv.km[a], col = t.cat[k], main = a === arm || a === "Aleatório";
        if (main) {
          tr.push({ type: "scatter", mode: "lines", x: tt, y: km.hi, line: { width: 0, shape: "hv" }, hoverinfo: "skip", showlegend: false, legendgroup: a });
          tr.push({ type: "scatter", mode: "lines", x: tt, y: km.lo, fill: "tonexty", fillcolor: hexA(col, t.dark ? 0.18 : 0.13), line: { width: 0, shape: "hv" }, hoverinfo: "skip", showlegend: false, legendgroup: a });
        }
        tr.push({ type: "scatter", mode: "lines", name: `${a} (RMST ${nf(Sv.rmst[a], 1)})`, x: tt, y: km.S, legendgroup: a,
          line: { color: col, width: main ? 2.6 : 1.3, shape: "hv", dash: main ? "solid" : "dot" },
          hovertemplate: `${a}: após %{x} experimentos, %{y:.0%} ainda sem chegar<extra></extra>` });
      });
      plot("bo-km", tr, { xaxis: { title: { text: "experimentos" }, range: [0, ds.budget] }, yaxis: { title: { text: "fração que ainda não chegou ao top 5 %" }, tickformat: ".0%", range: [0, 1.02] } });
      const rows = names.map((n) => B.datasets[n].survival.vs_random[arm]);
      plot("bo-rmst", [{ type: "scatter", mode: "markers+text", y: names, x: rows.map((r) => -r.rmst_diff),
        error_x: { type: "data", symmetric: false, array: rows.map((r) => -r.ci95[0] + r.rmst_diff), arrayminus: rows.map((r) => r.ci95[1] - r.rmst_diff), color: t.ink2, thickness: 1.6, width: 6 },
        marker: { size: 11, color: rows.map((r) => (r.ci95[1] < 0 ? t.cat[2] : r.ci95[0] > 0 ? t.cat[1] : t.other)), line: { width: 2, color: t.surface } },
        text: rows.map((r) => `P = ${nf(r.p_better, 2)}`), textposition: "top center", textfont: { size: 10, color: t.ink2 },
        customdata: rows.map((r) => [r.ci95[0], r.ci95[1], r.p_better, r.logrank_p]),
        hovertemplate: `%{y}: ${esc(arm)} economiza %{x:.1f} experimentos<br>P(melhor) = %{customdata[2]:.3f} · log-rank p = %{customdata[3]:.3g}<extra></extra>` }],
      { xaxis: { title: { text: `experimentos economizados (> 0: ${arm} melhor)` }, zeroline: true, zerolinecolor: t.ink }, yaxis: { autorange: "reversed", automargin: true }, margin: { l: 110 }, showlegend: false });
    };
    $("#bo-surv").innerHTML = "<thead><tr><th>Campanha</th><th class='num'>RMST aleatório</th>" + others.map((a) => `<th class="num">${a}: economia (IC 95 %) · P(melhor) · log-rank</th>`).join("") + "</tr></thead><tbody>" +
      names.map((n) => { const Sv = B.datasets[n].survival; return `<tr><td>${esc(n)}</td><td class="num">${nf(Sv.rmst["Aleatório"], 1)}</td>` +
        others.map((a) => { const r = Sv.vs_random[a], sig = r.ci95[1] < 0;
          return `<td class="num">${sig ? "<b>" : ""}${nf(-r.rmst_diff, 1)}${sig ? "</b>" : ""} <span class="muted">(${nf(-r.ci95[1], 1)} a ${nf(-r.ci95[0], 1)}) · ${nf(r.p_better, 2)} · ${pf(r.logrank_p)}</span></td>`; }).join("") + "</tr>"; }).join("") + "</tbody>";
    $("#bo-ds").addEventListener("change", drawSurv); $("#bo-arm").addEventListener("change", drawSurv);
    drawer(drawSurv);
    const wonBy = names.filter((n) => { const pr = B.datasets[n].paired["GP-EI"]; return pr.p < 0.05 && pr.wins > pr.losses; });
    const wonHolm = names.filter((n) => { const pr = B.datasets[n].paired["GP-EI"]; return pr.p_holm < 0.05 && pr.wins > pr.losses; });
    $("#bo-insight").innerHTML = `<b>Leitura.</b> O GP-EI chega antes do acaso com p < 0,05 em ${wonBy.join(", ")} e empata nas demais; corrigindo para as 15 comparações (Holm), só ${wonHolm.join(", ") || "nenhuma"} se mantém, e as outras ficam como evidência sugestiva (a economia em experimentos, abaixo, tem IC fora do zero nelas). ` +
      `O ganho cresce com o espaço de busca: com cerca de 100 condições (${names.filter((n) => B.datasets[n].n_pool <= 110).join(", ")}), o top 5 % tem só 5 condições e a partida aleatória já cobre boa parte dele. ` +
      "É o mesmo quadro de Liang et al. (npj Comput. Mater. 2021), de onde vêm essas bases: GP com ARD e floresta aleatória superam o acaso, com vantagem maior nos espaços grandes.";
    $("#bo-ds").addEventListener("change", draw); $("#bo-arm").addEventListener("change", draw);
    drawer(draw);
    $("#bo-tbl").innerHTML = "<thead><tr><th>Campanha</th><th class='num'>Condições</th>" + B.arms.map((a) => `<th class="num">${a}</th>`).join("") + "</tr></thead><tbody>" +
      names.map((n) => { const ds = B.datasets[n]; return `<tr><td>${esc(n)} <span class="muted">(${esc(ds.objective)})</span></td><td class="num">${ds.n_pool}</td>` +
        B.arms.map((a) => { const m = ds.median_censored[a]; if (a === "Aleatório") return `<td class="num">${nf(m, m % 1 ? 1 : 0)}</td>`;
          const pr = ds.paired[a], sig = pr.p_holm < 0.05;
          return `<td class="num">${sig ? "<b>" : ""}${nf(m, m % 1 ? 1 : 0)}${sig ? "</b>" : ""} <span class="muted">(${pr.wins}–${pr.ties}–${pr.losses}; ${pf(pr.p)}; Holm ${nf(pr.p_holm, 3)})</span></td>`; }).join("") + "</tr>"; }).join("") + "</tbody>";
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
    const Sb = S.agnp.sobol, fl = S.agnp.features;
    drawer(() => {
      const t = T(), bar = (k, name, col) => ({ type: "bar", orientation: "h", name, y: fl, x: Sb[k].map((v) => Math.max(0, v)), marker: { color: col },
        error_x: { type: "data", symmetric: false, array: Sb[k].map((v, i) => Sb[k + "_ci"][i][1] - Math.max(0, v)), arrayminus: Sb[k].map((v, i) => Math.max(0, Math.max(0, v) - Sb[k + "_ci"][i][0])), color: t.ink2, thickness: 1.2, width: 4 },
        hovertemplate: `%{y}: ${name} = %{x:.3f}<extra></extra>` });
      plot("sh-sobol", [bar("S1", "S1 (sozinha)", t.cat[0]), bar("ST", "ST (com interações)", t.cat[1])],
        { barmode: "group", xaxis: { title: { text: "fração da variância" }, range: [0, 1] }, yaxis: { autorange: "reversed", automargin: true }, margin: { l: 130 } });
    });
    {
      const order = fl.map((n, i) => [n, Sb.ST[i] - Sb.S1[i]]).sort((a, b) => b[1] - a[1]);
      $("#sh-sobol-txt").innerHTML = `<p>As vazões explicam sozinhas ${nf(100 * Sb.sum_S1, 0)} % da variância; os outros ${nf(100 * (1 - Sb.sum_S1), 0)} % vêm de interações. ` +
        `A que mais age em conjunto é ${esc(order[0][0])} (ST − S1 = ${nf(order[0][1], 2)}), coerente com o mapa H² acima. ` +
        "Uma vazão com ST ≈ 0 pode ser fixada sem perder nada: é a variável que dá para tirar da otimização.</p>";
    }
    fillFeatures();
    $("#sh-m").addEventListener("change", () => { fillFeatures(); draw(); }); $("#sh-f").addEventListener("change", draw);
    drawer(draw);
  };

  /* ================================================================== preditor de síntese */
  function hgbPred(M, x) {                                   // soma das folhas das árvores exportadas (igual a analyses.hgb_predict)
    let s = M.base;
    for (const r of M.roots) {
      let k = r;
      while (M.f[k] >= 0) { const v = x[M.f[k]]; k = v == null || Number.isNaN(v) ? (M.m[k] ? M.l[k] : M.r[k]) : (v <= M.t[k] ? M.l[k] : M.r[k]); }
      s += M.v[k];
    }
    return s;
  }
  INIT.preditor = function () {
    const P = A.predictor, F = P.features, fi = (n) => F.indexOf(n), Bd = P.bands;
    const RED = F.slice(0, 10), CAP = F.slice(10, 19), CAT = P.categorical;
    const freq = (name) => { const j = CAT.indexOf(name); return P.recipes.reduce((a, r) => a + (r.sig[j] === "1" ? r.n : 0), 0); };
    const chips = (names) => names.map((n) => `<label><input type="checkbox" value="${esc(n)}">${esc(n)} <small>${ni(freq(n))}</small></label>`).join("");
    $("#pr-red").innerHTML = chips(RED); $("#pr-cap").innerHTML = chips(CAP);
    const tgD0 = A.optics.target.diameter, toV = (d) => Math.round(Math.log(d) / Math.log(300) * 1000), fromV = (v) => Math.pow(300, v / 1000);
    $("#pr-target").value = toV(tgD0);
    let seed = 0;
    const PRE = [["Turkevich (citrato, 100 °C)", ["citrato"], [], 0, "sph", 100],
      ["Brust (NaBH₄ + tiol + TOAB)", ["NaBH₄"], ["tiol (GSH/dodecanotiol)", "TOAB"], 0, "sph", 25],
      ["Sementes + CTAB (bastões)", ["NaBH₄", "ácido ascórbico"], ["CTAB"], 1, "rod", 30],
      ["Redução verde (ácido tânico + citrato)", ["ácido tânico", "citrato"], [], 0, "sph", 70],
      ["Aglomerados com GSH", ["NaBH₄"], ["tiol (GSH/dodecanotiol)"], 0, "clu", 25],
      ["Sementes de citrato + ascórbico", ["citrato", "ácido ascórbico"], [], 1, "sph", 25]];
    $("#pr-presets").insertAdjacentHTML("beforeend", PRE.map(([l], i) => `<button type="button" data-i="${i}">${esc(l)}</button>`).join(""));
    const setSeed = (v) => { seed = +v; $("#pr-seed").querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", b.dataset.v === String(seed) ? "true" : "false")); };
    function load(i) {
      const [, r, c, sd, mo, T] = PRE[i];
      $("#pr-red").querySelectorAll("input").forEach((x) => { x.checked = r.includes(x.value); });
      $("#pr-cap").querySelectorAll("input").forEach((x) => { x.checked = c.includes(x.value); });
      setSeed(sd); $("#pr-morph").value = mo; $("#pr-T").value = T; $("#pr-Tna").checked = false;
      $("#pr-presets").querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", b.dataset.i === String(i) ? "true" : "false"));
    }
    // estado da interface → vetor de variáveis do modelo
    function state() {
      return { red: [...$("#pr-red").querySelectorAll("input:checked")].map((x) => x.value), cap: [...$("#pr-cap").querySelectorAll("input:checked")].map((x) => x.value),
        seed, morph: $("#pr-morph").value, T: $("#pr-Tna").checked ? null : +$("#pr-T").value, year: +$("#pr-year").value,
        go: $("#pr-go").checked, src: $("#pr-src").value };
    }
    function vec(st) {
      const x = new Array(F.length).fill(0);
      st.red.concat(st.cap).forEach((n) => { x[fi(n)] = 1; });
      x[fi("mediada por sementes")] = st.seed; x[fi("temperatura (°C)")] = st.T == null ? NaN : st.T; x[fi("ano")] = st.year;
      x[fi("forma não esférica")] = st.morph === "rod" || st.morph === "oth" ? 1 : 0; x[fi("bastão")] = st.morph === "rod" ? 1 : 0;
      x[fi("aglomerado")] = st.morph === "clu" ? 1 : 0; x[fi("menciona GO")] = st.go ? 1 : 0;
      x[fi("base NSP")] = st.src === "nsp" ? 1 : 0; x[fi("base AuNC")] = st.src === "aunc" ? 1 : 0;
      return x;
    }
    const sigOf = (x) => CAT.map((n) => (x[fi(n)] ? "1" : "0")).join("");
    // quantis conformalizados em ln d → nós da distribuição preditiva (CDF linear por partes)
    function dist(x) {
      const q = {}; ["0.05", "0.25", "0.5", "0.75", "0.95"].forEach((k) => { q[k] = hgbPred(P.models[k], x); });
      const v = [q["0.05"] - Bd["90"].Q, q["0.25"] - Bd["50"].Q, q["0.5"], q["0.75"] + Bd["50"].Q, q["0.95"] + Bd["90"].Q].sort((a, b) => a - b);
      return { v, p: [0.05, 0.25, 0.5, 0.75, 0.95] };
    }
    function cdf(D, lx) {
      const { v, p } = D;
      if (lx <= v[0]) { const sl = (p[1] - p[0]) / Math.max(v[1] - v[0], 1e-6); return Math.max(0, p[0] - (v[0] - lx) * sl); }
      if (lx >= v[4]) { const sl = (p[4] - p[3]) / Math.max(v[4] - v[3], 1e-6); return Math.min(1, p[4] + (lx - v[4]) * sl); }
      let i = 0; while (lx > v[i + 1]) i++;
      return p[i] + (p[i + 1] - p[i]) * (lx - v[i]) / Math.max(v[i + 1] - v[i], 1e-9);
    }
    const pTarget = (D, t) => cdf(D, Math.log(1.2 * t)) - cdf(D, Math.log(0.8 * t));
    const recs = P.recipes.map((r) => ({ ...r, bits: r.sig }));
    function similar(sg) {
      const rb = sg.slice(0, 19);
      return recs.filter((r) => r.sig !== sg && r.n >= 2).map((r) => {
        let inter = 0, uni = 0;
        for (let j = 0; j < 19; j++) { const a = rb[j] === "1", b = r.sig[j] === "1"; if (a && b) inter++; if (a || b) uni++; }
        const jac = uni ? inter / uni : 1;
        return { r, score: jac - 0.35 * (r.sig[19] !== sg[19]) - 0.35 * (r.sig.slice(20) !== sg.slice(20)) };
      }).sort((a, b) => b.score - a.score || b.r.n - a.r.n).slice(0, 6);
    }
    function describe(r, sg) {                                 // diferença da receita r para a atual, em palavras
      const out = [];
      for (let j = 0; j < 19; j++) if (r.sig[j] !== sg[j]) out.push((r.sig[j] === "1" ? "+ " : "− ") + CAT[j]);
      if (r.sig[19] !== sg[19]) out.push(r.sig[19] === "1" ? "com sementes" : "rota direta");
      if (r.sig.slice(20) !== sg.slice(20)) out.push("forma: " + (r.sig[21] === "1" ? "bastão" : r.sig[22] === "1" ? "aglomerado" : r.sig[20] === "1" ? "outra" : "esfera"));
      return out.length ? out.join(", ") : "idêntica";
    }
    const MORPH_TXT = { sph: "esfera ou partícula", rod: "bastão", clu: "aglomerado", oth: "outra não esférica" };
    function alternatives(st) {                               // trocas de um único item da receita
      const alts = [];
      RED.concat(CAP).forEach((n) => { const isR = RED.includes(n), on = (isR ? st.red : st.cap).includes(n);
        const s2 = { ...st, red: st.red.slice(), cap: st.cap.slice() }, arr = isR ? s2.red : s2.cap;
        if (on) arr.splice(arr.indexOf(n), 1); else arr.push(n);
        alts.push([(on ? "− " : "+ ") + n, s2]); });
      alts.push([st.seed ? "rota direta" : "rota com sementes", { ...st, seed: 1 - st.seed }]);
      Object.keys(MORPH_TXT).filter((m) => m !== st.morph).forEach((m) => alts.push(["forma: " + MORPH_TXT[m], { ...st, morph: m }]));
      [25, 100].filter((T) => st.T !== T).forEach((T) => alts.push([`T = ${T} °C`, { ...st, T }]));
      return alts;
    }
    const link = (e) => (/^10\./.test(e) ? `<a href="https://doi.org/${esc(e)}" target="_blank" rel="noopener">${esc(e)}</a>` : esc(e));
    function draw() {
      const t = T(), st = state(), x = vec(st), D = dist(x), sg = sigOf(x), tg = fromV(+$("#pr-target").value);
      $("#pr-T-o").textContent = st.T == null ? "—" : `${st.T} °C`; $("#pr-year-o").textContent = st.year; $("#pr-target-o").textContent = `${nf(tg, tg < 10 ? 1 : 0)} nm`;
      const ex = (k) => Math.exp(D.v[k]), med = ex(2), pt = pTarget(D, tg);
      const same = recs.find((r) => r.sig === sg), sim = similar(sg);
      kpis("#pr-kpis", [
        { k: "Tamanho mediano previsto", v: nf(med, med < 10 ? 1 : 0), u: "nm", s: `50 %: ${nf(ex(1), 1)}–${nf(ex(3), 1)} nm`, key: true },
        { k: "Intervalo de 90 % (conformal)", v: `${nf(ex(0), ex(0) < 10 ? 1 : 0)}–${nf(ex(4), 0)}`, u: "nm", s: `cobre ${nf(100 * Bd["90"].coverage_articles, 0)} % dos artigos novos na validação` },
        { k: `P(alvo ${nf(tg, 0)} nm ± 20 %)`, v: nf(100 * pt, 0), u: "%", s: "da distribuição preditiva (CDF por partes entre os quantis)" },
        { k: "Receita idêntica na literatura", v: same ? ni(same.n) : "nenhuma", u: same ? "sínteses" : "", s: same ? `${ni(same.n_art)} artigos · mediana ${nf(same.median, 1)} nm (10–90 %: ${nf(same.q10, 1)}–${nf(same.q90, 1)})` : "o modelo extrapola: veja as parecidas" },
      ]);
      // floresta: previsão + receitas
      const rows = [{ lab: "previsão (este protocolo)", m: med, lo: ex(0), hi: ex(4), lo50: ex(1), hi50: ex(3), n: null, pred: true }];
      if (same) rows.push({ lab: `receita idêntica (${ni(same.n)})`, m: same.median, lo: same.q10, hi: same.q90, n: same.n });
      sim.forEach(({ r }) => rows.push({ lab: `${describe(r, sg)} (${ni(r.n)})`, m: r.median, lo: r.q10, hi: r.q90, n: r.n }));
      const ys = rows.map((r) => (r.lab.length > 46 ? r.lab.slice(0, 44) + "…" : r.lab));
      const tr = [
        { type: "scatter", mode: "lines", x: [rows[0].lo, rows[0].hi], y: [ys[0], ys[0]], line: { color: t.ruby, width: 2 }, hoverinfo: "skip", showlegend: false },
        { type: "scatter", mode: "lines", x: [rows[0].lo50, rows[0].hi50], y: [ys[0], ys[0]], line: { color: t.ruby, width: 9 }, hoverinfo: "skip", showlegend: false },
        { type: "scatter", mode: "markers", x: [med], y: [ys[0]], marker: { size: 13, color: t.surface, line: { width: 3, color: t.ruby } },
          hovertemplate: `previsto: mediana %{x:.1f} nm<br>50 %: ${nf(ex(1), 1)}–${nf(ex(3), 1)} · 90 %: ${nf(ex(0), 1)}–${nf(ex(4), 1)} nm<extra></extra>`, showlegend: false }];
      const lit = rows.slice(1);
      if (lit.length) tr.push({ type: "scatter", mode: "markers", x: lit.map((r) => r.m), y: ys.slice(1),
        error_x: { type: "data", symmetric: false, array: lit.map((r) => r.hi - r.m), arrayminus: lit.map((r) => r.m - r.lo), color: t.ink2, thickness: 1.4, width: 4 },
        marker: { size: lit.map((r) => 6 + 3 * Math.log10(r.n)), color: t.cat[0], line: { width: 1.5, color: t.surface } },
        customdata: lit.map((r) => [r.lo, r.hi, r.n]), hovertemplate: "%{y}<br>mediana %{x:.1f} nm · 10–90 %: %{customdata[0]:.1f}–%{customdata[1]:.1f}<extra></extra>", showlegend: false });
      plot("pr-forest", tr, { xaxis: { type: "log", title: { text: "tamanho relatado (nm)" }, tickvals: [1, 2, 5, 10, 20, 50, 100, 200], range: [0, Math.log10(300)] },
        yaxis: { autorange: "reversed", automargin: true }, margin: { l: 250 },
        shapes: [{ type: "rect", xref: "x", yref: "paper", x0: 0.8 * tg, x1: 1.2 * tg, y0: 0, y1: 1, fillcolor: hexA(t.dark ? "#e0b45c" : "#b8862a", 0.2), line: { width: 0 }, layer: "below" }] });
      // cor e LSPR
      const O = A.optics, lc = O.lspr_curve, lam = interp(Math.log(med), lc.d.map(Math.log), lc.lambda), G = goldColors();
      const gi = O.d.reduce((b, d, i) => (Math.abs(Math.log(d / med)) < Math.abs(Math.log(O.d[b] / med)) ? i : b), 0), col = G.cols[gi];
      $("#pr-cuv").style.setProperty("--col", col);
      $("#pr-cuv-t").innerHTML = `<b>${nf(lam, 0)} nm</b><span>LSPR esperado (Mie) para ${nf(med, med < 10 ? 1 : 0)} nm</span><br><span class="hex">${col}</span>`;
      const lamLo = interp(Math.log(ex(1)), lc.d.map(Math.log), lc.lambda), lamHi = interp(Math.log(ex(3)), lc.d.map(Math.log), lc.lambda);
      $("#pr-read").innerHTML = `<p>Na faixa de 50 % o pico fica entre ${nf(Math.min(lamLo, lamHi), 0)} e ${nf(Math.max(lamLo, lamHi), 0)} nm. ` +
        (st.morph === "rod" ? "Para bastões, o Mie de esferas não vale: o modo longitudinal aparece no vermelho/IV próximo. " : st.morph === "clu" || med < 3 ? "Abaixo de ~2 nm não há plásmon: a cor vem de transições moleculares (aglomerados). " : "") +
        (same && same.n >= 10 && Math.abs(Math.log(same.median / med)) > Math.log(2) ? `<b>Atenção:</b> as ${ni(same.n)} sínteses com esta mesma receita têm mediana ${nf(same.median, 1)} nm, longe da previsão; o modelo suaviza combinações raras de reagentes, então para esta receita confie mais no relato direto. ` : "") +
        `O intervalo de 90 % cobre um fator ×${nf(ex(4) / ex(0), 0)}: a receita, sozinha, não fixa o tamanho — razões molares, pH e ordem de adição, que as bases não registram, decidem o resto.</p>`;
      // e se? trocas de um item
      const al = alternatives(st).map(([lab, s2]) => [lab, pTarget(dist(vec(s2)), tg) - pt]).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1])).slice(0, 10).reverse();
      plot("pr-whatif", [{ type: "bar", orientation: "h", y: al.map((a) => a[0]), x: al.map((a) => 100 * a[1]),
        marker: { color: al.map((a) => (a[1] > 0 ? t.cat[2] : t.cat[1])) }, hovertemplate: "%{y}: %{x:+.1f} pontos percentuais<extra></extra>" }],
      { xaxis: { title: { text: `variação em P(alvo ± 20 %) (pontos percentuais; hoje ${nf(100 * pt, 0)} %)` }, zeroline: true, zerolinecolor: t.ink },
        yaxis: { automargin: true }, margin: { l: 200 }, showlegend: false });
      // temperatura
      const Ts = lin(0, 300, 31), DT = Ts.map((T) => dist(vec({ ...st, T })));
      const band = (i, j, op, name) => [
        { type: "scatter", mode: "lines", x: Ts, y: DT.map((d) => Math.exp(d.v[j])), line: { width: 0 }, hoverinfo: "skip", showlegend: false },
        { type: "scatter", mode: "lines", name, x: Ts, y: DT.map((d) => Math.exp(d.v[i])), fill: "tonexty", fillcolor: hexA(t.cat[0], op), line: { width: 0 }, hoverinfo: "skip" }];
      plot("pr-temp", [...band(0, 4, t.dark ? 0.14 : 0.1, "90 %"), ...band(1, 3, t.dark ? 0.28 : 0.22, "50 %"),
        { type: "scatter", mode: "lines", name: "mediana", x: Ts, y: DT.map((d) => Math.exp(d.v[2])), line: { color: t.cat[0], width: 2.4 }, hovertemplate: "%{x} °C: mediana %{y:.1f} nm<extra></extra>" },
        ...(st.T == null ? [] : [{ type: "scatter", mode: "markers", x: [st.T], y: [med], marker: { size: 11, color: t.ruby, line: { width: 2, color: t.surface } }, hoverinfo: "skip", showlegend: false }])],
      { xaxis: { title: { text: "temperatura de síntese (°C)" } }, yaxis: { type: "log", title: { text: "tamanho (nm)" }, tickvals: [1, 2, 5, 10, 20, 50, 100, 200] } });
      // tabela
      const tbl = (same ? [{ r: same, score: 1 }] : []).concat(sim);
      $("#pr-tbl").innerHTML = "<thead><tr><th>Receita (diferença para a sua)</th><th class='num'>Sínteses</th><th class='num'>Artigos</th><th class='num'>Mediana (nm)</th><th class='num'>10–90 % (nm)</th><th>Exemplos</th></tr></thead><tbody>" +
        tbl.map(({ r }) => `<tr><td>${esc(describe(r, sg))}</td><td class="num">${ni(r.n)}</td><td class="num">${ni(r.n_art)}</td><td class="num">${nf(r.median, 1)}</td><td class="num">${nf(r.q10, 1)}–${nf(r.q90, 1)}</td><td class="refs">${r.ex.map(link).join("<br>")}</td></tr>`).join("") + "</tbody>";
    }
    // design inverso: receitas publicadas (n ≥ 5) × 3 temperaturas, ordenadas por P(alvo ± 20 %)
    const fromSig = (sg, base) => ({ ...base, red: RED.filter((_, j) => sg[j] === "1"), cap: CAP.filter((_, j) => sg[10 + j] === "1"), seed: +sg[19],
      morph: sg[21] === "1" ? "rod" : sg[22] === "1" ? "clu" : sg[20] === "1" ? "oth" : "sph" });
    const cand = recs.filter((r) => r.n >= 5);
    let invRows = [];
    function inverse() {
      const st = state(), tg = fromV(+$("#pr-target").value), rows = [];
      cand.forEach((r) => [25, 60, 100].forEach((T) => { const s2 = fromSig(r.sig, { ...st, T }), D = dist(vec(s2));
        rows.push({ r, T, s2, p: pTarget(D, tg), med: Math.exp(D.v[2]) }); }));
      const best = new Map();                                    // a melhor temperatura de cada receita
      rows.forEach((x) => { const b = best.get(x.r.sig); if (!b || x.p > b.p) best.set(x.r.sig, x); });
      invRows = [...best.values()].sort((a, b) => b.p - a.p).slice(0, 8);
      const words = (s2) => [...s2.red, ...s2.cap].join(" + ") + (s2.seed ? " · sementes" : "") + (s2.morph !== "sph" ? " · " + MORPH_TXT[s2.morph] : "");
      $("#pr-inv").innerHTML = `<thead><tr><th>#</th><th>Receita</th><th class='num'>T</th><th class='num'>P(alvo ${nf(tg, 0)} nm ± 20 %)</th><th class='num'>Mediana prevista</th><th class='num'>Relatado (mediana; 10–90 %)</th><th class='num'>Sínteses</th><th><span class="sr">Ação</span></th></tr></thead><tbody>` +
        invRows.map((x, i) => `<tr><td>${i + 1}</td><td>${esc(words(x.s2) || "sem reagente citado")}</td><td class="num">${x.T} °C</td><td class="num"><b>${nf(100 * x.p, 0)} %</b></td><td class="num">${nf(x.med, 1)} nm</td>` +
          `<td class="num">${nf(x.r.median, 1)} nm; ${nf(x.r.q10, 1)}–${nf(x.r.q90, 1)}</td><td class="num">${ni(x.r.n)}</td><td><button type="button" class="btn" data-k="${i}">Carregar</button></td></tr>`).join("") + "</tbody>";
    }
    $("#pr-inv").addEventListener("click", (e) => { const b = e.target.closest("button[data-k]"); if (!b) return; const s2 = invRows[+b.dataset.k].s2;
      $("#pr-red").querySelectorAll("input").forEach((x) => { x.checked = s2.red.includes(x.value); });
      $("#pr-cap").querySelectorAll("input").forEach((x) => { x.checked = s2.cap.includes(x.value); });
      setSeed(s2.seed); $("#pr-morph").value = s2.morph; $("#pr-T").value = s2.T; $("#pr-Tna").checked = false;
      $("#pr-presets").querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", "false"));
      draw(); $("#p-preditor").scrollIntoView({ behavior: "smooth" }); });
    const invT = throttle(inverse, 150);
    const drawF = perFrame(draw);
    ["#pr-target", "#pr-year"].forEach((id) => $(id).addEventListener("input", invT));
    ["#pr-src", "#pr-go"].forEach((id) => $(id).addEventListener("change", inverse));
    inverse();
    $("#pr-presets").addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) { load(+b.dataset.i); draw(); } });
    $("#pr-seed").addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) { setSeed(b.dataset.v); draw(); } });
    ["#pr-red", "#pr-cap", "#pr-morph", "#pr-Tna", "#pr-src", "#pr-go"].forEach((id) => $(id).addEventListener("change", draw));
    ["#pr-T", "#pr-year", "#pr-target"].forEach((id) => $(id).addEventListener("input", drawF));
    load(0);
    drawer(draw);
    $("#pr-val").innerHTML = "<thead><tr><th>Intervalo</th><th class='num'>Nominal</th><th class='num'>Sem conformal</th><th class='num'>Conformal: registros</th><th class='num'>Conformal: artigos novos</th><th class='num'>Ajuste Q (ln d)</th><th class='num'>Largura típica</th></tr></thead><tbody>" +
      ["50", "90"].map((k) => { const b = Bd[k]; return `<tr><td>${k} % (q ${nf(b.q_lo, 2)}–${nf(b.q_hi, 2)})</td><td class="num">${nf(100 * b.level, 0)} %</td><td class="num">${nf(100 * b.coverage_uncorrected, 1)} %</td><td class="num">${nf(100 * b.coverage_records, 1)} %</td><td class="num"><b>${nf(100 * b.coverage_articles, 1)} %</b></td><td class="num">${nf(b.Q, 3)}</td><td class="num">fator ×${nf(b.median_fold_width, 1)}</td></tr>`; }).join("") + "</tbody>";
    $("#pr-val-txt").innerHTML = `<p>Treinado em ${ni(P.n)} sínteses de ${ni(P.n_articles)} artigos. A cobertura por artigo novo bate com a nominal, então os intervalos são honestos. ` +
      `A largura também é um resultado: o intervalo de 90 % cobre um fator ×${nf(Bd["90"].median_fold_width, 0)} no tamanho. Com só o que os artigos registram (reagentes, rota, forma, temperatura), o tamanho é pouco determinado; ` +
      "é a variabilidade entre fontes que o projeto propõe medir e modelar com o contexto do lote.</p>";
  };

  /* ================================================================== guia completo */
  let GUIDE = null;
  const guide = () => (GUIDE = GUIDE || (window.AUGO_GUIDE ? window.AUGO_GUIDE(A, { nf, ni, esc, pf }) : null));
  let guideReveal = null;                                     // definida pelo INIT.guia
  // gerador pseudoaleatório com semente (as demonstrações dão o mesmo resultado a cada visita)
  const rng32 = (seed) => () => { seed |= 0; seed = (seed + 0x6D2B79F5) | 0; let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  // link "como ler" em cada gráfico e tabela que tem explicação no guia
  function addGuideLinks() {
    const G = guide(); if (!G) return;
    const icoG = '<svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="6.3" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M6.3 6.2a1.8 1.8 0 1 1 2.4 1.7c-.5.2-.7.6-.7 1.1M8 11.3v.2" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>';
    document.querySelectorAll(".panel:not(#p-guia) .card").forEach((card) => {
      const el = card.querySelector(".plot[id], table[id]"), head = card.querySelector(".card-h");
      if (!el || !head || !G.FIG[el.id]) return;
      let g = head.querySelector(".btns");
      if (!g) { g = document.createElement("div"); g.className = "btns"; head.appendChild(g); }
      g.insertAdjacentHTML("afterbegin", `<a class="icon-btn" href="#doc-${el.id}" aria-label="Como ler este gráfico (guia)">${icoG}<span>como ler</span></a>`);
    });
  }
  INIT.guia = function () {
    const G = guide(), main = $("#gd-main"), toc = [];
    if (!G) { main.innerHTML = "<p>Guia indisponível.</p>"; return; }
    const sec = (id, title, html, lvl = 1) => { toc.push([id, title, lvl]); return `<section class="gsec" id="${id}"><h3 class="gh">${title}</h3>${html}</section>`; };
    // cls "gs" = unidade de busca (some se não contiver o termo); cartões sem "gs" somem quando nenhuma unidade dentro deles casa
    const card = (id, title, html, extra = "", cls = "gs") => `<div class="card gcard ${cls}" id="${id}"><div class="card-h"><div><h3>${title}</h3>${extra}</div></div><div class="card-b pad prose">${html}</div></div>`;
    const tabName = (id) => (TABS.find((t) => t[0] === id) || [id, id])[1];
    const figTitle = (el) => { const c = el.closest(".card"), h = c && c.querySelector("h3"); if (!h) return el.id;
      const f = h.querySelector(".fig"); return h.textContent.replace(f ? f.textContent : "", "").trim(); };
    const KIND = { "2d": ["gráfico 2D", "Passe o mouse sobre pontos, barras ou linhas para ver os valores exatos. Arraste para ampliar uma região; duplo clique volta à vista inteira. Clique num item da legenda para escondê-lo (duplo clique mostra só ele). No cartão, <b>dados</b> mostra a tabela, copia o CSV e baixa o PNG; <b>ampliar</b> abre em tela cheia."],
      "3d": ["gráfico 3D", "Arraste para girar. Para aproximar, use o botão de zoom da barra do gráfico (no celular, a pinça); o botão da casinha volta à vista inicial. Passe o mouse para ler as três coordenadas. A roda do mouse rola a página, de propósito, para você não ficar preso no gráfico."],
      table: ["tabela", "Role para o lado se a tabela não couber na tela. Links (DOI, \"carregar\") são clicáveis; o negrito destaca o resultado principal ou o que passou no critério."],
      html: ["painel", "Passe o mouse ou clique nos elementos; os textos, números e cores são recalculados dos dados ao abrir a página."],
      svg: ["diagrama", "Diagrama desenhado a partir da teoria e dos resultados; os valores nas setas vêm das análises."] };
    const cfor = {};                                                    // figura → conceitos que a explicam
    G.CONCEPTS.forEach((c) => (c.where || []).forEach((w) => { (cfor[w] = cfor[w] || []).push(c); }));
    const target = (id) => (G.FIG[id] ? "#doc-" + id : G.KPI[id] ? "#gk-" + id : null);
    const chips = (list) => `<div class="gchips">${list.join("")}</div>`;
    const symSvg = (k_) => `<svg viewBox="0 0 48 20" class="gsy" role="img" aria-label="${k_}">${{ dot: '<circle cx="24" cy="10" r="6" class="f"/>', ring: '<circle cx="24" cy="10" r="5.5" class="o"/>',
      diamond: '<path d="M24 3l7 7-7 7-7-7z" class="f"/>', line: '<path d="M4 10h40" class="l"/>', dash: '<path d="M4 10h40" class="l" stroke-dasharray="7 5"/>',
      dotted: '<path d="M4 10h40" class="l" stroke-dasharray="1.5 4" stroke-linecap="round"/>', band: '<rect x="4" y="4" width="40" height="12" rx="2" class="b"/><path d="M4 10h40" class="l"/>',
      err: '<path d="M8 10h32M8 5v10M40 5v10" class="l"/><circle cx="24" cy="10" r="4" class="f"/>' }[k_] || ""}</svg>`;
    const swatch = (c) => (c === "seq" ? `<i class="gsw" data-c="seq"></i>` : `<i class="gsw" data-c="${c}"></i>`);
    let html = `<div class="gbar" id="gd-bar" role="search"><label class="gsearch"><span class="sr">Buscar no guia</span>` +
      `<svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="7" cy="7" r="4.6" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M10.4 10.4L14 14" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>` +
      `<input type="search" id="gd-q" placeholder="buscar no guia: bootstrap, cor, Fig. 4.9…" autocomplete="off"></label>` +
      `<div class="seg" id="gd-lvl" role="group" aria-label="Nível de detalhe"><button type="button" aria-pressed="true" data-v="full">completo</button><button type="button" aria-pressed="false" data-v="basic">básico</button></div>` +
      `<button type="button" class="btn ghost" id="gd-open">expandir figuras</button><button type="button" class="btn ghost" id="gd-close">recolher</button>` +
      `<span class="gcount" id="gd-count" role="status" aria-live="polite"></span><div class="gprog" aria-hidden="true"><i id="gd-prog"></i></div></div>`;
    /* ---------- parte 1: comece aqui */
    html += sec("g-start", "1. Comece aqui",
      card("g-what", "O que é este site, em um minuto",
        `<p>Este painel acompanha uma pesquisa de iniciação científica (FAPESP, UNESP de Araraquara) que quer usar <b>inteligência artificial</b> para decidir, experimento a experimento, como produzir <b>nanopartículas de ouro sobre óxido de grafeno</b> com o tamanho e a cor desejados, mesmo quando a matéria-prima muda de um lote para outro.</p>` +
        `<p>Enquanto as sínteses do projeto não ficam prontas, o site aplica os métodos da proposta a <b>dados experimentais reais e públicos</b>: ${ni(A.overview.kpis.literature_records)} sínteses de ouro descritas em ${ni(A.overview.kpis.literature_dois)} artigos, cinco campanhas de laboratórios automatizados, a emissão de ${ni(A.overview.kpis.aunc_entries)} nanoaglomerados, imagens de difração de raios X e as propriedades ópticas medidas do ouro. Nada vem de simulação.</p>` +
        `<div class="gdiag">${svgPipeline()}</div><p class="muted">Esquema do fluxo: dos dados públicos às análises, ao site e às decisões do projeto.</p>` +
        `<p><b>Como usar este guia.</b> Leia a parte 1 para se orientar; a parte 2 explica os conceitos (com exemplos que você pode mexer); a parte 3 percorre cada aba e cada figura; as partes 4 a 7 trazem as fórmulas, como tudo foi feito, perguntas frequentes e o glossário. A busca no topo filtra tudo; <b>básico</b> esconde fórmulas e detalhes de cálculo.</p>`) +
      card("g-tour", "Roteiro de 10 minutos", `<p>Para quem tem pouco tempo: nove paradas, na ordem, que contam a história inteira. Cada uma leva ao gráfico no painel e à explicação aqui.</p><ol class="gtour">` +
        G.TOUR.map(([tab, fid, min, txt]) => `<li class="gs"><span class="gt-tab">${ico(tab, "gt-ico")} ${esc(tabName(tab))} · ${min} min</span><span>${txt}</span><span class="gt-go"><a href="#${fid}">ver no painel →</a> <a href="#doc-${fid}">como ler</a></span></li>`).join("") + "</ol>") +
      card("g-nav", "Como navegar",
        `<div class="gsteps">` + [["Menu lateral", "As abas seguem as etapas da proposta: Panorama, Dados, Modelos, Decisão e Projeto. O ponto colorido mostra o estado de cada aba (verde = dados experimentais; amarelo = parcial; cinza = aguarda o laboratório)."],
          ["Ficha de cada aba", "No topo de cada aba, três linhas resumem tudo: <b>Dados</b> (de onde veio), <b>Método</b> (o que foi feito) e <b>Achado</b> (o resultado)."],
          ["Figuras numeradas", "Cada gráfico tem um número (Fig. 4.9e = seção 4.9 da proposta, 5º gráfico da aba). O número é um link: clicar nele faz o endereço da página apontar para aquela figura, pronto para copiar."],
          ["Botões dos gráficos", "<b>como ler</b> abre a explicação aqui no guia; <b>dados</b> mostra a tabela, copia o CSV e baixa a figura em PNG; <b>ampliar</b> abre em tela cheia (Esc fecha)."],
          ["Interagir", "Passe o mouse para ver os valores; arraste para girar os gráficos 3D ou ampliar os 2D (duplo clique volta); clique na legenda para esconder uma série."],
          ["Buscar", "Ctrl K (ou /) abre a busca de qualquer gráfico ou seção do site; a busca no topo deste guia filtra o próprio guia."],
          ["Tema e impressão", "O botão no topo troca entre claro e escuro; Ctrl P imprime (ou salva em PDF) só a aba aberta, com as figuras do guia expandidas."]]
          .map(([t, d], i) => `<div class="gstep"><span class="n">${i + 1}</span><div><b>${t}</b><p>${d}</p></div></div>`).join("") + "</div>") +
      card("g-anatomy", "Como ler qualquer gráfico",
        `<div class="gdiag">${svgAnatomy()}</div><ol class="glist"><li><b>Título e legenda</b> dizem o que está sendo comparado; leia antes de olhar os pontos.</li><li><b>Eixos</b>: confira a unidade e se a escala é linear ou logarítmica (marcas 1, 10, 100 = log).</li><li><b>Ponto</b> = uma medida ou estimativa; <b>barra de erro</b> = a incerteza (normalmente IC 95 %).</li><li><b>Faixa sombreada</b> = região de incerteza ou região de referência (o alvo, a faixa da literatura).</li><li><b>Linha de referência</b> (pontilhada) = \"nenhum efeito\", \"previsão perfeita\" ou \"calibração perfeita\".</li><li>Desconfie de diferenças menores que a barra de erro.</li></ol>`) +
      card("g-colors", "Cores e símbolos usados em todo o site",
        `<p>As cores têm o mesmo significado em todas as abas, e nenhuma informação depende só da cor (há sempre legenda, rótulo ou forma).</p><div class="gpal">${G.PALETTE.map(([c, n, d]) => `<div class="gs">${swatch(c)}<div><b>${n}</b><p>${d}</p></div></div>`).join("")}</div>` +
        `<h4 class="gk">Símbolos</h4><table class="gtbl gsym"><tbody>${G.SYMBOLS.map(([s, d]) => `<tr class="gs"><th>${symSvg(s)}</th><td>${d}</td></tr>`).join("")}</tbody></table>`, "", "") +
      card("g-keys", "Atalhos de teclado e gestos", `<table class="gtbl"><tbody>${G.KEYS.map(([k_, d]) => `<tr class="gs"><th><kbd>${k_}</kbd></th><td>${d}</td></tr>`).join("")}</tbody></table>`, "", ""));
    /* ---------- parte 2: conceitos */
    const groups = [...new Set(G.CONCEPTS.map((c) => c.group))];
    html += sec("g-concepts", "2. Conceitos, com exemplos interativos",
      `<p class="gintro">${G.CONCEPTS.length} conceitos de química, física e estatística, cada um com uma comparação do dia a dia, a conta em palavras, onde aparece no site, o erro de leitura mais comum e, quase sempre, um exemplo que você pode mexer. Todos os exemplos usam os dados reais do site; os esquemas desenhados estão marcados como esquema.</p>` +
      groups.map((gname) => `<h4 class="gsub">${gname}</h4>` + G.CONCEPTS.filter((c) => c.group === gname).map((c) =>
        card(c.id, c.title, c.body +
          (c.analogy ? `<div class="gana"><b>Comparação.</b> ${c.analogy}</div>` : "") +
          (c.formula ? `<div class="gadv gform1"><b>A conta.</b> ${c.formula}</div>` : "") +
          (c.confuse ? `<div class="gwarn"><b>Confusão comum.</b> ${c.confuse}</div>` : "") +
          (c.where && c.where.length ? `<div class="gwhere"><span>Onde aparece:</span>${chips(c.where.map((w) => `<a class="gchip" href="${target(w) || "#" + w}">${esc(G.FIG[w] && G.FIG[w].title ? G.FIG[w].title : (G.KPI[w] ? G.KPI[w].title : w))}</a>`))}</div>` : "") +
          (c.demo ? `<div class="gdemo" id="demo-${c.demo}"></div>` : ""))).join("")).join(""));
    G.CONCEPTS.forEach((c) => toc.push([c.id, c.title, 2]));
    /* ---------- parte 3: aba por aba */
    const tabsDoc = TABS.filter(([id]) => id !== "guia" && G.TABS[id]), tabToc = [];
    let nFig = 0;
    html += sec("g-tabs", "3. Aba por aba, figura por figura",
      `<p class="gintro">Para cada aba: a pergunta que ela responde, para que serve, de onde vêm os dados, um roteiro de leitura, o que faz cada controle, o significado de cada indicador, os resultados e os limites. Depois, cada gráfico e tabela: a pergunta, os elementos, a leitura passo a passo, como interagir, um exemplo com os números atuais, os cuidados, os erros comuns e como foi calculado. Clique numa figura para abrir a explicação (ou use <b>expandir figuras</b> no topo).</p>` +
      tabsDoc.map(([id, , secn]) => {
        const T_ = G.TABS[id], panel = document.getElementById("p-" + id);
        const ids = [...panel.querySelectorAll("[id]")].map((e) => e.id).filter((x, i, a) => G.FIG[x] && a.indexOf(x) === i);
        const ctrls = T_.controls.length ? `<h4 class="gk">Controles: o que cada um faz</h4><table class="gtbl gctrl"><thead><tr><th>Controle</th><th>O que faz</th><th>Faixa e padrão</th></tr></thead><tbody>${T_.controls.map(([c, d, r]) => `<tr><th>${c}</th><td>${d}</td><td>${r || "—"}</td></tr>`).join("")}</tbody></table>` : "";
        const kpis_ = Object.entries(G.KPI).filter(([, K]) => K.tab === id).map(([kid, K]) => `<div class="gkpi" id="gk-${kid}"><h4 class="gk">${esc(K.title)}</h4><table class="gtbl"><thead><tr><th>Indicador</th><th>O que significa</th><th>Como é calculado e como ler</th></tr></thead><tbody>${K.items.map(([a, b, c]) => `<tr><th>${a}</th><td>${b}</td><td>${c}</td></tr>`).join("")}</tbody></table></div>`).join("");
        const flow = T_.flow && T_.flow.length ? `<h4 class="gk">Roteiro de leitura</h4><ol class="gflow">${T_.flow.map(([fid, txt]) => { const tg = fid && target(fid); return `<li>${txt}${tg ? ` <a href="${tg}">explicação ↓</a>` : ""}</li>`; }).join("")}</ol>` : "";
        const figIdx = [], figs = ids.map((fid) => {
          const F = G.FIG[fid], el = document.getElementById(fid), c = el && el.closest(".card"), lab = c && c.querySelector(".fig"), kd = KIND[F.kind] || KIND.html;
          const title = esc(F.title || (el ? figTitle(el) : fid)); nFig++;
          figIdx.push(`<a class="gchip" href="#doc-${fid}">${lab ? `<b>${lab.textContent}</b> ` : ""}${title}</a>`);
          const rel = (cfor[fid] || []).map((cc) => `<a class="gchip" href="#${cc.id}">${esc(cc.title)}</a>`);
          return `<details class="gfig gs" id="doc-${fid}"><summary><span class="gsum">${lab ? `<span class="fig">${lab.textContent}</span>` : ""}<span class="gft">${title}</span><span class="gkind">${kd[0]}</span></span><span class="gone">${F.one}</span></summary><div class="gfb">` +
            (F.question ? `<p class="gq"><b>A pergunta que responde.</b> ${F.question}</p>` : "") +
            `<div class="gcols"><div><h5>O que mostra</h5><p>${F.what}</p></div>` +
            (F.elements && F.elements.length ? `<div><h5>Elementos do gráfico</h5><table class="gtbl gel"><tbody>${F.elements.map(([a, b]) => `<tr><th>${a}</th><td>${b}</td></tr>`).join("")}</tbody></table></div>` : "") + `</div>` +
            (F.steps && F.steps.length ? `<h5>Como ler, passo a passo</h5><ol class="gnum">${F.steps.map((s) => `<li>${s}</li>`).join("")}</ol>` : "") +
            `<h5>Como interagir</h5><p>${kd[1]}</p>` +
            (F.example ? `<div class="gex"><b>Exemplo com os dados atuais.</b> ${F.example}</div>` : "") +
            (F.caution ? `<div class="gwarn"><b>Cuidado.</b> ${F.caution}</div>` : "") +
            (F.mistakes && F.mistakes.length ? `<div class="gmis"><b>Erros comuns de leitura</b><ul>${F.mistakes.map((m) => `<li>${m}</li>`).join("")}</ul></div>` : "") +
            `<div class="gadv gmeth"><h5>Como foi calculado</h5><p>${F.method}</p>${F.code ? `<p class="gcode"><span>Código:</span> ${esc(F.code)}</p>` : ""}</div>` +
            (rel.length ? `<div class="gwhere"><span>Conceitos para entender:</span>${chips(rel)}</div>` : "") +
            (c && c.id ? `<p class="gfoot"><a class="go" href="#${c.id}">ver no painel →</a></p>` : "") + "</div></details>";
        }).join("");
        tabToc.push(["g-tab-" + id, tabName(id), 2]);
        return `<div class="card gcard gtab" id="g-tab-${id}"><div class="card-h"><div><span class="eyebrow">${secn ? "§" + secn + " · " : ""}aba</span><h3>${ico(id, "gt-ico")} ${esc(tabName(id))}</h3></div><a class="icon-btn" href="#${id}">abrir a aba →</a></div>` +
          `<div class="card-b pad prose"><div class="gs gtabi">${T_.question ? `<p class="gq gqbig">${T_.question}</p>` : ""}` +
          `<div class="gcols"><div><h4 class="gk">Para que serve</h4><p>${T_.purpose}</p></div>${T_.why ? `<div><h4 class="gk">Por que importa para o projeto</h4><p>${T_.why}</p></div>` : ""}</div>` +
          `<h4 class="gk">De onde vêm os dados</h4><p>${T_.data}</p>${flow}${ctrls}${kpis_}` +
          (T_.results && T_.results.length ? `<h4 class="gk">Resultados principais (números atuais)</h4><ul class="glist">${T_.results.map((r) => `<li>${r}</li>`).join("")}</ul>` : "") +
          `<div class="gkey"><b>A mensagem principal.</b> ${T_.take}</div>` +
          (T_.limits && T_.limits.length ? `<div class="gwarn"><b>Limites desta aba.</b><ul>${T_.limits.map((x) => `<li>${x}</li>`).join("")}</ul></div>` : "") +
          (T_.try && T_.try.length ? `<div class="gtry"><b>Experimente</b><ol>${T_.try.map((x) => `<li>${x}</li>`).join("")}</ol><a class="icon-btn" href="#${id}">abrir a aba →</a></div>` : "") + `</div>` +
          (figs ? `<h4 class="gk">Figuras e tabelas desta aba (${ids.length})</h4>${chips(figIdx)}${figs}` : "") + `</div></div>`;
      }).join(""));
    toc.push(...tabToc);
    /* ---------- parte 4: fórmulas */
    html += `<div class="gadv">` + sec("g-formulas", "4. Fórmulas, em símbolos e em palavras",
      card("g-form", `As ${G.FORMULAS.length} contas por trás do site`, `<p>Para quem quer conferir: cada fórmula usada nas análises, com a leitura em palavras e a aba onde aparece. Nada aqui é necessário para ler os gráficos.</p>` +
        `<div class="tbl-wrap" tabindex="0" role="region" aria-label="Fórmulas"><table class="gtbl gformt"><thead><tr><th>Nome</th><th>Fórmula</th><th>Em palavras</th><th>Onde</th></tr></thead><tbody>${G.FORMULAS.map(([n, f, w, o]) => `<tr class="gs"><th>${n}</th><td class="gfx">${f}</td><td>${w}</td><td>${o}</td></tr>`).join("")}</tbody></table></div>`, "", "")) + `</div>`;
    /* ---------- parte 5: como foi feito */
    html += sec("g-how", "5. Como tudo foi feito",
      card("g-pipe", "Princípios e etapas", `<div class="gsteps">${G.HOW.map(([t, d], i) => `<div class="gstep gs"><span class="n">${i < 4 ? "★" : i - 3}</span><div><b>${t}</b><p>${d}</p></div></div>`).join("")}</div>`, "", "") +
      card("g-dec", "Registro de decisões: o que foi testado, adotado e rejeitado",
        `<p>Toda escolha de método seguiu um critério fixado antes de olhar o resultado e avaliado em dados separados. Esta é a lista completa, inclusive do que não funcionou.</p><div class="tbl-wrap" tabindex="0" role="region" aria-label="Decisões"><table class="gtbl"><thead><tr><th>Decisão</th><th>O que foi comparado</th><th>Resultado</th></tr></thead><tbody>${G.DECISIONS.map(([a, b, c]) => `<tr class="gs"><th>${a}</th><td>${b}</td><td>${c}</td></tr>`).join("")}</tbody></table></div>`, "", "") +
      `<div class="gadv">` + card("g-code", "Mapa do código: de cada aba ao programa que a calcula",
        `<p>Onde está cada conta, para quem quiser conferir ou reproduzir. As análises em Python ficam em <span class="mono">code/webapp/analyses.py</span>; as contas feitas ao vivo no navegador, em <span class="mono">code/webapp/app.js</span>.</p><div class="tbl-wrap" tabindex="0" role="region" aria-label="Mapa do código"><table class="gtbl"><thead><tr><th>Aba</th><th>Análise (Python)</th><th>No navegador</th><th>Dados</th></tr></thead><tbody>${G.CODEMAP.map(([a, b, c, d]) => `<tr class="gs"><th>${a}</th><td class="mono">${b}</td><td>${c}</td><td class="mono">${d}</td></tr>`).join("")}</tbody></table></div>`, "", "") + `</div>` +
      card("g-time", "Linha do tempo do trabalho", `<ol class="gtime">${G.TIMELINE.map(([d, t, x]) => `<li class="gs"><time>${d}</time><b>${t}</b><p>${x}</p></li>`).join("")}</ol>`, "", "") +
      card("g-lim", "Limites: o que estes resultados NÃO dizem", `<ul class="glist">${G.LIMITS.map((x) => `<li class="gs">${x}</li>`).join("")}</ul>`, "", ""));
    /* ---------- parte 6: perguntas frequentes */
    html += sec("g-faq", "6. Perguntas frequentes",
      card("g-faqs", `${G.FAQ.length} perguntas e respostas`, G.FAQ.map(([q, a]) => `<details class="gfaq gs"><summary>${q}</summary><p>${a}</p></details>`).join(""), "", ""));
    /* ---------- parte 7: glossário e referências */
    const GL = G.GLOSS.slice().sort((a, b) => a[0].localeCompare(b[0], "pt", { sensitivity: "base" }));
    const letter = (t) => t.normalize("NFD").replace(/[̀-ͯ]/g, "").charAt(0).toUpperCase();
    const letters = [...new Set(GL.map(([t]) => letter(t)))].filter((c) => /[A-Z]/.test(c));
    html += sec("g-gloss", "7. Glossário e referências",
      card("g-glossary", `Glossário (${GL.length} termos)`, `<nav class="gabc" aria-label="Letras do glossário">${letters.map((l) => `<a href="#gl-${l}">${l}</a>`).join("")}</nav><dl class="gglos" id="gd-gl">` +
        GL.map(([t, d], i) => { const l = letter(t), first = i === 0 || letter(GL[i - 1][0]) !== l; return `<div class="gs"${first && /[A-Z]/.test(l) ? ` id="gl-${l}"` : ""}><dt>${t}</dt><dd>${d}</dd></div>`; }).join("") + "</dl>", "", "") +
      card("g-refs", `Referências (${G.REFS.reduce((a, [, r]) => a + r.length, 0)})`, G.REFS.map(([g, rs]) => `<h4 class="gk">${g}</h4><ol class="glist">${rs.map((r) => `<li class="gs">${esc(r)}</li>`).join("")}</ol>`).join(""), "", ""));
    main.innerHTML = html;
    $("#gd-toc").innerHTML = `<b>Sumário</b><ol>${toc.map(([id, t, l]) => `<li class="l${l}"><a href="#${id}" data-t="${id}">${id.startsWith("g-tab-") ? ico(id.slice(6), "gt-ico") + " " : ""}${esc(t.replace(/^\d+\.\s*/, ""))}</a></li>`).join("")}</ol>`;
    const nWords = main.textContent.split(/\s+/).filter(Boolean).length;
    $("#fi-guia").innerHTML = `<div><dt>Dados</dt><dd>os mesmos do site; cada número citado aqui é lido dos dados e acompanha as análises</dd></div><div><dt>Método</dt><dd>${G.CONCEPTS.length} conceitos com ${main.querySelectorAll(".gdemo").length} exemplos interativos, ${nFig} figuras e tabelas explicadas, ${Object.keys(G.KPI).length} fileiras de indicadores, ${G.FORMULAS.length} fórmulas, ${G.FAQ.length} perguntas, ${GL.length} termos</dd></div><div><dt>Achado</dt><dd>leitura guiada de todas as ${tabsDoc.length} abas, do zero (~${ni(Math.round(nWords / 1000) * 1000)} palavras, ~${ni(Math.round(nWords / 220 / 5) * 5)} min de leitura)</dd></div>`;
    // cores das amostras: seguem o tema
    drawer(() => { const t = T(); main.querySelectorAll(".gsw").forEach((s) => { const c = s.dataset.c;
      s.style.background = c === "seq" ? `linear-gradient(90deg, ${t.seqScale.map((x) => x[1]).join(", ")})` : c.startsWith("cat:") ? t.cat[+c.slice(4)] : c; }); });
    /* ---------- busca, nível, recolher/expandir, sumário ativo e progresso */
    const norm = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
    const units = [...main.querySelectorAll(".gs")], boxes = [...main.querySelectorAll(".gcard:not(.gs)")], secs = [...main.querySelectorAll(".gsec")];
    const utext = units.map((u) => norm(u.textContent));
    const search = (raw) => {
      const q = norm(raw.trim()); let n = 0;
      units.forEach((u, i) => { const hit = !q || utext[i].includes(q); u.hidden = !hit; if (hit && q) { n++; if (u.tagName === "DETAILS") u.open = true; } });
      boxes.forEach((b) => { b.hidden = !!q && !b.querySelector(".gs:not([hidden])"); });
      secs.forEach((s) => { s.hidden = !!q && !s.querySelector(".gcard:not([hidden])"); });
      main.querySelectorAll(".gsub").forEach((h_) => { let x = h_.nextElementSibling, any = false;          // título de grupo sem cartões visíveis some
        while (x && !x.classList.contains("gsub")) { if (x.classList.contains("gcard") && !x.hidden) any = true; x = x.nextElementSibling; } h_.hidden = !!q && !any; });
      $("#gd-count").textContent = q ? (n ? `${ni(n)} trecho${n > 1 ? "s" : ""} com \"${raw.trim()}\"` : "nada encontrado") : "";
    };
    $("#gd-q").addEventListener("input", throttle(() => search($("#gd-q").value), 120));
    let lvl = "full"; try { lvl = localStorage.getItem("augo-guia-lvl") || "full"; } catch (e) { /* armazenamento indisponível */ }
    const setLvl = (x) => { lvl = x; main.classList.toggle("basic", x === "basic"); $("#gd-lvl").querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", b.dataset.v === x ? "true" : "false"));
      try { localStorage.setItem("augo-guia-lvl", x); } catch (e) { /* armazenamento indisponível */ } };
    setLvl(lvl); segmented("#gd-lvl", setLvl);
    // um link para dentro do guia (#doc-…, sumário) precisa achar o alvo visível: limpa a busca, volta ao nível completo e abre a figura
    guideReveal = (el) => {
      if (el.closest("#gd-main [hidden]")) { $("#gd-q").value = ""; search(""); }
      if (el.closest(".gadv") && lvl === "basic") setLvl("full");
      const d = el.tagName === "DETAILS" ? el : el.closest("details"); if (d) d.open = true;
    };
    $("#gd-open").addEventListener("click", () => main.querySelectorAll("details.gfig").forEach((d) => { d.open = true; }));
    $("#gd-close").addEventListener("click", () => main.querySelectorAll("details.gfig, details.gfaq").forEach((d) => { d.open = false; }));
    window.addEventListener("beforeprint", () => { if (current === "guia") main.querySelectorAll("details").forEach((d) => { d.open = true; }); });
    const links = [...$("#gd-toc").querySelectorAll("a[data-t]")], tgt = links.map((a) => document.getElementById(a.dataset.t));
    const onScroll = throttle(() => {
      if (current !== "guia") return;
      const top = (document.querySelector(".top") || { offsetHeight: 60 }).offsetHeight + 40;
      let k = 0; tgt.forEach((el, i) => { if (el && !el.closest("[hidden]") && el.getBoundingClientRect().top < top) k = i; });
      links.forEach((a, i) => a.classList.toggle("on", i === k));
      const r = main.getBoundingClientRect(), span = Math.max(1, r.height - innerHeight);
      $("#gd-prog").style.width = `${Math.max(0, Math.min(100, (-r.top + top) / span * 100))}%`;
    }, 100);
    window.addEventListener("scroll", onScroll, { passive: true }); onScroll();
    guideDemos();
    addExpanders(main);
  };
  /* ---------- esquemas desenhados (não são dados) */
  function svgPipeline() {
    const box = (x, y, w, t1, t2, c) => `<g transform="translate(${x},${y})"><rect width="${w}" height="64" rx="12" class="gb ${c || ""}"/><text x="${w / 2}" y="27" class="gt1">${t1}</text><text x="${w / 2}" y="46" class="gt2">${t2}</text></g>`;
    const arr = (x1, x2, y) => `<path d="M${x1} ${y}H${x2}" class="ga" marker-end="url(#gar)"/>`;
    return `<svg viewBox="0 0 980 120" role="img" aria-label="Esquema: dados públicos, análises, site, decisões do projeto"><defs><marker id="gar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" class="gah"/></marker></defs>` +
      box(4, 28, 200, "Dados públicos", "artigos · campanhas · física") + arr(208, 248, 60) + box(252, 28, 200, "Curadoria", "reagentes · filtros físicos") + arr(456, 496, 60) +
      box(500, 28, 200, "Análises", "Mie · GP · causal · SHAP") + arr(704, 744, 60) + box(748, 28, 228, "Este site e as decisões", "o que testar a seguir", "gbk") +
      `<text x="490" y="14" class="gt2">esquema</text></svg>`;
  }
  function svgAnatomy() {
    return `<svg viewBox="0 0 800 300" role="img" aria-label="Esquema de um gráfico com eixos, pontos, barra de erro, faixa e legenda"><g class="gax"><path d="M70 30V250H610"/></g>` +
      `<rect x="70" y="110" width="540" height="60" class="gband"/><path d="M70 140H610" class="gref"/>` +
      [[150, 120, 20], [260, 95, 28], [370, 150, 16], [480, 75, 22]].map(([x, y, e]) => `<path d="M${x} ${y - e}V${y + e}M${x - 6} ${y - e}H${x + 6}M${x - 6} ${y + e}H${x + 6}" class="gerr"/><circle cx="${x}" cy="${y}" r="7" class="gpt"/>`).join("") +
      `<text x="340" y="285" class="gt2">eixo x: o que varia (unidade; linear ou log)</text><text x="22" y="140" class="gt2" transform="rotate(-90 22 140)">eixo y: o resultado</text>` +
      [[1, 260, 60, "ponto = estimativa"], [2, 290, 120, "barra = incerteza (IC 95 %)"], [3, 560, 128, "linha pontilhada = referência"], [4, 560, 186, "faixa = região de referência"]]
        .map(([n, x, y, t]) => `<g class="gcall"><circle cx="${x}" cy="${y}" r="11"/><text x="${x}" y="${y + 4}">${n}</text><text x="${x + 18}" y="${y + 4}" class="gl">${t}</text></g>`).join("") +
      `<text x="790" y="20" class="gt2" style="text-anchor:end">esquema</text></svg>`;
  }
  /* ---------- demonstrações interativas (dados reais) */
  function guideDemos() {
    const D_ = (id) => document.getElementById("demo-" + id);
    const wrap = (id, ctl, plots, txt) => { const el = D_(id); if (!el) return null;
      el.innerHTML = `${ctl ? `<div class="controls gctl">${ctl}</div>` : ""}${plots.map((p) => `<div class="plot ${p[1] || ""}" id="${p[0]}"></div>`).join("")}<div class="prose gdtxt" id="${id}-txt">${txt || ""}</div>`; return el; };
    // escala dos objetos (esquema)
    { const el = D_("scale");
      if (el) { const items = [[0.29, "átomo de ouro"], [2, "nanoaglomerado (AuNC)"], [20, "AuNP alvo do projeto"], [100, "vírus"], [2000, "bactéria"], [80000, "fio de cabelo"]];
        const x = (d) => 40 + (Math.log10(d) + 1) / 6 * 900;
        el.innerHTML = `<svg viewBox="0 0 980 150" role="img" aria-label="Régua de tamanhos em escala logarítmica, do átomo ao fio de cabelo"><path d="M40 80H940" class="gax2"/>` +
          [0.1, 1, 10, 100, 1000, 10000, 100000].map((d) => `<path d="M${x(d)} 74V86" class="gax2"/><text x="${x(d)}" y="104" class="gt2">${d >= 1000 ? nf(d / 1000, 0) + " µm" : nf(d, d < 1 ? 1 : 0) + " nm"}</text>`).join("") +
          items.map(([d, t], i) => `<circle cx="${x(d)}" cy="80" r="7" class="${d === 20 ? "gpt2" : "gpt"}"/><text x="${x(d)}" y="${i % 2 ? 130 : 50}" class="gl2">${t}</text><path d="M${x(d)} ${i % 2 ? 88 : 72}V${i % 2 ? 118 : 56}" class="gtick"/>`).join("") +
          `<text x="940" y="20" class="gt2" style="text-anchor:end">escala logarítmica · esquema</text></svg><p class="muted">Cada marca é 10× a anterior. Uma AuNP de 20 nm está para um fio de cabelo como uma bola de futebol está para um campo de 900 km.</p>`; } }
    // tamanho → espectro → cor
    { const O = A.optics, el = wrap("color", `<div class="ctl"><label for="gd-d">Diâmetro <output id="gd-d-o"></output></label><input type="range" id="gd-d" min="0" max="${O.d.length - 1}" step="1" value="${O.d.findIndex((d) => d >= 20)}"></div><div class="cuvette" id="gd-cuv" role="img" aria-label="Cor da dispersão"></div>`, [["gd-spec", "short"]]);
      if (el) { const draw = () => { const t = T(), i = +$("#gd-d").value, d = O.d[i], row = O.C_ext[i], G = goldColors(), pk = peakOf(O.wl, row);
          $("#gd-d-o").textContent = `${nf(d, d < 10 ? 1 : 0)} nm`; $("#gd-cuv").style.setProperty("--col", G.cols[i]);
          plot("gd-spec", [{ type: "scatter", mode: "lines", x: O.wl, y: row, line: { color: t.cat[0], width: 2.4 }, fill: "tozeroy", fillcolor: hexA(G.cols[i], 0.35), hovertemplate: "λ = %{x} nm: %{y:.2f}<extra></extra>" }],
            { xaxis: { title: { text: "comprimento de onda (nm): violeta → vermelho" } }, yaxis: { title: { text: "extinção (máx. = 1)" }, range: [0, 1.05] }, showlegend: false,
              shapes: [{ type: "line", x0: pk, x1: pk, yref: "paper", y0: 0, y1: 1, line: { color: t.ink, width: 1, dash: "dot" } }],
              annotations: [{ x: pk, y: 1, yref: "paper", text: `pico ${nf(pk, 0)} nm`, showarrow: false, xanchor: "left", xshift: 6, font: { size: 11, color: t.ink } }] });
          $("#color-txt").innerHTML = `<p>${nf(d, d < 10 ? 1 : 0)} nm: pico em <b>${nf(pk, 0)} nm</b>. ${d < 3.5 ? "Quase não há pico: aglomerados muito pequenos não têm plásmon." : d < 30 ? "O ouro absorve o verde (~520 nm) e a dispersão parece vermelha (a cor complementar)." : d < 80 ? "O pico vai para a direita e alarga: a cor puxa para o púrpura." : "Partículas grandes espalham muita luz; o pico fica largo e a cor, azul-acinzentada."}</p>`; };
        $("#gd-d").addEventListener("input", perFrame(draw)); drawer(draw); } }
    // nucleação e crescimento (esquema)
    { const el = D_("lamer");
      if (el) el.innerHTML = `<svg viewBox="0 0 980 240" role="img" aria-label="Esquema do modelo de LaMer: concentração de ouro reduzido ao longo do tempo, nucleação e crescimento">` +
        `<path d="M60 20V190H560" class="gax2"/><path d="M60 70H560" class="gref"/><text x="565" y="74" class="gl2" style="text-anchor:start">limite de nucleação</text>` +
        `<path d="M60 185C130 180 150 40 200 40S250 95 300 110S450 135 555 140" class="gcurve"/>` +
        `<rect x="160" y="22" width="95" height="168" class="gband"/><text x="207" y="210" class="gl2">nucleação</text><text x="110" y="210" class="gl2">redução</text><text x="420" y="210" class="gl2">crescimento</text>` +
        `<text x="20" y="105" class="gt2" transform="rotate(-90 20 105)">Au⁰ dissolvido</text><text x="310" y="228" class="gt2">tempo →</text>` +
        `<g transform="translate(700,34)"><text x="120" y="0" class="gl2">redutor forte (NaBH₄)</text>${Array.from({ length: 27 }, (_, i) => `<circle cx="${8 + (i % 9) * 28}" cy="${20 + Math.floor(i / 9) * 20}" r="5" class="gpt"/>`).join("")}<text x="120" y="86" class="gt2">muitos núcleos → partículas pequenas</text></g>` +
        `<g transform="translate(700,150)"><text x="120" y="0" class="gl2">redutor suave (citrato)</text>${[40, 120, 200].map((cx) => `<circle cx="${cx}" cy="32" r="16" class="gpt2"/>`).join("")}<text x="120" y="68" class="gt2">poucos núcleos → partículas maiores</text></g>` +
        `<text x="970" y="16" class="gt2" style="text-anchor:end">esquema qualitativo</text></svg>`; }
    // distribuição: média × mediana, escala log
    { const s = A.variability.turkevich.sizes_per_paper.filter((x) => x > 0), el = wrap("dist", `<div class="ctl ctl-auto"><span class="lbl" id="gd-sc-l">Escala do eixo</span><div class="seg" id="gd-sc" role="group" aria-labelledby="gd-sc-l"><button type="button" aria-pressed="true" data-v="log">logarítmica</button><button type="button" aria-pressed="false" data-v="lin">linear</button></div></div>`, [["gd-dist"]]);
      if (el) { let sc = "log"; const mean = s.reduce((a, b) => a + b, 0) / s.length, med = median(s), q1 = quant(s, 0.25), q3 = quant(s, 0.75);
        const draw = () => { const t = T(), lg = sc === "log", f = lg ? Math.log10 : (x) => x, lo = lg ? 0.4 : 0, hi = lg ? 2.2 : 150, nb = 40, w = (hi - lo) / nb, c = new Array(nb).fill(0);
          s.forEach((x) => { const j = Math.floor((f(x) - lo) / w); if (j >= 0 && j < nb) c[j]++; });
          const mids = c.map((_, j) => lo + (j + 0.5) * w), vl = (x, dash, lab, col) => ({ shape: { type: "line", x0: f(x), x1: f(x), yref: "paper", y0: 0, y1: 1, line: { color: col, width: 1.6, dash } }, ann: { x: f(x), y: 1, yref: "paper", text: lab, showarrow: false, textangle: -90, xanchor: "right", yanchor: "top", font: { size: 10, color: col } } });
          const L_ = [vl(med, "solid", `mediana ${nf(med, 1)}`, t.ink), vl(mean, "dash", `média ${nf(mean, 1)}`, t.ruby), vl(q1, "dot", "1º quartil", t.muted), vl(q3, "dot", "3º quartil", t.muted)];
          plot("gd-dist", [{ type: "bar", x: mids, y: c, width: w * 0.92, marker: { color: t.cat[0] }, customdata: mids.map((m) => (lg ? Math.pow(10, m) : m)), hovertemplate: "≈ %{customdata:.1f} nm: %{y} artigos<extra></extra>" }],
            { bargap: 0, showlegend: false, yaxis: { title: { text: "artigos" } }, shapes: L_.map((x) => x.shape), annotations: L_.map((x) => x.ann),
              xaxis: lg ? { title: { text: "tamanho (nm), escala log" }, tickvals: [0.477, 0.699, 1, 1.301, 1.699, 2], ticktext: ["3", "5", "10", "20", "50", "100"] } : { title: { text: "tamanho (nm), escala linear" } } });
          $("#dist-txt").innerHTML = `<p>${ni(s.length)} artigos com a receita de Turkevich, um tamanho por artigo. A <b>mediana (${nf(med, 1)} nm)</b> fica no meio; a <b>média (${nf(mean, 1)} nm)</b> é puxada para cima pelos poucos artigos com partículas grandes. Metade dos artigos está entre ${nf(q1, 1)} e ${nf(q3, 1)} nm (entre os quartis). Na escala linear a distribuição parece uma parede à esquerda com uma cauda longa; na log ela fica simétrica e legível.</p>`; };
        segmented("#gd-sc", (x) => { sc = x; draw(); }); drawer(draw); } }
    // bootstrap
    { const pool = A.variability.turkevich.sizes_per_paper, el = wrap("boot", `<div class="ctl"><label for="gd-n">Artigos na amostra <output id="gd-n-o"></output></label><input type="range" id="gd-n" min="5" max="400" step="5" value="30"></div><button type="button" class="btn" id="gd-redraw">sortear outra amostra</button>`, [["gd-boot", "short"]]);
      if (el) { let seed = 7, bands = [];
        const draw = () => { const t = T(), n = +$("#gd-n").value, r = rng32(seed * 1000 + n), samp = Array.from({ length: n }, () => pool[Math.floor(r() * pool.length)]);
          const meds = Array.from({ length: 600 }, () => median(Array.from({ length: n }, () => samp[Math.floor(r() * n)]))), lo = quant(meds, 0.025), hi = quant(meds, 0.975), m = median(samp), all = median(pool);
          $("#gd-n-o").textContent = ni(n);
          plot("gd-boot", [{ type: "histogram", x: meds, nbinsx: 40, marker: { color: t.cat[0] }, hovertemplate: "mediana ≈ %{x:.1f} nm: %{y} reamostragens<extra></extra>" }],
            { showlegend: false, xaxis: { title: { text: "mediana do tamanho (nm) em cada reamostragem" }, range: [8, 30] }, yaxis: { title: { text: "reamostragens" } },
              shapes: [{ type: "rect", x0: lo, x1: hi, yref: "paper", y0: 0, y1: 1, fillcolor: hexA(t.dark ? "#e0b45c" : "#b8862a", 0.2), line: { width: 0 }, layer: "below" },
                { type: "line", x0: all, x1: all, yref: "paper", y0: 0, y1: 1, line: { color: t.ruby, width: 2, dash: "dot" } }],
              annotations: [{ x: all, y: 1, yref: "paper", text: `todos os ${ni(pool.length)} artigos: ${nf(all, 1)} nm`, showarrow: false, xanchor: "left", xshift: 5, font: { size: 10, color: t.ruby } }] });
          $("#boot-txt").innerHTML = `<p>Amostra de ${ni(n)} artigos: mediana <b>${nf(m, 1)} nm</b>, IC 95 % por bootstrap <b>${nf(lo, 1)}–${nf(hi, 1)} nm</b> (faixa dourada, largura ${nf(hi - lo, 1)} nm). A linha vermelha é o valor com todos os artigos: o IC quase sempre a contém. Aumente a amostra e veja a faixa estreitar.</p>`; };
        $("#gd-n").addEventListener("input", perFrame(draw)); $("#gd-redraw").addEventListener("click", () => { seed++; draw(); }); drawer(draw); } }
    // p-valores e Holm
    { const B_ = A.benchmark, rows = []; Object.entries(B_.datasets).forEach(([n, ds]) => B_.arms.slice(1).forEach((a) => rows.push({ n, a, p: ds.paired[a].p, ph: ds.paired[a].p_holm })));
      rows.sort((x, y) => x.p - y.p); const m = rows.length, el = wrap("holm", "", [["gd-holm"]]);
      if (el) { const draw = () => { const t = T(), xs = rows.map((_, i) => i + 1);
          plot("gd-holm", [{ type: "scatter", mode: "lines", name: "limiar ingênuo (0,05)", x: [1, m], y: [0.05, 0.05], line: { color: t.muted, dash: "dot", width: 1.4 }, hoverinfo: "skip" },
            { type: "scatter", mode: "lines", name: "limiar de Holm: 0,05/(m − posição + 1)", x: xs, y: xs.map((i) => 0.05 / (m - i + 1)), line: { color: t.ruby, width: 2, shape: "hv" }, hoverinfo: "skip" },
            { type: "scatter", mode: "markers", name: "teste", x: xs, y: rows.map((r) => r.p), customdata: rows.map((r) => [r.n, r.a, r.ph]),
              marker: { size: 11, color: rows.map((r) => (r.ph < 0.05 ? t.cat[2] : r.p < 0.05 ? t.cat[1] : t.other)), line: { width: 1.5, color: t.surface } },
              hovertemplate: "%{customdata[0]} · %{customdata[1]}<br>p = %{y:.4f} · Holm %{customdata[2]:.3f}<extra></extra>" }],
            { xaxis: { title: { text: "posição do teste (do menor p para o maior)" }, dtick: 1 }, yaxis: { type: "log", title: { text: "p-valor" } } });
          const naive = rows.filter((r) => r.p < 0.05).length, holm = rows.filter((r) => r.ph < 0.05).length;
          $("#holm-txt").innerHTML = `<p>Os ${m} testes pareados da aba Aprendizado (5 campanhas × 3 estratégias). <b>${naive}</b> ficam abaixo de 0,05 (ingênuo), mas só <b>${holm}</b> ficam abaixo da escada de Holm (verdes): os laranjas são \"significativos\" só se ignorarmos que fizemos ${m} testes.</p>`; };
        drawer(draw); } }
    // ingênuo × ajustado
    { const E_ = A.causal.effects.filter((e) => !e.binary), el = wrap("naive", "", [["gd-naive", "short"]]);
      if (el) { const draw = () => { const t = T(), y = E_.map((e) => e.name);
          plot("gd-naive", [{ type: "scatter", mode: "markers", name: "comparação ingênua", y, x: E_.map((e) => e.naive_ratio), marker: { size: 12, symbol: "x", color: t.cat[1] }, hovertemplate: "%{y}<br>ingênuo ×%{x:.2f}<extra></extra>" },
            { type: "scatter", mode: "markers", name: "ajustado (AIPW)", y, x: E_.map((e) => e.estimate), marker: { size: 12, color: t.cat[0], line: { width: 2, color: t.surface } },
              error_x: { type: "data", symmetric: false, array: E_.map((e) => e.estimate_ci95[1] - e.estimate), arrayminus: E_.map((e) => e.estimate - e.estimate_ci95[0]), color: t.ink2, width: 4 }, hovertemplate: "%{y}<br>ajustado ×%{x:.2f}<extra></extra>" }],
            { xaxis: { type: "log", title: { text: "efeito no tamanho (razão; 1 = nenhum)" }, tickvals: [0.2, 0.5, 1, 2] }, yaxis: { automargin: true, autorange: "reversed" }, margin: { l: 220 },
              shapes: [{ type: "line", x0: 1, x1: 1, yref: "paper", y0: 0, y1: 1, line: { color: t.ink, dash: "dot", width: 1 } }] });
          $("#naive-txt").innerHTML = "<p>Cada linha é um efeito no tamanho. O X é a comparação simples entre quem usou e quem não usou o reagente; o círculo é a estimativa depois de equilibrar os grupos nos confundidores medidos. Quando os dois diferem, a comparação simples estava contaminada por outras diferenças entre as sínteses.</p>"; };
        drawer(draw); } }
    // validação: previsto × medido
    { const cv = A.designer.cv, el = wrap("cv", "", [["gd-cv"]]);
      if (el) { const draw = () => { const t = T(), res = cv.obs.map((o, i) => o - cv.pred[i]), worst = res.reduce((b, r, i) => (Math.abs(r) > Math.abs(res[b]) ? i : b), 0), best = res.reduce((b, r, i) => (Math.abs(r) < Math.abs(res[b]) ? i : b), 0);
          const mn = Math.min(...cv.obs, ...cv.pred), mx = Math.max(...cv.obs, ...cv.pred);
          plot("gd-cv", [{ type: "scatter", mode: "lines", x: [mn, mx], y: [mn, mx], line: { color: t.muted, dash: "dot" }, hoverinfo: "skip", showlegend: false },
            { type: "scatter", mode: "markers", x: cv.pred, y: cv.obs, marker: { size: 7, color: t.cat[0], opacity: 0.8 }, hovertemplate: "previsto %{x:.2f} · medido %{y:.2f}<extra></extra>", showlegend: false }],
            { xaxis: { title: { text: "previsto pelo modelo (sem ter visto o ponto)" } }, yaxis: { title: { text: "medido" } },
              annotations: [{ x: cv.pred[worst], y: cv.obs[worst], text: "maior erro:<br>longe da diagonal", ax: 60, ay: -40, font: { size: 11, color: t.ink }, arrowcolor: t.ink },
                { x: cv.pred[best], y: cv.obs[best], text: "acerto: na diagonal", ax: -70, ay: 40, font: { size: 11, color: t.ink }, arrowcolor: t.ink },
                { x: mx, y: mx, text: "diagonal = previsão perfeita", showarrow: false, xanchor: "right", yanchor: "bottom", font: { size: 10, color: t.muted } }] });
          $("#cv-txt").innerHTML = `<p>Cada ponto é uma condição da campanha AgNP prevista por um modelo que NÃO a viu no treino (validação cruzada). Quanto mais perto da diagonal, melhor. R² = ${nf(cv.r2, 2)}: o modelo explica ${nf(100 * cv.r2, 0)} % da variação das medidas; o restante é erro.</p>`; };
        drawer(draw); } }
    // GP e EI numa fatia
    { const Dg = A.designer, el = wrap("gp", `<div class="ctl"><label for="gd-gpv">Variável da fatia</label><select id="gd-gpv">${Dg.labels.map((l, j) => `<option value="${j}">${esc(l)}</option>`).join("")}</select></div>`, [["gd-gp", "tall"]]);
      if (el) { const best = Math.min(...Dg.cv.obs), x0 = Dg.best_measured.x, nrm = (x) => x.map((v2, j) => (v2 - Dg.lo[j]) / (Dg.hi[j] - Dg.lo[j]));
        const draw = () => { const t = T(), j = +$("#gd-gpv").value, g = lin(Dg.lo[j], Dg.hi[j], 80), mu = [], up = [], dn = [], ei = [];
          g.forEach((x) => { const q = x0.slice(); q[j] = x; const [m, s] = gpPredict(Dg.gp, nrm(q)); mu.push(Math.exp(m)); up.push(Math.exp(m + 1.96 * s)); dn.push(Math.exp(m - 1.96 * s));
            const z = (best - m) / s; ei.push((best - m) * ncdf(z) + s * npdf(z)); });
          const xn0 = nrm(x0), near = Dg.points.X.map((r, i) => [r, i]).filter(([r]) => Math.hypot(...nrm(r).map((v2, k2) => (k2 === j ? 0 : v2 - xn0[k2]))) < 0.2);
          const eiMax = Math.max(...ei) || 1, eiRel = ei.map((e) => e / eiMax);
          plot("gd-gp", [{ type: "scatter", mode: "lines", x: g, y: up, line: { width: 0 }, hoverinfo: "skip", showlegend: false, xaxis: "x", yaxis: "y" },
            { type: "scatter", mode: "lines", name: "faixa de 95 %", x: g, y: dn, fill: "tonexty", fillcolor: hexA(t.cat[0], 0.16), line: { width: 0 }, hoverinfo: "skip" },
            { type: "scatter", mode: "lines", name: "previsão do GP", x: g, y: mu, line: { color: t.cat[0], width: 2.4 }, hovertemplate: "%{x:.1f}: perda %{y:.3f}<extra></extra>" },
            { type: "scatter", mode: "markers", name: "medidas próximas", x: near.map(([r]) => r[j]), y: near.map(([, i]) => Dg.points.mean[i]), marker: { size: 7, color: t.ruby }, hovertemplate: "medida: %{y:.3f}<extra></extra>" },
            { type: "scatter", mode: "lines", name: "melhoria esperada (EI, máx. = 1)", x: g, y: eiRel, line: { color: t.cat[2], width: 2 }, fill: "tozeroy", fillcolor: hexA(t.cat[2], 0.15), xaxis: "x2", yaxis: "y2", hovertemplate: "%{x:.1f}: EI relativa %{y:.2f}<extra></extra>" }],
            { grid: { rows: 2, columns: 1, pattern: "independent", roworder: "top to bottom" }, xaxis: { matches: "x2", showticklabels: false }, yaxis: { title: { text: "perda prevista" }, rangemode: "tozero" },
              xaxis2: { title: { text: Dg.labels[j] } }, yaxis2: { title: { text: "EI relativa" }, range: [0, 1.05] }, legend: { y: 1.12 } });
          const k2 = ei.indexOf(Math.max(...ei));
          $("#gp-txt").innerHTML = `<p>As outras quatro vazões ficam na melhor condição medida. A faixa azul é estreita onde há medidas (pontos vermelhos) e larga onde não há. A curva verde (EI) é maior onde vale mais a pena testar: aqui, em ${esc(Dg.labels[j])} ≈ ${nf(g[k2], 1)}. Ela aparece relativa (máximo = 1) porque, partindo da melhor condição já medida, a melhoria esperada em valor absoluto é pequena: o GP acha pouco provável superar o que já se tem, e o pouco de chance que sobra fica onde a incerteza é maior.</p>`; };
        $("#gd-gpv").addEventListener("change", draw); drawer(draw); } }
    // Kaplan–Meier passo a passo
    { const ag = A.benchmark.datasets.AgNP, Bm = ag.budget, ev = ag.reach_top5["GP-EI"].per_seed.slice().sort((x, y) => (x == null) - (y == null) || x - y), el = wrap("km", `<div class="ctl"><label for="gd-t">Experimentos feitos <output id="gd-t-o"></output></label><input type="range" id="gd-t" min="0" max="${Bm}" step="1" value="12"></div>`, [["gd-kmt", "short"], ["gd-kmc", "short"]]);
      if (el) { const draw = () => { const t = T(), tt = +$("#gd-t").value, n = ev.length;
          plot("gd-kmt", [{ type: "scatter", mode: "lines", x: [].concat(...ev.map((e, i) => [0, Math.min(e == null ? Bm : e, tt), null])), y: [].concat(...ev.map((_, i) => [i + 1, i + 1, null])), line: { color: t.lineStrong, width: 2 }, hoverinfo: "skip", showlegend: false },
            { type: "scatter", mode: "markers", x: ev.map((e) => (e != null && e <= tt ? e : null)), y: ev.map((_, i) => i + 1), marker: { size: 8, color: t.cat[2] }, hovertemplate: "repetição %{y}: chegou no experimento %{x}<extra></extra>", showlegend: false }],
            { xaxis: { title: { text: "experimento" }, range: [0, Bm] }, yaxis: { title: { text: "repetição (ordenada)" }, showticklabels: false }, margin: { t: 10 } });
          const S = [1]; for (let k = 1; k <= tt; k++) { const atRisk = ev.filter((e) => e == null || e >= k).length, d = ev.filter((e) => e === k).length; S.push(S[S.length - 1] * (atRisk ? 1 - d / atRisk : 1)); }
          plot("gd-kmc", [{ type: "scatter", mode: "lines", x: S.map((_, i) => i), y: S, line: { color: t.cat[0], width: 2.6, shape: "hv" }, hovertemplate: "após %{x} experimentos: %{y:.0%} ainda sem chegar<extra></extra>" }],
            { xaxis: { title: { text: "experimentos" }, range: [0, Bm] }, yaxis: { title: { text: "ainda não chegou" }, tickformat: ".0%", range: [0, 1.02] }, showlegend: false, margin: { t: 10 } });
          $("#gd-t-o").textContent = ni(tt);
          $("#km-txt").innerHTML = `<p>Em cima, as ${n} repetições do GP-EI na campanha AgNP, ordenadas pelo momento em que chegaram: cada linha avança um experimento por vez e ganha um ponto verde quando acha o top 5 %. Embaixo, a curva de Kaplan–Meier: a fração que ainda não chegou. Depois de ${ni(tt)} experimentos, <b>${nf(100 * S[S.length - 1], 0)} %</b> ainda não tinham chegado.</p>`; };
        $("#gd-t").addEventListener("input", perFrame(draw)); drawer(draw); } }
    // SHAP em cascata
    { const S_ = A.interpret.agnp, Dg = A.designer, X_ = S_.X, n = X_.length, nrm = (x) => x.map((v2, j) => (v2 - Dg.lo[j]) / (Dg.hi[j] - Dg.lo[j]));
      const pred = X_.map((x) => gpPredict(Dg.gp, nrm(x))[0]), ord = pred.map((p, i) => [p, i]).sort((a, b) => a[0] - b[0]);
      const pick = [["melhor prevista", ord[0][1]], ["mediana", ord[n >> 1][1]], ["pior prevista", ord[n - 1][1]], ["um quarto", ord[n >> 2][1]], ["três quartos", ord[(3 * n) >> 2][1]]];
      const el = wrap("shap", `<div class="ctl"><label for="gd-sh">Condição</label><select id="gd-sh">${pick.map(([l, i], k) => `<option value="${i}">${l} (perda prevista ${nf(Math.exp(pred[i]), 3)})</option>`).join("")}</select></div>`, [["gd-shap"]]);
      if (el) { const draw = () => { const t = T(), i = +$("#gd-sh").value, sv = S_.values[i], base = pred[i] - sv.reduce((a, b) => a + b, 0);
          plot("gd-shap", [{ type: "waterfall", orientation: "v", measure: ["absolute", ...sv.map(() => "relative"), "total"], x: ["média do modelo", ...S_.features.map((f, j) => `${f}<br>= ${nf(X_[i][j], 1)}`), "previsão"],
            y: [base, ...sv, 0], connector: { line: { color: t.lineStrong } }, increasing: { marker: { color: t.cat[1] } }, decreasing: { marker: { color: t.cat[2] } }, totals: { marker: { color: t.cat[0] } },
            hovertemplate: "%{x}: %{y:+.3f}<extra></extra>" }], { yaxis: { title: { text: "ln(perda) prevista" } }, showlegend: false, margin: { b: 80 } });
          $("#shap-txt").innerHTML = `<p>Comece da média do modelo (${nf(base, 2)} em ln). Cada barra é quanto uma vazão, no valor desta condição, empurra a previsão: verde para baixo (melhor, perda menor), laranja para cima. A soma dá a previsão (${nf(pred[i], 2)}, perda ${nf(Math.exp(pred[i]), 3)}).</p>`; };
        $("#gd-sh").addEventListener("change", draw); drawer(draw); } }
    // conformal
    { const Bd = A.predictor.bands, el = wrap("conformal", "", [["gd-conf", "short"]]);
      if (el) { const draw = () => { const t = T(), ks = ["50", "90"], lab = ks.map((k) => `intervalo de ${k} %`);
          plot("gd-conf", [{ type: "bar", name: "prometido", x: lab, y: ks.map((k) => 100 * Bd[k].level), marker: { color: t.other } },
            { type: "bar", name: "modelo cru", x: lab, y: ks.map((k) => 100 * Bd[k].coverage_uncorrected), marker: { color: t.cat[1] } },
            { type: "bar", name: "conformal, artigos novos", x: lab, y: ks.map((k) => 100 * Bd[k].coverage_articles), marker: { color: t.cat[0] } }],
            { barmode: "group", yaxis: { title: { text: "% dos casos dentro do intervalo" }, range: [0, 100] } });
          $("#conformal-txt").innerHTML = `<p>A barra azul (conformal, medida em artigos que o modelo nunca viu) bate com a cinza (o prometido): ${nf(100 * Bd["90"].coverage_articles, 1)} % para 90 %, ${nf(100 * Bd["50"].coverage_articles, 1)} % para 50 %.</p>`; };
        drawer(draw); } }
    // Bayes: inversão pico → tamanho
    { const IV = A.optics.inversion, el = wrap("bayes", `<div class="ctl ctl-auto"><span class="lbl" id="gd-pk-l">Pico medido</span><div class="seg" id="gd-pk" role="group" aria-labelledby="gd-pk-l">${[518, 525, 540, 560].map((p, i) => `<button type="button" aria-pressed="${i === 0}" data-v="${p}">${p} nm</button>`).join("")}</div></div>`, [["gd-bayes", "short"]]);
      if (el) { let pk = 518; const draw = () => { const t = T(), g = IV.d, nu = IV.nu, pn = (a) => { const m = Math.max(...a); return a.map((x) => x / m); };
          const lik = g.map((_, i) => { const z = (pk - IV.lam[i] - IV.bias[i]) / IV.sd[i]; return (nu > 0 ? Math.pow(1 + z * z / nu, -(nu + 1) / 2) : Math.exp(-0.5 * z * z)) / IV.sd[i]; }), post = lik.map((x, i) => x * IV.prior[i]);
          plot("gd-bayes", [{ type: "scatter", mode: "lines", name: "a priori (o que se sabia)", x: g, y: pn(IV.prior), line: { color: t.muted, dash: "dot", width: 1.6 } },
            { type: "scatter", mode: "lines", name: "verossimilhança (o que o pico diz)", x: g, y: pn(lik), line: { color: t.cat[1], dash: "dash", width: 1.8 } },
            { type: "scatter", mode: "lines", name: "posterior (o que se sabe agora)", x: g, y: pn(post), fill: "tozeroy", fillcolor: hexA(t.cat[0], 0.16), line: { color: t.cat[0], width: 2.4 } }],
            { xaxis: { type: "log", title: { text: "diâmetro (nm)" }, tickvals: [2, 5, 10, 20, 50, 100, 200] }, yaxis: { title: { text: "plausibilidade (máx. = 1)" }, range: [0, 1.05] } });
          $("#bayes-txt").innerHTML = `<p>Posterior = a priori × verossimilhança, renormalizada. Com o pico em ${pk} nm, ${pk < 530 ? "a verossimilhança é larga (o pico quase não muda abaixo de 25 nm) e a posterior herda boa parte da a priori" : "a verossimilhança se concentra em partículas maiores e puxa a posterior para lá"}.</p>`; };
        segmented("#gd-pk", (x) => { pk = +x; draw(); }); drawer(draw); } }
    // perda J ponto a ponto (ensemble de Mie com σ do alvo)
    { const O = A.optics, tg = O.target, wl = O.wl, ld = O.d.map(Math.log), C = O.C_ext.map((r, i) => r.map((v2) => v2 * O.C_ext_max[i]));
      const nG = Math.round((tg.grid[1] - tg.grid[0]) / tg.grid[2]) + 1, gw = Array.from({ length: nG }, (_, i) => tg.grid[0] + i * tg.grid[2]);
      const at = (w, xs, ys) => { let j = 0; while (j < xs.length - 2 && xs[j + 1] < w) j++; const f = (w - xs[j]) / (xs[j + 1] - xs[j]); return ys[j] + f * (ys[j + 1] - ys[j]); };
      const tN = (() => { const e = gw.map((w) => at(w, tg.wl, tg.E)), m = Math.max(...e); return e.map((x) => x / m); })();
      const spec = (d) => { const sl = Math.sqrt(Math.log(1 + tg.sigma * tg.sigma)), mu = Math.log(d) - sl * sl / 2, w = ld.map((x) => Math.exp(-0.5 * ((x - mu) / sl) ** 2)), tot = w.reduce((a, b) => a + b, 0);
        const E = wl.map((_, j) => w.reduce((a, wi, i) => a + (wi > 1e-9 * tot ? wi * C[i][j] : 0), 0) / tot), e = gw.map((x) => at(x, wl, E)), m = Math.max(...e); return e.map((x) => x / m); };
      const el = wrap("jloss", `<div class="ctl"><label for="gd-jd">Diâmetro médio <output id="gd-jd-o"></output></label><input type="range" id="gd-jd" min="0" max="100" step="1" value="50"></div>`, [["gd-jl", "tall"]]);
      if (el) { const draw = () => { const t = T(), d = tg.diameter * Math.pow(2.5, (+$("#gd-jd").value - 50) / 50), e = spec(d), r = e.map((x, i) => (x - tN[i]) / tg.s_m), J = r.reduce((a, x) => a + x * x, 0) / r.length;
          $("#gd-jd-o").textContent = `${nf(d, d < 10 ? 1 : 0)} nm`;
          plot("gd-jl", [{ type: "scatter", mode: "lines", name: "espectro da amostra", x: gw, y: e, line: { color: t.cat[0], width: 2.4 }, hovertemplate: "λ = %{x} nm: %{y:.3f}<extra></extra>" },
            { type: "scatter", mode: "lines", name: `alvo (${nf(tg.diameter, 0)} nm, σ = ${nf(100 * tg.sigma, 0)} %)`, x: gw, y: tN, line: { color: t.ink, dash: "dash", width: 1.8 }, hoverinfo: "skip" },
            { type: "bar", name: "diferença ÷ sₘ", x: gw, y: r, marker: { color: r.map((x) => (x > 0 ? t.cat[1] : t.cat[2])) }, xaxis: "x2", yaxis: "y2", hovertemplate: "λ = %{x} nm: %{y:.0f} × sₘ<extra></extra>" }],
            { grid: { rows: 2, columns: 1, pattern: "independent", roworder: "top to bottom" }, xaxis: { matches: "x2", showticklabels: false }, yaxis: { title: { text: "extinção (máx. = 1)" }, range: [0, 1.05] },
              xaxis2: { title: { text: "comprimento de onda (nm)" } }, yaxis2: { title: { text: "(E − E*) / sₘ" } }, bargap: 0, legend: { y: 1.14 } });
          $("#jloss-txt").innerHTML = `<p>Embaixo, a diferença em cada comprimento de onda em unidades do ruído de medida (sₘ = ${nf(tg.s_m, 3)}): barras laranja = a amostra absorve mais que o alvo; verdes = menos. J é a média dos quadrados dessas barras: <b>J ${J < 0.01 ? "≈ 0" : "= " + nf(J, J < 10 ? 2 : 0)}</b> (log₁₀ J = ${J > 0 ? nf(Math.log10(J), 1) : "−∞"}). ${J < 1 ? "Abaixo de 1: a diferença é do tamanho do ruído, a amostra atende ao alvo." : J < 100 ? "Diferença maior que o ruído: forma do espectro distinguível do alvo." : "Diferença muito maior que o ruído: espectro claramente fora do alvo."} A dispersão foi mantida igual à do alvo (${nf(100 * tg.sigma, 0)} %) para isolar o efeito do diâmetro.</p>`; };
        $("#gd-jd").addEventListener("input", perFrame(draw)); drawer(draw); } }
    // correlação de Spearman: tamanho × pico relatados
    { const S0 = A.optics.lit_spheres, el = wrap("corr", `<div class="ctl ctl-auto"><span class="lbl" id="gd-cr-l">Faixa de tamanho</span><div class="seg" id="gd-cr" role="group" aria-labelledby="gd-cr-l"><button type="button" aria-pressed="true" data-v="all">todos</button><button type="button" aria-pressed="false" data-v="small">abaixo de 25 nm</button><button type="button" aria-pressed="false" data-v="big">25 a 150 nm</button></div></div>`, [["gd-corr"]]);
      const rank = (v) => { const o = v.map((x, i) => [x, i]).sort((a, b) => a[0] - b[0]), r = new Array(v.length); let i = 0;
        while (i < o.length) { let j = i; while (j + 1 < o.length && o[j + 1][0] === o[i][0]) j++; for (let k2 = i; k2 <= j; k2++) r[o[k2][1]] = (i + j) / 2 + 1; i = j + 1; } return r; };
      const pear = (a, b) => { const n = a.length, ma = a.reduce((s, x) => s + x, 0) / n, mb = b.reduce((s, x) => s + x, 0) / n; let sab = 0, saa = 0, sbb = 0;
        for (let i = 0; i < n; i++) { sab += (a[i] - ma) * (b[i] - mb); saa += (a[i] - ma) ** 2; sbb += (b[i] - mb) ** 2; } return sab / Math.sqrt(saa * sbb); };
      if (el) { let rg = "all"; const draw = () => { const t = T(), keep = S0.size.map((s, i) => i).filter((i) => (rg === "all" ? true : rg === "small" ? S0.size[i] < 25 : S0.size[i] >= 25 && S0.size[i] <= 150));
          const x = keep.map((i) => S0.size[i]), y = keep.map((i) => S0.peak[i]), rho = pear(rank(x), rank(y));
          plot("gd-corr", [{ type: "scatter", mode: "markers", x, y, marker: { size: 6, color: t.cat[0], opacity: 0.55, line: { width: 0 } }, hovertemplate: "%{x:.1f} nm → pico %{y:.0f} nm<extra></extra>" }],
            { showlegend: false, xaxis: { type: "log", title: { text: "tamanho relatado (nm)" }, tickvals: [3, 5, 10, 20, 50, 100] }, yaxis: { title: { text: "pico relatado (nm)" } } });
          $("#corr-txt").innerHTML = `<p>${ni(x.length)} relatos de esferas. Correlação de Spearman <b>ρ = ${nf(rho, 2)}</b>: ${rho > 0.6 ? "forte e positiva (partículas maiores, pico mais à direita)" : rho > 0.3 ? "moderada" : "fraca"}. ${rg === "small" ? "Abaixo de 25 nm o pico quase não muda com o tamanho (Mie), e a correlação cai: o que sobra é ruído de relato." : rg === "big" ? "Acima de 25 nm o pico anda com o tamanho, como Mie e Haiss preveem." : "Restrinja a faixa para ver onde a relação existe."}</p>`; };
        segmented("#gd-cr", (v2) => { rg = v2; draw(); }); drawer(draw); } }
    // boosting: a previsão se formando árvore a árvore
    { const P = A.predictor, M = P.models["0.5"], F = P.features, fi = (n) => F.indexOf(n);
      const R = [["Turkevich (citrato, 100 °C)", ["citrato"], 0, 100, 0], ["Brust (NaBH₄ + tiol + TOAB, 25 °C)", ["NaBH₄", "tiol (GSH/dodecanotiol)", "TOAB"], 0, 25, 0], ["Sementes + CTAB, bastões (30 °C)", ["NaBH₄", "ácido ascórbico", "CTAB"], 1, 30, 1]];
      const vecR = ([, names, seed, Tc, rod]) => { const x = new Array(F.length).fill(0); names.forEach((n) => { x[fi(n)] = 1; }); x[fi("mediada por sementes")] = seed; x[fi("temperatura (°C)")] = Tc; x[fi("ano")] = 2020;
        x[fi("forma não esférica")] = rod; x[fi("bastão")] = rod; return x; };
      const leaf = (r, x) => { let k2 = r; while (M.f[k2] >= 0) { const v2 = x[M.f[k2]]; k2 = v2 == null || Number.isNaN(v2) ? (M.m[k2] ? M.l[k2] : M.r[k2]) : (v2 <= M.t[k2] ? M.l[k2] : M.r[k2]); } return M.v[k2]; };
      const el = wrap("boost", `<div class="ctl"><label for="gd-br">Receita</label><select id="gd-br">${R.map((r, i) => `<option value="${i}">${esc(r[0])}</option>`).join("")}</select></div><div class="ctl"><label for="gd-bn">Árvores somadas <output id="gd-bn-o"></output></label><input type="range" id="gd-bn" min="0" max="${M.roots.length}" step="1" value="${M.roots.length}"></div>`, [["gd-boost"]]);
      if (el) { const draw = () => { const t = T(), x = vecR(R[+$("#gd-br").value]), n = +$("#gd-bn").value, cum = [M.base]; M.roots.forEach((r) => cum.push(cum[cum.length - 1] + leaf(r, x)));
          const nm = cum.map(Math.exp);
          plot("gd-boost", [{ type: "scatter", mode: "lines", name: "todas as árvores", x: nm.map((_, i) => i), y: nm, line: { color: t.lineStrong, width: 1.5 }, hoverinfo: "skip" },
            { type: "scatter", mode: "lines", name: "somadas até aqui", x: nm.slice(0, n + 1).map((_, i) => i), y: nm.slice(0, n + 1), line: { color: t.cat[0], width: 2.6 }, hovertemplate: "%{x} árvores: %{y:.1f} nm<extra></extra>" },
            { type: "scatter", mode: "markers", name: "previsão atual", x: [n], y: [nm[n]], marker: { size: 11, color: t.ruby, line: { width: 2, color: t.surface } }, hovertemplate: "%{y:.1f} nm<extra></extra>" }],
            { xaxis: { title: { text: "número de árvores somadas" } }, yaxis: { type: "log", title: { text: "tamanho mediano previsto (nm)" } }, legend: { y: 1.12 } });
          $("#gd-bn-o").textContent = ni(n);
          const q4 = Math.round(M.roots.length / 4), tot = cum[cum.length - 1] - cum[0], fr = Math.abs(tot) > 1e-9 ? (cum[q4] - cum[0]) / tot : 1;
          $("#boost-txt").innerHTML = `<p>A previsão começa no valor típico de toda a base (${nf(nm[0], 1)} nm, árvore 0) e cada árvore pequena acrescenta uma correção (a taxa de aprendizado deixa cada passo pequeno, o que evita decorar os dados). Com ${ni(n)} de ${ni(M.roots.length)} árvores a mediana prevista é <b>${nf(nm[n], 1)} nm</b>. Nesta receita, o primeiro quarto das árvores (${ni(q4)}) faz ${nf(100 * Math.max(0, Math.min(1.5, fr)), 0)} % da mudança total, de ${nf(nm[0], 1)} para ${nf(nm[nm.length - 1], 1)} nm. Troque a receita: com a de Brust a soma desce para poucos nanômetros.</p>`; };
        $("#gd-br").addEventListener("change", draw); $("#gd-bn").addEventListener("input", perFrame(draw)); drawer(draw); } }
    // meta-análise: efeitos fixos × aleatórios
    { const E_ = A.causal.effects, el = wrap("meta", `<div class="ctl"><label for="gd-me">Efeito</label><select id="gd-me">${E_.map((e, i) => `<option value="${i}">${esc(e.name)}</option>`).join("")}</select></div><div class="ctl ctl-auto"><span class="lbl" id="gd-mm-l">Modelo</span><div class="seg" id="gd-mm" role="group" aria-labelledby="gd-mm-l"><button type="button" aria-pressed="false" data-v="fixed">efeito fixo</button><button type="button" aria-pressed="true" data-v="random">efeitos aleatórios</button></div></div>`, [["gd-meta", "short"]]);
      if (el) { let mm = "random"; const draw = () => { const t = T(), e = E_[+$("#gd-me").value], R2 = e.replication, b = R2.bases;
          const w = b.map((x) => 1 / (x.se_log * x.se_log)), fx = Math.exp(b.reduce((a, x, i) => a + w[i] * Math.log(x.estimate), 0) / w.reduce((a, x) => a + x, 0)), fse = 1 / Math.sqrt(w.reduce((a, x) => a + x, 0));
          const pool = mm === "fixed" ? [fx, fx * Math.exp(-1.96 * fse), fx * Math.exp(1.96 * fse)] : [R2.pooled, R2.pooled_ci95[0], R2.pooled_ci95[1]];
          const ys = [...b.map((x) => x.base), mm === "fixed" ? "combinado (fixo)" : "combinado (aleatório)"], xs = [...b.map((x) => x.estimate), pool[0]], lo = [...b.map((x) => x.ci95[0]), pool[1]], hi = [...b.map((x) => x.ci95[1]), pool[2]];
          plot("gd-meta", [{ type: "scatter", mode: "markers", x: xs, y: ys, marker: { size: [12, 12, 15], symbol: ["circle", "circle", "diamond"], color: [t.cat[0], t.cat[3], t.ruby], line: { width: 2, color: t.surface } },
            error_x: { type: "data", symmetric: false, array: hi.map((h2, i) => h2 - xs[i]), arrayminus: lo.map((l2, i) => xs[i] - l2), color: t.ink2, width: 5 }, hovertemplate: "%{y}: ×%{x:.2f}<extra></extra>" }],
            { showlegend: false, xaxis: { type: "log", title: { text: e.binary ? "razão de riscos (1 = nenhum efeito)" : "razão de tamanhos (1 = nenhum efeito)" } }, yaxis: { automargin: true, autorange: "reversed" },
              shapes: [{ type: "line", x0: 1, x1: 1, yref: "paper", y0: 0, y1: 1, line: { color: t.ink, dash: "dot", width: 1 } }] });
          $("#meta-txt").innerHTML = `<p>${mm === "fixed" ? `O modelo de efeito fixo supõe um único efeito verdadeiro e dá um intervalo estreito (×${nf(pool[1], 2)} a ×${nf(pool[2], 2)}), mas ignora que as bases discordam mais do que o acaso explica.` : `O modelo de efeitos aleatórios admite que o efeito varie entre as bases (τ = ${nf(R2.tau, 2)} em log) e alarga o intervalo para ×${nf(pool[1], 2)} a ×${nf(pool[2], 2)}: é o intervalo honesto.`} I² = ${nf(100 * R2.I2, 0)} %: ${R2.I2 > 0.75 ? "a maior parte da diferença entre as bases não é acaso" : R2.I2 > 0.25 ? "parte da diferença entre as bases não é acaso" : "a diferença entre as bases é compatível com o acaso"}. ${R2.same_direction ? "As duas bases concordam na direção." : "As bases discordam na direção."}</p>`; };
        $("#gd-me").addEventListener("change", draw); segmented("#gd-mm", (v2) => { mm = v2; draw(); }); drawer(draw); } }
    // lei de Bragg: energia do feixe × anéis medidos
    { const X_ = A.xrd, g = X_.geometry, rings = X_.rings, el = wrap("bragg", `<div class="ctl"><label for="gd-be">Energia do feixe <output id="gd-be-o"></output></label><input type="range" id="gd-be" min="${Math.round(g.energy_keV - 12)}" max="${Math.round(g.energy_keV + 12)}" step="0.1" value="${nf(g.energy_keV, 1).replace(",", ".")}"></div>`, [["gd-bragg"]]);
      if (el) { const r0 = X_.profile.map((_, i) => i), prof = X_.profile.map((v2, i) => Math.max(v2 - X_.baseline[i], 0) + 1);
        const draw = () => { const t = T(), E = +$("#gd-be").value, lam = 12.398 / E, rp = rings.map((r) => { const s = lam / (2 * g.a_ceo2_A / Math.sqrt(r.N)); return g.distance_px * Math.tan(2 * Math.asin(s)); });
          const res = rp.map((r, i) => r - rings[i].r_obs), rms = Math.sqrt(res.reduce((a, x) => a + x * x, 0) / res.length), top = Math.max(...prof);
          $("#gd-be-o").textContent = `${nf(E, 1)} keV`;
          plot("gd-bragg", [{ type: "scatter", mode: "lines", name: "perfil medido (anéis = picos)", x: r0, y: prof, line: { color: t.cat[0], width: 1.4 }, hovertemplate: "r = %{x} px<extra></extra>" },
            { type: "scatter", mode: "markers", name: "anel previsto pela energia escolhida", x: rp, y: rp.map(() => top * 1.6), text: rings.map((r) => r.hkl), marker: { symbol: "triangle-down", size: 10, color: t.ruby }, hovertemplate: "hkl %{text}: previsto %{x:.0f} px<extra></extra>" }],
            { xaxis: { title: { text: "raio no detector (pixels)" }, range: [150, X_.profile.length] }, yaxis: { type: "log", title: { text: "intensidade acima da linha de base" } }, legend: { y: 1.14 },
              shapes: rp.map((x) => ({ type: "line", x0: x, x1: x, yref: "paper", y0: 0, y1: 1, line: { color: hexA(t.ruby, 0.45), width: 1, dash: "dot" } })) });
          $("#bragg-txt").innerHTML = `<p>Os picos azuis são os anéis medidos; os triângulos vermelhos, onde a lei de Bragg põe cada anel para a energia escolhida (com a distância do detector fixa em ${ni(g.distance_px)} px). Erro médio entre previsto e medido: <b>${nf(rms, rms < 1 ? 2 : 0)} pixel</b>. ${Math.abs(E - g.energy_keV) < 0.15 ? `Na energia ajustada (${nf(g.energy_keV, 1)} keV) os triângulos caem exatamente sobre os picos: é a calibração.` : `Fora da energia ajustada (${nf(g.energy_keV, 1)} keV) os triângulos escorregam: ${E > g.energy_keV ? "energia maior = comprimento de onda menor = ângulos menores = anéis mais perto do centro" : "energia menor = comprimento de onda maior = ângulos maiores = anéis mais longe do centro"}.`}</p>`; };
        $("#gd-be").addEventListener("input", perFrame(draw)); drawer(draw); } }
    // deslocamento de Stokes
    { const U_ = A.aunc, idx = U_.exc.map((_, i) => i).filter((i) => U_.exc[i] != null && U_.em[i] != null), el = wrap("stokes", "", [["gd-stokes"]]);
      if (el) { const draw = () => { const t = T(), x = idx.map((i) => U_.exc[i]), y = idx.map((i) => U_.em[i]), st = idx.map((i) => U_.em[i] - U_.exc[i]), lo = Math.min(...x, ...y) - 10, hi = Math.max(...x, ...y) + 10;
          plot("gd-stokes", [{ type: "scatter", mode: "lines", name: "emissão = excitação", x: [lo, hi], y: [lo, hi], line: { color: t.muted, dash: "dot", width: 1.2 }, hoverinfo: "skip" },
            { type: "scatter", mode: "markers", name: "aglomerado relatado", x, y, customdata: st, marker: { size: 7, color: t.cat[0], opacity: 0.7, line: { width: 1, color: t.surface } }, hovertemplate: "excitação %{x} nm → emissão %{y} nm<br>Stokes %{customdata} nm<extra></extra>" }],
            { xaxis: { title: { text: "excitação (nm)" } }, yaxis: { title: { text: "emissão (nm)" } }, legend: { y: 1.12 } });
          $("#stokes-txt").innerHTML = `<p>${ni(x.length)} aglomerados. Todos ficam acima da diagonal: a luz emitida tem comprimento de onda maior (menos energia) que a de excitação. Deslocamento de Stokes mediano: <b>${nf(median(st), 0)} nm</b> (metade entre ${nf(quant(st, 0.25), 0)} e ${nf(quant(st, 0.75), 0)} nm). A distância vertical até a diagonal é o deslocamento de cada ponto.</p>`; };
        drawer(draw); } }
    // pesos de propensão: antes × depois
    { const E_ = A.causal.effects, el = wrap("ipw", `<div class="ctl"><label for="gd-pe">Efeito</label><select id="gd-pe">${E_.map((e, i) => `<option value="${i}">${esc(e.name)}</option>`).join("")}</select></div><label class="toggle" for="gd-pw"><input type="checkbox" id="gd-pw"> aplicar os pesos (1/e e 1/(1 − e))</label>`, [["gd-ipw"]]);
      if (el) { const hist = (v, w) => { const c = new Array(25).fill(0); v.forEach((x, i) => { const j = Math.min(24, Math.max(0, Math.floor(x * 25))); c[j] += w[i]; }); const s = c.reduce((a, b) => a + b, 0) || 1; return c.map((x) => x / s * 25); };
        const draw = () => { const t = T(), e = E_[+$("#gd-pe").value], on = $("#gd-pw").checked, cl = (x) => Math.min(0.98, Math.max(0.02, x)), tr = e.propensity.treated, ct = e.propensity.control;
          const ht = hist(tr, tr.map((x) => (on ? 1 / cl(x) : 1))), hc = hist(ct, ct.map((x) => (on ? 1 / (1 - cl(x)) : 1))), mid = ht.map((_, j) => (j + 0.5) / 25);
          const ov = ht.reduce((a, x, j) => a + Math.min(x, hc[j]), 0) / 25;
          plot("gd-ipw", [{ type: "bar", name: "tratados", x: mid, y: ht, marker: { color: hexA(t.cat[1], 0.65) }, hovertemplate: "e ≈ %{x:.2f}: densidade %{y:.2f}<extra>tratados</extra>" },
            { type: "bar", name: "controles", x: mid, y: hc, marker: { color: hexA(t.cat[0], 0.65) }, hovertemplate: "e ≈ %{x:.2f}: densidade %{y:.2f}<extra>controles</extra>" }],
            { barmode: "overlay", bargap: 0.04, xaxis: { title: { text: "escore de propensão e (chance de receber o tratamento)" }, range: [0, 1] }, yaxis: { title: { text: on ? "densidade ponderada" : "densidade" } }, legend: { y: 1.12 } });
          $("#ipw-txt").innerHTML = `<p>${esc(e.name)}: ${ni(e.n_treated)} tratados e ${ni(e.n - e.n_treated)} controles (amostra para o gráfico). ${on ? "Com os pesos, cada síntese \"rara\" para o seu grupo vale por várias, e as duas distribuições se aproximam: os grupos ficam comparáveis, como num sorteio." : "Sem pesos, tratados têm escores mais altos que os controles: os grupos diferem antes mesmo do tratamento."} Sobreposição das duas distribuições: <b>${nf(100 * ov, 0)} %</b>. Marque e desmarque a caixa para comparar.</p>`; };
        $("#gd-pe").addEventListener("change", draw); $("#gd-pw").addEventListener("change", draw); drawer(draw); } }
  }

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
      // replicação por base
      const yR = [], xR = [], rlo = [], rhi = [], cR = [], sz = [], cd = [];
      E.forEach((e) => { const R = e.replication; if (!R || !R.bases.length) return;
        R.bases.forEach((b) => { yR.push(`${e.name} · ${b.base}`); xR.push(b.estimate); rlo.push(b.estimate - b.ci95[0]); rhi.push(b.ci95[1] - b.estimate);
          cR.push(b.base.startsWith("Cruse") ? t.cat[0] : t.cat[3] || t.cat[2]); sz.push(9); cd.push(`${ni(b.n)} registros, ${ni(b.n_articles)} artigos`); });
        if (R.pooled) { yR.push(`${e.name} · combinado`); xR.push(R.pooled); rlo.push(R.pooled - R.pooled_ci95[0]); rhi.push(R.pooled_ci95[1] - R.pooled);
          cR.push(t.ruby); sz.push(13); cd.push(`efeitos aleatórios · I² = ${nf(100 * R.I2, 0)} % · Q ${pf(R.Q_p)}`); } });
      plot("ca-rep", [{ type: "scatter", mode: "markers", x: xR, y: yR, customdata: cd,
        error_x: { type: "data", symmetric: false, array: rhi, arrayminus: rlo, color: t.ink2, thickness: 1.4, width: 5 },
        marker: { size: sz, color: cR, symbol: sz.map((v) => (v > 10 ? "diamond" : "circle")), line: { width: 1.5, color: t.surface } },
        hovertemplate: "%{y}: %{x:.2f}<br>%{customdata}<extra></extra>" }],
      { xaxis: { type: "log", title: { text: "efeito (razão; 1 = nenhum efeito)" }, tickvals: [0.1, 0.2, 0.5, 1, 2, 5] }, yaxis: { autorange: "reversed", automargin: true },
        margin: { l: 300 }, showlegend: false, shapes: [{ type: "line", x0: 1, x1: 1, yref: "paper", y0: 0, y1: 1, line: { color: t.ink, width: 1, dash: "dot" } }] });
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
      const reps = E.filter((e) => e.replication && e.replication.pooled), sameDir = reps.filter((e) => e.replication.same_direction).length,
        bothSig = reps.filter((e) => e.replication.both_significant).length, nspBigger = reps.filter((e) => Math.abs(Math.log(e.replication.bases[1].estimate)) > Math.abs(Math.log(e.replication.bases[0].estimate))).length;
      $("#ca-rep-txt").innerHTML = `<p><b>${sameDir} de ${reps.length}</b> efeitos têm a mesma direção nas duas bases e <b>${bothSig}</b> são significativos em ambas. ` +
        `As magnitudes diferem (I² de ${nf(100 * Math.min(...reps.map((e) => e.replication.I2)), 0)} a ${nf(100 * Math.max(...reps.map((e) => e.replication.I2)), 0)} %), e o NSP dá o efeito mais forte em ${nspBigger} de ${reps.length}. ` +
        "É o esperado por diluição: no Cruse o tamanho é um só por artigo e se repete nos parágrafos, então parte dos registros recebe o tamanho de outra síntese do mesmo artigo, o que puxa o contraste para 1 (erro de medida no desfecho). " +
        "A direção, que é o que a literatura prevê, é robusta; a magnitude depende da fonte, e por isso o combinado usa efeitos aleatórios e tem IC mais largo.</p>";
    }
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
    const winsHolm = Object.values(B.datasets).filter((x) => x.paired["GP-EI"].p_holm < 0.05 && x.paired["GP-EI"].wins > x.paired["GP-EI"].losses).length;
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
        "reexecução com as medidas reais como oráculo; Wilcoxon pareado pela partida comum, Holm nas 15 comparações; Kaplan–Meier e RMST",
        `GP-EI melhor que o acaso em <b>${wins} de ${Object.keys(B.datasets).length}</b> campanhas (${winsHolm} após Holm); nas demais, empate`],
      variabilidade: [`${ni(V.agnp.n_measurements)} réplicas AgNP, ${ni(V.turkevich.n_papers)} artigos de Turkevich, ${ni(V.aunc_generalization.n_papers)} artigos de AuNC`,
        "Brown–Forsythe, ICC, um valor por artigo, validação agrupada por artigo",
        `mesma rota: <b>${nf(V.turkevich.q10_q90[0], 1)}–${nf(V.turkevich.q10_q90[1], 1)} nm</b>; R² cai de ${nf(V.aunc_generalization.r2_random, 2)} para ${nf(V.aunc_generalization.r2_new_paper, 2)} em artigo novo`],
      causal: [`${ni(Math.max(...C.effects.map((e) => e.n)))} sínteses de Cruse 2022 e NSP 2026 (a base de AuNC, selecionada pelo produto, fica fora)`,
        "grafo mecanístico; AIPW duplamente robusto, conferido por IPW, entropia e aparo; bootstrap de artigos; E-value",
        `<b>${C.effects.filter((e) => e.verdict.startsWith("confirma")).length} de ${C.effects.length}</b> efeitos na direção da literatura; ${C.effects.filter((e) => e.robust).length} robustos`],
      preditor: [`${ni(A.predictor.n)} sínteses de ${ni(A.predictor.n_articles)} artigos, ${ni(A.predictor.recipes.length)} receitas distintas`,
        "regressão quantílica com árvores, conformalizada por artigo (CQR), avaliada no próprio navegador",
        `intervalo de 90 % cobre <b>${nf(100 * A.predictor.bands["90"].coverage_articles, 0)} %</b> dos artigos novos; largura típica ×${nf(A.predictor.bands["90"].median_fold_width, 0)}`],
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
    addGuideLinks();
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
