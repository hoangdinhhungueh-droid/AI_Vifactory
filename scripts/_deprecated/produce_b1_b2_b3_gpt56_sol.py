import os, sys, json, time, re

sys.path.insert(0, '/root/video_factory')
import scripts.compile_episode_from_notion as comp
comp._token()

from app.services.hhtech_reasoner import call_gpt56_sol
from app.services import story_gate as sgate
from scripts.ag_notion_bridge import resolve_id, update_page_properties, create_page
from scripts.skill_ai_live import load_skill_ai_live

print('=== [Skill AI] Loading LIVE skill context from Notion (Rule 121 - mandatory fresh load) ===')
SKILL_AI_CONTEXT = load_skill_ai_live()

from app.services.trend_gate_ai import get_next_episode_id
episode_id = get_next_episode_id("en", "byzantine-empire")
print(f"Rule 117 Dynamic Numbering: Generated {episode_id}")
story_page_id = '3c301989-2400-817a-858d-c234c6e3b6c9'
out_dir = f'/var/vf/episodes/{episode_id}'
os.makedirs(out_dir, exist_ok=True)

print('=== [B2] Generating 5-Arc Byzantine Story via GPT-5.6-SOL ===')

acts_plan = [
    {
        'act': 'Act I: The Unconquerable Illusion (Hook & Apex)',
        'target_words': 240,
        'instructions': 'Hook Shock in first 60 words: Describe the breach on May 29, 1453 where 400,000 citizens lost their world in hours, and the shocking truth that Rome never fell in 476 AD—it lived for another thousand years in Constantinople. Mention the triple Theodosian Walls and Justinian’s glittering golden capital.'
    },
    {
        'act': 'Act II: The Secret Weapons & Internal Rot',
        'target_words': 240,
        'instructions': 'Describe Greek Fire—the classified napalm-like incendiary weapon sprayed from bronze lion siphons that burned on water and decimated Arab armadas. Then introduce the rot: endless civil wars, blinding of rival emperors, and debasement of the solidus gold coin.'
    },
    {
        'act': 'Act III: The Venetian Financial Trap & 1204 Betrayal',
        'target_words': 250,
        'instructions': 'Detail the economic death spiral: tax exemptions given to Venetian merchants, the fatal 85,000 silver marks debt negotiated by Alexios IV, and Enrico Dandolo diverting the Fourth Crusade in 1204 to brutally sack Christian Constantinople, stripping Hagia Sophia of relics and gold.'
    },
    {
        'act': 'Act IV: The Final Siege of 1453',
        'target_words': 240,
        'instructions': 'The terminal catastrophe: Mehmed II hauling 70 warships overland into the Golden Horn, firing the 27-foot Basilica cannon against 7,000 defenders led by Emperor Constantine XI. The fatal open Kerkoporta gate and the final charge of the last Roman emperor.'
    },
    {
        'act': 'Act V: Payoff & The Thousand-Year Lesson',
        'target_words': 230,
        'instructions': 'The profound historical payoff: Byzantine scholars fleeing to Italy sparking the European Renaissance, the preservation of Roman Law (Corpus Juris Civilis), and the core mechanism: an empire is never destroyed by foreign armies until it first bankrupts its own core and mortgages its sovereignty.'
    }
]

act_texts = []
for item in acts_plan:
    act_name = item['act']
    print(f'Generating {act_name}...')
    system = f'''{SKILL_AI_CONTEXT}

You are an elite historical documentary scriptwriter.
Write {act_name} for a high-retention English documentary.
Target word count: {item["target_words"]} words (around 2 tight paragraphs, each 80-130 words).
Instructions: {item["instructions"]}
Output ONLY the narration paragraphs. No headers, no markdown tags.'''
    
    text = call_gpt56_sol(f'Write {act_name} now.', system_prompt=system)
    # Clean text
    clean_p = [p.strip() for p in text.split('\n\n') if p.strip() and not p.strip().startswith('#')]
    act_texts.append('\n\n'.join(clean_p))
    time.sleep(1)

full_script = '\n\n'.join(act_texts)
words = len(full_script.split())
print(f'Generated Full 5-Act Story: {words} words across {len(act_texts)} acts.')

# Audit
audit = sgate.score_story(full_script)
print(f'Story Gate Score: {audit.get("score")}/{audit.get("max_score")} | Verdict: {audit.get("verdict")}')

with open(f'{out_dir}/story.txt', 'w', encoding='utf-8') as f:
    f.write(full_script)

