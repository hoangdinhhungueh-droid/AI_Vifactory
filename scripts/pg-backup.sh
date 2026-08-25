#!/bin/bash
# VF Postgres Backup — daily 3AM → local + R2
# Created by Notion AI audit 15/08/2026
set -euo pipefail

DATE=$(date +%Y%m%d)
BACKUP_DIR=/tmp/vf-backups
mkdir -p $BACKUP_DIR

# Backup ALL databases (video_factory_db + n8n_db)
pg_dumpall -U postgres 2>/dev/null | gzip > $BACKUP_DIR/pg-all-$DATE.sql.gz

# Keep 7 rolling copies locally
find $BACKUP_DIR -name "pg-all-*.sql.gz" -mtime +7 -delete 2>/dev/null || true

# Upload to R2 if aws cli configured
if command -v aws &>/dev/null; then
  source /root/video_factory/.env 2>/dev/null || true
  if [ -n "${R2_ENDPOINT_URL:-}" ]; then
    aws s3 cp $BACKUP_DIR/pg-all-$DATE.sql.gz \
      s3://vf-assets/backups/pg-all-$DATE.sql.gz \
      --endpoint-url $R2_ENDPOINT_URL 2>/dev/null || true
    # Keep 7 on R2 too
    aws s3 ls s3://vf-assets/backups/ --endpoint-url $R2_ENDPOINT_URL 2>/dev/null \
      | sort | head -n -7 | awk '{print $4}' \
      | xargs -I{} aws s3 rm s3://vf-assets/backups/{} --endpoint-url $R2_ENDPOINT_URL 2>/dev/null || true
  fi
fi

logger -t vf-backup "Postgres backup complete: pg-all-$DATE.sql.gz"
