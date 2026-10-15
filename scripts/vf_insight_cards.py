#!/usr/bin/env python3
"""
scripts/vf_insight_cards.py
=============================================================================
VF Pipeline InsightCard Module -- B11 -> B2 Feedback Loop
=============================================================================
Provides:
  - distill_insights_to_cards(): Called by B11 to write InsightCards to Notion
  - fetch_active_insights(): Called by B2 to read actionable directives

InsightCard Schema (Rule 128 compliant -- zero semantic bias):
  All directives contain STRUCTURAL cues only (pacing, angle type, tempo).
  NEVER contains topic names, episode slugs, or domain-specific content.

Integration:
  B11 calls distill_insights_to_cards() after supreme analysis
  B2 calls fetch_active_insights(market) before generating story prompt
=============================================================================
"""
import json
import os
import time
import urllib.request
from datetime import datetime, timezone
from typing import Optional

# ---- CONSTANTS ----------------------------------------------------------------
EXPERIMENT_LAB_DB_ID = os.getenv(
    'B11_EXPERIMENT_LAB_DB_ID',
    '76601989-2400-838f-ad45-816777c57ffd'
)

# InsightCard dimensions (Rule 128: structural, not semantic)
DIMENSIONS = [
    'hook_pacing',       # Speed of hook opening (0-30s, 30-45s, 45-60s)
    'content_angle',     # Type of angle (investigative, systemic, personal)
    'narration_tempo',   # Narration speed and rhythm
    'visual_density',    # Scenes per minute in director plan
    'story_structure',   # Act proportion balance
]

MIN_EPISODES_FOR_CARD = 2    # need at least 2 data points
MIN_CONFIDENCE = 0.55        # minimum confidence to write a card
ACTIVE_CONFIDENCE_GATE = 0.6 # B2 only receives cards >= this confidence
DEFAULT_EXPIRES_AFTER = 20   # episodes
INSIGHT_CARD_TYPE = 'InsightCard'  # property to tag rows in Experiment Lab DB


# ---- NOTION HTTP HELPER -------------------------------------------------------
def _notion_req(notion_token: str, endpoint: str,
                method: str = 'GET', payload: Optional[dict] = None) -> dict:
    """Minimal Notion API call -- fail closed on HTTP errors (Rule 118/139)."""
    if not notion_token:
        raise ValueError("[vf_insight_cards] Missing notion_token for Notion API call")
    url = f'https://api.notion.com/v1/{endpoint}'
    data = json.dumps(payload).encode('utf-8') if payload else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={
            'Authorization': f'Bearer {notion_token}',
            'Notion-Version': '2022-06-28',
            'Content-Type': 'application/json',
        }
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode('utf-8'))


