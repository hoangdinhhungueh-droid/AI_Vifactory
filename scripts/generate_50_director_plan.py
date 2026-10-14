"""
scripts/generate_50_director_plan.py — Canonical B3 Dispatcher Wrapper (Rule 119)
Redirects legacy calls to app.services.director_planner_b3.generate_director_plan.
"""
import sys
from pathlib import Path
sys.path.insert(0, '/root/video_factory')
from app.services.director_planner_b3 import generate_director_plan

# Canonical Director Planner Dispatcher (Rule 125 Single Pipeline Truth)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/generate_50_director_plan.py <episode_id>")
        sys.exit(1)
    ep_id = sys.argv[1]
    plan = generate_director_plan(ep_id)
    print(f"✅ Successfully generated Director Plan for {ep_id}: {plan['total_scenes']} scenes.")
