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
      // Escape closes open modals & drawers
      if (e.key === 'Escape') {
        this.closeCommandPalette();
        this.closeApiKeyModal();
        const drawerBackdrop = document.querySelector('.drawer-backdrop.active');
        if (drawerBackdrop) drawerBackdrop.classList.remove('active');
      }
    });
  }
};

window.addEventListener('DOMContentLoaded', () => App.init());
