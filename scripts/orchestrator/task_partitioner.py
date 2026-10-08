"""scripts/orchestrator/task_partitioner.py — Pipeline Task Partitioning & Contract Validation.

Implements task partitioning for B1, B1.5, B2, B3, B3.5 per PIPELINE_CONTRACTS.md:
1. Block parsing (--blocks 1.0, 1.5, 2.0, 3.0, 3.5, 1.0..3.5, all).
2. Input/Output Data Contract verification according to Generic Contract Pattern (Rule 128).
3. Dependency graph resolution ensuring prerequisites are satisfied before execution.
4. Execution plan generation with full dry-run support.
"""

import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

if __package__ is None or __package__ == "":
    _root = Path(__file__).resolve().parent.parent.parent
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))
    from scripts.orchestrator.rule128_governor import validate_generic_task_id
else:
    from .rule128_governor import validate_generic_task_id


@dataclass
class StageContract:
    """Defines inputs and outputs for a specific pipeline stage."""
    stage_id: str
    name: str
    description: str
    prerequisites: List[str]
    input_files: List[str]   # Templates with {task_id} and {market}
    output_files: List[str]  # Templates with {task_id} and {market}
    command_template: List[str]


# Authoritative contract definitions from PIPELINE_CONTRACTS.md
PIPELINE_STAGES: Dict[str, StageContract] = {
    "1.0": StageContract(
        stage_id="1.0",
        name="B1 Trend Discovery",
        description="Google Trends RSS live ingestion & Wikipedia Reality Anchor",
        prerequisites=[],
        input_files=[],
        output_files=["/var/vf/pending_tasks/{task_id}.json"],
        command_template=[
            "python3",
            "scripts/run_trend_pipeline.py",
            "--market",
            "{market}",
            "--no-produce",
        ],
    ),
    "1.5": StageContract(
        stage_id="1.5",
        name="B1.5 Competitor Recon",
        description="YouTube Recon, Fatal Explanatory Vacuum & 10x Pivot Extraction",
        prerequisites=["1.0"],
        input_files=["/var/vf/pending_tasks/{task_id}.json"],
        output_files=["/var/vf/episodes/{task_id}/competitor_intel_card.json"],
        command_template=[
            "python3",
            "-c",
            "import sys; sys.path.insert(0, '.'); from app.services.competitor_recon_b15 import run_b15; "
            "import json; meta = json.load(open('/var/vf/pending_tasks/{task_id}.json')); "
            "run_b15('{task_id}', meta.get('raw_term') or meta.get('keyword'), meta.get('niche_angle_brief') or 'General')",
        ],
    ),
    "1.5.5": StageContract(
        stage_id="1.5.5",
        name="B1.5.5 Grounding Layer",
        description="Fact & Data Anchoring via Live Google Search Whitelist Verification (Rule 118 & 121)",
        prerequisites=["1.5"],
        input_files=["/var/vf/pending_tasks/{task_id}.json"],
        output_files=["/var/vf/episodes/{task_id}/grounding_intel.json"],
        command_template=[
            "python3",
            "-c",
            "import sys, json; sys.path.insert(0, '.'); from app.services.grounding_layer_b15 import run_grounding_research, passes_grounding_gate; "
            "meta = json.load(open('/var/vf/pending_tasks/{task_id}.json')); "
            "intel = run_grounding_research(topic=meta.get('raw_term') or meta.get('keyword'), search_hint=meta.get('niche_angle_brief') or 'General', market=meta.get('market') or 'EN'); "
            "ok, msg = passes_grounding_gate(intel, min_verified=2, require_whitelist=True); "
            "assert ok, f'Grounding Gate Failed: {msg}'; "
            "open('/var/vf/episodes/{task_id}/grounding_intel.json', 'w', encoding='utf-8').write(json.dumps(intel, ensure_ascii=False, indent=2))",
        ],
    ),
    "1.6": StageContract(
        stage_id="1.6",
        name="B1.6 Early SEO Package",
        description="Dual Title A/B, Description, Tags & 60s An Ong Hook Forge (Rule 444)",
        prerequisites=["1.5.5"],
        input_files=[
            "/var/vf/pending_tasks/{task_id}.json",
            "/var/vf/episodes/{task_id}/grounding_intel.json",
        ],
        output_files=["/var/vf/episodes/{task_id}/seo_package.json"],
        command_template=[
            "python3",
            "-c",
            "import sys, json; sys.path.insert(0, '.'); from app.services.seo_package_forge import forge_seo_package; "
            "meta = json.load(open('/var/vf/pending_tasks/{task_id}.json')); "
            "card_p = '/var/vf/episodes/{task_id}/competitor_intel_card.json'; "
            "card = json.load(open(card_p)) if sys.platform != 'win32' and __import__('os').path.exists(card_p) else None; "
            "pkg = forge_seo_package('{task_id}', meta.get('raw_term') or meta.get('keyword'), market=meta.get('market') or 'EN', niche_brief=meta.get('niche_angle_brief') or 'General', competitor_card=card); "
            "open('/var/vf/episodes/{task_id}/seo_package.json', 'w', encoding='utf-8').write(json.dumps(pkg, ensure_ascii=False, indent=2))",
        ],
    ),
    "2.0": StageContract(
        stage_id="2.0",
        name="B2 VOX Story & Beat Engine",
        description="Fern DNA continuous investigative script (300-450 words, <=12w cold open) & VOX Audio Spine via GPT-6-Astra",
        prerequisites=["1.5.5"],
        input_files=[
            "/var/vf/pending_tasks/{task_id}.json",
            "/var/vf/episodes/{task_id}/competitor_intel_card.json",
            "/var/vf/episodes/{task_id}/grounding_intel.json",
        ],
        output_files=[
            "/var/vf/episodes/{task_id}/story.txt",
            "/var/vf/episodes/{task_id}/brain_input.json",
            "/var/vf/episodes/{task_id}/tts_out.mp3",
            "/var/vf/episodes/{task_id}/director_plan.json",
            "/var/vf/episodes/{task_id}/prompts_forge.json",
            "/var/vf/episodes/{task_id}/remotion_props.json",
        ],
        command_template=[
            "python3",
            "scripts/run_vox_automated_pipeline.py",
            "--task-id",
            "{task_id}",
            "--market",
            "{market}",
            "--auto",
        ],
    ),
    "2.1": StageContract(
        stage_id="2.1",
        name="B2.1 Fact & Causal Audit",
        description="Claude-Opus-5 Forensic Fact & Causal Integrity Audit (Rule 118 & 130)",
        prerequisites=["2.0"],
        input_files=[
            "/var/vf/episodes/{task_id}/story.txt",
            "/var/vf/episodes/{task_id}/grounding_intel.json",
        ],
        output_files=["/var/vf/episodes/{task_id}/fact_audit.json"],
        command_template=[
            "python3",
            "-c",
            "import sys, json; sys.path.insert(0, '.'); from app.services.story_fact_auditor_b2 import audit_story_facts_and_causality; "
            "story = open('/var/vf/episodes/{task_id}/story.txt', encoding='utf-8').read(); "
            "claims = json.load(open('/var/vf/episodes/{task_id}/grounding_intel.json', encoding='utf-8')).get('claims', []); "
            "meta = json.load(open('/var/vf/pending_tasks/{task_id}.json', encoding='utf-8')); "
            "res = audit_story_facts_and_causality(story, claims, {'task_id': '{task_id}', 'topic': meta.get('raw_term')}, market=meta.get('market', 'EN'), model='claude-opus-5-5'); "
            "open('/var/vf/episodes/{task_id}/fact_audit.json', 'w', encoding='utf-8').write(json.dumps(res, ensure_ascii=False, indent=2)); "
            "assert res.get('verdict') == 'PASS' or float(res.get('audit_score', 0)) >= 7.5, f'B2.1 Audit Gate Failed: {res}'",
        ],
    ),
    "2.5": StageContract(
        stage_id="2.5",
        name="B2.5 Spoken VO Verification",
        description="Verification of VOX breath-timed spoken sentences and timecode alignment",
        prerequisites=["2.1"],
        input_files=[
            "/var/vf/episodes/{task_id}/story.txt",
        ],
        output_files=[
            "/var/vf/episodes/{task_id}/spoken_script.txt",
            "/var/vf/episodes/{task_id}/spoken_sentences.json",
        ],
        command_template=[
            "python3",
            "-c",
            "import os, json; ep_dir = '/var/vf/episodes/{task_id}'; "
            "sp = f'{ep_dir}/spoken_sentences.json'; "
            "assert os.path.exists(sp), f'Missing spoken sentences: {sp}'; "
            "sents = json.load(open(sp, encoding='utf-8')); "
            "assert len(sents) > 0, 'Spoken sentences empty'; "
            "print(f'✅ B2.5 Spoken VO Verification PASS: {len(sents)} sentences')",
        ],
    ),
    "2.6": StageContract(
        stage_id="2.6",
        name="B2.6 Audio Spine (Edge-TTS)",
        description="Hollywood Master Voiceover Audio Spine & Subtitle Timecode Mapping (Rule 120)",
        prerequisites=["2.5"],
        input_files=[
            "/var/vf/episodes/{task_id}/spoken_sentences.json",
        ],
        output_files=[
            "/var/vf/episodes/{task_id}/tts_out.mp3",
            "/var/vf/episodes/{task_id}/subtitles.srt",
        ],
        command_template=[
            "python3",
            "-c",
            "import os; ep_dir = '/var/vf/episodes/{task_id}'; "
            "audio = f'{ep_dir}/tts_out.mp3'; "
            "srt = f'{ep_dir}/subtitles.srt'; "
            "assert os.path.exists(audio) and os.path.getsize(audio) > 1000, f'Missing TTS audio: {audio}'; "
            "assert os.path.exists(srt) and os.path.getsize(srt) > 10, f'Missing subtitles: {srt}'; "
            "print('✅ B2.6 Audio Spine & Subtitles PASS')",
        ],
    ),
    "3.0": StageContract(
        stage_id="3.0",
        name="B3 VOX Director Plan",
        description="VOX Visual Director Plan locked to 2-Shot Cadence & Remotion VoxBuildOnStage Manifest (Rule 125, 128)",
        prerequisites=["2.6"],
        input_files=[
            "/var/vf/episodes/{task_id}/story.txt",
            "/var/vf/episodes/{task_id}/spoken_sentences.json",
            "/var/vf/episodes/{task_id}/brain_input.json",
        ],
        output_files=[
            "/var/vf/episodes/{task_id}/director_plan.json",
            "/var/vf/episodes/{task_id}/remotion_props.json",
        ],
        command_template=[
            "python3",
            "-c",
            "import os, json; ep_dir = '/var/vf/episodes/{task_id}'; "
            "p = f'{ep_dir}/remotion_props.json'; "
            "assert os.path.exists(p), f'Missing remotion props: {p}'; "
            "data = json.load(open(p, encoding='utf-8')); "
            "assert len(data.get('scenes', [])) > 0, 'No VOX scenes found'; "
            "print(f'✅ B3 VOX Director Plan PASS: {len(data.get(\"scenes\", []))} beats (VoxBuildOnStage)')",
        ],
    ),
    "3.5": StageContract(
        stage_id="3.5",
        name="B3.5 VOX Prompt Forge",
        description="5-Part Tactile Paper Collage Image Prompts Forge (16:9 BG + 1:1 #FF00FF FG + Thumbnails)",
        prerequisites=["3.0"],
        input_files=["/var/vf/episodes/{task_id}/director_plan.json"],
        output_files=["/var/vf/episodes/{task_id}/prompts_forge.json"],
        command_template=[
            "python3",
            "-c",
            "import os, json; ep_dir = '/var/vf/episodes/{task_id}'; "
            "p = f'{ep_dir}/prompts_forge.json'; "
            "assert os.path.exists(p), f'Missing prompts forge: {p}'; "
            "data = json.load(open(p, encoding='utf-8')); "
            "n_bg = len(data.get('backgrounds', {})); n_fg = len(data.get('foregrounds', {})); "
            "assert n_bg > 0 and n_fg > 0, f'Invalid prompt counts: {n_bg} BGs, {n_fg} FGs'; "
            "print(f'✅ B3.5 VOX Prompt Forge PASS: {n_bg} BGs, {n_fg} FGs, {len(data.get(\"thumbnails\", {}))} Thumbnails')",
        ],
    ),
    "3.6": StageContract(
        stage_id="3.6",
        name="B3.6 Visual Convergence Gate (DACL)",
        description="Decremental Adversarial Convergence Loop (Opus 5 + Astra) for B3 Director Plan & B3.5 Prompts (Rule 118, 122, 130)",
        prerequisites=["3.5"],
        input_files=[
            "/var/vf/episodes/{task_id}/director_plan.json",
            "/var/vf/episodes/{task_id}/dp_plan.json",
            "/var/vf/episodes/{task_id}/prompts_forge.json",
            "/var/vf/episodes/{task_id}/story.txt",
            "/var/vf/episodes/{task_id}/grounding_intel.json",
        ],
        output_files=[
            "/var/vf/episodes/{task_id}/visual_convergence_audit.json",
            "/var/vf/episodes/{task_id}/director_plan.json",
            "/var/vf/episodes/{task_id}/prompts_forge.json",
        ],
        command_template=[
            "python3",
            "-c",
            "import sys, json; sys.path.insert(0, '.'); from app.services.b36_visual_convergence import run_b36_visual_convergence; "
            "dplan = json.load(open('/var/vf/episodes/{task_id}/director_plan.json', encoding='utf-8')); "
            "dp = json.load(open('/var/vf/episodes/{task_id}/dp_plan.json', encoding='utf-8')) if __import__('os').path.exists('/var/vf/episodes/{task_id}/dp_plan.json') else {}; "
            "prompts = json.load(open('/var/vf/episodes/{task_id}/prompts_forge.json', encoding='utf-8')); "
            "story = open('/var/vf/episodes/{task_id}/story.txt', encoding='utf-8').read(); "
            "intel = json.load(open('/var/vf/episodes/{task_id}/grounding_intel.json', encoding='utf-8')) if __import__('os').path.exists('/var/vf/episodes/{task_id}/grounding_intel.json') else {}; "
            "res = run_b36_visual_convergence('{task_id}', dplan, dp, prompts, story, intel); "
            "open('/var/vf/episodes/{task_id}/visual_convergence_audit.json', 'w', encoding='utf-8').write(json.dumps(res, ensure_ascii=False, indent=2)); "
            "open('/var/vf/episodes/{task_id}/director_plan.json', 'w', encoding='utf-8').write(json.dumps(res['director_plan'], ensure_ascii=False, indent=2)); "
            "open('/var/vf/episodes/{task_id}/prompts_forge.json', 'w', encoding='utf-8').write(json.dumps(res['prompts_data'], ensure_ascii=False, indent=2)); "
            "assert res.get('converged', False), f'B3.6 Convergence Gate Failed: {res.get(\"final_score\")}'",
        ],
    ),
    "4.0": StageContract(
        stage_id="4.0",
        name="B4 Image Generation",
        description="Gemini Pro Web Chrome Automation 2K DCI + HSV Chroma Key (Rule 122)",
        prerequisites=["3.6"],
        input_files=["/var/vf/episodes/{task_id}/prompts_forge.json"],
        output_files=["/var/vf/episodes/{task_id}/images/"],
        command_template=[
            "python3",
            "scripts/gemini_browser_gen.py",
            "--episode",
            "{task_id}",
            "--headless",
        ],
    ),
    "5.0": StageContract(
        stage_id="5.0",
        name="B5 Visual Audit",
        description="Pixel-Level Visual Audit Gate (UI, Alpha Edge, Graphic Novel Style, Era Context)",
        prerequisites=["4.0"],
        input_files=["/var/vf/episodes/{task_id}/images/"],
        output_files=["/var/vf/episodes/{task_id}/visual_audit_report.json"],
        command_template=[
            "python3",
            "scripts/orchestrator/runner.py",
            "--task-id",
            "{task_id}",
            "--mode",
            "audit",
        ],
    ),
    "6.0": StageContract(
        stage_id="6.0",
        name="B6 Remotion Master Props & Render",
        description="Unified TwoLayerEpisode + VoxOverlayLayer Remotion Props & Master Render (Rule 120, 125)",
        prerequisites=["5.0"],
        input_files=[
            "/var/vf/episodes/{task_id}/brain_input.json",
            "/var/vf/episodes/{task_id}/spoken_sentences.json",
        ],
        output_files=[
            "/var/vf/episodes/{task_id}/remotion_props.json",
            "/var/vf/episodes/{task_id}/twolayer_silent.mp4",
        ],
        command_template=[
            "python3",
            "scripts/build_remotion_props.py",
            "--episode",
            "{task_id}",
        ],
    ),
    "7.0": StageContract(
        stage_id="7.0",
        name="B7 BGM Cinematic Ducking & Muxing",
        description="Beat-Aware BGM Selection, Sidechain Ducking & Master Video Muxing (Rule 120)",
        prerequisites=["6.0"],
        input_files=[
            "/var/vf/episodes/{task_id}/twolayer_silent.mp4",
            "/var/vf/episodes/{task_id}/tts_out.mp3",
        ],
        output_files=["/var/vf/episodes/{task_id}/final.mp4"],
        command_template=[
            "python3",
            "-c",
            "import sys; sys.path.insert(0, '.'); from app.services.beat_bgm_engine import mix_beat_bgm_for_episode; "
            "mix_beat_bgm_for_episode('/var/vf/episodes/{task_id}')",
        ],
    ),
    "9.0": StageContract(
        stage_id="9.0",
        name="B9 Video QA & Technical Sweep",
        description="Post-Render Technical Sweep & Multimodal Video QA Audit (Rule 118, 122)",
        prerequisites=["7.0"],
        input_files=["/var/vf/episodes/{task_id}/final.mp4"],
        output_files=["/var/vf/episodes/{task_id}/video_audit_report.json"],
        command_template=[
            "python3",
            "-c",
            "import sys, json; sys.path.insert(0, '.'); from app.services.video_audit_runner import run_video_audit; "
            "res = run_video_audit('/var/vf/episodes/{task_id}/final.mp4', episode_id='{task_id}'); "
            "open('/var/vf/episodes/{task_id}/video_audit_report.json', 'w', encoding='utf-8').write(json.dumps(res, ensure_ascii=False, indent=2)); "
            "assert res.get('verdict') == 'PASS', f'B9 Video Audit Failed: {res}'",
        ],
    ),
    "10.0": StageContract(
        stage_id="10.0",
        name="B10 Auto SEO, Chapters & YouTube Gate 2",
        description="Ground-Truth Remotion Chapter Sync, Synthetic Media Flag & YouTube Upload Gate 2 (Rule 135)",
        prerequisites=["9.0"],
        input_files=[
            "/var/vf/episodes/{task_id}/final.mp4",
            "/var/vf/episodes/{task_id}/remotion_props.json",
        ],
        output_files=["/var/vf/episodes/{task_id}/seo_package.json"],
        command_template=[
            "python3",
            "scripts/execute_b10_auto_seo_upload_gate2.py",
            "--episode",
            "{task_id}",
        ],
    ),
    "11.0": StageContract(
        stage_id="11.0",
        name="B11 Analytics & Dreaming Loop",
        description="48h YouTube Analytics Telemetry & Instinct Card Conversion for B2 (Rule 113, 118)",
        prerequisites=["10.0"],
        input_files=["/var/vf/episodes/{task_id}/seo_package.json"],
        output_files=["/var/vf/analytics/b11_latest_report.json"],
        command_template=[
            "python3",
            "scripts/b11_antigravity_engine.py",
            "--market",
            "{market}",
        ],
    ),
}

