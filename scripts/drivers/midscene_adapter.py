"""
Midscene.js-Inspired Semantic Automation Adapter for Playwright.
Provides Record-to-Replay caching mechanism for UI automation (Google Flow, Gemini Web, YouTube Studio),
eliminating brittle CSS selector churn and achieving deterministic runs at $0 token cost.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("midscene_adapter")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(asctime)s][%(levelname)s][midscene_adapter] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

DEFAULT_CACHE_PATH = Path("config/midscene_action_cache.json")


@dataclass
class CachedActionRecord:
    semantic_target: str
    url_pattern: str
    resolved_selectors: List[str] = field(default_factory=list)
    hit_count: int = 0
    last_success_ts: float = field(default_factory=time.time)
    attributes: Dict[str, Any] = field(default_factory=dict)


class MidsceneAdapter:
    """
    Midscene Record-to-Replay Action Adapter.
    Caches verified DOM selectors for high-level semantic intents.
    """

    def __init__(self, cache_file: Path | str = DEFAULT_CACHE_PATH):
        self.cache_file = Path(cache_file)
        self.cache: Dict[str, CachedActionRecord] = {}
        self._load_cache()

    def _get_cache_key(self, url: str, semantic_target: str) -> str:
        # Normalize url domain/path pattern
        clean_url = url.split("?")[0].split("#")[0]
        # Extract host or main section
        return f"{clean_url}::{semantic_target.strip().lower()}"

    def _load_cache(self) -> None:
        if not self.cache_file.exists():
            self.cache = {}
            return
        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.cache = {
                k: CachedActionRecord(**v) for k, v in data.items() if isinstance(v, dict)
            }
            logger.info("Loaded %d action records from cache %s", len(self.cache), self.cache_file)
        except Exception as e:
            logger.warning("Failed to load cache from %s: %s. Starting with empty cache.", self.cache_file, e)
            self.cache = {}

    def _save_cache(self) -> None:
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            temp_file = self.cache_file.with_suffix(".tmp")
            data = {k: asdict(v) for k, v in self.cache.items()}
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            temp_file.replace(self.cache_file)
            logger.debug("Persisted %d records to cache %s", len(self.cache), self.cache_file)
        except Exception as e:
            logger.warning("Could not persist cache to %s: %s", self.cache_file, e)

    def resolve_selector(
        self,
        page: Any,
        semantic_target: str,
        heuristic_selectors: Optional[List[str]] = None,
        timeout_ms: int = 5000,
    ) -> Optional[str]:
        """
        Locates the element using cached selector first ($0 cost Replay).
        If cache misses or selector is obsolete, tries heuristic selectors and records the working one.
        """
        url = page.url if hasattr(page, "url") else ""
        cache_key = self._get_cache_key(url, semantic_target)

        # 1. Phase: Replay Cache
        if cache_key in self.cache:
            record = self.cache[cache_key]
            for selector in record.resolved_selectors:
                try:
                    elem = page.query_selector(selector)
                    if elem and elem.is_visible():
                        record.hit_count += 1
                        record.last_success_ts = time.time()
                        self._save_cache()
                        logger.info(
                            "[Midscene Replay] Hit cached selector '%s' for '%s' (hits=%d)",
                            selector,
                            semantic_target,
                            record.hit_count,
                        )
                        return selector
                except Exception as e:
                    logger.debug("Cached selector '%s' check error: %s", selector, e)

        # 2. Phase: Heuristic Discovery & Self-Healing
        candidates = heuristic_selectors or []
        # Add basic fallback patterns based on semantic_target
        clean_target = semantic_target.replace("_", " ").strip()
        candidates.extend([
            f'button:has-text("{clean_target}")',
            f'a:has-text("{clean_target}")',
            f'[aria-label*="{clean_target}" i]',
            f'[data-testid*="{semantic_target}" i]',
            f'[title*="{clean_target}" i]',
        ])

        start_time = time.time()
        while (time.time() - start_time) * 1000 < timeout_ms:
            for selector in candidates:
                try:
                    elem = page.query_selector(selector)
                    if elem and elem.is_visible():
                        logger.info(
                            "[Midscene Discover] Discovered working selector '%s' for target '%s'",
                            selector,
                            semantic_target,
                        )
                        # Record into cache
                        existing_selectors = (
                            self.cache[cache_key].resolved_selectors if cache_key in self.cache else []
                        )
                        new_selectors = [selector] + [s for s in existing_selectors if s != selector]
                        self.cache[cache_key] = CachedActionRecord(
                            semantic_target=semantic_target,
                            url_pattern=url.split("?")[0],
                            resolved_selectors=new_selectors,
                            hit_count=1,
                            last_success_ts=time.time(),
                        )
                        self._save_cache()
                        return selector
                except Exception as e:
                    logger.debug("Candidate selector '%s' error: %s", selector, e)
            time.sleep(0.2)

        logger.warning(
            "[Midscene] Could not resolve selector for target '%s' after %d ms",
            semantic_target,
            timeout_ms,
        )
        return None

    def ai_click(
        self,
        page: Any,
        semantic_target: str,
        heuristic_selectors: Optional[List[str]] = None,
        timeout_ms: int = 5000,
    ) -> bool:
        """
        Executes a robust semantic click via Record-to-Replay selector lookup.
        """
        selector = self.resolve_selector(page, semantic_target, heuristic_selectors, timeout_ms)
        if not selector:
            return False
        try:
            elem = page.query_selector(selector)
            if elem:
                elem.scroll_into_view_if_needed()
                elem.click()
                return True
        except Exception as e:
            logger.error("Failed to click element with selector '%s': %s", selector, e)
        return False

    def ai_fill(
        self,
        page: Any,
        semantic_target: str,
        text: str,
        heuristic_selectors: Optional[List[str]] = None,
        timeout_ms: int = 5000,
    ) -> bool:
        """
        Executes a semantic input fill via Record-to-Replay selector lookup.
        """
        selector = self.resolve_selector(page, semantic_target, heuristic_selectors, timeout_ms)
        if not selector:
            return False
        try:
            elem = page.query_selector(selector)
            if elem:
                elem.scroll_into_view_if_needed()
                elem.fill(text)
                return True
        except Exception as e:
            logger.error("Failed to fill input with selector '%s': %s", selector, e)
        return False
