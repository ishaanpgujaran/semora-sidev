"""Test suite for semora.mcp.filesystem_server.

Tests the three MCP tools exposed by FilesystemMCPServer:
  - list_files   : glob-style listing relative to the mounted root
  - read_file    : text content retrieval with binary-file rejection
  - get_git_diff : staged / unstaged diff via GitPython

Fixture strategy
----------------
``fixture_repo`` creates a real git repository inside a ``tmp_path``
temporary directory.  The directory structure is:

    <tmp>/
        hello.py           (tracked)
        README.md          (tracked)
        src/
            utils.py       (tracked)

The server is constructed directly in-process (no subprocess needed because
FastMCP 1.x exposes ``call_tool`` for synchronous / async in-process testing).

Error contract
--------------
FastMCP wraps tool exceptions in ``mcp.server.fastmcp.exceptions.ToolError``
with the original exception preserved as ``__cause__``.  Tests that expect a
PermissionError therefore assert ``isinstance(exc.value.__cause__, PermissionError)``.
"""

import asyncio
from pathlib import Path
from typing import Generator

import git
import pytest

from mcp.server.fastmcp.exceptions import ToolError
from semora.mcp.filesystem_server import FilesystemMCPServer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run(coro):  # type: ignore[no-untyped-def]
    """Run a coroutine synchronously — avoids repeating asyncio.run()."""
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def fixture_repo(tmp_path: Path) -> Generator[tuple[Path, FilesystemMCPServer], None, None]:
    """Create a minimal git repository and return (repo_root, server).

    The repository contains:
      - hello.py       (tracked, committed)
      - README.md      (tracked, committed)
      - src/utils.py   (tracked, committed)

    All files are committed so that git diff operations start from a clean
    baseline.
    """
    # ---- Create directory layout ----------------------------------------
    (tmp_path / "src").mkdir()

    hello_py = tmp_path / "hello.py"
    hello_py.write_text('print("hello, semora")\n', encoding="utf-8")

    readme = tmp_path / "README.md"
    readme.write_text("# Fixture Repo\nUsed for MCP server tests.\n", encoding="utf-8")

    utils_py = tmp_path / "src" / "utils.py"
    utils_py.write_text("def noop() -> None:\n    pass\n", encoding="utf-8")

    # ---- Initialise git repo and commit all files -----------------------
    repo = git.Repo.init(str(tmp_path))
    repo.config_writer().set_value("user", "name", "Test User").release()
    repo.config_writer().set_value("user", "email", "test@semora.dev").release()

    repo.index.add(["hello.py", "README.md", "src/utils.py"])
    repo.index.commit("chore: initial fixture commit")

    # ---- Spin up the in-process MCP server -------------------------------
    server = FilesystemMCPServer(repo_root=str(tmp_path))

    yield tmp_path, server


# ---------------------------------------------------------------------------
# Tests: list_files
# ---------------------------------------------------------------------------


class TestListFiles:
    """Verify the list_files tool."""

    def test_list_all_python_files(
        self, fixture_repo: tuple[Path, FilesystemMCPServer]
    ) -> None:
        """list_files with '**/*.py' must find hello.py and src/utils.py."""
        _, server = fixture_repo

        content_blocks, structured = _run(
            server.mcp.call_tool("list_files", {"pattern": "**/*.py"})
        )
        result: list = structured["result"]

        assert isinstance(result, list), "Expected a list return value"
        assert "hello.py" in result
        assert "src/utils.py" in result

    def test_list_markdown_files(
        self, fixture_repo: tuple[Path, FilesystemMCPServer]
    ) -> None:
        """list_files with '*.md' must find README.md at root level."""
        _, server = fixture_repo

        _, structured = _run(
            server.mcp.call_tool("list_files", {"pattern": "*.md"})
        )
        result: list = structured["result"]

        assert "README.md" in result

    def test_list_nested_only(
        self, fixture_repo: tuple[Path, FilesystemMCPServer]
    ) -> None:
        """list_files with 'src/*.py' must return only files inside src/."""
        _, server = fixture_repo

        _, structured = _run(
            server.mcp.call_tool("list_files", {"pattern": "src/*.py"})
        )
        result: list = structured["result"]

        assert result == ["src/utils.py"]

    def test_list_empty_when_no_match(
        self, fixture_repo: tuple[Path, FilesystemMCPServer]
    ) -> None:
        """list_files with a pattern matching nothing must return []."""
        _, server = fixture_repo

        _, structured = _run(
            server.mcp.call_tool("list_files", {"pattern": "**/*.ts"})
        )
        result: list = structured["result"]

        assert result == []


