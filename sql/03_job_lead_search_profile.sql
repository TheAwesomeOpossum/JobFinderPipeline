-- Migration: add search_profile column to job_lead
ALTER TABLE job_lead
    ADD COLUMN IF NOT EXISTS search_profile VARCHAR(100);