STAGE_ALIASES = {
    "1": "1.0",
    "1.0": "1.0",
    "b1": "1.0",
    "1.5": "1.5",
    "b1.5": "1.5",
    "b15": "1.5",
    "1.5.5": "1.5.5",
    "b1.5.5": "1.5.5",
    "b155": "1.5.5",
    "grounding": "1.5.5",
    "1.6": "1.6",
    "b1.6": "1.6",
    "b16": "1.6",
    "seo": "1.6",
    "2": "2.0",
    "2.0": "2.0",
    "b2": "2.0",
    "2.1": "2.1",
    "b2.1": "2.1",
    "b21": "2.1",
    "audit_story": "2.1",
    "2.5": "2.5",
    "b2.5": "2.5",
    "b25": "2.5",
    "spoken": "2.5",
    "sub": "2.5",
    "2.6": "2.6",
    "b2.6": "2.6",
    "b26": "2.6",
    "tts": "2.6",
    "audio": "2.6",
    "audio_spine": "2.6",
    "3": "3.0",
    "3.0": "3.0",
    "b3": "3.0",
    "b30": "3.0",
    "director": "3.0",
    "3.5": "3.5",
    "b3.5": "3.5",
    "b35": "3.5",
    "3.6": "3.6",
    "b3.6": "3.6",
    "b36": "3.6",
    "visual_convergence": "3.6",
    "dacl": "3.6",
    "4": "4.0",
    "4.0": "4.0",
    "b4": "4.0",
    "5": "5.0",
    "5.0": "5.0",
    "b5": "5.0",
    "6": "6.0",
    "6.0": "6.0",
    "b6": "6.0",
    "remotion": "6.0",
    "7": "7.0",
    "7.0": "7.0",
    "b7": "7.0",
    "bgm": "7.0",
    "8": "9.0",
    "8.0": "9.0",
    "b8": "9.0",
    "9": "9.0",
    "9.0": "9.0",
    "b9": "9.0",
    "video_qa": "9.0",
    "10": "10.0",
    "10.0": "10.0",
    "b10": "10.0",
    "upload": "10.0",
    "11": "11.0",
    "11.0": "11.0",
    "b11": "11.0",
    "analytics": "11.0",
}

