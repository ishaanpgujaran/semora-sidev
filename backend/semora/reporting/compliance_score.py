"""
Compliance Score Calculation Module.

Calculates the final compliance score based on execution results and threat findings.
"""

from typing import Any, Dict, List

def calculate_compliance_score(
    execution_results: Dict[str, Any],
    threat_findings: List[Dict[str, Any]]
) -> int:
    """
    Computes the RunState.compliance_score as an integer 0-100.

    Formula:
    - 40% weight on spec pass-rate (passed tests / total tests).
    - 40% weight on security posture. Starts at 100. Subtract 15 per HIGH finding 
      and 5 per WARNING finding. If any CRITICAL finding exists, hard-cap this 
      component at 40 regardless of other findings. Minimum security component is 0.
    - 20% weight on full-flow/integration pass-rate. For now, treated the same as 
      spec pass-rate.

    Returns:
        int: The computed compliance score (0-100).
    """
    # 1. Calculate Spec Pass-Rate and Integration Pass-Rate (currently identical)
    total_tests = len(execution_results)
    passed_tests = sum(
        1 for result in execution_results.values() 
        if isinstance(result, dict) and result.get("passed", False)
    )
    
    # If no tests exist, assume 100% pass rate to avoid division by zero
    pass_rate = (passed_tests / total_tests) if total_tests > 0 else 1.0
    
    spec_score_component = pass_rate * 100
    integration_score_component = pass_rate * 100

    # 2. Calculate Security Posture Component
    security_score_component = 100
    has_critical = False
    
    for finding in threat_findings:
        severity = finding.get("severity", "").upper()
        if severity == "CRITICAL":
            has_critical = True
        elif severity == "HIGH":
            security_score_component -= 15
        elif severity == "WARNING":
            security_score_component -= 5
            
    # Ensure security score doesn't go below 0
    security_score_component = max(0, security_score_component)
    
    # Apply CRITICAL hard-cap
    if has_critical:
        security_score_component = min(security_score_component, 40)
        
    # 3. Apply Weights
    # - 40% Spec Pass-Rate
    # - 40% Security Posture
    # - 20% Integration Pass-Rate
    final_score = (
        (spec_score_component * 0.40) +
        (security_score_component * 0.40) +
        (integration_score_component * 0.20)
    )
    
    return int(round(final_score))
