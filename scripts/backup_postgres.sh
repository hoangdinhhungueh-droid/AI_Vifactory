#!/bin/bash
# G5-2 — Postgres daily backup → R2
# Runs: 3AM daily via cron
# Requires: s3cmd or rclone configured, or awscli with R2 endpoint
set -e

DB=video_factory_db
BACKUP_DIR=/tmp/vf/backups
DATE=$(date +%Y%m%d_%H%M)
FILE="${BACKUP_DIR}/vf_pg_${DATE}.sql.gz"

mkdir -p "$BACKUP_DIR"

# Dump
pg_dump -U postgres "$DB" | gzip > "$FILE"
echo "[backup] Dumped: $FILE ($(du -sh $FILE | cut -f1))"

# Upload to R2
# Load env vars
set -a; source /root/secrets/.env; set +a

if command -v aws &>/dev/null; then
  aws s3 cp "$FILE" \
    "s3://${R2_BUCKET_NAME}/backups/postgres/$(basename $FILE)" \
    --endpoint-url "${R2_ENDPOINT_URL}" \
    --no-progress 2>&1
  echo "[backup] Uploaded to R2 OK"
else
  echo "[backup] WARN: aws CLI not found — file kept at $FILE"
fi

# Cleanup local files older than 3 days
find "$BACKUP_DIR" -name 'vf_pg_*.sql.gz' -mtime +3 -delete
echo "[backup] Done: ${DATE}"