# ---------------------------------------------------------------------------
# Tests: read_file
# ---------------------------------------------------------------------------


class TestReadFile:
    """Verify the read_file tool."""

    def test_read_valid_file_returns_correct_content(
        self, fixture_repo: tuple[Path, FilesystemMCPServer]
    ) -> None:
        """read_file must return the exact text of hello.py."""
        _, server = fixture_repo

        _, structured = _run(
            server.mcp.call_tool("read_file", {"path": "hello.py"})
        )
        content: str = structured["result"]

        assert 'print("hello, semora")' in content

    def test_read_nested_file(
        self, fixture_repo: tuple[Path, FilesystemMCPServer]
    ) -> None:
        """read_file must work for files in subdirectories."""
        _, server = fixture_repo

        _, structured = _run(
            server.mcp.call_tool("read_file", {"path": "src/utils.py"})
        )
        content: str = structured["result"]

        assert "def noop" in content

    def test_read_file_raises_permission_error_on_traversal(
        self, fixture_repo: tuple[Path, FilesystemMCPServer]
    ) -> None:
        """read_file must raise PermissionError for paths containing '..'."""
        _, server = fixture_repo

        with pytest.raises(ToolError) as exc_info:
            _run(
                server.mcp.call_tool("read_file", {"path": "../../etc/passwd"})
            )

        # FastMCP wraps the original exception as __cause__
        assert isinstance(exc_info.value.__cause__, PermissionError), (
            f"Expected PermissionError as __cause__, got: "
            f"{type(exc_info.value.__cause__)}"
        )

    def test_read_file_raises_permission_error_for_symlink_escape(
        self, fixture_repo: tuple[Path, FilesystemMCPServer]
    ) -> None:
        """read_file must reject a path that resolves outside root via symlink."""
        repo_root, server = fixture_repo

        # Create a symlink inside the repo that points to a file outside it.
        # (On systems that support symlinks; skip otherwise.)
        outside_file = repo_root.parent / "outside.txt"
        outside_file.write_text("secret content", encoding="utf-8")
        link = repo_root / "escape_link.txt"
        try:
            link.symlink_to(outside_file)
        except (OSError, NotImplementedError):
            pytest.skip("Symlinks not supported on this system")

        with pytest.raises(ToolError) as exc_info:
            _run(
                server.mcp.call_tool("read_file", {"path": "escape_link.txt"})
            )

        assert isinstance(exc_info.value.__cause__, PermissionError)

    def test_read_binary_file_raises_value_error(
        self, fixture_repo: tuple[Path, FilesystemMCPServer]
    ) -> None:
        """read_file must raise ValueError on binary files, not return garbage."""
        repo_root, server = fixture_repo

        binary_file = repo_root / "data.bin"
        binary_file.write_bytes(bytes(range(256)))  # definitely not valid UTF-8

        with pytest.raises(ToolError) as exc_info:
            _run(
                server.mcp.call_tool("read_file", {"path": "data.bin"})
            )

        assert isinstance(exc_info.value.__cause__, ValueError)

    def test_read_file_not_found(
        self, fixture_repo: tuple[Path, FilesystemMCPServer]
    ) -> None:
        """read_file must raise FileNotFoundError for non-existent paths."""
        _, server = fixture_repo

        with pytest.raises(ToolError) as exc_info:
            _run(
                server.mcp.call_tool("read_file", {"path": "nonexistent.py"})
            )

        assert isinstance(exc_info.value.__cause__, FileNotFoundError)


