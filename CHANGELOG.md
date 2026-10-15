# 📝 CHANGELOG — AI VIDEO FACTORY

All notable changes to the AI Video Factory project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- **Vox Director Autonomous Engine (`AVF-VOX-001`)**: Tích hợp pipeline làm video phong cách Vox/Fern tactile paper-collage với living poster animation và dynamic counter tickers.
- **Single Unified Vox Pipeline with Tactile Object Decomposition (`AVF-VOX-001`)**: Hoàn thiện pipeline phong cách Vox/Fern đơn nhất (`vox/`), phân rã đối tượng foreground/background từng scene, tích hợp two-pass EBU R128 loudnorm (-16.0 LUFS, TP <= -2.0 dBTP to absorb AAC overshoot per AES TD1004), word-level Whisper alignment (parity drift <= 33.3ms), dynamic 2.5D multiplane camera compositing, và QA Gates xác thực video CFR 30fps H.264/AAC.
- **Hermetic Pipeline Smoketests & Non-Vacuous Cross-Market Neighbor Testing**: Bổ sung dry-run sink cho Gate 15 Notion insights, kiểm thử đối kháng đa thị trường JP vs EN 100% disjoint.
- **Automated Ruff Linter Baseline & Strict Zero-Error Enforcement**: Cấu hình ruff linting trên `vox/` và `tools/` với 0 cảnh báo.
- **CI/CD Pipeline with Conditional VPS CD Template (`.github/workflows/ci.yml`)**: Bổ sung Job 2 deploy lên Hetzner VPS thông qua SSH (tự động kích hoạt khi cấu hình VPS_HOST/VPS_SSH_KEY repository secrets, an toàn bỏ qua với cảnh báo khi chưa nạp secrets; tích hợp cơ chế snapshot rollback an toàn, py_compile, docker compose restart và post-deployment health check).
- **1-Command Makefile & PowerShell Suite (`Makefile`, `make.ps1`)**: Chuẩn hóa toàn bộ tác vụ của dự án (`make test`, `make lint`, `make review`, `make ci`, `make sync`, `make deploy`, `make health`, `make report`, `make memory`, `make clean`).
- **Antigravity Memory Governance (`ROADMAP.md`, `CHANGELOG.md`, `scripts/orchestrator/memory_governor.py`)**: Thiết lập bộ nhớ dự án dài hạn chống mất ngữ cảnh khi agent bị compaction (học hỏi từ bài học 6 bước Vibe Coding).
- **Custom Commands Suite Upgrades (`vf-pipeline-teamwork`)**: Mở rộng Chat UI subcommands `/vf-pipeline-teamwork deploy`, `health`, `report`, `memory` và vai trò số 7 (Vibe Memory & CD Gatekeeper).
- **Safe Vibe-to-Code Engine Upgrades (`antigravity-code-review`)**: Tích hợp quy trình 8 bước Vibe-to-Code kèm chốt chặn Memory Anchoring & One-Command Readiness.
- **Vibe Coding Spec Templates (`specs/business_flow_template.md` & `specs/design_spec_template.md`)**: Cung cấp bản vẽ chuẩn cho mọi module trước khi viết mã nguồn.
- **SDLC Enterprise Reporter Upgrade (`sdlc-enterprise-reporter`)**: Nâng cấp toàn diện 14 giai đoạn với kiến trúc CI/CD 2-Job, Deploy 1-lệnh (`make deploy`), Health check 7 trục, Interactive HTML Dashboard, và Memory Governance chống Amnesia (`ROADMAP.md` & `CHANGELOG.md`).

### Changed
- **Orchestrator Runner (`scripts/orchestrator/runner.py`)**: Hỗ trợ 4 mode vận hành mới: `--mode health`, `--mode report`, `--mode memory`, `--mode deploy`, mở rộng khả năng gọi composable capabilities.

---

## [1.2.1] - 2026-10-13 (Commit a6bda51)
### Added
- **Comprehensive System Health Reporter (`scripts/orchestrator/system_health_reporter.py`)**: Thu thập chỉ số phần cứng (CPU, RAM, Swap, Disk), dịch vụ (PostgreSQL, Redis, Celery), Remotion và AI Quotas; xuất báo kép (Markdown + Interactive HTML Dashboard).

### Changed
- **Health Check Engine (`scripts/health-check.py`)**: Nâng cấp từ kiểm tra đơn sơ (3 lệnh) lên kiểm toán 7 trục toàn diện, bao gồm cả tài nguyên bộ nhớ, trạng thái container và kiểm tra độ sạch mã nguồn (Rule 125).

---

## [1.2.0] - 2026-10-06
### Added
- **Automated Human Gate 2 Dispatch**: Cơ chế duyệt kịch bản và đạo diễn tự động qua Telegram Interactive Buttons.
- **Opus 5.5 Anti-Bloat Supervisory Gate**: Giám sát giới hạn token ($\le 10,000$ in / $\le 5,000$ out) cho các tác vụ lập kế hoạch và review hội đồng.

### Fixed
- **Rule 136 Speaker Tag Leak**: Khử hoàn toàn việc rò rỉ mã asset, layer, extension `.png` lên phụ đề Remotion.
- **Rule 135 Timeline Synchronization**: Chuẩn hóa YouTube chapters lấy trực tiếp từ `remotion_props.json` thay vì tính ước lượng.

---

## [1.1.0] - 2026-09-15
### Added
- **Four-Role Council Deliberation (`runner.py --mode council`)**: Hội đồng 4 Agent (Architect, Builder, QA Test Harness, Adversarial Auditor) kiểm định đồng thuận 4/4 trước khi nghiệm thu.
- **Alibaba Open Code Review (OCR)**: Tích hợp cổng kiểm toán AST tĩnh và rà soát diff tự động trước khi commit.
- **Automated 4-Layer Ghost Code Hunter (`tools/ghost_scan.py`)**: Quét đĩa cứng vật lý loại bỏ toàn bộ file rác `.bak*`, orphan scripts và bypass code.

---

## [1.0.0] - 2026-08-01
### Added
- **AI Video Factory Baseline Release**: Hoàn thiện toàn bộ pipeline từ B1 đến B11 cho 4 thị trường (EN, JP, KR, VN).
- **18 Kỷ Luật Thép Antigravity (AGENTS.md)**: Khởi tạo quy chuẩn tối thượng bảo vệ mã nguồn, cấm số liệu giả (Rule 118) và bảo vệ an toàn ổ đĩa (Rule 137).
