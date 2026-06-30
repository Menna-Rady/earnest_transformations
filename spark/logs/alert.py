"""Optional failure notifications. Missing webhook configuration is harmless."""

from __future__ import annotations

import os

import requests

from .logger import get_logger

logger = get_logger(__name__)


def broadcast_alert(step_name: str, error_message: str) -> None:
    """Send a concise Discord alert when a webhook has been configured."""
    webhook = os.getenv("DISCORD_WEBHOOK_URL", "").strip()
    if not webhook:
        logger.info("Alert skipped because DISCORD_WEBHOOK_URL is not configured")
        return

    response = requests.post(
        webhook,
        json={"content": f"Pipeline failure in {step_name}: {error_message}"},
        timeout=10,
    )
    response.raise_for_status()
