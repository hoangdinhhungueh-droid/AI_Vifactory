#!/usr/bin/env python3
"""Package a portable source skill; exclude local dependencies and user media."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import re
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SKIP = {'.git', '.github', 'node_modules', '.venv', '.venv-asr', '.cache', '__pycache__', 'qa',
        'dist', 'evidence', 'exports', 'screenshots', 'fixtures', '.DS_Store'}
# --lite: drop everything only the upstream interactive game uses (the video entry never imports or fetches it),
# plus developer-only material. Measured with an import trace from engine/src/video/index.js.
LITE_SKIP = ('engine/index.html', 'engine/src/main.js', 'engine/src/game/', 'engine/src/life/', 'engine/src/player/controls.js',
             'engine/src/audio/', 'engine/src/camera/follow.js', 'engine/src/camera/views.js', 'engine/src/core/loop.js',
             'engine/public/social-card.jpg', 'engine/public/textures/art/animals.png', 'engine/public/textures/art/animals.json',
             'engine/public/textures/art/game_icons.png', 'engine/public/textures/art/game_icons.json', 'tests/', 'ENGINE-REPORT.md')


def source_files(lite=False):
    for path in sorted(ROOT.rglob('*')):
        relative = path.relative_to(ROOT)
        if any(part in SKIP or part == '.env' or part.startswith('.env.') for part in relative.parts) or path.suffix.lower() in ('.mp4', '.mp3', '.wav', '.zip', '.pyc'):
            continue
        if lite and any(relative.as_posix() == x or relative.as_posix().startswith(x) for x in LITE_SKIP):
            continue
        if path.is_file() and relative.as_posix() != 'package-manifest.json':
            yield path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--lite', action='store_true', help='video-only package: omit the upstream game entry, its assets, tests and dev reports')
    args = parser.parse_args()
    output = Path(args.output).expanduser().resolve()
    if output.exists():
        parser.error('Output exists. Pick a new package filename; do not overwrite silently.')
    if ROOT in output.parents:
        parser.error('Write ZIP beside the skill directory, not inside it.')
    files = list(source_files(args.lite))
    inventory = {p.relative_to(ROOT).as_posix(): {'sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'bytes': p.stat().st_size} for p in files}
    for required in ('SKILL.md', 'scripts/pipeline.py', 'scripts/render.mjs', 'engine/video.html', 'engine/LICENSE', 'rights/SOURCES.md', 'requirements-asr.txt', 'package-lock.json'):
        if required not in inventory:
            parser.error('Package missing ' + required)
    version = re.search(r'^\s*version:\s*"?([\w.]+)', (ROOT / 'SKILL.md').read_text(encoding='utf-8'), re.M)
    manifest = {'skill': 'papertrails-video', 'version': version.group(1) if version else 'unknown', 'profile': 'lite' if args.lite else 'full', 'createdUtc': datetime.now(timezone.utc).isoformat(),
                'upstreamCommit': '5a284f71164ea3bd54ee788553e21f7f21a1b7b7', 'files': inventory,
                'notBundled': sorted(SKIP) + (list(LITE_SKIP) if args.lite else []), 'note': 'Source/assets package. Models, npm installs, voice fixtures, and rendered video are excluded.'}
    (ROOT / 'package-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    files.append(ROOT / 'package-manifest.json')
    with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            archive.write(path, 'papertrails-video/' + path.relative_to(ROOT).as_posix())
    # Read the actual ZIP, verify every member and every payload hash.
    with zipfile.ZipFile(output) as archive:
        error = archive.testzip()
        if error:
            raise RuntimeError('Corrupted ZIP member: ' + error)
        names = archive.namelist()
        for name in names:
            parts = Path(name).parts
            if '..' in parts or name.startswith(('/', '\\')):
                raise RuntimeError('Unsafe ZIP path: ' + name)
        for relative, item in inventory.items():
            if hashlib.sha256(archive.read('papertrails-video/' + relative)).hexdigest() != item['sha256']:
                raise RuntimeError('Package hash mismatch: ' + relative)
    print(json.dumps({'zip': str(output), 'files': len(files), 'bytes': output.stat().st_size,
                      'sha256': hashlib.sha256(output.read_bytes()).hexdigest(), 'verified': True}, indent=2))


if __name__ == '__main__':
    main()
