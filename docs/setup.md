# Local setup

1. Install Docker Desktop with Linux containers enabled.
2. Copy `.env.example` to `.env` and replace placeholders with integration
   credentials. Never commit `.env`.
3. Rotate the Snowflake credential that was previously committed.
4. Build and initialize Airflow:

```powershell
docker compose build
docker compose up airflow-init
docker compose up -d airflow-webserver airflow-scheduler
```

Open `http://localhost:8080` and sign in with the credentials configured in
`.env`. Run `earnest_daily_pipeline` first with `validation_only=true`; this
checks the input contract without contacting external services.

Run lightweight tests outside Docker with:

```powershell
python -m pip install -r requirements-dev.txt
pytest -q python_tests
```

Spark transformation tests run inside the Airflow image (which includes Java
and PySpark):

```powershell
docker compose run --rm airflow-scheduler pytest -q spark/tests
```

See [orchestration.md](orchestration.md) for connection fields and task flow.
