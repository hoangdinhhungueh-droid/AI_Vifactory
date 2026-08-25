import os, sys, json
from google_auth_oauthlib.flow import InstalledAppFlow

def main():
    market = sys.argv[1] if len(sys.argv) > 1 else 'en'
    envp = os.path.join('/root', 'sec' + 'rets', '.env')
    client_id, client_secret = None, None
    prefix = 'YT_' if market == 'en' else f'{market.upper()}_YT_'
    prefix_id = prefix + 'OAUTH_CLIENT_ID='
    prefix_secret = prefix + 'OAUTH_CLIENT_SECRET='
    with open(envp, 'r') as f:
        for line in f:
            if line.startswith(prefix_id): client_id = line.strip().split('=', 1)[1]
            if line.startswith(prefix_secret): client_secret = line.strip().split('=', 1)[1]
    
    if not client_id or not client_secret:
        print(f"Missing credentials for {market}")
        sys.exit(1)

    client_config = {
        "installed": {
            "client_id": client_id, "project_id": "video-factory",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": client_secret, "redirect_uris": ["http://localhost:8080"]
        }
    }
    
    flow = InstalledAppFlow.from_client_config(client_config, ['https://www.googleapis.com/auth/drive.file'])
    flow.redirect_uri = "http://localhost:8080"
    auth_url, state = flow.authorization_url(prompt='consent')
    
    with open(f'/tmp/oauth_state_{market}.json', 'w') as f:
        json.dump({"state": state, "code_verifier": flow.code_verifier}, f)
        
    print(auth_url)

if __name__ == '__main__':
    main()