CREATE TABLE IF NOT EXISTS nidh.public.read_audit (
    audit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    read_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    username STRING NOT NULL,
    role_name STRING NOT NULL,
    endpoint STRING NOT NULL,
    district_scope STRING NOT NULL,
    outcome STRING NOT NULL
);
