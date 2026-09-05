"""
backfill_task_id.py -- Add + backfill a "Task ID" property (format
EP000-EN) derived from the existing "Episode ID" (e.g.
en-jack-the-ripper-ep002 -> EP002-EN) across the VF Notion databases that
carry an Episode ID column, plus Prompt Library (title-derived, see below).

Usage (on VPS):
    python3 /root/video_factory/scripts/backfill_task_id.py

Safe to re-run: skips rows that already have a non-empty Task ID, and skips
rows whose Episode ID does not match the expected "<slug>-ep<NNN>" pattern
(these are logged so they can be fixed manually).

RESOLVED 23/08/2026: Prompt Library used to be excluded here because it had
no Episode ID column and mixed generic templates with per-episode rows. As
of the subpage-per-episode migration (plan item 5), the flat Prompt Library
DB only holds per-episode rows (e.g. "Prompt Library — EP001-EN (episode-id)"
subpage-container rows, or hub/pointer rows like "en-enron-ep006 — ..." whose
real prompts live in the migrated Director Plan child DB). Task ID is now
derived from the row Title (it embeds "EPnnn-XX" or the raw episode slug),
not from an Episode ID column.
"""
import sys, re, json, time
sys.path.insert(0, '/root/video_factory/scripts')
import ag_notion_bridge as b

DATABASES = {
    'Director Plan': '5b201989-2400-8295-be81-81c2c0e4e138',
    'Image Asset Library': 'f9101989-2400-830c-ab89-01700bb07933',
    'Experiment Lab': '76601989-2400-838f-ad45-816777c57ffd',
    'YouTube Registry': '3c301989-2400-81b9-a4bb-e5568ce942f8',
    'Story Library': 'b0301989-2400-836b-bdb5-8131fea17736',
}

PROMPT_LIBRARY_DB = '8c801989-2400-831a-901d-014aebdc3b31'

EP_PATTERN = re.compile(r'^([a-z]{2})-.+-ep(\d+)$')
TASK_ID_IN_TITLE_PATTERN = re.compile(r'\bEP(\d+)-([A-Z]{2})\b')


def derive_task_id(episode_id: str):
    """en-jack-the-ripper-ep002 -> EP002-EN. Returns None if unparseable."""
    if not episode_id:
        return None
    m = EP_PATTERN.match(episode_id.strip().lower())
    if not m:
        return None
    market, num = m.group(1), m.group(2)
    return 'EP%03d-%s' % (int(num), market.upper())


def derive_task_id_from_title(title: str):
    """Extract an already-embedded 'EPnnn-XX' token from a row title, else
    fall back to parsing a trailing '<slug>-epNNN' episode-id-like token."""
    if not title:
        return None
    m = TASK_ID_IN_TITLE_PATTERN.search(title)
    if m:
        return 'EP%s-%s' % (m.group(1).zfill(3), m.group(2))
    m2 = re.search(r'([a-z]{2}-[a-z0-9-]+-ep\d+)', title.lower())
    if m2:
        return derive_task_id(m2.group(1))
    return None


def ensure_task_id_property(db_id: str) -> bool:
    res = b._req('PATCH', 'databases/' + db_id, {
        'properties': {'Task ID': {'rich_text': {}}}
    })
    if res.get('error'):
        print('  SCHEMA_PATCH_FAILED:', res.get('status_code'), res.get('message'))
        return False
    return True


def get_rich_text(props: dict, name: str) -> str:
    p = props.get(name) or {}
    arr = p.get('rich_text') or []
    return ''.join(seg.get('plain_text', '') for seg in arr)


def get_title(props: dict, name: str) -> str:
    p = props.get(name) or {}
    arr = p.get('title') or []
    return ''.join(seg.get('plain_text', '') for seg in arr)


def backfill_db(name: str, db_id: str):
    print('===', name, db_id, '===')
    if not ensure_task_id_property(db_id):
        return
    res = b.query_db(db_id)
    if res.get('error'):
        print('  QUERY_FAILED:', res)
        return
    rows = res.get('results', [])
    print('  rows:', len(rows))
    updated, skipped_has_task_id, skipped_unparseable = 0, 0, 0
    unparseable_examples = []
    for row in rows:
        page_id = row.get('id')
        props = row.get('properties', {})
        existing_task_id = get_rich_text(props, 'Task ID')
        if existing_task_id:
            skipped_has_task_id += 1
            continue
        episode_id = get_rich_text(props, 'Episode ID')
        task_id = derive_task_id(episode_id)
        if not task_id:
            skipped_unparseable += 1
            if len(unparseable_examples) < 5:
                unparseable_examples.append(episode_id or '(empty)')
            continue
        upd = b.update_page_properties(page_id, {
            'Task ID': {'rich_text': [{'type': 'text', 'text': {'content': task_id}}]}
        })
        if upd.get('error'):
            print('  UPDATE_FAILED', page_id, upd.get('status_code'), upd.get('message'))
        else:
            updated += 1
        time.sleep(0.1)
    print('  updated=%d skipped_has_task_id=%d skipped_unparseable=%d' % (updated, skipped_has_task_id, skipped_unparseable))
    if unparseable_examples:
        print('  unparseable_examples:', unparseable_examples)


def backfill_prompt_library():
    name, db_id = 'Prompt Library', PROMPT_LIBRARY_DB
    print('===', name, db_id, '===')
    if not ensure_task_id_property(db_id):
        return
    res = b.query_db(db_id)
    if res.get('error'):
        print('  QUERY_FAILED:', res)
        return
    rows = res.get('results', [])
    print('  rows:', len(rows))
    updated, skipped_has_task_id, skipped_unparseable = 0, 0, 0
    unparseable_examples = []
    for row in rows:
        page_id = row.get('id')
        props = row.get('properties', {})
        existing_task_id = get_rich_text(props, 'Task ID')
        if existing_task_id:
            skipped_has_task_id += 1
            continue
        title = get_title(props, 'Title')
        task_id = derive_task_id_from_title(title)
        if not task_id:
            skipped_unparseable += 1
            if len(unparseable_examples) < 5:
                unparseable_examples.append(title or '(empty)')
            continue
        upd = b.update_page_properties(page_id, {
            'Task ID': {'rich_text': [{'type': 'text', 'text': {'content': task_id}}]}
        })
        if upd.get('error'):
            print('  UPDATE_FAILED', page_id, upd.get('status_code'), upd.get('message'))
        else:
            updated += 1
        time.sleep(0.1)
    print('  updated=%d skipped_has_task_id=%d skipped_unparseable=%d' % (updated, skipped_has_task_id, skipped_unparseable))
    if unparseable_examples:
        print('  unparseable_examples (generic/non-episode rows, left as-is):', unparseable_examples)


if __name__ == '__main__':
    for name, db_id in DATABASES.items():
        backfill_db(name, db_id)
    backfill_prompt_library()
    print('DONE')
