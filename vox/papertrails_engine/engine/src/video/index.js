import * as THREE from 'three';
import { state } from '../core/state.js';
import { CONFIG } from '../core/config.js';
import { biomeAt } from '../core/biomes.js';
import { loadAssets } from '../assets/loader.js';
import { createMaterials } from '../render/materials.js';
import { createRenderer } from '../render/renderer.js';
import { createLights } from '../render/lights.js';
import { createDayNight } from '../render/daynight.js';
import { createPost } from '../render/post.js';
import { createWFC } from '../world/wfc.js';
import { createWorld } from '../world/world.js';
import { createTraveller } from '../player/traveller.js';
import { createForensicDesk, computeJourneyOrigins } from './forensic_desk.js';
import { createProp } from './props.js';
import { preloadIllustrationImages } from './print_textures.js';
import { validateTimeline, sampleTimeline, seededRandom, frameCount } from './timeline.mjs';
import { smooth, easeInOutCubic, easeOutBack } from './motion.js';

// Torn paper edge for the caption strip, deterministic per caption (seeded by its start time).
function tornClip(seed) {
  let s = Math.floor(seed * 1000) + 7; const r = () => ((s = (s * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff);
  const top = [], bottom = [];
  for (let i = 0; i <= 24; i++) { const x = i / 24 * 100; top.push(`${x.toFixed(2)}% ${(r() * 7).toFixed(2)}%`); bottom.push(`${(100 - x).toFixed(2)}% ${(100 - r() * 7).toFixed(2)}%`); }
  return `polygon(${top.join(',')},${bottom.join(',')})`;
}

const BEAT_STUDIO_MOOD = {
  1: { bg: '#8c6f4b', fadeA: '#9d7f57', fadeB: '#856a49' },
  2: { bg: '#967c5a', fadeA: '#a78c66', fadeB: '#8d7453' },
  3: { bg: '#7b8792', fadeA: '#8b97a2', fadeB: '#737f8a' },
  4: { bg: '#5b6c80', fadeA: '#6a7c91', fadeB: '#526275' },
  5: { bg: '#86725d', fadeA: '#96816b', fadeB: '#7c6955' },
};

let runtime;
window.__papertrails = {
  ready: true,
  async init(timeline, options = {}) {
    if(runtime) throw new Error('Already initialized; reload the page to reset deterministic state');
    validateTimeline(timeline);
    const isDeskMode = timeline.stageMode === 'forensic_desk';
    const quality=options.quality || 'med';
    const allowSeek=!!options.allowSeek;
    if(!['low','vox','med','high'].includes(quality))throw new Error('Invalid quality');
    const envelope=Array.isArray(options.envelope)?options.envelope:null;
    const levelAt=time=>{if(!envelope||!envelope.length)return null;const i=Math.min(envelope.length-1,Math.max(0,Math.round(time*timeline.fps)));return envelope[i];};
    Math.random=seededRandom(timeline.seed);
    state.seed=timeline.seed;state.quality=quality;state.time=0;state.frame=0;
    const scene=new THREE.Scene();
    const { renderer, setSize }=createRenderer({canvas:document.querySelector('#atlas'),quality});
    setSize(timeline.width,timeline.height);
    const materials=createMaterials({quality});
    const assets = isDeskMode
      ? { source: 'forensic_desk_3d', textures: null }
      : await loadAssets({materials,renderer,quality});
    if(assets.textures) materials.setTextures(assets.textures);
    if(!isDeskMode && assets.source!=='gltf')throw new Error(`Required upstream glTF assets missing: ${assets.source}`);
    const illustrationImgs = await preloadIllustrationImages(timeline.illustrations || {});
    const sceneIdxMap = new Map(timeline.scenes.map((s, idx) => [s.id, idx]));
    const journeyOrigins = isDeskMode ? computeJourneyOrigins(timeline.scenes) : null;
    const desk = isDeskMode ? createForensicDesk({ scene, materials, seed: timeline.seed, scenes: timeline.scenes, market: timeline.market, origins: journeyOrigins }) : null;
    const wfc = isDeskMode ? null : createWFC({seed:timeline.seed});
    const world = isDeskMode ? desk : createWorld({scene,assets,wfc,materials,quality});
    const traveller = isDeskMode
      ? {
          position: new THREE.Vector3(),
          moveDir: new THREE.Vector3(0, 0, 1),
          speed: 0,
          group: new THREE.Group(),
          teleport(x, z) { this.position.set(x, 0, z); this.group.position.set(x, 0, z); },
          update() {},
        }
      : createTraveller({scene,assets,world,materials});
    const camera=new THREE.PerspectiveCamera(37,timeline.width/timeline.height,.05,250);
    const lights=createLights({scene,quality});const daynight=createDayNight({scene});
    const post=createPost({renderer,scene,camera,quality});post.setSize(timeline.width,timeline.height);
    const origins=isDeskMode
      ? journeyOrigins
      : new Map(timeline.scenes.map(s=>{
          const preferred={heartland:[0,0],desert:[22,0],snow:[-22,0],blossom:[0,22],pinewood:[0,-22]}[s.biome];
          for(let r=0;r<=14;r+=2)for(let i=0;i<16;i++){const x=preferred[0]+Math.cos(i*Math.PI/8)*r,z=preferred[1]+Math.sin(i*Math.PI/8)*r;if(biomeAt(timeline.seed,x/2,z/2)===s.biome&&world.isWalkable(x-1.2,z+1.3))return [s.id, new THREE.Vector3(x,0,z)];}
          return [s.id, new THREE.Vector3(preferred[0],0,preferred[1])];
        }));
    const subjects=new Map();
    for(const s of timeline.scenes){
      const illImg = s.illustrationKey ? (illustrationImgs.get(s.illustrationKey) || null) : null;
      const prop=createProp(s.prop,{materials,assets,color:s.color,sceneData:{...s,market:timeline.market},isDeskMode,illustrationImg:illImg});
      const o=origins.get(s.id);
      if (isDeskMode && o) prop.group.position.copy(o);
      prop.group.visible=false;
      scene.add(prop.group);
      subjects.set(s.id,prop);
    }
    const sides=new Map();{let prev=null,k=0;for(const s of timeline.scenes){k=prev&&prev.biome===s.biome?k+1:0;sides.set(s.id,[.32,-.44,.75,-.78][k%4]);prev=s;}}
    let active=null,lastFrame=-1;
    const focus=new THREE.Vector3();

    function computePoseForScene(s, progress) {
      const origin = origins.get(s.id);
      const side = sides.get(s.id) ?? .32;
      const p = easeInOutCubic(progress);
      const portrait = timeline.height > timeline.width;
      const k = portrait ? 1.27 : 1;
      const foc = origin.clone();
      foc.y = isDeskMode ? 0.96 : 0.9;
      let dist = 9, height = .68, angle = side;
      if (isDeskMode) {
        // Gentle editorial desk framing showing hero plate + neighboring connected dossiers
        angle = (side * 0.45);
        switch (s.camera) {
          case 'close': dist = 5.9 - 0.35 * p; height = .42; angle += 0.08 * p; break;
          case 'wide': dist = 7.8 - 0.40 * p; height = .48; angle += 0.06 * Math.sin(p * Math.PI); break;
          case 'orbit': dist = 6.7; height = .44; angle += -0.10 + p * 0.28; break;
          case 'push': dist = 7.4 - 1.5 * p; height = .48 - 0.08 * p; break;
          case 'low': dist = 5.6 - 0.35 * p; height = .32; angle += 0.10 * p; foc.y = 1.02; break;
          case 'crane': dist = 7.1; height = .36 + .28 * p; break;
        }
        if (s.connector === 'pullback_mosaic') dist = Math.max(dist, 7.6 + 0.6 * p);
      } else {
        switch(s.camera){
          case 'close': dist=6.8-0.45*p; angle=side+0.10*p; break;
          case 'wide': dist=11-0.55*p; angle=side+0.08*Math.sin(p*Math.PI); break;
          case 'orbit': angle=side+.14+p*.45; break;
          case 'push': dist=10.5-4.2*p; height=.62-.12*p; break;
          case 'low': dist=5.4-.5*p; height=.42; angle=side+.12*p; foc.y=1.18; break;
          case 'crane': dist=8.5; height=.22+.72*p; break;
        }
      }
      if (isDeskMode && !portrait && s.card && (s.card.side === 'left' || s.card.side === 'right')) {
        dist = Math.max(dist, 6.6);
      }
      const d = dist * k;
      const pos = new THREE.Vector3();
      if (s.camera === 'top') pos.set(origin.x + .01 + Math.sin(p * Math.PI) * .45, (13 - 0.7 * p) * (portrait ? 1.2 : 1), origin.z + 2);
      else pos.set(origin.x + Math.sin(angle) * d, Math.max(1.15, d * height), origin.z + Math.cos(angle) * d);
      if (isDeskMode && !portrait && s.card && (s.card.side === 'left' || s.card.side === 'right')) {
        const rightX = Math.cos(angle), rightZ = -Math.sin(angle);
        const shift = s.card.side === 'left' ? -1.55 : 1.55;
        foc.x += rightX * shift;
        foc.z += rightZ * shift;
        pos.x += rightX * shift * 0.58;
        pos.z += rightZ * shift * 0.58;
      }
      return { pos, foc };
    }

    function updateCamera(sample) {
      const s = sample.scene;
      const curPose = computePoseForScene(s, sample.progress);
      const idx = sceneIdxMap.get(s.id) ?? 0;
      if (isDeskMode && idx > 0 && sample.local < 0.55) {
        const prevScene = timeline.scenes[idx - 1];
        const prevPose = computePoseForScene(prevScene, 1.0);
        const u = easeInOutCubic(sample.local / 0.55);
        camera.position.lerpVectors(prevPose.pos, curPose.pos, u);
        focus.lerpVectors(prevPose.foc, curPose.foc, u);
      } else {
        camera.position.copy(curPose.pos);
        focus.copy(curPose.foc);
      }
      camera.lookAt(focus); camera.updateMatrixWorld();
      const right = new THREE.Vector3().setFromMatrixColumn(camera.matrixWorld, 0);
      state.listener.rightX = right.x; state.listener.rightZ = right.z;
    }

    function applyDeskStudioMood(s) {
      const beat = BEAT_STUDIO_MOOD[s.beat || 1] || BEAT_STUDIO_MOOD[1];
      CONFIG.lights.background = beat.bg;
      CONFIG.lights.fade.color = beat.fadeA;
      CONFIG.lights.fade.colorRight = beat.fadeB;
      CONFIG.lights.fade.start = 11.5;
      CONFIG.lights.fade.end = 26.0;
      CONFIG.lights.fade.amount = 0.72;
      CONFIG.lights.key.intensity = s.night ? 2.55 : 2.85;
      CONFIG.lights.fill.intensity = s.night ? 1.10 : 1.20;
      CONFIG.lights.hemi.intensity = 0.62;
      CONFIG.post.bloom = 0.06;
      CONFIG.post.vignette = 0.12;
      CONFIG.post.exposure = 0.88;
      CONFIG.post.closeExposure = 0.94;
      CONFIG.dof.maxBlurPx = 4.0;
    }

    function syncVisibleNeighborhood(curId) {
      if (!isDeskMode) {
        for (const [id, p] of subjects.entries()) p.group.visible = (id === curId);
        return;
      }
      const curIdx = sceneIdxMap.get(curId) ?? 0;
      for (const s of timeline.scenes) {
        const idx = sceneIdxMap.get(s.id) ?? 0;
        const prop = subjects.get(s.id);
        const vis = Math.abs(idx - curIdx) <= 3;
        prop.group.visible = vis;
        if (vis && s.id !== curId) {
          prop.update(1.5, 1.0, 'idle', { time: state.time, scene: s });
          prop.group.rotation.y = Math.sin(idx * 0.8) * 0.14;
        }
      }
    }

    function enter(sample) {
      const s=sample.scene,origin=origins.get(s.id);
      active=s.id;
      syncVisibleNeighborhood(s.id);
      traveller.teleport(origin.x, origin.z, 1, -.2);
      daynight.grade.force(s.biome);daynight.set(s.night,true);
      updateCamera(sample);
      if (!isDeskMode) {
        for(let i=0;i<90;i++){state.time=-3+i/30;world.update(1/30,traveller.position,traveller.moveDir);}
      }
    }
    const elTitle=document.querySelector('#title'),elCap=document.querySelector('#caption'),elWrap=document.querySelector('#capwrap'),elWipe=document.querySelector('#wipe');
    const cuts=timeline.scenes.slice(1).map(s=>s.start);
    let capKey=null;
    const elCard=document.querySelector('#card');let cardKey=null;
    const esc=t=>t.replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
    const inline=t=>esc(t).replace(/`([^`]+)`/g,'<code>$1</code>');
    function cardOverlay(sample){
      const c=sample.scene.card;
      if(!c){if(cardKey!==null){elCard.style.display='none';elCard.innerHTML='';cardKey=null;}return;}
      if(cardKey!==sample.scene.id){
        cardKey=sample.scene.id;elCard.className=c.side||'right';elCard.style.display='flex';
        if(c.kind==='note')elCard.innerHTML=`<div class="note${c.big?' big':''}">${c.head?`<h3>${inline(c.head)}</h3>`:''}${(c.lines||[]).map((l,i)=>`<div class="ln" data-i="${i}">${c.numbered===false?'':`<span class="dot">${i+1}</span>`}<span>${inline(l)}</span></div>`).join('')}</div>`;
        else{const h=c.hl;elCard.innerHTML=`<div class="photo"><div class="ph"><img src="${c.img}">${h?`<svg viewBox="0 0 100 ${100*(c.aspect||0.5625)}" preserveAspectRatio="none"><ellipse cx="${(h[0]+h[2]/2)*100}" cy="${(h[1]+h[3]/2)*100*(c.aspect||0.5625)}" rx="${h[2]*62}" ry="${h[3]*62*(c.aspect||0.5625)}" fill="none" stroke="#d2321f" stroke-width="0.9" stroke-linecap="round" pathLength="100" stroke-dasharray="100" stroke-dashoffset="100"/></svg>`:''}</div>${c.caption?`<div class="cap">${esc(c.caption)}</div>`:''}${c.badge?`<div class="stamp">${esc(c.badge)}</div>`:''}</div>`;}
      }
      const t=sample.local,dur=sample.scene.end-sample.scene.start,box=elCard.firstElementChild;
      const k=easeOutBack(t/.5);box.style.transform=`translateY(${((1-smooth(t/.35))*12).toFixed(2)}vh) rotate(${(Math.sin(sample.scene.start*2.3)*1.6).toFixed(2)}deg) scale(${(.88+.12*k).toFixed(3)})`;box.style.opacity=String(smooth(t/.25));
      if(c.kind==='note')elCard.querySelectorAll('.ln').forEach(el=>{const i=+el.dataset.i,n=(c.lines||[]).length,at=c.lineAt?.[i]??(.35+i*Math.min(1.1,(dur*.65)/Math.max(1,n)));const v=smooth((t-at)/.3);el.style.opacity=String(v);el.style.transform=`translateX(${((1-v)*1.2).toFixed(2)}em)`;});
      else{const e=elCard.querySelector('ellipse'),st=elCard.querySelector('.stamp'),hat=c.hlAt??.9;if(e)e.setAttribute('stroke-dashoffset',String(100*(1-smooth((t-hat)/.6))));if(st){const v=smooth((t-(c.badgeAt??hat+.5))/.18);st.style.opacity=String(v);st.style.transform=`rotate(8deg) scale(${(1.6-.6*v).toFixed(3)})`;}}
    }
    function overlays(sample,time){
      const s=sample.scene;cardOverlay(sample);
      if(elTitle.textContent!==s.title)elTitle.textContent=s.title;
      const tk=easeOutBack(sample.local/.45);
      elTitle.style.transform=`translateY(${(1-smooth(sample.local/.3))*-1.2}em) rotate(${(-2+1.2*Math.sin(s.start*3.1)).toFixed(2)}deg) scale(${(.85+.15*tk).toFixed(3)})`;
      elTitle.style.opacity=String(smooth(sample.local/.25));
      const text=sample.caption||'';
      elWrap.classList.toggle('empty',!text);
      const tokens=text.split(/\s+/).filter(Boolean),words=sample.captionWords;
      const timed=words&&words.length===tokens.length;
      const key=`${sample.captionStart}|${text}`;
      if(key!==capKey){
        capKey=key;elCap.textContent='';
        if(timed){tokens.forEach((w,i)=>{if(i)elCap.appendChild(document.createTextNode(' '));const span=document.createElement('span');span.className='w';span.textContent=w;elCap.appendChild(span);});}
        else elCap.textContent=text;
        elCap.style.clipPath=tornClip(sample.captionStart+1);
        elCap.style.transform=`rotate(${(Math.sin(sample.captionStart*7.3)*.8).toFixed(2)}deg)`;
      }
      if(timed)[...elCap.querySelectorAll('.w')].forEach((sp,i)=>{sp.className='w '+(i===sample.captionIndex?'on':i<sample.captionIndex?'done':'todo');});
      if (isDeskMode) {
        elWipe.style.display = 'none';
      } else {
        const cut=cuts.find(c=>Math.abs(time-c)<=.18+1e-9);
        if(cut===undefined){elWipe.style.display='none';}
        else{const u=(time-(cut-.18))/.36;elWipe.style.display='block';elWipe.style.left=`${(-160+260*smooth(u)).toFixed(2)}%`;}
      }
    }
    function simulate(frame) {
      const time=frame/timeline.fps,sample=sampleTimeline(timeline,time);
      if(active!==sample.scene.id)enter(sample);
      state.time=time;state.frame=frame;
      const dt=1/timeline.fps;
      traveller.update(dt,sample.scene.action==='walk'?{x:.45,z:0}:{x:0,z:0});
      const p=traveller.position;Object.assign(state.traveller,{x:p.x,y:p.y,z:p.z,dirX:traveller.moveDir.x,dirZ:traveller.moveDir.z,speed:traveller.speed});
      if(sample.scene.action==='celebrate')traveller.group.position.y+=Math.abs(Math.sin(sample.local*5))*.12;
      world.update(dt,p,isDeskMode?time:traveller.moveDir);daynight.update(dt);
      if (isDeskMode) applyDeskStudioMood(sample.scene);
      materials.update(dt);updateCamera(sample);lights.update(dt,traveller,camera);
      const prop=subjects.get(sample.scene.id);
      prop.update(sample.local,sample.progress,sample.scene.action,{level:levelAt(time),levelAt,time,scene:sample.scene});
      prop.group.position.x=origins.get(sample.scene.id).x;prop.group.position.z=origins.get(sample.scene.id).z;
      const rawYaw = Math.atan2(camera.position.x-prop.group.position.x,camera.position.z-prop.group.position.z);
      prop.group.rotation.y = isDeskMode ? Math.max(-0.28, Math.min(0.28, rawYaw)) : rawYaw;
      overlays(sample,time);
      document.body.dataset.scene=sample.scene.id;
      return sample;
    }
    let warmed = false;
    runtime={renderFrame(frame){
      if(!Number.isInteger(frame)||frame<0||frame>=frameCount(timeline))throw new Error('Frame index out of range');
      if(frame<lastFrame)throw new Error('Frames must be nondecreasing; reload to rewind');
      if((lastFrame===-1&&frame>0)||allowSeek){
        const targetSample=sampleTimeline(timeline,frame/timeline.fps);
        const sceneStart=Math.max(0,Math.floor(targetSample.scene.start*timeline.fps));
        if(sceneStart>lastFrame+1){
          if(active!==targetSample.scene.id)enter(sampleTimeline(timeline,targetSample.scene.start+1e-6));
          lastFrame=sceneStart-1;
        }
      }
      let sample;for(let f=lastFrame+1;f<=frame;f++)sample=simulate(f);
      lastFrame=frame;
      post.setFocus(focus);
      if (!warmed) {
        // Warm up WebGL shaders, PCSS shadow state (paperState.pcss), and post targets so frame 0 is bit-identical on repeat.
        post.render(1/timeline.fps);
        lights.update(0, traveller, camera);
        warmed = true;
      }
      post.render(1/timeline.fps);
      renderer.getContext().finish();
      return {frame,time:frame/timeline.fps,scene:document.body.dataset.scene,caption:document.querySelector('#caption').textContent,assetSource:assets.source};
    }};
    await document.fonts.ready;
    return {assetSource:assets.source,frames:frameCount(timeline),width:timeline.width,height:timeline.height};
  },
  renderFrame(frame){if(!runtime)throw new Error('Call init(timeline) first');return runtime.renderFrame(frame);}
};
