#!/usr/bin/env python3
import sys, asyncio, os, re, httpx
sys.path.insert(0, '/root/video_factory')
from app.services import telegram_buttons as tb
from app.services.hhtech_reasoner import reason_topic_niche
from app.services.trend_gate_ai import get_next_episode_id

# 1. Reason with GPT-6-Astra
en_info = reason_topic_niche("Jack the Ripper", "EN", 0.97)
jp_info = reason_topic_niche("ライブドア事件", "JP", 0.832)
kr_info = reason_topic_niche("도박 중독", "KR", 0.723)

en_slug = en_info.get('task_slug', 'jack-the-ripper')
jp_slug = jp_info.get('task_slug', 'livedoor-scandal')
kr_slug = kr_info.get('task_slug', 'kangwonland-trap')

# 2. Dynamic Episode IDs
en_task = get_next_episode_id("EN", en_slug)
jp_task = get_next_episode_id("JP", jp_slug)
kr_task = get_next_episode_id("KR", kr_slug)

print('Resolved Task IDs:', en_task, jp_task, kr_task)

# 3. Cache pending tasks (DELAYED increment -- committed to Notion
# only when /run task:<id> actually triggers production; see
# app/services/episode_numbering.py)
from app.services import episode_numbering as _epnum
for m_name, t_sub, t_v, t_id, t_dict in [("EN", "Jack the Ripper", 0.97, en_task, en_info), ("JP", "ライブドア事件", 0.832, jp_task, jp_info), ("KR", "도박 중독", 0.723, kr_task, kr_info)]:
    _epnum.cache_pending_task(t_id, m_name, {
        "topic_name": str(t_dict.get("topic_name_vi", t_sub)),
        "keyword": str(t_dict.get("search_specific_keyword", t_sub)),
        "virality_score": t_v,
        "niche_brief": str(t_dict.get("niche_angle_brief", "")),
        "story_arcs": str(t_dict.get("story_direction_5_arcs", "")),
    })

# Save gate1 pending tasks for bulk actions
tb._save_gate1_pending({'en': en_task, 'jp': jp_task, 'kr': kr_task})

gate1_text = (
    "🎯 <b>[HUMAN GATE 1] PHÊ DUYỆT CHỦ ĐỀ SẢN XUẤT (GO-LIVE 2026)</b>\n"
    "<i>(✨ Suy luận chiến lược & Đúc kết ngách bởi GPT-6-Astra qua HHTech API)</i>\n\n"
    f"🇺🇸 <b>Market EN:</b> <code>Jack the Ripper</code> (Virality: 0.97)\n"
    f"• <b>Đề tài:</b> {en_info.get('topic_name_vi')}\n"
    f"• <b>Search-Specific Key:</b> <code>{en_info.get('search_specific_keyword')}</code>\n"
    f"• <b>Niche Brief:</b> {en_info.get('niche_angle_brief')}\n"
    f"• <b>5-Act Direction:</b> {en_info.get('story_direction_5_arcs')[:200]}...\n"
    f"👉 <b>Task ID / Mã khởi động EN:</b> <code>{en_task}</code>\n\n"
    f"🇯🇵 <b>Market JP:</b> <code>ライブドア事件</code> (Virality: 0.832)\n"
    f"• <b>Đề tài:</b> {jp_info.get('topic_name_vi')}\n"
    f"• <b>Search-Specific Key:</b> <code>{jp_info.get('search_specific_keyword')}</code>\n"
    f"• <b>Niche Brief:</b> {jp_info.get('niche_angle_brief')}\n"
    f"• <b>5-Act Direction:</b> {jp_info.get('story_direction_5_arcs')[:200]}...\n"
    f"👉 <b>Task ID / Mã khởi động JP:</b> <code>{jp_task}</code>\n\n"
    f"🇰🇷 <b>Market KR:</b> <code>도박 중독</code> (Virality: 0.723)\n"
    f"• <b>Đề tài:</b> {kr_info.get('topic_name_vi')}\n"
    f"• <b>Search-Specific Key:</b> <code>{kr_info.get('search_specific_keyword')}</code>\n"
    f"• <b>Niche Brief:</b> {kr_info.get('niche_angle_brief')}\n"
    f"• <b>5-Act Direction:</b> {kr_info.get('story_direction_5_arcs')[:200]}...\n"
    f"👉 <b>Task ID / Mã khởi động KR:</b> <code>{kr_task}</code>\n\n"
    "--------------------------------------------------\n"
    "💡 <i>Bấm <b>[Approve]</b> để duyệt kênh cần sản xuất. Copy <b>Task ID</b> dán vào Antigravity chat để bắt đầu B2-B10!</i>"
)

gate1_rows = [
    [(f'🇺🇸 EN: Approve ✅', f'apr:{en_task}'), (f'🇺🇸 EN: Deny ❌', f'rej:{en_task}')],
    [(f'🇯🇵 JP: Approve ✅', f'apr:{jp_task}'), (f'🇯🇵 JP: Deny ❌', f'rej:{jp_task}')],
    [(f'🇰🇷 KR: Approve ✅', f'apr:{kr_task}'), (f'🇰🇷 KR: Deny ❌', f'rej:{kr_task}')],
    [('🚀 Approve Tất Cả 3 Kênh', 'ap_all'), ('❌ Deny Tất Cả', 'rj_all')]
]

asyncio.run(tb.send_with_buttons(gate1_text, gate1_rows))
print('Sent Telegram Gate 1 with dynamic episode numbers!')
