"""Labelled Held-Out Ground Truth Benchmark Dataset for CodeSentinel.

Contains multi-language real defects (True Positives) and tricky benign/safe code
patterns that naive scanners misflag as false positives (True Negatives).
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class BenchmarkCase:
    id: str
    language: str
    filename: str
    code: str
    is_defect: bool
    category: str
    defect_description: str
    cwe: Optional[str] = None
    expected_rule: Optional[str] = None


BENCHMARK_DATASET: list[BenchmarkCase] = [
    # ==================== PYTHON DEFECTS ====================
    BenchmarkCase(
        id="PY-DEF-01",
        language="python",
        filename="backend/database/user_queries.py",
        code="""def get_user_record(cursor, username: str):
    # Formatted SQL query allows arbitrary SQL injection
    query = f"SELECT id, name, role FROM users WHERE username = '{username}'"
    cursor.execute(query)
    return cursor.fetchone()
""",
        is_defect=True,
        category="security",
        defect_description="Direct SQL injection via f-string formatting in cursor.execute",
        cwe="CWE-89",
        expected_rule="B608",
    ),
    BenchmarkCase(
        id="PY-DEF-02",
        language="python",
        filename="backend/system/diagnostics.py",
        code="""import subprocess

def ping_host(target_host: str):
    # Command injection vulnerability via shell=True with unescaped input
    cmd = f"ping -c 1 {target_host}"
    return subprocess.run(cmd, shell=True, capture_output=True)
""",
        is_defect=True,
        category="security",
        defect_description="Command injection via subprocess.run with shell=True",
        cwe="CWE-78",
        expected_rule="B602",
    ),
    BenchmarkCase(
        id="PY-DEF-03",
        language="python",
        filename="backend/calc/parser.py",
        code="""def evaluate_expression(user_formula: str):
    # Raw eval allows arbitrary code execution
    return eval(user_formula)
""",
        is_defect=True,
        category="security",
        defect_description="Arbitrary code execution via raw built-in eval()",
        cwe="CWE-95",
        expected_rule="B307",
    ),
    BenchmarkCase(
        id="PY-DEF-04",
        language="python",
        filename="backend/services/aws_client.py",
        code="""# Production AWS secret key committed in plaintext
AWS_ACCESS_KEY_ID = "AKIA3FODNN7QL9PX8M2A"
AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYzQ7A419KLM"

def init_s3():
    return {"access": AWS_ACCESS_KEY_ID, "secret": AWS_SECRET_ACCESS_KEY}
""",
        is_defect=True,
        category="security",
        defect_description="High-entropy AWS secret access key hardcoded in plaintext",
        cwe="CWE-798",
        expected_rule="SECRET_AWS_KEY",
    ),

    # ==================== PYTHON TRICKY SAFE SAMPLES (FALSE POSITIVE CANDIDATES) ====================
    BenchmarkCase(
        id="PY-SAFE-01",
        language="python",
        filename="backend/database/safe_queries.py",
        code="""def get_user_safely(cursor, username: str):
    # Parameterized query with placeholder tuple - immune to SQL injection
    query = "SELECT id, name, role FROM users WHERE username = %s"
    cursor.execute(query, (username,))
    return cursor.fetchone()
""",
        is_defect=False,
        category="security",
        defect_description="Parameterized SQL query using %s placeholder and parameters tuple (safe)",
    ),
    BenchmarkCase(
        id="PY-SAFE-02",
        language="python",
        filename="backend/config/safe_parser.py",
        code="""import ast

def parse_config_safely(untrusted_payload: str):
    # ast.literal_eval is safely sandboxed to Python literal structures
    return ast.literal_eval(untrusted_payload)
""",
        is_defect=False,
        category="security",
        defect_description="ast.literal_eval() safely parsing literals without code execution (safe)",
    ),
    BenchmarkCase(
        id="PY-SAFE-03",
        language="python",
        filename="backend/system/safe_process.py",
        code="""import subprocess

def list_files_safely(directory: str):
    # Passing an argument list with shell=False prevents shell interpolation
    return subprocess.run(["ls", "-la", directory], shell=False, check=True)
""",
        is_defect=False,
        category="security",
        defect_description="subprocess.run with argument vector and shell=False (safe)",
    ),
    BenchmarkCase(
        id="PY-SAFE-04",
        language="python",
        filename="tests/test_mock_auth.py",
        code="""# Test mock dummy token used purely for unit testing
