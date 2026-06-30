"""Small Airflow tasks used by the pipeline DAG.

Keeping task implementation here leaves the DAG file responsible only for
schedule, parameters, and dependency order.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from airflow.decorators import task
from airflow.operators.python import get_current_context

from .commands import run_command
from .contracts import validate_csv
from .health_checks import (
    adls_health,
    duckdb_health,
    kafka_health,
    optional_http_health,
    snowflake_health,
)
from .producer import publish_files
from .settings import integration_environment, validate_integration_settings

PROJECT_ROOT = Path(os.getenv("EARNEST_PROJECT_ROOT", "/opt/earnest"))


def run_configuration() -> tuple[list[str], bool, bool]:
    """Read manual-run parameters from the current Airflow task context."""
    params = get_current_context()["params"]
    inputs = [str(PROJECT_ROOT / value) for value in params["input_files"]]
    return inputs, bool(params["validation_only"]), bool(params["skip_llm"])


@task
def preflight():
    """Step 1: fail early when required integration settings are missing."""
    _, validation_only, _ = run_configuration()
    if validation_only:
        return {"mode": "validation_only"}
    return validate_integration_settings()


@task
def validate_inputs():
    """Step 2: protect Kafka and Spark from malformed source files."""
    inputs, _, _ = run_configuration()
    return [validate_csv(path) for path in inputs]


@task
def publish_to_kafka():
    """Step 3: encode validated rows as Avro and publish them to Kafka."""
    inputs, validation_only, _ = run_configuration()
    return {"status": "skipped"} if validation_only else publish_files(inputs)


@task
def run_spark():
    """Step 4: consume Kafka until idle and write Iceberg/Snowflake outputs."""
    _, validation_only, skip_llm = run_configuration()
    if validation_only:
        return {"status": "skipped"}

    command = [
        sys.executable, "main.py", "--mode", "streaming",
        "--idle-timeout-minutes", "10",
    ]
    if skip_llm:
        command.append("--skip-llm")
    return run_command(
        command,
        PROJECT_ROOT / "spark",
        env=integration_environment(),
    )


@task
def build_dbt():
    """Step 5: compile, build, and test the analytical Snowflake models."""
    _, validation_only, _ = run_configuration()
    if validation_only:
        return {"status": "skipped"}

    environment = integration_environment()
    run_command(
        ["dbt", "parse", "--profiles-dir", "."],
        PROJECT_ROOT,
        env=environment,
    )
    return run_command(
        ["dbt", "build", "--profiles-dir", "."],
        PROJECT_ROOT,
        env=environment,
    )


@task
def integration_health():
    """Step 6: prove all configured storage and serving boundaries are reachable."""
    _, validation_only, _ = run_configuration()
    if validation_only:
        return {"status": "skipped"}

    report = {}
    report.update(kafka_health())
    report.update(adls_health())
    report.update(snowflake_health())
    report.update(duckdb_health())
    report.update(optional_http_health("FASTAPI_HEALTH_URL"))
    report.update(optional_http_health("SUPERSET_HEALTH_URL"))
    return report
