"""Tests for recruiter Account/Contact upsert and updated write_job() in sf_writer.py"""

import sys
import pytest


def _set_env(monkeypatch):
    for k, v in {
        "SERPER_API_KEY": "x", "ANTHROPIC_API_KEY": "x",
        "SF_USERNAME": "x", "SF_PASSWORD": "x", "SF_SECURITY_TOKEN": "x",
        "PG_DBNAME": "x", "PG_USER": "x", "PG_PASSWORD": "x",
    }.items():
        monkeypatch.setenv(k, v)


def _reload(monkeypatch):
    _set_env(monkeypatch)
    for mod in ["job_finder.config", "job_finder.sf_writer"]:
        sys.modules.pop(mod, None)
    from job_finder import sf_writer
    return sf_writer


def _make_job(**overrides):
    base = {
        "title": "Senior Software Engineer",
        "company": "Acme Corp",
        "description": "We are looking for a senior software engineer.",
        "description_html": "<p>We are looking for...</p>",
        "url": "https://jobs.lever.co/acme/abc-123",
        "url_hash": "abc123",
        "ats_type": "lever",
        "location": "Remote",
        "department": "Engineering",
        "posted_at": "2026-03-25",
        "score": 80,
        "mission": "To do great things.",
        "core_values": ["Quality", "Integrity"],
        "hq_address": {"street": "123 Main", "city": "SF", "state": "CA",
                       "postal_code": "94105", "country": "US"},
        "website_url": "https://acmecorp.com",
        "sf_job_app_id": None,
        "sf_account_id": None,
        # Recruiter defaults
        "recruiter_name": "Jane Smith",
        "recruiter_email": "jane@acmecorp.com",
        "recruiter_is_internal": True,
        "recruiter_firm_name": None,
        "recruiter_firm_mission": None,
        "recruiter_firm_values": [],
        "recruiter_firm_website": None,
        "recruiter_firm_hq": None,
        "sf_recruiter_account_id": None,
        "sf_recruiter_contact_id": None,
        # Salary defaults
        "annual_salary_min": 80000.0,
        "annual_salary_max": 120000.0,
        "hourly_rate_min": None,
        "hourly_rate_max": None,
        "salary_range_text": "$80k-$120k/yr",
        "salary_type": "annual",
    }
    base.update(overrides)
    return base


class MockSF:
    """Tracks all SF API calls for assertions."""

    def __init__(self, existing_account_id=None, existing_contact_id=None):
        self._existing_account_id = existing_account_id
        self._existing_contact_id = existing_contact_id
        self._query_calls: list[str] = []
        self.account_ops:   list = []
        self.job_app_ops:   list = []
        self.contact_ops:   list = []
        self.job_app_updates: list = []  # separate tracker for update calls

    def query(self, soql: str):
        self._query_calls.append(soql)
        if "Contact" in soql and self._existing_contact_id:
            return {"totalSize": 1, "records": [{"Id": self._existing_contact_id}]}
        if "Account" in soql and self._existing_account_id:
            return {"totalSize": 1, "records": [{"Id": self._existing_account_id}]}
        return {"totalSize": 0, "records": []}

    class _Obj:
        def __init__(self, new_id, ops):
            self._id = new_id
            self._ops = ops

        def create(self, payload):
            self._ops.append(("create", payload))
            return {"id": self._id, "success": True, "errors": []}

        def update(self, record_id, payload):
            self._ops.append(("update", record_id, payload))
            return None

    @property
    def Account(self):
        return self._Obj("new_account_id", self.account_ops)

    @property
    def Job_Application__c(self):
        return self._Obj("new_job_app_id", self.job_app_ops)

    @property
    def Contact(self):
        return self._Obj("new_contact_id", self.contact_ops)


# ---------------------------------------------------------------------------
# upsert_recruiter_contact
# ---------------------------------------------------------------------------

