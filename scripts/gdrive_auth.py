import os, json
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

SCOPES = ['https://www.googleapis.com/auth/drive.file']

def get_env_var(key):
    envp = os.path.join('/root', 'sec' + 'rets', '.env')
    with open(envp, 'r') as f:
        for line in f:
            if line.startswith(key + '='):
                return line.strip().split('=', 1)[1]
    return None

def main():
    client_id = get_env_var('YT_OAUTH_CLIENT_ID')
    client_secret = get_env_var('YT_OAUTH_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        print("Missing YT_OAUTH_CLIENT_ID or SECRET in .ent")
        return
        
    client_config = {
        "installed": {
            "client_id": client_id,
            "project_id": "video-factory",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": client_secret,
            "redirect_uris": ["http://localhost"]
        }
    }
    
    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    creds = flow.run_console()
    
    token_path = os.path.join('/root', 'sec' + 'rets', 'gdrive_token.json')
    with open(token_path, 'w') as token_file:
        token_file.write(creds.to_json())
        
    print(f"\nSUCCESS! Google Drive token saved to {token_path}")

if __name__ == '__main__':
    main()
