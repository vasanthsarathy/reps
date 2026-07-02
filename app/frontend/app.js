const $ = (sel) => document.querySelector(sel);
let editor, currentProblem = null, attemptLogged = false;
let activeFocus = localStorage.getItem("reps_focus") || "all";

async function api(path, opts) {
  const r = await fetch("/api" + path, opts);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
function post(path, body) {
  return api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
}

function initEditor() {
  editor = CodeMirror.fromTextArea($("#code"), {
    mode: "python", theme: "material-darker", lineNumbers: true,
    indentUnit: 4, matchBrackets: true,
  });
}

async function loadProblem(slug) {
  const p = await api("/problem/" + slug);
  currentProblem = p; attemptLogged = false;
  window._lastAllPassed = false;
  window._lastSubmit = null;
  $("#problem-title").textContent = p.title + "  ·  " + p.difficulty;
  $("#problem-desc").innerHTML = renderMarkdown(p.description);
  typesetMath($("#problem-desc"));
  renderHints(p.hints);
  renderSolutions(p.solutions);
  editor.setValue(p.starter_code || "");
  $("#results").textContent = "";
}

function renderMarkdown(md) {
  const html = window.marked ? marked.parse(md || "") : (md || "");
  return html;
}
function typesetMath(el) {
  if (window.renderMathInElement) {
    renderMathInElement(el, {
      delimiters: [{left: "$$", right: "$$", display: true},
                   {left: "$", right: "$", display: false}],
      throwOnError: false,
    });
  }
}

function renderHints(hints) {
  const box = $("#hints"); box.innerHTML = "";
  (hints || []).forEach((h, i) => {
    const btn = document.createElement("button");
    btn.textContent = "Hint " + (i + 1);
    btn.onclick = () => {
      const d = document.createElement("div"); d.className = "hint";
      d.innerHTML = renderMarkdown(h);
      box.replaceChild(d, btn);
      typesetMath(d);
    };
    box.appendChild(btn);
  });
}

function renderSolutions(sols) {
  const box = $("#solutions"); box.innerHTML = "";
  (sols || []).forEach((s) => {
    const el = document.createElement("div");
    el.innerHTML = "<h4>" + s.name + "</h4>" + renderMarkdown(s.explanation) + "<pre>" +
      s.code.replace(/</g, "&lt;") + "</pre><em>" + s.complexity + "</em>";
    box.appendChild(el);
  });
  typesetMath(box);
}

async function runCode() {
  $("#results").textContent = "Running…";
  try {
    const r = await post("/run", { code: editor.getValue() });
    $("#results").textContent = (r.stdout || "") + (r.error ? "\n" + r.error : "");
  } catch (e) {
    $("#results").textContent = "Error: " + e.message;
  }
}

async function submitCode() {
  $("#results").innerHTML = "Running tests…";
  let r;
  try {
    r = await post("/submit", { slug: currentProblem.slug, code: editor.getValue() });
  } catch (e) {
    $("#results").textContent = "Error: " + e.message;
    return;
  }
  const box = $("#results"); box.innerHTML = "";
  if (r.error) { box.textContent = r.error; window._lastAllPassed = false; window._lastSubmit = null; return; }
  const head = document.createElement("div");
  head.textContent = `${r.passed}/${r.total} passed · ${r.runtime_ms}ms`;
  box.appendChild(head);
  // Show failing cases first (the useful ones); if all pass, show a few samples.
  const failing = r.results.filter((c) => !c.passed);
  const shown = failing.length ? failing.slice(0, 10) : r.results.slice(0, 6);
  shown.forEach((c) => {
    const d = document.createElement("div");
    d.className = "case " + (c.passed ? "pass" : "fail");
    const got = typeof c.got === "string" ? String(c.got) : JSON.stringify(c.got);
    const expected = typeof c.expected === "string" ? String(c.expected) : JSON.stringify(c.expected);
    let line = `${c.passed ? "✓" : "✗"} args=${JSON.stringify(c.args)} → got ${got} · want ${expected}`;
    if (c.max_abs_err !== undefined && c.max_abs_err !== null) line += ` · max_abs_err=${c.max_abs_err}`;
    if (c.note) line += ` · ${c.note}`;
    d.textContent = line;
    box.appendChild(d);
  });
  const hidden = r.results.length - shown.length;
  if (hidden > 0) {
    const more = document.createElement("div");
    more.className = "case-more";
    more.textContent = `… ${hidden} more ${failing.length ? "case(s)" : "passing case(s)"} not shown`;
    box.appendChild(more);
  }
  window._lastAllPassed = r.all_passed;
  window._lastSubmit = { passed: r.passed, total: r.total, all_passed: r.all_passed };
}

async function loadFocusGroups() {
  const groups = await api("/focus-groups");
  const sel = $("#focus-select");
  sel.innerHTML = "";
  groups.forEach((g) => {
    const opt = document.createElement("option");
    opt.value = g.id; opt.textContent = g.label;
    sel.appendChild(opt);
  });
  sel.value = activeFocus;
}

function wire() {
  $("#run-btn").onclick = runCode;
  $("#submit-btn").onclick = submitCode;
  $("#next-btn").onclick = goNext;
  document.querySelectorAll("#rating-bar button[data-level]").forEach((b) =>
    b.onclick = () => finishAttempt(b.dataset.level));
  wireTimer();
  $("#browse-btn").onclick = openBrowse;
  $("#browse-close").onclick = closeBrowse;
  $("#browse-search").oninput = (e) => renderBrowse(filterItems(e.target.value));
  $("#browse-overlay").onclick = (e) => { if (e.target.id === "browse-overlay") closeBrowse(); };
  $("#focus-select").onchange = (e) => {
    activeFocus = e.target.value;
    localStorage.setItem("reps_focus", activeFocus);
    goNext();
  };
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !$("#browse-overlay").hidden) closeBrowse();
  });
}

