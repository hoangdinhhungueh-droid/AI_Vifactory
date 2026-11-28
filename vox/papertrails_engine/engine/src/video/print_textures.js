import * as THREE from 'three';

const FONT_STACK = '"Noto Sans CJK KR","Noto Sans CJK JP","Noto Sans","Segoe UI",Arial,sans-serif';

const MARKET_COPY = {
  KR: { tag: '핵심 기록 // 보도 분석', docTitle: '핵심 기록', chartTitle: '시장 지표', ledgerTitle: '자금 원장', stamp: '핵심 확인' },
  KO: { tag: '핵심 기록 // 보도 분석', docTitle: '핵심 기록', chartTitle: '시장 지표', ledgerTitle: '자금 원장', stamp: '핵심 확인' },
  JA: { tag: '検証記録 // 報道資料', docTitle: '検証記録', chartTitle: '市場指標', ledgerTitle: '資金台帳', stamp: '検証済' },
  JP: { tag: '検証記録 // 報道資料', docTitle: '検証記録', chartTitle: '市場指標', ledgerTitle: '資金台帳', stamp: '検証済' },
  VN: { tag: 'HỒ SƠ // ĐỐI CHIẾU', docTitle: 'HỒ SƠ ĐIỀU TRA', chartTitle: 'DỮ LIỆU THỊ TRƯỜNG', ledgerTitle: 'SỔ CÁI ĐỐI CHIẾU', stamp: 'ĐỐI CHIẾU' },
  VI: { tag: 'HỒ SƠ // ĐỐI CHIẾU', docTitle: 'HỒ SƠ ĐIỀU TRA', chartTitle: 'DỮ LIỆU THỊ TRƯỜNG', ledgerTitle: 'SỔ CÁI ĐỐI CHIẾU', stamp: 'ĐỐI CHIẾU' },
  EN: { tag: 'ARCHIVE // DOSSIER', docTitle: 'INVESTIGATIVE RECORD', chartTitle: 'MARKET DATA', ledgerTitle: 'AUDIT LEDGER', stamp: 'VERIFIED' },
};

export function resolveMarket(sceneData) {
  const m = String(sceneData?.market || '').trim().toUpperCase();
  if (m && MARKET_COPY[m]) return m;
  const txt = `${sceneData?.title || ''} ${sceneData?.narration || ''} ${sceneData?.card?.head || ''}`;
  if (/[\uAC00-\uD7A3]/.test(txt)) return 'KR';
  if (/[\u3040-\u30FF]/.test(txt)) return 'JA';
  if (/[ăâđêôơưĂÂĐÊÔƠƯ]/.test(txt)) return 'VN';
  return 'EN';
}

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

function paintPaperGrain(ctx, w, h, baseColor, seedStr, vignetteStrength = 0.08) {
  ctx.fillStyle = baseColor;
  ctx.fillRect(0, 0, w, h);
  const rand = makeRng(hashStr(seedStr || baseColor));
  for (let i = 0; i < Math.floor((w * h) / 360); i++) {
    const x = rand() * w;
    const y = rand() * h;
    const sz = 1 + rand() * 2.4;
    ctx.fillStyle = rand() > 0.5 ? 'rgba(62,44,24,0.055)' : 'rgba(255,248,232,0.07)';
    ctx.fillRect(x, y, sz, sz);
  }
  if (vignetteStrength > 0) {
    const g = ctx.createRadialGradient(w * 0.5, h * 0.45, Math.min(w, h) * 0.25, w * 0.5, h * 0.5, Math.max(w, h) * 0.72);
    g.addColorStop(0, 'rgba(0,0,0,0)');
    g.addColorStop(1, `rgba(42,28,14,${vignetteStrength})`);
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, w, h);
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
  const numM = src.match(/\d[\d,.]*(?:\s*(?:조\s*\d[\d,.]*\s*억\s*원|조\s*\d[\d,.]*\s*억|조\s*원|억\s*원|만\s*원|개\s*기관|개\s*은행|개\s*사|개\s*곳|개월|차례|퍼센트|조|억|만|원|%|곳|건|년|배|trillion|billion|million|thousand|percent|cases|years|months|banks|tỷ\s*USD|tỷ\s*đồng|triệu\s*đồng|tỷ|triệu|nghìn|năm|lần|兆円|億円|万円|兆|億|万|円|件|社))/i);
  return numM ? numM[0].replace(/\s+/g, ' ').trim() : '';
}

