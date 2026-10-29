/**
 * CodeSentinel API Client
 * Centralized fetch handler with X-API-Key injection, health polling, and endpoint wrappers
 */

const API = {
  getApiKey() {
    return localStorage.getItem('codesentinel_api_key') || '';
  },

  setApiKey(key) {
    if (key) {
      localStorage.setItem('codesentinel_api_key', key.trim());
    } else {
      localStorage.removeItem('codesentinel_api_key');
    }
  },

  getBaseUrl() {
    return localStorage.getItem('codesentinel_api_url') || '';
  },

  setBaseUrl(url) {
    if (url) {
      localStorage.setItem('codesentinel_api_url', url.trim().replace(/\/+$/, ''));
    } else {
      localStorage.removeItem('codesentinel_api_url');
    }
  },

  getToken() {
    return localStorage.getItem('codesentinel_token') || '';
  },

  setToken(token) {
    if (token) {
      localStorage.setItem('codesentinel_token', token.trim());
      document.cookie = `codesentinel_token=${encodeURIComponent(token.trim())}; path=/; max-age=86400; SameSite=Lax`;
    } else {
      localStorage.removeItem('codesentinel_token');
      document.cookie = 'codesentinel_token=; path=/; max-age=0; SameSite=Lax';
    }
  },

  getRefreshToken() {
    return localStorage.getItem('codesentinel_refresh_token') || '';
  },

  setRefreshToken(token) {
    if (token) localStorage.setItem('codesentinel_refresh_token', token.trim());
    else localStorage.removeItem('codesentinel_refresh_token');
  },

  getUser() {
    try {
      return JSON.parse(localStorage.getItem('codesentinel_user') || 'null');
    } catch (e) {
      return null;
    }
  },

  setUser(user) {
    if (user) localStorage.setItem('codesentinel_user', JSON.stringify(user));
    else localStorage.removeItem('codesentinel_user');
  },

  clearAuth() {
    this.setToken('');
    this.setRefreshToken('');
    this.setUser(null);
  },

  isAuthenticated() {
    return !!this.getToken();
  },

  getHeaders(customHeaders = {}) {
    const headers = {
      'Content-Type': 'application/json',
      ...customHeaders
    };
    const token = this.getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    const apiKey = this.getApiKey();
    if (apiKey) {
      headers['X-API-Key'] = apiKey;
    }
    return headers;
  },

  async request(endpoint, options = {}) {
    const baseUrl = this.getBaseUrl();
    const url = `${baseUrl}${endpoint}`;
    const opts = {
      ...options,
      headers: this.getHeaders(options.headers || {})
    };

    try {
      const response = await fetch(url, opts);
      if (!response.ok) {
        if (response.status === 401 && !url.includes('/api/v1/auth/login') && !url.includes('/api/v1/auth/register')) {
          console.warn('Session expired or unauthorized (401). Redirecting to /login...');
          this.clearAuth();
          if (!window.location.pathname.startsWith('/login')) {
            window.location.replace('/login');
            return;
          }
        }
        let errMessage = `HTTP ${response.status}: ${response.statusText}`;
        try {
          const errData = await response.json();
          if (errData.detail) errMessage = errData.detail;
        } catch (_) {}
        const error = new Error(errMessage);
        error.status = response.status;
        throw error;
      }
      return await response.json();
    } catch (err) {
      console.error(`API Error [${endpoint}]:`, err);
      throw err;
    }
  },

  // Generic HTTP verb helpers
  async get(endpoint, options = {}) {
    return this.request(endpoint, { ...options, method: 'GET' });
  },

  async post(endpoint, data = {}, options = {}) {
    return this.request(endpoint, {
      ...options,
      method: 'POST',
      body: typeof data === 'string' ? data : JSON.stringify(data)
    });
  },

  async put(endpoint, data = {}, options = {}) {
    return this.request(endpoint, {
      ...options,
      method: 'PUT',
      body: typeof data === 'string' ? data : JSON.stringify(data)
    });
  },

  async delete(endpoint, options = {}) {
    return this.request(endpoint, { ...options, method: 'DELETE' });
  },

  // Health check
  async health() {
    return this.request('/api/v1/health');
  },

  // Metrics
  async metrics() {
    return this.request('/api/v1/metrics');
  },

  // Review files only
  async review(files) {
    return this.request('/api/v1/review', {
      method: 'POST',
      body: JSON.stringify({ files })
    });
  },

  // Full loop: review + autonomous fix + validation
  async revise(files) {
    return this.request('/api/v1/revise', {
      method: 'POST',
      body: JSON.stringify({ files })
    });
  },

  // Quick single-snippet audit
  async quickAudit(code, filename = 'snippet.py') {
    return this.request('/api/v1/audit/quick', {
      method: 'POST',
      body: JSON.stringify({ code, filename })
    });
  },

  // Submit GitHub PR review job
  async submitPullRequest(repo, prNumber, token = null, createRevisionPr = true) {
    const body = {
      repo,
      pr_number: parseInt(prNumber, 10),
      create_revision_pr: !!createRevisionPr
    };
    if (token) body.github_token = token;
    return this.request('/api/v1/github/pull-request', {
      method: 'POST',
      body: JSON.stringify(body)
    });
  },

  // Validate GitHub repository access and metadata
  async validateGitHubRepo(repo, token = null) {
    const body = { repo };
    if (token) body.github_token = token;
    return this.request('/api/v1/github/validate', {
      method: 'POST',
      body: JSON.stringify(body)
    });
  },

  // Fetch authenticated GitHub user and rate limits
  async getGitHubUser(token = null) {
    const query = token ? `?token=${encodeURIComponent(token)}` : '';
    return this.get(`/api/v1/github/user${query}`);
  },

  // List user repositories
  async listGitHubRepos(token = null) {
    const query = token ? `?token=${encodeURIComponent(token)}` : '';
    return this.get(`/api/v1/github/repos${query}`);
  },

  // List pull requests for a repository
  async listRepoPulls(owner, repo, state = 'open', token = null) {
    const query = token ? `?state=${encodeURIComponent(state)}&token=${encodeURIComponent(token)}` : `?state=${encodeURIComponent(state)}`;
    return this.get(`/api/v1/github/repos/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}/pulls${query}`);
  },

  // Export finding as GitHub Issue
  async createGitHubIssue(repo, title, body, labels = [], token = null) {
    return this.post('/api/v1/github/issues', {
      repo,
      title,
      body,
      labels,
      github_token: token
    });
  },

  // Get Job status
  async getJob(jobId) {
    return this.request(`/api/v1/jobs/${encodeURIComponent(jobId)}`);
  },

  // Export SARIF 2.1.0
  async exportSarif(findings) {
    return this.request('/api/v1/export/sarif', {
      method: 'POST',
      body: JSON.stringify({ findings })
    });
  },

  // Export Markdown report
  async exportMarkdown(files) {
    return this.request('/api/v1/export/markdown', {
      method: 'POST',
      body: JSON.stringify({ files })
    });
  },

  // Connection indicator live polling
  initHealthMonitor(callback) {
    const check = async () => {
      try {
        const data = await this.health();
        if (callback) callback({ online: true, ...data });
      } catch (err) {
        if (callback) callback({ online: false, error: err.message });
      }
    };
    check();
    setInterval(check, 30000); // Poll every 30s as specified
  },

  // JWT Authentication Helpers
  async login(username, password) {
    const data = await this.post('/api/v1/auth/login', { username, password });
    if (data && data.access_token) {
      this.setToken(data.access_token);
      this.setRefreshToken(data.refresh_token);
      this.setUser(data.user);
    }
    return data;
  },

  async register(payload) {
    const data = await this.post('/api/v1/auth/register', payload);
    if (data && data.access_token) {
      this.setToken(data.access_token);
      this.setRefreshToken(data.refresh_token);
      this.setUser(data.user);
    }
    return data;
  },

  async logout() {
    try {
      await this.post('/api/v1/auth/logout');
    } catch (_) {}
    this.clearAuth();
    window.location.href = '/login';
  },

  async getProfile() {
    return this.get('/api/v1/auth/me');
  }
};
