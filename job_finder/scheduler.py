"""Nightly scheduler daemon — runs the JobFinder pipeline on a cron schedule."""

import argparse
import logging
import signal
import sys
from pathlib import Path

from pytz import utc
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from job_finder import config, orchestrator
from job_finder.notifications import post_summary
from job_finder.profiles import get_schedule, get_skills, load_profile

logger = logging.getLogger(__name__)


def _run_job(profile: dict, profile_path: str) -> None:
    """Scheduled job: run the discovery pipeline using profile config."""
    keywords = profile.get("keywords", config.DEFAULT_KEYWORDS)
    limit = int(profile.get("limit", config.DAILY_LIMIT))
    profile_name = Path(profile_path).stem
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
            required_skills=required_skills or None,
            bonus_skills=bonus_skills or None,
            profile_name=profile_name,
        )
        logger.info(
            "Run complete: found=%d new=%d pushed=%d skills_filtered=%d skipped=%d failed=%d",
            summary["found"],
            summary["new"],
            summary["pushed"],
            summary["skills_filtered"],
            summary["skipped"],
            summary["failed"],
        )
        post_summary(summary)
    except Exception as exc:
        logger.error("Scheduled run failed: %s", exc, exc_info=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="JobFinder — nightly scheduler daemon")
    parser.add_argument(
        "--profiles",
        nargs="+",
        default=["profiles/default.yaml"],
        metavar="PROFILE",
        help="Paths to YAML profile files (default: profiles/default.yaml)",
    )
    args = parser.parse_args()

    scheduler = BlockingScheduler(
        timezone=utc,
        job_defaults={
            "coalesce": True,           # If missed multiple runs, fire once on resume
            "max_instances": 1,         # Never run overlapping copies
            "misfire_grace_time": 3600, # Fire if up to 1h late (e.g. container restart)
        },
    )

    # Explicit SIGTERM handler — docker stop sends SIGTERM, not SIGINT.
    # try/except KeyboardInterrupt alone silently ignores docker stop.
    def _shutdown(signum, frame):
        logger.info("Received signal %s — shutting down scheduler gracefully", signum)
        scheduler.shutdown(wait=True)  # wait=True: finish any running job before exit
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    for profile_path in args.profiles:
        profile = load_profile(profile_path)
        hour, minute = get_schedule(profile)
        profile_name = Path(profile_path).stem
        scheduler.add_job(
            _run_job,
            CronTrigger(hour=hour, minute=minute, timezone=utc),
            args=[profile, profile_path],
            id=f"job_finder_{profile_name}",
            name=f"JobFinder — {profile_name}",
            replace_existing=True,  # Idempotent on restart — no duplicate job entries
        )
        logger.info(
            "Scheduled profile=%r at %02d:%02d UTC (id=job_finder_%s)",
            profile_path, hour, minute, profile_name,
        )

    # Suppress verbose APScheduler internal logs
    logging.getLogger("apscheduler").setLevel(logging.WARNING)

    logger.info("Scheduler started with %d profile(s)", len(args.profiles))
    scheduler.start()  # Blocks here until _shutdown() calls scheduler.shutdown()


if __name__ == "__main__":
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    main()
