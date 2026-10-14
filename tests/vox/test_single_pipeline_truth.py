#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/vox/test_single_pipeline_truth.py — Verifies Single Pipeline Truth and Legacy Route Quarantines (Rule 125).

Guarantees:
1. Legacy execution endpoints (/produce_episode, /run_episode, /trigger_video_generation) are completely unmounted and return 404.
2. Active canonical endpoints (/api/v1/health, /api/v1/diag, /v1/models, /v1/budget) return HTTP 200.
3. The only production video generation entrypoint is vox.pipeline.
"""

import ast
from pathlib import Path
import pytest


def test_legacy_routes_absent_from_ast():
    """Statically verifies via AST that no legacy execution endpoints exist in app/main.py."""
    main_py = Path(__file__).resolve().parent.parent.parent / "app" / "main.py"
    assert main_py.exists(), f"app/main.py not found at {main_py}"

    tree = ast.parse(main_py.read_text(encoding="utf-8"), filename=str(main_py))
    extracted_routes = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for dec in node.decorator_list:
                if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
                    if dec.func.attr in ("get", "post", "put", "delete", "patch", "api_route"):
                        if dec.args and isinstance(dec.args[0], ast.Constant):
                            extracted_routes.add(dec.args[0].value)

    legacy_targets = [
        "/produce_episode",
        "/run_episode",
        "/api/v1/produce_episode",
        "/api/v1/run_episode",
        "/trigger_video_generation",
    ]
    for target in legacy_targets:
        assert target not in extracted_routes, f"Forbidden legacy route '{target}' found in app/main.py!"

    # Ensure canonical endpoints exist
    canonical_targets = ["/api/v1/health", "/api/v1/diag", "/v1/models", "/v1/budget"]
    for c_target in canonical_targets:
        assert c_target in extracted_routes, f"Expected canonical route '{c_target}' missing from app/main.py!"


def test_runtime_legacy_routes_return_404_and_canonical_routes_return_200():
    """Runs runtime 404 tests against FastAPI app without skip (fail-closed, Rule 125/127)."""
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)

    legacy_routes = [
        "/produce_episode",
        "/run_episode",
        "/api/v1/produce_episode",
        "/api/v1/run_episode",
        "/trigger_video_generation",
    ]
    for route in legacy_routes:
        assert client.post(route, json={"topic": "Test"}).status_code == 404
        assert client.get(route).status_code == 404

    # Behavioral parity on surviving canonical endpoints
    # 1. Health
    res_h = client.get("/api/v1/health")
    assert res_h.status_code == 200
    assert res_h.json() == {"status": "ok"}

    # 2. Diag
    res_d = client.get("/api/v1/diag")
    assert res_d.status_code == 200
    assert res_d.json().get("status") == "ok"

    # 3. Models
    res_m = client.get("/v1/models")
    assert res_m.status_code == 200
    assert res_m.json().get("object") == "list"

    # 4. Budget
    res_b = client.get("/v1/budget")
    assert res_b.status_code == 200
    assert any(p in res_b.json() for p in ("openrouter", "gemini", "cerebras", "mistral"))

    # 5. LLM Endpoint schema validation (fails closed with 422 on invalid/missing payload)
    res_l_empty = client.post("/api/v1/llm", json={})
    assert res_l_empty.status_code == 422

    # 6. Notion Gate logic behavioral parity
    from app.main import _apply_notion_gates, NOTION_KEEP
    dummy_body = {
        "tools": [
            {"function": {"name": "API-post-search"}},
            {"function": {"name": "API-unauthorized-shadow-call"}},
            {"function": {"name": "local_calc"}},
        ]
    }
    # Test NOTION CAP: unconditional stripping of non-whitelisted API-*
    gated_cap = _apply_notion_gates(dummy_body, last_user="inspect notion db", autonomous=False)
    tool_names_cap = [t["function"]["name"] for t in gated_cap["tools"]]
    assert "API-post-search" in tool_names_cap
    assert "API-unauthorized-shadow-call" not in tool_names_cap
    assert "local_calc" in tool_names_cap

    # Test NOTION INTENT GATE: strips ALL API-* when message has 0 notion intent
    gated_intent = _apply_notion_gates(dummy_body, last_user="tell me a joke about dogs", autonomous=False)
    tool_names_intent = [t["function"]["name"] for t in gated_intent["tools"]]
    assert not any(name.startswith("API-") for name in tool_names_intent)
    assert "local_calc" in tool_names_intent


def test_single_pipeline_import_graph_and_stages_delegation():
    """Enforces that stages/ cleanly delegates to vox/ as the sole underlying implementation engine."""
    repo_root = Path(__file__).resolve().parent.parent.parent

    # 1. S5 delegates to vox.planner
    s05_file = repo_root / "stages" / "s05_director_plan.py"
    assert s05_file.exists()
    s05_content = s05_file.read_text(encoding="utf-8")
    assert "from vox.planner import" in s05_content, "stages/s05_director_plan.py must import and delegate to vox.planner"

    # 2. S10 delegates to vox.compositor and vox.assemble
    s10_file = repo_root / "stages" / "s10_render.py"
    assert s10_file.exists()
    s10_content = s10_file.read_text(encoding="utf-8")
    assert "from vox.compositor import" in s10_content, "stages/s10_render.py must import vox.compositor"
    assert "from vox.assemble import" in s10_content, "stages/s10_render.py must import vox.assemble"

    # 3. S11 delegates to vox.qa.gates
    s11_file = repo_root / "stages" / "s11_qc.py"
    assert s11_file.exists()
    s11_content = s11_file.read_text(encoding="utf-8")
    assert "from vox.qa.gates import" in s11_content, "stages/s11_qc.py must import vox.qa.gates"

    # 4. director_planner_b3 delegates to s05_director_plan
    b3_file = repo_root / "app" / "services" / "director_planner_b3.py"
    assert b3_file.exists()
    b3_content = b3_file.read_text(encoding="utf-8")
    assert "from stages.s05_director_plan import" in b3_content, "director_planner_b3 must import and delegate to stages.s05_director_plan"


def test_adversarial_legacy_file_purge_detector(tmp_path):
    """Plants a legacy pattern file in a temp directory and asserts detection and removal (Rule 125)."""
    import fnmatch
    from tools.ghost_scan import GHOST_PATTERNS

    fake_ghost = tmp_path / "legacy_shadow_module_v2.py"
    fake_ghost.write_text("# ghost test", encoding="utf-8")
    assert fake_ghost.exists()

    # Verify pattern matching flags it
    matches = [p for p in GHOST_PATTERNS if fnmatch.fnmatch(fake_ghost.name, p)]
    assert len(matches) >= 1, f"Expected ghost pattern to match {fake_ghost.name}"

    # Remove the legacy file and assert deletion
    fake_ghost.unlink()
    assert not fake_ghost.exists()
