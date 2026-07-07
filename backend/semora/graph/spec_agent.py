"""Spec Agent Module.

Handles automated BDD (Behavior-Driven Development) test spec generation
by analyzing code diffs.
This module defines the Spec Agent workflow node and helper functions,
utilizing Gemini API for Gherkin feature file generation.
"""

import os
from typing import Dict, Any, Union, List
from dotenv import load_dotenv
from pydantic import BaseModel
from google import genai
from google.genai import types

from backend.semora.graph.state import RunState

# Load environment variables from .env
load_dotenv()


class FeatureFile(BaseModel):
    """Represents a single Gherkin feature file."""
    filename: str
    content: str


class FeatureGenerationResult(BaseModel):
    """List of generated feature files."""
    features: List[FeatureFile]


def generate_specs(
    state: Union[Dict[str, Any], RunState],
    recent_commit_messages: List[str] = None
) -> Union[Dict[str, Any], RunState]:
    """Analyze changes in the target repository and generate BDD feature files.

    Args:
        state (Union[Dict[str, Any], RunState]): Current pipeline state.
        recent_commit_messages (List[str], optional): Recent commit messages.

    Returns:
        Union[Dict[str, Any], RunState]: Updated pipeline state with generated specifications.
    """
    is_pydantic = not isinstance(state, dict) and hasattr(state, "repo_path")

    if is_pydantic:
        repo_path = state.repo_path
        diff_text = state.diff_text
        generated_specs = state.generated_specs
    else:
        repo_path = state.get("repo_path", "")
        diff_text = state.get("diff_text", "")
        generated_specs = state.setdefault("generated_specs", [])

    if not diff_text or not diff_text.strip():
        # No diff to analyze, return state unmodified
        return state

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set.")

    # Initialize Gemini Client
    client = genai.Client(api_key=api_key)

    commit_msg_str = "\n".join(recent_commit_messages) if recent_commit_messages else "None"

    prompt = f"""You are an expert QA and BDD test spec writer.
Analyze the following git diff and recent commit messages to identify new or changed functions.

For each new or changed function, write a Gherkin .feature file.
The filename of each Gherkin .feature file MUST be exactly '<function_name>.feature' where <function_name> is the name of the new or changed function (for example, if the function is named 'is_valid_email', the filename MUST be exactly 'is_valid_email.feature').

Each Gherkin .feature file MUST cover:
1. Happy path: The standard successful execution flow of the function.
2. At least three adversarial edge cases appropriate to the function's apparent purpose. For functions taking user input, this means:
   - An empty string or default/empty input.
   - A value of the wrong type (e.g. integer instead of string, None/null, etc.).
   - A boundary or injection-style payload where relevant (e.g. extremely long strings, SQL injection, script injection, format characters).
3. Explicit exception-handling expectations: The spec must assert that invalid input produces a clean error response, custom exception, or validation error, and never causes an unhandled crash or unexpected crash.

Ensure scenario titles are highly descriptive and human-readable, not generic (do NOT use "Scenario 1", "Edge case 2", or similar). Each feature file must have at least 4 scenarios.

Git Diff:
{diff_text}

Recent Commit Messages:
{commit_msg_str}
"""

    import time
    max_retries = 5
    delay = 2.0
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=FeatureGenerationResult,
                ),
            )
            break
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            time.sleep(delay)
            delay *= 2.0

    result = response.parsed
    if not result or not result.features:
        return state

    # Ensure target tests/features directory exists
    features_dir = os.path.join(repo_path, "tests", "features")
    os.makedirs(features_dir, exist_ok=True)

    for feature in result.features:
        filename = feature.filename
        if not filename.endswith(".feature"):
            filename += ".feature"

        file_path = os.path.join(features_dir, filename)
        gherkin_content = feature.content.replace("\\n", "\n").replace("\\r\\n", "\n")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(gherkin_content)

        if is_pydantic:
            if file_path not in state.generated_specs:
                state.generated_specs.append(file_path)
        else:
            if file_path not in state["generated_specs"]:
                state["generated_specs"].append(file_path)

    return state
