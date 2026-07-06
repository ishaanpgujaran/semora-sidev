"""Test suite for the Spec Agent spec generation logic.

Verifies that the generate_specs function analyzes diffs, invokes the Gemini API,
generates appropriate Gherkin BDD specifications with edge cases and happy paths,
writes the result feature files to tests/features/ in the target repository,
and updates the shared pipeline RunState correctly.
"""

import os
import shutil
from pathlib import Path
import pytest

from backend.semora.graph.state import RunState
from backend.semora.graph.spec_agent import generate_specs


@pytest.fixture
def temp_repo(tmp_path: Path) -> Path:
    """Fixture that creates a temporary directory simulating the target repository."""
    return tmp_path


def test_generate_specs_with_dict(temp_repo: Path) -> None:
    """Verify BDD spec generation when state is passed as a dictionary."""
    diff_text = '''diff --git a/email_helper.py b/email_helper.py
new file mode 100644
index 0000000..e69de29
--- /dev/null
+++ b/email_helper.py
@@ -0,0 +1,11 @@
+def is_valid_email(email: str) -> bool:
+    """Validate if an email is syntactically correct.
+
+    Raises TypeError if input is not a string.
+    """
+    if not isinstance(email, str):
+        raise TypeError("Email must be a string")
+    if not email:
+        return False
+    if "@" not in email or "." not in email:
+        return False
+    return True
'''
    recent_commit_messages = ["feat: add email validation helper function"]

    state = {
        "repo_path": str(temp_repo),
        "diff_text": diff_text,
        "generated_specs": []
    }

    # Call generate_specs
    updated_state = generate_specs(state, recent_commit_messages=recent_commit_messages)

    assert isinstance(updated_state, dict)
    assert len(updated_state["generated_specs"]) > 0

    # Ensure files exist in tests/features/
    feature_file_path = updated_state["generated_specs"][0]
    assert os.path.exists(feature_file_path)
    assert "tests/features" in feature_file_path

    # Read and inspect Gherkin content
    content = Path(feature_file_path).read_text(encoding="utf-8")
    assert "Feature:" in content

    # Check scenario counts
    scenarios = [
        line
        for line in content.splitlines()
        if line.strip().startswith("Scenario:") or line.strip().startswith("Scenario Outline:")
    ]
    assert len(scenarios) >= 4, f"Expected at least 4 scenarios, got {len(scenarios)}:\n{content}"


    # Verify scenario titles are not generic (like "Scenario 1" or "Edge case 1")
    for scenario_line in scenarios:
        title = scenario_line.split(":", 1)[1].strip()
        assert len(title) > 5, f"Scenario title is too short or empty: {title!r}"
        assert not title.lower().startswith("scenario"), f"Generic scenario title: {title!r}"
        assert not title.isdigit(), f"Generic numeric scenario title: {title!r}"


def test_generate_specs_with_run_state(temp_repo: Path) -> None:
    """Verify BDD spec generation when state is passed as a RunState model."""
    diff_text = '''diff --git a/email_helper.py b/email_helper.py
new file mode 100644
index 0000000..e69de29
--- /dev/null
+++ b/email_helper.py
@@ -0,0 +1,11 @@
+def is_valid_email(email: str) -> bool:
+    """Validate if an email is syntactically correct.
+
+    Raises TypeError if input is not a string.
+    """
+    if not isinstance(email, str):
+        raise TypeError("Email must be a string")
+    if not email:
+        return False
+    if "@" not in email or "." not in email:
+        return False
+    return True
'''
    recent_commit_messages = ["feat: add email validation helper function"]

    run_state = RunState(
        repo_path=str(temp_repo),
        diff_text=diff_text,
        generated_specs=[]
    )

    # Call generate_specs
    updated_state = generate_specs(run_state, recent_commit_messages=recent_commit_messages)

    assert isinstance(updated_state, RunState)
    assert len(updated_state.generated_specs) > 0

    feature_file_path = updated_state.generated_specs[0]
    assert os.path.exists(feature_file_path)

    # Read and inspect Gherkin content
    content = Path(feature_file_path).read_text(encoding="utf-8")
    assert "Feature:" in content

    scenarios = [
        line
        for line in content.splitlines()
        if line.strip().startswith("Scenario:") or line.strip().startswith("Scenario Outline:")
    ]
    assert len(scenarios) >= 4, f"Expected at least 4 scenarios, got {len(scenarios)}"
