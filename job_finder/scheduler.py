"""Nightly scheduler daemon — runs the JobFinder pipeline on a cron schedule."""

import argparse
import logging
import signal
import sys
from pathlib import Path

from pytz import utc
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from job_finder import config, orchestrator, sf_config_reader, sf_writer
from job_finder.notifications import post_summary
from job_finder.profiles import get_schedule, get_skills, load_profile

logger = logging.getLogger(__name__)


def _run_job(profile: dict, profile_name: str, sf: object = None) -> None:
    """Scheduled job: run the discovery pipeline using profile config."""
    keywords          = profile.get("keywords", config.DEFAULT_KEYWORDS)
    limit             = int(profile.get("limit", config.DAILY_LIMIT))
    days              = int(profile.get("days", 1))
    sf_config_id      = profile.get("sf_record_id")            # None for YAML-sourced
    min_annual_salary = profile.get("min_annual_salary")       # None for YAML-sourced
    required_skills, bonus_skills = get_skills(profile)

    logger.info(
        "Scheduled run starting — profile=%r keywords=%r limit=%d required_skills=%r",
        profile_name, keywords, limit, required_skills,
    )
    try:
        summary = orchestrator.run(
            keywords=keywords,
            limit=limit,
            dry_run=False,
            days=days,
            required_skills=required_skills or None,
            bonus_skills=bonus_skills or None,
            profile_name=profile_name,
            sf_search_config_id=sf_config_id,
            min_annual_salary=min_annual_salary,
        )
        logger.info(
            "Run complete: found=%d new=%d pushed=%d skills_filtered=%d skipped=%d failed=%d",
            summary["found"], summary["new"], summary["pushed"],
            summary["skills_filtered"], summary["skipped"], summary["failed"],
        )
        post_summary(summary)

        # Write-back to SF config record (only for SF-sourced profiles)
        if sf_config_id and sf:
            sf_config_reader.writeback(sf, sf_config_id, summary)

    except Exception as exc:
        logger.error("Scheduled run failed: %s", exc, exc_info=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="JobFinder — nightly scheduler daemon")
    parser.add_argument(
        "--profiles",
        nargs="+",
        default=["profiles/default.yaml"],
        metavar="PROFILE",
        help="YAML profile paths used as fallback when Salesforce has no active configs",
    )
    args = parser.parse_args()

    scheduler = BlockingScheduler(
        timezone=utc,
        job_defaults={
            "coalesce": True,
            "max_instances": 1,
            "misfire_grace_time": 3600,
        },
    )

    def _shutdown(signum, frame):
        logger.info("Received signal %s — shutting down scheduler gracefully", signum)
        scheduler.shutdown(wait=True)
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    # ── Attempt SF-driven config loading ──────────────────────────────────
    sf = None
    sf_profiles = []
    try:
        sf = sf_writer.connect()
        sf_profiles = sf_config_reader.load_sf_profiles(sf)
    except Exception as exc:
        logger.warning(
            "Could not load Salesforce configs (will use YAML fallback): %s", exc
        )

    if sf_profiles:
        logger.info("Using %d Salesforce-driven profile(s)", len(sf_profiles))
        profiles_to_schedule = [(p["profile_name"], p) for p in sf_profiles]
    else:
        logger.info("Using %d YAML profile(s) as fallback", len(args.profiles))
        profiles_to_schedule = []
        for profile_path in args.profiles:
            profile = load_profile(profile_path)
            profiles_to_schedule.append((Path(profile_path).stem, profile))
    # ──────────────────────────────────────────────────────────────────────

    for profile_name, profile in profiles_to_schedule:
        hour, minute = get_schedule(profile)
        scheduler.add_job(
            _run_job,
            CronTrigger(hour=hour, minute=minute, timezone=utc),
            args=[profile, profile_name, sf],
            id=f"job_finder_{profile_name}",
            name=f"JobFinder — {profile_name}",
            replace_existing=True,
        )
        logger.info(
            "Scheduled profile=%r at %02d:%02d UTC (id=job_finder_%s)",
            profile_name, hour, minute, profile_name,
        )

    # Suppress verbose APScheduler internal logs
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
    logger.info("Scheduler started with %d profile(s)", len(profiles_to_schedule))
    scheduler.start()


if __name__ == "__main__":
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    main()
