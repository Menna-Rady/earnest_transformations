"""Offline contract checks for every scraper project."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRAPERS = ROOT / "scraping/scrapers"
SAMPLE_FIELDS = [
    "name", "price", "old_price", "discount", "category", "brand",
    "url", "image_url", "availability", "seller",
]


def scraper_folders():
    return sorted(path for path in SCRAPERS.iterdir() if path.is_dir())


def test_collection_contains_39_documented_scrapers():
    assert len(scraper_folders()) == 39


def test_every_scraper_has_one_entrypoint_readme_and_sample():
    failures = []
    for folder in scraper_folders():
        entrypoints = [
            path for path in (folder / "scraper.py", folder / "scraper.js")
            if path.is_file()
        ]
        if len(entrypoints) != 1:
            failures.append(f"{folder.name}: expected one scraper entrypoint")
        if not (folder / "README.md").is_file():
            failures.append(f"{folder.name}: missing README.md")
        if not (folder / "sample_data.csv").is_file():
            failures.append(f"{folder.name}: missing sample_data.csv")
    assert not failures, failures


def test_every_sample_has_ten_rows_and_the_standard_schema():
    failures = []
    for folder in scraper_folders():
        with (folder / "sample_data.csv").open(
            "r", encoding="utf-8-sig", newline=""
        ) as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
        if reader.fieldnames != SAMPLE_FIELDS:
            failures.append(f"{folder.name}: columns={reader.fieldnames}")
        if len(rows) != 10:
            failures.append(f"{folder.name}: rows={len(rows)}")
    assert not failures, failures
