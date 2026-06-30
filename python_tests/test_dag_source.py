import ast
from pathlib import Path


def test_dag_declares_expected_task_boundaries():
    path = Path(__file__).parents[1] / "orchestration/airflow_tasks.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    functions = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert {
        "preflight", "validate_inputs", "publish_to_kafka", "run_spark",
        "build_dbt", "integration_health",
    } <= functions


def test_dag_uses_cairo_daily_schedule():
    source = (
        Path(__file__).parents[1] / "airflow/dags/earnest_pipeline.py"
    ).read_text(encoding="utf-8")
    assert 'schedule="0 2 * * *"' in source
    assert 'pendulum.timezone("Africa/Cairo")' in source
    assert "catchup=False" in source


def test_dag_file_only_builds_the_workflow_graph():
    source = (
        Path(__file__).parents[1] / "airflow/dags/earnest_pipeline.py"
    ).read_text(encoding="utf-8")
    assert "ready >> checked >> published >> transformed >> modeled >> healthy" in source
    assert "subprocess" not in source
    assert "snowflake.connector" not in source
