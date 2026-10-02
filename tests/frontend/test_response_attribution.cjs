// Actual shipped page scripts; every request and result is synthetic. No service/store.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const { JSDOM, VirtualConsole } = require("jsdom");
const leaf = process.env.STATS_TEST_LEAF || path.resolve(__dirname, "../../src/scitex_stats/_django");
const markup = fs.readFileSync(path.join(leaf, "templates/stats/stats.html"), "utf8")
  .replace(/\{% comment %\}[\s\S]*?\{% endcomment %\}/g, "")
  .replace(/\{%[\s\S]*?%\}/g, "").replace(/\{\{[\s\S]*?\}\}/g, "");
const scripts = ["stx-mount.js", "plot.js", "app.js", "recommend.js", "report.js"]
  .map((name) => fs.readFileSync(path.join(leaf, "static/stats/js", name), "utf8")).join("\n");
const complete = "a,b\n1,10\n2,20\n3,30\n";
const incompleteSameValues = "a,b\n1,10\n,\n2,20\n3,30\n";
const recommendation = {
  primary: { test_id: "ttest_rel", label: "Synthetic paired", reason_item: { msg: "Synthetic", args: [] } },
  applicability: [{ test_id: "ttest_rel", label: "Synthetic paired", applicable: true, reason_items: [] }],
  notes: [], decision_path: [], alternatives: [],
};
const result = (label) => ({ test_method: label, formatted: label, provenance: { synthetic: label } });
const runResult = (label) => ({ warning_item: { msg: label, args: [] }, results: [], agreement: { status: "ok", summary_item: { msg: label, args: [] } } });
const plotResult = (label) => ({ svg: `data:image/svg+xml,${label}`, png: `data:image/png,${label}`, plot_spec: { synthetic: label }, figrecipe: { available: false } });
function deferred() {
  let resolve, reject;
  const promise = new Promise((a, b) => { resolve = a; reject = b; });
  return { promise, resolve, reject };
}
function response(body, ok = true) {
  return { ok, status: ok ? 200 : 503, json: async () => body, blob: async () => new Blob(["synthetic"]),
    arrayBuffer: async () => new Uint8Array([1, 2]).buffer, headers: { get: () => "" } };
}
async function tick() { for (let i = 0; i < 3; i++) await new Promise((r) => setImmediate(r)); }
async function page(t) {
  const navigationAttempts = [];
  const virtualConsole = new VirtualConsole();
  virtualConsole.on("jsdomError", (error) => {
    if (/navigation/i.test(error.message)) navigationAttempts.push(error.message);
    else throw error;
  });
  const dom = new JSDOM(markup, { url: "https://example.invalid/apps/u/stats/", runScripts: "outside-only", virtualConsole });
  t.after(() => dom.window.close());
  const win = dom.window, document = win.document;
  document.querySelector('meta[name="stx-mount"]').content = "/apps/u/stats";
  document.querySelector("[data-stats-project]").setAttribute("data-stats-project", "synthetic-project");
  const requests = [], routes = new Map(), downloads = [], copies = [];
  win.confirm = () => true;
  win.URL.createObjectURL = () => "blob:synthetic";
  win.URL.revokeObjectURL = () => {};
  win.HTMLAnchorElement.prototype.click = function () { downloads.push({ href: this.href, download: this.download }); };
  document.execCommand = () => { copies.push(document.getElementById("statsJson").textContent); return true; };
  win.fetch = async (url, options = {}) => {
    const key = String(url), request = { url: key, options };
    requests.push(request);
    const route = [...routes.entries()].find(([suffix]) => key.endsWith(suffix));
    if (route) return route[1](request);
    if (key.includes("/api/project-import?")) return response({ name: "synthetic.csv", text: complete });
    if (key.endsWith("/api/recommend-test")) return response(recommendation);
    if (key.endsWith("/api/report/capabilities")) return response({ pdf: true, save_to_files: true });
    if (key.includes("/api/project-save?")) return response({ path: "synthetic/saved.json" });
    return response({ error: "synthetic unavailable" }, false);
  };
  Object.defineProperty(document, "readyState", { value: "complete" });
  win.eval(scripts);
  await tick();
  const ui = { dom, win, document, requests, downloads, copies, routes, navigationAttempts,
    el: (id) => document.getElementById(id),
    sent: (suffix) => requests.filter((r) => r.url.includes(suffix)),
    click(id) { this.el(id).dispatchEvent(new win.Event("click", { bubbles: true })); },
    change(id, value, event = true) { this.el(id).value = value; if (event) this.el(id).dispatchEvent(new win.Event("change", { bubbles: true })); },
    select(name, event = true) {
      const radio = document.querySelector(`input[name="statsTest"][value="${name}"]`);
      assert.ok(radio); radio.checked = true;
      if (event) radio.dispatchEvent(new win.Event("change", { bubbles: true }));
    },
    edit(event = true) {
      const area = document.querySelector(".stats-group__input"); area.value = "8 9 10";
      if (event) area.dispatchEvent(new win.Event("input", { bubbles: true }));
    },
    async file(text) {
      const file = new win.File([text], "synthetic.csv", { type: "text/csv" });
      const input = this.el("statsCsv");
      Object.defineProperty(input, "files", { configurable: true, value: [file] });
      const done = new Promise((resolve, reject) => {
        const read = win.FileReader.prototype.readAsText;
        win.FileReader.prototype.readAsText = function (...args) {
          win.FileReader.prototype.readAsText = read;
          this.addEventListener("load", resolve, { once: true });
          this.addEventListener("error", reject, { once: true });
          return read.apply(this, args);
        };
      });
      input.dispatchEvent(new win.Event("change")); await done; await tick();
    },
    async projectFile(text) {
      routes.set("/api/project-import?project=synthetic-project&name=synthetic.csv", () => response({ text, name: "synthetic.csv" }));
      const b = document.createElement("button"); b.className = "stats-project__import"; b.dataset.file = "synthetic.csv";
      this.el("statsProjectFiles").appendChild(b); b.click(); await tick();
    },
    async prepared() {
      await this.file(complete); this.change("statsDesign", "paired"); this.select("ttest_rel");
      this.click("statsRecommend"); await tick();
      assert.equal(this.el("statsRunAll").hidden, false);
    },
  };
  await ui.prepared();
  return ui;
}

