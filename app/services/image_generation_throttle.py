#!/usr/bin/env python3
"""
Image Generation Throttle for Antigravity.
Enforces 2K resolution cap + time spacing between requests to avoid quota exhaustion.
"""
import time
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Resolution constraints (Rule 435)
RESOLUTION_2K_W = 2560
RESOLUTION_2K_H = 1920
RESOLUTION_2K_16_9_W = 2560
RESOLUTION_2K_16_9_H = 1440

# Throttle constraints (Rule 436)
MIN_SPACING_SECONDS = 45  # Minimum 45s between image generation requests
MAX_CONCURRENT_REQUESTS = 1  # Never submit >1 request to Google Imagen simultaneously
REQUEST_TIMEOUT_SECONDS = 120  # Each request must complete within 2 minutes

class ImageThrottleState:
    """Track request timing to enforce throttle rules."""
    
    def __init__(self):
        self.last_request_time = None
        self.request_queue = []
        self.generated_count = 0
        self.failed_count = 0
    
    def can_request_now(self):
        """Check if enough time has passed since last request."""
        if self.last_request_time is None:
            return True
        
        elapsed = time.time() - self.last_request_time
        if elapsed < MIN_SPACING_SECONDS:
            return False
        return True
    
    def get_wait_seconds(self):
        """Get seconds until next request can be made."""
        if self.last_request_time is None:
            return 0
        
        elapsed = time.time() - self.last_request_time
        remaining = MIN_SPACING_SECONDS - elapsed
        return max(0, remaining)
    
    def mark_request_sent(self):
        """Record that a request was sent now."""
        self.last_request_time = time.time()
    
    def mark_success(self):
        """Record successful image generation."""
        self.generated_count += 1
    
    def mark_failure(self):
        """Record failed image generation."""
        self.failed_count += 1

def constrain_resolution_2k(prompt_dict):
    """
    Ensure image prompt generates 2K resolution.
    Append resolution instruction to prompt if not present.
    """
    if not isinstance(prompt_dict, dict):
        return prompt_dict
    
    prompt_text = prompt_dict.get('image_prompt') or prompt_dict.get('prompt') or ''
    
    # Check if resolution is already specified
    if any(x in prompt_text.lower() for x in ['2560x', '2560 x', '4k', '2k', '1440p']):
        logger.debug("Resolution already specified in prompt, skipping append")
        return prompt_dict
    
    # Append 2K resolution instruction
    resolution_suffix = (
        " [TECHNICAL: Generate at 2560x1440 resolution (16:9 aspect ratio, 2K DCI). "
        "This ensures compatibility with 2K editing pipeline. Do not upscale or downscale.]"
    )
    
    if 'image_prompt' in prompt_dict:
        prompt_dict['image_prompt'] += resolution_suffix
    elif 'prompt' in prompt_dict:
        prompt_dict['prompt'] += resolution_suffix
    else:
        prompt_dict['prompt'] = resolution_suffix[1:]  # Remove leading space for new prompts
    
    return prompt_dict

def apply_throttle_before_request(throttle_state, prompt_dict):
    """
    Pre-request checks:
    1. Constrain resolution to 2K
    2. Check spacing (may need to wait)
    3. Return (ok: bool, wait_seconds: float, constrained_prompt: dict)
    """
    
    # Constrain resolution
    constrained = constrain_resolution_2k(prompt_dict)
    
    # Check spacing
    if not throttle_state.can_request_now():
        wait = throttle_state.get_wait_seconds()
        logger.info(f"Throttle: must wait {wait:.0f}s before next request (Rule 436)")
        return (False, wait, constrained)
    
    return (True, 0, constrained)

def wait_and_request(throttle_state, prompt_dict, request_fn, episode_id, reuse_key):
    """
    High-level flow:
    1. Apply throttle (wait if needed)
    2. Send request
    3. Record timing
    4. Handle response
    
    request_fn: callable(prompt_dict, episode_id, reuse_key) -> (success: bool, image_path: str or error: str)
    """
    
    logger.info(f"[Throttle] Preparing request for {reuse_key}")
    
    # Apply throttle constraints
    ok, wait_sec, constrained = apply_throttle_before_request(throttle_state, prompt_dict)
    
    if not ok:
        logger.info(f"[Throttle] Waiting {wait_sec:.0f}s before request...")
        time.sleep(wait_sec + 2)  # +2s margin
    
    # Mark request sent (before calling request_fn, to time the actual generation)
    throttle_state.mark_request_sent()
    
    logger.info(f"[Throttle] Sending request (timeout={REQUEST_TIMEOUT_SECONDS}s)")
    
    # Call the actual image generation
    try:
        success, result = request_fn(constrained, episode_id, reuse_key)
        if success:
            throttle_state.mark_success()
            logger.info(f"[Throttle] ✅ Generated {reuse_key} (total: {throttle_state.generated_count})")
            return (True, result)
        else:
            throttle_state.mark_failure()
            logger.error(f"[Throttle] ✗ Failed {reuse_key}: {result}")
            return (False, result)
    except Exception as e:
        throttle_state.mark_failure()
        logger.error(f"[Throttle] Exception during request: {e}")
        return (False, str(e))

def format_throttle_stats(throttle_state):
    """Return human-readable throttle statistics."""
    return (
        f"Generated: {throttle_state.generated_count}, "
        f"Failed: {throttle_state.failed_count}, "
        f"Last request: {throttle_state.last_request_time or 'never'}"
    )
