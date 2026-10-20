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

const SampleReviewData = {
  isFullLoop: true,
  timestamp: new Date().toISOString(),
  files: [
    {
      name: 'backend/database.py',
      content: `import subprocess
import sqlite3

def query_user(username: str, cache: dict = {}):
    conn = sqlite3.connect("production.db")
    cursor = conn.cursor()
    # SQL injection via string interpolation
    cursor.execute(f"SELECT * FROM users WHERE username = '{username}'")
    return cursor.fetchall()

def export_db(dbname: str):
    # Dangerous subprocess execution with shell=True
    subprocess.run(f"pg_dump -U admin {dbname}", shell=True)
`
    },
    {
      name: 'backend/auth.py',
      content: `import os
import requests

# Hardcoded AWS access credentials in plaintext
AWS_ACCESS_KEY = "AKIA1234567890EXAMPLEKEY"
AWS_SECRET_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"

def verify_token(token: str):
    # Missing explicit timeout parameter on remote network request
    response = requests.get("https://oauth.provider.internal/verify?token=" + token)
    return response.json()
`
    }
  ],
  data: {
    review: {
      summary: {
        files_analyzed: 2,
        total_findings: 5,
        verified: 4,
        uncertain: 0,
        rejected: 1,
        overall_risk: 54.5,
        llm_used: true,
        posture_grade: 'B',
        by_severity: {
          critical: 1,
          high: 2,
          medium: 1,
          low: 1
        },
        by_category: {
          security: 3,
          bug: 1,
          performance: 1
        },
        cwe_counts: {
          'CWE-89': 1,
          'CWE-798': 1,
          'CWE-78': 1,
          'CWE-400': 1,
          'CWE-665': 1
        },
        top_risks: [
          'CRITICAL: SQL Injection via string interpolation [CWE-89] at backend/database.py:9 (risk 88.0)',
          'HIGH: Hardcoded AWS access credentials [CWE-798] at backend/auth.py:5 (risk 75.0)',
          'HIGH: Arbitrary Command Injection (shell=True) [CWE-78] at backend/database.py:15 (risk 68.0)'
        ]
      },
      findings: [
        {
          id: 'finding-cwe-89-sqli',
          title: 'SQL Injection via unescaped string formatting',
          description: 'User-controlled parameter is directly formatted into an SQL query without parameterized binding, allowing arbitrary database exfiltration.',
          severity: 'critical',
          category: 'security',
          cwe: 'CWE-89',
          file: 'backend/database.py',
          line: 9,
          snippet: 'cursor.execute(f"SELECT * FROM users WHERE username = \'{username}\'")',
          verification: 'verified',
          confidence: 0.98,
          corroborating_sources: ['Bandit B608', 'Security Auditor Agent', 'AST Taint Tracker'],
          risk_score: 88.0,
          explanation: 'SQL injection occurs when untrusted input is directly concatenated into an SQL statement. Attackers can bypass authentication or extract sensitive tables using UNION injections.',
          proposed_fix: 'cursor.execute("SELECT * FROM users WHERE username = ?", (username,))'
        },
        {
          id: 'finding-cwe-798-hardcoded-secret',
          title: 'Hardcoded Plaintext AWS Access Key & Secret',
          description: 'High-entropy plaintext AWS credentials detected directly in source code. Violates secrets management zero-tolerance policy.',
          severity: 'high',
          category: 'security',
          cwe: 'CWE-798',
          file: 'backend/auth.py',
          line: 5,
          snippet: 'AWS_ACCESS_KEY = "AKIA1234567890EXAMPLEKEY"',
          verification: 'verified',
          confidence: 0.96,
          corroborating_sources: ['Shannon Entropy Scanner', 'Bandit B105', 'Security Auditor Agent'],
          risk_score: 75.0,
          explanation: 'Hardcoding cloud access keys in source control allows anyone with repository read permissions to compromise AWS infrastructure.',
          proposed_fix: 'AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID", "")\nAWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")'
        },
        {
          id: 'finding-cwe-78-command-injection',
          title: 'Arbitrary Command Injection via subprocess with shell=True',
          description: 'Spawning a subshell with shell=True allows unescaped shell metacharacters to execute arbitrary system commands.',
          severity: 'high',
          category: 'security',
          cwe: 'CWE-78',
          file: 'backend/database.py',
          line: 15,
          snippet: 'subprocess.run(f"pg_dump -U admin {dbname}", shell=True)',
          verification: 'verified',
          confidence: 0.95,
          corroborating_sources: ['Bandit B602', 'AST Node Inspector', 'Security Auditor Agent'],
          risk_score: 68.0,
          explanation: 'Using shell=True invokes /bin/sh or cmd.exe. An attacker supplying a database name like "prod; rm -rf /" executes arbitrary commands.',
          proposed_fix: 'subprocess.run(["pg_dump", "-U", "admin", dbname], shell=False, check=True)'
        },
        {
          id: 'finding-cwe-400-missing-timeout',
          title: 'HTTP request without explicit connection timeout',
          description: 'Calling external HTTP endpoint without explicit timeout can lead to thread exhaustion and DoS.',
          severity: 'medium',
          category: 'performance',
          cwe: 'CWE-400',
          file: 'backend/auth.py',
          line: 10,
          snippet: 'response = requests.get("https://oauth.provider.internal/verify?token=" + token)',
          verification: 'verified',
          confidence: 0.90,
          corroborating_sources: ['Pylint AST', 'Performance Specialist'],
          risk_score: 35.0,
          explanation: 'Network requests without timeouts can hang indefinitely if the remote server fails to respond, locking worker processes.',
          proposed_fix: 'response = requests.get("https://oauth.provider.internal/verify?token=" + token, timeout=10.0)'
        },
        {
          id: 'finding-cwe-665-mutable-default',
          title: 'Mutable default argument in function signature',
          description: 'Default parameter cache={} is shared across all function calls, leading to cross-request state leakage.',
          severity: 'low',
          category: 'bug',
          cwe: 'CWE-665',
          file: 'backend/database.py',
          line: 4,
          snippet: 'def query_user(username: str, cache: dict = {}):',
          verification: 'verified',
          confidence: 0.94,
          corroborating_sources: ['Pylint W0102', 'Logic Bug Detector'],
          risk_score: 18.0,
          explanation: 'In Python, default arguments are evaluated only once at definition time, meaning mutations to cache persist across subsequent invocations.',
          proposed_fix: 'def query_user(username: str, cache: dict = None):\n    if cache is None:\n        cache = {}'
        },
        {
          id: 'finding-refuted-eval-fp',
          title: 'AST literal_eval flagged as unsafe eval (Refuted)',
          description: 'Initial scanner flagged eval-like pattern, but skeptical verification confirmed safe ast.literal_eval usage.',
          severity: 'high',
          category: 'security',
          cwe: 'CWE-95',
          file: 'backend/database.py',
          line: 20,
          snippet: 'data = ast.literal_eval(payload_str)',
          verification: 'rejected',
          confidence: 0.10,
          corroborating_sources: ['Skeptical Verifier (Refuted)'],
          risk_score: 0.0,
          explanation: 'ast.literal_eval safely parses Python literals without evaluating arbitrary bytecode or executing system commands.',
          proposed_fix: 'data = ast.literal_eval(payload_str)'
        }
      ]
    },
    notes: [
      'Multi-agent consensus corroborated 4 findings.',
      'Skeptical verifier successfully refuted 1 false positive alert.'
    ]
  }
};
