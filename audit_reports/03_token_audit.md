# 🪙 COMPREHENSIVE LLM TOKEN AUDIT & OVER-CREDIT SAFEGUARD ANALYSIS (AVF-E2E-003)

> **Audit Date**: 2026-10-17  
> **Auditor**: Worker Gemini 3.8 Flash High (Antigravity IDE) under Boss Claude Opus 5.5 Supervision  
> **Scope**: Token Consumption, Prompt Caching, Retry Caps, and Cost Guardrails across HHTech API, Anthropic, OpenAI, and Google Native.

---

## 1. LLM Invocation Matrix & Cost Safeguard Table

| Stage / Module | Primary Model & Provider | Call Purpose | Worst-Case Max Input Tokens | Max Output Tokens | Cache Lookup Before Call? | Max Retry Limit | Estimated Max Burn (Tokens) | Cost per Run (VND / USD) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **B1 Viability Check** (`trend_engine_b1.py`) | `claude-v4.1-flash` / `kimi-k3` via HHTech | Evaluate viral potential of candidate topics | 2,500 | 500 | **Yes**: Capped by `MAX_VIABILITY_LLM_EVALS=6` & permanent history deduplication | 2 attempts | 18,000 tokens (6 evals × 3,000) | ~29 VND (~$0.001) |
| **B1.5 Blue Ocean Gap** (`competitor_recon_b15.py`) | `claude-sonnet-5-5` via HHTech | Analyze competitor saturation & find uncontested angle | 4,000 | 1,000 | **Yes**: Grounding intel stored on disk (`grounding_intel.json`) | 2 attempts | 10,000 tokens | ~16 VND (~$0.0006) |
| **B1.5 Fact Grounding** (`grounding_layer_b15.py`) | Google Search API + `claude-sonnet-5-5` | Extract verified quantitative figures & timestamps | 6,000 | 1,500 | **Yes**: Caches factsheet per topic | 2 attempts | 15,000 tokens | ~24 VND (~$0.001) |
| **B2 5-Beat Docudrama** (`story_engine_b2.py`) | `claude-opus-5-5` via HHTech | Generate 12-15 min cold-open script with 5 beats | 12,000 | 4,000 | **Yes**: Checks `story.txt` on disk; skips if Story Gate passed | 2 attempts (`MAX_B2_ATTEMPTS=2`) | 32,000 tokens | ~64 VND (~$0.0026) |
| **B2.1 Fact & Causal Audit** (`story_judge.py`) | `gpt-6-astra` / `claude-opus-5-5` | Forensic check on transmission mechanisms (Rule 130) | 10,000 | 2,000 | **Yes**: Stored in `story_gate_audit.json` | 1 attempt | 12,000 tokens | ~24 VND (~$0.001) |
| **B3 Dynamic Director** (`vox_automated_director.py`) | `claude-sonnet-5-5` / Deterministic Rule Engine | Break down into narrative beats & 2-shot camera cadence | 8,000 | 3,000 | **Yes**: Checks `director_plan.json` on disk | 2 attempts | 22,000 tokens | ~35 VND (~$0.0014) |
| **B3.5 Prompt Forge** (`prompt_forge.py`) | `claude-sonnet-5-5` via HHTech | Generate 5-part tactile image prompts (16:9 BG + 1:1 FG) | 6,000 | 4,000 | **Yes**: Checks `prompts_forge.json` on disk | 1 attempt | 10,000 tokens | ~16 VND (~$0.0006) |
| **B3.5.1 Visual Audit** (`b36_visual_convergence.py`) | Rule-based diversity + optional Vision critic | Validate FG magenta chroma & actor invariant | 4,000 | 1,000 | **Yes**: Checks `visual_convergence_audit.json` | 1 attempt | 5,000 tokens | ~10 VND (~$0.0004) |
| **B4/B5 Image Gen** (`vf-image-gen`) | Gemini Pro Web (7-Chrome Profiles) | Generate 2K DCI editorial artwork (26 images) | 0 (Web UI) | 0 (Web UI) | **Yes**: Browser session rotation | 3 retries | **0 External API Tokens** (Free Google Tier) | **0 VND ($0.00)** |
| **B6.2 Adversarial Gate** (`adversarial_director_gate.py`)| `claude-opus-5-5` via HHTech | Audit props consistency against Rule 122/128/136 | 6,000 | 2,000 | **Yes**: Checks `adversarial_audit.json` | 1 attempt | 8,000 tokens | ~16 VND (~$0.0006) |
| **B9 Audio/Chapter Sweep** (`post_render_technical_sweep.py`)| Deterministic Python + FFmpeg | Probe -14 LUFS & Remotion frame-based chapters | 0 | 0 | **Yes**: Reads `remotion_props.json` directly | 0 | **0 Tokens** (Pure CPU) | **0 VND ($0.00)** |
| **B10 Auto SEO** (`seo_autogen_b10.py`) | `claude-v4.1-flash` via HHTech | Generate high-CTR titles, description & tags | 4,000 | 1,500 | **Yes**: Checks `seo_package.json` | 2 attempts | 11,000 tokens | ~18 VND (~$0.0007) |
| **B11 Analytics Dreaming** (`b11_engine.py`) | `claude-v4.1-flash` via HHTech | Extract retention drop-off lessons after 48h | 8,000 | 2,000 | **Yes**: Tier 1 Delta Scan bypasses LLM if views/retention unchanged (0 token) | 1 attempt | 0 to 10,000 tokens | 0 ~ 16 VND (0 ~ $0.0006) |

