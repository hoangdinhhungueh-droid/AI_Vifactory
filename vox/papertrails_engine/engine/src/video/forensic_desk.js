import * as THREE from 'three';
import {
  makeDeskSurfaceTexture,
  makeEditorialClippingMaterial,
  makeChartBoardPrintMaterial,
  makeLedgerPagePrintMaterial,
} from './print_textures.js';

export const JOURNEY_STEP_X = 4.6;

export function computeJourneyOrigins(scenes) {
  const origins = new Map();
  (scenes || []).forEach((s, idx) => {
    const x = idx * JOURNEY_STEP_X;
    const z = Math.sin(idx * 0.72) * 1.65;
    origins.set(s.id, new THREE.Vector3(x, 0, z));
  });
  return origins;
}

function addDeskMatMesh(geo, mat, cast = false, receive = true) {
  const m = new THREE.Mesh(geo, mat);
  m.castShadow = cast;
  m.receiveShadow = receive;
  return m;
}

function buildConnector(parent, a, b, type, mats, sceneData) {
  const start = new THREE.Vector3(a.x, 0.02, a.z);
  const end = new THREE.Vector3(b.x, 0.02, b.z);
  const dir = new THREE.Vector3().subVectors(end, start);
  const len = dir.length();
  if (len < 0.4) return;
  const mid = new THREE.Vector3().addVectors(start, end).multiplyScalar(0.5);
  const yaw = Math.atan2(dir.x, dir.z);

  const g = new THREE.Group();
  g.position.copy(mid);
  g.rotation.y = yaw;

  if (type === 'highlighter_sweep') {
    const ribbon = addDeskMatMesh(new THREE.BoxGeometry(0.24, 0.012, Math.max(0.5, len - 2.1)), mats.highlight, false, true);
    g.add(ribbon);
    for (const tz of [-(len - 2.4) * 0.48, (len - 2.4) * 0.48]) {
      const cap = addDeskMatMesh(new THREE.BoxGeometry(0.42, 0.018, 0.06), mats.ink, false, true);
      cap.position.set(0, 0.006, tz);
      g.add(cap);
    }
  } else if (type === 'timeline_rail') {
    const span = Math.max(0.6, len - 2.0);
    const rail = addDeskMatMesh(new THREE.BoxGeometry(0.08, 0.024, span), mats.brass, true, true);
    g.add(rail);
    const ticks = Math.max(3, Math.floor(span / 0.85));
    for (let i = 0; i <= ticks; i++) {
      const zOff = -span * 0.5 + (i / ticks) * span;
      const tick = addDeskMatMesh(new THREE.BoxGeometry(i % 2 === 0 ? 0.44 : 0.24, 0.02, 0.04), i % 2 === 0 ? mats.ink : mats.brass, false, true);
      tick.position.set(0, 0.008, zOff);
      g.add(tick);
    }
    const tab = addDeskMatMesh(new THREE.BoxGeometry(0.56, 0.016, 0.34), mats.cream, true, true);
    tab.position.set(0.32, 0.014, 0);
    tab.rotation.y = 0.14;
    g.add(tab);
  } else if (type === 'money_flow') {
    const span = Math.max(0.6, len - 2.2);
    const count = 4;
    for (let i = 0; i < count; i++) {
      const zPos = -span * 0.38 + (i / Math.max(1, count - 1)) * (span * 0.76);
      const chev = new THREE.Group();
      chev.position.set(0, 0.02, zPos);
      const leftArm = addDeskMatMesh(new THREE.BoxGeometry(0.06, 0.02, 0.30), mats.gold, true, true);
      leftArm.position.set(-0.10, 0, -0.08);
      leftArm.rotation.y = 0.58;
      const rightArm = addDeskMatMesh(new THREE.BoxGeometry(0.06, 0.02, 0.30), mats.gold, true, true);
      rightArm.position.set(0.10, 0, -0.08);
      rightArm.rotation.y = -0.58;
      chev.add(leftArm, rightArm);
      g.add(chev);
    }
    const trace = addDeskMatMesh(new THREE.BoxGeometry(0.035, 0.01, span), mats.teal, false, true);
    g.add(trace);
  } else if (type === 'red_yarn') {
    // Route cleanly behind the plates (-0.95 lateral X offset in local tangent) so yarn never pierces hero center
    const lat = 0.85;
    const pa = new THREE.Vector3(a.x, 0.06, a.z - lat);
    const pb = new THREE.Vector3(b.x, 0.06, b.z - lat);
    const segDir = new THREE.Vector3().subVectors(pb, pa);
    const segLen = segDir.length();
    if (segLen > 0.3) {
      const yarn = addDeskMatMesh(new THREE.CylinderGeometry(0.016, 0.016, segLen, 8), mats.crimson, true, false);
      yarn.position.copy(pa).add(pb).multiplyScalar(0.5);
      yarn.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), segDir.normalize());
      parent.add(yarn);
    }
    return;
  } else if (type === 'paper_tear') {
    const span = Math.max(0.6, len - 2.0);
    const strip = addDeskMatMesh(new THREE.BoxGeometry(0.46, 0.016, span), mats.kraft, true, true);
    g.add(strip);
    for (const tz of [-span * 0.28, span * 0.28]) {
      const tape = addDeskMatMesh(new THREE.BoxGeometry(0.62, 0.022, 0.14), mats.crimson, false, true);
      tape.position.set(0, 0.012, tz);
      tape.rotation.y = tz > 0 ? 0.25 : -0.25;
      g.add(tape);
    }
  } else {
    // pullback_mosaic: golden framing registration rails
    const span = Math.max(0.6, len - 2.0);
    for (const ox of [-0.42, 0.42]) {
      const rail = addDeskMatMesh(new THREE.BoxGeometry(0.028, 0.012, span), mats.brass, false, true);
      rail.position.set(ox, 0.008, 0);
      g.add(rail);
    }
  }

  parent.add(g);
  void sceneData;
}

