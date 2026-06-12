-- =====================================================================
-- Migration: G2 missing tables (voice_profiles, vf_episode_state,
--            early_platform_signals)
-- Date: 2026-06-04 | Method: RAW SQL canonical
-- Ly do: Alembic chua bao gio init; 16 bang hien tai deu raw SQL owner=postgres.
-- Thay the: alembic mpt_001 (ssml_style) + mpt_002 (vf_episode_state)
-- Idempotent: CREATE ... IF NOT EXISTS -> chay lai an toan.
-- =====================================================================
BEGIN;

-- ---------- G2-6: voice_profiles (base + ssml_style) -----------------
-- Mirror Notion DB 5 + mpt_001 ssml_style + page 05 voice_mode/lora
CREATE TABLE IF NOT EXISTS voice_profiles (
    series_id              VARCHAR(100) PRIMARY KEY,
    title                  TEXT,
    narrator_voice         TEXT,                                 -- Edge TTS voice code
    char_voices            JSONB        DEFAULT '{}'::jsonb,     -- {char_name: voice_code}
    vibe_palette           JSONB        DEFAULT '{}'::jsonb,     -- style params
    voice_mode             VARCHAR(20)  DEFAULT 'narrator_only', -- narrator_only | multi_character
    lora_path              TEXT,                                 -- R2 path to LoRA
    char_consistency_lora  TEXT,                                 -- S4 LoRA register
    ssml_style             JSONB        DEFAULT '{}'::jsonb,     -- rate/pitch/volume/emphasis
    created_at             TIMESTAMPTZ  DEFAULT NOW(),
    updated_at             TIMESTAMPTZ  DEFAULT NOW()
);
COMMENT ON COLUMN voice_profiles.ssml_style IS
  'SSML style config cho TTS. Keys: rate/pitch/volume/emphasis.';
CREATE INDEX IF NOT EXISTS idx_voice_profiles_ssml_style
    ON voice_profiles USING gin(ssml_style);

-- ---------- G2-7: vf_episode_state (canonical page 09) ---------------
CREATE TABLE IF NOT EXISTS vf_episode_state (
    episode_id        VARCHAR(100) PRIMARY KEY,
    series_id         VARCHAR(100) NOT NULL,
    current_stage     VARCHAR(50)  NOT NULL DEFAULT 'S1_queued',
    stage_started_at  TIMESTAMPTZ,
    stage_timeout_at  TIMESTAMPTZ,
    retry_count       INTEGER      DEFAULT 0,
    last_error        TEXT,
    metadata          JSONB        DEFAULT '{}'::jsonb,
    created_at        TIMESTAMPTZ   DEFAULT NOW(),
    updated_at        TIMESTAMPTZ   DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_vf_episode_state_series
    ON vf_episode_state (series_id, current_stage);
CREATE INDEX IF NOT EXISTS idx_vf_episode_state_timeout
    ON vf_episode_state (stage_timeout_at) WHERE stage_timeout_at IS NOT NULL;

CREATE OR REPLACE FUNCTION update_vf_episode_state_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_vf_episode_state_updated ON vf_episode_state;
CREATE TRIGGER trg_vf_episode_state_updated
    BEFORE UPDATE ON vf_episode_state
    FOR EACH ROW EXECUTE FUNCTION update_vf_episode_state_updated_at();
COMMENT ON TABLE vf_episode_state IS
  'MPT Salvage: per-episode pipeline state. Resume-on-crash + SLA monitoring.';

-- ---------- G2-10: early_platform_signals (DESIGN — no canonical) ----
CREATE TABLE IF NOT EXISTS early_platform_signals (
    id            SERIAL PRIMARY KEY,
    episode_id    VARCHAR(100) NOT NULL,
    platform      VARCHAR(50)  NOT NULL,        -- youtube/tiktok/spotify/...
    signal_type   VARCHAR(50)  NOT NULL,        -- views_1h/views_24h/ctr/retention_pct/likes
    value         FLOAT,
    captured_at   TIMESTAMPTZ  DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_early_platform_signals_episode
    ON early_platform_signals (episode_id, platform, captured_at DESC);

COMMIT;