const changes = {
  "input event": (ui) => ui.edit(),
  "silent input": (ui) => ui.edit(false),
  "same-values import/source generation": (ui) => ui.file(incompleteSameValues),
  "same-values complete reimport": (ui) => ui.file(complete),
  "project import": (ui) => ui.projectFile(incompleteSameValues),
  Clear: (ui) => ui.click("statsClear"),
  sample: (ui) => ui.click("statsSample"),
  "test change": (ui) => ui.select("wilcoxon"),
  "silent test change": (ui) => ui.select("wilcoxon", false),
  "design change": (ui) => ui.change("statsDesign", "independent"),
  "scale change": (ui) => ui.change("statsScale", "ordinal"),
  "alternative change": (ui) => ui.change("statsAlt", "less"),
  "population mean change": (ui) => ui.change("statsPopmean", "5"),
  "silent project change": (ui) => ui.document.querySelector("[data-stats-project]").setAttribute("data-stats-project", "other-project"),
  "silent raw formatting change": (ui) => { ui.document.querySelector(".stats-group__input").value += " "; },
  "silent correction method change": (ui) => ui.change("statsCorrMethod", "holm", false),
  "silent posthoc method change": (ui) => ui.change("statsPhMethod", "games_howell", false),
  "silent group label change": (ui) => { ui.document.querySelector(".stats-group__label span").textContent = "Different source group"; },
  "observed config ABA": (ui) => { ui.change("statsAlt", "less"); ui.change("statsAlt", "two-sided"); },
};

