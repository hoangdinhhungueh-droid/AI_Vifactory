#!/usr/bin/env python3
import sys, os, subprocess, re, argparse

def main():
    parser = argparse.ArgumentParser(description="B9 Quality Probe (LUFS & True Peak & Video Stream)")
    parser.add_argument("--episode", required=True, help="Episode ID")
    args = parser.parse_args()
    
    ep_dir = f"/var/vf/episodes/{args.episode}"
    video_file = f"{ep_dir}/final_169.mp4"
    if not os.path.exists(video_file):
        print(f"FAILED: Video {video_file} not found.")
        sys.exit(1)
        
    print(f"Running B9 Quality Probe on {video_file}...")
    
    # 1. Video Integrity (1080p, 30fps)
    probe_cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate", "-of", "default=noprint_wrappers=1:nokey=1", video_file]
    try:
        out = subprocess.check_output(probe_cmd).decode().strip().split('\n')
        width, height, fps_raw = out[0], out[1], out[2]
        fps = round(eval(fps_raw)) if '/' in fps_raw else float(fps_raw)
        if width != "1920" or height != "1080" or fps != 30:
            print(f"FAILED: Video stream invalid. Expected 1920x1080 30fps, got {width}x{height} {fps}fps.")
            sys.exit(1)
    except Exception as e:
        print(f"FAILED: Video probe error - {e}")
        sys.exit(1)
        
    # 2. EBU R128 LUFS & True Peak
    lufs_cmd = f'ffmpeg -nostats -i "{video_file}" -filter_complex ebur128=peak=true -f null - 2>&1'
    try:
        lufs_out = subprocess.check_output(lufs_cmd, shell=True).decode()
        integrated_lufs = re.search(r'Integrated loudness:.*?I:\s+([-0-9.]+)\s+LUFS', lufs_out, re.DOTALL)
        true_peak = re.search(r'True peak:.*?Peak:\s+([-0-9.]+)\s+dBFS', lufs_out, re.DOTALL)
        
        if not integrated_lufs or not true_peak:
            print("FAILED: Could not parse EBU R128 output from FFmpeg.")
            sys.exit(1)
            
        i_lufs = float(integrated_lufs.group(1))
        tp_dbfs = float(true_peak.group(1))
        
        print(f"LUFS: {i_lufs} (Target: -14 +/- 2)")
        print(f"True Peak: {tp_dbfs} dBTP (Target: < -1.0 dBTP)")
        
        if not (-16.0 <= i_lufs <= -12.0):
            print(f"FAILED: LUFS {i_lufs} is outside acceptable range (-14 +/- 2).")
            sys.exit(1)
            
        if tp_dbfs >= -1.0:
            print(f"FAILED: True Peak {tp_dbfs} is too high (must be < -1.0).")
            sys.exit(1)
            
        print("B9 Quality Probe PASSED ✅")
    except Exception as e:
        print(f"FAILED: LUFS probe error - {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
