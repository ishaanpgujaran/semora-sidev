"""Execution Agent Module.

This module defines the Execution Agent logic. It runs generated BDD tests
inside the secure isolated sandbox, collects test report metrics (durations,
status, error logs, assertion messages), and updates the shared pipeline RunState.
"""

from typing import Dict, Any, Union
from dotenv import load_dotenv

from backend.semora.graph.state import RunState
from backend.semora.sandbox.pytest_bdd_bridge import run_features

# Load env variables
load_dotenv()


def execute_specs(
    state: Union[Dict[str, Any], RunState]
) -> Union[Dict[str, Any], RunState]:
    """Execute generated BDD tests inside the isolated sandbox.

    Args:
        state (Union[Dict[str, Any], RunState]): Current pipeline state.

    Returns:
        Union[Dict[str, Any], RunState]: Updated pipeline state with execution ledger.
    """
    is_pydantic = not isinstance(state, dict) and hasattr(state, "repo_path")

    if is_pydantic:
        repo_path = state.repo_path
        feature_files = state.generated_specs
    else:
        repo_path = state.get("repo_path", "")
        feature_files = state.get("generated_specs", [])

    if not feature_files:
        # No tests to execute
        return state

    # Invoke BDD bridge execution runner
    outcome = run_features(feature_files, repo_path=repo_path)

    # Populate state execution results
    if is_pydantic:
        state.execution_results = outcome.get("results", {})
    else:
        state["execution_results"] = outcome.get("results", {})

    return state