// Real template anchors and shipped scripts; availability/preventDefault are
// DOM observations, not a claim that JSDOM performs a native browser download.
const downloadActions = [
  ["ordinary click", "click", { button: 0 }],
  ["modifier click", "click", { button: 0, ctrlKey: true }],
  ["shift click", "click", { button: 0, shiftKey: true }],
  ["Enter", "keydown", { key: "Enter" }],
  ["middle auxclick", "auxclick", { button: 1 }],
  ["context menu", "contextmenu", { button: 2 }],
  ["touch pointerdown", "pointerdown", { pointerType: "touch" }],
  ["middle mousedown", "mousedown", { button: 1 }],
];
async function renderedDownload(t) {
  const ui = await page(t);
  ui.routes.set("/api/run", () => response(result("CURRENT_DOWNLOAD")));
  ui.routes.set("/api/plot", () => response(plotResult("CURRENT_DOWNLOAD")));
  ui.click("statsCalculate"); await tick();
  assert.ok(ui.el("statsPlotSvg").getAttribute("href"));
  return ui;
}
function activateDownload(ui, id, type, options) {
  const Event = type === "keydown" ? ui.win.KeyboardEvent : ui.win.MouseEvent;
  const event = new Event(type, { ...options, bubbles: true, cancelable: true });
  if (type === "pointerdown") Object.defineProperty(event, "pointerType", { value: options.pointerType });
  ui.el(id).dispatchEvent(event);
  return event;
}
for (const id of ["statsPlotSvg", "statsPlotPng"]) {
  for (const [action, type, options] of downloadActions) {
    test(`${id} permits current ${action} and preserves its rendered href`, async (t) => {
      // Arrange
      const ui = await renderedDownload(t), href = ui.el(id).getAttribute("href");
      // Act
      const event = activateDownload(ui, id, type, options);
      // Assert
      assert.deepEqual([event.defaultPrevented, ui.el(id).hidden, ui.el(id).getAttribute("href")], [false, false, href]);
    });
    test(`${id} blocks ${action} after silent changed raw input`, async (t) => {
      // Arrange
      const ui = await renderedDownload(t); ui.edit(false);
      // Act
      const event = activateDownload(ui, id, type, options);
      // Assert
      assert.deepEqual([event.defaultPrevented, ...["statsPlotSvg", "statsPlotPng"].map((link) => [ui.el(link).hidden, ui.el(link).getAttribute("href")])], [true, [true, null], [true, null]]);
    });
  }
  for (const change of ["silent project change", "alternative change"]) {
    test(`${id} blocks ordinary activation after ${change}`, async (t) => {
      // Arrange
      const ui = await renderedDownload(t);
      if (change === "alternative change") ui.change("statsAlt", "less", false);
      else await changes[change](ui);
      // Act
      const event = activateDownload(ui, id, "click", { button: 0 });
      // Assert
      assert.deepEqual([event.defaultPrevented, ui.el(id).getAttribute("href")], [true, null]);
    });
  }
  test(`${id} cannot relabel an old link as a newer same-context drawing request`, async (t) => {
    // Arrange
    const ui = await renderedDownload(t), pending = deferred();
    ui.routes.set("/api/plot", () => pending.promise);
    ui.click("statsCalculate"); await tick();
    // Act
    const event = activateDownload(ui, id, "click", { button: 0 });
    // Assert
    assert.deepEqual([event.defaultPrevented, ui.el(id).getAttribute("href")], [true, null]);
  });
  test(`${id} rejects a href that differs from the exact rendered output`, async (t) => {
    // Arrange
    const ui = await renderedDownload(t); ui.el(id).href = "data:image/svg+xml,UNOWNED_OUTPUT";
    // Act
    const event = activateDownload(ui, id, "click", { button: 0 });
    // Assert
    assert.deepEqual([event.defaultPrevented, ui.el(id).getAttribute("href")], [true, null]);
  });
  test(`${id} rejects a superseded Calculate owner before its successor responds`, async (t) => {
    // Arrange
    const ui = await renderedDownload(t), pending = deferred();
    ui.routes.set("/api/run", () => pending.promise); ui.click("statsCalculate"); await tick();
    // Act
    const event = activateDownload(ui, id, "click", { button: 0 });
    // Assert
    assert.deepEqual([event.defaultPrevented, ui.el(id).getAttribute("href")], [true, null]);
  });
  test(`${id} fails closed if its application owner check is unavailable`, async (t) => {
    // Arrange
    const ui = await renderedDownload(t); ui.win.stxStatsApp.requestCurrent = undefined;
    // Act
    const event = activateDownload(ui, id, "click", { button: 0 });
    // Assert
    assert.deepEqual([event.defaultPrevented, ui.el(id).getAttribute("href")], [true, null]);
  });
  for (const unavailable of ["not callable", "throws", "unknown", "source fields removed"]) {
    test(`${id} prevents default download when ownership ${unavailable}`, async (t) => {
      // Arrange
      const ui = await renderedDownload(t);
      if (unavailable === "not callable") ui.win.stxStatsApp.requestCurrent = "unknown";
      else if (unavailable === "throws") ui.win.stxStatsApp.requestCurrent = () => { throw new Error("unknown owner"); };
      else if (unavailable === "unknown") ui.win.stxStatsApp.requestCurrent = () => "unknown";
      else ui.el("statsGroups").remove();
      // Act
      const event = activateDownload(ui, id, "click", { button: 0 });
      // Assert
      assert.deepEqual([event.defaultPrevented, ui.el(id).getAttribute("href"), ui.el(id).hidden], [true, null, true]);
    });
  }
  test(`${id} permits the fresh replacement after an old download was blocked`, async (t) => {
    // Arrange
    const ui = await renderedDownload(t); ui.edit(false);
    activateDownload(ui, id, "click", { button: 0 });
    await ui.file(complete);
    ui.click("statsCalculate"); await tick();
    // Act
    const event = activateDownload(ui, id, "click", { button: 0 });
    // Assert
    assert.deepEqual([event.defaultPrevented, ui.el(id).hidden, ui.el(id).getAttribute("href")?.includes("CURRENT_DOWNLOAD")], [false, false, true]);
  });
}

