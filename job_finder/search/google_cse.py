"""Google Search client via Serper.dev API."""

import logging
from datetime import date, timedelta

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


def _tbs_for_date(target: date) -> str:
    """
    Return a Serper custom date-range tbs string targeting a single calendar day.
    Format: cdr:1,cd_min:M/D/YYYY,cd_max:M/D/YYYY
    """
    date_str = f"{target.month}/{target.day}/{target.year}"
    return f"cdr:1,cd_min:{date_str},cd_max:{date_str}"


def search_one_site(domain: str, ats_type: str, keywords: str, max_results: int = 10, tbs: str = "qdr:d") -> list[dict]:
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
            "tbs":  tbs,
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
    Uses a single date-window query (suitable for nightly 1-day runs).
    For multi-day backfills use search_all_ats_backfill() instead.
    """
    tbs = _tbs_for_days(days)
    all_results = []
    for site in ATS_SITES:
        site_results = search_one_site(
            domain=site["domain"],
            ats_type=site["ats_type"],
            keywords=keywords,
            max_results=max_per_site,
            tbs=tbs,
        )
        all_results.extend(site_results)
    logger.info("search_all_ats total=%d results across %d sites", len(all_results), len(ATS_SITES))
    return all_results


def search_all_ats_backfill(keywords: str, days: int, max_per_site: int = 10) -> list[dict]:
    """
    One query per keyword per ATS site per day going back `days` calendar days.
    Each keyword is issued as a separate Serper call so Google treats them as
    distinct queries, maximising index coverage.
    Deduplicates by URL across all keywords / days before returning.
    Max theoretical yield: days × len(ATS_SITES) × len(keyword_list) × max_per_site.
    Serper cost: days × len(ATS_SITES) × len(keyword_list) queries.
    """
    keyword_list = [kw.strip() for kw in keywords.split(",") if kw.strip()]
    today = date.today()
    seen_urls: set[str] = set()
    all_results: list[dict] = []

    for offset in range(days, 0, -1):
        target = today - timedelta(days=offset)
        tbs = _tbs_for_date(target)
        day_results = []

        for kw in keyword_list:
            for site in ATS_SITES:
                site_results = search_one_site(
                    domain=site["domain"],
                    ats_type=site["ats_type"],
                    keywords=kw,
                    max_results=max_per_site,
                    tbs=tbs,
                )
                for r in site_results:
                    if r["url"] not in seen_urls:
                        seen_urls.add(r["url"])
                        day_results.append(r)

        logger.info("backfill day=%s → %d new results (running total=%d)", target, len(day_results), len(all_results) + len(day_results))
        all_results.extend(day_results)

    logger.info("search_all_ats_backfill total=%d unique results over %d days", len(all_results), days)
    return all_results
