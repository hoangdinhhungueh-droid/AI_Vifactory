"""
migrate_prompt_library_ep001.py -- Move the 17 real per-scene image prompts
for en-byzantine-empire-ep001 out of the flat, mixed-purpose Prompt Library DB
into a dedicated subpage + child database, mirroring the Director Plan
restructuring (plan item 5, partial: only the genuinely per-episode rows).

Deliberately NOT touched by this script (left in the flat DB, per plan's own
"khong tu suy noi dung prompt" rule -- do not invent template content):
  - The 1 'episode' category hub/pointer row for en-enron-ep006 (its real
    scene prompts already live in the migrated Director Plan child DB).
  - The 14 generic cross-stage template skeleton rows (seo/script/tts/viral/
    image categories) whose prompt_text is empty -- these are reusable
    templates across all episodes, not per-episode data, and their canonical
    text was not found already written down anywhere in the Decision Log.

Safe to re-run: skips if the manifest already shows status 'done'.
"""
import sys, json, os
sys.path.insert(0, '/root/video_factory/scripts')
import ag_notion_bridge as b

FLAT_DB_ID = '8c801989-2400-831a-901d-014aebdc3b31'
PARENT_PAGE_ID = '73801989-2400-82a7-ae5f-0110bfb666c8'
MANIFEST_PATH = '/tmp/vf/_prompt_library_ep001_migration_manifest.json'
EP_ID = 'en-byzantine-empire-ep001'
TASK_ID = 'EP001-EN'

ROW_IDS = [
    "3c401989-2400-8127-8fdd-c1bf1a2ebbd7", "3c401989-2400-81c7-ae4d-c2b0bba1474b",
    "3c401989-2400-815c-8d83-e6fcd2c456f3", "3c401989-2400-819a-9e5b-e3a7cc1db799",
    "3c401989-2400-81d1-b31a-ec280249d3e1", "3c401989-2400-8181-a14c-e96e163dbdd4",
    "3c401989-2400-8108-8a9c-f3092933e8a9", "3c401989-2400-81c4-a882-d7decca941ac",
    "3c401989-2400-8123-83dc-f380459da859", "3c401989-2400-8128-a7ff-cabe009d06f7",
    "3c401989-2400-8190-8b13-d92a73f76176", "3c401989-2400-81cf-ac93-d126e78afd7b",
    "3c401989-2400-81bc-acb9-d50c59ca7aa3", "3c401989-2400-8104-be77-f6efd0487b0b",
    "3c401989-2400-814b-8a37-f7eb541f09b0", "3c401989-2400-81bc-a83f-c41944cb882e",
    "3c401989-2400-81d1-a395-cd3b5e648f92",
]


def clean_property_schema(props):
    def strip_ids(obj):
        if isinstance(obj, dict):
            return {k: strip_ids(v) for k, v in obj.items() if k != 'id'}
        if isinstance(obj, list):
            return [strip_ids(v) for v in obj]
        return obj

    cleaned = {}
    for name, spec in props.items():
        if name == 'Title':
            continue  # title property is implicit for new databases
        t = spec['type']
        cleaned[name] = {'type': t, t: strip_ids(spec.get(t, {}))}
    return cleaned


def load_manifest():
    if os.path.exists(MANIFEST_PATH):
        with open(MANIFEST_PATH) as f:
            return json.load(f)
    return {}


def save_manifest(m):
    with open(MANIFEST_PATH, 'w') as f:
        json.dump(m, f, indent=2)


