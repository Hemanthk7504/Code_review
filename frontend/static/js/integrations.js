/**
 * CodeSentinel Integrations Hub Controller
 */
const IntegrationsController = {
  integrations: [],

  async init() {
    await this.loadIntegrations();
  },

  async loadIntegrations() {
    const grid = document.getElementById('integrations-grid');
    if (!grid) return;

    try {
      const data = await API.get('/api/v1/integrations');
      this.integrations = data.integrations || [];
      this.renderGrid();
    } catch (err) {
      console.warn('Using local integration presets:', err);
      this.integrations = [
        { id: 'slack', name: 'Slack Security Channel', type: 'slack', enabled: true, channel_or_project: '#security-reviews', events: ['review.completed', 'finding.critical'] },
        { id: 'jira', name: 'Jira Software', type: 'jira', enabled: true, channel_or_project: 'SEC', events: ['finding.critical'] },
        { id: 'github', name: 'GitHub Code Scanning', type: 'webhook', enabled: true, channel_or_project: 'octocat/repo', events: ['review.completed', 'revision.accepted'] },
        { id: 'linear', name: 'Linear Cycles', type: 'linear', enabled: false, channel_or_project: 'ENG', events: ['finding.critical'] },
        { id: 'teams', name: 'Microsoft Teams', type: 'teams', enabled: true, channel_or_project: 'SecOps Webhook', events: ['review.completed'] },
        { id: 'datadog', name: 'Datadog Observability', type: 'datadog', enabled: true, channel_or_project: 'prod-agent', events: ['review.completed'] },
      ];
      this.renderGrid();
    }
  },

  renderGrid() {
    const grid = document.getElementById('integrations-grid');
    if (!grid) return;

    const brandIcons = {
      slack: '💬',
      jira: '🔷',
      linear: '📐',
      teams: '👥',
      discord: '🎮',
      datadog: '🐶',
      webhook: '⚡'
    };

    grid.innerHTML = this.integrations.map(item => `
      <div class="card card-hoverable" style="display: flex; flex-direction: column; justify-content: space-between; height: 100%;">
        <div>
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
            <div style="display: flex; align-items: center; gap: 12px;">
              <span style="font-size: 28px;">${brandIcons[item.type] || '🔌'}</span>
              <div>
                <h4 style="font-weight: 700; font-size: var(--text-base);">${item.name}</h4>
                <span style="font-size: var(--text-xs); color: var(--color-text-muted); font-family: var(--font-mono);">${item.channel_or_project || item.type}</span>
              </div>
            </div>
            <span class="badge ${item.enabled ? 'badge-verified' : 'badge-rejected'}">
              ${item.enabled ? 'Connected' : 'Disabled'}
            </span>
          </div>

          <p style="font-size: var(--text-sm); color: var(--color-text-secondary); margin-bottom: 16px;">
            Dispatches automated findings, risk scores, and patch diagnostics directly to ${item.type.toUpperCase()}.
          </p>

          <div style="margin-bottom: 16px;">
            <div style="font-size: var(--text-xs); color: var(--color-text-muted); margin-bottom: 6px; font-weight: 600; text-transform: uppercase;">Active Subscriptions</div>
            <div style="display: flex; flex-wrap: wrap; gap: 4px;">
              ${(item.events || []).map(ev => `<span class="badge badge-source">${ev}</span>`).join('')}
            </div>
          </div>
        </div>

        <div style="display: flex; justify-content: space-between; align-items: center; pt: 12px; border-top: 1px solid var(--color-border-subtle); margin-top: 12px; padding-top: 12px;">
          <button class="btn btn-secondary btn-sm" onclick="IntegrationsController.testIntegration('${item.type}', '${item.name}', '${item.channel_or_project || ''}')">
            <span>Test Ping</span>
          </button>
          <button class="btn btn-ghost btn-sm" onclick="App.showToast('Configuring ${item.name}...', 'info')">
            <span>Settings</span>
          </button>
        </div>
      </div>
    `).join('');
  },

  async testIntegration(type, name, channel) {
    const modal = document.getElementById('integration-test-modal');
    const title = document.getElementById('test-modal-title');
    const content = document.getElementById('test-modal-content');
    if (!modal || !content) return;

    title.textContent = `Testing Integration: ${name}`;
    content.innerHTML = `<div class="skeleton-shimmer" style="height: 100px; border-radius: 8px;"></div>`;
    modal.classList.add('active');

    try {
      const resp = await API.post('/api/v1/integrations/test', {
        integration_type: type,
        channel_or_project: channel,
      });

      content.innerHTML = `
        <div style="display: flex; align-items: center; gap: 8px; color: var(--color-verified); margin-bottom: 12px; font-weight: 600;">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>
          <span>${resp.message || 'Handshake successful!'}</span>
        </div>
        <div style="font-size: var(--text-xs); color: var(--color-text-muted); margin-bottom: 6px;">Generated Payload Sample:</div>
        <pre class="code-editor" style="max-height: 220px; overflow-y: auto; font-size: 11px; padding: 10px; background: var(--color-surface-sunken); border-radius: 6px;"><code>${JSON.stringify(resp.generated_payload || resp, null, 2)}</code></pre>
      `;
      App.showToast(`Test succeeded for ${name}`, 'success');
    } catch (err) {
      content.innerHTML = `
        <div style="color: var(--color-critical); padding: 12px; background: rgba(225, 29, 72, 0.1); border-radius: 6px;">
          Failed to test connection: ${err.message}
        </div>
      `;
      App.showToast(`Test failed for ${name}`, 'error');
    }
  },

  closeTestModal() {
    const modal = document.getElementById('integration-test-modal');
    if (modal) modal.classList.remove('active');
  },

  async openPrometheusModal() {
    const modal = document.getElementById('prometheus-modal');
    const codeBlock = document.getElementById('prometheus-code-block');
    if (!modal || !codeBlock) return;

    modal.classList.add('active');
    try {
      const res = await fetch('/api/v1/integrations/metrics/prometheus');
      const text = await res.text();
      codeBlock.textContent = text;
    } catch (e) {
      codeBlock.textContent = 'Error fetching Prometheus metrics stream.';
    }
  },

  closePrometheusModal() {
    const modal = document.getElementById('prometheus-modal');
    if (modal) modal.classList.remove('active');
  },

  openConfigModal() {
    App.showToast('Select an integration card or configure custom webhook.', 'info');
  },

  copyBadgeMarkdown() {
    const origin = window.location.origin;
    const md = `[![CodeSentinel Security](${origin}/api/v1/badge/status.svg?label=CodeSentinel&message=A%2B%20pass&status=pass)](http://localhost:8000)`;
    navigator.clipboard.writeText(md).then(() => {
      App.showToast('Badge Markdown copied to clipboard!', 'success');
    }).catch(() => {
      prompt('Copy Markdown Badge:', md);
    });
  }
};
