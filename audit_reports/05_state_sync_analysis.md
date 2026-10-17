# 🌐 STATE SYNCHRONIZATION AUDIT: VPS ↔ LOCAL ↔ GIT (AVF-E2E-005)

> **Audit Date**: 2026-10-17  
> **Auditor**: Worker Gemini 3.8 Flash High (Antigravity IDE) under Boss Claude Opus 5.5 Supervision  
> **Scope**: Three-Way Physical Parity (Rule 126), Race Conditions, File Locking, and Concurrent Modification Isolation.

---

## 1. Git Repository Parity Verification

Live probe executed via `git status` locally and via `vps_runner.py` on VPS:
- **Local Branch**: `main` tracked with `origin/main` at commit `d6a6e00`
- **VPS Branch**: `/root/video_factory` on `main` at commit `d6a6e00`
- **Git Status**: Working tree clean across both environments.
- **Verdict**: **100% BIT-FOR-BIT SYNCHRONIZED**.

---

## 2. Multi-Location Architecture & Partitioning

The AI Video Factory uses a **partitioned workload model** rather than simultaneous distributed writes:

1. **VPS Responsibilities (Automated 24/7 Engine)**:
   - Topic discovery & research (B1, B1.5)
   - Narrative script & Audio TTS (B2, B2.6)
   - Director planning & Prompt packaging (B3, B3.5)
   - Master video rendering, LUFS audio normalization & chapter extraction (B7, B9)
   - YouTube staging upload & Unlisted publishing (B10)
   - 48h Post-mortem analytics dreaming (B11)
   - *State Directory*: `/var/vf/episodes/{episode_id}/`

2. **Antigravity Responsibilities (Local IDE & Human Gatekeeper)**:
   - Code engineering, refactoring, and test execution (Rule 127)
   - Multi-Account Image Generation (B4, B5 via Playwright in `stitch_designer_pool.py`)
   - Chroma keying & Visual Audit Gate 2
   - Image asset upload to VPS `/var/vf/episodes/{episode_id}/images/`
   - *State Directory*: `runs/{run_id}/` or `workspace/{episode_id}/`

---

## 3. Concurrency & Conflict Analysis

### Scenario A: Simultaneous Modification of `brain_input.json`
- **Risk**: VPS runs B3 Director Plan while Local Antigravity updates `brain_input.json`.
- **Mitigation in Code**:
  In `scripts/run_vox_automated_pipeline.py` (Line 572-631), atomic multi-location sync writes to `/var/vf/episodes/{id}/brain_input.json` and copies to `/root/video_factory/episodes/{id}/` using `json.dumps` with overwrite semantics.
  Crucially, B3 runs strictly **BEFORE** Human Gate 2. Local Antigravity does NOT touch `brain_input.json` until AFTER HG2 is triggered.
- **Race Condition Risk**: **LOW**. The pipeline enforces chronological separation.

### Scenario B: Concurrent Execution of Daily Trend Hunter
- **Risk**: Cron triggers `run_trend_pipeline.py` while a manual run or subagent is already processing a market.
- **Mitigation in Code**:
  In `app/services/daily_market_lock.py` and `trend_engine_b1.py` (Line 1109-1123):
  Uses atomic lock files `/var/locks/b1_daily_lock/{market}.lock` with PID tracking, TTL validation, and mutex serialization.
  If an active lock is held by a live PID, any concurrent runner safely aborts with code 0 without corrupting state.
- **Race Condition Risk**: **RESOLVED & PROTECTED**.

### Scenario C: Multiple Triggers of Image Ready Watcher
- **Risk**: `images_ready.json` triggers multiple parallel renders in `continue_after_images.py`.
- **Mitigation in Code**:
  In `scripts/watchers/image_ready_watcher.py`:
  1. Checks `self._is_completed(task_id)` (`hg3_dispatched.json` marker).
  2. Checks `self._is_process_running(task_id)` via `pgrep -f {task_id}`.
  3. Uses checkpoint file `/var/vf/image_ready_watcher_state.json` to deduplicate events.
- **Race Condition Risk**: **RESOLVED & PROTECTED**.

---

## 4. Conflict Resolution Recommendations

1. **Strict Staging Direction**: Maintain the one-way asset transfer flow:
   `VPS (B1-B3.5)` ➔ `Telegram HG2 Card` ➔ `Antigravity Local (B4-B5 Images)` ➔ `VPS (images_ready.json ➔ B6-B10)`.
2. **Atomic Manifest Writes**: In `core/gates.py#L96`, always write to `.tmp` files first, then execute `os.replace` (atomic file replacement) to prevent reading half-written JSON files during rapid inotify events.
