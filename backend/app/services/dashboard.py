"""Interactive modern web dashboard for the Agentic Code Review Framework.

Provides a rich visual UI for executing reviews, inspecting self-verification,
viewing diffs and companion unit tests, and downloading SARIF/Markdown reports.
"""

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Agentic Code Review & Autonomous Revision Framework</title>
  <style>
    :root {
      --bg: #0b0f19;
      --card-bg: rgba(22, 30, 49, 0.75);
      --card-border: rgba(255, 255, 255, 0.08);
      --text: #f3f4f6;
      --text-muted: #9ca3af;
      --accent: #6366f1;
      --accent-hover: #4f46e5;
      --critical: #ef4444;
      --high: #f97316;
      --medium: #eab308;
      --low: #3b82f6;
      --success: #10b981;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background-color: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      line-height: 1.5;
      padding: 24px;
    }
    .container { max-width: 1300px; margin: 0 auto; }
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 24px;
      border-bottom: 1px solid var(--card-border);
      margin-bottom: 24px;
    }
    .logo-group h1 { font-size: 1.5rem; font-weight: 700; color: #fff; display: flex; align-items: center; gap: 10px; }
    .logo-group p { font-size: 0.875rem; color: var(--text-muted); }
    .badge {
      display: inline-flex;
      align-items: center;
      padding: 4px 10px;
      border-radius: 9999px;
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    .badge-critical { background: rgba(239, 68, 68, 0.2); color: #fca5a5; border: 1px solid rgba(239, 68, 68, 0.4); }
    .badge-high { background: rgba(249, 115, 22, 0.2); color: #fdba74; border: 1px solid rgba(249, 115, 22, 0.4); }
    .badge-medium { background: rgba(234, 179, 8, 0.2); color: #fde047; border: 1px solid rgba(234, 179, 8, 0.4); }
    .badge-low { background: rgba(59, 130, 246, 0.2); color: #93c5fd; border: 1px solid rgba(59, 130, 246, 0.4); }
    .badge-success { background: rgba(16, 185, 129, 0.2); color: #6ee7b7; border: 1px solid rgba(16, 185, 129, 0.4); }
    .badge-neutral { background: rgba(255, 255, 255, 0.1); color: var(--text-muted); }

    .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 24px; }
    @media(max-width: 900px) { .grid-2 { grid-template-columns: 1fr; } }

    .card {
      background: var(--card-bg);
      backdrop-filter: blur(12px);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 20px;
      box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
    }
    .card-title { font-size: 1.1rem; font-weight: 600; margin-bottom: 14px; display: flex; justify-content: space-between; align-items: center; }

    textarea {
      width: 100%;
      height: 280px;
      background: rgba(11, 15, 25, 0.9);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      color: #e2e8f0;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 0.85rem;
      padding: 12px;
      resize: vertical;
    }
    textarea:focus { outline: none; border-color: var(--accent); }

    .controls-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: 14px;
      flex-wrap: wrap;
      gap: 12px;
    }
    select, button, input[type="text"] {
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--card-border);
      border-radius: 6px;
      color: #fff;
      padding: 8px 14px;
      font-size: 0.875rem;
      cursor: pointer;
      transition: all 0.2s;
    }
    button.primary {
      background: var(--accent);
      border: none;
      font-weight: 600;
    }
    button.primary:hover { background: var(--accent-hover); }
    button.secondary:hover { background: rgba(255, 255, 255, 0.1); }

    .stats-bar {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }
    .stat-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 16px;
      text-align: center;
    }
    .stat-val { font-size: 2rem; font-weight: 700; line-height: 1.2; }
    .stat-label { font-size: 0.8rem; color: var(--text-muted); text-transform: uppercase; margin-top: 4px; }

    .grade-badge {
      font-size: 2.2rem;
      font-weight: 800;
      border-radius: 8px;
      padding: 2px 16px;
      display: inline-block;
    }
    .grade-A { color: #34d399; }
    .grade-B { color: #60a5fa; }
    .grade-C { color: #fbbf24; }
    .grade-D { color: #fb923c; }
    .grade-F { color: #f87171; }

    .filter-tabs {
      display: flex;
      gap: 8px;
      margin-bottom: 16px;
      border-bottom: 1px solid var(--card-border);
      padding-bottom: 8px;
    }
    .filter-tab {
      background: none;
      border: none;
      color: var(--text-muted);
      font-weight: 500;
      padding: 6px 12px;
      border-radius: 6px;
    }
    .filter-tab.active { background: rgba(99, 102, 241, 0.2); color: #a5b4fc; }

    .finding-card {
      background: rgba(15, 23, 42, 0.6);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 16px;
      margin-bottom: 12px;
      transition: border-color 0.2s;
    }
    .finding-card:hover { border-color: rgba(99, 102, 241, 0.4); }
    .finding-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 8px;
    }
    .finding-title { font-weight: 600; font-size: 0.95rem; }
    .finding-meta { font-size: 0.75rem; color: var(--text-muted); margin-bottom: 8px; display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
    .snippet-box {
      background: rgba(0, 0, 0, 0.4);
      border-left: 3px solid var(--accent);
      padding: 8px 12px;
      font-family: monospace;
      font-size: 0.8rem;
      margin: 8px 0;
      color: #cbd5e1;
      border-radius: 0 4px 4px 0;
      white-space: pre-wrap;
    }
    .verification-info {
      font-size: 0.8rem;
      background: rgba(255, 255, 255, 0.03);
      padding: 6px 10px;
      border-radius: 6px;
      color: #94a3b8;
      margin-top: 6px;
    }

    pre.diff-view {
      background: rgba(0, 0, 0, 0.5);
      padding: 14px;
      border-radius: 8px;
      font-family: ui-monospace, SFMono-Regular, monospace;
      font-size: 0.82rem;
      overflow-x: auto;
      max-height: 400px;
    }
    .diff-add { color: #4ade80; background: rgba(34, 197, 94, 0.1); display: block; }
    .diff-del { color: #f87171; background: rgba(239, 68, 68, 0.1); display: block; }

    #loading { display: none; text-align: center; padding: 40px; }
    .spinner {
      border: 3px solid rgba(255,255,255,0.1);
      border-top: 3px solid var(--accent);
      border-radius: 50%;
      width: 32px;
      height: 32px;
      animation: spin 0.8s linear infinite;
      margin: 0 auto 12px;
    }
    @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
  </style>
</head>
<body>
<div class="container">
  <header>
    <div class="logo-group">
      <h1>🛡️ Agentic Code Review & Autonomous Revision Framework</h1>
      <p>Multi-Agent Cognitive Pipeline · Risk-Adaptive Scoring · Self-Verification · Reflexion Loop</p>
    </div>
    <div style="display:flex; gap:10px; align-items:center;">
      <span class="badge badge-success" id="llm-status-badge">LLM Ready</span>
      <a href="/docs" target="_blank" style="color:var(--text-muted); text-decoration:none; font-size:0.85rem;">API Docs ↗</a>
    </div>
  </header>

  <!-- Input Section -->
  <div class="grid-2">
    <div class="card">
      <div class="card-title">
        <span>Source Code Under Review</span>
        <select id="preset-selector" onchange="loadPreset()">
          <option value="eval">Preset: Eval & Bare Except</option>
          <option value="sqli">Preset: SQL Injection & Subprocess</option>
          <option value="secret">Preset: Hardcoded AWS & Credentials</option>
          <option value="clean">Preset: Clean Code (Secure)</option>
        </select>
      </div>
      <textarea id="code-input" spellcheck="false"></textarea>
      <div class="controls-row">
        <div>
          <label style="font-size:0.85rem; cursor:pointer;">
            <input type="checkbox" id="full-loop-check" checked> Full Loop (Review + Autonomous Fix + Tests)
          </label>
        </div>
        <div style="display:flex; gap:8px;">
          <button class="secondary" onclick="exportSarif()">Export SARIF</button>
          <button class="primary" id="run-btn" onclick="executeReview()">Run Agentic Review</button>
        </div>
      </div>
    </div>

    <!-- Executive Overview Card -->
    <div class="card" id="overview-card">
      <div class="card-title">
        <span>Executive Risk & Posture Assessment</span>
        <span id="posture-grade-container" class="grade-badge grade-A">A+</span>
      </div>
      <div class="stats-bar" style="margin-top:12px;">
        <div class="stat-card">
          <div class="stat-val" id="stat-risk">0.0</div>
          <div class="stat-label">Overall Risk Score</div>
        </div>
        <div class="stat-card">
          <div class="stat-val" id="stat-verified" style="color:var(--success)">0</div>
          <div class="stat-label">Verified Findings</div>
        </div>
        <div class="stat-card">
          <div class="stat-val" id="stat-uncertain" style="color:var(--medium)">0</div>
          <div class="stat-label">Uncertain / Pending</div>
        </div>
        <div class="stat-card">
          <div class="stat-val" id="stat-rejected" style="color:var(--text-muted)">0</div>
          <div class="stat-label">Rejected (Refuted)</div>
        </div>
      </div>

      <div style="margin-top: 16px;">
        <h4 style="font-size:0.85rem; color:var(--text-muted); text-transform:uppercase; margin-bottom:8px;">Top Risk Drivers & Taxonomy</h4>
        <div id="top-risks-container" style="display:flex; flex-direction:column; gap:6px;">
          <span style="font-size:0.85rem; color:var(--text-muted);">No active findings. Run an analysis to inspect risk drivers.</span>
        </div>
      </div>
    </div>
  </div>

  <div id="loading">
    <div class="spinner"></div>
    <div style="font-weight:600;">Multi-Agent Pipeline Executing...</div>
    <div style="font-size:0.8rem; color:var(--text-muted); margin-top:4px;">
      Running AST & static tools · Querying specialist LLM agents · Risk scoring · Self-verification · Reflexion repair
    </div>
  </div>

  <!-- Results Sections -->
  <div id="results-area" style="display:none;">
    <!-- Revision & Diff Section (if available) -->
    <div class="card" id="revision-card" style="margin-bottom:24px; display:none;">
      <div class="card-title">
        <span>🤖 Autonomous Revision & Verification Gate</span>
        <span id="revision-accepted-badge" class="badge badge-success">Accepted</span>
      </div>
      <div style="display:flex; gap:16px; margin-bottom:14px; font-size:0.85rem; color:var(--text-muted);" id="revision-metrics">
        <!-- populated via js -->
      </div>
      <h4 style="font-size:0.85rem; color:var(--text-muted); text-transform:uppercase; margin-bottom:6px;">Unified Diff</h4>
      <pre class="diff-view" id="diff-output"></pre>

      <div id="test-code-wrapper" style="margin-top:16px; display:none;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
          <h4 style="font-size:0.85rem; color:var(--text-muted); text-transform:uppercase;">🧪 Companion Regression Test (pytest)</h4>
          <button class="secondary" style="padding:4px 10px; font-size:0.75rem;" onclick="copyTestCode()">Copy Test</button>
        </div>
        <pre class="diff-view" style="color:#93c5fd;" id="test-code-output"></pre>
      </div>
    </div>

    <!-- Findings Section -->
    <div class="card">
      <div class="card-title">
        <span>Inspection Findings Explorer</span>
        <div class="filter-tabs">
          <button class="filter-tab active" onclick="filterFindings('all')">All (<span id="count-all">0</span>)</button>
          <button class="filter-tab" onclick="filterFindings('verified')">Verified (<span id="count-verified">0</span>)</button>
          <button class="filter-tab" onclick="filterFindings('uncertain')">Uncertain (<span id="count-uncertain">0</span>)</button>
          <button class="filter-tab" onclick="filterFindings('rejected')">Rejected (<span id="count-rejected">0</span>)</button>
        </div>
      </div>
      <div id="findings-container"></div>
    </div>
  </div>
</div>

<script>
const PRESETS = {
  eval: `def calculate_expression(expr, cache={}):
    # Dangerous mutable default argument and arbitrary eval
    try:
        val = eval(expr)
    except:
        pass
    return val
`,
  sqli: `import subprocess
import sqlite3

def run_query(user_id, cmd_arg):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    # SQL injection vulnerability via formatted f-string
    cursor.execute(f"SELECT * FROM users WHERE id = '{user_id}'")
    # Subprocess with shell=True
    subprocess.run(f"echo {cmd_arg}", shell=True)
`,
  secret: `import requests

AWS_ACCESS_KEY = "AKIAIOSFODNN7EXAMPLE"
API_SECRET = "sk-live-982348721389712398471239"

def fetch_data():
    # HTTP call without explicit timeout
    res = requests.get("https://api.internal.service/data")
    return res.json()
`,
  clean: `import ast
import logging

def safe_calculate(expr: str, cache: dict = None) -> int:
    if cache is None:
        cache = {}
    try:
        return ast.literal_eval(expr)
    except (ValueError, SyntaxError) as err:
        logging.warning("Failed to evaluate: %s", err)
        return 0
`
};

let currentResult = null;
let currentFilter = 'all';

function loadPreset() {
  const val = document.getElementById("preset-selector").value;
  document.getElementById("code-input").value = PRESETS[val] || "";
}

window.addEventListener("DOMContentLoaded", () => {
  loadPreset();
});

async function executeReview() {
  const code = document.getElementById("code-input").value;
  const isFullLoop = document.getElementById("full-loop-check").checked;
  const btn = document.getElementById("run-btn");
  const loading = document.getElementById("loading");
  const resultsArea = document.getElementById("results-area");

  btn.disabled = true;
  loading.style.display = "block";
  resultsArea.style.display = "none";

  const endpoint = isFullLoop ? "/api/v1/revise" : "/api/v1/review";
  const payload = { files: [{ path: "module.py", content: code }] };

  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const err = await res.json();
      alert("Error: " + (err.detail || JSON.stringify(err)));
      return;
    }
    const data = await res.json();
    currentResult = data;
    renderResults(data, isFullLoop);
  } catch (e) {
    alert("Request failed: " + e.message);
  } finally {
    btn.disabled = false;
    loading.style.display = "none";
    resultsArea.style.display = "block";
  }
}

function renderResults(data, isFullLoop) {
  const review = isFullLoop ? data.review : data;
  const s = review.summary;

  // Overview
  document.getElementById("stat-risk").innerText = s.overall_risk;
  document.getElementById("stat-verified").innerText = s.verified;
  document.getElementById("stat-uncertain").innerText = s.uncertain;
  document.getElementById("stat-rejected").innerText = s.rejected;

  const gradeEl = document.getElementById("posture-grade-container");
  const grade = s.posture_grade || "A+";
  gradeEl.innerText = grade;
  gradeEl.className = "grade-badge grade-" + grade[0];

  const topRisksContainer = document.getElementById("top-risks-container");
  if (s.top_risks && s.top_risks.length > 0) {
    topRisksContainer.innerHTML = s.top_risks.map(r => `
      <div style="background:rgba(255,255,255,0.04); padding:6px 10px; border-radius:6px; font-size:0.8rem; border-left:3px solid var(--critical);">
        ${r}
      </div>
    `).join("");
  } else {
    topRisksContainer.innerHTML = `<span style="font-size:0.85rem; color:var(--success);">✅ No critical security threats detected!</span>`;
  }

  // Counts
  const findings = review.findings || [];
  document.getElementById("count-all").innerText = findings.length;
  document.getElementById("count-verified").innerText = findings.filter(f => f.verification === "verified").length;
  document.getElementById("count-uncertain").innerText = findings.filter(f => f.verification === "uncertain").length;
  document.getElementById("count-rejected").innerText = findings.filter(f => f.verification === "rejected").length;

  // Render Findings
  renderFindingsList(findings);

  // Render Revisions
  const revCard = document.getElementById("revision-card");
  if (isFullLoop && data.revisions && data.revisions.length > 0) {
    revCard.style.display = "block";
    const revOutcome = data.revisions[0];
    const rev = revOutcome.revision;
    const val = revOutcome.validation;

    const badge = document.getElementById("revision-accepted-badge");
    badge.innerText = val.accepted ? "✅ Validation Passed" : "❌ Rejected";
    badge.className = "badge " + (val.accepted ? "badge-success" : "badge-critical");

    document.getElementById("revision-metrics").innerHTML = `
      <span>Resolved: <strong>${val.resolved}/${val.targeted}</strong></span>
      <span>New Issues: <strong>${val.new_findings.length}</strong></span>
      <span>Risk Trajectory: <strong>${val.risk_before} → ${val.risk_after}</strong></span>
      <span>Iterations: <strong>${rev.iterations || 1}</strong></span>
    `;

    renderDiff(rev.diff);

    const testWrapper = document.getElementById("test-code-wrapper");
    if (rev.test_code) {
      testWrapper.style.display = "block";
      document.getElementById("test-code-output").innerText = rev.test_code;
    } else {
      testWrapper.style.display = "none";
    }
  } else {
    revCard.style.display = "none";
  }
}

function renderDiff(diffText) {
  const container = document.getElementById("diff-output");
  if (!diffText) {
    container.innerHTML = "<em>No diff generated</em>";
    return;
  }
  const lines = diffText.split("\n");
  const formatted = lines.map(l => {
    if (l.startsWith("+") && !l.startsWith("+++")) return `<span class="diff-add">${escapeHtml(l)}</span>`;
    if (l.startsWith("-") && !l.startsWith("---")) return `<span class="diff-del">${escapeHtml(l)}</span>`;
    return `<span>${escapeHtml(l)}</span>`;
  }).join("");
  container.innerHTML = formatted;
}

function filterFindings(status) {
  currentFilter = status;
  document.querySelectorAll(".filter-tab").forEach(t => t.classList.remove("active"));
  event.target.classList.add("active");
  const review = currentResult.review ? currentResult.review : currentResult;
  renderFindingsList(review.findings || []);
}

function renderFindingsList(findings) {
  const container = document.getElementById("findings-container");
  let filtered = findings;
  if (currentFilter !== "all") {
    filtered = findings.filter(f => f.verification === currentFilter);
  }

  if (filtered.length === 0) {
    container.innerHTML = `<div style="text-align:center; padding:30px; color:var(--text-muted);">No findings in this category.</div>`;
    return;
  }

  container.innerHTML = filtered.map(f => {
    const sevBadge = `badge-${f.severity}`;
    const verBadge = f.verification === 'verified' ? 'badge-success' : (f.verification === 'uncertain' ? 'badge-medium' : 'badge-neutral');
    return `
      <div class="finding-card">
        <div class="finding-header">
          <div>
            <span class="finding-title">${escapeHtml(f.title)}</span>
            <div class="finding-meta" style="margin-top:4px;">
              <span class="badge ${sevBadge}">${f.severity}</span>
              <span class="badge ${verBadge}">${f.verification}</span>
              <span>Line ${f.line}</span>
              ${f.cwe_id ? `<span class="badge badge-neutral">${f.cwe_id}</span>` : ""}
              ${f.owasp_category ? `<span class="badge badge-neutral">${f.owasp_category.split(':')[0]}</span>` : ""}
              <span>Sources: ${f.sources.join(", ")}</span>
              <span>Risk: <strong>${f.risk_score}</strong></span>
            </div>
          </div>
        </div>
        <p style="font-size:0.875rem; color:#cbd5e1; margin-bottom:6px;">${escapeHtml(f.description)}</p>
        ${f.code_snippet ? `<div class="snippet-box">${escapeHtml(f.code_snippet)}</div>` : ""}
        ${f.recommendation ? `<p style="font-size:0.85rem; color:#93c5fd;"><strong>Recommendation:</strong> ${escapeHtml(f.recommendation)}</p>` : ""}
        <div class="verification-info">
          <em>Verification:</em> ${escapeHtml(f.verification_reason || "None recorded")}
        </div>
      </div>
    `;
  }).join("");
}

function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function copyTestCode() {
  const code = document.getElementById("test-code-output").innerText;
  navigator.clipboard.writeText(code);
  alert("Test code copied to clipboard!");
}

async function exportSarif() {
  if (!currentResult) {
    alert("Please run a review first before exporting SARIF.");
    return;
  }
  const review = currentResult.review ? currentResult.review : currentResult;
  const res = await fetch("/api/v1/export/sarif", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ findings: review.findings })
  });
  const sarifData = await res.json();
  const blob = new Blob([JSON.stringify(sarifData, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "code-review-results.sarif";
  a.click();
}
</script>
</body>
</html>
"""
