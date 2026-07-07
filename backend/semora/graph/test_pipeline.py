import asyncio
import sys
import os

# Add the project root to sys.path so we can import backend.semora.graph
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from google.adk.apps import App
from google.adk.runners import InMemoryRunner
from semora.graph.state import RunState
from semora.graph.pipeline import semora_graph

from google.genai import types
import json

async def main():
    print("Setting up App and Runner...")
    app = App(name="semora_app", root_agent=semora_graph)
    runner = InMemoryRunner(app=app)
    
    session = await runner.session_service.create_session(
        app_name="semora_app", user_id="test_user"
    )
    
    # Create dummy run state
    initial_state_dict = {
        "repo_path": "/fake/repo",
        "diff_text": "diff --git a/test b/test\n+ test line",
        "generated_specs": [],
        "execution_results": {},
        "threat_findings": [],
        "compliance_score": None
    }
    
    print("Starting Workflow Execution...")
    content = types.Content(role="user", parts=[types.Part.from_text(text=json.dumps(initial_state_dict))])
    
    async for event in runner.run_async(
        user_id="test_user",
        session_id=session.id,
        new_message=content
    ):
        if event.output is not None:
            print("Workflow Output Result:", event.output)

if __name__ == "__main__":
    asyncio.run(main())