export function extractSourceTag(sceneData) {
  const head = String(sceneData?.card?.head || '').trim();
  if (head.includes('//')) {
    const parts = head.split('//');
    if (parts[1] && parts[1].trim()) return parts[1].trim();
  }
  if (head) return head;
  return (MARKET_COPY[resolveMarket(sceneData)] || MARKET_COPY.EN).tag;
}

export function createPrintedPaperMaterial({ width = 768, height = 896, baseColor = '#ede4d0', seed = 'doc', draw, vignette = 0.08 }) {
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d');
  paintPaperGrain(ctx, width, height, baseColor, seed, vignette);
  if (draw) draw(ctx, width, height);
  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 8;
  tex.needsUpdate = true;
  const mat = new THREE.MeshLambertMaterial({
    color: new THREE.Color('#ffffff'),
    map: tex,
    emissive: new THREE.Color('#fff5e4'),
    emissiveMap: tex,
    emissiveIntensity: 0.17,
    side: THREE.DoubleSide,
  });
  mat.userData.noDayNightGlow = true;
  return mat;
}

export async function preloadIllustrationImages(illustrationsMap) {
  const loaded = new Map();
  if (!illustrationsMap || typeof illustrationsMap !== 'object') return loaded;
  const entries = Object.entries(illustrationsMap);
  await Promise.all(entries.map(async ([key, uri]) => {
    if (typeof uri !== 'string' || !uri.startsWith('data:image/')) return;
    const img = new Image();
    img.src = uri;
    try {
      if (typeof img.decode === 'function') {
        await img.decode();
      } else {
        await new Promise((res, rej) => {
          img.onload = () => res();
          img.onerror = (err) => rej(err);
        });
      }
      loaded.set(key, img);
    } catch {
      // Skip malformed image data silently so remaining plates still render cleanly
    }
  }));
  return loaded;
}

function drawInkStamp(ctx, label, x, y, angle = -0.14) {
  ctx.save();
  ctx.translate(x, y);
  ctx.rotate(angle);
  ctx.strokeStyle = 'rgba(196, 54, 34, 0.85)';
  ctx.lineWidth = 4;
  ctx.fillStyle = 'rgba(250, 240, 224, 0.72)';
  ctx.font = `900 22px ${FONT_STACK}`;
  const tw = Math.max(118, ctx.measureText(label).width + 36);
  ctx.fillRect(-tw / 2, -24, tw, 48);
  ctx.strokeRect(-tw / 2, -24, tw, 48);
  ctx.fillStyle = 'rgba(196, 54, 34, 0.92)';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(label, 0, 1);
  ctx.restore();
}

function drawNewsprintColumns(ctx, x, y, w, h, rand) {
  const colW = (w - 28) / 2;
  for (let c = 0; c < 2; c++) {
    const cx = x + c * (colW + 28);
    ctx.strokeStyle = 'rgba(72, 54, 34, 0.25)';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(cx, y);
    ctx.lineTo(cx + colW, y);
    ctx.stroke();
    let ly = y + 20;
    while (ly < y + h - 18) {
      const barW = colW * (0.58 + rand() * 0.40);
      ctx.fillStyle = rand() > 0.82 ? 'rgba(184, 56, 31, 0.22)' : 'rgba(58, 42, 26, 0.17)';
      ctx.fillRect(cx, ly, barW, 9);
      ly += 22;
    }
  }
}

