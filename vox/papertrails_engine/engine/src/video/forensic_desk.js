import * as THREE from 'three';
import { makeDeskSurfaceTexture, makeDocumentPrintMaterial } from './print_textures.js';

const STATION_COORDS = {
  heartland: [0, 0],
  desert: [22, 0],
  snow: [-22, 0],
  blossom: [0, 22],
  pinewood: [0, -22],
};

function makeStationRng(seed, salt) {
  let s = ((seed | 0) ^ (salt * 2654435761)) >>> 0;
  return () => {
    s = (Math.imul(s, 1664525) + 1013904223) >>> 0;
    return s / 4294967296;
  };
}

function addEvidenceThread(parent, a, b, mat) {
  const dir = new THREE.Vector3().subVectors(b, a);
  const len = dir.length();
  if (len < 0.05) return;
  const geo = new THREE.CylinderGeometry(0.015, 0.015, len, 8);
  const mesh = new THREE.Mesh(geo, mat);
  mesh.position.copy(a).add(b).multiplyScalar(0.5);
  mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.normalize());
  mesh.castShadow = true;
  parent.add(mesh);
}

export function createForensicDesk({ scene, materials, seed = 42, scenes = [] }) {
  const root = new THREE.Group();
  root.name = 'vox-forensic-desk';

  // Expansive warm dark walnut studio desk base under all 5 station mats
  const tableGeo = new THREE.BoxGeometry(108, 0.24, 108);
  const tableMat = materials.paper({ color: '#2b2118', side: THREE.FrontSide });
  const tableMesh = new THREE.Mesh(tableGeo, tableMat);
  tableMesh.position.set(0, -0.14, 0);
  tableMesh.receiveShadow = true;
  root.add(tableMesh);

  const paperMat = c => materials.paper({ color: c, side: THREE.DoubleSide });
  const redThreadMat = paperMat('#c83e2b');
  const brassMat = paperMat('#d8a740');
  const inkMat = paperMat('#3c3024');
  const creamMat = paperMat('#f3ead6');
  const kraftMat = paperMat('#c9b58e');
  const slateMat = paperMat('#bcc6ce');

  const sceneByBiome = {};
  for (const s of scenes || []) {
    if (s && s.biome && !sceneByBiome[s.biome]) sceneByBiome[s.biome] = s;
  }

  const pushpinCaps = [];

  Object.entries(STATION_COORDS).forEach(([biome, [ox, oz]], bIdx) => {
    const station = new THREE.Group();
    station.name = `desk-station-${biome}`;
    station.position.set(ox, 0, oz);
    root.add(station);

    const rand = makeRngSafe(seed, bIdx + 1);
    const deskTex = makeDeskSurfaceTexture(biome);
    const matGeo = new THREE.BoxGeometry(19.5, 0.06, 19.5);
    const matMaterial = new THREE.MeshLambertMaterial({ map: deskTex });
    const matMesh = new THREE.Mesh(matGeo, matMaterial);
    matMesh.position.set(0, -0.025, 0);
    matMesh.receiveShadow = true;
    station.add(matMesh);

    // Subtle brass corner rulers bordering the workspace edge
    for (const [rx, rz, rw, rd] of [[0, -8.8, 17.6, 0.16], [-8.8, 0, 0.16, 17.6]]) {
      const ruler = new THREE.Mesh(new THREE.BoxGeometry(rw, 0.03, rd), brassMat);
      ruler.position.set(rx, 0.02, rz);
      ruler.receiveShadow = true;
      station.add(ruler);
    }

    // Dossier stacks arranged in rear/flank semicircular arc (keeping r < 2.6 center completely open!)
    const stackSpecs = [
      { ang: Math.PI * 0.72, r: 3.4, w: 1.5, d: 1.9, h: 0.16, tab: true },
      { ang: Math.PI * 0.88, r: 4.1, w: 1.8, d: 1.35, h: 0.24, print: true },
      { ang: Math.PI * 1.06, r: 4.4, w: 1.7, d: 2.1, h: 0.20, tab: true },
      { ang: Math.PI * 1.24, r: 3.8, w: 1.6, d: 1.4, h: 0.15, print: true },
      { ang: Math.PI * 1.42, r: 3.3, w: 1.4, d: 1.8, h: 0.22, tab: true },
      { ang: Math.PI * 0.56, r: 4.8, w: 2.0, d: 1.5, h: 0.28, standing: true },
      { ang: Math.PI * 1.54, r: 4.9, w: 1.9, d: 1.5, h: 0.26, standing: true },
      { ang: Math.PI * 0.96, r: 6.2, w: 2.3, d: 1.7, h: 0.32, standing: true },
    ];

    const stationPins = [];
    const sampleSc = sceneByBiome[biome] || (scenes && scenes[bIdx]) || null;

    stackSpecs.forEach((sp, sIdx) => {
      const x = Math.sin(sp.ang) * sp.r;
      const z = Math.cos(sp.ang) * sp.r;
      const folder = new THREE.Group();
      folder.position.set(x, 0.01, z);
      folder.rotation.y = (rand() - 0.5) * 0.45;
      station.add(folder);

      const sheets = 3;
      for (let k = 0; k < sheets; k++) {
        const shH = sp.h / sheets;
        const shMat = k === sheets - 1 ? creamMat : (k % 2 === 0 ? kraftMat : slateMat);
        const sheet = new THREE.Mesh(new THREE.BoxGeometry(sp.w, shH, sp.d), shMat);
        sheet.position.set((rand() - 0.5) * 0.08, shH * (k + 0.5), (rand() - 0.5) * 0.08);
        sheet.rotation.y = (rand() - 0.5) * 0.12;
        sheet.castShadow = true;
        sheet.receiveShadow = true;
        folder.add(sheet);
      }

      if (sp.tab) {
        const tab = new THREE.Mesh(new THREE.BoxGeometry(sp.w * 0.36, 0.04, 0.22), sIdx % 2 ? redThreadMat : brassMat);
        tab.position.set(-sp.w * 0.24, sp.h + 0.02, -sp.d * 0.45);
        tab.castShadow = true;
        folder.add(tab);
      }

      if (sp.print && sampleSc) {
        const pageMat = makeDocumentPrintMaterial(sampleSc, { mode: 'dossier' });
        const page = new THREE.Mesh(new THREE.PlaneGeometry(sp.w * 0.88, sp.d * 0.88), pageMat);
        page.rotation.x = -Math.PI / 2;
        page.position.set(0, sp.h + 0.012, 0);
        page.receiveShadow = true;
        folder.add(page);
      }

      if (sp.standing) {
        const divider = new THREE.Mesh(new THREE.BoxGeometry(sp.w * 0.9, 0.85, 0.05), sIdx % 2 ? kraftMat : creamMat);
        divider.position.set(0, sp.h + 0.42, -sp.d * 0.35);
        divider.rotation.x = -0.14;
        divider.castShadow = true;
        divider.receiveShadow = true;
        folder.add(divider);
      }

      // Red pushpin anchoring evidence thread on top of stack
      const pin = new THREE.Group();
      pin.position.set(0, sp.h + 0.05, 0);
      const pinBase = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.08, 0.06, 16), brassMat);
      const pinCap = new THREE.Mesh(new THREE.CylinderGeometry(0.09, 0.09, 0.05, 16), redThreadMat);
      pinCap.position.y = 0.05;
      pin.add(pinBase, pinCap);
      folder.add(pin);
      pushpinCaps.push(pinCap);

      stationPins.push(new THREE.Vector3(x, sp.h + 0.10, z));
    });

    // Connect surrounding dossier stacks with taut red evidence yarn
    for (let i = 0; i < stationPins.length - 1; i++) {
      addEvidenceThread(station, stationPins[i], stationPins[i + 1], redThreadMat);
    }
    if (stationPins.length >= 5) {
      addEvidenceThread(station, stationPins[0], stationPins[4], redThreadMat);
      addEvidenceThread(station, stationPins[1], stationPins[5], redThreadMat);
    }

    // Subtle dark vertical archival backdrop binder strips far behind camera horizon
    const rim = new THREE.Mesh(new THREE.BoxGeometry(19.5, 0.4, 0.25), inkMat);
    rim.position.set(0, 0.18, -9.6);
    rim.castShadow = true;
    station.add(rim);
  });

  scene.add(root);

  return {
    group: root,
    isWalkable: () => true,
    update(_dt, _pos, time) {
      // Subtle 12fps living pin shimmer without modifying world structure
      const stepT = Math.floor((time || 0) * 12) / 12;
      for (let i = 0; i < pushpinCaps.length; i++) {
        pushpinCaps[i].scale.y = 1.0 + Math.sin(stepT * 2.0 + i) * 0.04;
      }
    },
  };
}

function makeRngSafe(seed, salt) {
  return makeStationRng(seed, salt);
}
