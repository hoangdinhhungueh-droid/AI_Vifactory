# tests/test_notion_state_machine.py
# Verification suite for Cross-DB Status Transitions & Label Architecture (B1 -> B3.5)
import os
import pytest
import scripts.ag_notion_bridge as bridge
from app.services.trend_brain_mirror import _yt_labels_for_subject, _STATUS_TO_DB


def test_trend_brain_schema_and_status_options():
    """Verify live Notion Trend Brain DB matches state machine contract."""
    db_id = "4c101989-2400-8334-8016-01d4f463b09f"
    res = bridge._req("GET", f"databases/{db_id}")
    assert not res.get("error"), f"Failed to fetch Trend Brain DB: {res}"
    props = res.get("properties", {})
    
    # Title property MUST be Keyword
    assert "Keyword" in props, "Trend Brain must have 'Keyword' property"
    assert props["Keyword"]["type"] == "title"
    
    # Status property MUST be empty string (header '')
    assert "" in props, "Trend Brain must have '' status property"
    assert props[""]["type"] == "status"
    status_opts = [o["name"] for o in props[""]["status"]["options"]]
    assert "New (from VPS)" in status_opts
    assert "Approved→Story" in status_opts
    assert "Used" in status_opts
    
    # Metric and labels
    assert "Trend Score" in props and props["Trend Score"]["type"] == "number"
    assert "YouTube Safety Label" in props and props["YouTube Safety Label"]["type"] == "multi_select"
    assert "Upload Treatment Note" in props and props["Upload Treatment Note"]["type"] == "rich_text"


def test_story_library_schema_and_status_options():
    """Verify live Notion Story Library DB matches state machine contract."""
    db_id = "b0301989-2400-836b-bdb5-8131fea17736"
    res = bridge._req("GET", f"databases/{db_id}")
    assert not res.get("error"), f"Failed to fetch Story Library DB: {res}"
    props = res.get("properties", {})
    
    assert "Name" in props and props["Name"]["type"] == "title"
    assert "Status" in props and props["Status"]["type"] == "status"
    status_opts = [o["name"] for o in props["Status"]["status"]["options"]]
    assert "Draft" in status_opts
    assert "Gate Passed" in status_opts
    assert "Compiled" in status_opts
    assert "Produced" in status_opts


def test_director_plan_schema_and_status_options():
    """Verify live Notion Director Plan DB matches state machine contract."""
    db_id = "5b201989-2400-8295-be81-81c2c0e4e138"
    res = bridge._req("GET", f"databases/{db_id}")
    assert not res.get("error"), f"Failed to fetch Director Plan DB: {res}"
    props = res.get("properties", {})
    
    assert "Name" in props and props["Name"]["type"] == "title"
    assert "Status" in props and props["Status"]["type"] == "status"
    status_opts = [o["name"] for o in props["Status"]["status"]["options"]]
    assert "Draft" in status_opts
    assert "Compiled" in status_opts
    assert "Prompted" in status_opts


def test_yt_safety_label_propagation():
    """Verify YouTube safety labels are generated accurately for platform compliance."""
    safe_labels, safe_note = _yt_labels_for_subject("Byzantine Empire economy collapse")
    assert "YT-History-Factual-Neutral" in safe_labels
    assert "FACTUAL HISTORY ONLY" in safe_note
    
    crime_labels, crime_note = _yt_labels_for_subject("Ted Bundy serial killer case investigation")
    assert "YT-Sensitive-TrueCrime" in crime_labels
    assert "CASE-SOLVING DOCUMENTARY ONLY" in crime_note
    
    fraud_labels, fraud_note = _yt_labels_for_subject("Bernie Madoff Ponzi Scheme")
    assert "YT-Fraud-Education" in fraud_labels
    assert "FRAUD/SCAM EDUCATION" in fraud_note
    
    normal_labels, normal_note = _yt_labels_for_subject("Semiconductor supply chain revolution")
    assert "YT-Safe" in normal_labels


def test_status_mapping_contract():
    """Verify internal status keys map precisely to Notion UI options."""
    assert _STATUS_TO_DB["available"] == "New (from VPS)"
    assert _STATUS_TO_DB["committed"] == "Approved→Story"
    assert _STATUS_TO_DB["used"] == "Used"
    assert _STATUS_TO_DB["rejected"] == "Rejected"
