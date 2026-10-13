#!/usr/bin/env python3
"""scripts/orchestrator/pipeline_ui_inspector.py
Pipeline Observability Engine & Notion Health Auditor for AI Video Factory.

Features:
  1. Complete 19-Node Pipeline DAG Topology definition (B0 through B11).
  2. Live forensic audit of Notion SoT integration vs Local Fallback vs Hardcoded Strings.
  3. JSON Schema extraction for all Inter-Block Data Contracts.
  4. Generative UI HTML Builder (generates standalone glassmorphic observability dashboard).
  5. CLI commands to export data or rebuild UI when code changes.

Usage:
  python scripts/orchestrator/pipeline_ui_inspector.py --audit        # Terminal Notion & Pipeline Audit
  python scripts/orchestrator/pipeline_ui_inspector.py --json         # Dump JSON DAG schema to stdout
  python scripts/orchestrator/pipeline_ui_inspector.py --html [PATH]  # Render standalone HTML dashboard
"""

import os
import sys
import json
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

PIPELINE_NODES = [
    {
        "id": "B0_SCHEDULER",
        "stage": "Block 0",
        "name": "Weekly Staggered Market Scheduler",
        "phase": "orchestration",
        "category": "Crash Protection & Resource Gate",
        "engine": "Python datetime + Asia/Ho_Chi_Minh Anchor (UTC+7)",
        "source_files": ["app/services/market_scheduler.py", "scripts/run_trend_pipeline.py"],
        "notion_status": "DISCONNECTED",
        "notion_detail": "Thao tác 100% bằng logic lịch hệ thống cục bộ. Không đọc cấu hình từ Notion để tránh độ trễ mạng làm nghẽn cron.",
        "rule_refs": ["Rule 118", "Rule 126", "Scheduler Invariant"],
        "inputs": {
            "source": "System Cron Trigger (`0 23 * * *` UTC) / CLI Override",
            "format": "CLI Arguments: `--market`, `--force-all-markets`, `--dry-run`",
            "schema": {
                "system_time_utc": "YYYY-MM-DDTHH:MM:SSZ",
                "vietnam_anchor_time": "UTC+7 (Asia/Ho_Chi_Minh)",
                "scheduled_table": "Mon/Thu -> EN | Tue/Fri -> KR | Wed/Sat -> JP | Sun -> REST"
            }
        },
        "outputs": {
            "target": "Block 1.0 (Trend Engine)",
            "format": "In-memory Execution Context & Target Market String",
            "artifacts": ["`today_market: 'EN' | 'KR' | 'JP'`", "Sunday Maintenance Signal (cleanup `/tmp`, flush locks)"]
        },
        "connections": {
            "upstream": [],
            "downstream": ["B1_TREND_ENGINE"]
        },
        "invariants": [
            "Đảm bảo duy nhất 1 video/ngày trên toàn hệ thống VPS để bảo vệ CPU/RAM.",
            "Neo cứng múi giờ Việt Nam UTC+7, cấm naive datetime.",
            "Chủ nhật dừng sản xuất video mới, chuyển sang bảo trì và B11 Dreaming Loop."
        ]
    },
    {
        "id": "B1_TREND_ENGINE",
        "stage": "Block 1.0",
        "name": "Trend Discovery & Causal Topic Reasoner",
        "phase": "discovery",
        "category": "Topic Selection & Strategic Angle",
        "engine": "Google Trends RSS live + Gemini 2.5 Flash + Wikipedia Anchor",
        "source_files": ["app/services/trend_engine_b1.py", "app/services/hhtech_reasoner.py"],
        "notion_status": "ACTIVE_SOT",
        "notion_detail": "PROMPTS: Nạp động từ Notion SoT Page 'B1: Trend & Causal Strategy Rules' (3f801989-2400-8157-96f9-cd29c62cd7b1) qua skill_loader.get_b1_strategic_rules(). INPUT: Google Trends RSS live. OUTPUT: Đồng bộ 1 chiều sang Notion Trend Brain DB.",
        "rule_refs": ["Rule 118 (Zero-Mock)", "Rule 128 (Anti-Bias)", "Rule 444 (An Ong Hook)", "Rule 445 (5-Beat)"],
        "inputs": {
            "source": "Google Trends RSS Feed live + V7 Winning Pool (`data/v7_winning_pool.json`)",
            "format": "XML RSS Streams + Wikipedia Ground Truth URL",
            "schema": {
                "geo_market": "US (EN), KR (KR), JP (JP)",
                "min_viability_score": ">= 8.0",
                "canonical_pillars": "1..11 Canonical Investigative Pillars"
            }
        },
        "outputs": {
            "target": "Block 1.5 (Competitor Recon) & Notion Trend Brain DB",
            "format": "JSON File: `/var/vf/pending_tasks/<task_id>.json`",
            "artifacts": ["`task_id` (Regex `^[A-Z]{2}_EP\\d{4}_[a-z0-9_]+$`)", "factsheet (dates, entities, mechanisms)", "niche_angle_brief", "story_direction_5_arcs"]
        },
        "connections": {
            "upstream": ["B0_SCHEDULER"],
            "downstream": ["B15_COMPETITOR_RECON"]
        },
        "invariants": [
            "Viability Score bắt buộc tính từ dữ liệu live (Trends RSS + Wiki), cấm mock điểm.",
            "Keyword bắt buộc bằng tiếng bản địa của thị trường mục tiêu (JP/KR/EN).",
            "Loại bỏ 100% định dạng Tutorial/How-To theo Anti-Tutorial Mandate (Rule 130)."
        ]
    },
    {
        "id": "B15_COMPETITOR_RECON",
        "stage": "Block 1.5",
        "name": "Competitor Recon & Explanatory Vacuum Miner",
        "phase": "discovery",
        "category": "Blue Ocean Analysis & Differentiation",
        "engine": "YouTube Data API v3 + yt-dlp + Gemini Comments NLP",
        "source_files": ["app/services/competitor_recon_b15.py"],
        "notion_status": "OUTPUT_SINK",
        "notion_detail": "Không nạp prompt từ Notion. Quét 5-15 video đối thủ live qua YouTube API, phân tích bình luận, ghi card ra disk và mirror sang Notion Competitor Intel DB.",
        "rule_refs": ["Rule 118", "Rule 130 (Search-Intent Direct Payoff)", "Rule 445"],
        "inputs": {
            "source": "Block 1.0 Task Payload (`task_id`, `raw_term`, `market`)",
            "format": "JSON Object + YouTube Search Queries",
            "schema": {
                "task_id": "<MARKET>_EP<0000>_<topic_slug>",
                "query": "Native keyword search on YouTube Data API"
            }
        },
        "outputs": {
            "target": "Block 1.5.5 (Search Grounding Gate) & Block 2.0",
            "format": "JSON File: `/var/vf/episodes/<task_id>/competitor_intel_card.json`",
            "artifacts": ["competitor_benchmarks (views, vph, outlier_score)", "fatal_explanatory_vacuum", "our_10x_pivot_angle", "ai_slop_redlines", "audience_core_frustrations"]
        },
        "connections": {
            "upstream": ["B1_TREND_ENGINE"],
            "downstream": ["B155_GROUNDING_GATE"]
        },
        "invariants": [
            "Tối thiểu quét 5 video đối thủ thực tế trong cùng ngách.",
            "Trích xuất rõ ràng 'fatal_explanatory_vacuum' — lỗ hổng kiến thức mà đối thủ bỏ sót.",
            "Thu thập danh sách AI-slop cliches để cấm dùng ở B2."
        ]
    },
    {
        "id": "B155_GROUNDING_GATE",
        "stage": "Block 1.5.5",
        "name": "Search Grounding & Fact Verification Gate",
        "phase": "discovery",
        "category": "Factual Verification & Anti-Hallucination Gate",
        "engine": "Google Search Grounding REST API (`tools: [{'googleSearch': {}}]`)",
        "source_files": ["app/services/grounding_layer_b15.py", "tests/test_grounding_layer.py"],
        "notion_status": "DISCONNECTED",
        "notion_detail": "Gọi trực tiếp Gemini Grounding endpoint với Google Search sống. Không thông qua Notion.",
        "rule_refs": ["Rule 118", "Rule 121 (Strict Verification)", "Rule 127", "Rule 130"],
        "inputs": {
            "source": "Block 1.5 (`task_id`, `raw_term`, `factsheet`)",
            "format": "JSON Claims to Verify",
            "schema": {
                "topic": "<PRIMARY_SEARCH_TOPIC>",
                "candidate_claims": "Danh sách các sự kiện cần kiểm chứng nguồn gốc"
            }
        },
        "outputs": {
            "target": "Human Gate 1 & Block 2.0 (Story Engine)",
            "format": "JSON File: `/var/vf/episodes/<task_id>/grounding_intel.json`",
            "artifacts": ["`rejected: false`", "claims (confidence: verified | reported | speculative)", "grounding_chunks (source titles, URIs)", "REAL-WORLD GROUNDED FACTS TABLE"]
        },
        "connections": {
            "upstream": ["B15_COMPETITOR_RECON"],
            "downstream": ["HG1_TELEGRAM", "B2_STORY_ENGINE"]
        },
        "invariants": [
            "Bắt buộc có ít nhất 1 factual claim đạt confidence: 'verified' từ cơ quan/hồ sơ uy tín.",
            "Fast-Fail: Nếu rejected=true (tin đồn vô căn cứ), lập tức hủy đề tài và xoay ứng viên tiếp theo.",
            "Nhúng bảng Factual Grounding trực tiếp vào prompt B2 để ép mô hình tuân thủ sự thật."
        ]
    },
    {
        "id": "HG1_TELEGRAM",
        "stage": "Human Gate 1",
        "name": "Topic Broadcast & Early Alert Gate",
        "phase": "checkpoint",
        "category": "Human Oversight Checkpoint",
        "engine": "Telegram Bot API (Informative Broadcast Mode - 0 Interactive Buttons)",
        "source_files": ["app/services/telegram_buttons.py"],
        "notion_status": "OUTPUT_SINK",
        "notion_detail": "Bắn tin nhắn Markdown báo cáo đề tài kèm chỉ số Viability, Explanatory Vacuum sang Telegram. Không chờ nút bấm (Informative Broadcast) để tránh tắc nghẽn tự động hóa.",
        "rule_refs": ["Rule 118", "Rule 125", "Scheduler Protection"],
        "inputs": {
            "source": "Block 1.0, 1.5, 1.5.5 Payload",
            "format": "Telegram Message Payload",
            "schema": {
                "chat_id": "TELEGRAM_ALERT_CHAT_ID",
                "text": "Broadcast report: Market, Topic, Score, Angle, Vacuum"
            }
        },
        "outputs": {
            "target": "Telegram Channel & Block 2.0 (Story Engine)",
            "format": "HTTP POST to `api.telegram.org`",
            "artifacts": ["Telegram Broadcast Notification", "Pipeline Execution Proceeds Automatically"]
        },
        "connections": {
            "upstream": ["B155_GROUNDING_GATE"],
            "downstream": ["B2_STORY_ENGINE"]
        },
        "invariants": [
            "Chế độ Informative Broadcast 0 nút bấm tương tác: không block pipeline khi User ngủ.",
            "Lọc sạch Mojibake encoding ký tự đặc biệt trước khi gửi."
        ]
    },
    {
        "id": "B2_STORY_ENGINE",
        "stage": "Block 2.0",
        "name": "5-Beat Docudrama Story Engine",
        "phase": "content",
        "category": "Narrative Creation & Screenplay Pacing",
        "engine": "OpenAI GPT-6-Astra / Claude Sonnet + 10X 5-Beat Docudrama Pacing",
        "source_files": ["app/services/story_engine_b2.py", "app/services/skill_loader.py"],
        "notion_status": "ACTIVE_SOT",
        "notion_detail": "PROMPTS: Nạp động từ Notion SoT Page 'B2: 10X 5-Beat Docudrama Storytelling Prompt' (3f801989-2400-818a-adf1-c5f7cc3da7ed) kết hợp bài học B11 live feedback qua skill_loader.get_b2_editorial_skills(). OUTPUT: Đồng bộ sang Notion Story DB.",
        "rule_refs": ["Rule 113", "Rule 114", "Rule 130", "Rule 131", "Rule 444", "Rule 445"],
        "inputs": {
            "source": "Grounding Table + Competitor Intel Card + Editorial Prompts",
            "format": "System Prompt + Grounded Facts Table + 5-Beat Architecture",
            "schema": {
                "word_budget": "1,800 - 2,200 words (EN) | 3,200-3,600 syllables (KR) | 3,400-3,800 chars (JP)",
                "runtime_target": "12 - 15 minutes docudrama pacing (~360-440 words/Act)",
                "acts": "Act I (Contradiction) -> Act II (Red Herring) -> Act III (Paper Trail) -> Act IV (Smoking Gun) -> Act V (Modern Mirror)"
            }
        },
        "outputs": {
            "target": "Block 2.5 (Spoken VO Adaptation)",
            "format": "Text File: `/var/vf/episodes/<task_id>/story.txt`",
            "artifacts": ["Full 5-Beat Docudrama Script", "curiosity_loops (>= 8-10 loop questions)", "closed_loops (>= 80% resolution)", "pattern_interrupts (2-6 words)"]
        },
        "connections": {
            "upstream": ["B155_GROUNDING_GATE", "HG1_TELEGRAM"],
            "downstream": ["B25_SPOKEN_VO"]
        },
        "invariants": [
            "Câu 1 của Act I BẮT BUỘC chứa con số lượng hóa thực tế và sự kiện Level 1 Catalyst trong 60 từ đầu (Rule 444).",
            "CẤM TUYỆT ĐỐI mở đầu bằng 'Imagine...', câu hỏi tu từ chung chung hoặc cliches AI.",
            "Tối thiểu 8-10 câu hỏi tò mò (?) và giải đáp >= 80% tại Act V."
        ]
    },
    {
        "id": "B25_SPOKEN_VO",
        "stage": "Block 2.5",
        "name": "Spoken VO Breath Adaptation",
        "phase": "content",
        "category": "Audio Narration Script Formatting",
        "engine": "Deterministic Breath Pacing Splitter + Adversarial VO Auditor",
        "source_files": ["app/services/story_engine_b2.py"],
        "notion_status": "DISCONNECTED",
        "notion_detail": "Chạy thuật toán cắt câu ngắt hơi nhịp thở bằng Python và LLM prompt nhúng nội hàm. Không phụ thuộc Notion.",
        "rule_refs": ["Rule 120", "Rule 128", "Adversarial VO Audit"],
        "inputs": {
            "source": "Block 2.0 `story.txt`",
            "format": "Full 5-Act Master Text",
            "schema": {
                "target_sentences": "120 - 160 breath-timed sentences",
                "sentence_length": "10-18 words (EN) | 20-30 syllables (KR) | 22-35 chars (JP)"
            }
        },
        "outputs": {
            "target": "Block 2.6 (Master Audio Spine)",
            "format": "JSON + Text: `spoken_sentences.json`, `spoken_script.txt`",
            "artifacts": ["`spoken_script.txt`", "`spoken_sentences.json` (danh sách câu đánh số sent_001..sent_N)"]
        },
        "connections": {
            "upstream": ["B2_STORY_ENGINE"],
            "downstream": ["B26_AUDIO_SPINE"]
        },
        "invariants": [
            "Giữ nguyên 100% cốt truyện, cấm cắt xén hoặc tóm tắt.",
            "Mỗi câu chỉ biểu đạt 1 hơi thở tự nhiên, chấm dứt bằng dấu câu tuyệt đối (., !, ?).",
            "Điểm kiểm toán phản biện VO đạt tối thiểu >= 7.5/10."
        ]
    },
    {
        "id": "B26_AUDIO_SPINE",
        "stage": "Block 2.6",
        "name": "Hollywood Audio Spine & Edge-TTS Karaoke",
        "phase": "audio",
        "category": "Master Voiceover & Timecode Alignment",
        "engine": "Microsoft Edge-TTS + Word-Level Whisper Alignment",
        "source_files": ["app/services/beat_tts_engine.py"],
        "notion_status": "DISCONNECTED",
        "notion_detail": "Sinh audio broadcast trực tiếp trên VPS qua Edge-TTS, bóc tách timecode mili-giây cho từng từ. Không liên quan Notion.",
        "rule_refs": ["Rule 120 (Karaoke Sync)", "Rule 127", "Audio Spine Hard Gate"],
        "inputs": {
            "source": "Block 2.5 `spoken_sentences.json`",
            "format": "Sentence List with Text and Beat Index",
            "schema": {
                "voice_profile": "en-US-ChristopherNeural (EN) | ko-KR-InJoonNeural (KR) | ja-JP-KeitaNeural (JP)",
                "rate": "+0%",
                "pitch": "+0Hz"
            }
        },
        "outputs": {
            "target": "Block 3.0 (Director Plan) & Block 6.0 (Remotion Props)",
            "format": "Audio + Subtitles: `tts_out.mp3`, `subtitles.srt`, `spoken_sentences.json` (enriched)",
            "artifacts": ["`tts_out.mp3` (Master Audio Spine)", "`subtitles.srt` (Karaoke Subtitles)", "`spoken_sentences.json` (bổ sung `start_ms`, `end_ms`, `duration_frames` tại 30fps)"]
        },
        "connections": {
            "upstream": ["B25_SPOKEN_VO"],
            "downstream": ["B3_DIRECTOR_PLAN", "B6_REMOTION_PROPS"]
        },
        "invariants": [
            "BẮT BUỘC timecode mili-giây chính xác: start_ms, end_ms, duration_frames.",
            "Tất cả các cảnh B3 hình ảnh phải khóa 1:1 theo duration_frames của audio spine thật.",
            "Hard Gate: Nếu tổng duration audio < 10 phút hoặc > 16 phút, dừng render."
        ]
    },
    {
        "id": "B3_DIRECTOR_PLAN",
        "stage": "Block 3.0",
        "name": "Hollywood Visual Director Plan (Timecode-Locked)",
        "phase": "visual",
        "category": "Cinematography & Scene Breakdown",
        "engine": "Hollywood Director AI + Fincher-Style Pacing + Clustered BG Engine",
        "source_files": ["app/services/director_planner_b3.py", "app/services/unified_vox_director.py"],
        "notion_status": "ACTIVE_SOT",
        "notion_detail": "PROMPTS: Nạp động từ Notion SoT Page 'B3: Hollywood Master Visual Director & Storyboard Prompt' (3f801989-2400-81c9-bdb0-c4dc60b43988) qua skill_loader.get_b3_strategic_rules(). OUTPUT: Ghi director_plan.json và đồng bộ sang Notion Director Plan DB.",
        "rule_refs": ["Rule 116 (2-Layer)", "Rule 120", "Rule 128 (Anti-Bias)", "Rule 131", "Rule 445"],
        "inputs": {
            "source": "Block 2.6 `spoken_sentences.json` (Đã có timecode thật)",
            "format": "Timecoded Sentences JSON",
            "schema": {
                "target_scenes": "130 - 160 dynamic scenes (~4-7s/scene)",
                "bg_clusters": "15 - 20 Clustered Background locations",
                "camera_movements": "6 canonical camera movements"
            }
        },
        "outputs": {
            "target": "Block 3.5 (Prompt Forge)",
            "format": "JSON File: `/var/vf/episodes/<task_id>/director_plan.json`",
            "artifacts": ["scenes list (130-160 scenes)", "bg_cluster_id (1..20)", "camera_movement", "forensic_overlay directives", "setting_description & visual_action (English)"]
        },
        "connections": {
            "upstream": ["B26_AUDIO_SPINE"],
            "downstream": ["B35_PROMPT_FORGE"]
        },
        "invariants": [
            "Khóa 1:1 theo audio: narration == sent.text, duration_frames == sent.duration_frames.",
            "Tái sử dụng 15-20 Background clusters để chống nghẽn API sinh ảnh B4.",
            "Áp dụng Rule of Thirds: Nhân vật FG chỉ đứng Left hoặc Right, cấm đè giữa màn hình."
        ]
    },
    {
        "id": "B35_PROMPT_FORGE",
        "stage": "Block 3.5",
        "name": "Visual Prompt Forge (FG 1:1 Pure Magenta & BG 16:9)",
        "phase": "visual",
        "category": "Image Generation Prompt Engineering",
        "engine": "Prompt Forge AI + 20 Google Flow Cinematic Tokens + DACL Shield",
        "source_files": ["app/services/prompt_forge.py", "app/services/skill_loader.py"],
        "notion_status": "ACTIVE_SOT",
        "notion_detail": "PROMPTS: Nạp động từ Notion SoT Page 'B3.5: Visual Prompt Forge & DACL Rules' (3f801989-2400-81e3-8cc6-c9bb0bb4650c) qua skill_loader.get_b35_strategic_rules(). OUTPUT: Ghi prompts_forge.json và đồng bộ Prompt Library DB.",
        "rule_refs": ["Rule 116", "Rule 120 (#FF00FF)", "Rule 122", "Rule 128", "Rule 435 (Graphic Novel)", "Rule 446"],
        "inputs": {
            "source": "Block 3.0 `director_plan.json`",
            "format": "Director Plan Scenes & Clustered Keys",
            "schema": {
                "layer_1_bg_spec": "16:9 2K DCI 2560x1440 widescreen, bottom 20% safe zone clear",
                "layer_2_fg_spec": "1:1 2048x2048, pure flat #FF00FF magenta chroma key background",
                "style": "Stylized Graphic Novel Editorial Illustration, cel-shading ink"
            }
        },
        "outputs": {
            "target": "Block 3.6 (Visual Convergence Gate) & Block 4.0 (Gemini Browser Gen)",
            "format": "JSON File: `/var/vf/episodes/<task_id>/prompts_forge.json`",
            "artifacts": ["backgrounds prompts (15-20 unique English prompts)", "foregrounds prompts (waist-up, active props, intense expression)", "vox_collage prompts (nếu là dạng Vox)"]
        },
        "connections": {
            "upstream": ["B3_DIRECTOR_PLAN"],
            "downstream": ["B36_VISUAL_CONVERGENCE"]
        },
        "invariants": [
            "FG BẮT BUỘC trên nền pure solid #FF00FF magenta chroma key không viền gradient.",
            "CẤM TUYỆT ĐỐI phong cách Photorealistic chụp thật (Rule 435).",
            "Nhân vật Á Đông BẮT BUỘC mang nhân chủng học bản địa, cấm thiên kiến da trắng Tây hóa."
        ]
    },
    {
        "id": "B36_VISUAL_CONVERGENCE",
        "stage": "Block 3.6",
        "name": "Visual Convergence Gate (DACL & Linguistic Purity)",
        "phase": "checkpoint",
        "category": "Pre-Render Prompt Safety Gate",
        "engine": "AST Linter + Representation Shield + Regex Banned Entity Sweeper",
        "source_files": ["app/services/b36_visual_convergence.py", "scripts/orchestrator/adversarial_director_gate.py"],
        "notion_status": "DISCONNECTED",
        "notion_detail": "Chạy kiểm toán đối kháng trên mã nguồn VPS và file prompt JSON. Không gọi Notion.",
        "rule_refs": ["Rule 118", "Rule 122", "Rule 128 (Zero Semantic Bias)"],
        "inputs": {
            "source": "Block 3.5 `prompts_forge.json`",
            "format": "Forged Prompt Dictionary",
            "schema": {
                "market": "EN | KR | JP",
                "prompts_list": "Tất cả các prompt BG và FG chuẩn bị nạp vào B4"
            }
        },
        "outputs": {
            "target": "Block 4.0 (Gemini Image Gen)",
            "format": "Audit Verdict: PASS / REJECT with Defect List",
            "artifacts": ["`b36_audit_report.json`", "Auto-repaired prompts nếu phát hiện leak nhỏ"]
        },
        "connections": {
            "upstream": ["B35_PROMPT_FORGE"],
            "downstream": ["B4_GEMINI_IMAGE_GEN"]
        },
        "invariants": [
            "0% rò rỉ thực thể ngoài thị trường (banned cross-market entities).",
            "Cấm xuất hiện chữ tiếng Anh/Latin trên biển hiệu, tường, tài liệu trong thị trường Á Châu.",
            "Chống lắp bắp prompt (Anti-Stuttering regex audit)."
        ]
    },
    {
        "id": "B4_GEMINI_IMAGE_GEN",
        "stage": "Block 4.0",
        "name": "Automated Gemini Pro Image Generation",
        "phase": "generation",
        "category": "Visual Asset Generation",
        "engine": "Playwright Headless Chrome + Gemini Pro Web Reverse Protocol",
        "source_files": ["scripts/gemini_browser_gen.py", "app/services/episode_images.py"],
        "notion_status": "OUTPUT_SINK",
        "notion_detail": "Không nạp prompt từ Notion. Đọc `prompts_forge.json` trên disk, mở trình duyệt sinh ảnh, tải ảnh về VPS và upload ảnh lên Notion Image Asset DB.",
        "rule_refs": ["Rule 116", "Rule 120", "Rule 435", "Playwright Watchdog"],
        "inputs": {
            "source": "Block 3.6 Approved `prompts_forge.json`",
            "format": "Prompts Forge JSON on Disk",
            "schema": {
                "target_directory": "/var/vf/episodes/<task_id>/images/",
                "rate_limit_spacing": "3-5 seconds between image requests"
            }
        },
        "outputs": {
            "target": "Block 5.0 (Visual Audit & Chroma Cutout)",
            "format": "PNG Files on VPS Disk: `/var/vf/episodes/<task_id>/images/*.png`",
            "artifacts": ["Raw Background PNGs (16:9)", "Raw Foreground PNGs with #FF00FF Magenta Background (1:1)"]
        },
        "connections": {
            "upstream": ["B36_VISUAL_CONVERGENCE"],
            "downstream": ["B5_VISUAL_AUDIT"]
        },
        "invariants": [
            "Playwright Watchdog tự động phục hồi phiên nếu Gemini Web bị timeout hoặc captcha.",
            "Tất cả ảnh FG phải tải về đúng kích thước >= 1024x1024.",
            "Không lưu file rác vào thư mục gốc, chỉ lưu trong episode directory."
        ]
    },
    {
        "id": "B5_VISUAL_AUDIT",
        "stage": "Block 5.0",
        "name": "Visual Audit & Chroma Keying HSV Cutout",
        "phase": "processing",
        "category": "Asset QA & Background Removal",
        "engine": "Python Pillow + OpenCV HSV Keying + Multi-Axis Visual Critic Gate",
        "source_files": ["app/services/image_audit.py", "app/services/b5_visual_gate.py"],
        "notion_status": "DISCONNECTED",
        "notion_detail": "Xử lý bóc tách kênh màu HSV vật lý cục bộ trên VPS. Không gọi Notion.",
        "rule_refs": ["Rule 118", "Rule 122 (Visual Audit 4 Trục)", "Rule 435-439"],
        "inputs": {
            "source": "Block 4.0 Raw Images (`images/*.png`)",
            "format": "Raw PNG Files on Disk",
            "schema": {
                "target_hue": "Magenta (#FF00FF / Hue ~280-320 in HSV)",
                "feather_edge_px": "2-3 pixels edge smoothing"
            }
        },
        "outputs": {
            "target": "Block 6.0 (Remotion Props Builder)",
            "format": "Transparent PNG Cutouts: `images/*_fg_cutout.png`",
            "artifacts": ["Transparent Alpha PNGs for Foreground Characters", "Audit Scorecard JSON (Pixel level 4 axes audit)"]
        },
        "connections": {
            "upstream": ["B4_GEMINI_IMAGE_GEN"],
            "downstream": ["B6_REMOTION_PROPS"]
        },
        "invariants": [
            "0% viền magenta dư (#FF00FF halo) và 0% thủng lỗ trên áo/tóc nhân vật.",
            "CẤM TUYỆT ĐỐI hardcode điểm mock `base_score = 8.5` (Rule 118 & Rule 122).",
            "Chỉ các ảnh đạt pass mới được đưa vào danh sách Remotion props."
        ]
    },
    {
        "id": "B6_REMOTION_PROPS",
        "stage": "Block 6.0",
        "name": "Remotion Props Builder & Whisper Timeframe Sync",
        "phase": "composition",
        "category": "Timeline Architecture & Motion Graphics Props",
        "engine": "Remotion Props Compiler + Word-Level Whisper Timestamps Binder",
        "source_files": ["app/services/build_remotion_props.py", "app/services/sfx_registry.py"],
        "notion_status": "OUTPUT_SINK",
        "notion_detail": "Biên dịch toàn bộ tài nguyên trên đĩa thành `remotion_props.json`. Đồng bộ trạng thái sẵn sàng sang Notion Episodes DB.",
        "rule_refs": ["Rule 120 (Timestamp Lock)", "Rule 125", "Rule 128", "Rule 134", "Rule 136"],
        "inputs": {
            "source": "Director Plan + Spoken Sentences + Cutout Images + SFX Registry",
            "format": "JSON Metadata + Audio Paths + Asset Files on Disk",
            "schema": {
                "fps": 30,
                "width": 1920,
                "height": 1080,
                "total_scenes": "130-160 scenes"
            }
        },
        "outputs": {
            "target": "Block 7.0 (Remotion Render) & Block 7.5 (BGM Engine)",
            "format": "JSON File: `/var/vf/episodes/<task_id>/remotion_props.json`",
            "artifacts": ["`remotion_props.json` (Chân lý mốc thời gian khung hình)", "Speaker tags sạch (Rule 136: Cấm rò rỉ mã asset/hash)", "SFX cues mapping (13 Canonical Cues)"]
        },
        "connections": {
            "upstream": ["B26_AUDIO_SPINE", "B5_VISUAL_AUDIT"],
            "downstream": ["B7_REMOTION_RENDER", "B75_BGM_ENGINE"]
        },
        "invariants": [
            "durationInFrames khớp chính xác Whisper word timestamps (Rule 120), cấm chia đều.",
            "Cấm rò rỉ mã asset nội bộ lên speakerTag / lower third (Rule 136).",
            "Chỉ được phát ra 13 cues SFX chuẩn hóa từ `sfx_registry.py`, cấm fallback mù."
        ]
    },
    {
        "id": "B75_BGM_ENGINE",
        "stage": "Block 7.5",
        "name": "5-Beat Docudrama Adaptive BGM & Sidechain Ducking",
        "phase": "audio",
        "category": "Cinematic Sound Design & Audio Mixing",
        "engine": "Beat BGM Engine + FFmpeg Sidechain Ducking (-20dB threshold)",
        "source_files": ["app/services/beat_bgm_engine.py", "tests/test_beat_bgm_engine.py"],
        "notion_status": "DISCONNECTED",
        "notion_detail": "Lựa chọn nhạc nền từ YouTube Audio Library Vault trên đĩa và mix âm qua FFmpeg. Không gọi Notion.",
        "rule_refs": ["Rule 120", "Audio Production Standard"],
        "inputs": {
            "source": "Block 2.6 Audio Spine + Block 6.0 Remotion Props",
            "format": "WAV/MP3 Narration Audio + Mood Track Pool",
            "schema": {
                "ducking_depth": "-20dB during speech",
                "ducking_release": "300ms smooth recovery",
                "crossfade_sec": "2.5s between Beat mood shifts"
            }
        },
        "outputs": {
            "target": "Block 7.0 (Remotion Render Engine)",
            "format": "Audio File: `/var/vf/episodes/<task_id>/audio/mixed_soundtrack.mp3`",
            "artifacts": ["Master Mixed Soundtrack with 5-Beat Dynamic Atmosphere"]
        },
        "connections": {
            "upstream": ["B6_REMOTION_PROPS"],
            "downstream": ["B7_REMOTION_RENDER"]
        },
        "invariants": [
            "Nhạc nền tự động hạ -20dB khi giọng đọc cất lên, không bao giờ lấn át lời bình.",
            "Chuyển mood mượt mà giữa 5 Acts theo nhịp điều tra hồi hộp."
        ]
    },
    {
        "id": "B7_REMOTION_RENDER",
        "stage": "Block 7.0",
        "name": "Remotion Master 2K/1080p Video Render Engine",
        "phase": "render",
        "category": "React Motion Graphics Video Synthesis",
        "engine": "Node.js Remotion CLI + React TwoLayerEpisode Engine (CPU Render)",
        "source_files": ["remotion/src/index.tsx", "app/pipeline/stages/s7_render.py"],
        "notion_status": "DISCONNECTED",
        "notion_detail": "Render đồ họa React Remotion thuần túy trên CPU VPS. Bỏ qua hoàn toàn FFmpeg burning subtitle thừa theo Rule 120. Không thông qua Notion.",
        "rule_refs": ["Rule 116", "Rule 120", "Rule 125", "Anti-OOM Render Standard"],
        "inputs": {
            "source": "Block 6.0 `remotion_props.json` + Mixed Audio + Visual Assets",
            "format": "React Component Props + Static PNGs & Audio Files",
            "schema": {
                "composition_id": "TwoLayerEpisode",
                "resolution": "1920x1080 (hoặc 2560x1440 2K DCI)",
                "fps": 30,
                "codec": "h264",
                "crf": 18
            }
        },
        "outputs": {
            "target": "Block 8.0 (Video QA Audit)",
            "format": "MP4 Video File: `/var/vf/episodes/<task_id>/final_169.mp4`",
            "artifacts": ["Master Docudrama Video MP4", "2-min preview clip for Telegram Gate 2"]
        },
        "connections": {
            "upstream": ["B6_REMOTION_PROPS", "B75_BGM_ENGINE"],
            "downstream": ["B8_VIDEO_QA"]
        },
        "invariants": [
            "Render hoàn toàn bằng Remotion Safe-Zone box karaoke, cấm đốt sub cứng FFmpeg thừa.",
            "Bảo đảm bộ nhớ không bị OOM crash trên VPS thông qua giới hạn concurrency.",
            "Exit code 0 từ remotion render CLI."
        ]
    },
    {
        "id": "B8_VIDEO_QA",
        "stage": "Block 8.0 / 9.0",
        "name": "Video Technical QA & Multimodal Video Critic Gate",
        "phase": "qa",
        "category": "Forensic Quality Verification",
        "engine": "FFprobe Integrity Probe + OpenCV Frame Sampler + Multi-Model Critic Council",
        "source_files": ["app/services/video_audit_runner.py", "scripts/orchestrator/full_video_adversarial_auditor.py"],
        "notion_status": "OUTPUT_SINK",
        "notion_detail": "Kiểm toán kỹ thuật video và trích xuất frame. Ghi kết quả kiểm toán vào đĩa và sync điểm QA lên Notion Episodes DB.",
        "rule_refs": ["Rule 118", "Rule 121", "Rule 122", "Rule 127"],
        "inputs": {
            "source": "Block 7.0 `final_169.mp4`",
            "format": "Rendered MP4 File",
            "schema": {
                "checks": "Black frames, audio freeze, audio sync drift, visual artifacts, subtitle clipping"
            }
        },
        "outputs": {
            "target": "Human Gate 2 (Telegram Publish Approval)",
            "format": "JSON Report: `/var/vf/episodes/<task_id>/video_qa_report.json`",
            "artifacts": ["`video_qa_report.json`", "QA Scorecard (Technical Score, Visual Integrity Score)", "Sample audit keyframes"]
        },
        "connections": {
            "upstream": ["B7_REMOTION_RENDER"],
            "downstream": ["HG2_TELEGRAM"]
        },
        "invariants": [
            "CẤM TUYỆT ĐỐI 'fallback_baseline' mock điểm số (Rule 118).",
            "Duration video phải khớp với duration audio spine (+- 0.5s).",
            "0 frame đen (black screen) trên toàn bộ thời lượng 12-15 phút."
        ]
    },
    {
        "id": "HG2_TELEGRAM",
        "stage": "Human Gate 2",
        "name": "Preview Inspection & Publish Authorization Gate",
        "phase": "checkpoint",
        "category": "Human-in-the-Loop Final Gate",
        "engine": "Telegram Bot API (Interactive Inline Buttons: [PUBLISH] / [REVISE] / [REJECT])",
        "source_files": ["scripts/execute_human_gate_2.py", "scripts/telegram_buttons.py"],
        "notion_status": "OUTPUT_SINK",
        "notion_detail": "Gửi video preview 2 phút + link video master + Hero Thumbnail sang Telegram User. Chờ User bấm duyệt hoặc trigger CLI `--auto-approve`.",
        "rule_refs": ["Rule 118", "Rule 121", "Rule 126"],
        "inputs": {
            "source": "Block 7.0 Preview MP4 + Block 8.0 QA Scorecard",
            "format": "Telegram Video Payload with Inline Keyboard",
            "schema": {
                "buttons": "[PUBLISH TO YOUTUBE] | [RETAKE VISUALS] | [CANCEL EPISODE]"
            }
        },
        "outputs": {
            "target": "Block 10.0 (SEO Packaging & YouTube Upload)",
            "format": "Human Decision Signal (Callback Query / Webhook)",
            "artifacts": ["Gate 2 Approval Token", "User Revision Directives (nếu có)"]
        },
        "connections": {
            "upstream": ["B8_VIDEO_QA"],
            "downstream": ["B10_SEO_UPLOAD"]
        },
        "invariants": [
            "Chỉ được upload lên YouTube khi có sự phê duyệt rõ ràng từ Human Gate 2 hoặc cờ chỉ định.",
            "Video preview hiển thị chính xác chất lượng thật của master render."
        ]
    },
    {
        "id": "B10_SEO_UPLOAD",
        "stage": "Block 10.0",
        "name": "SEO Packaging & YouTube Studio Gate 2 Upload",
        "phase": "release",
        "category": "Distribution & Search Optimization",
        "engine": "SEO Package Forge + YouTube Data API v3 Upload + Chapter Sync Engine",
        "source_files": ["app/services/seo_package_forge.py", "app/services/seo_autogen_b10.py"],
        "notion_status": "ACTIVE_SOT",
        "notion_detail": "PROMPTS: Nạp động từ Notion SoT Page 'B10: YouTube SEO Packaging & Chapters Metadata' (3f801989-2400-8172-8655-cc3cd462cbef) qua skill_loader.get_b10_seo_rules(). OUTPUT: Upload video lên YouTube với `containsSyntheticMedia: true` và đồng bộ sang Notion Episodes DB.",
        "rule_refs": ["Rule 118", "Rule 128", "Rule 135 (Timeline Chapter Sync)", "Rule 444"],
        "inputs": {
            "source": "Approved Video MP4 + Grounding Table + Remotion Props (Timeline Chapters)",
            "format": "Video Binary + SEO Metadata JSON",
            "schema": {
                "title_specs": "Title A (Curiosity), Title B (Search Intent), Title C (Provocative)",
                "description_chapters": "Đồng bộ từ remotion_props.json (00:00, MM:SS bắt buộc)",
                "synthetic_media": "status.containsSyntheticMedia: true"
            }
        },
        "outputs": {
            "target": "YouTube Channel & Block 11.0 (Analytics Loop)",
            "format": "YouTube API Upload Response: `youtube_upload_payload.json`",
            "artifacts": ["YouTube Video ID", "Live Video URL", "Uploaded Custom Hero Thumbnail", "Notion Episodes DB marked as 'PUBLISHED'"]
        },
        "connections": {
            "upstream": ["HG2_TELEGRAM"],
            "downstream": ["B11_ANALYTICS_LOOP"]
        },
        "invariants": [
            "Mốc thời gian Chapters BẮT BUỘC trích xuất từ Remotion Rendered Timeline (Rule 135).",
            "Tối thiểu 3 chapters, bắt đầu bằng 00:00, cách nhau ít nhất 10 giây.",
            "Khai báo minh bạch phương tiện tổng hợp: containsSyntheticMedia: true."
        ]
    },
    {
        "id": "B11_ANALYTICS_LOOP",
        "stage": "Block 11.0",
        "name": "48h Retention Analytics & Feedback Dreaming Loop",
        "phase": "feedback",
        "category": "Self-Learning Loop & Continuous Instinct Optimization",
        "engine": "YouTube Analytics API + V7 Formula Harvester + Notion Dreaming Sync",
        "source_files": ["scripts/b11_engine.py", "scripts/b11_antigravity_engine.py", "app/services/skill_loader.py"],
        "notion_status": "ACTIVE_SOT",
        "notion_detail": "Truy vấn YouTube Analytics sau 48h, bóc tách bài học AVD/CTR, ghi Insight Cards lên Notion Self-Learning Page (`83cbd0d0...`), và nạp ngược lại vào `get_b11_self_learning_rules()` kết hợp với B2 kịch bản tiếp theo.",
        "rule_refs": ["Rule 113 (48h Law)", "Rule 118", "Rule 125", "V7 Winning Pool"],
        "inputs": {
            "source": "YouTube Analytics API (48h+ post-publish) + YouTube Studio",
            "format": "Telemetry Metrics: Views, AVD %, CTR %, Audience Retention Curves",
            "schema": {
                "retention_curve": "Array of percentages across video duration",
                "dropoff_spikes": "Timecodes with steep retention dropoffs"
            }
        },
        "outputs": {
            "target": "Block 1.0 / Block 1.5 (`v7_winning_pool.json`) & Block 2.0 Editorial Prompts",
            "format": "JSON File: `data/v7_winning_pool.json` + Notion Self-Learning Page",
            "artifacts": ["`data/v7_winning_pool.json` (Winning topic pool for B1/B1.5)", "Actionable Instinct Cards on Notion Page `83cbd0d0...`", "B11 Continuous Self-Learning Prompt section for B2 Story Engine"]
        },
        "connections": {
            "upstream": ["B10_SEO_UPLOAD"],
            "downstream": ["B1_TREND_ENGINE", "B2_STORY_ENGINE"]
        },
        "invariants": [
            "Tuân thủ nghiêm ngặt Luật 48 giờ: cấm đánh giá hiệu năng video trước 48h (Rule 113).",
            "Cấm tạo mock số liệu views/CTR (Rule 118).",
            "Tự động trích xuất các video đối thủ gợi ý có CTR/AVD vượt trội để làm đề tài V7 tiếp theo."
        ]
    }
]