for (const [lane, button, route, sink, body] of [
  ["Calculate", "statsCalculate", "/api/run", "statsJson", result],
  ["Run all", "statsRunAll", "/api/run-all", "statsRunAllOut", runResult],
]) {
  for (const [name, change] of Object.entries(changes)) {
    test(`${lane} discards late success after ${name}`, async (t) => {
      const ui = await page(t), pending = deferred();
      ui.routes.set(route, () => pending.promise);
      ui.click(button); await tick(); assert.equal(ui.sent(route).length, 1);
      await change(ui); pending.resolve(response(body("OLD_SYNTHETIC_RESULT"))); await tick();
      assert.equal(ui.el(sink).textContent, "", "old result must never repopulate the current sink");
      if (lane === "Calculate") assert.equal(ui.el("statsResult").hidden, true);
      else assert.equal(ui.el(sink).hidden, true);
    });
  }
  for (const failure of ["http", "network"]) {
    test(`${lane} discards late ${failure} error after edit`, async (t) => {
      const ui = await page(t), pending = deferred(); ui.routes.set(route, () => pending.promise);
      ui.click(button); await tick(); ui.edit();
      if (failure === "http") pending.resolve(response({ error: "OLD_ERROR" }, false));
      else pending.reject(new Error("synthetic failure"));
      await tick(); assert.equal(ui.el(lane === "Calculate" ? "statsError" : sink).textContent, "");
    });
  }
  test(`${lane} accepts unchanged response`, async (t) => {
    const ui = await page(t); ui.routes.set(route, () => response(body("CURRENT_SYNTHETIC_RESULT")));
    ui.click(button); await tick(); assert.match(ui.el(sink).textContent, /CURRENT_SYNTHETIC_RESULT/);
  });
  test(`${lane} discards stale deferred JSON body`, async (t) => {
    const ui = await page(t), pending = deferred(), res = response({});
    res.json = () => pending.promise; ui.routes.set(route, () => res);
    ui.click(button); await tick(); ui.change("statsAlt", "greater");
    pending.resolve(body("OLD_BODY")); await tick(); assert.equal(ui.el(sink).textContent, "");
    assert.equal(ui.el(button).disabled, false, "context invalidation must not leave the sole request busy");
  });
  test(`${lane} competing requests retain newest response and busy ownership`, async (t) => {
    const ui = await page(t), first = deferred(), second = deferred(); let count = 0;
    ui.routes.set(route, () => (++count === 1 ? first : second).promise);
    ui.click(button); ui.click(button); await tick(); assert.equal(count, 2);
    first.resolve(response(body("OLD_RESULT"))); await tick();
    assert.equal(ui.el(button).disabled, true, "older request cannot release newer busy controls");
    assert.equal(ui.el(sink).textContent, "");
    second.resolve(response(body("NEW_RESULT"))); await tick(); assert.match(ui.el(sink).textContent, /NEW_RESULT/);
    assert.equal(ui.el(button).disabled, false);
  });
  test(`${lane} late older error cannot replace newest success`, async (t) => {
    const ui = await page(t), first = deferred(), second = deferred(); let count = 0;
    ui.routes.set(route, () => (++count === 1 ? first : second).promise);
    ui.click(button); ui.click(button); await tick(); second.resolve(response(body("NEW_RESULT"))); await tick();
    first.resolve(response({ error: "OLD_ERROR" }, false)); await tick();
    assert.match(ui.el(sink).textContent, /NEW_RESULT/);
    if (lane === "Calculate") assert.equal(ui.el("statsError").textContent, "");
  });
}

