/**
 * CodeSentinel Software Composition Analysis (SCA) & SBOM Controller
 */
const DependenciesController = {
  lastScanResult: null,

  async init() {
    await this.scanManifest();
  },

  async scanManifest() {
    const textarea = document.getElementById('manifest-textarea');
    const select = document.getElementById('manifest-type-select');
    if (!textarea) return;

    const content = textarea.value;
    const manifestType = select ? select.value : 'requirements.txt';

    try {
      const result = await API.post('/api/v1/sca/scan', {
        content: content,
        manifest_type: manifestType
      });
      this.lastScanResult = result;
      this.render();
      App.showToast(`Identified ${result.vulnerabilities_count} supply-chain vulnerabilities`, result.vulnerabilities_count > 0 ? 'warning' : 'success');
    } catch (err) {
      console.error('Error scanning dependencies:', err);
      App.showToast('Dependency scan failed: ' + err.message, 'error');
    }
  },

  render() {
    if (!this.lastScanResult) return;
    const r = this.lastScanResult;

    const totalDeps = document.getElementById('sca-total-deps');
    if (totalDeps) totalDeps.textContent = r.total_dependencies;

    const totalCves = document.getElementById('sca-total-cves');
    if (totalCves) totalCves.textContent = r.vulnerabilities_count;

    const riskScore = document.getElementById('sca-risk-score');
    if (riskScore) {
      riskScore.textContent = r.risk_score.toFixed(1);
      riskScore.style.color = r.risk_score > 40 ? 'var(--color-critical)' : 'var(--color-verified)';
    }

    const badge = document.getElementById('sca-status-badge');
    if (badge) {
      if (r.vulnerabilities_count === 0) {
        badge.className = 'badge badge-verified';
        badge.textContent = 'All Clean';
      } else if (r.critical_count > 0) {
        badge.className = 'badge badge-critical';
        badge.textContent = `${r.critical_count} Critical`;
      } else {
        badge.className = 'badge badge-uncertain';
        badge.textContent = 'Patches Available';
      }
    }

    const tbody = document.getElementById('sca-findings-table-body');
    if (!tbody) return;

    if (r.findings.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="5" style="text-align: center; color: var(--color-verified); padding: 24px;">
            ✓ Zero known vulnerabilities detected in scanned packages!
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = r.findings.map(f => `
      <tr>
        <td><strong style="font-family: var(--font-mono); font-size: var(--text-xs); color: var(--color-primary);">${f.package}</strong></td>
        <td><code style="font-size: var(--text-xs);">${f.installed_version}</code></td>
        <td>
          <a href="https://nvd.nist.gov/vuln/detail/${f.cve_id}" target="_blank" style="color: var(--color-primary); font-weight: 600; text-decoration: underline;">
            ${f.cve_id}
          </a>
        </td>
        <td>
          <span class="badge ${f.severity === 'critical' ? 'badge-critical' : 'badge-high'}">
            ${f.severity}
          </span>
        </td>
        <td>
          <span style="color: var(--color-verified); font-weight: 600; font-size: var(--text-xs); font-family: var(--font-mono);">
            Upgrade to >= ${f.fixed_version}
          </span>
        </td>
      </tr>
    `).join('');
  },

  async downloadSbom() {
    const textarea = document.getElementById('manifest-textarea');
    if (!textarea) return;

    try {
      const sbom = await API.post('/api/v1/sca/sbom', {
        content: textarea.value,
        manifest_type: 'requirements.txt'
      });

      const jsonStr = JSON.stringify(sbom, null, 2);
      const blob = new Blob([jsonStr], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `cyclonedx_sbom_${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      App.showToast('CycloneDX v1.5 SBOM downloaded successfully!', 'success');
    } catch (err) {
      App.showToast('Failed to generate SBOM: ' + err.message, 'error');
    }
  },

  loadSampleSafeManifest() {
    const textarea = document.getElementById('manifest-textarea');
    if (textarea) {
      textarea.value = `# Fully Patched Modern Dependencies
requests==2.31.0
cryptography==41.0.3
django==4.2.5
urllib3==1.26.18
pyyaml==6.0.1
pillow==10.1.0
fastapi==0.110.0
pydantic==2.6.0
uvicorn==0.27.0
jinja2==3.1.3
`;
      this.scanManifest();
    }
  }
};
