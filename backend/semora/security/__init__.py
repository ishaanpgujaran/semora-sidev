"""Security analysis package for Semora.

Provides STRIDE threat modeling via Semgrep scanning and category mapping.

Public API
----------
run_semgrep       — invoke the semgrep CLI against a list of changed files
SemgrepNotFoundError — raised when semgrep is not on PATH
map_to_stride     — enrich a raw semgrep finding with STRIDE category + patch
STRIDE_MAPPING    — exact-match lookup table (custom rule IDs → STRIDE category)
"""

from semora.security.semgrep_wrapper import SemgrepNotFoundError, run_semgrep
from semora.security.stride_rules import STRIDE_MAPPING, map_to_stride

__all__ = [
    "run_semgrep",
    "SemgrepNotFoundError",
    "map_to_stride",
    "STRIDE_MAPPING",
]
