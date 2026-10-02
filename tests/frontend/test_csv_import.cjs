// Synthetic DOM tests of the shipped leaf scripts. No Django/server/store.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const { JSDOM } = require("jsdom");

const leaf = path.resolve(__dirname, "../../src/scitex_stats/_django");
const markup = fs.readFileSync(path.join(leaf, "templates/stats/stats.html"), "utf8")
  .replace(/\{% comment %\}[\s\S]*?\{% endcomment %\}/g, "")
  .replace(/\{%[\s\S]*?%\}/g, "")
  .replace(/\{\{[\s\S]*?\}\}/g, "");
const scripts = ["stx-mount.js", "app.js", "recommend.js", "report.js"].map((name) =>
  fs.readFileSync(path.join(leaf, "static/stats/js", name), "utf8")
).join("\n");

async function page(t, { prefix = "", project = "", recommendation = null } = {}) {
  const dom = new JSDOM(markup, {
    url: `https://example.invalid${prefix}/`,
    runScripts: "outside-only",
  });
  t.after(() => dom.window.close());
  const { document } = dom.window;
  document.querySelector('meta[name="stx-mount"]').content = prefix;
  document.querySelector("[data-stats-project]").setAttribute("data-stats-project", project);
  let imported;
  let fileRead;
  const readAsText = dom.window.FileReader.prototype.readAsText;
  dom.window.FileReader.prototype.readAsText = function (...args) {
    fileRead = new Promise((resolve, reject) => {
      this.addEventListener("load", resolve, { once: true });
      this.addEventListener("error", () => reject(this.error), { once: true });
    });
    return readAsText.apply(this, args);
  };
  const requests = [];
  dom.window.fetch = async (url, options = {}) => {
    requests.push({ url: String(url), options });
    if (String(url).startsWith(`${prefix}/api/project-import?`)) {
      return { ok: true, status: 200, json: async () => imported };
    }
    if (String(url) === `${prefix}/api/report/capabilities`) {
      return { ok: true, status: 200, json: async () => ({ pdf: true, save_to_files: true }) };
    }
    if (String(url) === `${prefix}/api/recommend-test` && recommendation) {
      const body = typeof recommendation === "function" ? await recommendation() : recommendation;
      return { ok: true, status: 200, json: async () => body };
    }
    return { ok: false, status: 503, json: async () => ({ error: "synthetic service unavailable" }) };
  };
  // Exercise the actual startup and click handlers, including the mount script.
  Object.defineProperty(document, "readyState", { value: "complete" });
  dom.window.eval(scripts);
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(document.querySelector("[data-stats-ready]").dataset.statsReady, "1");
  return {
    dom,
    document,
    requests,
    groups: () => [...document.querySelectorAll(".stats-group__input")].map((el) => el.value),
    counts: () => [...document.querySelectorAll(".stats-group__count")].map((el) => el.textContent),
    async file(text, name = "synthetic.csv") {
      const input = document.getElementById("statsCsv");
      const file = new dom.window.File([text], name, { type: "text/csv" });
      Object.defineProperty(input, "files", { configurable: true, value: [file] });
      input.dispatchEvent(new dom.window.Event("change"));
      assert.ok(fileRead, "file picker invoked the actual FileReader");
      await fileRead;
    },
    async projectFile(text, name = "synthetic.csv") {
      imported = { text, name };
      const button = document.createElement("button");
      button.className = "stats-project__import";
      button.setAttribute("data-file", name);
      document.getElementById("statsProjectFiles").appendChild(button);
      button.click();
      await new Promise((resolve) => setImmediate(resolve));
    },
  };
}

