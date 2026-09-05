"""safety_gate.py - Page 22 item B: 5-tier pre-upload Safety Gate (Phase 5, 07/08/2026).

FREE, deterministic, NO network, NO paid calls. Blocking stage: called from
youtube_upload.upload_from_payload() BEFORE platform_validator/rate_risk_controller.

This complements (does not replace) the existing checks:
  - scripts/preflight_upload_gate.py (export profile, blacklist, duplicate,
    pacing, BGM CC0 license) -- an optional manual/cron pre-flight report.
  - platform_validator.py (per-platform export constraints).
  - rate_risk_controller.py (upload pacing / risk throttling).

safety_gate.py adds the 5 tiers from Page 22 SS4 that those modules do not
cover: Copyright, Inauthentic/Reused, Child Safety, Advertiser-Friendly,
Anti-Ban/Spam. Detection here is keyword/heuristic-based (no ML classifier,
no third-party content-ID API available in this environment) -- it is a
honest, deterministic first line of defense, not a guarantee of policy
compliance. Any HARD violation blocks the upload; SOFT hits are warn-only.

Public API:
    run_safety_gate(episode_dir, payload, platform) -> SafetyGateResult
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List

# ---- Tier 3: Child Safety --------------------------------------------------
# Hard-block if content markets to/about minors combined with unsafe themes.
CHILD_SAFETY_HARD_PATTERNS = [
    r"\bkids?\b.{0,25}\b(prank|scary|horror|violen\w*|gore|nude|sex\w*)\b",
    r"\b(child|minor|teen)\w*\b.{0,25}\b(abuse|exploit\w*|groom\w*)\b",
    r"\bchallenge\b.{0,20}\bkids?\b.{0,20}\b(danger\w*|hurt|injur\w*)\b",
]

# ---- Tier 4: Advertiser-Friendly ------------------------------------------
# Q2/2026 YouTube advertiser-friendly guideline categories, keyword heuristic.
# RED = hard block (severe/repeated policy category); YELLOW = warn only.
ADVERTISER_RED_TERMS = [
    "suicide", "self-harm", "self harm", "beheading", "terroris", "child abuse",
    "csam", "snuff", "how to make a bomb", "school shooting",
]
ADVERTISER_YELLOW_TERMS = [
    "graphic violence", "gore", "drug use", "heroin", "cocaine", "hate speech",
    "racial slur", "gun violence", "torture", "gambling", "nsfw",
]

# ---- Tier 5: Anti-Ban / Spam ------------------------------------------------
SPAM_TITLE_PATTERNS = [
    r"(FREE\s*){3,}", r"(!{4,})", r"(SUBSCRIBE\s*NOW\s*){2,}",
    r"\bclick\s*here\b", r"\bmust\s*watch\s*or\s*die\b",
]


@dataclass
class SafetyGateResult:
    episode_id: str
    platform: str
    passed: bool
    tiers: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    blocks: List[str] = field(default_factory=list)
    warns: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "platform": self.platform,
            "passed": self.passed,
            "tiers": self.tiers,
            "blocks": self.blocks,
            "warns": self.warns,
        }


def _caps_ratio(s: str) -> float:
    letters = [c for c in s if c.isalpha()]
    if not letters:
        return 0.0
    caps = [c for c in letters if c.isupper()]
    return len(caps) / len(letters)


def _tier_copyright(episode_dir: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Tier 1: Copyright.

    Checks: AI-disclosure flag present (payload / seo_metadata always sets
    ai_disclosure=True); a BGM license sidecar exists whenever a BGM track is
    referenced; no asset in the episode dir is flagged as unlicensed
    user-uploaded footage (simulated_asset_gate.py / character_refs.py already
    block ungenerated/ unsourced visuals upstream -- this is a final safety net).
    """
    blocks, warns = [], []
    if payload.get("ai_disclosure") is not True:
        blocks.append("copyright: ai_disclosure flag missing/false in payload")
    try:
        has_bgm_ref = False
        brain_path = os.path.join(episode_dir, "brain_input.json")
        if os.path.exists(brain_path):
            with open(brain_path) as f:
                brain = json.load(f)
            has_bgm_ref = bool(brain.get("bgm_mood") or brain.get("bgm_path"))
        if has_bgm_ref:
            licenses = [fn for fn in os.listdir(episode_dir) if fn.endswith("_bgm.license.json")]
            if not licenses:
                warns.append("copyright: bgm referenced but no *_bgm.license.json sidecar found")
    except Exception as e:  # noqa: BLE001
        warns.append("copyright: bgm license check skipped (%s)" % e)
    flag_path = os.path.join(episode_dir, "unlicensed_footage.flag")
    if os.path.exists(flag_path):
        blocks.append("copyright: unlicensed_footage.flag present in episode dir")
    return {"blocks": blocks, "warns": warns}


