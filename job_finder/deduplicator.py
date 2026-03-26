"""URL normalization, hashing, and duplicate detection against PG + Salesforce."""

import hashlib
import logging
from urllib.parse import urlparse, urlunparse, urlencode, parse_qsl

from job_finder import db

logger = logging.getLogger(__name__)

UTM_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"}


def normalize_url(url: str) -> str:
    """Strip UTM params, trailing slash, lowercase scheme+host."""
    parsed = urlparse(url.strip().rstrip("/"))
    clean_qs = urlencode([(k, v) for k, v in parse_qsl(parsed.query) if k not in UTM_PARAMS])
    return urlunparse(parsed._replace(
        scheme=parsed.scheme.lower(),
        netloc=parsed.netloc.lower(),
        query=clean_qs,
        fragment="",
    ))


def hash_url(url: str) -> str:
    """Return SHA-256 hex digest of the normalized URL."""
    return hashlib.sha256(normalize_url(url).encode("utf-8")).hexdigest()


def is_duplicate(conn, sf, url: str) -> bool:
    """
    Return True if this URL has already been processed.

    Check order:
    1. PostgreSQL url_hash lookup (fast)
    2. Salesforce SOQL fallback (catches records pushed before PG tracking existed)
    """
    url_hash = hash_url(url)

    # 1. PG check
    if db.url_hash_exists(conn, url_hash):
        logger.debug("Duplicate found in PG: %s", url_hash)
        return True

    # 2. SF fallback — use raw URL (SF stores whatever was pushed, may not be normalized)
    try:
        safe_url = url.replace("'", "\\'")
        result = sf.query(
            f"SELECT Id FROM JobApplication__c WHERE Job_Posting_URL__c = '{safe_url}' LIMIT 1"
        )
        if result["totalSize"] > 0:
            logger.debug("Duplicate found in SF: %s", url)
            return True
    except Exception as exc:
        logger.warning("SF duplicate check failed for %s: %s", url, exc)

    return False
