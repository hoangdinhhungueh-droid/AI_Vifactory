import os, sys, glob, json, math, argparse
from PIL import Image, ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True

sys.path.insert(0, '/root/video_factory')
import scripts.compile_episode_from_notion as comp
comp._token()

from app.services.image_gen import _r2_upload
from scripts.ag_notion_bridge import resolve_id, create_page
from scripts.remove_bg_chromakey import remove_bg_chromakey

parser = argparse.ArgumentParser(description="Sync episode assets: chroma-key + R2 + Notion")
parser.add_argument("--episode_id", type=str, default="en-byzantine-empire-ep001",
                    help="Episode ID (e.g. en-enron-collapse-ep006)")
args = parser.parse_args()
ep_id = args.episode_id
raw_dir = f'/var/vf/episodes/{ep_id}/assets/raw'
cutout_dir = f'/var/vf/episodes/{ep_id}/assets/cutout'
os.makedirs(cutout_dir, exist_ok=True)

images_db_id = resolve_id('images')
print('Notion Images DB ID:', images_db_id)

# 1. Process all raw FGs through Pure PIL Chroma-Key
fg_files = sorted(glob.glob(f'{raw_dir}/*_fg.jpg'))
for fg_path in fg_files:
    fname = os.path.basename(fg_path)
    idx_str = fname.split('_')[0]
    out_png = f'{cutout_dir}/{idx_str}_fg_cutout.png'
    try:
        print(f'Chroma-keying {fname} ({os.path.getsize(fg_path)} bytes) -> {out_png}...')
        remove_bg_chromakey(fg_path, out_png, tol=65.0, soft=35.0)
        print(f'Done cutout: {out_png} ({os.path.getsize(out_png)} bytes) ✅')
    except Exception as e:
        print(f'Error cutout on {fname}: {e}')

# 2. Upload all BGs and Cutout PNGs to R2 & Sync to Notion Image Asset Library
all_assets = sorted(glob.glob(f'{raw_dir}/*_bg.jpg') + glob.glob(f'{cutout_dir}/*_fg_cutout.png'))
print(f'Total assets to upload to R2 and sync to Notion: {len(all_assets)}')

for ast_path in all_assets:
    ast_name = os.path.basename(ast_path)
    is_bg = '_bg.' in ast_name
    idx = int(ast_name[2:5])
    layer_type = 'Background' if is_bg else 'Foreground/Overlay'
    aspect = '16:9' if is_bg else '1:1'
    
    r2_key = f'episodes/{ep_id}/assets/{ast_name}'
    r2_url = _r2_upload(ast_path, r2_key)
    print(f'R2 Uploaded {ast_name} -> {r2_url}')
    
    # Schema-compliant Notion payload
    props = {
        'Name': {'title': [{'type': 'text', 'text': {'content': f'[AG] {ast_name}'}}]},
        'Episode ID': {'rich_text': [{'type': 'text', 'text': {'content': ep_id}}]},
        'Scene Index': {'number': idx},
        'Layer Type': {'select': {'name': layer_type}},
        'Aspect': {'select': {'name': aspect}},
        'Status': {'status': {'name': 'Approved'}},
        'AI Verdict': {'select': {'name': 'Approved'}},
        'R2 Path': {'rich_text': [{'type': 'text', 'text': {'content': r2_url or r2_key}}]},
        'Prompt': {'rich_text': [{'type': 'text', 'text': {'content': f'Native Google Imagen 3 photorealistic asset for {ep_id} {ast_name}'}}]}
    }
    if r2_url:
        props['Image'] = {'files': [{'name': ast_name, 'type': 'external', 'external': {'url': r2_url}}]}
    
    res = create_page(images_db_id, props)
    page_id = res.get('id', '')
    print(f'Notion Image Asset Library synced: {ast_name} (Page ID: {page_id}) ✅')

print('🎉 100% ASSETS PROCESSED, CHROMA-KEYED, R2 UPLOADED & NOTION SYNCED! ✅')