def test_upsert_recruiter_contact_creates_new_by_email(monkeypatch):
    sf_writer = _reload(monkeypatch)
    sf = MockSF(existing_contact_id=None)
    job = _make_job()

    contact_id = sf_writer.upsert_recruiter_contact(sf, job, "account_001")

    assert contact_id == "new_contact_id"
    assert any(op[0] == "create" for op in sf.contact_ops)
    payload = next(op[1] for op in sf.contact_ops if op[0] == "create")
    assert payload["Email"] == "jane@acmecorp.com"
    assert payload["LastName"] == "Smith"
    assert payload["FirstName"] == "Jane"


def test_upsert_recruiter_contact_dedupes_by_email(monkeypatch):
    sf_writer = _reload(monkeypatch)
    sf = MockSF(existing_contact_id="existing_contact_001")
    job = _make_job()

    contact_id = sf_writer.upsert_recruiter_contact(sf, job, "account_001")

    assert contact_id == "existing_contact_001"
    assert any(op[0] == "update" for op in sf.contact_ops)


def test_upsert_recruiter_contact_dedupes_by_name_when_no_email(monkeypatch):
    sf_writer = _reload(monkeypatch)
    sf = MockSF(existing_contact_id=None)
    job = _make_job(recruiter_email=None)

    sf_writer.upsert_recruiter_contact(sf, job, "account_001")

    # Should query by Name + AccountId (not Email)
    assert any("AccountId" in q for q in sf._query_calls)
    assert not any("Email" in q for q in sf._query_calls)


def test_upsert_recruiter_contact_returns_none_when_no_name(monkeypatch):
    sf_writer = _reload(monkeypatch)
    sf = MockSF()
    job = _make_job(recruiter_name=None)

    result = sf_writer.upsert_recruiter_contact(sf, job, "account_001")

    assert result is None
    assert len(sf.contact_ops) == 0


def test_upsert_recruiter_contact_splits_full_name(monkeypatch):
    sf_writer = _reload(monkeypatch)
    sf = MockSF()
    job = _make_job(recruiter_name="Bob Johnson", recruiter_email=None)

    sf_writer.upsert_recruiter_contact(sf, job, "account_001")

    payload = next(op[1] for op in sf.contact_ops if op[0] == "create")
    assert payload["FirstName"] == "Bob"
    assert payload["LastName"] == "Johnson"


def test_upsert_recruiter_contact_single_word_name(monkeypatch):
    sf_writer = _reload(monkeypatch)
    sf = MockSF()
    job = _make_job(recruiter_name="Cher", recruiter_email=None)

    sf_writer.upsert_recruiter_contact(sf, job, "account_001")

    payload = next(op[1] for op in sf.contact_ops if op[0] == "create")
    assert payload["LastName"] == "Cher"
    assert "FirstName" not in payload


def test_upsert_recruiter_contact_escapes_apostrophe(monkeypatch):
    sf_writer = _reload(monkeypatch)
    queries = []

    class QuoteSF(MockSF):
        def query(self, soql):
            queries.append(soql)
            return {"totalSize": 0, "records": []}

    sf = QuoteSF()
    job = _make_job(recruiter_name="O'Brien Pat", recruiter_email=None)

    sf_writer.upsert_recruiter_contact(sf, job, "account_001")

    assert any("O\\'Brien Pat" in q for q in queries)


# ---------------------------------------------------------------------------
# upsert_recruiter_account
# ---------------------------------------------------------------------------

def test_upsert_recruiter_account_creates_new(monkeypatch):
    sf_writer = _reload(monkeypatch)
    sf = MockSF(existing_account_id=None)
    job = _make_job(
        recruiter_is_internal=False,
        recruiter_firm_name="Hays Recruiting",
        recruiter_firm_website="https://hays.com",
        recruiter_firm_hq={"city": "London", "country": "UK"},
    )

    account_id = sf_writer.upsert_recruiter_account(sf, job)

    assert account_id == "new_account_id"
    payload = next(op[1] for op in sf.account_ops if op[0] == "create")
    assert payload["Type"] == "Recruiter Account"
    assert payload["Name"] == "Hays Recruiting"


