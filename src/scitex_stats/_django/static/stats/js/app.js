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

  // kind: how the Data groups map onto run_test arguments.
  var TESTS = [
    { cat: "Two independent groups", name: "ttest_ind", label: "Student's t-test", kind: "two" },
    { cat: "Two independent groups", name: "mannwhitneyu", label: "Mann–Whitney U", kind: "two" },
    { cat: "Two independent groups", name: "brunner_munzel", label: "Brunner–Munzel", kind: "two" },
    { cat: "Two independent groups", name: "ks_2samp", label: "Kolmogorov–Smirnov (2-sample)", kind: "two" },
    { cat: "Paired groups", name: "ttest_rel", label: "Paired t-test", kind: "paired" },
    { cat: "Paired groups", name: "wilcoxon", label: "Wilcoxon signed-rank", kind: "paired" },
    { cat: "Three or more groups", name: "anova", label: "One-way ANOVA", kind: "groups" },
    { cat: "Three or more groups", name: "kruskal", label: "Kruskal–Wallis", kind: "groups" },
    { cat: "Three or more groups", name: "friedman", label: "Friedman (repeated measures)", kind: "groups" },
    { cat: "Correlation", name: "pearson", label: "Pearson r", kind: "two" },
    { cat: "Correlation", name: "spearman", label: "Spearman ρ", kind: "two" },
    { cat: "Correlation", name: "kendall", label: "Kendall τ", kind: "two" },
    { cat: "One sample", name: "ttest_1samp", label: "One-sample t-test", kind: "one" },
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

  async function api(path, payload) {
    var options = payload === undefined
      ? { method: "GET" }
      : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) };
    var res = await fetch(STX_MOUNT + path, options);
    var body = {};
    try { body = await res.json(); } catch (e) { /* non-JSON */ }
    return { ok: res.ok, status: res.status, body: body };
  }

  // ---- Data -------------------------------------------------------------
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
      row.remove();
      renumber();
    });
    function updateCount() {
      count.textContent = fmt(_("n = %s"), [parseNumbers(area.value).length]);
    }
    area.addEventListener("input", updateCount);
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

  function setGroups(groups) {
    $("statsGroups").innerHTML = "";
    groups.forEach(function (g) { addGroup(g); });
    if (groups.length < 2) addGroup();
  }

  function loadCsv(file) {
    var reader = new FileReader();
    reader.onload = function () {
      var lines = String(reader.result).split(/\r?\n/).filter(function (l) { return l.trim(); });
      var sep = file.name.endsWith(".tsv") || (lines[0] || "").indexOf("\t") >= 0 ? "\t" : ",";
      var rows = lines.map(function (l) { return l.split(sep); });
      var cols = rows.reduce(function (m, r) { return Math.max(m, r.length); }, 0);
      var groups = [];
      for (var c = 0; c < cols; c++) {
        var col = rows
          .map(function (r) { return r[c] === undefined ? NaN : Number(String(r[c]).trim()); })
          .filter(function (n) { return Number.isFinite(n); });
        if (col.length) groups.push(col);
      }
      if (groups.length) setGroups(groups);
      else showError(_("No numeric columns found in this file."));
    };
    reader.readAsText(file);
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
      text.textContent = t.label;
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
    var filled = groups.filter(function (g) { return g.length; });
    var payload = { test_name: test.name, alternative: $("statsAlt").value };
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
    showError("");
    var btn = $("statsCalculate");
    btn.disabled = true;
    try {
      var r = await api("/api/run", payload);
      if (!r.ok) return showError((r.body && r.body.error) || fmt(_("Request failed (HTTP %s)."), [r.status]));
      renderResult(test, r.body);
      if (window.stxPanes) window.stxPanes.show("results", "stats");
    } catch (e) {
      showError(_("Could not reach the Statistics service."));
    } finally {
      btn.disabled = false;
    }
  }

  // ---- Results ----------------------------------------------------------
  function num(v, digits) {
    if (v === null || v === undefined || v === "") return "—";
    if (typeof v !== "number") return String(v);
    if (v !== 0 && Math.abs(v) < 0.001) return v.toExponential(2);
    return v.toFixed(digits === undefined ? 3 : digits);
  }

  function rows(tbody, pairs) {
    tbody.innerHTML = "";
    pairs.forEach(function (p) {
      if (p[1] === undefined || p[1] === null || p[1] === "—") return;
      var tr = document.createElement("tr");
      var th = document.createElement("th");
      th.textContent = p[0];
      var td = document.createElement("td");
      td.textContent = p[1];
      tr.append(th, td);
      tbody.appendChild(tr);
    });
  }

  function renderResult(test, res) {
    $("statsEmpty").hidden = true;
    $("statsResult").hidden = false;
    $("statsCopy").hidden = false;
    $("statsResultTitle").textContent = res.test_method || test.label;
    $("statsFormatted").textContent = res.formatted || "";
    var n = res.n !== undefined ? res.n
      : res.n_x !== undefined ? [res.n_x, res.n_y].filter(function (x) { return x !== undefined && x !== null; }).join(", ")
      : Array.isArray(res.n_samples) ? res.n_samples.join(", ") : undefined;
    rows($("statsResultRows"), [
      [_("Statistic") + (res.stat_symbol ? " (" + res.stat_symbol + ")" : ""), num(res.statistic)],
      [_("p-value"), num(res.pvalue, 4)],
      [_("Significance"), res.stars !== undefined ? (res.significant ? _("significant") : _("not significant")) + " (" + res.stars + ")" : undefined],
      [_("Effect size") + (res.effect_size_metric ? " (" + res.effect_size_metric + ")" : ""), res.effect_size !== undefined ? num(res.effect_size) : undefined],
      [_("Interpretation"), res.effect_size_interpretation],
      [_("Power"), res.power !== undefined ? num(res.power) : undefined],
      [_("Sample size"), n === undefined || n === "" ? undefined : String(n)],
      [_("Null hypothesis"), res.H0],
    ]);
    $("statsJson").textContent = JSON.stringify(res, null, 2);
  }

  async function correct() {
    var pvalues = parseNumbers($("statsCorrP").value);
    var out = $("statsCorrOut");
    if (!pvalues.length) return rows(out, [[_("Error"), _("Enter p-values.")]]);
    var r = await api("/api/correct", { pvalues: pvalues, method: $("statsCorrMethod").value });
    if (!r.ok) return rows(out, [[_("Error"), (r.body && r.body.error) || "HTTP " + r.status]]);
    rows(out, (r.body.results || []).map(function (x) {
      return [num(x.pvalue, 4), "→ " + num(x.pvalue_adjusted, 4) + (x.rejected ? " *" : "")];
    }));
  }

  async function posthoc() {
    var groups = readGroups().filter(function (g) { return g.length; });
    var out = $("statsPhOut");
    if (groups.length < 2) return rows(out, [[_("Error"), _("This test needs at least two groups.")]]);
    var r = await api("/api/posthoc", {
      groups: groups,
      method: $("statsPhMethod").value,
      group_names: groups.map(function (_g, i) { return groupName(i); }),
    });
    if (!r.ok) return rows(out, [[_("Error"), (r.body && r.body.error) || "HTTP " + r.status]]);
    rows(out, (r.body.comparisons || []).map(function (c) {
      return [c.group_i + " – " + c.group_j, "p = " + num(c.pvalue, 4) + " " + (c.pstars || "")];
    }));
  }

  function copyResult() {
    var text = $("statsResultTitle").textContent + "\n" + $("statsFormatted").textContent;
    if (navigator.clipboard) navigator.clipboard.writeText(text);
  }

  async function init() {
    setGroups([[], []]);
    renderTests(null);
    $("statsAddGroup").addEventListener("click", function () { addGroup(); });
    $("statsClear").addEventListener("click", function () { setGroups([[], []]); });
    $("statsSample").addEventListener("click", function () { setGroups(SAMPLE); });
    $("statsCsv").addEventListener("change", function () {
      if (this.files && this.files[0]) loadCsv(this.files[0]);
      this.value = "";
    });
    $("statsCalculate").addEventListener("click", calculate);
    $("statsCorrect").addEventListener("click", correct);
    $("statsPosthoc").addEventListener("click", posthoc);
    $("statsCopy").addEventListener("click", copyResult);
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
