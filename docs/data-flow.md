# Data flow

```text
CSV fixtures
  -> canonical schema validation
  -> Avro encoding
  -> external Kafka topic
  -> Spark Structured Streaming
       -> ADLS Iceberg Bronze (raw records)
       -> ADLS Iceberg Silver (normalized records)
       -> Snowflake STG_ALL_SELLERS_PRODUCTS
  -> dbt dimensions, fact table, tests, and metrics
  -> dashboard and external serving connection checks
```

Airflow owns scheduling and task state. Kafka owns buffering, Spark owns record
transformation, Iceberg owns lake history, Snowflake remains the authoritative
analytics warehouse, and dbt owns analytical business logic.
