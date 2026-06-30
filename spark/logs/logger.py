"""Small, dependency-free logging configuration used by every Spark module."""

from __future__ import annotations

import logging
import os
from pathlib import Path


def get_logger(name: str = "EarnestPipeline") -> logging.Logger:
    """Return a configured logger without adding duplicate handlers."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

    log_path = os.getenv("LOG_PATH", "").strip()
    if log_path:
        path = Path(log_path)
        path.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(path / "pipeline.log", encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    logger.propagate = False
    return logger