export function createForensicDesk({ scene, materials, seed = 42, scenes = [], market, origins = null }) {
  const root = new THREE.Group();
  root.name = 'vox-forensic-desk';

  const resolvedOrigins = origins || computeJourneyOrigins(scenes);
  let minX = 0, maxX = 0;
  for (const v of resolvedOrigins.values()) {
    minX = Math.min(minX, v.x);
    maxX = Math.max(maxX, v.x);
  }
  const centerX = (minX + maxX) * 0.5;
  const spanX = Math.max(48, (maxX - minX) + 46);

  // Warm dark walnut base slab
  const walnutMat = materials.paper({ color: '#1b140e', side: THREE.FrontSide });
  const baseTable = addDeskMatMesh(new THREE.BoxGeometry(spanX + 18, 0.28, 46), walnutMat, false, true);
  baseTable.position.set(centerX, -0.18, 0);
  root.add(baseTable);

  // Continuous editorial desk cutting mat covering entire S-curve journey
  const deskTex = makeDeskSurfaceTexture('heartland');
  deskTex.repeat.set(Math.max(6, Math.round(spanX / 10)), 4);
  const deskMat = new THREE.MeshLambertMaterial({
    color: new THREE.Color('#ffffff'),
    map: deskTex,
    emissive: new THREE.Color('#2a2016'),
    emissiveMap: deskTex,
    emissiveIntensity: 0.04,
  });
  deskMat.userData.noDayNightGlow = true;
  const matMesh = addDeskMatMesh(new THREE.BoxGeometry(spanX, 0.06, 28), deskMat, false, true);
  matMesh.position.set(centerX, -0.03, 0);
  root.add(matMesh);

  const paperMat = (c) => materials.paper({ color: c, side: THREE.DoubleSide });
  const mats = {
    crimson: paperMat('#c83e2b'),
    brass: paperMat('#d4a23c'),
    gold: paperMat('#e8b842'),
    highlight: paperMat('#edd04e'),
    ink: paperMat('#2a2016'),
    cream: paperMat('#eae0ca'),
    kraft: paperMat('#bfa780'),
    slate: paperMat('#6c7b88'),
    teal: paperMat('#3f7f84'),
  };

  // Brass horizon desk rulers along the rear edge of the studio table
  for (const rz of [-7.4, 7.6]) {
    const ruler = addDeskMatMesh(new THREE.BoxGeometry(spanX - 4, 0.03, 0.16), mats.brass, false, true);
    ruler.position.set(centerX, 0.015, rz);
    root.add(ruler);
  }

  let sSeed = (seed | 0) ^ 0x9e3779b9;
  const rand = () => {
    sSeed = (Math.imul(sSeed, 1664525) + 1013904223) >>> 0;
    return sSeed / 4294967296;
  };

  const pushpinCaps = [];

  // Scatter layered editorial desk dressing behind & beside every node so no frame ever feels empty
  (scenes || []).forEach((sc, idx) => {
    const o = resolvedOrigins.get(sc.id);
    if (!o) return;
    const scCtx = { ...sc, market: market || sc.market };

    // Rear angled broadsheet newspaper clippings & stacked folders (keeps r < 2.25 center open for hero plate)
    const rearSlots = [
      { dx: -1.1, dz: -2.95, w: 1.9, d: 2.3, h: 0.14, rot: (rand() - 0.5) * 0.35, clip: true },
      { dx: 1.5, dz: -3.45, w: 2.2, d: 1.65, h: 0.22, rot: (rand() - 0.5) * 0.42, stand: true },
      { dx: 0.2, dz: -4.8, w: 2.5, d: 1.85, h: 0.26, rot: (rand() - 0.5) * 0.25, clip: idx % 2 === 0 },
    ];

    rearSlots.forEach((sl, j) => {
      const folder = new THREE.Group();
      folder.position.set(o.x + sl.dx, 0.01, o.z + sl.dz);
      folder.rotation.y = sl.rot;
      root.add(folder);

      const sheets = 3;
      for (let k = 0; k < sheets; k++) {
        const shH = sl.h / sheets;
        const shMat = k === sheets - 1 ? mats.cream : (k % 2 === 0 ? mats.kraft : mats.slate);
        const sh = addDeskMatMesh(new THREE.BoxGeometry(sl.w, shH, sl.d), shMat, true, true);
        sh.position.set((rand() - 0.5) * 0.07, shH * (k + 0.5), (rand() - 0.5) * 0.07);
        folder.add(sh);
      }

      if (sl.clip) {
        const clipMat = idx % 3 === 1
          ? makeLedgerPagePrintMaterial(scCtx, 'left')
          : (idx % 3 === 2 ? makeChartBoardPrintMaterial(scCtx) : makeEditorialClippingMaterial(scCtx));
        const page = addDeskMatMesh(new THREE.PlaneGeometry(sl.w * 0.88, sl.d * 0.88), clipMat, false, true);
        page.rotation.x = -Math.PI / 2;
        page.position.set(0, sl.h + 0.012, 0);
        folder.add(page);
      }

      if (sl.stand) {
        const binder = addDeskMatMesh(new THREE.BoxGeometry(sl.w * 0.92, 0.78, 0.06), j % 2 ? mats.kraft : mats.slate, true, true);
        binder.position.set(0, sl.h + 0.39, -sl.d * 0.36);
        binder.rotation.x = -0.14;
        folder.add(binder);
      }

      // Red/brass anchor pin on first rear slot
      if (j === 0) {
        const base = addDeskMatMesh(new THREE.CylinderGeometry(0.06, 0.08, 0.05, 16), mats.brass, true, true);
        base.position.set(0, sl.h + 0.03, 0);
        const cap = addDeskMatMesh(new THREE.CylinderGeometry(0.09, 0.09, 0.045, 16), mats.crimson, true, true);
        cap.position.set(0, sl.h + 0.075, 0);
        folder.add(base, cap);
        pushpinCaps.push(cap);
      }
    });

    // Subtle foreground flank desk clippings (offset cleanly at z + 2.55 so center foreground captions remain crisp)
    if (idx % 2 === 0) {
      const fMat = makeEditorialClippingMaterial(scCtx);
      const flankSheet = addDeskMatMesh(new THREE.BoxGeometry(1.75, 0.03, 1.35), mats.kraft, true, true);
      flankSheet.position.set(o.x - 1.65, 0.015, o.z + 2.55);
      flankSheet.rotation.y = 0.28 + (rand() - 0.5) * 0.18;
      const flankPage = addDeskMatMesh(new THREE.PlaneGeometry(1.58, 1.18), fMat, false, true);
      flankPage.rotation.x = -Math.PI / 2;
      flankPage.position.set(0, 0.022, 0);
      flankSheet.add(flankPage);
      root.add(flankSheet);
    }

    // Dynamic story connector linking previous plate -> current plate
    if (idx > 0) {
      const prevSc = scenes[idx - 1];
      const prevO = resolvedOrigins.get(prevSc.id);
      if (prevO) {
        const cType = sc.connector || 'timeline_rail';
        buildConnector(root, prevO, o, cType, mats, scCtx);
      }
    }
  });

  scene.add(root);

  return {
    group: root,
    isWalkable: () => true,
    update(_dt, _pos, time) {
      const stepT = Math.floor((time || 0) * 12) / 12;
      for (let i = 0; i < pushpinCaps.length; i++) {
        pushpinCaps[i].scale.y = 1.0 + Math.sin(stepT * 2.0 + i) * 0.04;
      }
    },
  };
}
