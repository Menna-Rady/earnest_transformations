# Deployment notes

The included Compose environment is intended for development and demonstrations.
Production should use a managed Airflow deployment or independently managed
webserver, scheduler, metadata database, and secret backend.

- Store Kafka, Snowflake, and Azure credentials in the platform secret backend.
- Keep Airflow workers close to Kafka, ADLS, and Snowflake network endpoints.
- Persist Spark checkpoints and the Iceberg warehouse in ADLS.
- Run one active pipeline instance to avoid duplicate fixture publication.
- Configure task alerts and retain Airflow/Spark logs centrally.
- Deploy FastAPI, DuckDB, and Superset independently, then configure their health
  endpoints in Airflow.
