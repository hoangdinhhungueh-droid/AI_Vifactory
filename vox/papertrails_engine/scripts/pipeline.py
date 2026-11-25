#!/usr/bin/env python3
"""Voice -> measured transcript -> editable Papertrails timeline -> MP4.

Core planning uses only Python's standard library. ASR is optional, CPU-local,
and requires faster-whisper. A timed JSON/SRT bypasses the ASR dependency.
The starter plan is explicitly rule-based; the calling agent directs the film.
"""
import argparse
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
import unicodedata
from array import array
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(args):
    return subprocess.run([str(a) for a in args], check=True, capture_output=True, text=True, encoding='utf-8')


def tool(name):
    found = shutil.which(name)
    if not found:
        raise ValueError(f'Missing {name}. Install it and put it on PATH; see references/setup.md.')
    return found


def audio_info(path):
    path = Path(path).expanduser().resolve(strict=True)
    if not path.is_file():
        raise ValueError('Audio input must be a local file.')
    data = json.loads(run([tool('ffprobe'), '-v', 'error', '-show_format', '-show_streams', '-of', 'json', path]).stdout)
    streams = [s for s in data.get('streams', []) if s.get('codec_type') == 'audio']
    if not streams:
        raise ValueError(f'No audio stream in {path.name}.')
    duration = float(data.get('format', {}).get('duration') or streams[0].get('duration', 0))
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError('Audio duration must be finite and positive.')
    return {'path': str(path), 'duration': duration, 'codec': streams[0].get('codec_name'),
            'sampleRate': int(streams[0].get('sample_rate', 0))}


def number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{label} must be a finite number.')
    return float(value)


def normalize_transcript(data, duration):
    segments = data.get('segments') if isinstance(data, dict) else data
    if not isinstance(segments, list) or not segments:
        raise ValueError('Transcript needs nonempty timed segments: [{start, end, text}]. Plain text has no measured timings.')
    clean = []
    previous_end = 0.0
    for i, segment in enumerate(segments):
        if not isinstance(segment, dict):
            raise ValueError(f'Segment {i} is not an object.')
        start = number(segment.get('start'), f'segment {i} start')
        end = number(segment.get('end'), f'segment {i} end')
        text = segment.get('text')
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f'Segment {i} has empty text.')
        if start < 0 or end <= start or end > duration + .2 or start < previous_end - .02:
            raise ValueError(f'Segment {i}: invalid, overlapping, or out-of-audio timestamps ({start}, {end}); audio={duration:.3f}s.')
        start = max(start, previous_end)
        end = min(end, duration)
        if start >= end:
            raise ValueError(f'Segment {i} lies outside the measured audio.')
        item = {'start': start, 'end': end, 'text': ' '.join(text.split())}
        words = segment.get('words', [])
        if words:
            if not isinstance(words, list):
                raise ValueError(f'Segment {i} words must be a list.')
            item['words'] = []
            prev = start
            for word in words:
                a = number(word.get('start'), 'word start')
                b = number(word.get('end'), 'word end')
                token = word.get('word', word.get('text', ''))
                if not isinstance(token, str) or not token.strip() or a < start - .02 or b > end + .2 or b < a or a < prev - .02:
                    raise ValueError(f'Segment {i} has invalid word timestamps.')
                a, b = max(start, a, prev), min(end, b)
                if b <= a:
                    # Whisper occasionally gives punctuation a zero-length token.
                    if item['words']:
                        item['words'][-1]['word'] += token
                    else:
                        raise ValueError(f'Segment {i} starts with a zero-length word.')
                    continue
                item['words'].append({'word': token.strip(), 'start': a, 'end': b})
                prev = b
        clean.append(item)
        previous_end = end
    return clean


