-- Apply after schema.sql with cockroach sql --file=partition.sql.
-- Run statements in autocommit so each online schema job finishes before the
-- next step. After an interruption or concurrent DDL retry, rerun this file.
USE nidh;

-- Eight ranges are a deployment choice. Only the child ID selects the bucket,
-- so different doses for a child use the same prefix across all districts.
ALTER TABLE public.vaccination_dose
    ADD COLUMN IF NOT EXISTS child_bucket INT NOT VISIBLE NOT NULL
    AS (fnv32(child_id) & 7) STORED;

-- CockroachDB maintains the old UUID primary key as a unique secondary index
-- through the online swap. The existing logical-dose index stays unique too.
ALTER TABLE public.vaccination_dose
    ALTER PRIMARY KEY USING COLUMNS (child_bucket, record_id);

-- Split the primary row data at every interior bucket boundary, even on an
-- empty table. CockroachDB controls range placement and replication.
ALTER TABLE public.vaccination_dose SPLIT AT
    SELECT bucket FROM generate_series(1, 7) AS buckets(bucket);
