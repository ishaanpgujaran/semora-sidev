"""Filesystem MCP Server — core of the Semora MCP Agent.

This module is the single, authoritative gateway through which every other
Semora agent (Spec, Execution, Security, Reporting/Sync) reads the target
repository.  No agent is permitted to touch the host filesystem directly;
all file access must flow through the three tools registered here.

Position in the Semora architecture
------------------------------------
  Git Commit
    └─> Semora CLI
          └─> ADK Graph Orchestrator
                ├─> Spec Agent  ──────────────────┐
                ├─> Execution Agent  ─────────────┼──> FilesystemMCPServer (THIS MODULE)
                ├─> Security Agent  ──────────────┘
                └─> Reporting/Sync Agent

Security contract
-----------------
* The server is constructed with an explicit *repo_root* directory.
* Every path argument passed to ``read_file`` or ``list_files`` is resolved
  with ``os.path.realpath`` and checked to confirm it stays inside that root
  before any I/O occurs.  Any violation raises ``PermissionError``—never a
  silent failure or garbage return value.
* A path containing ``..`` segments is also rejected at the string level as
  an early-exit defence-in-depth measure.

Configuration
-------------
The repo_root must be supplied by the caller (e.g. from the environment via
``os.getenv``); nothing in this file is hardcoded.
"""

import glob
import os
from pathlib import Path
from typing import List

import git
from mcp.server.fastmcp import FastMCP


