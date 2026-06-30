# Airflow orchestration

The `earnest_daily_pipeline` DAG connects the implemented repository to the
external platform boundaries in the architecture diagram.

## Task flow

1. Check integration configuration.
2. Validate CSV files against the canonical product contract.
3. Encode each product as Avro and publish it to Kafka.
4. Run bounded Spark Structured Streaming.
5. Write Bronze and Silver Iceberg tables to the configured ADLS warehouse and
   load the Snowflake staging table.
6. Run `dbt parse` and `dbt build`.
7. Check Kafka, ADLS, Snowflake, DuckDB, FastAPI, and Superset boundaries.

The DAG runs at 02:00 `Africa/Cairo`, does not backfill, and permits one active
run. Manual runs accept `input_files`, `validation_only`, and `skip_llm`.

## Code map

The orchestration files are intentionally small and separated by responsibility:

| File | Responsibility |
|---|---|
| `airflow/dags/earnest_pipeline.py` | Schedule, parameters, and task order only |
| `orchestration/airflow_tasks.py` | The six numbered Airflow task implementations |
| `orchestration/contracts.py` | Canonical CSV and Avro product schemas |
| `orchestration/producer.py` | Avro serialization and Kafka publication |
| `orchestration/settings.py` | Airflow Connection and environment resolution |
| `orchestration/commands.py` | Safe Spark and dbt subprocess execution |
| `orchestration/health_checks.py` | Read-only external service checks |

Start with the DAG file to understand execution order, then open only the module
for the step being changed.

## Connections

Connections can be supplied through `.env` or Airflow Admin > Connections.
Use these IDs for Airflow-managed values:

| Connection ID | Generic fields | Extra JSON keys |
|---|---|---|
| `kafka_default` | host, port, login, password | `KAFKA_SERVER` |
| `snowflake_default` | host/account, login, password, schema | `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_DATABASE`, `SNOWFLAKE_SCHEMA`, `SNOWFLAKE_WAREHOUSE` |
| `azure_data_lake_default` | host/account, password/key | `AZURE_STORAGE_ACCOUNT_NAME`, `AZURE_STORAGE_ACCOUNT_KEY` |

NiFi, n8n, the vision agent, FastAPI, DuckDB, and Superset remain external
components. This repository defines their boundaries and health checks; it does
not provision them.