export function makeEditorialClippingMaterial(sceneData, opts = {}) {
  const mode = opts.mode || 'dossier';
  const copy = MARKET_COPY[resolveMarket(sceneData)] || MARKET_COPY.EN;
  const title = String(sceneData?.title || copy.docTitle).trim();
  const narration = String(sceneData?.narration || '').trim();
  const metric = extractDisplayMetric(sceneData);
  const srcTag = extractSourceTag(sceneData);
  const baseColor = opts.baseColor || (mode === 'stamp' ? '#f0e6d2' : '#ede4d0');

  return createPrintedPaperMaterial({
    width: 768,
    height: 920,
    baseColor,
    seed: `${sceneData?.id || 'clip'}-${mode}`,
    vignette: 0.11,
    draw: (ctx, w, h) => {
      const rand = makeRng(hashStr(`${sceneData?.id || 'clip'}-cols`));
      // Top dark editorial press masthead bar
      ctx.fillStyle = '#231b14';
      ctx.fillRect(0, 0, w, 72);
      ctx.fillStyle = '#f5ecd9';
      ctx.font = `800 22px ${FONT_STACK}`;
      ctx.fillText(srcTag, 48, 44);
      ctx.fillStyle = '#c83e2b';
      ctx.fillRect(0, 72, w, 7);

      // Left archival margin rule
      ctx.fillStyle = '#c83e2b';
      ctx.fillRect(36, 102, 8, h - 140);

      // Newspaper headline
      ctx.fillStyle = '#1e160f';
      ctx.font = `900 44px ${FONT_STACK}`;
      const titleLines = wrapLines(ctx, title, w - 120, 2);
      titleLines.forEach((ln, idx) => ctx.fillText(ln, 64, 142 + idx * 54));

      // Rule under headline
      let curY = titleLines.length > 1 ? 222 : 172;
      ctx.strokeStyle = 'rgba(42,30,18,0.45)';
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.moveTo(64, curY);
      ctx.lineTo(w - 48, curY);
      ctx.stroke();
      curY += 28;

      // Quantitative callout bar if metric exists
      if (metric) {
        ctx.fillStyle = '#c83e2b';
        ctx.fillRect(64, curY, w - 112, 88);
        ctx.fillStyle = '#fff6e6';
        ctx.font = `900 48px ${FONT_STACK}`;
        ctx.fillText(metric, 88, curY + 60);
        curY += 116;
      }

      // Narration excerpt lines WITH warm yellow felt-tip highlighter strokes underneath
      ctx.font = `700 29px ${FONT_STACK}`;
      const bodyLines = wrapLines(ctx, narration, w - 124, 4);
      bodyLines.forEach((ln, idx) => {
        const ly = curY + idx * 48;
        if (idx < 2) {
          const lw = Math.min(w - 116, ctx.measureText(ln).width + 18);
          ctx.fillStyle = 'rgba(244, 206, 66, 0.56)';
          ctx.fillRect(60, ly - 30, lw, 38);
        }
        ctx.fillStyle = '#241a12';
        ctx.fillText(ln, 66, ly);
      });
      curY += Math.max(1, bodyLines.length) * 48 + 26;

      // Fill lower half with realistic dense 2-column broadsheet copy blocks so zero void remains
      const remH = h - curY - 48;
      if (remH >= 80) {
        drawNewsprintColumns(ctx, 64, curY, w - 112, remH, rand);
      }

      // Angled red archival verification stamp
      drawInkStamp(ctx, copy.stamp, w - 148, h - 84, -0.13);
    },
  });
}

export function makeDocumentPrintMaterial(sceneData, opts = {}) {
  return makeEditorialClippingMaterial(sceneData, opts);
}

