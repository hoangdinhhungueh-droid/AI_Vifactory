# 🗺️ AI VIDEO FACTORY — PROJECT ROADMAP & STATE ARCHITECTURE

> **Single Source of Truth (SoT) cho lộ trình kỹ thuật và trạng thái tính năng của AI Video Factory.**  
> *Áp dụng quy chuẩn Vibe Coding 6 Bước (Plan -> Design -> Code -> Test -> Deploy -> Maintain & Memory).*  
> *Cập nhật bắt buộc sau mỗi Sprint / Tính năng để bảo toàn bộ nhớ dài hạn, chống mất context và "đập đi code lại".*

---

## 🏛️ TỔNG QUAN KIẾN TRÚC 6 PHA (CANONICAL PHASES)

```
[Phase 1: Hạ Tầng Cốt Lõi & Khế Ước Bất Biến]
       ↓
[Phase 2: Content Engine — B1..B2.5 (Nghiên cứu xu hướng & Kịch bản 5 Beat)]
       ↓
[Phase 3: Audio & Director — B2.6..B3.5 (Audio Spine, Timecode Karaoke & Prompt Forge)]
       ↓
[Phase 4: Visual Engine — B4..B5 (Sinh ảnh Gemini Pro Web & Audit Thị giác 4 Trục)]
       ↓
[Phase 5: Render & Phân Phối — B6..B10 (Remotion Engine, Dynamic Ducking & Auto SEO Upload)]
       ↓
[Phase 6: Trí Tuệ & Phản Hồi — B11 (Analytics 48h & Dreaming Feedback Loop)]
```

---

## 📍 TRẠNG THÁI CHI TIẾT TỪNG PHA

### Phase 1: Hạ Tầng Cốt Lõi, Khế Ước Bất Biến & Vận Hành (Foundation & Invariants)
- [x] **18 Kỷ Luật Thép Antigravity (AGENTS.md)**: Rule 118 (Zero-Mock), Rule 119 (Existing Codebase), Rule 121 (Verification), Rule 122 (Visual Audit), Rule 124 (Atomic Commit), Rule 125 (Zero Ghost Code), Rule 126 (Three-Way Sync), Rule 127 (Programmatic Runtime), Rule 128 (Generic Contract), Rule 137 (Zero-Drive-Wipe).
- [x] **Hạ tầng Multi-Agent Orchestrator (`scripts/orchestrator/runner.py`)**: Council deliberation, Lifecycle Manager, Resource Sandbox (`/tmp/` isolation), Ghost Code Hunter.
- [x] **Open Code Review (OCR) Engine**: Tích hợp Alibaba OCR (`ocr review`, `ocr delegate`) cho kiểm toán AST tự động.
- [x] **Pre-Push Blast Guard (`scripts/orchestrator/runner.py`)**: Ngăn chặn rò rỉ kiến trúc và refactor diện rộng > 25% blast radius (Pillar 1 Gate).
- [x] **Hệ thống CI/CD & Deploy 1-Lệnh (`Makefile` + GitHub Actions)**: Tự động hóa kiểm thử, build và deploy an toàn lên Hetzner VPS.

---

### Phase 2: Content Engine — Nghiên Cứu Xu Hướng & Kịch Bản (B1..B2.5)
- [x] **B1 Trend Reconnaissance (`app/services/trend_recon_b1.py`)**: Google Trends RSS live, đa thị trường (EN, JP, KR, VN), khử synthetic seeds.
- [x] **B1.5 YouTube Competitor Intel (`app/services/youtube_recon_b15.py`)**: Bóc tách retention hooks, CTR insights từ đối thủ cùng ngách.
- [x] **B2 Kịch Bản 5 Beat Docudrama (`app/services/story_engine_b2.py`)**: Cold Strike (0-20s) -> Paradox (20-60s) -> False Narrative -> Forensic Trail -> Smoking Gun -> Modern Mirror.
- [x] **Rule 130 Factual Causal Integrity**: Cấm giật gân vô căn cứ; phân định rạch ròi Causal Level 1 (Catalyst) vs Level 2 (Transmission Mechanism).
- [x] **Rule 132 Decoupled Engine**: Prompt kịch bản tách rời hoàn toàn khỏi mã nguồn Python, nạp động từ Notion SoT / `config/prompts/`.

---

### Phase 3: Audio & Đạo Diễn Hình Ảnh (B2.6..B3.5)
- [x] **B2.6 Hollywood Audio Spine (`app/services/beat_tts_engine.py`)**: Microsoft Edge-TTS đa ngôn ngữ, sync audio word-level chính xác đến millisecond.
- [x] **B3 Dynamic Director Plan (`app/services/director_planner_b3.py`)**: Khóa timecode từng phân cảnh theo beat audio; phân chia Layer 1 Background (16:9) và Layer 2 Foreground (1:1).
- [x] **B3.5 Prompt Forge (`app/services/prompt_forge_b35.py`)**: Chuyển hóa kịch bản thành prompt tiếng Anh chuẩn Graphic Novel Editorial Illustration, chống lặp hành động nhân vật.

