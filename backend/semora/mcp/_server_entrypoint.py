"""Server entrypoint for the Semora filesystem MCP server subprocess.

This module is invoked by ``mcp_client_config.get_mcp_server_params()`` as::

    python -m semora.mcp._server_entrypoint

It reads ``SEMORA_REPO_ROOT`` from the environment, creates a
:class:`~semora.mcp.filesystem_server.FilesystemMCPServer`, and starts the
stdio transport so that MCP clients (ADK agents) can call its tools.

This file must NOT contain business logic; it is a thin launch shim only.
"""

import os
import sys

from dotenv import load_dotenv

from semora.mcp.filesystem_server import create_server


def main() -> None:
    """Load config, create the server, and start the stdio transport.

    Raises:
        SystemExit: With a non-zero exit code if ``SEMORA_REPO_ROOT`` is unset.
    """
    load_dotenv()

    repo_root = os.getenv("SEMORA_REPO_ROOT")
    if not repo_root:
        print(
            "ERROR: SEMORA_REPO_ROOT environment variable is not set.",
            file=sys.stderr,
        )
        sys.exit(1)

    server = create_server(repo_root=repo_root)
    server.mcp.run()  # stdio transport; blocks until the client disconnects


if __name__ == "__main__":
    main()
