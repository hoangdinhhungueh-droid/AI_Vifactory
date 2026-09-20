# 🧪 [TEST_HARNESS_PLAN] VOX_PARALLAX_ATMOSPHERE_AND_AI_TIMELINE_EDITOR_COUNCIL

## 🎯 1. Chiến Lược Kiểm Thử (Test Strategy)
- **Phạm vi bao phủ**: Unit Tests, LLM Director Mock/Fallback, Remotion Bundler, Zero-Ghost Code Scan, ISO Invariant Parity.
- **Môi trường**: Sandbox cách ly (Rule 119) & VPS Linux Environment (Rule 126).

---

## 📊 2. Ma Trận Test Cases
| ID | Hạng Mục Kiểm Thử | Lệnh Thực Thi (Command) | Kết Quả Kỳ Vọng | Ngưỡng Timeout |
| :--- | :--- | :--- | :--- | :--- |
| **TC-01** | Python AST Compilation | `python3 -m py_compile app/services/timeline_editor_agent.py app/services/build_remotion_props.py tests/test_timeline_editor_agent.py` | 100% Passed, Exit 0 | 15s |
| **TC-02** | Unit & Fallback Suite | `pytest tests/test_timeline_editor_agent.py -v` | 7/7 Passed, Exit 0 | 30s |
| **TC-03** | Remotion Bundle Build | `cd remotion && npx remotion bundle src/index.tsx` | Zero TypeScript/React errors, Exit 0 | 60s |
| **TC-04** | 4-Layer Zero-Ghost Scan | `python3 scripts/orchestrator/ghost_code_detector.py` | 0 defects, 0 ghost artifacts, Exit 0 | 30s |
| **TC-05** | Council Runner Evaluation | `python3 scripts/orchestrator/runner.py --mode council --task-id EN_EP0260_macro_liquidity` | 4/4 Unanimous Pass | 45s |
