# PATCH for run_episode.py - Issue #5: UnboundLocalError on clip_paths
# 
# ROOT CAUSE:
# - clip_paths initialized at line 463 (S5 section)
# - Used at line 617 (result dictionary)
# - S4.5 coverage check (line 422) can raise RuntimeError, skipping S5
# - Error handling code then references uninitialized clip_paths
#
# FIX:
# Add this line after line 148 (after os.makedirs):
#
#     clip_paths = []  # BUG FIX 01/09/2026: initialize early to prevent UnboundLocalError
#
# LOCATION: Insert after this block:
#     t0 = time.time()
#     out_dir = os.path.join("/var/vf/episodes", episode_id)
#     os.makedirs(out_dir, exist_ok=True)
#     clip_paths = []  # <-- ADD THIS LINE
#
# The existing line 463 assignment will still work correctly (it reassigns the list).

# MINIMAL SURGICAL PATCH - EXACT TEXT TO ADD:

AFTER_LINE_148 = '''    t0 = time.time()
    out_dir = os.path.join("/var/vf/episodes", episode_id)
    os.makedirs(out_dir, exist_ok=True)'''

REPLACEMENT = '''    t0 = time.time()
    out_dir = os.path.join("/var/vf/episodes", episode_id)
    os.makedirs(out_dir, exist_ok=True)

    # BUG FIX 01/09/2026 (Issue #5): Initialize clip_paths early to prevent
    # UnboundLocalError when S4.5 coverage check raises RuntimeError before
    # S5 runs. Line 463 will reassign this during normal S5 execution.
    clip_paths = []'''