for (const action of ["statsSaveResults", "statsSaveProvenance", "statsCopy"]) {
  for (const silent of [false, true]) {
    test(`${action} refuses rendered old result after ${silent ? "silent" : "observed"} edit`, async (t) => {
      const ui = await page(t); ui.routes.set("/api/run", () => response(result("OLD_RESULT")));
      ui.click("statsCalculate"); await tick(); assert.match(ui.el("statsJson").textContent, /OLD_RESULT/);
      ui.edit(!silent); ui.click(action); await tick();
      assert.equal(ui.sent("/api/project-save?").length, 0); assert.equal(ui.copies.length, 0);
      assert.equal(ui.el("statsJson").textContent, "");
    });
  }
}

for (const action of ["statsReportPdf", "statsReportSave"]) {
  const route = action === "statsReportPdf" ? "/api/report/pdf" : "/api/report/save";
  for (const stage of ["fetch", "body"]) {
    test(`${action} discards stale ${stage} response without download/saved link`, async (t) => {
      const ui = await page(t), pending = deferred();
      const res = response({ saved: "OLD_REPORT", files_url: "/old-files/" });
      if (stage === "body") res[action === "statsReportPdf" ? "blob" : "json"] = () => pending.promise;
      ui.routes.set(route, () => stage === "fetch" ? pending.promise : res);
      ui.click(action); await tick(); ui.edit();
      pending.resolve(stage === "fetch" ? res : action === "statsReportPdf" ? new Blob(["old"]) : { saved: "OLD_REPORT", files_url: "/old-files/" });
      await tick(); assert.equal(ui.downloads.length, 0); assert.equal(ui.el("statsReportStatus").textContent, "");
      assert.equal(ui.el("statsReportStatus").querySelector("a"), null);
    });
  }
  test(`${action} accepts unchanged response`, async (t) => {
    const ui = await page(t); ui.routes.set(route, () => response({ saved: "CURRENT_REPORT", files_url: "/current-files/" }));
    ui.click(action); await tick();
    if (action === "statsReportPdf") assert.equal(ui.downloads.length, 1);
    else assert.match(ui.el("statsReportStatus").textContent, /CURRENT_REPORT/);
  });
  for (const [failure, stage] of [["http", "fetch"], ["http", "body"], ["network", "fetch"]]) {
    test(`${action} discards late ${failure}/${stage} error and releases controls`, async (t) => {
      const ui = await page(t), pending = deferred(), res = response({ error: "OLD_REPORT_ERROR" }, false);
      if (stage === "body") res.json = () => pending.promise;
      ui.routes.set(route, () => stage === "fetch" ? pending.promise : res);
      ui.click(action); await tick(); ui.change("statsPhMethod", "games_howell");
      if (failure === "network") pending.reject(new Error("synthetic failure"));
      else pending.resolve(stage === "body" ? { error: "OLD_REPORT_ERROR" } : res);
      await tick(); assert.equal(ui.el("statsReportStatus").textContent, "");
      assert.equal(ui.el("statsReportPdf").disabled, false); assert.equal(ui.el("statsReportSave").disabled, false);
    });
  }
  test(`${action} competing requests keep newest response and busy controls`, async (t) => {
    const ui = await page(t), first = deferred(), second = deferred(); let count = 0;
    ui.routes.set(route, () => (++count === 1 ? first : second).promise);
    ui.click(action); ui.click(action); await tick();
    first.resolve(response({ saved: "OLD_REPORT" })); await tick();
    assert.equal(ui.el(action).disabled, true); assert.equal(ui.downloads.length, 0);
    assert.doesNotMatch(ui.el("statsReportStatus").textContent, /OLD_REPORT/);
    second.resolve(response({ saved: "NEW_REPORT" })); await tick(); assert.equal(ui.el(action).disabled, false);
    if (action === "statsReportPdf") assert.equal(ui.downloads.length, 1);
    else assert.match(ui.el("statsReportStatus").textContent, /NEW_REPORT/);
  });
}