---

### Phase 4: Visual Engine & Tách Nền Thị Giác (B4..B5)
- [x] **B4 Gemini Pro Web Image Generation (`scripts/gemini_browser_gen.py`)**: Playwright tự động hóa sinh ảnh chất lượng cao 100% PNG, watchdog chống treo.
- [x] **B5 Chroma HSV Keying (`scripts/remove_bg_chromakey.py`)**: Tách nền tiền cảnh tự động, khử viền magenta, bảo toàn độ mượt alpha.
- [x] **B5 4-Axis Visual Audit Gate (`scripts/auto_b5_audit.py`)**: Kiểm toán thị giác 4 trục (UI/Artifact 0%, Alpha integrity 100%, Style Graphic Novel 100%, Era/Ethnic context).

---

### Phase 5: Render Video (Sole Canonical Engine: Vox Tactile Compositor) & Phân Phối (B6..B10)
- [x] **Sole Canonical Render Engine: Vox Tactile Compositor (`vox/assemble.py`, `vox/compositor.py`)**: Native Python/FFmpeg multi-layer compositor with two-pass EBU R128 (-16.0 LUFS, TP <= -2.0 dBTP), sub-frame A/V drift (< 1 frame), and ASS word-level karaoke burn-in. Single pipeline truth (Rule 125).
- [x] **Auxiliary Post-Production Toolkit: Remotion Motion Suite (`remotion/`)**: Decoupled non-pipeline auxiliary toolkit for standalone kinetic typography & title generation; not an alternate pipeline render path.
- [x] **Chapter Synchronization SoT (Rule 135)**: Trích xuất mốc chapter trực tiếp và duy nhất từ `manifest.json` (`scenes[i].start` và `scenes[i].end`) dựa trên timeline thực tế đã render của vox.assemble (Rule 125 Single Truth).
- [x] **B8 BGM Cinematic Ducking (`app/services/beat_bgm_engine.py`)**: Tự động dìm nhạc nền khi có voiceover và đẩy cao trào tại các beat chuyển đoạn.
- [x] **B10 YouTube Auto SEO & Gate 2 (`scripts/execute_b10_auto_seo_upload_gate2.py`)**: Đồng bộ chapters chuẩn timeline thực tế, gắn cờ Synthetic Media.
- [x] **Rule 136 Pure Beat Header**: Chống rò rỉ mã asset/hash/layer lên tiêu đề phụ đề Remotion/ASS.

---

### Phase 6: Trí Tuệ Sau Phát Hành & Vòng Lặp Phản Hồi (B11)
- [x] **B11 YouTube Analytics 48h (`scripts/b11_engine.py`)**: Thu thập chỉ số giữ chân người xem (Retention/AVD), CTR, điểm rơi bỏ xem (drop-off points).
- [x] **Feedback Dreaming Loop (`scripts/daily_knowledge_dreaming_sync.py`)**: Đúc kết bài học thực tế, cập nhật tự động vào Notion Memory Vault và prompt kịch bản B2.

---

## 🧩 ARCHITECTURAL SCOPE & CROSS-CUTTING FOUNDATION JUSTIFICATION

1. **Code Map GPS & AST Toolkit (`tools/codemap/`, TASK-CODEMAP-001)**:
   - *Rationale*: Enforces Rule 138 (Blast Radius Analysis & Pre-Impact Graph Check). Required during AVF-VOX-001 to programmatically verify that deleting legacy `app/pipeline/` and deprecated routes left exactly 0 orphan callers across all 11 stages.
2. **Trend Engine Candidate Bounds (`app/services/trend_engine_b1.py`, TASK-TREND-001)**:
   - *Rationale*: Enforces Rule 118 (Zero-Mock Data) & Rule 130 (Factual Causal Integrity). Provides strictly capped, verified non-fiction topics to prevent pipeline starvation or fallback to mock data.
3. **Memory Governance & 1-Command Suite (`Makefile`, `make.ps1`, `scripts/orchestrator/memory_governor.py`, TASK-INFRA-001)**:
   - *Rationale*: Enforces Rule 124 (Atomic Code-ification) & Rule 126 (Three-Way Physical Sync). Guarantees reproducible, one-command verification across environments and preserves architecture state against context compaction amnesia.
4. **Canonical Continuous Deployment (CD) Architecture (Rule 126)**:
   - *Architecture*: Manual `runner.py --mode sync` / `scripts/vps_runner.py` (FastVPSClient with Cloudflare Access tunnel tokens) is the authoritative, canonical CD deployment path for AI Video Factory to Hetzner VPS (`/root/video_factory`), maintaining 100% bit-for-bit physical SHA-256 tree parity before any stage execution. Direct GitHub Actions SSH push is staged for Milestone M1 pending dedicated VPS secret key provisioning.
