// SciTeX Statistics: bundled report (PDF download, Save to Files).
// Reads the Data pane from the DOM so app.js stays untouched.

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

  async function post(path, body, busyButton) {
    var buttons = [$("statsReportPdf"), $("statsReportSave")];
    buttons.forEach(function (b) { if (b) b.disabled = true; });
    busyButton.setAttribute("aria-busy", "true");
    try {
      return await fetch(STX_MOUNT + path, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken() },
        credentials: "same-origin",
        body: JSON.stringify(body),
      });
    } finally {
      buttons.forEach(function (b) { if (b) b.disabled = false; });
      busyButton.removeAttribute("aria-busy");
    }
  }

  async function errorText(res) {
    try { return (await res.json()).error || ""; } catch (e) { return ""; }
  }

  function ready() {
    var body = payload();
    if (body.groups.length < 2) {
      status(_("A report needs at least two groups of numbers."), true);
      return null;
    }
    return body;
  }

  async function downloadPdf() {
    var body = ready();
    if (!body) return;
    status(_("Building report…"));
    try {
      var res = await post("/api/report/pdf", body, $("statsReportPdf"));
      if (!res.ok) return status((await errorText(res)) || _("Could not build the report."), true);
      var blob = await res.blob();
      var match = /filename="([^"]+)"/.exec(res.headers.get("Content-Disposition") || "");
      var a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = match ? match[1] : "stats-report.pdf";
      document.body.appendChild(a);
      a.click();
      setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
      status(_("Report downloaded."));
    } catch (e) {
      status(_("Could not reach the Statistics service."), true);
    }
  }

  async function saveToFiles() {
    var body = ready();
    if (!body) return;
    status(_("Saving report to Files…"));
    try {
      var res = await post("/api/report/save", body, $("statsReportSave"));
      if (!res.ok) return status((await errorText(res)) || _("Could not save the report."), true);
      var out = await res.json();
      status(_("Saved to Files:") + " " + out.saved, false, { href: out.files_url || "/apps/files/", text: _("Open Files") });
    } catch (e) {
      status(_("Could not reach the Statistics service."), true);
    }
  }

  async function init() {
    var pdfBtn = $("statsReportPdf");
    if (!pdfBtn) return;
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
