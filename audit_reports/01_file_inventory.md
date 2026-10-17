# 📋 PIPELINE FILE INVENTORY & LLM CALL MAPPING (AVF-E2E-001)

> **Audit Date**: 2026-10-17  
> **Auditor**: Worker Gemini 3.8 Flash High (Antigravity IDE) under Boss Claude Opus 5.5 Supervision  
> **Scope**: VPS (`/root/video_factory`), Local Workspace (`AI Video Factory`), and Git parity (`main@d6a6e00`).

---

## 1. Modular Stage Architecture (s01 → s11 / Core Pipeline)

The core modular pipeline provides a deterministic, zero-cost (when mocked/cached) state machine governed by Pydantic v2 strict contracts (`core/contracts/stages.py`) and atomic validation gates (`core/gates.py`).

| Stage ID | Stage Name | Implementation File | Entrypoint Function | Upstream / Downstream | LLM Call Sites | Human Gate Involvement |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **s01_ideation** | Trend Discovery & Ideation | `stages/s01_ideation.py` | `run(ctx: RunContext)` | Up: None<br>Down: `s02_research` | Google Trends / RSS / Optional GPT-6-Astra | None (Auto-proceed) |
| **s02_research** | Deep Investigative Research | `stages/s02_research.py` | `run(ctx: RunContext)` | Up: `s01_ideation`<br>Down: `s03_script` | Grounding API / Search / Optional Claude | None (Auto-proceed) |
| **s03_script** | 5-Beat Docudrama Script | `stages/s03_script.py` | `run(ctx: RunContext)` | Up: `s02_research`<br>Down: `s04_critic_script`, `s09_voice_tts` | Claude-Sonnet-5-5 / Claude-Opus-5.5 | **Human Gate 1** (Telegram Broadcast) |
| **s04_critic_script**| Critic Council Script Audit | `stages/s04_critic_script.py` | `run(ctx: RunContext)` | Up: `s03_script`<br>Down: `s05_director_plan` | Dual-Critic: Claude-Opus-5.5 + GPT-6-Astra | Non-blocking auto-repair (Max 2 rounds) |
| **s05_director_plan**| Dynamic Director Plan & Cutouts | `stages/s05_director_plan.py` | `run(ctx: RunContext)` | Up: `s04_critic_script`<br>Down: `s06_critic_visual` | Claude-Sonnet-5-5 / VoxAutomatedDirector | **Human Gate 2** (Telegram Card + Command Block) |
| **s06_critic_visual**| Critic Visual & Composition | `stages/s06_critic_visual.py` | `run(ctx: RunContext)` | Up: `s05_director_plan`<br>Down: `s07_image_gen` | Dual-Critic: Multimodal Vision Council | Convergence Score Gate (Threshold >= 8.0) |
| **s07_image_gen** | Gemini Seed Image Generation | `stages/s07_image_gen.py` | `run(ctx: RunContext)` | Up: `s06_critic_visual`<br>Down: `s08_video_gen` | Gemini Web (7 Accounts Rotation in Antigravity) | Antigravity Local Execution (`/vf-image-gen`) |
| **s08_video_gen** | Veo 3.1 Video Gen (7 Acc) | `stages/s08_video_gen.py` | `run(ctx: RunContext)` | Up: `s07_image_gen`<br>Down: `s10_render` | Google Flow I2V (7 Account Rotation) | Quota rotation circuit breaker |
| **s09_voice_tts** | Edge-TTS Voiceover & Karaoke | `stages/s09_voice_tts.py` | `run(ctx: RunContext)` | Up: `s03_script`<br>Down: `s10_render` | Edge-TTS Neural Voice (Zero API cost) | None (Auto-proceed) |
| **s10_render** | Vox Tactile Compositor Assembly| `stages/s10_render.py` | `run(ctx: RunContext)` | Up: `s08_video_gen`, `s09_voice_tts`<br>Down: `s11_qc` | FFmpeg / Remotion CPU / Loudnorm | None (Deterministic Render) |
| **s11_qc** | Master QC Final Verification | `stages/s11_qc.py` | `run(ctx: RunContext)` | Up: `s10_render`<br>Down: YouTube Upload | `vox.qa.gates` Forensic probe | **Human Gate 3** (Final YouTube Review & Publish) |

---

## 2. Production Services & 24/7 VPS Background Services

| Service / Script | Purpose | VPS Path | Execution Cadence | Inter-service Dependencies |
| :--- | :--- | :--- | :--- | :--- |
| `run_trend_pipeline.py` | Weekly staggered market scheduler & B1-B3 pipeline | `/root/video_factory/scripts/run_trend_pipeline.py` | Cron: Daily at 23:00 UTC (06:00 VN) | `trend_engine_b1.py`, `market_scheduler.py`, `daily_market_lock.py` |
| `prompts_forge_watcher.py` | FileSystem watcher for B3.5 `prompts_forge.json` | `/root/video_factory/scripts/watchers/prompts_forge_watcher.py` | Daemon (Systemd / Background PID 3300050) | `telegram_buttons.py` -> Human Gate 2 card |
| `image_ready_watcher.py` | FileSystem watcher for B5 `images_ready.json` | `/root/video_factory/scripts/watchers/image_ready_watcher.py` | Daemon (Systemd / Background PID 3300051) | Spawns `continue_after_images.py` |
| `continue_after_images.py` | Master B6 -> B10 post-production runner | `/root/video_factory/scripts/continue_after_images.py` | Invoked on `images_ready.json` event | `build_remotion_props.py`, `resume_episode.py`, `execute_b10_auto_seo_upload_gate2.py` |
| `b11_engine.py` | Post-mortem 48h YouTube analytics dreaming loop | `/root/video_factory/scripts/b11_engine.py` | Cron: Every 6 hours (`15 */6 * * *`) | YouTube Analytics API, Notion Memory Vault |
| `post_sync_cleanup.py` | Daily storage lifecycle & temporary file purging | `/root/video_factory/scripts/post_sync_cleanup.py` | Cron: Daily at 20:00 UTC (03:00 VN) | Cleans `/tmp/`, unlinked renders, expired R2 cache |
| `uvicorn app.main:app` | FastAPI Webhook & Diagnostic API Server | `/root/video_factory/app/main.py` | Daemon: Port 8000 (PID 104192) | Health check, manual trigger webhooks |
| `celery worker (default)` | Celery async queue for background tasks | `app.celery_app` (`vf-celery-default.service`) | Daemon: Concurrency 2 | RabbitMQ `amqp://127.0.0.1:5672` |
| `celery worker (video)` | Celery video heavy worker for CPU renders | `app.celery_app` (`vf-celery-video.service`) | Daemon: Concurrency 1, max memory 900MB | RabbitMQ `amqp://127.0.0.1:5672` |

---

## 3. Physical State & Cache Locations

- **VPS Root State**: `/var/vf/episodes/{episode_id}/` (or `/root/video_factory/episodes/{episode_id}/`)
- **Locks & Idempotency Markers**: `/var/vf/locks/` and `var/locks/`
- **Cost Telemetry Database**: `/var/vf/cost_tracker.json`
- **Local Runs**: `runs/{run_id}/`
- **Antigravity Brain Assets**: `C:\Users\hunghd2\.gemini\antigravity\brain\browser_assets\`
