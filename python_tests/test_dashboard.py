"""Dashboard smoke tests that do not require a live Snowflake account."""

from __future__ import annotations

import importlib


def test_dashboard_builds_layout_without_credentials(monkeypatch):
    for name in (
        "SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_PASSWORD",
        "SNOWFLAKE_WAREHOUSE", "SNOWFLAKE_DATABASE", "SNOWFLAKE_SCHEMA",
    ):
        monkeypatch.delenv(name, raising=False)

    module = importlib.import_module("dashboard.app")
    assert module.app.layout is not None
    assert len(module.app.callback_map) >= 1
    assert module.DATA.products.empty
