// SciTeX Statistics: bundled report (PDF download, Save to Files).
// Reads the Data pane and consults app.js's source-row alignment guard.

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
  var WITHIN = { ttest_rel: 1, wilcoxon: 1, friedman: 1 };

  function csrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    if (meta && meta.content && meta.content !== "NOTPROVIDED") return meta.content;
    var m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : "";
  }

  function numbers(text) {
    return String(text || "").split(/[\s,;]+/).filter(Boolean).map(Number)
      .filter(function (n) { return Number.isFinite(n); });
  }

  function payload() {
    var groups = [];
    var names = [];
    document.querySelectorAll("#statsGroups .stats-group").forEach(function (row) {
      var values = numbers((row.querySelector(".stats-group__input") || {}).value);
      if (!values.length) return;
      groups.push(values);
      var label = row.querySelector(".stats-group__label span");
      names.push(label ? label.textContent.trim() : "Group " + (groups.length));
    });
    var select = $("statsDesign");
    var checked = document.querySelector('input[name="statsTest"]:checked');
    var design = select ? (select.value === "paired" ? "within" : "between")
      : (checked && WITHIN[checked.value] ? "within" : "between");
    return { groups: groups, group_names: names, design: design, posthoc: "auto" };
  }

  function status(message, isError, link) {
    var el = $("statsReportStatus");
    el.textContent = message || "";
    el.classList.toggle("stats-error", !!isError);
    if (link) {
      el.appendChild(document.createTextNode(" "));
      var a = document.createElement("a");
      a.href = link.href;
      a.textContent = link.text;
      el.appendChild(a);
    }
  }

  function begin() {
    var app = window.stxStatsApp;
    if (!app || !app.beginRequest || !app.requestCurrent || !app.requestLatest) {
      status(_("Could not verify the current report inputs. Reload the Statistics page."), true);
      return null;
    }
    return app.beginRequest("report");
  }

  function current(request) { return window.stxStatsApp.requestCurrent(request); }

  function busy(button, value) {
    var buttons = [$("statsReportPdf"), $("statsReportSave")];
    buttons.forEach(function (b) { if (b) { b.disabled = value; b.removeAttribute("aria-busy"); } });
    if (value) button.setAttribute("aria-busy", "true");
  }

  function post(path, body) {
    return fetch(STX_MOUNT + path, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken() },
      credentials: "same-origin",
      body: JSON.stringify(body),
    });
  }

  async function errorText(res) {
    try { return (await res.json()).error || ""; } catch (e) { return ""; }
  }

  function ready() {
    var body = payload();
    if (body.design === "within") {
      var app = window.stxStatsApp;
      var alignmentError = app && typeof app.rowIntegrityError === "function"
        ? app.rowIntegrityError(null, body.design)
        : _("Source row alignment is unavailable. Reload the Statistics page and import a complete CSV or TSV file.");
      if (alignmentError) {
        status(alignmentError, true);
        return null;
      }
    }
    if (body.groups.length < 2) {
      status(_("A report needs at least two groups of numbers."), true);
      return null;
    }
    return body;
  }

  async function downloadPdf() {
    var body = ready();
    if (!body) return;
    var request = begin();
    if (!request) return;
    busy($("statsReportPdf"), true);
    status(_("Building report…"));
    try {
      var res = await post("/api/report/pdf", body);
      if (!current(request)) return;
      if (!res.ok) {
        var error = await errorText(res);
        if (current(request)) status(error || _("Could not build the report."), true);
        return;
      }
      var blob = await res.blob();
      if (!current(request)) return;
      var match = /filename="([^"]+)"/.exec(res.headers.get("Content-Disposition") || "");
      var a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = match ? match[1] : "stats-report.pdf";
      document.body.appendChild(a);
      a.click();
      setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
      status(_("Report downloaded."));
    } catch (e) {
      if (current(request)) status(_("Could not reach the Statistics service."), true);
    } finally {
      if (window.stxStatsApp.requestLatest(request)) busy($("statsReportPdf"), false);
    }
  }

  async function saveToFiles() {
    var body = ready();
    if (!body) return;
    var request = begin();
    if (!request) return;
    busy($("statsReportSave"), true);
    status(_("Saving report to Files…"));
    try {
      var res = await post("/api/report/save", body);
      if (!current(request)) return;
      if (!res.ok) {
        var error = await errorText(res);
        if (current(request)) status(error || _("Could not save the report."), true);
        return;
      }
      var out = await res.json();
      if (!current(request)) return;
      var link = out.files_url ? { href: out.files_url, text: _("Open Files") } : null;
      status(_("Saved to Files:") + " " + out.saved, false, link);
    } catch (e) {
      if (current(request)) status(_("Could not reach the Statistics service."), true);
    } finally {
      if (window.stxStatsApp.requestLatest(request)) busy($("statsReportSave"), false);
    }
  }

  async function init() {
    var pdfBtn = $("statsReportPdf");
    if (!pdfBtn) return;
    document.addEventListener("stats:analysis-change", function () { status(""); });
    pdfBtn.addEventListener("click", downloadPdf);
    $("statsReportSave").addEventListener("click", saveToFiles);
    try {
      var res = await fetch(STX_MOUNT + "/api/report/capabilities", { credentials: "same-origin" });
      var caps = await res.json();
      $("statsReportSave").hidden = !caps.save_to_files;
      if (!caps.pdf) {
        pdfBtn.disabled = true;
        status(_("PDF reports are not available on this server."), true);
      }
    } catch (e) { /* keep Download visible; Save stays hidden */ }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