for (const prefix of ["", "/apps/u/stats"]) {
  test(`CSV blanks stay absent in visible data and request payload (${prefix || "standalone"})`, async (t) => {
    const ui = await page(t, { prefix });
    await ui.file("a,b\n1,10\n,20\n3,\n0,40\n");
    assert.deepEqual(ui.groups(), ["1 3 0", "10 20 40"]);
    assert.deepEqual(ui.counts(), ["n = 3", "n = 3"]);
    ui.document.getElementById("statsCalculate").click();
    await new Promise((resolve) => setImmediate(resolve));
    const request = ui.requests.find((r) => r.url === `${prefix}/api/run`);
    assert.ok(request, "calculation used the declared mount prefix");
    const payload = JSON.parse(request.options.body);
    assert.equal(payload.test_name, "ttest_ind");
    assert.deepEqual(payload.data, [1, 3, 0]);
    assert.deepEqual(payload.data2, [10, 20, 40]);
  });
}

test("TSV whitespace and ragged rows never insert zero", async (t) => {
  const ui = await page(t);
  await ui.file("a\tb\n-2\t0\n \t2.5\n3\n1e2\t \n", "synthetic.tsv");
  assert.deepEqual(ui.groups(), ["-2 3 100", "0 2.5"]);
  assert.deepEqual(ui.counts(), ["n = 3", "n = 2"]);
});

test("a column containing only missing values does not become an observed group", async (t) => {
  const ui = await page(t);
  await ui.file("a,missing,b\n1,,10\n2, ,20\n");
  assert.deepEqual(ui.groups(), ["1 2", "10 20"]);
});

test("empty input preserves existing values and shows an error", async (t) => {
  const ui = await page(t);
  await ui.file("a,b\n0,-1\n2,3\n");
  const before = ui.groups();
  await ui.file("a,b\n,\n , \n");
  assert.deepEqual(ui.groups(), before);
  assert.equal(ui.document.getElementById("statsError").textContent, "No numeric columns found in this file.");
  assert.equal(ui.document.getElementById("statsError").hidden, false);
});

test("project import uses the same parser and declared route", async (t) => {
  const prefix = "/apps/u/stats";
  const ui = await page(t, { prefix, project: "synthetic-project" });
  await ui.projectFile("a,b\n1,\n,2\n0,0\n");
  assert.deepEqual(ui.groups(), ["1 0", "2 0"]);
  assert.ok(ui.requests.some((r) => r.url.startsWith(`${prefix}/api/project-import?project=synthetic-project&`)));
  assert.equal(ui.document.querySelector("[data-stats-app]").dataset.statsMode, "project");
});

const rowDependent = ["ttest_rel", "wilcoxon", "pearson", "spearman", "kendall", "friedman"];
const incomplete = "a,b,c\n1,10,100\n,20,200\n3,,300\n0,40,\n";
const complete = "a,b,c\n1,10,100\n2,20,200\n0,40,400\n";
const tick = () => new Promise((resolve) => setImmediate(resolve));

function select(ui, name) {
  const radio = ui.document.querySelector(`input[name="statsTest"][value="${name}"]`);
  assert.ok(radio, `${name} is an available UI test`);
  radio.checked = true;
  radio.dispatchEvent(new ui.dom.window.Event("change"));
}

async function calculate(ui, name) {
  select(ui, name);
  ui.document.getElementById("statsCalculate").click();
  await tick();
}

function runs(ui) {
  return ui.requests.filter((request) => request.url.endsWith("/api/run"));
}

function assertRefused(ui) {
  assert.equal(runs(ui).length, 0, "unsafe input never reaches the calculation API");
  const error = ui.document.getElementById("statsError");
  assert.equal(error.hidden, false);
  assert.match(error.textContent, /source rows|row alignment/i);
}

for (const name of rowDependent) {
  test(`${name} refuses equal-length columns compacted from different source rows`, async (t) => {
    const ui = await page(t);
    await ui.file(incomplete);
    assert.deepEqual(ui.groups(), ["1 3 0", "10 20 40", "100 200 300"]);
    await calculate(ui, name);
    assertRefused(ui);
  });

  test(`${name} accepts unchanged complete numeric source rows`, async (t) => {
    const ui = await page(t);
    await ui.file(complete);
    await calculate(ui, name);
    assert.equal(runs(ui).length, 1);
    assert.equal(JSON.parse(runs(ui)[0].options.body).test_name, name);
  });
}

