import asyncio
from google.adk.workflow import Workflow, JoinNode, node
from semora.graph.state import RunState
from semora.graph.spec_agent import generate_specs
from semora.graph.threat_agent import audit_security
from semora.graph.aggregator import aggregate_results


@node
async def spec_node(node_input: RunState) -> RunState:
    print(f"[spec_node] Received RunState with repo: {node_input.repo_path}")
    # Call BDD spec generation
    updated_state = generate_specs(node_input)
    print(f"[spec_node] Finished.")
    return updated_state



from semora.graph.execution_agent import execute_specs


@node
async def execution_node(node_input: RunState) -> RunState:
    print(f"[execution_node] Started processing...")
    updated_state = execute_specs(node_input)
    print(f"[execution_node] Finished.")
    return updated_state


@node
async def threat_node(node_input: RunState) -> RunState:
    print(f"[threat_node] Started processing...")
    updated_state = audit_security(node_input)
    print(f"[threat_node] Finished.")
    return updated_state


@node
async def aggregator_node(node_input: dict) -> RunState:
    # JoinNode output is a dict keyed by predecessor node names
    print(f"[aggregator_node] Aggregating results from: {list(node_input.keys())}")

    # Merge execution results and threat findings into a single RunState
    exec_state = node_input.get("execution_node")
    threat_state = node_input.get("threat_node")

    if exec_state is None:
        exec_state = RunState(repo_path="", diff_text="")
    if threat_state is None:
        threat_state = RunState(repo_path="", diff_text="")

    # Build merged state: start from execution, overlay threat findings
    merged = exec_state.model_copy()
    merged.threat_findings = threat_state.threat_findings

    # Compute compliance score via the aggregator
    final_state = aggregate_results(merged)
    print(f"[aggregator_node] Compliance score: {final_state.compliance_score}")
    print(f"[aggregator_node] Finished.")
    return final_state


merge = JoinNode(name="merge")

# Wire the graph topology
semora_graph = Workflow(
    name="semora_graph",
    input_schema=RunState,
    state_schema=RunState,
    edges=[
        ('START', spec_node),
        (spec_node, (execution_node, threat_node)),
        ((execution_node, threat_node), merge),
        (merge, aggregator_node)
    ]
)
