"""
rater.py — Rate a single job posting against the candidate's CV via OpenRouter.

Sends a chat-completion request to OpenRouter with a structured system prompt
and a user prompt containing the CV and job details.  Parses the JSON response
defensively and returns a score dict.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict

import httpx

from config import OPENROUTER_API_KEY, OPENROUTER_MODEL

logger = logging.getLogger(__name__)

OR_URL = "https://openrouter.ai/api/v1/chat/completions"

SYSTEM_PROMPT = (
    "You are an expert recruitment screener specialising in KYC, AML, and "
    "financial-crime compliance roles. You assess how well ONE job posting fits "
    "a specific candidate, based only on the CV and job text provided. Be "
    "calibrated and sceptical: most jobs are average fits. Reserve scores above "
    "85 for genuinely strong matches where seniority, domain, and core skills "
    "clearly align. Penalise seniority mismatch (e.g. a senior role for a junior "
    "CV, or vice-versa) and missing must-have requirements. Output a single "
    "strict JSON object and nothing else — no markdown, no code fences, no "
    "commentary."
)

USER_PROMPT_TEMPLATE = """CANDIDATE CV:
\"\"\"
{cv_text}
\"\"\"

JOB POSTING:
Title: {title}
Company: {company}
Location: {location}
Description:
\"\"\"
{description}
\"\"\"

Score this job for THIS candidate. Return JSON with these keys only:
{{
  "score": <integer 0-100>,
  "verdict": "<one of: strong, possible, weak>",
  "reason": "<max 2 sentences explaining the score>",
  "key_matches": ["<3-5 concrete overlaps between CV and job>"],
  "gaps": ["<1-3 requirements the candidate may not meet>"],
  "seniority_fit": "<one of: under, match, over>"
}}
Return only the JSON object."""


def _parse_response(raw: str) -> Dict[str, Any]:
    """Parse the LLM response as JSON, stripping markdown fences if present."""
    # Strip ```json ... ``` fences
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return json.loads(cleaned)


def rate_job(cv_text: str, job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Rate *job* against *cv_text* using OpenRouter.

    Returns a dict with keys: score, verdict, reason, key_matches, gaps,
    seniority_fit.  On any failure, returns score=0 with reason="rating failed".
    """
    user_prompt = USER_PROMPT_TEMPLATE.format(
        cv_text=cv_text,
        title=job["title"],
        company=job["company"],
        location=job["location"],
        description=job["description"],
    )

    payload: Dict[str, Any] = {
        "model": OPENROUTER_MODEL,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    }

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/kyc-job-finder",
        "X-Title": "kyc-job-finder",
    }

    for attempt in (1, 2):
        try:
            with httpx.Client(timeout=60) as client:
                resp = client.post(OR_URL, headers=headers, json=payload)
                resp.raise_for_status()
                body = resp.json()
                content: str = body["choices"][0]["message"]["content"]
                result = _parse_response(content)
                # Ensure required keys exist
                result.setdefault("score", 0)
                result.setdefault("verdict", "weak")
                result.setdefault("reason", "")
                result.setdefault("key_matches", [])
                result.setdefault("gaps", [])
                result.setdefault("seniority_fit", "match")
                logger.info(
                    "Rated '%s' at %s → score %d",
                    job["title"],
                    job["company"],
                    result["score"],
                )
                return result
        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning(
                "Parse failure for '%s' (attempt %d): %s",
                job["title"],
                attempt,
                exc,
            )
            if attempt == 2:
                logger.error("Giving up on '%s' after 2 attempts", job["title"])
        except httpx.HTTPError as exc:
            logger.error("HTTP error rating '%s': %s", job["title"], exc)
            break
        except Exception:
            logger.exception("Unexpected error rating '%s'", job["title"])
            break

    return {
        "score": 0,
        "verdict": "weak",
        "reason": "rating failed",
        "key_matches": [],
        "gaps": [],
        "seniority_fit": "match",
    }