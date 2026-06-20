"""
store.py — SQLite-backed deduplication store for seen job IDs.

Maintains a `seen.db` file with a single table `seen` that records every
job_id the application has already processed, so they are never re-rated
or re-emailed on subsequent runs.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import List

DB_PATH = Path("seen.db")

logger = logging.getLogger(__name__)


def _get_conn() -> sqlite3.Connection:
    """Return a connection to the SQLite database, creating the table if needed."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        "CREATE TABLE IF NOT EXISTS seen (job_id TEXT PRIMARY KEY, seen_at TEXT)"
    )
    conn.commit()
    return conn


def is_seen(job_id: str) -> bool:
    """Return True if *job_id* has already been processed."""
    conn = _get_conn()
    try:
        row = conn.execute("SELECT 1 FROM seen WHERE job_id = ?", (job_id,)).fetchone()
        return row is not None
    finally:
        conn.close()


def mark_seen(job_ids: List[str]) -> None:
    """Mark every job_id in *job_ids* as processed (INSERT OR IGNORE)."""
    if not job_ids:
        return
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_conn()
    try:
        conn.executemany(
            "INSERT OR IGNORE INTO seen (job_id, seen_at) VALUES (?, ?)",
            [(jid, now) for jid in job_ids],
        )
        conn.commit()
        logger.info("Marked %d job(s) as seen", len(job_ids))
    finally:
        conn.close()