// SciTeX Statistics: applicable tests (✓/✗ + reasons), the primary recommendation,
// a figure slot, and "Run all applicable" sensitivity analyses.
// All decisions come from the package (/api/recommend-test, /api/run-all).

(function () {
  "use strict";

  var app = window.stxStatsApp;
  if (!app) return;
  var _ = app._;
  var $ = function (id) { return document.getElementById(id); };

  // Italic Latin statistical symbols (APA) before a relation or in a test name ("t-test", "U test"); Greek stays upright.
  var SYM_RE = /(^|[^A-Za-zÀ-ɏ'’])(p|n|t|F|U|H|W|BM|OR|M|SD)(?=\s*[=<>≥≤]|-test|-value|\s+test|\s*検定|\s*値)/g;

  function el(tag, cls, text) {
    var node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function symbolSegments(text) {
    var segs = [];
    var last = 0;
    String(text).replace(SYM_RE, function (m, pre, sym, at) {
      var start = at + pre.length;
      if (start > last) segs.push({ text: text.slice(last, start), kind: "text" });
      segs.push({ text: sym, kind: "sym" });
      last = start + sym.length;
      return m;
    });
    if (last < text.length) segs.push({ text: text.slice(last), kind: "text" });
    return segs;
  }

  // A reason item from the package: {msg, args, status}; msg is the gettext msgid.
  function itemText(item) {
    var args = (item.args || []).map(function (a) { return typeof a === "string" ? _(a) : a; });
    return args.length ? app.fmt(_(item.msg), args) : _(item.msg);
  }

  function itemNode(tag, item, cls) {
    var node = el(tag, cls);
    app.setSegments(node, symbolSegments(itemText(item)));
    return node;
  }

  function labelNode(tag, label, cls) {
    var node = el(tag, cls);
    app.setSegments(node, symbolSegments(_(label)));
    return node;
  }

  function currentPayload() {
    var raw = app.readGroups();
    var groups = [];
    var names = [];
    raw.forEach(function (g, i) {
      if (g.length) { groups.push(g); names.push(app.groupName(i)); }
    });
    if (groups.length < 2) return null;
    return { groups: groups, group_names: names, design: $("statsDesign").value, scale: $("statsScale").value };
  }

  var lastPayload = null;
  var lastRec = null;

  function setVisible(show) {
    $("statsSummary").hidden = !show;
    if (show) $("statsEmpty").hidden = true;
    else if ($("statsResult").hidden) $("statsEmpty").hidden = false;
  }

  function renderNotes(notes) {
    var ul = $("statsRecNotes");
    ul.textContent = "";
    (notes || []).forEach(function (n) { ul.appendChild(itemNode("li", n)); });
    ul.hidden = !ul.children.length;
  }

  function renderApplicability(rec) {
    var body = $("statsApplicRows");
    body.textContent = "";
    var primaryId = rec.primary && rec.primary.test_id;
    var rows = rec.applicability.slice().sort(function (a, b) {
      var ra = a.test_id === primaryId ? 0 : a.applicable ? 1 : 2;
      var rb = b.test_id === primaryId ? 0 : b.applicable ? 1 : 2;
      return ra - rb;
    });
    rows.forEach(function (row) {
      var tr = el("tr", "stats-applic__row" + (row.applicable ? " is-ok" : " is-no") + (row.test_id === primaryId ? " is-primary" : ""));
      var mark = el("td", "stats-applic__mark", row.applicable ? "✓" : "×"); // ✗ (U+2717) is missing from common phone UI fonts
      mark.setAttribute("aria-label", row.applicable ? _("Applicable") : _("Not applicable"));
      var name = el("td", "stats-applic__name");
      name.appendChild(labelNode("span", row.label));
      if (row.test_id === primaryId) name.appendChild(el("span", "stats-badge stats-badge--primary", _("Recommended")));
      var reasons = el("td", "stats-applic__reasons");
      var ul = el("ul", "stats-reasons");
      row.reason_items
        .filter(function (i) { return row.applicable ? i.status !== "fail" : i.status !== "ok"; })
        .forEach(function (i) { ul.appendChild(itemNode("li", i, "is-" + i.status)); });
      reasons.appendChild(ul);
      tr.append(mark, name, reasons);
      body.appendChild(tr);
    });
  }

  function renderCard(rec) {
    var card = $("statsRecCard");
    card.textContent = "";
    if (!rec.primary) {
      card.appendChild(el("p", "stats-rec__title", _("No test can be recommended for these data.")));
    } else {
      var title = el("p", "stats-rec__title");
      title.append(el("span", "stats-rec__kicker", _("Recommended primary test")), labelNode("strong", rec.primary.label));
      card.append(title, itemNode("p", rec.primary.reason_item, "stats-rec__reason"));
    }
    var path = el("ol", "stats-rec__path");
    rec.decision_path.forEach(function (i) { path.appendChild(itemNode("li", i, "is-" + i.status)); });
    var pathBox = el("details", "stx-acc stats-acc");
    pathBox.open = true;
    pathBox.append(el("summary", "", _("Decision path")), path);
    card.appendChild(pathBox);
    if (rec.alternatives.length) {
      var alts = el("details", "stx-acc stats-acc");
      var list = el("ul", "stats-reasons");
      rec.alternatives.forEach(function (a) {
        var li = el("li");
        li.append(labelNode("strong", a.label), document.createTextNode(": "), itemNode("span", a.why_item));
        list.appendChild(li);
      });
      alts.append(el("summary", "", app.fmt(_("Alternatives (%s), secondary"), [rec.alternatives.length])), list);
      card.appendChild(alts);
    }
  }

  function fixed(v, digits) {
    return v === null || v === undefined ? "" : Number(v).toFixed(digits);
  }

  function checkSegments(r) {
    var segs = [];
    if (r.symbol) {
      segs.push({ text: r.symbol, kind: "sym" });
      segs.push({ text: (r.df ? "(" + r.df.join(", ") + ")" : "") + " = " + fixed(r.statistic, r.symbol === "W" ? 3 : 2), kind: "text" });
    } else {
      segs.push({ text: fixed(r.statistic, 2), kind: "text" });
    }
    if (r.p_apa) segs.push({ text: ", ", kind: "text" }, { text: "p", kind: "sym" }, { text: " " + r.p_apa, kind: "text" });
    return segs;
  }

  var SVG = "http://www.w3.org/2000/svg";
  function svgEl(tag, attrs) {
    var node = document.createElementNS(SVG, tag);
    Object.keys(attrs).forEach(function (k) { node.setAttribute(k, attrs[k]); });
    return node;
  }

  // Minimal normal Q-Q plot: points against the fitted reference line.
  function qqPlot(q) {
    var size = 120, pad = 14;
    var xs = q.theoretical, ys = q.observed;
    var x0 = Math.min.apply(null, xs), x1 = Math.max.apply(null, xs);
    var lineY = function (x) { return q.line.slope * x + q.line.intercept; };
    var yv = ys.concat([lineY(x0), lineY(x1)]);
    var y0 = Math.min.apply(null, yv), y1 = Math.max.apply(null, yv);
    var sx = function (x) { return pad + (x - x0) / ((x1 - x0) || 1) * (size - 2 * pad); };
    var sy = function (y) { return size - pad - (y - y0) / ((y1 - y0) || 1) * (size - 2 * pad); };
    var svg = svgEl("svg", { viewBox: "0 0 " + size + " " + size, class: "stats-qq__svg", role: "img" });
    svg.appendChild(svgEl("rect", { x: 0.5, y: 0.5, width: size - 1, height: size - 1, class: "stats-qq__frame" }));
    svg.appendChild(svgEl("line", { x1: sx(x0), y1: sy(lineY(x0)), x2: sx(x1), y2: sy(lineY(x1)), class: "stats-qq__line" }));
    xs.forEach(function (x, i) { svg.appendChild(svgEl("circle", { cx: sx(x), cy: sy(ys[i]), r: 2.2, class: "stats-qq__pt" })); });
    var fig = el("figure", "stats-qq");
    svg.setAttribute("aria-label", app.fmt(_("Normal Q-Q plot: %s"), [_(q.sample)]));
    fig.append(svg, el("figcaption", "", _(q.sample)));
    return fig;
  }

  function renderAssumptions(rec) {
    var box = $("statsAssumptions");
    box.textContent = "";
    var sec = rec.assumption_checks;
    if (!sec || !sec.rows.length) return;
    box.appendChild(el("h3", "stats-summary__title", _("Assumption checks")));
    var table = el("table", "stats-applic stats-applic--checks");
    var head = el("tr");
    [_("Check"), _("Sample"), _("Result"), _("Threshold"), _("Decision")].forEach(function (h) {
      var th = el("th", "", h); th.scope = "col"; head.appendChild(th);
    });
    var thead = el("thead");
    thead.appendChild(head);
    var tbody = el("tbody");
    sec.rows.forEach(function (r) {
      var tr = el("tr", "is-" + r.decision.replace(/\s+/g, "-"));
      var result = el("td", "stats-applic__stat");
      app.setSegments(result, checkSegments(r));
      tr.append(el("td", "", _(r.check)), el("td", "", _(r.sample)), result, itemNode("td", r.threshold), el("td", "stats-check__decision", _(r.decision)));
      tbody.appendChild(tr);
    });
    table.append(thead, tbody);
    var wrap = el("div", "stats-applic-wrap");
    wrap.appendChild(table);
    box.appendChild(wrap);
    sec.notes.forEach(function (n) { box.appendChild(itemNode("p", n, "stats-check-note")); });
    if (sec.qq.length) {
      var grid = el("div", "stats-qq-grid");
      sec.qq.forEach(function (q) { grid.appendChild(qqPlot(q)); });
      box.appendChild(grid);
    }
  }

  async function recommend(opts) {
    var payload = currentPayload();
    if (!payload) { lastRec = null; setVisible(false); return; }
    var key = JSON.stringify(payload);
    if (key === lastPayload && !(opts && opts.force)) return;
    lastPayload = key;
    var r = await app.api("/api/recommend-test", payload);
    if (JSON.stringify(currentPayload()) !== key) return; // data changed meanwhile
    if (!r.ok) {
      lastRec = null;
      renderNotes([{ msg: (r.body && r.body.error) || "Request failed (HTTP %s).", args: r.body && r.body.error ? [] : [r.status] }]);
      $("statsApplicRows").textContent = "";
      $("statsRecCard").textContent = "";
      $("statsAssumptions").textContent = "";
      $("statsRunAll").hidden = true;
      setVisible(true);
      return;
    }
    lastRec = r.body;
    renderNotes(lastRec.notes);
    renderApplicability(lastRec);
    renderCard(lastRec);
    renderAssumptions(lastRec);
    $("statsRunAll").hidden = !lastRec.applicability.some(function (t) { return t.applicable; });
    $("statsRunAllOut").hidden = true;
    setVisible(true);
    document.dispatchEvent(new CustomEvent("stats:recommendation", {
      detail: { payload: payload, recommendation: lastRec, slot: $("statsPlotSlot") },
    }));
    if (opts && opts.show) {
      // Calculate then runs the recommended test, not whatever was checked before.
      var radio = lastRec.primary && document.querySelector('input[name="statsTest"][value="' + lastRec.primary.test_id + '"]');
      if (radio) { radio.checked = true; radio.dispatchEvent(new Event("change")); }
      if (window.stxPanes) window.stxPanes.show("results", "stats");
    }
  }

  function num(v) {
    if (v === null || v === undefined) return "";
    var x = Number(v);
    return Number.isInteger(x) ? String(x) : x.toFixed(2);
  }

  function statSegments(r) {
    if (r.error) return [{ text: r.error, kind: "text" }];
    var segs = [];
    if (r.statistic !== null) {
      var df = Array.isArray(r.df) ? r.df.map(num).join(", ") : num(r.df);
      segs.push({ text: r.stat_symbol, kind: /^[A-Za-z]+$/.test(r.stat_symbol) ? "sym" : "text" });
      segs.push({ text: (df ? "(" + df + ")" : "") + " = " + Number(r.statistic).toFixed(2).replace("-", "−") + ", ", kind: "text" });
    }
    segs.push({ text: "p", kind: "sym" });
    segs.push({ text: " " + (r.p_apa || "n/a"), kind: "text" });
    return segs;
  }

  async function runAll() {
    var payload = currentPayload();
    var out = $("statsRunAllOut");
    if (!payload || !lastRec) return;
    var btn = $("statsRunAll");
    btn.disabled = true;
    try {
      payload.primary = lastRec.primary ? lastRec.primary.test_id : null;
      var r = await app.api("/api/run-all", payload);
      out.textContent = "";
      out.hidden = false;
      if (!r.ok) { out.appendChild(el("p", "stats-error", (r.body && r.body.error) || "HTTP " + r.status)); return; }
      var res = r.body;
      out.appendChild(el("h3", "stats-summary__title", _("Sensitivity analyses")));
      var warn = itemNode("p", res.warning_item, "stats-warning");
      warn.setAttribute("role", "note");
      out.appendChild(warn);
      var table = el("table", "stats-applic stats-applic--results");
      var head = el("tr");
      [_("Role"), _("Test"), _("Result")].forEach(function (h) { var th = el("th", "", h); th.scope = "col"; head.appendChild(th); });
      var thead = el("thead");
      thead.appendChild(head);
      var tbody = el("tbody");
      res.results.forEach(function (row) {
        var tr = el("tr", row.role === "primary" ? "is-primary" : "");
        var role = el("td");
        role.appendChild(el("span", "stats-badge" + (row.role === "primary" ? " stats-badge--primary" : ""), row.role === "primary" ? _("Primary (pre-specified)") : _("Sensitivity")));
        var val = el("td", "stats-applic__stat");
        app.setSegments(val, statSegments(row));
        tr.append(role, labelNode("td", row.label), val);
        tbody.appendChild(tr);
      });
      table.append(thead, tbody);
      var wrap = el("div", "stats-applic-wrap");
      wrap.appendChild(table);
      out.append(wrap, itemNode("p", res.agreement.summary_item, "stats-agreement is-" + res.agreement.status));
    } catch (e) {
      out.hidden = false;
      out.textContent = _("Could not reach the Statistics service.");
    } finally {
      btn.disabled = false;
    }
  }

  var timer = null;
  function soon() {
    clearTimeout(timer);
    timer = setTimeout(function () { recommend(); }, 500);
  }

  function init() {
    $("statsRecommend").addEventListener("click", function () { recommend({ force: true, show: true }); });
    $("statsRunAll").addEventListener("click", runAll);
    $("statsGroups").addEventListener("input", soon);
    new MutationObserver(soon).observe($("statsGroups"), { childList: true });
    $("statsDesign").addEventListener("change", soon);
    $("statsScale").addEventListener("change", soon);
    $("statsSample").addEventListener("click", function () {
      setTimeout(function () { recommend({ force: true, show: true }); }, 0);
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