MOCK_API_KEY = "test_dummy_mock_fake_token_for_pytest_123456"

def test_authorization_header():
    headers = {"Authorization": f"Bearer {MOCK_API_KEY}"}
    assert headers["Authorization"].startswith("Bearer")
""",
        is_defect=False,
        category="security",
        defect_description="Dummy mock token in unit test file (safe test fixture)",
    ),
    BenchmarkCase(
        id="PY-SAFE-05",
        language="python",
        filename="backend/storage/safe_file.py",
        code="""import os

def read_user_report(base_dir: str, filename: str):
    # Sanitized using basename to prevent path traversal
    safe_name = os.path.basename(filename)
    full_path = os.path.join(base_dir, safe_name)
    with open(full_path, "r", encoding="utf-8") as f:
        return f.read()
""",
        is_defect=False,
        category="security",
        defect_description="Path sanitized with os.path.basename preventing traversal (safe)",
    ),

    # ==================== JAVASCRIPT DEFECTS ====================
    BenchmarkCase(
        id="JS-DEF-01",
        language="javascript",
        filename="frontend/src/utils/merge.js",
        code="""function deepMerge(target, source) {
    for (let key in source) {
        // Prototype pollution via __proto__ assignment
        target[key] = source[key];
    }
    return target;
}
""",
        is_defect=True,
        category="security",
        defect_description="Prototype pollution via unvalidated key assignment in deep merge",
        cwe="CWE-1321",
        expected_rule="JS-PROTO-POLLUTION",
    ),
    BenchmarkCase(
        id="JS-DEF-02",
        language="javascript",
        filename="frontend/src/views/profile.js",
        code="""function renderUserBio(bioHtml) {
    // DOM XSS: direct assignment to innerHTML with untrusted input
    document.getElementById("user-bio").innerHTML = bioHtml;
}
""",
        is_defect=True,
        category="security",
        defect_description="DOM XSS via unescaped innerHTML assignment",
        cwe="CWE-79",
        expected_rule="JS-DOM-XSS",
    ),
    BenchmarkCase(
        id="JS-DEF-03",
        language="javascript",
        filename="server/exec.js",
        code="""const { exec } = require('child_process');

function runBackup(backupName) {
    // Command injection via child_process.exec
    exec('tar -czf ' + backupName + '.tar.gz /data');
}
""",
        is_defect=True,
        category="security",
        defect_description="Command injection via child_process.exec string concatenation",
        cwe="CWE-78",
        expected_rule="JS-COMMAND-INJECTION",
    ),

    # ==================== JAVASCRIPT TRICKY SAFE SAMPLES ====================
    BenchmarkCase(
        id="JS-SAFE-01",
        language="javascript",
        filename="server/db/safe_query.js",
        code="""async function getUserProfile(pool, userId) {
    // Safe parameterized query using $1 binding
    const res = await pool.query('SELECT id, name FROM users WHERE id = $1', [userId]);
    return res.rows[0];
}
""",
        is_defect=False,
        category="security",
        defect_description="PostgreSQL parameterized query with array binding (safe)",
    ),
    BenchmarkCase(
        id="JS-SAFE-02",
        language="javascript",
        filename="frontend/src/views/safe_profile.js",
        code="""function renderUserDisplayName(name) {
    // Safe textContent assignment immune to DOM XSS
    document.getElementById("user-name").textContent = name;
}
""",
        is_defect=False,
        category="security",
        defect_description="Safe textContent assignment instead of innerHTML (safe)",
    ),

    # ==================== GO DEFECTS ====================
    BenchmarkCase(
        id="GO-DEF-01",
        language="go",
        filename="pkg/db/user.go",
        code="""package db

import (
    "database/sql"
    "fmt"
)

func QueryUser(db *sql.DB, username string) (*sql.Rows, error) {
    // SQL injection via fmt.Sprintf string interpolation
    query := fmt.Sprintf("SELECT id, email FROM accounts WHERE username = '%s'", username)
    return db.Query(query)
}
""",
        is_defect=True,
        category="security",
        defect_description="SQL injection via fmt.Sprintf query formatting",
        cwe="CWE-89",
        expected_rule="GO-SQL-INJECTION",
    ),
    BenchmarkCase(
        id="GO-DEF-02",
        language="go",
        filename="pkg/worker/shell.go",
        code="""package worker

