const $ = (sel) => document.querySelector(sel);
let editor, currentProblem = null, aided = false;

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
  currentProblem = p; aided = false;
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
  const r = await post("/run", { code: editor.getValue() });
  $("#results").textContent = (r.stdout || "") + (r.error ? "\n" + r.error : "");
}

async function submitCode() {
  $("#results").innerHTML = "Running tests…";
  const r = await post("/submit", { slug: currentProblem.slug, code: editor.getValue() });
  const box = $("#results"); box.innerHTML = "";
  if (r.error) { box.textContent = r.error; return; }
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
}

function wire() {
  $("#run-btn").onclick = runCode;
  $("#submit-btn").onclick = submitCode;
}

window.addEventListener("DOMContentLoaded", async () => {
  initEditor();
  wire();
  // Load the recommended next problem on open (falls back to first problem).
  const nxt = await api("/next");
  const slug = nxt.recommended || (await api("/problems"))[0]?.slug;
  if (slug) loadProblem(slug);
});