print('=== [B3] Generating Dynamic Director Plan via GPT-5.6-SOL ===')
dp_system = SKILL_AI_CONTEXT + '''

You are the Lead Art Director for Video Factory (VF Pipeline v3 / Rule 92, 93, 95, 100).
Your task is to take the 5-Act Byzantine script and produce scenes dynamically covering the entire script (DO NOT hardcode, create as many as needed).

STRICT VISUAL RULES:
1. Scene 00 MUST be the Hero Frame: Constantine XI on the Theodosian Walls.
2. Background Prompts (bg_prompt): High-Key Warm Documentary, 16:9 aspect ratio, atmospheric cinematic lighting, under 35 words, NO text, NO characters.
3. Foreground Prompts (fg_prompt): EXACTLY 1 full-body character from head to toe, historical authentic attire, centered on SOLID #FF00FF MAGENTA CHROMA-KEY BACKGROUND. CRITICAL: NEVER include borders, circular frames, medallion rings, pedestals, or square boxes. ONLY character on pure flat magenta.
4. Foreground Position (fg_position): Strictly alternate 'left' and 'right' across all scenes.

Output ONLY valid JSON array with all scene objects:
[
  {
    "scene_idx": 0,
    "name": "sc000_hero_theodosian_walls",
    "arc": "Act I - The Unconquerable Illusion",
    "narration_text": "...",
    "bg_prompt": "Cinematic wide angle high-key view of massive ancient stone fortress walls under golden sunrise lighting, photorealistic 8k documentary style.",
    "fg_prompt": "Full body standing Emperor Constantine XI in Byzantine imperial armor with purple mantle holding a sword, head to shoes visible, centered on solid #FF00FF magenta background, no frame, no border.",
    "fg_position": "left"
  }, ...
]'''

dp_prompt = f'Generate the 16 scene Director Plan for this script:\n\n{full_script[:3500]}'
dp_raw = call_gpt56_sol(dp_prompt, system_prompt=dp_system)

if dp_raw.startswith('```'):
    dp_raw = dp_raw.split('```')[1]
    if dp_raw.startswith('json'):
        dp_raw = dp_raw[4:]
dp_raw = dp_raw.strip()

scenes = json.loads(dp_raw)
print(f'Generated {len(scenes)} scenes for Director Plan! ✅')

for i, sc in enumerate(scenes):
    sc['scene_idx'] = i
    sc['fg_position'] = 'left' if i % 2 == 0 else 'right'

breakout_queries = [
    'Constantinople siege 1453',
    'Greek fire secret',
    'Mehmed II cannon',
    'Venetian betrayal 1204'
]

brain_input = {
    'episode_id': episode_id,
    'market': 'en',
    'topic': 'Byzantine Empire',
    'story': full_script,
    'story_gate_score': f'{audit.get("score")}/{audit.get("max_score")}',
    'bgm_mood': 'dramatic',
    'hook_3s': 'On May 29, 1453, a 1,123-year empire collapsed overnight.',
    'breakout_queries': breakout_queries,
    'scenes': scenes,
    'total_scenes': len(scenes),
    'render_architecture': 'two_layer_v1'
}

with open(f'{out_dir}/brain_input.json', 'w', encoding='utf-8') as f:
    json.dump(brain_input, f, ensure_ascii=False, indent=2)

print('=== [Notion Sync] Updating Story Library & Seeding Director Plan ===')
director_db_id = resolve_id('director')

props = {
    'Status': {'status': {'name': 'Approved'}},
    'Story Gate Score': {'rich_text': [{'type': 'text', 'text': {'content': f'[AG] {audit.get("score")}/{audit.get("max_score")} PASS (GPT-5.6-SOL)'}}]},
    'YouTube Title': {'rich_text': [{'type': 'text', 'text': {'content': 'How the Byzantine Empire Ruled for 1,123 Years (And Why It Fell)'}}]},
    'YouTube Tags': {'rich_text': [{'type': 'text', 'text': {'content': 'Byzantine Empire, Constantinople, Roman Empire, Justinian, Greek Fire, 1453 Siege, History Documentary'}}]},
    'Rising Queries': {'rich_text': [{'type': 'text', 'text': {'content': ', '.join(breakout_queries)}}]}
}
update_page_properties(story_page_id, props)

for sc in scenes:
    idx = sc.get('scene_idx')
    name = sc.get('name')
    sc_props = {
        'Name': {'title': [{'type': 'text', 'text': {'content': f'[AG] sc{idx:03d}_{name}'}}]},
        'Episode ID': {'rich_text': [{'type': 'text', 'text': {'content': episode_id}}]},
        'Scene Index': {'number': idx},
        'Arc': {'select': {'name': sc.get('arc', 'Act I')[:50]}},
        'Narration Text': {'rich_text': [{'type': 'text', 'text': {'content': sc.get('narration_text', '')[:1000]}}]},
        'Background Prompt': {'rich_text': [{'type': 'text', 'text': {'content': sc.get('bg_prompt', '')[:1000]}}]},
        'Foreground Prompt': {'rich_text': [{'type': 'text', 'text': {'content': sc.get('fg_prompt', '')[:1000]}}]},
        'Foreground Position': {'select': {'name': sc.get('fg_position', 'left')}},
        'Status': {'status': {'name': 'Ready'}}
    }
    create_page(director_db_id, sc_props)

print(f'Successfully synced {len(scenes)} scenes to Notion Director Plan! 🎉')
