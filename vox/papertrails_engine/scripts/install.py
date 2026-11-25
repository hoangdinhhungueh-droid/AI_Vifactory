#!/usr/bin/env python3
"""Copy the portable package into an explicit agent skill directory.

Dry-run by default; --apply is required. Existing installations are never replaced.
"""
import argparse
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = 'papertrails-video'
EXCLUDED = {'.git', '.github', 'node_modules', '.venv', '.venv-asr', '.cache', '__pycache__', 'qa',
            'dist', 'evidence', 'exports', 'screenshots', '.pytest_cache', '.ruff_cache', 'coverage', '.DS_Store'}


def target_for(agent, project=None, skills_dir=None):
    if skills_dir:
        return Path(skills_dir).expanduser().resolve() / SKILL
    if agent == 'hermes':
        home = os.environ.get('HERMES_HOME')
        if not home:
            raise ValueError('HERMES_HOME is not set. Supply --skills-dir pointing at the active profile skills folder; never guess a different profile.')
        return Path(home).expanduser().resolve() / 'skills' / SKILL
    base = Path(project).expanduser().resolve() if project else Path.home()
    folder = {'claude': '.claude', 'cursor': '.cursor', 'codex': '.agents'}[agent]
    return base / folder / 'skills' / SKILL


def ignore(directory, names):
    return [name for name in names if name in EXCLUDED or name.endswith(('.pyc', '.mp4', '.zip')) or (Path(directory).name == 'tests' and name == 'fixtures')]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--agent', choices=['claude', 'cursor', 'codex', 'hermes'], required=True)
    parser.add_argument('--project', help='project-local install; omit for user-level install; Hermes uses active profile instead')
    parser.add_argument('--skills-dir', help='exact skill parent folder; useful for an explicit Hermes profile path')
    parser.add_argument('--apply', action='store_true', help='actually copy after reviewing the dry-run target')
    args = parser.parse_args()
    if args.agent == 'hermes' and args.project:
        parser.error('Hermes: use HERMES_HOME or --skills-dir, not --project.')
    target = target_for(args.agent, args.project, args.skills_dir)
    if target == ROOT or ROOT in target.parents or target in ROOT.parents:
        parser.error('Installation target must not contain, or be contained by, the source package.')
    if target.exists():
        parser.error('Target already exists; preserve it and choose a different skills-dir or remove it manually after backup.')
    print(json.dumps({'agent': args.agent, 'target': str(target), 'mode': 'APPLY' if args.apply else 'DRY_RUN',
                      'note': 'Copies source/assets only. Run scripts/setup.py --with-asr in installed copy before use.'}, indent=2))
    if args.apply:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(ROOT, target, ignore=ignore)
        if not (target / 'SKILL.md').is_file() or not (target / 'engine' / 'public' / 'models' / 'traveller.glb').is_file():
            raise RuntimeError('Incomplete installation; target was left in place for inspection.')
        print('Installed. Reopen agent session if the new skill is not discovered.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, RuntimeError) as exc:
        print(f'INSTALL ERROR: {exc}', file=sys.stderr)
        sys.exit(1)
