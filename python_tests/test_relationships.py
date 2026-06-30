"""Cross-module relationship tests that catch broken names and file moves."""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

from orchestration.contracts import PRODUCT_FIELDS


ROOT = Path(__file__).parents[1]


def test_dbt_refs_point_to_existing_models():
    model_names = {path.stem for path in (ROOT / "models").rglob("*.sql")}
    referenced = set()
    for path in [*ROOT.glob("models/**/*.sql"), *ROOT.glob("tests/*.sql")]:
        referenced.update(re.findall(r"ref\(['\"]([^'\"]+)", path.read_text(encoding="utf-8")))
    assert referenced <= model_names, f"Missing dbt models: {sorted(referenced - model_names)}"


def test_dbt_sources_use_the_declared_source_and_table():
    sources = (ROOT / "models/staging/sources.yml").read_text(encoding="utf-8")
    assert "- name: raw_data" in sources
    assert "- name: STG_ALL_SELLERS_PRODUCTS" in sources
    for path in (ROOT / "models").rglob("*.sql"):
        for source, table in re.findall(
            r"source\(['\"]([^'\"]+)['\"],\s*['\"]([^'\"]+)",
            path.read_text(encoding="utf-8"),
        ):
            assert source == "raw_data"
            assert table == "STG_ALL_SELLERS_PRODUCTS"


def test_airflow_dag_imports_real_task_functions():
    dag_tree = ast.parse(
        (ROOT / "airflow/dags/earnest_pipeline.py").read_text(encoding="utf-8")
    )
    task_tree = ast.parse(
        (ROOT / "orchestration/airflow_tasks.py").read_text(encoding="utf-8")
    )
    imported = {
        alias.name
        for node in ast.walk(dag_tree)
        if isinstance(node, ast.ImportFrom)
        and node.module == "orchestration.airflow_tasks"
        for alias in node.names
    }
    implemented = {
        node.name for node in ast.walk(task_tree) if isinstance(node, ast.FunctionDef)
    }
    assert imported <= implemented


def test_kafka_producer_and_spark_consumer_share_avro_fields():
    namespace = {}
    avro_path = ROOT / "spark/jobs/avro_schema.py"
    exec(compile(avro_path.read_text(encoding="utf-8"), str(avro_path), "exec"), namespace)
    spark_schema = json.loads(namespace["STREAMING_AVRO_SCHEMA_JSON"])
    spark_fields = [field["name"] for field in spark_schema["fields"]]
    assert spark_fields == PRODUCT_FIELDS


def test_registered_seller_inputs_exist():
    config_source = (ROOT / "spark/config/pipeline_config.py").read_text(encoding="utf-8")
    filenames = re.findall(r'_DATA_DIR,\s*"([^"]+\.csv)"', config_source)
    missing = [name for name in filenames if not (ROOT / "spark/Data" / name).is_file()]
    assert not missing, f"Missing configured seller CSV files: {missing}"


def test_root_readme_links_point_to_existing_files():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    targets = re.findall(r"\[[^\]]+\]\(([^)]+)\)", readme)
    local_targets = [
        target.split("#", 1)[0]
        for target in targets
        if not target.startswith(("http://", "https://", "#"))
    ]
    missing = [target for target in local_targets if not (ROOT / target).exists()]
    assert not missing, f"README links to missing files: {missing}"
