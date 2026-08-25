#!/usr/bin/env bash
# Convenience wrapper: loads YT_OAUTH_CLIENT_ID/SECRET from /root/secrets/.env
# then runs the consent helper. Run from a machine with a browser, or on the
# VPS through an SSH tunnel:  ssh -L 8765:localhost:8765 root@188.40.168.214
set -a
. /root/secrets/.env
set +a
cd /root/video_factory
exec python3 scripts/yt_oauth_setup.py
