/* AuGOSintesIA — painel interativo (Plotly). Dados em window.AUGO, gerados por code/webapp/build_site.py. */
(function () {
  "use strict";
  const A = window.AUGO || {};
  const $ = (s, r) => (r || document).querySelector(s);
  const nf = (x, d = 1) => (x == null || !isFinite(x)) ? "—" :
    Number(x).toLocaleString("pt-BR", { minimumFractionDigits: d, maximumFractionDigits: d });
  const ni = (x) => (x == null || !isFinite(x)) ? "—" : Math.round(x).toLocaleString("pt-BR");
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

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
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  }
  function tok(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }
  function T() {
    const dark = isDark();
    const seq = dark ? SEQ.slice().reverse() : SEQ;     // no escuro, "perto de zero" recua para a superfície escura
    return {
      dark, cat: dark ? CAT.dark : CAT.light,
      seqScale: seq.map((c, i) => [i / (seq.length - 1), c]),
      divScale: [[0, dark ? "#3987e5" : "#2a78d6"], [0.5, dark ? "#383835" : "#f0efec"], [1, dark ? "#e66767" : "#e34948"]],
      surface: tok("--surface"), ink: tok("--ink"), ink2: tok("--ink-2"), muted: tok("--muted"),
      line: tok("--line"), lineStrong: tok("--line-strong"), ruby: tok("--ruby"), gold: tok("--gold"),
      other: dark ? "#6b6870" : "#a9a5ad",
    };
  }
  function layout(extra) {
    const t = T();
    const ax = { gridcolor: t.line, linecolor: t.lineStrong, zeroline: false, tickfont: { color: t.muted, size: 11 },
      title: { font: { color: t.ink2, size: 12 } }, automargin: true };
    const base = {
      paper_bgcolor: t.surface, plot_bgcolor: t.surface,
      font: { family: '"IBM Plex Sans", system-ui, sans-serif', color: t.ink2, size: 12 },
      margin: { l: 56, r: 18, t: 12, b: 48 }, hovermode: "closest",
      hoverlabel: { bgcolor: t.surface, bordercolor: t.lineStrong, font: { color: t.ink, family: '"IBM Plex Sans", sans-serif' } },
      legend: { orientation: "h", y: 1.08, x: 0, font: { color: t.ink2, size: 11 }, bgcolor: "rgba(0,0,0,0)" },
      xaxis: Object.assign({}, ax), yaxis: Object.assign({}, ax),
    };
    return deepMerge(base, extra || {});
  }
  function scene(x, y, z, extra) {
    const t = T();
    const ax = (title) => ({ title: { text: title, font: { color: t.ink2, size: 12 } }, gridcolor: t.line,
      linecolor: t.lineStrong, zerolinecolor: t.line, backgroundcolor: t.surface, showbackground: true,
      tickfont: { color: t.muted, size: 10 } });
    return deepMerge({ xaxis: ax(x), yaxis: ax(y), zaxis: ax(z), bgcolor: t.surface,
      camera: { eye: { x: 1.55, y: -1.55, z: 0.95 } }, aspectmode: "cube" }, extra || {});
  }
  function deepMerge(a, b) {
    const o = Array.isArray(a) ? a.slice() : Object.assign({}, a);
    for (const k of Object.keys(b)) {
      if (b[k] && typeof b[k] === "object" && !Array.isArray(b[k]) && a[k] && typeof a[k] === "object") o[k] = deepMerge(a[k], b[k]);
      else o[k] = b[k];
    }
    return o;
  }
  // na página única publicada (visualizador sem permissão de download) o botão "baixar PNG" não funcionaria
  const CFG = { displaylogo: false, responsive: true,
    modeBarButtonsToRemove: ["lasso2d", "select2d", "autoScale2d"].concat(window.AUGO_EMBED ? ["toImage"] : []) };
  function plot(id, data, lay) {
    const el = document.getElementById(id);
    if (!el || !window.Plotly) return;
    Plotly.react(el, data, layout(lay), CFG);
  }
  function kpis(id, items) {
    $(id).innerHTML = items.map((k) => `<div class="kpi${k.key ? " key" : ""}"><span class="k">${k.k}</span>` +
      `<span class="v">${k.v}${k.u ? `<span class="u">${k.u}</span>` : ""}</span>${k.s ? `<span class="s">${k.s}</span>` : ""}</div>`).join("");
  }
  const lin = (a, b, n) => Array.from({ length: n }, (_, i) => a + (b - a) * i / (n - 1));
  const median = (v) => { const s = v.filter((x) => x != null && isFinite(x)).sort((a, b) => a - b); if (!s.length) return NaN; const m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };
  const quant = (v, q) => { const s = v.filter((x) => x != null && isFinite(x)).sort((a, b) => a - b); if (!s.length) return NaN; const p = (s.length - 1) * q, i = Math.floor(p); return s[i] + (s[Math.min(i + 1, s.length - 1)] - s[i]) * (p - i); };
  function interp(x, xs, ys) {
    if (x <= xs[0]) return ys[0];
    if (x >= xs[xs.length - 1]) return ys[ys.length - 1];
    let lo = 0, hi = xs.length - 1;
    while (hi - lo > 1) { const m = (lo + hi) >> 1; if (xs[m] <= x) lo = m; else hi = m; }
    const f = (x - xs[lo]) / (xs[hi] - xs[lo]);
    return ys[lo] + f * (ys[hi] - ys[lo]);
  }
  function peakOf(w, e, lo = 480) {                           // máximo acima de lo, refinado por parábola (= analyses._peak)
    let i = -1; for (let j = 0; j < w.length; j++) if (w[j] >= lo && (i < 0 || e[j] > e[i])) i = j;
    if (i <= 0 || i >= w.length - 1 || w[i - 1] < lo) return w[i];
    const den = e[i - 1] - 2 * e[i] + e[i + 1];
    return w[i] + (den ? 0.5 * (e[i - 1] - e[i + 1]) / den : 0) * (w[i + 1] - w[i]);
  }
  const PT = { normal: { pdf: (z) => Math.exp(-0.5 * z * z) / Math.sqrt(2 * Math.PI) } };
  function ncdf(z) { const t = 1 / (1 + 0.2316419 * Math.abs(z)); const d = PT.normal.pdf(z);
    const p = d * t * (0.319381530 + t * (-0.356563782 + t * (1.781477937 + t * (-1.821255978 + t * 1.330274429))));
    return z > 0 ? 1 - p : p; }

  /* ------------------------------------------------------------------ abas */
  const TABS = [["visao", "Visão geral", ""], ["literatura", "Literatura", "4.1"], ["optica", "Óptica e J", "4.4"],
    ["designer", "AuNP Designer", "4.5"], ["aprendizado", "Aprendizado ativo", "4.15"],
    ["interpretabilidade", "Interpretabilidade", "4.13"], ["variabilidade", "Variabilidade", "4.17"],
    ["causal", "Causalidade", "4.9"], ["caracterizacao", "Caracterização", "4.2"], ["sobre", "Sobre e dados", ""]];
  const rendered = {};
  const RENDER = {};
  function show(id) {
    if (!TABS.some((t) => t[0] === id)) id = "visao";
    for (const [t] of TABS) {
      const p = document.getElementById("p-" + t), b = document.getElementById("t-" + t);
      p.hidden = t !== id; b.setAttribute("aria-selected", t === id ? "true" : "false"); b.tabIndex = t === id ? 0 : -1;
    }
    const tb = document.getElementById("t-" + id), bar = $("#tabs");
    if (bar.scrollWidth > bar.clientWidth) bar.scrollTo({ left: tb.offsetLeft - bar.clientWidth / 2 + tb.offsetWidth / 2, behavior: "smooth" });
    if (!rendered[id] && RENDER[id]) { RENDER[id](); rendered[id] = true; }
    else document.querySelectorAll(`#p-${id} .js-plotly-plot`).forEach((el) => Plotly.Plots.resize(el));
    try { localStorage.setItem("augo-tab", id); } catch (e) { /* armazenamento indisponível */ }
  }
  function buildTabs() {
    $("#tabs").innerHTML = TABS.map(([id, label, sec]) =>
      `<a class="tab" role="tab" id="t-${id}" href="#${id}" aria-controls="p-${id}">${label}${sec ? ` <small>§${sec}</small>` : ""}</a>`).join("");
    $("#tabs").addEventListener("keydown", (e) => {
      if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
      const ids = TABS.map((t) => t[0]), cur = ids.findIndex((i) => document.getElementById("t-" + i).getAttribute("aria-selected") === "true");
      const nxt = ids[(cur + (e.key === "ArrowRight" ? 1 : ids.length - 1)) % ids.length];
      location.hash = nxt; document.getElementById("t-" + nxt).focus();
    });
    window.addEventListener("hashchange", () => show(location.hash.slice(1)));
  }
  function rerenderAll() { for (const k of Object.keys(rendered)) rendered[k] = false; show((location.hash || "#visao").slice(1)); }

  /* ================================================================== visão geral */
  RENDER.visao = function () {
    const O = A.overview, op = A.optics, k = O.kpis;
    // Mie: superfície (λ × log d)
    const t = T();
    plot("ov-hero", [{ type: "surface", x: op.wl, y: op.d.map(Math.log10), z: op.C_ext, colorscale: t.seqScale, showscale: false,
      contours: { z: { show: false } }, hovertemplate: "λ = %{x} nm<br>d = %{customdata:.1f} nm<br>extinção rel. %{z:.2f}<extra></extra>",
      customdata: op.d.map((d) => op.wl.map(() => d)) }],
    { margin: { l: 0, r: 0, t: 0, b: 0 }, scene: scene("λ (nm)", "log₁₀ d (nm)", "extinção normalizada",
      { camera: { eye: { x: -1.6, y: -1.35, z: 0.85 } } }) });
    kpis("#ov-kpis", [
      { k: "Sínteses de ouro na literatura", v: ni(k.literature_records), s: `${ni(k.literature_dois)} DOIs · ${ni(k.go_records)} com GO/rGO` },
      { k: "Medidas da campanha AgNP", v: ni(k.agnp_measurements), s: `${ni(k.agnp_conditions)} condições com réplicas` },
      { k: "Designer: R² em validação cruzada", v: nf(k.designer_cv_r2, 2), s: `cobertura do IC 95 %: ${nf(100 * k.designer_coverage, 0)} %`, key: true },
      { k: "Mie × LSPR medido", v: nf(k.mie_median_abs_residual, 1), u: "nm", s: `erro mediano em ${ni(k.mie_validation_n)} esferas` },
      { k: "NaBH₄ × citrato: tamanho", v: "×" + nf(k.causal_ratio, 2), s: `IC 95 % ${nf(k.causal_ci[0], 2)}–${nf(k.causal_ci[1], 2)} (IPW)` },
      { k: `Mesma rota em ${ni(k.turkevich_papers)} artigos`, v: "×" + nf(k.turkevich_fold, 2), s: "fator de 1 dp no tamanho (Turkevich)" },
    ]);
    const st = { experimental: ["exp", "dados experimentais"], parcial: ["par", "parcial"], laboratorio: ["lab", "aguarda o laboratório"] };
    $("#ov-map").innerHTML = O.map.map((m) => `<a href="#${m.tab}" title="${esc(m.note || "")}"><span class="n">§${m.sec}</span>` +
      `<span class="t">${esc(m.title)}</span><span class="st ${st[m.status][0]}">● ${st[m.status][1]}${m.note ? " — " + esc(m.note) : ""}</span></a>`).join("");
    const B = A.benchmark, names = Object.keys(B.datasets);
    plot("ov-bench", B.arms.map((arm, i) => ({ type: "scatter", mode: "markers", name: arm, y: names,
      x: names.map((n) => B.datasets[n].reach_top5[arm].median_experiments),
      marker: { size: 11, color: t.cat[i], line: { width: 2, color: t.surface } },
      hovertemplate: `${arm}<br>%{y}: %{x:.0f} experimentos<extra></extra>` })),
    { xaxis: { title: { text: "experimentos (mediana)" }, rangemode: "tozero" }, margin: { l: 110 }, legend: { y: 1.18 } });
    const src = [["Literatura (Cruse, NSP, AuNC)", k.literature_records], ["AuNC (fluorescência)", k.aunc_entries]]
      .concat(Object.entries(O.benchmark_measurements)).sort((a, b) => b[1] - a[1]);
    plot("ov-sources", [{ type: "bar", orientation: "h", y: src.map((s) => s[0]), x: src.map((s) => s[1]),
      marker: { color: t.cat[0] }, hovertemplate: "%{y}: %{x:,} registros<extra></extra>" }],
    { xaxis: { type: "log", title: { text: "registros" }, dtick: 1 }, yaxis: { autorange: "reversed" }, margin: { l: 170 } });
  };

  /* ================================================================== literatura */
  RENDER.literatura = function () {
    const L = A.literature, R = L.records, n = R.size.length;
    const sel = (id, opts, keep) => { const s = $(id); s.innerHTML = keep + opts.map(([v, l]) => `<option value="${v}">${esc(l)}</option>`).join(""); };
    sel("#lit-src", L.sources.map((s, i) => [i, s]), '<option value="-1">Todas</option>');
    sel("#lit-red", L.reductants.map((s, i) => [i, s.replace(/_/g, " ")]), '<option value="-2">Todos</option><option value="-1">não citado</option>');
    sel("#lit-morph", L.morph.map((s, i) => [i, s]), '<option value="-2">Todas</option>');
    const RED3 = ["citrato", "NaBH₄", "ácido ascórbico"];
    function idx() {
      const s = +$("#lit-src").value, r = +$("#lit-red").value, m = +$("#lit-morph").value, sd = +$("#lit-seed").value, go = $("#lit-go").checked;
      const out = [];
      for (let i = 0; i < n; i++) {
        if (s >= 0 && R.source[i] !== s) continue;
        if (r !== -2 && R.red[i] !== r) continue;
        if (m !== -2 && R.morph[i] !== m) continue;
        if (sd >= 0 && R.seed[i] !== sd) continue;
        if (go && !R.go[i]) continue;
        out.push(i);
      }
      return out;
    }
    function draw() {
      const t = T(), I = idx();
      const sizes = I.map((i) => R.size[i]).filter((x) => x != null), peaks = I.map((i) => R.peak[i]).filter((x) => x != null);
      kpis("#lit-kpis", [
        { k: "Registros na seleção", v: ni(I.length), s: `${ni(sizes.length)} com tamanho` },
        { k: "Tamanho mediano", v: nf(median(sizes), 1), u: "nm", s: `quartis ${nf(quant(sizes, .25), 0)}–${nf(quant(sizes, .75), 0)} nm` },
        { k: "Pico de absorção mediano", v: nf(median(peaks), 0), u: "nm", s: `${ni(peaks.length)} registros` },
        { k: "Rota mediada por sementes", v: nf(100 * I.filter((i) => R.seed[i]).length / Math.max(I.length, 1), 1), u: "%" },
      ]);
      // 3D
      const tri = I.filter((i) => R.size[i] != null && R.peak[i] != null && R.T[i] != null);
      const groups = [0, 1, 2, -9].map((g) => tri.filter((i) => g === -9 ? !(R.red[i] >= 0 && R.red[i] <= 2) : R.red[i] === g));
      plot("lit-3d", groups.map((g, k) => ({ type: "scatter3d", mode: "markers", name: k < 3 ? RED3[k] : "outros",
        x: g.map((i) => R.T[i]), y: g.map((i) => Math.log10(R.size[i])), z: g.map((i) => R.peak[i]),
        customdata: g.map((i) => [R.size[i], L.sources[R.source[i]]]),
        marker: { size: 3.6, color: k < 3 ? t.cat[k] : t.other, opacity: 0.85, line: { width: 0 } },
        hovertemplate: "T = %{x:.0f} °C<br>d = %{customdata[0]:.1f} nm<br>pico = %{z:.0f} nm<br>%{customdata[1]}<extra></extra>" })),
      { margin: { l: 0, r: 0, t: 30, b: 0 }, scene: scene("T (°C)", "log₁₀ tamanho (nm)", "pico (nm)", { camera: { eye: { x: 1.25, y: -1.3, z: 0.7 } } }) });
      // histograma em log
      const lv = sizes.filter((x) => x > 0).map(Math.log10), edges = lin(-0.3, 3, 45), cnt = new Array(44).fill(0);
      for (const v of lv) { const j = Math.floor((v - edges[0]) / (edges[1] - edges[0])); if (j >= 0 && j < 44) cnt[j]++; }
      const mid = edges.slice(0, -1).map((e) => e + (edges[1] - edges[0]) / 2);
      plot("lit-hist", [{ type: "bar", x: mid, y: cnt, marker: { color: t.cat[0] }, width: (edges[1] - edges[0]) * 0.92,
        customdata: mid.map((m) => Math.pow(10, m)), hovertemplate: "≈ %{customdata:.1f} nm: %{y} registros<extra></extra>" }],
      { xaxis: { title: { text: "tamanho (nm)" }, tickvals: [0, 0.477, 1, 1.477, 2, 2.477, 3], ticktext: ["1", "3", "10", "30", "100", "300", "1000"] },
        yaxis: { title: { text: "registros" } }, bargap: 0,
        shapes: sizes.length ? [{ type: "line", x0: Math.log10(median(sizes)), x1: Math.log10(median(sizes)), y0: 0, y1: 1, yref: "paper", line: { color: t.ink, width: 1.5 } }] : [],
        annotations: sizes.length ? [{ x: Math.log10(median(sizes)), y: 1, yref: "paper", text: `mediana ${nf(median(sizes), 1)} nm`, showarrow: false, xanchor: "left", xshift: 6, font: { color: t.ink, size: 11 } }] : [] });
      const mc = L.morph.map((_, j) => I.filter((i) => R.morph[i] === j).length);
      const ord = mc.map((c, j) => [c, j]).filter((x) => x[0] > 0).sort((a, b) => b[0] - a[0]).slice(0, 8);
      plot("lit-morph-bar", [{ type: "bar", orientation: "h", y: ord.map((o) => L.morph[o[1]]), x: ord.map((o) => o[0]),
        marker: { color: t.cat[0] }, hovertemplate: "%{y}: %{x} registros<extra></extra>" }],
      { yaxis: { autorange: "reversed" }, margin: { l: 80, t: 4, b: 30 }, xaxis: { title: { text: "" } } });
    }
    ["#lit-src", "#lit-red", "#lit-morph", "#lit-seed", "#lit-go"].forEach((s) => $(s).addEventListener("change", draw));
    draw();
    // redutores por ano (participação)
    const t = T(), Y = L.reductant_by_year, years = Y.years, tot = years.map((_, i) => Object.values(Y.series).reduce((s, v) => s + v[i], 0));
    const keep = years.map((_, i) => tot[i] >= 40);
    const names = [["trisodium_citrate", "citrato"], ["NaBH4", "NaBH₄"], ["ascorbic_acid", "ácido ascórbico"]];
    const tr = names.map(([key, lab], k) => ({ type: "scatter", mode: "lines+markers", name: lab,
      x: years.filter((_, i) => keep[i]), y: years.map((_, i) => 100 * (Y.series[key] || [])[i] / tot[i]).filter((_, i) => keep[i]),
      line: { color: t.cat[k], width: 2 }, marker: { size: 6, color: t.cat[k] }, hovertemplate: `${lab}: %{y:.1f} % (%{x})<extra></extra>` }));
    plot("lit-years", tr, { yaxis: { title: { text: "% das sínteses do ano" }, rangemode: "tozero" }, xaxis: { title: { text: "ano de publicação" } } });
    // tabela GO
    const rows = L.go_rows;
    function table(q) {
      q = (q || "").toLowerCase();
      const f = rows.filter((r) => !q || [r.doi, r.title, r.reductants, r.supports, r.morph].join(" ").toLowerCase().includes(q));
      $("#go-tbl").innerHTML = "<thead><tr><th>Ano</th><th>Artigo / DOI</th><th>Redutores</th><th>Suporte</th><th>Morfologia</th><th class='num'>Tamanho (nm)</th><th class='num'>T (°C)</th></tr></thead><tbody>" +
        f.map((r) => `<tr><td class="num">${r.year || "—"}</td><td>${esc(r.title || r.source)}${r.doi ? `<br><a href="https://doi.org/${esc(r.doi)}" target="_blank" rel="noopener">${esc(r.doi)}</a>` : ""}</td>` +
          `<td>${esc(r.reductants.replace(/\|/g, ", ").replace(/_/g, " "))}</td><td>${esc(r.supports.replace(/\|/g, ", ").replace(/_/g, " "))}</td>` +
          `<td>${esc(r.morph.replace(/\|/g, ", "))}</td><td class="num">${r.size == null ? "—" : nf(r.size, 1)}</td><td class="num">${r.T == null ? "—" : nf(r.T, 0)}</td></tr>`).join("") + "</tbody>";
    }
    $("#go-q").addEventListener("input", (e) => table(e.target.value));
    table("");
  };

  /* ================================================================== óptica e J */
  RENDER.optica = function () {
    const O = A.optics, wl = O.wl, dg = O.d, ld = dg.map(Math.log);
    const C = O.C_ext.map((row, i) => row.map((v) => v * O.C_ext_max[i]));      // nm² por partícula
    const vol = dg.map((d) => Math.PI * d * d * d / 6);
    const tg = O.target, gridW = []; for (let w = tg.grid[0]; w <= tg.grid[1] + 1e-9; w += tg.grid[2]) gridW.push(w);
    const tgOnGrid = gridW.map((w) => interp(w, tg.wl, tg.E)), tmax = Math.max(...tgOnGrid), tN = tgOnGrid.map((v) => v / tmax);
    let mode = "max";
    const dOf = () => 2 * Math.exp(+$("#op-d").value / 1000 * Math.log(75)), sOf = () => +$("#op-s").value / 100;
    function ensemble(d, s) {
      const w = new Array(dg.length).fill(0);
      if (s <= 0.005) {                                         // monodisperso: interpola em log d entre os vizinhos
        let j = 0; while (j < ld.length - 2 && ld[j + 1] < Math.log(d)) j++;
        const f = Math.min(1, Math.max(0, (Math.log(d) - ld[j]) / (ld[j + 1] - ld[j]))); w[j] = 1 - f; w[j + 1] = f; }
      else { const sl = Math.sqrt(Math.log(1 + s * s)), mu = Math.log(d) - sl * sl / 2; let tot = 0;
        ld.forEach((l, i) => { w[i] = Math.exp(-0.5 * ((l - mu) / sl) ** 2); tot += w[i]; }); w.forEach((_, i) => { w[i] /= tot; }); }
      const E = wl.map((_, j) => w.reduce((acc, wi, i) => acc + wi * C[i][j], 0));
      const V = w.reduce((acc, wi, i) => acc + wi * vol[i], 0);
      return { E, V };
    }
    function J(E) {
      const e = gridW.map((w) => interp(w, wl, E)), m = Math.max(...e);
      let acc = 0; for (let i = 0; i < e.length; i++) acc += ((e[i] / m - tN[i]) / tg.s_m) ** 2;
      return acc / e.length;
    }
    function draw() {
      const t = T(), d = dOf(), s = sOf(), { E, V } = ensemble(d, s);
      $("#op-d-o").textContent = nf(d, d < 10 ? 1 : 0) + " nm"; $("#op-s-o").textContent = nf(100 * s, 0) + " %";
      const pk = [peakOf(wl, E)];
      const j = J(E);
      kpis("#op-kpis", [
        { k: "λ do LSPR previsto", v: nf(pk[0], 0), u: "nm", s: "máximo acima de 480 nm" },
        { k: "Perda J (Eq. 1)", v: j < 0.01 ? "< 0,01" : nf(j, j < 10 ? 2 : j < 100 ? 1 : 0), s: `log₁₀ J = ${nf(Math.log10(j), 2)}`, key: true },
        { k: "Especificação (rascunho)", v: j <= 1 ? "atende" : "não atende", s: "J ≤ 1 no pré-registro" },
        { k: "Extinção por volume de Au", v: nf(Math.max(...E) / V, 3), u: "nm⁻¹", s: "Cext,máx / V — partículas pequenas absorvem menos por átomo" },
      ]);
      const y = mode === "max" ? E.map((v) => v / Math.max(...E)) : E.map((v) => v / V);
      const tr = [{ type: "scatter", mode: "lines", name: `previsto (d = ${nf(d, 0)} nm, σ = ${nf(100 * s, 0)} %)`, x: wl, y,
        line: { color: t.cat[0], width: 2.4 }, hovertemplate: "λ = %{x} nm: %{y:.3f}<extra>previsto</extra>" }];
      if (mode === "max") tr.push({ type: "scatter", mode: "lines", name: `alvo do pré-registro (${tg.diameter} nm)`, x: gridW, y: tN,
        line: { color: t.ink, width: 1.6, dash: "solid" }, hovertemplate: "λ = %{x} nm: %{y:.3f}<extra>alvo</extra>" });
      plot("op-spec", tr, { xaxis: { title: { text: "λ (nm)" } }, yaxis: { title: { text: mode === "max" ? "extinção normalizada" : "Cext / V (nm⁻¹)" }, rangemode: "tozero" } });
      // superfície com a linha do diâmetro escolhido
      const k = ld.reduce((b, l, i) => (Math.abs(l - Math.log(d)) < Math.abs(ld[b] - Math.log(d)) ? i : b), 0);
      plot("op-surf", [{ type: "surface", x: wl, y: dg.map(Math.log10), z: O.C_ext, colorscale: t.seqScale, showscale: false, opacity: 0.96,
        hovertemplate: "λ = %{x} nm<br>log₁₀ d = %{y:.2f}<br>%{z:.2f}<extra></extra>" },
      { type: "scatter3d", mode: "lines", x: wl, y: wl.map(() => Math.log10(dg[k])), z: O.C_ext[k].map((v) => v + 0.01), line: { color: t.ruby, width: 7 }, hoverinfo: "skip", showlegend: false }],
      { margin: { l: 0, r: 0, t: 0, b: 0 }, scene: scene("λ (nm)", "log₁₀ d (nm)", "extinção", { camera: { eye: { x: -1.5, y: -1.5, z: 0.9 } } }) });
      // superfície J
      const JS = O.J_surface;
      plot("op-J", [{ type: "surface", x: JS.d.map(Math.log10), y: JS.sigma, z: JS.log10J, colorscale: t.seqScale, reversescale: true, showscale: false,
        hovertemplate: "d = %{customdata:.1f} nm<br>σ = %{y:.2f}<br>log₁₀ J = %{z:.2f}<extra></extra>", customdata: JS.sigma.map(() => JS.d) },
      { type: "scatter3d", mode: "markers", x: [Math.log10(d)], y: [s], z: [Math.log10(j)], marker: { size: 7, color: t.ruby, line: { width: 2, color: t.surface } },
        hovertemplate: "escolha atual<br>log₁₀ J = %{z:.2f}<extra></extra>", showlegend: false }],
      { margin: { l: 0, r: 0, t: 0, b: 0 }, scene: scene("log₁₀ d (nm)", "σ", "log₁₀ J") });
    }
    $("#op-d").value = Math.round(Math.log(tg.diameter / 2) / Math.log(75) * 1000);
    $("#op-s").value = Math.round(100 * tg.sigma);                      // começa no alvo: J ≈ 0
    ["#op-d", "#op-s"].forEach((s) => $(s).addEventListener("input", draw));
    $("#op-norm").addEventListener("click", (e) => { const b = e.target.closest("button"); if (!b) return; mode = b.dataset.v;
      $("#op-norm").querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", x === b ? "true" : "false")); draw(); });
    draw();
    // validação contra medidas
    const t = T(), V = O.lit_spheres, srcs = [...new Set(V.source)];
    plot("op-valid", srcs.map((s, k) => {
      const I = V.source.map((x, i) => (x === s ? i : -1)).filter((i) => i >= 0);
      return { type: "scattergl", mode: "markers", name: s, x: I.map((i) => V.size[i]), y: I.map((i) => V.peak[i]),
        customdata: I.map((i) => V.doi[i] || "—"), marker: { size: 6, color: t.cat[k], opacity: 0.7, line: { width: 1, color: t.surface } },
        hovertemplate: "d = %{x:.1f} nm · pico %{y:.0f} nm<br>%{customdata}<extra>" + s + "</extra>" };
    }).concat([{ type: "scatter", mode: "lines", name: "Mie (Johnson & Christy, σ = 10 %)", x: O.lspr_curve.d, y: O.lspr_curve.lambda,
      line: { color: t.ink, width: 2.2 }, hovertemplate: "Mie: d = %{x:.1f} nm → %{y:.0f} nm<extra></extra>" }]),
    { xaxis: { type: "log", title: { text: "tamanho relatado (nm)" }, range: [Math.log10(2.5), Math.log10(160)], tickvals: [3, 5, 10, 20, 50, 100, 150] },
      yaxis: { title: { text: "pico de absorção relatado (nm)" }, range: [495, 620] } });
    $("#op-bins").innerHTML = "<thead><tr><th>Faixa de tamanho</th><th class='num'>Registros</th><th class='num'>Resíduo mediano (nm)</th><th class='num'>Desvio absoluto mediano (nm)</th></tr></thead><tbody>" +
      V.by_bin.map((b) => `<tr><td>${b.range}</td><td class="num">${b.n}</td><td class="num">${nf(b.median_residual, 1)}</td><td class="num">${nf(b.mad, 1)}</td></tr>`).join("") +
      `<tr><td><b>Todas</b></td><td class="num">${V.n}</td><td class="num">—</td><td class="num">${nf(V.median_abs_residual, 1)} (|resíduo| mediano)</td></tr></tbody>`;
  };

  /* ================================================================== AuNP Designer (GP no navegador) */
  function gpPredict(gp, xn) {
    const X = gp.X, ls = gp.ls, n = X.length, k = new Array(n);
    for (let i = 0; i < n; i++) {
      let r2 = 0; for (let j = 0; j < ls.length; j++) { const d = (xn[j] - X[i][j]) / ls[j]; r2 += d * d; }
      const r = Math.sqrt(r2), s5 = Math.sqrt(5) * r;
      k[i] = gp.outputscale * (1 + s5 + 5 / 3 * r2) * Math.exp(-s5);
    }
    let mu = gp.const; for (let i = 0; i < n; i++) mu += k[i] * gp.alpha[i];
    const L = gp.L, v = new Array(n);                            // L v = k (substituição direta)
    let vv = 0;
    for (let i = 0; i < n; i++) { let s = k[i]; const Li = L[i]; for (let j = 0; j < i; j++) s -= Li[j] * v[j]; v[i] = s / Li[i]; vv += v[i] * v[i]; }
    const sd = Math.sqrt(Math.max(gp.outputscale - vv, 1e-12));
    return [gp.y_mean + gp.y_std * mu, gp.y_std * sd];
  }
  RENDER.designer = function () {
    const D = A.designer, gp = D.gp, p = D.columns.length, lo = D.lo, hi = D.hi;
    const bestLn = Math.min(...D.cv.obs);
    const box = $("#ds-sliders");
    box.innerHTML = D.labels.map((lab, j) => `<div class="ctl"><label for="ds-v${j}">${esc(lab)} <output id="ds-o${j}"></output></label>` +
      `<input type="range" id="ds-v${j}" min="${lo[j]}" max="${hi[j]}" step="${(hi[j] - lo[j]) / 200}" value="${D.best_measured.x[j]}"></div>`).join("");
    const opts = D.labels.map((l, j) => `<option value="${j}">${esc(l)}</option>`).join("");
    $("#ds-x").innerHTML = opts; $("#ds-y").innerHTML = opts; $("#ds-x").value = "3"; $("#ds-y").value = "0";
    let mode = "mean";
    const cur = () => D.labels.map((_, j) => +$("#ds-v" + j).value);
    const norm = (x) => x.map((v, j) => (v - lo[j]) / (hi[j] - lo[j]));
    function ei(mu, sd) { const z = (bestLn - mu) / sd; return (bestLn - mu) * ncdf(z) + sd * PT.normal.pdf(z); }
    function draw() {
      const t = T(), x = cur();
      x.forEach((v, j) => { $("#ds-o" + j).textContent = nf(v, j === 4 ? 0 : 1); });
      const [mu, sd] = gpPredict(gp, norm(x));
      // condição medida mais próxima (espaço normalizado)
      const P = D.points; let bi = 0, bd = 1e9;
      P.X.forEach((r, i) => { const dd = Math.hypot(...r.map((v, j) => (v - x[j]) / (hi[j] - lo[j]))); if (dd < bd) { bd = dd; bi = i; } });
      kpis("#ds-kpis", [
        { k: "Perda prevista no ponto", v: nf(Math.exp(mu), 3), s: `IC 95 % ${nf(Math.exp(mu - 1.96 * sd), 3)}–${nf(Math.exp(mu + 1.96 * sd), 3)}`, key: true },
        { k: "Melhor condição medida", v: nf(D.best_measured.loss, 3), s: `dp das réplicas ${nf(D.best_measured.sd, 3)}` },
        { k: "Condição medida mais próxima", v: nf(P.mean[bi], 3), s: `${P.n[bi]} réplicas · distância ${nf(bd, 2)}` },
        { k: "Validação cruzada", v: "R² " + nf(D.cv.r2, 2), s: `RMSE ln ${nf(D.cv.rmse, 3)} · cobertura ${nf(100 * D.cv.coverage95, 0)} %` },
        { k: "Melhoria esperada (EI)", v: nf(ei(mu, sd), 4), s: "sobre ln(perda), em relação à melhor medida" },
      ]);
      const ix = +$("#ds-x").value, iy = +$("#ds-y").value;
      const gx = lin(lo[ix], hi[ix], 34), gy = lin(lo[iy], hi[iy], 34);
      const Z = gy.map((yv) => gx.map((xv) => { const q = x.slice(); q[ix] = xv; q[iy] = yv; const [m, s] = gpPredict(gp, norm(q));
        return mode === "mean" ? Math.exp(m) : mode === "sd" ? s : ei(m, s); }));
      const ztitle = mode === "mean" ? "perda prevista" : mode === "sd" ? "dp de ln(perda)" : "EI";
      const tr = [{ type: "surface", x: gx, y: gy, z: Z, colorscale: t.seqScale, reversescale: mode === "mean", opacity: 0.95,
        colorbar: { title: { text: ztitle, side: "right", font: { color: t.ink2 } }, thickness: 12, len: 0.6, tickfont: { color: t.muted } },
        hovertemplate: `${D.labels[ix]} = %{x:.1f}<br>${D.labels[iy]} = %{y:.1f}<br>${ztitle} = %{z:.3f}<extra>GP</extra>` }];
      if (mode === "mean") tr.push({ type: "scatter3d", mode: "markers", name: "condições medidas", x: P.X.map((r) => r[ix]), y: P.X.map((r) => r[iy]),
        z: P.mean, customdata: P.n, marker: { size: 3.4, color: t.ruby, opacity: 0.9, line: { width: 0 } },
        hovertemplate: `medida: perda %{z:.3f} (%{customdata} réplicas)<extra></extra>` });
      plot("ds-surf", tr, { margin: { l: 0, r: 0, t: 0, b: 0 }, showlegend: false, scene: scene(D.labels[ix], D.labels[iy], ztitle) });
      // efeito de cada variável
      let ytop = 0;
      const traces = [], lay = { grid: { rows: 1, columns: p, pattern: "independent" }, showlegend: false, margin: { l: 50, r: 10, t: 26, b: 44 }, annotations: [] };
      D.labels.forEach((lab, j) => {
        const g = lin(lo[j], hi[j], 40), m = [], u = [], l2 = [];
        g.forEach((v) => { const q = x.slice(); q[j] = v; const [mm, ss] = gpPredict(gp, norm(q)); m.push(Math.exp(mm)); u.push(Math.exp(mm + 1.96 * ss)); l2.push(Math.exp(mm - 1.96 * ss)); });
        const ax = j === 0 ? "" : String(j + 1);
        traces.push({ type: "scatter", mode: "lines", x: g, y: u, line: { width: 0 }, xaxis: "x" + ax, yaxis: "y" + ax, hoverinfo: "skip" });
        traces.push({ type: "scatter", mode: "lines", x: g, y: l2, fill: "tonexty", fillcolor: t.dark ? "rgba(57,135,229,.18)" : "rgba(42,120,214,.14)", line: { width: 0 }, xaxis: "x" + ax, yaxis: "y" + ax, hoverinfo: "skip" });
        traces.push({ type: "scatter", mode: "lines", x: g, y: m, line: { color: t.cat[0], width: 2 }, xaxis: "x" + ax, yaxis: "y" + ax,
          hovertemplate: `${lab} = %{x:.1f}<br>perda %{y:.3f}<extra></extra>` });
        traces.push({ type: "scatter", mode: "markers", x: [x[j]], y: [Math.exp(mu)], marker: { size: 8, color: t.ruby, line: { width: 2, color: t.surface } }, xaxis: "x" + ax, yaxis: "y" + ax, hoverinfo: "skip" });
        lay["xaxis" + ax] = { title: { text: lab, font: { size: 11 } }, gridcolor: t.line, tickfont: { color: t.muted, size: 10 } };
        lay["yaxis" + ax] = { gridcolor: t.line, tickfont: { color: t.muted, size: 10 }, title: j === 0 ? { text: "perda prevista" } : undefined };
        ytop = Math.max(ytop, ...u);
      });
      D.labels.forEach((_, j) => { lay["yaxis" + (j === 0 ? "" : String(j + 1))].range = [0, Math.min(ytop * 1.04, 2)]; });   // mesma escala nos 5
      plot("ds-pd", traces, lay);
    }
    D.labels.forEach((_, j) => $("#ds-v" + j).addEventListener("input", draw));
    ["#ds-x", "#ds-y"].forEach((s) => $(s).addEventListener("change", draw));
    $("#ds-mode").addEventListener("click", (e) => { const b = e.target.closest("button"); if (!b) return; mode = b.dataset.v;
      $("#ds-mode").querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", x === b ? "true" : "false")); draw(); });
    draw();
    // validação cruzada
    const t = T(), cv = D.cv, mn = Math.min(...cv.obs, ...cv.pred) - 0.1, mx = Math.max(...cv.obs, ...cv.pred) + 0.1;
    plot("ds-cv", [{ type: "scatter", mode: "markers", x: cv.pred, y: cv.obs, error_x: { type: "data", array: cv.sd.map((s) => 1.96 * s), color: t.lineStrong, thickness: 1, width: 0 },
      marker: { size: 7, color: t.cat[0], line: { width: 1.5, color: t.surface } }, hovertemplate: "previsto %{x:.2f} · medido %{y:.2f}<extra></extra>" },
    { type: "scatter", mode: "lines", x: [mn, mx], y: [mn, mx], line: { color: t.muted, width: 1 }, hoverinfo: "skip" }],
    { showlegend: false, xaxis: { title: { text: "ln(perda) prevista" } }, yaxis: { title: { text: "ln(perda) medida" } },
      annotations: [{ x: 0.02, y: 0.98, xref: "paper", yref: "paper", xanchor: "left", text: `R² = ${nf(cv.r2, 2)} · 95 %: ${nf(100 * cv.coverage95, 0)} %`, showarrow: false, font: { color: t.ink, size: 12 } }] });
    // sugestões
    $("#ds-sugg").innerHTML = "<thead><tr><th>#</th>" + D.labels.map((l) => `<th class="num">${esc(l)}</th>`).join("") +
      "<th class='num'>Perda prevista</th><th class='num'>IC 95 %</th><th class='num'>EI</th><th></th></tr></thead><tbody>" +
      D.suggestions.map((s, i) => `<tr><td>${i + 1}</td>${s.x.map((v, j) => `<td class="num">${nf(v, j === 4 ? 0 : 1)}</td>`).join("")}` +
        `<td class="num">${nf(s.pred_loss, 3)}</td><td class="num">${nf(s.lo, 3)}–${nf(s.hi, 3)}</td><td class="num">${nf(s.ei, 4)}</td>` +
        `<td><button class="btn" type="button" data-s="${i}">Carregar</button></td></tr>`).join("") + "</tbody>";
    $("#ds-sugg").addEventListener("click", (e) => { const b = e.target.closest("button[data-s]"); if (!b) return;
      D.suggestions[+b.dataset.s].x.forEach((v, j) => { $("#ds-v" + j).value = v; }); draw(); $("#ds-surf").scrollIntoView({ block: "center" }); });
  };

  /* ================================================================== aprendizado ativo */
  RENDER.aprendizado = function () {
    const B = A.benchmark, names = Object.keys(B.datasets);
    $("#bo-ds").innerHTML = names.map((n) => `<option>${esc(n)}</option>`).join("");
    function draw() {
      const t = T(), ds = B.datasets[$("#bo-ds").value], x = ds.curves[B.arms[0]].median.map((_, i) => i + 1);
      const R = ds.reach_top5, rnd = R["Aleatório"].median_experiments, gpm = R["GP-EI"].median_experiments;
      kpis("#bo-kpis", [
        { k: "Condições distintas medidas", v: ni(ds.n_pool), s: `${ds.features.length} variáveis · ${esc(ds.reference)}` },
        { k: "Objetivo", v: ds.minimize ? "minimizar" : "maximizar", s: esc(ds.objective) },
        { k: "GP-EI até o top 5 %", v: gpm == null ? "—" : ni(gpm), u: "experimentos", s: `${nf(100 * R["GP-EI"].fraction, 0)} % das campanhas chegaram`, key: true },
        { k: "Aleatório até o top 5 %", v: rnd == null ? "—" : ni(rnd), u: "experimentos", s: `${nf(100 * R["Aleatório"].fraction, 0)} % chegaram` },
        (rnd && gpm) ? (gpm <= rnd ? { k: "GP-EI × aleatório", v: nf(100 * (1 - gpm / rnd), 0), u: "%", s: "menos experimentos (mediana)" }
          : { k: "GP-EI × aleatório", v: "+" + nf(100 * (gpm / rnd - 1), 0), u: "%", s: "mais experimentos: aqui o acaso ganhou" })
          : { k: "GP-EI × aleatório", v: "—" },
      ]);
      const tr = [];
      B.arms.forEach((arm, k) => {
        const c = ds.curves[arm], col = t.cat[k];
        tr.push({ type: "scatter", mode: "lines", x, y: c.q75, line: { width: 0 }, hoverinfo: "skip", showlegend: false, legendgroup: arm });
        tr.push({ type: "scatter", mode: "lines", x, y: c.q25, fill: "tonexty", fillcolor: hexA(col, t.dark ? 0.16 : 0.12), line: { width: 0 }, hoverinfo: "skip", showlegend: false, legendgroup: arm });
        tr.push({ type: "scatter", mode: "lines", name: arm, x, y: c.median, line: { color: col, width: 2.2 }, legendgroup: arm,
          hovertemplate: `${arm}: %{y:.2f} após %{x} experimentos<extra></extra>` });
      });
      const ylo = Math.min(...B.arms.map((a) => Math.min(...ds.curves[a].q25)));
      plot("bo-curves", tr, { xaxis: { title: { text: "experimentos" } }, yaxis: { title: { text: "melhor resultado (normalizado)" }, range: [Math.max(0, ylo - 0.03), 1.01] } });
      const tr2 = [];
      B.arms.forEach((arm, k) => {
        const v = R[arm].per_seed.map((h) => (h == null ? ds.budget + 3 : h));
        tr2.push({ type: "box", name: arm, y: v, boxpoints: "all", jitter: 0.45, pointpos: 0, fillcolor: "rgba(0,0,0,0)",
          line: { color: t.cat[k], width: 1.5 }, marker: { color: t.cat[k], size: 6, opacity: 0.8 },
          hovertemplate: `${arm}: %{y} experimentos<extra></extra>` });
      });
      plot("bo-reach", tr2, { showlegend: false, yaxis: { title: { text: "experimentos até o top 5 %" }, rangemode: "tozero" },
        shapes: [{ type: "line", xref: "paper", x0: 0, x1: 1, y0: ds.budget + 1.5, y1: ds.budget + 1.5, line: { color: t.lineStrong, width: 1 } }],
        annotations: [{ xref: "paper", x: 1, y: ds.budget + 3, text: "não chegou", showarrow: false, xanchor: "right", font: { size: 10, color: t.muted } }] });
    }
    $("#bo-ds").addEventListener("change", draw);
    draw();
    $("#bo-tbl").innerHTML = "<thead><tr><th>Campanha</th><th class='num'>Condições</th>" + B.arms.map((a) => `<th class="num">${a}</th>`).join("") + "</tr></thead><tbody>" +
      names.map((n) => { const ds = B.datasets[n]; return `<tr><td>${esc(n)} <span style="color:var(--muted)">(${esc(ds.objective)})</span></td><td class="num">${ds.n_pool}</td>` +
        B.arms.map((a) => { const r = ds.reach_top5[a]; return `<td class="num">${r.median_experiments == null ? "—" : ni(r.median_experiments)} <span style="color:var(--muted)">(${nf(100 * r.fraction, 0)} %)</span></td>`; }).join("") + "</tr>"; }).join("") + "</tbody>";
  };
  function hexA(hex, a) { const n = parseInt(hex.slice(1), 16); return `rgba(${n >> 16},${(n >> 8) & 255},${n & 255},${a})`; }

  /* ================================================================== interpretabilidade */
  RENDER.interpretabilidade = function () {
    const S = A.interpret;
    function draw() {
      const t = T(), m = S[$("#sh-m").value], V = m.values, X = m.X, p = m.features.length;
      const imp = m.features.map((_, j) => V.reduce((a, r) => a + Math.abs(r[j] || 0), 0) / V.length);
      const ord = imp.map((v, j) => [v, j]).sort((a, b) => a[0] - b[0]).map((x) => x[1]);   // menor → maior (de baixo p/ cima)
      if (!$("#sh-f").dataset.model || $("#sh-f").dataset.model !== $("#sh-m").value) {
        $("#sh-f").innerHTML = ord.slice().reverse().map((j) => `<option value="${j}">${esc(m.features[j])}</option>`).join("");
        $("#sh-f").dataset.model = $("#sh-m").value;
      }
      const top = ord[ord.length - 1];
      const extra = m.cv_r2 != null ? `R² (validação) ${nf(m.cv_r2, 2)}` : m.cv_r2_by_paper != null ? `R² por artigo ${nf(m.cv_r2_by_paper, 2)}` : "GP do Designer";
      const kind = $("#sh-m").value === "agnp" ? "GP · SHAP exato" : "árvores · TreeSHAP";
      kpis("#sh-kpis", [{ k: "Modelo e alvo", v: kind, s: `${esc(m.target)} · ${extra}` }, { k: "Sínteses explicadas", v: ni(V.length), s: m.n ? `de ${ni(m.n)} registros` : "" },
        { k: "Variável mais influente", v: esc(m.features[top]), s: `|SHAP| médio ${nf(imp[top], 3)}`, key: true }]);
      // enxame
      const xs = [], ys = [], cs = [], cd = [];
      ord.forEach((j, row) => {
        const col = X.map((r) => r[j]), fin = col.filter((v) => v != null), mn = Math.min(...fin), mx = Math.max(...fin);
        V.forEach((r, i) => { if (r[j] == null) return; xs.push(r[j]); ys.push(row + (Math.random() - 0.5) * 0.55);
          cs.push(X[i][j] == null ? 0.5 : (mx > mn ? (X[i][j] - mn) / (mx - mn) : 0.5)); cd.push([m.features[j], X[i][j]]); });
      });
      plot("sh-bees", [{ type: "scattergl", mode: "markers", x: xs, y: ys, customdata: cd,
        marker: { size: 5, color: cs, colorscale: t.seqScale, cmin: 0, cmax: 1, opacity: 0.85,
          colorbar: { title: { text: "valor", side: "right", font: { color: t.ink2 } }, tickvals: [0, 1], ticktext: ["baixo", "alto"], thickness: 10, len: 0.5, tickfont: { color: t.muted } } },
        hovertemplate: "%{customdata[0]} = %{customdata[1]}<br>SHAP %{x:.3f}<extra></extra>" }],
      { yaxis: { tickvals: ord.map((_, i) => i), ticktext: ord.map((j) => m.features[j]), zeroline: false }, margin: { l: 150 },
        xaxis: { title: { text: "contribuição para " + m.target }, zeroline: true, zerolinecolor: t.lineStrong } });
      plot("sh-bar", [{ type: "bar", orientation: "h", y: ord.map((j) => m.features[j]), x: ord.map((j) => imp[j]), marker: { color: t.cat[0] },
        hovertemplate: "%{y}: %{x:.3f}<extra></extra>" }], { margin: { l: 150 }, xaxis: { title: { text: "|SHAP| médio" } } });
      const f = +$("#sh-f").value;
      plot("sh-dep", [{ type: "scattergl", mode: "markers", x: X.map((r) => r[f]), y: V.map((r) => r[f]),
        marker: { size: 6, color: t.cat[0], opacity: 0.7, line: { width: 1, color: t.surface } }, hovertemplate: "%{x} → %{y:.3f}<extra></extra>" }],
      { xaxis: { title: { text: m.features[f] } }, yaxis: { title: { text: "SHAP" }, zeroline: true, zerolinecolor: t.lineStrong } });
      const fl = S.agnp.features, H = S.agnp.H2.map((row, i) => row.map((v, j) => (i === j ? null : v)));
      plot("sh-h2", [{ type: "heatmap", z: H, x: fl, y: fl, colorscale: t.seqScale, zmin: 0, xgap: 2, ygap: 2,
        colorbar: { title: { text: "H²", font: { color: t.ink2 } }, thickness: 10, tickfont: { color: t.muted } },
        hovertemplate: "%{x} × %{y}: H² = %{z:.3f}<extra></extra>" }], { margin: { l: 120, b: 90 }, yaxis: { autorange: "reversed" } });
    }
    $("#sh-m").addEventListener("change", draw); $("#sh-f").addEventListener("change", draw);
    draw();
  };

  /* ================================================================== variabilidade */
  RENDER.variabilidade = function () {
    const Va = A.variability, ag = Va.agnp, tk = Va.turkevich, ge = Va.aunc_generalization, t = T();
    kpis("#va-kpis", [
      { k: "CV mediano das réplicas (AgNP)", v: nf(100 * ag.median_cv, 1), u: "%", s: `${ni(ag.n_measurements)} medidas, ${ni(ag.mean.length)} condições` },
      { k: "Fração da variância entre condições", v: nf(ag.icc, 2), s: "ICC: o resto é ruído de réplica" },
      { k: "Ruído heteroscedástico?", v: ag.levene_p < 0.05 ? "sim" : "não", s: `Brown–Forsythe W = ${nf(ag.levene_W, 1)}, p ${ag.levene_p < 1e-4 ? "< 0,0001" : "= " + nf(ag.levene_p, 3)}`, key: true },
      { k: "Turkevich em 1 746 artigos", v: nf(tk.median, 1), u: "nm", s: `10–90 %: ${nf(tk.q10_q90[0], 1)}–${nf(tk.q10_q90[1], 1)} nm · fator ×${nf(tk.fold_1sd, 2)}` },
      { k: "AuNC: R² para artigo novo", v: nf(ge.r2_new_paper, 2), s: `aleatório: ${nf(ge.r2_random, 2)} · ${ge.n_papers} artigos` },
    ]);
    plot("va-noise", [{ type: "scatter", mode: "markers", x: ag.mean, y: ag.sd, customdata: ag.n,
      marker: { size: ag.n.map((n) => 4 + Math.sqrt(n) * 1.4), color: t.cat[0], opacity: 0.75, line: { width: 1.5, color: t.surface } },
      hovertemplate: "média %{x:.3f} · dp %{y:.3f}<br>%{customdata} réplicas<extra></extra>" }],
    { xaxis: { title: { text: "perda média da condição" } }, yaxis: { title: { text: "dp entre réplicas" }, rangemode: "tozero" } });
    const D = A.designer, P = D.points, cv = ag.sd.map((s, i) => s / ag.mean[i]);
    plot("va-3d", [{ type: "scatter3d", mode: "markers", x: P.X.map((r) => r[0]), y: P.X.map((r) => r[3]), z: P.X.map((r) => r[2]),
      marker: { size: 5, color: cv, colorscale: t.seqScale, opacity: 0.95, colorbar: { title: { text: "CV", font: { color: t.ink2 } }, thickness: 10, len: 0.6, tickformat: ".0%", tickfont: { color: t.muted } } },
      customdata: cv, hovertemplate: "CV = %{customdata:.1%}<extra></extra>" }],
    { margin: { l: 0, r: 0, t: 0, b: 0 }, scene: scene(D.labels[0], D.labels[3], D.labels[2]) });
    const lv = tk.sizes_per_paper.map(Math.log10), edges = lin(0.3, 2.2, 40), cnt = new Array(39).fill(0);
    lv.forEach((v) => { const j = Math.floor((v - edges[0]) / (edges[1] - edges[0])); if (j >= 0 && j < 39) cnt[j]++; });
    const mid = edges.slice(0, -1).map((e) => e + (edges[1] - edges[0]) / 2);
    const vline = (v, lab) => ({ type: "line", x0: Math.log10(v), x1: Math.log10(v), y0: 0, y1: 1, yref: "paper", line: { color: t.ink, width: lab ? 1.6 : 1 } });
    plot("va-turk", [{ type: "bar", x: mid, y: cnt, width: (edges[1] - edges[0]) * 0.92, marker: { color: t.cat[0] }, customdata: mid.map((m) => Math.pow(10, m)),
      hovertemplate: "≈ %{customdata:.1f} nm: %{y} artigos<extra></extra>" }],
    { bargap: 0, xaxis: { title: { text: "tamanho relatado (nm)" }, tickvals: [0.477, 0.699, 1, 1.301, 1.699, 2], ticktext: ["3", "5", "10", "20", "50", "100"] },
      yaxis: { title: { text: "artigos" } }, shapes: [vline(tk.median, 1), vline(tk.q10_q90[0]), vline(tk.q10_q90[1])],
      annotations: [{ x: Math.log10(tk.median), y: 1, yref: "paper", text: `mediana ${nf(tk.median, 1)} nm`, showarrow: false, xanchor: "left", xshift: 5, font: { color: t.ink, size: 11 } }] });
    const mn = Math.min(...ge.obs), mx = Math.max(...ge.obs);
    plot("va-gen", [
      { type: "scatter", mode: "markers", name: `síntese nova (R² ${nf(ge.r2_random, 2)})`, x: ge.obs, y: ge.pred_random, marker: { size: 7, color: t.cat[0], opacity: 0.8, line: { width: 1, color: t.surface } }, hovertemplate: "medido %{x} · previsto %{y:.0f} nm<extra></extra>" },
      { type: "scatter", mode: "markers", name: `artigo novo (R² ${nf(ge.r2_new_paper, 2)})`, x: ge.obs, y: ge.pred_new_paper, marker: { size: 7, color: t.cat[1], opacity: 0.8, symbol: "diamond", line: { width: 1, color: t.surface } }, hovertemplate: "medido %{x} · previsto %{y:.0f} nm<extra></extra>" },
      { type: "scatter", mode: "lines", x: [mn, mx], y: [mn, mx], line: { color: t.muted, width: 1 }, hoverinfo: "skip", showlegend: false }],
    { xaxis: { title: { text: "λ de emissão medido (nm)" } }, yaxis: { title: { text: "λ de emissão previsto (nm)" } } });
  };

  /* ================================================================== causal */
  RENDER.causal = function () {
    const C = A.causal, t = T();
    kpis("#ca-kpis", [
      { k: "Registros comparados", v: ni(C.n), s: `${ni(C.n_treated)} com NaBH₄, ${ni(C.n - C.n_treated)} com citrato` },
      { k: "Diferença bruta (sem ajuste)", v: "×" + nf(Math.exp(C.naive), 3), s: "razão das médias geométricas do tamanho" },
      { k: "Efeito ajustado (IPW)", v: "×" + nf(C.ratio, 3), s: `IC 95 % ${nf(C.ratio_ci95[0], 3)}–${nf(C.ratio_ci95[1], 3)} · o ajuste quase não muda a estimativa`, key: true },
      { k: "E-value", v: nf(C.e_value, 2), s: "força mínima de um confundidor oculto para anular o efeito" },
    ]);
    // confundidores acima e abaixo do eixo redutor → tamanho, para nenhuma seta cruzar um nó
    const pos = { "fonte (base)": [320, 36], "temperatura": [320, 100], "redutor": [90, 170], "tamanho": [550, 170],
      "sementes": [320, 240], "ligante": [320, 304] };
    const W = 640, H = 340, HW = 62, HH = 18;
    const clip = (dx, dy, pad) => { const k = Math.min(dx ? (HW + pad) / Math.abs(dx) : Infinity, dy ? (HH + pad) / Math.abs(dy) : Infinity); return [dx * k, dy * k]; };
    const arrow = (a, b, main) => { const [x1, y1] = pos[a], [x2, y2] = pos[b]; const dx = x2 - x1, dy = y2 - y1;
      const [ox, oy] = clip(dx, dy, 2), [ix, iy] = clip(dx, dy, 6);
      return `<path class="edge${main ? " main" : ""}" d="M${x1 + ox},${y1 + oy} L${x2 - ix},${y2 - iy}" marker-end="url(#ah${main ? "m" : ""})"/>`; };
    $("#ca-dag").innerHTML = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Grafo causal: redutor, temperatura, sementes, ligante e fonte afetam o tamanho">
      <defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="${t.muted}"/></marker>
      <marker id="ahm" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="${t.ruby}"/></marker></defs>
      ${C.dag.edges.map(([a, b]) => arrow(a, b, a === "redutor" && b === "tamanho")).join("")}
      ${C.dag.nodes.map((n) => { const [x, y] = pos[n]; const cls = n === "redutor" ? " t" : n === "tamanho" ? " y" : "";
        return `<g class="node${cls}"><rect x="${x - HW}" y="${y - HH}" width="${2 * HW}" height="${2 * HH}" rx="10"/><text x="${x}" y="${y + 4}" text-anchor="middle">${esc(n)}</text></g>`; }).join("")}
      <text class="eff" x="${(pos.redutor[0] + pos.tamanho[0]) / 2}" y="${pos.redutor[1] - 10}" text-anchor="middle">×${nf(C.ratio, 2)} no tamanho</text>
      </svg>`;
    const covs = C.covariates;
    plot("ca-smd", [
      { type: "scatter", mode: "markers", name: "antes", y: covs, x: C.smd_before, marker: { size: 10, color: t.cat[1], line: { width: 2, color: t.surface } }, hovertemplate: "%{y}: %{x:.2f}<extra>antes</extra>" },
      { type: "scatter", mode: "markers", name: "depois (IPW)", y: covs, x: C.smd_after, marker: { size: 10, color: t.cat[0], symbol: "diamond", line: { width: 2, color: t.surface } }, hovertemplate: "%{y}: %{x:.2f}<extra>depois</extra>" }],
    { margin: { l: 190 }, xaxis: { title: { text: "diferença média padronizada" }, zeroline: true, zerolinecolor: t.lineStrong },
      shapes: [{ type: "rect", x0: -0.1, x1: 0.1, y0: 0, y1: 1, yref: "paper", fillcolor: hexA(t.dark ? "#3987e5" : "#2a78d6", 0.08), line: { width: 0 } }] });
    plot("ca-ps", [
      { type: "histogram", name: "citrato", x: C.propensity.control, opacity: 0.65, marker: { color: t.cat[1] }, xbins: { start: 0, end: 1, size: 0.025 }, histnorm: "probability density", hovertemplate: "e = %{x}: %{y:.2f}<extra>citrato</extra>" },
      { type: "histogram", name: "NaBH₄", x: C.propensity.treated, opacity: 0.65, marker: { color: t.cat[0] }, xbins: { start: 0, end: 1, size: 0.025 }, histnorm: "probability density", hovertemplate: "e = %{x}: %{y:.2f}<extra>NaBH₄</extra>" }],
    { barmode: "overlay", xaxis: { title: { text: "escore de propensão (probabilidade de usar NaBH₄)" }, range: [0, 1] }, yaxis: { title: { text: "densidade" } } });
  };

  /* ================================================================== caracterização */
  RENDER.caracterizacao = function () {
    const X = A.xrd, g = X.geometry || {}, t = T();
    kpis("#xr-kpis", [
      { k: "Energia do feixe", v: nf(g.energy_keV, 1), u: "keV", s: `λ = ${nf(g.wavelength_A, 4)} Å (a CeO₂ = 5,4116 Å)`, key: true },
      { k: "Distância amostra–detector", v: ni(g.distance_px), u: "px", s: `≈ ${ni(g.distance_mm_if_200um)} mm com pixel de 200 µm` },
      { k: "Anéis indexados", v: ni(g.n_rings), u: `de ${ni(g.n_predicted)}`, s: `resíduo RMS ${nf(g.rms_residual_px, 2)} px no raio` },
      { k: "Quadros médios", v: ni(X.n_frames), s: `${X.shape[0]} × ${X.shape[1]} px, dark subtraído` },
    ]);
    const n = X.image_log10.length, sc = X.shape[0] / n, flat = [].concat(...X.image_log10);
    plot("xr-img", [{ type: "heatmap", z: X.image_log10, colorscale: t.seqScale, showscale: false, zmin: quant(flat, 0.03), zmax: quant(flat, 0.997),
      hovertemplate: "(%{x}, %{y}): log₁₀ I = %{z:.2f}<extra></extra>" },
    { type: "scatter", mode: "markers", x: [X.center[1] / sc], y: [X.center[0] / sc], marker: { symbol: "cross-thin", size: 14, line: { width: 2, color: t.ruby } }, hoverinfo: "skip" }],
    { showlegend: false, xaxis: { showgrid: false, title: { text: "pixel / " + sc }, range: [0, n], constrain: "domain" },
      yaxis: { showgrid: false, range: [n, 0], scaleanchor: "x", constrain: "domain" }, margin: { l: 40, r: 10 } });
    plot("xr-3d", [{ type: "surface", z: X.surface_log10, colorscale: t.seqScale, showscale: false, hovertemplate: "log₁₀ I = %{z:.2f}<extra></extra>" }],
      { margin: { l: 0, r: 0, t: 0, b: 0 }, scene: scene("x (bloco)", "y (bloco)", "log₁₀ I", { camera: { eye: { x: 1.3, y: -1.6, z: 1.1 } }, aspectratio: { x: 1, y: 1, z: 0.5 }, aspectmode: "manual" }) });
    const r = X.profile.map((_, i) => i), matched = X.rings.filter((m) => m.r_obs != null);
    plot("xr-prof", [{ type: "scatter", mode: "lines", name: "perfil radial", x: r, y: X.profile, line: { color: t.cat[0], width: 1.6 }, hovertemplate: "r = %{x} px: %{y:.0f}<extra></extra>" },
      { type: "scatter", mode: "markers+text", name: "anéis indexados (fluorita)", x: matched.map((m) => m.r_obs), y: matched.map((m) => X.profile[Math.round(m.r_obs)] * 1.25),
        text: matched.map((m) => m.hkl), textposition: "top center", textfont: { color: t.ink, size: 10 },
        marker: { size: 7, symbol: "triangle-down", color: t.ruby }, customdata: matched.map((m) => [m.two_theta, m.resid_px]),
        hovertemplate: "(%{text}) r = %{x:.2f} px<br>2θ = %{customdata[0]:.3f}° · resíduo %{customdata[1]:.2f} px<extra></extra>" }],
    { xaxis: { title: { text: "raio a partir do centro (px)" }, range: [150, X.profile.length] }, yaxis: { title: { text: "intensidade média (contagens)" }, type: "log" } });
    $("#xr-tbl").innerHTML = "<thead><tr><th>hkl</th><th class='num'>2θ (°)</th><th class='num'>r previsto</th><th class='num'>r medido</th><th class='num'>resíduo (px)</th></tr></thead><tbody>" +
      X.rings.map((m) => `<tr><td>(${m.hkl})</td><td class="num">${nf(m.two_theta, 3)}</td><td class="num">${nf(m.r_pred, 1)}</td><td class="num">${m.r_obs == null ? "não resolvido" : nf(m.r_obs, 1)}</td><td class="num">${m.resid_px == null ? "—" : nf(m.resid_px, 2)}</td></tr>`).join("") + "</tbody>";
    // AuNC
    const U = A.aunc, groups = ["GSH", "outros tióis", "outros"];
    plot("au-3d", groups.map((gname, k) => { const I = U.ligand.map((l, i) => (l === gname ? i : -1)).filter((i) => i >= 0);
      return { type: "scatter3d", mode: "markers", name: gname, x: I.map((i) => U.size[i]), y: I.map((i) => U.exc[i]), z: I.map((i) => U.em[i]),
        customdata: I.map((i) => U.doi[i]), marker: { size: 4.5, color: t.cat[k], opacity: 0.9, line: { width: 0 } },
        hovertemplate: "tamanho %{x} nm · exc %{y} nm · em %{z} nm<br>%{customdata}<extra>" + gname + "</extra>" }; }),
    { margin: { l: 0, r: 0, t: 30, b: 0 }, scene: scene("tamanho (nm)", "λ exc (nm)", "λ em (nm)") });
    plot("au-T", groups.map((gname, k) => { const I = U.ligand.map((l, i) => (l === gname ? i : -1)).filter((i) => i >= 0 && U.T[i] != null);
      return { type: "scatter", mode: "markers", name: gname, x: I.map((i) => U.T[i]), y: I.map((i) => U.em[i]),
        marker: { size: 7, color: t.cat[k], opacity: 0.8, line: { width: 1, color: t.surface } }, hovertemplate: "%{x} °C → %{y} nm<extra>" + gname + "</extra>" }; }),
    { xaxis: { title: { text: "temperatura de síntese (°C)" } }, yaxis: { title: { text: "λ de emissão (nm)" } } });
  };

  /* ================================================================== sobre */
  RENDER.sobre = function () {
    const k = A.overview.kpis, bm = A.overview.benchmark_measurements;
    const liang = ["P3HT/CNT", "Perovskita", "Crossed barrel", "AutoAM"].reduce((s, n) => s + (bm[n] || 0), 0);
    const src = [
      ["Sínteses de AuNP (texto minerado)", "Cruse et al., Sci. Data 9:234 (2022)", "10.6084/m9.figshare.16614262", "7 183 receitas", "CC BY 4.0"],
      ["Rotas de nanocristais de Au", "Nanocrystal Synthesis Platform (NSP, 2026)", "—", "8 538 rotas", "MIT"],
      ["Fluorescência de AuNC", "compilação por DOI (datasets/aunc-fluorescence)", "—", `${k.aunc_entries} entradas`, "ver DOIs"],
      ["Campanha AgNP em microfluídica", "Mekki-Berrada et al., npj Comput. Mater. 7:55 (2021)", "10.1038/s41524-021-00520-w", `${ni(k.agnp_measurements)} medidas`, "MIT (PV-Lab)"],
      ["P3HT/CNT, perovskitas, crossed barrel, AutoAM", "Liang et al., npj Comput. Mater. 7:188 (2021)", "10.1038/s41524-021-00656-9", `${ni(liang)} medidas`, "MIT (PV-Lab)"],
      ["Constantes ópticas do Au", "Johnson & Christy, Phys. Rev. B 6:4370 (1972)", "10.1103/PhysRevB.6.4370", "n, k medidos", "CC0 (refractiveindex.info)"],
      ["Difração do padrão CeO₂", "quadros do detector GE (datasets/xrd-ceo2-calibration)", "—", "5 + 5 quadros", "ver origem"],
    ];
    $("#ab-src").innerHTML = "<thead><tr><th>Dados</th><th>Origem</th><th>DOI</th><th>Volume</th><th>Licença</th></tr></thead><tbody>" +
      src.map((s) => `<tr><td>${esc(s[0])}</td><td>${esc(s[1])}</td><td>${s[2] !== "—" ? `<a href="https://doi.org/${esc(s[2])}" target="_blank" rel="noopener">${esc(s[2])}</a>` : "—"}</td><td>${esc(s[3])}</td><td>${esc(s[4])}</td></tr>`).join("") + "</tbody>";
    $("#ab-methods").innerHTML = [
      "<b>Medidas</b>: perdas espectrais e réplicas (AgNP e demais campanhas), emissões de AuNC, quadros de difração, n e k do ouro.",
      "<b>Relatos minerados</b>: tamanho, pico e temperatura da literatura vêm de texto extraído por NLP/LLM. Em Cruse et al., o tamanho é do artigo, não do parágrafo; erros de extração existem e os filtros físicos removem os grosseiros.",
      "<b>Modelos</b>: Mie (física, sem ajuste); GP do AuNP Designer (Matérn-5/2 + ARD, prior de comprimento, BoTorch), executado no navegador com os parâmetros ajustados; árvores de gradiente para SHAP; regressão logística para o escore de propensão.",
      "<b>Inferência</b>: a análise causal é observacional — o E-value diz o tamanho do confundimento oculto que a anularia. As campanhas de aprendizado ativo usam as medidas reais como oráculo, então as estratégias só escolhem entre condições que foram medidas.",
    ].map((p) => `<p style="margin:0 0 10px">${p}</p>`).join("");
    $("#ab-pending").innerHTML = [
      "<b>Lotes de GO</b> (§4.2–4.3): XPS, Raman, AFM e impurezas por lote, e o GO Navigator com esses descritores.",
      "<b>Representações contextuais do Designer</b> (§4.5) e <b>transferência entre lotes</b> (§4.7): precisam de sínteses GO–AuNP em lotes diferentes.",
      "<b>MISO</b> (§4.8): UV-Vis, DLS e TEM das mesmas sínteses.",
      "<b>Campanha prospectiva</b> (§4.11) e <b>confirmação por TEM</b> (§4.12): piloto, 12 + 24 + 16 sínteses e o plano pré-registrado congelado.",
      "O código para tudo isso já está no repositório (code/, ver docs/ANALISE_REPOSITORIO.md); este painel recebe essas seções quando as medidas existirem.",
    ].map((p) => `<p style="margin:0 0 10px">${p}</p>`).join("");
  };

  /* ------------------------------------------------------------------ início */
  function start() {
    buildTabs();
    $("#foot").innerHTML = `AuGOSintesIA · gerado em ${esc(A.overview.generated)} por <span class="mono">code/webapp/build_site.py</span> a partir dos dados experimentais do repositório. ` +
      "Modelos e previsões são marcados como tal; nenhum dado simulado entra nesta página.";
    try { const th = localStorage.getItem("augo-theme"); if (th) document.documentElement.setAttribute("data-theme", th); } catch (e) { /* sem armazenamento */ }
    $("#themeBtn").addEventListener("click", () => {
      const next = isDark() ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      try { localStorage.setItem("augo-theme", next); } catch (e) { /* sem armazenamento */ }
    });
    // qualquer troca de tema (botão, visualizador ou sistema) redesenha os gráficos com as cores do tema
    let pend = 0;
    const redraw = () => { clearTimeout(pend); pend = setTimeout(rerenderAll, 60); };
    new MutationObserver(redraw).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    if (window.matchMedia) window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
      if (!document.documentElement.getAttribute("data-theme")) redraw(); });
    let first = (location.hash || "").slice(1);
    if (!first) { try { first = localStorage.getItem("augo-tab") || "visao"; } catch (e) { first = "visao"; } }
    show(first);
  }
  if (!window.Plotly) {
    document.getElementById("main").insertAdjacentHTML("afterbegin",
      '<p class="note">A biblioteca de gráficos (Plotly) não carregou. Abra o arquivo site/index.html da pasta do repositório, com a pasta vendor/ ao lado.</p>');
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
})();
