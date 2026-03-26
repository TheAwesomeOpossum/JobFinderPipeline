"""Tests for job_finder/parser/generic.py"""

import sys
import pytest


def _set_env(monkeypatch):
    for k, v in {
        "SERPER_API_KEY": "x", "ANTHROPIC_API_KEY": "x",
        "SF_USERNAME": "x", "SF_PASSWORD": "x", "SF_SECURITY_TOKEN": "x",
        "PG_DBNAME": "x", "PG_USER": "x", "PG_PASSWORD": "x",
    }.items():
        monkeypatch.setenv(k, v)


HTML_FIXTURE = """<!DOCTYPE html>
<html>
<head><title>Senior Engineer | Acme Corp</title></head>
<body>
<nav>Navigation menu</nav>
<main>
  <h1>Senior Software Engineer</h1>
  <p>We are looking for a talented engineer to join our team.</p>
  <script>console.log("noise")</script>
  <style>.btn { color: red; }</style>
</main>
<footer>Copyright 2026</footer>
</body>
</html>"""


def test_can_parse_always_true(monkeypatch):
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    from job_finder.parser.generic import can_parse
    assert can_parse("https://anything.com") is True
    assert can_parse("https://wd1.myworkdayjobs.com/acme/jobs/123") is True


def test_parse_strips_noise_tags(monkeypatch):
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    from job_finder.parser import generic

    class MockResponse:
        text = HTML_FIXTURE
        apparent_encoding = "utf-8"
        def raise_for_status(self): pass

    monkeypatch.setattr("job_finder.parser.generic.requests.get", lambda *a, **kw: MockResponse())

    raw = {"url": "https://wd1.myworkdayjobs.com/acme/jobs/1", "title": "SE", "snippet": "", "ats_type": "workday", "url_hash": ""}
    result = generic.parse(raw)

    assert result is not None
    # Noise tags should be removed from description
    assert "console.log" not in result["description"]
    assert "Copyright" not in result["description"]
    assert "Navigation menu" not in result["description"]


def test_parse_splits_title_on_pipe(monkeypatch):
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    from job_finder.parser import generic

    class MockResponse:
        text = HTML_FIXTURE
        apparent_encoding = "utf-8"
        def raise_for_status(self): pass

    monkeypatch.setattr("job_finder.parser.generic.requests.get", lambda *a, **kw: MockResponse())

    raw = {"url": "https://wd1.myworkdayjobs.com/acme/jobs/1", "title": "SE", "snippet": "", "ats_type": "workday", "url_hash": ""}
    result = generic.parse(raw)

    assert result is not None
    # Title should be "Senior Engineer" (before " | ")
    assert result["title"] == "Senior Engineer"


def test_parse_sets_apparent_encoding(monkeypatch):
    """resp.encoding must be set from apparent_encoding before accessing .text."""
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    from job_finder.parser import generic

    encoding_set = []

    class MockResponse:
        text = "<html><head><title>Job</title></head><body><p>Hello</p></body></html>"
        apparent_encoding = "utf-8"

        @property
        def encoding(self):
            return self._encoding

        @encoding.setter
        def encoding(self, val):
            encoding_set.append(val)
            self._encoding = val

        def raise_for_status(self): pass

    monkeypatch.setattr("job_finder.parser.generic.requests.get", lambda *a, **kw: MockResponse())

    raw = {"url": "https://wd1.myworkdayjobs.com/acme/jobs/1", "title": "", "snippet": "", "ats_type": "workday", "url_hash": ""}
    generic.parse(raw)

    assert "utf-8" in encoding_set


def test_parse_returns_none_on_fetch_error(monkeypatch):
    _set_env(monkeypatch)
    sys.modules.pop("job_finder.config", None)
    from job_finder.parser import generic

    monkeypatch.setattr(
        "job_finder.parser.generic.requests.get",
        lambda *a, **kw: (_ for _ in ()).throw(Exception("Network error"))
    )

    raw = {"url": "https://wd1.myworkdayjobs.com/acme/jobs/1", "title": "", "snippet": "", "ats_type": "workday", "url_hash": ""}
    assert generic.parse(raw) is None
