# Agentic Code Review & Autonomous Revision Framework (v2.0)

Enterprise-grade backend and interactive dashboard for the **Agentic AI-Based Risk-Adaptive and Self-Verifying Framework for Autonomous Code Review and Automated Code Revision**.

Features a full multi-agent cognitive architecture, static analysis synergy (Pylint, Bandit, Radon, AST, Secret Scanner), industry-standard CWE & OWASP taxonomy mapping, OASIS SARIF v2.1.0 export, multi-turn reflexion repair loop, companion regression test generation, and an interactive modern web dashboard.

---

## 🚀 What Makes It Advanced

1. **Multi-Agent Cognitive Pipeline & Synergistic Hints**:
   - 7 Specialist Agents: `Bug Detection`, `Security Analysis`, `Code Quality`, `Refactoring`, `Performance & Optimization`, `Testability & Robustness`, and `Architecture & Clean Code`.
   - **Static-to-AI Prior Hints**: Static tool outputs are fed into the AI agents as structured priors, allowing LLMs to drill down into compiler/linter warnings and discover deeper logical flaws without hallucinating.

2. **Automated Multi-Turn Reflexion & Self-Correction (Fix Loop)**:
   - When an automated revision fails the validation gate (e.g. syntax slip, unresolved target, or introduced side-effect), the system executes an automated **Reflexion Repair Loop** (up to `MAX_FIX_RETRIES`), prompting the Fixer Agent with exact validation gate diagnostics to self-correct.

3. **Automated Unit & Regression Test Generation**:
   - The Fix Generation Agent now generates companion unit test suites (using `pytest`) asserting the bug is resolved and ensuring zero regression.

4. **Deep AST Analysis & Secret / Credential Scanner**:
   - High-entropy credential scanner detecting AWS keys, GitHub PATs, OpenAI keys, Stripe secrets, Slack webhooks, JWT tokens, and unencrypted private keys.
   - Deep AST rules for SQL Injection (`f-string` / `.execute()`), command injection (`subprocess shell=True`), insecure deserialization (`pickle.loads`), HTTP calls without timeout, and resource leaks.

5. **CWE & OWASP Vulnerability Taxonomy**:
   - Every finding is mapped to its official **CWE ID** (e.g. CWE-89, CWE-798, CWE-94, CWE-502), **OWASP Top 10 category**, remediation effort estimate (`trivial`, `low`, `medium`, `high`), and blast radius (`local`, `function`, `module`, `system`).

6. **Executive Risk Index & Posture Grading**:
   - Aggregates overall risk into an industry-standard security posture grade (`A+`, `A`, `B`, `C`, `D`, `F`), top risk driver extraction, and CWE distribution summaries.

7. **OASIS SARIF v2.1.0 Exporter**:
   - Native integration with **GitHub Code Scanning**, SonarQube, GitLab Security, and VS Code SARIF viewers via `/api/v1/export/sarif`.

8. **Built-in Interactive Web Dashboard**:
   - Sleek dark-mode glassmorphism interface at `/dashboard` with live preset tests, side-by-side diff viewer, verification inspector, companion test code viewer, and one-click export.

---

## 📐 Architecture & Flow

```
[ GitHub PR or Webhook / Web Dashboard / REST API ]
                       │
                       ▼
             [ Input Preprocessor ]
                       │
       ┌───────────────┴───────────────┐
       ▼                               ▼
 [ Static Pipeline ]             [ AI Pipeline ]
  • Pylint                        • Bug Detection Agent
  • Bandit (Security)             • Security Analysis Agent
  • Radon (Complexity & MI)       • Code Quality Agent
  • Deep AST Rules (SQLi, etc.)   • Refactoring Agent
  • Secret Scanner (AWS, JWT)     • Performance Agent
       │                          • Test Coverage Agent
       └──────────────┬───────────• Architecture Agent
                      │ (Static Hints fed into AI)
                      ▼
            [ Consolidation Engine ]
       (Semantic & line-proximity clustering)
                      │
                      ▼
         [ Risk Engine & CWE Taxonomy ]
       (Risk 0-100 · Posture A+ to F · Blast Radius)
                      │
                      ▼
         [ Self-Verification Engine ]
       (Independent verifier · Adaptive confidence threshold)
                      │
                      ▼
         [ Autonomous Fix Generation ]
       (Complete code rewrite + Companion pytest tests)
                      │
                      ▼
          [ Automated Validation Gate ]
     (Re-analyze · No new issues · Risk reduction)
                      │
           ┌──────────┴──────────┐
      [Passed]                [Failed]
           │                     │
           │                     ▼
           │          [ Reflexion Self-Repair ]
           │          (Feedback loop up to N retries)
           ▼                     │
[ New Branch & PR Opened ] ◄─────┘
(Original PR untouched)
```

