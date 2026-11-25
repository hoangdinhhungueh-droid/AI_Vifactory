#!/usr/bin/env node
import { spawn, execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { writeFile, mkdir, stat, rename, rm } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { randomUUID } from 'node:crypto';
import { loadTimeline } from './lib/renderer.mjs';
import { frameCount } from '../engine/src/video/timeline.mjs';

const run = promisify(execFile);
const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const engineRoot = path.resolve(scriptDir, '..');

const usage = 'Usage: node scripts/render_parallel.mjs timeline.json out.mp4 [--quality low|med|high] [--sfx] [--gpu] [--workers 3]';

function computeSceneAlignedChunks(t, frames, numWorkers) {
  const W = Math.max(1, Math.min(4, numWorkers, t.scenes.length || 1));
  if (W === 1) return [{ index: 0, startFrame: 0, endFrame: frames }];

  const candidates = t.scenes
    .slice(1)
    .map(s => Math.round(s.start * t.fps))
    .filter(f => f > 0 && f < frames);

  const boundaries = [0];
  for (let w = 1; w < W; w++) {
    const target = Math.round((w * frames) / W);
    const prev = boundaries[boundaries.length - 1];
    const remainingNeeded = W - w;
    const valid = candidates.filter(f => f > prev && f < frames - remainingNeeded);
    let chosen;
    if (valid.length) {
      chosen = valid.reduce((best, cur) => Math.abs(cur - target) < Math.abs(best - target) ? cur : best, valid[0]);
    } else {
      chosen = Math.min(frames - remainingNeeded, Math.max(prev + 1, target));
    }
    boundaries.push(chosen);
  }
  boundaries.push(frames);

  const chunks = [];
  for (let i = 0; i < boundaries.length - 1; i++) {
    if (boundaries[i + 1] > boundaries[i]) {
      chunks.push({ index: i, startFrame: boundaries[i], endFrame: boundaries[i + 1] });
    }
  }
  return chunks;
}

function cleanNodeEnv() {
  const env = { ...process.env };
  delete env.NODE_CHANNEL_FD;
  delete env.NODE_CHANNEL_SERIALIZATION_MODE;
  delete env.NODE_APP_INSTANCE;
  return env;
}

function spawnSegmentWorker(timelinePath, segOut, chunk, options, progressMap, totalFrames, onTick) {
  return new Promise((resolve, reject) => {
    const args = [
      path.join(scriptDir, 'render.mjs'),
      timelinePath,
      segOut,
      '--quality', options.quality,
      '--start-frame', String(chunk.startFrame),
      '--end-frame', String(chunk.endFrame),
      '--silent-only',
    ];
    if (options.gpu) args.push('--gpu');

    const child = spawn(process.execPath, args, {
      cwd: engineRoot,
      env: cleanNodeEnv(),
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: true,
    });

    let stderrBuf = '';
    child.stderr.on('data', d => {
      const text = d.toString();
      stderrBuf = (stderrBuf + text).slice(-8000);
      const matches = [...text.matchAll(/\[render\]\s+(\d+)\/(\d+)\s+(\S+)/g)];
      for (const m of matches) {
        progressMap.set(chunk.index, Number(m[1]));
        onTick(m[3]);
      }
    });

    child.on('error', err => reject(err));
    child.on('close', code => {
      if (code !== 0) {
        reject(new Error(`Worker ${chunk.index} [${chunk.startFrame}..${chunk.endFrame}) exited with ${code}:\n${stderrBuf}`));
      } else {
        progressMap.set(chunk.index, chunk.endFrame - chunk.startFrame);
        resolve(segOut);
      }
    });
  });
}

async function main() {
  const [timelineArg, outputArg, ...args] = process.argv.slice(2);
  if (!timelineArg || !outputArg || timelineArg === '--help' || timelineArg === '-h') {
    process.stdout.write(`${usage}\n`);
    return;
  }

  const options = { quality: 'med', sfx: false, gpu: false, workers: 3 };
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--quality' && args[i + 1]) options.quality = args[++i];
    else if (args[i] === '--sfx') options.sfx = true;
    else if (args[i] === '--gpu') options.gpu = true;
    else if (args[i] === '--workers' && args[i + 1]) options.workers = Number(args[++i]);
    else throw new Error(`Unknown/missing option: ${args[i]}\n${usage}`);
  }

  const t = await loadTimeline(timelineArg);
  const frames = frameCount(t);
  const output = path.resolve(outputArg);
  await mkdir(path.dirname(output), { recursive: true });

  const token = randomUUID();
  const workDir = path.join(path.dirname(output), `.parallel_${token}`);
  await mkdir(workDir, { recursive: true });
  const partial = `${output}.${token}.partial.mp4`;
  const metaPartial = `${output}.${token}.partial.json`;
  const concatFile = path.join(workDir, 'concat.txt');

  try {
    const chunks = computeSceneAlignedChunks(t, frames, options.workers);
    process.stderr.write(`[parallel] Launching ${chunks.length} workers across ${frames} frames (${t.width}x${t.height} quality=${options.quality})...\n`);

    const progressMap = new Map(chunks.map(c => [c.index, 0]));
    let lastReported = -1;
    const onTick = scene => {
      let sum = 0;
      for (const v of progressMap.values()) sum += v;
      if (sum - lastReported >= 30 || sum === frames) {
        lastReported = sum;
        const pct = ((sum / frames) * 100).toFixed(1);
        process.stderr.write(`[parallel] ${sum}/${frames} (${pct}%) ${scene}\n`);
      }
    };

    const segPaths = [];
    const promises = chunks.map(ch => {
      const segOut = path.join(workDir, `seg_${String(ch.index).padStart(2, '0')}.mp4`);
      segPaths.push(segOut);
      return spawnSegmentWorker(timelineArg, segOut, ch, options, progressMap, frames, onTick);
    });
    await Promise.all(promises);

    const concatLines = segPaths.map(p => `file '${p.replace(/'/g, "'\\''")}'`).join('\n') + '\n';
    await writeFile(concatFile, concatLines, 'utf8');

    const cuts = t.scenes.slice(1).map(s => s.start);
    const audioArgs = options.sfx && cuts.length
      ? [
          '-f', 'lavfi', '-i', 'anoisesrc=d=0.34:c=pink:r=48000:a=0.5', '-filter_complex',
          `[2:a]highpass=f=900,lowpass=f=7000,afade=t=in:d=0.02,afade=t=out:st=0.05:d=0.27,volume=0.22,asplit=${cuts.length}${cuts.map((_, i) => `[n${i}]`).join('')};` +
          cuts.map((c, i) => `[n${i}]adelay=${Math.max(0, Math.round((c - 0.14) * 1000))}:all=1[d${i}]`).join(';') + ';' +
          `[1:a]aresample=48000[v];[v]${cuts.map((_, i) => `[d${i}]`).join('')}amix=inputs=${cuts.length + 1}:normalize=0:duration=first[aout]`,
          '-map', '0:v:0', '-map', '[aout]'
        ]
      : ['-map', '0:v:0', '-map', '1:a:0'];

    const ffArgs = [
      '-hide_banner', '-loglevel', 'error', '-y',
      '-f', 'concat', '-safe', '0', '-i', concatFile,
      '-i', t.audio,
      ...audioArgs,
      '-c:v', 'copy',
      '-c:a', 'aac', '-b:a', '192k',
      '-t', String(frames / t.fps),
      '-movflags', '+faststart',
      partial,
    ];
    await run('ffmpeg', ffArgs, { timeout: 300000, maxBuffer: 4e6 });

    const { stdout } = await run('ffprobe', ['-v', 'error', '-show_streams', '-show_format', '-of', 'json', partial], { timeout: 30000, maxBuffer: 2e6 });
    const probe = JSON.parse(stdout);
    const video = probe.streams.find(s => s.codec_type === 'video');
    const hasAudio = probe.streams.some(s => s.codec_type === 'audio');
    if (!video || video.width !== t.width || video.height !== t.height || Number(video.nb_frames) !== frames || !hasAudio) {
      throw new Error(`Parallel mux failed verification: ${video?.width}x${video?.height}, nb_frames=${video?.nb_frames} (expected ${frames}), audio=${hasAudio}`);
    }

    const result = {
      version: 1,
      frames,
      duration: t.duration,
      fps: t.fps,
      width: t.width,
      height: t.height,
      seed: t.seed,
      quality: options.quality,
      workers: chunks.length,
      chunks,
      sfx: !!(options.sfx && cuts.length),
      gpu: !!options.gpu,
      audio: t.audio,
      output,
      encodedDuration: Number(probe.format.duration),
      bytes: (await stat(partial)).size,
      shots: t.scenes.map(s => ({ id: s.id, start: s.start, end: s.end, prop: s.prop, action: s.action, camera: s.camera })),
    };

    await writeFile(metaPartial, JSON.stringify(result, null, 2));
    await rename(partial, output);
    await rename(metaPartial, `${output}.json`);
    process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
  } finally {
    await rm(partial, { force: true }).catch(() => {});
    await rm(metaPartial, { force: true }).catch(() => {});
    await rm(workDir, { recursive: true, force: true }).catch(() => {});
  }
}

main().catch(e => {
  console.error(`[parallel] ${e.message}`);
  process.exitCode = 1;
});