def _tier_inauthentic(episode_dir: str, payload: Dict[str, Any], platform: str) -> Dict[str, Any]:
    """Tier 2: Inauthentic / Reused content.

    Checks the local publish_ledger for an exact title+platform re-upload
    (near-duplicate re-publish of the same asset), and requires the AI
    disclosure to be set (YouTube's "altered/synthetic content" self-declare
    requirement doubles as an inauthentic-content signal).
    """
    blocks, warns = [], []
    title = (payload.get("title") or "").strip().lower()
    try:
        from app.services import publish_ledger
        entries = []
        if hasattr(publish_ledger, "list_recent"):
            entries = publish_ledger.list_recent(limit=200) or []
        elif hasattr(publish_ledger, "load_all"):
            entries = publish_ledger.load_all() or []
        for e in entries:
            et = str(e.get("title", "")).strip().lower()
            if et and et == title:
                blocks.append("inauthentic: title already published (publish_ledger match): %s" % title[:80])
                break
    except Exception as e:  # noqa: BLE001
        warns.append("inauthentic: publish_ledger check skipped (%s)" % e)
    return {"blocks": blocks, "warns": warns}


def _tier_child_safety(payload: Dict[str, Any], episode: Dict[str, Any]) -> Dict[str, Any]:
    """Tier 3: Child Safety."""
    blocks: List[str] = []
    hay = " ".join([
        str(payload.get("title", "")),
        str(payload.get("description", "")),
        str((episode or {}).get("story", ""))[:2000],
    ]).lower()
    for pat in CHILD_SAFETY_HARD_PATTERNS:
        if re.search(pat, hay, re.I):
            blocks.append("child_safety: matched hard pattern '%s'" % pat)
    if payload.get("made_for_kids") not in (False, True):
        blocks.append("child_safety: made_for_kids not explicitly declared")
    return {"blocks": blocks, "warns": []}


def _tier_advertiser_friendly(payload: Dict[str, Any], episode: Dict[str, Any]) -> Dict[str, Any]:
    """Tier 4: Advertiser-Friendly content guidelines (keyword heuristic)."""
    blocks, warns = [], []
    hay = " ".join([
        str(payload.get("title", "")),
        str(payload.get("description", "")),
        str((episode or {}).get("story", ""))[:2000],
    ]).lower()
    for term in ADVERTISER_RED_TERMS:
        if term in hay:
            blocks.append("advertiser_friendly: RED term matched '%s'" % term)
    for term in ADVERTISER_YELLOW_TERMS:
        if term in hay:
            warns.append("advertiser_friendly: YELLOW term matched '%s' (limited-ads risk, not blocked)" % term)
    return {"blocks": blocks, "warns": warns}


# YT_SAFETY_LABELS_20260819 — E2E upload checker for Trend Brain labels.
YT_FORBIDDEN_GRAPHIC_TERMS = [
    'gore','bloody','blood-soaked','blood splatter','corpse','dead body','body discovery',
    'wound','wounds','stabbing','strangling','torture','dismember','cannibal','rape',
    'sexual assault','victim last moments','brutal murder','most brutal','how he killed','how they killed'
]
YT_KILLER_GLORIFY_TERMS = ['genius killer','mastermind killer','legendary killer','cool killer','most terrifying killer','inside the killer mind']
YT_CURRENT_POLITICS_TERMS = ['election 2026','vote for','vote against','democrat vs republican','left-wing agenda','right-wing agenda','party propaganda']
YT_MAINSTREAM_RELIGION_TERMS = ['christianity','buddhism','islam','hinduism','judaism','catholic church','buddhist doctrine','muslim doctrine']

def _load_yt_safety_meta(episode_dir: str, payload: Dict[str, Any], episode: Dict[str, Any]) -> Dict[str, Any]:
    meta = {}
    for src in [payload, episode]:
        for k in ('youtube_safety_label','YouTube Safety Label','yt_safety_labels','safety_labels'):
            if isinstance(src, dict) and src.get(k): meta['labels'] = src.get(k)
        for k in ('upload_treatment_note','Upload Treatment Note','treatment_note'):
            if isinstance(src, dict) and src.get(k): meta['note'] = str(src.get(k))
    # best-effort local sidecar generated by future Notion/VPS compilers
    for fn in ('yt_safety.json','youtube_safety.json','safety_labels.json'):
        fp=os.path.join(episode_dir, fn)
        if os.path.exists(fp):
            try:
                data=json.load(open(fp))
                meta.update({k:v for k,v in data.items() if k in ('labels','note')})
            except Exception: pass
    labels = meta.get('labels') or []
    if isinstance(labels, str): labels=[x.strip() for x in labels.replace(';',',').split(',') if x.strip()]
    meta['labels']=labels
    return meta

