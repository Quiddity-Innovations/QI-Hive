/* ============================================================
   QI Plex — D3 force-directed renderer for the Documentation Brain graph.

   Rebuilt 2026-08-22. The previous Plex was a stock vis-network canvas:
   grey boxes, grey lines, no legend, every affordance buried in a
   right-click menu. This is a straight port of the visual grammar used by
   the World Mythologies relationship map (C:\APPS\Mythologies\site\js),
   which is the quality bar Renne asked for.

   What that grammar buys, concretely:
     · node radius encodes degree — the hubs are visibly the hubs
     · every relation has its own colour AND dash pattern, so the graph
       survives greyscale printing and colour-vision deficiency
     · selecting dims instead of hides, so context is never lost
     · SVG, not canvas — nodes are real focusable elements, so the graph
       is keyboard-navigable and screen-reader addressable

   Public API — QIPlex.create(container, opts) -> instance
     opts.fetchGraph(id)  -> Promise<{focus, nodes[], links[]}>   (required)
     opts.onSelect(node)  called when a node is selected (may be null)
     opts.onRecenter(id, data)  called after the Plex re-centres
     opts.actions         { open, reveal, download, copy } — omit any to
                          hide that button; each takes the bare node id
     instance.recenter(id), .select(id), .home(), .fit(), .resize(), .destroy()

   Depends on d3 v7 being on the page (window.d3).
   ============================================================ */
"use strict";

