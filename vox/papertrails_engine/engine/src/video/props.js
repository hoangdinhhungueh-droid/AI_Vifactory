import * as THREE from 'three';
import { clamp01, smooth, easeInOutCubic, easeOutBack, squashPreserveVolume, overlap, impactPulse, bezierArc } from './motion.js';
import {
  makeDocumentPrintMaterial,
  makeEditorialClippingMaterial,
  makeIllustratedCollagePlateMaterial,
  makeChartBoardPrintMaterial,
  makeLedgerPagePrintMaterial,
} from './print_textures.js';

// Extension point: add a named builder here and the same name to timeline.mjs PROPS.
// In forensic_desk mode, all scenes render lush layered Vox editorial collage plates, charts, ledgers & illustrations.
export function createProp(kind, { materials, assets, color = '#b26d42', sceneData = null, isDeskMode = false, illustrationImg = null }) {
  const root = new THREE.Group(); root.name = `subject-${kind}`;
  const anim = [];
  const paper = c => materials.paper({ color: c, side: THREE.DoubleSide });
  const mesh = (geo, c, x=0, y=0, z=0, parent=root) => {
    const m = new THREE.Mesh(geo,paper(c)); m.position.set(x,y,z); m.castShadow=true; m.receiveShadow=true; parent.add(m); return m;
  };
  const applyFace = (w, h, mat, x, y, z, parent=root, ry=0) => {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), mat);
    m.position.set(x, y, z); m.rotation.y = ry; m.receiveShadow = true; parent.add(m); return m;
  };
  const rect = (w,h,c,x,y,z=.02,parent=root) => mesh(new THREE.BoxGeometry(w,h,.045),c,x,y,z,parent);
  const disc = (r,c,x,y,z=.06,parent=root) => mesh(new THREE.CylinderGeometry(r,r,.045,48).rotateX(Math.PI/2),c,x,y,z,parent);
  const polygon = (points,c,z=.01) => {const s=new THREE.Shape(); points.forEach(([x,y],i)=>i?s.lineTo(x,y):s.moveTo(x,y));s.closePath();return mesh(new THREE.ExtrudeGeometry(s,{depth:.035,bevelEnabled:false}),c,0,0,z);};
  const line = (x,y,x2,y2,c='#554637',w=.035,z=.10) => { const m=rect(w,Math.hypot(x2-x,y2-y),c,(x+x2)/2,(y+y2)/2,z);m.rotation.z=-Math.atan2(x2-x,y2-y);return m; };
  const cream='#f1e6cf', kraft='#cbb48c', ink='#2b2016', gold='#dfb044', green='#487858', crimson='#c83e2b', slate='#212832';

  // Helper: double-sided broadsheet editorial plate
  const buildClippingPlate = (w, h, x, y, z, ry, mode = 'dossier', backing = kraft) => {
    const plate = new THREE.Group();
    plate.position.set(x, y, z);
    plate.rotation.y = ry;
    root.add(plate);
    rect(w, h, backing, 0, 0, 0, plate);
    rect(w * 0.96, h * 0.96, cream, 0, 0, 0.012, plate);
    const mat = makeEditorialClippingMaterial(sceneData, { mode });
    applyFace(w * 0.92, h * 0.92, mat, 0, 0, 0.04, plate);
    applyFace(w * 0.92, h * 0.92, mat, 0, 0, -0.03, plate, Math.PI);
    rect(0.32, 0.09, gold, -w * 0.24, h * 0.49, 0.045, plate);
    return plate;
  };

  if (isDeskMode && illustrationImg) {
    // HYBRID VOX GRAPHIC NOVEL COLLAGE DIORAMA (AI 4:3 Illustration + Overlapping Broadsheet + Kinetic Accent)
    const heroPlate = new THREE.Group();
    heroPlate.position.set(-0.34, 1.04, 0.08);
    heroPlate.rotation.y = -0.07;
    root.add(heroPlate);
    rect(2.46, 1.98, kraft, 0, 0, -0.01, heroPlate);
    rect(2.38, 1.90, cream, 0, 0, 0.015, heroPlate);
    const illMat = makeIllustratedCollagePlateMaterial(sceneData, illustrationImg);
    applyFace(2.30, 1.84, illMat, 0, 0, 0.044, heroPlate);
    applyFace(2.30, 1.84, illMat, 0, 0, -0.036, heroPlate, Math.PI);
    disc(0.11, crimson, 0, 0.92, 0.06, heroPlate);

    const sideClip = buildClippingPlate(1.52, 1.86, 1.04, 0.96, -0.14, 0.16, 'dossier', slate);

    // Subtle 3D interactive accent matching kind & contactSec
    const miniBars = [];
    for (let i = 0; i < 3; i++) {
      const h = 0.24 + i * 0.16;
      const b = rect(0.16, h, i === 1 ? crimson : gold, 0.72 + i * 0.22, 0.16 + h / 2, 0.12);
      miniBars.push({ mesh: b, h });
    }
    const stampBadge = disc(0.24, crimson, -1.08, 0.44, 0.16);
    anim.push((t, p, ctx) => {
      const stepT = Math.floor(t * 12) / 12;
      heroPlate.position.y = 1.04 + Math.sin(stepT * 1.4) * 0.025;
      sideClip.rotation.y = 0.16 + Math.sin(p * Math.PI) * 0.04;
      const cSec = ctx?.scene?.timing?.contactSec ?? 0.44;
      const pulse = impactPulse(t, cSec, 0.12, 0.14, 0.26);
      stampBadge.scale.setScalar(0.88 + 0.24 * pulse.impact);
      miniBars.forEach(({ mesh: bm, h }, idx) => {
        const g = Math.max(0.15, Math.min(1, p * 1.5 - idx * 0.12));
        bm.scale.y = g;
        bm.position.y = 0.16 + (h * g) / 2;
      });
    });
  } else if (isDeskMode) {
    // PURE EDITORIAL BRIDGE / DATA PLATES (Zero toy shapes!)
    if (['chart', 'coin', 'briefcase', 'factory', 'container'].includes(kind)) {
      buildClippingPlate(1.48, 1.72, -1.16, 0.92, -0.22, -0.22, 'dossier', kraft);
      const board = new THREE.Group();
      board.position.set(0.22, 1.02, 0.04);
      root.add(board);
      rect(2.68, 1.96, slate, 0, 0, -0.02, board);
      rect(2.58, 1.88, cream, 0, 0, 0.01, board);
      if (sceneData) {
        applyFace(2.48, 1.78, makeChartBoardPrintMaterial(sceneData), 0, 0, 0.046, board);
      }
      const xAxis = mesh(new THREE.BoxGeometry(2.14, 0.036, 0.045), ink, 0, -0.78, 0.09, board);
      const yAxis = mesh(new THREE.BoxGeometry(0.036, 1.24, 0.045), ink, -1.04, -0.16, 0.09, board);
      void xAxis; void yAxis;
      for (let i = 0; i < 4; i++) {
        const bh = 0.28 + i * 0.24;
        const bar = rect(0.28, bh, i % 2 ? crimson : gold, -0.68 + i * 0.48, -0.76 + bh / 2, 0.10, board);
        anim.push((t, p) => {
          const sy = 0.15 + 0.85 * Math.min(1, p * 1.35 - i * 0.08);
          bar.scale.y = Math.max(0.1, sy);
          bar.position.y = -0.76 + (bh * bar.scale.y) / 2;
        });
      }
      const trend = mesh(new THREE.BoxGeometry(0.055, 1.66, 0.045), green, 0.05, -0.04, 0.14, board);
      trend.rotation.z = -1.08;
    } else if (['ledger', 'scale', 'shield', 'courthouse', 'gavel'].includes(kind)) {
      rect(2.48, 1.98, ink, 0, 1.02, -0.04);
      rect(1.14, 1.84, cream, -0.59, 1.04, 0.01);
      rect(1.14, 1.84, cream, 0.59, 1.04, 0.01);
      if (sceneData) {
        applyFace(1.08, 1.76, makeLedgerPagePrintMaterial(sceneData, 'left'), -0.59, 1.04, 0.044);
        applyFace(1.08, 1.76, makeLedgerPagePrintMaterial(sceneData, 'right'), 0.59, 1.04, 0.044);
      }
      rect(0.08, 1.88, ink, 0, 1.04, 0.05);
      for (let i = 0; i < 4; i++) {
        const w = 0.34 + ((i * 37) % 48) / 100;
        const bar = rect(w, 0.10, i % 2 ? crimson : green, -1.02 + w / 2, 1.54 - i * 0.28, 0.074);
        anim.push((t, p) => { bar.scale.x = Math.max(0.12, Math.min(1, p * 1.6 - i * 0.12)); });
      }
      const sweep = new THREE.Mesh(
        new THREE.BoxGeometry(0.92, 0.13, 0.02),
        new THREE.MeshBasicMaterial({ color: '#f0c83c', transparent: true, opacity: 0.52 })
      );
      sweep.position.set(0.59, 1.48, 0.07);
      root.add(sweep);
      const seal = disc(0.22, crimson, 0.86, 0.38, 0.09);
      anim.push((t, p, ctx) => {
        const cSec = ctx?.scene?.timing?.contactSec ?? 0.44;
        sweep.position.y = 1.48 - ((Math.floor(t * 1.8) % 4) * 0.26);
        const pulse = impactPulse(t, cSec, 0.12, 0.14, 0.24);
        seal.scale.setScalar(0.85 + 0.22 * pulse.impact);
      });
    } else if (['hanko-stamp', 'brass-caliper', 'forensic-loupe', 'clock', 'vault'].includes(kind)) {
      buildClippingPlate(2.26, 1.92, 0, 1.02, -0.02, 0, kind === 'hanko-stamp' ? 'stamp' : 'dossier', kraft);
      if (kind === 'hanko-stamp') {
        const imprint = new THREE.Group(); imprint.position.set(0.56, 0.56, 0.075); root.add(imprint);
        imprint.add(new THREE.Mesh(new THREE.RingGeometry(0.20, 0.27, 32), paper(crimson)));
        rect(0.05, 0.22, crimson, 0, 0, 0.01, imprint); rect(0.18, 0.04, crimson, 0, 0.04, 0.01, imprint);
        const stamper = new THREE.Group(); stamper.position.set(0.56, 0.56, 0.14); root.add(stamper);
        rect(0.44, 0.44, gold, 0, 0, 0, stamper);
        rect(0.34, 0.34, crimson, 0, 0, 0.04, stamper);
        mesh(new THREE.CylinderGeometry(0.14, 0.18, 0.64, 24).rotateX(Math.PI / 2), '#6e1e19', 0, 0, 0.36, stamper);
        anim.push((t, p, ctx) => {
          const pulse = impactPulse(t, ctx?.scene?.timing?.contactSec ?? 0.44, 0.14, 0.14, 0.28);
          stamper.position.z = 0.14 + 0.46 * pulse.lift + (1 - pulse.impact) * 0.30;
          const rev = overlap(t, ctx?.scene?.timing?.contactSec ?? 0.44, 0.02, 0.18);
          imprint.visible = rev > 0.01;
          imprint.scale.setScalar(Math.max(0.01, easeOutBack(rev)));
        });
      } else if (kind === 'brass-caliper') {
        const rail = rect(1.88, 0.13, gold, 0, 1.38, 0.10);
        for (let i = 0; i < 9; i++) rect(0.025, 0.07, ink, -0.76 + i * 0.19, 0, 0.04, rail);
        const lJaw = new THREE.Group(); lJaw.position.set(-0.28, 1.02, 0.12); root.add(lJaw);
        rect(0.13, 0.82, gold, 0, 0, 0, lJaw); rect(0.24, 0.14, gold, 0.11, -0.34, 0.02, lJaw);
        const rJaw = new THREE.Group(); rJaw.position.set(0.56, 1.02, 0.12); root.add(rJaw);
        rect(0.13, 0.82, gold, 0, 0, 0, rJaw); rect(0.24, 0.14, gold, -0.11, -0.34, 0.02, rJaw);
        anim.push((t, p, ctx) => {
          const pulse = impactPulse(t, ctx?.scene?.timing?.contactSec ?? 0.46, 0.14, 0.15, 0.28);
          rJaw.position.x = 0.56 + 0.34 * pulse.lift + 0.28 * (1 - pulse.impact);
        });
      } else if (kind === 'forensic-loupe') {
        const loupe = new THREE.Group(); loupe.position.set(-0.55, 1.35, 0.26); root.add(loupe);
        loupe.add(new THREE.Mesh(new THREE.RingGeometry(0.36, 0.46, 36), paper(gold)));
        const lens = disc(0.35, '#dcebf2', 0, 0, -0.01, loupe);
        lens.material.transparent = true; lens.material.opacity = 0.34;
        const handle = rect(0.10, 0.66, ink, 0.38, -0.38, 0, loupe);
        handle.rotation.z = Math.PI / 4;
        anim.push((t, p, ctx) => {
          const cSec = ctx?.scene?.timing?.contactSec ?? 0.46;
          const moveU = easeInOutCubic(clamp01(t / Math.max(0.18, cSec)));
          const pos = bezierArc({ x: -0.58, y: 1.35, z: 0.28 }, { x: 0.24, y: 0.82, z: 0.20 }, 0.32, moveU);
          loupe.position.set(pos.x, pos.y, pos.z);
        });
      } else {
        // vault / clock editorial plate + metallic dial emblem
        const wheel = new THREE.Group(); wheel.position.set(0.62, 0.58, 0.11); root.add(wheel);
        disc(0.38, slate, 0, 0, -0.02, wheel);
        disc(0.30, gold, 0, 0, 0.01, wheel);
        for (let i = 0; i < 6; i++) {
          const sp = rect(0.05, 0.44, cream, 0, 0, 0.03, wheel);
          sp.rotation.z = (i * Math.PI) / 3;
        }
        anim.push((t) => { wheel.rotation.z = Math.sin(t * 1.4) * 1.2; });
      }
    } else {
      // Layered Broadsheet Newspaper Spread with animated golden highlighter bar
      buildClippingPlate(1.42, 1.72, -1.04, 0.94, -0.18, -0.22, 'dossier', slate);
      const mainPaper = buildClippingPlate(2.24, 1.98, 0.18, 1.04, 0.04, 0.05, 'dossier', kraft);
      const hiBar = new THREE.Mesh(
        new THREE.BoxGeometry(1.56, 0.16, 0.02),
        new THREE.MeshBasicMaterial({ color: '#f4ce42', transparent: true, opacity: 0.48 })
      );
      hiBar.position.set(-0.04, 0.16, 0.065);
      mainPaper.add(hiBar);
      const pin = disc(0.11, crimson, 0, 0.90, 0.07, mainPaper);
      void pin;
      anim.push((t, p) => {
        const sweep = clamp01(p * 1.8);
        hiBar.scale.x = Math.max(0.05, easeInOutCubic(sweep));
        hiBar.position.x = -0.82 + 0.78 * hiBar.scale.x;
      });
    }
    return { group: root, update(time, progress, action, ctx = {}) {
      const open = action === 'reveal' ? easeOutBack(clamp01(progress / 0.42)) : 1;
      root.rotation.x = -(1 - open) * 0.22;
      if (action === 'grow') {
        const gu = easeOutBack(clamp01(progress / 0.36));
        root.scale.setScalar(0.84 + 0.16 * gu);
      } else {
        root.scale.setScalar(1);
      }
      root.position.y = action === 'celebrate' ? Math.abs(Math.sin(time * 4)) * 0.08 : 0;
      for (const fn of anim) fn(time, Math.min(1, progress * 2), ctx);
    }};
  }

  // Legacy upstream storybook paths (used ONLY when stageMode === 'storybook')
  const tile = {village:'village',forest:'forest',house:'house',tree:'grove',bridge:'bridge',mountain:'hills',water:'pond'}[kind];
  if (tile && assets && typeof assets.getTilePrototype === 'function') {
    const t=assets.getTilePrototype(tile).clone(true); t.scale.setScalar({village:2.2,house:2.0,forest:1.6}[kind]||1.4);
    t.traverse(o=>{if(/^base/i.test(o.name))o.visible=false; if(o.userData.hinge)o.rotation.x=0;});root.add(t);
    const pieces=[];t.traverse(o=>{if(o.isMesh&&o.visible&&!/^base/i.test(o.name))pieces.push(o);});
    pieces.forEach((m,i)=>{m.userData.baseScale=m.scale.clone();m.userData.order=(i*0.618)%1;});
    root.userData.grow=(p)=>{for(const m of pieces){const k=THREE.MathUtils.smoothstep(p*1.35-m.userData.order*.55,0,.45);const o=1+.18*Math.sin(Math.min(1,k)*Math.PI);const sc=Math.max(.001,k*o);m.scale.set(m.userData.baseScale.x*sc,m.userData.baseScale.y*sc,m.userData.baseScale.z*sc);}};
  } else if (tile) {
    buildClippingPlate(1.85, 1.45, 0, 0.94, 0, 0, 'dossier', color);
  } else if (kind==='book') {
    for(const sign of [-1,1]) {
      const leaf=new THREE.Group();root.add(leaf);leaf.rotation.y=sign*.22;
      rect(1.12,1.55,color,sign*.57,.9,0,leaf);rect(1.04,1.43,cream,sign*.57,.92,.04,leaf);
      if (sign > 0 && sceneData) {
        applyFace(.96, 1.35, makeDocumentPrintMaterial(sceneData, { mode: 'dossier' }), sign*.57, .92, .068, leaf);
      } else {
        for(let i=0;i<6;i++)rect(.74,.025,'#b5a58a',sign*.57,1.38-i*.15,.08,leaf);
      }
      anim.push((time,p)=>leaf.rotation.y=sign*(.12+.58*(1-p)));
    }
    rect(.08,1.6,ink,0,.9,.01);
  } else if (kind==='coin') {
    for(let i=0;i<3;i++){const c=disc(.58,gold,(i-1)*.64,.68+i*.16,.1*i);disc(.47,'#c88e35',(i-1)*.64,.68+i*.16,.1*i+.03);rect(.075,.5,cream,(i-1)*.64,.68+i*.16,.1*i+.08);anim.push((t)=>c.rotation.y=Math.sin(t*1.8+i)*.25);}
  } else if (kind==='chart') {
    rect(2.6,1.9,cream,0,1);
    if (sceneData) {
      applyFace(2.44, 1.76, makeChartBoardPrintMaterial(sceneData), 0, 1, .048);
    }
    line(-1.05,.2,-1.05,1.46);line(-1.05,.2,1.1,.2);
    for(let i=0;i<4;i++){const h=.30+i*.25;const bar=rect(.3,h,i%2?gold:color,-.7+i*.5,.22+h/2,.1);anim.push((t,p)=>{bar.scale.y=.12+.88*p;bar.position.y=.22+h*bar.scale.y/2;});}
    line(-.72,.62,.85,1.42,green,.06,.15);
  } else if (kind==='factory') {
    polygon([[-1.3,0],[1.3,0],[1.3,1.1],[.5,.8],[.5,1.25],[-.3,.9],[-.3,1.3],[-1.3,.9]],color);
    rect(.3,1.9,ink,.85,.95,-.06);
  } else {
    buildClippingPlate(2.0, 1.7, 0, 1.0, 0, 0, 'dossier', color);
  }
  return { group:root, update(time, progress, action, ctx={}) {
    const tileGrow=!!root.userData.grow&&(action==='grow'||action==='reveal');
    const open=action==='reveal'&&!tileGrow?easeOutBack(clamp01(progress/.42)):1;
    root.rotation.x=-(1-open)*Math.PI/2;
    if(root.userData.grow)root.userData.grow(tileGrow?Math.min(1,progress*1.6):1);
    if(action==='grow'&&!root.userData.grow){
      const gu=easeOutBack(clamp01(progress/.36));
      const sq=squashPreserveVolume(1+.12*Math.sin(Math.min(1,progress/.36)*Math.PI)*(1-clamp01(progress/.36)));
      root.scale.set(Math.max(.001,gu)*sq.sx,Math.max(.001,gu)*sq.sy,Math.max(.001,gu)*sq.sz);
    } else root.scale.setScalar(1);
    root.position.y=action==='celebrate'?Math.abs(Math.sin(time*4))*.2:0;
    for(const fn of anim)fn(time,Math.min(1,progress*2),ctx);
  }};
}
