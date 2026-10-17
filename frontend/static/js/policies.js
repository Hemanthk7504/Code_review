/**
 * CodeSentinel Quality Gates Controller
 */
const PoliciesController = {
  async init() {
    await this.loadPolicy();
    this.simulateLastReview();
  },

  async loadPolicy() {
    try {
      const p = await API.get('/api/v1/policy/config');
      if (p) {
        const riskInput = document.getElementById('input-risk-threshold');
        const riskVal = document.getElementById('val-risk-threshold');
        if (riskInput && riskVal) {
          riskInput.value = p.max_risk_score;
          riskVal.textContent = p.max_risk_score.toFixed(1);
        }

        const findingsInput = document.getElementById('input-max-findings');
        const findingsVal = document.getElementById('val-max-findings');
        if (findingsInput && findingsVal) {
          findingsInput.value = p.max_unresolved_findings;
          findingsVal.textContent = p.max_unresolved_findings;
        }

        const blockCrit = document.getElementById('check-block-critical');
        if (blockCrit) blockCrit.checked = !!p.block_on_critical;

        const blockHigh = document.getElementById('check-block-high');
        if (blockHigh) blockHigh.checked = !!p.block_on_high;

        const blockSec = document.getElementById('check-block-secrets');
        if (blockSec) blockSec.checked = !!p.block_on_secrets;

        const reqSyntax = document.getElementById('check-require-syntax');
        if (reqSyntax) reqSyntax.checked = !!p.require_syntax_check;
      }
    } catch (e) {
      console.warn('Using default policy configuration:', e);
    }
  },

  async savePolicy() {
    const payload = {
      name: 'Enterprise Strict Gate (Production)',
      max_risk_score: parseFloat(document.getElementById('input-risk-threshold').value),
      max_unresolved_findings: parseInt(document.getElementById('input-max-findings').value, 10),
      block_on_critical: document.getElementById('check-block-critical').checked,
      block_on_high: document.getElementById('check-block-high').checked,
      block_on_secrets: document.getElementById('check-block-secrets').checked,
      require_syntax_check: document.getElementById('check-require-syntax').checked,
      min_verification_confidence: 0.6,
    };

    try {
      await API.post('/api/v1/policy/config', payload);
      App.showToast('Quality Gate policies successfully updated & saved!', 'success');
      this.simulateLastReview();
    } catch (err) {
      App.showToast('Failed to save policy: ' + err.message, 'error');
    }
  },

  async simulateLastReview() {
    let reviewData = null;
    try {
      const stored = localStorage.getItem('codesentinel_last_review') || localStorage.getItem('codesentinel_latest_review');
      if (stored) {
        const parsed = JSON.parse(stored);
        reviewData = parsed.data ? (parsed.data.review || parsed.data) : parsed;
      }
    } catch (e) {}

    // Fallback benchmark review if none stored in localStorage
    if (!reviewData || !reviewData.summary) {
      reviewData = {
        summary: {
          files_analyzed: 2,
          total_findings: 3,
          verified: 2,
          rejected: 1,
          uncertain: 0,
          by_severity: { critical: 0, high: 1, medium: 2, low: 0, info: 0 },
          by_category: { security: 1, bug: 2 },
          overall_risk: 28.5,
          llm_used: true,
          posture_grade: 'A',
        },
        findings: [
          {
            id: 'demo-1',
            file: 'src/payment.py',
            line: 45,
            category: 'security',
            severity: 'high',
            title: 'Hardcoded Cryptographic Salt',
            rule_id: 'SEC-CRYPTO-SALT',
            verification: 'verified',
            cwe_id: 'CWE-327',
            risk_score: 45.0,
            sources: ['bandit']
          },
          {
            id: 'demo-2',
            file: 'src/utils.py',
            line: 18,
            category: 'bug',
            severity: 'medium',
            title: 'Unchecked File Handle',
            rule_id: 'RESOURCE-LEAK',
            verification: 'verified',
            cwe_id: 'CWE-404',
            risk_score: 22.0,
            sources: ['ast']
          }
        ]
      };
    }

    try {
      const evalResult = await API.post('/api/v1/policy/evaluate', reviewData);
      this.renderEvaluation(evalResult);
    } catch (err) {
      console.error('Error evaluating quality gate:', err);
    }
  },

  renderEvaluation(res) {
    const badge = document.getElementById('eval-status-badge');
    const banner = document.getElementById('eval-summary-banner');
    const rulesList = document.getElementById('eval-rules-list');
    if (!badge || !banner || !rulesList) return;

    badge.textContent = res.status;
    if (res.status === 'PASSED') {
      badge.className = 'badge badge-verified';
      banner.style.background = 'rgba(16, 185, 129, 0.1)';
      banner.style.border = '1px solid rgba(16, 185, 129, 0.3)';
      banner.innerHTML = `
        <div style="display: flex; align-items: center; gap: 10px; color: var(--color-verified); font-weight: 700;">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>
          <span>All Quality Gate Conditions Satisfied (Compliance Score: ${res.score}%)</span>
        </div>
        <p style="font-size: var(--text-xs); color: var(--color-text-secondary); margin-top: 4px;">Pull request meets zero-trust security standards and is approved for automated merge.</p>
      `;
    } else if (res.status === 'BLOCKED') {
      badge.className = 'badge badge-critical';
      banner.style.background = 'rgba(225, 29, 72, 0.1)';
      banner.style.border = '1px solid rgba(225, 29, 72, 0.3)';
      banner.innerHTML = `
        <div style="display: flex; align-items: center; gap: 10px; color: var(--color-critical); font-weight: 700;">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>
          <span>Merge Blocked by Security Policy (Score: ${res.score}%)</span>
        </div>
        <div style="margin-top: 8px;">
          ${(res.violations || []).map(v => `<div style="font-size: var(--text-xs); color: var(--color-critical); margin-bottom: 2px;">• ${v}</div>`).join('')}
        </div>
      `;
    } else {
      badge.className = 'badge badge-uncertain';
      banner.style.background = 'rgba(245, 158, 11, 0.1)';
      banner.style.border = '1px solid rgba(245, 158, 11, 0.3)';
      banner.innerHTML = `
        <div style="display: flex; align-items: center; gap: 10px; color: var(--color-uncertain); font-weight: 700;">
          <span>Quality Gate Warning (Score: ${res.score}%)</span>
        </div>
      `;
    }

    rulesList.innerHTML = (res.evaluations || []).map(e => `
      <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px 12px; background: var(--color-surface-sunken); border-radius: var(--radius-md); font-size: var(--text-sm);">
        <div style="display: flex; align-items: center; gap: 8px;">
          <span style="color: ${e.passed ? 'var(--color-verified)' : 'var(--color-critical)'}; font-weight: 700;">
            ${e.passed ? '✓' : '✕'}
          </span>
          <span style="font-weight: 500;">${e.rule}</span>
        </div>
        <span style="font-size: var(--text-xs); color: var(--color-text-secondary); font-family: var(--font-mono);">
          ${e.message}
        </span>
      </div>
    `).join('');
  }
};
