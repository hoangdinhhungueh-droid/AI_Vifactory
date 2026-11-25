#!/usr/bin/env python3
"""Install local runtime dependencies, not global agent configuration."""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--with-asr', action='store_true', help='also create local Python 3.12 speech-recognition venv (requires uv)')
    parser.add_argument('--skip-browser', action='store_true', help='skip Chromium download if already installed')
    args = parser.parse_args()
    for required in ('node', 'npm', 'ffmpeg', 'ffprobe'):
        if not shutil.which(required):
            parser.error(f'{required} missing from PATH; see references/setup.md')
    for location in (ROOT, ROOT / 'engine'):
        subprocess.run([shutil.which('npm'), 'ci', '--no-audit', '--no-fund'], cwd=location, check=True)
    if not args.skip_browser:
        subprocess.run([shutil.which('node'), str(ROOT / 'node_modules' / 'playwright' / 'cli.js'), 'install', 'chromium'], cwd=ROOT, check=True)
    py = ROOT / '.venv-asr' / ('Scripts/python.exe' if sys.platform == 'win32' else 'bin/python')
    if args.with_asr:
        uv = shutil.which('uv')
        if not uv:
            parser.error('uv missing: install uv, or create a Python 3.12 venv manually; see references/setup.md')
        if not py.exists():
            subprocess.run([uv, 'venv', str(ROOT / '.venv-asr'), '--python', '3.12'], check=True)
        subprocess.run([uv, 'pip', 'install', '--python', str(py), '-r', str(ROOT / 'requirements-asr.txt')], cwd=ROOT, check=True)
    print('Runtime setup complete. No global agent settings changed.')
    if args.with_asr:
        print('Voice-only command uses this Python:', py)
    print('Whisper model weights download on first voice-only prepare, into .cache/whisper; use --model /local/model offline.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, subprocess.SubprocessError) as exc:
        print(f'SETUP ERROR: {exc}', file=sys.stderr)
        sys.exit(1)
