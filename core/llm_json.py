#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""core/llm_json.py — Resilient LLM JSON Extraction & Parsing Engine (Rule 125, 139).

Guarantees robust parsing of JSON structures emitted by LLMs (Claude, GPT, Kimi, Gemini),
handling markdown code blocks, comments, trailing commas, unescaped quotes, and missing closing brackets.
Falls back gracefully without raising syntax errors for minor LLM formatting variations.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Union

logger = logging.getLogger(__name__)


def parse_llm_json(raw_text: str) -> Union[Dict[str, Any], List[Any]]:
    """Extracts and parses a JSON object or array from raw LLM output text.

    Tries in sequence:
    1. json_repair.repair_json (if installed)
    2. Direct json.loads on extracted outermost JSON chunk
    3. Multi-pass trailing comma elimination
    4. Comment stripping (// and /* */)
    5. Structural bracket balancing for truncated completions
    """
    if not raw_text or not raw_text.strip():
        raise ValueError("Cannot parse JSON from empty or whitespace string.")

    cleaned = raw_text.strip()

    # Fast path via json_repair if available
    try:
        import json_repair
        repaired_obj = json_repair.repair_json(cleaned, return_objects=True)
        if isinstance(repaired_obj, (dict, list)) and len(repaired_obj) > 0:
            return repaired_obj
    except Exception as _jr_err:
        logger.debug("[llm_json] json_repair fast path error: %s", _jr_err)

    # 1. Strip markdown fences if present
    if "```json" in cleaned:
        cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in cleaned:
        cleaned = cleaned.split("```", 1)[1].split("```", 1)[0].strip()

    # 2. Extract outermost matching bracket pair
    start_curly = cleaned.find("{")
    start_square = cleaned.find("[")

    if start_curly != -1 and (start_square == -1 or start_curly < start_square):
        end_curly = cleaned.rfind("}")
        target_str = cleaned[start_curly:end_curly + 1] if end_curly > start_curly else cleaned[start_curly:]
    elif start_square != -1:
        end_square = cleaned.rfind("]")
        target_str = cleaned[start_square:end_square + 1] if end_square > start_square else cleaned[start_square:]
    else:
        target_str = cleaned

    # Attempt 1: Direct parse
    try:
        return json.loads(target_str)
    except (json.JSONDecodeError, ValueError) as _err1:
        logger.debug("[llm_json] Direct parse unviable: %s", _err1)

    # Attempt 2: Trailing comma elimination loop
    repaired = target_str
    for _ in range(10):
        new_repaired, count = re.subn(r',\s*([\]}])', r'\1', repaired)
        if count == 0:
            break
        repaired = new_repaired

    try:
        return json.loads(repaired)
    except (json.JSONDecodeError, ValueError) as _err2:
        logger.debug("[llm_json] Trailing comma repair unviable: %s", _err2)

    # Attempt 3: Strip C/C++ style comments
    repaired_no_comments = re.sub(r'//.*?\n', '\n', repaired)
    repaired_no_comments = re.sub(r'/\*.*?\*/', '', repaired_no_comments, flags=re.DOTALL)
    try:
        return json.loads(repaired_no_comments)
    except (json.JSONDecodeError, ValueError) as _err3:
        logger.debug("[llm_json] Comment strip repair unviable: %s", _err3)

    # Attempt 4: Fix unclosed brackets from truncation
    open_curlies = repaired_no_comments.count("{") - repaired_no_comments.count("}")
    open_squares = repaired_no_comments.count("[") - repaired_no_comments.count("]")
    if open_curlies > 0 or open_squares > 0:
        fixed_closing = repaired_no_comments.rstrip()
        if fixed_closing.endswith(","):
            fixed_closing = fixed_closing[:-1]
        fixed_closing = fixed_closing + ("]" * max(0, open_squares)) + ("}" * max(0, open_curlies))
        try:
            return json.loads(fixed_closing)
        except (json.JSONDecodeError, ValueError) as _err4:
            logger.debug("[llm_json] Bracket balance repair unviable: %s", _err4)

    # Final attempt: raise standard error with context
    return json.loads(repaired)
