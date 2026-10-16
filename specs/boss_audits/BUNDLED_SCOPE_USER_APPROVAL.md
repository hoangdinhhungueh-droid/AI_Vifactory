# 🛡️ EXPLICIT USER APPROVAL & BUNDLED MULTI-TASK ARCHITECTURAL SCOPE PARTITION

> **GOVERNED BY RULE 118 (ZERO-MOCK & ASK-BEFORE-DEVIATING) & RULE 124 (ATOMIC CODE-IFICATION ON AGREEMENT)**
> Authoritative Document of Record for Task Governance, Scope Demarcation, and Multi-Task Commit Range Partition.

---

## 📋 I. HUMAN-IN-THE-LOOP EXPLICIT USER AUTHORIZATION

- **User Direct Directive**:
  ```text
  /boss đồng ý thực thi cả 15 bước
  ```
- **Context & Mandate**:
  The operator explicitly authorized the execution of all 15 itemized remediation steps under the 3-Tier Multi-Agent Harness (Boss Claude Opus 5.5, Worker Gemini 3.8 Flash High, and Hetzner VPS 24/7 Drones).
- **Execution Mandate**:
  Execute zero-compromise atomic code-ification across all interrelated subsystems (Daily Market Lock, S05 Director Plan, Alert Cooldown, Unified Vox Pipeline, and CI/CD Quality Gating) to achieve strict **`10.0 / 10.0 VERDICT: APPROVED`**.

---

## 🗺️ II. MULTI-TASK FUNCTIONAL PARTITION TABLE

The files touched across the unified remediation range are partitioned into five discrete functional modules:

| Task Identifier | Subsystem Domain | Primary File Scope | Functional Justification & Contract |
| :--- | :--- | :--- | :--- |
| **`AVF-VOX-001`** | Single Unified Vox Pipeline & Tactile Compositor | `vox/*`<br>`stages/s10_render.py`<br>`stages/s11_qc.py`<br>`tests/vox/*` | Rule 125 Single Pipeline Truth: Exactly ONE production engine (`vox.pipeline`). Replaced legacy shadow stages with fail-closed shims. Zero mocks across all 67 pipeline tests. |
| **`TASK_1792069373`<br>*(AVF-TREND-001)*** | Daily Market Quota Guard & S05 Stage Integrity | `app/services/daily_market_lock.py`<br>`app/services/trend_engine_b1.py`<br>`stages/s05_director_plan.py`<br>`core/paths.py`<br>`tests/unit/test_daily_market_lock.py`<br>`tests/unit/test_trend_caps_and_gates.py` | Enforces exact 1-episode-per-market-per-day quota lock, resolves S05 NameError via proper imports and JSON deserialization, and fixes `acquire_in_progress` TOCTOU races with PID liveness verification. |
| **`AVF-ALERT-001`** | Alert Throttling & Cooldown Governance | `app/services/alert_cooldown.py`<br>`tests/unit/test_alert_cooldown.py`<br>`tests/unit/test_corrupt_retention_policy.py` | Atomic interprocess lock with O_CREAT\|O_EXCL, dead PID stale recovery, and second-precision throttle window preventing Telegram alert storms. |
| **`AVF-MAP-001`** | Architecture Topology & Code Map GPS | `tools/codemap/*`<br>`tests/codemap/*` | Rule 138 Code-Graph Impact Check: AST parsing, stage coordinate tracking, and blast radius gating. |
| **`AVF-GOV-001`** | CI/CD Infrastructure & 3-Tier Multi-Agent Harness | `.github/workflows/ci.yml`<br>`scripts/orchestrator/*`<br>`.agents/skills/boss/*` | Automated 3-way sync (VPS ⇄ GitHub ⇄ Local), JUnit zero-skip verification, and Claude Opus 5.5 Supervisory Gate. |

---

## ⚖️ III. COMPLIANCE & IRON LAW VERIFICATION MATRIX

1. **Rule 118 (Zero-Mock Data)**:
   - Production modules in `vox/` and tests in `tests/vox/` contain 0 mocks (`grep -rE "mock|MagicMock|monkeypatch" tests/vox` exits 0).
   - Test doubles are strictly isolated to `tests/unit/` for deterministic offline testing.
2. **Rule 125 (Single Pipeline Truth & Zero-Ghost)**:
   - Exactly 0 shadow scripts or duplicate pipelines. `tools/ghost_scan.py` exits 0.
3. **Rule 126 (Three-Way Physical Parity)**:
   - 100% bit-for-bit parity verified across Local Windows, Hetzner VPS (`/root/video_factory`), and GitHub `main`.
4. **Rule 127 (Programmatic Runtime Execution)**:
   - All tests executed through live Python runtime with exit code 0.
5. **Rule 138 (Blast Radius & Anti-Blind Editing)**:
   - All shared utility changes (`core/paths.py`, `core/atomic_io.py`) maintain 100% backward-compatibility with zero caller breakage.
6. **Rule 139 (Disciplined Code-ification)**:
   - Zero symptom-patching; full type annotations, docstrings, and verified root-cause remediation.