class FilesystemMCPServer:
    """MCP server that exposes a target repository to Semora's ADK agents.

    All three tools (``list_files``, ``read_file``, ``get_git_diff``) are
    registered on a ``FastMCP`` instance during construction.  The caller
    owns the transport lifecycle; use ``server.mcp`` to access the underlying
    ``FastMCP`` object.

    Args:
        repo_root: Absolute path to the repository directory to mount.  This
            value is never hardcoded—callers must supply it (e.g. from an
            environment variable).

    Raises:
        ValueError: If *repo_root* does not exist or is not a directory.
    """

    def __init__(self, repo_root: str) -> None:
        resolved_root = Path(os.path.realpath(repo_root))
        if not resolved_root.is_dir():
            raise ValueError(
                f"repo_root must be an existing directory; got: {repo_root!r}"
            )

        self._root: Path = resolved_root
        self.mcp: FastMCP = FastMCP("semora-filesystem")

        # Register all three tools on the FastMCP instance.
        self._register_tools()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _safe_resolve(self, relative_path: str) -> Path:
        """Resolve *relative_path* against the mounted root and validate it.

        Args:
            relative_path: A caller-supplied path string, relative to the
                mounted root.  Must not contain ``..`` components and must
                resolve (via ``os.path.realpath``) to a location inside
                ``self._root``.

        Returns:
            The fully resolved absolute :class:`pathlib.Path`.

        Raises:
            PermissionError: If *relative_path* contains ``..`` components or
                resolves to a location outside the mounted root.
        """
        # Defence-in-depth: reject any path that contains ".." at the string
        # level before touching the filesystem.
        normalised = os.path.normpath(relative_path)
        if ".." in Path(normalised).parts:
            raise PermissionError(
                f"Path traversal detected in {relative_path!r}: '..' components "
                "are not permitted."
            )

        # Resolve symlinks and relative segments, then verify containment.
        candidate = Path(os.path.realpath(self._root / relative_path))
        try:
            candidate.relative_to(self._root)
        except ValueError:
            raise PermissionError(
                f"Access denied: resolved path {str(candidate)!r} is outside "
                f"the mounted root {str(self._root)!r}."
            ) from None

        return candidate

    # ------------------------------------------------------------------
    # Tool registration
    # ------------------------------------------------------------------

    def _register_tools(self) -> None:
        """Register all MCP tools on ``self.mcp``."""

        # Keep ``self`` in scope via closure; ``mcp`` is a local alias so the
        # decorator syntax is clean.
        mcp = self.mcp
        server = self  # explicit alias avoids late-binding pitfalls

        # ------------------------------------------------------------------ #
        # Tool 1 — list_files                                                  #
        # ------------------------------------------------------------------ #
        @mcp.tool()
        def list_files(pattern: str) -> List[str]:
            """Glob-style file listing relative to the mounted repository root.

            Args:
                pattern: A glob pattern evaluated relative to the mounted root
                    (e.g. ``"**/*.py"`` or ``"src/*.ts"``).  The pattern must
                    not contain ``..`` path components.

            Returns:
                A sorted list of matching file paths, each expressed relative
                to the mounted root, using forward slashes.

            Raises:
                PermissionError: If the pattern resolves any results outside
                    the mounted root.
            """
            # Validate that the pattern itself does not start with a traversal.
            normalised_pattern = os.path.normpath(pattern)
            if ".." in Path(normalised_pattern).parts:
                raise PermissionError(
                    f"Path traversal detected in glob pattern {pattern!r}: "
                    "'..' components are not permitted."
                )

            abs_pattern = str(server._root / pattern)
            raw_matches = glob.glob(abs_pattern, recursive=True)

            result: List[str] = []
            for abs_match in sorted(raw_matches):
                resolved = Path(os.path.realpath(abs_match))
                # Skip any match that somehow resolves outside the root
                # (e.g. via symlinks).
                try:
                    rel = resolved.relative_to(server._root)
                except ValueError:
                    raise PermissionError(
                        f"Glob result {abs_match!r} resolves outside the "
                        f"mounted root {str(server._root)!r}."
                    ) from None
                if resolved.is_file():
                    result.append(rel.as_posix())

            return result

        # ------------------------------------------------------------------ #
        # Tool 2 — read_file                                                   #
        # ------------------------------------------------------------------ #
        @mcp.tool()
        def read_file(path: str) -> str:
            """Return the text content of a file inside the mounted repository.

            Args:
                path: Path to the file, relative to the mounted root.  Must
                    not contain ``..`` components and must resolve inside the
                    root.

            Returns:
                The file contents decoded as UTF-8 text.

            Raises:
                PermissionError: If *path* traverses outside the mounted root.
                ValueError: If the file is binary (non-UTF-8) so that garbage
                    bytes are never silently returned to an LLM agent.
                FileNotFoundError: If the resolved path does not exist.
            """
            resolved = server._safe_resolve(path)

            if not resolved.exists():
                raise FileNotFoundError(
                    f"File not found inside mounted root: {path!r}"
                )
            if not resolved.is_file():
                raise IsADirectoryError(
                    f"Path {path!r} is a directory, not a file."
                )

            # Read as bytes first so we can detect binary content.
            raw_bytes = resolved.read_bytes()
            try:
                return raw_bytes.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ValueError(
                    f"File {path!r} appears to be binary and cannot be returned "
                    "as text.  Only UTF-8-encoded text files are supported."
                ) from exc

        # ------------------------------------------------------------------ #
        # Tool 3 — get_git_diff                                                #
        # ------------------------------------------------------------------ #
        @mcp.tool()
        def get_git_diff(staged_only: bool) -> str:
            """Return the git diff for the mounted repository.

            Uses GitPython internally to compute the diff without spawning a
            shell subprocess, which keeps the operation safe on all platforms.

            Args:
                staged_only: When ``True``, returns the diff of staged changes
                    (equivalent to ``git diff --staged``).  When ``False``,
                    returns the diff of unstaged working-tree changes (equivalent
                    to ``git diff``).

            Returns:
                The diff output as a UTF-8 string.  Returns an empty string if
                there are no changes of the requested type.

            Raises:
                git.InvalidGitRepositoryError: If the mounted root is not inside
                    a git repository.
                git.GitCommandError: If the underlying git operation fails.
            """
            repo = git.Repo(str(server._root), search_parent_directories=True)

            if staged_only:
                # Diff between HEAD and the index (staging area).
                # create_patch=True is required — without it, diff_item.diff
                # contains only metadata (an empty string), not the actual hunk.
                try:
                    diff_items = repo.index.diff("HEAD", create_patch=True)
                except git.BadName:
                    # Brand-new repo with no commits yet — nothing staged.
                    return ""

                parts: list[str] = []
                for diff_item in diff_items:
                    raw: bytes = diff_item.diff  # bytes when create_patch=True
                    parts.append(raw.decode("utf-8", errors="replace"))
                return "".join(parts)
            else:
                # Diff between the index and the working tree (unstaged changes).
                diff_items = repo.index.diff(None, create_patch=True)
                parts = []
                for diff_item in diff_items:
                    raw = diff_item.diff  # bytes when create_patch=True
                    parts.append(raw.decode("utf-8", errors="replace"))
                return "".join(parts)



def create_server(repo_root: str) -> FilesystemMCPServer:
    """Factory function: create a :class:`FilesystemMCPServer` for *repo_root*.

    This is the preferred entry-point for external callers.  ``repo_root``
    should be read from the environment at the call site, not hardcoded.

    Example::

        import os
        from semora.mcp.filesystem_server import create_server

        server = create_server(os.environ["SEMORA_REPO_ROOT"])
        server.mcp.run()  # starts stdio transport

    Args:
        repo_root: Absolute path to the repository to mount.

    Returns:
        A fully configured :class:`FilesystemMCPServer` instance.
    """
    return FilesystemMCPServer(repo_root=repo_root)