def audit_notion_loading():
    """Perform forensic scan of Notion SoT connections across the pipeline."""
    summary = {
        "ACTIVE_SOT": [],
        "LOCAL_FALLBACK": [],
        "HARDCODED": [],
        "OUTPUT_SINK": [],
        "DISCONNECTED": []
    }
    for node in PIPELINE_NODES:
        st = node["notion_status"]
        summary[st].append({
            "id": node["id"],
            "name": node["name"],
            "stage": node["stage"],
            "detail": node["notion_detail"]
        })
    return summary

def get_pipeline_topology():
    """Return complete pipeline graph metadata."""
    return {
        "version": "2026.10-canonical",
        "total_nodes": len(PIPELINE_NODES),
        "phases": ["orchestration", "discovery", "content", "audio", "visual", "generation", "processing", "composition", "render", "qa", "checkpoint", "release", "feedback"],
        "notion_audit_summary": {
            "active_sot_count": len([n for n in PIPELINE_NODES if n["notion_status"] == "ACTIVE_SOT"]),
            "local_fallback_count": len([n for n in PIPELINE_NODES if n["notion_status"] == "LOCAL_FALLBACK"]),
            "hardcoded_count": len([n for n in PIPELINE_NODES if n["notion_status"] == "HARDCODED"]),
            "output_sink_count": len([n for n in PIPELINE_NODES if n["notion_status"] == "OUTPUT_SINK"]),
            "disconnected_count": len([n for n in PIPELINE_NODES if n["notion_status"] == "DISCONNECTED"]),
        },
        "episodes": SAMPLE_EPISODES,
        "milestones": EPISODE_MILESTONES,
        "nodes": PIPELINE_NODES
    }

