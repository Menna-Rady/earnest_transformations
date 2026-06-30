from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_fact_model_has_no_trailing_select_comma():
    sql = (ROOT / "models/marts/fact_product.sql").read_text(encoding="utf-8")
    assert "product_measuring_unit,\n" not in sql


def test_date_dimension_deduplicates_by_date():
    sql = (ROOT / "models/marts/dim_date.sql").read_text(encoding="utf-8")
    assert "PARTITION BY date_id" in sql
    assert "PARTITION BY time_id" not in sql


def test_dashboard_contains_no_literal_password():
    source = (ROOT / "dashboard/app.py").read_text(encoding="utf-8")
    assert '"password": os.getenv("SNOWFLAKE_PASSWORD"' in source
