import json
from pathlib import Path

p = Path("/var/vf/episodes/EN_EP0006_foreign_capital_us_stocks/beat_1_cluster_props.json")
data = json.load(open(p))
for i, s in enumerate(data["scenes"]):
    print(f"Scene {i}:")
    print(f"  background: {s.get('background')}")
    print(f"  foreground: {s.get('foreground')}")
    print(f"  primary_hero: {s.get('primary_hero')}")
    print(f"  linked_secondary: {s.get('linked_secondary_objects')}")
