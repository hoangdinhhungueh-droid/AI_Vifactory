# ==============================================================================
# AI Video Factory — Universal 1-Command Makefile
# Reference: Class_CI-CD (GitHub Actions + Docker + VPS + PM2 + Makefile standard)
# ==============================================================================

PYTHON ?= python
PIP ?= pip
PYTEST ?= pytest
RUFF ?= ruff

.PHONY: help test lint review ci sync deploy health report memory clean docker-up docker-down

help:
	@echo "=========================================================================="
	@echo "AI VIDEO FACTORY - 1-COMMAND AUTOMATION CLI"
	@echo "=========================================================================="
	@echo "  make test      - Run Hermetic Unit & Contract Tests"
	@echo "  make lint      - Check Ruff Linter & Rule 128 Anti-Bias Gate"
	@echo "  make review    - Audit Code with Alibaba Open Code Review (OCR)"
	@echo "  make ci        - Run ISO Neighbor Testing & Master E2E Smoke Gate"
	@echo "  make sync      - Verify Three-Way Sync (Local - VPS - GitHub)"
	@echo "  make deploy    - Verify clean state, push & watch GitHub Actions CI/CD deployment"
	@echo "  make health    - 7-Axis System Health Check (Hardware & Services)"
	@echo "  make report    - Generate System Metrics Report (Markdown + HTML)"
	@echo "  make memory    - Verify Project Memory (ROADMAP.md & CHANGELOG.md)"
	@echo "  make clean     - Safe cleanup of orchestrator temporary files (Rule 119)"
	@echo "  make docker-up - Launch Redis & Flower background services"
	@echo "=========================================================================="

test:
	$(PYTEST) -m "not integration" -v tests/

lint:
	$(RUFF) check vox/ tools/ tests/vox/ app/main.py scripts/orchestrator/boss_orchestrator.py scripts/orchestrator/runner.py app/services/trend_engine_b1.py app/services/daily_market_lock.py app/services/alert_cooldown.py core/paths.py
	$(RUFF) check app/ scripts/ --exit-zero
	$(PYTEST) -v tests/test_zero_semantic_bias.py

review:
	$(PYTHON) scripts/orchestrator/runner.py --mode review

ci:
	$(PYTHON) scripts/orchestrator/runner.py --mode ci

sync:
	$(PYTHON) scripts/orchestrator/runner.py --mode sync

deploy:
	$(PYTHON) scripts/orchestrator/runner.py --mode deploy

health:
	$(PYTHON) scripts/health-check.py

report:
	$(PYTHON) scripts/orchestrator/system_health_reporter.py

memory:
	$(PYTHON) scripts/orchestrator/memory_governor.py --strict

clean:
	$(PYTHON) scripts/orchestrator/runner.py --cleanup-tmp

docker-up:
	docker compose up -d

docker-down:
	docker compose down
