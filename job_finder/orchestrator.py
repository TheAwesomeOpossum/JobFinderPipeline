"""Top-level pipeline coordinator."""

import logging

from simple_salesforce import SalesforceExpiredSession

from job_finder import config, db, enrichment, sf_writer
from job_finder.deduplicator import is_duplicate, hash_url
from job_finder.scoring import score
from job_finder.search import google_cse
from job_finder.parser import greenhouse, lever, generic
from job_finder.salary_extractor import annual_midpoint

logger = logging.getLogger(__name__)

PARSERS = [greenhouse, lever, generic]  # order matters — generic is catch-all


def _get_parser(url: str):
    for p in PARSERS:
        if p.can_parse(url):
            return p
    return generic


def _above_salary_threshold(job: dict, threshold: float) -> bool:
    """
    Return True if the job passes the given salary threshold.

    Filter logic: keep if max known salary >= threshold.
    If no salary data is known, always keep (don't penalise missing data).
    """
    if threshold <= 0:
        return True

    # Collect all known salary ceiling values
    ceilings: list[float] = []
    if job.get("annual_salary_max") is not None:
        ceilings.append(job["annual_salary_max"])
    elif job.get("annual_salary_min") is not None:
        ceilings.append(job["annual_salary_min"])
    if job.get("hourly_rate_max") is not None:
        ceilings.append(job["hourly_rate_max"] * 2080)
    elif job.get("hourly_rate_min") is not None:
        ceilings.append(job["hourly_rate_min"] * 2080)

    if not ceilings:
        return True  # unknown salary — pass through

    return max(ceilings) >= threshold


def run(
    keywords: str,
    limit: int,
    dry_run: bool,
    days: int = 1,
    verbose: bool = False,
    required_skills: list[str] | None = None,
    bonus_skills: list[str] | None = None,
    profile_name: str | None = None,
    sf_search_config_id: str | None = None,
    min_annual_salary: float | None = None,
) -> dict:
    """
    Execute the full job discovery pipeline.

    Returns a summary dict: {found, new, parsed, skills_filtered, qualified, pushed, skipped, failed, salary_filtered}
    """
    summary = {
        "found":            0,
        "new":              0,
        "parsed":           0,
        "skills_filtered":  0,
        "salary_filtered":  0,
        "qualified":        0,
        "pushed":           0,
        "skipped":          0,
        "failed":           0,
    }

    pg_conn = db.connect()
    sf = None

    try:
        if not dry_run:
            sf = sf_writer.connect()

        # Stage 1: Search
        raw_results = google_cse.search_all_ats(keywords, max_per_site=10, days=days)
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

        # Stage 4: Score and sort (pass runtime keywords so scoring aligns with search)
        for job in parsed_jobs:
            score(job, keywords=keywords, bonus_skills=bonus_skills)
        parsed_jobs.sort(key=lambda j: j.get("score", 0), reverse=True)

        # Stage 4.25: Hard required-skills filter (drops non-technical roles before scoring count)
        def _has_required_skill(job: dict) -> bool:
            if not required_skills:
                return True
            desc = (job.get("description") or "").lower()
            return any(s.lower() in desc for s in required_skills)

        before_skills = len(parsed_jobs)
        parsed_jobs = [j for j in parsed_jobs if _has_required_skill(j)]
        summary["skills_filtered"] = before_skills - len(parsed_jobs)
        if summary["skills_filtered"]:
            logger.info(
                "%d jobs dropped by required-skills filter",
                summary["skills_filtered"],
            )

        # Stage 4.5: Hard salary threshold filter (never reaches job_lead)
        _salary_threshold = min_annual_salary if min_annual_salary is not None else config.MIN_ANNUAL_SALARY
        if _salary_threshold > 0:
            before = len(parsed_jobs)
            parsed_jobs = [j for j in parsed_jobs if _above_salary_threshold(j, _salary_threshold)]
            summary["salary_filtered"] = before - len(parsed_jobs)
            if summary["salary_filtered"]:
                logger.info(
                    "%d jobs dropped by salary threshold ($%.0f)",
                    summary["salary_filtered"],
                    _salary_threshold,
                )

        # Stage 5: Split qualified vs. skipped
        qualified = parsed_jobs[:limit]
        skipped = parsed_jobs[limit:]
        summary["qualified"] = len(qualified)
        summary["skipped"] = len(skipped)

        # Stamp each job with the profile name and SF config ID before DB insert
        for job in qualified + skipped:
            job["search_profile"] = profile_name or "default"
            job["sf_search_config_id"] = sf_search_config_id

        # Stage 6: Insert all into PG
        for job in qualified + skipped:
            db.insert_job_lead(pg_conn, job)

        # Mark skipped jobs
        for job in skipped:
            db.mark_skipped(pg_conn, job["url_hash"])

        if dry_run:
            logger.info("Dry run complete. Would push %d jobs to Salesforce.", len(qualified))
            logger.info("--- Qualified jobs (would be pushed) ---")
            for i, job in enumerate(qualified, 1):
                salary_info = job.get("salary_range_text") or ""
                logger.info(
                    "  %d. [score=%d] %s @ %s%s\n     %s",
                    i,
                    job.get("score", 0),
                    job.get("title", "?"),
                    job.get("company", "?"),
                    f"  {salary_info}" if salary_info else "",
                    job.get("url", ""),
                )
            if verbose and skipped:
                logger.info("--- Skipped jobs (scored too low) ---")
                for i, job in enumerate(skipped, 1):
                    salary_info = job.get("salary_range_text") or ""
                    logger.info(
                        "  %d. [score=%d] %s @ %s%s\n     %s",
                        i,
                        job.get("score", 0),
                        job.get("title", "?"),
                        job.get("company", "?"),
                        f"  {salary_info}" if salary_info else "",
                        job.get("url", ""),
                    )
            return summary

        # Stage 7: Enrich companies (one Claude call per unique company)
        qualified = enrichment.enrich_jobs(qualified)

        # Stage 7.5: Enrich recruiter context (for Lever jobs with hiring_managers)
        qualified = enrichment.enrich_recruiter_jobs(qualified)

        # Stage 8: Write to Salesforce
        for job in qualified:
            try:
                sf_job_app_id, sf_account_id, sf_recruiter_contact_id = sf_writer.write_job(sf, job)
                db.mark_pushed(
                    pg_conn,
                    job["url_hash"],
                    sf_job_app_id,
                    sf_account_id,
                    sf_recruiter_contact_id=sf_recruiter_contact_id,
                    annual_salary=annual_midpoint(job),
                    salary_range_text=(job.get("salary_range_text") or "")[:20] or None,
                    search_profile=job.get("search_profile"),
                    sf_search_config_id=job.get("sf_search_config_id"),
                )
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
        "Pipeline complete: found=%d new=%d parsed=%d skills_filtered=%d salary_filtered=%d "
        "qualified=%d pushed=%d skipped=%d failed=%d",
        summary["found"], summary["new"], summary["parsed"], summary["skills_filtered"],
        summary["salary_filtered"], summary["qualified"], summary["pushed"],
        summary["skipped"], summary["failed"],
    )
    return summary