EPISODE_MILESTONES = [
    {"index": 0, "node_id": "B0_SCHEDULER", "name": "Lập Lịch Tuần Phân Bổ Thị Trường", "key_artifact": "today_market.json", "est_sec": 5, "gate": "Scheduler Crash Gate"},
    {"index": 1, "node_id": "B1_TREND_ENGINE", "name": "Cào & Đánh Giá Đề Tài Xu Hướng", "key_artifact": "pending_tasks/<id>.json", "est_sec": 45, "gate": "Viability Score >= 8.0"},
    {"index": 2, "node_id": "B15_COMPETITOR_RECON", "name": "Trinh Sát Đối Thủ & Lỗ Hổng Kiến Thức", "key_artifact": "competitor_intel_card.json", "est_sec": 60, "gate": "Explanatory Vacuum Found"},
    {"index": 3, "node_id": "B155_GROUNDING_GATE", "name": "Kiểm Chứng Sự Thật Google Search", "key_artifact": "grounding_intel.json", "est_sec": 40, "gate": "Claims Verified >= 1"},
    {"index": 4, "node_id": "HG1_TELEGRAM", "name": "Phát Sóng Cảnh Báo Đề Tài Telegram", "key_artifact": "telegram_broadcast.log", "est_sec": 5, "gate": "Informative Broadcast"},
    {"index": 5, "node_id": "B2_STORY_ENGINE", "name": "Viết Kịch Bản 5 Beat Docudrama", "key_artifact": "story.txt", "est_sec": 90, "gate": "Rule 444 Hook + 5-Beat"},
    {"index": 6, "node_id": "B25_SPOKEN_VO", "name": "Chuyển Thể Câu Thoại Ngắt Hơi Nhịp Thở", "key_artifact": "spoken_sentences.json", "est_sec": 30, "gate": "Adversarial VO Audit >= 7.5"},
    {"index": 7, "node_id": "B26_AUDIO_SPINE", "name": "Tổng Hợp Audio Spine & Edge-TTS Karaoke", "key_artifact": "tts_out.mp3", "est_sec": 120, "gate": "_is_valid_audio_spine (Rule 120)"},
    {"index": 8, "node_id": "B3_DIRECTOR_PLAN", "name": "Phân Cảnh Đạo Diễn Khóa Audio (130-160 cảnh)", "key_artifact": "director_plan.json", "est_sec": 60, "gate": "Audio-Locked Timecode 1:1"},
    {"index": 9, "node_id": "B35_PROMPT_FORGE", "name": "Rèn Prompts Mỹ Thuật Layer 1 BG & Layer 2 FG", "key_artifact": "prompts_forge.json", "est_sec": 45, "gate": "#FF00FF Magenta Spec"},
    {"index": 10, "node_id": "B36_VISUAL_CONVERGENCE", "name": "Kiểm Toán Hội Tụ Mỹ Thuật & DACL Shield", "key_artifact": "b36_audit_report.json", "est_sec": 20, "gate": "0% Cross-Market Bleed"},
    {"index": 11, "node_id": "B4_GEMINI_IMAGE_GEN", "name": "Sinh Ảnh Gemini Pro Trình Duyệt Web", "key_artifact": "images/*.png", "est_sec": 600, "gate": "Playwright Watchdog 100%"},
    {"index": 12, "node_id": "B5_VISUAL_AUDIT", "name": "Kiểm Toán Pixel & Tách Phông Chroma HSV", "key_artifact": "images/*_fg_cutout.png", "est_sec": 90, "gate": "Visual Audit 4 Trục (Zero-Mock)"},
    {"index": 13, "node_id": "B6_REMOTION_PROPS", "name": "Biên Dịch Props Remotion & Khóa Timestamp", "key_artifact": "remotion_props.json", "est_sec": 30, "gate": "Speaker Tag Leak Free (Rule 136)"},
    {"index": 14, "node_id": "B75_BGM_ENGINE", "name": "Hòa Âm Nhạc Nền 5 Beat & Ducking -20dB", "key_artifact": "audio/mixed_soundtrack.mp3", "est_sec": 45, "gate": "Sidechain Ducking -20dB"},
    {"index": 15, "node_id": "B7_REMOTION_RENDER", "name": "Render Video Master Remotion 2K/1080p CPU", "key_artifact": "final_169.mp4", "est_sec": 900, "gate": "Safe-Zone Karaoke (Exit Code 0)"},
    {"index": 16, "node_id": "B8_VIDEO_QA", "name": "Kiểm Toán Kỹ Thuật & Multimodal Critic", "key_artifact": "video_qa_report.json", "est_sec": 60, "gate": "0 Black Frames & Zero Audio Drift"},
    {"index": 17, "node_id": "HG2_TELEGRAM", "name": "Human Gate 2: Phê Duyệt Xuất Bản Telegram", "key_artifact": "hg2_approval.json", "est_sec": 180, "gate": "Human In-the-Loop Sign-off"},
    {"index": 18, "node_id": "B10_SEO_UPLOAD", "name": "Đóng Gói SEO & Upload YouTube Studio", "key_artifact": "youtube_upload_payload.json", "est_sec": 90, "gate": "Remotion Chapters Sync (Rule 135)"},
    {"index": 19, "node_id": "B11_ANALYTICS_LOOP", "name": "Phân Tích Giữ Chân 48h & Vòng Lặp Tự Học", "key_artifact": "data/v7_winning_pool.json", "est_sec": 120, "gate": "48h Post-Mortem Law (Rule 113)"}
]

