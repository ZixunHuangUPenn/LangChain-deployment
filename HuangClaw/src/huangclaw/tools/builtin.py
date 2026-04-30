from __future__ import annotations

import os
import subprocess
from pathlib import Path

from langchain_core.tools import tool

from huangclaw.config import get_settings
from huangclaw.skills import PdfSkill


SKIP_DIRS = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache", ".ruff_cache", "chroma"}
PROTECTED_FILENAMES = {".env"}
BINARY_SUFFIXES = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".zip",
    ".gz",
    ".tar",
    ".7z",
    ".exe",
    ".dll",
    ".pyd",
    ".sqlite",
    ".db",
}


def _workspace_root() -> Path:
    return get_settings().workspace_dir.resolve()


def _resolve_workspace_path(relative_path: str) -> Path:
    path = Path(relative_path)
    if path.is_absolute():
        raise ValueError("Use a relative path inside the workspace.")
    root = _workspace_root()
    target = (root / path).resolve()
    if target != root and root not in target.parents:
        raise ValueError("Path escapes the configured workspace.")
    if target.name in PROTECTED_FILENAMES:
        raise ValueError("Protected files cannot be read or written by this agent.")
    if any(part in {".git", ".venv"} for part in target.parts):
        raise ValueError("Protected directories cannot be accessed by this agent.")
    return target


def _is_probably_text(path: Path) -> bool:
    return path.suffix.lower() not in BINARY_SUFFIXES


@tool
def list_workspace(relative_path: str = ".", max_entries: int = 80) -> str:
    """List files and folders under a relative workspace path."""
    target = _resolve_workspace_path(relative_path)
    if not target.exists():
        return f"Path not found: {relative_path}"
    if target.is_file():
        return str(target.relative_to(_workspace_root()))

    entries = []
    for child in sorted(target.iterdir(), key=lambda item: (item.is_file(), item.name.lower())):
        if child.name in SKIP_DIRS:
            continue
        suffix = "/" if child.is_dir() else ""
        entries.append(f"{child.relative_to(_workspace_root())}{suffix}")
        if len(entries) >= max_entries:
            entries.append("...")
            break
    return "\n".join(entries) or "(empty)"


@tool
def read_text_file(relative_path: str, max_chars: int = 12000) -> str:
    """Read a text file from the workspace."""
    target = _resolve_workspace_path(relative_path)
    if not target.exists():
        return f"File not found: {relative_path}"
    if not target.is_file():
        return f"Not a file: {relative_path}"
    if not _is_probably_text(target):
        return f"Refusing to read likely-binary file: {relative_path}"
    content = target.read_text(encoding="utf-8", errors="replace")
    if len(content) > max_chars:
        return content[:max_chars] + f"\n\n[truncated after {max_chars} chars]"
    return content


@tool
def write_text_file(relative_path: str, content: str, overwrite: bool = False) -> str:
    """Write a UTF-8 text file inside the workspace. Set overwrite=true to replace an existing file."""
    target = _resolve_workspace_path(relative_path)
    if target.exists() and not overwrite:
        return f"File already exists: {relative_path}. Pass overwrite=true to replace it."
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"Wrote {len(content)} chars to {target.relative_to(_workspace_root())}"


@tool
def search_workspace(query: str, glob: str = "*", max_matches: int = 40) -> str:
    """Search text files in the workspace for a case-insensitive query."""
    if not query.strip():
        return "Empty query."

    root = _workspace_root()
    matches: list[str] = []
    needle = query.lower()

    for path in root.rglob(glob or "*"):
        if len(matches) >= max_matches:
            break
        if path.is_dir() or any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.name in PROTECTED_FILENAMES or not _is_probably_text(path):
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line_no, line in enumerate(lines, start=1):
            if needle in line.lower():
                rel = path.relative_to(root)
                matches.append(f"{rel}:{line_no}: {line.strip()[:240]}")
                if len(matches) >= max_matches:
                    break

    return "\n".join(matches) if matches else "No matches."


@tool
def run_shell_command(command: str, timeout_seconds: int = 30) -> str:
    """Run a bounded shell command in the workspace and return stdout/stderr."""
    blocked = [
        "rm -rf",
        "git reset --hard",
        "git checkout --",
        "remove-item",
        "del /s",
        "format ",
    ]
    lowered = command.lower()
    if any(term in lowered for term in blocked):
        return "Command blocked by built-in safety policy."

    timeout = max(1, min(timeout_seconds, 120))
    if os.name == "nt":
        args = ["powershell", "-NoProfile", "-Command", command]
    else:
        args = ["/bin/sh", "-lc", command]

    try:
        completed = subprocess.run(
            args,
            cwd=_workspace_root(),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return f"Command timed out after {timeout} seconds."

    output = []
    output.append(f"exit_code={completed.returncode}")
    if completed.stdout:
        output.append("[stdout]\n" + completed.stdout[-12000:])
    if completed.stderr:
        output.append("[stderr]\n" + completed.stderr[-12000:])
    return "\n".join(output)


@tool
def rag_search(question: str, k: int = 5) -> str:
    """Search the Learning in Robotics PDF knowledge base stored in Chroma."""
    try:
        hits = PdfSkill().query(question, k=k)
    except Exception as exc:
        return f"RAG search failed: {exc}"
    if not hits:
        return "No PDF chunks found. Run `uv run huangclaw ingest --reset` first."
    return "\n\n---\n\n".join(hit.format() for hit in hits)


def get_builtin_tools():
    return [
        list_workspace,
        read_text_file,
        write_text_file,
        search_workspace,
        run_shell_command,
        rag_search,
    ]
