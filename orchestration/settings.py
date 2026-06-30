"""Resolve integration settings from Airflow Connections or environment variables."""

from __future__ import annotations

import os


def airflow_connection(conn_id: str):
    """Return an Airflow Connection when running in Airflow, otherwise None."""
    try:
        from airflow.exceptions import AirflowNotFoundException
        from airflow.hooks.base import BaseHook
        return BaseHook.get_connection(conn_id)
    except ImportError:
        return None
    except AirflowNotFoundException:
        return None


def connection_config(conn_id: str, env_names: list[str]) -> dict[str, str]:
    """Combine a generic Airflow Connection with explicit environment values."""
    values = {name: os.getenv(name, "") for name in env_names}
    connection = airflow_connection(conn_id)
    if not connection:
        return values

    extras = connection.extra_dejson
    generic = {
        "host": connection.host or "",
        "port": str(connection.port or ""),
        "login": connection.login or "",
        "password": connection.password or "",
        "schema": connection.schema or "",
    }
    for name in env_names:
        values[name] = values[name] or str(extras.get(name, ""))
    values["_host"] = generic["host"]
    values["_port"] = generic["port"]
    values["_login"] = generic["login"]
    values["_password"] = generic["password"]
    values["_schema"] = generic["schema"]
    return values


def validate_integration_settings() -> dict[str, str]:
    """Check required connection boundaries without opening network connections."""
    kafka = connection_config("kafka_default", ["KAFKA_SERVER"])
    snowflake = connection_config("snowflake_default", [
        "SNOWFLAKE_ACCOUNT", "SNOWFLAKE_DATABASE", "SNOWFLAKE_SCHEMA",
        "SNOWFLAKE_WAREHOUSE",
    ])
    azure = connection_config("azure_data_lake_default", [
        "AZURE_STORAGE_ACCOUNT_NAME", "AZURE_STORAGE_ACCOUNT_KEY",
    ])
    missing = []
    if not (kafka["KAFKA_SERVER"] or kafka.get("_host")):
        missing.append("kafka_default/KAFKA_SERVER")
    if not (snowflake["SNOWFLAKE_ACCOUNT"] or snowflake.get("_host")):
        missing.append("snowflake_default/SNOWFLAKE_ACCOUNT")
    for name in ("SNOWFLAKE_DATABASE", "SNOWFLAKE_SCHEMA", "SNOWFLAKE_WAREHOUSE"):
        if not snowflake[name]:
            missing.append(name)
    if not (azure["AZURE_STORAGE_ACCOUNT_NAME"] or azure.get("_host")):
        missing.append("azure_data_lake_default/AZURE_STORAGE_ACCOUNT_NAME")
    if not (azure["AZURE_STORAGE_ACCOUNT_KEY"] or azure.get("_password")):
        missing.append("azure_data_lake_default/AZURE_STORAGE_ACCOUNT_KEY")
    if missing:
        raise ValueError("Missing integration settings: " + ", ".join(missing))
    return {"connections": "configured"}


def integration_environment() -> dict[str, str]:
    """Build subprocess environment values from Airflow Connections and `.env`."""
    environment = os.environ.copy()
    kafka = connection_config("kafka_default", ["KAFKA_SERVER"])
    snowflake = connection_config("snowflake_default", [
        "SNOWFLAKE_ACCOUNT", "SNOWFLAKE_DATABASE", "SNOWFLAKE_SCHEMA",
        "SNOWFLAKE_WAREHOUSE",
    ])
    azure = connection_config("azure_data_lake_default", [
        "AZURE_STORAGE_ACCOUNT_NAME", "AZURE_STORAGE_ACCOUNT_KEY",
    ])

    kafka_server = kafka["KAFKA_SERVER"] or kafka.get("_host", "")
    if kafka.get("_port") and ":" not in kafka_server:
        kafka_server = f"{kafka_server}:{kafka['_port']}"
    resolved = {
        "KAFKA_SERVER": kafka_server,
        "KAFKA_USERNAME": environment.get("KAFKA_USERNAME") or kafka.get("_login", ""),
        "KAFKA_PASSWORD": environment.get("KAFKA_PASSWORD") or kafka.get("_password", ""),
        "SNOWFLAKE_ACCOUNT": snowflake["SNOWFLAKE_ACCOUNT"] or snowflake.get("_host", ""),
        "SNOWFLAKE_URL": snowflake["SNOWFLAKE_ACCOUNT"] or snowflake.get("_host", ""),
        "SNOWFLAKE_USER": environment.get("SNOWFLAKE_USER") or snowflake.get("_login", ""),
        "SNOWFLAKE_PASSWORD": environment.get("SNOWFLAKE_PASSWORD") or snowflake.get("_password", ""),
        "SNOWFLAKE_DATABASE": snowflake["SNOWFLAKE_DATABASE"],
        "SNOWFLAKE_SCHEMA": snowflake["SNOWFLAKE_SCHEMA"] or snowflake.get("_schema", ""),
        "SNOWFLAKE_WAREHOUSE": snowflake["SNOWFLAKE_WAREHOUSE"],
        "AZURE_STORAGE_ACCOUNT_NAME": azure["AZURE_STORAGE_ACCOUNT_NAME"] or azure.get("_host", ""),
        "AZURE_STORAGE_ACCOUNT_KEY": azure["AZURE_STORAGE_ACCOUNT_KEY"] or azure.get("_password", ""),
    }
    environment.update({key: value for key, value in resolved.items() if value})
    return environment
