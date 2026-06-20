"""
config.py — Load and validate environment variables for kyc-job-finder.

Loads all configuration from environment variables (or a .env file via python-dotenv),
validates that required keys are present, and exposes them as module-level constants.
"""

from __future__ import annotations

import os
import sys
from typing import List

from dotenv import load_dotenv

# Load .env if present (local development); in CI, secrets are set directly.
load_dotenv()

_REQUIRED_KEYS: List[str] = [
    "ADZUNA_APP_ID",
    "ADZUNA_APP_KEY",
    "OPENROUTER_API_KEY",
]


def _validate() -> None:
    """Check that all required environment variables are set; exit with a clear message if not."""
    missing = [k for k in _REQUIRED_KEYS if not os.getenv(k)]
    if missing:
        print(
            f"ERROR: Missing required environment variable(s): {', '.join(missing)}. "
            "Sign up for a free Adzuna API key at https://developer.adzuna.com/signup",
            file=sys.stderr,
        )
        sys.exit(1)


_validate()

# --- API keys ---
ADZUNA_APP_ID: str = os.environ["ADZUNA_APP_ID"]
ADZUNA_APP_KEY: str = os.environ["ADZUNA_APP_KEY"]
OPENROUTER_API_KEY: str = os.environ["OPENROUTER_API_KEY"]

# --- OpenRouter ---
OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL") or "deepseek/deepseek-v4-flash"

# --- SMTP (optional — if SMTP_PASS is not set, results print to console) ---
# For ProtonMail: SMTP_HOST=smtp.protonmail.ch, SMTP_PORT=587
# For Gmail:      SMTP_HOST=smtp.gmail.com,   SMTP_PORT=587
SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.protonmail.ch")
SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER: str = os.getenv("SMTP_USER", "")
SMTP_PASS: str = os.getenv("SMTP_PASS", "")
EMAIL_TO: str = os.getenv("EMAIL_TO", "")

# --- ntfy.sh push notifications (free, no account needed) ---
NTFY_TOPIC: str = os.getenv("NTFY_TOPIC", "")

# --- Search ---
SEARCH_QUERIES: List[str] = [
    q.strip()
    for q in (
        os.getenv("SEARCH_QUERIES")
        or "KYC analyst, AML analyst, financial crime analyst, customer due diligence, KYC onboarding"
    ).split(",")
    if q.strip()
]

LOCATION: str = os.getenv("LOCATION") or "United Kingdom"

# --- Scoring ---
MIN_SCORE: int = int(os.getenv("MIN_SCORE") or "70")
MAX_JOBS_PER_RUN: int = int(os.getenv("MAX_JOBS_PER_RUN") or "40")

# --- CV ---
CV_PATH: str = os.getenv("CV_PATH") or "cv.pdf"