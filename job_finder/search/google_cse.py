"""Paginated Google Custom Search API client."""

import logging
import requests

from job_finder import config
from job_finder.search.ats_sites import ATS_SITES, build_query

logger = logging.getLogger(__name__)

CSE_ENDPOINT = "https://customsearch.googleapis.com/customsearch/v1"
MAX_RESULTS_PER_QUERY = 100
PAGE_SIZE = 10


def search_one_site(domain: str, ats_type: str, keywords: str, max_results: int = 10) -> list[dict]:
    """
    Query Google CSE for a single ATS domain.
    Returns a list of raw result dicts with url, title, snippet, ats_type.
    """
    results = []
    cap = min(max_results, MAX_RESULTS_PER_QUERY)
    query = build_query(domain, keywords)

    for start in range(1, cap + 1, PAGE_SIZE):
        params = {
            "key":         config.GOOGLE_API_KEY,
            "cx":          config.GOOGLE_CSE_ID,
            "q":           query,
            "num":         PAGE_SIZE,
            "start":       start,
            "dateRestrict": "d1",
        }
        try:
            resp = requests.get(CSE_ENDPOINT, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.warning("CSE request failed for domain=%s start=%d: %s", domain, start, exc)
            break

        items = data.get("items")
        if not items:
            logger.debug("No more results for domain=%s at start=%d", domain, start)
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


def search_all_ats(keywords: str, max_per_site: int = 10) -> list[dict]:
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
        )
        all_results.extend(site_results)
    logger.info("search_all_ats total=%d results across %d sites", len(all_results), len(ATS_SITES))
    return all_results
