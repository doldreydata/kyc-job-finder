"""
cv.py — Load a CV PDF and extract its plain text.

Reads the PDF at `CV_PATH` (from config), extracts all page text, collapses
excessive whitespace, and caches the result in a module-level variable so the
file is only parsed once per run.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from pypdf import PdfReader

from config import CV_PATH

logger = logging.getLogger(__name__)

_cv_text_cache: str | None = None


def load_cv() -> str:
    """
    Extract and return the full plain-text content of the CV PDF.

    The result is cached after the first call; subsequent calls return the
    cached string without re-reading the file.

    Raises
    ------
    FileNotFoundError
        If the CV PDF does not exist at `CV_PATH`.
    """
    global _cv_text_cache  # noqa: PLW0603
    if _cv_text_cache is not None:
        return _cv_text_cache

    cv_path = Path(CV_PATH)
    if not cv_path.exists():
        raise FileNotFoundError(
            f"CV file not found at {cv_path.resolve()}. "
            "Place your CV as 'cv.pdf' in the project root or set CV_PATH."
        )

    logger.info("Loading CV from %s", cv_path)
    reader = PdfReader(str(cv_path))
    pages: list[str] = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)

    raw = "\n".join(pages)
    # Collapse multiple whitespace runs into single spaces, trim.
    cleaned = re.sub(r"\s+", " ", raw).strip()
    _cv_text_cache = cleaned
    logger.info("CV loaded: %d characters", len(cleaned))
    return cleaned