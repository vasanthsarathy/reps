const $ = (sel) => document.querySelector(sel);
let editor, currentProblem = null, attemptLogged = false;

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
  renderHints(p.hints);
  renderSolutions(p.solutions);
  editor.setValue(p.starter_code || "");
  $("#results").textContent = "";
}

function renderMarkdown(md) {
  // Minimal: fence code blocks and preserve line breaks. Good enough for problem text.
  const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  return esc(md)
    .replace(/```([\s\S]*?)```/g, (_, c) => "<pre>" + c.trim() + "</pre>")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\n/g, "<br/>");
}

function renderHints(hints) {
  const box = $("#hints"); box.innerHTML = "";
  (hints || []).forEach((h, i) => {
    const btn = document.createElement("button");
    btn.textContent = "Hint " + (i + 1);
    btn.onclick = () => {
      const d = document.createElement("div"); d.className = "hint"; d.textContent = h;
      box.replaceChild(d, btn);
    };
    box.appendChild(btn);
  });
}

function renderSolutions(sols) {
  const box = $("#solutions"); box.innerHTML = "";
  (sols || []).forEach((s) => {
    const el = document.createElement("div");
    el.innerHTML = "<h4>" + s.name + "</h4><p>" + s.explanation + "</p><pre>" +
      s.code.replace(/</g, "&lt;") + "</pre><em>" + s.complexity + "</em>";
    box.appendChild(el);
  });
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
  r.results.forEach((c) => {
    const d = document.createElement("div");
    d.className = "case " + (c.passed ? "pass" : "fail");
    d.textContent = `${c.passed ? "✓" : "✗"} args=${JSON.stringify(c.args)} → got ${JSON.stringify(c.got)} · want ${JSON.stringify(c.expected)}`;
    box.appendChild(d);
  });
  window._lastAllPassed = r.all_passed;
  window._lastSubmit = { passed: r.passed, total: r.total, all_passed: r.all_passed };
}

function wire() {
  $("#run-btn").onclick = runCode;
  $("#submit-btn").onclick = submitCode;
  $("#next-btn").onclick = goNext;
  document.querySelectorAll("#rating-bar button[data-level]").forEach((b) =>
    b.onclick = () => finishAttempt(b.dataset.level));
  wireTimer();
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
  const n = await api("/next");
  if (!n.recommended) { alert("Nothing due right now. Add problems or come back later."); return; }
  clearNotes(); resetTimer(); loadProblem(n.recommended);
}

window.addEventListener("DOMContentLoaded", async () => {
  initEditor();
  wire();
  try {
    // Load the recommended next problem on open (falls back to first problem).
    const nxt = await api("/next");
    const slug = nxt.recommended || (await api("/problems"))[0]?.slug;
    if (slug) loadProblem(slug);
  } catch (e) {
    $("#results").textContent = "Error loading problems: " + e.message;
  }
});
