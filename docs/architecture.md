# Architecture

This document describes the end-to-end architecture of the Earnest data platform: from raw web scraping to the dbt-powered semantic layer.

## High-Level Data Flow
```
Scraping (scraping/)
        |
        v
Raw Data (CSV / landing zone)
        |
        v
Kafka (external high-throughput buffer)
        |
        v
Spark Processing (spark/)
        |
        v
ADLS / Iceberg (Bronze and Silver) + Snowflake staging
        |
        v
dbt Staging Layer (models/staging/)
        |
        v
dbt Marts Layer (models/marts/) - star schema
        |
        v
dbt Semantic Layer (MetricFlow) - metrics & semantic models
        |
        v
BI Tools / Dashboards / Future Website
```

## Components

### 1. Scraping (`scraping/`)
Collects raw e-commerce product listings (prices, availability, discounts) from Egyptian e-commerce platforms (Noon, Amazon Egypt, Talabat, and others).

- **Input:** target site URLs / product categories
- **Output:** raw CSV files (see `spark/Data/*.csv` for examples of expected shape)
- **Frequency:** _TODO: document scraping schedule (manual / cron / Airflow)_

### 2. Spark Processing (`spark/`)
Cleans, normalizes, and enriches raw scraped data before it lands in Snowflake.

- **Input:** raw CSVs produced by the scraper
- **Processing:** cleaning (`transformers/cleaner.py`), feature extraction (`transformers/feature_extractor.py`), date/time parsing (`transformers/date_time_extractor.py`), and LLM-assisted imputation (`transformers/llm_imputer.py`) for missing values
- **Output:** Bronze/Silver Iceberg tables in ADLS, Snowflake staging rows,
  and registry maps used for consistent dimension keys
- **Agents:** Pluggable LLM agent layer (`agents/`) with failover support (`FailoverManager.py`) across providers (Groq, Llama, GPT-OSS variants)

### 3. Snowflake (Data Warehouse)
Target warehouse for all transformed data.

- **Database:** `New_N`
- **Schema:** `NEW_DEV`
- **Source database:** `DEPI_DB.PUBLIC`
- _TODO: document raw vs. staging schema separation and warehouse sizing_

### 4. dbt Project (`models/`)
Transforms raw Snowflake tables into a dimensional model and semantic layer.

- **Staging (`models/staging/`):** normalizes column names and casts types
- **Marts (`models/marts/`):** star schema — `fact_product`, `dim_product`, `dim_seller`, `dim_date`, `dim_time`
- **Semantic (`models/marts/schema.yml` + `metricflow_time_spine.sql`):** MetricFlow semantic models, measures, and metrics (see [docs/semantic-layer.md](semantic-layer.md) for full detail)

### 5. Future Website / API Layer
A separate frontend repository is planned to consume this data, likely via the dbt Semantic Layer or a dedicated API.

- _TODO: link the website repo here once the integration contract is defined_
- _TODO: document whether the website queries Snowflake directly, via dbt Semantic Layer (MetricFlow), or via a dedicated API service_

### 6. Airflow (`airflow/`)

Airflow schedules the daily/manual workflow, validates contracts, publishes the
fixture stream, runs bounded Spark processing, executes dbt quality gates, and
checks serving connections. Kafka, ADLS, FastAPI, DuckDB, and Superset are
external connection boundaries rather than services provisioned here.

## Data Lineage

Within the dbt project, lineage can be visualized with:

```bash
dbt docs generate
dbt docs serve
```

This only covers lineage from dbt sources downward. Lineage from the scraper through Spark into Snowflake is **not yet documented or automated** — this is a known gap (see root README review).

## Open Architecture Questions (TODO)

- [ ] How/where does the scraper run on a schedule?
- [ ] How are Spark jobs triggered (manual, Airflow, cron)?
- [ ] What orchestrator (if any) coordinates scraper → Spark → dbt?
- [ ] How are credentials/secrets managed across the three domains?
- [ ] What does the website/API layer actually consume?



