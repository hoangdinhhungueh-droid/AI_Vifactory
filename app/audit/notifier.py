# app/audit/notifier.py -- Telegram notifications for audit results
import os
import logging
import json

from app.utils.security import mask_exception_text

logger = logging.getLogger(__name__)

def _send_telegram(message: str):
    """Send message to Telegram. Uses existing VF Telegram bot."""
    try:
        import requests
        token = os.environ.get("VF_TG_BOT_TOKEN", os.environ.get("TELEGRAM_BOT_TOKEN", ""))
        chat_id = os.environ.get("VF_TG_CHAT_ID", os.environ.get("TELEGRAM_CHAT_ID", ""))
        if not token or not chat_id:
            logger.warning("Telegram token/chat_id not set -- skipping notification")
            return
        api_url = f"https://api.telegram.org/bot{token}/sendMessage"
        resp = requests.post(
            api_url,
            json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"},
            timeout=10,
        )
        if resp.status_code != 200:
            # 16/08 fix: audit/fix texts may contain literal "<...>" (naming-convention
            # placeholders) which Telegram HTML parse_mode rejects with 400 -> retry plain
            logger.warning(f"Telegram HTML send failed: {resp.status_code} -- retrying plain")
            resp = requests.post(
                resp.request.url,
                json={"chat_id": chat_id, "text": message},
                timeout=10,
            )
            if resp.status_code != 200:
                logger.warning(f"Telegram plain send failed: {resp.status_code}")
    except Exception as e:
        logger.warning(f"Telegram notification error: {mask_exception_text(str(e))}")


def send_audit_notification(episode_id: str, audit_type: str, stage: str,
                              score: float, verdict: str, axis_scores: dict, issues: list):
    """Send audit result notification to Telegram."""
    verdict_emoji = {"APPROVED": "\u2705", "REVIEW": "\u26a0\ufe0f", "REJECTED": "\U0001f534"}.get(verdict, "\u2753")
    
    # Build axis score table
    axis_lines = []
    for axis, score_val in sorted(axis_scores.items(), key=lambda x: x[1]):
        bar = "\u2588" * int(score_val) + "\u2591" * (10 - int(score_val))
        axis_lines.append(f"  {axis:20s} {score_val:4.1f} {bar}")
    
    # Build issues summary
    issue_lines = []
    high_issues = [i for i in issues if i.get("severity") in ("high", "critical")]
    if high_issues:
        issue_lines.append(f"\n<b>\u26a0\ufe0f Issues ({len(high_issues)} high):</b>")
        for i in high_issues[:5]:  # Top 5
            issue_lines.append(f"  \u2022 [{i.get('axis', '?')}] {i.get('message', '')[:80]}")
    
    message = f"""<b>{verdict_emoji} Audit: {audit_type.upper()}</b>
<b>Episode:</b> {episode_id}
<b>Stage:</b> {stage}
<b>Score:</b> {score}/10 \u2192 <b>{verdict}</b>

<b>Axis Scores:</b>
{chr(10).join(axis_lines)}
{chr(10).join(issue_lines)}

<b>LLM:</b> {'Groq free tier' if score > 0 else 'rule-only'}"""
    
    _send_telegram(message)


def send_enhancement_notification(skill_name: str, enhancement_type: str,
                                     proposed_value: str, rationale: str, confidence: float):
    """Send skill enhancement proposal to Telegram for human approval."""
    message = f"""<b>\U0001f504 Skill Enhancement Proposal</b>
<b>Skill:</b> {skill_name}
<b>Type:</b> {enhancement_type}
<b>Confidence:</b> {confidence:.0%}

<b>Proposed:</b> {proposed_value[:200]}

<b>Rationale:</b> {rationale[:200]}

<i>Review and approve in Notion or via Telegram callback.</i>"""
    _send_telegram(message)


def send_learn_summary(scope: str, patterns: int, proposals: int, items: list) -> None:
    """16/08: ONE consolidated Telegram message per learn cycle (anti-spam)."""
    lines = [
        f"[LEARN CYCLE DONE] scope={scope}",
        f"Patterns: {patterns} | Proposals saved: {proposals} | High-conf: {len(items)}",
    ]
    for skill_name, enhancement_type, proposed_value, confidence in items[:10]:
        lines.append(f"- [{skill_name}] {enhancement_type} ({confidence:.0%}): {proposed_value[:120]}")
    lines.append("NEXT: python scripts/run-learn.py --queue -> review + approve proposal de apply vao skill.")
    _send_telegram("\n".join(lines))


def send_skill_ai_sync_result(skill_name: str, verdict: str, rule_title: str, detail: str):
    """23/08/2026 -- Rule 121 reverse-sync gate result. Notifies the human after
    scripts/sync_skill_enhancements.py has run the GPT-5.6-Sol strict absolute audit
    on an already human-approved enhancement, and either wrote a new generalized rule
    into the live Skill AI page (verdict='APPLIED') or rejected it for being too
    narrow/episode-specific or conflicting with existing rules (verdict='REJECTED'),
    or hit an error calling the LLM (verdict='AUDIT_ERROR').
    """
    emoji = {"APPLIED": "\u2705", "REJECTED": "\U0001f6d1", "AUDIT_ERROR": "\u26a0\ufe0f"}.get(verdict, "\u2753")
    message = f"""<b>{emoji} Skill AI Reverse-Sync -- {verdict}</b>
<b>Skill:</b> {skill_name}
<b>Rule:</b> {rule_title}

{detail[:400]}"""
    _send_telegram(message)