def _tier_youtube_safety_labels(episode_dir: str, payload: Dict[str, Any], episode: Dict[str, Any]) -> Dict[str, Any]:
    blocks, warns = [], []
    meta = _load_yt_safety_meta(episode_dir, payload, episode)
    labels = set(meta.get('labels') or [])
    hay = ' '.join([str(payload.get('title','')), str(payload.get('description','')), ' '.join(map(str,payload.get('tags') or [])), str((episode or {}).get('story',''))[:4000]]).lower()
    if any(str(x).startswith('YT-HardBlock') for x in labels):
        blocks.append('yt_safety_label: hard-block label present: %s' % ','.join(sorted(labels)))
    if labels & {'YT-Sensitive-TrueCrime','YT-Sensitive-CultCrime','YT-NonGraphic-Required'}:
        for term in YT_FORBIDDEN_GRAPHIC_TERMS + YT_KILLER_GLORIFY_TERMS:
            if term in hay:
                blocks.append("yt_safety_label: sensitive/non-graphic label violated by term '%s'" % term)
        ok_terms = ['investigation','evidence','forensic','trial','court','accountability','case','timeline','documentary','why']
        if not any(t in hay for t in ok_terms):
            warns.append('yt_safety_label: sensitive true-crime upload lacks clear investigation/case-solving framing')
    if 'YT-History-Factual-Neutral' in labels:
        for term in YT_CURRENT_POLITICS_TERMS:
            if term in hay: blocks.append("yt_safety_label: history-neutral label violated by current-politics term '%s'" % term)
    if 'YT-HardBlock-MainstreamReligion' in labels or any(t in hay for t in YT_MAINSTREAM_RELIGION_TERMS):
        if 'YT-Sensitive-CultCrime' not in labels:
            blocks.append('yt_safety_label: mainstream-religion framing risk')
    return {'blocks': blocks, 'warns': warns}

def _tier_anti_ban_spam(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Tier 5: Anti-Ban / Spam."""
    blocks, warns = [], []
    title = str(payload.get("title", ""))
    for pat in SPAM_TITLE_PATTERNS:
        if re.search(pat, title, re.I):
            blocks.append("anti_ban: spam pattern in title '%s'" % pat)
    ratio = _caps_ratio(title)
    if ratio > 0.7 and len(title) > 12:
        warns.append("anti_ban: title is %.0f%% caps (clickbait/spam risk)" % (ratio * 100))
    tags = payload.get("tags") or []
    if len(tags) != len(set(t.lower() for t in tags)):
        warns.append("anti_ban: duplicate tags detected")
    return {"blocks": blocks, "warns": warns}


def run_safety_gate(episode_dir: str, payload: Dict[str, Any], platform: str = "youtube") -> SafetyGateResult:
    """Run all 5 safety tiers for one upload payload. Returns SafetyGateResult.

    `payload` is the platform upload payload (title/description/tags/...),
    e.g. the dict loaded from youtube_upload_payload.json. Story text (for
    child-safety / advertiser-friendly scanning) is best-effort loaded from
    brain_input.json in episode_dir when present.
    """
    episode_id = os.path.basename(os.path.normpath(episode_dir)) if episode_dir else ""
    episode: Dict[str, Any] = {}
    try:
        brain_path = os.path.join(episode_dir, "brain_input.json")
        if os.path.exists(brain_path):
            with open(brain_path) as f:
                episode = json.load(f)
    except Exception:  # noqa: BLE001
        episode = {}

    tiers = {
        "1_copyright": _tier_copyright(episode_dir, payload),
        "2_inauthentic_reused": _tier_inauthentic(episode_dir, payload, platform),
        "3_child_safety": _tier_child_safety(payload, episode),
        "4_advertiser_friendly": _tier_advertiser_friendly(payload, episode),
        "5_yt_safety_labels": _tier_youtube_safety_labels(episode_dir, payload, episode),
        "6_anti_ban_spam": _tier_anti_ban_spam(payload),
    }
    blocks: List[str] = []
    warns: List[str] = []
    for t in tiers.values():
        blocks.extend(t.get("blocks", []))
        warns.extend(t.get("warns", []))
    return SafetyGateResult(
        episode_id=episode_id, platform=platform, passed=(len(blocks) == 0),
        tiers=tiers, blocks=blocks, warns=warns,
    )


if __name__ == "__main__":
    import sys
    ep_dir = sys.argv[1] if len(sys.argv) > 1 else "/var/vf/episodes/betrayal-revenge-quiet-2026-ep001"
    pf = os.path.join(ep_dir, "youtube_upload_payload.json")
    with open(pf) as f:
        pl = json.load(f)
    res = run_safety_gate(ep_dir, pl, "youtube")
    print(json.dumps(res.to_dict(), indent=2, ensure_ascii=False))
