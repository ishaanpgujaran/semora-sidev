"""
Markdown Report formatting for Semora terminal output.
"""
import os
import subprocess
from typing import Any
from semora.graph.state import RunState

def get_git_branch(repo_path: str) -> str:
    """Gets the current git branch name."""
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip() or "unknown-branch"
    except Exception:
        return "unknown-branch"

def generate_markdown_report(state: RunState) -> str:
    """Generates a terminal-formatted markdown report from a RunState."""
    branch = get_git_branch(state.repo_path)
    
    # Use the basename of the repo path
    repo_name = os.path.basename(os.path.abspath(state.repo_path))
    
    score = state.compliance_score if state.compliance_score is not None else 0
    passed_flag = "✔ PASSED" if score >= 60 else "❌ COMMIT BLOCKED"
    
    total_tests = len(state.execution_results)
    passed_tests = sum(
        1 for res in state.execution_results.values() 
        if isinstance(res, dict) and res.get("passed", False)
    )
    
    spec_mark = "✔" if len(state.generated_specs) > 0 else "✘"
    num_specs = len(state.generated_specs)
    spec_path = state.generated_specs[0] if num_specs > 0 else "N/A"
    
    exec_mark = "✔" if total_tests > 0 and passed_tests == total_tests else "✘"
    failure_summary = f"{total_tests - passed_tests} failed" if passed_tests < total_tests else "All clear"
    if total_tests == 0:
        failure_summary = "No tests executed"
    
    report_lines = []
    report_lines.append(f"SEMORA COMPLIANCE REPORT — {repo_name} (branch: {branch})")
    report_lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    report_lines.append(f"Compliance Score: {score}/100  {passed_flag}")
    report_lines.append("")
    report_lines.append(f"{spec_mark} Specs generated: {num_specs} scenarios → {spec_path}")
    report_lines.append(f"{exec_mark} Execution: {passed_tests}/{total_tests} passed — {failure_summary}")
    report_lines.append("")
    report_lines.append("STRIDE Findings:")
    
    if state.threat_findings:
        for finding in state.threat_findings:
            sev = finding.get("severity", "WARNING").upper()
            if sev == "CRITICAL":
                icon = "🔴"
            elif sev == "HIGH":
                icon = "🟠"
            else:
                icon = "🟡"
            
            cat = finding.get("category", "Unknown")
            desc = finding.get("description", "")
            report_lines.append(f"  {icon} {sev:<10} [{cat}]  {desc}")
    else:
        report_lines.append("  No threat findings.")
        
    has_patch = False
    for finding in state.threat_findings:
        if finding.get("suggested_patch"):
            if not has_patch:
                report_lines.append("")
                report_lines.append("Suggested patch:")
                has_patch = True
            
            patch = finding["suggested_patch"]
            # Formatting logic for patch if it's not already multiline diff
            for line in patch.split("\n"):
                if line.strip():
                    report_lines.append(f"  {line}")
            break # Just show one patch as per example
            
    report_lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    report_lines.append("Full history and trend for this repo: https://semora.firebaseapp.com/dashboard")
    
    return "\n".join(report_lines)
