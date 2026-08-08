/* AI-GENERATED BEGIN (Claude Code, 2026-06-20)
   BU Hive Information — alternate lenses over the same /api/graph data:
   Mind Map, Outline, Cards, Full Content. The interactive Map (bu-graph.js)
   stays the default. The chosen lens is remembered per device in localStorage.
   Dependency-free, CSP-safe (no inline handlers). */
(function () {
  "use strict";
  var KEY = "bu-hive-infoview";
  var VIEWS = ["map", "mindmap", "outline", "cards", "full"];
  // Fallback palette if bu-colors.js isn't loaded; mirrors BUCAT.DEFAULTS.
  var CATCOLOR = { hub: "#CC0000", layer: "#E8552D", page: "#F0883E", project: "#E64980",
    data: "#4DABF7", config: "#9775FA", security: "#FAB005", hook: "#20C997", custom: "#E599F7" };
  var CATLABEL = { hub: "BU Hive core", layer: "Nav layer", page: "Page", data: "Data source",
    config: "Config / data", project: "Project", security: "Security / governance",
    hook: "Automation hook", custom: "Custom / file" };

  var switchEl = document.getElementById("viewSwitch");
  if (!switchEl) return;

  var DATA = null, byId = {}, adjL = {}, tree = null, cardFilter = "all", currentFullId = null, infoQuery = "";
  // Mind-map pan/zoom + focus state
  var mmStage = null, mmVp = null, mmView = { x: 0, y: 0, k: 1 }, mmW = 0, mmH = 0, mmBound = false;
  var mmPos = {}, mmEls = {}, mmEdgeEls = [], mmFocusId = null;

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function color(cat) {
    return (window.BUCAT && window.BUCAT.get) ? window.BUCAT.get(cat) : (CATCOLOR[cat] || "#888");
  }
  // Appearance prefs (window.BUSET) with fallbacks — shared with the Map lens.
  function pref(k, d) { return (window.BUSET && window.BUSET.get(k) != null) ? window.BUSET.get(k) : d; }

  // ---- "Bubble" style: glossy 3D spheres via per-category radial gradients,
  // mirroring the Map lens (bu-graph.js). Gradients live in the mind-map <defs>.
  var mmDefs = null, mmBubGrads = {};
  function shade(hex, amt) {  // amt>0 → toward white, amt<0 → toward black
    var m = /^#?([0-9a-f]{6})$/i.exec(hex || ""); if (!m) return hex || "#888";
    var n = parseInt(m[1], 16), r = (n >> 16) & 255, g = (n >> 8) & 255, b = n & 255;
    if (amt >= 0) { r += (255 - r) * amt; g += (255 - g) * amt; b += (255 - b) * amt; }
    else { var f = 1 + amt; r *= f; g *= f; b *= f; }
    function cl(x) { return Math.max(0, Math.min(255, Math.round(x))); }
    return "#" + ((1 << 24) + (cl(r) << 16) + (cl(g) << 8) + cl(b)).toString(16).slice(1);
  }
  function mmBubbleStops(cat) {
    var base = color(cat);
    return [["0%", "#ffffff", "0.92"], ["20%", shade(base, 0.5), "1"],
            ["58%", base, "1"], ["100%", shade(base, -0.34), "1"]];
  }
  function ensureMmBubble(cat) {
    if (!mmDefs) return null;
    if (!mmBubGrads[cat]) {
      var NS2 = "http://www.w3.org/2000/svg";
      var grad = document.createElementNS(NS2, "radialGradient");
      grad.setAttribute("id", "mmbub-" + cat);
      grad.setAttribute("cx", "50%"); grad.setAttribute("cy", "50%"); grad.setAttribute("r", "58%");
      grad.setAttribute("fx", "34%"); grad.setAttribute("fy", "30%");
      var stops = mmBubbleStops(cat).map(function (st) {
        var s = document.createElementNS(NS2, "stop");
        s.setAttribute("offset", st[0]); s.setAttribute("stop-color", st[1]); s.setAttribute("stop-opacity", st[2]);
        grad.appendChild(s); return s;
      });
      mmDefs.appendChild(grad); mmBubGrads[cat] = stops;
    }
    return "mmbub-" + cat;
  }
  function refreshMmBubbles() {
    for (var cat in mmBubGrads) {
      var st = mmBubbleStops(cat);
      mmBubGrads[cat].forEach(function (s, i) { s.setAttribute("stop-color", st[i][1]); s.setAttribute("stop-opacity", st[i][2]); });
    }
  }
  function mmFill(cat, style) {
    if (style === "filled") return color(cat);
    if (style === "bubble") { var id = ensureMmBubble(cat); return id ? "url(#" + id + ")" : color(cat); }
    return "transparent";
  }
  function mmStroke(cat, style) { return style === "bubble" ? shade(color(cat), -0.3) : color(cat); }
  // searchable text for a node: label + description + any meta values (e.g. file path)
  function hay(n) {
    var parts = [n.label, n.detail || ""];
    if (n.meta) for (var k in n.meta) parts.push(String(n.meta[k]));
    return parts.join(" ").toLowerCase();
  }
  function dot(cat) { return "<span class='cat-dot' style='background:" + color(cat) + "'></span>"; }
  // external (http/https) routes open in a new tab
  function ext(r) { return /^https?:\/\//.test(r || ""); }
  function tgt(r) { return ext(r) ? " target='_blank' rel='noopener'" : ""; }

  /* ---- load ---- */
  fetch("/api/graph").then(function (r) { return r.json(); }).then(function (data) {
    DATA = data;
    data.nodes.forEach(function (n) { byId[n.id] = n; adjL[n.id] = []; });
    data.edges.forEach(function (e) {
      if (!byId[e.s] || !byId[e.t]) return;
      adjL[e.s].push({ id: e.t, label: e.label }); adjL[e.t].push({ id: e.s, label: e.label });
    });
    tree = buildTree();
    renderOutline(); renderCards(); renderMindmap(); buildFullPicker();
    showFull(tree.rootId);
    setView(stored());
    initSearch();
    if (window.BUCAT && window.BUCAT.onChange) window.BUCAT.onChange(recolorLenses);
    // style / size / label changes need a Mind Map rebuild; other lenses recolour.
    if (window.BUSET && window.BUSET.onChange) window.BUSET.onChange(function () {
      if (document.getElementById("mindmapSvg")) renderMindmap();
      recolorLenses();
    });
  }).catch(function () {
    ["outlineRoot", "cardGrid", "fullBody"].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.innerHTML = "<div class='notice'>Graph data unavailable.</div>";
    });
  });

  /* ---- spanning tree from the hub (undirected BFS) ---- */
  function buildTree() {
    var rootId = byId.hub ? "hub" : (DATA.nodes[0] && DATA.nodes[0].id);
    var children = {}, depth = {}, seen = {}, parent = {};
    DATA.nodes.forEach(function (n) { children[n.id] = []; });
    var q = [rootId]; seen[rootId] = 1; depth[rootId] = 0; parent[rootId] = null;
    while (q.length) {
      var id = q.shift();
      adjL[id].forEach(function (nb) {
        if (seen[nb.id]) return;
        seen[nb.id] = 1; depth[nb.id] = depth[id] + 1; parent[nb.id] = id;
        children[id].push(nb.id); q.push(nb.id);
      });
    }
    // attach anything disconnected directly under the root
    DATA.nodes.forEach(function (n) {
      if (!seen[n.id]) { seen[n.id] = 1; depth[n.id] = 1; parent[n.id] = rootId; children[rootId].push(n.id); }
    });
    return { rootId: rootId, children: children, depth: depth, parent: parent };
  }

  /* ---- view switching + persistence ---- */
  function stored() {
    var v = localStorage.getItem(KEY);
    return VIEWS.indexOf(v) >= 0 ? v : "map";
  }
  function setView(v) {
    if (VIEWS.indexOf(v) < 0) v = "map";
    localStorage.setItem(KEY, v);
    VIEWS.forEach(function (name) {
      var pane = document.getElementById("view-" + name);
      if (pane) pane.hidden = name !== v;
    });
    switchEl.querySelectorAll(".vs-btn").forEach(function (b) {
      b.classList.toggle("active", b.getAttribute("data-view") === v);
    });
    if (v === "map" && window.BUGraph) window.BUGraph.relayout();
    if (v === "mindmap") requestAnimationFrame(mmFit);  // fit once the pane has real size
    if (infoQuery) applySearch(infoQuery);  // keep the active search applied across lenses
  }
  switchEl.querySelectorAll(".vs-btn").forEach(function (b) {
    b.addEventListener("click", function () { setView(b.getAttribute("data-view")); });
  });

  /* ---- OUTLINE ---- */
  function renderOutline() {
    var root = document.getElementById("outlineRoot");
    if (!root) return;
    root.innerHTML = "<ul class='ol-list'>" + olNode(tree.rootId) + "</ul>";
    root.querySelectorAll(".ol-toggle").forEach(function (t) {
      t.addEventListener("click", function () {
        var li = t.closest(".ol-li"); li.classList.toggle("collapsed");
      });
    });
    root.querySelectorAll(".ol-focus").forEach(function (a) {
      a.addEventListener("click", function (e) { e.preventDefault(); goFull(a.getAttribute("data-id")); });
    });
    bindOnce("olExpand", function () { setCollapsed(root, false); });
    bindOnce("olCollapse", function () { setCollapsed(root, true); });
  }
  function olNode(id) {
    var n = byId[id], kids = tree.children[id] || [];
    var has = kids.length > 0;
    var route = n.route ? " <a class='ol-open' href='" + esc(n.route) + "'" + tgt(n.route) + " title='Open'><i class='bi bi-box-arrow-up-right'></i></a>" : "";
    var status = n.status ? " <span class='badge badge-soft'>" + esc(n.status) + "</span>" : "";
    var h = "<li class='ol-li" + (has ? "" : " leaf") + "'>";
    h += "<div class='ol-row'>";
    h += has ? "<button class='ol-toggle' aria-label='toggle'><i class='bi bi-caret-down-fill'></i></button>" : "<span class='ol-bullet'></span>";
    h += dot(n.cat);
    h += "<a href='#' class='ol-focus' data-id='" + esc(id) + "'>" + esc(n.label) + "</a>" + status + route;
    h += "</div>";
    if (n.detail) h += "<div class='ol-detail muted'>" + esc(n.detail) + "</div>";
    if (has) {
      h += "<ul class='ol-list'>";
      kids.forEach(function (k) { h += olNode(k); });
      h += "</ul>";
    }
    return h + "</li>";
  }
  function setCollapsed(root, on) {
    root.querySelectorAll(".ol-li").forEach(function (li) {
      if (li.classList.contains("leaf")) return;
      li.classList.toggle("collapsed", on);
    });
  }

  /* ---- CARDS ---- */
  function renderCards() {
    var cats = {}; DATA.nodes.forEach(function (n) { cats[n.cat] = 1; });
    var bar = document.getElementById("cardCats");
    var btns = "<button class='btn btn-sm vs-cat active' data-cat='all'>All</button>";
    Object.keys(cats).forEach(function (c) {
      btns += "<button class='btn btn-sm vs-cat' data-cat='" + c + "'>" + esc(CATLABEL[c] || c) + "</button>";
    });
    bar.innerHTML = btns;
    bar.querySelectorAll(".vs-cat").forEach(function (b) {
      b.addEventListener("click", function () {
        cardFilter = b.getAttribute("data-cat");
        bar.querySelectorAll(".vs-cat").forEach(function (x) { x.classList.toggle("active", x === b); });
        paintCards();
      });
    });
    bindOnce("cardSort", null, "change", paintCards);
    paintCards();
  }
  function paintCards() {
    var grid = document.getElementById("cardGrid");
    var sort = (document.getElementById("cardSort") || {}).value || "cat";
    var q = (infoQuery || "").toLowerCase();
    var list = DATA.nodes.filter(function (n) {
      if (cardFilter !== "all" && n.cat !== cardFilter) return false;
      if (q && (n.label + " " + (n.detail || "") + " " + (CATLABEL[n.cat] || "")).toLowerCase().indexOf(q) < 0) return false;
      return true;
    });
    list.sort(function (a, b) {
      if (sort === "name") return a.label.localeCompare(b.label);
      if (sort === "status") return (a.status || "~").localeCompare(b.status || "~") || a.label.localeCompare(b.label);
      return (CATLABEL[a.cat] || a.cat).localeCompare(CATLABEL[b.cat] || b.cat) || a.label.localeCompare(b.label);
    });
    var h = "";
    list.forEach(function (n) {
      var conns = (adjL[n.id] || []).length;
      h += "<div class='info-card' style='border-top:3px solid " + color(n.cat) + "'>";
      h += "<div class='ic-cat' style='color:" + color(n.cat) + "'>" + esc(CATLABEL[n.cat] || n.cat) + "</div>";
      h += "<div class='ic-title'>" + esc(n.label) + "</div>";
      if (n.detail) h += "<div class='ic-detail muted'>" + esc(n.detail) + "</div>";
      h += "<div class='ic-meta'>";
      if (n.status) h += "<span class='badge badge-soft'>" + esc(n.status) + "</span>";
      h += "<span class='badge badge-soft'>" + conns + " links</span>";
      if (n.meta) for (var k in n.meta) h += "<span class='badge badge-soft'>" + esc(k) + ": " + esc(n.meta[k]) + "</span>";
      h += "</div>";
      h += "<div class='ic-actions'>";
      h += "<button class='btn btn-sm btn-icon ic-focus' data-id='" + esc(n.id) + "'><i class='bi bi-card-text'></i> Details</button>";
      if (n.route) h += " <a class='btn btn-sm btn-icon' href='" + esc(n.route) + "'" + tgt(n.route) + "><i class='bi bi-box-arrow-up-right'></i> Open</a>";
      h += "</div></div>";
    });
    grid.innerHTML = h || "<div class='muted'>No nodes in this category.</div>";
    grid.querySelectorAll(".ic-focus").forEach(function (b) {
      b.addEventListener("click", function () { goFull(b.getAttribute("data-id")); });
    });
  }

  /* ---- MIND MAP (tidy left-to-right tree, pan + zoom) ---- */
  function renderMindmap() {
    var svg = document.getElementById("mindmapSvg");
    if (!svg) return;
    mmStage = document.getElementById("mindmapStage");
    var COLX = 220, ROWY = 30, leaf = 0, pos = {};
    (function layout(id, depth) {
      var kids = tree.children[id] || [];
      if (!kids.length) { pos[id] = { x: depth * COLX, y: leaf * ROWY }; leaf++; return pos[id].y; }
      var ys = kids.map(function (k) { return layout(k, depth + 1); });
      var y = (ys[0] + ys[ys.length - 1]) / 2;
      pos[id] = { x: depth * COLX, y: y }; return y;
    })(tree.rootId, 0);

    var minY = 1e9, maxY = -1e9, maxX = 0;
    Object.keys(pos).forEach(function (id) {
      minY = Math.min(minY, pos[id].y); maxY = Math.max(maxY, pos[id].y); maxX = Math.max(maxX, pos[id].x);
    });
    var PADX = 130, PADY = 24;
    mmW = maxX + PADX * 2; mmH = (maxY - minY) + PADY * 2;
    var ox = PADX, oy = PADY - minY;

    var NS = "http://www.w3.org/2000/svg";
    while (svg.firstChild) svg.removeChild(svg.firstChild);
    svg.removeAttribute("viewBox");                 // pixel coords; pan/zoom via the viewport <g>
    mmDefs = document.createElementNS(NS, "defs"); mmBubGrads = {}; svg.appendChild(mmDefs);
    mmVp = document.createElementNS(NS, "g");
    var gE = document.createElementNS(NS, "g"), gN = document.createElementNS(NS, "g");
    mmVp.appendChild(gE); mmVp.appendChild(gN); svg.appendChild(mmVp);

    mmPos = {}; mmEls = {}; mmEdgeEls = []; mmFocusId = null;
    // edges (parent → child), elbow curves
    Object.keys(tree.children).forEach(function (pid) {
      (tree.children[pid] || []).forEach(function (cid) {
        var a = pos[pid], b = pos[cid];
        var x1 = a.x + ox, y1 = a.y + oy, x2 = b.x + ox, y2 = b.y + oy;
        var mx = (x1 + x2) / 2;
        var path = document.createElementNS(NS, "path");
        path.setAttribute("d", "M" + x1 + "," + y1 + " C" + mx + "," + y1 + " " + mx + "," + y2 + " " + x2 + "," + y2);
        path.setAttribute("class", "mm-edge");
        gE.appendChild(path);
        mmEdgeEls.push({ s: pid, t: cid, el: path });
      });
    });
    // nodes (click handled centrally in mmBindEvents so it survives pan capture)
    DATA.nodes.forEach(function (n) {
      var p = pos[n.id]; if (!p) return;
      var x = p.x + ox, y = p.y + oy;
      var g = document.createElementNS(NS, "g");
      g.setAttribute("class", "mm-node"); g.setAttribute("data-nid", n.id);
      g.setAttribute("transform", "translate(" + x + "," + y + ")");
      var c = document.createElementNS(NS, "circle");
      var style = pref("nodeStyle", "outline");
      c.setAttribute("r", (n.cat === "hub" ? 8 : 5) * (parseFloat(pref("nodeScale", 1)) || 1));
      c.setAttribute("fill", mmFill(n.cat, style)); c.setAttribute("stroke", mmStroke(n.cat, style));
      c.setAttribute("cx", 0); c.setAttribute("cy", 0);
      var t = document.createElementNS(NS, "text");
      t.setAttribute("x", 10); t.setAttribute("y", 4); t.textContent = n.label;
      if (!pref("showLabels", true)) t.style.display = "none";
      g.appendChild(c); g.appendChild(t);
      gN.appendChild(g);
      mmEls[n.id] = g; mmPos[n.id] = { x: x, y: y };
    });

    mmBindEvents(svg);
    mmFit();
  }

  // Drill-in focus: bring the selection to centre, zoom, and spotlight its
  // next level (children). Ancestors stay visible for context; the rest recede.
  function mmFocus(id) {
    if (!mmPos[id] || !mmStage) return;
    mmFocusId = id;
    var kids = {}; (tree.children[id] || []).forEach(function (c) { kids[c] = 1; });
    var anc = {}; var cur = tree.parent[id]; while (cur) { anc[cur] = 1; cur = tree.parent[cur]; }
    Object.keys(mmEls).forEach(function (nid) {
      var g = mmEls[nid]; g.classList.remove("mm-focus", "mm-next", "mm-dim");
      if (nid === id) g.classList.add("mm-focus");
      else if (kids[nid]) g.classList.add("mm-next");
      else if (!anc[nid]) g.classList.add("mm-dim");
    });
    mmEdgeEls.forEach(function (e) {
      var hot = e.s === id || e.t === id;          // edges to children + to parent
      var keep = hot || (anc[e.s] && (anc[e.t] || e.t === id));  // ancestor path
      e.el.classList.toggle("mm-hot", hot);
      e.el.classList.toggle("mm-dim", !keep);
    });
    // zoom toward the selection (CSS-animated for a smooth drill-in feel)
    var r = mmStage.getBoundingClientRect();
    var k = Math.min(2.2, Math.max(mmView.k, 1.25));
    mmView.k = k;
    mmView.x = r.width * 0.42 - mmPos[id].x * k;   // bias left so children have room
    mmView.y = r.height * 0.5 - mmPos[id].y * k;
    if (mmVp) mmVp.classList.add("mm-animate");
    mmApply(); mmSyncSlider();
  }
  function mmClearFocus() {
    mmFocusId = null;
    Object.keys(mmEls).forEach(function (nid) { mmEls[nid].classList.remove("mm-focus", "mm-next", "mm-dim"); });
    mmEdgeEls.forEach(function (e) { e.el.classList.remove("mm-hot", "mm-dim"); });
  }

  function mmApply() {
    if (mmVp) mmVp.setAttribute("transform", "translate(" + mmView.x + "," + mmView.y + ") scale(" + mmView.k + ")");
  }
  function mmFit() {
    if (!mmStage || !mmW) return;
    var r = mmStage.getBoundingClientRect();
    if (!r.width || !r.height) return;
    var pad = 30;
    var k = Math.min((r.width - pad) / mmW, (r.height - pad) / mmH, 1.5);
    if (!isFinite(k) || k <= 0) k = 1;
    mmView.k = k;
    mmView.x = (r.width - mmW * k) / 2;
    mmView.y = (r.height - mmH * k) / 2;
    mmClearFocus();
    if (mmVp) mmVp.classList.add("mm-animate");
    mmApply(); mmSyncSlider();
  }
  function mmZoom(factor, cx, cy) { mmSetZoom(mmView.k * factor, cx, cy); }
  // Absolute zoom (slider/wheel/buttons) — keeps (cx,cy) fixed on screen.
  function mmSetZoom(nk, cx, cy) {
    if (!mmStage) return;
    var r = mmStage.getBoundingClientRect();
    if (cx == null) { cx = r.width / 2; cy = r.height / 2; }
    nk = Math.max(0.2, Math.min(4, nk));
    mmView.x = cx - (cx - mmView.x) * (nk / mmView.k);
    mmView.y = cy - (cy - mmView.y) * (nk / mmView.k);
    mmView.k = nk; mmApply(); mmSyncSlider();
  }
  function mmSyncSlider() { var s = document.getElementById("mmZoom"); if (s) s.value = mmView.k; }
  function mmBindEvents(svg) {
    if (mmBound) return; mmBound = true;
    var panning = false, last = null, dragged = false, downNode = null;
    svg.addEventListener("pointerdown", function (ev) {
      panning = true; dragged = false; last = { x: ev.clientX, y: ev.clientY };
      var hit = ev.target.closest ? ev.target.closest(".mm-node") : null;
      downNode = hit ? hit.getAttribute("data-nid") : null;
      if (mmVp) mmVp.classList.remove("mm-animate");  // snappy pan, no easing
      svg.classList.add("panning"); svg.setPointerCapture(ev.pointerId);
    });
    svg.addEventListener("pointermove", function (ev) {
      if (!panning) return;
      var dx = ev.clientX - last.x, dy = ev.clientY - last.y;
      if (Math.abs(dx) + Math.abs(dy) > 3) dragged = true;
      mmView.x += dx; mmView.y += dy; last = { x: ev.clientX, y: ev.clientY }; mmApply();
    });
    function end() {
      if (panning && !dragged) {
        if (downNode) mmFocus(downNode);   // click a node → drill-in focus
        else mmClearFocus();               // click empty space → reset spotlight
      }
      panning = false; downNode = null; svg.classList.remove("panning");
    }
    svg.addEventListener("pointerup", end);
    svg.addEventListener("pointercancel", end);
    svg.addEventListener("dblclick", function (ev) {
      var hit = ev.target.closest ? ev.target.closest(".mm-node") : null;
      if (hit) goFull(hit.getAttribute("data-nid"));   // double-click → open full details
    });
    svg.addEventListener("wheel", function (ev) {
      ev.preventDefault();
      if (mmVp) mmVp.classList.remove("mm-animate");
      var r = mmStage.getBoundingClientRect();
      mmZoom(ev.deltaY < 0 ? 1.12 : 0.89, ev.clientX - r.left, ev.clientY - r.top);
    }, { passive: false });
  }

  /* ---- FULL CONTENT ---- */
  function buildFullPicker() {
    var sel = document.getElementById("fullPick");
    if (!sel) return;
    var opts = DATA.nodes.slice().sort(function (a, b) {
      return (CATLABEL[a.cat] || a.cat).localeCompare(CATLABEL[b.cat] || b.cat) || a.label.localeCompare(b.label);
    });
    sel.innerHTML = opts.map(function (n) {
      return "<option value='" + esc(n.id) + "'>" + esc((CATLABEL[n.cat] || n.cat) + " · " + n.label) + "</option>";
    }).join("");
    sel.addEventListener("change", function () { showFull(sel.value); });
  }
  function showFull(id) {
    var n = byId[id]; if (!n) return;
    currentFullId = id;
    var sel = document.getElementById("fullPick"); if (sel) sel.value = id;
    var h = "<div class='fc-cat' style='color:" + color(n.cat) + "'>" + esc((CATLABEL[n.cat] || n.cat).toUpperCase()) + "</div>";
    h += "<h2 class='fc-title'>" + esc(n.label) + "</h2>";
    if (n.status) h += "<div class='mb-2'><span class='badge badge-soft'>" + esc(n.status) + "</span></div>";
    h += "<p>" + esc(n.detail || "No description.") + "</p>";
    if (n.meta && Object.keys(n.meta).length) {
      h += "<table class='hive-table' style='max-width:480px'><tbody>";
      for (var k in n.meta) h += "<tr><th>" + esc(k) + "</th><td>" + esc(n.meta[k]) + "</td></tr>";
      h += "</tbody></table>";
    }
    if (n.route) h += "<a class='btn btn-sm btn-scarlet my-2' href='" + esc(n.route) + "'" + tgt(n.route) + "><i class='bi bi-box-arrow-up-right'></i> " + (ext(n.route) ? "Open link" : "Open page") + "</a>";
    var conns = adjL[n.id] || [];
    if (conns.length) {
      h += "<div class='section-label'>Connections (" + conns.length + ")</div><div class='fc-conns'>";
      conns.forEach(function (c) {
        var m = byId[c.id]; if (!m) return;
        var rel = c.label ? " <span class='muted'>· " + esc(c.label) + "</span>" : "";
        h += "<div class='fc-conn' data-id='" + esc(c.id) + "'>" + dot(m.cat) + esc(m.label) + rel + "</div>";
      });
      h += "</div>";
    }
    var body = document.getElementById("fullBody"); body.innerHTML = h;
    body.querySelectorAll(".fc-conn").forEach(function (row) {
      row.addEventListener("click", function () { showFull(row.getAttribute("data-id")); });
    });
  }
  // jump to a node in Full Content and switch to that lens
  function goFull(id) { showFull(id); setView("full"); }

  // re-apply category colours across the lenses when the picker changes one
  function recolorLenses() {
    var style = pref("nodeStyle", "outline");
    refreshMmBubbles();  // re-tint bubble gradients to the current colours
    Object.keys(mmEls).forEach(function (id) {
      var c = mmEls[id].querySelector("circle"), n = byId[id];
      if (c && n) { c.setAttribute("stroke", mmStroke(n.cat, style)); c.setAttribute("fill", mmFill(n.cat, style)); }
    });
    if (document.getElementById("outlineRoot")) renderOutline();
    if (document.getElementById("cardGrid")) paintCards();
    if (currentFullId) showFull(currentFullId);
    if (infoQuery) searchOutline(infoQuery);  // re-rendered outline lost its filter
  }

  /* ---- cross-lens search (one field, acts on the active lens) ---- */
  function currentView() {
    var b = document.querySelector(".vs-btn.active");
    return b ? b.getAttribute("data-view") : "map";
  }
  function firstMatch(q) {
    q = q.toLowerCase();
    for (var i = 0; i < DATA.nodes.length; i++) {
      if (hay(DATA.nodes[i]).indexOf(q) >= 0) return DATA.nodes[i].id;
    }
    return null;
  }
  function searchOutline(q) {
    var root = document.getElementById("outlineRoot"); if (!root) return;
    var lis = root.querySelectorAll(".ol-li");
    if (!q) { lis.forEach(function (li) { li.classList.remove("ol-hidden", "ol-hit"); }); return; }
    var ql = q.toLowerCase();
    lis.forEach(function (li) { li.classList.add("ol-hidden"); li.classList.remove("ol-hit"); });
    lis.forEach(function (li) {
      var a = li.querySelector(".ol-focus");
      var n = a && byId[a.getAttribute("data-id")];
      if (n && hay(n).indexOf(ql) >= 0) {
        li.classList.add("ol-hit");
        var cur = li;  // reveal the match and its ancestor path
        while (cur && cur.classList && cur.classList.contains("ol-li")) {
          cur.classList.remove("ol-hidden", "collapsed");
          cur = cur.parentElement ? cur.parentElement.closest(".ol-li") : null;
        }
      }
    });
  }
  function searchMindmap(q) {
    var ql = q.toLowerCase();
    Object.keys(mmEls).forEach(function (id) {
      var g = mmEls[id], n = byId[id];
      if (!q) { g.classList.remove("mm-search-hit", "mm-search-dim"); return; }
      var hit = n && hay(n).indexOf(ql) >= 0;
      g.classList.toggle("mm-search-hit", hit);
      g.classList.toggle("mm-search-dim", !hit);
    });
  }
  function applySearch(q) {
    infoQuery = q;
    var clear = document.getElementById("infoSearchClear"); if (clear) clear.hidden = !q;
    var gs = document.getElementById("gSearch");          // drive the Map's existing engine
    if (gs) { gs.value = q; gs.dispatchEvent(new Event("input", { bubbles: true })); }
    paintCards(); searchOutline(q); searchMindmap(q);
  }
  function searchEnter() {
    var q = (infoQuery || "").trim(); if (!q || !DATA) return;
    var id = firstMatch(q); if (!id) return;
    var v = currentView();
    if (v === "map") {
      var gs = document.getElementById("gSearch");
      if (gs) { gs.value = q; gs.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true })); }
    } else if (v === "mindmap") { mmFocus(id); }
    else if (v === "full") { showFull(id); }
    else {
      var el = document.querySelector(v === "cards" ? "#cardGrid .info-card" : "#outlineRoot .ol-hit");
      if (el) el.scrollIntoView({ block: "center", behavior: "smooth" });
    }
  }
  function initSearch() {
    var si = document.getElementById("infoSearch"); if (!si) return;
    si.addEventListener("input", function () { applySearch(si.value); });
    si.addEventListener("keydown", function (ev) { if (ev.key === "Enter") { ev.preventDefault(); searchEnter(); } });
    var sc = document.getElementById("infoSearchClear");
    if (sc) sc.addEventListener("click", function () { si.value = ""; applySearch(""); si.focus(); });
  }

  /* ---- small helper: bind once if element exists ---- */
  function bindOnce(elId, handler, evt, handler2) {
    var el = document.getElementById(elId); if (!el) return;
    el.addEventListener(evt || "click", handler || handler2);
  }

  bindOnce("mmFit", function () { mmFit(); });
  bindOnce("mmZoomIn", function () { mmZoom(1.2); });
  bindOnce("mmZoomOut", function () { mmZoom(0.8); });
  bindOnce("mmZoom", function () { mmSetZoom(parseFloat(document.getElementById("mmZoom").value)); }, "input");

  /* ---- Expand / full-screen the active lens ----
     Maximizes the whole #infoStage (so the lens switcher + search stay usable)
     as an in-page overlay, layered with the native Fullscreen API for true
     full screen where the browser allows it. Esc or the toggle restores. */
  var infoStage = document.getElementById("infoStage");
  var isExpanded = false;
  function refitActive() {
    var v = currentView();
    if (v === "map" && window.BUGraph) window.BUGraph.relayout();
    else if (v === "mindmap") mmFit();
  }
  function setExpanded(on) {
    if (!infoStage || on === isExpanded) return;
    isExpanded = on;
    infoStage.classList.toggle("info-expanded", on);
    var btn = document.getElementById("infoExpand");
    if (btn) {
      btn.setAttribute("aria-pressed", on ? "true" : "false");
      btn.classList.toggle("active", on);
      var ic = btn.querySelector("i"), lbl = btn.querySelector("span");
      if (ic) ic.className = on ? "bi bi-fullscreen-exit" : "bi bi-arrows-fullscreen";
      if (lbl) lbl.textContent = on ? "Restore" : "Expand";
      btn.title = on ? "Restore this view (Esc)" : "Expand this view — fill the screen (Esc to exit)";
    }
    // true full screen where supported; the in-page overlay stands in either way
    try {
      if (on && infoStage.requestFullscreen && !document.fullscreenElement) infoStage.requestFullscreen();
      else if (!on && document.fullscreenElement) document.exitFullscreen();
    } catch (e) { /* overlay alone is enough */ }
    // let the new size settle, then refit the visual lenses
    requestAnimationFrame(function () { requestAnimationFrame(refitActive); });
  }
  bindOnce("infoExpand", function () { setExpanded(!isExpanded); });
  document.addEventListener("keydown", function (ev) {
    if (ev.key === "Escape" && isExpanded && !document.fullscreenElement) setExpanded(false);
  });
  // leaving native full screen (Esc / browser chrome) drops us back to normal too
  document.addEventListener("fullscreenchange", function () {
    if (!document.fullscreenElement && isExpanded) setExpanded(false);
  });
  window.addEventListener("resize", function () { if (isExpanded) refitActive(); });
})();
/* AI-GENERATED END */