for (const [reason, text] of [
  ["same missing-row pattern", "a,b\n1,10\n,\n3,30\n"],
  ["invalid cell", "a,b\n1,10\ninvalid,20\n3,30\n"],
  ["ragged row", "a,b\n1,10\n2\n3,30\n"],
  ["entire blank interior row", "a,b\n1,10\n\n3,30\n"],
  ["all-missing column", "a,missing,b\n1,,10\n2,,20\n"],
]) {
  test(`Pearson refuses ${reason} without choosing an omission policy`, async (t) => {
    const ui = await page(t);
    await ui.file(text);
    await calculate(ui, "pearson");
    assertRefused(ui);
  });
}

test("changing test after an independent request does not erase import uncertainty", async (t) => {
  const ui = await page(t);
  await ui.file(incomplete);
  await calculate(ui, "ttest_ind");
  assert.equal(runs(ui).length, 1);
  await calculate(ui, "ttest_rel");
  assert.equal(runs(ui).length, 1, "test switch must not send a second request");
  assert.match(ui.document.getElementById("statsError").textContent, /source rows|row alignment/i);
});

for (const edit of ["input event", "unannounced restored values", "add group", "remove group"]) {
  test(`${edit} makes complete imported row alignment uncertain`, async (t) => {
    const ui = await page(t);
    await ui.file(complete);
    const first = ui.document.querySelector(".stats-group__input");
    if (edit === "input event" || edit === "unannounced restored values") {
      first.value = "8 9 10";
      if (edit === "input event") first.dispatchEvent(new ui.dom.window.Event("input"));
    } else if (edit === "add group") {
      ui.document.getElementById("statsAddGroup").click();
    } else {
      [...ui.document.querySelectorAll(".stats-group__remove")].at(-1).click();
    }
    await calculate(ui, "pearson");
    assertRefused(ui);
  });
}

test("an unsuccessful import preserves the previous uncertainty", async (t) => {
  const ui = await page(t);
  await ui.file(incomplete);
  await ui.file("a,b\n,\n");
  await calculate(ui, "ttest_rel");
  assertRefused(ui);
});

test("cancelled sample replacement preserves uncertainty; accepted replacement resets it", async (t) => {
  const ui = await page(t);
  await ui.file(incomplete);
  ui.dom.window.confirm = () => false;
  ui.document.getElementById("statsSample").click();
  await calculate(ui, "pearson");
  assertRefused(ui);
  ui.dom.window.confirm = () => true;
  ui.document.getElementById("statsSample").click();
  await calculate(ui, "pearson");
  assert.equal(runs(ui).length, 1, "replacement sample is new input, not retained imported data");
});

test("a new complete import replaces uncertain input", async (t) => {
  const ui = await page(t);
  await ui.file(incomplete);
  await ui.file("1,10\n2,20\n0,40\n");
  await calculate(ui, "ttest_rel");
  assert.equal(runs(ui).length, 1);
  assert.deepEqual(JSON.parse(runs(ui)[0].options.body).data, [1, 2, 0]);
});

test("Clear replaces all values before allowing new manual input", async (t) => {
  const ui = await page(t);
  await ui.file(incomplete);
  ui.document.getElementById("statsClear").click();
  assert.deepEqual(ui.groups(), ["", ""]);
  const fields = [...ui.document.querySelectorAll(".stats-group__input")];
  fields.forEach((field, i) => {
    field.value = i ? "10 20 30" : "1 2 3";
    field.dispatchEvent(new ui.dom.window.Event("input"));
  });
  await calculate(ui, "ttest_rel");
  assert.equal(runs(ui).length, 1);
});

test("saved config records uncertainty after unannounced changes to imported values", async (t) => {
  const ui = await page(t, { project: "synthetic-project" });
  await ui.projectFile(complete);
  ui.document.querySelector(".stats-group__input").value = "9 8 7";
  ui.document.getElementById("statsSaveConfig").click();
  await tick();
  const request = ui.requests.find((r) => r.url.startsWith("/api/project-save?"));
  assert.ok(request);
  const config = JSON.parse(request.options.body).payload;
  assert.equal(config.row_integrity.status, "uncertain");
  assert.equal(config.row_integrity.reason, "edited-or-restored-data");
  assert.equal(config.row_integrity.source, "csv");
});