def read_transcript(path, duration):
    path = Path(path)
    if path.suffix.lower() == '.json':
        return normalize_transcript(json.loads(path.read_text(encoding='utf-8-sig')), duration)
    if path.suffix.lower() != '.srt':
        raise ValueError('Use timed .json or .srt, not a plain text script with guessed timing.')
    text = path.read_text(encoding='utf-8-sig').replace('\r\n', '\n').strip()
    pattern = re.compile(r'(\d+):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d+):(\d{2}):(\d{2})[,.](\d{3})')
    segments = []
    for block in re.split(r'\n\s*\n', text):
        lines = block.strip().splitlines()
        timing = next((i for i, line in enumerate(lines) if '-->' in line), None)
        if timing is None:
            raise ValueError('Malformed SRT: block has no timing arrow.')
        match = pattern.fullmatch(lines[timing].strip())
        if not match:
            raise ValueError('Malformed SRT timestamp.')
        values = list(map(int, match.groups()))
        for base in (0, 4):
            if values[base + 1] > 59 or values[base + 2] > 59:
                raise ValueError('Invalid SRT minute/second.')
        def seconds(v):
            return v[0] * 3600 + v[1] * 60 + v[2] + v[3] / 1000
        segments.append({'start': seconds(values[:4]), 'end': seconds(values[4:]), 'text': ' '.join(lines[timing + 1:])})
    return normalize_transcript(segments, duration)


def transcribe(audio, language, model):
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise ValueError('ASR unavailable. Install requirements-asr.txt into a Python 3.12 venv, then run its Python; or supply --transcript timed.json/captions.srt. No video was fabricated.') from exc
    recognizer = WhisperModel(model, device='cpu', compute_type='int8', download_root=str(ROOT / '.cache' / 'whisper'))
    results, info = recognizer.transcribe(str(audio), language=None if language == 'auto' else language,
                                         word_timestamps=True, vad_filter=True, beam_size=5)
    segments = []
    for seg in results:
        if not seg.text.strip():
            continue
        segments.append({'start': seg.start, 'end': seg.end, 'text': seg.text.strip(),
                         'words': [{'word': w.word, 'start': w.start, 'end': w.end} for w in (seg.words or [])]})
    return {'segments': segments, 'language': info.language, 'backend': 'faster-whisper', 'model': model}


def plain(text):
    text = unicodedata.normalize('NFKD', text.lower()).replace('đ', 'd')
    return ''.join(c for c in text if not unicodedata.combining(c))


# Priority matters: compound subjects precede words they contain (nha may vs nha).
SUBJECTS = [
    ('factory', 'heartland', ['nha may', 'factory', 'industry', 'san xuat', 'cong nghiep']),
    ('chart', 'heartland', ['bieu do', 'chart', 'growth', 'tang truong', 'percent', 'phan tram']),
    ('coin', 'heartland', ['tien', 'money', 'savings', 'saving', 'cost', 'chi phi', 'do la', 'ngan hang', 'dollar', 'kinh te', 'economy']),
    ('clock', 'heartland', ['thoi gian', 'dong ho', 'clock', 'time', 'deadline', 'hour', 'minute', 'gio phut']),
    ('book', 'heartland', ['hoc', 'sach', 'book', 'learn', 'school', 'education', 'knowledge', 'kien thuc']),
    ('globe', 'heartland', ['the gioi', 'trai dat', 'world', 'earth', 'planet', 'global']),
    ('bridge', 'heartland', ['cau', 'bridge', 'crossing', 'qua song']),
    ('forest', 'pinewood', ['rung', 'forest', 'woodland', 'nature', 'thien nhien']),
    ('tree', 'blossom', ['cay', 'tree', 'garden', 'vuon', 'flower', 'hoa no']),
    ('mountain', 'snow', ['tuyet', 'snow', 'mountain', 'nui', 'winter', 'mua dong']),
    ('water', 'heartland', ['song', 'bien', 'ocean', 'river', 'water', 'nuoc', 'lake', 'ho nuoc']),
    ('sun', 'desert', ['sa mac', 'desert', 'sun', 'mat troi', 'nang', 'heat']),
    ('moon', 'pinewood', ['moon', 'trang', 'night', 'ban dem', 'midnight']),
    ('village', 'heartland', ['village', 'lang', 'thi tran', 'town', 'city', 'thanh pho']),
    ('house', 'heartland', ['nha', 'home', 'house', 'family', 'gia dinh']),
    ('people', 'heartland', ['nguoi', 'people', 'team', 'nhan vien', 'ban be', 'friend']),
]


def subject_for(text):
    text = ' ' + re.sub(r'[^a-z0-9]+', ' ', plain(text)) + ' '
    for prop, biome, keys in SUBJECTS:
        if any(' ' + key + ' ' in text for key in keys):
            return prop, biome
    return 'book', 'heartland'


