-- ============================================================
-- G2-1: MIGRATIONS theo đúng thứ tự FK (R17.4)
-- Chạy: psql -U postgres -d video_factory_db -f run_migrations_g2.sql
-- ============================================================

-- ─── BƯỚC 1: Core tables (không có FK) ───────────────────────

CREATE TABLE IF NOT EXISTS job_log (
    id          SERIAL PRIMARY KEY,
    episode_id  VARCHAR(100),
    stage       VARCHAR(50),
    status      VARCHAR(20) DEFAULT 'pending',
    started_at  TIMESTAMPTZ DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    error_msg   TEXT,
    metadata    JSONB DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS series_bible (
    series_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    world_name        TEXT,
    setting           TEXT,
    tone              TEXT,
    characters        JSONB,
    key_plot_points   JSONB,
    established_rules JSONB,
    running_threads   JSONB,
    last_updated      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS video_metrics (
    id           SERIAL PRIMARY KEY,
    episode_id   VARCHAR(100),
    platform     VARCHAR(50),
    views        INTEGER DEFAULT 0,
    watch_time_s INTEGER DEFAULT 0,
    cpm_usd      FLOAT,
    captured_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS comment_clusters (
    id          SERIAL PRIMARY KEY,
    video_id    VARCHAR(100),
    cluster_tag VARCHAR(100),
    count       INTEGER DEFAULT 0,
    captured_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS experiment_variants (
    id           SERIAL PRIMARY KEY,
    episode_id   VARCHAR(100),
    variant_name VARCHAR(100),
    metric_key   VARCHAR(100),
    metric_value FLOAT,
    recorded_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS retention_curve (
    id         SERIAL PRIMARY KEY,
    episode_id VARCHAR(100),
    second_mark INTEGER,
    pct_retained FLOAT,
    platform   VARCHAR(50),
    captured_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS monthly_spend (
    id          SERIAL PRIMARY KEY,
    month       VARCHAR(7),
    service     VARCHAR(50),
    amount_usd  FLOAT DEFAULT 0.0,
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS api_usage (
    service     VARCHAR(50) NOT NULL,
    month       VARCHAR(7)  NOT NULL,
    chars_used  BIGINT DEFAULT 0,
    calls_count INT DEFAULT 0,
    PRIMARY KEY (service, month)
);

CREATE TABLE IF NOT EXISTS vps_config (
    key        VARCHAR(50) PRIMARY KEY,
    value      TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS circuit_breaker (
    service       VARCHAR(50) PRIMARY KEY,
    failure_count INT DEFAULT 0,
    last_fail_at  TIMESTAMPTZ,
    reset_after   INTERVAL DEFAULT '30 minutes'
);

CREATE TABLE IF NOT EXISTS weight_proposals (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    proposal_data JSONB NOT NULL,
    summary      TEXT,
    status       VARCHAR(20) DEFAULT 'pending',
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    approved_at  TIMESTAMPTZ,
    rejected_at  TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS gemini_rate_state (
    id           SERIAL PRIMARY KEY,
    window_start TIMESTAMPTZ DEFAULT NOW(),
    call_count   INT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS music_library (
    id           SERIAL PRIMARY KEY,
    filename     TEXT,
    mood         TEXT,
    genre        TEXT,
    acr_status   TEXT DEFAULT 'pending',
    license_type TEXT,
    license_url  TEXT,
    downloaded_at DATE
);

CREATE TABLE IF NOT EXISTS job_dlq (
    id         SERIAL PRIMARY KEY,
    episode_id VARCHAR(100),
    stage      VARCHAR(50),
    error_msg  TEXT,
    failed_at  TIMESTAMP DEFAULT NOW(),
    resolved   BOOLEAN DEFAULT FALSE
);

-- ─── BƯỚC 2: Tables có FK → chạy SAU bước 1 ─────────────────

CREATE TABLE IF NOT EXISTS scoring_history (
    id          SERIAL PRIMARY KEY,
    job_id      INTEGER REFERENCES job_log(id) ON DELETE CASCADE,
    market_code VARCHAR(10),
    niche_tag   VARCHAR(100),
    score       FLOAT,
    scored_at   TIMESTAMPTZ DEFAULT NOW()
);

-- ─── BƯỚC 3: Seed vps_config ─────────────────────────────────

INSERT INTO vps_config (key, value) VALUES
    ('vps_expiry_date', '2026-06-02'),
    ('rewrite_branch_active', 'true')
ON CONFLICT (key) DO NOTHING;

-- ─── KIỂM TRA ─────────────────────────────────────────────────
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
