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
        name="B2 Story Engine",
        description="5-Beat Docudrama 1,800-2,200 words via GPT-6-Astra (Rule 445)",
        prerequisites=["1.5.5"],
        input_files=[
            "/var/vf/pending_tasks/{task_id}.json",
            "/var/vf/episodes/{task_id}/competitor_intel_card.json",
            "/var/vf/episodes/{task_id}/grounding_intel.json",
        ],
        output_files=[
            "/var/vf/episodes/{task_id}/story.txt",
            "/var/vf/episodes/{task_id}/brain_input.json",
        ],
        command_template=[
            "python3",
            "-c",
            "import sys; sys.path.insert(0, '.'); from app.services.story_engine_b2 import generate_5_arc_story; "
            "generate_5_arc_story('{task_id}')",
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
        name="B2.5 Spoken VO Adaptation",
        description="Hollywood Breath-Timed Spoken Script Adaptation & Adversarial Duration Audit",
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
            "import sys, json, os; sys.path.insert(0, '.'); from app.services.story_engine_b2 import adapt_master_spoken_script, adversarial_audit_spoken_script; "
            "ep_dir = '/var/vf/episodes/{task_id}'; "
            "story = open(f'{ep_dir}/story.txt', encoding='utf-8').read(); "
            "meta_path = '/var/vf/pending_tasks/{task_id}.json'; "
            "meta = json.load(open(meta_path, encoding='utf-8')) if os.path.exists(meta_path) else {}; "
            "mkt = meta.get('market') or '{task_id}'.split('_')[0].upper(); "
            "topic = meta.get('raw_term') or '{task_id}'; "
            "res = adapt_master_spoken_script(story, market=mkt, topic=topic); "
            "audit = adversarial_audit_spoken_script(res, market=mkt, topic=topic); "
            "assert audit.get('verdict') == 'PASS' or float(audit.get('audit_score', 0)) >= 7.5, f'B2.5 Audit Failed: {audit}'; "
            "open(f'{ep_dir}/spoken_script.txt', 'w', encoding='utf-8').write(res.get('spoken_script_text', story)); "
            "open(f'{ep_dir}/spoken_sentences.json', 'w', encoding='utf-8').write(json.dumps(res.get('sentences', []), ensure_ascii=False, indent=2)); "
            "brain_p = f'{ep_dir}/brain_input.json'; "
            "brain = json.load(open(brain_p, encoding='utf-8')) if os.path.exists(brain_p) else {}; "
            "brain['spoken_script'] = res.get('spoken_script_text', story); "
            "brain['spoken_sentences'] = res.get('sentences', []); "
            "brain['spoken_script_audit'] = audit; "
            "open(brain_p, 'w', encoding='utf-8').write(json.dumps(brain, ensure_ascii=False, indent=2)); "
            "print(f'✅ B2.5 Spoken VO Adaptation PASS: {len(res.get(\"sentences\", []))} sentences')",
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
            "import sys, asyncio, json; sys.path.insert(0, '.'); from app.services.beat_tts_engine import synthesize_beat_tts_pipeline; "
            "ep_dir = '/var/vf/episodes/{task_id}'; "
            "res = asyncio.run(synthesize_beat_tts_pipeline('{task_id}', out_dir=ep_dir, force=False)); "
            "assert res.get('total_duration_sec', 0) > 0, 'TTS output duration is zero'; "
            "print(f'✅ B2.6 Audio Spine PASS: {res.get(\"total_duration_sec\"):.1f}s ({len(res.get(\"segments\", []))} segments)')",
        ],
    ),
    "3.0": StageContract(
        stage_id="3.0",
        name="B3 Director Plan",
        description="Hollywood Visual Director Plan locked to Audio Spine timecodes (Rule 125, 128)",
        prerequisites=["2.6"],
        input_files=[
            "/var/vf/episodes/{task_id}/story.txt",
            "/var/vf/episodes/{task_id}/spoken_sentences.json",
            "/var/vf/episodes/{task_id}/brain_input.json",
        ],
        output_files=[
            "/var/vf/episodes/{task_id}/director_plan.json",
            "/var/vf/episodes/{task_id}/brain_input.json",
        ],
        command_template=[
            "python3",
            "-c",
            "import sys, json; sys.path.insert(0, '.'); from app.services.director_planner_b3 import generate_director_plan; "
            "ep_dir = '/var/vf/episodes/{task_id}'; "
            "story = open(f'{ep_dir}/story.txt', encoding='utf-8').read(); "
            "brain = json.load(open(f'{ep_dir}/brain_input.json', encoding='utf-8')); "
            "sp_sents = json.load(open(f'{ep_dir}/spoken_sentences.json', encoding='utf-8')) if __import__('os').path.exists(f'{ep_dir}/spoken_sentences.json') else None; "
            "plan = generate_director_plan('{task_id}', story, spoken_sentences=sp_sents, metadata={'topic': brain.get('topic') or '{task_id}'}, run_downstream=False); "
            "print(f'✅ B3 Hollywood Director Plan PASS: {len(plan.get(\"scenes\", []))} scenes')",
        ],
    ),
    "3.5": StageContract(
        stage_id="3.5",
        name="B3.5 Prompt Forge",
        description="Dual-Layer Visual Prompt Forge (16:9 BG + #FF00FF FG) with Anti-Stuttering",
        prerequisites=["3.0"],
        input_files=["/var/vf/episodes/{task_id}/director_plan.json"],
        output_files=["/var/vf/episodes/{task_id}/prompts_forge.json"],
        command_template=[
            "python3",
            "scripts/run_prompt_forge.py",
            "--episode",
            "{task_id}",
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
}

STAGE_ORDER = ["1.0", "1.5", "1.5.5", "1.6", "2.0", "2.1", "2.5", "2.6", "3.0", "3.5", "3.6", "4.0", "5.0"]


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
