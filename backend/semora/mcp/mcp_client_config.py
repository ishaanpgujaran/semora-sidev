"""MCP Client Configuration for Semora ADK Graph Agents.

This module shows how the ADK Graph agents (Spec, Execution, Security,
Reporting/Sync) connect to the ``FilesystemMCPServer`` as MCP clients.

Position in the Semora architecture
------------------------------------
  ADK Graph Orchestrator
    ├─> Spec Agent  ──────────────────┐
    ├─> Execution Agent  ─────────────┼──> get_mcp_server_params()
    ├─> Security Agent  ──────────────┘          │
    └─> Reporting/Sync Agent                     ▼
                                     FilesystemMCPServer (filesystem_server.py)

Design notes
------------
* Connection configuration is read exclusively from environment variables;
  nothing is hardcoded here.
* The returned ``StdioServerParameters`` object is compatible with the ADK
  ``MCPToolset`` integration, which accepts stdio-based MCP server configs
  directly.
* This module contains **connection setup only**.  Business logic (which tool
  to call and with what arguments) lives in the respective agent modules under
  ``semora/graph/``.

Environment variables consumed
------------------------------
``SEMORA_REPO_ROOT``
    Absolute path to the target repository that the MCP server should mount.
    Must be set before any agent calls :func:`get_mcp_server_params`.
"""

import os
from typing import List

from mcp.client.stdio import StdioServerParameters


def get_mcp_server_params(extra_args: List[str] | None = None) -> StdioServerParameters:
    """Build the ``StdioServerParameters`` for connecting to the Semora filesystem server.

    This configuration is passed directly to the ADK ``MCPToolset`` (or any
    MCP client that accepts ``StdioServerParameters``) so that agents can call
    ``list_files``, ``read_file``, and ``get_git_diff`` without touching the
    filesystem themselves.

    The MCP server is launched as a subprocess via ``python -m
    semora.mcp._server_entrypoint``, which reads ``SEMORA_REPO_ROOT`` from the
    environment and passes it to :class:`~semora.mcp.filesystem_server.FilesystemMCPServer`.

    Args:
        extra_args: Optional list of additional CLI arguments forwarded to the
            server subprocess.  Rarely needed in normal usage.

    Returns:
        A :class:`mcp.client.stdio.StdioServerParameters` instance ready for
        use with ``MCPToolset`` or ``ClientSession``.

    Raises:
        EnvironmentError: If the required ``SEMORA_REPO_ROOT`` environment
            variable is not set.

    Example::

        import asyncio
        from mcp.client.stdio import stdio_client
        from semora.mcp.mcp_client_config import get_mcp_server_params

        params = get_mcp_server_params()

        async def run():
            async with stdio_client(params) as (read, write):
                # Use read/write streams with a ClientSession to call tools.
                ...

        asyncio.run(run())
    """
    repo_root = os.getenv("SEMORA_REPO_ROOT")
    if not repo_root:
        raise EnvironmentError(
            "The SEMORA_REPO_ROOT environment variable must be set to the "
            "absolute path of the repository to analyse."
        )

    command_args: List[str] = [
        "-m",
        "semora.mcp._server_entrypoint",
    ]
    if extra_args:
        command_args.extend(extra_args)

    return StdioServerParameters(
        command="python",
        args=command_args,
        env={
            **os.environ.copy(),   # propagate the full current environment
            "SEMORA_REPO_ROOT": repo_root,
        },
    )
