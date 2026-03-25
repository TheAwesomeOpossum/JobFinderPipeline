"""Top-level pipeline coordinator."""

import logging

from simple_salesforce import SalesforceExpiredSession

from job_finder import config, db, enrichment, sf_writer
from job_finder.deduplicator import is_duplicate, hash_url
from job_finder.scoring import score
from job_finder.search import google_cse
from job_finder.parser import greenhouse, lever, generic

logger = logging.getLogger(__name__)

PARSERS = [greenhouse, lever, generic]  # order matters — generic is catch-all


def _get_parser(url: str):
    for p in PARSERS:
        if p.can_parse(url):
            return p
    return generic


def run(keywords: str, limit: int, dry_run: bool) -> dict:
    """
    Execute the full job discovery pipeline.

    Returns a summary dict: {found, new, parsed, qualified, pushed, skipped, failed}
    """
    summary = {
        "found":     0,
        "new":       0,
        "parsed":    0,
        "qualified": 0,
        "pushed":    0,
        "skipped":   0,
        "failed":    0,
    }

    pg_conn = db.connect()
    sf = None

    try:
        if not dry_run:
            sf = sf_writer.connect()

        # Stage 1: Search
        raw_results = google_cse.search_all_ats(keywords, max_per_site=10)
        summary["found"] = len(raw_results)
        logger.info("Found %d raw results from Google CSE", len(raw_results))

        # Stage 2: Deduplicate
        new_results = []
        for raw in raw_results:
            url = raw["url"]
            raw["url_hash"] = hash_url(url)
            if dry_run or not is_duplicate(pg_conn, sf, url):
                new_results.append(raw)
        summary["new"] = len(new_results)
        logger.info("%d new (non-duplicate) results", len(new_results))

        # Stage 3: Parse
        parsed_jobs = []
        for raw in new_results:
            parser = _get_parser(raw["url"])
            job = parser.parse(raw)
            if job is not None:
                job["url_hash"] = hash_url(job["url"])
                parsed_jobs.append(job)
            else:
                logger.warning("Parser returned None for: %s", raw["url"])
        summary["parsed"] = len(parsed_jobs)
        logger.info("%d jobs parsed successfully", len(parsed_jobs))

        # Stage 4: Score and sort
        for job in parsed_jobs:
            score(job)
        parsed_jobs.sort(key=lambda j: j.get("score", 0), reverse=True)

        # Stage 5: Split qualified vs. skipped
        qualified = parsed_jobs[:limit]
        skipped = parsed_jobs[limit:]
        summary["qualified"] = len(qualified)
        summary["skipped"] = len(skipped)

        # Stage 6: Insert all into PG
        for job in qualified + skipped:
            db.insert_job_lead(pg_conn, job)

        # Mark skipped jobs
        for job in skipped:
            db.mark_skipped(pg_conn, job["url_hash"])

        if dry_run:
            logger.info("Dry run complete. Would push %d jobs to Salesforce.", len(qualified))
            return summary

        # Stage 7: Enrich (one Claude call per unique company)
        qualified = enrichment.enrich_jobs(qualified)

        # Stage 8: Write to Salesforce
        for job in qualified:
            try:
                sf_job_app_id, sf_account_id = sf_writer.write_job(sf, job)
                db.mark_pushed(pg_conn, job["url_hash"], sf_job_app_id, sf_account_id)
                summary["pushed"] += 1
                logger.info("Pushed: %s — %s", job.get("company"), job.get("title"))
            except SalesforceExpiredSession:
                raise
            except Exception as exc:
                db.mark_failed(pg_conn, job["url_hash"], str(exc)[:2000])
                logger.error("Failed to push %s: %s", job.get("url"), exc)
                summary["failed"] += 1

    finally:
        pg_conn.close()

    logger.info(
        "Pipeline complete: found=%d new=%d parsed=%d qualified=%d pushed=%d skipped=%d failed=%d",
        summary["found"], summary["new"], summary["parsed"],
        summary["qualified"], summary["pushed"], summary["skipped"], summary["failed"],
    )
    return summary
