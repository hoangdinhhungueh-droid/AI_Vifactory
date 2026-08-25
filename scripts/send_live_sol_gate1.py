
import sys, asyncio
sys.path.insert(0, '/root/video_factory')
from app.services import telegram_buttons as tb
from app.services.hhtech_reasoner import reason_topic_niche

en_info = reason_topic_niche("Byzantine Empire", "EN", 0.973)
jp_info = reason_topic_niche("ライブドア事件", "JP", 0.832)
kr_info = reason_topic_niche("도박 중독", "KR", 0.722)

en_task = f"en-{en_info.get('task_slug', 'topic')}-ep001"
jp_task = f"jp-{jp_info.get('task_slug', 'topic')}-ep001"
kr_task = f"kr-{kr_info.get('task_slug', 'topic')}-ep001"

# Save to Notion Story Library
try:
    import os, httpx
    ntoken = os.getenv("NOTION_TOKEN")
    if ntoken:
        s_headers = {"Authorization": f"Bearer {ntoken}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}
        s_db_id = "b0301989-2400-836b-bdb5-8131fea17736"
        for m_name, t_sub, t_v, t_id, t_dict in [("EN", "Byzantine Empire", 0.973, en_task, en_info), ("JP", "ライブドア事件", 0.832, jp_task, jp_info), ("KR", "도박 중독", 0.722, kr_task, kr_info)]:
            row = {
                "parent": {"database_id": s_db_id},
                "properties": {
                    "Name": {"title": [{"type": "text", "text": {"content": f"[{m_name}] " + str(t_dict.get("topic_name_vi", t_sub))}}]},
                    "Episode ID": {"rich_text": [{"type": "text", "text": {"content": t_id}}]},
                    "Keyword": {"rich_text": [{"type": "text", "text": {"content": str(t_dict.get("search_specific_keyword", t_sub))}}]},
                    "Market": {"select": {"name": m_name}},
                    "Virality Score": {"number": int(float(t_v)*100)},
                    "Niche Angle Brief": {"rich_text": [{"type": "text", "text": {"content": str(t_dict.get("niche_angle_brief", ""))}}]},
                    "Story Direction (5 Arcs)": {"rich_text": [{"type": "text", "text": {"content": str(t_dict.get("story_direction_5_arcs", ""))}}]}
                }
            }
            httpx.post("https://api.notion.com/v1/pages", headers=s_headers, json=row, timeout=10.0)
except Exception as e:
    print("Notion error:", e)

gate1_text = (
    "🎯 <b>[HUMAN GATE 1] PHÊ DUYỆT CHỦ ĐỀ SẢN XUẤT (GO-LIVE 2026)</b>\n"
    "<i>(✨ Suy luận chiến lược & Đúc kết ngách bởi GPT-5.6-Sol qua HHTech API)</i>\n\n"
    f"🇺🇸 <b>Market EN:</b> <code>Byzantine Empire</code> (Virality: 0.973)\n"
    f"• <b>Đề tài:</b> {en_info.get('topic_name_vi')}\n"
    f"• <b>Search-Specific Key:</b> <code>{en_info.get('search_specific_keyword')}</code>\n"
    f"• <b>Niche Brief:</b> {en_info.get('niche_angle_brief')}\n"
    f"• <b>5-Act Direction:</b> {en_info.get('story_direction_5_arcs')[:220]}...\n"
    f"👉 <b>Mã khởi động EN:</b> <code>/run task:{en_task}</code>\n\n"
    f"🇯🇵 <b>Market JP:</b> <code>ライブドア事件</code> (Virality: 0.832)\n"
    f"• <b>Đề tài:</b> {jp_info.get('topic_name_vi')}\n"
    f"• <b>Search-Specific Key:</b> <code>{jp_info.get('search_specific_keyword')}</code>\n"
    f"• <b>Niche Brief:</b> {jp_info.get('niche_angle_brief')}\n"
    f"• <b>5-Act Direction:</b> {jp_info.get('story_direction_5_arcs')[:220]}...\n"
    f"👉 <b>Mã khởi động JP:</b> <code>/run task:{jp_task}</code>\n\n"
    f"🇰🇷 <b>Market KR:</b> <code>도박 중독</code> (Virality: 0.722)\n"
    f"• <b>Đề tài:</b> {kr_info.get('topic_name_vi')}\n"
    f"• <b>Search-Specific Key:</b> <code>{kr_info.get('search_specific_keyword')}</code>\n"
    f"• <b>Niche Brief:</b> {kr_info.get('niche_angle_brief')}\n"
    f"• <b>5-Act Direction:</b> {kr_info.get('story_direction_5_arcs')[:220]}...\n"
    f"👉 <b>Mã khởi động KR:</b> <code>/run task:{kr_task}</code>\n\n"
    "--------------------------------------------------\n"
    "💡 <i>Bấm <b>[Approve]</b> rồi copy <b>Mã khởi động</b> dán vào chat Antigravity để bắt đầu sản xuất B2-B10!</i>"
)

gate1_rows = [
    [('🇺🇸 EN: Approve ✅', 'ap:en'), ('🇺🇸 EN: Deny ❌', 'rj:en')],
    [('🇯🇵 JP: Approve ✅', 'ap:jp'), ('🇯🇵 JP: Deny ❌', 'rj:jp')],
    [('🇰🇷 KR: Approve ✅', 'ap:kr'), ('🇰🇷 KR: Deny ❌', 'rj:kr')],
    [('🚀 Approve Tất Cả 3 Kênh', 'ap_all'), ('❌ Deny Tất Cả', 'rj_all')]
]

asyncio.run(tb.send_with_buttons(gate1_text, gate1_rows))
print('Delivered Live HHTech GPT-5.6-Sol Gate 1 notification to Telegram!')