export function makeIllustratedCollagePlateMaterial(sceneData, imgElement) {
  const copy = MARKET_COPY[resolveMarket(sceneData)] || MARKET_COPY.EN;
  const title = String(sceneData?.title || copy.docTitle).trim();
  const metric = extractDisplayMetric(sceneData);
  const srcTag = extractSourceTag(sceneData);

  return createPrintedPaperMaterial({
    width: 1024,
    height: 820,
    baseColor: '#efe6d2',
    seed: `${sceneData?.id || 'plate'}-ill`,
    vignette: 0.09,
    draw: (ctx, w, h) => {
      // Double deckle archival frame lines
      ctx.strokeStyle = 'rgba(42, 30, 18, 0.35)';
      ctx.lineWidth = 3;
      ctx.strokeRect(24, 24, w - 48, h - 48);

      // Artwork viewport [48, 44, 928, 636] using cover crop to prevent distortion
      const vx = 48, vy = 44, vw = w - 96, vh = 636;
      if (imgElement && imgElement.width > 0 && imgElement.height > 0) {
        const iw = imgElement.width, ih = imgElement.height;
        const scale = Math.max(vw / iw, vh / ih);
        const sw = vw / scale, sh = vh / scale;
        const sx = (iw - sw) * 0.5, sy = (ih - sh) * 0.5;
        ctx.drawImage(imgElement, sx, sy, sw, sh, vx, vy, vw, vh);
      } else {
        ctx.fillStyle = '#252d38';
        ctx.fillRect(vx, vy, vw, vh);
      }

      // Bold Vox comic ink border around artwork
      ctx.strokeStyle = '#1e160f';
      ctx.lineWidth = 6;
      ctx.strokeRect(vx, vy, vw, vh);

      // Corner translucent archival tape strips
      ctx.fillStyle = 'rgba(232, 206, 146, 0.72)';
      ctx.save();
      ctx.translate(64, 48);
      ctx.rotate(-0.42);
      ctx.fillRect(-44, -14, 88, 28);
      ctx.restore();
      ctx.save();
      ctx.translate(w - 64, 48);
      ctx.rotate(0.42);
      ctx.fillRect(-44, -14, 88, 28);
      ctx.restore();

      // Editorial caption strip strictly below artwork (y = 696..796)
      ctx.fillStyle = '#211912';
      ctx.fillRect(vx, 696, vw, 86);
      ctx.fillStyle = '#f2ce58';
      ctx.font = `800 20px ${FONT_STACK}`;
      ctx.fillText(srcTag, vx + 24, 725);

      let badgeW = 0;
      if (metric) {
        ctx.font = `900 30px ${FONT_STACK}`;
        badgeW = Math.min(340, Math.max(130, ctx.measureText(metric).width + 44));
        const bx = vx + vw - badgeW - 18;
        ctx.fillStyle = '#c83e2b';
        ctx.fillRect(bx, 710, badgeW, 58);
        ctx.fillStyle = '#fff8ee';
        ctx.textAlign = 'center';
        ctx.fillText(metric, bx + badgeW / 2, 749);
        ctx.textAlign = 'left';
      }

      ctx.fillStyle = '#faf2e1';
      ctx.font = `900 34px ${FONT_STACK}`;
      const hLines = wrapLines(ctx, title, metric ? vw - badgeW - 64 : vw - 48, 1);
      if (hLines[0]) ctx.fillText(hLines[0], vx + 24, 764);
    },
  });
}