def main():
    manifest = load_manifest()
    if manifest.get('status') == 'done':
        print('Already migrated. Manifest:', json.dumps(manifest, indent=2))
        return

    schema_res = b._req('GET', 'databases/' + FLAT_DB_ID, None)
    if schema_res.get('error'):
        print('FATAL: could not load flat DB schema:', schema_res)
        return
    props_schema = schema_res.get('properties', {})
    new_db_properties = clean_property_schema(props_schema)

    rows = []
    for rid in ROW_IDS:
        r = b._req('GET', 'pages/' + rid, None)
        if r.get('error'):
            print('FATAL: could not load row', rid, r)
            return
        rows.append(r)
    print('Loaded %d source rows.' % len(rows))

    page_title = 'Prompt Library \u2014 %s (%s)' % (TASK_ID, EP_ID)
    callout_text = ('Task ID: %s | Episode ID: %s | %d BG/FG image prompts. Migrated from the '
                     'flat, mixed-purpose Prompt Library DB on 23/08/2026 (per-episode subset '
                     'only; the 14 generic cross-stage template rows were left in place).') % (
                         TASK_ID, EP_ID, len(rows))
    page_payload = {
        'parent': {'type': 'page_id', 'page_id': PARENT_PAGE_ID},
        'icon': {'type': 'emoji', 'emoji': '\U0001F9E9'},
        'properties': {'title': {'title': [{'type': 'text', 'text': {'content': page_title}}]}},
        'children': [
            {
                'object': 'block',
                'type': 'callout',
                'callout': {
                    'icon': {'type': 'emoji', 'emoji': '\U0001F9E9'},
                    'rich_text': [{'type': 'text', 'text': {'content': callout_text}}]
                }
            }
        ]
    }
    page_res = b._req('POST', 'pages', page_payload)
    if page_res.get('error'):
        print('FAILED to create subpage:', page_res)
        return
    subpage_id = page_res['id']
    print('Created subpage:', subpage_id)

    db_payload = {
        'parent': {'type': 'page_id', 'page_id': subpage_id},
        'title': [{'type': 'text', 'text': {'content': 'Prompts'}}],
        'properties': dict(new_db_properties, Title={'title': {}}),
    }
    db_res = b._req('POST', 'databases', db_payload)
    if db_res.get('error'):
        print('FAILED to create child database:', db_res)
        manifest.update({'status': 'partial_page_only', 'subpage_id': subpage_id})
        save_manifest(manifest)
        return
    child_db_id = db_res['id']
    print('Created child database:', child_db_id)

    copied = 0
    failed_rows = []
    for r in rows:
        src_props = r.get('properties', {})
        new_props = {}
        for name, spec in src_props.items():
            t = spec.get('type')
            if t == 'title':
                new_props[name] = {'title': spec.get('title', [])}
            elif t == 'rich_text':
                new_props[name] = {'rich_text': spec.get('rich_text', [])}
            elif t == 'number':
                new_props[name] = {'number': spec.get('number')}
            elif t == 'select':
                sel = spec.get('select')
                new_props[name] = {'select': ({'name': sel['name']} if sel else None)}
            elif t == 'date':
                new_props[name] = {'date': spec.get('date')}
            elif t == 'checkbox':
                new_props[name] = {'checkbox': spec.get('checkbox')}
        create_res = b._req('POST', 'pages', {
            'parent': {'type': 'database_id', 'database_id': child_db_id},
            'properties': new_props,
        })
        if create_res.get('error'):
            failed_rows.append((r.get('id'), create_res))
        else:
            copied += 1
    print('Copied %d/%d rows (%d failed)' % (copied, len(rows), len(failed_rows)))
    for fid, err in failed_rows[:5]:
        print('  FAILED row', fid, ':', err)

    if failed_rows:
        print('NOT archiving originals -- some rows failed to copy. Fix and re-run.')
        manifest.update({'status': 'partial', 'subpage_id': subpage_id, 'child_db_id': child_db_id,
                          'copied': copied, 'failed': len(failed_rows)})
        save_manifest(manifest)
        return

    verify_res = b.query_db(child_db_id)
    verify_count = len(verify_res.get('results', [])) if not verify_res.get('error') else -1
    if verify_count != len(rows):
        print('VERIFY MISMATCH: expected %d, found %d. NOT archiving originals.' % (len(rows), verify_count))
        manifest.update({'status': 'verify_failed', 'subpage_id': subpage_id, 'child_db_id': child_db_id})
        save_manifest(manifest)
        return

    archived = 0
    for r in rows:
        arch_res = b._req('PATCH', 'pages/' + r['id'], {'archived': True})
        if not arch_res.get('error'):
            archived += 1
    print('Verified %d rows in child DB. Archived %d/%d original rows.' % (verify_count, archived, len(rows)))

    manifest.update({
        'status': 'done',
        'subpage_id': subpage_id,
        'child_db_id': child_db_id,
        'row_count': len(rows),
        'archived_originals': archived,
    })
    save_manifest(manifest)
    print('DONE. Manifest:', json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
