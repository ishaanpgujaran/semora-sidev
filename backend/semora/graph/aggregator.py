"""
Aggregator Node Module.

Provides the ADK graph node that computes the final compliance verdict
by aggregating results from upstream Execution and Threat nodes.
"""

from typing import Any, Union
from semora.graph.state import RunState
from semora.reporting.compliance_score import calculate_compliance_score

def aggregate_results(
    state: Union[dict[str, Any], RunState],
) -> Union[dict[str, Any], RunState]:
    """
    ADK graph node for aggregation.
    
    Reads `execution_results` and `threat_findings` from the state,
    computes the `compliance_score`, and updates the state.

    Args:
        state: Current pipeline state, either a `RunState` Pydantic model or
            a plain dict with the same top-level keys.

    Returns:
        The updated pipeline state with `compliance_score` populated.
    """
    is_pydantic = not isinstance(state, dict) and hasattr(state, "repo_path")
    
    if is_pydantic:
        execution_results = getattr(state, "execution_results", {})
        threat_findings = getattr(state, "threat_findings", [])
    else:
        execution_results = state.get("execution_results", {})
        threat_findings = state.get("threat_findings", [])
        
    score = calculate_compliance_score(execution_results, threat_findings)
    
    if is_pydantic:
        state.compliance_score = score
    else:
        state["compliance_score"] = score
        
    return state
