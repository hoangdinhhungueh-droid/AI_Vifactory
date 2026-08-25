# app/services/keyword_library.py — keyword library, DB-backed (Trend Brain).
# Rewritten 10/08/2026 (user directive): storage moved from
# data/keyword_library.json (DELETED) to the Notion DB "VF Trend Brain".
# This module is now a thin adapter keeping the ORIGINAL public API so all
# callers stay unchanged:
#   virality_score.py : available_subjects / mark_used / upsert_scored
#   trend_gate_ai.py  : mark_used (pick_of_day)
# See Decisions - Production (10/08/2026) + Skill AI Rule 0-ter point 7.

from app.services import trend_brain_mirror as _tbm


def upsert_scored(subject, market, scores=None, source="virality", status=None):
    return _tbm.upsert_scored(subject, market, scores, source=source, status=status)


def mark_used(subject, market):
    return _tbm.mark_used(subject, market)


def available_subjects(market=None, limit=None):
    return _tbm.available_subjects(market, limit)


def get_subject(subject, market):
    return _tbm.get_subject(subject, market)


def stats():
    return _tbm.stats()


if __name__ == "__main__":
    import json
    import logging
    logging.basicConfig(level=logging.INFO)
    print(json.dumps(stats(), indent=2, ensure_ascii=False))
