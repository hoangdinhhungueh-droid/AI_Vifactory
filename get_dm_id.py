import os, requests
r = requests.post("https://api.dailymotion.com/oauth/token", data={
    "grant_type": "password",
    "client_id": os.environ["DAILYMOTION_API_KEY"],
    "client_secret": os.environ["DAILYMOTION_API_SECRET"],
    "username": os.environ["DAILYMOTION_USERNAME"],
    "password": os.environ["DAILYMOTION_PASSWORD"],
    "scope": "manage_videos",
})
r.raise_for_status()
tok = r.json()["access_token"]
me = requests.get("https://api.dailymotion.com/me",
    params={"fields": "id,screenname,username"},
    headers={"Authorization": f"Bearer {tok}"}).json()
print(me)
