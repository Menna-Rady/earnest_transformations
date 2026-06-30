"""Input contracts shared by Airflow validation and the Kafka producer."""

from __future__ import annotations

import csv
from pathlib import Path


PRODUCT_FIELDS = [
    "title", "name", "product_current_price", "product_old_price",
    "product_discount", "product_url", "product_image_url",
    "product_seller", "product_availability", "product_category",
    "product_subcategory", "product_unit", "product_weight",
    "scraping_time", "timestamp_timezone", "product_brand",
    "product_ram", "product_storage",
]

PRODUCT_AVRO_SCHEMA = {
    "type": "record",
    "name": "ProductRecord",
    "fields": [
        {"name": field, "type": ["null", "string"], "default": None}
        for field in PRODUCT_FIELDS
    ],
}


def validate_csv(path: str | Path) -> dict[str, int | str]:
    """Validate one CSV and return a compact report for Airflow XCom."""
    csv_path = Path(path)
    if not csv_path.is_file():
        raise FileNotFoundError(f"Input CSV does not exist: {csv_path}")

    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = sorted(set(PRODUCT_FIELDS) - set(reader.fieldnames or []))
        if missing:
            raise ValueError(f"{csv_path.name} is missing columns: {', '.join(missing)}")

        rows = 0
        invalid = 0
        for row in reader:
            rows += 1
            if not row.get("product_url", "").strip() or not row.get(
                "product_current_price", ""
            ).strip():
                invalid += 1

    if rows == 0:
        raise ValueError(f"Input CSV is empty: {csv_path}")
    if invalid:
        raise ValueError(f"{csv_path.name} has {invalid} rows without URL or price")
    return {"path": str(csv_path), "rows": rows}


def read_products(path: str | Path):
    """Yield canonical string-or-null records from a validated CSV."""
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            yield {
                field: (row.get(field, "").strip() or None)
                for field in PRODUCT_FIELDS
            }
