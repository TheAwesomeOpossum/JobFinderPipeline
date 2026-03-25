"""Tests for job_finder/notifications.py"""

import sys


_SUMMARY = {
    "found": 10,
    "new": 7,
    "parsed": 7,
    "qualified": 5,
    "pushed": 5,
    "skipped": 2,
    "failed": 0,
}


def _reload(monkeypatch):
    sys.modules.pop("job_finder.notifications", None)


def test_post_summary_skips_when_no_webhook(monkeypatch):
    _reload(monkeypatch)
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
    mock_post = monkeypatch.setattr("requests.post", lambda *a, **kw: (_ for _ in ()).throw(AssertionError("should not call requests.post")))  # noqa
    # Simpler: just patch via mocker-style approach using monkeypatch
    calls = []

    import requests as req_mod
    monkeypatch.setattr(req_mod, "post", lambda *a, **kw: calls.append((a, kw)))

    from job_finder.notifications import post_summary

    post_summary(_SUMMARY)

    assert calls == [], "requests.post should not be called when SLACK_WEBHOOK_URL is unset"


def test_post_summary_posts_when_webhook_set(monkeypatch):
    _reload(monkeypatch)
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "http://example.com/webhook")

    posted = []

    class _FakeResp:
        def raise_for_status(self):
            pass

    import requests as req_mod
    monkeypatch.setattr(req_mod, "post", lambda url, **kw: posted.append((url, kw)) or _FakeResp())

    from job_finder.notifications import post_summary

    post_summary(_SUMMARY)

    assert len(posted) == 1
    url, kwargs = posted[0]
    assert url == "http://example.com/webhook"
    assert "json" in kwargs
    assert "found=10" in kwargs["json"]["text"]
    assert "pushed=5" in kwargs["json"]["text"]


def test_post_summary_handles_request_exception_silently(monkeypatch):
    _reload(monkeypatch)
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "http://example.com/webhook")

    import requests as req_mod
    monkeypatch.setattr(req_mod, "post", lambda *a, **kw: (_ for _ in ()).throw(Exception("network error")))

    from job_finder.notifications import post_summary

    # Should not raise
    post_summary(_SUMMARY)
