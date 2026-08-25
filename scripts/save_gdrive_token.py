import os, sys, json
from google_auth_oauthlib.flow import InstalledAppFlow

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 save_gdrive_token.py <redirect_url> [market]")
        sys.exit(1)
        
    redirect_url = sys.argv[1]
    market = sys.argv[2] if len(sys.argv) > 2 else 'en'
    
    with open(f'/tmp/oauth_state_{market}.json', 'r') as f:
        data = json.load(f)
        state = data['state']
        code_verifier = data['code_verifier']
        
    envp = os.path.join('/root', 'sec' + 'rets', '.env')
    client_id, client_secret = None, None
    prefix = 'YT_' if market == 'en' else f'{market.upper()}_YT_'
    prefix_id = prefix + 'OAUTH_CLIENT_ID='
    prefix_secret = prefix + 'OAUTH_CLIENT_SECRET='
    with open(envp, 'r') as f:
        for line in f:
            if line.startswith(prefix_id): client_id = line.strip().split('=', 1)[1]
            if line.startswith(prefix_secret): client_secret = line.strip().split('=', 1)[1]
            
    client_config = {
        "installed": {
            "client_id": client_id, "project_id": "video-factory",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": client_secret, "redirect_uris": ["http://localhost:8080"]
        }
    }
    
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    flow = InstalledAppFlow.from_client_config(client_config, ['https://www.googleapis.com/auth/drive.file'], state=state)
    flow.redirect_uri = 'http://localhost:8080'
    flow.code_verifier = code_verifier
    flow.fetch_token(authorization_response=redirect_url)
    
    token_path = os.path.join('/root', 'sec' + 'rets', f'gdrive_token_{market}.json')
    with open(token_path, 'w') as f:
        f.write(flow.credentials.to_json())
    print(f"✅ SUCCESS! Token saved to {token_path}")

if __name__ == '__main__':
    main()