for (const [button, route, sink, option, body] of [
  ["statsCorrect", "/api/correct", "statsCorrOut", "statsCorrMethod", { results: [{ p_apa: "OLD", p_adjusted_apa: "OLD", rejected: false }] }],
  ["statsPosthoc", "/api/posthoc", "statsPhOut", "statsPhMethod", { comparisons: [{ group_i: "OLD", group_j: "OLD", p_apa: "OLD" }] }],
]) {
  for (const failure of [false, true]) {
    test(`${button} discards stale ${failure ? "error" : "success"} after method change`, async (t) => {
      const ui = await page(t), pending = deferred(); ui.change("statsCorrP", "0.01 0.2");
      ui.routes.set(route, () => pending.promise); ui.click(button); await tick(); assert.equal(ui.sent(route).length, 1);
      ui.change(option, option === "statsCorrMethod" ? "holm" : "games_howell");
      if (failure) pending.reject(new Error("synthetic")); else pending.resolve(response(body));
      await tick(); assert.equal(ui.el(sink).textContent, "");
    });
  }
}

for (const action of ["statsSaveResults", "statsSaveProvenance", "statsSaveConfig"]) {
  for (const failure of [false, true]) {
    test(`${action} suppresses delayed ${failure ? "error" : "acknowledgement"} after project change`, async (t) => {
      const ui = await page(t), pending = deferred(); ui.routes.set("/api/run", () => response(result("CURRENT_RESULT")));
      ui.click("statsCalculate"); await tick();
      ui.routes.set("/api/project-save?project=synthetic-project", () => pending.promise);
      ui.click(action); await tick(); assert.equal(ui.sent("/api/project-save?").length, 1, "valid source save was already dispatched");
      ui.document.querySelector("[data-stats-project]").setAttribute("data-stats-project", "other-project");
      if (failure) pending.reject(new Error("synthetic")); else pending.resolve(response({ path: "OLD_PATH" }));
      await tick(); assert.equal(ui.el("statsSaveStatus").textContent, "");
      assert.equal(ui.sent("/api/project-save?").length, 1, "no replacement write is issued");
    });
  }
}

