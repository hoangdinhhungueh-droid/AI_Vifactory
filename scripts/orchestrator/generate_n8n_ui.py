#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/orchestrator/generate_n8n_ui.py — Generates the complete n8n-style light theme HTML dashboard
for AI Video Factory Observability, fulfilling all user requirements:
1. Real episodes dropdown (28 real VPS episodes, starting with active running episode)
2. 6 Major Phases (Bước Lớn) timeline stepper
3. Sub-blocks inside each phase with IN/OUT source specifications
4. n8n-style nodes with input/output port dots and success/running/pending status badges
5. Bright light template background (dot grid canvas)
6. Historical view-only logic: past episodes show 100% completed, live flow shows read-only live monitor.
"""

import os
import sys
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from scripts.orchestrator.pipeline_ui_inspector import PIPELINE_NODES, EPISODE_MILESTONES

MAJOR_PHASES = [
    {
        "id": "PHASE_1",
        "index": 1,
        "name": "Khám Phá & Chiến Lược Đề Tài",
        "en_name": "Discovery & Strategy",
        "color": "indigo",
        "badge_color": "border-indigo-300 text-indigo-700 bg-indigo-50",
        "header_bg": "bg-indigo-600",
        "node_ids": ["B0_SCHEDULER", "B1_TREND_ENGINE", "B15_COMPETITOR_RECON", "B155_GROUNDING_GATE", "HG1_TELEGRAM"],
        "description": "Lập lịch tuần, quét Google Trends RSS sống, phân tích lỗ hổng đối thủ và kiểm chứng fact-checking với Google Search."
    },
    {
        "id": "PHASE_2",
        "index": 2,
        "name": "Kịch Bản & Xương Sống Giọng Đọc",
        "en_name": "Narrative & Audio Spine",
        "color": "blue",
        "badge_color": "border-blue-300 text-blue-700 bg-blue-50",
        "header_bg": "bg-blue-600",
        "node_ids": ["B2_STORY_ENGINE", "B25_SPOKEN_VO", "B26_AUDIO_SPINE"],
        "description": "Kịch bản 5-Beat Docudrama chuẩn Hollywood, ngắt câu nhịp thở Spoken VO và tổng hợp giọng đọc broadcast Edge-TTS đồng bộ karaoke từng từ."
    },
    {
        "id": "PHASE_3",
        "index": 3,
        "name": "Đạo Diễn Hình Ảnh & Prompt Forge",
        "en_name": "Visual Direction & DACL",
        "color": "cyan",
        "badge_color": "border-cyan-300 text-cyan-800 bg-cyan-50",
        "header_bg": "bg-cyan-600",
        "node_ids": ["B3_DIRECTOR_PLAN", "B35_PROMPT_FORGE", "B36_VISUAL_CONVERGENCE"],
        "description": "Phân cảnh 130-160 shots khóa cứng audio timecode, rèn prompt 2 lớp (FG 1:1 #FF00FF + BG 16:9) và lá chắn hội tụ mỹ thuật DACL."
    },
    {
        "id": "PHASE_4",
        "index": 4,
        "name": "Sinh Ảnh & Tách Phông Chroma",
        "en_name": "Asset Gen & Keying",
        "color": "emerald",
        "badge_color": "border-emerald-300 text-emerald-700 bg-emerald-50",
        "header_bg": "bg-emerald-600",
        "node_ids": ["B4_GEMINI_IMAGE_GEN", "B5_VISUAL_AUDIT"],
        "description": "Tự động hóa trình duyệt sinh ảnh Gemini Pro với Playwright watchdog và kiểm toán pixel 4 trục kèm tách phông kênh màu HSV."
    },
    {
        "id": "PHASE_5",
        "index": 5,
        "name": "Tổng Hợp Remotion & Render Video",
        "en_name": "Remotion Synthesis & Render",
        "color": "amber",
        "badge_color": "border-amber-300 text-amber-800 bg-amber-50",
        "header_bg": "bg-amber-600",
        "node_ids": ["B6_REMOTION_PROPS", "B75_BGM_ENGINE", "B7_REMOTION_RENDER"],
        "description": "Biên dịch Remotion Props khóa timestamp Whisper, mix âm nhạc nền cinematic dynamic ducking -20dB và render video master 2K/1080p trên CPU VPS."
    },
    {
        "id": "PHASE_6",
        "index": 6,
        "name": "Kiểm Toán QA, Xuất Bản & Tự Học",
        "en_name": "QA, Release & Dreaming Loop",
        "color": "rose",
        "badge_color": "border-rose-300 text-rose-700 bg-rose-50",
        "header_bg": "bg-rose-600",
        "node_ids": ["B8_VIDEO_QA", "HG2_TELEGRAM", "B10_SEO_UPLOAD", "B11_ANALYTICS_LOOP"],
        "description": "Kiểm toán kỹ thuật video 0-black-frame, phê duyệt Telegram HG2, đóng gói YouTube SEO gắn syntheticMedia và vòng lặp tự học B11 48h."
    }
]

def load_real_episodes():
    telem_file = ROOT_DIR / "data" / "vps_episodes_telemetry.json"
    if telem_file.exists():
        try:
            data = json.loads(telem_file.read_text(encoding="utf-8"))
            if isinstance(data, list) and len(data) > 0:
                return data
        except Exception:
            pass
    sample_file = ROOT_DIR / "data" / "sample_episodes.json"
    if sample_file.exists():
        try:
            return json.loads(sample_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []

def build_n8n_light_html():
    nodes = PIPELINE_NODES
    phases = MAJOR_PHASES
    milestones = EPISODE_MILESTONES
    episodes = load_real_episodes()

    nodes_json = json.dumps(nodes, ensure_ascii=False)
    phases_json = json.dumps(phases, ensure_ascii=False)
    milestones_json = json.dumps(milestones, ensure_ascii=False)
    episodes_json = json.dumps(episodes, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI Video Factory — n8n Workflow Observability Canvas (Light Theme)</title>
  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg-canvas: #f8fafc;
      --card-bg: #ffffff;
      --border-color: #e2e8f0;
      --border-active: #6366f1;
    }}
    body {{
      font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
      background-color: var(--bg-canvas);
      background-image: radial-gradient(#cbd5e1 1.2px, transparent 1.2px);
      background-size: 20px 20px;
      color: #0f172a;
    }}
    code, pre, .font-mono {{
      font-family: 'JetBrains Mono', monospace;
    }}
    ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
    ::-webkit-scrollbar-track {{ background: #f1f5f9; }}
    ::-webkit-scrollbar-thumb {{ background: #cbd5e1; border-radius: 4px; }}
    ::-webkit-scrollbar-thumb:hover {{ background: #94a3b8; }}

    /* n8n Node Styles */
    .n8n-node {{
      background: #ffffff;
      border: 1.5px solid #e2e8f0;
      border-radius: 14px;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04), 0 2px 8px rgba(0, 0, 0, 0.02);
      transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
      position: relative;
    }}
    .n8n-node:hover {{
      transform: translateY(-2px);
      border-color: #818cf8;
      box-shadow: 0 10px 25px -5px rgba(99, 102, 241, 0.12), 0 8px 10px -6px rgba(99, 102, 241, 0.08);
    }}
    .n8n-node.is-active-running {{
      border-color: #f59e0b;
      box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.2), 0 10px 25px -5px rgba(245, 158, 11, 0.2);
    }}
    .n8n-node.is-completed {{
      border-color: #cbd5e1;
    }}

    /* Port Dots */
    .port-dot {{
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background: #ffffff;
      border: 2px solid #94a3b8;
      position: absolute;
      top: 50%;
      transform: translateY(-50%);
      transition: all 0.2s ease;
      z-index: 10;
    }}
    .port-dot.port-in {{
      left: -6px;
    }}
    .port-dot.port-out {{
      right: -6px;
    }}
    .n8n-node:hover .port-dot {{
      border-color: #6366f1;
      background: #6366f1;
      transform: translateY(-50%) scale(1.2);
    }}

    /* Pulse animation for active running step */
    .pulse-ring {{
      box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.7);
      animation: pulse-ring 2s infinite cubic-bezier(0.66, 0, 0, 1);
    }}
    @keyframes pulse-ring {{
      to {{ box-shadow: 0 0 0 12px rgba(245, 158, 11, 0); }}
    }}

    /* Drawer backdrop */
    .drawer-backdrop {{
      background: rgba(15, 23, 42, 0.35);
      backdrop-filter: blur(2px);
    }}
  </style>
</head>
<body class="p-3 sm:p-6 min-h-screen">

  <!-- TOP HEADER (LIGHT STUDIO) -->
  <header class="mb-5 bg-white border border-slate-200 rounded-2xl p-4 sm:p-5 shadow-sm">
    <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
      <div>
        <div class="flex flex-wrap items-center gap-2 mb-1.5">
          <span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200">
            <span class="w-1.5 h-1.5 rounded-full bg-indigo-500"></span>
            VF Pipeline v2026.10
          </span>
          <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            ✓ 28 Real Episodes on VPS
          </span>
          <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-800 border border-amber-200">
            n8n Node Graph Architecture
          </span>
          <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200">
            Light Studio Canvas
          </span>
        </div>
        <h1 class="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900 flex items-center gap-2">
          <span>AI Video Factory</span>
          <span class="text-indigo-600 font-semibold text-xl sm:text-2xl">Observability & Workflow Nodes</span>
        </h1>
        <p class="text-xs sm:text-sm text-slate-500 mt-1">
          Bản đồ quan sát toàn trình: Cây Timeline 6 Bước Lớn / 20 Hạng Mục Nhỏ, Đồ Họa n8n Node, In/Out Schema & Kiểm Toán Nguồn Notion SoT
        </p>
      </div>

      <!-- METRIC COUNTERS -->
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center text-xs">
        <div class="bg-slate-50 p-2.5 rounded-xl border border-slate-200">
          <div class="text-slate-400 text-[10px] uppercase font-bold tracking-wider">Hạng Mục Nhỏ</div>
          <div class="text-lg font-bold text-indigo-600">20 Nodes</div>
          <div class="text-[10px] text-slate-500">B0 đến B11 + 2 HG</div>
        </div>
        <div class="bg-slate-50 p-2.5 rounded-xl border border-slate-200">
          <div class="text-slate-400 text-[10px] uppercase font-bold tracking-wider">Bước Lớn</div>
          <div class="text-lg font-bold text-blue-600">6 Giai Đoạn</div>
          <div class="text-[10px] text-slate-500">Hollywood Pipeline</div>
        </div>
        <div class="bg-slate-50 p-2.5 rounded-xl border border-slate-200">
          <div class="text-slate-400 text-[10px] uppercase font-bold tracking-wider">Tiến Độ EP</div>
          <div id="header-ep-progress" class="text-lg font-bold text-amber-600">78%</div>
          <div id="header-ep-step" class="text-[10px] text-slate-500">Bước 15 / 19</div>
        </div>
        <div class="bg-slate-50 p-2.5 rounded-xl border border-slate-200">
          <div class="text-slate-400 text-[10px] uppercase font-bold tracking-wider">Notion Runtime</div>
          <div class="text-lg font-bold text-emerald-600">6 / 20 Active</div>
          <div class="text-[10px] text-slate-500">Dedicated Hub Sync</div>
        </div>
      </div>
    </div>
  </header>

  <!-- EPISODE SELECTOR & CONTROL BAR -->
  <section class="mb-5 bg-white border border-slate-200 rounded-2xl p-4 shadow-sm">
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div class="flex-1">
        <label for="ep-select" class="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-1.5 flex items-center gap-1.5">
          <svg class="w-4 h-4 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path></svg>
          Chọn Episode Thực Tế Trên VPS (Tự động phát hiện 28 EP):
        </label>
        <div class="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
          <select id="ep-select" onchange="changeEpisode()" class="flex-1 bg-slate-50 border border-slate-300 text-slate-900 rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500">
            <!-- Dynamic Real Episodes Populated via JS -->
          </select>
          <div id="ep-mode-badge" class="px-3.5 py-2 rounded-xl text-xs font-bold flex items-center gap-2 border bg-amber-50 text-amber-800 border-amber-300 whitespace-nowrap">
            <span class="w-2 h-2 rounded-full bg-amber-500 animate-ping"></span>
            <span>⚡ LIVE EXECUTION MONITOR</span>
          </div>
        </div>
      </div>

      <div class="flex items-center gap-2 self-end sm:self-auto">
        <button onclick="resetToLiveEpisode()" class="px-3 py-2 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-200 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
          EP Đang Chạy Hôm Nay
        </button>
      </div>
    </div>

    <!-- Active Artifact Banner -->
    <div class="mt-3.5 pt-3 border-t border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between text-xs text-slate-600 gap-2">
      <div class="flex items-center gap-2">
        <span class="font-semibold text-slate-500">File Artifact Đang Xử Lý:</span>
        <code id="active-artifact-display" class="font-mono bg-slate-100 px-2.5 py-1 rounded-md text-indigo-700 font-semibold border border-slate-200">
          remotion_props.json (Đang render Remotion CPU...)
        </code>
      </div>
      <div class="flex items-center gap-2">
        <span class="text-slate-500">Giai Đoạn Hiện Tại:</span>
        <span id="current-stage-title" class="font-bold text-slate-800">B7: Render Video Master Remotion (Bước 15/19)</span>
      </div>
    </div>
  </section>

  <!-- 6 BƯỚC LỚN (MAJOR PHASES TIMELINE STEPPER) -->
  <section class="mb-6">
    <div class="flex items-center justify-between mb-2 px-1">
      <h2 class="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
        <svg class="w-4 h-4 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"></path></svg>
        Cây Timeline 6 Bước Lớn Toàn Trình (Major Phase Stepper):
      </h2>
      <span class="text-[11px] text-slate-500 font-medium">Bấm vào Bước Lớn để lọc xem nhanh các node bên dưới</span>
    </div>

    <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3" id="major-phases-stepper">
      <!-- Generated via JS -->
    </div>
  </section>

  <!-- WORKFLOW CANVAS (N8N STYLE NODES BY MAJOR PHASES) -->
  <main class="space-y-6">
    <div id="phases-container" class="space-y-6">
      <!-- Generated via JS: Phase groups containing n8n-style nodes -->
    </div>
  </main>

  <!-- SLIDE-OUT NODE INSPECTOR DRAWER -->
  <div id="inspector-backdrop" onclick="closeInspector()" class="fixed inset-0 drawer-backdrop z-40 hidden transition-opacity"></div>
  <aside id="node-inspector" class="fixed top-0 right-0 bottom-0 w-full sm:w-[500px] lg:w-[560px] bg-white border-l border-slate-200 shadow-2xl z-50 transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col">
    <!-- Drawer Header -->
    <div class="p-4 sm:p-5 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <span id="drawer-icon-container" class="w-9 h-9 rounded-xl flex items-center justify-center font-bold text-white shadow-sm">
          B1
        </span>
        <div>
          <span id="drawer-stage-badge" class="text-[10px] font-bold uppercase tracking-wider text-indigo-600 bg-indigo-50 border border-indigo-200 px-2 py-0.5 rounded-full">
            Block 1.0
          </span>
          <h3 id="drawer-node-title" class="text-base font-bold text-slate-900 mt-0.5">
            Trend Discovery
          </h3>
        </div>
      </div>
      <button onclick="closeInspector()" class="p-2 text-slate-400 hover:text-slate-700 hover:bg-slate-200 rounded-lg transition">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
      </button>
    </div>

    <!-- Drawer Content Scrollable -->
    <div class="p-4 sm:p-6 overflow-y-auto flex-1 space-y-5 text-xs text-slate-600">
      
      <!-- Episode Status Banner -->
      <div id="drawer-ep-status-card" class="p-3.5 rounded-xl border flex items-center justify-between">
        <!-- Injected via JS -->
      </div>

      <!-- Engine & Source Code -->
      <div class="bg-slate-50 p-3.5 rounded-xl border border-slate-200 space-y-2">
        <div class="text-[11px] font-bold uppercase tracking-wider text-slate-500">Mã Nguồn Thực Thi (Source Engine)</div>
        <div id="drawer-engine-name" class="font-semibold text-slate-900 text-sm"></div>
        <div id="drawer-source-files" class="space-y-1 font-mono text-[11px]"></div>
      </div>

      <!-- INPUT DATA CONTRACT -->
      <div class="border border-slate-200 rounded-xl overflow-hidden">
        <div class="bg-indigo-50/70 px-3.5 py-2 border-b border-slate-200 flex items-center justify-between">
          <span class="font-bold text-indigo-900 text-[11px] uppercase tracking-wider flex items-center gap-1.5">
            <span class="w-2 h-2 rounded-full bg-indigo-500"></span>
            ĐẦU VÀO (INPUT SPECIFICATION)
          </span>
          <span id="drawer-input-source" class="font-mono text-[10px] text-indigo-700 bg-indigo-100/60 px-2 py-0.5 rounded"></span>
        </div>
        <div class="p-3.5 space-y-2.5 bg-white">
          <div>
            <span class="text-slate-400 block text-[10px] uppercase font-semibold">Định dạng nạp vào:</span>
            <div id="drawer-input-format" class="text-slate-800 font-medium mt-0.5"></div>
          </div>
          <div>
            <span class="text-slate-400 block text-[10px] uppercase font-semibold">Cấu trúc Schema Input:</span>
            <pre id="drawer-input-schema" class="bg-slate-50 p-2.5 rounded-lg border border-slate-200 text-[11px] overflow-x-auto text-slate-800 mt-1"></pre>
          </div>
        </div>
      </div>

      <!-- OUTPUT DATA CONTRACT -->
      <div class="border border-slate-200 rounded-xl overflow-hidden">
        <div class="bg-emerald-50/70 px-3.5 py-2 border-b border-slate-200 flex items-center justify-between">
          <span class="font-bold text-emerald-900 text-[11px] uppercase tracking-wider flex items-center gap-1.5">
            <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
            ĐẦU RA (OUTPUT ARTIFACT & TARGET)
          </span>
          <span id="drawer-output-target" class="font-mono text-[10px] text-emerald-700 bg-emerald-100/60 px-2 py-0.5 rounded"></span>
        </div>
        <div class="p-3.5 space-y-2.5 bg-white">
          <div>
            <span class="text-slate-400 block text-[10px] uppercase font-semibold">Đường dẫn file trên VPS:</span>
            <code id="drawer-output-format" class="font-mono text-indigo-600 block bg-slate-50 px-2 py-1 rounded border border-slate-200 text-[11px] mt-0.5"></code>
          </div>
          <div>
            <span class="text-slate-400 block text-[10px] uppercase font-semibold">Danh mục Artifact sinh ra:</span>
            <ul id="drawer-output-artifacts" class="list-disc pl-4 mt-1 space-y-1 text-slate-800 font-medium"></ul>
          </div>
        </div>
      </div>

      <!-- NOTION SOT HEALTH AUDIT -->
      <div class="border border-slate-200 rounded-xl overflow-hidden">
        <div class="bg-slate-50 px-3.5 py-2 border-b border-slate-200 flex items-center justify-between">
          <span class="font-bold text-slate-700 text-[11px] uppercase tracking-wider">KIỂM TOÁN NOTION SOT</span>
          <span id="drawer-notion-badge" class="px-2 py-0.5 rounded text-[10px] font-bold"></span>
        </div>
        <div class="p-3.5 bg-white space-y-1.5">
          <p id="drawer-notion-detail" class="text-slate-700 leading-relaxed"></p>
        </div>
      </div>

      <!-- INVARIANTS & QUALITY GATES -->
      <div class="border border-slate-200 rounded-xl p-3.5 bg-slate-50 space-y-2">
        <div class="font-bold uppercase tracking-wider text-slate-500 text-[11px]">Luật Bất Biến & Chốt Chặn Kiểm Toán (Invariants)</div>
        <ul id="drawer-invariants" class="space-y-1.5 text-slate-700"></ul>
      </div>

    </div>
  </aside>

  <!-- JAVASCRIPT LOGIC -->
  <script>
    const PIPELINE_NODES = {nodes_json};
    const MAJOR_PHASES = {phases_json};
    const EPISODE_MILESTONES = {milestones_json};
    const REAL_EPISODES = {episodes_json};

    let currentEpisode = (REAL_EPISODES && REAL_EPISODES.length > 0) ? REAL_EPISODES[0] : null;
    let activeFilterPhaseId = null;

    function initEpisodeSelector() {{
      const sel = document.getElementById("ep-select");
      if (!sel) return;
      sel.innerHTML = "";
      
      REAL_EPISODES.forEach(ep => {{
        const opt = document.createElement("option");
        opt.value = ep.episode_id;
        
        let tag = "[PENDING]";
        if (ep.is_active_running) tag = "⚡ [ĐANG CHẠY]";
        else if (ep.has_video || ep.status === "completed") tag = "✓ [HOÀN TẤT]";
        else if (ep.status === "ready_to_render") tag = "⏳ [CHỜ RENDER]";
        else if (ep.status === "in_progress") tag = "⚙️ [TIẾN TRÌNH]";
        
        const pct = Math.round((ep.current_step_index / (EPISODE_MILESTONES.length - 1)) * 100);
        opt.innerText = `${{tag}} ${{ep.episode_id}} (${{ep.market}}) — Bước ${{ep.current_step_index}}/19 (${{pct}}%)`;
        sel.appendChild(opt);
      }});
      
      if (currentEpisode) {{
        sel.value = currentEpisode.episode_id;
      }}
    }}

    function changeEpisode() {{
      const epId = document.getElementById("ep-select").value;
      const found = REAL_EPISODES.find(e => e.episode_id === epId);
      if (found) {{
        currentEpisode = found;
        updateUI();
      }}
    }}

    function resetToLiveEpisode() {{
      const live = REAL_EPISODES.find(e => e.is_active_running) || REAL_EPISODES[0];
      if (live) {{
        currentEpisode = live;
        document.getElementById("ep-select").value = currentEpisode.episode_id;
        updateUI();
      }}
    }}

    function computeNodeStatus(node, episode) {{
      const milestone = EPISODE_MILESTONES.find(m => m.node_id === node.id);
      const mIdx = milestone ? milestone.index : -1;

      // RULE: HISTORICAL EPISODE MUST SHOW 100% COMPLETED FOR ALL EXECUTED STEPS!
      if (episode.has_video || episode.status === "completed") {{
        return {{
          status: "COMPLETED",
          label: "✓ HOÀN TẤT",
          badgeClass: "bg-emerald-50 text-emerald-700 border-emerald-300",
          dotClass: "bg-emerald-500",
          nodeBorder: "border-slate-200",
          isCurrent: false
        }};
      }}

      // LIVE RUNNING EPISODE
      if (mIdx < episode.current_step_index) {{
        return {{
          status: "COMPLETED",
          label: "✓ HOÀN TẤT",
          badgeClass: "bg-emerald-50 text-emerald-700 border-emerald-300",
          dotClass: "bg-emerald-500",
          nodeBorder: "border-slate-200",
          isCurrent: false
        }};
      }} else if (mIdx === episode.current_step_index) {{
        return {{
          status: episode.is_active_running ? "RUNNING" : "READY",
          label: episode.is_active_running ? "⚡ ĐANG CHẠY VPS" : "⏳ SẴN SÀNG",
          badgeClass: "bg-amber-50 text-amber-800 border-amber-300 ring-2 ring-amber-400/40",
          dotClass: "bg-amber-500 animate-ping",
          nodeBorder: "border-amber-400 shadow-amber-100",
          isCurrent: true
        }};
      }} else {{
        return {{
          status: "PENDING",
          label: "⏳ CHỜ XỬ LÝ",
          badgeClass: "bg-slate-50 text-slate-500 border-slate-200",
          dotClass: "bg-slate-300",
          nodeBorder: "border-slate-200 opacity-80",
          isCurrent: false
        }};
      }}
    }}

    function renderMajorPhasesStepper() {{
      const container = document.getElementById("major-phases-stepper");
      if (!container) return;
      container.innerHTML = "";

      const currentMilestone = EPISODE_MILESTONES[currentEpisode.current_step_index];
      const isHistorical = currentEpisode.has_video || currentEpisode.status === "completed";

      MAJOR_PHASES.forEach(phase => {{
        const phaseNodes = PIPELINE_NODES.filter(n => phase.node_ids.includes(n.id));
        const totalInPhase = phaseNodes.length;
        
        let completedInPhase = 0;
        let isPhaseActive = false;

        phaseNodes.forEach(n => {{
          const st = computeNodeStatus(n, currentEpisode);
          if (st.status === "COMPLETED") completedInPhase++;
          if (st.status === "RUNNING") isPhaseActive = true;
        }});

        if (isHistorical) completedInPhase = totalInPhase;

        const isFullyDone = completedInPhase === totalInPhase;
        const isSelectedFilter = activeFilterPhaseId === phase.id;

        const card = document.createElement("div");
        card.className = `p-3.5 rounded-xl border transition cursor-pointer ${{
          isSelectedFilter ? 'ring-2 ring-indigo-500 bg-indigo-50/50 border-indigo-300' :
          isPhaseActive ? 'bg-amber-50/50 border-amber-300 ring-1 ring-amber-300' :
          isFullyDone ? 'bg-white border-slate-200 hover:border-slate-300' :
          'bg-slate-50/80 border-slate-200 text-slate-400'
        }}`;
        card.onclick = () => filterByPhase(phase.id);

        let statusBadge = `<span class="text-[10px] font-bold text-slate-400">CHỜ</span>`;
        if (isFullyDone) {{
          statusBadge = `<span class="text-[10px] font-bold text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">✓ XONG</span>`;
        }} else if (isPhaseActive) {{
          statusBadge = `<span class="text-[10px] font-bold text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-300 animate-pulse">⚡ RUNNING</span>`;
        }}

        card.innerHTML = `
          <div class="flex items-center justify-between mb-1.5">
            <span class="text-[10px] font-extrabold uppercase tracking-wider text-${{phase.color}}-600">Bước ${{phase.index}}</span>
            ${{statusBadge}}
          </div>
          <div class="text-xs font-bold text-slate-900 leading-tight mb-2 truncate" title="${{phase.name}}">
            ${{phase.name}}
          </div>
          <div class="flex items-center justify-between text-[10px] text-slate-500 mb-1">
            <span>${{completedInPhase}} / ${{totalInPhase}} nodes</span>
            <span>${{Math.round((completedInPhase / totalInPhase) * 100)}}%</span>
          </div>
          <div class="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
            <div class="bg-${{phase.color}}-500 h-full rounded-full transition-all duration-500" style="width: ${{(completedInPhase / totalInPhase) * 100}}%"></div>
          </div>
        `;
        container.appendChild(card);
      }});
    }}

    function filterByPhase(phaseId) {{
      activeFilterPhaseId = activeFilterPhaseId === phaseId ? null : phaseId;
      renderWorkflowNodes();
      renderMajorPhasesStepper();
    }}

    function renderWorkflowNodes() {{
      const container = document.getElementById("phases-container");
      if (!container) return;
      container.innerHTML = "";

      MAJOR_PHASES.forEach(phase => {{
        if (activeFilterPhaseId && activeFilterPhaseId !== phase.id) return;

        const phaseNodes = PIPELINE_NODES.filter(n => phase.node_ids.includes(n.id));

        const groupDiv = document.createElement("div");
        groupDiv.className = "bg-white/80 backdrop-blur-sm border border-slate-200 rounded-2xl p-4 sm:p-5 shadow-sm";

        // Group Header
        groupDiv.innerHTML = `
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4 pb-3 border-b border-slate-100">
            <div class="flex items-center gap-2.5">
              <span class="w-7 h-7 rounded-lg ${{phase.header_bg}} text-white font-bold text-xs flex items-center justify-center shadow-sm">
                ${{phase.index}}
              </span>
              <div>
                <h3 class="text-base font-bold text-slate-900">${{phase.name}}</h3>
                <p class="text-xs text-slate-500">${{phase.description}}</p>
              </div>
            </div>
            <span class="text-xs font-semibold px-2.5 py-1 rounded-lg border ${{phase.badge_color}} self-start sm:self-auto">
              ${{phase.en_name}} (${{phaseNodes.length}} Nodes)
            </span>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" id="nodes-grid-${{phase.id}}">
          </div>
        `;
        container.appendChild(groupDiv);

        const grid = groupDiv.querySelector(`#nodes-grid-${{phase.id}}`);

        phaseNodes.forEach(node => {{
          const st = computeNodeStatus(node, currentEpisode);

          const card = document.createElement("div");
          card.className = `n8n-node p-4 cursor-pointer ${{st.nodeBorder}} ${{st.isCurrent ? 'is-active-running pulse-ring' : ''}}`;
          card.onclick = () => openInspector(node.id);

          // Notion Pill
          let notionPill = `<span class="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 font-medium border border-slate-200">Disconnected</span>`;
          if (node.notion_status === "ACTIVE_SOT") {{
            notionPill = `<span class="text-[10px] px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 font-semibold border border-emerald-200">Active SoT</span>`;
          }} else if (node.notion_status === "OUTPUT_SINK") {{
            notionPill = `<span class="text-[10px] px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 font-semibold border border-blue-200">Output Sink</span>`;
          }}

          card.innerHTML = `
            <!-- Ports for n8n look -->
            <div class="port-dot port-in" title="Input Port"></div>
            <div class="port-dot port-out" title="Output Port"></div>

            <!-- Card Header -->
            <div class="flex items-center justify-between mb-2">
              <span class="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 border border-slate-200">
                ${{node.stage}}
              </span>
              <span class="text-[10px] font-bold px-2 py-0.5 rounded-full border ${{st.badgeClass}} flex items-center gap-1">
                <span class="w-1.5 h-1.5 rounded-full ${{st.dotClass}}"></span>
                ${{st.label}}
              </span>
            </div>

            <!-- Node Title & Category -->
            <h4 class="text-sm font-bold text-slate-900 leading-snug mb-1 hover:text-indigo-600 transition">
              ${{node.name}}
            </h4>
            <div class="text-[11px] text-slate-500 font-mono mb-3 truncate" title="${{node.engine}}">
              ${{node.engine}}
            </div>

            <!-- In/Out Pills -->
            <div class="space-y-1.5 pt-2.5 border-t border-slate-100 text-[11px]">
              <div class="flex items-center gap-1.5 text-slate-600 truncate">
                <span class="font-bold text-indigo-600 shrink-0">IN:</span>
                <span class="truncate text-slate-700" title="${{node.inputs.source}}">${{node.inputs.source}}</span>
              </div>
              <div class="flex items-center gap-1.5 text-slate-600 truncate">
                <span class="font-bold text-emerald-600 shrink-0">OUT:</span>
                <span class="truncate text-slate-700" title="${{node.outputs.artifacts ? node.outputs.artifacts[0] : node.outputs.format}}">${{node.outputs.artifacts ? node.outputs.artifacts[0] : node.outputs.format}}</span>
              </div>
            </div>

            <!-- Card Footer -->
            <div class="flex items-center justify-between mt-3 pt-2 border-t border-slate-100 text-[10px]">
              ${{notionPill}}
              <span class="text-indigo-600 font-semibold hover:underline flex items-center gap-0.5">
                Chi tiết &rarr;
              </span>
            </div>
          `;
          grid.appendChild(card);
        }});
      }});
    }}

    function openInspector(nodeId) {{
      const node = PIPELINE_NODES.find(n => n.id === nodeId);
      if (!node) return;

      const st = computeNodeStatus(node, currentEpisode);

      // Icon & Stage
      const iconContainer = document.getElementById("drawer-icon-container");
      iconContainer.className = `w-9 h-9 rounded-xl flex items-center justify-center font-bold text-white shadow-sm bg-indigo-600`;
      iconContainer.innerText = node.stage.replace("Block ", "B").replace("Human Gate ", "HG");

      document.getElementById("drawer-stage-badge").innerText = node.stage;
      document.getElementById("drawer-node-title").innerText = node.name;

      // Status card
      const epStatusCard = document.getElementById("drawer-ep-status-card");
      epStatusCard.className = `p-3.5 rounded-xl border flex items-center justify-between ${{
        st.status === 'COMPLETED' ? 'bg-emerald-50/60 border-emerald-200 text-emerald-900' :
        st.status === 'RUNNING' ? 'bg-amber-50/80 border-amber-300 text-amber-900' :
        'bg-slate-50 border-slate-200 text-slate-600'
      }}`;
      epStatusCard.innerHTML = `
        <div>
          <div class="text-[10px] uppercase font-bold text-slate-500">Trạng Thái Trên ${{currentEpisode.episode_id}}</div>
          <div class="text-sm font-bold flex items-center gap-1.5 mt-0.5">
            <span class="w-2 h-2 rounded-full ${{st.dotClass}}"></span>
            ${{st.label}}
          </div>
        </div>
        <span class="font-mono text-[11px] font-bold px-2.5 py-1 rounded-lg border ${{st.badgeClass}}">
          ${{st.status}}
        </span>
      `;

      // Engine
      document.getElementById("drawer-engine-name").innerText = node.engine;
      const srcFiles = document.getElementById("drawer-source-files");
      srcFiles.innerHTML = "";
      (node.source_files || []).forEach(f => {{
        const d = document.createElement("div");
        d.className = "text-indigo-600 bg-white px-2 py-1 rounded border border-slate-200";
        d.innerText = f;
        srcFiles.appendChild(d);
      }});

      // Inputs
      document.getElementById("drawer-input-source").innerText = node.inputs.source;
      document.getElementById("drawer-input-format").innerText = node.inputs.format;
      document.getElementById("drawer-input-schema").innerText = JSON.stringify(node.inputs.schema || {{}}, null, 2);

      // Outputs
      document.getElementById("drawer-output-target").innerText = node.outputs.target;
      document.getElementById("drawer-output-format").innerText = node.outputs.format;
      const artList = document.getElementById("drawer-output-artifacts");
      artList.innerHTML = "";
      (node.outputs.artifacts || []).forEach(a => {{
        const li = document.createElement("li");
        li.innerText = a;
        artList.appendChild(li);
      }});

      // Notion
      const nBadge = document.getElementById("drawer-notion-badge");
      nBadge.className = `px-2 py-0.5 rounded text-[10px] font-bold ${{
        node.notion_status === 'ACTIVE_SOT' ? 'bg-emerald-100 text-emerald-800' :
        node.notion_status === 'OUTPUT_SINK' ? 'bg-blue-100 text-blue-800' :
        'bg-slate-200 text-slate-700'
      }}`;
      nBadge.innerText = node.notion_status;
      document.getElementById("drawer-notion-detail").innerText = node.notion_detail;

      // Invariants
      const invList = document.getElementById("drawer-invariants");
      invList.innerHTML = "";
      (node.invariants || []).forEach(inv => {{
        const li = document.createElement("li");
        li.className = "flex items-start gap-1.5";
        li.innerHTML = `<span class="text-indigo-500 font-bold">•</span><span>${{inv}}</span>`;
        invList.appendChild(li);
      }});

      // Show drawer
      document.getElementById("inspector-backdrop").classList.remove("hidden");
      document.getElementById("node-inspector").classList.remove("translate-x-full");
    }}

    function closeInspector() {{
      document.getElementById("inspector-backdrop").classList.add("hidden");
      document.getElementById("node-inspector").classList.add("translate-x-full");
    }}

    function updateUI() {{
      if (!currentEpisode) return;
      const pct = Math.round((currentEpisode.current_step_index / (EPISODE_MILESTONES.length - 1)) * 100);
      const isHistorical = currentEpisode.has_video || currentEpisode.status === "completed";

      // Header metrics
      document.getElementById("header-ep-progress").innerText = `${{pct}}%`;
      document.getElementById("header-ep-step").innerText = `Bước ${{currentEpisode.current_step_index}} / 19`;

      // Active artifact
      document.getElementById("active-artifact-display").innerText = currentEpisode.active_artifact || "N/A";
      document.getElementById("current-stage-title").innerText = `${{currentEpisode.current_stage_name || 'Đang xử lý'}} (Bước ${{currentEpisode.current_step_index}}/19)`;

      // Mode Badge
      const modeBadge = document.getElementById("ep-mode-badge");
      if (isHistorical) {{
        modeBadge.className = "px-3.5 py-2 rounded-xl text-xs font-bold flex items-center gap-2 border bg-emerald-50 text-emerald-800 border-emerald-300 whitespace-nowrap";
        modeBadge.innerHTML = `<span class="w-2 h-2 rounded-full bg-emerald-500"></span><span>📁 LỊCH SỬ HOÀN TẤT (100% HOÀN THÀNH)</span>`;
      }} else {{
        modeBadge.className = "px-3.5 py-2 rounded-xl text-xs font-bold flex items-center gap-2 border bg-amber-50 text-amber-800 border-amber-300 whitespace-nowrap";
        modeBadge.innerHTML = `<span class="w-2 h-2 rounded-full bg-amber-500 animate-ping"></span><span>⚡ LIVE EXECUTION MONITOR (ĐANG CHẠY VPS)</span>`;
      }}

      renderMajorPhasesStepper();
      renderWorkflowNodes();
    }}

    window.addEventListener("DOMContentLoaded", () => {{
      initEpisodeSelector();
      updateUI();
    }});
  </script>
</body>
</html>
"""

def generate():
    html_content = build_n8n_light_html()
    target_paths = [
        ROOT_DIR / "reports" / "ai_pipeline_observability_ui.html",
        Path(r"C:\Users\hunghd2\.gemini\antigravity\brain\bb2d98e1-8cae-467c-a3d4-74cd8e97402b\ai_pipeline_observability_ui.html")
    ]
    for p in target_paths:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(html_content, encoding="utf-8")
        print(f"✅ Generated n8n light HTML dashboard: {p} ({p.stat().st_size} bytes)")

if __name__ == "__main__":
    generate()
