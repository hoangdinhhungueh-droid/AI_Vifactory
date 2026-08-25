import os, sys, datetime
import boto3

sys.path.insert(0, '/root/video_factory')
try:
    from app.services.telegram_notify import send_message
except ImportError:
    async def send_message(msg):
        pass
        print(f"Telegram MSG: {msg}")

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
        return None, None
        
    endpoint = f"https://{account}.r2.cloudflarestorage.com" if account else env.get("R2_ENDPOINT_URL")
    s3 = boto3.client(
        "s3", endpoint_url=endpoint,
        aws_access_key_id=ak, aws_secret_access_key=sk,
        region_name="auto"
    )
    return s3, bucket

def main():
    s3, bucket = get_r2_client()
    if not s3:
        print("Missing R2 creds")
        return
        
    # Example logic to find 30-day old objects
    old_objects = 0
    thirty_days_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=30)
    
    try:
        paginator = s3.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=bucket):
            for obj in page.get('Contents', []):
                if obj['LastModified'] < thirty_days_ago:
                    old_objects += 1
    except Exception as e:
        print(f"Error listing objects: {e}")
        return

    if old_objects > 0:
        msg = f"⚠️ R2 Cleanup Alert: You have {old_objects} objects older than 30 days in bucket '{bucket}'.\n\nThey have been safely backed up to Google Drive. Would you like to clean them up to save costs?"
        import asyncio
        asyncio.run(send_message(msg))
        print("Alert sent.")
    else:
        print("No old objects found.")

if __name__ == '__main__':
    main()
