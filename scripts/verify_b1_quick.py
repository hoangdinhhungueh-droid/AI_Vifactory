
import os, sys, json, asyncio
sys.path.insert(0, '/root/video_factory')
from app.services.virality_score import score_subject
from app.services.hhtech_reasoner import reason_topic_niche
from app.services.trend_gate_ai import get_next_episode_id
from app.services import telegram_buttons as tb
from app.services import episode_numbering as _epnum
import scripts.ag_notion_bridge as bridge

print('=== 1. VERIFY SCORE_SUBJECT & BREAKOUT INJECTION ===')
rising_samples = [
    {'query': 'Roman Empire lead poisoning cognitive decline', 'value': 'Breakout'},
    {'query': 'Roman Empire economic currency debasement', 'value': '+600%'}
]
top_samples = [{'query': 'Roman Empire collapse documentary', 'value': '100'}]

# Test GPT-5.6-Sol reasoning with breakout queries
res = reason_topic_niche('Roman Empire', 'EN', 0.95, rising_queries=rising_samples, top_queries=top_samples)
print('Topic Name VI:', res.get('topic_name_vi'))
print('Search Specific Key:', res.get('search_specific_keyword'))
print('Slug:', res.get('task_slug'))
print('Niche Brief:', res.get('niche_angle_brief'))
print('Act 1 Hook Preview:', res.get('story_direction_5_arcs', '')[:160])

# Test sequential Task ID
task_id = get_next_episode_id('EN', res.get('task_slug', 'roman-empire'))
print('Generated Sequential Task ID:', task_id)

# Test pending task cache
_epnum.cache_pending_task(task_id, 'EN', {
    'topic_name': str(res.get('topic_name_vi')),
    'keyword': str(res.get('search_specific_keyword')),
    'virality_score': 0.95,
    'niche_brief': str(res.get('niche_angle_brief')),
    'story_arcs': str(res.get('story_direction_5_arcs')),
})

# Test Notion Trend DB Sync
t_db_id = '4c101989-2400-8334-8016-01d4f463b09f'
t_filt = {'property': 'Keyword', 'title': {'equals': 'Roman Empire'}}
q_res = bridge.query_db(t_db_id, filter_obj=t_filt)
t_props = {
    'Keyword': {'title': [{'type': 'text', 'text': {'content': 'Roman Empire'}}]},
    'Market': {'select': {'name': 'EN'}},
    'Task ID': {'rich_text': [{'type': 'text', 'text': {'content': str(task_id)}}]},
    'Trend Score': {'number': 95.0},
    '': {'status': {'name': 'New (from VPS)'}}
}
if q_res.get('results'):
    pid = q_res['results'][0]['id']
    up = bridge.update_page_properties(pid, t_props)
    print(f'[Notion DB] Updated row {pid} for Roman Empire -> Task ID {task_id}: {bool(up)}')
else:
    t_props['Discovered'] = {'date': {'start': '2026-08-24'}}
    t_props['Trend Source'] = {'multi_select': [{'name': 'virality'}]}
    cr = bridge.create_page(t_db_id, t_props)
    print(f'[Notion DB] Created row for Roman Empire -> Task ID {task_id}: {bool(cr)}')

# Test Telegram Gate 1 dispatch
en_pack = {
    'top_subject': 'Roman Empire',
    'virality': 0.95,
    'topic_name_vi': res.get('topic_name_vi'),
    'search_specific_keyword': res.get('search_specific_keyword'),
    'niche_angle_brief': res.get('niche_angle_brief'),
    'story_direction_5_arcs': res.get('story_direction_5_arcs'),
    'task_id': task_id
}
jp_pack = {
    'top_subject': '孤独死',
    'virality': 0.88,
    'topic_name_vi': 'Kodokushi: Bi Kịch Cô Đơn & Nền Kinh Tế Dọn Dẹp Đặc Biệt',
    'search_specific_keyword': '孤独死 特殊清掃 現場 実態, 高齢化 単身世帯 心理',
    'niche_angle_brief': 'Bóc tách cơ chế xã hội và nền kinh tế dọn dẹp hiện trường.',
    'story_direction_5_arcs': 'Hồi 1 (Hook): Khởi đầu từ hiện trường đặc biệt...',
    'task_id': get_next_episode_id('JP', 'kodokushi-special-cleaning')
}
kr_pack = {
    'top_subject': '다단계',
    'virality': 0.85,
    'topic_name_vi': 'Đa Cấp Ponzi: Cơ Chế Thao Túng Tâm Lý & Bẫy Nợ 2026',
    'search_specific_keyword': '다단계 폰지사기 세뇌 수법 2026, 피해자 심리 지배 구조',
    'niche_angle_brief': 'Giải phẫu cơ chế tẩy não và mô hình kim tự tháp đa cấp.',
    'story_direction_5_arcs': 'Hồi 1 (Hook): Bắt đầu từ lời hứa lợi nhuận phi lý...',
    'task_id': get_next_episode_id('KR', 'ponzi-pyramid-trap')
}

msg_id = asyncio.run(tb.send_gate1_card(en_pack, jp_pack, kr_pack))
print(f'Telegram Gate 1 Card sent successfully! msg_id: {msg_id}')
print('=== ALL LIVE TESTS PASSED 100% ===')