// ---- Browse panel ----
let browseItems = [];

function todayISO() { return new Date().toISOString().slice(0, 10); }

async function openBrowse() {
  browseItems = await api("/problems");
  renderBrowse(filterItems($("#browse-search").value));
  $("#browse-overlay").hidden = false;
  $("#browse-search").focus();
}

function closeBrowse() {
  $("#browse-overlay").hidden = true;
}

function filterItems(query) {
  const q = query.trim().toLowerCase();
  return browseItems.filter((item) =>
    (!q || item.title.toLowerCase().includes(q) ||
     (item.concepts || []).some((c) => c.toLowerCase().includes(q))));
}

function shortDate(due) {
  return new Date(due + "T00:00:00").toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function browseRow(item) {
  const row = document.createElement("div");
  row.className = "browse-row";
  const main = document.createElement("div");
  main.className = "browse-row-main";
  const title = document.createElement("div");
  title.className = "browse-row-title";
  title.textContent = item.title;
  const sub = document.createElement("div");
  sub.className = "browse-row-sub";
  sub.textContent = item.difficulty + " · " + (item.concepts || []).join(", ");
  main.appendChild(title); main.appendChild(sub);

  const status = document.createElement("div");
  status.className = "browse-row-status";
  const badge = document.createElement("span");
  if (!item.seen) {
    badge.className = "badge new"; badge.textContent = "New";
  } else if (item.due && item.due <= todayISO()) {
    badge.className = "badge due"; badge.textContent = "Due";
  } else {
    badge.className = "badge sched"; badge.textContent = "next: " + shortDate(item.due);
  }
  status.appendChild(badge);
  if (item.seen) {
    const chip = document.createElement("span");
    chip.className = "chip " + item.last_result;
    chip.textContent = item.last_result + " ×" + item.repetitions;
    status.appendChild(chip);
  }

  row.appendChild(main); row.appendChild(status);
  row.onclick = () => { loadProblem(item.slug); clearNotes(); resetTimer(); closeBrowse(); };
  return row;
}

function renderBrowse(items) {
  const list = $("#browse-list");
  list.innerHTML = "";
  const today = todayISO();
  const due = items.filter((i) => i.seen && i.due && i.due <= today)
    .sort((a, b) => a.due < b.due ? -1 : a.due > b.due ? 1 : 0);
  const isNew = items.filter((i) => !i.seen);
  const scheduled = items.filter((i) => i.seen && !(i.due && i.due <= today))
    .sort((a, b) => (a.due || "") < (b.due || "") ? -1 : (a.due || "") > (b.due || "") ? 1 : 0);

  const groups = [["Due", due], ["New", isNew], ["Scheduled", scheduled]];
  groups.forEach(([label, groupItems]) => {
    if (groupItems.length === 0) return;
    const header = document.createElement("div");
    header.className = "browse-group";
    header.textContent = label;
    list.appendChild(header);
    groupItems.forEach((item) => list.appendChild(browseRow(item)));
  });
}

let timer = { total: 20 * 60, remaining: 20 * 60, id: null, startedAt: null, elapsedMs: 0 };

function fmt(sec) {
  const s = Math.max(0, Math.abs(sec));
  const m = Math.floor(s / 60), r = s % 60;
  return (sec < 0 ? "-" : "") + String(m).padStart(2, "0") + ":" + String(r).padStart(2, "0");
}
function paintTimer() {
  const d = $("#timer-display");
  d.textContent = fmt(timer.remaining);
  d.classList.toggle("overtime", timer.remaining < 0);
}
function tickTimer() {
  timer.remaining -= 1;
  timer.elapsedMs += 1000;
  paintTimer();
}
function startTimer() {
  if (timer.id) return;
  timer.startedAt = Date.now();
  timer.id = setInterval(tickTimer, 1000);
}
function pauseTimer() { clearInterval(timer.id); timer.id = null; }
function resetTimer() {
  pauseTimer();
  timer.total = (parseInt($("#timer-minutes").value, 10) || 20) * 60;
  timer.remaining = timer.total; timer.elapsedMs = 0;
  paintTimer();
}
function getElapsedMs() { return timer.elapsedMs; }
function getNotes() {
  const notes = {};
  document.querySelectorAll("#notes textarea[data-note]").forEach((t) => notes[t.dataset.note] = t.value);
  return notes;
}
function clearNotes() { document.querySelectorAll("#notes textarea[data-note]").forEach((t) => t.value = ""); }

function wireTimer() {
  $("#timer-start").onclick = startTimer;
  $("#timer-pause").onclick = pauseTimer;
  $("#timer-reset").onclick = resetTimer;
  $("#timer-minutes").onchange = resetTimer;
}

async function finishAttempt(result) {
  if (attemptLogged) return;
  if (!currentProblem) return;
  attemptLogged = true;
  pauseTimer();
  const body = {
    slug: currentProblem.slug, code: editor.getValue(),
    elapsed_ms: getElapsedMs(), result, notes: getNotes(),
    test_summary: window._lastSubmit || null,
    focus: activeFocus || null,
  };
  const res = await post("/attempt", body);
  const n = res.next;
  const msg = n.recommended
    ? `Logged "${result}". Next up: ${n.recommended} (${n.reason}).`
    : `Logged "${result}". Nothing due — you're clear.`;
  if (confirm(msg + "\n\nLoad next problem now?") && n.recommended) {
    clearNotes(); resetTimer(); loadProblem(n.recommended);
  }
}

async function goNext() {
  const q = activeFocus && activeFocus !== "all" ? "?focus=" + activeFocus : "";
  const n = await api("/next" + q);
  if (!n.recommended) { alert("Nothing due right now. Add problems or come back later."); return; }
  clearNotes(); resetTimer(); loadProblem(n.recommended);
}

window.addEventListener("DOMContentLoaded", async () => {
  initEditor();
  wire();
  await loadFocusGroups();
  try {
    // Load the recommended next problem on open (falls back to first problem).
    const q = activeFocus && activeFocus !== "all" ? "?focus=" + activeFocus : "";
    const nxt = await api("/next" + q);
    const slug = nxt.recommended || (await api("/problems"))[0]?.slug;
    if (slug) loadProblem(slug);
  } catch (e) {
    $("#results").textContent = "Error loading problems: " + e.message;
  }
});
