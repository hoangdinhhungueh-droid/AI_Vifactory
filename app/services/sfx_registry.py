"""
app/services/sfx_registry.py — Single Source of Truth (SoT) for Foley & Sound Effects.

Architectural Mandates (Rule 118, 120, 128 & 134):
- Defines the CLOSED canonical registry of all supported sound effects (SFX) in the AI Video Factory pipeline.
- 100% 1:1 parity with physical files in `remotion/public/sfx/*.mp3`.
- Strict semantic resolver mapping narrative keywords (EN, JP, KR, VN) to canonical keys.
- ZERO blind/silent fallbacks: any unknown cue or missing file must trigger an explicit validation error.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
SFX_DIR = ROOT_DIR / "remotion" / "public" / "sfx"

CANONICAL_SFX_REGISTRY: Dict[str, Dict[str, Any]] = {
    "counter_tick": {
        "filename": "counter_tick.mp3",
        "category": "INSTRUMENT_METER",
        "description": "Ticking stopwatch / forensic rollup counter sound for numerical tension",
        "keywords": ["counter", "tick", "clock", "timer", "seconds", "rollup", "숫자", "카운터", "計数", "時計", "đếm"]
    },
    "document_table_thud": {
        "filename": "document_table_thud.mp3",
        "category": "PERCUSSION_IMPACT",
        "description": "Heavy paper docket or binder dropping onto wooden table",
        "keywords": ["invoice", "damage", "bill", "check", "listing", "card", "hóa đơn", "chi phí", "영수증", "손해", "請求書", "損害", "drop", "thud"]
    },
    "gauge_needle_hiss": {
        "filename": "gauge_needle_hiss.mp3",
        "category": "INSTRUMENT_METER",
        "description": "Pressure gauge needle deflection with chemical hiss / laboratory spectrometry tension",
        "keywords": ["gauge", "meter", "vial", "chemical", "hóa chất", "lưu huỳnh", "sulfur", "residue", "spectrometry", "측정", "분석", "検査", "残余", "hiss", "pressure"]
    },
    "gavel_thud": {
        "filename": "gavel_thud.mp3",
        "category": "PERCUSSION_IMPACT",
        "description": "Judicial wooden gavel striking sound block",
        "keywords": ["gavel", "judge", "búa", "scales", "justice", "thẩm phán", "裁判", "判決", "판사", "법원", "verdict", "court"]
    },
    "marker_stroke": {
        "filename": "marker_stroke.mp3",
        "category": "MARKER_GRAPHIC",
        "description": "Felt tip highlighter pen squeak / investigative marker strike",
        "keywords": ["marker", "highlight", "strike", "pen", "ink", "bút", "vạch", "형광펜", "마커", "蛍光ペン", "線"]
    },
    "node_pop": {
        "filename": "node_pop.mp3",
        "category": "DIGITAL_NETWORK",
        "description": "Tactile bubble pop for relationship graph / conspiratorial node appearance",
        "keywords": ["node", "network", "bubble", "pop", "graph", "mạng lưới", "mắt xích", "노드", "네트워크", "ネットワーク"]
    },
    "paper_crease_snap": {
        "filename": "paper_crease_snap.mp3",
        "category": "PAPER_TACTILE",
        "description": "Crisp paper folding or heavy cardstock crease snapping open",
        "keywords": ["dossier", "contract", "agreement", "binder", "ledger", "book", "hợp đồng", "sổ sách", "hồ sơ", "계약", "장부", "契約", "帳簿", "crease", "fold"]
    },
    "paper_page_turn": {
        "filename": "paper_page_turn.mp3",
        "category": "PAPER_TACTILE",
        "description": "Corner dog-ear peel or single dossier page turning",
        "keywords": ["docket", "memo", "confidential", "secret", "whistleblower", "dog-ear", "peel", "cáo trạng", "khởi tố", "mật", "bóc tách", "기소", "고발", "비밀", "内部告発", "page", "turn"]
    },
    "paper_rustle": {
        "filename": "paper_rustle.mp3",
        "category": "PAPER_TACTILE",
        "description": "General paper shuffling / desk document movement",
        "keywords": ["paper", "rustle", "document", "sheet", "giấy", "tài liệu", "서류", "종이", "書類", "紙"]
    },
    "paper_slide": {
        "filename": "paper_slide.mp3",
        "category": "PAPER_TACTILE",
        "description": "Smooth slide of document across investigative desk",
        "keywords": ["slide", "glide", "push", "trượt", "đẩy", "슬라이드", "밀다", "スライド"]
    },
    "sonar_ping": {
        "filename": "sonar_ping.mp3",
        "category": "INSTRUMENT_METER",
        "description": "Deep sonar sweep / radar ping for intelligence reconnaissance",
        "keywords": ["sonar", "radar", "ping", "recon", "satellite", "rada", "trinh sát", "레이더", "소나", "ソナー", "探知"]
    },
    "stamp_impact": {
        "filename": "stamp_impact.mp3",
        "category": "PERCUSSION_IMPACT",
        "description": "Official rubber stamp imprint sound (medium tactile)",
        "keywords": ["stamp", "seal", "imprint", "mộc", "dấu", "도장", "날인", "印鑑", "検印"]
    },
    "stamp_slam": {
        "filename": "stamp_slam.mp3",
        "category": "PERCUSSION_IMPACT",
        "description": "Authoritative heavy seal slam (e.g. red hanko, rejection stamp)",
        "keywords": ["slam", "red stamp", "rejected", "bác bỏ", "đóng dấu đỏ", "반려", "거부", "赤印", "却下"]
    }
}


def get_canonical_sfx_list() -> List[str]:
    """Trả về danh sách toàn bộ các foley cue chuẩn trong hệ thống."""
    return list(CANONICAL_SFX_REGISTRY.keys())


def is_valid_sfx(cue: Optional[str]) -> bool:
    """Kiểm tra cue có thuộc CANONICAL_SFX_REGISTRY không (hỗ trợ cả slug lẫn file name)."""
    if not cue:
        return False
    clean = str(cue).strip().replace("sfx/", "").replace(".mp3", "")
    return clean in CANONICAL_SFX_REGISTRY


def get_sfx_filename(cue: str) -> str:
    """Lấy tên file vật lý tương ứng với cue. Ném ValueError nếu cue không hợp lệ."""
    clean = str(cue).strip().replace("sfx/", "").replace(".mp3", "")
    if clean not in CANONICAL_SFX_REGISTRY:
        raise ValueError(
            f"Invalid SFX cue '{cue}'. Must be one of {get_canonical_sfx_list()}."
        )
    return CANONICAL_SFX_REGISTRY[clean]["filename"]


def resolve_semantic_foley(narr: str, fg_key: Optional[str], hero_index: int = 0) -> str:
    """Ánh xạ ngữ nghĩa đa ngôn ngữ (EN, JP, KR, VN) một cách tất định vào CANONICAL_SFX_REGISTRY.
    CẤM sinh bất kỳ chuỗi cue nào nằm ngoài CANONICAL_SFX_REGISTRY.
    """
    n_low = (narr or "").lower()
    fg_low = (fg_key or "").lower()
    combined = f"{n_low} {fg_low}"

    # 1. Gavel / Justice / Court
    if any(k in combined for k in CANONICAL_SFX_REGISTRY["gavel_thud"]["keywords"]):
        return "gavel_thud"

    # 2. Gauge / Chemical / Spectrometry / Lab
    if any(k in combined for k in CANONICAL_SFX_REGISTRY["gauge_needle_hiss"]["keywords"]):
        return "gauge_needle_hiss"

    # 3. Sonar / Radar / Satellite Recon
    if any(k in combined for k in CANONICAL_SFX_REGISTRY["sonar_ping"]["keywords"]):
        return "sonar_ping"

    # 4. Stamp / Seal / Ink mark
    if any(k in combined for k in CANONICAL_SFX_REGISTRY["stamp_slam"]["keywords"]):
        return "stamp_slam"
    if any(k in combined for k in CANONICAL_SFX_REGISTRY["stamp_impact"]["keywords"]):
        return "stamp_impact"

    # 5. Node / Network / Graph pop
    if any(k in combined for k in CANONICAL_SFX_REGISTRY["node_pop"]["keywords"]):
        return "node_pop"

    # 6. Counter / Stopwatch / Rollup
    if any(k in combined for k in CANONICAL_SFX_REGISTRY["counter_tick"]["keywords"]):
        return "counter_tick"

    # 7. Dossier / Contract / Binder
    if any(k in combined for k in CANONICAL_SFX_REGISTRY["paper_crease_snap"]["keywords"]):
        return "paper_crease_snap"

    # 8. Docket / Memo / Confidential / Dog-ear
    if any(k in combined for k in CANONICAL_SFX_REGISTRY["paper_page_turn"]["keywords"]):
        return "paper_page_turn"

    # 9. Invoice / Bill / Damage / Table Drop
    if any(k in combined for k in CANONICAL_SFX_REGISTRY["document_table_thud"]["keywords"]):
        return "document_table_thud"

    # 10. Slide
    if any(k in combined for k in CANONICAL_SFX_REGISTRY["paper_slide"]["keywords"]):
        return "paper_slide"

    # Deterministic Tactile Paper Cycle for generic scenes (Rule 128)
    cycle = hero_index % 3
    if cycle == 0:
        return "paper_page_turn"
    elif cycle == 1:
        return "document_table_thud"
    else:
        return "paper_crease_snap"


def verify_physical_sfx_assets(sfx_dir: Optional[Path] = None) -> Tuple[bool, List[str]]:
    """Kiểm toán đối kháng vật lý (Physical Asset Parity Gate):
    Xác nhận 100% các file âm thanh trong CANONICAL_SFX_REGISTRY thực sự tồn tại trên đĩa và dung lượng > 1KB.
    """
    target_dir = sfx_dir or SFX_DIR
    missing = []
    for cue, meta in CANONICAL_SFX_REGISTRY.items():
        expected_file = target_dir / meta["filename"]
        if not expected_file.exists():
            missing.append(f"Missing file: {meta['filename']} for cue '{cue}'")
        elif expected_file.stat().st_size < 1000:
            missing.append(f"Corrupt/empty file (<1KB): {meta['filename']} ({expected_file.stat().st_size} bytes)")

    return (len(missing) == 0, missing)
