import * as THREE from 'three';

const FONT_STACK = '"Noto Sans CJK KR","Noto Sans CJK JP","Noto Sans","Segoe UI",Arial,sans-serif';

function hashStr(s) {
  let h = 2166136261 >>> 0;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619) >>> 0;
  }
  return h;
}

function makeRng(seed) {
  let s = (seed >>> 0) || 1;
  return () => {
    s = (Math.imul(s, 1664525) + 1013904223) >>> 0;
    return s / 4294967296;
  };
}

function paintPaperGrain(ctx, w, h, baseColor, seedStr) {
  ctx.fillStyle = baseColor;
  ctx.fillRect(0, 0, w, h);
  const rand = makeRng(hashStr(seedStr || baseColor));
  for (let i = 0; i < Math.floor((w * h) / 420); i++) {
    const x = rand() * w;
    const y = rand() * h;
    const sz = 1 + rand() * 2.2;
    ctx.fillStyle = rand() > 0.5 ? 'rgba(90,68,42,0.045)' : 'rgba(255,250,240,0.08)';
    ctx.fillRect(x, y, sz, sz);
  }
}

function wrapLines(ctx, text, maxW, maxLines) {
  const clean = String(text || '').replace(/\s+/g, ' ').trim();
  if (!clean) return [];
  const words = clean.split(' ');
  const lines = [];
  let cur = '';
  for (const word of words) {
    const cand = cur ? `${cur} ${word}` : word;
    if (ctx.measureText(cand).width <= maxW) {
      cur = cand;
    } else if (!cur) {
      let chunk = '';
      for (const ch of word) {
        if (ctx.measureText(chunk + ch).width > maxW && chunk) {
          lines.push(chunk);
          if (lines.length >= maxLines) return lines;
          chunk = ch;
        } else {
          chunk += ch;
        }
      }
      cur = chunk;
    } else {
      lines.push(cur);
      if (lines.length >= maxLines) return lines;
      cur = word;
    }
  }
  if (cur && lines.length < maxLines) lines.push(cur);
  return lines;
}

