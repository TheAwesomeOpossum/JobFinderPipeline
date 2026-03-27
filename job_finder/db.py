"""PostgreSQL connection and job_lead CRUD operations."""

import logging
import psycopg2
import psycopg2.extras
from job_finder import config

logger = logging.getLogger(__name__)


def connect():
    """Return a psycopg2 connection to PostgreSQL with autocommit=False."""
    conn = psycopg2.connect(
        host=config.PG_HOST,
        port=config.PG_PORT,
        dbname=config.PG_DBNAME,
        user=config.PG_USER,
        password=config.PG_PASSWORD,
        sslmode=config.PG_SSLMODE,
    )
    conn.autocommit = False
    return conn


def insert_job_lead(conn, job: dict) -> int:
    """Insert a job_lead row; silently skip on duplicate url_hash. Returns PG row id."""
    sql = """
        INSERT INTO job_lead (url_hash, url, title, company, ats_type, score, search_profile)
        VALUES (%(url_hash)s, %(url)s, %(title)s, %(company)s, %(ats_type)s, %(score)s, %(search_profile)s)
        ON CONFLICT (url_hash) DO NOTHING
        RETURNING id
    """
    row = {
        "url_hash":       job.get("url_hash"),
        "url":            job.get("url"),
        "title":          job.get("title"),
        "company":        job.get("company"),
        "ats_type":       job.get("ats_type"),
        "score":          job.get("score"),
        "search_profile": job.get("search_profile"),
    }
    with conn.cursor() as cur:
        cur.execute(sql, row)
        result = cur.fetchone()
        conn.commit()
        return result[0] if result else 0


def mark_pushed(
    conn,
    url_hash: str,
    sf_job_app_id: str,
    sf_account_id: str,
    sf_recruiter_contact_id: str | None = None,
    annual_salary: float | None = None,
    salary_range_text: str | None = None,
    search_profile: str | None = None,
    sf_search_config_id: str | None = None,
) -> None:
    """Update job_lead status to 'pushed' with Salesforce IDs and salary data."""
    sql = """
        UPDATE job_lead
        SET status = 'pushed',
            sf_job_app_id = %(sf_job_app_id)s,
            sf_account_id = %(sf_account_id)s,
            sf_recruiter_contact_id = %(sf_recruiter_contact_id)s,
            annual_salary = %(annual_salary)s,
            salary_range_text = %(salary_range_text)s,
            search_profile = %(search_profile)s,
            sf_search_config_id = %(sf_search_config_id)s
        WHERE url_hash = %(url_hash)s
    """
    with conn.cursor() as cur:
        cur.execute(sql, {
            "url_hash":               url_hash,
            "sf_job_app_id":          sf_job_app_id,
            "sf_account_id":          sf_account_id,
            "sf_recruiter_contact_id": sf_recruiter_contact_id,
            "annual_salary":          annual_salary,
            "salary_range_text":      salary_range_text,
            "search_profile":         search_profile,
            "sf_search_config_id":    sf_search_config_id,
        })
        conn.commit()


def mark_skipped(conn, url_hash: str) -> None:
    """Update job_lead status to 'skipped'."""
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE job_lead SET status = 'skipped' WHERE url_hash = %(url_hash)s",
            {"url_hash": url_hash},
        )
        conn.commit()


def mark_failed(conn, url_hash: str, error_message: str) -> None:
    """Update job_lead status to 'failed' with error message."""
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE job_lead SET status = 'failed', error_message = %(error_message)s WHERE url_hash = %(url_hash)s",
            {"url_hash": url_hash, "error_message": error_message},
        )
        conn.commit()


def url_hash_exists(conn, url_hash: str) -> bool:
    """Return True if a row with this url_hash already exists in job_lead."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM job_lead WHERE url_hash = %(url_hash)s LIMIT 1",
            {"url_hash": url_hash},
        )
        return cur.fetchone() is not None