for (const button of ["statsReportPdf", "statsReportSave"]) {
  test(`${button} refuses paired-design export of uncertain imported rows`, async (t) => {
    const ui = await page(t, { prefix: "/apps/u/stats", project: "synthetic-project" });
    await ui.projectFile(incomplete);
    ui.document.getElementById("statsDesign").value = "paired";
    ui.document.getElementById(button).click();
    await tick();
    assert.equal(ui.requests.filter((r) => /\/api\/report\/(pdf|save)$/.test(r.url)).length, 0);
    assert.match(ui.document.getElementById("statsReportStatus").textContent, /source rows|row alignment/i);
  });

  test(`${button} allows unchanged complete rows through the same paired-design guard`, async (t) => {
    const ui = await page(t, { project: "synthetic-project" });
    await ui.projectFile(complete);
    ui.document.getElementById("statsDesign").value = "paired";
    ui.document.getElementById(button).click();
    await tick();
    const request = ui.requests.find((r) => /\/api\/report\/(pdf|save)$/.test(r.url));
    assert.ok(request);
    assert.equal(JSON.parse(request.options.body).design, "within");
  });
}

test("paired reports fail closed when the shared alignment guard is unavailable", async (t) => {
  const ui = await page(t);
  await ui.file(complete);
  delete ui.dom.window.stxStatsApp.rowIntegrityError;
  ui.document.getElementById("statsDesign").value = "paired";
  ui.document.getElementById("statsReportPdf").click();
  await tick();
  assert.equal(ui.requests.filter((r) => r.url.endsWith("/api/report/pdf")).length, 0);
  assert.match(ui.document.getElementById("statsReportStatus").textContent, /source rows|row alignment/i);
});

const syntheticRecommendation = {
  notes: [],
  applicability: [{ test_id: "ttest_rel", label: "synthetic paired", applicable: true, reason_items: [] }],
  primary: { test_id: "ttest_rel", label: "synthetic paired", reason_item: { msg: "synthetic fixture", args: [] } },
  decision_path: [], alternatives: [], assumption_checks: { rows: [] },
};

async function recommend(ui) {
  ui.document.getElementById("statsRecommend").click();
  await tick();
}

function requestsFor(ui, endpoint) {
  return ui.requests.filter((request) => request.url.endsWith(`/api/${endpoint}`));
}

test("paired recommendations refuse uncertain source rows before requesting assumption checks", async (t) => {
  const ui = await page(t, { recommendation: syntheticRecommendation });
  await ui.file(incomplete);
  ui.document.getElementById("statsDesign").value = "paired";
  await recommend(ui);
  assert.equal(requestsFor(ui, "recommend-test").length, 0);
  assert.equal(ui.document.getElementById("statsRunAll").hidden, true);
  assert.match(ui.document.getElementById("statsRecNotes").textContent, /source rows|row alignment/i);
});

for (const mode of ["file", "projectFile"]) {
  test(`Run all rejects stale paired recommendation after incomplete ${mode} import`, async (t) => {
    const ui = await page(t, { prefix: "/apps/u/stats", project: mode === "projectFile" ? "synthetic-project" : "", recommendation: syntheticRecommendation });
    await ui[mode](complete);
    ui.document.getElementById("statsDesign").value = "paired";
    await recommend(ui);
    assert.equal(ui.document.getElementById("statsRunAll").hidden, false);
    await ui[mode](incomplete);
    assert.equal(ui.document.getElementById("statsRunAll").hidden, true, "import invalidates the old recommendation immediately");
    ui.document.getElementById("statsRunAll").click();
    await tick();
    assert.equal(requestsFor(ui, "run-all").length, 0);
  });
}