def caption_from(group):
    # Keep measured word timings so the renderer can highlight the word being spoken.
    return {'start': group[0]['start'], 'end': group[-1]['end'], 'text': ' '.join(w['word'] for w in group),
            'words': [{'word': w['word'], 'start': w['start'], 'end': w['end']} for w in group]}


def split_captions(segments, max_seconds):
    captions = []
    for seg in segments:
        words = seg.get('words') or []
        if words:
            group = []
            for word in words:
                if group and (word['end'] - group[0]['start'] > min(3.5, max_seconds) or len(group) >= 8):
                    captions.append(caption_from(group))
                    group = []
                group.append(word)
                if len(group) >= 3 and re.search(r'[,.;:!?][\"\'’”)]*$', word['word']):
                    captions.append(caption_from(group))
                    group = []
            if group:
                captions.append(caption_from(group))
        else:
            # Preserve measured sentence timing. Never claim forced word alignment.
            captions.append({key: seg[key] for key in ('start', 'end', 'text')})
    return captions


def build_timeline(segments, duration, audio, orientation='landscape', fps=30, seed=42, max_seconds=5):
    segments = normalize_transcript(segments, duration)
    if orientation not in ('landscape', 'portrait'):
        raise ValueError('format must be landscape or portrait')
    if isinstance(fps, bool) or not isinstance(fps, int) or fps < 1 or fps > 60:
        raise ValueError('fps must be an integer from 1 to 60')
    if max_seconds <= 0 or not math.isfinite(max_seconds):
        raise ValueError('max shot seconds must be positive')
    captions = split_captions(segments, max_seconds)
    beats = []
    for seg in segments:
        if seg['end'] - seg['start'] > max_seconds and seg.get('words'):
            # Reuse measured word groups, not guessed equal-duration cuts.
            beats.extend(split_captions([seg], max_seconds))
        else:
            beats.append({key: seg[key] for key in ('start', 'end', 'text')})
    width, height = (1920, 1080) if orientation == 'landscape' else (1080, 1920)
    cameras = ['wide', 'close', 'orbit', 'wide', 'top']
    scenes = []
    for i, beat in enumerate(beats):
        prop, biome = subject_for(beat['text'])
        title = ' '.join(beat['text'].split()[:6]).strip(' .,!?;:')
        scenes.append({'id': f'shot-{i + 1:03}', 'start': 0 if i == 0 else beat['start'],
                       'end': beats[i + 1]['start'] if i + 1 < len(beats) else duration,
                       'narration': beat['text'], 'title': title, 'biome': biome,
                       'night': prop == 'moon', 'action': 'reveal' if i % 2 == 0 else 'idle',
                       'prop': prop, 'camera': cameras[i % len(cameras)], 'color': '#d79a45',
                       'visual': f'Paper cut-out {prop}: animate the subject revealing itself as this sentence is spoken. Agent must refine literal staging to the narration.'})
    return {'version': 1, 'width': width, 'height': height, 'fps': fps, 'seed': seed,
            'duration': duration, 'audio': str(audio), 'captions': captions, 'scenes': scenes,
            'timing': {'mode': 'word' if all(s.get('words') for s in segments) else 'segment',
                       'note': 'Timestamps measured from audio/ASR or supplied timed transcript; never fabricated from plain text.'},
            'direction': {'status': 'starter-needs-agent-review', 'planner': 'local bilingual keyword rules, not a semantic AI model',
                          'requirement': 'The calling agent must read transcript and refine each shot to its actual narration before final render. Add custom scene props when needed; never represent unmeasured values as data.'}}


def srt_time(seconds):
    ms = round(seconds * 1000)
    hours, ms = divmod(ms, 3600000)
    minutes, ms = divmod(ms, 60000)
    sec, ms = divmod(ms, 1000)
    return f'{hours:02}:{minutes:02}:{sec:02},{ms:03}'


