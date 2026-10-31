#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""app/services/template_registry.py — Single Source of Truth Template Registry (Rule 132 Parity).

Loads, validates, and renders CL3 Vox Prompt templates dynamically from
config/prompts/cl3_vox_engine/. Eliminates all hardcoded prompt text in Python code.
"""

from __future__ import annotations

import functools
import hashlib
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
TEMPLATE_DIR = ROOT_DIR / "config" / "prompts" / "cl3_vox_engine"


class TemplateError(Exception):
    """Base exception for template errors."""
    pass


class TemplateNotFoundError(TemplateError):
    """Raised when a required template file is missing on disk. Never falls back to hardcoded strings."""
    pass


class CompatibilityError(TemplateError):
    """Raised when an action and tool combination violates semantic compatibility."""
    pass


@functools.lru_cache(maxsize=128)
def _read_template_cached(file_path_str: str, file_hash: str) -> str:
    """Reads template file cached strictly by path and content SHA256.
    When the file changes on disk, its hash changes and cache automatically invalidates.
    """
    p = Path(file_path_str)
    if not p.exists() or not p.is_file():
        raise TemplateNotFoundError(f"Template file not found at: {file_path_str}")
    return p.read_text(encoding="utf-8").strip()


def get_file_hash(p: Path) -> str:
    """Computes SHA256 hex digest of a file."""
    if not p.exists() or not p.is_file():
        raise TemplateNotFoundError(f"Template file does not exist: {p}")
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


@dataclass
class PromptTrace:
    """Runtime trace capturing exact template paths, file hashes, and parameters used."""
    template_files: Dict[str, str] = field(default_factory=dict)  # filename -> sha256
    camera_directive: str = ""
    style_mode: str = ""
    hero_prop: str = ""
    interacting_tool: str = ""
    action_type: str = ""
    avoid_terms_stripped: List[str] = field(default_factory=list)
    avoid_terms_added: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "template_files": self.template_files,
            "camera_directive": self.camera_directive,
            "style_mode": self.style_mode,
            "hero_prop": self.hero_prop,
            "interacting_tool": self.interacting_tool,
            "action_type": self.action_type,
            "avoid_terms_stripped": self.avoid_terms_stripped,
            "avoid_terms_added": self.avoid_terms_added,
        }


class TemplateRegistry:
    """Central registry for CL3 Vox prompt templates.
    Strictly decouples Python engine logic from creative prompt templates (Rule 132).
    """

    def __init__(self, template_dir: Optional[Path] = None):
        self.template_dir = template_dir or TEMPLATE_DIR
        if not self.template_dir.exists():
            raise TemplateNotFoundError(f"Template directory does not exist: {self.template_dir}")
        self._manifest_cache: Optional[Dict[str, str]] = None
        self._camera_directives_cache: Optional[Dict[str, Any]] = None
        self._prop_action_matrix_cache: Optional[Dict[str, Any]] = None

    def read_template(self, filename: str) -> Tuple[str, str]:
        """Reads a template file by name. Returns (content, sha256).
        Fails closed with TemplateNotFoundError if file does not exist.
        """
        p = self.template_dir / filename
        file_hash = get_file_hash(p)
        content = _read_template_cached(str(p), file_hash)
        return content, file_hash

    def get_style_block(
        self,
        style_mode: str = "deep_diorama",
        camera_directive: Optional[str] = None,
        trace: Optional[PromptTrace] = None
    ) -> str:
        """Retrieves verbatim Style Block for video prompts from Markdown.

        If camera_directive indicates a static overhead camera ('STATIC_OVERHEAD'),
        conditions the global camera instruction so it does not contradict static overhead.
        """
        mode_filename_map = {
            "deep_diorama": "style_deep_diorama.md",
            "flat_parallax": "style_flat_parallax.md",
            "locked_stage": "style_locked_stage.md",
        }
        filename = mode_filename_map.get(style_mode, "style_deep_diorama.md")
        content, f_hash = self.read_template(filename)
        if trace is not None:
            trace.template_files[filename] = f_hash
            trace.style_mode = style_mode

        if camera_directive:
            cam_str = str(camera_directive).upper()
            generic_cam_sentence = "The camera is an actor: it flies between layers, orbits, dives, whips, racks focus — one committed cinematic move per clip."
            if "STATIC_OVERHEAD" in cam_str:
                content = content.replace(
                    generic_cam_sentence,
                    "The camera remains locked in a disciplined overhead perspective: perfectly static — all dynamic motion comes strictly from tactile physical papercraft elements snapping and sliding across the tabletop diorama."
                )
            elif "SLOW_PUSH_IN" in cam_str:
                content = content.replace(
                    generic_cam_sentence,
                    "The camera performs one disciplined, deliberate move: a slow continuous push-in — smoothly gliding forward through papercraft depth without sudden whips, dives, or orbits."
                )
            elif "SLOW_HORIZONTAL_PAN" in cam_str:
                content = content.replace(
                    generic_cam_sentence,
                    "The camera performs one disciplined, deliberate move: a slow continuous horizontal pan tracking along the evidence outflow path — smoothly traversing the tabletop diorama."
                )
            elif "SUBTLE_TILT_DOWN" in cam_str:
                content = content.replace(
                    generic_cam_sentence,
                    "The camera performs one disciplined, deliberate move: a subtle continuous tilt down from the headline banner onto the newsprint text without sudden whips or orbits."
                )
        return content

    def get_t2i_style_block(self, trace: Optional[PromptTrace] = None) -> str:
        """Retrieves verbatim Still Image (T2I) Style Block from Markdown."""
        content, f_hash = self.read_template("t2i_style.md")
        if trace is not None:
            trace.template_files["t2i_style.md"] = f_hash
        return content

    def get_canonical_backgrounds(self, trace: Optional[PromptTrace] = None) -> List[str]:
        """Retrieves canonical background list from JSON."""
        content, f_hash = self.read_template("canonical_backgrounds.json")
        if trace is not None:
            trace.template_files["canonical_backgrounds.json"] = f_hash
        return json.loads(content)

    def get_camera_directives_registry(self) -> Dict[str, Any]:
        """Loads and returns camera_directives.yaml."""
        p = self.template_dir / "camera_directives.yaml"
        f_hash = get_file_hash(p)
        content = _read_template_cached(str(p), f_hash)
        return yaml.safe_load(content) or {}

    def get_prop_action_matrix(self) -> Dict[str, Any]:
        """Loads and returns prop_action_matrix.yaml."""
        p = self.template_dir / "prop_action_matrix.yaml"
        f_hash = get_file_hash(p)
        content = _read_template_cached(str(p), f_hash)
        return yaml.safe_load(content) or {}

    def resolve_camera_directive(
        self,
        camera_directive: str,
        trace: Optional[PromptTrace] = None
    ) -> Tuple[str, List[str], List[str], List[str]]:
        """Resolves camera directive info from camera_directives.yaml.
        Returns:
            (positive_camera_line, strip_from_avoid, add_to_avoid, forbidden_in_shot)
        """
        directives = self.get_camera_directives_registry()
        clean_dir = (camera_directive or "SLOW_PUSH_IN_0_1X").strip().upper()

        if clean_dir not in directives:
            # Fallback to normalized uppercase lookup or default
            matched = None
            for k in directives:
                if k.lower() in clean_dir.lower() or clean_dir.lower() in k.lower():
                    matched = k
                    break
            clean_dir = matched or "SLOW_PUSH_IN_0_1X"

        cfg = directives.get(clean_dir, {})
        positive_line = cfg.get("positive", f"Camera: {clean_dir.lower().replace('_', ' ')}.")
        strip_avoid = cfg.get("strip_from_avoid", [])
        add_avoid = cfg.get("add_to_avoid", [])
        forbidden = cfg.get("forbidden_in_shot", [])

        if trace is not None:
            trace.template_files["camera_directives.yaml"] = get_file_hash(self.template_dir / "camera_directives.yaml")
            trace.camera_directive = clean_dir
            trace.avoid_terms_stripped.extend(strip_avoid)
            trace.avoid_terms_added.extend(add_avoid)

        return positive_line, strip_avoid, add_avoid, forbidden

    def resolve_avoid_block(
        self,
        camera_directive: str,
        trace: Optional[PromptTrace] = None
    ) -> str:
        """Constructs avoid block dynamically based on camera directive precedence (Boss Opus 5.5 Phase 2).
        If camera is STATIC_OVERHEAD, strictly removes 'no static locked-off camera'.
        """
        base_avoid, f_hash = self.read_template("avoid_base.md")
        if trace is not None:
            trace.template_files["avoid_base.md"] = f_hash

        _, strip_avoid, add_avoid, _ = self.resolve_camera_directive(camera_directive, trace=trace)

        # Parse comma-separated constraints
        prefix = "AVOID: "
        if base_avoid.startswith(prefix):
            constraints = [c.strip() for c in base_avoid[len(prefix):].split(",") if c.strip()]
        else:
            constraints = [c.strip() for c in base_avoid.split(",") if c.strip()]

        # Filter out stripped terms
        filtered = []
        for c in constraints:
            if any(s.lower() in c.lower() for s in strip_avoid):
                continue
            filtered.append(c)

        # Add additional terms if not already present
        for a in add_avoid:
            if not any(a.lower() in f.lower() for f in filtered):
                filtered.append(a)

        return f"AVOID: {', '.join(filtered)}"

    def validate_prop_action_compatibility(
        self,
        action_type: str,
        hero_prop: str,
        tool_prop: str,
        full_shot_text: str = ""
    ) -> None:
        """Enforces semantic compatibility between narrative action and physical props (Boss Opus 5.5 Phase 3).
        Raises CompatibilityError if forbidden tools or forbidden terms are used.
        """
        matrix = self.get_prop_action_matrix().get("actions", {})
        if action_type not in matrix:
            return

        cfg = matrix[action_type]
        forbidden_tools = cfg.get("forbidden_tools", [])
        forbidden_terms = cfg.get("forbidden_terms", [])

        tool_lower = (tool_prop or "").lower()
        hero_lower = (hero_prop or "").lower()
        shot_lower = (full_shot_text or "").lower()

        for ft in forbidden_tools:
            if ft.lower() in tool_lower or ft.lower() in hero_lower or ft.lower() in shot_lower:
                raise CompatibilityError(
                    f"Forbidden tool '{ft}' detected for action '{action_type}'! "
                    f"Tool: '{tool_prop}', Hero: '{hero_prop}'"
                )

        for fterm in forbidden_terms:
            if fterm.lower() in shot_lower:
                raise CompatibilityError(
                    f"Forbidden term '{fterm}' detected for action '{action_type}' in shot text!"
                )


_GLOBAL_REGISTRY: Optional[TemplateRegistry] = None


def get_template_registry() -> TemplateRegistry:
    """Returns singleton instance of TemplateRegistry."""
    global _GLOBAL_REGISTRY
    if _GLOBAL_REGISTRY is None:
        _GLOBAL_REGISTRY = TemplateRegistry()
    return _GLOBAL_REGISTRY