for (const edit of ["input", "add group", "remove group", "Clear", "sample"]) {
  test(`${edit} immediately invalidates the recommendation for old imported data`, async (t) => {
    const ui = await page(t, { recommendation: syntheticRecommendation });
    await ui.file(complete);
    ui.document.getElementById("statsDesign").value = "paired";
    await recommend(ui);
    assert.equal(ui.document.getElementById("statsRunAll").hidden, false);
    if (edit === "input") {
      const first = ui.document.querySelector(".stats-group__input");
      first.value = "8 9 10";
      first.dispatchEvent(new ui.dom.window.Event("input", { bubbles: true }));
    } else if (edit === "remove group") {
      [...ui.document.querySelectorAll(".stats-group__remove")].at(-1).click();
    } else {
      ui.dom.window.confirm = () => true;
      ui.document.getElementById({ "add group": "statsAddGroup", Clear: "statsClear", sample: "statsSample" }[edit]).click();
    }
    assert.equal(ui.document.getElementById("statsRunAll").hidden, true);
    ui.document.getElementById("statsRunAll").click();
    assert.equal(requestsFor(ui, "run-all").length, 0);
  });
}

test("Run all catches restored values even when no data-change event fires", async (t) => {
  const ui = await page(t, { recommendation: syntheticRecommendation });
  await ui.file(complete);
  ui.document.getElementById("statsDesign").value = "paired";
  await recommend(ui);
  ui.document.querySelector(".stats-group__input").value = "7 8 9";
  ui.document.getElementById("statsRunAll").click();
  await tick();
  assert.equal(requestsFor(ui, "run-all").length, 0);
  assert.equal(ui.document.getElementById("statsRunAll").hidden, true);
});

test("Run all accepts the recommendation only for unchanged complete source rows", async (t) => {
  const ui = await page(t, { recommendation: syntheticRecommendation });
  await ui.file(complete);
  ui.document.getElementById("statsDesign").value = "paired";
  await recommend(ui);
  ui.document.getElementById("statsRunAll").click();
  await tick();
  const sent = requestsFor(ui, "run-all");
  assert.equal(sent.length, 1);
  const payload = JSON.parse(sent[0].options.body);
  assert.equal(payload.design, "paired");
  assert.equal(payload.primary, "ttest_rel");
  assert.deepEqual(payload.groups, [[1, 2, 0], [10, 20, 40], [100, 200, 400]]);
});

test("an in-flight recommendation cannot certify a later import with identical compacted values", async (t) => {
  let resolve;
  const pending = new Promise((done) => { resolve = done; });
  const ui = await page(t, { recommendation: () => pending });
  await ui.file(complete);
  ui.document.getElementById("statsDesign").value = "paired";
  ui.document.getElementById("statsRecommend").click();
  await tick();
  assert.equal(requestsFor(ui, "recommend-test").length, 1);
  await ui.file("a,b,c\n1,10,100\n,,\n2,20,200\n0,40,400\n");
  assert.deepEqual(ui.groups(), ["1 2 0", "10 20 40", "100 200 400"]);
  resolve(syntheticRecommendation);
  await tick();
  assert.equal(ui.document.getElementById("statsRunAll").hidden, true);
  assert.equal(ui.document.getElementById("statsRecCard").textContent, "");
  ui.document.getElementById("statsRunAll").click();
  await tick();
  assert.equal(requestsFor(ui, "run-all").length, 0);
});

test("paired recommendation and Run all fail closed without the shared guard", async (t) => {
  const ui = await page(t, { recommendation: syntheticRecommendation });
  await ui.file(complete);
  ui.document.getElementById("statsDesign").value = "paired";
  await recommend(ui);
  delete ui.dom.window.stxStatsApp.rowIntegrityError;
  ui.document.getElementById("statsRunAll").click();
  await tick();
  await recommend(ui);
  assert.equal(requestsFor(ui, "run-all").length, 0);
  assert.equal(requestsFor(ui, "recommend-test").length, 1);
  assert.match(ui.document.getElementById("statsRecNotes").textContent, /source rows|row alignment/i);
});