---

## 🛠️ Modular Architecture Overview

The repository is cleanly structured into separated `backend/` and `frontend/` modules:

| Module | Purpose |
|---|---|
| `backend/app/engine/pipeline.py` | Multi-agent orchestration, review, verification, and PR review engine |
| `backend/app/engine/agents.py` | 7 specialist LLM agents with static context synergy |
| `backend/app/engine/verifier.py` | Independent skeptical self-verification engine |
| `backend/app/engine/risk.py` | Risk-adaptive scoring, security posture grading (A+ to F), top risks |
| `backend/app/remediation/fixer.py` | Fix Generation Agent, deterministic AST engine, companion tests, reflexion repair |
| `backend/app/remediation/revalidation.py` | Second-cycle verification gate and resolution validator |
| `backend/app/scanners/static_analysis.py` | AST checks (SQLi, subprocess, pickle), Pylint, Bandit, Radon |
| `backend/app/scanners/secret_scanner.py` | High-entropy secret and credential scanning (AWS, OpenAI, JWT, private keys) |
| `backend/app/scanners/sca.py` | Software Composition Analysis, dependency CVE checks, CycloneDX SBOM generator |
| `backend/app/services/policy_engine.py` | Enterprise quality gates, PR compliance rules, and pass/fail enforcement |
| `backend/app/services/github_client.py` | GitHub REST client for branch creation, file commits, and PR submissions |
| `backend/app/cli_review_pr.py` | Autonomous CLI review tool used by GitHub Actions and terminal runs |
| `frontend/` | Modern web UI templates, glassmorphism styles, analytics, and interactive review tools |

---

## 🤖 GitHub Pull Request Auto-Revision Workflow

When a Pull Request is opened or updated in your GitHub repository:
1. **Defect & Vulnerability Detection**: CodeSentinel inspects all changed files using static analysis (Bandit, Pylint, AST, Secrets) and multi-agent AI.
2. **Autonomous Remediation**: If security vulnerabilities or bugs (e.g., dynamic `eval`, command injection, bare `except`, mutable defaults, SQL injection, leaked secrets) are detected, verified code fixes are automatically generated.
3. **Automated Revision PR**: CodeSentinel commits the remediated files to an isolated branch (`ai-review/pr-{pr_number}-{id}`) and automatically opens a **new Pull Request** with the corrected code and companion unit tests, leaving the original PR unchanged.
4. **Autonomous GitHub Action & CLI**:
   - Executes autonomously inside GitHub Actions via `.github/workflows/ai-code-review.yml`.
   - Or runs locally via CLI:
     ```bash
     python -m backend.app.cli_review_pr --repo <owner/repo> --pr <pr_number> --token $GITHUB_TOKEN
     ```

---

## ⚡ Quickstart

```bash
# 1. Activate environment
source venv/bin/activate      # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r backend/requirements.txt

# 3. Configure environment variables (optional for AI mode; works offline in static mode)
cp .env.example .env

# 4. Start the server
uvicorn backend.main:app --reload
```

- Open **Interactive Dashboard**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- Open **Interactive API Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 📡 REST API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | CodeSentinel Enterprise Web Portal |
| `GET` | `/dashboard` | Interactive Web Dashboard (HTML UI) |
| `GET` | `/api/v1/health` | Health status and engine readiness |
| `GET` | `/api/v1/metrics` | System capabilities, registered agents, and active tools |
| `POST` | `/api/v1/review` | Multi-agent + static review, risk scoring, verification |
| `POST` | `/api/v1/revise` | Full loop: review, autonomous fixes, companion tests, validation |
| `POST` | `/api/v1/audit/quick` | Fast single-snippet code audit for playgrounds |
| `POST` | `/api/v1/export/sarif` | Export findings to OASIS SARIF v2.1.0 format |
| `POST` | `/api/v1/export/markdown`| Export clean Markdown audit report |
| `POST` | `/api/v1/github/pull-request` | Review a GitHub PR and open an automated revision PR |
| `POST` | `/api/v1/github/webhook` | GitHub webhook receiver (HMAC SHA-256 authenticated) |
| `GET` | `/api/v1/jobs/{id}` | Status and result of background analysis jobs |

---

## 🧪 Testing

Run the full automated test suite (all 40 unit, integration, and security tests run out of the box):

```bash
pytest tests/ -v
```

