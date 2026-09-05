# VF Audit Pipeline — automated quality audit + self-learning feedback loop
# Created by Notion AI audit 15/08/2026
# Design: 100% free, no crash, RAM efficient, reliable, quality-first
"""
VF Audit Pipeline
=================
Automated quality audit engine for Video Factory pipeline.
Runs after each pipeline stage, scores quality on multiple axes,
stores results in Postgres, and feeds back into skills for self-enhancement.

Key principles:
- 100% FREE: deterministic checks first (0 LLM cost), LLM only for subjective scoring (Groq free tier)
- NO CRASH: 30s timeout per audit, graceful degradation, circuit breaker for LLM
- RAM EFFICIENT: on-demand Celery task, max 200MB per audit, not resident
- RELIABLE: idempotent, retry 3x, checkpoint in Postgres
- QUALITY: multi-axis rubric scoring, human approval gate for skill enhancements
"""

__version__ = "1.0.0"
__all__ = ["engine", "db", "rubrics", "story_audit", "director_audit", "prompt_audit", "learn", "notifier"]