export function extractDisplayMetric(sceneData) {
  if (!sceneData) return '';
  const cardLines = sceneData.card?.lines || [];
  for (const ln of cardLines) {
    const m = String(ln).match(/`([^`]+)`/);
    if (m && m[1]) return m[1].trim();
  }
  const src = `${sceneData.title || ''} ${sceneData.narration || ''}`;
  const numM = src.match(/\d[\d,.]*(?:\s*(?:조|억|만|%|곳|건|차례|년|개월|배|원|billion|million|trillion|percent|cases|years|months))?/i);
  return numM ? numM[0].trim() : '';
}

export function extractSourceTag(sceneData) {
  const head = String(sceneData?.card?.head || '').trim();
  if (head.includes('//')) {
    const parts = head.split('//');
    if (parts[1] && parts[1].trim()) return parts[1].trim();
  }
  if (head) return head;
  return 'ARCHIVE // DOSSIER';
}

export function createPrintedPaperMaterial({ width = 768, height = 768, baseColor = '#f4efe3', seed = 'doc', draw }) {
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d');
  paintPaperGrain(ctx, width, height, baseColor, seed);
  if (draw) draw(ctx, width, height);
  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 8;
  tex.needsUpdate = true;
  return new THREE.MeshLambertMaterial({ map: tex, side: THREE.DoubleSide });
}

export function makeDocumentPrintMaterial(sceneData, opts = {}) {
  const mode = opts.mode || 'dossier';
  const title = String(sceneData?.title || 'INVESTIGATIVE RECORD').trim();
  const narration = String(sceneData?.narration || '').trim();
  const metric = extractDisplayMetric(sceneData);
  const srcTag = extractSourceTag(sceneData);
  const baseColor = opts.baseColor || (mode === 'stamp' ? '#f6efe0' : '#f4efe3');

  return createPrintedPaperMaterial({
    width: 768,
    height: 896,
    baseColor,
    seed: `${sceneData?.id || 'doc'}-${mode}`,
    draw: (ctx, w, h) => {
      // Subtle ruled ledger lines
      ctx.strokeStyle = 'rgba(130,108,78,0.16)';
      ctx.lineWidth = 2;
      for (let y = 175; y < h - 70; y += 54) {
        ctx.beginPath();
        ctx.moveTo(56, y);
        ctx.lineTo(w - 56, y);
        ctx.stroke();
      }
      // Red editorial margin bar
      ctx.fillStyle = '#c83e2b';
      ctx.fillRect(46, 56, 10, h - 112);

      // Masthead tag + divider
      ctx.fillStyle = '#b8381f';
      ctx.font = `800 24px ${FONT_STACK}`;
      ctx.fillText(srcTag, 76, 88);
      ctx.strokeStyle = '#3b2e21';
      ctx.lineWidth = 4;
      ctx.beginPath();
      ctx.moveTo(76, 106);
      ctx.lineTo(w - 56, 106);
      ctx.stroke();

      // Main headline
      ctx.fillStyle = '#241a12';
      ctx.font = `900 44px ${FONT_STACK}`;
      const titleLines = wrapLines(ctx, title, w - 140, 2);
      titleLines.forEach((ln, idx) => ctx.fillText(ln, 76, 162 + idx * 54));

      // Quantitative callout box
      let bodyTop = titleLines.length > 1 ? 265 : 220;
      if (metric) {
        ctx.fillStyle = 'rgba(200,62,43,0.10)';
        ctx.fillRect(76, bodyTop, w - 136, 98);
        ctx.strokeStyle = '#c83e2b';
        ctx.lineWidth = 3;
        ctx.strokeRect(76, bodyTop, w - 136, 98);
        ctx.fillStyle = '#b8381f';
        ctx.font = `900 54px ${FONT_STACK}`;
        ctx.fillText(metric, 98, bodyTop + 66);
        bodyTop += 132;
      }

      // Narration excerpt lines
      ctx.fillStyle = '#3b2e21';
      ctx.font = `700 30px ${FONT_STACK}`;
      const maxExcerptLines = mode === 'contract' ? 4 : 5;
      const bodyLines = wrapLines(ctx, narration, w - 144, maxExcerptLines);
      bodyLines.forEach((ln, idx) => ctx.fillText(ln, 76, bodyTop + idx * 46));
    },
  });
}

export function makeChartBoardPrintMaterial(sceneData) {
  const title = String(sceneData?.title || 'MARKET DATA').trim();
  const metric = extractDisplayMetric(sceneData);
  const srcTag = extractSourceTag(sceneData);

  return createPrintedPaperMaterial({
    width: 1024,
    height: 768,
    baseColor: '#f5efe2',
    seed: `${sceneData?.id || 'chart'}-board`,
    draw: (ctx, w, h) => {
      // Faint horizontal chart gridlines
      ctx.strokeStyle = 'rgba(95,78,56,0.20)';
      ctx.lineWidth = 2;
      ctx.setLineDash([8, 8]);
      for (let y = 190; y <= h - 120; y += 92) {
        ctx.beginPath();
        ctx.moveTo(90, y);
        ctx.lineTo(w - 72, y);
        ctx.stroke();
      }
      ctx.setLineDash([]);

      // Top editorial header
      ctx.fillStyle = '#8b6f4e';
      ctx.font = `800 22px ${FONT_STACK}`;
      ctx.fillText(srcTag, 76, 62);

      ctx.fillStyle = '#241a12';
      ctx.font = `900 42px ${FONT_STACK}`;
      const hLines = wrapLines(ctx, title, metric ? w - 380 : w - 150, 1);
      if (hLines[0]) ctx.fillText(hLines[0], 76, 118);

      if (metric) {
        const badgeW = Math.min(300, Math.max(170, ctx.measureText(metric).width + 64));
        const bx = w - badgeW - 60;
        ctx.fillStyle = '#c83e2b';
        ctx.fillRect(bx, 46, badgeW, 82);
        ctx.fillStyle = '#fff8ee';
        ctx.font = `900 40px ${FONT_STACK}`;
        ctx.textAlign = 'center';
        ctx.fillText(metric, bx + badgeW / 2, 101);
        ctx.textAlign = 'left';
      }
    },
  });
}

export function makeLedgerPagePrintMaterial(sceneData, side = 'left') {
  const title = String(sceneData?.title || 'AUDIT LEDGER').trim();
  const narration = String(sceneData?.narration || '').trim();
  const metric = extractDisplayMetric(sceneData);
  const srcTag = extractSourceTag(sceneData);

  return createPrintedPaperMaterial({
    width: 640,
    height: 896,
    baseColor: '#f4efe1',
    seed: `${sceneData?.id || 'ledger'}-${side}`,
    draw: (ctx, w, h) => {
      // Accounting vertical & horizontal column rules
      ctx.strokeStyle = 'rgba(120,96,68,0.22)';
      ctx.lineWidth = 2;
      for (let y = 150; y < h - 60; y += 64) {
        ctx.beginPath();
        ctx.moveTo(40, y);
        ctx.lineTo(w - 40, y);
        ctx.stroke();
      }
      ctx.strokeStyle = 'rgba(184,56,31,0.35)';
      ctx.beginPath();
      ctx.moveTo(side === 'left' ? 56 : w - 165, 110);
      ctx.lineTo(side === 'left' ? 56 : w - 165, h - 60);
      ctx.stroke();

      if (side === 'left') {
        ctx.fillStyle = '#b8381f';
        ctx.font = `800 22px ${FONT_STACK}`;
        ctx.fillText(srcTag, 74, 72);
        ctx.fillStyle = '#241a12';
        ctx.font = `900 36px ${FONT_STACK}`;
        wrapLines(ctx, title, w - 110, 2).forEach((ln, i) => ctx.fillText(ln, 74, 122 + i * 44));
      } else {
        let topY = 92;
        if (metric) {
          ctx.fillStyle = '#241a12';
          ctx.fillRect(46, 52, w - 92, 86);
          ctx.fillStyle = '#f8efd8';
          ctx.font = `900 44px ${FONT_STACK}`;
          ctx.fillText(metric, 68, 110);
          topY = 186;
        }
        ctx.fillStyle = '#3b2e21';
        ctx.font = `700 27px ${FONT_STACK}`;
        wrapLines(ctx, narration, w - 110, 6).forEach((ln, i) => ctx.fillText(ln, 48, topY + i * 48));
      }
    },
  });
}

const DESK_PALETTES = {
  heartland: { base: '#efe8d8', line: 'rgba(120,96,68,0.16)', accent: 'rgba(184,56,31,0.22)', kind: 'newsprint' },
  pinewood: { base: '#cab894', line: 'rgba(84,64,40,0.18)', accent: 'rgba(160,48,30,0.20)', kind: 'kraft' },
  desert: { base: '#e7dac0', line: 'rgba(110,88,58,0.18)', accent: 'rgba(184,56,31,0.20)', kind: 'graph' },
  snow: { base: '#d5dde3', line: 'rgba(65,86,108,0.20)', accent: 'rgba(184,56,31,0.25)', kind: 'blueprint' },
  blossom: { base: '#ede3d4', line: 'rgba(105,82,58,0.16)', accent: 'rgba(184,56,31,0.22)', kind: 'broadsheet' },
};

export function makeDeskSurfaceTexture(themeId = 'heartland') {
  const pal = DESK_PALETTES[themeId] || DESK_PALETTES.heartland;
  const canvas = document.createElement('canvas');
  canvas.width = 1024;
  canvas.height = 1024;
  const ctx = canvas.getContext('2d');
  paintPaperGrain(ctx, 1024, 1024, pal.base, `desk-${themeId}`);

  // Archival graph / editorial desk grid
  const step = pal.kind === 'graph' || pal.kind === 'blueprint' ? 64 : 128;
  ctx.strokeStyle = pal.line;
  ctx.lineWidth = 2;
  for (let i = 0; i <= 1024; i += step) {
    ctx.beginPath();
    ctx.moveTo(i, 0);
    ctx.lineTo(i, 1024);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(0, i);
    ctx.lineTo(1024, i);
    ctx.stroke();
  }

  // Subtle registration crosshairs & editorial column margin lines
  ctx.strokeStyle = pal.accent;
  ctx.lineWidth = 3;
  for (const c of [256, 512, 768]) {
    ctx.beginPath();
    ctx.moveTo(c - 18, c);
    ctx.lineTo(c + 18, c);
    ctx.moveTo(c, c - 18);
    ctx.lineTo(c, c + 18);
    ctx.stroke();
  }

  const tex = new THREE.CanvasTexture(canvas);
  tex.wrapS = THREE.RepeatWrapping;
  tex.wrapT = THREE.RepeatWrapping;
  tex.repeat.set(3, 3);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 8;
  tex.needsUpdate = true;
  return tex;
}
