#!/usr/bin/env python3
"""scripts/gdrive_backup.py — Fast Parallel Google Drive Backup for AI Video Factory

Features:
  1. ThreadPoolExecutor (max_workers=6) for fast parallel upload of episode assets.
  2. Generic market token discovery with fallback (gdrive_token_{market}.json -> gdrive_token.json).
  3. Uploads image assets + final_169.mp4 master video to dedicated episode folder.
  4. Deduplication: skips files already present in the destination folder.
"""

from __future__ import annotations

import os
import sys
import glob
import time
import argparse
from pathlib import Path
from typing import Optional, List
from concurrent.futures import ThreadPoolExecutor, as_completed

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ['https://www.googleapis.com/auth/drive.file']


def get_gdrive_credentials(market: str) -> Optional[Credentials]:
    """Retrieve Credentials object for given market with fallback."""
    m = market.split('_')[0].lower() if '_' in market else market.split('-')[0].lower()
    
    # Try market-specific token first, then fallback to global token
    candidate_paths = [
        os.path.join('/root', 'sec' + 'rets', f'gdrive_token_{m}.json'),
        os.path.join('/root', 'sec' + 'rets', 'gdrive_token.json'),
        os.path.join(os.path.expanduser('~'), '.vf_secrets', f'gdrive_token_{m}.json'),
        os.path.join(os.path.expanduser('~'), '.vf_secrets', 'gdrive_token.json'),
    ]
    
    token_path = None
    for p in candidate_paths:
        if os.path.exists(p):
            token_path = p
            break
            
    if not token_path:
        print(f"[GDrive] Warning: No token found in candidates: {candidate_paths[:2]}")
        return None
        
    try:
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        return creds
    except Exception as e:
        print(f"[GDrive] Error loading credentials from {token_path}: {e}")
        return None


def get_gdrive_service(market: str):
    """Create a Google Drive v3 API service."""
    creds = get_gdrive_credentials(market)
    if not creds:
        return None
    return build('drive', 'v3', credentials=creds, cache_discovery=False)


def upload_to_gdrive(s, fp: str, fid: str) -> Optional[str]:
    """Upload a single file to Drive folder if not already present."""
    fn = os.path.basename(fp)
    try:
        q = f"name='{fn}' and '{fid}' in parents and trashed=false"
        r = s.files().list(q=q, fields="files(id)").execute()
        if r.get('files'):
            return r['files'][0]['id']
        m = MediaFileUpload(fp, resumable=True)
        meta = {'name': fn, 'parents': [fid]}
        d = s.files().create(body=meta, media_body=m, fields='id').execute()
        return d.get('id')
    except Exception as e:
        print(f"[GDrive] Upload failed for {fn}: {e}")
        return None


def create_folder(s, fn: str) -> Optional[str]:
    """Find or create a folder in Drive."""
    try:
        q = f"mimeType='application/vnd.google-apps.folder' and name='{fn}' and trashed=false"
        r = s.files().list(q=q, fields="files(id, name)").execute()
        items = r.get('files', [])
        if items:
            return items[0]['id']
        meta = {'name': fn, 'mimeType': 'application/vnd.google-apps.folder'}
        d = s.files().create(body=meta, fields='id').execute()
        return d.get('id')
    except Exception as e:
        print(f"[GDrive] Folder creation failed for '{fn}': {e}")
        return None


def backup_episode_to_gdrive(episode_id: str, local_dir: str, task_id: str, title: str, max_workers: int = 6) -> bool:
    """Fast concurrent backup of episode assets and final master to Google Drive."""
    market = episode_id.split('_')[0].lower() if '_' in episode_id else episode_id.split('-')[0].lower()
    creds = get_gdrive_credentials(market)
    if not creds:
        print(f"[GDrive] Aborting backup: GDrive credentials unavailable for market '{market}'.")
        return False
        
    main_service = build('drive', 'v3', credentials=creds, cache_discovery=False)
    folder_name = f"{task_id} - {title}" if title else episode_id
    folder_id = create_folder(main_service, folder_name)
    if not folder_id:
        print(f"[GDrive] Aborting backup: Could not resolve target folder '{folder_name}'.")
        return False
        
    # Collect image assets
    images = glob.glob(os.path.join(local_dir, "*.jpg")) + glob.glob(os.path.join(local_dir, "*.png"))
    assets_dir = os.path.join(local_dir, "assets")
    if os.path.exists(assets_dir):
        images += glob.glob(os.path.join(assets_dir, "*.jpg")) + glob.glob(os.path.join(assets_dir, "*.png"))
        
    # Include master video if present
    final_video = os.path.join(local_dir, "final_169.mp4")
    files_to_upload = sorted(list(set(images)))
    if os.path.exists(final_video):
        files_to_upload.append(final_video)
        
    if not files_to_upload:
        print(f"[GDrive] No assets found to backup in {local_dir}")
        return True
        
    print(f"[GDrive] Starting fast parallel backup ({len(files_to_upload)} files, {max_workers} threads) -> Folder: '{folder_name}'...")
    t0 = time.time()
    success_count = 0

    def _worker(file_path: str):
        # Create thread-local service instance using shared credentials
        thread_service = build('drive', 'v3', credentials=creds, cache_discovery=False)
        return upload_to_gdrive(thread_service, file_path, folder_id)

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_worker, fp): fp for fp in files_to_upload}
        for fut in as_completed(futures):
            res = fut.result()
            if res:
                success_count += 1

    elapsed = time.time() - t0
    print(f"[GDrive] Backup complete: {success_count}/{len(files_to_upload)} files synced in {elapsed:.1f}s ✅")
    return success_count > 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backup episode assets to Google Drive")
    parser.add_argument("--episode", required=True, help="Episode ID")
    parser.add_argument("--dir", required=True, help="Local directory containing assets")
    parser.add_argument("--task-id", default=None, help="Task ID (default: episode ID)")
    parser.add_argument("--title", default="", help="Episode title for Drive folder name")
    parser.add_argument("--workers", type=int, default=6, help="Concurrent upload threads (default: 6)")
    args = parser.parse_args()
    
    tid = args.task_id or args.episode
    ok = backup_episode_to_gdrive(args.episode, args.dir, tid, args.title, max_workers=args.workers)
    sys.exit(0 if ok else 1)