export function makeChartBoardPrintMaterial(sceneData) {
  const copy = MARKET_COPY[resolveMarket(sceneData)] || MARKET_COPY.EN;
  const title = String(sceneData?.title || copy.chartTitle).trim();
  const metric = extractDisplayMetric(sceneData);
  const srcTag = extractSourceTag(sceneData);

  return createPrintedPaperMaterial({
    width: 1024,
    height: 768,
    baseColor: '#eee5d2',
    seed: `${sceneData?.id || 'chart'}-board`,
    vignette: 0.08,
    draw: (ctx, w, h) => {
      // Dark editorial slate header bar
      ctx.fillStyle = '#1f252e';
      ctx.fillRect(0, 0, w, 134);
      ctx.fillStyle = '#c83e2b';
      ctx.fillRect(0, 134, w, 8);

      ctx.fillStyle = '#e5bc3a';
      ctx.font = `800 22px ${FONT_STACK}`;
      ctx.fillText(srcTag, 56, 46);

      let badgeW = 0;
      if (metric) {
        let badgeFontPx = 38;
        ctx.font = `900 ${badgeFontPx}px ${FONT_STACK}`;
        let mWidth = ctx.measureText(metric).width;
        if (mWidth > 320) {
          badgeFontPx = 30;
          ctx.font = `900 ${badgeFontPx}px ${FONT_STACK}`;
          mWidth = ctx.measureText(metric).width;
        }
        badgeW = Math.min(430, Math.max(180, mWidth + 56));
        const bx = w - badgeW - 48;
        ctx.fillStyle = '#c83e2b';
        ctx.fillRect(bx, 30, badgeW, 76);
        ctx.fillStyle = '#fff8ee';
        ctx.font = `900 ${badgeFontPx}px ${FONT_STACK}`;
        ctx.textAlign = 'center';
        ctx.fillText(metric, bx + badgeW / 2, 81);
        ctx.textAlign = 'left';
      }

      ctx.fillStyle = '#faf2e1';
      ctx.font = `900 40px ${FONT_STACK}`;
      const titleMaxW = metric ? Math.max(260, w - badgeW - 140) : w - 120;
      const hLines = wrapLines(ctx, title, titleMaxW, 1);
      if (hLines[0]) ctx.fillText(hLines[0], 56, 102);

      // Subtle Y-axis tick bands & gridlines strictly inside lower plot area
      ctx.strokeStyle = 'rgba(72, 58, 42, 0.24)';
      ctx.lineWidth = 2;
      ctx.setLineDash([8, 8]);
      for (let y = 215; y <= h - 105; y += 92) {
        ctx.beginPath();
        ctx.moveTo(86, y);
        ctx.lineTo(w - 56, y);
        ctx.stroke();
      }
      ctx.setLineDash([]);

      // Editorial source rule footer
      ctx.fillStyle = 'rgba(42,30,18,0.55)';
      ctx.font = `700 20px ${FONT_STACK}`;
      ctx.fillText(`${srcTag} // ${copy.chartTitle}`, 56, h - 34);
    },
  });
}

export function makeLedgerPagePrintMaterial(sceneData, side = 'left') {
  const copy = MARKET_COPY[resolveMarket(sceneData)] || MARKET_COPY.EN;
  const title = String(sceneData?.title || copy.ledgerTitle).trim();
  const narration = String(sceneData?.narration || '').trim();
  const metric = extractDisplayMetric(sceneData);
  const srcTag = extractSourceTag(sceneData);

  return createPrintedPaperMaterial({
    width: 640,
    height: 896,
    baseColor: '#ede4d0',
    seed: `${sceneData?.id || 'ledger'}-${side}`,
    vignette: 0.09,
    draw: (ctx, w, h) => {
      const rand = makeRng(hashStr(`${sceneData?.id || 'ledger'}-${side}-rows`));
      // Top dark ledger binding header
      ctx.fillStyle = '#231b14';
      ctx.fillRect(0, 0, w, 86);
      ctx.fillStyle = '#e5bc3a';
      ctx.font = `800 20px ${FONT_STACK}`;
      ctx.fillText(srcTag, 44, 34);

      if (side === 'left') {
        ctx.fillStyle = '#faf2e1';
        ctx.font = `900 32px ${FONT_STACK}`;
        wrapLines(ctx, title, w - 88, 1).forEach((ln) => ctx.fillText(ln, 44, 70));
      } else {
        ctx.fillStyle = '#faf2e1';
        ctx.font = `900 30px ${FONT_STACK}`;
        ctx.fillText(metric || copy.ledgerTitle, 44, 70);
      }

      // Alternating ledger row bands + accounting double lines
      for (let idx = 0; idx < 11; idx++) {
        const y = 112 + idx * 66;
        if (idx % 2 === 0) {
          ctx.fillStyle = 'rgba(110, 86, 56, 0.08)';
          ctx.fillRect(36, y, w - 72, 56);
        }
        ctx.strokeStyle = 'rgba(95, 75, 52, 0.24)';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(36, y + 56);
        ctx.lineTo(w - 36, y + 56);
        ctx.stroke();
      }
      ctx.strokeStyle = 'rgba(196, 56, 32, 0.45)';
      ctx.beginPath();
      ctx.moveTo(side === 'left' ? 52 : w - 155, 98);
      ctx.lineTo(side === 'left' ? 52 : w - 155, h - 42);
      ctx.stroke();

      if (side === 'right') {
        ctx.font = `700 25px ${FONT_STACK}`;
        const lines = wrapLines(ctx, narration, w - 108, 4);
        lines.forEach((ln, i) => {
          const ly = 152 + i * 66;
          if (i === 0) {
            const lw = Math.min(w - 110, ctx.measureText(ln).width + 16);
            ctx.fillStyle = 'rgba(244, 206, 66, 0.52)';
            ctx.fillRect(46, ly - 26, lw, 34);
          }
          ctx.fillStyle = '#241a12';
          ctx.fillText(ln, 50, ly);
        });
        // Subtle lower tabular figure bars
        for (let r = 5; r < 11; r++) {
          const ry = 132 + r * 66;
          ctx.fillStyle = 'rgba(56, 42, 28, 0.20)';
          ctx.fillRect(50, ry, 180 + rand() * 140, 12);
          ctx.fillStyle = r % 3 === 0 ? 'rgba(196,56,32,0.45)' : 'rgba(56,42,28,0.28)';
          ctx.fillRect(w - 135, ry, 72, 12);
        }
        drawInkStamp(ctx, copy.stamp, w - 135, h - 78, -0.10);
      }
    },
  });
}

