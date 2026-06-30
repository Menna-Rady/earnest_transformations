"""Safe subprocess execution for Spark and dbt commands."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def require_environment(names: list[str]) -> dict[str, str]:
    """Report all missing variables together instead of failing one at a time."""
    missing = [name for name in names if not os.getenv(name, "").strip()]
    if missing:
        raise ValueError("Missing required settings: " + ", ".join(missing))
    return {"configured": str(len(names))}


def run_command(
    command: list[str],
    cwd: str | Path,
    env: dict[str, str] | None = None,
) -> dict[str, str | int]:
    """Run one command and include useful output when it fails.

    A shell is intentionally not used. Each list item is passed as one argument,
    so credentials and user-provided paths cannot be interpreted as shell code.
    """
    result = subprocess.run(
        command,
        cwd=str(cwd),
        check=False,
        text=True,
        capture_output=True,
        env=env,
    )
    if result.returncode:
        raise RuntimeError(
            f"Command failed ({result.returncode}): {' '.join(command)}\n"
            f"{result.stdout}\n{result.stderr}"
        )

    # XCom should remain small, so only the useful end of stdout is returned.
    return {"returncode": result.returncode, "stdout": result.stdout[-4000:]}
