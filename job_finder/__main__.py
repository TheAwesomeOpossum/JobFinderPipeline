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
    if pre_args.profile:
        from job_finder.profiles import load_profile
        profile_data = load_profile(pre_args.profile)
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
    args = parser.parse_args()

    summary = orchestrator.run(
        keywords=args.keywords,
        limit=args.limit,
        dry_run=args.dry_run,
    )

    print(
        f"\nSummary: found={summary['found']} new={summary['new']} parsed={summary['parsed']} "
        f"salary_filtered={summary['salary_filtered']} qualified={summary['qualified']} "
        f"pushed={summary['pushed']} skipped={summary['skipped']} failed={summary['failed']}"
    )

    sys.exit(1 if summary.get("failed", 0) > 0 else 0)


if __name__ == "__main__":
    main()
