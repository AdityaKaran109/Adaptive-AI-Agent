"""Tools the agent can call. The lesson task is running the sandbox/ tests.

Every call is recorded, because the recording is what induction later reads. Keep this
surface small so traces stay readable.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from langchain_core.tools import tool

from src.traces.models import ToolCall

ROOT = Path(__file__).resolve().parents[2]
SANDBOX = ROOT / "sandbox"

CALLS: list[ToolCall] = []


def reset() -> None:
    CALLS.clear()


def _record(name: str, args: dict, ok: bool, output: str) -> None:
    CALLS.append(ToolCall(tool=name, args=args, ok=ok, output=output.strip()[:600]))


def _run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=300)
    return proc.returncode, (proc.stdout + proc.stderr)


@tool
def run_script(name: str) -> str:
    """Run a Python script in the sandbox directory by filename."""
    target = (SANDBOX / name).resolve()
    if not str(target).startswith(str(SANDBOX)) or target.suffix != ".py":
        _record("run_script", {"name": name}, False, "refused")
        return "refused: must be a .py file inside the sandbox"
    if not target.exists():
        _record("run_script", {"name": name}, False, "not found")
        return f"not found: {name}"
    code, out = _run([sys.executable, target.name], SANDBOX)
    _record("run_script", {"name": name}, code == 0, out)
    return out.strip() or f"exit code {code}"


@tool
def run_tests() -> str:
    """Run the pytest suite in the sandbox and return its output."""
    code, out = _run([sys.executable, "-m", "pytest", "tests", "-q"], SANDBOX)
    _record("run_tests", {}, code == 0, out)
    tail = "\n".join(out.strip().splitlines()[-12:])
    return f"exit code {code}\n{tail}"


@tool
def list_dir(path: str = ".") -> str:
    """List files in a path relative to the sandbox directory."""
    target = (SANDBOX / path).resolve()
    if not str(target).startswith(str(SANDBOX)):
        _record("list_dir", {"path": path}, False, "path escapes the sandbox")
        return "refused: path escapes the sandbox"
    if not target.exists():
        _record("list_dir", {"path": path}, False, "not found")
        return f"not found: {path}"
    names = sorted(p.name + ("/" if p.is_dir() else "") for p in target.iterdir())
    _record("list_dir", {"path": path}, True, ", ".join(names))
    return "\n".join(names) or "(empty)"


@tool
def read_file(path: str) -> str:
    """Read a text file relative to the sandbox directory."""
    target = (SANDBOX / path).resolve()
    if not str(target).startswith(str(SANDBOX)):
        _record("read_file", {"path": path}, False, "path escapes the sandbox")
        return "refused: path escapes the sandbox"
    if not target.exists():
        _record("read_file", {"path": path}, False, "not found")
        return f"not found: {path}"
    text = target.read_text(encoding="utf-8")[:4000]
    _record("read_file", {"path": path}, True, f"{len(text)} chars")
    return text


ALL = [run_script, run_tests, list_dir, read_file]
