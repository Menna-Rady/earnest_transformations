"""Daily orchestration for CSV -> Kafka -> Spark -> Snowflake -> dbt."""

from __future__ import annotations

from datetime import datetime, timedelta

import pendulum
from airflow.decorators import dag

from orchestration.airflow_tasks import (
    build_dbt,
    integration_health,
    preflight,
    publish_to_kafka,
    run_spark,
    validate_inputs,
)

DEFAULT_INPUTS = ["spark/Data/cleaned_products.csv"]


@dag(
    dag_id="earnest_daily_pipeline",
    description="Validate, publish, transform, model, test, and check serving boundaries.",
    start_date=datetime(2026, 1, 1, tzinfo=pendulum.timezone("Africa/Cairo")),
    schedule="0 2 * * *",
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=5)},
    params={
        "input_files": DEFAULT_INPUTS,
        "validation_only": False,
        "skip_llm": True,
    },
    tags=["earnest", "data-platform"],
)
def earnest_daily_pipeline():
    # Each function creates one visible Airflow task. The variable names make
    # the graph readable without hiding the execution order in helper code.
    ready = preflight()
    checked = validate_inputs()
    published = publish_to_kafka()
    transformed = run_spark()
    modeled = build_dbt()
    healthy = integration_health()

    # Workflow: configuration -> input -> transport -> processing -> modeling -> checks.
    ready >> checked >> published >> transformed >> modeled >> healthy


earnest_daily_pipeline()
