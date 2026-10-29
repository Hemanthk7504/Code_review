/**
 * CodeSentinel Pull Request & Background Job Controller
 * Handles PR submission, 3-second status polling, and job history tracking
 */

const JobsController = {
  activeJobId: null,
  pollTimer: null,
  githubUser: null,
  activeRepos: [],
  selectedRepo: 'Hemanthk7504/Code_review',

  init() {
    this.renderJobsTable();
    this.initGitHubIntegration();
  },

  async initGitHubIntegration() {
    try {
      const user = await API.getGitHubUser();
      const statusCard = document.getElementById('gh-connection-card');
      const userAvatar = document.getElementById('gh-user-avatar');
      const userName = document.getElementById('gh-user-name');
      const userHandle = document.getElementById('gh-user-handle');
      const rateQuota = document.getElementById('gh-rate-quota');

      if (user && user.connected) {
        this.githubUser = user;
        if (statusCard) statusCard.style.display = 'flex';
        if (userAvatar) userAvatar.src = user.avatar_url || '/static/img/avatar.png';
        if (userName) userName.innerText = user.name || user.login;
        if (userHandle) userHandle.innerText = `@${user.login} (${user.public_repos || 0} public, ${user.total_private_repos || 0} private repos)`;
        if (rateQuota && user.rate_limit) {
          rateQuota.innerText = `${user.rate_limit.remaining} / ${user.rate_limit.limit} requests`;
        }
        await this.loadRepos();
      } else {
        if (statusCard) {
          statusCard.style.display = 'flex';
          const indicator = document.getElementById('gh-status-indicator');
          if (indicator) {
            indicator.className = 'badge badge-warning';
            indicator.innerText = 'Token Needed';
          }
          if (userHandle) userHandle.innerText = 'Configure GITHUB_TOKEN in .env or Settings for full live sync';
        }
        await this.loadRepos();
      }
    } catch (err) {
      console.warn('GitHub integration check error:', err);
    }
  },

  async loadRepos() {
    const selectEl = document.getElementById('gh-repo-select');
    if (!selectEl) return;
    try {
      const res = await API.listGitHubRepos();
      let repos = res && res.repos && res.repos.length > 0 ? res.repos : [];
      if (!repos.some(r => r.full_name === 'Hemanthk7504/Code_review')) {
        repos.unshift({
          full_name: 'Hemanthk7504/Code_review',
          name: 'Code_review',
          language: 'Python',
          private: false,
          description: 'Autonomous AI Code Review & Remediation Platform'
        });
      }
      this.activeRepos = repos;
      selectEl.innerHTML = repos.map(r => `
        <option value="${r.full_name}" ${r.full_name === this.selectedRepo ? 'selected' : ''}>
          ${r.full_name} (${r.language || 'Code'}) ${r.private ? '🔒' : '🌐'}
        </option>
      `).join('');

      await this.loadLivePullRequests(this.selectedRepo);
    } catch (err) {
      console.error('Failed to load GitHub repos:', err);
    }
  },

  async onRepoChange(repoName) {
    this.selectedRepo = repoName;
    const inputEl = document.getElementById('pr-repo-input');
    if (inputEl) inputEl.value = repoName;
    await this.loadLivePullRequests(repoName);
  },

  async loadLivePullRequests(repoName) {
    const target = repoName || this.selectedRepo;
    const container = document.getElementById('live-prs-container');
    const loadingEl = document.getElementById('live-prs-loading');
    if (!container) return;

    if (loadingEl) loadingEl.style.display = 'block';
    container.innerHTML = '';

    const parts = target.split('/');
    if (parts.length !== 2) return;
    const [owner, name] = parts;

    try {
      const res = await API.listRepoPulls(owner, name, 'open');
      if (loadingEl) loadingEl.style.display = 'none';

      const pulls = res && res.pulls ? res.pulls : [];
      if (pulls.length === 0) {
        container.innerHTML = `
          <div style="text-align: center; padding: 24px; color: var(--color-text-muted);">
            No open pull requests found for <strong>${target}</strong>.
          </div>
        `;
        return;
      }

      container.innerHTML = pulls.map(pr => {
        const timeAgo = new Date(pr.created_at).toLocaleDateString();
        const safeTitle = String(pr.title).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        return `
          <div class="card" style="margin-bottom: 12px; padding: 14px 18px; display: flex; justify-content: space-between; align-items: center; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-md); transition: var(--transition-fast); flex-wrap: wrap; gap: 12px;">
            <div style="display: flex; gap: 12px; align-items: center;">
              <img src="${pr.user.avatar_url || '/static/img/avatar.png'}" style="width: 34px; height: 34px; border-radius: 50%; border: 1px solid var(--color-border);" />
              <div>
                <div style="font-weight: 600; font-size: var(--text-sm); display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                  <span style="color: var(--color-primary); font-family: var(--font-mono); font-weight: 700;">#${pr.number}</span>
                  <span>${safeTitle}</span>
                  ${pr.draft ? '<span class="badge badge-neutral" style="font-size: 10px;">Draft</span>' : '<span class="badge badge-verified" style="font-size: 10px;">Open</span>'}
                </div>
                <div style="color: var(--color-text-muted); font-size: var(--text-xs); margin-top: 3px;">
                  by <strong>@${pr.user.login}</strong> · <code>${pr.head.ref}</code> → <code>${pr.base.ref}</code> · Created ${timeAgo}
                </div>
              </div>
            </div>
            <div style="display: flex; gap: 8px;">
              <a href="${pr.html_url}" target="_blank" class="btn btn-sm btn-secondary" style="font-size: 12px;">GitHub ↗</a>
              <button class="btn btn-sm btn-primary" onclick="JobsController.quickLaunchReview('${target}', ${pr.number})" style="font-size: 12px;">
                ⚡ 1-Click Review
              </button>
            </div>
          </div>
        `;
      }).join('');
    } catch (err) {
      if (loadingEl) loadingEl.style.display = 'none';
      container.innerHTML = `
        <div style="padding: 16px; color: var(--color-text-muted); font-size: var(--text-xs);">
          Could not fetch live PRs for ${target}: ${err.message}.
        </div>
      `;
    }
  },

  quickLaunchReview(repo, prNumber) {
    const repoInput = document.getElementById('pr-repo-input');
    const numberInput = document.getElementById('pr-number-input');
    if (repoInput) repoInput.value = repo;
    if (numberInput) numberInput.value = prNumber;
    App.showToast('Launching Review', `Starting automated review on ${repo} #${prNumber}...`, 'info');
    this.submitPR();
    setTimeout(() => {
      const tracker = document.getElementById('active-job-card');
      if (tracker) tracker.scrollIntoView({ behavior: 'smooth' });
    }, 300);
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

    const isRunning = job.status === 'running';
    const isDone = job.status === 'done';
    const isFailed = job.status === 'failed';

    const chip = document.getElementById('job-status-chip');
    if (chip) {
      chip.className = `badge badge-${isDone ? 'verified' : (isFailed ? 'critical' : 'medium')}`;
      chip.innerHTML = isRunning ?
        '<span class="dot-indicator dot-warning live-pulse"></span> RUNNING' :
        job.status.toUpperCase();
    }

    const stageBadge = document.getElementById('job-stage-badge');
    if (stageBadge) {
      stageBadge.innerText = job.current_stage || (isDone ? 'Completed' : (isRunning ? 'Processing' : 'Queued'));
      stageBadge.className = `badge badge-${isDone ? 'verified' : (isFailed ? 'critical' : 'primary')}`;
    }

    const pollStatus = document.getElementById('job-poll-status');
    if (pollStatus) {
      pollStatus.innerText = isDone ? 'Job finished.' : (isFailed ? 'Job terminated with error.' : 'Polling GitHub background worker (every 3s)...');
    }

    const liveInd = document.getElementById('job-live-indicator');
    if (liveInd) {
      liveInd.className = `dot-indicator dot-${isDone ? 'success' : (isFailed ? 'critical' : 'warning live-pulse')}`;
    }

    const progress = Math.max(5, Math.min(100, job.progress !== undefined ? job.progress : (isDone ? 100 : 25)));
    const progressBar = document.getElementById('job-progress-bar');
    const progressPercent = document.getElementById('job-progress-percent');
    if (progressBar) progressBar.style.width = `${progress}%`;
    if (progressPercent) progressPercent.innerText = `${progress}%`;

    const detailEl = document.getElementById('job-detail-text');
    if (detailEl) {
      detailEl.innerText = job.detail || (isRunning ? 'Processing AST, AI agents, and automated PR verification...' : 'Completed');
    }

    // Update 7 PR Stage Bubbles based on progress
    const stageThresholds = [10, 20, 35, 50, 70, 85, 100];
    for (let i = 1; i <= 7; i++) {
      const bubble = document.getElementById(`job-stage-bubble-${i}`);
      if (!bubble) continue;
      const thresh = stageThresholds[i - 1];
      if (progress >= thresh) {
        bubble.className = progress > thresh || isDone ? 'stage-bubble done' : 'stage-bubble active';
      } else {
        bubble.className = 'stage-bubble';
      }
    }

    // Update Terminal Feed
    const terminal = document.getElementById('job-terminal-body');
    if (terminal && job.logs && job.logs.length > 0) {
      terminal.innerHTML = job.logs.map(logStr => {
        const match = logStr.match(/^\[(.*?)\]\s*(.*)$/);
        const ts = match ? match[1] : '00:00:00';
        const msg = match ? match[2] : logStr;
        let tag = 'info';
        if (msg.includes('Static') || msg.includes('Bandit') || msg.includes('Pylint')) tag = 'static';
        else if (msg.includes('AI') || msg.includes('Agent') || msg.includes('specialist')) tag = 'agent';
        else if (msg.includes('Risk') || msg.includes('CVSS') || msg.includes('Finding')) tag = 'risk';
        else if (msg.includes('Verify') || msg.includes('verified')) tag = 'verify';
        else if (msg.includes('Fix') || msg.includes('remediation') || msg.includes('AST')) tag = 'fix';
        else if (msg.includes('PR') || msg.includes('GitHub') || msg.includes('branch')) tag = 'gate';
        else if (msg.includes('Complete') || msg.includes('successfully') || msg.includes('Opened')) tag = 'done';
        else if (msg.includes('Error') || msg.includes('fail')) tag = 'error';

        const safeMsg = String(msg).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        return `
          <div class="terminal-line">
            <span class="terminal-timestamp">[${ts}]</span>
            <span class="terminal-tag terminal-tag-${tag}">${tag.toUpperCase()}</span>
            <span>${safeMsg}</span>
          </div>
        `;
      }).join('');
      terminal.scrollTop = terminal.scrollHeight;
    }

    // Show result link & banner if PR was created
    const resultBox = document.getElementById('job-result-container');
    const prBanner = document.getElementById('job-pr-banner');
    const prLink = document.getElementById('job-pr-link');

    if (resultBox && job.result) {
      resultBox.style.display = 'block';
      if (job.result.revision_pr) {
        if (prBanner) prBanner.style.display = 'block';
        if (prLink) {
          prLink.href = job.result.revision_pr;
          prLink.style.display = 'inline-flex';
        }
      }
      const rawEl = document.getElementById('job-json-raw');
      if (rawEl) rawEl.innerText = JSON.stringify(job.result, null, 2);
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
            <div style="display: inline-flex; gap: 4px; justify-content: flex-end;">
              <button class="btn btn-xs btn-secondary" onclick="JobsController.inspectJob('${j.job_id}')">Inspect</button>
              ${j.result ? `<button class="btn btn-xs btn-primary" onclick="JobsController.openInReviewResults('${j.job_id}')">Results →</button>` : ''}
              ${j.result && j.result.revision_pr ?
                `<a href="${j.result.revision_pr}" target="_blank" class="btn btn-xs btn-outline-primary">PR ↗</a>` : ''}
            </div>
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
  },

  async openInReviewResults(jobId) {
    try {
      const targetId = jobId || this.activeJobId;
      if (!targetId) {
        window.location.href = '/review/results';
        return;
      }
      const job = await API.getJob(targetId);
      if (!job || !job.result) {
        App.showToast('No Findings Yet', 'Job has not completed or findings are still processing.', 'warning');
        return;
      }
      const reviewPayload = {
        isFullLoop: true,
        timestamp: new Date().toISOString(),
        files: job.result.files || [],
        data: job.result.review ? job.result : { review: job.result, revisions: job.result.revisions || [] }
      };
      localStorage.setItem('codesentinel_last_review', JSON.stringify(reviewPayload));
      App.showToast('Opening Results', 'Transferring audit findings to Review Results...', 'success');
      setTimeout(() => {
        window.location.href = '/review/results';
      }, 400);
    } catch (e) {
      App.showToast('Error Loading Results', e.message, 'error');
    }
  }
};
