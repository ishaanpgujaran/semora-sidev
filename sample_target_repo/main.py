"""Sample FastAPI Application.

Acts as a target repository for demonstrating Semora quality gate checks.
"""

from fastapi import FastAPI

app = FastAPI(title="Dummy Target Repo")


@app.get("/")
def read_root() -> dict:
    """Home endpoint.

    Returns:
        dict: Standard greeting.
    """
    # TODO(spec-execution-agent): Implement mock endpoints to run quality checks against.
    return {"hello": "world"}