# ---- DISTILLATION: B11 -> InsightCard -----------------------------------------
def distill_insights_to_cards(
        notion_token: str,
        market: str,
        analytics_summary: dict,
        existing_cards: Optional[list] = None,
        dry_run: bool = False,
) -> list:
    """
    Analyse analytics_summary from B11 supreme run and distill into
    actionable InsightCards. Writes new/updated cards to Experiment Lab DB (or dry-run sink).

    Args:
        notion_token: Notion API token
        market: Market code (EN, JP, KR)
        analytics_summary: Dict with keys:
            avd_sec: average view duration in seconds
            duration_sec: total video duration in seconds
            hook_retention_0_30s: float 0.0-1.0 (% retained at 30s)
            hook_retention_0_60s: float 0.0-1.0 (% retained at 60s)
            mobile_pct: float, % of views from mobile
            ctr: float, click-through rate 0.0-1.0
            views: int
            trigger_reason: str describing why supreme was triggered
        existing_cards: Optional list of existing InsightCard dicts from DB

    Returns:
        List of card dicts that were written to Notion
    """
    if not notion_token or not market:
        print('[vf_insight_cards] Missing token or market -- skip distillation', flush=True)
        return []

    market = market.upper()
    written_cards = []
    ts = datetime.now(timezone.utc).isoformat()
    avd_sec = analytics_summary.get('avd_sec', 0)
    duration_sec = analytics_summary.get('duration_sec', 1) or 1
    hook_30s = analytics_summary.get('hook_retention_0_30s', None)
    hook_60s = analytics_summary.get('hook_retention_0_60s', None)
    avd_ratio = avd_sec / duration_sec if duration_sec else 0

    def _save_card(dim: str, obs: str, dir_text: str, conf: float) -> str:
        if dry_run:
            print(f"[vf_insight_cards] [DRY-RUN] Verified InsightCard for {market}/{dim} (confidence={conf:.2f}, zero Notion writes)", flush=True)
            return f"dry_run_{market}_{dim}_{int(time.time())}"
        return _write_or_update_card(notion_token, market, dim, obs, dir_text, conf, ts)

    # --- Pattern: Hook pacing ------------------------------------------------
    if hook_30s is not None and hook_60s is not None:
        if hook_30s >= 0.70:
            directive = 'Maintain aggressive hook compression: open with paradox or quantitative shock within 30s'
            obs = f'Hook 0-30s retention: {hook_30s:.0%} (strong)'
            confidence = min(0.60 + (hook_30s - 0.70) * 2, 0.95)
            card_id = _save_card('hook_pacing', obs, directive, confidence)
            written_cards.append({'dimension': 'hook_pacing', 'directive': directive, 'id': card_id})
        elif hook_60s < 0.55:
            directive = 'Shorten hook to under 35s: cut exposition, lead with core contradiction immediately'
            obs = f'Hook 0-60s retention: {hook_60s:.0%} (weak -- viewers dropping early)'
            confidence = min(0.60 + (0.55 - hook_60s) * 1.5, 0.90)
            card_id = _save_card('hook_pacing', obs, directive, confidence)
            written_cards.append({'dimension': 'hook_pacing', 'directive': directive, 'id': card_id})

    # --- Pattern: AVD / story structure --------------------------------------
    if avd_ratio >= 0.68:
        directive = 'Maintain current 5-beat story structure balance -- high retention confirms pacing works'
        obs = f'AVD/Duration ratio: {avd_ratio:.0%} (above 68% threshold)'
        confidence = min(0.60 + (avd_ratio - 0.68) * 1.5, 0.90)
        card_id = _save_card('story_structure', obs, directive, confidence)
        written_cards.append({'dimension': 'story_structure', 'directive': directive, 'id': card_id})
    elif avd_ratio < 0.45:
        directive = 'Insert micro-cliffhanger at mid-story (around 45-50% mark) -- AVD drop indicates engagement loss'
        obs = f'AVD/Duration ratio: {avd_ratio:.0%} (below 45% -- mid-story drop detected)'
        confidence = min(0.60 + (0.45 - avd_ratio) * 1.5, 0.88)
        card_id = _save_card('story_structure', obs, directive, confidence)
        written_cards.append({'dimension': 'story_structure', 'directive': directive, 'id': card_id})

    if written_cards:
        dest_label = "Dry-Run Sink" if dry_run else "Experiment Lab DB"
        print(f'[vf_insight_cards] Distilled {len(written_cards)} InsightCard(s) '
              f'for market={market} -> {dest_label}', flush=True)
    else:
        print(f'[vf_insight_cards] No patterns crossed confidence threshold '
              f'for market={market} -- no cards written', flush=True)

    return written_cards


def _write_or_update_card(
        notion_token: str, market: str, dimension: str,
        observation: str, directive: str, confidence: float, ts: str
):
    """Upsert an InsightCard row in Experiment Lab DB."""
    # Check existing card for same market+dimension (keyed by Episode ID)
    card_ep_id = f'IC_{market}_{dimension}'
    filter_payload = {
        'filter': {
            'property': 'Episode ID', 'rich_text': {'equals': card_ep_id}
        }
    }
    existing = _notion_req(
        notion_token,
        f'databases/{EXPERIMENT_LAB_DB_ID}/query',
        method='POST', payload=filter_payload
    )
    results = existing.get('results', [])

    props = {
        'Name': {'title': [{'type': 'text', 'text': {
            'content': f'[{market}] IC_{dimension}'[:80]
        }}]},
        'Episode ID': {'rich_text': [{'type': 'text', 'text': {
            'content': card_ep_id
        }}]},
        'Task ID': {'rich_text': [{'type': 'text', 'text': {
            'content': card_ep_id
        }}]},
        'State Stage': {'select': {'name': INSIGHT_CARD_TYPE}},
        'Insight': {'rich_text': [{'type': 'text', 'text': {
            'content': (
                f'[DIMENSION] {dimension}\n'
                f'[MARKET] {market}\n'
                f'[OBSERVATION] {observation}\n'
                f'[DIRECTIVE] {directive}\n'
                f'[CONFIDENCE] {confidence:.2f}\n'
                f'[EXPIRES_AFTER] {DEFAULT_EXPIRES_AFTER} episodes\n'
                f'[UPDATED] {ts}'
            )[:1900]
        }}]},
    }

    if results:
        page_id = results[0]['id']
        _notion_req(notion_token, f'pages/{page_id}',
                    method='PATCH', payload={'properties': props})
        print(f'[vf_insight_cards] Updated InsightCard page {page_id} '
              f'({market}/{dimension}) confidence={confidence:.2f}', flush=True)
        return page_id
    else:
        create_payload = {
            'parent': {'database_id': EXPERIMENT_LAB_DB_ID},
            'properties': props
        }
        resp = _notion_req(notion_token, 'pages',
                           method='POST', payload=create_payload)
        new_id = resp.get("id")
        if not new_id or new_id == "?":
            raise RuntimeError(f"[vf_insight_cards] Failed to create InsightCard in Notion DB {EXPERIMENT_LAB_DB_ID}: empty response")
        print(f'[vf_insight_cards] Created InsightCard {new_id} '
              f'({market}/{dimension}) confidence={confidence:.2f}', flush=True)
        return new_id