def save_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def prepare(args):
    audio = Path(args.audio).expanduser().resolve(strict=True)
    project = Path(args.project).expanduser().resolve()
    if project.exists() and any(project.iterdir()):
        raise ValueError('Project folder is not empty; choose a new folder to preserve approved edits.')
    info = audio_info(audio)
    if args.transcript:
        transcript = {'segments': read_transcript(args.transcript, info['duration']), 'backend': 'user-supplied-timed-transcript'}
    else:
        try:
            transcript = transcribe(audio, args.language, args.model)
            transcript['segments'] = normalize_transcript(transcript, info['duration'])
        except Exception as exc:
            raise ValueError(f'Speech recognition failed: {exc}. No project or fabricated transcript was created. Check the ASR environment/network, or supply a measured SRT/JSON.') from exc
    timeline = build_timeline(transcript['segments'], info['duration'], '', args.format, args.fps, args.seed, args.max_shot_seconds)
    # No project is created until input/ASR has succeeded. Keep the source voice untouched.
    project.mkdir(parents=True, exist_ok=True)
    media = project / 'media'
    media.mkdir(exist_ok=True)
    copied = media / ('voice' + audio.suffix.lower())
    shutil.copy2(audio, copied)
    timeline['audio'] = str(copied.resolve())
    timeline['source'] = {'originalName': audio.name, 'audioSha256': hashlib.sha256(copied.read_bytes()).hexdigest(),
                          'asr': {k: v for k, v in transcript.items() if k != 'segments'}}
    save_json(project / 'transcript.json', transcript)
    save_json(project / 'timeline.json', timeline)
    (project / 'transcript.txt').write_text('\n'.join(f"[{s['start']:.3f}-{s['end']:.3f}] {s['text']}" for s in transcript['segments']) + '\n', encoding='utf-8')
    (project / 'captions.srt').write_text('\n'.join(f"{i + 1}\n{srt_time(s['start'])} --> {srt_time(s['end'])}\n{s['text']}\n" for i, s in enumerate(timeline['captions'])), encoding='utf-8')
    (project / 'DIRECTION.md').write_text('# Shot direction\n\nStatus: starter-needs-agent-review.\n\nRead transcript.txt. Edit timeline.json to make each shot show the sentence being spoken, not just a metaphor or a walk loop. Add concrete props for unsupported subjects. Preserve measured timing, source voice, and facts. Mark direction.status as agent-reviewed only after checking every scene.\n', encoding='utf-8')
    return {'project': str(project), 'timeline': str(project / 'timeline.json'), 'duration': info['duration'],
            'scenes': len(timeline['scenes']), 'timing': timeline['timing']['mode'], 'direction': timeline['direction']['status']}


