"""
jobs.py — Fetch KYC/AML job postings from the Adzuna API (free tier).

For each search query in `SEARCH_QUERIES`, calls the Adzuna search endpoint,
normalises the results into a standard dict shape, and returns a merged,
within-run-deduplicated list.

Adzuna free tier: 1,000 API calls/month — enough for daily runs.
Sign up at https://developer.adzuna.com/signup
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List

import httpx

from config import ADZUNA_APP_ID, ADZUNA_APP_KEY, LOCATION, SEARCH_QUERIES

logger = logging.getLogger(__name__)

ADZUNA_URL = "https://api.adzuna.com/v1/api/jobs/gb/search/1"
MAX_RETRIES = 3
RETRY_BACKOFF = 2  # seconds


def _normalise(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a raw Adzuna result dict into our standard job dict."""
    description = raw.get("description") or ""
    company = raw.get("company") or {}
    location = raw.get("location") or {}
    return {
        "job_id": raw.get("id", ""),
        "title": raw.get("title", ""),
        "company": company.get("display_name", ""),
        "location": location.get("display_name", ""),
        "description": description[:6000],  # truncate for LLM
        "apply_link": raw.get("redirect_url", ""),
        "posted": raw.get("created", ""),
        "source": "Adzuna",
    }


def _fetch_query(client: httpx.Client, query: str) -> List[Dict[str, Any]]:
    """Fetch jobs for a single search query, with retry/back-off on failure."""
    params: Dict[str, Any] = {
        "app_id": ADZUNA_APP_ID,
        "app_key": ADZUNA_APP_KEY,
        "what": query,
        "results_per_page": 50,
        "sort_by": "date",
        "content-type": "application/json",
        "max_days_old": 14,
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = client.get(ADZUNA_URL, params=params, timeout=30)
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
            raw_jobs: List[Dict[str, Any]] = data.get("results", [])
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