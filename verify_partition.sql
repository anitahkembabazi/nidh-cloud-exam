-- Run after partition.sql with cockroach sql --file=verify_partition.sql.
USE nidh;

SHOW CREATE TABLE public.vaccination_dose;
SHOW RANGES FROM INDEX public.vaccination_dose@vaccination_dose_pkey;

-- Fail the command on a missing invariant, including on an empty table.
WITH dose_constraints AS (
    SELECT details FROM [SHOW CONSTRAINTS FROM public.vaccination_dose]
    WHERE validated
), missing_splits AS (
    SELECT '…/' || i::STRING FROM generate_series(1, 7) AS buckets(i)
    EXCEPT
    SELECT start_key FROM [SHOW RANGES FROM INDEX public.vaccination_dose@vaccination_dose_pkey]
)
SELECT CASE
    WHEN NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'vaccination_dose'
          AND column_name = 'child_bucket' AND is_generated = 'ALWAYS'
          AND is_nullable = 'NO' AND generation_expression = 'fnv32(child_id) & 7'
    ) THEN crdb_internal.force_error('P0001', 'Expected eight buckets computed from child_id')
    WHEN (SELECT count(DISTINCT details) FROM dose_constraints
          WHERE details IN ('PRIMARY KEY (child_bucket ASC, record_id ASC)',
                            'UNIQUE (record_id ASC)',
                            'UNIQUE (child_id ASC, vaccine_code ASC, dose_no ASC)')) <> 3
        THEN crdb_internal.force_error('P0001', 'Missing primary key or worker uniqueness constraint')
    WHEN EXISTS (SELECT 1 FROM missing_splits)
        THEN crdb_internal.force_error('P0001', 'Missing primary-index split at a child bucket boundary')
    ELSE 1
END AS partition_verified;

-- Zero counts are valid for empty or small deployments.
SELECT b.bucket, count(d.record_id) AS doses, count(DISTINCT d.child_id) AS children
FROM generate_series(0, 7) AS b(bucket)
LEFT JOIN public.vaccination_dose AS d ON d.child_bucket = b.bucket
GROUP BY b.bucket ORDER BY b.bucket;
