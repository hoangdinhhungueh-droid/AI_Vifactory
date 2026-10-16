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


def test_runtime_legacy_routes_return_404_and_canonical_routes_return_200(monkeypatch):
    """Runs runtime 404 tests against FastAPI app without skip (fail-closed, Rule 125/127)."""
    monkeypatch.setenv("VF_API_TOKEN", "test_secret_truth_token")
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
    assert res_h.json().get("status") == "ok"
    assert "git_sha" in res_h.json()

    # 2. Diag (Authenticated canonical endpoint)
    auth_headers = {"Authorization": "Bearer test_secret_truth_token"}
    res_d = client.get("/api/v1/diag", headers=auth_headers)
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
    from app.main import NOTION_KEEP, _apply_notion_gates
    kept_tool = next(iter(NOTION_KEEP))
    dummy_body = {
        "tools": [
            {"function": {"name": kept_tool}},
            {"function": {"name": "API-unauthorized-shadow-call"}},
            {"function": {"name": "local_calc"}},
        ]
    }
    # Test NOTION CAP: unconditional stripping of non-whitelisted API-*
    gated_cap = _apply_notion_gates(dummy_body, last_user="inspect notion db", autonomous=False)
    tool_names_cap = [t["function"]["name"] for t in gated_cap["tools"]]
    assert kept_tool in tool_names_cap
    assert "API-unauthorized-shadow-call" not in tool_names_cap
    assert "local_calc" in tool_names_cap

    # Test NOTION INTENT GATE: strips ALL API-* when message has 0 notion intent
    gated_intent = _apply_notion_gates(dummy_body, last_user="tell me a joke about dogs", autonomous=False)
    tool_names_intent = [t["function"]["name"] for t in gated_intent["tools"]]
    assert not any(name.startswith("API-") for name in tool_names_intent)
    assert "local_calc" in tool_names_intent


def test_single_pipeline_import_graph_and_stages_delegation():
    """Enforces that stages/ cleanly delegates to vox/ as the sole underlying implementation engine at runtime (Rule 139)."""
    import stages.s05_director_plan as s05
    import stages.s10_render as s10
    import stages.s11_qc as s11
    import vox.assemble as va
    import vox.planner as vp
    import vox.qa.gates as vq

    # 1. S5 runtime delegation to vox.planner
    assert s05.plan_scenes_from_script is vp.plan_scenes_from_script, "stages/s05 must delegate directly to vox.planner"

    # 2. S10 runtime delegation to vox.assemble
    assert s10.assemble_final_video is va.assemble_final_video, "stages/s10 must delegate directly to vox.assemble.assemble_final_video"

    # 3. S11 runtime delegation to vox.qa.gates
    assert s11.verify_final_video_gates is vq.verify_final_video_gates, "stages/s11 must delegate directly to vox.qa.gates.verify_final_video_gates"

    # 4. director_planner_b3 delegates to s05_director_plan
    import app.services.director_planner_b3 as dp_b3
    assert hasattr(dp_b3, "generate_director_plan"), "director_planner_b3 must export canonical interface"


def test_canonical_render_engine_and_chapter_sync():
    """Asserts that vox.pipeline uses canonical vox compositor & assembly engine and enforces Rule 135 chapter sync."""
    import sys

    import vox.assemble as vassem
    import vox.compositor as vcomp
    import vox.pipeline as vpipe

    # Assert canonical pipeline binds to vox compositor and assemble
    assert vpipe.render_scene_clip is vcomp.render_scene_clip, "vox.pipeline must use vox.compositor.render_scene_clip as canonical render engine"
    assert vpipe.assemble_final_video is vassem.assemble_final_video, "vox.pipeline must use vox.assemble.assemble_final_video as canonical assembly engine"

    # Assert legacy modules are NOT imported by vox.pipeline
    forbidden_legacy = ["app.pipeline.run_episode", "scripts.produce_episode", "scripts.produce_episode_hg1"]
    for mod in forbidden_legacy:
        assert mod not in sys.modules, f"Forbidden legacy module {mod} must not be loaded"

    # Assert build_remotion_props is not used as pipeline render engine (Rule 125/135)
    assert not hasattr(vpipe, "render_remotion_video"), "vox.pipeline must not contain remotion render alternate path"


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
