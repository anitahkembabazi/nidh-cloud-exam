CREATE DATABASE IF NOT EXISTS nidh;

CREATE TABLE IF NOT EXISTS nidh.public.vaccination_dose (
    record_id   UUID PRIMARY KEY,
    child_id    STRING NOT NULL,
    vaccine_code STRING NOT NULL,
    dose_no     INT NOT NULL CHECK (dose_no BETWEEN 1 AND 3),
    district_id STRING,
    facility_id STRING,
    stored_at   TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT one_logical_dose UNIQUE (child_id, vaccine_code, dose_no)

);
CREATE TABLE IF NOT EXISTS nidh.public.rejected_message (
    reject_key   STRING PRIMARY KEY,
    source_queue STRING NOT NULL,
    raw_body     BYTES NOT NULL,
    reason       STRING NOT NULL,
    rejected_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- Assumed eligible-child counts for the two synthetic demonstration districts.
CREATE TABLE IF NOT EXISTS nidh.public.demo_district_population (
    district_id STRING PRIMARY KEY,
    eligible_children INT NOT NULL CHECK (eligible_children > 0)
);
INSERT INTO nidh.public.demo_district_population VALUES ('D001', 1000), ('D002', 1000)
ON CONFLICT (district_id) DO NOTHING;
