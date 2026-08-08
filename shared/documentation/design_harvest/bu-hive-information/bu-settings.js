/* AI-GENERATED BEGIN (Claude Code, 2026-06-22)
   BU Hive — universal client settings store. One source of truth (window.BUSET)
   for per-device customisation that needs no server restart: the universal accent
   scheme (applied app-wide) and the BU Hive Information graph appearance (node
   style, size, labels, physics). Persisted in localStorage; listeners re-apply on
   change so the Config page edits everything live. Mirrors the bu-colors.js store. */
(function () {
  "use strict";
  var KEY = "bu-hive-settings";
  var DEFAULTS = {
    accent: "#CC0000",     // universal UI accent (overrides --bu-red app-wide)
    nodeStyle: "outline",  // "outline" (transparent fill, coloured border) | "filled"
    nodeScale: 1,          // node radius multiplier (0.6–1.8)
    nodeStroke: 1.5,       // sphere border thickness, px (0.75–3) — thin & modern by default
    edgeWidth: 1.4,        // connecting-line thickness, px (0.5–5)
    edgeColor: "",         // connecting-line colour ("" = theme default --hv-line)
    bgColor: "",           // canvas background colour ("" = theme default gradient)
    labelSize: 11,         // node label font size, px (8–18)
    showLabels: true,      // draw node text labels on the Map / Mind Map
    physics: true          // animate the force layout (off = static, draggable)
  };
  var s = {};
  for (var k in DEFAULTS) s[k] = DEFAULTS[k];
  try {
    var saved = JSON.parse(localStorage.getItem(KEY) || "{}");
    for (var c in saved) if (c in DEFAULTS && saved[c] != null) s[c] = saved[c];
  } catch (e) { /* ignore */ }

  var listeners = [];
  function save() { try { localStorage.setItem(KEY, JSON.stringify(s)); } catch (e) {} }
  function fire() { listeners.forEach(function (cb) { try { cb(); } catch (e) {} }); }

  // Lighten a #rrggbb toward white by amt (0–1) — used to derive the "bright" accent.
  function lighten(hex, amt) {
    var m = /^#?([0-9a-f]{6})$/i.exec(hex || ""); if (!m) return hex;
    var n = parseInt(m[1], 16), r = (n >> 16) & 255, g = (n >> 8) & 255, b = n & 255;
    r = Math.round(r + (255 - r) * amt); g = Math.round(g + (255 - g) * amt); b = Math.round(b + (255 - b) * amt);
    return "#" + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1);
  }
  // Push the accent into the global CSS variables every page reads.
  function applyAccent() {
    var root = document.documentElement;
    root.style.setProperty("--bu-red", s.accent);
    root.style.setProperty("--bu-red-bright", lighten(s.accent, 0.2));
  }

  // Push the graph appearance prefs into CSS variables the Information views
  // read (border thickness, line thickness/colour, label size, canvas bg). An
  // empty colour removes the override so the theme default cascades back in.
  function gnum(v, d) { var n = parseFloat(v); return isFinite(n) ? n : d; }
  function applyGraphVars() {
    var root = document.documentElement;
    root.style.setProperty("--gm-node-stroke", gnum(s.nodeStroke, 1.5) + "px");
    root.style.setProperty("--gm-edge-width", gnum(s.edgeWidth, 1.4) + "px");
    root.style.setProperty("--gm-label-size", gnum(s.labelSize, 11) + "px");
    if (s.edgeColor) root.style.setProperty("--gm-edge-color", s.edgeColor);
    else root.style.removeProperty("--gm-edge-color");
    if (s.bgColor) root.style.setProperty("--gm-bg", s.bgColor);
    else root.style.removeProperty("--gm-bg");
  }
  function applyAll() { applyAccent(); applyGraphVars(); }

  window.BUSET = {
    DEFAULTS: DEFAULTS,
    get: function (k) { return s[k]; },
    all: function () { var o = {}; for (var x in s) o[x] = s[x]; return o; },
    set: function (k, v) { if (k in DEFAULTS) { s[k] = v; save(); applyAll(); fire(); } },
    reset: function () { for (var x in DEFAULTS) s[x] = DEFAULTS[x]; save(); applyAll(); fire(); },
    onChange: function (cb) { if (typeof cb === "function") listeners.push(cb); },
    applyAccent: applyAccent
  };
  applyAll();  // apply saved accent + graph appearance before first paint
})();
/* AI-GENERATED END */
