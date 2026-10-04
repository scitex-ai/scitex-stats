// SciTeX Statistics: Data | Test | Results over the scitex-stats API.
// Classic script sharing STX_MOUNT with stx-mount.js (loaded first).

(function () {
  "use strict";

  // Django-compatible gettext over the {% scitex_js_catalog %} json_script.
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
  function fmt(template, args) {
    var i = 0;
    return template.replace(/%s/g, function () { return String(args[i++]); });
  }

  // ---- APA symbols ------------------------------------------------------
  // Segments {text, kind} come from the package's result["apa"]; kind is
  // text | sym (italic Latin) | greek (upright) | sub | sup. DOM only, no innerHTML.
  var SEG_TAGS = { sym: "i", greek: "span", sub: "sub", sup: "sup" };

  function segNode(seg) {
    var tag = SEG_TAGS[seg.kind];
    if (!tag) return document.createTextNode(String(seg.text));
    var el = document.createElement(tag);
    if (seg.kind === "sym") el.className = "stx-sym";
    if (seg.kind === "greek") el.className = "stx-sym stx-sym--greek";
    el.textContent = String(seg.text);
    return el;
  }

  function setSegments(el, segs) {
    el.textContent = "";
    segs.forEach(function (s) { el.appendChild(segNode(s)); });
  }

  function T(text) { return { text: text, kind: "text" }; }
  function S(text) { return { text: text, kind: "sym" }; }

  // Italicize the first standalone `sym` in an (already translated) string,
  // so "p-value" and "p値" both keep an italic p.
  function withSymbol(text, sym) {
    text = String(text);
    if (!sym) return [T(text)];
    var re = new RegExp("(^|[^A-Za-z])" + sym + "(?![A-Za-z])");
    var m = re.exec(text);
    if (!m) return [T(text)];
    var at = m.index + m[1].length;
    return [T(text.slice(0, at)), S(sym), T(text.slice(at + sym.length))].filter(function (s) { return s.text; });
  }

  // Library segments carry English label text; translate each text piece.
  function translated(segs) {
    return (segs || []).map(function (s) { return s.kind === "text" ? T(_(s.text)) : s; });
  }

  // kind: how the Data groups map onto run_test arguments; sym: italic in the label.
  var TESTS = [
    { cat: "Two independent groups", name: "ttest_ind", label: "Student's t-test", kind: "two", sym: "t" },
    { cat: "Two independent groups", name: "ttest_welch", label: "Welch's t-test", kind: "two", sym: "t" },
    { cat: "Two independent groups", name: "mannwhitneyu", label: "Mann–Whitney U", kind: "two", sym: "U" },
    { cat: "Two independent groups", name: "brunner_munzel", label: "Brunner–Munzel", kind: "two" },
    { cat: "Two independent groups", name: "ks_2samp", label: "Kolmogorov–Smirnov (2-sample)", kind: "two" },
    { cat: "Paired groups", name: "ttest_rel", label: "Paired t-test", kind: "paired", sym: "t" },
    { cat: "Paired groups", name: "wilcoxon", label: "Wilcoxon signed-rank", kind: "paired" },
    { cat: "Three or more groups", name: "anova", label: "One-way ANOVA", kind: "groups" },
    { cat: "Three or more groups", name: "kruskal", label: "Kruskal–Wallis", kind: "groups" },
    { cat: "Three or more groups", name: "friedman", label: "Friedman (repeated measures)", kind: "groups" },
    { cat: "Correlation", name: "pearson", label: "Pearson r", kind: "two", sym: "r" },
    { cat: "Correlation", name: "spearman", label: "Spearman ρ", kind: "two" },
    { cat: "Correlation", name: "kendall", label: "Kendall τ", kind: "two" },
    { cat: "One sample", name: "ttest_1samp", label: "One-sample t-test", kind: "one", sym: "t" },
    { cat: "One sample", name: "shapiro", label: "Shapiro–Wilk normality", kind: "one" },
    { cat: "One sample", name: "ks_1samp", label: "Kolmogorov–Smirnov (1-sample)", kind: "one" },
    { cat: "Contingency table", name: "chi2", label: "Chi-square test", kind: "table" },
    { cat: "Contingency table", name: "fisher", label: "Fisher's exact test", kind: "table" },
  ];
  // Literal msgids so extraction finds them.
  var CATEGORY_LABELS = {
    "Two independent groups": _("Two independent groups"),
    "Paired groups": _("Paired groups"),
    "Three or more groups": _("Three or more groups"),
    "Correlation": _("Correlation"),
    "One sample": _("One sample"),
    "Contingency table": _("Contingency table"),
  };
  var SAMPLE = [
    [5.1, 4.9, 5.6, 5.8, 6.0, 5.4, 5.2, 5.7],
    [6.3, 6.8, 6.1, 7.0, 6.6, 6.9, 6.4, 7.2],
  ];

  var $ = function (id) { return document.getElementById(id); };

  function parseNumbers(text) {
    return String(text || "")
      .split(/[\s,;]+/)
      .filter(Boolean)
      .map(Number)
      .filter(function (n) { return Number.isFinite(n); });
  }

  function csrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute("content") : "";
  }

  async function api(path, payload) {
    var options = payload === undefined
      ? { method: "GET" }
      : {
          method: "POST",
          // The app is CSRF-protected on writes: the page carries the token and
          // every POST sends it back, so a cross-site page cannot save into a
          // project on the user's behalf.
          headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken() },
          body: JSON.stringify(payload),
        };
    var res = await fetch(STX_MOUNT + path, options);
    var body = {};
    try { body = await res.json(); } catch (e) { /* non-JSON */ }
    return { ok: res.ok, status: res.status, body: body };
  }

  // ---- Data -------------------------------------------------------------
  // Import alignment is a property of the SOURCE rows, not equal array lengths.
  // No omission policy is chosen here: any discarded data cell is uncertain.
  var rowIntegrity = { status: "manual", reason: "new-manual-input", source: "manual" };
  var importedSnapshot = null;
  var ROW_DEPENDENT = { ttest_rel: 1, wilcoxon: 1, pearson: 1, spearman: 1, kendall: 1, friedman: 1 };

  function groupSnapshot() {
    return JSON.stringify(Array.prototype.map.call(
      $("statsGroups").querySelectorAll(".stats-group__input"),
      function (area) { return area.value; }
    ));
  }

  function invalidateImportedRows() {
    if (rowIntegrity.source === "csv") {
      rowIntegrity = { status: "uncertain", reason: "edited-or-restored-data", source: "csv" };
      importedSnapshot = null;
    }
    document.dispatchEvent(new CustomEvent("stats:data-change"));
  }

  function currentRowIntegrity() {
    // Also catches form restoration/programmatic edits which emit no input event.
    if (importedSnapshot !== null && importedSnapshot !== groupSnapshot()) invalidateImportedRows();
    return { status: rowIntegrity.status, reason: rowIntegrity.reason, source: rowIntegrity.source };
  }

  function rowIntegrityError(testName, design) {
    var integrity = currentRowIntegrity();
    if ((ROW_DEPENDENT[testName] || design === "within") && integrity.status === "uncertain") {
      return _("This analysis needs matching source rows. Imported data contain missing or invalid cells, or have changed. Reload a complete CSV or TSV file with one observation per row.");
    }
    return "";
  }

  function csvRowIntegrity(text, sep, cols) {
    var lines = String(text).split(/\r?\n/);
    if (lines[lines.length - 1] === "") lines.pop(); // ordinary terminal newline
    var rows = lines.map(function (line) { return line.split(sep); });
    // Recognize only an unambiguous label row; numeric-looking/missing markers
    // never grant alignment. Unsupported header syntax remains uncertain.
    var header = rows.length > 1 && rows[0].length === cols && rows[0].every(function (cell) {
      cell = String(cell).trim();
      return /^[A-Za-z_][A-Za-z0-9_ .-]*$/.test(cell) && !/^(nan|inf|infinity|null|none|na)$/i.test(cell);
    });
    if (header) rows.shift();
    var aligned = rows.length > 0 && rows.every(function (row) {
      return row.length === cols && row.every(function (cell) {
        cell = String(cell).trim();
        return cell !== "" && Number.isFinite(Number(cell));
      });
    });
    return {
      status: aligned ? "aligned" : "uncertain",
      reason: aligned ? "complete-numeric-source-rows" : "missing-or-invalid-source-rows",
      source: "csv",
    };
  }

  function groupName(i) { return fmt(_("Group %s"), [i + 1]); }

  function addGroup(values) {
    var wrap = $("statsGroups");
    var i = wrap.children.length;
    var row = document.createElement("div");
    row.className = "stats-group";
    var label = document.createElement("label");
    label.className = "stats-group__label";
    var name = document.createElement("span");
    name.textContent = groupName(i);
    var count = document.createElement("span");
    count.className = "stats-group__count";
    var area = document.createElement("textarea");
    area.rows = 3;
    area.className = "stats-group__input";
    area.placeholder = "1.2 3.4 5.6";
    area.value = values ? values.join(" ") : "";
    var remove = document.createElement("button");
    remove.type = "button";
    remove.className = "stats-btn stats-btn--ghost stats-group__remove";
    remove.setAttribute("aria-label", _("Remove group"));
    remove.textContent = "×";
    remove.addEventListener("click", function () {
      invalidateImportedRows();
      row.remove();
      renumber();
    });
    function updateCount() {
      setSegments(count, withSymbol(fmt(_("n = %s"), [parseNumbers(area.value).length]), "n"));
    }
    area.addEventListener("input", function () {
      invalidateImportedRows();
      updateCount();
    });
    label.append(name, count);
    row.append(label, remove, area);
    wrap.appendChild(row);
    updateCount();
  }

  function renumber() {
    Array.prototype.forEach.call($("statsGroups").children, function (row, i) {
      row.querySelector(".stats-group__label span").textContent = groupName(i);
    });
  }

  function readGroups() {
    return Array.prototype.map.call(
      $("statsGroups").querySelectorAll(".stats-group__input"),
      function (area) { return parseNumbers(area.value); }
    );
  }

  function setGroups(groups, integrity) {
    $("statsGroups").innerHTML = "";
    groups.forEach(function (g) { addGroup(g); });
    if (groups.length < 2) addGroup();
    rowIntegrity = integrity || { status: "manual", reason: "new-manual-input", source: "manual" };
    importedSnapshot = integrity ? groupSnapshot() : null;
    document.dispatchEvent(new CustomEvent("stats:data-change"));
  }

  // True when the user has typed or loaded something the sample would replace.
  function hasUserData() {
    return Array.prototype.some.call(
      $("statsGroups").querySelectorAll(".stats-group__input"),
      function (area) { return area.value.trim() !== ""; }
    );
  }

  function loadCsvText(text, name) {
    var lines = String(text).split(/\r?\n/).filter(function (l) { return l.trim(); });
    var sep = (name || "").toLowerCase().endsWith(".tsv") || (lines[0] || "").indexOf("\t") >= 0 ? "\t" : ",";
    var rows = lines.map(function (l) { return l.split(sep); });
    var cols = rows.reduce(function (m, r) { return Math.max(m, r.length); }, 0);
    var groups = [];
    for (var c = 0; c < cols; c++) {
      var col = rows
        .map(function (r) {
          var cell = r[c] === undefined ? "" : String(r[c]).trim();
          // A missing observation is not zero. Keep explicit "0" values,
          // while matching the number boxes' existing empty-value handling.
          return cell === "" ? NaN : Number(cell);
        })
        .filter(function (n) { return Number.isFinite(n); });
      if (col.length) groups.push(col);
    }
    if (groups.length) setGroups(groups, csvRowIntegrity(text, sep, cols));
    else showError(_("No numeric columns found in this file."));
  }

  function loadCsv(file) {
    var reader = new FileReader();
    reader.onload = function () { loadCsvText(reader.result, file.name); };
    reader.readAsText(file);
  }

  // ---- Project-default mode --------------------------------------------
  // The MODE IS THE URL, so the server can enforce it: project mode is
  // `?project=<id>` (server-resolved, and the only state in which persistence
  // is allowed), Quick analysis is the same page WITHOUT a project — the
  // stateless mode, where every write is refused server-side as well as hidden
  // here. Nothing about the mode depends on client-only state the server cannot
  // see.
  function projectId() {
    var root = document.querySelector("[data-stats-project]");
    var id = root ? root.getAttribute("data-stats-project") : "";
    return id && id !== "None" ? id : "";
  }

  function currentMode() {
    return projectId() ? "project" : "quick";
  }

  function applyMode() {
    var mode = currentMode();
    var hasProject = !!projectId();
    var app = document.querySelector("[data-stats-app]");
    if (app) app.setAttribute("data-stats-mode", mode);
    var panel = $("statsProjectFiles");
    if (panel) panel.hidden = !hasProject;
    var manual = $("statsManualData");
    if (manual) manual.hidden = hasProject;
    var saves = $("statsSaveRow");
    if (saves) saves.hidden = !hasProject;
    var plotSave = $("statsSavePlot");
    if (plotSave) plotSave.hidden = !hasProject;
    var toggle = $("statsModeToggle");
    if (toggle) toggle.hidden = !hasProject;
  }

  function setSaveStatus(message) {
    var line = $("statsSaveStatus");
    if (line) line.textContent = message || "";
  }

  async function importProjectFile(name) {
    var res = await api("/api/project-import?project=" + encodeURIComponent(projectId()) + "&name=" + encodeURIComponent(name));
    if (!res.ok) { showError(_("That project file is not available.")); return; }
    loadCsvText(res.body.text, res.body.name);
    setSaveStatus(fmt(_("Imported %s"), [res.body.name]));
  }

  function currentConfig() {
    var test = selectedTest();
    return {
      project: projectId(),
      test: test ? test.name : null,
      design: $("statsDesign").value,
      scale: $("statsScale").value,
      alternative: $("statsAlt").value,
      popmean: $("statsPopmean") ? Number($("statsPopmean").value) : null,
      group_sizes: readGroups().map(function (g) { return g.length; }),
      // Metadata only; no persisted values or restore proof is claimed.
      row_integrity: currentRowIntegrity(),
    };
  }

  // Responses belong to the exact inputs that dispatched them, and to the
  // latest request for their output. This is page-local ownership, not stored
  // source-row proof. Raw values catch silent edits; events also catch ABA
  // imports/options even when the visible values return to their old state.
  var analysisGeneration = 0;
  var analysisKey = null;
  var requestSequences = Object.create(null);
  var resultOwner = null;

  function clearResult() {
    resultOwner = null;
    lastPlain = "";
    lastApaHtml = "";
    ["statsJson", "statsFormatted", "statsResultTitle", "statsResultRows", "statsDescHead", "statsDescRows"].forEach(function (id) {
      $(id).textContent = "";
    });
    $("statsResult").hidden = true;
    $("statsCopy").hidden = true;
    $("statsDescTable").hidden = true;
    $("statsEmpty").hidden = $("statsSummary") && !$("statsSummary").hidden;
    showCopyState("idle");
  }

  function invalidateAnalysis() {
    analysisGeneration += 1;
    analysisKey = null;
    clearResult();
    ["statsRunAllOut", "statsCorrOut", "statsPhOut"].forEach(function (id) { $(id).textContent = ""; });
    $("statsRunAllOut").hidden = true;
    showError("");
    setSaveStatus("");
    document.dispatchEvent(new CustomEvent("stats:analysis-change"));
  }

  function currentAnalysisKey() {
    var integrity = currentRowIntegrity();
    var checked = document.querySelector('input[name="statsTest"]:checked');
    var key = JSON.stringify({
      groups: groupSnapshot(), project: projectId(), test: checked ? checked.value : null,
      group_names: Array.prototype.map.call($("statsGroups").querySelectorAll(".stats-group__label span"), function (label) { return label.textContent; }),
      options: ["statsDesign", "statsScale", "statsAlt", "statsPopmean", "statsCorrP", "statsCorrMethod", "statsPhMethod"].map(function (id) {
        return $(id) ? $(id).value : null;
      }),
      row_integrity: integrity,
    });
    if (analysisKey !== null && analysisKey !== key) invalidateAnalysis();
    analysisKey = key;
    return key;
  }

  function beginRequest(lane) {
    var key = currentAnalysisKey();
    requestSequences[lane] = (requestSequences[lane] || 0) + 1;
    return { generation: analysisGeneration, key: key, lane: lane, sequence: requestSequences[lane] };
  }

  function requestLatest(owner) {
    return !!owner && requestSequences[owner.lane] === owner.sequence;
  }

  function requestCurrent(owner) {
    var key = currentAnalysisKey();
    return requestLatest(owner) && owner.generation === analysisGeneration && owner.key === key;
  }

  function lastResult() {
    if (!requestCurrent(resultOwner)) return null;
    var pre = $("statsJson");
    if (!pre || !pre.textContent.trim()) return null;
    try { return JSON.parse(pre.textContent); } catch (e) { return null; }
  }

  async function saveArtifact(kind, name, payload, payloadBase64, owner) {
    if (owner && !requestCurrent(owner)) return;
    if (!projectId()) { setSaveStatus(_("No project is active.")); return; }
    var request = beginRequest("save");
    var body = { project: projectId(), kind: kind, name: name, payload: payload };
    if (payloadBase64) body.payload_base64 = payloadBase64;
    // State the project in the URL as well as the body: the server binds the
    // write to the project the REQUEST resolves, so the request must be the
    // project's own URL rather than relying on ambient stored state.
    try {
      var res = await api("/api/project-save?project=" + encodeURIComponent(projectId()), body);
      if (!requestCurrent(request) || (owner && !requestCurrent(owner))) return;
      setSaveStatus(res.ok ? fmt(_("Saved %s to the project"), [res.body.path || name]) : _("Save failed."));
    } catch (e) {
      if (requestCurrent(request) && (!owner || requestCurrent(owner))) setSaveStatus(_("Save failed."));
    }
  }

  async function saveResults() {
    var result = lastResult();
    if (!result) { setSaveStatus(_("Run a test first.")); return; }
    await saveArtifact("results", "result.json", result, null, resultOwner);
  }

  async function saveProvenance() {
    var result = lastResult();
    if (!result || !result.provenance) { setSaveStatus(_("No provenance in the current result.")); return; }
    await saveArtifact("provenance", "provenance.json", result.provenance, null, resultOwner);
  }

  function saveConfig() {
    return saveArtifact("config", "config.json", currentConfig());
  }

  async function saveRenderedPlot(owner, request) {
    var plot = window.stxStatsPlot;
    function current() { return requestCurrent(request) && requestCurrent(owner) && plot.owner() === owner; }
    if (!current()) return false;
    var link = $("statsPlotPng");
    var href = link && !link.hidden ? link.getAttribute("href") : "";
    if (!href) return false;
    var response = await fetch(href);
    if (!current()) return false;
    if (!response.ok) return false;
    var view = new Uint8Array(await response.arrayBuffer());
    if (!current()) return false;
    var binary = "";
    for (var i = 0; i < view.length; i++) binary += String.fromCharCode(view[i]);
    await saveArtifact("plots", "plot.png", null, window.btoa(binary), owner);
    return true;
  }

  async function savePlot() {
    // Prefer the RENDERED plot: a project should get the figure, not only its
    // spec. The spec is the fallback when no image has been drawn yet.
    var request = beginRequest("save-plot");
    var plot = window.stxStatsPlot;
    var owner = plot && plot.owner ? plot.owner() : null;
    if (!owner) { setSaveStatus(_("Draw a plot first.")); return; }
    try {
      if (await saveRenderedPlot(owner, request)) return;
      if (!requestCurrent(request) || !requestCurrent(owner) || plot.owner() !== owner) return;
      var spec = plot.spec ? plot.spec() : null;
      if (!spec) { setSaveStatus(_("Draw a plot first.")); return; }
      await saveArtifact("plots", "plot-spec.json", spec, null, owner);
    } catch (e) {
      if (requestCurrent(request) && requestCurrent(owner)) setSaveStatus(_("Save failed."));
    }
  }

  // ---- Test -------------------------------------------------------------
  function selectedTest() {
    var checked = document.querySelector('input[name="statsTest"]:checked');
    return checked ? TESTS.find(function (t) { return t.name === checked.value; }) : null;
  }

  function renderTests(available) {
    var box = $("statsTests");
    box.innerHTML = "";
    var lastCat = null;
    TESTS.forEach(function (t, i) {
      if (available && available.indexOf(t.name) < 0) return;
      if (t.cat !== lastCat) {
        var h = document.createElement("div");
        h.className = "stats-tests__cat";
        h.textContent = CATEGORY_LABELS[t.cat] || t.cat;
        box.appendChild(h);
        lastCat = t.cat;
      }
      var label = document.createElement("label");
      label.className = "stats-test";
      var input = document.createElement("input");
      input.type = "radio";
      input.name = "statsTest";
      input.value = t.name;
      if (i === 0) input.checked = true;
      input.addEventListener("change", syncOptions);
      var text = document.createElement("span");
      setSegments(text, withSymbol(t.label, t.sym));
      label.append(input, text);
      box.appendChild(label);
    });
    syncOptions();
  }

  function syncOptions() {
    var t = selectedTest();
    $("statsPopmeanWrap").hidden = !t || t.name !== "ttest_1samp";
  }

  function showError(message) {
    var el = $("statsError");
    el.textContent = message || "";
    el.hidden = !message;
    if (message && window.stxPanes) window.stxPanes.show("test", "stats");
  }

  function buildPayload(test, groups) {
    var alignmentError = rowIntegrityError(test.name);
    if (alignmentError) return alignmentError;
    var filled = groups.filter(function (g) { return g.length; });
    var payload = { test_name: test.name, alternative: $("statsAlt").value, group_names: [] };
    groups.forEach(function (g, i) { if (g.length) payload.group_names.push(groupName(i)); });
    if (test.kind === "one") {
      if (filled.length < 1) return _("Enter at least one group of numbers.");
      payload.data = filled[0];
      if (test.name === "ttest_1samp") payload.popmean = Number($("statsPopmean").value) || 0;
    } else if (test.kind === "two" || test.kind === "paired") {
      if (filled.length < 2) return _("This test needs two groups.");
      if (test.kind === "paired" && filled[0].length !== filled[1].length)
        return _("Paired tests need both groups to have the same number of values.");
      payload.data = filled[0];
      payload.data2 = filled[1];
    } else {
      if (filled.length < 2) return _("This test needs at least two groups.");
      payload.groups = filled;
    }
    return payload;
  }

  async function calculate() {
    var test = selectedTest();
    if (!test) return showError(_("Pick a test."));
    var payload = buildPayload(test, readGroups());
    if (typeof payload === "string") return showError(payload);
    var request = beginRequest("calculate");
    clearResult();
    if (window.stxStatsPlot && window.stxStatsPlot.invalidate) window.stxStatsPlot.invalidate();
    showError("");
    var btn = $("statsCalculate");
    btn.disabled = true;
    try {
      var r = await api("/api/run", payload);
      if (!requestCurrent(request)) return;
      if (!r.ok) return showError((r.body && r.body.error) || fmt(_("Request failed (HTTP %s)."), [r.status]));
      renderResult(test, r.body, request);
      if (window.stxStatsPlot) window.stxStatsPlot.draw(payload, request);
      if (window.stxPanes) window.stxPanes.show("results", "stats");
    } catch (e) {
      if (requestCurrent(request)) showError(_("Could not reach the Statistics service."));
    } finally {
      if (requestLatest(request)) btn.disabled = false;
    }
  }

  // ---- Results ----------------------------------------------------------
  // All formatting (rounding, symbols, labels) comes from the library's result["apa"].

  // Cells are strings or segment arrays.
  function cell(el, v) {
    if (Array.isArray(v)) setSegments(el, v);
    else el.textContent = v;
  }

  function rows(tbody, pairs) {
    tbody.textContent = "";
    pairs.forEach(function (p) {
      if (p[1] === undefined || p[1] === null || p[1] === "") return;
      var tr = document.createElement("tr");
      var th = document.createElement("th");
      cell(th, p[0]);
      var td = document.createElement("td");
      cell(td, p[1]);
      tr.append(th, td);
      tbody.appendChild(tr);
    });
  }

  function descriptives(desc) {
    var table = $("statsDescTable");
    table.hidden = !desc;
    if (!desc) return;
    var head = $("statsDescHead");
    var body = $("statsDescRows");
    head.textContent = "";
    body.textContent = "";
    var hr = document.createElement("tr");
    desc.columns.forEach(function (segs) {
      var th = document.createElement("th");
      th.scope = "col";
      setSegments(th, translated(segs));
      hr.appendChild(th);
    });
    head.appendChild(hr);
    desc.rows.forEach(function (r) {
      var tr = document.createElement("tr");
      r.forEach(function (segs) {
        var td = document.createElement("td");
        setSegments(td, segs);
        tr.appendChild(td);
      });
      body.appendChild(tr);
    });
  }

  var lastPlain = "";
  var lastApaHtml = "";

  function renderResult(test, res, owner) {
    resultOwner = owner;
    var apa = res.apa || null;
    $("statsEmpty").hidden = true;
    $("statsResult").hidden = false;
    $("statsCopy").hidden = false;
    $("statsResultTitle").textContent = res.test_method || test.label;
    if (apa) setSegments($("statsFormatted"), apa.segments);
    else $("statsFormatted").textContent = res.formatted || "";
    descriptives(apa && apa.descriptives);
    lastPlain = apa ? apa.plain + (apa.descriptives ? "\n" + apa.descriptives.plain : "") : res.formatted || "";
    lastApaHtml = apa ? apa.html + (apa.descriptives ? "<br>" + apa.descriptives.html : "") : "";
    rows($("statsResultRows"), apa ? apa.table.map(function (r) { return [translated(r.label), r.value]; }) : []);
    $("statsJson").textContent = JSON.stringify(res, null, 2);
  }

  async function correct() {
    var pvalues = parseNumbers($("statsCorrP").value);
    var out = $("statsCorrOut");
    if (!pvalues.length) return rows(out, [[_("Error"), _("Enter p-values.")]]);
    var request = beginRequest("correct");
    try {
      var r = await api("/api/correct", { pvalues: pvalues, method: $("statsCorrMethod").value });
      if (!requestCurrent(request)) return;
      if (!r.ok) return rows(out, [[_("Error"), (r.body && r.body.error) || "HTTP " + r.status]]);
      rows(out, (r.body.results || []).map(function (x) {
        return [[S("p"), T(" " + x.p_apa)], [T("→ "), S("p"), T(" " + x.p_adjusted_apa + (x.rejected ? " *" : ""))]];
      }));
    } catch (e) {
      if (requestCurrent(request)) rows(out, [[_("Error"), _("Could not reach the Statistics service.")]]);
    }
  }

  async function posthoc() {
    var groups = readGroups().filter(function (g) { return g.length; });
    var out = $("statsPhOut");
    if (groups.length < 2) return rows(out, [[_("Error"), _("This test needs at least two groups.")]]);
    var request = beginRequest("posthoc");
    try {
      var r = await api("/api/posthoc", {
        groups: groups,
        method: $("statsPhMethod").value,
        group_names: groups.map(function (_g, i) { return groupName(i); }),
      });
      if (!requestCurrent(request)) return;
      if (!r.ok) return rows(out, [[_("Error"), (r.body && r.body.error) || "HTTP " + r.status]]);
      rows(out, (r.body.comparisons || []).map(function (c) {
        return [c.group_i + " – " + c.group_j, [S("p"), T(" " + c.p_apa + " " + (c.pstars || ""))]];
      }));
    } catch (e) {
      if (requestCurrent(request)) rows(out, [[_("Error"), _("Could not reach the Statistics service.")]]);
    }
  }

  function escapeHtml(text) {
    var div = document.createElement("div");
    div.textContent = String(text);
    return div.innerHTML;
  }

  // Title, APA summary and table, as HTML (keeps <i>/<sub> in Word/Docs) and plain text.
  function resultClip() {
    var title = $("statsResultTitle").textContent;
    var table = $("statsResultRows").closest("table");
    var rowsText = Array.prototype.map.call(table.rows, function (tr) {
      return Array.prototype.map.call(tr.cells, function (c) { return c.textContent; }).join("\t");
    }).join("\n");
    var summaryHtml = lastApaHtml || escapeHtml(lastPlain);
    var desc = $("statsDescTable");
    var descHtml = desc.hidden ? "" : '<table border="1" cellpadding="4" style="border-collapse:collapse">' +
      desc.tHead.innerHTML + desc.tBodies[0].innerHTML + "</table><br>";
    var tableHtml = descHtml + '<table border="1" cellpadding="4" style="border-collapse:collapse">' +
      table.tBodies[0].innerHTML + "</table>";
    return {
      html: "<p><b>" + escapeHtml(title) + "</b></p><p>" + summaryHtml + "</p>" + tableHtml,
      text: title + "\n" + lastPlain + (rowsText ? "\n\n" + rowsText : ""),
    };
  }

  // No ClipboardItem or plain http: copying a selected rendered element still carries formatting.
  function legacyCopy(clip) {
    var holder = document.createElement("div");
    holder.contentEditable = "true";
    holder.innerHTML = clip.html;
    holder.style.cssText = "position:fixed;top:0;left:-9999px;opacity:0;pointer-events:none;white-space:pre-wrap";
    document.body.appendChild(holder);
    var sel = window.getSelection();
    var range = document.createRange();
    range.selectNodeContents(holder);
    sel.removeAllRanges();
    sel.addRange(range);
    // Set the data ourselves: the browser's own serialization inlines the page's (dark) theme colours.
    function onCopy(e) {
      if (!e.clipboardData) return;
      e.clipboardData.setData("text/html", clip.html);
      e.clipboardData.setData("text/plain", clip.text);
      e.preventDefault();
    }
    document.addEventListener("copy", onCopy, true);
    var ok = false;
    try { ok = document.execCommand("copy"); } catch (e) { ok = false; }
    document.removeEventListener("copy", onCopy, true);
    sel.removeAllRanges();
    holder.remove();
    return ok;
  }

  function selectResultText() {
    var range = document.createRange();
    range.selectNodeContents($("statsFormatted"));
    var sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
  }

  var copyTimer = null;

  function showCopyState(state) {
    var btn = $("statsCopy");
    var label = btn.querySelector(".stats-copy__label");
    var message = state === "copied" ? _("Copied") : state === "failed" ? _("Copy failed") : _("Copy");
    label.textContent = message;
    btn.dataset.state = state;
    $("statsCopyStatus").textContent = state === "idle" ? "" : message;
    clearTimeout(copyTimer);
    if (state !== "idle") copyTimer = setTimeout(function () { showCopyState("idle"); }, 1500);
  }

  async function copyResult() {
    if (!lastResult()) return;
    var owner = resultOwner;
    var clip = resultClip();
    var ok = false;
    if (window.isSecureContext && navigator.clipboard && navigator.clipboard.write && window.ClipboardItem) {
      try {
        await navigator.clipboard.write([new ClipboardItem({
          "text/html": new Blob([clip.html], { type: "text/html" }),
          "text/plain": new Blob([clip.text], { type: "text/plain" }),
        })]);
        ok = true;
      } catch (e) { ok = false; }
    }
    if (!requestCurrent(owner)) return;
    if (!ok) ok = legacyCopy(clip);
    if (!ok) selectResultText();
    if (!requestCurrent(owner)) return;
    showCopyState(ok ? "copied" : "failed");
  }

  // Shared with recommend.js (loaded next).
  window.stxStatsApp = { _: _, fmt: fmt, api: api, readGroups: readGroups, groupName: groupName, setSegments: setSegments,
    rowIntegrityError: rowIntegrityError, beginRequest: beginRequest, requestCurrent: requestCurrent, requestLatest: requestLatest };

  async function init() {
    setGroups([[], []]);
    renderTests(null);
    document.addEventListener("stats:data-change", invalidateAnalysis);
    document.addEventListener("change", function (event) {
      if (event.target.name === "statsTest" || ["statsDesign", "statsScale", "statsAlt", "statsPopmean", "statsCorrP", "statsCorrMethod", "statsPhMethod"].indexOf(event.target.id) !== -1) invalidateAnalysis();
    });
    document.addEventListener("input", function (event) {
      if (["statsPopmean", "statsCorrP"].indexOf(event.target.id) !== -1) invalidateAnalysis();
    });
    $("statsAddGroup").addEventListener("click", function () {
      invalidateImportedRows();
      addGroup();
    });
    $("statsClear").addEventListener("click", function () { setGroups([[], []]); });
    $("statsSample").addEventListener("click", function () {
      if (hasUserData() && !window.confirm(_("Replace the data in the boxes with the sample dataset?"))) return;
      setGroups(SAMPLE);
    });
    $("statsChooseFile").addEventListener("click", function () {
      // Project mode imports from the PROJECT; the manual picker is Quick
      // analysis' input, so it refuses here instead of offering a second path.
      if (projectId()) { showError(_("In project mode data comes from the project. Use Quick analysis to choose a file.")); return; }
      $("statsCsv").click();
    });
    $("statsCsv").addEventListener("change", function () {
      if (this.files && this.files[0]) loadCsv(this.files[0]);
      this.value = "";
    });
    var dropZone = $("statsDataDrop");
    // The whole zone stays a click target; interactive children keep their own
    // behaviour (the choose button, the group boxes), so forward only the rest.
    dropZone.addEventListener("click", function (event) {
      if (projectId()) return;  // project mode has no manual picker
      if (event.target.closest("button, input, textarea, select, label, a")) return;
      $("statsCsv").click();
    });
    ["dragenter", "dragover"].forEach(function (eventName) {
      dropZone.addEventListener(eventName, function (event) {
        event.preventDefault();
        dropZone.classList.add("stats-dropzone--active");
      });
    });
    dropZone.addEventListener("dragleave", function (event) {
      if (!dropZone.contains(event.relatedTarget)) {
        dropZone.classList.remove("stats-dropzone--active");
      }
    });
    dropZone.addEventListener("drop", function (event) {
      event.preventDefault();
      dropZone.classList.remove("stats-dropzone--active");
      if (projectId()) { showError(_("In project mode data comes from the project. Use Quick analysis to drop a file.")); return; }
      var file = event.dataTransfer && event.dataTransfer.files && event.dataTransfer.files[0];
      if (!file) return;
      if (!/\.(csv|tsv|txt)$/i.test(file.name)) {
        showError(_("Choose a CSV or TSV file."));
        return;
      }
      loadCsv(file);
    });
    $("statsCalculate").addEventListener("click", calculate);
    $("statsCorrect").addEventListener("click", correct);
    $("statsPosthoc").addEventListener("click", posthoc);
    $("statsCopy").addEventListener("click", copyResult);
    applyMode();
    var modeToggle = $("statsModeToggle");
    if (modeToggle) {
      modeToggle.addEventListener("click", function () {
        // Leaving project mode is a NAVIGATION, not a UI flag: the page reloads
        // without `?project=`, which is the stateless state the server refuses
        // to persist into.
        var url = new URL(window.location.href);
        url.searchParams.delete("project");
        // Explicit stateless mode: without this the SDK would resume the LAST
        // VISITED project and the page would keep accepting writes.
        url.searchParams.set("quick", "1");
        window.location.href = url.toString();
      });
    }
    var filePanel = $("statsProjectFiles");
    if (filePanel) {
      filePanel.addEventListener("click", function (event) {
        var button = event.target.closest(".stats-project__import");
        if (button) importProjectFile(button.getAttribute("data-file"));
      });
    }
    $("statsSaveResults").addEventListener("click", saveResults);
    $("statsSaveProvenance").addEventListener("click", saveProvenance);
    $("statsSaveConfig").addEventListener("click", saveConfig);
    $("statsSavePlot").addEventListener("click", savePlot);
    // Readiness marker: every listener above is attached, so an automation
    // client may interact. Without it a browser test has to guess with a sleep,
    // and a click that lands in the gap between DOM-ready and this line is
    // silently dropped (measured: the e2e layer flaked exactly that way).
    var appRoot = document.querySelector("[data-stats-app]");
    if (appRoot) appRoot.setAttribute("data-stats-ready", "1");
    try {
      var t = await api("/api/tests");
      if (t.ok && Array.isArray(t.body.tests)) {
        var current = selectedTest();
        renderTests(t.body.tests);
        if (current) {
          var again = document.querySelector('input[name="statsTest"][value="' + current.name + '"]');
          if (again) again.checked = true;
        }
      }
    } catch (e) { /* keep the static list */ }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
