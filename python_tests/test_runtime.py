import sys

import pytest

from orchestration.commands import require_environment, run_command


def test_require_environment_lists_all_missing_values(monkeypatch):
    monkeypatch.delenv("ONE", raising=False)
    monkeypatch.delenv("TWO", raising=False)
    with pytest.raises(ValueError, match="ONE, TWO"):
        require_environment(["ONE", "TWO"])


def test_run_command_captures_success(tmp_path):
    result = run_command([sys.executable, "-c", "print('ok')"], tmp_path)
    assert result["returncode"] == 0
    assert "ok" in result["stdout"]


def test_run_command_raises_with_output(tmp_path):
    with pytest.raises(RuntimeError, match="expected failure"):
        run_command(
            [sys.executable, "-c", "raise SystemExit('expected failure')"],
            tmp_path,
        )
