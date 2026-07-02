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
  // Protect LaTeX ($$...$$ and $...$) from the markdown pass so marked can't
  // mangle math (e.g. eat underscores in scores_{i,j} as emphasis). KaTeX
  // typesets the restored spans afterwards (see typesetMath).
  let s = md || "";
  const math = [];
  s = s.replace(/\$\$[\s\S]+?\$\$/g, (m) => { math.push(m); return "@@MATH" + (math.length - 1) + "@@"; });
  s = s.replace(/\$[^$\n]+?\$/g, (m) => { math.push(m); return "@@MATH" + (math.length - 1) + "@@"; });
  let html = window.marked ? marked.parse(s) : s;
  html = html.replace(/@@MATH(\d+)@@/g, (_, i) => math[+i]);
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
  $("#dashboard-btn").onclick = openDashboard;
  $("#dashboard-close").onclick = closeDashboard;
  $("#dashboard-overlay").onclick = (e) => { if (e.target.id === "dashboard-overlay") closeDashboard(); };
  $("#focus-select").onchange = (e) => {
    activeFocus = e.target.value;
    localStorage.setItem("reps_focus", activeFocus);
    goNext();
  };
  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;
    if (!$("#browse-overlay").hidden) closeBrowse();
    if (!$("#dashboard-overlay").hidden) closeDashboard();
  });
}

// ---- Dashboard panel ----
async function openDashboard() {
  const s = await api("/stats");
  renderDashboard(s);
  $("#dashboard-overlay").hidden = false;
}

function closeDashboard() {
  $("#dashboard-overlay").hidden = true;
}

function dashSection(title) {
  const sec = document.createElement("div");
  sec.className = "dash-section";
  const h = document.createElement("h3");
  h.textContent = title;
  sec.appendChild(h);
  return sec;
}

function cap(s) { return s.charAt(0).toUpperCase() + s.slice(1); }

function renderProgressSection(s) {
  const sec = dashSection("Progress");
  const overall = document.createElement("div");
  overall.className = "dash-line";
  overall.textContent = `${s.overall.attempted}/${s.overall.total} attempted`;
  sec.appendChild(overall);
  [["coding", "Coding"], ["ml", "ML"]].forEach(([key, label]) => {
    const t = s.by_track[key];
    if (!t) return;
    const line = document.createElement("div");
    line.className = "dash-line dash-line-sub";
    line.textContent = `${label}: ${t.attempted}/${t.total} attempted · ${t.due} due`;
    sec.appendChild(line);
  });
  return sec;
}

function renderStagesSection(s) {
  const sec = dashSection("Stages");
  const row = document.createElement("div");
  row.className = "dash-chip-row";
  ["new", "learning", "reviewing"].forEach((k) => {
    const chip = document.createElement("span");
    chip.className = "dash-stage-chip";
    chip.textContent = `${cap(k)}: ${s.stages[k] || 0}`;
    row.appendChild(chip);
  });
  sec.appendChild(row);
  return sec;
}

function renderRatingsSection(s) {
  const sec = dashSection("Ratings");
  const row = document.createElement("div");
  row.className = "dash-chip-row";
  ["easy", "good", "hard", "hint", "peeked"].forEach((level) => {
    const chip = document.createElement("span");
    chip.className = "chip " + level;
    chip.textContent = `${level}: ${s.ratings[level] || 0}`;
    row.appendChild(chip);
  });
  sec.appendChild(row);
  return sec;
}

function renderConceptsSection(s) {
  const sec = dashSection("Problem areas");
  const caption = document.createElement("div");
  caption.className = "dash-caption";
  caption.textContent = "lowest clean-rate first";
  sec.appendChild(caption);

  const table = document.createElement("table");
  table.className = "dash-concepts";
  const thead = document.createElement("thead");
  const hr = document.createElement("tr");
  ["Concept", "Attempts", "Clean rate"].forEach((h) => {
    const th = document.createElement("th");
    th.textContent = h;
    hr.appendChild(th);
  });
  thead.appendChild(hr);
  table.appendChild(thead);

  const tbody = document.createElement("tbody");
  (s.concepts || []).forEach((row) => {
    const tr = document.createElement("tr");
    const tagTd = document.createElement("td");
    tagTd.textContent = row.tag;
    const attemptsTd = document.createElement("td");
    attemptsTd.textContent = String(row.attempts);
    const rateTd = document.createElement("td");
    const bar = document.createElement("div");
    bar.className = "rate-bar";
    const fill = document.createElement("div");
    fill.className = "rate-bar-fill";
    fill.style.width = Math.round(row.rate * 100) + "%";
    bar.appendChild(fill);
    const pct = document.createElement("span");
    pct.className = "rate-bar-pct";
    pct.textContent = Math.round(row.rate * 100) + "%";
    rateTd.appendChild(bar);
    rateTd.appendChild(pct);
    tr.appendChild(tagTd); tr.appendChild(attemptsTd); tr.appendChild(rateTd);
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  sec.appendChild(table);
  return sec;
}

function shortTime(ts) {
  if (!ts) return "";
  const m = String(ts).match(/^(\d{4}-\d{2}-\d{2})T(\d{2})-(\d{2})-(\d{2})$/);
  if (!m) return ts;
  const d = new Date(`${m[1]}T${m[2]}:${m[3]}:${m[4]}`);
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" }) +
    " " + d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}

function renderRecentSection(s) {
  const sec = dashSection("Recent");
  const list = document.createElement("div");
  list.className = "dash-recent-list";
  (s.recent || []).forEach((r) => {
    const row = document.createElement("div");
    row.className = "dash-recent-row";
    const slug = document.createElement("span");
    slug.className = "dash-recent-slug";
    slug.textContent = r.slug || "";
    const result = document.createElement("span");
    result.className = "chip " + (r.result || "");
    result.textContent = r.result || "";
    const time = document.createElement("span");
    time.className = "dash-recent-time";
    time.textContent = shortTime(r.timestamp);
    row.appendChild(slug); row.appendChild(result); row.appendChild(time);
    list.appendChild(row);
  });
  if (!(s.recent || []).length) {
    const empty = document.createElement("div");
    empty.className = "dash-empty";
    empty.textContent = "No attempts yet.";
    list.appendChild(empty);
  }
  sec.appendChild(list);
  return sec;
}

function renderDashboard(s) {
  const body = $("#dashboard-body");
  body.innerHTML = "";
  body.appendChild(renderProgressSection(s));
  body.appendChild(renderStagesSection(s));
  body.appendChild(renderRatingsSection(s));
  body.appendChild(renderConceptsSection(s));
  body.appendChild(renderRecentSection(s));
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
