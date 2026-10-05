# app/config.py — LLM_ROUTING v8 (Phase 1: Best-of-FREE pinned priority + Cerebras + Gemini 2.5 FL)
# Source of Truth: 08 Tool & Platform Routing. (Legacy free router spec mirror - archived reference.)

OR_PRIORITY = [
    "nvidia/nemotron-3-nano-30b-a3b:free", "openai/gpt-oss-20b:free",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free", "qwen/qwen3-next-80b-a3b-instruct:free",
    "google/gemma-4-31b-it:free", "z-ai/glm-4.5-air:free",
    "meta-llama/llama-3.3-70b-instruct:free", "qwen/qwen3-coder:free",
    "google/gemma-4-26b-a4b-it:free", "poolside/laguna-m.1:free",
    "nvidia/nemotron-nano-9b-v2:free", "nvidia/nemotron-nano-12b-v2-vl:free",
    "liquid/lfm-2.5-1.2b-thinking:free", "liquid/lfm-2.5-1.2b-instruct:free",
    # 2x 120B DROPPED (run#7 re-test khong on dinh); owl-alpha removed (NO :free)
]

FREE_CREATIVE = [
    {"provider": "hhtech",     "model": "claude-sonnet-5-5",       "type": "paid"},
    {"provider": "cerebras",   "model": "gpt-oss-120b",          "type": "free", "tpd": 1000000},  # ctx free CAP 64K
    {"provider": "openrouter", "model": "OR_PRIORITY",           "type": "free", "rpm": 20, "rpd": 1000},
    {"provider": "groq",       "model": "qwen/qwen3-32b",        "type": "free", "rpd": 14400},  # small-ctx only
    {"provider": "mistral",    "model": "mistral-medium-latest", "type": "free", "rpd": 1000000},
    {"provider": "hhtech",     "model": "claude-sonnet-5-5",       "type": "paid"},  # LUON FALLBACK CUOI
]
FREE_REASONING = [
    {"provider": "hhtech",     "model": "claude-sonnet-5-5",       "type": "paid"},
    {"provider": "openrouter", "model": "OR_PRIORITY",           "type": "free", "rpm": 20, "rpd": 1000},
    {"provider": "cerebras",   "model": "gpt-oss-120b",          "type": "free", "tpd": 1000000},
    {"provider": "mistral",    "model": "mistral-medium-latest", "type": "free", "rpd": 1000000},
    {"provider": "hhtech",     "model": "claude-sonnet-5-5",       "type": "paid"},
]
FREE_UTILITY = [
    {"provider": "groq",       "model": "qwen/qwen3-32b",        "type": "free", "rpd": 14400},
    {"provider": "hhtech",     "model": "claude-sonnet-5-5",       "type": "paid"},
    {"provider": "cerebras",   "model": "gpt-oss-120b",          "type": "free", "tpd": 1000000},
    {"provider": "mistral",    "model": "mistral-small-latest",  "type": "free", "rpd": 1000000},
    {"provider": "hhtech",     "model": "claude-sonnet-5-5",       "type": "paid"},
]
EMBED_LOCAL = [
    {"provider": "local", "model": "sentence-transformers/all-MiniLM-L6-v2", "type": "local"},
]

LLM_ROUTING = {
    "S1_trend_score":      {"layers": FREE_REASONING},
    "S1_dedup_embed":      {"layers": EMBED_LOCAL},
    "S2_story_outline":    {"layers": FREE_CREATIVE},
    "S2_quality_check":    {"layers": FREE_REASONING},
    "S3_script_gen":       {"layers": FREE_CREATIVE},
    "S3_translation":      {"layers": FREE_UTILITY},
    "S4_voiceover_script": {"layers": FREE_CREATIVE},
    "S5_content_safety":   {"layers": FREE_UTILITY},
    "S6_affiliate_inject": {"layers": FREE_REASONING},
    "S6_affiliate_embed":  {"layers": EMBED_LOCAL},
    "S8_publish_meta":     {"layers": FREE_UTILITY},
    "S9_dreaming_loop":    {"layers": FREE_REASONING},
    "S9_kb_gap_embed":     {"layers": EMBED_LOCAL},
    "S9_rule_proposal":    {"layers": FREE_REASONING},
    "SETUP_ORCHESTRATE":   {"layers": FREE_REASONING},
}

RATE_LIMITS = {
    "openrouter_free_rpm": 20,   "openrouter_free_rpd": 1000,
    "cerebras_free_rpm":   30,   "cerebras_free_tpd":   1000000,
    "groq_rpm":            30,   "groq_rpd":            14400,
    "onmay_gemini_rpd":    200,
    "gemini_rpd":          1500,  "gemini_tpm":          250000,
    "mistral_rps":         1,    "mistral_tpm":         500000,   "mistral_tpmonth":     1000000000,
}

OPENROUTER_KEYS = {
    "llm_free":  {"env": "OPENROUTER_API_KEY",       "scope": "text/reasoning :free", "hard_cap_usd": 0.00},
    "media_cap": {"env": "OPENROUTER_MEDIA_API_KEY", "scope": "image/video/bgm",       "hard_cap_usd": 20.00},
}

BUDGET = {
    "llm_daily_cap_usd":      0.00,
    "media_daily_cap_usd":    0.50,
    "media_monthly_hard_usd": 20.00,
    "media_monthly_soft_usd": 15.00,
}