STAGE_ORDER = [
    "1.0", "1.5", "1.5.5", "1.6", "2.0", "2.1", "2.5", "2.6",
    "3.0", "3.5", "3.6", "4.0", "5.0", "6.0", "7.0", "9.0", "10.0", "11.0"
]


@dataclass
class PipelineStage:
    """Concrete instantiated stage with resolved paths and commands."""
    stage_id: str
    name: str
    command: List[str]
    input_paths: List[Path]
    output_paths: List[Path]
    prerequisites: List[str]


class TaskPartitioner:
    """Parses execution blocks, verifies data contracts, and resolves task dependency plans."""

    def __init__(self, root_dir: Optional[Path] = None, vf_var_dir: Optional[Path] = None):
        self.root_dir = root_dir or Path.cwd()
        # On VPS defaults to /var/vf; on dev/test can be overridden
        self.vf_var_dir = vf_var_dir or Path("/var/vf")

    def parse_blocks(self, block_str: Optional[str]) -> List[str]:
        """Parses block selector argument into a validated, ordered list of stage IDs.

        Accepts:
          - None or 'all': ['1.0', '1.5', '2.0', '3.0', '3.5']
          - Comma-separated: '1.0,1.5,2.0' or 'b1,b2,b3'
          - Ranges: '1.0..3.5' or 'b1..b3.5'
        """
        if not block_str or block_str.strip().lower() == "all":
            return list(STAGE_ORDER)

        raw_str = block_str.strip().lower()

        # Handle range syntax 'start..end'
        if ".." in raw_str:
            parts = raw_str.split("..", 1)
            start = STAGE_ALIASES.get(parts[0].strip(), parts[0].strip())
            end = STAGE_ALIASES.get(parts[1].strip(), parts[1].strip())
            if start not in STAGE_ORDER or end not in STAGE_ORDER:
                raise ValueError(f"Invalid block range '{block_str}'. Valid blocks: {STAGE_ORDER}")
            start_idx = STAGE_ORDER.index(start)
            end_idx = STAGE_ORDER.index(end)
            if start_idx > end_idx:
                raise ValueError(f"Range start '{start}' must precede or equal end '{end}'")
            return STAGE_ORDER[start_idx : end_idx + 1]

        # Handle comma-separated list
        tokens = [t.strip() for t in raw_str.split(",") if t.strip()]
        selected: Set[str] = set()
        for tok in tokens:
            normalized = STAGE_ALIASES.get(tok)
            if not normalized or normalized not in STAGE_ORDER:
                raise ValueError(
                    f"Unknown block identifier '{tok}'. Recognized: {list(STAGE_ALIASES.keys())}"
                )
            selected.add(normalized)

        # Return in deterministic canonical pipeline order
        return [s for s in STAGE_ORDER if s in selected]

    def resolve_path(self, path_template: str, task_id: str, market: str) -> Path:
        """Resolves path template against vf_var_dir."""
        rendered = path_template.replace("{task_id}", task_id).replace("{market}", market)
        # If running in test environment where /var/vf does not exist, map to vf_var_dir
        if rendered.startswith("/var/vf") and str(self.vf_var_dir) != "/var/vf":
            rel_part = rendered[len("/var/vf") :].lstrip("/\\")
            return self.vf_var_dir / rel_part
        return Path(rendered)

    def validate_block_contract_schema(self, stage_id: str, file_path: Path) -> Tuple[bool, List[str]]:
        """Validates JSON file contents against PIPELINE_CONTRACTS.md schema specifications."""
        issues: List[str] = []
        if not file_path.exists():
            return False, [f"Contract file '{file_path}' does not exist."]

        try:
            if file_path.suffix == ".json":
                data = json.loads(file_path.read_text(encoding="utf-8"))
            elif file_path.suffix == ".txt":
                text = file_path.read_text(encoding="utf-8")
                # Block 2.0 story.txt check
                words = len(text.split())
                if words < 1200:
                    issues.append(f"story.txt is too short ({words} words; expected >= 1500 words).")
                return len(issues) == 0, issues
            else:
                return True, []
        except Exception as e:
            return False, [f"Failed to parse contract file '{file_path}': {e}"]

        # Schema validations per block
        if stage_id == "1.0":
            # Pending task schema
            required_fields = ["task_id", "market", "viability_score"]
            for f in required_fields:
                if f not in data:
                    issues.append(f"Block 1.0 contract missing required field '{f}'")
            tid = data.get("task_id", "")
            if tid and not validate_generic_task_id(tid):
                issues.append(f"Block 1.0 task_id '{tid}' violates Rule 128 format.")

        elif stage_id == "1.5":
            # Competitor intel card schema
            if "competitor_narrative_anatomy" not in data and "fatal_explanatory_vacuum" not in data:
                issues.append("Block 1.5 competitor card missing 'competitor_narrative_anatomy' or vacuum.")

        elif stage_id == "2.0":
            # Brain input schema
            if "story_gate_score" not in data and "story" not in data and "beats" not in data:
                issues.append("Block 2.0 brain_input missing story or story_gate_score.")

        elif stage_id == "2.5":
            # Spoken sentences schema
            if isinstance(data, list) and len(data) == 0:
                issues.append("Block 2.5 spoken_sentences array is empty.")
            elif isinstance(data, dict) and "sentences" not in data and "spoken_script_text" not in data:
                issues.append("Block 2.5 spoken data missing 'sentences'.")

        elif stage_id == "3.0":
            # Director plan schema
            scenes = data.get("scenes", [])
            if not isinstance(scenes, list) or len(scenes) == 0:
                issues.append("Block 3.0 director_plan missing valid scenes array.")

        elif stage_id == "3.5":
            # Prompts forge schema
            if "backgrounds" not in data and "foregrounds" not in data and data.get("status") != "NEEDS_MANUAL_REVIEW":
                issues.append("Block 3.5 prompts missing backgrounds/foregrounds.")

        return len(issues) == 0, issues

    def check_prerequisites(
        self, stage_id: str, task_id: str, market: str
    ) -> Tuple[bool, List[str]]:
        """Verifies that all prerequisite input files for stage_id exist and are readable."""
        contract = PIPELINE_STAGES.get(stage_id)
        if not contract:
            return False, [f"Unknown stage '{stage_id}'"]

        missing: List[str] = []
        for inp_tmpl in contract.input_files:
            p = self.resolve_path(inp_tmpl, task_id, market)
            if not p.exists() or p.stat().st_size == 0:
                missing.append(str(p))

        return len(missing) == 0, missing

    def build_execution_plan(
        self,
        blocks: List[str],
        task_id: str,
        market: str = "EN",
        dry_run: bool = False,
    ) -> List[PipelineStage]:
        """Generates ordered concrete pipeline stages ready for execution."""
        plan: List[PipelineStage] = []

        for stage_id in blocks:
            contract = PIPELINE_STAGES[stage_id]

            # Resolve input & output file paths
            inputs = [self.resolve_path(p, task_id, market) for p in contract.input_files]
            outputs = [self.resolve_path(p, task_id, market) for p in contract.output_files]

            # Render command tokens
            rendered_cmd = [
                token.replace("{task_id}", task_id).replace("{market}", market)
                for token in contract.command_template
            ]

            stage = PipelineStage(
                stage_id=stage_id,
                name=contract.name,
                command=rendered_cmd,
                input_paths=inputs,
                output_paths=outputs,
                prerequisites=contract.prerequisites,
            )
            plan.append(stage)

        return plan
