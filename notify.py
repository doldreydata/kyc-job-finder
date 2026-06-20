"""
notify.py — Send push notifications to your phone via ntfy.sh (free, no account).

ntfy.sh is an open-source push notification service. You pick a unique topic
name, install the app on your phone, and subscribe to that topic. This module
sends job match summaries as push notifications.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

import httpx

from config import NTFY_TOPIC

logger = logging.getLogger(__name__)

NTFY_URL = "https://ntfy.sh"


def _build_message(matches: List[Dict[str, Any]]) -> str:
    """Build a compact notification message from the top matches."""
    lines: List[str] = []
    for i, m in enumerate(matches[:5], 1):  # max 5 in notification body
        job = m["job"]
        r = m["rating"]
        lines.append(
            f"{i}. [{r['score']}/100] {job['title']} — {job['company']}"
        )
        lines.append(f"   {r['reason']}")
        lines.append(f"   🔗 {job['apply_link']}")
        lines.append("")
    if len(matches) > 5:
        lines.append(f"... and {len(matches) - 5} more matches")
    return "\n".join(lines)


def send_notification(matches: List[Dict[str, Any]]) -> None:
    """
    Send a push notification via ntfy.sh with the top job matches.

    Does nothing if NTFY_TOPIC is not configured.
    """
    if not NTFY_TOPIC:
        logger.info("ntfy.sh not configured — skipping push notification.")
        return

    if not matches:
        return

    title = f"🔍 {len(matches)} new KYC match{'es' if len(matches) != 1 else ''}"
    body = _build_message(matches)

    # Click action: open the top match's apply link
    click_url = matches[0]["job"]["apply_link"]

    try:
        with httpx.Client(timeout=15) as client:
            resp = client.post(
                f"{NTFY_URL}/{NTFY_TOPIC}",
                data=body.encode("utf-8"),
                headers={
                    "Title": title,
                    "Priority": "default",
                    "Tags": "briefcase,memo",
                    "Click": click_url,
                },
            )
            resp.raise_for_status()
        logger.info("Push notification sent via ntfy.sh")
    except Exception:
        logger.exception("Failed to send ntfy.sh notification")