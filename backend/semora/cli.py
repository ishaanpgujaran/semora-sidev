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
    # TODO(reporting-sync-agent): Authenticate user via firebase_auth.py.
    click.echo("Logging in to Firebase backend...")


@main.command()
@click.option("--commit", is_flag=True, help="Run in pre-commit hook mode.")
def run(commit: bool) -> None:
    """Execute quality-gate checks (BDD tests, STRIDE threat modeling, and reporting)."""
    # TODO(adk-graph-agent): Invoke the ADK Graph workflow to run spec generation, sandbox execution, STRIDE threat model, and sync results.
    click.echo(f"Executing quality gate (commit_mode={commit})...")


if __name__ == "__main__":
    main()
