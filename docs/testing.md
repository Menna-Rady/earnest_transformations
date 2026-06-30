# Testing strategy

The repository separates fast offline checks from integration tests that need
infrastructure or third-party websites.

## Offline quality gates

| Gate | Coverage |
|---|---|
| `pytest -q python_tests` | Contracts, relationships, all 39 scraper samples, DAG structure, Compose structure, dashboard startup, and regressions |
| `pytest -q spark/tests` | Local PySpark transformation behavior with external LLM calls disabled |
| `ruff check ...` | Maintained orchestration, Spark, dashboard, and test code |
| `python -m compileall ...` | Syntax for all Python pipeline and scraper entrypoints |
| `node --check` | Syntax for all JavaScript scraper entrypoints |
| `dbt parse` | dbt models, 276 tests, sources, semantic models, metrics, and macros |
| `actionlint` | GitHub Actions syntax, expressions, jobs, and step structure |
| `pip check` | Installed dependency compatibility |

## Credential-gated integration tests

These checks cannot be replaced by mocks and must run in the integration
owner's environment:

- `docker compose build` and Airflow DAG import inside the Linux image.
- Kafka authentication and Avro message delivery.
- ADLS authentication and Iceberg Bronze/Silver writes.
- Snowflake staging load plus `dbt build` and all SQL data tests.
- Dashboard queries against populated Snowflake marts.
- FastAPI, DuckDB, and Superset health endpoints.
- Live scraper requests, which must respect each site's terms, robots policy,
  throttling, and anti-bot controls.

Start with `validation_only=true` in Airflow. Enable one integration boundary at
a time and preserve the Airflow/Spark logs when handing failures to another
owner.