var QIPlex = (function () {

  /* Brain entity types. Colour comes from CSS custom properties so the
     Plex follows the dashboard theme rather than carrying its own. */
  var TYPES = {
    root:     { label: "Ecosystem", varName: "--plex-root" },
    project:  { label: "Project",   varName: "--plex-project" },
    doc:      { label: "Document",  varName: "--plex-doc" },
    decision: { label: "Decision",  varName: "--plex-decision" },
    feature:  { label: "Feature",   varName: "--plex-feature" },
    session:  { label: "Session",   varName: "--plex-session" }
  };
  var TYPE_ORDER = ["root", "project", "doc", "decision", "feature", "session"];

  /* Edge label (as the API emits it) -> visual relation kind. The API uses
     the bare type name for the leaf branches (decision/feature/session) and
     a verb everywhere else; both map onto the same six kinds. */
  var EDGE_KIND = {
    project: "project", has: "has", mentions: "mentions",
    decided: "decided", decision: "decided",
    implements: "implements", feature: "implements",
    produced: "produced", session: "produced"
  };
  var EDGE_LABEL = {
    project: "in ecosystem", has: "contains", mentions: "mentions",
    decided: "decided", implements: "implements", produced: "produced",
    other: "related"
  };
  var EDGE_ORDER = ["project", "has", "decided", "implements", "produced", "mentions"];
  var DIRECTIONAL = { has: 1, decided: 1, implements: 1, produced: 1, mentions: 1 };
  /* Above this many lit edges, captions stop helping and start shouting. */
  var EDGE_LABEL_CAP = 14;

  function edgeKind(label) { return EDGE_KIND[label] || "other"; }
  function nodeType(n) { return TYPES[n.type] ? n.type : "doc"; }

  /* Resolve a CSS custom property against a live element, so a theme
     switch is picked up on the next render without a hardcoded palette. */
  function cssVar(el, name, fallback) {
    try {
      var v = getComputedStyle(el).getPropertyValue(name).trim();
      return v || fallback;
    } catch (e) { return fallback; }
  }

  /* Pick black or white for the medallion initial, by luminance — the same
     rule the Mythologies map uses, so a gold disc gets dark ink and a
     slate one gets light. Handles #rgb, #rrggbb and rgb(). */
  function letterInk(color) {
    var r = 0, g = 0, b = 0, m;
    if (!color) return "#fdf8ec";
    if (color.charAt(0) === "#") {
      var h = color.slice(1);
      if (h.length === 3) h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2];
      var n = parseInt(h, 16);
      if (isNaN(n)) return "#fdf8ec";
      r = (n >> 16) & 255; g = (n >> 8) & 255; b = n & 255;
    } else if ((m = color.match(/rgba?\(([^)]+)\)/))) {
      var p = m[1].split(",");
      r = parseFloat(p[0]); g = parseFloat(p[1]); b = parseFloat(p[2]);
    } else return "#fdf8ec";
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) > 150 ? "#1c1608" : "#fdf8ec";
  }

  function initialOf(label) {
    var m = String(label || "?").match(/[A-Za-z0-9]/);
    return m ? m[0].toUpperCase() : "\u25C6";
  }

  function truncate(s, n) {
    s = String(s == null ? "" : s);
    return s.length > n ? s.slice(0, n - 1).replace(/[\s\-_,.]+$/, "") + "\u2026" : s;
  }

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function bareId(id) { var i = String(id).indexOf(":"); return i < 0 ? id : id.slice(i + 1); }

  /* ---------------------------------------------------------------- */

  function create(container, opts) {
    opts = opts || {};
    if (!container) throw new Error("QIPlex: no container");
    if (typeof opts.fetchGraph !== "function") throw new Error("QIPlex: fetchGraph is required");
    var actions = opts.actions || {};

    container.classList.add("qi-plex");
    container.innerHTML = "";

    /* ---- chrome ---- */
    var svgEl = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svgEl.setAttribute("class", "plex-svg");
    svgEl.setAttribute("role", "application");
    svgEl.setAttribute("aria-roledescription", "knowledge graph");
    svgEl.setAttribute("aria-label",
      "Documentation Brain relationship graph. Tab moves between nodes, Enter selects one, " +
      "E expands it, Escape clears the selection. The Search lens lists the same documents without the graph.");
    container.appendChild(svgEl);

    var loading = document.createElement("div");
    loading.className = "qi-plex-loading";
    loading.setAttribute("role", "status");
    loading.innerHTML = '<span class="qi-plex-ring" aria-hidden="true"></span> Drawing the Plex\u2026';
    container.appendChild(loading);

    var tools = document.createElement("div");
    tools.className = "plex-tools";
    tools.setAttribute("role", "group");
    tools.setAttribute("aria-label", "Plex view controls");
    tools.innerHTML =
      '<button type="button" class="plex-btn" data-act="in"   aria-label="Zoom in" title="Zoom in">+</button>' +
      '<button type="button" class="plex-btn" data-act="out"  aria-label="Zoom out" title="Zoom out">\u2212</button>' +
      '<button type="button" class="plex-btn" data-act="fit"  aria-label="Fit to view" title="Fit to view">\u21BA</button>' +
      '<button type="button" class="plex-btn" data-act="home" aria-label="Back to the ecosystem root" title="Ecosystem root">\u2302</button>';
    container.appendChild(tools);

    var legend = document.createElement("details");
    legend.className = "plex-legend";
    legend.innerHTML = "<summary>Legend</summary><div class='legend-body'></div>";
    container.appendChild(legend);

    var inspector = document.createElement("div");
    inspector.className = "plex-inspector";
    inspector.setAttribute("role", "region");
    inspector.setAttribute("aria-label", "Selected node");
    container.appendChild(inspector);

    /* ---- d3 scaffolding ---- */
    var svg = d3.select(svgEl);
    var defs = svg.append("defs");
    EDGE_ORDER.concat(["other"]).forEach(function (k) {
      if (!DIRECTIONAL[k]) return;
      defs.append("marker")
        .attr("id", "plex-arrow-" + k)
        .attr("viewBox", "0 0 10 10")
        .attr("refX", 9).attr("refY", 5)
        .attr("markerWidth", 7).attr("markerHeight", 7)
        .attr("orient", "auto-start-reverse")
        .append("path").attr("class", "m-" + k).attr("d", "M0,0 L10,5 L0,10 Z");
    });

    var gRoot = svg.append("g");
    var gLinks = gRoot.append("g").attr("aria-hidden", "true");
    var gELabels = gRoot.append("g").attr("aria-hidden", "true");
    var gNodes = gRoot.append("g");

    var zoomBehavior = d3.zoom()
      .scaleExtent([0.2, 5])
      .on("zoom", function (ev) { gRoot.attr("transform", ev.transform); })
      .on("start", function () { svg.classed("grabbing", true); })
      .on("end", function () { svg.classed("grabbing", false); });
    svg.call(zoomBehavior).on("dblclick.zoom", null);

    /* ---- state ---- */
    var sim = null, nodeSel = null, edgeSel = null, elabelSel = null;
    var nodes = [], links = [], neighbors = new Map();
    var focusId = null, selectedId = null;
    var trail = [];                       /* breadcrumb of re-centres */
    var destroyed = false;
    var reqSeq = 0;                       /* drop out-of-order responses */
    var positions = new Map();            /* keep layout stable across re-centres */

    function W() { return container.clientWidth || 900; }
    function H() { return container.clientHeight || 600; }

    function degree(id) { var s = neighbors.get(id); return s ? s.size : 0; }
    function nodeRadius(d) {
      var r = 15 + degree(d.id) * 1.5;
      if (d.type === "root") r += 6;
      return Math.max(16, Math.min(36, r));
    }
    function typeColor(t) {
      var spec = TYPES[t] || TYPES.doc;
      return cssVar(container, spec.varName, "#9aa6b8");
    }

    /* ---------------- data shaping ---------------- */
    function ingest(d) {
      var byId = new Map();
      (d.nodes || []).forEach(function (n) { byId.set(n.id, n); });

      neighbors = new Map();
      byId.forEach(function (_, id) { neighbors.set(id, new Set()); });
      (d.links || []).forEach(function (l) {
        if (neighbors.has(l.from)) neighbors.get(l.from).add(l.to);
        if (neighbors.has(l.to)) neighbors.get(l.to).add(l.from);
      });

      /* Seed each node at its previous position where we have one, so
         re-centring reads as the graph rearranging rather than a cut. */
      nodes = (d.nodes || []).map(function (n) {
        var prev = positions.get(n.id);
        var seed = prev || { x: W() / 2 + (Math.random() - 0.5) * 120,
                             y: H() / 2 + (Math.random() - 0.5) * 120 };
        return Object.assign({}, n, { type: nodeType(n), x: seed.x, y: seed.y });
      });

      links = (d.links || [])
        .filter(function (l) { return byId.has(l.from) && byId.has(l.to); })
        .map(function (l) {
          return { from: l.from, to: l.to, label: l.label,
                   kind: edgeKind(l.label), source: l.from, target: l.to };
        });

      /* Fan parallel edges apart so a doubled relation is two arcs, not
         one line hiding another. */
      var count = new Map(), seen = new Map();
      links.forEach(function (l) {
        var k = [l.from, l.to].sort().join("|");
        count.set(k, (count.get(k) || 0) + 1);
      });
      links.forEach(function (l) {
        var k = [l.from, l.to].sort().join("|"), n = count.get(k);
        if (n > 1) {
          var i = seen.get(k) || 0;
          seen.set(k, i + 1);
          l.curve = (i - (n - 1) / 2) * 24;
        } else l.curve = 0;
      });
    }

    /* ---------------- render ---------------- */
    function render() {
      if (sim) sim.stop();

      edgeSel = gLinks.selectAll("path").data(links, function (d) {
        return d.from + "|" + d.to + "|" + d.label;
      }).join("path")
        .attr("class", function (d) { return "edge e-" + d.kind; })
        .attr("marker-end", function (d) {
          return DIRECTIONAL[d.kind] ? "url(#plex-arrow-" + d.kind + ")" : null;
        });
      edgeSel.selectAll("title").remove();
      edgeSel.append("title").text(edgeDescription);

      elabelSel = gELabels.selectAll("text").data(links, function (d) {
        return d.from + "|" + d.to + "|" + d.label;
      }).join("text")
        .attr("class", "elabel")
        .text(function (d) { return EDGE_LABEL[d.kind] || d.label || ""; });

      nodeSel = gNodes.selectAll("g.node").data(nodes, function (d) { return d.id; })
        .join(
          function (enter) {
            var g = enter.append("g")
              .attr("class", "node")
              .attr("tabindex", 0)
              .attr("role", "button");
            g.append("circle").attr("class", "halo");
            g.append("circle").attr("class", "ring");
            g.append("circle").attr("class", "medallion");
            g.append("text").attr("class", "initial").attr("dy", "0.36em");
            g.append("circle").attr("class", "focus-ring");
            g.append("text").attr("class", "nlabel");
            g.append("text").attr("class", "nsub");
            g.append("title");
            return g;
          },
          function (update) { return update; },
          function (exit) { return exit.remove(); }
        );

      nodeSel
        .attr("aria-label", function (d) {
          return d.label + ", " + (TYPES[d.type] || TYPES.doc).label +
                 (d.sub ? ", " + d.sub : "") + ". Enter to select, E to expand.";
        })
        .classed("is-focus", function (d) { return d.id === focusId; });

      nodeSel.select(".halo").attr("r", function (d) { return nodeRadius(d) + 7; });
      nodeSel.select(".ring")
        .attr("r", function (d) { return nodeRadius(d) + 2.5; })
        .attr("stroke", function (d) { return typeColor(d.type); });
      nodeSel.select(".medallion")
        .attr("r", nodeRadius)
        .attr("fill", function (d) { return typeColor(d.type); });
      nodeSel.select(".initial")
        .attr("fill", function (d) { return letterInk(typeColor(d.type)); })
        .style("font-size", function (d) { return Math.round(nodeRadius(d) * 1.02) + "px"; })
        .text(function (d) { return initialOf(d.label); });
      nodeSel.select(".focus-ring").attr("r", function (d) { return nodeRadius(d) + 11; });
      nodeSel.select(".nlabel")
        .attr("y", function (d) { return nodeRadius(d) + 15; })
        .text(function (d) { return truncate(d.label, 28); });
      nodeSel.select(".nsub")
        .attr("y", function (d) { return nodeRadius(d) + 27; })
        .text(function (d) { return truncate(d.sub || "", 30); });
      nodeSel.select("title").text(function (d) { return d.path || d.sub || d.label; });

      nodeSel
        .on("click", function (ev, d) {
          if (ev.defaultPrevented) return;
          ev.stopPropagation();
          select(d.id);
        })
        .on("dblclick", function (ev, d) { ev.preventDefault(); ev.stopPropagation(); recenter(d.id); })
        .on("keydown", function (ev, d) {
          if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); select(d.id); }
          else if (ev.key === "e" || ev.key === "E") { ev.preventDefault(); recenter(d.id); }
          else if (ev.key === "Escape") { ev.preventDefault(); select(null); }
        })
        .on("contextmenu", function (ev, d) {
          if (!opts.onContextMenu) return;
          ev.preventDefault();
          select(d.id);
          opts.onContextMenu(ev, d);
        })
        .call(d3.drag()
          .on("start", function (ev, d) {
            if (!ev.active && sim) sim.alphaTarget(0.25).restart();
            d.fx = d.x; d.fy = d.y;
          })
          .on("drag", function (ev, d) { d.fx = ev.x; d.fy = ev.y; })
          .on("end", function (ev, d) {
            if (!ev.active && sim) sim.alphaTarget(0);
            d.fx = null; d.fy = null;
          }));

      sim = d3.forceSimulation(nodes)
        .force("link", d3.forceLink(links).id(function (d) { return d.id; })
          .distance(function (l) {
            return l.kind === "project" ? 150 : (l.kind === "has" ? 118 : 108);
          })
          .strength(0.32))
        .force("charge", d3.forceManyBody().strength(-560))
        .force("center", d3.forceCenter(W() / 2, H() / 2))
        .force("collide", d3.forceCollide().radius(function (d) { return nodeRadius(d) + 22; }))
        .force("x", d3.forceX(W() / 2).strength(0.05))
        .force("y", d3.forceY(H() / 2).strength(0.06))
        .on("tick", tick);

      /* Settle off-screen first: a graph that arrives composed reads as
         considered, one that flails into place reads as a demo. */
      sim.stop();
      for (var i = 0; i < 190; i++) sim.tick();
      tick();
      sim.alpha(0.14).restart();

      refreshDimming();
      buildLegend();
    }

    function tick() {
      if (!edgeSel) return;
      edgeSel.attr("d", function (d) {
        var sx = d.source.x, sy = d.source.y, tx = d.target.x, ty = d.target.y;
        var dx = tx - sx, dy = ty - sy;
        var dist = Math.hypot(dx, dy) || 1;
        var ux = dx / dist, uy = dy / dist;
        var rs = nodeRadius(d.source) + 3;
        var rt = nodeRadius(d.target) + (DIRECTIONAL[d.kind] ? 10 : 3);
        var x1 = sx + ux * rs, y1 = sy + uy * rs;
        var x2 = tx - ux * rt, y2 = ty - uy * rt;
        if (!d.curve) return "M" + x1 + "," + y1 + "L" + x2 + "," + y2;
        var mx = (x1 + x2) / 2 - uy * d.curve;
        var my = (y1 + y2) / 2 + ux * d.curve;
        return "M" + x1 + "," + y1 + "Q" + mx + "," + my + " " + x2 + "," + y2;
      });
      if (elabelSel) {
        elabelSel.attr("transform", function (d) {
          var mx = (d.source.x + d.target.x) / 2, my = (d.source.y + d.target.y) / 2;
          if (d.curve) {
            var dx = d.target.x - d.source.x, dy = d.target.y - d.source.y;
            var dist = Math.hypot(dx, dy) || 1;
            mx -= (dy / dist) * d.curve * 0.5;
            my += (dx / dist) * d.curve * 0.5;
          }
          return "translate(" + mx + "," + (my - 4) + ")";
        });
      }
      nodeSel.attr("transform", function (d) {
        positions.set(d.id, { x: d.x, y: d.y });
        return "translate(" + d.x + "," + d.y + ")";
      });
    }

    function edgeDescription(l) {
      var a = nodes.find(function (n) { return n.id === l.from; });
      var b = nodes.find(function (n) { return n.id === l.to; });
      if (!a || !b) return "";
      var verb = {
        project: " sits in ", has: " contains ", mentions: " mentions ",
        decided: " decided ", implements: " implements ", produced: " produced "
      }[l.kind] || (" \u2014 " + (l.label || "related") + " \u2014 ");
      return (l.kind === "project" ? b.label + " sits in " + a.label : a.label + verb + b.label);
    }

    /* ---------------- selection ---------------- */
    function refreshDimming() {
      if (!nodeSel) return;
      if (!selectedId) {
        nodeSel.classed("is-dim", false).classed("is-selected", false);
        edgeSel.classed("is-dim", false).classed("is-lit", false);
        elabelSel.classed("is-lit", false);
        return;
      }
      var nb = neighbors.get(selectedId) || new Set();
      var incident = function (d) { return d.from === selectedId || d.to === selectedId; };
      nodeSel
        .classed("is-selected", function (d) { return d.id === selectedId; })
        .classed("is-dim", function (d) { return d.id !== selectedId && !nb.has(d.id); });
      edgeSel
        .classed("is-lit", incident)
        .classed("is-dim", function (d) { return !incident(d); });

      /* Captions only pay for themselves when you can read them. Selecting
         a hub lights its whole star — 39 captions at once is worse than
         none, so past a legible handful they stay off and the dash
         patterns carry the relation instead. */
      var litCount = links.reduce(function (n, d) { return incident(d) ? n + 1 : n; }, 0);
      elabelSel.classed("is-lit", litCount <= EDGE_LABEL_CAP ? incident : false);
    }

    function select(id) {
      selectedId = id && nodes.some(function (n) { return n.id === id; }) ? id : null;
      refreshDimming();
      renderInspector();
      if (opts.onSelect) {
        opts.onSelect(selectedId ? nodes.find(function (n) { return n.id === selectedId; }) : null);
      }
    }

    svgEl.addEventListener("click", function () { select(null); });

    /* ---------------- inspector ---------------- */
    function renderInspector() {
      var d = selectedId ? nodes.find(function (n) { return n.id === selectedId; }) : null;
      if (!d) { inspector.classList.remove("is-open"); inspector.innerHTML = ""; return; }

      var color = typeColor(d.type);
      var kind = (TYPES[d.type] || TYPES.doc).label;
      var raw = bareId(d.id);
      var deg = degree(d.id);

      var btns = [];
      if (d.type === "doc" && actions.open) btns.push(["open", "Open", "primary"]);
      if (d.type === "doc" && actions.reveal) btns.push(["reveal", "Reveal", ""]);
      if (d.type === "doc" && actions.download) btns.push(["download", "Download", ""]);
      if (d.path && actions.copy) btns.push(["copy", "Copy path", ""]);
      btns.push(["center", d.id === focusId ? "Re-expand" : "Expand here", ""]);

      inspector.innerHTML =
        '<div class="insp-head">' +
          '<span class="insp-dot" style="color:' + esc(color) + '"></span>' +
          '<div style="min-width:0">' +
            '<div class="insp-title">' + esc(d.label) + '</div>' +
            '<div class="insp-kind">' + esc(kind) + (d.sub ? " \u00B7 " + esc(d.sub) : "") + '</div>' +
          '</div>' +
          '<button type="button" class="insp-close" data-act="close" aria-label="Clear selection">\u00D7</button>' +
        '</div>' +
        '<div class="insp-body">' +
          (d.path ? '<div class="insp-path">' + esc(d.path) + '</div>' : "") +
          '<div class="insp-meta">' + deg + " direct connection" + (deg === 1 ? "" : "s") +
            " in this view</div>" +
          '<div class="insp-actions">' +
            btns.map(function (b) {
              return '<button type="button" class="insp-btn ' + b[2] + '" data-act="' + b[0] + '">' +
                     esc(b[1]) + "</button>";
            }).join("") +
          "</div>" +
        "</div>";

      inspector.classList.add("is-open");
      inspector.querySelectorAll("[data-act]").forEach(function (b) {
        b.addEventListener("click", function (ev) {
          ev.stopPropagation();
          var a = b.getAttribute("data-act");
          if (a === "close") return select(null);
          if (a === "center") return recenter(d.id);
          if (a === "copy" && actions.copy) return actions.copy(d.path, d);
          if (actions[a]) actions[a](raw, d);
        });
      });
    }

    /* ---------------- legend ---------------- */
    var legendBuilt = false;
    function buildLegend() {
      if (legendBuilt) return;
      legendBuilt = true;
      var body = legend.querySelector(".legend-body");
      var rel = EDGE_ORDER.map(function (k) {
        return '<li>' + edgeSample(k) + "<span>" + esc(EDGE_LABEL[k]) + "</span></li>";
      }).join("");
      var cat = TYPE_ORDER.map(function (t) {
        return '<li><span class="legend-swatch" style="color:' + esc(typeColor(t)) + '"></span>' +
               "<span>" + esc(TYPES[t].label) + "</span></li>";
      }).join("");
      body.innerHTML =
        '<h3 class="legend-h">Relationships</h3><ul class="legend-list">' + rel + "</ul>" +
        '<h3 class="legend-h">Node types</h3><ul class="legend-list">' + cat + "</ul>";
    }

    function edgeSample(kind) {
      var w = 40;
      var marker = DIRECTIONAL[kind]
        ? '<path class="m-' + kind + '" d="M' + (w - 8) + ',3 L' + w + ',7 L' + (w - 8) + ',11 Z"></path>' : "";
      return '<svg width="' + w + '" height="14" aria-hidden="true" style="flex:0 0 ' + w + 'px">' +
        '<line class="edge e-' + kind + ' is-lit" x1="1" y1="7" x2="' + (w - (marker ? 9 : 1)) + '" y2="7"></line>' +
        marker + "</svg>";
    }

    /* ---------------- viewport ---------------- */
    function fit(duration) {
      if (!nodes.length) return;
      var pad = 64;
      var xs = nodes.map(function (d) { return d.x; });
      var ys = nodes.map(function (d) { return d.y; });
      var minX = Math.min.apply(null, xs) - pad, maxX = Math.max.apply(null, xs) + pad;
      var minY = Math.min.apply(null, ys) - pad, maxY = Math.max.apply(null, ys) + pad;
      var w = W(), h = H();
      var k = Math.min(1.6, 0.95 / Math.max((maxX - minX) / w, (maxY - minY) / h));
      var t = d3.zoomIdentity
        .translate(w / 2 - k * (minX + maxX) / 2, h / 2 - k * (minY + maxY) / 2)
        .scale(k);
      (duration ? svg.transition().duration(duration) : svg).call(zoomBehavior.transform, t);
    }

    function resize() {
      if (!sim) return;
      sim.force("center", d3.forceCenter(W() / 2, H() / 2));
      sim.force("x", d3.forceX(W() / 2).strength(0.05));
      sim.force("y", d3.forceY(H() / 2).strength(0.06));
      sim.alpha(0.1).restart();
      fit(300);
    }

    var ro = null;
    try {
      ro = new ResizeObserver(function () { if (!destroyed) resize(); });
      ro.observe(container);
    } catch (e) { /* older browser: the window listener below still covers it */ }
    var onWinResize = function () { if (!destroyed) resize(); };
    window.addEventListener("resize", onWinResize);

    tools.addEventListener("click", function (ev) {
      var b = ev.target.closest("[data-act]");
      if (!b) return;
      var a = b.getAttribute("data-act");
      if (a === "in") svg.transition().duration(200).call(zoomBehavior.scaleBy, 1.45);
      else if (a === "out") svg.transition().duration(200).call(zoomBehavior.scaleBy, 1 / 1.45);
      else if (a === "fit") fit(450);
      else if (a === "home") home();
    });

    /* ---------------- navigation ---------------- */
    function setLoading(on) { loading.style.display = on ? "" : "none"; }
    setLoading(true);

    function showEmpty(msg) {
      var e = container.querySelector(".qi-plex-empty");
      if (!msg) { if (e) e.remove(); return; }
      if (!e) {
        e = document.createElement("div");
        e.className = "qi-plex-empty";
        container.appendChild(e);
      }
      e.textContent = msg;
    }

    function recenter(id, opt) {
      opt = opt || {};
      var seq = ++reqSeq;
      setLoading(true);
      return Promise.resolve(opts.fetchGraph(id)).then(function (d) {
        if (destroyed || seq !== reqSeq) return d;
        setLoading(false);
        if (!d || !d.nodes || !d.nodes.length) {
          showEmpty("Nothing is linked to this node yet.");
          return d;
        }
        showEmpty(null);

        focusId = d.focus || id;
        if (!opt.silent) pushTrail(id, d);
        ingest(d);
        render();
        select(focusId);
        setTimeout(function () { if (!destroyed) fit(420); }, 40);
        if (opts.onRecenter) opts.onRecenter(focusId, d);
        return d;
      }).catch(function (err) {
        if (destroyed || seq !== reqSeq) return;
        setLoading(false);
        showEmpty("Could not load this part of the Plex.");
        if (window.console) console.error("QIPlex.recenter", err);
      });
    }

    function pushTrail(id, d) {
      var node = (d.nodes || []).find(function (n) { return n.id === (d.focus || id); });
      var label = node ? node.label : id;
      var at = trail.findIndex(function (t) { return t.id === id; });
      if (at >= 0) trail = trail.slice(0, at + 1);
      else trail.push({ id: id, label: label, type: node ? node.type : "" });
      if (trail.length > 8) trail = trail.slice(trail.length - 8);
      if (opts.onTrail) opts.onTrail(trail.slice());
    }

    function home() { trail = []; return recenter(opts.rootId || "root:qi"); }

    function destroy() {
      destroyed = true;
      if (sim) sim.stop();
      if (ro) try { ro.disconnect(); } catch (e) {}
      window.removeEventListener("resize", onWinResize);
      container.innerHTML = "";
      container.classList.remove("qi-plex");
    }

    return {
      recenter: recenter,
      select: select,
      home: home,
      fit: fit,
      resize: resize,
      destroy: destroy,
      trail: function () { return trail.slice(); },
      focusId: function () { return focusId; }
    };
  }

  return { create: create, TYPES: TYPES, EDGE_LABEL: EDGE_LABEL };
})();
