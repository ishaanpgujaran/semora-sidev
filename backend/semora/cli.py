"""Command Line Interface (CLI) for Semora.

This module exposes terminal commands to initialize the quality-gate system, 
log into the Firebase dashboard, and run the pipeline checks.
"""

import sys
from typing import Any
import click


@click.group()
def main() -> Any:
    """Semora - Autonomous Local CI & Quality-Gate Tool."""
    # TODO(scaffold-agent): Initialize CLI state if needed.
    pass


@main.command()
def init() -> None:
    """Initialize Semora configurations and hook scripts in the target repository."""
    # TODO(scaffold-agent): Scaffold local directories and write pre-commit hook files.
    click.echo("Initializing Semora...")


@main.command()
def login() -> None:
    """Log in to Firebase using user credentials for reporting sync."""
    click.echo("Logging in to Firebase backend...")
    email = click.prompt("Email", type=str)
    password = click.prompt("Password", type=str, hide_input=True)
    
    from semora.sync.firebase_auth import login_command
    try:
        login_command(email, password)
    except Exception as e:
        click.echo(f"Login failed: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option("--commit", is_flag=True, help="Run in pre-commit hook mode.")
def run(commit: bool) -> None:
    """Execute quality-gate checks (BDD tests, STRIDE threat modeling, and reporting)."""
    import os
    import git

    click.echo(f"Executing quality gate (commit_mode={commit})...")

    # 1. Determine the repository path
    repo_path = os.getcwd()

    # 2. Get the git diff (staged for commit mode, unstaged otherwise)
    try:
        repo = git.Repo(repo_path, search_parent_directories=True)
        repo_path = repo.working_tree_dir or repo_path
        if commit:
            try:
                diff_items = repo.index.diff("HEAD", create_patch=True)
            except git.BadName:
                diff_items = []
        else:
            diff_items = repo.index.diff(None, create_patch=True)
        diff_text = "".join(
            d.diff.decode("utf-8", errors="replace") for d in diff_items
        )
    except git.InvalidGitRepositoryError:
        click.echo("Warning: Not inside a git repository. Running with empty diff.")
        diff_text = ""

    # 3. Build the initial RunState
    from semora.graph.state import RunState
    state = RunState(repo_path=repo_path, diff_text=diff_text)

    # 4. Run the pipeline nodes synchronously (matching the ADK graph topology)
    #    spec_node → parallel(execution_node, threat_node) → aggregator_node
    from semora.graph.spec_agent import generate_specs
    from semora.graph.execution_agent import execute_specs
    from semora.graph.threat_agent import audit_security
    from semora.graph.aggregator import aggregate_results

    click.echo("  [1/4] Generating BDD specs...")
    state = generate_specs(state)
    click.echo(f"         → {len(state.generated_specs)} spec(s) generated")

    click.echo("  [2/4] Executing BDD tests in sandbox...")
    state = execute_specs(state)

    click.echo("  [3/4] Running STRIDE threat scan...")
    try:
        state = audit_security(state)
        click.echo(f"         → {len(state.threat_findings)} finding(s)")
    except RuntimeError as e:
        click.echo(f"  Warning: Security scan skipped — {e}", err=True)

    click.echo("  [4/4] Computing compliance score...")
    state = aggregate_results(state)

    # 5. Generate and display the terminal report
    from semora.reporting.markdown_report import generate_markdown_report
    report = generate_markdown_report(state)
    click.echo("")
    click.echo(report)

    # 6. Sync results to Firebase Dashboard
    from semora.sync.firestore_client import sync_report
    sync_report(state)

    # 7. Pre-commit hook compliance check
    score = state.compliance_score if state.compliance_score is not None else 0
    if score < 60:
        sys.exit(1)


if __name__ == "__main__":
    main()
