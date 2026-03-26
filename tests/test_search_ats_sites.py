"""Tests for job_finder/search/ats_sites.py"""


def test_ats_sites_has_five_entries():
    from job_finder.search.ats_sites import ATS_SITES
    assert len(ATS_SITES) == 5


def test_ats_sites_has_greenhouse():
    from job_finder.search.ats_sites import ATS_SITES
    types = [s["ats_type"] for s in ATS_SITES]
    assert "greenhouse" in types
    assert "lever" in types


def test_build_query_includes_domain_and_keywords():
    from job_finder.search.ats_sites import build_query
    q = build_query("boards.greenhouse.io", "Software Engineer")
    assert "site:boards.greenhouse.io" in q
    assert "Software Engineer" in q
