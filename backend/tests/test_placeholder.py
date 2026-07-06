"""Test suite for the Semora CLI.

Assures the command-line interface bootstraps correctly.
"""

from click.testing import CliRunner
from semora.cli import main


def test_cli_help_menu() -> None:
    """Verify that the CLI output shows options and help text."""
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "Autonomous Local CI" in result.output
