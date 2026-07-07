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
    
    from backend.semora.sync.firebase_auth import login_command
    try:
        login_command(email, password)
    except Exception as e:
        click.echo(f"Login failed: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option("--commit", is_flag=True, help="Run in pre-commit hook mode.")
def run(commit: bool) -> None:
    """Execute quality-gate checks (BDD tests, STRIDE threat modeling, and reporting)."""
    # TODO(adk-graph-agent): Invoke the ADK Graph workflow to run spec generation, sandbox execution, STRIDE threat model, and sync results.
    click.echo(f"Executing quality gate (commit_mode={commit})...")
    
    # ---------------------------------------------------------
    # PLACEHOLDER: The ADK Graph execution should populate this.
    # Below we simulate getting the final RunState from the graph.
    from backend.semora.graph.state import RunState
    final_state = RunState(repo_path=".", diff_text="")
    final_state.compliance_score = 100 # Mock value until graph is fully wired
    # ---------------------------------------------------------

    from backend.semora.reporting.markdown_report import generate_markdown_report
    report = generate_markdown_report(final_state)
    click.echo(report)
    
    # Sync results to Firebase Dashboard
    from backend.semora.sync.firestore_client import sync_report
    sync_report(final_state)
    
    # Pre-commit hook compliance check
    score = final_state.compliance_score if final_state.compliance_score is not None else 0
    if score < 60:
        sys.exit(1)


if __name__ == "__main__":
    main()