import (
    "os/exec"
)

func ExecuteTask(taskCommand string) error {
    // Command injection via shell execution wrapper
    cmd := exec.Command("sh", "-c", taskCommand)
    return cmd.Run()
}
""",
        is_defect=True,
        category="security",
        defect_description="Command execution via sh -c with unvalidated user input",
        cwe="CWE-78",
        expected_rule="GO-COMMAND-INJECTION",
    ),

    # ==================== GO TRICKY SAFE SAMPLES ====================
    BenchmarkCase(
        id="GO-SAFE-01",
        language="go",
        filename="pkg/db/safe_user.go",
        code="""package db

import "database/sql"

func SafeQueryUser(db *sql.DB, userId int) *sql.Row {
    // Safe parameterized SQL query with placeholder
    return db.QueryRow("SELECT id, email FROM accounts WHERE id = ?", userId)
}
""",
        is_defect=False,
        category="security",
        defect_description="Parameterized Go SQL query using ? placeholder (safe)",
    ),
    BenchmarkCase(
        id="GO-SAFE-02",
        language="go",
        filename="pkg/worker/safe_cmd.go",
        code="""package worker

import "os/exec"

func SafeListDir(targetDir string) ([]byte, error) {
    // Static executable with individual argument slices (no shell interpolation)
    return exec.Command("ls", "-la", targetDir).Output()
}
""",
        is_defect=False,
        category="security",
        defect_description="exec.Command with discrete argument list without shell (safe)",
    ),

    # ==================== JAVA DEFECTS ====================
    BenchmarkCase(
        id="JAVA-DEF-01",
        language="java",
        filename="src/main/java/com/app/dao/UserDao.java",
        code="""package com.app.dao;

import java.sql.Connection;
import java.sql.ResultSet;
import java.sql.Statement;

public class UserDao {
    public ResultSet getUser(Connection conn, String id) throws Exception {
        Statement stmt = conn.createStatement();
        // SQL injection via string concatenation in executeQuery
        return stmt.executeQuery("SELECT * FROM members WHERE id = '" + id + "'");
    }
}
""",
        is_defect=True,
        category="security",
        defect_description="JDBC SQL injection via string concatenation in Statement.executeQuery",
        cwe="CWE-89",
        expected_rule="JAVA-SQL-INJECTION",
    ),
    BenchmarkCase(
        id="JAVA-DEF-02",
        language="java",
        filename="src/main/java/com/app/service/CommandRunner.java",
        code="""package com.app.service;

public class CommandRunner {
    public void executeScript(String scriptName) throws Exception {
        // Command injection via Runtime.getRuntime().exec
        Runtime.getRuntime().exec("sh /scripts/" + scriptName);
    }
}
""",
        is_defect=True,
        category="security",
        defect_description="Command injection via Runtime.getRuntime().exec concatenation",
        cwe="CWE-78",
        expected_rule="JAVA-COMMAND-INJECTION",
    ),

    # ==================== JAVA TRICKY SAFE SAMPLES ====================
    BenchmarkCase(
        id="JAVA-SAFE-01",
        language="java",
        filename="src/main/java/com/app/dao/SafeUserDao.java",
        code="""package com.app.dao;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;

public class SafeUserDao {
    public ResultSet getUserSafely(Connection conn, String id) throws Exception {
        // Safe PreparedStatement with positional parameter
        PreparedStatement pstmt = conn.prepareStatement("SELECT * FROM members WHERE id = ?");
        pstmt.setString(1, id);
        return pstmt.executeQuery();
    }
}
""",
        is_defect=False,
        category="security",
        defect_description="Safe JDBC PreparedStatement with parameterized placeholder (safe)",
    ),
    BenchmarkCase(
        id="JAVA-SAFE-02",
        language="java",
        filename="src/main/java/com/app/service/SafeProcess.java",
        code="""package com.app.service;

import java.util.List;

public class SafeProcess {
    public Process startSafeProcess(List<String> commandList) throws Exception {
        // Safe ProcessBuilder using discrete argument list
        ProcessBuilder pb = new ProcessBuilder(commandList);
        return pb.start();
    }
}
""",
        is_defect=False,
        category="security",
        defect_description="Safe ProcessBuilder with discrete argument vector (safe)",
    ),
]
