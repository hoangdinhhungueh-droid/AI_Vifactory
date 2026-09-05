"""
scripts/generate_50_director_plan.py — Canonical B3 Dispatcher Wrapper (Rule 119)
Redirects legacy calls to app.services.director_planner_b3.generate_director_plan.
"""
import sys
from pathlib import Path
sys.path.insert(0, '/root/video_factory')
from app.services.director_planner_b3 import generate_director_plan

# Canonical alias
generate_50_scene_plan = generate_director_plan

if __name__ == "__main__":
    ep_id = sys.argv[1] if len(sys.argv) > 1 else "en-byzantine-empire-ep001"
    plan = generate_director_plan(ep_id)
    print(f"✅ Successfully generated Director Plan for {ep_id}: {plan['total_scenes']} scenes.")
