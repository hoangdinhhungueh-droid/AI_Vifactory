#!/usr/bin/env python3
"""Enrich remotion_props with Stat Cards, Act Badges, Clean Studio BGM, and render Full Remotion Master Video."""
import asyncio
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, '/root/video_factory')
sys.path.insert(0, '/root/video_factory/scripts')

from app.services.mpt_ported.tts_edge import synthesize_with_fallback

EPISODE_ID = "en-enron-ep006"
OUT_DIR = Path(f"/var/vf/episodes/{EPISODE_ID}")
PROPS_PATH = OUT_DIR / "remotion_props.json"
PULLED_DIR = Path(f"/root/video_factory/remotion/public/pulled/{EPISODE_ID}")
TEMP_DIR = Path("/tmp/vf/ep006_pro_render")
CLEAN_BGM = Path("/root/video_factory/assets/bgm/calm_004_fs725597.mp3")

PULLED_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# Copy all images
for img_name in [
    "fg_ken_lay.png", "fg_jeff_skilling.png", "fg_andy_fastow.png",
    "fg_sherron_watkins.png", "fg_auditor.png", "fg_sec_investigator.png",
    "bg_arc01_enron_hq.jpg", "bg_arc02_accounting_vault.jpg", "bg_arc02_boardroom.jpg",
    "bg_arc03_regulatory_records.jpg", "bg_arc04_market_crash.jpg", "bg_arc05_courthouse.jpg"
]:
    src = OUT_DIR / "images" / img_name
    dst = PULLED_DIR / img_name
    if src.exists():
        shutil.copyfile(src, dst)

FG_ASSIGNMENTS = [
    # Scene 00 - 05: Arc 1 Hook
    ("fg_ken_lay.png", "left"),
    ("fg_jeff_skilling.png", "right"),
    ("fg_auditor.png", "left"),
    ("fg_ken_lay.png", "right"),
    ("fg_auditor.png", "left"),
    ("fg_ken_lay.png", "right"),
    # Scene 06 - 20: Arc 2 Rise
    ("fg_jeff_skilling.png", "left"),
    ("fg_ken_lay.png", "right"),
    ("fg_jeff_skilling.png", "left"),
    ("fg_jeff_skilling.png", "right"),
    ("fg_andy_fastow.png", "left"),
    ("fg_jeff_skilling.png", "right"),
    ("fg_ken_lay.png", "left"),
    ("fg_jeff_skilling.png", "right"),
    ("fg_andy_fastow.png", "left"),
    ("fg_auditor.png", "right"),
    ("fg_auditor.png", "left"),
    ("fg_andy_fastow.png", "right"),
    ("fg_jeff_skilling.png", "left"),
    ("fg_ken_lay.png", "right"),
    ("fg_andy_fastow.png", "left"),
    # Scene 21 - 33: Arc 3 Mechanism
    ("fg_andy_fastow.png", "right"),
    ("fg_auditor.png", "left"),
    ("fg_sherron_watkins.png", "right"),
    ("fg_andy_fastow.png", "left"),
    ("fg_auditor.png", "right"),
    ("fg_andy_fastow.png", "left"),
    ("fg_sherron_watkins.png", "right"),
    ("fg_andy_fastow.png", "left"),
    ("fg_auditor.png", "right"),
    ("fg_sherron_watkins.png", "left"),
    ("fg_jeff_skilling.png", "right"),
    ("fg_sec_investigator.png", "left"),
    ("fg_ken_lay.png", "right"),
    # Scene 34 - 44: Arc 4 Collapse
    ("fg_jeff_skilling.png", "left"),
    ("fg_auditor.png", "right"),
    ("fg_auditor.png", "left"),
    ("fg_auditor.png", "right"),
    ("fg_ken_lay.png", "left"),
    ("fg_sec_investigator.png", "right"),
    ("fg_auditor.png", "left"),
    ("fg_ken_lay.png", "right"),
    ("fg_sherron_watkins.png", "left"),
    ("fg_sec_investigator.png", "right"),
    ("fg_sec_investigator.png", "left"),
    # Scene 45 - 54: Arc 5 Payoff
    ("fg_ken_lay.png", "right"),
    ("fg_jeff_skilling.png", "left"),
    ("fg_sec_investigator.png", "right"),
    ("fg_auditor.png", "left"),
    ("fg_andy_fastow.png", "right"),
    ("fg_ken_lay.png", "left"),
    ("fg_jeff_skilling.png", "right"),
    ("fg_auditor.png", "left"),
    ("fg_ken_lay.png", "right"),
    ("fg_sec_investigator.png", "left")
]