test("copy fallback cannot copy old output after deferred clipboard failure and edit", async (t) => {
  const ui = await page(t), pending = deferred();
  Object.defineProperty(ui.win, "isSecureContext", { value: true });
  ui.win.ClipboardItem = class { constructor(value) { this.value = value; } };
  Object.defineProperty(ui.win.navigator, "clipboard", { value: { write: () => pending.promise } });
  ui.routes.set("/api/run", () => response(result("OLD_RESULT"))); ui.click("statsCalculate"); await tick();
  ui.click("statsCopy"); await tick(); ui.edit(); pending.reject(new Error("synthetic clipboard failure")); await tick();
  assert.equal(ui.copies.length, 0); assert.equal(ui.el("statsCopyStatus").textContent, "");
});

test("late plot response cannot create savable old plot after edit", async (t) => {
  const ui = await page(t), pending = deferred();
  ui.routes.set("/api/run", () => response(result("OLD_RESULT")));
  ui.routes.set("/api/plot", () => pending.promise);
  ui.click("statsCalculate"); await tick(); assert.equal(ui.sent("/api/plot").length, 1);
  ui.edit(); pending.resolve(response(plotResult("OLD_PLOT"))); await tick();
  assert.equal(ui.el("statsPlotImg").hidden, true); assert.equal(ui.win.stxStatsPlot.spec(), null);
  ui.click("statsSavePlot"); await tick(); assert.equal(ui.sent("/api/project-save?").length, 0);
});

test("competing plots discard older success without replacing newer spec", async (t) => {
  const ui = await page(t), first = deferred(), second = deferred(); let count = 0;
  ui.routes.set("/api/plot", () => (++count === 1 ? first : second).promise);
  ui.win.stxStatsPlot.draw({ groups: [[1], [2]] }); ui.win.stxStatsPlot.draw({ groups: [[1], [2]] }); await tick();
  second.resolve(response(plotResult("NEW_PLOT"))); await tick(); first.resolve(response(plotResult("OLD_PLOT"))); await tick();
  assert.equal(ui.win.stxStatsPlot.spec().synthetic, "NEW_PLOT"); assert.match(ui.el("statsPlotImg").src, /NEW_PLOT/);
});

for (const failure of [false, true]) {
  test(`FigRecipe old plot ${failure ? "error" : "success"} cannot affect newer same-context plot`, async (t) => {
    const ui = await page(t), pending = deferred(); let count = 0;
    ui.routes.set("/api/run", () => response(result("CURRENT_RESULT")));
    ui.routes.set("/api/plot", () => response({ ...plotResult(++count === 1 ? "PLOT_A" : "PLOT_B"),
      figrecipe: { available: true, import_url: "/synthetic-figrecipe-import", open_url: "/synthetic-figrecipe-open" } }));
    ui.routes.set("/synthetic-figrecipe-import", () => pending.promise);
    ui.click("statsCalculate"); await tick(); assert.equal(ui.win.stxStatsPlot.spec().synthetic, "PLOT_A");
    ui.click("statsOpenFigrecipe"); await tick();
    assert.equal(JSON.parse(ui.sent("synthetic-figrecipe-import")[0].options.body).spec.synthetic, "PLOT_A");
    ui.click("statsCalculate"); await tick(); assert.equal(ui.win.stxStatsPlot.spec().synthetic, "PLOT_B");
    if (failure) pending.reject(new Error("synthetic old import failure"));
    else pending.resolve(response({ recipe_path: "old-plot-a.yaml" }));
    await tick(); assert.equal(ui.navigationAttempts.length, 0, "old import cannot navigate using a newer plot's ownership");
    assert.equal(ui.el("statsPlotStatus").textContent, "", "old error cannot replace newer plot status");
    assert.equal(ui.el("statsOpenFigrecipe").disabled, false);
  });
}

