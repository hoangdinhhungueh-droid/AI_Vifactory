#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/codemap/test_runtime_lineage.py — Forensic tests for Approval Lineage verification."""

import pytest
from pathlib import Path
from tools.codemap.approval import record_approval
from tools.codemap.lineage import compute_lineage_report
from tools.codemap.runtime import pipeline_stage, run_context


@pipeline_stage(id="stage_consumer", order=2)
def consumer_stage(payload: dict) -> dict:
    return {"status": "consumed", "data": payload}


def test_lineage_intact(tmp_path):
    run_id = "run_test_intact"
    appr_payload = {"title": "Approved Topic", "scenes": 5}

    # 1. Record approval
    appr = record_approval(run_id, "stage_consumer", appr_payload, repo_root=tmp_path)

    # 2. Run stage under context with approval reference
    with run_context(run_id, repo_root=tmp_path, approval_refs=[appr.approval_id]):
        consumer_stage(appr_payload)

    # 3. Compute lineage
    reports = compute_lineage_report(run_id, repo_root=tmp_path)
    assert len(reports) == 1
    rep = reports[0]
    assert rep.overall == "INTACT"
    verdicts = {v.path: v.verdict for v in rep.fields}
    assert verdicts.get("/args/0/title") == "CARRIED" or verdicts.get("/title") == "CARRIED" or any(v == "CARRIED" for v in verdicts.values())


def test_lineage_modified_drift(tmp_path):
    run_id = "run_test_modified"
    appr_payload = {"title": "Original Approved Title", "scenes": 5}

    appr = record_approval(run_id, "stage_consumer", appr_payload, repo_root=tmp_path)

    # Consumer receives tampered data
    tampered_payload = {"title": "TAMPERED WITHOUT PERMISSION", "scenes": 5}
    with run_context(run_id, repo_root=tmp_path, approval_refs=[appr.approval_id]):
        consumer_stage(tampered_payload)

    reports = compute_lineage_report(run_id, repo_root=tmp_path)
    assert len(reports) == 1
    rep = reports[0]
    assert rep.overall == "DRIFT"
    assert any(v.verdict in ("MODIFIED", "DROPPED") for v in rep.fields)


def test_lineage_not_consumed_bypass(tmp_path):
    run_id = "run_test_bypass"
    appr_payload = {"title": "Approved Title"}

    # Record approval for target stage
    appr = record_approval(run_id, "stage_consumer", appr_payload, repo_root=tmp_path)

    # Stage executes WITHOUT referencing the approval ID (bypassing it!)
    with run_context(run_id, repo_root=tmp_path, approval_refs=[]):
        consumer_stage({"title": "Bypass Data"})

    reports = compute_lineage_report(run_id, repo_root=tmp_path)
    assert len(reports) == 1
    rep = reports[0]
    assert rep.overall == "NOT_CONSUMED"
