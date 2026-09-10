// SciTeX Statistics — thin vanilla-JS calculator over the scitex-stats API.
// No build step. `STX_MOUNT` is declared once in stx-mount.js (loaded first);
// these are classic <script> tags sharing one global scope, so redeclaring it
// here would be a SyntaxError that breaks the whole page.

function parseNumbers(text) {
  if (!text) return [];
  return String(text)
    .split(/[\s,;\t\n]+/)
    .filter(function (t) { return t.length > 0; })
    .map(Number)
    .filter(function (n) { return !Number.isNaN(n); });
}

async function api(path, options) {
  const res = await fetch(STX_MOUNT + path, options);
  let body = {};
  try { body = await res.json(); } catch (e) { /* non-JSON */ }
  return { ok: res.ok, status: res.status, body: body };
}

const $ = function (id) { return document.getElementById(id); };

function setStatus(state, text) {
  const el = $('serviceStatus');
  if (!el) return;
  el.innerHTML = '<span class="status-indicator status-' + state + '">&#9679; ' + text + '</span>';
}

async function init() {
  // Status
  try {
    const h = await api('/api/health', { method: 'GET' });
    if (h.ok) setStatus('ok', 'Online &middot; ' + h.body.package_version + ' &middot; ' + h.body.tests + ' tests');
    else setStatus('err', 'API unreachable');
  } catch (e) { setStatus('err', 'API unreachable'); }

  // Test catalogue -> run select
  try {
    const t = await api('/api/tests', { method: 'GET' });
    if (t.ok && t.body.tests) {
      const sel = $('runTest');
      sel.innerHTML = '';
      t.body.tests.forEach(function (name) {
        const opt = document.createElement('option');
        opt.value = name; opt.textContent = name;
        sel.appendChild(opt);
      });
    }
  } catch (e) { /* non-fatal */ }

  // Mode toggle shows/hides data2
  $('runMode').addEventListener('change', function () {
    const one = this.value === 'one';
    $('runData2Wrap').style.display = one ? 'none' : '';
  });
}

async function onRecommend() {
  const n = Math.max(1, parseInt($('recGroups').value, 10) || 2);
  const payload = {
    n_groups: n,
    sample_sizes: [30, 30, 30, 30, 30].slice(0, n),
    outcome_type: $('recOutcome').value,
    design: $('recDesign').value,
    paired: $('recPaired').checked,
    top_k: 4,
  };
  const list = $('recList');
  list.innerHTML = '<li class="rec-list__loading">Recommending&hellip;</li>';
  try {
    const r = await api('/api/recommend', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (r.ok && r.body.recommendations) {
      list.innerHTML = '';
      r.body.recommendations.forEach(function (name, i) {
        const li = document.createElement('li');
        li.textContent = (i + 1) + '. ' + name;
        li.className = 'rec-list__item';
        li.style.cursor = 'pointer';
        li.addEventListener('click', function () { $('runTest').value = name; });
        list.appendChild(li);
      });
    } else {
      list.innerHTML = '<li class="rec-list__err">' + (r.body.error || 'recommend failed') + '</li>';
    }
  } catch (e) {
    list.innerHTML = '<li class="rec-list__err">request failed: ' + e + '</li>';
  }
}

async function onRun() {
  const test_name = $('runTest').value;
  const payload = { test_name: test_name, alternative: $('runAlt').value };
  const mode = $('runMode').value;
  payload.data = parseNumbers($('runData').value);
  if (mode === 'two') payload.data2 = parseNumbers($('runData2').value);
  if (mode === 'groups') {
    payload.groups = parseNumbers($('runData').value); // single textarea for grouped demo
    delete payload.data;
  }
  const fmt = $('resultFormatted');
  const js = $('resultJson');
  js.textContent = 'Running ' + test_name + '&hellip;';
  try {
    const r = await api('/api/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (r.ok) {
      fmt.textContent = r.body.formatted || '(no formatted string)';
      js.textContent = JSON.stringify(r.body, null, 2);
    } else {
      fmt.textContent = '';
      js.textContent = (r.body && r.body.error) ? r.body.error : ('HTTP ' + r.status);
    }
  } catch (e) {
    fmt.textContent = '';
    js.textContent = 'request failed: ' + e;
  }
}

async function onCorrect() {
  const pvalues = parseNumbers($('corrP').value);
  const payload = { pvalues: pvalues, method: $('corrMethod').value, alpha: parseFloat($('corrAlpha').value) };
  const out = $('corrOut');
  out.textContent = 'Correcting&hellip;';
  const r = await api('/api/correct', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  out.textContent = r.ok ? JSON.stringify(r.body, null, 2) : ((r.body && r.body.error) || ('HTTP ' + r.status));
}

async function onPosthoc() {
  const lines = String($('phGroups').value).split('\n').map(function (l) { return l.trim(); }).filter(Boolean);
  const groups = lines.map(parseNumbers).filter(function (g) { return g.length > 0; });
  const payload = { groups: groups, method: $('phMethod').value };
  const out = $('phOut');
  out.textContent = 'Comparing&hellip;';
  const r = await api('/api/posthoc', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  out.textContent = r.ok ? JSON.stringify(r.body, null, 2) : ((r.body && r.body.error) || ('HTTP ' + r.status));
}

document.addEventListener('DOMContentLoaded', function () {
  init();
  $('btnRecommend').addEventListener('click', onRecommend);
  $('btnRun').addEventListener('click', onRun);
  $('btnCorrect').addEventListener('click', onCorrect);
  $('btnPosthoc').addEventListener('click', onPosthoc);
});
