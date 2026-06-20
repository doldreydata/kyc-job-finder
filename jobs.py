"""
jobs.py — Fetch KYC/AML job postings from the JSearch API (via RapidAPI).

For each search query in `SEARCH_QUERIES`, calls the JSearch endpoint,
normalises the results into a standard dict shape, and returns a merged,
within-run-deduplicated list.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List

import httpx

from config import JSEARCH_API_KEY, LOCATION, SEARCH_QUERIES

logger = logging.getLogger(__name__)

JSEARCH_URL = "https://jsearch.p.rapidapi.com/search"
HEADERS = {
    "x-rapidapi-key": JSEARCH_API_KEY,
    "x-rapidapi-host": "jsearch.p.rapidapi.com",
}
MAX_RETRIES = 3
RETRY_BACKOFF = 2  # seconds


def _normalise(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a raw JSearch result dict into our standard job dict."""
    description = raw.get("job_description") or ""
    return {
        "job_id": raw.get("job_id", ""),
        "title": raw.get("job_title", ""),
        "company": raw.get("employer_name", ""),
        "location": ", ".join(
            filter(
                None,
                [
                    raw.get("job_city"),
                    raw.get("job_state"),
                    raw.get("job_country"),
                ],
            )
        ),
        "description": description[:6000],  # truncate for LLM
        "apply_link": raw.get("job_apply_link", ""),
        "posted": raw.get("job_posted_at_datetime_utc", ""),
        "source": raw.get("job_publisher", ""),
    }


def _fetch_query(client: httpx.Client, query: str) -> List[Dict[str, Any]]:
    """Fetch jobs for a single search query, with retry/back-off on failure."""
    params: Dict[str, Any] = {
        "query": f"{query} in {LOCATION}",
        "page": 1,
        "num_pages": 1,
        "date_posted": "week",
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = client.get(JSEARCH_URL, headers=HEADERS, params=params)
            if resp.status_code == 429:
                wait = RETRY_BACKOFF * attempt
                logger.warning(
                    "Rate-limited on query '%s' (attempt %d/%d), waiting %ds…",
                    query,
                    attempt,
                    MAX_RETRIES,
                    wait,
                )
                time.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json()
            raw_jobs: List[Dict[str, Any]] = data.get("data", [])
            logger.info("Query '%s' returned %d job(s)", query, len(raw_jobs))
            return [_normalise(j) for j in raw_jobs]
        except httpx.HTTPError as exc:
            logger.error(
                "HTTP error on query '%s' (attempt %d/%d): %s",
                query,
                attempt,
                MAX_RETRIES,
                exc,
            )
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF * attempt)
            else:
                logger.exception("Exhausted retries for query '%s'", query)
        except Exception:
            logger.exception("Unexpected error on query '%s'", query)
            break

    return []


def fetch_all_jobs() -> List[Dict[str, Any]]:
    """
    Fetch jobs for every query in `SEARCH_QUERIES`, merge, and deduplicate
    by `job_id` within this run.

    Returns a list of unique job dicts.
    """
    all_jobs: List[Dict[str, Any]] = []
    seen_ids: set[str] = set()

    with httpx.Client(timeout=30) as client:
        for query in SEARCH_QUERIES:
            for job in _fetch_query(client, query):
                jid = job["job_id"]
                if jid and jid not in seen_ids:
                    seen_ids.add(jid)
                    all_jobs.append(job)

    logger.info("Total unique jobs fetched this run: %d", len(all_jobs))
    return all_jobs