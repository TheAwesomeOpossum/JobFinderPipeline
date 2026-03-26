"""Google Search client via Serper.dev API."""

import logging
import requests

from job_finder import config
from job_finder.search.ats_sites import ATS_SITES, build_query

logger = logging.getLogger(__name__)

SERPER_ENDPOINT = "https://google.serper.dev/search"
MAX_RESULTS_PER_QUERY = 100
PAGE_SIZE = 10


def _tbs_for_days(days: int) -> str:
    """Convert a day count to a Serper/Google tbs date-restrict string."""
    if days <= 1:
        return "qdr:d"
    if days <= 7:
        return f"qdr:d{days}"
    weeks = days // 7
    return f"qdr:w{weeks}" if weeks > 1 else "qdr:w"


def search_one_site(domain: str, ats_type: str, keywords: str, max_results: int = 10, days: int = 1) -> list[dict]:
    """
    Query Serper for a single ATS domain.
    Returns a list of raw result dicts with url, title, snippet, ats_type.
    """
    results = []
    cap = min(max_results, MAX_RESULTS_PER_QUERY)
    query = build_query(domain, keywords)
    total_pages = (cap + PAGE_SIZE - 1) // PAGE_SIZE

    for page in range(1, total_pages + 1):
        payload = {
            "q":    query,
            "num":  PAGE_SIZE,
            "page": page,
            "tbs":  _tbs_for_days(days),
        }
        headers = {"X-API-KEY": config.SERPER_API_KEY, "Content-Type": "application/json"}
        try:
            resp = requests.post(SERPER_ENDPOINT, json=payload, headers=headers, timeout=15)
            if not resp.ok:
                logger.warning("Serper request failed for domain=%s page=%d: %s — %s", domain, page, resp.status_code, resp.text[:500])
                break
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.warning("Serper request failed for domain=%s page=%d: %s", domain, page, exc)
            break

        items = data.get("organic")
        if not items:
            logger.debug("No more results for domain=%s at page=%d", domain, page)
            break

        for item in items:
            results.append({
                "url":      item["link"],
                "title":    item["title"],
                "snippet":  item.get("snippet", ""),
                "ats_type": ats_type,
            })

        if len(items) < PAGE_SIZE:
            break  # fewer than a full page means no more results

    logger.info("search_one_site domain=%s → %d results", domain, len(results))
    return results


def search_all_ats(keywords: str, max_per_site: int = 10, days: int = 1) -> list[dict]:
    """
    Query all registered ATS sites and return a combined flat list of raw results.
    """
    all_results = []
    for site in ATS_SITES:
        site_results = search_one_site(
            domain=site["domain"],
            ats_type=site["ats_type"],
            keywords=keywords,
            max_results=max_per_site,
            days=days,
        )
        all_results.extend(site_results)
    logger.info("search_all_ats total=%d results across %d sites", len(all_results), len(ATS_SITES))
    return all_results
