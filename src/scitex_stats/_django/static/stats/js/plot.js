// SciTeX Statistics: Plot view in the Results pane, plus "Open in FigRecipe".
// Classic script after stx-mount.js; app.js calls stxStatsPlot.draw(payload).

(function () {
  "use strict";

  var CATALOG = {};
  document
    .querySelectorAll('script[type="application/json"][id^="scitex-i18n-catalog-"]')
    .forEach(function (el) {
      try {
        Object.assign(CATALOG, (JSON.parse(el.textContent || "{}") || {}).catalog || {});
      } catch (e) { /* no catalog: English */ }
    });
  function _(msgid) {
    var t = CATALOG[msgid];
    return typeof t === "string" && t ? t : Array.isArray(t) ? t[0] : msgid;
  }

  var $ = function (id) { return document.getElementById(id); };
  var lastSpec = null;
  var owner = null;
  var downloadOwner = null;
  var figrecipe = { available: false };
  var seq = 0;

  function status(text) { $("statsPlotStatus").textContent = text || ""; }

  function csrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    if (meta && meta.content) return meta.content;
    var m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : "";
  }

  function syncFigrecipe() {
    $("statsOpenFigrecipe").hidden = !(figrecipe.available && lastSpec);
  }

  function current() {
    var app = window.stxStatsApp;
    return !!(app && app.requestCurrent && app.requestCurrent(owner));
  }

  function clearDownloads() {
    downloadOwner = null;
    ["statsPlotSvg", "statsPlotPng"].forEach(function (id) {
      var link = $(id);
      if (link) { link.hidden = true; link.removeAttribute("href"); }
    });
  }

  function guardDownload(event, link) {
    if (event.type === "keydown" && event.key !== "Enter") return;
    var rendered = downloadOwner;
    var app = window.stxStatsApp;
    var valid = false;
    try {
      valid = !!(rendered && owner === rendered.request && seq === rendered.sequence &&
        app && typeof app.requestCurrent === "function" && app.requestCurrent(rendered.request) === true &&
        downloadOwner === rendered && !link.hidden && link.href && link.href === rendered.hrefs[link.id]);
    } catch (e) { /* uncertain ownership cannot permit a native link action */ }
    if (!valid) {
      event.preventDefault();
      link.hidden = true;
      link.removeAttribute("href");
      clearDownloads();
    }
  }

  function invalidate() {
    seq += 1;
    owner = null;
    lastSpec = null;
    $("statsPlot").hidden = true;
    $("statsPlotImg").hidden = true;
    $("statsPlotImg").removeAttribute("src");
    clearDownloads();
    $("statsOpenFigrecipe").disabled = false;
    syncFigrecipe();
    status("");
  }

  async function draw(payload, request) {
    var app = window.stxStatsApp;
    if (!app || !app.beginRequest || !app.requestCurrent) return;
    owner = request || app.beginRequest("plot");
    if (!current()) return;
    var mine = ++seq;
    var plotOwner = owner;
    clearDownloads();
    var box = $("statsPlot");
    box.hidden = false;
    lastSpec = null;
    syncFigrecipe();
    status(_("Drawing plot…"));
    var body = Object.assign({}, payload);
    if (body.groups && body.groups.length >= 3) body.posthoc = "tukey";
    try {
      var res = await fetch(STX_MOUNT + "/api/plot", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      var data = await res.json();
      if (mine !== seq || !current()) return;
      if (!res.ok) throw new Error(data.error || "HTTP " + res.status);
      var img = $("statsPlotImg");
      img.src = data.svg;
      img.hidden = false;
      $("statsPlotSvg").href = data.svg;
      $("statsPlotPng").href = data.png;
      $("statsPlotSvg").hidden = false;
      $("statsPlotPng").hidden = false;
      downloadOwner = { request: plotOwner, sequence: mine, hrefs: {
        statsPlotSvg: $("statsPlotSvg").href,
        statsPlotPng: $("statsPlotPng").href,
      } };
      lastSpec = data.plot_spec;
      figrecipe = data.figrecipe || { available: false };
      syncFigrecipe();
      status("");
    } catch (e) {
      if (mine !== seq || !current()) return;
      $("statsPlotImg").hidden = true;
      status(_("Could not draw the plot."));
    }
  }

  async function openInFigrecipe() {
    if (!current() || !lastSpec || !figrecipe.available) return;
    var plotOwner = owner;
    function importCurrent() {
      return owner === plotOwner && window.stxStatsApp.requestCurrent(plotOwner) && window.stxStatsApp.requestCurrent(request);
    }
    var request = window.stxStatsApp.beginRequest("figrecipe");
    var btn = $("statsOpenFigrecipe");
    btn.disabled = true;
    status(_("Creating the figure in FigRecipe…"));
    try {
      var res = await fetch(figrecipe.import_url, {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken() },
        body: JSON.stringify({ spec: lastSpec }),
      });
      var data = {};
      try { data = await res.json(); } catch (e) { /* non-JSON */ }
      if (!importCurrent()) return;
      if (!res.ok || !data.recipe_path) throw new Error(data.error || "HTTP " + res.status);
      window.location.href = figrecipe.open_url + "?recipe=" + encodeURIComponent(data.recipe_path);
    } catch (e) {
      if (importCurrent()) status(_("Could not open the plot in FigRecipe."));
    } finally {
      if (window.stxStatsApp.requestLatest(request)) btn.disabled = false;
    }
  }

  function init() {
    document.addEventListener("stats:analysis-change", invalidate);
    ["statsPlotSvg", "statsPlotPng"].forEach(function (id) {
      var link = $(id);
      ["click", "auxclick", "contextmenu", "pointerdown", "mousedown", "keydown", "focus"].forEach(function (type) {
        link.addEventListener(type, function (event) { guardDownload(event, link); }, true);
      });
    });
    $("statsOpenFigrecipe").addEventListener("click", openInFigrecipe);
    fetch(STX_MOUNT + "/api/integrations")
      .then(function (r) { return r.ok ? r.json() : {}; })
      .then(function (d) { figrecipe = (d && d.figrecipe) || { available: false }; syncFigrecipe(); })
      .catch(function () { /* stays hidden */ });
  }

  window.stxStatsPlot = { draw: draw, invalidate: invalidate,
    spec: function () { return current() ? lastSpec : null; },
    owner: function () { return current() ? owner : null; } };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
