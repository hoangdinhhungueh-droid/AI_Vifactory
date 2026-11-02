# 🗺️ Code Map GPS Verification (Rule 138)

> **Document Version**: 1.0.0  
> **Source**: `.codemap/codemap.json` & Physical AST Inspection  
> **Date**: 2026-11-02  
> **Status**: VERIFIED & RECONCILED  

---

## 1. Executive Summary
This GPS verification audit reconciles the initial estimates from Boss Plan (`specs/boss_plans/TASK_1793543777_plan.md` Section 6) against the ground-truth physical codebase and `.codemap/codemap.json`.

All 11 pipeline stages, entrypoints, and core services were located, verified, and mapped. Discrepancies between initial estimations and exact AST lines have been documented below.

---

## 2. Pipeline Coordinates: Estimated vs. Ground Truth

| Stage / Component | Target File | Estimated Lines (Boss Plan) | Ground Truth Lines (.codemap / AST) | File Total Lines | Status / Notes |
|---|---|---|---|---|---|
| **s01_ideation** | `stages/s01_ideation.py` | L33-L72 | L33-L123 (`run`) | 124 | Reconciled with story branch |
| **s02_research** | `stages/s02_research.py` | L33-L71 | L33-L246 (`run`) | 247 | Reconciled with story evidence ledger |
| **s03_script** | `stages/s03_script.py` | L37-L112 | L36-L487 (`run`) | 489 | Reconciled with 5-beat story script |
| **s04_critic_script** | `stages/s04_critic_script.py` | L33-L122 | L33-L271 (`run`) | 272 | Reconciled with 5 deterministic gates |
| **s05_director_plan** | `stages/s05_director_plan.py` | L56-L142 | L811-L1093 (`run`) | 1,254 | Reconciled with story_shots and H1-H7 |
| **s06_critic_visual** | `stages/s06_critic_visual.py` | L33-L76 | L46-L253 (`run`) | 333 | Reconciled with visual critic gates |
| **s07_image_gen** | `stages/s07_image_gen.py` | L35-L106 | L35-L112 (`run`) | 124 | Reconciled with 16:9 newsprint styling |
| **s08_video_gen** | `stages/s08_video_gen.py` | L37-L131 | L159-L473 (`run`) | 500 | Reconciled with Veo quota limiter |
| **s09_voice_tts** | `stages/s09_voice_tts.py` | L40-L140 | L40-L245 (`run`) | 254 | Reconciled with duration measuring & WPM |
| **s10_render** | `stages/s10_render.py` | L56-L197 | L58-L530 (`run`) | 533 | Output directory is `10_render/` (canonical) |
| **s11_qc** | `stages/s11_qc.py` | L34-L96 | L339-L558 (`run`) | 564 | Reconciled with hard gate checks |
| **Orchestrator** | `orchestrator/run_pipeline.py` | Unverified | L58-L230 (`execute_pipeline`), L233-L260 (`main`) | 270 | Added resolve_stage_index & --preset |
| **Vox Director** | `app/services/unified_vox_director.py` | Unverified | L1-L1798 | 1,798 | Receives shot plan from S5 |
| **Kinetic H1-H7** | `app/services/kinetic_sub_director.py` | Unverified | L1-L1789 (`KineticFamily` L56-L65) | 1,789 | Authoritative physics engine |

---

## 3. Discrepancy & Anomaly Analysis

1. **Output Directory for S10 Render**:
   - As noted in Boss Plan, Stage S10 emits artifacts into `10_render/` rather than `s10_render/`.
   - **Action**: Invariant preserved. No renaming of `10_render/`.

2. **Schema Module Ingress**:
   - Current schema modules: `core/contracts/stages.py`, `core/contracts/b2_b3_contract.py`.
   - Directory `app/schemas` does not exist yet.
   - **Action**: Create `app/schemas/story_contracts.py` with standard Pydantic models for `EvidenceClaim`, `StorySceneLine`, `StoryShotPlan`, etc.

3. **Stage S4 Critic Gate Loop**:
   - `stages/s04_critic_script.py` currently invokes `app.services.vox_critic_council.run_dual_critic_review()`.
   - For `story_forensic` preset, deterministic code gates (`every_factual_line_has_claim_id`, `legal_language_matches_status`, `pattern_interrupt_gap_ok`) will be executed directly in Python code, bypassing LLM subjectivity for legal verification.

4. **Taxonomy H1-H7**:
   - `app/services/kinetic_sub_director.py` defines `KineticFamily`:
     - `H1_IMPACT`: Va chạm & Dập mực (stamp, slam, etc.)
     - `H2_CONSTRAINT`: Kẹp giữ & Đo đạc (caliper, compa, measure, clamp)
     - `H3_SEVER`: Cắt xé & Phân tách (scissors, tear, cut)
     - `H4_TETHER`: Dây căng & Neo giữ (copper pin, red yarn)
     - `H5_OPTICAL`: Khúc xạ quang học (magnifier, barrel distortion)
     - `H6_MARK`: Quét mực & Xung dạ quang (highlighter neon)
     - `H7_DISPLACE`: Xô đẩy & Bung nếp gấp (friction slide, pop-up unfold)
   - These 7 kinetic families and tactile props (`#F4F1EA` paper base) are 100% intact.

---

## 4. Verdict
GPS verification complete. Discrepancies reconciled and documented. Proceed to Task T1 (Preset Infrastructure).
