"""Unit tests for BDD Execution Bridge and Execution Agent.

Simulates a target repository containing a deliberately incomplete implementation of
is_valid_email (which returns True on empty string), mock-generates BDD specs,
executes the tests in the isolated sandbox, and asserts that the resulting ledger
properly flags the empty string scenario as failed with a clear assertion message.
"""

import os
import shutil
import pytest
from pathlib import Path
import git
from unittest.mock import patch

from backend.semora.graph.state import RunState
from backend.semora.graph.execution_agent import execute_specs

MOCK_FEATURE_CONTENT = """Feature: Email Validation
  As a user
  I want to check email validity
  So that I can verify format correctness

  Scenario: Empty email string is invalid
    Given the email address ""
    When we check the email
    Then it should return False

  Scenario: Valid email is valid
    Given the email address "test@example.com"
    When we check the email
    Then it should return True
"""

MOCK_STEP_DEFS = """
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from email_helper import is_valid_email
from pytest_bdd import scenarios, given, when, then
import pytest

scenarios('is_valid_email.feature')

@pytest.fixture
def test_state():
    return {}

@given('the email address ""')
def given_empty(test_state):
    test_state["email"] = ""

@given('the email address "test@example.com"')
def given_valid(test_state):
    test_state["email"] = "test@example.com"

@when('we check the email')
def check_email(test_state):
    test_state["result"] = is_valid_email(test_state["email"])

@then('it should return False')
def should_return_false(test_state):
    assert test_state["result"] is False

@then('it should return True')
def should_return_true(test_state):
    assert test_state["result"] is True
"""


@pytest.fixture
def mock_target_repo(tmp_path: Path) -> Path:
    """Fixture to set up a git repository with an incomplete is_valid_email helper."""
    # Write target code file
    email_helper_py = tmp_path / "email_helper.py"
    email_helper_py.write_text('''"""Email Helper module."""

def is_valid_email(email: str) -> bool:
    """Validate if an email is syntactically correct.

    Raises TypeError if input is not a string.
    """
    if not isinstance(email, str):
        raise TypeError("Email must be a string")
    # Deliberately incomplete: empty strings are treated as valid (returns True)
    if email == "":
        return True
    if "@" not in email or "." not in email:
        return False
    return True
''', encoding="utf-8")

    # Initialize Git
    repo = git.Repo.init(str(tmp_path))
    repo.config_writer().set_value("user", "name", "Test User").release()
    repo.config_writer().set_value("user", "email", "test@semora.dev").release()
    repo.index.add(["email_helper.py"])
    repo.index.commit("chore: initial incomplete email helper commit")

    return tmp_path


def test_execution_agent_deliberately_incomplete_email_helper(mock_target_repo: Path) -> None:
    """Verify that execute_specs catches the empty string failure on the incomplete helper."""
    feat_dir = mock_target_repo / "tests" / "features"
    feat_dir.mkdir(parents=True, exist_ok=True)
    feat_file = feat_dir / "is_valid_email.feature"
    feat_file.write_text(MOCK_FEATURE_CONTENT, encoding="utf-8")

    # 1. Start with RunState populated with generated specs
    state = RunState(
        repo_path=str(mock_target_repo),
        diff_text="",
        generated_specs=[str(feat_file)],
        execution_results={},
        threat_findings=[],
        compliance_score=None
    )

    # 2. Call Execution Agent, patching step generation to avoid hitting Gemini API quota limits
    with patch("backend.semora.sandbox.pytest_bdd_bridge.generate_step_defs_via_gemini", return_value=MOCK_STEP_DEFS):
        final_state = execute_specs(state)

    # 3. Check results ledger
    feat_path_str = str(feat_file)
    assert feat_path_str in final_state.execution_results
    spec_results = final_state.execution_results[feat_path_str]

    # Verify that the BDD spec suite reported failures
    assert spec_results["passed"] is False, "BDD specs should fail on incomplete email helper"

    # Find the specific empty string test case
    empty_str_test = None
    for tc in spec_results["tests"]:
        # Find test scenario checking empty email string
        if "empty" in tc["name"].lower() or "blank" in tc["name"].lower():
            empty_str_test = tc
            break

    assert empty_str_test is not None, f"Could not find empty string scenario in test cases: {spec_results['tests']}"
    assert empty_str_test["status"] == "failed", f"Expected empty string scenario to fail, got status: {empty_str_test}"
    
    # Assert meaningful assertion message, not just "False"
    assertion_msg = empty_str_test["assertion_message"]
    assert len(assertion_msg) > 5, f"Expected detailed assertion message, got: {assertion_msg!r}"
    assert "False" in assertion_msg or "true" in assertion_msg.lower() or "assert" in assertion_msg.lower() or "failed" in assertion_msg.lower()
