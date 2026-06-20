"""
main.py — Orchestration entry point for kyc-job-finder.

Runs once per day (triggered by GitHub Actions cron or manually):
  1. Load config + CV text.
  2. Fetch jobs from JSearch, deduplicate within the run.
  3. Drop already-seen jobs; cap at MAX_JOBS_PER_RUN.
  4. Rate each new job against the CV via OpenRouter.
  5. Keep jobs scoring >= MIN_SCORE, sort by score descending.
  6. Email matches; mark ALL newly-processed job_ids as seen.
  7. Log a one-line summary.
"""

from __future__ import annotations

import logging
import sys
from typing import Any, Dict, List

from config import MIN_SCORE, NTFY_TOPIC, SMTP_PASS
from cv import load_cv
from jobs import fetch_all_jobs
from mailer import send_matches
from notify import send_notification
from rater import rate_job
from store import is_seen, mark_seen

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("main")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _filter_new(jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return only jobs whose job_id has NOT been seen before."""
    new_jobs = [j for j in jobs if not is_seen(j["job_id"])]
    logger.info(
        "%d total, %d already seen, %d new",
        len(jobs),
        len(jobs) - len(new_jobs),
        len(new_jobs),
    )
    return new_jobs


def _rate_all(
    cv_text: str, jobs: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Rate every job in *jobs* against *cv_text*.

    Returns a list of ``{"job": ..., "rating": ...}`` dicts.  Individual
    failures are logged and skipped — they never crash the run.
    """
    rated: List[Dict[str, Any]] = []
    for job in jobs:
        try:
            rating = rate_job(cv_text, job)
            rated.append({"job": job, "rating": rating})
        except Exception:
            logger.exception("Skipping job '%s' due to rating error", job.get("title"))
    return rated


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    """Run the full fetch → dedupe → rate → email pipeline."""
    logger.info("=== KYC Job Finder run starting ===")

    # 1. Load CV
    try:
        cv_text = load_cv()
    except FileNotFoundError as exc:
        logger.error(str(exc))
        sys.exit(1)

    # 2. Fetch jobs
    all_jobs = fetch_all_jobs()
    fetched_count = len(all_jobs)

    # 3. Drop seen — rate ALL new jobs (no cap)
    new_jobs = _filter_new(all_jobs)
    logger.info("Rating %d new job(s) against your CV...", len(new_jobs))

    # 4. Rate ALL new jobs
    rated = _rate_all(cv_text, new_jobs)

    # 5. Filter by MIN_SCORE, sort descending
    matches = [r for r in rated if r["rating"]["score"] >= MIN_SCORE]
    matches.sort(key=lambda r: r["rating"]["score"], reverse=True)

    # 6. Output results (email if SMTP configured, otherwise print)
    if matches:
        if SMTP_PASS:
            send_matches(matches)
        else:
            _print_matches(matches)
        # Always try push notification if ntfy is configured
        send_notification(matches)
    else:
        logger.info("No jobs met the minimum score of %d", MIN_SCORE)

    # 7. Mark ALL new jobs as seen (regardless of score)
    processed_ids = [j["job_id"] for j in new_jobs]
    mark_seen(processed_ids)

    # 8. Summary
    logger.info(
        "=== Run complete: fetched %d, new %d, matched %d ===",
        fetched_count,
        len(new_jobs),
        len(matches),
    )


def _print_matches(matches: List[Dict[str, Any]]) -> None:
    """Print match results to the console in a readable format."""
    from datetime import date

    today = date.today().isoformat()
    print(f"\n{'='*60}")
    print(f"  🔍 KYC JOB FINDER — {len(matches)} MATCH(ES) — {today}")
    print(f"{'='*60}\n")
    for i, m in enumerate(matches, 1):
        job = m["job"]
        r = m["rating"]
        print(f"  {i}. [{r['score']}/100] {job['title']} — {job['company']}")
        print(f"     📍 {job['location']}  |  {job.get('source', '')}")
        print(f"     🏷️  {r['verdict'].upper()}  |  Seniority: {r['seniority_fit']}")
        print(f"     💬 {r['reason']}")
        print(f"     ✅ Matches: {', '.join(r.get('key_matches', []))}")
        if r.get("gaps"):
            print(f"     ⚠️  Gaps: {', '.join(r['gaps'])}")
        search_link = job.get("search_link", "")
        print(f"     🔍 Search: {search_link}")
        print(f"     🔗 Apply: {job['apply_link']}")
        print()


if __name__ == "__main__":
    main()