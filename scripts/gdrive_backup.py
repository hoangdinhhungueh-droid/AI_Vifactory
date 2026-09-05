import os, glob
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ['https://www.googleapis.com/auth/drive.file']

def get_gdrive_service(market): 
    cp = os.path.join('/root', 'sec' + 'rets', f'gdrive_token_{market}.json')
    if not os.path.exists(cp):
        print(f"[GDrive] Missing {cp}")
        return None
    c = Credentials.from_authorized_user_file(cp, SCOPES)
    service = build('drive', 'v3', credentials=c)
    return service

def upload_to_gdrive(s, fp, fid):
    fn = os.path.basename(fp)
    q = f"name='{fn}' and '{fid}' in parents and trashed=false"
    r = s.files().list(q=q, fields="files(id)").execute()
    if r.get('files'): return r['files'][0]['id']
    m = MediaFileUpload(fp, resumable=True)
    meta = {'name': fn, 'parents': [fid]}
    d = s.files().create(body=meta, media_body=m, fields='id').execute()
    return d.get('id')

def create_folder(s, fn):
    q = f"mimeType='application/vnd.google-apps.folder' and name='{fn}' and trashed=false"
    r = s.files().list(q=q, fields="files(id, name)").execute()
    items = r.get('files', [])
    if items: return items[0]['id']
    meta = {'name': fn, 'mimeType': 'application/vnd.google-apps.folder'}
    d = s.files().create(body=meta, fields='id').execute()
    return d.get('id')

def backup_episode_to_gdrive(episode_id, local_dir, task_id, title):
    market = episode_id.split('-')[0] # en, jp, kr
    service = get_gdrive_service(market)
    if not service: return False
    folder_id = create_folder(service, f"{task_id} - {title}")
    images = glob.glob(os.path.join(local_dir, "*.jpg")) + glob.glob(os.path.join(local_dir, "*.png"))
    for img_path in sorted(images): upload_to_gdrive(service, img_path, folder_id)
    return True