5. **Daily Market Lock Quota & Operator Force Override (`app/services/daily_market_lock.py`, TASK_1792069373)**:
   - *Rationale*: Enforces Rule 118 (Zero-Mock Data) & Rule 126 (Three-Way Physical Parity). Prevents duplicate episode production and unconstrained LLM token burning by enforcing exactly-one successful episode per market per calendar day (UTC/VN timezone).
   - *Operator Override Runbook*: When an episode run encounters an unrecoverable downstream error (e.g. B3 runtime error, network timeout) after stamping `EXHAUSTED_TODAY` or `IN_PROGRESS`, operators can safely force an immediate re-run using either:
     1. CLI Flag: `python3 scripts/run_trend_pipeline.py --market <MKT> --force`
     2. Environment Variable: `B1_FORCE_CRAWL=1 python3 scripts/run_trend_pipeline.py --market <MKT>`
   - Both mechanisms atomically bypass existing daily lock files, safely clear stale states, and initiate a fresh live trend candidate evaluation loop while preserving audit logging.
   - *5.1 Partial Scan Behavior (< MAX_SCAN_CANDIDATES) vs Full Scan Quota Exhaustion (Boss Round 11 Item 16 & Round 18)*:
     * **Partial Scan (< 10 candidates)**: When an exploratory or testing crawl runs with `max_scan_candidates < MAX_SCAN_CANDIDATES_DEFAULT` (10) and finishes without topic production, the uncommitted lock is intentionally RELEASED via `release_lock()` without stamping `EXHAUSTED_TODAY`. This preserves the daily cron quota for subsequent scheduled runs so the market is not prematurely locked out. `is_market_done_today()` remains `False`.
     * **Full Scan (>= 10 candidates)**: When a canonical crawl exhausts the full candidate quota (`scan_count >= 10`) without any candidate passing the viability gate, `mark_exhausted_today()` atomically stamps `EXHAUSTED_TODAY` with `reason="no_candidates_passed_viability"`. This terminates the editorial day for that market and protects LLM token budget. `is_market_done_today()` returns `True`.
6. **Editorial Schedule & MIN_PRODUCTION_HOUR_VN=6 Policy (Boss Round 15 Item 10)**:
   - *Rationale*: 06:00 AM Asia/Ho_Chi_Minh (UTC+7 / 23:00 UTC previous day) marks the official opening of the Vietnam editorial day. Automated morning crawlers execute from 06:00 AM onwards when Asian financial markets open and US/EU late evening digests are complete. Overnight hours (00:00 - 05:59 VN) are gated to prevent unmonitored quota burn, bypassable with `--force` or `B1_FORCE_CRAWL=1`.
7. **Windows NTFS `msvcrt.locking` 1-Byte Lock Semantics (Boss Round 15 Item 9)**:
   - *Rationale*: In `alert_cooldown.py` (and `resource_recycler.py`), cross-process locking on Windows uses `msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)` on byte 0 of the canonical `.lock` file. Because all cooperating processes target offset 0 on the same file descriptor, this delivers deterministic kernel-level mutual exclusion identical to POSIX `fcntl.flock(LOCK_EX | LOCK_NB)`. If a process terminates or crashes, the Windows kernel releases the lock entry immediately.
8. **Strict Zero-Buffer AST Ratchet Policy (Boss Round 15 Item 6)**:
   - *Rationale*: Enforces Rule 139 (Disciplined Code-ification & Zero-Symptom Patching). Removed the +10 buffer in CI and `probe_ast_ratchet_gate.py`. The legacy defect count is strictly bounded (`entries <= 221 <= 227 max_allowed`), guaranteeing monotonic decrease with zero backdoor growth.
9. **Windows CI Test Matrix Justification (Boss Round 15 Item 8)**:
   - *Rationale*: The 91 tests executed in `windows-lock-tests` cover all platform-divergent system calls (file locks, NTFS paths, atomic file replacement, network IPv4). The remaining 214 tests were adversarially audited and proven to contain 0 subprocess calls, 0 file locks, and 0 platform-divergent syscalls (pure in-memory AST visitors, schema assertions, and pure Python arithmetic).

---

## 🎯 CÁC MỤC TIÊU TIẾP THEO (NEXT MILESTONES)
- [ ] **M1**: Tích hợp Docker containerization hoàn chỉnh cho Remotion render engine trên VPS nhằm cô lập 100% môi trường Chrome/NodeJS.
- [ ] **M2**: Dashboard giám sát hệ thống thời gian thực (Real-time WebSocket Health Monitor) trên Flower/FastAPI.
- [ ] **M3**: Mở rộng hỗ trợ tự động hóa đa kênh (TikTok, Facebook Reels, YouTube Shorts) bằng cơ chế Dynamic Aspect Ratio 9:16.

