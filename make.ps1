<#
.SYNOPSIS
  PowerShell wrapper for Makefile targets on Windows environments.
  Usage: .\make.ps1 <target>
#>

param(
    [string]$Target = "help"
)

$PYTHON = "python"
$PYTEST = "pytest"
$RUFF = "ruff"

switch ($Target.ToLower()) {
    "help" {
        Write-Host "==========================================================================" -ForegroundColor Cyan
        Write-Host "AI VIDEO FACTORY - 1-COMMAND AUTOMATION CLI (WINDOWS POWERSHELL)" -ForegroundColor Cyan
        Write-Host "==========================================================================" -ForegroundColor Cyan
        Write-Host "  .\make.ps1 test      - Run Hermetic Unit & Contract Tests"
        Write-Host "  .\make.ps1 lint      - Check Ruff Linter & Rule 128 Anti-Bias Gate"
        Write-Host "  .\make.ps1 review    - Audit Code with Alibaba Open Code Review (OCR)"
        Write-Host "  .\make.ps1 ci        - Run ISO Neighbor Testing & Master E2E Smoke Gate"
        Write-Host "  .\make.ps1 sync      - Verify Three-Way Sync (Local - VPS - GitHub)"
        Write-Host "  .\make.ps1 deploy    - Stage, commit, push & trigger automated VPS deployment"
        Write-Host "  .\make.ps1 health    - 7-Axis System Health Check (Hardware & Services)"
        Write-Host "  .\make.ps1 report    - Generate System Metrics Report (Markdown + HTML)"
        Write-Host "  .\make.ps1 memory    - Verify Project Memory (ROADMAP.md & CHANGELOG.md)"
        Write-Host "  .\make.ps1 clean     - Safe cleanup of orchestrator temporary files (Rule 119)"
        Write-Host "  .\make.ps1 docker-up - Launch Redis & Flower background services"
        Write-Host "==========================================================================" -ForegroundColor Cyan
    }
    "test" {
        & $PYTEST -m "not integration" -v tests/
    }
    "lint" {
        & $RUFF check app/ scripts/ --exit-zero
        & $PYTEST -v tests/test_zero_semantic_bias.py
    }
    "review" {
        & $PYTHON scripts/orchestrator/runner.py --mode review
    }
    "ci" {
        & $PYTHON scripts/orchestrator/runner.py --mode ci
    }
    "sync" {
        & $PYTHON scripts/orchestrator/runner.py --mode sync
    }
    "deploy" {
        & $PYTHON scripts/orchestrator/runner.py --mode deploy
    }
    "health" {
        & $PYTHON scripts/health-check.py
    }
    "report" {
        & $PYTHON scripts/orchestrator/system_health_reporter.py
    }
    "memory" {
        & $PYTHON scripts/orchestrator/memory_governor.py --strict
    }
    "clean" {
        & $PYTHON scripts/orchestrator/runner.py --cleanup-tmp
    }
    "docker-up" {
        docker compose up -d
    }
    "docker-down" {
        docker compose down
    }
    default {
        Write-Host "Unknown target '$Target'. Run '.\make.ps1 help' for usage." -ForegroundColor Red
        exit 1
    }
}