def soundtrack_samples(video, source, duration):
    """Compare decoded waveform windows at three real times, allowing codec jitter.

    This is a sampled identity/sync check, not a full-recording ASR audit.
    """
    def samples(path, start):
        result = subprocess.run([tool('ffmpeg'), '-v', 'error', '-i', str(path), '-ss', str(start),
                                 '-t', str(min(1.0, duration - start)), '-map', '0:a:0', '-vn',
                                 '-ac', '1', '-ar', '8000', '-f', 's16le', '-'], check=True, capture_output=True)
        out = array('h')
        out.frombytes(result.stdout)
        if sys.byteorder != 'little':
            out.byteswap()
        return list(out)
    checked = []
    for start in sorted({0.0, max(0.0, duration / 2 - .5), max(0.0, duration - 1.1)}):
        a, b = samples(source, start), samples(video, start)
        n = min(len(a), len(b))
        if n < 80:
            raise ValueError('soundtrack sample is truncated')
        a, b = a[:n], b[:n]
        energy_a = sum(x * x for x in a) / n
        energy_b = sum(x * x for x in b) / n
        if energy_a < 100:
            if energy_b > 10000:
                raise ValueError('soundtrack has extra sound during source silence')
            checked.append({'at': start, 'kind': 'source-silence'})
            continue
        best = (-1.0, 0)
        max_lag = min(240, ((n - 40) // 20) * 10)
        for lag in range(-max_lag, max_lag + 1, 10):
            x = a[max(0, -lag):n - max(0, lag)]
            y = b[max(0, lag):n - max(0, -lag)]
            mx, my = sum(x) / len(x), sum(y) / len(y)
            xx = sum((v - mx) ** 2 for v in x)
            yy = sum((v - my) ** 2 for v in y)
            corr = sum((v - mx) * (w - my) for v, w in zip(x, y)) / math.sqrt(xx * yy) if xx * yy else 0
            if corr > best[0]:
                best = (corr, lag)
        if best[0] < .8:
            raise ValueError(f'voice content / soundtrack mismatch at {start:.3f}s (correlation={best[0]:.3f})')
        checked.append({'at': round(start, 3), 'correlation': round(best[0], 5), 'lagMs': best[1] / 8})
    return checked


def verify_video(path, timeline_path):
    timeline = json.loads(Path(timeline_path).read_text(encoding='utf-8'))
    data = json.loads(run([tool('ffprobe'), '-v', 'error', '-show_format', '-show_streams', '-count_frames', '-of', 'json', Path(path).resolve(strict=True)]).stdout)
    video = next((s for s in data.get('streams', []) if s.get('codec_type') == 'video'), None)
    audio = next((s for s in data.get('streams', []) if s.get('codec_type') == 'audio'), None)
    if not video or not audio:
        raise ValueError('Output needs BOTH video and original voice audio streams.')
    num, den = map(int, video['avg_frame_rate'].split('/'))
    fps = num / den
    duration = float(data['format']['duration'])
    errors = []
    if (video['width'], video['height']) != (timeline['width'], timeline['height']):
        errors.append('wrong dimensions')
    if abs(fps - timeline['fps']) > .01:
        errors.append('wrong frame rate')
    container_tolerance = .08 + 1 / fps
    if abs(duration - timeline['duration']) > container_tolerance:
        errors.append(f'video container duration differs by more than one frame ({container_tolerance:.3f}s)')
    if abs(float(audio.get('duration', duration)) - timeline['duration']) > .12:
        errors.append('voice track duration differs by more than 120ms')
    frames = int(video.get('nb_read_frames') or video.get('nb_frames') or 0)
    if abs(frames - math.ceil(timeline['duration'] * timeline['fps'])) > 1:
        errors.append('unexpected decoded frame count')
    run([tool('ffmpeg'), '-v', 'error', '-i', Path(path).resolve(), '-f', 'null', '-'])
    source_audio = Path(timeline['audio'])
    if not source_audio.is_absolute():
        source_audio = Path(timeline_path).resolve().parent / source_audio
    source_audio = source_audio.resolve(strict=True)
    expected_hash = timeline.get('source', {}).get('audioSha256')
    if expected_hash and hashlib.sha256(source_audio.read_bytes()).hexdigest() != expected_hash:
        errors.append('source voice hash changed')
    soundtrack = soundtrack_samples(Path(path).resolve(), source_audio, timeline['duration'])
    report = {'status': 'FAIL' if errors else 'PASS', 'checks': 'decode, streams, dimensions, fps, voice duration, frame count, sampled soundtrack identity/sync; not visual/semantic QA',
              'soundtrackSamples': soundtrack,
              'video': str(Path(path).resolve()), 'width': video['width'], 'height': video['height'],
              'fps': fps, 'duration': duration, 'frames': frames, 'errors': errors}
    if errors:
        raise ValueError(json.dumps(report))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    p = commands.add_parser('prepare', help='ingest one voice and create an editable measured timeline')
    p.add_argument('--audio', required=True)
    p.add_argument('--project', required=True)
    p.add_argument('--transcript', help='optional timed Whisper JSON or SRT; never a plain text timing guess')
    p.add_argument('--language', default='auto')
    p.add_argument('--model', default='small', help='faster-whisper model name or local model directory')
    p.add_argument('--format', choices=['landscape', 'portrait'], default='landscape')
    p.add_argument('--fps', type=int, default=30)
    p.add_argument('--seed', type=int, default=42)
    p.add_argument('--max-shot-seconds', type=float, default=5)
    v = commands.add_parser('verify', help='decode and measure the rendered file; does not judge meaning or visual quality')
    v.add_argument('--video', required=True)
    v.add_argument('--timeline', required=True)
    r = commands.add_parser('render', help='run the Node frame renderer, then independently decode and measure MP4')
    r.add_argument('--timeline', required=True)
    r.add_argument('--output', required=True)
    r.add_argument('--quality', choices=['low', 'med', 'high'], default='med')
    args = parser.parse_args()
    if args.command == 'prepare':
        result = prepare(args)
    elif args.command == 'verify':
        result = verify_video(args.video, args.timeline)
    else:
        if Path(args.output).resolve().exists():
            raise ValueError('Output already exists; choose a new name to preserve the previous render.')
        subprocess.run([tool('node'), str(ROOT / 'scripts' / 'render.mjs'), str(Path(args.timeline).resolve()), str(Path(args.output).resolve()), '--quality', args.quality], check=True, cwd=ROOT)
        result = verify_video(args.output, args.timeline)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        sys.exit(1)
