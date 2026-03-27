"""CLI entry point: python -m job_finder"""

import argparse
import logging
import sys

from job_finder import config
from job_finder import orchestrator


def main():
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # ── Two-pass: pre-parse --profile before setting argparse defaults ──
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--profile")
    pre_args, _ = pre.parse_known_args()

    profile_data: dict = {}
    profile_name: str | None = None
    _req_skills: list[str] = []
    _bonus_skills: list[str] = []
    if pre_args.profile:
        from pathlib import Path
        from job_finder.profiles import load_profile, get_skills, get_location, get_seniority
        profile_data = load_profile(pre_args.profile)
        profile_name = Path(pre_args.profile).stem
        _req_skills, _bonus_skills = get_skills(profile_data)
    # ── End profile pre-parse ──

    parser = argparse.ArgumentParser(
        description="JobFinder — discover freshly posted engineering jobs"
    )
    parser.add_argument(
        "--profile",
        help="Path to YAML profile file (overrides env defaults, overridden by explicit flags)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run full pipeline without writing to Salesforce",
    )
    parser.add_argument(
        "--keywords",
        default=profile_data.get("keywords", config.DEFAULT_KEYWORDS),
        help="Comma-separated search keywords (default: %(default)s)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=profile_data.get("limit", config.DAILY_LIMIT),
        help="Max jobs to push to Salesforce (default: %(default)s)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=1,
        help="How many days back to search for job postings (default: 1)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="In dry-run mode, print all scored jobs (qualified + skipped)",
    )
    parser.add_argument(
        "--required-skills",
        nargs="+",
        default=_req_skills or None,
        metavar="SKILL",
        help="Skills that must appear in job description (any-of gate). Overrides profile.",
    )
    parser.add_argument(
        "--bonus-skills",
        nargs="+",
        default=_bonus_skills or None,
        metavar="SKILL",
        help="Skills that boost relevance score (+5 each, max 20). Overrides profile.",
    )
    args = parser.parse_args()

    summary = orchestrator.run(
        keywords=args.keywords,
        limit=args.limit,
        dry_run=args.dry_run,
        days=args.days,
        verbose=args.verbose,
        required_skills=args.required_skills,
        bonus_skills=args.bonus_skills,
        profile_name=profile_name,
    )

    print(
        f"\nSummary: found={summary['found']} new={summary['new']} parsed={summary['parsed']} "
        f"skills_filtered={summary['skills_filtered']} salary_filtered={summary['salary_filtered']} "
        f"qualified={summary['qualified']} pushed={summary['pushed']} "
        f"skipped={summary['skipped']} failed={summary['failed']}"
    )

    sys.exit(1 if summary.get("failed", 0) > 0 else 0)


if __name__ == "__main__":
    main()