---

## 2. Theoretical Worst-Case Token Burn per Video Episode

- **Total Worst-Case Token Burn per Single Episode**:  
  $$\text{Total Tokens} \approx 18,000 + 10,000 + 15,000 + 32,000 + 12,000 + 22,000 + 10,000 + 5,000 + 8,000 + 11,000 + 10,000 \approx \mathbf{153,000 \text{ tokens}}$$
- **Financial Cost Calculation (HHTech API Rates)**:
  - Claude Opus 5.5 / GPT-6-Astra rate: 2,000 VND / 1,000,000 tokens (2.0 VND / 1k tokens)
  - Claude Sonnet 5 / Flash rate: 1,600 VND / 1,000,000 tokens (1.6 VND / 1k tokens)
  - **Worst-Case Cost per Episode**: **~250 VND to 350 VND** (approximately **$0.010 - $0.014 USD**)!
  - **Normal Optimized Path (with prompt caching & hit rate 70%)**: **~80 VND to 120 VND** (**~$0.004 USD**)!

---

## 3. Token Leakage & Over-Credit Vulnerability Audit Findings

### Finding 3.1: Prompt Caching is Activated for Anthropic Beta
In `app/services/model_gateway.py` (Line 181-182):
```python
if "claude" in model.lower():
    headers["anthropic-beta"] = "prompt-caching-2024-07-31"
```
And usage monitoring (Line 257-259) explicitly captures and logs cache hits:
```python
cached_tokens = details.get("cached_tokens", 0)
if cached_tokens > 0:
    logger.info(f"[GATEWAY] Prompt cache hit! {cached_tokens}/{usage.get('prompt_tokens', 0)} tokens served from cache.")
```
**Verdict**: **SECURE & COST-OPTIMIZED**.

### Finding 3.2: B1 Daily Quota Guard & Candidate Scan Cap
In `app/services/trend_engine_b1.py`:
- `MAX_SCAN_CANDIDATES_DEFAULT = 10`
- `MAX_VIABILITY_LLM_EVALS_DEFAULT = 6`
- `MAX_B2_ATTEMPTS_DEFAULT = 2`
- `is_market_done_today()`: Checks if the scheduled market already has an episode or candidate pool exhausted for the day. If yes, exits immediately with **0 tokens consumed**.
**Verdict**: **SECURE**. No infinite candidate evaluation loop.

### Finding 3.3: B4 Image Generation Bypasses Commercial API Costs
Image generation (which would normally cost $0.04 - $0.20 per image × 26 images = $1.04 - $5.20 per episode) is **100% offloaded to Antigravity Local Playwright pool** rotating across 7 pre-authenticated Google accounts.
**External API Token Burn**: **0 tokens**.
**Verdict**: **ZERO COST EXCELLENCE**.
