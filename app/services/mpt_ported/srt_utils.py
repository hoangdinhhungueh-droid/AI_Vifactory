"""
MPT-G3-5 - SRT timestamp utils. FULLY IMPLEMENTED.
"""
def ms_to_srt_ts(ms: int) -> str:
    h = ms // 3_600_000; ms %= 3_600_000
    m = ms // 60_000;    ms %= 60_000
    s = ms // 1_000;     ms %= 1_000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
def srt_ts_to_ms(ts: str) -> int:
    ts = ts.replace(",",".")
    h, m, s_ms = ts.split(":")
    s, frac = s_ms.split(".")
    return int(h)*3_600_000 + int(m)*60_000 + int(s)*1_000 + int(frac)