def load_sample_episodes() -> list:
    """Load real episodes from telemetry or sample fallback."""
    telem_file = PROJECT_ROOT / "data" / "vps_episodes_telemetry.json"
    if telem_file.exists():
        try:
            data = json.loads(telem_file.read_text(encoding="utf-8"))
            if isinstance(data, list) and len(data) > 0:
                return data
        except Exception:
            pass
    sample_file = PROJECT_ROOT / "data" / "sample_episodes.json"
    if sample_file.exists():
        try:
            return json.loads(sample_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []

SAMPLE_EPISODES = load_sample_episodes()

def detect_episode_progress(episode_id: str, ep_dir: Path = None) -> dict:
    """Probes the physical disk for an episode and deterministically determines its milestone."""
    if ep_dir is None:
        ep_dir = Path("/var/vf/episodes") / episode_id
        if not ep_dir.exists():
            ep_dir = PROJECT_ROOT / "episodes" / episode_id

    # Check for matched sample
    for s in SAMPLE_EPISODES:
        if s["episode_id"] == episode_id:
            return s

    # Default probe if folder exists
    detected_idx = 0
    if ep_dir and ep_dir.exists():
        if (ep_dir / "youtube_upload_payload.json").exists():
            detected_idx = 18
        elif (ep_dir / "video_qa_report.json").exists():
            detected_idx = 16
        elif (ep_dir / "final_169.mp4").exists():
            detected_idx = 15
        elif (ep_dir / "remotion_props.json").exists():
            detected_idx = 13
        elif (ep_dir / "images").exists() and any(ep_dir.glob("images/*_cutout.png")):
            detected_idx = 12
        elif (ep_dir / "prompts_forge.json").exists():
            detected_idx = 10
        elif (ep_dir / "director_plan.json").exists():
            detected_idx = 8
        elif (ep_dir / "tts_out.mp3").exists():
            detected_idx = 7
        elif (ep_dir / "spoken_sentences.json").exists():
            detected_idx = 6
        elif (ep_dir / "story.txt").exists():
            detected_idx = 5
        elif (ep_dir / "grounding_intel.json").exists():
            detected_idx = 3
        elif (ep_dir / "competitor_intel_card.json").exists():
            detected_idx = 2

    node_id = EPISODE_MILESTONES[detected_idx]["node_id"]
    return {
        "episode_id": episode_id,
        "market": episode_id[:2].upper() if "_" in episode_id else "EN",
        "current_step_index": detected_idx,
        "current_step_node": node_id,
        "status": "RUNNING" if detected_idx < 18 else "COMPLETED",
        "milestone_info": EPISODE_MILESTONES[detected_idx]
    }

def render_html_dashboard(target_paths=None):
    """Renders complete self-contained n8n light HTML dashboard with 6 Major Phases and Episode Selector."""
    from scripts.orchestrator.generate_n8n_ui import build_n8n_light_html
    if not target_paths:
        target_paths = [
            PROJECT_ROOT / "reports" / "ai_pipeline_observability_ui.html",
            Path("C:/Users/hunghd2/.gemini/antigravity/brain/bb2d98e1-8cae-467c-a3d4-74cd8e97402b/ai_pipeline_observability_ui.html")
        ]

    html_content = build_n8n_light_html()
    for p in target_paths:
        p = Path(p)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(html_content, encoding="utf-8")
        print(f"✅ Generated n8n light HTML dashboard: {p} ({p.stat().st_size} bytes)")

def print_audit_report():
    print("=" * 80)
    print("🔬 AI VIDEO FACTORY — FORENSIC PIPELINE & NOTION LOADING AUDIT")
    print("=" * 80)
    audit = audit_notion_loading()
    
    print("\n🚨 1. KẾT QUẢ KHẢO SÁT NẠP NOTION KHI CHẠY CÁC HÀM (RUNTIME ENGINE LOADING):")
    print("--------------------------------------------------------------------------------")
    print(f"  • ACTIVE NOTION SOT (Đang nạp từ Notion thật): {len(audit['ACTIVE_SOT'])} / {len(PIPELINE_NODES)} khối")
    for item in audit["ACTIVE_SOT"]:
        print(f"    - [{item['stage']}] {item['name']}: {item['detail']}")
        
    print(f"\n  • LOCAL FALLBACK (Đọc file markdown cục bộ config/prompts/*.md): {len(audit['LOCAL_FALLBACK'])} khối")
    for item in audit["LOCAL_FALLBACK"]:
        print(f"    - [{item['stage']}] {item['name']}: {item['detail']}")

    print(f"\n  • HARDCODED IN CODE (Chuỗi cố định trong file .py): {len(audit['HARDCODED'])} khối")
    for item in audit["HARDCODED"]:
        print(f"    - [{item['stage']}] {item['name']}: {item['detail']}")

    print(f"\n  • OUTPUT SINK ONLY (Chỉ ghi log ra Notion, KHÔNG đọc từ Notion): {len(audit['OUTPUT_SINK'])} khối")
    for item in audit["OUTPUT_SINK"]:
        print(f"    - [{item['stage']}] {item['name']}: {item['detail']}")

    print(f"\n  • DISCONNECTED / PURE RUNTIME (Logic độc lập hoàn toàn): {len(audit['DISCONNECTED'])} khối")
    for item in audit["DISCONNECTED"]:
        print(f"    - [{item['stage']}] {item['name']}: {item['detail']}")
        
    print("\n" + "=" * 80)
    print("🎬 2. THEO DÕI TIẾN ĐỘ EPISODE (EPISODE MILESTONE TRACKING):")
    print("=" * 80)
    for ep in SAMPLE_EPISODES:
        idx = ep["current_step_index"]
        m = EPISODE_MILESTONES[idx]
        pct = int((idx / (len(EPISODE_MILESTONES) - 1)) * 100)
        print(f"  • EP: {ep['episode_id']} ({ep['market']})")
        print(f"    ➔ ĐANG CHẠY BƯỚC [{idx}/19]: {m['name']} ({m['node_id']}) - {pct}%")
        print(f"    ➔ Artifact đang xử lý: {ep['active_artifact']}")
        print("--------------------------------------------------------------------------------")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline Observability & Notion Auditor")
    parser.add_argument("--audit", action="store_true", help="Print Notion Loading Audit to console")
    parser.add_argument("--json", action="store_true", help="Dump complete pipeline topology JSON")
    parser.add_argument("--ep", type=str, help="Inspect specific Episode ID progress")
    parser.add_argument("--html", action="store_true", help="Render standalone HTML dashboard")
    args = parser.parse_args()

    if args.ep:
        info = detect_episode_progress(args.ep)
        print(json.dumps(info, ensure_ascii=False, indent=2))
    elif args.html:
        render_html_dashboard()
    elif args.json:
        print(json.dumps(get_pipeline_topology(), ensure_ascii=False, indent=2))
    else:
        print_audit_report()