STAT_MAP = {
    0: ("$63 BILLION", "LARGEST CHAPTER 11 BANKRUPTCY IN US HISTORY", "THE $63B COLLAPSE"),
    1: ("$80 → <$1", "STOCK COLLAPSE & RETIREMENT SAVINGS LOSS", "SHARE PRICE EVAPORATION"),
    5: ("<$1.00", "FINAL VERDICT ON RISK CONCEALMENT", "THE FINAL VERDICT"),
    6: ("ENERGY MARKET", "1985 DEREGULATION & GAS BANK INNOVATION", "FOUNDING & VISION"),
    12: ("$90.75", "ENRON ALL-TIME HIGH PEAK (AUG 2000)", "THE PEAK VALUATION"),
    15: ("MARK-TO-MARKET", "HYPOTHETICAL LONG-TERM PROFITS BOOKED ON DAY ONE", "PAPER ACCOUNTING"),
    19: ("GROWTH PRESSURE", "CONSTANT NEED FOR BOLDER PROJECTIONS", "THE EXPANSION LOOP"),
    21: ("SPE NETWORK", "SPECIAL PURPOSE ENTITIES: CHEWCO & LJM", "DEBT CONCEALMENT"),
    23: ("NO CASH FLOW", "THE ILLUSION OF SOLVENCY & REVENUE GAP", "THE REALITY GAP"),
    26: ("CIRCULAR HEDGE", "ENRON STOCK DEFENDING ENRON BALANCE SHEET", "THE FATAL TRAP"),
    29: ("-$1.2 BILLION", "REDUCTION IN SHAREHOLDERS EQUITY (OCT 2001)", "THE RECKONING"),
    30: ("-$600 MILLION", "PROFIT RESTATEMENT DATING BACK TO 1997", "SEC RESTATEMENT"),
    34: ("CREDIT DOWNGRADE", "TRADING PARTNERS DEMAND COLLATERAL", "RUN ON CONFIDENCE"),
    39: ("<$1.00 / SHARE", "CHAPTER 11 BANKRUPTCY (DEC 2, 2001)", "TOTAL INSOLVENCY"),
    43: ("400+ BOXES", "EVIDENCE RECOVERED BY FBI TASK FORCE", "CRIMINAL INVESTIGATION"),
    45: ("GUILTY VERDICT", "KEN LAY & JEFF SKILLING CONVICTED OF FRAUD", "FEDERAL JURY RULING"),
    48: ("OPAQUE BUSINESS", "COMPLEXITY WITHOUT SCRUTINY IS DANGER", "GOVERNANCE LESSON"),
    54: ("THE LESSON", "WHO CARRIES THE RISK WHEN CONFIDENCE FAILS?", "LEGACY OF ENRON"),
}

def step1_prepare_props():
    print("=== [STEP 1/5] Enriching remotion_props.json with Stat Cards & 100% FG ===")
    with open(PROPS_PATH, encoding='utf-8') as f:
        props = json.load(f)
        
    scenes = props.get('scenes', [])
    for i, s in enumerate(scenes):
        fg_file, pos = FG_ASSIGNMENTS[i]
        s['foreground'] = f"pulled/{EPISODE_ID}/{fg_file}"
        s['foregroundPosition'] = pos
        s['foregroundFadeFrames'] = 15
        
        if i in STAT_MAP:
            s['statValue'] = STAT_MAP[i][0]
            s['statLabel'] = STAT_MAP[i][1]
            s['speakerTag'] = STAT_MAP[i][2]
        else:
            s['statValue'] = None
            s['statLabel'] = None
            s['speakerTag'] = (
                "CASE OVERVIEW // THE COLLAPSE" if i <= 5 else
                "GROWTH & INNOVATION // MARK-TO-MARKET" if i <= 20 else
                "FINANCIAL ENGINEERING // SPEs & HEDGING" if i <= 33 else
                "THE UNRAVELING // LIQUIDITY CRISIS" if i <= 44 else
                "TRIAL & VERDICT // MODERN REGULATION"
            )
            
    with open(PROPS_PATH, 'w', encoding='utf-8') as f:
        json.dump(props, f, indent=2, ensure_ascii=False)
        
    print(f"Enriched {len(scenes)} scenes with 100% FG and {len(STAT_MAP)} Stat Cards! ✅")

