from app.services.episode_images import _generate_thumbnail_prompt
import json

with open("/var/vf/episodes/en-byzantine-empire-ep001/brain_input.json") as f:
    brain = json.load(f)

print(_generate_thumbnail_prompt(brain))
