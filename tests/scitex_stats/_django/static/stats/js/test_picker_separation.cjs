// Operator CCT4715: picker surfaces must never glue separate texts together.
// - The recommendation verdict kicker is an eyebrow ABOVE the test name,
//   not a run-on glued to it (stats-rec__kicker is block-level).
// - A disabled picker's hover tooltip separates multiple reasons (middle dot),
//   not a bare space that fuses two sentences.
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
const css = fs.readFileSync(path.join(leaf, "static/stats/css/stats.css"), "utf8");
const scripts = ["stx-mount.js", "plot.js", "app.js", "recommend.js", "report.js"]
  .map((name) => fs.readFileSync(path.join(leaf, "static/stats/js", name), "utf8")).join("\n");
const complete = "a,b\n1,10\n2,20\n3,30\n";
const recommendation = {
  primary: { test_id: "ttest_rel", label: "Synthetic paired", reason_item: { msg: "Synthetic primary.", args: [] } },
  applicability: [
    { test_id: "ttest_rel", label: "Synthetic paired", applicable: true, reason_items: [] },
    {
      test_id: "friedman", label: "Synthetic repeated", applicable: false,
      reason_items: [
        { msg: "First synthetic reason.", args: [], status: "fail" },
        { msg: "Second synthetic reason.", args: [], status: "fail" },
      ],
    },
  ],
  notes: [], decision_path: [], alternatives: [],
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
  // Shipped leaf stylesheet, so computed-style assertions pin the real CSS.
  const style = document.createElement("style");
  style.textContent = css;
  document.head.appendChild(style);
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
    },
  };
  await ui.prepared();
  return ui;
}

test("verdict kicker renders as an eyebrow above the test name, not glued to it", async (t) => {
  const ui = await page(t);
  const title = ui.document.querySelector("#statsRecCard .stats-rec__title");
  assert.ok(title, "verdict title rendered");
  const kicker = title.querySelector(":scope > .stats-rec__kicker");
  const label = title.querySelector(":scope > strong");
  assert.ok(kicker, "kicker element present");
  assert.ok(label, "label element present");
  assert.equal(kicker.textContent, "Recommended primary test");
  assert.equal(label.textContent, "Synthetic paired");
  assert.equal(ui.win.getComputedStyle(kicker).display, "block", "kicker breaks above the label");
});

test("disabled picker tooltip separates multiple reasons instead of fusing them", async (t) => {
  const ui = await page(t);
  const label = ui.document.querySelector('input[name="statsTest"][value="friedman"]').closest("label.stats-test");
  assert.ok(label, "friedman picker label present");
  assert.equal(
    label.getAttribute("title"),
    "First synthetic reason. · Second synthetic reason.",
    "reasons separated, not space-glued",
  );
});
