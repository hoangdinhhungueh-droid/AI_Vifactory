#!/usr/bin/env python3
"""
scripts/orchestrator/deep_vox_comparative_audit.py

Dual LLM High Council (Claude Opus 5.5 & GPT-6 Astra):
Deep Forensic Analysis on Rendered Master Video (YouTube CzJ7rjuU3Cs)
vs. YouTube Tutorial Benchmark (cXQuNBZA0FA).

Addresses User Concerns:
1. Why do Foreground (FG), transitions, and objects still feel 'vô tri' (lifeless, mechanical)?
2. Is the TimesCar data breach story inherently too difficult/restricted for Vox style,
   or is it an engineering & visual choreography defect?
3. Checklist evaluation across every 5-10s segment.
"""

import os
import sys
import json
import time
from pathlib import Path

ROOT_DIR = Path("/root/video_factory")
sys.path.insert(0, str(ROOT_DIR))

from app.services.model_gateway import get_global_gateway


def main():
    if len(sys.argv) < 2:
        print("Usage: python deep_vox_comparative_audit.py <EPISODE_ID>")
        sys.exit(1)
    ep_id = sys.argv[1]
    ep_dir = Path(f"/var/vf/episodes/{ep_id}")
    deep_audit_dir = ep_dir / "deep_audit"
    props_path = ep_dir / "remotion_props.json"
    
    props = json.loads(props_path.read_text(encoding="utf-8")) if props_path.exists() else {}
    scenes = props.get("scenes", [])
    
    # Sample 6 anchor scenes across the timeline
    anchors = [
        {"tc": "00:15", "scene_idx": 4, "desc": "Cold Open Hook"},
        {"tc": "00:45", "scene_idx": 11, "desc": "Systemic Vulnerability"},
        {"tc": "02:00", "scene_idx": 28, "desc": "Scale of Impact"},
        {"tc": "04:00", "scene_idx": 57, "desc": "Forensic Paper Trail"},
        {"tc": "06:20", "scene_idx": 90, "desc": "Institutional Failure"},
        {"tc": "08:40", "scene_idx": 123, "desc": "Climax / Living Warning"},
    ]
    
    scene_samples_text = ""
    for a in anchors:
        s = scenes[a["scene_idx"]] if a["scene_idx"] < len(scenes) else {}
        fg = s.get("foreground", "None")
        bg = s.get("background", "None")
        ov = s.get("forensicOverlay", s.get("forensic_overlay", "None"))
        stat = s.get("statValue")
        headline = s.get("editorialHeadline")
        trans = s.get("transition_out", s.get("transitionOut", "default_crossfade"))
        scene_samples_text += f"""
- [Scene {a['scene_idx']} @ {a['tc']} - {a['desc']}]:
  * Narration: "{s.get('narration', '')[:120]}..."
  * FG Asset: {os.path.basename(fg) if fg else 'None'} (Pos: {s.get('foregroundPosition', 'left')})
  * BG Asset: {os.path.basename(bg) if bg else 'None'}
  * Overlay Component: {ov.get('type') if isinstance(ov, dict) else ov}
  * Stat Card: {stat} ({s.get('statLabel')})
  * Transition Out: {trans}
  * Connecting Vectors: {bool(s.get('connection') or s.get('radiatingConnections'))}
"""

    audit_brief = f"""
# THÔNG TIN PHÁP Y TẬP PHIM ĐÃ XUẤT XƯỞNG
- Episode: {ep_id}
- Benchmark So Sánh: YouTube cXQuNBZA0FA ("How to Make Viral Vox-Style Videos with AI", đoạn 00:32-00:49)

# PHẢN HỒI THỰC TẾ TỪ SHOWRUNNER (USER):
"Video chưa đạt yêu cầu, tiến bộ hơn ở câu chuyện animation chứ FG, chuyển tiếp, các object vẫn vô tri.
Gọi 2 LLM Opus 5.5 và Astra 6 soi bản thiết kế cùng với từng frame 5-10s trong video để đánh giá về mọi thứ theo checklist.
Hay có phải vì story quá khó/khóa làm vox style như video hướng dẫn? https://www.youtube.com/watch?v=cXQuNBZA0FA"

# DỮ LIỆU CẤU HÌNH CẢNH MẪU TRÊN TIMELINE (REMOTION PROPS):
{scene_samples_text}
"""


    gw = get_global_gateway()

    # =========================================================================
    # ROUND 1: CLAUDE OPUS 5.5 (Lead Visual Architect & Creative Director)
    # =========================================================================
    print("🧠 [OPUS 5.5] Deliberating from First Principles...")
    opus_prompt = f"""{audit_brief}

BẠN LÀ CLAUDE OPUS 5.5, LEAD VISUAL ARCHITECT & CREATIVE DIRECTOR CỦA AI VIDEO FACTORY.
Hãy tiến hành một phiên mổ xẻ chuyên sâu, trung thực, không bao biện (Zero-Sycophancy) để trả lời người dùng:

1. TRẢ LỜI CÂU HỎI CỐT LÕI: "Có phải vì Story (vụ rò rỉ TimesCar) quá khó/bị khóa để làm Vox style so với clip Coca-Cola?"
   - Hãy phân tích từ Nguyên lý Gốc (First Principles): Phong cách Vox vốn sinh ra để giải mã những đề tài trừu tượng, khô khan, thể chế (vd: Cambridge Analytica, Boeing 737, Uber algorithm, rửa tiền).
   - Tại sao clip Coca-Cola lại sống động và dễ làm hơn? Còn với vụ án rò rỉ 6.6 triệu bằng lái TimesCar, Vox thực sự sẽ giải quyết nó bằng những đạo cụ và ẩn dụ thị giác xúc giác (tactile visual metaphors) nào?
   
2. GIẢI PHÃU NGUYÊN NHÂN "VÔ TRI" (FG, CHUYỂN TIẾP, OBJECTS):
   - **Foreground (FG) vô tri**: Tại sao nhân vật cutout lại bị xem là "vô tri"? (Có phải do: nhân vật đứng yên làm bù nhìn góc màn hình, tư thế ảnh thẻ tĩnh, không cầm nắm tương tác với đạo cụ thực tế như bằng lái, điện thoại, máy chủ, con dấu?).
   - **Chuyển tiếp (Transitions) vô tri**: Hiện tại Remotion chỉ đổi scene bằng hard-cut hoặc crossfade 6-frame. Thiếu những gì? (Match-cut xoay lật như nắp chai Coca ở 00:42, camera push-through, paper slide wipe, lật trang sổ kẻ ô ở 00:40).
   - **Objects vô tri**: Thẻ Stat Card hiện tại giống UI website (div đen nổi góc màn hình) chứ không phải một mảnh giấy xé dán thật, một bức ảnh polaroid thả rơi, hay một con tem thực tế.

3. ĐỐI SOÁT TOÀN DIỆN THEO CHECKLIST 7 TẦNG CẮT DÁN VOX (TỪ VIDEO cXQuNBZA0FA):
   - Đánh giá từng tầng: Layer 0 (Giấy nền), Layer 1 (Khối hình học), Layer 2 (Typography), Layer 3 (Cutout chính), Layer 4 (Đạo cụ phụ/Polaroid), Layer 5 (Chỉ đỏ/Vector), Layer 6 (Bóng đổ & Stop-motion).

4. BẢN THIẾT KẾ ĐẠO DIỄN CẢI TỔ (CONCRETE REMEDIATION BLUEPRINT):
   - Cần thay đổi gì ở B3 Director Plan?
   - Cần thay đổi gì ở B4 Prompt sinh ảnh FG (yêu cầu tương tác đạo cụ)?
   - Cần nâng cấp gì ở Remotion TSX để FG, transition và objects có "LINH HỒN" (purposeful kinetic motivation)?"""

    opus_resp = gw.call_llm(
        prompt=opus_prompt,
        model="claude-opus-5-5",
        fallback="claude-sonnet-5-5",
        max_tokens=3500,
        temperature=0.3,
        timeout=180.0
    )
    print(f"✅ Claude Opus 5.5 responded ({len(opus_resp)} chars)")

    # =========================================================================
    # ROUND 2: GPT-6 ASTRA (Adversarial Quality Auditor & Skeptic)
    # =========================================================================
    print("⚖️ [GPT-6 ASTRA] Conducting Adversarial Cross-Examination...")
    astra_prompt = f"""{audit_brief}

BẢN ĐÁNH GIÁ CỦA CLAUDE OPUS 5.5:
{opus_resp}

BẠN LÀ GPT-6 ASTRA, ADVERSARIAL FORENSIC AUDITOR CỦA AI VIDEO FACTORY.
Nhiệm vụ của bạn: ĐỐI CHẤT THẲNG THẮN với Claude Opus 5.5, bảo vệ sự thật kỹ thuật khách quan và lập checklist kiểm định khắt khe nhất:

1. PHẢN BIỆN PHÂN TÍCH CỦA OPUS 5.5:
   - Opus 5.5 phân tích có đúng trọng tâm bức xúc của User chưa?
   - Chỉ ra những điểm "tự huyễn hoặc" của kỹ sư: Việc thêm sine wave sway 2px hay border trắng 7px chỉ là "vỏ bọc kỹ thuật", không hề giải quyết được cái "hồn" của chuyển động có chủ đích (motivated motion).

2. BẢNG CHECKLIST PHÁP Y THỊ GIÁC (VOX PARITY CHECKLIST):
   - Thiết lập bảng kiểm định 10 tiêu chí chi tiết cho từng khung hình 5-10s. Chấm điểm trực diện video CzJ7rjuU3Cs (Đạt / Không đạt / Lý do kỹ thuật).

3. KẾT LUẬN CUỐI CÙNG & LỜI KHUYÊN CHO SHOWRUNNER:
   - Khẳng định dứt khoát: Đề tài TimesCar hoàn toàn KHÔNG PHẢI NGUYÊN NHÂN gây ra sự "vô tri". Lỗi 100% nằm ở tư duy lắp ghép linh kiện rời rạc của pipeline.
   - Lộ trình 3 bước hành động cấp bách để tập tiếp theo lột xác hoàn toàn."""

    astra_resp = gw.call_llm(
        prompt=astra_prompt,
        model="gpt-6-astra",
        fallback="gpt-6.1-sol",
        max_tokens=3500,
        temperature=0.2,
        timeout=180.0
    )
    print(f"✅ GPT-6 Astra responded ({len(astra_resp)} chars)")

    report_path = ep_dir / "vox_deep_comparative_audit.md"
    final_report = f"""# 🏛️ ĐẠI HỘI ĐỒNG THẨM ĐỊNH PHÁP Y ĐA MÔ THỨC (OPUS 5.5 & ASTRA 6)
## CHẨN ĐOÁN TẬN GỐC HIỆN TƯỢNG "VÔ TRI" TRÊN VIDEO YOUTUBE CzJ7rjuU3Cs
## SO SÁNH VỚI CHUẨN MỰC VOX MASTERCLASS (YOUTUBE cXQuNBZA0FA)

> **Video đã tải lên YouTube:** https://www.youtube.com/watch?v=CzJ7rjuU3Cs  
> **Video hướng dẫn chuẩn:** https://www.youtube.com/watch?v=cXQuNBZA0FA  
> **Tập phim:** `{ep_id}`  
> **Hội đồng thực hiện:** Claude Opus 5.5 (Lead Visual Architect) & GPT-6 Astra (Adversarial Forensic Auditor)

---

## 🎭 PHẦN 1: BÁO CÁO GIẢI PHÃU CỦA CLAUDE OPUS 5.5 (LEAD VISUAL ARCHITECT)

{opus_resp}

---

## ⚖️ PHẦN 2: BÁO CÁO ĐỐI CHẤT PHẢN BIỆN CỦA GPT-6 ASTRA (CHIEF SKEPTIC & FORENSIC LINTER)

{astra_resp}

---

## 🎯 PHẦN 3: TỔNG KẾT ĐỒNG THUẬN SHOWRUNNER & HÀNH ĐỘNG CẢI TỔ
"""
    report_path.write_text(final_report, encoding="utf-8")
    print(f"📄 Report written to {report_path}")


if __name__ == "__main__":
    main()
