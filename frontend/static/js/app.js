/**
 * CodeSentinel Core Application Controller
 * Handles Theme, Sidebar Collapse, Command Palette (Cmd+K), Toasts, and Global Modals
 */

const App = {
  theme: 'system',

  init() {
    this.initTheme();
    this.initSidebar();
    this.initCommandPalette();
    this.initConnectionMonitor();
    this.initAuthUI();
    this.initKeybindings();
    this.initProcessGuide();
    this.initPageExplainers();
    this.initButtonEffects();
  },

  /* ==========================================================================
     Theme Controller
     ========================================================================== */
  initTheme() {
    const saved = localStorage.getItem('codesentinel_theme') || 'system';
    this.setTheme(saved, false);

    // Watch for OS preference changes when in system mode
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
      if (this.theme === 'system') {
        this.applyThemeToDOM('system');
      }
    });
  },

  setTheme(themeName, animate = true) {
    this.theme = themeName;
    localStorage.setItem('codesentinel_theme', themeName);

    if (animate) {
      document.documentElement.style.transition = 'background-color 300ms ease, color 300ms ease, border-color 300ms ease';
    }
    this.applyThemeToDOM(themeName);
    this.updateThemeMenuUI(themeName);
  },

  applyThemeToDOM(themeName) {
    let resolved = themeName;
    if (themeName === 'system') {
      resolved = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    document.documentElement.setAttribute('data-theme', resolved);
  },

  updateThemeMenuUI(themeName) {
    const iconContainer = document.getElementById('theme-btn-icon');
    if (!iconContainer) return;
    if (themeName === 'dark') {
      iconContainer.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>`;
    } else if (themeName === 'light') {
      iconContainer.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>`;
    } else {
      iconContainer.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect><line x1="8" y1="21" x2="16" y2="21"></line><line x1="12" y1="17" x2="12" y2="21"></line></svg>`;
    }
  },

  /* ==========================================================================
     Sidebar Controller
     ========================================================================== */
  initSidebar() {
    const isCollapsed = localStorage.getItem('codesentinel_sidebar_collapsed') === 'true';
    const sidebar = document.getElementById('app-sidebar');
    if (sidebar && isCollapsed) {
      sidebar.classList.add('sidebar-collapsed');
    }
  },

  toggleSidebar() {
    const sidebar = document.getElementById('app-sidebar');
    if (!sidebar) return;
    const isCollapsed = sidebar.classList.toggle('sidebar-collapsed');
    localStorage.setItem('codesentinel_sidebar_collapsed', isCollapsed);
  },

  toggleMobileSidebar() {
    const sidebar = document.getElementById('app-sidebar');
    const backdrop = document.getElementById('mobile-drawer-backdrop');
    if (!sidebar) return;
    const open = sidebar.classList.toggle('mobile-open');
    if (backdrop) backdrop.classList.toggle('active', open);
  },

  /* ==========================================================================
     Command Palette (Cmd/Ctrl + K)
     ========================================================================== */
  initCommandPalette() {
    const input = document.getElementById('cmd-palette-input');
    if (!input) return;

    input.addEventListener('input', (e) => this.filterCommandPalette(e.target.value));
    input.addEventListener('keydown', (e) => this.navigateCommandPalette(e));
  },

  openCommandPalette() {
    const backdrop = document.getElementById('cmd-palette-backdrop');
    const input = document.getElementById('cmd-palette-input');
    if (backdrop) {
      backdrop.classList.add('active');
      if (input) {
        input.value = '';
        input.focus();
        this.filterCommandPalette('');
      }
    }
  },

  closeCommandPalette() {
    const backdrop = document.getElementById('cmd-palette-backdrop');
    if (backdrop) backdrop.classList.remove('active');
  },

  getCommandItems() {
    return [
      { id: 'nav-dashboard', title: 'Go to Dashboard', category: 'Navigation', icon: 'layout-dashboard', action: () => window.location.href = '/dashboard' },
      { id: 'nav-new-review', title: 'New Code Review', category: 'Actions', icon: 'plus-circle', action: () => window.location.href = '/review/new' },
      { id: 'nav-results', title: 'View Review Results', category: 'Navigation', icon: 'shield-check', action: () => window.location.href = '/review/results' },
      { id: 'nav-revisions', title: 'Automated Revisions & Diffs', category: 'Navigation', icon: 'git-pull-request', action: () => window.location.href = '/revisions' },
      { id: 'nav-prs', title: 'GitHub Pull Requests', category: 'Navigation', icon: 'git-merge', action: () => window.location.href = '/pull-requests' },
      { id: 'nav-dependencies', title: 'Dependencies & SBOM (SCA)', category: 'Security', icon: 'package', action: () => window.location.href = '/dependencies' },
      { id: 'nav-policies', title: 'Quality Gates & Policies', category: 'Governance', icon: 'shield', action: () => window.location.href = '/policies' },
      { id: 'nav-compliance', title: 'Regulatory Compliance (OWASP/SOC2)', category: 'Governance', icon: 'award', action: () => window.location.href = '/compliance' },
      { id: 'nav-analytics', title: 'Security & Quality Analytics', category: 'Navigation', icon: 'bar-chart-2', action: () => window.location.href = '/analytics' },
      { id: 'nav-integrations', title: 'Integrations Hub (Slack/Jira/Datadog)', category: 'Enterprise', icon: 'plug', action: () => window.location.href = '/integrations' },
      { id: 'nav-repos', title: 'Repositories (Preview)', category: 'Enterprise', icon: 'folder-git-2', action: () => window.location.href = '/repositories' },
      { id: 'nav-audit', title: 'Audit Log (Preview)', category: 'Enterprise', icon: 'file-text', action: () => window.location.href = '/audit-log' },
      { id: 'nav-team', title: 'Team & Access (Preview)', category: 'Enterprise', icon: 'users', action: () => window.location.href = '/team' },
      { id: 'nav-settings', title: 'Platform Settings & Engine Config', category: 'Settings', icon: 'settings', action: () => window.location.href = '/settings' },
      { id: 'act-theme-dark', title: 'Switch to Dark Theme', category: 'Appearance', icon: 'moon', action: () => this.setTheme('dark') },
      { id: 'act-theme-light', title: 'Switch to Light Theme', category: 'Appearance', icon: 'sun', action: () => this.setTheme('light') },
      { id: 'act-theme-system', title: 'Follow System Theme', category: 'Appearance', icon: 'monitor', action: () => this.setTheme('system') },
      { id: 'act-signin', title: 'Sign In / Switch User (JWT)', category: 'Authentication', icon: 'log-in', action: () => window.location.href = '/login' },
      { id: 'act-signout', title: 'Sign Out (End Session)', category: 'Authentication', icon: 'log-out', action: () => API.logout() }
    ];
  },

  filterCommandPalette(query) {
    const list = document.getElementById('cmd-palette-results');
    if (!list) return;

    const q = query.toLowerCase().trim();
    const items = this.getCommandItems().filter(item =>
      !q || item.title.toLowerCase().includes(q) || item.category.toLowerCase().includes(q)
    );

    if (items.length === 0) {
      list.innerHTML = `<div style="padding: 24px; text-align: center; color: var(--color-text-muted); font-size: var(--text-sm);">No matching commands found</div>`;
      return;
    }

    list.innerHTML = items.map((item, idx) => `
      <div class="cmd-item ${idx === 0 ? 'selected' : ''}" data-index="${idx}" onclick="App.executeCommand(${idx})">
        <div style="display: flex; align-items: center; gap: 10px;">
          <span style="color: var(--color-primary); font-size: 16px;">✦</span>
          <span>${item.title}</span>
        </div>
        <kbd>${item.category}</kbd>
      </div>
    `).join('');
    this._filteredCommands = items;
  },

  navigateCommandPalette(e) {
    const items = document.querySelectorAll('.cmd-item');
    if (!items.length) return;

    let selectedIdx = Array.from(items).findIndex(el => el.classList.contains('selected'));

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      selectedIdx = (selectedIdx + 1) % items.length;
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      selectedIdx = (selectedIdx - 1 + items.length) % items.length;
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (selectedIdx >= 0) this.executeCommand(selectedIdx);
      return;
    } else if (e.key === 'Escape') {
      this.closeCommandPalette();
      return;
    }

    items.forEach((el, idx) => el.classList.toggle('selected', idx === selectedIdx));
    if (items[selectedIdx]) {
      items[selectedIdx].scrollIntoView({ block: 'nearest' });
    }
  },

  executeCommand(idx) {
    if (this._filteredCommands && this._filteredCommands[idx]) {
      const cmd = this._filteredCommands[idx];
      this.closeCommandPalette();
      cmd.action();
    }
  },

  /* ==========================================================================
     Toast Notifications
     ========================================================================== */
  showToast(title, message = '', type = 'info', duration = 4000) {
    let container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      container.className = 'toast-container';
      document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    const icons = {
      success: '✓',
      error: '✕',
      warning: '⚠',
      info: 'ℹ'
    };

    toast.innerHTML = `
      <div style="font-weight: 700; color: var(--color-${type === 'info' ? 'primary' : (type === 'error' ? 'critical' : type)}); font-size: 16px;">
        ${icons[type] || 'ℹ'}
      </div>
      <div style="flex: 1;">
        <div style="font-weight: 600; font-size: var(--text-sm); color: var(--color-text);">${title}</div>
        ${message ? `<div style="font-size: var(--text-xs); color: var(--color-text-secondary); margin-top: 2px;">${message}</div>` : ''}
      </div>
      <button style="background: none; border: none; color: var(--color-text-muted); cursor: pointer; padding: 2px;" onclick="this.parentElement.remove()">✕</button>
    `;

    container.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add('show'));

    if (duration > 0) {
      setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
      }, duration);
    }
  },

  /* ==========================================================================
     API Key & Connection Settings Modal
     ========================================================================== */
  openApiKeyModal() {
    const modal = document.getElementById('api-key-modal');
    if (!modal) return;
    const keyInput = document.getElementById('modal-api-key-input');
    const urlInput = document.getElementById('modal-api-url-input');
    if (keyInput) keyInput.value = API.getApiKey();
    if (urlInput) urlInput.value = API.getBaseUrl();
    modal.classList.add('active');
  },

  closeApiKeyModal() {
    const modal = document.getElementById('api-key-modal');
    if (modal) modal.classList.remove('active');
  },

  saveApiKeyFromModal() {
    const keyInput = document.getElementById('modal-api-key-input');
    const urlInput = document.getElementById('modal-api-url-input');
    if (keyInput) API.setApiKey(keyInput.value);
    if (urlInput) API.setBaseUrl(urlInput.value);
    this.closeApiKeyModal();
    this.showToast('Settings Saved', 'API Key & Base URL successfully updated.', 'success');
  },

  /* ==========================================================================
     Live Connection Monitor
     ========================================================================== */
  initConnectionMonitor() {
    API.initHealthMonitor((status) => {
      const pill = document.getElementById('topbar-connection-pill');
      if (!pill) return;

      if (status.online) {
        const llmStatus = status.llm_enabled ? 'LLM On' : 'Static Only';
        pill.innerHTML = `
          <span class="dot-indicator dot-success live-pulse"></span>
          <span>Connected</span>
          <span class="badge badge-neutral" style="font-size: 10px; padding: 1px 6px;">${llmStatus}</span>
        `;
      } else {
        pill.innerHTML = `
          <span class="dot-indicator dot-danger"></span>
          <span>Offline</span>
        `;
      }
    });
  },

  /* ==========================================================================
     Authentication & User State UI
     ========================================================================== */
  async initAuthUI() {
    const path = window.location.pathname;
    const isPublicPage = path === '/' || path === '' || path.startsWith('/login');
    const token = API.getToken();

    // Strict route protection: unauthenticated users cannot access dashboard or console views
    if (!isPublicPage && !token) {
      window.location.replace('/login');
      return;
    }

    const userArea = document.getElementById('topbar-user-area');
    if (!userArea) return;

    const user = API.getUser();
    if (user && user.username) {
      this.renderUserArea(user);
    } else if (token) {
      try {
        const profile = await API.getProfile();
        API.setUser(profile);
        this.renderUserArea(profile);
      } catch (err) {
        if (!isPublicPage) {
          API.clearAuth();
          window.location.replace('/login');
          return;
        }
      }
    } else {
      userArea.innerHTML = `
        <a href="/login" class="btn btn-ghost btn-sm" style="display: flex; align-items: center; gap: 6px;" title="Sign In with JWT">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"></path><polyline points="10 17 15 12 10 7"></polyline><line x1="15" y1="12" x2="3" y2="12"></line></svg>
          <span>Sign In</span>
        </a>
      `;
    }
  },

  renderUserArea(user) {
    const userArea = document.getElementById('topbar-user-area');
    if (!userArea) return;

    const initials = (user.full_name || user.username)
      .split(' ')
      .map(n => n[0])
      .join('')
      .slice(0, 2)
      .toUpperCase();

    const role = user.role || 'viewer';
    userArea.innerHTML = `
      <div class="user-menu-pill" title="Logged in as ${user.full_name || user.username} (${role})">
        <div class="user-avatar-circle">${initials}</div>
        <span class="user-name-label">${user.username}</span>
        <span class="user-role-badge user-role-${role}">${role}</span>
        <button class="btn btn-ghost btn-sm btn-icon-only" onclick="event.stopPropagation(); API.logout();" title="Sign Out" style="padding: 2px 4px; margin-left: 2px;">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path><polyline points="16 17 21 12 16 7"></polyline><line x1="21" y1="12" x2="9" y2="12"></line></svg>
        </button>
      </div>
    `;
  },

  /* ==========================================================================
     Global Keyboard Shortcuts
     ========================================================================== */
  initKeybindings() {
    document.addEventListener('keydown', (e) => {
      // Cmd/Ctrl + K opens Command Palette
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        const backdrop = document.getElementById('cmd-palette-backdrop');
        if (backdrop && backdrop.classList.contains('active')) {
          this.closeCommandPalette();
        } else {
          this.openCommandPalette();
        }
      }
      // Cmd/Ctrl + / toggles Process & Architecture Guide
      if ((e.metaKey || e.ctrlKey) && e.key === '/') {
        e.preventDefault();
        this.toggleProcessGuide();
      }
      // Escape closes open modals & drawers
      if (e.key === 'Escape') {
        this.closeCommandPalette();
        this.closeApiKeyModal();
        this.closeProcessGuide();
        const drawerBackdrop = document.querySelector('.drawer-backdrop.active');
        if (drawerBackdrop) drawerBackdrop.classList.remove('active');
      }
    });
  },

  /* ==========================================================================
     Page Explainers & Global Process Guide Drawer
     ========================================================================== */
  activeGuidePage: 'dashboard',

  processGuideData: {
    dashboard: {
      name: 'Dashboard',
      icon: '📊',
      title: 'Security & Risk Posture Dashboard',
      subtitle: 'Central command for code review telemetry, posture scoring, and CWE distributions',
      steps: [
        { num: '01', title: 'Data Aggregation', desc: 'Queries SQLite audit storage for historical scan metrics, files analyzed, and defect counts.' },
        { num: '02', title: 'CVSS 3.1 Risk Scoring', desc: 'Computes continuous composite risk scores (0-100) based on severity distributions and finding counts.' },
        { num: '03', title: 'Posture Grading', desc: 'Assigns definitive letter grades (A+ through F) based on risk ceiling criteria and high-severity presence.' },
        { num: '04', title: 'CWE Taxonomy Grouping', desc: 'Maps corroborated findings to MITRE Common Weakness Enumeration standards (e.g. CWE-89, CWE-798).' }
      ],
      underTheHood: [
        'Composite risk formula weights Critical (35pts), High (20pts), Medium (10pts), and Low (2pts) with non-linear saturation.',
        'Skeptical self-verification monitors track refuted false positive rates to ensure LLM agent fidelity.',
        'Continuous synchronization with background GitHub Actions and webhook workers.'
      ],
      howToUse: [
        'Inspect the Risk Gauge and Posture Grade to evaluate release readiness.',
        'Click into "Top Security Risks" to jump directly into line-level code evidence.',
        'Use the quick action buttons to dispatch a new review or inspect a GitHub Pull Request.'
      ],
      glossary: [
        { term: 'CVSS 3.1', desc: 'Common Vulnerability Scoring System standard for security defect severity.' },
        { term: 'Posture Grade', desc: 'A+ (0-15 risk) to F (75+ risk) enterprise health rating.' },
        { term: 'Refuted', desc: 'Hallucinations or false alarms discarded by the self-verification auditor.' }
      ]
    },
    new_review: {
      name: 'New Review',
      icon: '⚡',
      title: 'Review Code & Autonomous Reflexion Revision',
      subtitle: 'Interactive multi-file code editor with real-time SSE execution telemetry',
      steps: [
        { num: '01', title: 'Static SAST Scanners', desc: 'Bandit SAST, Pylint AST, Radon Complexity, and Shannon Entropy secret scanners execute in parallel.' },
        { num: '02', title: 'Multi-Agent AI Consensus', desc: 'Security, Logic Bug, Quality, Performance, and Architecture specialists analyze AST semantics.' },
        { num: '03', title: 'Consolidation & Merge', desc: 'Deduplicates findings, calculates CVSS base scores, and maps MITRE CWE tags.' },
        { num: '04', title: 'Reflexion Auto-Repair', desc: 'Synthesizes verified AST fixes, runs compile gate, and verifies 0 regressions.' }
      ],
      underTheHood: [
        'Real-time streaming via Server-Sent Events (SSE) `/api/v1/review/stream` displays live terminal output.',
        'Offline fallback: Deterministic AST transform engine repairs bare exceptions, eval injections, and missing timeouts without requiring cloud LLMs.',
        'Syntax verification gate validates ast.parse() on every modified file prior to accepting patches.'
      ],
      howToUse: [
        'Paste code directly or drag and drop multiple .py files into the tabbed editor.',
        'Click "Review Only" for read-only static + AI analysis.',
        'Click "Review and Auto-Revise (Full Loop)" to synthesize verified fixes and companion unit tests.'
      ],
      glossary: [
        { term: 'Full Loop', desc: 'Complete review -> verify -> fix -> re-validate reflection loop.' },
        { term: 'SSE Stream', desc: 'Server-Sent Events streaming live execution telemetry to the terminal.' },
        { term: 'AST Transform', desc: 'Safe syntax tree rewriting that preserves code formatting.' }
      ]
    },
    results: {
      name: 'Review Results',
      icon: '🛡️',
      title: 'Audit Results & Evidence Explorer',
      subtitle: 'Line-by-line defect inspection, multi-tool corroboration, and remediated code preview',
      steps: [
        { num: '01', title: 'Evidence Corroboration', desc: 'Cross-checks detections across Bandit, Pylint, AST, and AI agents.' },
        { num: '02', title: 'Verification Audit', desc: 'Flags findings as Verified, Uncertain, or Refuted based on AST backing.' },
        { num: '03', title: 'CWE Categorization', desc: 'Enriches defects with CWE-ID, OWASP Top 10 category, and risk score.' },
        { num: '04', title: 'Export & Remediation', desc: 'Enables one-click OASIS SARIF v2.1.0, Markdown, and revised code downloads.' }
      ],
      underTheHood: [
        'Refuted false positives are kept in an audit-accessible view rather than silently deleted.',
        'SARIF 2.1.0 exporter enables direct integration with GitHub Code Scanning alerts.',
        'Remediated code viewer applies verified patch lines in descending index order to avoid line drift.'
      ],
      howToUse: [
        'Filter findings by Severity, Category, Verification Status, or search by keyword.',
        'Click "⚡ View Remediated Code" to preview, copy, or download the fully patched Python file.',
        'Inspect the "Pipeline Execution Audit Trail" tab to verify all static tools and validation gates.'
      ],
      glossary: [
        { term: 'Corroboration', desc: 'Two or more independent engines confirming the same defect.' },
        { term: 'SARIF', desc: 'Static Analysis Results Interchange Format for GitHub and CI/CD tools.' },
        { term: 'Line Replacement', desc: 'Deterministic patch targeting the exact offending line number.' }
      ]
    },
    revisions: {
      name: 'Revisions & Diffs',
      icon: '🔄',
      title: 'Automated Code Revisions & Interactive Diffs',
      subtitle: 'Side-by-side differential viewer with validation gate diagnostics and companion unit tests',
      steps: [
        { num: '01', title: 'Differential Synthesis', desc: 'Generates line-by-line unified and side-by-side visual diffs.' },
        { num: '02', title: 'AST Syntax Gate', desc: 'Compiles revised source to ensure zero syntax or indentation errors.' },
        { num: '03', title: 'Regression Gate', desc: 'Re-runs static analysis on revised code to verify 0 new flaws were introduced.' },
        { num: '04', title: 'Unit Test Synthesis', desc: 'Generates pytest test functions targeting the specific fixed defects.' }
      ],
      underTheHood: [
        'Validation ratio compares targeted findings against resolved findings (resolution_ratio >= 1.0).',
        'Multi-file tab switcher preserves revision state across all uploaded files in the session.',
        'Supports standard .patch file downloads compatible with git apply.'
      ],
      howToUse: [
        'Toggle between "Side-by-Side" and "Unified" diff modes to inspect changes.',
        'Inspect the Validation Gate metrics: targeted vs resolved issues and risk delta.',
        'Click "Copy Revised Code" or "Download Patch" to merge into your codebase.'
      ],
      glossary: [
        { term: 'Risk Delta', desc: 'The mathematical reduction in CVSS risk score between original and revised code.' },
        { term: 'Regression Gate', desc: 'Safety check ensuring a fix did not introduce secondary bugs.' },
        { term: 'Unit Test Gate', desc: 'Generated automated test asserting the defect is fixed.' }
      ]
    },
    pull_requests: {
      name: 'Pull Requests',
      icon: '🔀',
      title: 'GitHub Pull Request Review & Autonomous PR Dispatch',
      subtitle: 'Continuous CI/CD review agent that reviews PRs and opens separate fix pull requests',
      steps: [
        { num: '01', title: 'GitHub Handshake', desc: 'Fetches PR metadata, patch diffs, and head commit SHA from GitHub API.' },
        { num: '02', title: 'Diff Analysis', desc: 'Extracts modified Python files and focuses analysis on changed lines.' },
        { num: '03', title: 'Remediation Loop', desc: 'Synthesizes verified AST fixes for detected bugs and vulnerabilities.' },
        { num: '04', title: 'PR Creation', desc: 'Creates branch ai-review/pr-X-XXXXXX, commits fixes, and opens a new PR.' }
      ],
      underTheHood: [
        'Webhook listener /api/v1/github/webhook verifies HMAC-SHA256 signatures using GITHUB_WEBHOOK_SECRET.',
        'Background job runner polls state every 3 seconds and updates live terminal logs.',
        'Dual-target fallback: Targets PR head branch first; falls back to repository base branch if fork permissions require.'
      ],
      howToUse: [
        'Specify GitHub repository (owner/repo) and PR number.',
        'Optionally provide a personal GitHub Access Token with pull-requests: write permission.',
        'Click "Dispatch Background Review Job" and watch the live 7-stage tracker and terminal feed.'
      ],
      glossary: [
        { term: 'Bot Branch', desc: 'Dedicated git branch prefixed with ai-review/ containing verified fixes.' },
        { term: 'PR Comment', desc: 'Markdown audit summary posted directly into the original GitHub PR conversation.' },
        { term: 'Target Fallback', desc: 'Intelligent PR retargeting handling cross-fork pull requests.' }
      ]
    },
    dependencies: {
      name: 'Dependencies',
      icon: '📦',
      title: 'Software Composition Analysis (SCA) & SBOM',
      subtitle: 'Supply-chain vulnerability scanner and CycloneDX v1.5 SBOM generator',
      steps: [
        { num: '01', title: 'Manifest Parsing', desc: 'Parses requirements.txt, pyproject.toml, and Pipfile packages and pinned versions.' },
        { num: '02', title: 'NVD & Advisory Lookup', desc: 'Cross-checks dependencies against known NIST CVEs and PyPA vulnerability databases.' },
        { num: '03', title: 'Risk Aggregation', desc: 'Ranks vulnerable packages by CVSS score and provides fixed safe versions.' },
        { num: '04', title: 'CycloneDX SBOM Export', desc: 'Formats components, hashes, licenses, and purls into OASIS CycloneDX JSON.' }
      ],
      underTheHood: [
        'Directly maps to Executive Order 14028 supply-chain transparency requirements.',
        'CycloneDX v1.5 compliant structure includes component purl, versions, and security metadata.',
        'Detects critical CVEs including Request Header Injection and Cryptography Buffer Overflows.'
      ],
      howToUse: [
        'Paste your project dependencies into the package manifest editor.',
        'Click "Scan Manifest Now" to view all detected supply-chain CVEs.',
        'Click "Download CycloneDX SBOM" to export compliance-ready JSON documentation.'
      ],
      glossary: [
        { term: 'SBOM', desc: 'Software Bill of Materials — formal list of software components and dependencies.' },
        { term: 'CycloneDX', desc: 'OWASP-backed enterprise standard for software supply chain security.' },
        { term: 'CVE', desc: 'Common Vulnerabilities and Exposures dictionary identifier.' }
      ]
    },
    policies: {
      name: 'Quality Gates',
      icon: '🚪',
      title: 'Quality Gates & Enterprise Policy Engine',
      subtitle: 'Zero-trust governance rules enforcing automated merge blockers in CI/CD',
      steps: [
        { num: '01', title: 'Policy Definition', desc: 'Configures acceptable risk ceilings, finding limits, and mandatory blockers.' },
        { num: '02', title: 'Review Evaluation', desc: 'Evaluates findings from the latest review against active gate thresholds.' },
        { num: '03', title: 'Violation Analysis', desc: 'Identifies specific rule violations that caused a policy failure.' },
        { num: '04', title: 'Enforcement Decision', desc: 'Issues definitive PASSED or BLOCKED verdict to CI/CD pipelines.' }
      ],
      underTheHood: [
        'Rules engine evaluates: max risk threshold, critical blockers, high blockers, and hardcoded secrets.',
        'Specialized blocker flags for CWE-94 (Arbitrary Code Injection) and CWE-89 (SQL Injection).',
        'Policy configuration persists across engine restarts in SQLite storage.'
      ],
      howToUse: [
        'Adjust the Maximum Allowed Risk Score slider (e.g. 35.0).',
        'Toggle enforcement checkboxes for critical flaws, secrets, and injection vulnerabilities.',
        'Click "Save Active Policy", then click "Evaluate Last Review" to test enforcement.'
      ],
      glossary: [
        { term: 'Quality Gate', desc: 'Automated milestone check that must pass before code can be merged.' },
        { term: 'Merge Blocker', desc: 'A critical security finding that halts automated PR merging.' },
        { term: 'Zero Trust', desc: 'Security model that validates every commit regardless of author.' }
      ]
    },
    compliance: {
      name: 'Compliance',
      icon: '📜',
      title: 'Regulatory Compliance Scorecards',
      subtitle: 'Automated vulnerability attribution to OWASP Top 10, SOC 2, and PCI-DSS',
      steps: [
        { num: '01', title: 'Finding Attribution', desc: 'Translates CWE finding IDs into regulatory control numbers.' },
        { num: '02', title: 'Control Evaluation', desc: 'Determines whether each framework requirement is COMPLIANT or NON_COMPLIANT.' },
        { num: '03', title: 'Scorecard Synthesis', desc: 'Calculates compliance percentages and identifies specific failing lines.' },
        { num: '04', title: 'Audit Certification', desc: 'Generates printable certificates and JSON audit records for external auditors.' }
      ],
      underTheHood: [
        'OWASP Top 10 (2021) covers A01 through A10 controls with direct CWE mapping.',
        'SOC 2 Type II evaluates Security, Confidentiality, and Processing Integrity Trust Services Criteria.',
        'PCI-DSS v4.0 evaluates payment application security controls and data protection.'
      ],
      howToUse: [
        'Select the desired standard (OWASP Top 10, SOC 2, or PCI-DSS).',
        'Review individual control items and inspect the non-compliant code findings.',
        'Click "Print Certificate" or "Export Audit JSON" to provide evidence to compliance auditors.'
      ],
      glossary: [
        { term: 'OWASP Top 10', desc: 'Standard awareness document for developers on web application security.' },
        { term: 'SOC 2 Type II', desc: 'Auditing procedure ensuring service providers securely manage customer data.' },
        { term: 'PCI-DSS', desc: 'Payment Card Industry Data Security Standard for cardholder data protection.' }
      ]
    },
    integrations: {
      name: 'Integrations',
      icon: '🔌',
      title: 'Integrations Hub & CI/CD Telemetry',
      subtitle: 'Connect CodeSentinel to ChatOps, Prometheus metrics, and live repository status badges',
      steps: [
        { num: '01', title: 'Connector Handshake', desc: 'Establishes webhook communication with Slack, Teams, and Discord.' },
        { num: '02', title: 'Prometheus Exposition', desc: 'Exports real-time metrics in OpenMetrics exposition format.' },
        { num: '03', title: 'SVG Badge Generation', desc: 'Renders dynamic vector status badges showing current security grade.' },
        { num: '04', title: 'Audit Dispatching', desc: 'Forwards security events to SIEM systems like Splunk or Datadog.' }
      ],
      underTheHood: [
        'Prometheus metrics endpoint /api/v1/integrations/metrics/prometheus exposes gauge and counter metrics.',
        'Dynamic SVG badges can be embedded directly into markdown headers (/api/v1/badge/status.svg).',
        'Webhook dispatcher includes timeout safeguards and response code validation.'
      ],
      howToUse: [
        'Click "Add Integration" to configure a Slack or Teams notification webhook.',
        'Click "Prometheus Metrics" to view OpenMetrics telemetry for Prometheus/Grafana.',
        'Click "Copy Badge Markdown" to paste a live security badge into your README.'
      ],
      glossary: [
        { term: 'Prometheus', desc: 'Cloud Native Computing Foundation open-source monitoring and alerting toolkit.' },
        { term: 'OpenMetrics', desc: 'Standard format for exposing metrics from cloud applications.' },
        { term: 'ChatOps', desc: 'Managing development and security operations via chat tools like Slack.' }
      ]
    },
    analytics: {
      name: 'Analytics',
      icon: '📈',
      title: 'Risk Analytics & Trend Intelligence',
      subtitle: 'Historical risk score velocity, defect density metrics, and posture trends',
      steps: [
        { num: '01', title: 'Temporal Tracking', desc: 'Records risk scores, files analyzed, and verified defects across time.' },
        { num: '02', title: 'Velocity Calculation', desc: 'Measures Mean Time to Remediate (MTTR) and defect resolution rates.' },
        { num: '03', title: 'Severity Drift', desc: 'Tracks shifting distributions between critical, high, and medium defects.' },
        { num: '04', title: 'Posture Forecasting', desc: 'Projects security health trajectories based on historical remediation speed.' }
      ],
      underTheHood: [
        'Time-series aggregation groups audit events by day, week, and month.',
        'Chart.js interactive visualizations render smooth animations with responsive resizing.',
        'Correlates tool detections with developer fix acceptance rates.'
      ],
      howToUse: [
        'Inspect the Risk Trend chart to ensure overall vulnerability scores are declining.',
        'Analyze the Findings by Category chart to identify common defect patterns.',
        'Use velocity metrics to evaluate security engineering productivity.'
      ],
      glossary: [
        { term: 'MTTR', desc: 'Mean Time to Remediate — average time taken to repair a verified security vulnerability.' },
        { term: 'Defect Density', desc: 'Number of verified defects per 1,000 lines of code (KLOC).' },
        { term: 'Severity Drift', desc: 'The trend of vulnerabilities shifting toward lower severity over time.' }
      ]
    },
    audit_log: {
      name: 'Audit Log',
      icon: '📋',
      title: 'Enterprise Audit Trail & Forensic Records',
      subtitle: 'Immutable record of user actions, policy updates, reviews, and authentication events',
      steps: [
        { num: '01', title: 'Event Capture', desc: 'Captures all administrative and review actions with authenticated user context.' },
        { num: '02', title: 'IP & Session Tracking', desc: 'Records client IP addresses, user agents, and authorization methods.' },
        { num: '03', title: 'SQLite Persistence', desc: 'Stores events in an immutable, queryable database table.' },
        { num: '04', title: 'Forensic Audit View', desc: 'Provides searchable, filterable logs for compliance verification.' }
      ],
      underTheHood: [
        'Audit middleware automatically logs reviews, policy modifications, and logins.',
        'Events are tamper-evident and timestamped with ISO 8601 UTC standards.',
        'Satisfies SOC 2 CC6.8 and ISO 27001 A.12.4 logging requirements.'
      ],
      howToUse: [
        'Search audit logs by username, action type, or IP address.',
        'Review timestamps to investigate security policy modifications or permission changes.',
        'Export audit trails for external compliance auditors.'
      ],
      glossary: [
        { term: 'Audit Trail', desc: 'A chronological record providing documentary evidence of the sequence of activities.' },
        { term: 'Forensic Record', desc: 'Immutable log entry suitable for post-incident security analysis.' },
        { term: 'ISO 27001', desc: 'International standard for managing information security.' }
      ]
    },
    repositories: {
      name: 'Repositories',
      icon: '📁',
      title: 'Managed Code Repositories & Branch Tracking',
      subtitle: 'Manage monitored GitHub, GitLab, and Bitbucket repos and schedule automated scans',
      steps: [
        { num: '01', title: 'Repo Connection', desc: 'Links GitHub repositories via personal access tokens or OAuth.' },
        { num: '02', title: 'Branch Tracking', desc: 'Monitors default branches (main/master) for new push events and pull requests.' },
        { num: '03', title: 'Scheduled Scans', desc: 'Executes recurring nighttime security audits and dependency scans.' },
        { num: '04', title: 'Posture Baseline', desc: 'Establishes repository baseline scores to detect security regressions.' }
      ],
      underTheHood: [
        'Uses GitHub REST API to list branches, commits, and pull requests.',
        'Stores repository configurations with encrypted token credentials.',
        'Triggers automated reviews upon push and pull_request webhook events.'
      ],
      howToUse: [
        'Connect your GitHub repository using the repository URL.',
        'Configure branch monitoring rules for automated review triggers.',
        'View the latest baseline posture grade for each managed project.'
      ],
      glossary: [
        { term: 'Baseline', desc: 'The starting security score against which new commits are compared.' },
        { term: 'Branch Tracking', desc: 'Monitoring specific git branches for code changes.' },
        { term: 'Webhook Trigger', desc: 'Automated event sent by GitHub when code is pushed.' }
      ]
    },
    team: {
      name: 'Team & Access',
      icon: '👥',
      title: 'Role-Based Access Control (RBAC) & Team Management',
      subtitle: 'User accounts, permissions, JWT authentication, and API key provisioning',
      steps: [
        { num: '01', title: 'Authentication', desc: 'Verifies user identity using cryptographically signed JWT bearer tokens.' },
        { num: '02', title: 'Role Assignment', desc: 'Assigns users to Administrator, Reviewer, or Viewer roles.' },
        { num: '03', title: 'Permission Enforcement', desc: 'Guards endpoints and UI views using strict role-based claims.' },
        { num: '04', title: 'API Key Management', desc: 'Provisions service API keys for CI/CD runners and automated pipelines.' }
      ],
      underTheHood: [
        'JWT tokens are signed using HMAC-SHA256 with secure 8-hour expiration and refresh exchange.',
        'Admins have full write permissions; Reviewers can run reviews and auto-repair; Viewers are read-only.',
        'Dual-authentication allows requests with either Bearer tokens or X-API-Key headers.'
      ],
      howToUse: [
        'Inspect active team members and their assigned roles.',
        'Generate new user accounts with appropriate least-privilege permissions.',
        'Revoke or regenerate API keys for automated CI/CD runners.'
      ],
      glossary: [
        { term: 'RBAC', desc: 'Role-Based Access Control restricting system access to authorized users.' },
        { term: 'JWT', desc: 'JSON Web Token — open standard (RFC 7519) for securely transmitting information.' },
        { term: 'Least Privilege', desc: 'Security practice of granting users only the minimum access needed.' }
      ]
    },
    settings: {
      name: 'Settings',
      icon: '⚙️',
      title: 'Engine Configuration & Model Settings',
      subtitle: 'Configure static tool execution, LLM models, and reflexion retry limits',
      steps: [
        { num: '01', title: 'Scanner Selection', desc: 'Enable or disable Bandit, Pylint, Radon, AST Scanner, and Secret Scanner.' },
        { num: '02', title: 'LLM Engine Setup', desc: 'Configure OpenAI, Anthropic, or Google Gemini API keys and model parameters.' },
        { num: '03', title: 'Reflexion Tuning', desc: 'Configure maximum auto-repair retry attempts (default: 3 iterations).' },
        { num: '04', title: 'GitHub Integration', desc: 'Configure bot branch prefixes, GitHub tokens, and webhook secrets.' }
      ],
      underTheHood: [
        'Settings are backed by Pydantic BaseSettings reading environment variables and .env files.',
        'Dynamic engine toggles allow CodeSentinel to operate 100% offline using deterministic AST tools.',
        'Shannon entropy threshold can be calibrated to balance secret detection against false alarms.'
      ],
      howToUse: [
        'Toggle individual static scanners based on your project requirements.',
        'Configure your LLM provider API key to activate AI specialist agents.',
        'Save configuration and verify engine readiness via the live connection badge.'
      ],
      glossary: [
        { term: 'Reflexion Retries', desc: 'Number of times CodeSentinel will self-repair code if a syntax error occurs.' },
        { term: 'Shannon Entropy', desc: 'Information theory metric used to calculate password/key randomness.' },
        { term: 'Offline Mode', desc: 'Deterministic mode operating without external cloud LLM dependencies.' }
      ]
    }
  },

  initProcessGuide() {
    const nav = document.getElementById('guide-drawer-nav');
    if (!nav) return;

    // Detect active page from body attribute or URL
    const bodyPage = document.body.getAttribute('data-active-page');
    let initialPage = 'dashboard';
    if (bodyPage && this.processGuideData[bodyPage]) {
      initialPage = bodyPage;
    } else {
      const path = window.location.pathname;
      if (path.includes('review/new')) initialPage = 'new_review';
      else if (path.includes('review/results')) initialPage = 'results';
      else if (path.includes('revisions')) initialPage = 'revisions';
      else if (path.includes('pull-requests')) initialPage = 'pull_requests';
      else if (path.includes('dependencies')) initialPage = 'dependencies';
      else if (path.includes('policies')) initialPage = 'policies';
      else if (path.includes('compliance')) initialPage = 'compliance';
      else if (path.includes('integrations')) initialPage = 'integrations';
      else if (path.includes('analytics')) initialPage = 'analytics';
      else if (path.includes('audit-log')) initialPage = 'audit_log';
      else if (path.includes('repositories')) initialPage = 'repositories';
      else if (path.includes('team')) initialPage = 'team';
      else if (path.includes('settings')) initialPage = 'settings';
    }

    this.activeGuidePage = initialPage;

    // Build navigation buttons
    nav.innerHTML = Object.keys(this.processGuideData).map(k => {
      const page = this.processGuideData[k];
      const isActive = k === initialPage;
      return `
        <button class="guide-drawer-nav-btn ${isActive ? 'active' : ''}" id="guide-nav-${k}" onclick="App.switchGuideTab('${k}')">
          <span>${page.icon}</span>
          <span>${page.name}</span>
        </button>
      `;
    }).join('');

    this.renderGuideBody(initialPage);
  },

  switchGuideTab(pageKey) {
    if (!this.processGuideData[pageKey]) return;
    this.activeGuidePage = pageKey;

    document.querySelectorAll('.guide-drawer-nav-btn').forEach(b => b.classList.remove('active'));
    const btn = document.getElementById(`guide-nav-${pageKey}`);
    if (btn) btn.classList.add('active');

    this.renderGuideBody(pageKey);
  },

  renderGuideBody(pageKey) {
    const body = document.getElementById('guide-drawer-body');
    const data = this.processGuideData[pageKey];
    if (!body || !data) return;

    body.innerHTML = `
      <div style="margin-bottom: 20px;">
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
          <span style="font-size: 24px;">${data.icon}</span>
          <h2 style="font-size: var(--text-lg); font-weight: 800; margin: 0; color: var(--color-text);">${data.title}</h2>
        </div>
        <p style="color: var(--color-text-secondary); font-size: var(--text-xs); margin: 0;">${data.subtitle}</p>
      </div>

      <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--color-primary); margin-bottom: 8px;">
        ✦ 4-Stage Operational Dataflow
      </div>
      <div class="process-flow-track" style="grid-template-columns: 1fr; gap: 8px; margin-bottom: 20px;">
        ${data.steps.map(s => `
          <div class="process-flow-step" style="padding: 10px 12px;">
            <div class="process-flow-step-num">Step ${s.num}</div>
            <div class="process-flow-step-title" style="font-size: 12px;">${s.title}</div>
            <div class="process-flow-step-desc">${s.desc}</div>
          </div>
        `).join('')}
      </div>

      <div style="margin-bottom: 20px;">
        <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--color-text-muted); margin-bottom: 8px;">
          ⚙️ Under The Hood: Engines & Heuristics
        </div>
        <ul class="explainer-bullet-list">
          ${data.underTheHood.map(u => `<li>${u}</li>`).join('')}
        </ul>
      </div>

      <div style="margin-bottom: 20px;">
        <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--color-text-muted); margin-bottom: 8px;">
          📖 How To Use / Developer Workflow
        </div>
        <ul class="explainer-bullet-list">
          ${data.howToUse.map(h => `<li>${h}</li>`).join('')}
        </ul>
      </div>

      <div>
        <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--color-text-muted); margin-bottom: 8px;">
          🏷️ Key Concepts & Terminology
        </div>
        <div class="explainer-glossary-pills">
          ${data.glossary.map(g => `
            <div class="glossary-pill" title="${g.desc}">
              <strong>${g.term}:</strong> <span>${g.desc}</span>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  },

  toggleProcessGuide(pageKey) {
    const drawer = document.getElementById('process-guide-drawer');
    const backdrop = document.getElementById('process-guide-backdrop');
    if (!drawer) return;

    const isOpen = drawer.classList.contains('open');
    if (isOpen) {
      this.closeProcessGuide();
    } else {
      this.openProcessGuide(pageKey);
    }
  },

  openProcessGuide(pageKey) {
    const drawer = document.getElementById('process-guide-drawer');
    const backdrop = document.getElementById('process-guide-backdrop');
    if (!drawer) return;

    const nav = document.getElementById('guide-drawer-nav');
    if (!nav || !nav.children.length) {
      this.initProcessGuide();
    }

    const bodyPage = document.body.getAttribute('data-active-page');
    const targetKey = pageKey || (bodyPage && this.processGuideData[bodyPage] ? bodyPage : (this.activeGuidePage || 'dashboard'));
    this.switchGuideTab(this.processGuideData[targetKey] ? targetKey : 'dashboard');

    drawer.classList.add('open');
    if (backdrop) backdrop.classList.add('active');
  },

  closeProcessGuide() {
    const drawer = document.getElementById('process-guide-drawer');
    const backdrop = document.getElementById('process-guide-backdrop');
    if (drawer) drawer.classList.remove('open');
    if (backdrop) backdrop.classList.remove('active');
  },

  togglePageExplainer(pageId) {
    const body = document.getElementById(`explainer-body-${pageId}`);
    const icon = document.getElementById(`explainer-icon-${pageId}`);
    const text = document.getElementById(`explainer-text-${pageId}`);
    if (!body) return;

    const isHidden = body.style.display === 'none';
    body.style.display = isHidden ? 'block' : 'none';
    if (icon) icon.innerText = isHidden ? '▾' : '▸';
    if (text) text.innerText = isHidden ? 'Hide Guide' : 'Explain This Page';

    localStorage.setItem(`codesentinel_explainer_${pageId}`, isHidden ? 'open' : 'closed');
  },

  initPageExplainers() {
    document.querySelectorAll('.page-explainer-card').forEach(card => {
      const pageId = card.id.replace('explainer-', '');
      const savedState = localStorage.getItem(`codesentinel_explainer_${pageId}`);
      if (savedState === 'closed') {
        const body = document.getElementById(`explainer-body-${pageId}`);
        const icon = document.getElementById(`explainer-icon-${pageId}`);
        const text = document.getElementById(`explainer-text-${pageId}`);
        if (body) body.style.display = 'none';
        if (icon) icon.innerText = '▸';
        if (text) text.innerText = 'Explain This Page';
      }
    });
  },

  /* ==========================================================================
     High-Quality Tactile Button Ripple Interaction
     ========================================================================== */
  initButtonEffects() {
    document.addEventListener('pointerdown', (e) => {
      const btn = e.target.closest('.btn');
      if (!btn || btn.disabled || btn.getAttribute('aria-disabled') === 'true') return;

      const rect = btn.getBoundingClientRect();
      const ripple = document.createElement('span');
      ripple.className = 'btn-ripple-wave';

      const size = Math.max(rect.width, rect.height) * 1.6;
      ripple.style.width = `${size}px`;
      ripple.style.height = `${size}px`;
      ripple.style.left = `${e.clientX - rect.left}px`;
      ripple.style.top = `${e.clientY - rect.top}px`;

      btn.appendChild(ripple);
      setTimeout(() => {
        if (ripple.parentNode === btn) {
          btn.removeChild(ripple);
        }
      }, 700);
    }, { passive: true });
  }
};

window.addEventListener('DOMContentLoaded', () => App.init());
