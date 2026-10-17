/**
 * CodeSentinel Enterprise Preview Data
 * Sample data for Repositories, Audit Log, Team & Access Control (Preview features)
 */

const EnterpriseData = {
  repositories: [
    {
      id: 'repo-1',
      name: 'sentinel-core-engine',
      owner: 'acme-corp',
      branch: 'main',
      status: 'active',
      lastReview: '12 mins ago',
      findingsCount: 4,
      riskScore: 24.5,
      webhookHealth: 'healthy'
    },
    {
      id: 'repo-2',
      name: 'payment-gateway-service',
      owner: 'acme-corp',
      branch: 'master',
      status: 'active',
      lastReview: '2 hours ago',
      findingsCount: 1,
      riskScore: 12.0,
      webhookHealth: 'healthy'
    },
    {
      id: 'repo-3',
      name: 'identity-auth-broker',
      owner: 'acme-corp',
      branch: 'main',
      status: 'active',
      lastReview: 'Yesterday',
      findingsCount: 0,
      riskScore: 0.0,
      webhookHealth: 'healthy'
    },
    {
      id: 'repo-4',
      name: 'analytics-pipeline',
      owner: 'acme-corp',
      branch: 'develop',
      status: 'paused',
      lastReview: '3 days ago',
      findingsCount: 7,
      riskScore: 58.0,
      webhookHealth: 'failing'
    }
  ],

  auditLogs: [
    {
      id: 'evt-1092',
      actor: 'devops-lead@acme.internal',
      action: 'REVISION_PR_ACCEPTED',
      target: 'acme-corp/sentinel-core-engine #412',
      timestamp: '2026-10-17 10:48:12',
      ip: '10.240.12.8',
      status: 'SUCCESS'
    },
    {
      id: 'evt-1091',
      actor: 'ai-review-bot[bot]',
      action: 'SELF_VERIFICATION_COMPLETE',
      target: 'acme-corp/payment-gateway-service #89',
      timestamp: '2026-10-17 09:22:45',
      ip: '127.0.0.1',
      status: 'SUCCESS'
    },
    {
      id: 'evt-1090',
      actor: 'security-auditor@acme.internal',
      action: 'API_KEY_ROTATED',
      target: 'API Key (SHA: 4f8a...92b1)',
      timestamp: '2026-10-16 16:35:10',
      ip: '10.240.14.2',
      status: 'SUCCESS'
    },
    {
      id: 'evt-1089',
      actor: 'github-webhook',
      action: 'WEBHOOK_SIGNATURE_VERIFIED',
      target: 'acme-corp/identity-auth-broker (PR #102)',
      timestamp: '2026-10-16 14:12:08',
      ip: '140.82.112.4',
      status: 'SUCCESS'
    },
    {
      id: 'evt-1088',
      actor: 'external-contributor',
      action: 'REVISION_VALIDATION_REJECTED',
      target: 'acme-corp/analytics-pipeline (PR #56)',
      timestamp: '2026-10-15 11:05:32',
      ip: '198.51.100.24',
      status: 'WARNING'
    }
  ],

  teamMembers: [
    {
      id: 'usr-1',
      name: 'Elena Rostova',
      email: 'elena.rostova@acme.internal',
      role: 'Admin',
      teams: ['Security Engineering', 'Core Platform'],
      mfa: true,
      lastActive: '5 mins ago'
    },
    {
      id: 'usr-2',
      name: 'Marcus Chen',
      email: 'marcus.chen@acme.internal',
      role: 'Reviewer',
      teams: ['Core Platform'],
      mfa: true,
      lastActive: '1 hour ago'
    },
    {
      id: 'usr-3',
      name: 'Aisha Al-Mansoor',
      email: 'aisha.m@acme.internal',
      role: 'Reviewer',
      teams: ['App Security'],
      mfa: true,
      lastActive: 'Yesterday'
    },
    {
      id: 'usr-4',
      name: 'David Kim',
      email: 'david.kim@acme.internal',
      role: 'Viewer',
      teams: ['Quality Assurance'],
      mfa: false,
      lastActive: '3 days ago'
    }
  ]
};
