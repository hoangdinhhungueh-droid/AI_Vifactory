"""
migrate_director_plan.py -- Restructure the flat Director Plan database into
"1 Episode = 1 subpage + 1 child scene database", per the 23/08/2026
implementation plan (item 4).

For each distinct Episode ID currently in the flat Director Plan DB:
  1. Create a subpage (sibling of the old flat DB, under the same parent)
     titled with the episode's Task ID + Episode ID.
  2. Create a child database inside that subpage with the same property
     schema as the flat DB.
  3. Copy every scene row for that episode into the new child database.
  4. Archive (not delete) the original rows in the flat DB once the copy is
     verified to have the same row count.

Safe to re-run: skips episodes that already have a migrated subpage (tracked
via a small on-disk manifest at /tmp/vf/_director_plan_migration_manifest.json).
"""
import sys, json, os
sys.path.insert(0, '/root/video_factory/scripts')
import ag_notion_bridge as b

FLAT_DB_ID = '5b201989-2400-8295-be81-81c2c0e4e138'
PARENT_PAGE_ID = '73801989-2400-82a7-ae5f-0110bfb666c8'
MANIFEST_PATH = '/tmp/vf/_director_plan_migration_manifest.json'


def get_rich_text(props, name):
    p = props.get(name) or {}
    arr = p.get('rich_text') or []
    return ''.join(seg.get('plain_text', '') for seg in arr)


def clean_property_schema(props):
    """Strip server-assigned ids from a property schema so it can be reused
    verbatim when creating a new database (keeps options/groups/colors)."""
    def strip_ids(obj):
        if isinstance(obj, dict):
            return {k: strip_ids(v) for k, v in obj.items() if k != 'id'}
        if isinstance(obj, list):
            return [strip_ids(v) for v in obj]
        return obj

    cleaned = {}
    for name, spec in props.items():
        if name == 'Name':
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

    schema_res = b._req('GET', 'databases/' + FLAT_DB_ID, None)
    if schema_res.get('error'):
        print('FATAL: could not load flat DB schema:', schema_res)
        return
    props_schema = schema_res.get('properties', {})
    new_db_properties = clean_property_schema(props_schema)

    query_res = b.query_db(FLAT_DB_ID)
    if query_res.get('error'):
        print('FATAL: could not query flat DB:', query_res)
        return
    rows = query_res.get('results', [])
    print('Flat DB total rows:', len(rows))

    by_episode = {}
    for r in rows:
        eid = get_rich_text(r.get('properties', {}), 'Episode ID')
        by_episode.setdefault(eid, []).append(r)

    for eid, ep_rows in by_episode.items():
        if not eid:
            print('SKIP: rows with empty Episode ID (%d rows) -- needs manual triage' % len(ep_rows))
            continue
        if manifest.get(eid, {}).get('status') == 'done':
            print('SKIP (already migrated):', eid)
            continue

        task_id = get_rich_text(ep_rows[0].get('properties', {}), 'Task ID') or eid
        print('=== Migrating', eid, '(%d scenes, Task ID=%s) ===' % (len(ep_rows), task_id))

        # 1. Create subpage
        page_title = 'Director Plan \u2014 %s (%s)' % (task_id, eid)
        callout_text = 'Task ID: %s | Episode ID: %s | %d scenes. Migrated from the flat Director Plan DB on 23/08/2026 (1 EP = 1 subpage + child scene DB restructuring).' % (task_id, eid, len(ep_rows))
        page_payload = {
            'parent': {'type': 'page_id', 'page_id': PARENT_PAGE_ID},
            'icon': {'type': 'emoji', 'emoji': '\U0001F3AC'},
            'properties': {
                'title': {'title': [{'type': 'text', 'text': {'content': page_title}}]}
            },
            'children': [
                {
                    'object': 'block',
                    'type': 'callout',
                    'callout': {
                        'icon': {'type': 'emoji', 'emoji': '\U0001F3AC'},
                        'rich_text': [{'type': 'text', 'text': {'content': callout_text}}]
                    }
                }
            ]
        }
        page_res = b._req('POST', 'pages', page_payload)
        if page_res.get('error'):
            print('  FAILED to create subpage:', page_res)
            continue
        subpage_id = page_res['id']
        print('  Created subpage:', subpage_id)

        # 2. Create child database inside the subpage
        db_payload = {
            'parent': {'type': 'page_id', 'page_id': subpage_id},
            'title': [{'type': 'text', 'text': {'content': 'Scenes'}}],
            'properties': dict(new_db_properties, Name={'title': {}}),
        }
        db_res = b._req('POST', 'databases', db_payload)
        if db_res.get('error'):
            print('  FAILED to create child database:', db_res)
            continue
        child_db_id = db_res['id']
        print('  Created child database:', child_db_id)

        # 3. Copy rows
        copied = 0
        failed_rows = []
        for r in ep_rows:
            src_props = r.get('properties', {})
            new_props = {}
            for name, spec in src_props.items():
                if name == 'Created At':
                    continue  # created_time is auto-generated, cannot be set
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
                elif t == 'status':
                    st = spec.get('status')
                    new_props[name] = {'status': ({'name': st['name']} if st else None)}
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
        print('  Copied %d/%d scenes (%d failed)' % (copied, len(ep_rows), len(failed_rows)))
        for fid, err in failed_rows[:5]:
            print('    FAILED row', fid, ':', err)

        if failed_rows:
            print('  NOT archiving originals for', eid, '-- some rows failed to copy. Fix and re-run.')
            manifest[eid] = {'status': 'partial', 'subpage_id': subpage_id, 'child_db_id': child_db_id, 'copied': copied, 'failed': len(failed_rows)}
            save_manifest(manifest)
            continue

        # 4. Verify + archive originals
        verify_res = b.query_db(child_db_id)
        verify_count = len(verify_res.get('results', [])) if not verify_res.get('error') else -1
        if verify_count != len(ep_rows):
            print('  VERIFY MISMATCH: expected %d, found %d in child DB. NOT archiving originals.' % (len(ep_rows), verify_count))
            manifest[eid] = {'status': 'verify_failed', 'subpage_id': subpage_id, 'child_db_id': child_db_id}
            save_manifest(manifest)
            continue

        archived = 0
        for r in ep_rows:
            arch_res = b._req('PATCH', 'pages/' + r['id'], {'archived': True})
            if not arch_res.get('error'):
                archived += 1
        print('  Verified %d rows in child DB. Archived %d/%d original rows.' % (verify_count, archived, len(ep_rows)))

        manifest[eid] = {
            'status': 'done',
            'subpage_id': subpage_id,
            'child_db_id': child_db_id,
            'scene_count': len(ep_rows),
            'archived_originals': archived,
        }
        save_manifest(manifest)

    print('DONE. Manifest:', json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