# ---- FETCH: B2 reads InsightCards -------------------------------------------
def fetch_active_insights(
        notion_token: str,
        market: str,
        max_cards: int = 5
) -> list:
    """
    Fetch active InsightCards for a market to inject into B2 story prompt.
    Only returns cards with confidence >= ACTIVE_CONFIDENCE_GATE.
    Returns empty list if Notion unavailable (B2 must NOT crash on this).

    Args:
        notion_token: Notion API token
        market: Market code (EN, JP, KR)
        max_cards: Max number of cards to return (default 5)

    Returns:
        List of dicts with keys: dimension, directive, confidence, observation
    """
    if not notion_token or not market:
        return []

    market = market.upper()
    filter_payload = {
        'filter': {
            'and': [
                {'property': 'Episode ID', 'rich_text': {'starts_with': f'IC_{market}_'}},
                {'property': 'State Stage', 'select': {'equals': INSIGHT_CARD_TYPE}},
            ]
        },
        'page_size': max_cards
    }
    try:
        results_raw = _notion_req(
            notion_token,
            f'databases/{EXPERIMENT_LAB_DB_ID}/query',
            method='POST', payload=filter_payload
        )
        cards = []
        for page in results_raw.get('results', []):
            insight_text = ''
            try:
                insight_text = (
                    page.get('properties', {})
                    .get('Insight', {})
                    .get('rich_text', [{}])[0]
                    .get('text', {}).get('content', '')
                )
            except (IndexError, KeyError):
                pass

            parsed = _parse_insight_text(insight_text)
            if parsed and parsed.get('confidence', 0) >= ACTIVE_CONFIDENCE_GATE:
                cards.append(parsed)

        # Sort by confidence descending
        cards.sort(key=lambda c: c.get('confidence', 0), reverse=True)
        if cards:
            print(f'[vf_insight_cards] Fetched {len(cards)} active InsightCard(s) '
                  f'for market={market}', flush=True)
        else:
            print(f'[vf_insight_cards] No active InsightCards for market={market} '
                  f'-- B2 will use baseline prompt', flush=True)
        return cards[:max_cards]

    except Exception as e:
        # Non-fatal: B2 continues without feedback if Notion unavailable
        print(f'[vf_insight_cards] fetch_active_insights failed (non-fatal): {e}',
              flush=True)
        return []


def _parse_insight_text(text: str) -> Optional[dict]:
    """Parse structured InsightCard text back into a dict."""
    if not text or '[DIMENSION]' not in text:
        return None
    result = {}
    for line in text.splitlines():
        for key in ['DIMENSION', 'MARKET', 'OBSERVATION', 'DIRECTIVE', 'CONFIDENCE', 'EXPIRES_AFTER']:
            prefix = f'[{key}] '
            if line.startswith(prefix):
                val = line[len(prefix):].strip()
                if key == 'CONFIDENCE':
                    try:
                        result['confidence'] = float(val)
                    except ValueError:
                        pass
                elif key == 'EXPIRES_AFTER':
                    try:
                        result['expires_after'] = int(val.split()[0])
                    except (ValueError, IndexError):
                        pass
                else:
                    result[key.lower()] = val
    return result if 'dimension' in result and 'directive' in result else None


# ---- BUILD FEEDBACK BLOCK for B2 prompt injection ----------------------------
def build_feedback_block(cards: list) -> str:
    """
    Render active InsightCards as a feedback block for B2 prompt injection.
    Returns empty string if no cards (B2 prompt unchanged).
    """
    if not cards:
        return ''

    lines = [
        '\n## PERFORMANCE FEEDBACK DIRECTIVES (from Experiment Lab -- live data):',
        f'(Based on {len(cards)} active InsightCard(s) from previous episodes)\n',
    ]
    for card in cards:
        dim = card.get('dimension', 'unknown').upper().replace('_', ' ')
        directive = card.get('directive', '')
        conf = card.get('confidence', 0)
        obs = card.get('observation', '')
        lines.append(f'  [{dim}] (confidence: {conf:.0%})')
        lines.append(f'    Observed: {obs}')
        lines.append(f'    Apply:   {directive}')
        lines.append('')

    lines.append(
        'INSTRUCTION: Apply the above structural directives into the 5-Beat script.'
        ' These are measured behavioral patterns from real viewer data.'
        ' Do NOT anchor to any specific topic or episode -- these are STRUCTURAL guidelines only.'
    )
    return '\n'.join(lines)