# ---------------------------------------------------------------------------
# Tests: get_git_diff
# ---------------------------------------------------------------------------


class TestGetGitDiff:
    """Verify the get_git_diff tool."""

    def test_no_unstaged_diff_on_clean_repo(
        self, fixture_repo: tuple[Path, FilesystemMCPServer]
    ) -> None:
        """After the initial commit with no further changes, unstaged diff is empty."""
        _, server = fixture_repo

        _, structured = _run(
            server.mcp.call_tool("get_git_diff", {"staged_only": False})
        )
        diff: str = structured["result"]

        assert diff == "", f"Expected empty diff on clean repo, got: {diff!r}"

    def test_no_staged_diff_on_clean_repo(
        self, fixture_repo: tuple[Path, FilesystemMCPServer]
    ) -> None:
        """After the initial commit with nothing staged, staged diff is empty."""
        _, server = fixture_repo

        _, structured = _run(
            server.mcp.call_tool("get_git_diff", {"staged_only": True})
        )
        diff: str = structured["result"]

        assert diff == "", f"Expected empty staged diff on clean repo, got: {diff!r}"

    def test_unstaged_diff_after_modifying_tracked_file(
        self, fixture_repo: tuple[Path, FilesystemMCPServer]
    ) -> None:
        """Modifying a tracked file must produce a non-empty unstaged diff."""
        repo_root, server = fixture_repo

        # Modify hello.py without staging
        hello_py = repo_root / "hello.py"
        hello_py.write_text(
            'print("hello, semora")\nprint("new line added")\n',
            encoding="utf-8",
        )

        _, structured = _run(
            server.mcp.call_tool("get_git_diff", {"staged_only": False})
        )
        diff: str = structured["result"]

        assert diff != "", "Expected a non-empty diff after modifying a tracked file"

    def test_staged_diff_after_staging_modification(
        self, fixture_repo: tuple[Path, FilesystemMCPServer]
    ) -> None:
        """Staging a modification must produce a non-empty staged diff."""
        repo_root, server = fixture_repo

        # Modify and stage hello.py
        hello_py = repo_root / "hello.py"
        hello_py.write_text(
            'print("hello, semora")\nprint("staged line")\n',
            encoding="utf-8",
        )
        repo = git.Repo(str(repo_root))
        repo.index.add(["hello.py"])

        _, structured = _run(
            server.mcp.call_tool("get_git_diff", {"staged_only": True})
        )
        diff: str = structured["result"]

        assert diff != "", "Expected a non-empty staged diff after git add"

    def test_staged_diff_empty_after_unstaged_change(
        self, fixture_repo: tuple[Path, FilesystemMCPServer]
    ) -> None:
        """An unstaged modification must NOT appear in the staged diff."""
        repo_root, server = fixture_repo

        # Modify hello.py but do NOT stage it
        hello_py = repo_root / "hello.py"
        hello_py.write_text(
            'print("hello, semora")\nprint("unstaged")\n',
            encoding="utf-8",
        )

        _, structured = _run(
            server.mcp.call_tool("get_git_diff", {"staged_only": True})
        )
        diff: str = structured["result"]

        assert diff == "", (
            "Unstaged change must not appear in staged diff; got: {diff!r}"
        )


# ---------------------------------------------------------------------------
# Tests: constructor validation
# ---------------------------------------------------------------------------


class TestConstructorValidation:
    """Verify FilesystemMCPServer rejects invalid root paths at construction."""

    def test_nonexistent_root_raises_value_error(self, tmp_path: Path) -> None:
        """Constructor must raise ValueError for a path that does not exist."""
        with pytest.raises(ValueError, match="existing directory"):
            FilesystemMCPServer(repo_root=str(tmp_path / "no_such_dir"))

    def test_file_as_root_raises_value_error(self, tmp_path: Path) -> None:
        """Constructor must raise ValueError when root is a file, not a directory."""
        f = tmp_path / "not_a_dir.txt"
        f.write_text("content", encoding="utf-8")
        with pytest.raises(ValueError, match="existing directory"):
            FilesystemMCPServer(repo_root=str(f))
