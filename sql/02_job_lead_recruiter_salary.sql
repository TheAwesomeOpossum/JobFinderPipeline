-- Migration: add recruiter contact/account IDs and salary fields to job_lead
ALTER TABLE job_lead
    ADD COLUMN IF NOT EXISTS sf_recruiter_account_id  VARCHAR(18),
    ADD COLUMN IF NOT EXISTS sf_recruiter_contact_id  VARCHAR(18),
    ADD COLUMN IF NOT EXISTS annual_salary            DECIMAL(12, 2),
    ADD COLUMN IF NOT EXISTS salary_range_text        VARCHAR(20);