def test_upsert_recruiter_account_updates_existing(monkeypatch):
    sf_writer = _reload(monkeypatch)
    sf = MockSF(existing_account_id="existing_recruiter_acct")
    job = _make_job(
        recruiter_firm_name="Hays Recruiting",
        recruiter_firm_website="https://hays.com",
    )

    account_id = sf_writer.upsert_recruiter_account(sf, job)

    assert account_id == "existing_recruiter_acct"
    assert any(op[0] == "update" for op in sf.account_ops)


# ---------------------------------------------------------------------------
# write_job — updated 3-tuple return + recruiter flow
# ---------------------------------------------------------------------------

def test_write_job_returns_three_tuple(monkeypatch):
    sf_writer = _reload(monkeypatch)
    sf = MockSF()
    job = _make_job()

    result = sf_writer.write_job(sf, job)

    assert len(result) == 3
    job_app_id, account_id, recruiter_contact_id = result
    assert isinstance(job_app_id, str)
    assert isinstance(account_id, str)


def test_write_job_sets_recruiter_on_job_application(monkeypatch):
    sf_writer = _reload(monkeypatch)
    sf = MockSF()
    job = _make_job()

    _, _, recruiter_contact_id = sf_writer.write_job(sf, job)

    assert recruiter_contact_id == "new_contact_id"
    # Verify Job_Application__c.update was called with Recruiter__c
    update_calls = [op for op in sf.job_app_ops if op[0] == "update"]
    assert any("Recruiter__c" in op[2] for op in update_calls)


def test_write_job_no_recruiter_contact_when_no_name(monkeypatch):
    sf_writer = _reload(monkeypatch)
    sf = MockSF()
    job = _make_job(recruiter_name=None)

    _, _, recruiter_contact_id = sf_writer.write_job(sf, job)

    assert recruiter_contact_id is None
    assert len(sf.contact_ops) == 0


def test_write_job_still_succeeds_when_recruiter_raises(monkeypatch):
    sf_writer = _reload(monkeypatch)

    class BrokenContactSF(MockSF):
        @property
        def Contact(self):
            class _Broken:
                def create(self, payload):
                    raise RuntimeError("Contact API down")
                def update(self, record_id, payload):
                    raise RuntimeError("Contact API down")
            return _Broken()

    sf = BrokenContactSF()
    job = _make_job()

    # Should NOT raise — recruiter errors are non-fatal
    job_app_id, account_id, recruiter_contact_id = sf_writer.write_job(sf, job)

    assert job_app_id == "new_job_app_id"  # job app was still created
    assert recruiter_contact_id is None


def test_write_job_creates_recruiter_account_for_external_firm(monkeypatch):
    sf_writer = _reload(monkeypatch)
    sf = MockSF()
    job = _make_job(
        recruiter_is_internal=False,
        recruiter_firm_name="TEKsystems",
        recruiter_firm_website="https://teksystems.com",
        recruiter_firm_hq=None,
    )

    _, _, _ = sf_writer.write_job(sf, job)

    # A Recruiter Account should have been created
    recruiter_account_ops = [op for op in sf.account_ops if op[0] == "create"
                              and op[1].get("Type") == "Recruiter Account"]
    assert len(recruiter_account_ops) == 1


def test_write_job_uses_company_account_for_internal_recruiter(monkeypatch):
    sf_writer = _reload(monkeypatch)
    sf = MockSF()
    job = _make_job(recruiter_is_internal=True, recruiter_firm_name=None)

    _, _, _ = sf_writer.write_job(sf, job)

    # No Recruiter Account should have been created — only the Job Application Account
    recruiter_account_ops = [op for op in sf.account_ops
                              if op[0] == "create" and op[1].get("Type") == "Recruiter Account"]
    assert len(recruiter_account_ops) == 0


def test_write_job_salary_fields_in_payload(monkeypatch):
    sf_writer = _reload(monkeypatch)
    sf = MockSF()
    job = _make_job()

    sf_writer.write_job(sf, job)

    job_app_create_calls = [op for op in sf.job_app_ops if op[0] == "create"]
    assert len(job_app_create_calls) == 1
    payload = job_app_create_calls[0][1]
    assert payload.get("Annual_Salary__c") == 100000.0  # midpoint of 80k-120k
    assert payload.get("Salary_Range__c") == "$80k-$120k/yr"