const DESK_PALETTES = {
  heartland: { base: '#b89c74', line: 'rgba(54,38,22,0.22)', accent: 'rgba(148,96,26,0.48)', clip: 'rgba(72,50,28,0.08)' },
  pinewood: { base: '#8fa189', line: 'rgba(34,48,32,0.22)', accent: 'rgba(142,96,26,0.46)', clip: 'rgba(42,58,40,0.08)' },
  desert: { base: '#c2a274', line: 'rgba(66,44,20,0.22)', accent: 'rgba(156,94,22,0.48)', clip: 'rgba(84,56,28,0.08)' },
  snow: { base: '#9cb0c4', line: 'rgba(28,44,64,0.22)', accent: 'rgba(156,104,28,0.46)', clip: 'rgba(36,54,76,0.08)' },
  blossom: { base: '#bfa89c', line: 'rgba(62,40,36,0.21)', accent: 'rgba(148,88,28,0.46)', clip: 'rgba(76,48,44,0.08)' },
};

export function makeDeskSurfaceTexture(themeId = 'heartland') {
  const pal = DESK_PALETTES[themeId] || DESK_PALETTES.heartland;
  const canvas = document.createElement('canvas');
  canvas.width = 1024;
  canvas.height = 1024;
  const ctx = canvas.getContext('2d');
  paintPaperGrain(ctx, 1024, 1024, pal.base, `desk-${themeId}`, 0.06);

  // Subtle cutting-mat millimeter grid
  ctx.strokeStyle = pal.line;
  ctx.lineWidth = 1.5;
  for (let i = 0; i <= 1024; i += 64) {
    ctx.beginPath();
    ctx.moveTo(i, 0);
    ctx.lineTo(i, 1024);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(0, i);
    ctx.lineTo(1024, i);
    ctx.stroke();
  }

  // Faint ghosted newsprint editorial columns embedded into desk texture so background never looks sterile
  const rand = makeRng(hashStr(`desk-cols-${themeId}`));
  for (let b = 0; b < 4; b++) {
    const bx = 64 + (b % 2) * 512;
    const by = 64 + Math.floor(b / 2) * 512;
    ctx.fillStyle = pal.clip;
    ctx.fillRect(bx, by, 384, 320);
    for (let ln = 0; ln < 7; ln++) {
      ctx.fillRect(bx + 24, by + 32 + ln * 36, 180 + rand() * 140, 12);
    }
  }

  // Brass registration crosshairs
  ctx.strokeStyle = pal.accent;
  ctx.lineWidth = 2.5;
  for (const c of [256, 512, 768]) {
    ctx.beginPath();
    ctx.moveTo(c - 16, c);
    ctx.lineTo(c + 16, c);
    ctx.moveTo(c, c - 16);
    ctx.lineTo(c, c + 16);
    ctx.stroke();
  }

  const tex = new THREE.CanvasTexture(canvas);
  tex.wrapS = THREE.RepeatWrapping;
  tex.wrapT = THREE.RepeatWrapping;
  tex.repeat.set(8, 4);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 8;
  tex.needsUpdate = true;
  return tex;
}
