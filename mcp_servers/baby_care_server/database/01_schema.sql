-- Care Server 로컬 개발용 Schema입니다.
-- babies는 care_logs 외래키 테스트를 위한 최소 테이블이며 실제 관리는 Backend가 담당합니다.

CREATE TABLE IF NOT EXISTS babies (
    id VARCHAR(100) PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS care_logs (
    id VARCHAR(100) PRIMARY KEY,
    baby_id VARCHAR(100) NOT NULL,
    log_type VARCHAR(20) NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    idempotency_key VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT ck_care_logs_log_type
        CHECK (log_type IN ('feeding', 'sleep', 'diaper', 'growth')),

    CONSTRAINT fk_care_logs_baby
        FOREIGN KEY (baby_id)
        REFERENCES babies(id)
        ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_care_logs_baby_recorded_at
    ON care_logs (baby_id, recorded_at DESC);

CREATE INDEX IF NOT EXISTS idx_care_logs_baby_log_type
    ON care_logs (baby_id, log_type);
