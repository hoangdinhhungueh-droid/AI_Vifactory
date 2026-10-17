# 🛑 HUMAN GATE ARCHITECTURE & APPROVAL CONTRACT VERIFICATION (AVF-E2E-006)

> **Audit Date**: 2026-10-17  
> **Auditor**: Worker Gemini 3.8 Flash High (Antigravity IDE) under Boss Claude Opus 5.5 Supervision  
> **Scope**: Human-in-the-Loop Governance, Telegram Notification Protocols, and Antigravity Interaction Points.

---

## 1. The Three Human Gate Hierarchy

The AI Video Factory enforces a strict 3-tiered Human Gate protocol designed to balance **100% autonomous speed** with **editorial quality control**:

```
[B1/B1.5/B2 Discovery]
        │
        ▼
   [HUMAN GATE 1]  ───> Pure Informative Broadcast on Telegram (0 buttons, Non-Blocking)
        │
        ▼
[B3 Director & Audio]
        │
        ▼
   [HUMAN GATE 2]  ───> Telegram Notification with 1-Click Antigravity Execution Block
        │               (User runs Playwright 7-Account Image Generator in Local IDE)
        ▼
[B4/B5 Local Images]
        │
        ▼
[B6-B10 VPS Render]
        │
        ▼
   [HUMAN GATE 3]  ───> YouTube Unlisted Staged + Telegram Approval Card (5 Action Buttons)
        │               (User creates Gemini Thumbnail on YouTube Studio, clicks "Public")
        ▼
 [YouTube Public]
```

---

## 2. Gate Specifications & Contracts

### Human Gate 1: Pure Informative Broadcast
- **Trigger**: Emitted after B1 Trend Hunter, B1.5 Blue Ocean Gap, and B2.1 Fact Causal Audit pass.
- **Implementation**: `app/services/trend_engine_b1.py::send_pure_telegram_gate1_notification()`
- **Interactive Buttons**: **0 buttons** (Non-blocking).
- **Behavior**: Broadcasts topic title, viral angle, competitor differentiation gap, and B2 story gate score to Telegram. The pipeline immediately auto-transitions to B3 Director Plan without waiting for human input.
- **Architectural Guard**:
  - `trend_engine_b1.py#L780`: Gate Order Integrity Guard prevents HG1 from being dispatched if B3 Director Plan or HG2 already exists for that episode.

### Human Gate 2: Image Generation Delegation
- **Trigger**: Emitted after B3.5 Prompt Forge and B3.5.1 Visual Convergence Audit (`visual_convergence_audit.json` score >= 8.0).
- **Implementation**: `app/services/telegram_buttons.py::send_gate2_card()` and `scripts/watchers/prompts_forge_watcher.py`
- **Payload**:
  - Episode ID, Scene count, BG (16:9) count, FG (1:1 Magenta) count
  - 1-Click Code block formatted for Antigravity:
    ```
    /vf-image-gen
    /run:image --episode <EPISODE_ID> --headless
    ```
- **Behavior**: The VPS workflow pauses at B3.5. The user copies the command block into Antigravity IDE. Antigravity executes Playwright browser automation across 7 Google accounts to generate images, cut out backgrounds via pure PIL chroma keying, and push assets back to VPS.
- **Timeout Policy**: Idle state. Does NOT consume VPS CPU or LLM tokens while waiting for the user.

### Human Gate 3: YouTube Release & Thumbnail Approval
- **Trigger**: Emitted after B10 uploads the rendered video to YouTube as **Unlisted** with `altered_or_synthetic_content: true`.
- **Implementation**: `app/services/telegram_buttons.py::send_gate3_card()`
- **Interactive Buttons**:
  1. `[🎨 Mở Studio (Tạo Thumbnail Gemini)]`: Deep-links to YouTube Studio edit page.
  2. `[📺 Xem trước Video (Unlisted)]`: Unlisted YouTube playback link.
  3. `[🚀 Chuyển sang Công Khai (Public)]`: Callback `pub:<video_id>` (switches privacy status to public).
  4. `[🌐 Công Khai Tất cả Video (Public All)]`: Callback `puball`.
  5. `[🔒 Giữ Không Công Khai (Unlisted)]`: Callback `kp:<video_id>`.
- **Behavior**: The video stays safely Unlisted until human approval. If human does not respond, the video remains Unlisted indefinitely (safe fail-closed).

---

## 3. Human Gate Verification Verdict

- **HG1 Broadcast**: **VERIFIED** (0 buttons, non-blocking, order-enforced).
- **HG2 Antigravity Handoff**: **VERIFIED** (Clean code block, zero API token burn, decoupled).
- **HG3 Release Gate**: **VERIFIED** (Unlisted by default, altered content flagged, 1-click publishing).
- **Overall Verdict**: **PASS (100% COMPLIANT WITH USER MANDATE)**.