test("FigRecipe unchanged current plot import can navigate", async (t) => {
  const ui = await page(t);
  ui.routes.set("/api/run", () => response(result("CURRENT_RESULT")));
  ui.routes.set("/api/plot", () => response({ ...plotResult("CURRENT_PLOT"),
    figrecipe: { available: true, import_url: "/synthetic-figrecipe-import", open_url: "/synthetic-figrecipe-open" } }));
  ui.routes.set("/synthetic-figrecipe-import", () => response({ recipe_path: "current.yaml" }));
  ui.click("statsCalculate"); await tick(); ui.click("statsOpenFigrecipe"); await tick();
  assert.equal(ui.navigationAttempts.length, 1, "JSDOM observes the actual current navigation attempt");
});

test("old image save cannot fall back to a newer plot after data/context replacement", async (t) => {
  const ui = await page(t), pending = deferred();
  ui.routes.set("/api/run", () => response(result("OLD_RESULT"))); ui.routes.set("/api/plot", () => response(plotResult("OLD_PLOT")));
  ui.click("statsCalculate"); await tick();
  ui.routes.set("data:image/png,OLD_PLOT", () => pending.promise); ui.click("statsSavePlot"); await tick();
  await ui.file(complete);
  ui.routes.set("/api/run", () => response(result("NEW_RESULT"))); ui.routes.set("/api/plot", () => response(plotResult("NEW_PLOT")));
  ui.click("statsCalculate"); await tick(); assert.equal(ui.win.stxStatsPlot.spec().synthetic, "NEW_PLOT");
  pending.resolve(response({})); await tick(); assert.equal(ui.sent("/api/project-save?").length, 0);
});

test("newer Save plot request prevents older image await dispatch", async (t) => {
  const ui = await page(t), first = deferred(), second = deferred(); let count = 0;
  ui.routes.set("/api/run", () => response(result("CURRENT_RESULT"))); ui.routes.set("/api/plot", () => response(plotResult("CURRENT_PLOT")));
  ui.click("statsCalculate"); await tick();
  ui.routes.set("data:image/png,CURRENT_PLOT", () => (++count === 1 ? first : second).promise);
  ui.click("statsSavePlot"); ui.click("statsSavePlot"); await tick();
  second.resolve(response({})); await tick(); assert.equal(ui.sent("/api/project-save?").length, 1);
  first.resolve(response({})); await tick(); assert.equal(ui.sent("/api/project-save?").length, 1);
});

for (const stage of ["fetch", "body"]) {
  test(`Save plot refuses old bytes after ${stage} await and project change`, async (t) => {
    const ui = await page(t), pending = deferred();
    ui.routes.set("/api/run", () => response(result("CURRENT_RESULT")));
    ui.routes.set("/api/plot", () => response(plotResult("CURRENT_PLOT")));
    ui.click("statsCalculate"); await tick(); assert.equal(ui.el("statsPlotPng").hidden, false);
    const res = response({}); if (stage === "body") res.arrayBuffer = () => pending.promise;
    ui.routes.set("data:image/png,CURRENT_PLOT", () => stage === "fetch" ? pending.promise : res);
    ui.click("statsSavePlot"); await tick();
    ui.document.querySelector("[data-stats-project]").setAttribute("data-stats-project", "other-project");
    pending.resolve(stage === "fetch" ? res : new Uint8Array([1, 2]).buffer); await tick();
    assert.equal(ui.sent("/api/project-save?").length, 0, "old image cannot be assigned to changed project");
  });
}
