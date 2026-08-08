/* AI-GENERATED BEGIN (Claude Code, 2026-06-21)
   Shared category-colour store for the BU Hive Information views. One source of
   truth (window.BUCAT) read by the Map (bu-graph.js) and the alternate lenses
   (bu-info-views.js), so the in-legend colour picker recolours everything and the
   choice persists per device. Brighter defaults than the old near-black/gray set
   so every category is legible on the dark theme. */
(function () {
  "use strict";
  var KEY = "bu-hive-catcolors";
  // Distinct + legible on both dark and light themes. BU red stays for the core.
  var DEFAULTS = {
    hub: "#CC0000",       // BU red — core
    layer: "#E8552D",     // vermilion
    page: "#F0883E",      // orange
    project: "#E64980",   // rose
    data: "#4DABF7",      // sky blue
    config: "#9775FA",    // violet
    security: "#FAB005",  // amber (was near-black)
    hook: "#20C997",      // teal (was espresso)
    custom: "#E599F7"     // orchid — user-added nodes/files
  };
  var colors = {};
  for (var k in DEFAULTS) colors[k] = DEFAULTS[k];
  try {
    var saved = JSON.parse(localStorage.getItem(KEY) || "{}");
    for (var c in saved) if (saved[c]) colors[c] = saved[c];
  } catch (e) { /* ignore */ }

  var listeners = [];
  function save() { try { localStorage.setItem(KEY, JSON.stringify(colors)); } catch (e) {} }
  function fire() { listeners.forEach(function (cb) { try { cb(); } catch (e) {} }); }

  window.BUCAT = {
    DEFAULTS: DEFAULTS,
    get: function (cat) { return colors[cat] || "#888"; },
    all: function () { return colors; },
    set: function (cat, hex) { if (hex) { colors[cat] = hex; save(); fire(); } },
    reset: function () { var d = {}; for (var x in DEFAULTS) d[x] = DEFAULTS[x]; colors = d; save(); fire(); },
    onChange: function (cb) { if (typeof cb === "function") listeners.push(cb); }
  };
})();
/* AI-GENERATED END */
