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
        "--url",
        help="Push a single job URL directly to Salesforce (skips search/filters)",
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
        help="Print score-filtered jobs (dropped below threshold) and, in dry-run, skipped jobs",
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

    # ── Single-URL push mode ──
    if args.url:
        result = orchestrator.push_url(url=args.url, dry_run=args.dry_run)
        if result.get("success"):
            if result.get("dry_run"):
                print("\nDry run complete. Job parsed but not pushed to Salesforce.")
            else:
                print(
                    f"\nPushed: {result.get('title')} @ {result.get('company')}"
                    f"\n  JobApplication: {result.get('sf_job_app_id')}"
                    f"\n  Account:        {result.get('sf_account_id')}"
                )
        else:
            print(f"\nFailed: {result.get('error')}")
        sys.exit(0 if result.get("success") else 1)

    # ── Normal pipeline mode ──
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
