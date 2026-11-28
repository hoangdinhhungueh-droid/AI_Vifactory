import * as THREE from 'three';
import { clamp01, smooth, easeInOutCubic, easeOutBack, squashPreserveVolume, overlap, impactPulse, bezierArc } from './motion.js';
import { makeDocumentPrintMaterial, makeChartBoardPrintMaterial, makeLedgerPagePrintMaterial } from './print_textures.js';

// Extension point: add a named builder here and the same name to timeline.mjs PROPS.
// Each builder returns real layered paper geometry, never a generic title slide.
export function createProp(kind, { materials, assets, color = '#b26d42', sceneData = null }) {
  const root = new THREE.Group(); root.name = `subject-${kind}`;
  const anim = [];
  const paper = c => materials.paper({ color: c, side: THREE.DoubleSide });
  const mesh = (geo, c, x=0, y=0, z=0, parent=root) => {
    const m = new THREE.Mesh(geo,paper(c)); m.position.set(x,y,z); m.castShadow=true; m.receiveShadow=true; parent.add(m); return m;
  };
  const applyFace = (w, h, mat, x, y, z, parent=root) => {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), mat);
    m.position.set(x, y, z); m.receiveShadow = true; parent.add(m); return m;
  };
  const rect = (w,h,c,x,y,z=.02,parent=root) => mesh(new THREE.BoxGeometry(w,h,.045),c,x,y,z,parent);
  const disc = (r,c,x,y,z=.06,parent=root) => mesh(new THREE.CylinderGeometry(r,r,.045,48).rotateX(Math.PI/2),c,x,y,z,parent);
  const polygon = (points,c,z=.01) => {const s=new THREE.Shape(); points.forEach(([x,y],i)=>i?s.lineTo(x,y):s.moveTo(x,y));s.closePath();return mesh(new THREE.ExtrudeGeometry(s,{depth:.035,bevelEnabled:false}),c,0,0,z);};
  const line = (x,y,x2,y2,c='#554637',w=.035,z=.10) => { const m=rect(w,Math.hypot(x2-x,y2-y),c,(x+x2)/2,(y+y2)/2,z);m.rotation.z=-Math.atan2(x2-x,y2-y);return m; };
  const cream='#f7e8c6', ink='#443e32', gold='#e2b54b', green='#6d966e';
  const tile = {village:'village',forest:'forest',house:'house',tree:'grove',bridge:'bridge',mountain:'hills',water:'pond'}[kind];
  if (tile && assets && typeof assets.getTilePrototype === 'function') {
    const t=assets.getTilePrototype(tile).clone(true); t.scale.setScalar({village:2.2,house:2.0,forest:1.6}[kind]||1.4);
    t.traverse(o=>{if(/^base/i.test(o.name))o.visible=false; if(o.userData.hinge)o.rotation.x=0;});root.add(t);
    // Pieces pop up one after another (trees growing, houses unfolding) instead of the whole tile flipping.
    const pieces=[];t.traverse(o=>{if(o.isMesh&&o.visible&&!/^base/i.test(o.name))pieces.push(o);});
    pieces.forEach((m,i)=>{m.userData.baseScale=m.scale.clone();m.userData.order=(i*0.618)%1;});
    root.userData.grow=(p)=>{for(const m of pieces){const k=THREE.MathUtils.smoothstep(p*1.35-m.userData.order*.55,0,.45);const o=1+.18*Math.sin(Math.min(1,k)*Math.PI);const sc=Math.max(.001,k*o);m.scale.set(m.userData.baseScale.x*sc,m.userData.baseScale.y*sc,m.userData.baseScale.z*sc);}};
  } else if (tile) {
    // Procedural 3D Vox archival evidence folder fallback when rendered without GLTF tiles (forensic_desk mode)
    const folder = new THREE.Group(); root.add(folder);
    rect(1.85, 1.45, color, 0, .92, -.02, folder);
    rect(1.68, 1.32, cream, 0, .94, .03, folder);
    if (sceneData) {
      applyFace(1.56, 1.22, makeDocumentPrintMaterial(sceneData, { mode: 'dossier' }), 0, .94, .062, folder);
    }
    rect(.52, .12, gold, -.46, 1.66, .04, folder);
    rect(.14, .28, '#c83e2b', .55, 1.56, .08, folder);
    anim.push((time, p) => { folder.position.y = Math.sin(time * 1.4) * .03; folder.rotation.y = Math.sin(p * Math.PI) * .08; });
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
    for(let i=0;i<5;i++){const w=rect(.22,.28,gold,-.95+i*.46,.5,.09);anim.push(t=>{if(w.material.emissive)w.material.emissive.setScalar(Math.sin(t*3+i*1.7)>.2?.35:.12);});}
    const gear=new THREE.Group();gear.position.set(-.55,1.02,.12);root.add(gear);
    disc(.26,'#8a6a45',0,0,0,gear);disc(.1,cream,0,0,.03,gear);for(let i=0;i<8;i++){const tooth=rect(.09,.12,'#8a6a45',Math.sin(i*Math.PI/4)*.3,Math.cos(i*Math.PI/4)*.3,0,gear);tooth.rotation.z=-i*Math.PI/4;}
    anim.push(t=>gear.rotation.z=-t*1.6);
    for(let i=0;i<4;i++){const puff=disc(.2,cream,.88,1.95,0);anim.push(t=>{const u=((t*.45+i/4)%1);puff.position.set(.88+u*.55+Math.sin(t*2+i)*.06,1.95+u*1.25,0);puff.scale.setScalar(.6+u*1.1);puff.visible=u<.92;});}
  } else if (kind==='clock') {
    disc(.95,color,0,1.05,0);disc(.83,cream,0,1.05,.04);
    for(let i=0;i<12;i++){let a=i*Math.PI/6;line(Math.sin(a)*.69,1.05+Math.cos(a)*.69,Math.sin(a)*.76,1.05+Math.cos(a)*.76,ink,.035,.1);}
    const hand=line(0,1.05,0,1.68,ink,.055,.15); hand.geometry.translate(0,-.315,0);hand.position.set(0,1.05,.15);
    anim.push(t=>hand.rotation.z=-t*.8);line(0,1.05,.35,1.32,color,.08,.17);disc(.09,gold,0,1.05,.2);
  } else if (kind==='people') {
    for(let i=0;i<3;i++) {const g=new THREE.Group();g.position.x=(i-1)*.8;root.add(g);disc(.22,cream,0,1.48,0,g);rect(.42,.65,i%2?green:color,0,.91,0,g);for(const sign of [-1,1]){rect(.11,.48,ink,sign*.12,.36,0,g);const arm=rect(.1,.55,cream,sign*.32,1,0,g);arm.rotation.z=sign*.4;}anim.push(t=>g.rotation.z=Math.sin(t*3+i)*.06);}
  } else if (kind==='globe') {
    disc(1,'#5a9cab',0,1.2,0);
    // Deliberately simplified but recognizable Americas, Eurasia, Africa and Australia.
    const continents=[
      [[-.82,1.65],[-.65,1.95],[-.35,2.04],[-.12,1.84],[-.25,1.66],[-.46,1.57],[-.36,1.35],[-.51,1.25],[-.64,1.48]],
      [[-.38,1.29],[-.13,1.25],[0,1.02],[-.16,.75],[-.31,.49],[-.4,.69],[-.37,.96],[-.53,1.13]],
      [[.02,1.75],[.15,1.91],[.38,1.92],[.58,1.78],[.82,1.65],[.91,1.39],[.69,1.33],[.56,1.5],[.39,1.36],[.2,1.53],[.06,1.49]],
      [[.08,1.44],[.36,1.41],[.49,1.2],[.34,.89],[.22,.73],[.09,.96],[-.02,1.23]],
      [[.57,.78],[.76,.82],[.87,.67],[.71,.56],[.56,.64]]
    ];
    for(const shape of continents)polygon(shape,green,.06);
    for(const offset of [-.45,0,.45]){
      const radius=Math.sqrt(1-offset*offset);
      line(-radius,1.2+offset,radius,1.2+offset,cream,.012,.12);
    }
    for(const rx of [.3,.66]){
      const points=new THREE.EllipseCurve(0,1.2,rx,1,0,2*Math.PI).getPoints(64).map(v=>new THREE.Vector3(v.x,v.y,.115));
      root.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(points),new THREE.LineBasicMaterial({color:cream,transparent:true,opacity:.65})));
    }
    rect(.12,.35,ink,0,.12,-.05);rect(1.1,.12,color,0,0,-.05);
  } else if (kind==='voice-note') {
    // Decorative waveform driven by scene time, not an audio measurement.
    rect(2.5,1.55,cream,0,1.05,0);
    rect(2.28,.18,color,0,1.72,.06);
    disc(.18,gold,-.97,1.05,.08);
    for(let i=0;i<13;i++) {
      const h=.12 + (i%4)*.11;
      const bar=rect(.075,h,green,i*.13-.63,1.05,.1);
      bar.name=`wave-bar-${i+1}`;
      anim.push((t,p,ctx)=>{const lv=ctx&&ctx.levelAt?ctx.levelAt(ctx.time-Math.abs(i-6)*.035):null;bar.scale.y=lv==null?.72+.28*(.5+.5*Math.sin(t*5+i*.7))*p:(.25+2.6*lv)*(.4+.6*p);});
    }
    line(-.86,.45,.86,.45,green,.035,.1);
  } else if (kind==='edit-board') {
    // A paper editing board with a moving playhead and caption strip.
    rect(2.7,1.8,'#e8dcc2',0,1.05,0);
    rect(2.38,1.18,'#283b45',0,1.25,.06);
    for(let i=0;i<7;i++)rect(.22,.18,gold,i*.3-.9,.95,.1);
    const playhead=rect(.035,1.3,'#d75f45',-1.03,1.25,.16);
    playhead.name='playhead';
    anim.push((t,p)=>{playhead.position.x=-1.03+2.06*Math.min(1,p);});
    rect(1.95,.12,cream,0,.43,.1);
    rect(1.4,.12,cream,0,.25,.1);
  } else if (kind==='pop-up') {
    // Paper leaves rise from the board when a scene becomes active.
    rect(2.55,.2,ink,0,.12,0);
    for(let i=0;i<3;i++) {
      const leaf=new THREE.Group();leaf.name=i===1?'pop-up-leaf':`pop-up-leaf-${i+1}`;root.add(leaf);
      leaf.position.set((i-1)*.62,.2,0);
      const shape=new THREE.Shape();shape.moveTo(-.28,0);shape.lineTo(.28,0);shape.lineTo(.18,.9);shape.lineTo(0,1.25);shape.lineTo(-.18,.9);shape.closePath();
      const leafMesh=new THREE.Mesh(new THREE.ExtrudeGeometry(shape,{depth:.04,bevelEnabled:false}),paper(i===1?green:color));leafMesh.position.z=.08;leaf.add(leafMesh);
      anim.push((t,p)=>{leaf.rotation.z=(i-1)*.18+Math.sin(t*2+i)*.06;leaf.scale.y=.15+.85*p;});
    }
  } else if (kind==='film') {
    // A paper film strip scrolls past a clapperboard: "voice becomes an animated film".
    const strip=new THREE.Group();strip.position.set(0,1.15,.05);root.add(strip);
    for(let i=0;i<9;i++){const f=new THREE.Group();f.position.x=(i-4)*.62;strip.add(f);rect(.6,.82,'#2c2621',0,0,0,f);rect(.46,.5,[color,gold,green,cream][i%4],0,0,.03,f);for(const sy of [-.33,.33])for(let j=0;j<3;j++)rect(.07,.06,cream,(j-1)*.17,sy,.03,f);}
    anim.push(t=>{strip.position.x=-((t*.5)%.62);});
    const clap=new THREE.Group();clap.position.set(-1.25,.35,.25);root.add(clap);
    rect(.9,.62,ink,0,0,0,clap);rect(.8,.1,cream,0,.12,.03,clap);
    const arm=new THREE.Group();arm.position.set(-.45,.33,.02);clap.add(arm);rect(.92,.14,ink,.46,.07,0,arm);
    for(let i=0;i<4;i++){const st=rect(.12,.13,cream,.16+i*.22,.07,.03,arm);st.rotation.z=.5;}
    anim.push((t)=>{const k=(t%1.6)/1.6;arm.rotation.z=k<.12?.55*(1-k/.12):k<.2?0:.55*Math.min(1,(k-.2)/.25);});
  } else if (kind==='bubble') {
    // Speech bubble whose caption lines write in, over a small waveform: captions + the original audio.
    const shape=new THREE.Shape();shape.moveTo(-1.25,.55);shape.lineTo(1.25,.55);shape.lineTo(1.25,1.95);shape.lineTo(-1.25,1.95);shape.lineTo(-1.25,.55);
    const tail=new THREE.Shape();tail.moveTo(-.6,.58);tail.lineTo(-.15,.58);tail.lineTo(-.85,.12);tail.closePath();
    mesh(new THREE.ExtrudeGeometry(shape,{depth:.04,bevelEnabled:false}),cream,0,0,0);mesh(new THREE.ExtrudeGeometry(tail,{depth:.04,bevelEnabled:false}),cream,0,0,0);
    for(let i=0;i<3;i++){const w=1.9-i*.45;const ln=rect(w,.13,i===1?color:ink,0,1.62-i*.32,.07);ln.geometry.translate(w/2,0,0);ln.position.x=-1.0;anim.push((t,p)=>{ln.scale.x=Math.max(.001,Math.min(1,p*2.2-i*.45));});}
    for(let i=0;i<11;i++){const b=rect(.06,.2,green,.45+i*.08,.33,.07);anim.push((t,p,ctx)=>{const lv=ctx&&ctx.levelAt?ctx.levelAt(ctx.time-i*.03):null;b.scale.y=lv==null?.6+.4*Math.abs(Math.sin(t*6+i)):.3+3*lv;});}
  } else if (kind==='mic') {
    // A paper microphone on a stand with sound rings: "record your voice".
    disc(.36,color,0,1.62,0);disc(.27,'#3a3128',0,1.62,.04);for(let i=0;i<4;i++)rect(.42,.025,cream,0,1.5+i*.08,.08);
    rect(.5,.12,ink,0,1.2,0);rect(.08,1.0,ink,0,.68,-.02);rect(.7,.08,ink,0,.18,-.02);
    for(let i=0;i<3;i++){const ring=new THREE.Mesh(new THREE.TorusGeometry(.5,.025,6,40,Math.PI*.7),paper(gold));ring.rotation.z=-Math.PI*.35;ring.position.set(.12,1.62,.02);root.add(ring);
      anim.push((t,p,ctx)=>{const lv=ctx?ctx.level:null;const u=((t*.8+i/3)%1);ring.scale.setScalar(.7+u*1.1);ring.visible=u<.85&&(lv==null||lv>.04);});}
  } else if (kind==='sun'||kind==='moon') {
    disc(.7,kind==='sun'?gold:cream,0,1.5,0);
    if(kind==='sun')for(let i=0;i<12;i++){let a=i*Math.PI/6;line(Math.cos(a)*.82,1.5+Math.sin(a)*.82,Math.cos(a)*1.04,1.5+Math.sin(a)*1.04,gold,.06);}
    else {disc(.2,'#d9c7a2',-.22,1.65,.05);disc(.11,'#d9c7a2',.25,1.25,.05);}
  } else if (kind==='courthouse') {
    const crimson='#c83e2b';
    rect(2.6,.18,ink,0,.1,0);
    rect(2.3,.16,cream,0,.27,0.01);
    for(const cx of [-.84,-.28,.28,.84]){
      rect(.2,1.15,cream,cx,.92,.02);
      rect(.26,.08,gold,cx,1.5,.04);
    }
    const roof=new THREE.Group();root.add(roof);
    roof.add(polygon([[-1.35,1.55],[1.35,1.55],[0,2.22]],crimson,.04));
    roof.add(polygon([[-1.08,1.61],[1.08,1.61],[0,2.08]],cream,.08));
    const banner=rect(.24,.65,crimson,0,1.15,.08);
    anim.push((t,p)=>{
      roof.position.y=Math.max(0,(1-Math.min(1,p*1.4))*.35);
      banner.rotation.z=Math.sin(t*2.4)*.08;
    });
  } else if (kind==='gavel') {
    const crimson='#c83e2b', wood='#7c4b27';
    disc(.65,ink,-.35,.22,0);disc(.52,wood,-.35,.27,.03);
    const arm=new THREE.Group();arm.position.set(.85,.45,.05);root.add(arm);
    rect(1.35,.13,wood,-.67,0,0,arm);
    rect(.45,.72,gold,-1.25,0,.04,arm);
    rect(.52,.14,crimson,-1.25,.28,.06,arm);
    rect(.52,.14,crimson,-1.25,-.28,.06,arm);
    const shock=new THREE.Mesh(new THREE.RingGeometry(.45,.58,32),paper(crimson));
    shock.rotation.x=-Math.PI/2;shock.position.set(-.35,.32,0);root.add(shock);
    anim.push((t,p,ctx)=>{
      const cSec=ctx?.scene?.timing?.contactSec??0.42;
      const pulse=impactPulse(t,cSec,0.14,0.14,0.30);
      const breathe=pulse.struck?Math.sin((t-cSec)*3.0)*0.015:0;
      arm.rotation.z=0.38+0.32*pulse.lift-0.38*pulse.impact+breathe;
      const sq=squashPreserveVolume(pulse.squashY);
      arm.scale.set(sq.sx,sq.sy,sq.sz);
      const wave=pulse.struck?clamp01((t-cSec-0.12)/0.45):0;
      shock.visible=wave>0&&wave<1;shock.scale.setScalar(0.7+wave*1.45);
    });
  } else if (kind==='ledger') {
    const crimson='#c83e2b';
    rect(2.35,1.95,ink,0,1.02,-.03);
    rect(1.06,1.82,cream,-.55,1.04,.02);
    rect(1.06,1.82,cream,.55,1.04,.02);
    if (sceneData) {
      applyFace(1.0, 1.74, makeLedgerPagePrintMaterial(sceneData, 'left'), -.55, 1.04, .048);
      applyFace(1.0, 1.74, makeLedgerPagePrintMaterial(sceneData, 'right'), .55, 1.04, .048);
    }
    rect(.08,1.86,ink,0,1.04,.04);
    for(let i=0;i<5;i++){
      const w=.35+((i*37)%50)/100;
      const bar=rect(w,.12,i%2?crimson:green,-.95+w/2,1.62-i*.28,.076);
      anim.push((t,p)=>{bar.scale.x=Math.max(.1,Math.min(1,p*1.6-i*.15));});
      if (!sceneData) rect(.72,.04,'#9e8f75',.55,1.62-i*.28,.076);
    }
    const cursor=rect(.92,.14,gold,.55,1.62,.098);
    anim.push(t=>{cursor.position.y=1.62-(((t*.65)%4)*.28);});
  } else if (kind==='container') {
    const teal='#2b6c7a', rust='#b84a32';
    rect(1.35,.72,rust,-.55,.38,0);rect(1.35,.72,teal,.55,.38,.05);
    for(let i=0;i<5;i++){rect(.06,.56,cream,-1.0+i*.22,.38,.05);rect(.06,.56,cream,.1+i*.22,.38,.1);}
    line(-1.35,0,-1.35,2.2,ink,.09,.02);line(-1.35,2.15,.95,2.15,ink,.08,.02);
    const hoist=new THREE.Group();hoist.position.set(.05,2.12,.06);root.add(hoist);
    rect(.04,.62,ink,0,-.31,0,hoist);
    rect(1.15,.62,gold,0,-.88,0,hoist);
    anim.push(t=>{hoist.rotation.z=Math.sin(t*1.6)*.14;hoist.position.x=Math.sin(t*.8)*.35;});
  } else if (kind==='vault') {
    const steel='#6b7d8b', dark='#44525e';
    rect(2.26,2.26,gold,0,1.12,-.065);
    rect(2.15,2.15,dark,0,1.12,-.04);
    for(const sx of [-.94,.94])for(const sy of [.18,2.06])disc(.055,gold,sx,sy,.01);
    disc(.92,steel,0,1.12,.02);disc(.76,'#8fa0ac',0,1.12,.06);
    const wheel=new THREE.Group();wheel.position.set(0,1.12,.14);root.add(wheel);
    disc(.28,gold,0,0,0,wheel);
    for(let i=0;i<6;i++){
      const sp=rect(.07,.58,cream,0,0,.02,wheel);sp.rotation.z=i*Math.PI/3;
    }
    const bolts=[];
    for(let i=0;i<4;i++){const a=i*Math.PI/2;const b=rect(.18,.12,gold,Math.cos(a)*.82,1.12+Math.sin(a)*.82,.09);b.rotation.z=a;bolts.push([b,a]);}
    anim.push(t=>{
      wheel.rotation.z=Math.sin(t*1.4)*1.6;
      const slide=Math.sin(t*1.4)*.08;
      bolts.forEach(([b,a])=>b.position.set(Math.cos(a)*(.82+slide),1.12+Math.sin(a)*(.82+slide),.09));
    });
  } else if (kind==='scale') {
    rect(1.1,.14,ink,0,.1,0);rect(.12,1.75,ink,0,.95,0);disc(.14,gold,0,1.82,.04);
    const beam=new THREE.Group();beam.position.set(0,1.78,.05);root.add(beam);
    rect(2.1,.09,gold,0,0,0,beam);
    const pans=[];
    for(const side of [-.95,.95]){
      const pan=new THREE.Group();pan.position.set(side,-.72,.02);beam.add(pan);
      rect(.03,.72,ink,0,.36,0,pan);
      rect(.68,.09,cream,0,0,0,pan);
      disc(.24,side<0?gold:'#c83e2b',0,.18,.04,pan);
      pans.push(pan);
    }
    anim.push(t=>{
      const tilt=Math.sin(t*1.9)*.22;
      beam.rotation.z=tilt;
      pans.forEach(pn=>pn.rotation.z=-tilt);
    });
  } else if (kind==='contract') {
    const crimson='#c83e2b';
    const doc=rect(1.65,1.95,cream,0,1.02,0);
    rect(1.8,.16,'#d8c7a3',0,1.98,.05);
    if (sceneData) {
      applyFace(1.52, 1.82, makeDocumentPrintMaterial(sceneData, { mode: 'contract' }), 0, 0, .028, doc);
    } else {
      rect(1.25,.1,ink,-.05,1.65,.06);
      for(let i=0;i<5;i++)rect(1.22-(i%2)*.25,.045,'#9d8e74',-.05,1.35-i*.18,.06);
    }
    const seal=disc(.26,crimson,.45,.45,.12);
    const ribbon=rect(.18,.32,crimson,.45,.24,.09);
    anim.push((t,p,ctx)=>{
      const cSec=ctx?.scene?.timing?.contactSec??0.48;
      const openDoc=easeOutBack(clamp01(t/Math.max(0.18,cSec*0.72)));
      doc.scale.y=0.28+0.72*openDoc;
      const pulse=impactPulse(t,cSec,0.13,0.15,0.28);
      const sq=squashPreserveVolume(pulse.squashY);
      seal.visible=pulse.lift>0||pulse.impact>0;
      seal.position.z=0.12+0.28*pulse.lift;
      seal.scale.set(sq.sx*(0.9+0.1*pulse.settle),sq.sy*(0.9+0.1*pulse.settle),sq.sz);
      const ov=overlap(t,cSec,0.06,0.24);
      ribbon.visible=ov>0.02;
      ribbon.scale.y=Math.max(0.01,easeOutBack(ov));
      ribbon.rotation.z=Math.sin(t*2.5)*0.06*ov;
    });
  } else if (kind==='megaphone') {
    const crimson='#c83e2b';
    const cone=new THREE.Group();cone.position.set(-.2,1.15,.04);root.add(cone);
    cone.add(polygon([[-.75,-.22],[.65,-.62],[.65,.62],[-.75,.22]],crimson,.02));
    rect(.2,.55,ink,-.42,-.45,0,cone);
    const rings=[];
    for(let i=0;i<3;i++){
      const rg=new THREE.Mesh(new THREE.TorusGeometry(.48,.03,6,36,Math.PI*.65),paper(gold));
      rg.rotation.z=-Math.PI*.32;rg.position.set(.68,1.15,.05);root.add(rg);rings.push(rg);
    }
    anim.push((t,p,ctx)=>{
      const lv=ctx&&ctx.level!=null?ctx.level:.5;
      cone.rotation.z=.08+Math.sin(t*3)*.04;
      rings.forEach((rg,i)=>{const u=((t*.9+i/3)%1);rg.scale.setScalar(.6+u*(.9+lv*.6));rg.visible=u<.85;});
    });
  } else if (kind==='briefcase') {
    const leather='#5c3d28', crimson='#c83e2b';
    rect(1.9,1.15,leather,0,.62,0);
    rect(.65,.14,ink,0,1.25,0);
    rect(.18,.22,gold,-.5,.9,.05);rect(.18,.22,gold,.5,.9,.05);
    const lid=new THREE.Group();lid.position.set(0,1.15,-.03);root.add(lid);
    rect(1.9,.22,leather,0,.05,0,lid);
    const stacks=[];
    for(let i=0;i<4;i++){
      const st=rect(.32,.75,gold,(i-1.5)*.38,1.35,.04);
      rect(.34,.1,crimson,0,.05,.03,st);
      stacks.push(st);
    }
    anim.push((t,p)=>{
      const k=Math.min(1,p*1.6);
      lid.rotation.x=-.45*k;
      stacks.forEach((st,i)=>{st.position.y=1.05+k*(.35+Math.sin(t*2.5+i)*.08);});
    });
  } else if (kind==='shield') {
    const navy='#253b52', crimson='#c83e2b';
    polygon([[0,.15],[.95,.75],[.95,1.88],[0,2.08],[-.95,1.88],[-.95,.75]],navy,.01);
    polygon([[0,.32],[.76,.82],[.76,1.72],[0,1.9],[-.76,1.72],[-.76,.82]],cream,.05);
    const band=rect(1.1,.22,crimson,0,1.22,.09);
    const core=disc(.24,gold,0,1.22,.13);
    anim.push(t=>{
      const s=1+Math.sin(t*2.8)*.08;
      band.scale.setScalar(s);core.scale.setScalar(1.08-Math.sin(t*2.8)*.08);
    });
  } else if (kind==='hanko-stamp') {
    const crimson='#c83e2b', lacquer='#6e1e19';
    rect(2.1,1.72,cream,0,.98,0);
    if (sceneData) {
      applyFace(1.96, 1.58, makeDocumentPrintMaterial(sceneData, { mode: 'stamp' }), 0, .98, .028);
    } else {
      rect(1.38,.09,ink,-.12,1.6,.04);
      for(let i=0;i<4;i++)rect(1.22-(i%2)*.26,.045,'#9d8e74',-.18,1.35-i*.18,.04);
    }
    rect(.66,.38,ink,-.58,.42,.03);
    rect(.54,.28,crimson,-.58,.44,.06);
    const imprint=new THREE.Group();imprint.position.set(.42,.66,.055);root.add(imprint);
    const sealRing=new THREE.Mesh(new THREE.RingGeometry(.21,.28,32),paper(crimson));
    imprint.add(sealRing);
    rect(.05,.24,crimson,0,0,.01,imprint);
    rect(.2,.04,crimson,0,.05,.01,imprint);
    rect(.2,.04,crimson,0,-.06,.01,imprint);
    const stamper=new THREE.Group();stamper.position.set(.42,.66,.12);root.add(stamper);
    rect(.46,.46,gold,0,0,0,stamper);
    rect(.36,.36,crimson,0,0,.04,stamper);
    const grip=mesh(new THREE.CylinderGeometry(.16,.2,.72,24).rotateX(Math.PI/2),lacquer,0,0,.38,stamper);
    disc(.22,gold,0,0,.74,stamper);
    anim.push((t,p,ctx)=>{
      const cSec=ctx?.scene?.timing?.contactSec??0.44;
      const pulse=impactPulse(t,cSec,0.14,0.14,0.28);
      const sq=squashPreserveVolume(pulse.squashY);
      stamper.position.z=0.12+0.52*pulse.lift+(1-pulse.impact)*0.34;
      stamper.rotation.x=-0.22*pulse.lift;
      grip.scale.set(sq.sx,sq.sy,sq.sz);
      const rev=overlap(t,cSec,0.02,0.18);
      imprint.visible=rev>0.01;
      imprint.scale.setScalar(Math.max(0.01,easeOutBack(rev)));
    });
  } else if (kind==='brass-caliper') {
    const crimson='#c83e2b';
    rect(2.25,1.76,cream,0,.98,-.03);
    if (sceneData) {
      applyFace(2.1, 1.62, makeDocumentPrintMaterial(sceneData, { mode: 'caliper' }), 0, .98, -.002);
    } else {
      for(let i=0;i<5;i++)rect(.75,.04,'#a8987d',-.55,1.52-i*.24,.02);
    }
    const targetBar=rect(.78,.42,crimson,.18,.94,.04);
    const rail=rect(1.92,.14,gold,0,1.42,.11);
    for(let i=0;i<9;i++)rect(.025,.07,ink,-.78+i*.19,0,.04,rail);
    const leftJaw=new THREE.Group();leftJaw.position.set(-.26,1.06,.12);root.add(leftJaw);
    rect(.14,.86,gold,0,0,0,leftJaw);
    rect(.26,.16,gold,.12,-.36,.02,leftJaw);
    const rightJaw=new THREE.Group();rightJaw.position.set(.62,1.06,.12);root.add(rightJaw);
    rect(.14,.86,gold,0,0,0,rightJaw);
    rect(.26,.16,gold,-.12,-.36,.02,rightJaw);
    const lockPin=disc(.09,crimson,0,.38,.05,rightJaw);
    anim.push((t,p,ctx)=>{
      const cSec=ctx?.scene?.timing?.contactSec??0.46;
      const pulse=impactPulse(t,cSec,0.14,0.15,0.28);
      const spread=0.38*pulse.lift+0.32*(1-pulse.impact);
      rightJaw.position.x=0.60+spread;
      const sq=squashPreserveVolume(pulse.squashY);
      targetBar.scale.set(1-0.08*(1-sq.sy),sq.sy,1);
      const pin=overlap(t,cSec,0.05,0.16);
      lockPin.scale.setScalar(0.75+0.35*easeOutBack(pin));
    });
  } else if (kind==='forensic-loupe') {
    const crimson='#c83e2b', paleGlass='#e6f0ee';
    rect(2.05,1.88,cream,0,1.0,-.03);
    if (sceneData) {
      applyFace(1.9, 1.72, makeDocumentPrintMaterial(sceneData, { mode: 'loupe' }), 0, 1.0, -.002);
    } else {
      for(let i=0;i<6;i++)rect(1.45-(i%3)*.18,.045,'#9e8f75',0,1.62-i*.22,.02);
    }
    const clause=rect(.74,.14,gold,.26,.76,.05);
    const reticle=new THREE.Mesh(new THREE.RingGeometry(.24,.30,32),paper(crimson));
    reticle.position.set(.26,.76,.065);root.add(reticle);
    const loupe=new THREE.Group();loupe.position.set(-.65,1.45,.26);root.add(loupe);
    const bezel=new THREE.Mesh(new THREE.RingGeometry(.38,.48,36),paper(gold));
    loupe.add(bezel);
    const lens=disc(.37,paleGlass,0,0,-.02,loupe);
    lens.material.transparent=true;lens.material.opacity=0.36;
    const handle=rect(.11,.72,ink,.42,-.42,0,loupe);
    handle.rotation.z=Math.PI/4;
    anim.push((t,p,ctx)=>{
      const cSec=ctx?.scene?.timing?.contactSec??0.46;
      const moveU=easeInOutCubic(clamp01(t/Math.max(0.18,cSec)));
      const pos=bezierArc({x:-.68,y:1.45,z:.28},{x:.26,y:.76,z:.19},0.36,moveU);
      loupe.position.set(pos.x,pos.y,pos.z);
      const pulse=impactPulse(t,cSec,0.12,0.14,0.28);
      const sq=squashPreserveVolume(pulse.squashY);
      loupe.scale.set(sq.sx,sq.sy,sq.sz);
      const lock=overlap(t,cSec,0.04,0.22);
      reticle.scale.setScalar(0.85+0.25*easeOutBack(lock));
      clause.scale.x=1+0.12*smooth(lock);
    });
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
