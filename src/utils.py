import hashlib
import logging
import random
import re
import time

import requests

log = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0",
]

REQUEST_DELAY = 2.0  # seconds between requests
_last_request_time = 0.0


def rate_limit():
    """Enforce minimum delay between HTTP requests."""
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < REQUEST_DELAY:
        time.sleep(REQUEST_DELAY - elapsed)
    _last_request_time = time.time()


def fetch_url(url, max_retries=3):
    """Fetch a URL with rate limiting, retries, and UA rotation."""
    for attempt in range(max_retries):
        rate_limit()
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            wait = 2 ** (attempt + 1)
            log.warning(
                "Fetch %s attempt %d failed: %s — retrying in %ds", url, attempt + 1, e, wait
            )
            if attempt < max_retries - 1:
                time.sleep(wait)
            else:
                raise


def body_hash(text):
    """SHA-256 hash of page body for change detection."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# --------------- text cleaning ---------------

_MULTI_SPACE = re.compile(r"\s+")
_PARENS = re.compile(r"\s*\(.*?\)\s*")


def clean_text(s):
    """Normalize whitespace and strip a string."""
    if not s:
        return None
    return _MULTI_SPACE.sub(" ", s).strip() or None


def clean_name(s):
    """Clean a person name: strip parentheticals, titles, normalize."""
    if not s:
        return None
    s = _PARENS.sub(" ", s)
    s = clean_text(s)
    if not s:
        return None
    # Remove common trailing annotations
    for suffix in [" *", "*"]:
        s = s.rstrip(suffix).rstrip()
    return s


def clean_field(s):
    """Normalize field-of-study text; use semicolons to separate multiple."""
    if not s:
        return None
    s = clean_text(s)
    if not s:
        return None
    # Normalize separators to semicolons
    s = re.sub(r"\s*[,/&]\s*", "; ", s)
    return s


def classify_sector(text):
    """Classify a placement into academic/government/private/other."""
    if not text:
        return "other"
    low = text.lower()
    gov_kw = [
        "federal reserve",
        "fed ",
        "imf",
        "world bank",
        "treasury",
        "government",
        "bureau",
        "census",
        "congressional",
        "council of economic",
        "national bureau",
    ]
    if any(kw in low for kw in gov_kw):
        return "government"
    acad_kw = [
        "university",
        "college",
        "institute",
        "school of",
        "département",
        "department",
        "faculty",
        "professor",
        "postdoc",
        "post-doc",
    ]
    if any(kw in low for kw in acad_kw):
        return "academic"
    private_kw = [
        "consulting",
        "capital",
        "bank",
        "amazon",
        "google",
        "microsoft",
        "meta",
        "apple",
        "mckinsey",
        "deloitte",
        "goldman",
        "morgan stanley",
        "jpmorgan",
        "citadel",
        "uber",
        "airbnb",
        "netflix",
    ]
    if any(kw in low for kw in private_kw):
        return "private"
    return "other"


def detect_postdoc(institution, position):
    """Return True if the placement looks like a postdoc."""
    for text in [institution, position]:
        if text and re.search(r"post[\s-]?doc", text, re.IGNORECASE):
            return True
    return False


def parse_year(text):
    """Extract a 4-digit year from text. Returns int or None."""
    if not text:
        return None
    m = re.search(r"((?:19|20)\d{2})", str(text))
    return int(m.group(1)) if m else None
