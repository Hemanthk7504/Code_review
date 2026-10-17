/**
 * CodeSentinel Chart & Data Visualization Library
 * Count-up animation, SVG circular risk gauge, and Chart.js wrappers
 */

const Charts = {
  // Count-up animation for numbers
  countUp(elementOrId, target, duration = 1000, decimals = 0) {
    const el = typeof elementOrId === 'string' ? document.getElementById(elementOrId) : elementOrId;
    if (!el) return;

    const start = parseFloat(el.innerText) || 0;
    const finalVal = parseFloat(target) || 0;
    if (start === finalVal) {
      el.innerText = finalVal.toFixed(decimals);
      return;
    }

    const startTime = performance.now();
    const step = (currentTime) => {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // Ease out cubic
      const ease = 1 - Math.pow(1 - progress, 3);
      const current = start + (finalVal - start) * ease;
      el.innerText = current.toFixed(decimals);

      if (progress < 1) {
        requestAnimationFrame(step);
      } else {
        el.innerText = finalVal.toFixed(decimals);
      }
    };
    requestAnimationFrame(step);
  },

  // Render SVG Animated Circular Risk Gauge
  renderRiskGauge(containerId, score = 0, grade = 'A+') {
    const container = document.getElementById(containerId);
    if (!container) return;

    const radius = 54;
    const circumference = 2 * Math.PI * radius;
    const clampedScore = Math.min(100, Math.max(0, score));
    const offset = circumference - (clampedScore / 100) * circumference;

    // Determine color based on score
    let strokeColor = '#10B981'; // Green A+
    let gradeColor = 'var(--color-verified)';
    if (clampedScore > 75) {
      strokeColor = '#EF4444'; // Red
      gradeColor = 'var(--color-critical)';
    } else if (clampedScore > 50) {
      strokeColor = '#F97316'; // Orange
      gradeColor = 'var(--color-high)';
    } else if (clampedScore > 30) {
      strokeColor = '#F59E0B'; // Amber
      gradeColor = 'var(--color-medium)';
    } else if (clampedScore > 15) {
      strokeColor = '#3B82F6'; // Blue
      gradeColor = 'var(--color-low)';
    }

    container.innerHTML = `
      <div class="gauge-wrapper">
        <svg class="gauge-svg" width="140" height="140" viewBox="0 0 140 140">
          <circle class="gauge-circle-bg" cx="70" cy="70" r="${radius}" stroke-width="10" />
          <circle class="gauge-circle-val" id="${containerId}-circle" cx="70" cy="70" r="${radius}" stroke-width="10"
                  stroke="${strokeColor}"
                  stroke-dasharray="${circumference}"
                  stroke-dashoffset="${circumference}" />
        </svg>
        <div class="gauge-center-content">
          <span class="gauge-score" id="${containerId}-score">0</span>
          <span class="gauge-label">Risk Index</span>
          <span class="gauge-grade" style="color: ${gradeColor}; background: rgba(255,255,255,0.06);">${grade}</span>
        </div>
      </div>
    `;

    // Trigger stroke animation
    setTimeout(() => {
      const circle = document.getElementById(`${containerId}-circle`);
      if (circle) circle.style.strokeDashoffset = offset;
      this.countUp(`${containerId}-score`, clampedScore, 1000, 1);
    }, 100);
  },

  // Risk Over Time Gradient Area Chart
  renderRiskTrendChart(canvasId, labels, dataPoints) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || typeof Chart === 'undefined') return null;

    const ctx = canvas.getContext('2d');
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';

    const gradient = ctx.createLinearGradient(0, 0, 0, 240);
    gradient.addColorStop(0, 'rgba(99, 102, 241, 0.45)');
    gradient.addColorStop(1, 'rgba(99, 102, 241, 0.0)');

    return new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels || ['Day 1', 'Day 2', 'Day 3', 'Day 4', 'Day 5', 'Day 6', 'Day 7'],
        datasets: [{
          label: 'Overall Risk Score',
          data: dataPoints || [65, 58, 52, 44, 40, 32, 18],
          borderColor: '#6366F1',
          borderWidth: 2.5,
          pointBackgroundColor: '#6366F1',
          pointRadius: 3,
          pointHoverRadius: 6,
          fill: true,
          backgroundColor: gradient,
          tension: 0.35
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: isDark ? '#182236' : '#FFFFFF',
            titleColor: isDark ? '#F8FAFC' : '#0F172A',
            bodyColor: isDark ? '#94A3B8' : '#475569',
            borderColor: isDark ? 'rgba(255,255,255,0.1)' : '#E2E8F0',
            borderWidth: 1,
            padding: 10,
            displayColors: false,
            callbacks: {
              label: (ctx) => `Risk Score: ${ctx.parsed.y}/100`
            }
          }
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { color: isDark ? '#64748B' : '#94A3B8', font: { size: 11 } }
          },
          y: {
            min: 0,
            max: 100,
            grid: { color: isDark ? 'rgba(255,255,255,0.05)' : '#F1F5F9' },
            ticks: { color: isDark ? '#64748B' : '#94A3B8', font: { size: 11 }, stepSize: 25 }
          }
        }
      }
    });
  },

  // Findings by Severity Donut Chart
  renderSeverityDonut(canvasId, counts = {}) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || typeof Chart === 'undefined') return null;

    const ctx = canvas.getContext('2d');
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';

    const crit = counts.critical || 0;
    const high = counts.high || 0;
    const med = counts.medium || 0;
    const low = counts.low || 0;

    return new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: ['Critical', 'High', 'Medium', 'Low'],
        datasets: [{
          data: [crit, high, med, low],
          backgroundColor: ['#EF4444', '#F97316', '#F59E0B', '#3B82F6'],
          borderWidth: 0,
          hoverOffset: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '72%',
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              color: isDark ? '#94A3B8' : '#475569',
              boxWidth: 10,
              padding: 12,
              font: { size: 11 }
            }
          }
        }
      }
    });
  },

  // Findings by Category Bar Chart
  renderCategoryBar(canvasId, counts = {}) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || typeof Chart === 'undefined') return null;

    const ctx = canvas.getContext('2d');
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';

    const labels = Object.keys(counts).length ? Object.keys(counts) : ['security', 'bug', 'quality', 'refactor', 'complexity', 'performance'];
    const dataVals = labels.map(l => counts[l] || 0);

    return new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels.map(l => l.charAt(0).toUpperCase() + l.slice(1)),
        datasets: [{
          label: 'Findings',
          data: dataVals,
          backgroundColor: '#6366F1',
          borderRadius: 4,
          maxBarThickness: 24
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false }
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { color: isDark ? '#64748B' : '#94A3B8', font: { size: 11 } }
          },
          y: {
            beginAtZero: true,
            grid: { color: isDark ? 'rgba(255,255,255,0.05)' : '#F1F5F9' },
            ticks: { color: isDark ? '#64748B' : '#94A3B8', font: { size: 11 }, precision: 0 }
          }
        }
      }
    });
  }
};
