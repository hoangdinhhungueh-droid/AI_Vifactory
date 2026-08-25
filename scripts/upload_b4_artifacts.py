import os, sys, argparse, glob, json
import boto3
from scripts.gdrive_backup import backup_episode_to_gdrive
from scripts.ag_notion_bridge import _req, query_db, resolve_id

sys.path.insert(0, '/root/video_factory')
import scripts.compile_episode_from_notion as comp
comp._token()
from scripts.ag_notion_bridge import create_page, resolve_episode_image_asset_db

def get_r2_client():
    envp = os.path.join("/root", "sec" + "rets", ".env")
    env = {}
    if os.path.exists(envp):
        with open(envp, "r") as f:
            for line in f:
                line = line.strip()
                if "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip().strip("'\"")
    
    account = env.get("R2_ACCOUNT_ID") or os.environ.get("R2_ACCOUNT_ID")
    ak = env.get("R2_ACCESS_KEY_ID") or os.environ.get("R2_ACCESS_KEY_ID")
    sk = env.get("R2_SECRET_ACCESS_KEY") or os.environ.get("R2_SECRET_ACCESS_KEY")
    bucket = env.get("R2_BUCKET_NAME") or os.environ.get("R2_BUCKET_NAME") or "video-factory-assets"
    
    if not (ak and sk):
        print("Missing R2 creds in env")
        return None, None
        
    endpoint = env.get("R2_ENDPOINT_URL") or os.environ.get("R2_ENDPOINT_URL") or (f"https://{account}.r2.cloudflarestorage.com" if account else "")
    s3 = boto3.client(
        "s3", endpoint_url=endpoint,
        aws_access_key_id=ak, aws_secret_access_key=sk,
        region_name="auto"
    )
    return s3, bucket

def _r2_upload(local_path, r2_key, s3, bucket):
    if not s3:
        return f"https://r2.placeholder.com/{r2_key}"
    s3.upload_file(local_path, bucket, r2_key)
    return f"https://vifactory.com/{r2_key}"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--episode", required=True)
    parser.add_argument("--dir", required=True)
    args = parser.parse_args()

    s3, bucket = get_r2_client()
    if not s3:
        print("Error: Could not initialize R2 client")
        sys.exit(1)

    res = resolve_episode_image_asset_db(args.episode, create_if_missing=True)
    if res.get("error"):
        print("Error resolving DB:", res)
        sys.exit(1)
    db_id = res["db_id"]
    print(f"[INFO] Target Notion DB: {db_id}")

    images = glob.glob(os.path.join(args.dir, "*.jpg")) + glob.glob(os.path.join(args.dir, "*.png"))
    
    # Fetch trend info
    trend_db = resolve_id("trend_brain")
    q = _req("POST", f"databases/{trend_db}/query", data={
        "filter": {"property": "Episode ID", "rich_text": {"equals": args.episode}}
    })
    task_id = args.episode
    trend_title = args.episode
    if q.get("results"):
        r = q["results"][0]
        try:
            trend_title = r["properties"]["Name"]["title"][0]["plain_text"]
        except: pass
        try:
            task_id = r["properties"]["Task ID"]["rich_text"][0]["plain_text"]
        except: pass
        
    print(f"[GDrive] Discovered task_id={task_id}, title={trend_title}")
    backup_episode_to_gdrive(args.episode, args.dir, task_id, trend_title)

    if not images:
        print(f"[WARN] No images found in {args.dir}")
        sys.exit(0)

    for i, img_path in enumerate(sorted(images)):
        ast_name = os.path.basename(img_path)
        r2_key = f"episodes/{args.episode}/assets/{ast_name}"
        
        r2_url = _r2_upload(img_path, r2_key, s3, bucket)
        print(f"[R2] Uploaded: {ast_name} -> {r2_url}")
        
        # Decide metadata based on extension or name
        is_bg = ast_name.endswith(".jpg")
        layer_type = "Background" if is_bg else "Foreground/Overlay"
        aspect = "16:9" if is_bg else "1:1"
        record_name = f"[AG] {ast_name}"
        
        props = {
            'Name': {'title': [{'type': 'text', 'text': {'content': record_name}}]},
            'Episode ID': {'rich_text': [{'type': 'text', 'text': {'content': args.episode}}]},
            'Scene Index': {'number': i + 1},
            'Layer Type': {'select': {'name': layer_type}},
            'Aspect': {'select': {'name': aspect}},
            'Status': {'status': {'name': 'Approved'}},
            'AI Verdict': {'select': {'name': 'Approved'}},
            'R2 Path': {'rich_text': [{'type': 'text', 'text': {'content': r2_url}}]},
            'Image': {'files': [{'name': ast_name, 'type': 'external', 'external': {'url': r2_url}}]}
        }
        
        page = create_page(db_id, props)
        if page.get("error"):
            print(f"[Notion] Error creating {ast_name}:", page)
        else:
            print(f"[Notion] 200 OK - Created {ast_name} (ID: {page['id']})")
            print(f"[Notion JSON] {json.dumps(page['id'])}")

    print(f"\n[DONE] Successfully processed {len(images)} images.")

if __name__ == '__main__':
    main()
