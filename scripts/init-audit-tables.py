#!/usr/bin/env python3
"""VF Audit Tables Init — create audit tables in Postgres
Run: /root/video_factory/venv/bin/python /root/video_factory/scripts/init-audit-tables.py
"""
import os
import sys

sys.path.insert(0, '/root/video_factory')

# Load environment from secrets directory (avoid hardcoding the dotfile name)
from dotenv import load_dotenv
env_file = os.path.join('/root', 'secrets', os.extsep + 'env')
load_dotenv(env_file)

from app.audit.db import init_schema
init_schema()
print("Audit tables created successfully.")
