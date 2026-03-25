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

    parser = argparse.ArgumentParser(
        description="JobFinder — discover freshly posted engineering jobs"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run full pipeline without writing to Salesforce",
    )
    parser.add_argument(
        "--keywords",
        default=config.DEFAULT_KEYWORDS,
        help="Comma-separated search keywords (default: %(default)s)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=config.DAILY_LIMIT,
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
        f"qualified={summary['qualified']} pushed={summary['pushed']} "
        f"skipped={summary['skipped']} failed={summary['failed']}"
    )

    sys.exit(1 if summary.get("failed", 0) > 0 else 0)


if __name__ == "__main__":
    main()
