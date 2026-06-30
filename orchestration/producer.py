"""Publish validated product fixtures as raw Avro messages to Kafka."""

from __future__ import annotations

import io
import os

from fastavro import schemaless_writer

from .contracts import PRODUCT_AVRO_SCHEMA, read_products
from .settings import connection_config


def _producer_config() -> dict[str, str]:
    connection = connection_config("kafka_default", ["KAFKA_SERVER"])
    server = (connection["KAFKA_SERVER"] or connection.get("_host", "")).strip()
    if connection.get("_port") and ":" not in server:
        server = f"{server}:{connection['_port']}"
    if not server:
        raise ValueError("KAFKA_SERVER is required")

    config = {"bootstrap.servers": server, "client.id": "earnest-airflow"}
    username = (os.getenv("KAFKA_USERNAME", "") or connection.get("_login", "")).strip()
    password = (os.getenv("KAFKA_PASSWORD", "") or connection.get("_password", "")).strip()
    if username and password:
        config.update({
            "security.protocol": os.getenv("KAFKA_SECURITY_PROTOCOL", "SASL_SSL"),
            "sasl.mechanisms": os.getenv("KAFKA_SASL_MECHANISMS", "PLAIN"),
            "sasl.username": username,
            "sasl.password": password,
        })
    return config


def publish_files(paths: list[str]) -> dict[str, int | str]:
    """Publish all records and fail if Kafka reports a delivery error."""
    from confluent_kafka import Producer

    topic = os.getenv("KAFKA_TOPIC", "products")
    producer = Producer(_producer_config())
    delivered = 0
    errors: list[str] = []

    def delivery_report(error, _message):
        nonlocal delivered
        if error:
            errors.append(str(error))
        else:
            delivered += 1

    for path in paths:
        for record in read_products(path):
            buffer = io.BytesIO()
            schemaless_writer(buffer, PRODUCT_AVRO_SCHEMA, record)
            seller = record.get("product_seller") or "unknown_seller"
            producer.produce(
                topic,
                key=seller.encode("utf-8"),
                value=buffer.getvalue(),
                callback=delivery_report,
            )
            producer.poll(0)

    producer.flush(30)
    if errors:
        raise RuntimeError("Kafka delivery failed: " + "; ".join(errors[:3]))
    return {"topic": topic, "published": delivered}
