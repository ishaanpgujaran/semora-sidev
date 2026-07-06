import asyncio
from google.adk.workflow import Workflow, JoinNode, node
from backend.semora.graph.state import RunState


@node
async def spec_node(node_input: RunState) -> RunState:
    print(f"[spec_node] Received RunState with repo: {node_input.repo_path}")
    await asyncio.sleep(0.5)
    print(f"[spec_node] Finished.")
    return node_input


@node
async def execution_node(node_input: RunState) -> RunState:
    print(f"[execution_node] Started processing...")
    await asyncio.sleep(1.5)
    print(f"[execution_node] Finished.")
    return node_input


@node
async def threat_node(node_input: RunState) -> RunState:
    print(f"[threat_node] Started processing...")
    await asyncio.sleep(1.5)
    print(f"[threat_node] Finished.")
    return node_input


@node
async def aggregator_node(node_input: dict) -> RunState:
    # JoinNode output is a dict keyed by predecessor node names
    print(f"[aggregator_node] Aggregating results from: {list(node_input.keys())}")
    await asyncio.sleep(0.5)
    print(f"[aggregator_node] Finished.")
    return node_input["execution_node"]


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
