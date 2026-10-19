// Operator layout rule CCT: results-pane minutiae (assumption checks,
// sensitivity output) render inside collapsible <details>, open by default.
// Actual shipped page scripts; every request and result is synthetic. No service/store.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const { JSDOM, VirtualConsole } = require("jsdom");
const leaf = process.env.STATS_TEST_LEAF || path.resolve(__dirname, "../../../../../../src/scitex_stats/_django");
const markup = fs.readFileSync(path.join(leaf, "templates/stats/stats.html"), "utf8")
  .replace(/\{% comment %\}[\s\S]*?\{% endcomment %\}/g, "")
  .replace(/\{%[\s\S]*?%\}/g, "").replace(/\{\{[\s\S]*?\}\}/g, "");
const scripts = ["stx-mount.js", "plot.js", "app.js", "recommend.js", "report.js"]
  .map((name) => fs.readFileSync(path.join(leaf, "static/stats/js", name), "utf8")).join("\n");
const complete = "a,b\n1,10\n2,20\n3,30\n";
const recommendation = {
  primary: { test_id: "ttest_rel", label: "Synthetic paired", reason_item: { msg: "Synthetic", args: [] } },
  applicability: [{ test_id: "ttest_rel", label: "Synthetic paired", applicable: true, reason_items: [] }],
  notes: [], decision_path: [], alternatives: [],
  assumption_checks: {
    rows: [{
      check: "Normality", sample: "Differences", symbol: "W", df: [],
      statistic_apa: "0.98", p_apa: "= .591", n: 3,
      threshold: { msg: "Reject when p < .05.", args: [] }, decision: "not rejected",
    }],
    notes: [{ msg: "Synthetic check note.", args: [] }],
    qq: [{ theoretical: [-1, 0, 1], observed: [1, 2, 3], line: { slope: 1, intercept: 2 }, sample: "Differences" }],
  },
};
const runAllBody = {
  warning_item: { msg: "Synthetic sensitivity warning.", args: [] },
  results: [{ role: "primary", label: "Synthetic paired", stat_symbol: "t", statistic: 1.5, df: [2], p_apa: "= .272" }],
  agreement: { status: "ok", summary_item: { msg: "Synthetic agreement.", args: [] } },
};
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
    if (key.endsWith("/api/run-all")) return response(runAllBody);
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
    async prepared() {
      // No buttons: input re-derives the recommendation (debounced 500ms),
      // so wait past the debounce instead of clicking a removed button.
      await this.file(complete); this.change("statsDesign", "paired"); this.select("ttest_rel");
      await new Promise((r) => setTimeout(r, 800)); await tick();
      assert.ok(this.sent("recommend-test").length >= 1, "recommendation derived after input");
      assert.equal(this.el("statsRunAll").hidden, false);
    },
  };
  await ui.prepared();
  return ui;
}

test("assumption checks render inside an open collapsible details", async (t) => {
  const ui = await page(t);
  const box = ui.el("statsAssumptions");
  const acc = box.querySelector(":scope > details.stx-acc.stats-acc");
  assert.ok(acc, "assumptions wrapped in details.stx-acc");
  assert.equal(acc.open, true, "open by default (current visibility preserved)");
  assert.equal(acc.querySelector(":scope > summary").textContent, "Assumption checks");
  assert.ok(acc.querySelector(":scope > .stx-acc__body table.stats-applic--checks"), "checks table inside body");
  assert.ok(acc.querySelector(":scope > .stx-acc__body .stats-qq-grid"), "Q-Q plots inside body");
  assert.equal(box.querySelectorAll("table").length, 1, "no duplicate unwrapped table");
});

test("sensitivity output renders inside an open collapsible details", async (t) => {
  const ui = await page(t);
  ui.click("statsRunAll"); await tick();
  const out = ui.el("statsRunAllOut");
  assert.equal(out.hidden, false);
  const acc = out.querySelector(":scope > details.stx-acc.stats-acc");
  assert.ok(acc, "sensitivity output wrapped in details.stx-acc");
  assert.equal(acc.open, true, "open by default (current visibility preserved)");
  assert.equal(acc.querySelector(":scope > summary").textContent, "Sensitivity analyses");
  assert.ok(acc.querySelector(":scope > .stx-acc__body table.stats-applic--results"), "results table inside body");
  assert.ok(acc.querySelector(":scope > .stx-acc__body .stats-warning"), "warning inside body");
  assert.ok(acc.querySelector(":scope > .stx-acc__body .stats-agreement"), "agreement inside body");
});

test("assumption details collapse without losing content", async (t) => {
  const ui = await page(t);
  const acc = ui.el("statsAssumptions").querySelector(":scope > details");
  assert.ok(acc);
  acc.open = false;
  assert.ok(acc.querySelector("table.stats-applic--checks"), "content retained while collapsed");
});
