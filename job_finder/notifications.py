"""Optional Slack webhook notification — fire-and-forget, never crashes the pipeline."""

import logging
import os

import requests

logger = logging.getLogger(__name__)


def post_summary(summary: dict) -> None:
    """POST a run summary to SLACK_WEBHOOK_URL if configured. Silent on failure."""
    url = os.getenv("SLACK_WEBHOOK_URL")
    if not url:
        return
    text = (
        f":robot_face: *JobFinder* \u2014 run complete\n"
        f"found={summary['found']} new={summary['new']} "
        f"pushed={summary['pushed']} skipped={summary['skipped']} failed={summary['failed']}"
    )
    try:
        resp = requests.post(url, json={"text": text}, timeout=5)
        resp.raise_for_status()
        logger.info("Slack notification sent")
    except Exception as exc:
        logger.warning("Slack notification failed: %s", exc)
