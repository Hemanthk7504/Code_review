# 🛡️ CodeSentinel: Enterprise Agentic AI Code Review & Autonomous Revision Framework (v2.0)

> **Autonomous, Risk-Adaptive, and Self-Verifying Multi-Agent Code Review & Automated PR Revision Platform.**

CodeSentinel is an enterprise-grade AI pairing and code security system that goes far beyond traditional static linters and comment-only bots. When vulnerabilities, performance bugs, or bad code patterns are introduced in your codebase or pull requests, CodeSentinel **detects the defects, skeptical-verifies them, writes verified fixes, runs companion regression tests, self-heals via reflexion repair, and autonomously opens a NEW Pull Request with the corrected code against your branch.**

---

## 🌟 Table of Contents
- [Why CodeSentinel?](#-why-codesentinel)
- [Complete Feature Catalog](#-complete-feature-catalog)
- [System Architecture & Lifecycle](#-system-architecture--lifecycle)
- [How It Works: Step-by-Step](#-how-it-works-step-by-step)
  - [Workflow 1: GitHub Pull Request Autonomous Auto-Revision](#workflow-1-github-pull-request-autonomous-auto-revision)
  - [Workflow 2: Interactive Web Dashboard & Playgrounds](#workflow-2-interactive-web-dashboard--playgrounds)
  - [Workflow 3: Real-Time SSE Streaming & REST API](#workflow-3-real-time-sse-streaming--rest-api)
- [Modular Directory Structure](#-modular-directory-structure)
- [Quickstart & Local Installation](#-quickstart--local-installation)
- [GitHub Actions & CI/CD Setup](#-github-actions--cicd-setup)
- [REST API Reference](#-rest-api-reference)
- [Automated Verification & Test Suite](#-automated-verification--test-suite)

---

## 💡 Why CodeSentinel?

| Feature | Traditional Linters (Pylint, Flake8) | Typical AI Code Review Bots | 🛡️ **CodeSentinel v2.0** |
|---|---|---|---|
| **Analysis Scope** | Syntax & basic style only | LLM text comments only | Multi-Agent AI + Deep AST + Linters + Secrets + SCA |
| **Hallucination Protection** | N/A (rule-based) | High (frequently invents lines) | **Skeptical Self-Verification Gate** filters fake issues |
| **Static + AI Synergy** | None | Isolated (ignores compiler context) | **Priors Injection**: compiler diagnostics feed into LLMs |
| **Fix Generation** | None | Raw unchecked snippet suggestions | **Complete file revisions with AST check** |
| **Validation Gate** | None | None (blind suggestions) | Re-analyzes fix, ensures risk drops and no new issues |
| **Self-Healing Loop** | None | None | **Multi-turn Reflexion Loop** repairs rejected fixes |
| **Pull Request Automation** | Comments only | Comments only | **Autonomously creates branch & opens new PR with fixes** |
| **Offline Reliability** | Works offline | Fails if LLM API is down | **Deterministic AST Engine** guarantees verified fixes offline |
| **Companion Unit Tests** | None | None | Generates automated `pytest` regression suites for fixes |
| **Enterprise Governance** | None | Basic | RBAC, JWT Auth, Quality Gates, SBOM, SOC 2/PCI-DSS scorecards |

---

## 🚀 Complete Feature Catalog

### 1. 🤖 7 Specialist Cognitive LLM Agents
Instead of relying on a generic prompt, CodeSentinel orchestrates seven specialized cognitive agents:
1. **Bug Detection Agent**: Finds logical bugs, off-by-one errors, null pointers, race conditions, unhandled exceptions, and type errors.
2. **Security Analysis Agent**: Identifies OWASP Top 10 vulnerabilities (SQLi, command injection, SSRF, XSS, insecure deserialization, path traversal).
3. **Code Quality Agent**: Enforces clean code principles, DRY, SOLID, idiomatic Python, and maintainability.
4. **Refactoring Agent**: Identifies high-complexity functions, code smells, duplicate logic, and oversized parameters.
5. **Performance & Optimization Agent**: Spots algorithmic bottlenecks, $O(N^2)$ loops, thread starvation, missing timeouts, and memory leaks.
6. **Testability & Robustness Agent**: Analyzes edge case handling, mockability, assertion depth, and test readiness.
7. **Architecture & Clean Code Agent**: Evaluates structural coupling, cohesion, layer violations, and dependency flow.

### 2. ⚡ Static-to-AI Synergistic Prior Hints
Static analysis tools (Pylint, Bandit, Radon, Deep AST) execute first in parallel. Their exact line diagnostics, symbols, and cyclomatic complexities are formatted into structured priors fed into the specialist LLM agents. This grounds the AI in concrete compiler facts, virtually eliminating hallucinations.

### 3. 🔍 Deep AST & High-Entropy Credential Scanner
- **Deep AST Scanner**: Traverses Python abstract syntax trees to catch:
  - Dynamic `eval()` and `exec()` calls (CWE-95).
  - Subprocess calls with `shell=True` (CWE-78 command injection).
  - Insecure object deserialization via `pickle.loads()` (CWE-502).
  - SQL Injection via dynamic string interpolation/formatting in `cursor.execute()` (CWE-89).
  - Outbound HTTP requests without explicit timeouts in `requests` or `httpx` (CWE-400).
  - Relative imports beyond top-level packages (CWE-691).
  - Mutable default arguments `={}` and `=[]` (CWE-665).
  - Bare `except:` clauses and silently swallowed exceptions (CWE-703 / CWE-390).
- **High-Entropy Secret Scanner**: Detects exposed AWS access keys, GitHub Personal Access Tokens, OpenAI keys, Stripe secret keys, Slack webhooks, asymmetric private keys (`BEGIN RSA PRIVATE KEY`), and JWT tokens.

### 4. 📦 Software Composition Analysis (SCA) & CycloneDX SBOM
- Scans `requirements.txt`, `Pipfile`, and `poetry.lock` for vulnerable dependencies.
- Maps known CVEs, severity ratings, and patched versions.
- Generates industry-standard **CycloneDX v1.5 JSON Software Bill of Materials (SBOM)** on demand via `/api/v1/sca/sbom`.

### 5. 🎯 Skeptical Self-Verification Engine
Every candidate finding from both static tools and AI agents is evaluated by an independent verifier before being accepted:
- **Corroboration Tracking**: Corroborates AI findings with static evidence.
- **Line & Snippet Bounds Check**: Verifies that the flagged line actually exists and contains the matching code snippet.
- **Adaptive Confidence Thresholding**: Computes a dynamic acceptance threshold based on file risk:
  $$\text{Threshold} = \text{base\_threshold} + \text{risk\_weight} \times \left(\frac{\text{risk}}{100}\right)$$
- Findings falling below the threshold are tagged as `uncertain` or `rejected`, preventing noise and false positives.

### 6. 🛠️ Autonomous Fix Generation & Deterministic Fallback
- **LLM Fixer Agent**: Produces a complete, syntactically clean rewrite of the affected file resolving all targeted issues.
- **Deterministic AST Engine (`_derive_fix`)**: When running offline or if LLM APIs are unavailable, CodeSentinel uses an intelligent rule-based engine to synthesize valid AST fixes for SQL injection, `eval()`, `shell=True`, bare `except:`, mutable defaults, relative imports, and leaked credentials.

### 7. 🔄 Automated Validation Gate & Reflexion Self-Repair Loop
Every proposed revision must pass a rigorous 4-step validation gate:
1. **Syntax Validity**: Revision must pass `ast.parse()` without syntax errors.
2. **Target Resolution Ratio**: At least `min_resolution_ratio` (default 100%) of targeted bugs must be confirmed resolved upon re-analysis.
3. **No New Verified Issues**: Re-scanning the revised code must introduce zero new verified defects (`max_new_issues = 0`).
4. **Risk Reduction**: Overall risk score after fix must be strictly lower than before fix.
- **Reflexion Self-Repair Loop**: If the validation gate rejects a revision, CodeSentinel triggers a multi-turn reflexion loop (up to `MAX_FIX_RETRIES`), passing the exact compiler/validator rejection diagnostics back to the model to self-correct.

### 8. 🧪 Companion Regression Test Generator
For each accepted revision, CodeSentinel automatically generates a companion `pytest` test suite:
- Asserts syntax validity via `ast.parse`.
- Asserts vulnerable constructs (`eval(`, `shell=True`, bare excepts) are eliminated.
- Validates that safe alternatives (`ast.literal_eval`, `shell=False`) are present and functional.

### 9. 🤖 Autonomous GitHub Pull Request Auto-Revision
When a PR is reviewed:
1. Discovers verified security and bug defects.
2. Creates an isolated branch (`ai-review/pr-{pr_number}-{short_uuid}`).
3. Commits the remediated files with descriptive commit messages.
4. Opens a **NEW Pull Request** targeting the PR branch (with base fallback) with a comprehensive before/after diff summary.
5. Posts a detailed review breakdown and a direct link to the new revision PR on the original PR.

### 10. 🏛️ Enterprise Security, RBAC & Policy Gates
- **JWT Authentication & Passlib Hashing**: Secure user registration, login, token refresh, and profile management with pre-seeded enterprise accounts (`admin@codesentinel.io`, `reviewer@codesentinel.io`).
- **Role-Based Access Control (RBAC)**: Enforces role permissions across `Admin`, `Reviewer`, and `Auditor`.
- **Dual Authentication**: Supports both Bearer JWT tokens and `X-API-Key` headers for headless CI/CD integration.
- **Enterprise Policy Engine**: Enforces customizable quality gates (e.g. `block_on_critical: true`, `max_overall_risk: 30`, `disallow_unpinned_deps: true`).
- **Compliance Scorecards**: Evaluates repository posture against **OWASP Top 10**, **PCI-DSS v4.0**, **SOC 2 Type II**, and **HIPAA Security Rule**.
- **OASIS SARIF v2.1.0 Exporter**: Native export for GitHub Code Scanning alerts, SonarQube, and VS Code.

---

## 📐 System Architecture & Lifecycle

```
                           [ Developer Pull Request / Web Dashboard / API ]
                                                  │
                                                  ▼
                                        [ Input Preprocessor ]
                                                  │
                   ┌──────────────────────────────┴──────────────────────────────┐
                   ▼                                                             ▼
         [ Static Analysis Engine ]                                    [ Multi-Agent AI Pipeline ]
     • Pylint (Syntax & Quality)                                      • Bug Detection Agent
     • Bandit (AST Security)                                          • Security Analysis Agent
     • Radon (Complexity & MI)                                        • Code Quality Agent
     • Deep AST Rules (SQLi, eval, shell)                             • Refactoring Agent
     • Secret Scanner (AWS, JWT, Keys)                                • Performance & Optimization Agent
     • Software Composition (SCA & CVEs)                              • Testability & Robustness Agent
                   │                                                  • Architecture & Clean Code Agent
                   └──────────────────────────────┬──────────────────────────────┘
                                                  │ (Static priors fed into AI context)
                                                  ▼
                                      [ Consolidation Engine ]
                               (Semantic & Line Proximity Clustering)
                                                  │
                                                  ▼
                                    [ Risk Engine & CWE Taxonomy ]
                             (Risk 0-100 · Posture A+ to F · CWE Mapping)
                                                  │
                                                  ▼
                                    [ Self-Verification Engine ]
                             (Independent Verifier · Adaptive Threshold)
                                                  │
                                                  ▼
                                   [ Autonomous Fix Generation ]
                        (LLM Fixer Agent OR Deterministic AST Engine Fallback)
                                                  │
                                                  ▼
                                     [ Automated Validation Gate ]
                                 (Re-Analyze Revised Code in Isolation)
                                                  │
                                 ┌────────────────┴────────────────┐
                             [Passed]                          [Failed]
                                 │                                 │
                                 │                                 ▼
                                 │                    [ Reflexion Self-Repair Loop ]
                                 │                    (Multi-Turn LLM Error Correction)
                                 │                                 │
                                 ├─────────────────────────────────┘
                                 ▼
                   [ Pull Request Automation Engine ]
                                 │
             ┌───────────────────┴───────────────────┐
             ▼                                       ▼
  [ New Branch & PR Created ]             [ Review Comment Posted ]
• Branch: ai-review/pr-X-XXXX           • Line-by-line findings
• Commits corrected files               • Security & risk posture
• Opens NEW PR with diff & tests        • Link to the new revision PR
```

---

## 🔄 How It Works: Step-by-Step

### Workflow 1: GitHub Pull Request Autonomous Auto-Revision

Here is how CodeSentinel reviewed PR #2 and autonomously created **[PR #3: 🤖 Automated Security & Bug Fixes for #2](https://github.com/Hemanthk7504/Code_review/pull/3)** in real-time:

1. **Trigger**: A pull request is opened or updated on GitHub (e.g. `PR #2: Hemanthk7504 patch 1`).
2. **Ingestion**: The GitHub Actions runner checks out the PR and calls `python -m backend.app.cli_review_pr --repo <owner/repo> --pr 2 --token $GITHUB_TOKEN`.
3. **Diff Analysis**: The engine fetches changed files and patches via GitHub REST API, identifying changed line numbers.
4. **Defect Discovery**: Static analysis and AI agents inspect `backend/main.py` and flag:
   - `relative-beyond-top-level` (CWE-691): Attempted relative import beyond top-level package.
   - `unused-import`: Unused `main` imported from `main`.
5. **Remediation & AST Validation**:
   - The engine replaces the invalid relative import with clean absolute imports and fallback handling:
     ```python
     try:
         from backend.app.main import app
     except ImportError:
         from app.main import app
     ```
   - It strips the unused import.
   - Re-analysis confirms: **Issues resolved: 2/2, New issues: 0, Risk dropped: 71.96 → 0.0**.
6. **New Branch & Revision PR**:
   - Creates a dedicated branch: `ai-review/pr-2-766067`.
   - Commits the remediated `backend/main.py` to the branch.
   - Submits a **new Pull Request** targeting the developer's PR branch.
7. **Original PR Feedback**:
   - Posts a detailed review breakdown on PR #2.
   - Posts a notification comment on PR #2: `🤖 A revision PR with verified fixes was opened: https://github.com/Hemanthk7504/Code_review/pull/3`.

---

### Workflow 2: Interactive Web Dashboard & Playgrounds

1. Open your browser to `http://127.0.0.1:8000/`.
2. Login with pre-seeded credentials (`admin@codesentinel.io` / `Admin@CodeSentinel2026!`).
3. Navigate to **New Review** (`/new-review`) or **Dashboard** (`/dashboard`).
4. Paste code or upload multi-file projects:
   - Click **Run Full Review & Revise**.
   - Watch the multi-agent progress bar in real time.
5. In **Review Results** (`/results`):
   - Inspect the **Side-by-Side Diff Viewer** showing original vs remediated code.
   - View the generated **Pytest Companion Tests**.
   - Download audit reports as **OASIS SARIF v2.1.0** or **Markdown**.

---

### Workflow 3: Real-Time SSE Streaming & REST API

For IDE extensions, CLI tools, and automated pipelines, CodeSentinel provides a Server-Sent Events (SSE) streaming endpoint:

```bash
curl -N -X POST "http://127.0.0.1:8000/api/v1/review/stream" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{
    "files": [{"path": "server.py", "content": "import subprocess\ndef run(c): subprocess.call(c, shell=True)"}]
  }'
```

The server streams real-time stage updates (`static_analysis_started`, `agent_bug_detection_completed`, `verification_completed`, `remediation_finished`) followed by the full JSON result.

---

## 📂 Modular Directory Structure

```
code-review-agent/
├── .github/
│   └── workflows/
│       └── ai-code-review.yml       # GitHub Actions autonomous PR review workflow
├── backend/
│   ├── app/
│   │   ├── core/                    # Core configuration, schemas, and security
│   │   │   ├── auth.py              # JWT authentication, password hashing, RBAC
│   │   │   ├── config.py            # Pydantic environment settings
│   │   │   └── schemas.py           # Domain schemas (Findings, Revisions, Risk)
│   │   ├── db/                      # Database engine & sessions
│   │   │   └── session.py           # SQLite / PostgreSQL sessionmaker & seeders
│   │   ├── models/                  # SQLAlchemy ORM models
│   │   │   ├── user.py              # User, Role, and Profile entities
│   │   │   ├── review.py            # Review audit logs and saved findings
│   │   │   └── audit.py             # System event logs
│   │   ├── engine/                  # Cognitive multi-agent pipeline
│   │   │   ├── agents.py            # 7 specialist LLM review agents
│   │   │   ├── analysis.py          # Parallel analysis orchestrator
│   │   │   ├── consolidation.py     # Deduplication and semantic clustering
│   │   │   ├── llm.py               # Multi-provider LLM client (NVIDIA/OpenAI/Gemini)
│   │   │   ├── pipeline.py          # End-to-end review, verification & PR flow
│   │   │   ├── risk.py              # Posture grading, risk score calculation
│   │   │   └── verifier.py          # Skeptical independent self-verification
│   │   ├── remediation/             # Fix generation & validation
│   │   │   ├── fixer.py             # LLM fix generator + deterministic AST fallback
│   │   │   └── revalidation.py      # Automated validation gate (2nd cycle review)
│   │   ├── scanners/                # Static & dependency scanners
│   │   │   ├── static_analysis.py   # Pylint, Bandit, Radon, Deep AST checks
│   │   │   ├── secret_scanner.py    # High-entropy credential & secret detection
│   │   │   └── sca.py               # Dependency CVE scanning & CycloneDX SBOM
│   │   ├── services/                # Business services
│   │   │   ├── compliance.py        # SOC 2, PCI-DSS, HIPAA compliance engines
│   │   │   ├── dashboard.py         # Analytics & telemetry aggregator
│   │   │   ├── github_client.py     # GitHub REST API client
│   │   │   ├── jobs.py              # Asynchronous background job queue
│   │   │   └── policy_engine.py     # Enterprise quality gates & block rules
│   │   ├── routers/                 # FastAPI HTTP route handlers
│   │   │   ├── api.py               # REST API endpoints (/review, /revise, /sarif)
│   │   │   ├── auth.py              # Auth endpoints (/login, /register, /me)
│   │   │   └── ui.py                # Web dashboard server-rendered views
│   │   ├── utils/                   # Shared utilities
│   │   │   ├── cwe_mapping.py       # CWE & OWASP Top 10 taxonomy lookup
│   │   │   ├── report.py            # GitHub PR comments & markdown reports
│   │   │   ├── sarif.py             # OASIS SARIF v2.1.0 standard formatter
│   │   │   └── security.py          # HMAC verification & token utilities
│   │   ├── cli_review_pr.py         # Autonomous PR review CLI runner
│   │   └── main.py                  # FastAPI application factory
│   ├── main.py                      # Root backend entrypoint
│   └── requirements.txt             # Backend dependencies
├── frontend/                        # Web dashboard interface
│   ├── static/
│   │   ├── css/                     # Glassmorphism dark-mode stylesheets
│   │   ├── img/                     # SVG logos and icons
│   │   └── js/                      # Interactive frontend modules (diff, charts, auth)
│   └── templates/                   # HTML5 templates (dashboard, results, review)
├── tests/                           # Complete automated test suite (41 tests)
│   ├── test_advanced.py             # AST, SARIF, and taxonomy tests
│   ├── test_backend_structure.py    # Module separation & import tests
│   ├── test_core.py                 # Core analysis, verification & loop tests
│   ├── test_integrations_and_advanced.py # SCA, SBOM, quality gates & SSE tests
│   ├── test_jwt_auth.py             # Auth, RBAC, and dual authentication tests
│   └── test_pr_review.py            # GitHub PR review & auto-revision PR tests
├── pytest.ini                       # Pytest configuration
└── README.md                        # Documentation
```

---

## ⚡ Quickstart & Local Installation

### 1. Prerequisites
- **Python**: Version `3.11` or `3.12` installed.
- **Git**: Installed and configured.

### 2. Clone & Setup Virtual Environment
```bash
# Clone the repository
git clone https://github.com/Hemanthk7504/Code_review.git
cd Code_review

# Create and activate virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r backend/requirements.txt
```

### 3. Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Key environment variables:
```env
# Application Settings
APP_NAME="CodeSentinel Enterprise Code Review"
API_KEY="your-secret-api-key"

# JWT Authentication
JWT_SECRET_KEY="super-secret-jwt-signing-key"
JWT_ALGORITHM="HS256"

# LLM Provider (Optional: static review & deterministic fixes work 100% offline without keys!)
LLM_ENABLED=true
LLM_BASE_URL="https://integrate.api.nvidia.com/v1"
LLM_API_KEY=""
LLM_MODEL="nvidia/nemotron-3.5-lightning-30b-a3b"

# GitHub Token (Required for GitHub PR reviews)
GITHUB_TOKEN=""
BOT_BRANCH_PREFIX="ai-review/"
```

### 4. Launch the Server
```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

- **Web Portal**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Interactive Dashboard**: [http://127.0.0.1:8000/dashboard](http://127.0.0.1:8000/dashboard)
- **Interactive Swagger Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Specifications**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

### 5. Pre-Seeded Enterprise Accounts
| Email | Password | Role | Permissions |
|---|---|---|---|
| `admin@codesentinel.io` | `Admin@CodeSentinel2026!` | `admin` | Full system access, policy management, user administration |
| `reviewer@codesentinel.io` | `Reviewer@CodeSentinel2026!` | `reviewer` | Create reviews, trigger revisions, export reports |

---

## 🤖 GitHub Actions & CI/CD Setup

### 1. Enable GitHub Actions Pull Request Creation
In your GitHub repository:
1. Go to **Settings → Actions → General**.
2. Scroll to **Workflow permissions**:
   - Select **Read and write permissions**.
   - Check the box: **"Allow GitHub Actions to create and approve pull requests"**.
   - Click **Save**.

### 2. Workflow File (`.github/workflows/ai-code-review.yml`)
The workflow is pre-configured in `.github/workflows/ai-code-review.yml` and triggers automatically on:
- `pull_request: [opened, synchronize, reopened]`

```yaml
name: AI Code Review & Auto-Revision

on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  review:
    if: ${{ !startsWith(github.head_ref, 'ai-review/') }}
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write
      issues: write
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r backend/requirements.txt

      - name: Run Autonomous Review & Auto-Revision PR
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          python -m backend.app.cli_review_pr \
            --repo "${{ github.repository }}" \
            --pr ${{ github.event.pull_request.number }} \
            --token "$GITHUB_TOKEN"
```

### 3. Run Manually via CLI
You can run autonomous reviews from your local terminal or deployment pipelines anytime:
```bash
python -m backend.app.cli_review_pr --repo <owner/repo> --pr <number> --token <github_token>
```

---

## 📡 REST API Reference

| Category | Method | Path | Description | Auth Required |
|---|---|---|---|---|
| **Core UI** | `GET` | `/` | CodeSentinel Enterprise Web Portal | No |
| **Core UI** | `GET` | `/dashboard` | Interactive Web Dashboard | Yes (or cookie) |
| **Core UI** | `GET` | `/login` | User authentication screen | No |
| **Auth** | `POST` | `/api/v1/auth/login` | Login and receive JWT access/refresh tokens | No |
| **Auth** | `POST` | `/api/v1/auth/register` | Register new user account | No |
| **Auth** | `POST` | `/api/v1/auth/refresh` | Refresh expired access token | Yes |
| **Auth** | `GET` | `/api/v1/auth/me` | Fetch active user profile and roles | Yes |
| **Health** | `GET` | `/api/v1/health` | Health check & engine readiness status | No |
| **Metrics** | `GET` | `/api/v1/metrics` | System capabilities and active agents | No |
| **Review** | `POST` | `/api/v1/review` | Multi-agent + static review, risk scoring | Optional |
| **Revision** | `POST` | `/api/v1/revise` | Complete loop: review, fix, test, validate | Optional |
| **Stream** | `POST` | `/api/v1/review/stream` | Server-Sent Events (SSE) realtime review | Optional |
| **Playground**| `POST` | `/api/v1/audit/quick` | Fast single-snippet code audit | Optional |
| **GitHub** | `POST` | `/api/v1/github/pull-request` | Review a GitHub PR & open auto-revision PR | Yes |
| **GitHub** | `POST` | `/api/v1/github/webhook` | GitHub webhook receiver (HMAC SHA-256) | Signature |
| **Export** | `POST` | `/api/v1/export/sarif` | Export findings to OASIS SARIF v2.1.0 | Optional |
| **Export** | `POST` | `/api/v1/export/markdown` | Export report to GitHub-flavored Markdown | Optional |
| **Policies** | `GET` | `/api/v1/policies` | List active quality gates & rules | Yes |
| **Policies** | `POST` | `/api/v1/policies/evaluate` | Evaluate review against quality gates | Yes |
| **SCA** | `POST` | `/api/v1/sca/scan` | Scan dependencies for known CVEs | Yes |
| **SCA** | `POST` | `/api/v1/sca/sbom` | Export CycloneDX v1.5 JSON SBOM | Yes |
| **Compliance**| `POST` | `/api/v1/compliance/scorecard`| Generate SOC 2 / PCI-DSS / HIPAA scorecard| Yes |

---

## 🧪 Automated Verification & Test Suite

CodeSentinel features an automated test suite verifying all scanners, agents, token handling, AST transformations, and PR interactions without requiring an external paid LLM key.

Run the complete test suite:
```bash
python -m pytest tests/ -v
```

### Test Suite Breakdown (41 Tests, 100% Passing):
1. **`tests/test_core.py`** (11 tests):
   - JSON extraction and normalization.
   - Patch line parser (`changed_lines_from_patch`).
   - Static and AI finding consolidation.
   - Risk scoring ordering (security > quality > style).
   - Offline static review without LLM.
   - Syntax error reporting.
   - Full review loop with simulated fake LLM.
   - Rejection of invalid revisions by validation gate.
   - API endpoint contract validation.
   - API key enforcement.
   - Webhook HMAC SHA-256 signature verification.
2. **`tests/test_advanced.py`** (7 tests):
   - High-entropy secret and credential scanning.
   - Deep AST SQL injection and `shell=True` detection.
   - Deep AST pickle deserialization and missing HTTP timeout detection.
   - CWE and OWASP taxonomy mapping enrichment.
   - Security posture grading (`A+` to `F`) and top risk driver calculation.
   - OASIS SARIF v2.1.0 export schema compliance.
   - Advanced API endpoints.
3. **`tests/test_backend_structure.py`** (2 tests):
   - Folder separation integrity between `backend/` and `frontend/`.
   - Backward-compatibility aliases for legacy imports.
4. **`tests/test_integrations_and_advanced.py`** (6 tests):
   - Integrations list and webhook dispatcher tests.
   - Enterprise quality gates and policy evaluation.
   - Software Composition Analysis (SCA) & CycloneDX SBOM generation.
   - Regulatory compliance scorecards (SOC 2, PCI-DSS, HIPAA, OWASP).
   - Real-time review SSE streaming endpoint.
   - Advanced UI route rendering.
5. **`tests/test_jwt_auth.py`** (11 tests):
   - Pre-seeded account authentication.
   - Invalid credential rejection.
   - User registration and login lifecycle.
   - Refresh token rotation and exchange.
   - User profile endpoints.
   - RBAC permission enforcement (Admin vs Reviewer).
   - Dual authentication (Bearer JWT and X-API-Key).
   - Password changes and re-login verification.
   - Logout and UI login views.
   - Standalone landing page routing.
   - Dashboard authentication guards.
6. **`tests/test_pr_review.py`** (4 tests):
   - Pull request defect detection and automated revision PR creation.
   - Bot branch self-review loop prevention (`ai-review/*` ignore).
   - CLI review runner execution and exit code handling.
   - Relative-beyond-top-level import remediation and offline PR creation.

---

## 📄 License
This project is licensed under the Apache License 2.0.
