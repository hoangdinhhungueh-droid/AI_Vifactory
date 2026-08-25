#!/usr/bin/env bash
set -euo pipefail

ENV_PATH=/root/"secrets/.env"
set +e
set -a; source "$ENV_PATH" >/dev/null 2>&1; set +a
set -e

# Required env (names only)
: "${NOTION_TOKEN:?missing NOTION_TOKEN}"
: "${RUN_LOG_DB_ID:?missing RUN_LOG_DB_ID}"
: "${TELEGRAM_BOT_TOKEN:?missing TELEGRAM_BOT_TOKEN}"
: "${TELEGRAM_CHAT_ID:?missing TELEGRAM_CHAT_ID}"

API="http://127.0.0.1:8000"
LOG=/root/vf_autoloop_visuals.log
STATE=/tmp/vf/progress_state.json
mkdir -p /tmp/vf

notion_add_runlog() {
  local title="$1"; local status="$2"; local type="$3"; local service="$4"; local retries="$5"; local fixcmd="$6"; local logtxt="$7"
  # Trim log to avoid 413
  logtxt="${logtxt:0:1800}"
  curl -sS -X POST https://api.notion.com/v1/pages \
    -H "Authorization: Bearer ${NOTION_TOKEN}" \
    -H "Notion-Version: 2022-06-28" \
    -H "Content-Type: application/json" \
    -d "{\"parent\":{\"database_id\":\"${RUN_LOG_DB_ID}\"},\"properties\":{\"Name\":{\"title\":[{\"text\":{\"content\":${title@Q}}}]},\"Status\":{\"select\":{\"name\":${status@Q}}},\"Type\":{\"select\":{\"name\":${type@Q}}},\"Service\":{\"rich_text\":[{\"text\":{\"content\":${service@Q}}}]},\"Retries\":{\"number\":${retries}},\"Fix Cmd\":{\"rich_text\":[{\"text\":{\"content\":${fixcmd@Q}}}]},\"Log\":{\"rich_text\":[{\"text\":{\"content\":${logtxt@Q}}}]}}}" >/dev/null || true
}

tele_send() {
  local msg="$1"
  curl -sS -X POST "https://api.telegram.org/bot${VF_TG_BOT_TOKEN:-$TELEGRAM_BOT_TOKEN}/sendMessage" \
    -d "chat_id=${TELEGRAM_CHAT_ID}" \
    --data-urlencode "text=${msg}" >/dev/null || true
}

health_check() {
  curl -sS "${API}/api/v1/health" >/dev/null 2>&1
}

restart_vf_api_best_effort() {
  # Try systemd first, then pm2
  systemctl restart vf-api >/dev/null 2>&1 && return 0
  systemctl restart video-factory-api >/dev/null 2>&1 && return 0
  pm2 restart vf-api >/dev/null 2>&1 && return 0
  pm2 restart video_factory_api >/dev/null 2>&1 && return 0
  return 1
}

get_latest_episode_dir() {
  ls -1dt /var/vf/episodes/ep-en-visuals-* 2>/dev/null | head -n 1
}

has_final_video() {
  local d="$1"
  [[ -f "$d/final_916.mp4" || -f "$d/final_169.mp4" || -f "$d/final_11.mp4" ]]
}

has_stock_cache() {
  find /tmp/vf/stock_cache -type f \( -iname "*.mp4" -o -iname "*.jpg" \) -size +50k 2>/dev/null | head -n 1 | grep -q .
}

mark_done_once() {
  if [[ -f /tmp/vf/goal_done.flag ]]; then return 0; fi
  touch /tmp/vf/goal_done.flag

  local d
  d="$(get_latest_episode_dir || true)"
  local ep="${d##*/}"
  tele_send "✅ DONE — Visual stock fetched + final video produced. Episode=${ep}"
  notion_add_runlog "[progress] DONE episode=${ep}" "FIXED" "audit" "progress" 0 "none" "Goal reached: final video exists + stock_cache has real assets"
}

# Main watch loop (every 5 min)
while true; do
  # Snapshot
  latest="$(get_latest_episode_dir || true)"

  # Read last 50 lines of autoloop log if exists
  tailtxt=""
  if [[ -f "$LOG" ]]; then
    tailtxt="$(tail -n 50 "$LOG" 2>/dev/null || echo "")"
  fi

  # Check goal
  if [[ -n "$latest" ]] && has_final_video "$latest" && has_stock_cache; then
    mark_done_once
    exit 0
  fi

  # Health monitoring: if API down -> attempt one restart + log
  if ! health_check; then
    notion_add_runlog "[progress] vf-api healthcheck FAIL" "NEEDS_CONFIRM" "audit" "vf-api" 0 "restart_vf_api" "${tailtxt}"
    if restart_vf_api_best_effort; then
      sleep 5
      if health_check; then
        notion_add_runlog "[progress] vf-api restarted OK" "FIXED" "audit" "vf-api" 1 "restart_vf_api" "${tailtxt}"
      else
        notion_add_runlog "[progress] vf-api restart FAILED" "retry-exceeded" "audit" "vf-api" 1 "restart_vf_api" "${tailtxt}"
        tele_send "⚠️ VF WARNING: vf-api healthcheck failed and restart did not recover. Check logs."
      fi
    else
      notion_add_runlog "[progress] vf-api restart cmd not found" "no-rule-match" "audit" "vf-api" 0 "restart_vf_api" "${tailtxt}"
      tele_send "⚠️ VF WARNING: vf-api healthcheck failed; could not restart via systemctl/pm2."
    fi
  else
    # Heartbeat log (light)
    ep="${latest##*/}"
    notion_add_runlog "[progress] heartbeat ep=${ep}" "ALLOW" "audit" "progress" 0 "none" "${tailtxt}"
  fi

  sleep 300

done
