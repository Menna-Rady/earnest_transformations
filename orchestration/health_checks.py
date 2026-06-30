"""Read-only checks for every external platform boundary."""

from __future__ import annotations

import os
import socket
import urllib.request

from .settings import connection_config


def kafka_health() -> dict[str, str]:
    """Check network reachability without publishing a message."""
    connection = connection_config("kafka_default", ["KAFKA_SERVER"])
    server = (connection["KAFKA_SERVER"] or connection.get("_host", "")).split(",", 1)[0]
    if connection.get("_port") and ":" not in server:
        server = f"{server}:{connection['_port']}"
    host, port = server.rsplit(":", 1)
    with socket.create_connection((host, int(port)), timeout=10):
        return {"kafka": "reachable"}


def adls_health() -> dict[str, str]:
    """Authenticate to ADLS and perform a read-only filesystem listing."""
    from azure.storage.filedatalake import DataLakeServiceClient

    configured = connection_config(
        "azure_data_lake_default",
        ["AZURE_STORAGE_ACCOUNT_NAME", "AZURE_STORAGE_ACCOUNT_KEY"],
    )
    account = configured["AZURE_STORAGE_ACCOUNT_NAME"] or configured.get("_host")
    credential = configured["AZURE_STORAGE_ACCOUNT_KEY"] or configured.get("_password")
    client = DataLakeServiceClient(
        account_url=f"https://{account}.dfs.core.windows.net",
        credential=credential,
    )
    next(iter(client.list_file_systems(results_per_page=1)), None)
    return {"adls": "healthy"}


def snowflake_health() -> dict[str, str]:
    """Authenticate to Snowflake and execute only `SELECT 1`."""
    import snowflake.connector

    configured = connection_config("snowflake_default", [
        "SNOWFLAKE_ACCOUNT", "SNOWFLAKE_DATABASE", "SNOWFLAKE_SCHEMA",
        "SNOWFLAKE_WAREHOUSE",
    ])
    account = (
        os.getenv("SNOWFLAKE_ACCOUNT")
        or configured.get("_host")
        or os.getenv("SNOWFLAKE_URL", "").replace(".snowflakecomputing.com", "")
    )
    connection = snowflake.connector.connect(
        account=account,
        user=os.getenv("SNOWFLAKE_USER") or configured.get("_login"),
        password=os.getenv("SNOWFLAKE_PASSWORD") or configured.get("_password"),
        warehouse=configured["SNOWFLAKE_WAREHOUSE"],
        database=configured["SNOWFLAKE_DATABASE"],
        schema=configured["SNOWFLAKE_SCHEMA"] or configured.get("_schema"),
    )
    try:
        connection.cursor().execute("SELECT 1").fetchone()
    finally:
        connection.close()
    return {"snowflake": "healthy"}


def duckdb_health() -> dict[str, str]:
    """Open the serving database only when a path has been configured."""
    path = os.getenv("DUCKDB_PATH", "").strip()
    if not path:
        return {"duckdb": "not_configured"}
    import duckdb

    connection = duckdb.connect(path)
    try:
        connection.execute("SELECT 1").fetchone()
    finally:
        connection.close()
    return {"duckdb": "healthy"}


def optional_http_health(env_name: str) -> dict[str, str]:
    """Check an optional API URL, or clearly report that it is not configured."""
    url = os.getenv(env_name, "").strip()
    if not url:
        return {env_name: "not_configured"}
    with urllib.request.urlopen(url, timeout=10) as response:
        if response.status >= 400:
            raise RuntimeError(f"{env_name} returned HTTP {response.status}")
    return {env_name: "healthy"}
