/**
 * CodeSentinel Pull Request & Background Job Controller
 * Handles PR submission, 3-second status polling, and job history tracking
 */

const JobsController = {
  activeJobId: null,
  pollTimer: null,

  init() {
    this.renderJobsTable();
  },

  async submitPR(e) {
    if (e) e.preventDefault();

    const repoInput = document.getElementById('pr-repo-input');
    const numberInput = document.getElementById('pr-number-input');
    const tokenInput = document.getElementById('pr-token-input');
    const createPrCheck = document.getElementById('pr-create-check');
    const submitBtn = document.getElementById('pr-submit-btn');

    if (!repoInput || !numberInput) return;
    const repo = repoInput.value.trim();
    const prNumber = parseInt(numberInput.value.trim(), 10);
    const token = tokenInput ? tokenInput.value.trim() : null;
    const createRevPr = createPrCheck ? createPrCheck.checked : true;

    if (!repo || !prNumber) {
      App.showToast('Validation Error', 'Please specify a repository (owner/repo) and PR number.', 'warning');
      return;
    }

    if (submitBtn) submitBtn.disabled = true;

    try {
      const job = await API.submitPullRequest(repo, prNumber, token, createRevPr);
      this.saveJobToHistory({
        job_id: job.job_id,
        repo,
        pr_number: prNumber,
        status: job.status,
        timestamp: new Date().toISOString()
      });

      this.activeJobId = job.job_id;
      this.renderJobsTable();
      this.showActiveJobTracker(job);
      this.startPolling(job.job_id);

      App.showToast('Job Dispatched', `Background review queued (Job ID: ${job.job_id.substring(0, 8)}).`, 'info');
    } catch (err) {
      App.showToast('Submission Failed', err.message, 'error');
    } finally {
      if (submitBtn) submitBtn.disabled = false;
    }
  },

  startPolling(jobId) {
    if (this.pollTimer) clearInterval(this.pollTimer);

    this.pollTimer = setInterval(async () => {
      try {
        const job = await API.getJob(jobId);
        this.updateJobInHistory(job);
        this.showActiveJobTracker(job);
        this.renderJobsTable();

        if (job.status === 'done' || job.status === 'failed') {
          clearInterval(this.pollTimer);
          this.pollTimer = null;
          if (job.status === 'done') {
            App.showToast('Review Completed', 'PR analysis and automated revision completed.', 'success');
          } else {
            App.showToast('Job Failed', job.detail || 'Review failed during background processing.', 'error');
          }
        }
      } catch (err) {
        clearInterval(this.pollTimer);
        this.pollTimer = null;
      }
    }, 3000); // Poll every 3 seconds as required
  },

  showActiveJobTracker(job) {
    const card = document.getElementById('active-job-card');
    if (!card) return;

    card.style.display = 'block';
    document.getElementById('job-id-text').innerText = job.job_id;

    const chip = document.getElementById('job-status-chip');
    if (chip) {
      chip.className = `badge badge-${job.status === 'done' ? 'verified' : (job.status === 'failed' ? 'critical' : 'medium')}`;
      chip.innerHTML = job.status === 'running' ?
        '<span class="dot-indicator dot-warning live-pulse"></span> Running' :
        job.status.toUpperCase();
    }

    const detailEl = document.getElementById('job-detail-text');
    if (detailEl) detailEl.innerText = job.detail || (job.status === 'running' ? 'Processing AST, AI agents and re-validation...' : 'Completed');

    // Show result link if PR was created
    const resultBox = document.getElementById('job-result-container');
    const prLink = document.getElementById('job-pr-link');
    if (resultBox && job.result) {
      resultBox.style.display = 'block';
      if (prLink && job.result.revision_pr) {
        prLink.href = job.result.revision_pr;
        prLink.style.display = 'inline-flex';
        prLink.innerText = `View Automated PR: ${job.result.revision_pr}`;
      }
      document.getElementById('job-json-raw').innerText = JSON.stringify(job.result, null, 2);
    }
  },

  getJobsHistory() {
    return JSON.parse(localStorage.getItem('codesentinel_pr_jobs') || '[]');
  },

  saveJobToHistory(job) {
    const history = this.getJobsHistory();
    history.unshift(job);
    localStorage.setItem('codesentinel_pr_jobs', JSON.stringify(history.slice(0, 25)));
  },

  updateJobInHistory(job) {
    const history = this.getJobsHistory();
    const idx = history.findIndex(j => j.job_id === job.job_id);
    if (idx >= 0) {
      history[idx].status = job.status;
      history[idx].detail = job.detail;
      history[idx].result = job.result;
      localStorage.setItem('codesentinel_pr_jobs', JSON.stringify(history));
    }
  },

  renderJobsTable() {
    const tbody = document.getElementById('pr-jobs-tbody');
    if (!tbody) return;

    const history = this.getJobsHistory();
    if (history.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="5" style="text-align: center; padding: 32px; color: var(--color-text-muted);">
            No GitHub pull request jobs dispatched yet.
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = history.map(j => {
      const isDone = j.status === 'done';
      const isFail = j.status === 'failed';
      const badgeCls = isDone ? 'badge-verified' : (isFail ? 'badge-critical' : 'badge-medium');
      const timeStr = new Date(j.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

      return `
        <tr>
          <td><code>${j.job_id.substring(0, 8)}</code></td>
          <td><strong>${j.repo}</strong> #${j.pr_number}</td>
          <td><span class="badge ${badgeCls}">${j.status}</span></td>
          <td style="color: var(--color-text-muted); font-size: var(--text-xs);">${timeStr}</td>
          <td style="text-align: right;">
            ${j.result && j.result.revision_pr ?
              `<a href="${j.result.revision_pr}" target="_blank" class="btn btn-sm btn-secondary" style="font-size:11px;">View PR ↗</a>` :
              `<button class="btn btn-sm btn-ghost" onclick="JobsController.inspectJob('${j.job_id}')">Inspect</button>`}
          </td>
        </tr>
      `;
    }).join('');
  },

  async inspectJob(jobId) {
    try {
      const job = await API.getJob(jobId);
      this.showActiveJobTracker(job);
      App.showToast('Job Details Loaded', `Viewing status for ${jobId.substring(0, 8)}`, 'info');
    } catch (e) {
      App.showToast('Error', e.message, 'error');
    }
  }
};
