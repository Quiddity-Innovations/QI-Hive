/* AI-GENERATED BEGIN (Claude Code, 2026-06-19)
   BU Hive Information — a self-contained, dependency-free force-directed graph
   with TheBrain-style focus (click a node: it and its links light up, the rest
   recede). Pan (drag background), zoom (wheel), drag nodes, search. No CDN. */
(function () {
  "use strict";
  var NS = "http://www.w3.org/2000/svg";
  var svg = document.getElementById("graphSvg");
  var stage = document.getElementById("graphStage");
  if (!svg) return;

  // Fallback palette if the shared store (bu-colors.js) isn't loaded; mirrors BUCAT.DEFAULTS.
  var CATCOLOR = { hub: "#CC0000", layer: "#E8552D", page: "#F0883E", project: "#E64980",
    data: "#4DABF7", config: "#9775FA", security: "#FAB005", hook: "#20C997", custom: "#E599F7" };
  function catColor(cat) {
    return (window.BUCAT && window.BUCAT.get) ? window.BUCAT.get(cat) : (CATCOLOR[cat] || "#888");
  }
  // User appearance prefs (window.BUSET) with safe fallbacks.
  function pref(k, d) { return (window.BUSET && window.BUSET.get(k) != null) ? window.BUSET.get(k) : d; }
  function nodeScale() { return parseFloat(pref("nodeScale", 1)) || 1; }

  // ---- "Bubble" style: glossy 3D spheres via a per-category radial gradient
  // (bright off-centre highlight → saturated mid → dark rim). One gradient per
  // category, reused by every node of that kind; re-tinted live when colours change.
  function shade(hex, amt) {  // amt>0 → toward white, amt<0 → toward black
    var m = /^#?([0-9a-f]{6})$/i.exec(hex || ""); if (!m) return hex || "#888";
    var n = parseInt(m[1], 16), r = (n >> 16) & 255, g = (n >> 8) & 255, b = n & 255;
    if (amt >= 0) { r += (255 - r) * amt; g += (255 - g) * amt; b += (255 - b) * amt; }
    else { var k = 1 + amt; r *= k; g *= k; b *= k; }
    function cl(x) { return Math.max(0, Math.min(255, Math.round(x))); }
    return "#" + ((1 << 24) + (cl(r) << 16) + (cl(g) << 8) + cl(b)).toString(16).slice(1);
  }
  function bubbleStops(cat) {
    var base = catColor(cat);
    return [["0%", "#ffffff", "0.92"], ["20%", shade(base, 0.5), "1"],
            ["58%", base, "1"], ["100%", shade(base, -0.34), "1"]];
  }
  function ensureBubble(cat) {
    if (!gDefs) return null;
    if (!bubGrads[cat]) {
      var grad = el("radialGradient", { id: "gmbub-" + cat, cx: "50%", cy: "50%", r: "58%", fx: "34%", fy: "30%" });
      var stops = bubbleStops(cat).map(function (st) {
        var s = el("stop", { offset: st[0], "stop-color": st[1], "stop-opacity": st[2] });
        grad.appendChild(s); return s;
      });
      gDefs.appendChild(grad); bubGrads[cat] = stops;
    }
    return "gmbub-" + cat;
  }
  function refreshBubbles() {
    for (var cat in bubGrads) {
      var st = bubbleStops(cat);
      bubGrads[cat].forEach(function (s, i) { s.setAttribute("stop-color", st[i][1]); s.setAttribute("stop-opacity", st[i][2]); });
    }
  }
  function nodeFill(nd) {
    var style = pref("nodeStyle", "outline");
    if (style === "filled") return catColor(nd.cat);
    if (style === "bubble") { var id = ensureBubble(nd.cat); return id ? "url(#" + id + ")" : catColor(nd.cat); }
    return "transparent";
  }
  function nodeStrokeColor(nd) {
    return pref("nodeStyle", "outline") === "bubble" ? shade(catColor(nd.cat), -0.3) : catColor(nd.cat);
  }
  // searchable text: label + description + meta values (e.g. a node's file path)
  function nodeHay(m) {
    var parts = [m.label, m.detail || ""];
    if (m.meta) for (var k in m.meta) parts.push(String(m.meta[k]));
    return parts.join(" ").toLowerCase();
  }
  var CATLABEL = { hub: "BU Hive core", layer: "Nav layer", page: "Page", data: "Data source",
    config: "Config / data", project: "Project", security: "Security / governance",
    hook: "Automation hook", custom: "Custom / file" };
  var SIZE = { hub: 26, layer: 16, project: 13, config: 13, data: 12, security: 11, hook: 11, page: 9 };

  var W = 0, H = 0, view = { x: 0, y: 0, k: 1 };
  var nodes = [], edges = [], byId = {}, adj = {};
  var active = null, paused = false, raf = null, sizedOK = false;
  var dragNode = null, dragMoved = false, panning = false, last = null;

  function el(tag, attrs) { var e = document.createElementNS(NS, tag);
    for (var k in attrs) e.setAttribute(k, attrs[k]); return e; }
  function size() { var r = stage.getBoundingClientRect(); W = r.width; H = r.height; }
  function gx(cx) { return (cx - stage.getBoundingClientRect().left - view.x) / view.k; }
  function gy(cy) { return (cy - stage.getBoundingClientRect().top - view.y) / view.k; }

  // Endpoint comes from a data-attribute (CSP-safe — no inline script needed).
  var ENDPOINT = (stage && stage.getAttribute("data-endpoint")) ||
                 window.BU_GRAPH_ENDPOINT || "/api/graph";
  fetch(ENDPOINT).then(function (r) { return r.json(); })
    .then(init).catch(function () { stage.innerHTML = "<div class='notice' style='margin:18px'>Graph unavailable.</div>"; });

  function init(data) {
    size();
    data.nodes.forEach(function (node) {
      node.vx = 0; node.vy = 0; node.r = SIZE[node.cat] || 9; node.dispR = node.r;
      node.ringAng = null; node.fixed = false;
      byId[node.id] = node; adj[node.id] = adj[node.id] || {};
    });
    nodes = data.nodes;
    edges = data.edges.map(function (e) { return { s: e.s, t: e.t, label: e.label, sn: byId[e.s], tn: byId[e.t] }; })
      .filter(function (e) { return e.sn && e.tn; });
    edges.forEach(function (e) { adj[e.s][e.t] = e.label || true; adj[e.t][e.s] = e.label || true; });
    seed();
    sizedOK = W > 0 && H > 0;  // false if we initialised while the map pane was hidden
    buildDom(); colorLegend(); bindEvents(); initLegend();
    applyPrefs();  // honour saved style / labels / physics prefs
    if (window.BUSET && window.BUSET.onChange) window.BUSET.onChange(applyPrefs);
    start();
    if (byId.hub) focus(byId.hub);
  }

  // Place nodes in a ring around the hub. Falls back to sane dims if the stage
  // is hidden (zero-size) at init — relayout() re-seeds once it's visible.
  function seed() {
    var cx = (W || 900) / 2, cy = (H || 560) / 2, n = nodes.length || 1;
    nodes.forEach(function (node, i) {
      var a = i / n * Math.PI * 2;
      node.x = node.cat === "hub" ? cx : cx + Math.cos(a) * (130 + Math.random() * 170);
      node.y = node.cat === "hub" ? cy : cy + Math.sin(a) * (110 + Math.random() * 150);
    });
  }

  // Called by bu-info-views.js when the Map lens becomes visible, so a graph
  // that initialised hidden gets a correct first layout instead of a clump.
  function relayout() {
    size();
    if (!sizedOK && W > 0) { seed(); sizedOK = true; }
    fit();
  }
  window.BUGraph = { relayout: relayout, fit: fit };

  var vp, gEdges, gNodes, gLabels, gDefs = null, bubGrads = {};
  function buildDom() {
    svg.innerHTML = "";
    gDefs = el("defs", {}); bubGrads = {};
    vp = el("g", {}); gEdges = el("g", {}); gLabels = el("g", {}); gNodes = el("g", {});
    svg.appendChild(gDefs);
    vp.appendChild(gEdges); vp.appendChild(gLabels); vp.appendChild(gNodes); svg.appendChild(vp);
    edges.forEach(function (e) { e.line = el("line", { class: "gm-edge" }); gEdges.appendChild(e.line); });
    nodes.forEach(function (node) {
      var g = el("g", { class: "gm-node" });
      node.circle = el("circle", { r: node.r, fill: nodeFill(node), stroke: nodeStrokeColor(node) });
      node.circle.classList.toggle("gm-bubble", pref("nodeStyle", "outline") === "bubble");
      node.text = el("text", { "text-anchor": "middle" }); node.text.textContent = node.label;
      g.appendChild(node.circle); g.appendChild(node.text); node.g = g;
      g.addEventListener("pointerdown", function (ev) { startNodeDrag(node, ev); });
      gNodes.appendChild(g);
    });
  }

  function colorLegend() {
    document.querySelectorAll(".cat-sw").forEach(function (sw) {
      sw.style.background = catColor(sw.getAttribute("data-cat"));
    });
    document.querySelectorAll(".cat-color").forEach(function (inp) {
      inp.value = catColor(inp.getAttribute("data-cat"));
    });
  }

  // Re-colour node circles + sync the legend when a colour changes anywhere.
  function recolorNodes() {
    refreshBubbles();  // re-tint any bubble gradients to the current colours
    var bubble = pref("nodeStyle", "outline") === "bubble";
    nodes.forEach(function (nd) {
      if (!nd.circle) return;
      nd.circle.setAttribute("stroke", nodeStrokeColor(nd));
      nd.circle.setAttribute("fill", nodeFill(nd));
      nd.circle.classList.toggle("gm-bubble", bubble);
    });
    colorLegend();
    if (active) detail(active);  // refresh the open detail panel's swatches
  }

  // Apply appearance prefs (style, labels, physics) live from the Config page.
  function applyPrefs() {
    recolorNodes();  // covers fill/outline + colours
    var showLabels = pref("showLabels", true);
    nodes.forEach(function (nd) { if (nd.text) nd.text.style.display = showLabels ? "" : "none"; });
    // keep the legend + connection swatches matching the current sphere style
    var st = pref("nodeStyle", "outline");
    var box = document.querySelector(".graph-legend-box");
    if (box) {
      box.classList.toggle("style-outline", st === "outline");
      box.classList.toggle("style-filled", st === "filled");
      box.classList.toggle("style-bubble", st === "bubble");
    }
    var de = document.documentElement.classList;
    de.toggle("gm-sw-outline", st === "outline");
    de.toggle("gm-sw-bubble", st === "bubble");
    paused = !pref("physics", true);
    var pb = document.getElementById("gPhysics");
    if (pb) pb.innerHTML = paused ? "<i class='bi bi-play-fill'></i>" : "<i class='bi bi-pause-fill'></i>";
    render();  // reflect scale/style immediately even while paused
  }

  /* ---- legend category filter (which kinds show on the map) ---- */
  var CATKEY = "bu-hive-mapcats";
  var hiddenCats = {};
  function loadHiddenCats() {
    try { var s = localStorage.getItem(CATKEY); if (s) JSON.parse(s).forEach(function (k) { hiddenCats[k] = 1; }); }
    catch (e) { /* ignore */ }
  }
  function saveHiddenCats() {
    try { localStorage.setItem(CATKEY, JSON.stringify(Object.keys(hiddenCats))); } catch (e) { /* ignore */ }
  }
  function applyCatFilter() {
    nodes.forEach(function (nd) {
      nd.hidden = !!hiddenCats[nd.cat];
      if (nd.g) nd.g.style.display = nd.hidden ? "none" : "";
    });
    edges.forEach(function (e) {
      var hide = hiddenCats[e.sn.cat] || hiddenCats[e.tn.cat];
      e.line.style.display = hide ? "none" : "";
    });
  }
  function setRowState(row, on) {
    row.classList.toggle("off", !on);
    row.setAttribute("aria-pressed", on ? "true" : "false");
  }
  function initLegend() {
    loadHiddenCats();
    var box = document.querySelector(".graph-legend-box");
    if (box) {
      box.querySelectorAll(".glb-row").forEach(function (row) {
        var cat = row.getAttribute("data-cat");
        setRowState(row, !hiddenCats[cat]);
        function toggle() {
          if (hiddenCats[cat]) delete hiddenCats[cat]; else hiddenCats[cat] = 1;
          setRowState(row, !hiddenCats[cat]);
          saveHiddenCats(); applyCatFilter();
        }
        row.addEventListener("click", toggle);
        row.addEventListener("keydown", function (ev) {
          if (ev.target && ev.target.classList.contains("cat-color")) return;  // let the picker handle keys
          if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); toggle(); }
        });
        // colour picker (the dot) — must not toggle the row's visibility
        var inp = row.querySelector(".cat-color");
        if (inp) {
          inp.value = catColor(cat);
          inp.addEventListener("click", function (ev) { ev.stopPropagation(); });
          inp.addEventListener("input", function (ev) {
            ev.stopPropagation();
            if (window.BUCAT) window.BUCAT.set(cat, inp.value);
            else { CATCOLOR[cat] = inp.value; recolorNodes(); }
          });
        }
      });
      var all = document.getElementById("glbAll");
      if (all) all.addEventListener("click", function () {
        hiddenCats = {}; saveHiddenCats();
        box.querySelectorAll(".glb-row").forEach(function (r) { setRowState(r, true); });
        applyCatFilter();
      });
      var rc = document.getElementById("glbResetColors");
      if (rc) rc.addEventListener("click", function () {
        if (window.BUCAT) window.BUCAT.reset();  // fires onChange -> recolorNodes -> colorLegend
        else { colorLegend(); }
      });
    }
    // recolour the map whenever a category colour changes (here or in another lens)
    if (window.BUCAT && window.BUCAT.onChange) window.BUCAT.onChange(recolorNodes);
    applyCatFilter();
  }

  /* ---- force simulation ---- */
  function tick() {
    var i, j, a, b, dx, dy, d2, d, f;
    for (i = 0; i < nodes.length; i++) {
      a = nodes[i];
      if (a.hidden) continue;
      for (j = i + 1; j < nodes.length; j++) {
        b = nodes[j];
        if (b.hidden) continue;
        dx = a.x - b.x; dy = a.y - b.y; d2 = dx * dx + dy * dy || 0.01;
        if (d2 > 90000) continue;
        f = 2600 / d2; d = Math.sqrt(d2);
        var ux = dx / d, uy = dy / d;
        a.vx += ux * f; a.vy += uy * f; b.vx -= ux * f; b.vy -= uy * f;
      }
    }
    edges.forEach(function (e) {
      if (e.sn.hidden || e.tn.hidden) return;
      a = e.sn; b = e.tn; dx = b.x - a.x; dy = b.y - a.y; d = Math.sqrt(dx * dx + dy * dy) || 0.01;
      var target = (a.cat === "hub" || b.cat === "hub") ? 95 : 78;
      f = (d - target) * 0.018; var ux = dx / d, uy = dy / d;
      a.vx += ux * f; a.vy += uy * f; b.vx -= ux * f; b.vy -= uy * f;
    });
    var anchorX = W / 2, anchorY = H / 2, RING_R = 140;
    nodes.forEach(function (nd) {
      if (nd.hidden) return;  // filtered-out category — frozen and not drawn
      // gentle gravity to keep graph on-screen; active node pulled to centre
      nd.vx += (anchorX - nd.x) * 0.006; nd.vy += (anchorY - nd.y) * 0.006;
      if (nd === active) {
        nd.vx += (anchorX - nd.x) * 0.05; nd.vy += (anchorY - nd.y) * 0.05;
      } else if (active && nd.ringAng != null) {
        // associate: spring into its slot in the ring around the target
        var tx = active.x + Math.cos(nd.ringAng) * RING_R, ty = active.y + Math.sin(nd.ringAng) * RING_R;
        nd.vx += (tx - nd.x) * 0.06; nd.vy += (ty - nd.y) * 0.06;
      } else if (active) {
        // unrelated: drift outward so the focused cluster has room to expand
        var dx = nd.x - active.x, dy = nd.y - active.y, d = Math.sqrt(dx * dx + dy * dy) || 1;
        if (d < 250) { nd.vx += (dx / d) * 0.7; nd.vy += (dy / d) * 0.7; }
      }
      if (nd.fixed) { nd.vx = nd.vy = 0; return; }
      nd.vx *= 0.86; nd.vy *= 0.86;
      nd.vx = Math.max(-12, Math.min(12, nd.vx)); nd.vy = Math.max(-12, Math.min(12, nd.vy));
      nd.x += nd.vx; nd.y += nd.vy;
    });
    render();
  }

  function render() {
    edges.forEach(function (e) {
      e.line.setAttribute("x1", e.sn.x); e.line.setAttribute("y1", e.sn.y);
      e.line.setAttribute("x2", e.tn.x); e.line.setAttribute("y2", e.tn.y);
    });
    var sc = nodeScale();
    nodes.forEach(function (nd) {
      var dr = (nd.dispR || nd.r) * sc;
      nd.circle.setAttribute("cx", nd.x); nd.circle.setAttribute("cy", nd.y);
      nd.circle.setAttribute("r", dr);
      nd.text.setAttribute("x", nd.x); nd.text.setAttribute("y", nd.y + dr + 11);
    });
    vp.setAttribute("transform", "translate(" + view.x + "," + view.y + ") scale(" + view.k + ")");
  }

  function loop() { if (!paused) tick(); raf = requestAnimationFrame(loop); }
  function start() { if (!raf) loop(); }

  /* ---- focus (TheBrain plex) ---- */
  function neighbors(n) { var s = {}; s[n.id] = 1; for (var k in adj[n.id]) s[k] = 1; return s; }
  function focus(n) {
    active = n; var nb = neighbors(n);
    var nbIds = Object.keys(nb).filter(function (id) { return id !== n.id; });
    nodes.forEach(function (m) {
      var isNb = !!nb[m.id];
      m.g.classList.toggle("dim", !isNb);
      m.g.classList.toggle("active", m === n);
      m.g.classList.remove("hit");
      // expand the target, enlarge its associates, shrink everything else
      m.dispR = (m === n) ? m.r * 1.7 : (isNb ? m.r * 1.3 : m.r * 0.8);
      m.ringAng = null;
    });
    // arrange associates evenly around the target (the "expand" plex)
    nbIds.forEach(function (id, i) {
      var m = byId[id]; if (m) m.ringAng = (i / nbIds.length) * Math.PI * 2;
    });
    edges.forEach(function (e) {
      var hot = e.s === n.id || e.t === n.id;
      e.line.classList.toggle("hot", hot); e.line.classList.toggle("dim", !hot);
    });
    nodes.forEach(function (m) { m.vx += (Math.random() - .5) * 2; m.vy += (Math.random() - .5) * 2; });
    detail(n);
  }

  function detail(n) {
    document.getElementById("gdCat").textContent = (CATLABEL[n.cat] || n.cat).toUpperCase();
    document.getElementById("gdCat").style.color = catColor(n.cat);
    document.getElementById("gdTitle").textContent = n.label;
    var html = "<p>" + (n.detail || "") + "</p>";
    if (n.meta && Object.keys(n.meta).length) {
      html += "<div class='d-flex flex-wrap gap-1 mb-2'>";
      for (var k in n.meta) html += "<span class='badge badge-soft'>" + k + ": " + n.meta[k] + "</span>";
      html += "</div>";
    }
    if (n.status) html += "<div class='mb-2'><span class='badge badge-soft'>" + n.status + "</span></div>";
    if (n.route) {
      var ext = /^https?:\/\//.test(n.route);
      html += "<a class='btn btn-sm btn-scarlet mb-3' href='" + n.route + "'" +
        (ext ? " target='_blank' rel='noopener'" : "") + "><i class='bi bi-box-arrow-up-right'></i> " +
        (ext ? "Open link" : "Open page") + "</a>";
    }
    var ks = Object.keys(adj[n.id]);
    if (ks.length) {
      html += "<div class='section-label' style='margin:8px 0 4px'>Connections (" + ks.length + ")</div>";
      ks.forEach(function (id) {
        var m = byId[id]; if (!m) return;
        var rel = adj[n.id][id]; rel = (rel && rel !== true) ? " · " + rel : "";
        html += "<div class='gd-rel' data-id='" + id + "'><span class='swatch' style='background:" +
          catColor(m.cat) + "'></span><span>" + m.label + "<span class='muted'>" + rel + "</span></span></div>";
      });
    }
    var body = document.getElementById("gdBody"); body.innerHTML = html;
    body.querySelectorAll(".gd-rel").forEach(function (row) {
      row.addEventListener("click", function () { var m = byId[row.getAttribute("data-id")]; if (m) focus(m); });
    });
  }

  /* ---- interaction ---- */
  function startNodeDrag(node, ev) {
    ev.stopPropagation(); dragNode = node; dragMoved = false; node.fixed = true;
    svg.setPointerCapture(ev.pointerId);
  }
  function bindEvents() {
    svg.addEventListener("pointerdown", function (ev) {
      if (dragNode) return; panning = true; last = { x: ev.clientX, y: ev.clientY };
      svg.classList.add("panning"); svg.setPointerCapture(ev.pointerId);
    });
    svg.addEventListener("pointermove", function (ev) {
      if (dragNode) { dragMoved = true; dragNode.x = gx(ev.clientX); dragNode.y = gy(ev.clientY); return; }
      if (panning) { view.x += ev.clientX - last.x; view.y += ev.clientY - last.y;
        last = { x: ev.clientX, y: ev.clientY }; }
    });
    function endPointer() {
      if (dragNode) { if (!dragMoved) focus(dragNode); dragNode = null; }
      panning = false; svg.classList.remove("panning");
    }
    svg.addEventListener("pointerup", endPointer);
    svg.addEventListener("pointercancel", endPointer);
    svg.addEventListener("wheel", function (ev) {
      ev.preventDefault();
      var rect = stage.getBoundingClientRect();
      setZoom(view.k * (ev.deltaY < 0 ? 1.12 : 0.89), ev.clientX - rect.left, ev.clientY - rect.top);
    }, { passive: false });

    var zoom = document.getElementById("gZoom");
    if (zoom) {
      zoom.value = view.k;
      zoom.addEventListener("input", function () { setZoom(parseFloat(zoom.value)); });
    }

    document.getElementById("gReset").addEventListener("click", function () {
      active = null;
      nodes.forEach(function (m) {
        m.fixed = false; m.dispR = m.r; m.ringAng = null;
        m.g.classList.remove("dim", "active", "hit");
      });
      edges.forEach(function (e) { e.line.classList.remove("hot", "dim"); });
      if (byId.hub) focus(byId.hub);
    });
    document.getElementById("gPhysics").addEventListener("click", function (e) {
      paused = !paused; e.currentTarget.innerHTML = paused ? "<i class='bi bi-play-fill'></i>" : "<i class='bi bi-pause-fill'></i>";
    });
    document.getElementById("gFit").addEventListener("click", fit);
    var search = document.getElementById("gSearch");
    search.addEventListener("input", function () {
      var q = search.value.trim().toLowerCase();
      nodes.forEach(function (m) {
        var hit = q && nodeHay(m).indexOf(q) >= 0;
        m.g.classList.toggle("hit", !!hit);
        if (q) m.g.classList.toggle("dim", !hit); else if (!active) m.g.classList.remove("dim");
      });
    });
    search.addEventListener("keydown", function (ev) {
      if (ev.key !== "Enter") return;
      var q = search.value.trim().toLowerCase();
      var hit = nodes.filter(function (m) { return nodeHay(m).indexOf(q) >= 0; })[0];
      if (hit) focus(hit);
    });
    window.addEventListener("resize", size);
  }

  function fit() {
    if (!nodes.length) return;
    var minX = 1e9, minY = 1e9, maxX = -1e9, maxY = -1e9, seen = 0;
    nodes.forEach(function (n) {
      if (n.hidden) return;  // frame only the visible categories
      seen++; minX = Math.min(minX, n.x); minY = Math.min(minY, n.y);
      maxX = Math.max(maxX, n.x); maxY = Math.max(maxY, n.y);
    });
    if (!seen) return;
    var pad = 60, gw = (maxX - minX) || 1, gh = (maxY - minY) || 1;
    var k = Math.min((W - pad) / gw, (H - pad) / gh, 2);
    view.k = k; view.x = (W - (minX + maxX) * k) / 2; view.y = (H - (minY + maxY) * k) / 2;
    syncZoomSlider(); render();
  }

  // Absolute zoom (slider/wheel) — keeps the point (cx,cy) fixed on screen.
  function setZoom(nk, cx, cy) {
    nk = Math.max(0.3, Math.min(3, nk));
    if (cx == null) { cx = W / 2; cy = H / 2; }
    view.x = cx - (cx - view.x) * (nk / view.k);
    view.y = cy - (cy - view.y) * (nk / view.k);
    view.k = nk; syncZoomSlider(); render();
  }
  function syncZoomSlider() { var s = document.getElementById("gZoom"); if (s) s.value = view.k; }
})();
/* AI-GENERATED END */
