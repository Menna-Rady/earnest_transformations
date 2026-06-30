import csv

import pytest

from orchestration.contracts import PRODUCT_FIELDS, validate_csv


def write_fixture(path, rows, fields=PRODUCT_FIELDS):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def valid_row():
    row = {field: "" for field in PRODUCT_FIELDS}
    row.update({
        "title": "Example",
        "product_current_price": "100",
        "product_url": "https://example.test/product/1",
        "product_seller": "fixture",
    })
    return row


def test_validate_csv_accepts_canonical_contract(tmp_path):
    path = tmp_path / "products.csv"
    write_fixture(path, [valid_row()])
    assert validate_csv(path)["rows"] == 1


def test_validate_csv_reports_missing_columns(tmp_path):
    path = tmp_path / "products.csv"
    write_fixture(path, [{"product_url": "x"}], ["product_url"])
    with pytest.raises(ValueError, match="missing columns"):
        validate_csv(path)


def test_validate_csv_rejects_missing_business_keys(tmp_path):
    path = tmp_path / "products.csv"
    row = valid_row()
    row["product_url"] = ""
    write_fixture(path, [row])
    with pytest.raises(ValueError, match="without URL or price"):
        validate_csv(path)