def step2_build_clean_soundtrack():
    print("=== [STEP 2/5] Building Clean Studio BGM Soundtrack (Zero Crackle) ===")
    raw_voiceover = Path("/tmp/vf/ep006_audio_build/voiceover_concat.wav")
    norm_voiceover = TEMP_DIR / "voiceover_norm.wav"
    master_soundtrack = TEMP_DIR / "master_soundtrack_clean.mp3"
    
    # 1. Normalize voiceover to -14 LUFS
    subprocess.run([
        'ffmpeg', '-y', '-i', str(raw_voiceover),
        '-af', 'loudnorm=I=-14:LRA=11:TP=-1.5',
        '-ar', '48000', '-ac', '2',
        str(norm_voiceover)
    ], check=True, capture_output=True)
    
    # 2. Mix with Clean Studio BGM (calm_004_fs725597.mp3 - 300s looped, volume=0.065 / -24dB ducking)
    print(f"Mixing Clean Studio BGM: {CLEAN_BGM}")
    subprocess.run([
        'ffmpeg', '-y',
        '-i', str(norm_voiceover),
        '-stream_loop', '-1', '-i', str(CLEAN_BGM),
        '-filter_complex', '[1:a]volume=0.06,atrim=0:529.2[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2',
        '-ar', '48000', '-ac', '2', '-b:a', '192k',
        str(master_soundtrack)
    ], check=True, capture_output=True)
    
    print(f"Clean Master Soundtrack ready: {master_soundtrack} ✅")
    return master_soundtrack

def step3_render_remotion():
    print("=== [STEP 3/5] Rendering Remotion Full Video (with Effects + Top Progress Bar + Stat Cards) ===")
    silent_video = OUT_DIR / "twolayer_silent_effects.mp4"
    if silent_video.exists():
        silent_video.unlink()
        
    remotion_bin = "/root/video_factory/remotion/node_modules/.bin/remotion"
    cmd = [
        remotion_bin, "render",
        "src/index.tsx", "TwoLayerEpisode",
        str(silent_video),
        f"--props={PROPS_PATH}",
        "--log=error",
        "--concurrency=3"
    ]
    p = subprocess.run(cmd, cwd="/root/video_factory/remotion", capture_output=True, text=True)
    if p.returncode != 0:
        print("Remotion Render Error:", p.stderr, file=sys.stderr)
        sys.exit(1)
        
    print(f"Rendered Remotion silent video: {silent_video} ({silent_video.stat().st_size / (1024*1024):.1f} MB) ✅")
    return silent_video

def step4_mux_and_audit(silent_video, master_soundtrack):
    print("=== [STEP 4/5] Muxing Master Video + Audio ===")
    master_video = OUT_DIR / "master_video_pro.mp4"
    
    subprocess.run([
        'ffmpeg', '-y',
        '-i', str(silent_video),
        '-i', str(master_soundtrack),
        '-map', '0:v:0',
        '-map', '1:a:0',
        '-c:v', 'copy',
        '-c:a', 'aac', '-b:a', '192k',
        '-shortest',
        str(master_video)
    ], check=True, capture_output=True)
    
    # Audit Audio
    p = subprocess.run(
        ['ffmpeg', '-i', str(master_video), '-filter:a', 'volumedetect', '-f', 'null', '/dev/null'],
        capture_output=True, text=True
    )
    for line in p.stderr.split('\n'):
        if 'mean_volume' in line or 'max_volume' in line:
            print("  Audio Check:", line.strip())
            
    if silent_video.exists():
        silent_video.unlink()
        
    print(f"🎬 MASTER VIDEO PRO WITH REMOTION EFFECTS IS READY: {master_video} ({master_video.stat().st_size / (1024*1024):.1f} MB) ✅")
    return master_video

def main():
    step1_prepare_props()
    soundtrack = step2_build_clean_soundtrack()
    silent = step3_render_remotion()
    step4_mux_and_audit(silent, soundtrack)
    print("\n🎉 ALL PIPELINE STEPS COMPLETE SUCCESSFULLY!")

if __name__ == "__main__":
    main()
