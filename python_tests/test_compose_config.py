"""Offline structural validation for the Docker Compose Airflow stack."""

from pathlib import Path

import yaml


ROOT = Path(__file__).parents[1]


def compose_config():
    return yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))


def test_compose_declares_required_airflow_services():
    services = compose_config()["services"]
    assert {"postgres", "airflow-init", "airflow-webserver", "airflow-scheduler"} <= set(services)


def test_compose_dependencies_and_named_volumes_are_valid():
    config = compose_config()
    services = config["services"]
    volumes = set(config.get("volumes", {}))
    assert services["airflow-webserver"]["depends_on"]["postgres"]["condition"] == "service_healthy"
    assert {"airflow-db", "airflow-logs"} <= volumes


def test_compose_build_paths_exist():
    common = compose_config()["x-airflow-common"]
    dockerfile = ROOT / common["build"]["dockerfile"]
    assert dockerfile.is_file()
    assert (ROOT / "airflow/requirements.txt").is_file()


def test_compose_uses_local_executor_and_disables_examples():
    environment = compose_config()["x-airflow-common"]["environment"]
    assert environment["AIRFLOW__CORE__EXECUTOR"] == "LocalExecutor"
    assert environment["AIRFLOW__CORE__LOAD_EXAMPLES"] == "false"
