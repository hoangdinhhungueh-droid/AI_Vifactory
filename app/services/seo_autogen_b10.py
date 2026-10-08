# -*- coding: utf-8 -*-
"""Backward-compatible adapter forwarding to canonical app.services.seo_package_forge (Rule 125)."""
from app.services.seo_package_forge import (
    forge_seo_package,
    sync_exact_chapters_from_remotion,
    get_seo_hook_system_prompt,
    SEO_HOOK_SYSTEM_PROMPT,
)

# Alias for backward compatibility with legacy test callers
generate_seo_packaging = forge_seo_package

__all__ = [
    "forge_seo_package",
    "generate_seo_packaging",
    "sync_exact_chapters_from_remotion",
    "get_seo_hook_system_prompt",
    "SEO_HOOK_SYSTEM_PROMPT",
]
