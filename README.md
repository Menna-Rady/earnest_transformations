<div align="center">

# Earnest Data Platform

**A testable, end-to-end e-commerce data pipeline for collection, enrichment, analytics, and decision intelligence.**

---

[![dbt CI](https://github.com/Menna-Rady/earnest_transformations/actions/workflows/dbt-ci.yml/badge.svg)](https://github.com/Menna-Rady/earnest_transformations/actions/workflows/dbt-ci.yml)
![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![Apache Spark 4.0](https://img.shields.io/badge/Apache%20Spark-4.0-E25A1C?logo=apachespark&logoColor=white)
![Apache Airflow 2.10](https://img.shields.io/badge/Apache%20Airflow-2.10-017CEE?logo=apacheairflow&logoColor=white)
![dbt Snowflake](https://img.shields.io/badge/dbt-Snowflake-FF694B?logo=dbt&logoColor=white)

</div>

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Repository Structure](#repository-structure)
- [Pipeline Workflow](#pipeline-workflow)
- [Data Model](#data-model)
- [Getting Started](#getting-started)
- [Integration Boundaries](#integration-boundaries)
- [Security & Contribution](#security--contribution)

---

## Overview

Earnest collects Egyptian retail product data, validates a shared record contract, enriches it with PySpark, and builds a tested analytical star schema in Snowflake. Airflow coordinates the end-to-end workflow while ADLS/Iceberg provides Bronze and Silver lakehouse storage.

The repository intentionally keeps externally managed components behind clear connection boundaries. Kafka and ADLS are configured but not provisioned here; FastAPI, DuckDB, Superset, NiFi, n8n, and vision processing can be connected as their owning teams deliver them.

---

## Architecture

```
Retail APIs / curated CSV fixtures
                 |
                 v
      Validation + Avro contract
                 |
                 v
         External Kafka topic
                 |
                 v
      Spark Structured Streaming
          /                 \
         v                   v
ADLS Iceberg Bronze/Silver   Snowflake staging
                                  |
                                  v
                     dbt facts, dimensions,
                       tests, and metrics
                                  |
                                  v
                    Dashboard / serving APIs

Airflow schedules, retries, observes, and reports every stage.
```

Detailed architecture documents:
- [Architecture Overview](docs/architecture.md)
- [Data Flow](docs/data-flow.md)
- [Airflow Orchestration](docs/orchestration.md)
- [Testing Guide](docs/testing.md)

---

## Repository Structure

| Path | Responsibility |
|---|---|
| `scraping/` | Independent Python and JavaScript retail scrapers with curated samples |
| `spark/` | Batch/streaming ingestion, cleaning, enrichment, Iceberg, and Snowflake loading |
| `models/`, `macros/`, `tests/` | dbt star schema, semantic metrics, and data-quality assertions |
| `airflow/` | Docker image and the readable daily/manual DAG |
| `orchestration/` | Contracts, Airflow tasks, Kafka publishing, commands, and health checks |
| `dashboard/` | Dash/Plotly analytical application |
| `python_tests/` | Fast unit, contract, DAG-structure, and regression tests |
| `docs/` | Product documentation, brand guidelines, and project management artifacts |

---

## Pipeline Workflow

The `earnest_daily_pipeline` DAG runs daily at **02:00 Cairo time** and can also be triggered manually:

1. **Validate** — Integration configuration and input CSV files against the canonical product schema
2. **Serialize** — Records as Avro and publish them to Kafka
3. **Enrich** — Run bounded Spark streaming with optional LLM enrichment
4. **Model** — Build and test Snowflake models with dbt
5. **Monitor** — Check Kafka, ADLS, Snowflake, DuckDB, FastAPI, and Superset boundaries

> Use `validation_only=true` to test files and DAG behavior without contacting external systems.

---

## Data Model

The analytical layer follows a **star schema**:

| Table | Description |
|---|---|
| `fact_product` | One observation per product, seller, date, and time |
| `dim_product` | Latest attributes for each canonical product URL |
| `dim_seller` | One row per seller/platform |
| `dim_date` | Calendar, weekend, holiday, and season attributes |
| `dim_time` | Clock and part-of-day attributes |

Relationship, uniqueness, accepted-range, discount-consistency, and temporal tests protect the model. MetricFlow definitions provide consistent product, price, stock, and discount metrics.

---

## Getting Started

### Prerequisites

- **Python 3.11**
- **Java 17**
- **Node.js 20+** — for JavaScript scrapers
- **Docker Desktop** — for the Airflow development stack
- **Access credentials** — only when running live integrations

### Quick Start

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
pytest -q python_tests
```

### Running Spark Tests

```powershell
python -m pip install pytest pyspark==4.0.0 python-dotenv requests groq
$env:PYTHONPATH = "spark"
$env:PYSPARK_PYTHON = (Resolve-Path ".venv\Scripts\python.exe").Path
$env:PYSPARK_DRIVER_PYTHON = $env:PYSPARK_PYTHON
pytest -q spark/tests
```

### dbt Validation

```powershell
python -m pip install dbt-core dbt-snowflake
dbt parse --profiles-dir .
dbt build --profiles-dir .
```

> `dbt build` requires a configured Snowflake account. Parsing and unit/contract tests should remain credential-independent.

### Airflow

Copy `.env.example` to `.env`, supply integration values, then follow the [setup guide](docs/setup.md). Never commit `.env` or credentials.

---

## Integration Boundaries

| Component | Repository Responsibility |
|---|---|
| **Kafka** | Avro producer/consumer contract and health check |
| **ADLS / Iceberg** | Spark catalog configuration, Bronze/Silver writes, health check |
| **Snowflake** | Staging load, dbt warehouse, dashboard source |
| **FastAPI / DuckDB / Superset** | Optional connection and health-check hooks |
| **NiFi / n8n / Vision Agent** | Documented external ingestion boundaries |

The next integration owner should begin with [`docs/setup.md`](docs/setup.md) and run Airflow in validation-only mode before enabling live credentials.

---

## Security & Contribution

- **Secrets** — Store in Airflow Connections, a secret backend, or local `.env` files
- **Never commit** — Virtual environments, generated scraper exports, Spark caches, or browser profiles
- **Quality gates** — Run the relevant Python, Spark, and dbt checks before opening a pull request
- **Code style** — Keep task functions small and comments focused on intent and non-obvious decisions
- **Guidelines** — Follow [CONTRIBUTING.md](CONTRIBUTING.md) for branch and commit conventions
