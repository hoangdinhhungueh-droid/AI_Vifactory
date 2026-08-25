-- VF Audit Pipeline — Database Schema Initialization
-- Run once: psql -U postgres -d video_factory_db -f scripts/init-audit-tables.sql
-- Created by Notion AI audit 15/08/2026

-- Audit results: one row per audit run
CREATE TABLE IF NOT EXISTS audit_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    episode_id TEXT NOT NULL,
    audit_type TEXT NOT NULL,          -- story | director | prompt | image
    stage TEXT NOT NULL,                -- S2 | S2.5 | S5 | S9
    score NUMERIC(4,2) NOT NULL,        -- 0.00-10.00 composite score
    verdict TEXT NOT NULL,              -- APPROVED | REVIEW | REJECTED
    axis_scores JSONB NOT NULL,         -- {"structure": 9, "hook": 8, ...}
    issues JSONB NOT NULL,              -- [{"severity": "high", "axis": "hook", "message": "...", "fix": "..."}]
    recommendations JSONB NOT NULL,    -- [{"skill": "/video:story", "update": "...", "priority": "high"}]
    llm_used TEXT,                      -- groq | gemini | rule_only
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Skill enhancement proposals: generated from audit patterns
CREATE TABLE IF NOT EXISTS skill_enhancements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    audit_result_id UUID REFERENCES audit_results(id) ON DELETE CASCADE,
    skill_name TEXT NOT NULL,          -- /video:story, /video:director, /video:prompt
    enhancement_type TEXT NOT NULL,    -- prompt_update | rule_add | threshold_adjust | pattern_learn
    current_value TEXT,                -- current skill config value
    proposed_value TEXT NOT NULL,      -- proposed new value
    rationale TEXT NOT NULL,            -- why this enhancement is needed
    confidence NUMERIC(3,2) DEFAULT 0.50,  -- 0.00-1.00 confidence score
    status TEXT DEFAULT 'pending',     -- pending | approved | rejected | applied
    created_at TIMESTAMPTZ DEFAULT NOW(),
    approved_at TIMESTAMPTZ,
    applied_at TIMESTAMPTZ
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_audit_results_episode ON audit_results (episode_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_results_type ON audit_results (audit_type, verdict, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_skill_enhancements_status ON skill_enhancements (status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_skill_enhancements_skill ON skill_enhancements (skill_name, status);

-- Enable extension for gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

\echo 'Audit tables created successfully.'
