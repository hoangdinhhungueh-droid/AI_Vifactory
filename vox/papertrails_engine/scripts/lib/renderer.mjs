import { spawn, execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { readFile, writeFile, mkdir, stat, rename, rm } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash, randomUUID } from 'node:crypto';
import { once } from 'node:events';
import { chromium } from 'playwright';
import { validateTimeline, frameCount, sampleTimeline } from '../../engine/src/video/timeline.mjs';
const run = promisify(execFile);
const root = fileURLToPath(new URL('../../', import.meta.url));
const hash = b => createHash('sha256').update(b).digest('hex');
export async function loadTimeline(filename) {
  const t=validateTimeline(JSON.parse(await readFile(filename,'utf8')));
  t.audio=path.resolve(path.dirname(path.resolve(filename)),t.audio);
  if(!(await stat(t.audio)).isFile())throw new Error('Audio is not a regular file');
  const {stdout}=await run('ffprobe',['-v','error','-show_streams','-show_format','-of','json',t.audio],{timeout:30000,maxBuffer:2e6});
  const probe=JSON.parse(stdout),audio=probe.streams.find(s=>s.codec_type==='audio');
  if(!audio)throw new Error('Timeline audio must contain a real audio stream');
  const duration=Number(audio.duration || probe.format?.duration);
  const tolerance=.08;
  if(!Number.isFinite(duration)||Math.abs(duration-t.duration)>tolerance)throw new Error(`Audio duration ${duration} does not match timeline ${t.duration} (tolerance ${tolerance}s)`);
  return t;
}
// Loudness of the ORIGINAL voice per output frame (0..1), used only to animate waveform props.
export async function voiceEnvelope(audio,fps,frames){
  const sr=16000;
  const {stdout}=await run('ffmpeg',['-v','error','-i',audio,'-ac','1','-ar',String(sr),'-f','f32le','pipe:1'],{encoding:'buffer',maxBuffer:4*sr*60*60,timeout:120000});
  const x=new Float32Array(stdout.buffer,stdout.byteOffset,Math.floor(stdout.length/4)),hop=sr/fps,rms=[];
  for(let f=0;f<frames;f++){const a=Math.floor(f*hop),b=Math.min(x.length,Math.floor((f+1)*hop));let e=0;for(let i=a;i<b;i++)e+=x[i]*x[i];rms.push(b>a?Math.sqrt(e/(b-a)):0);}
  const ref=[...rms].sort((m,n)=>m-n)[Math.floor(rms.length*.95)]||1;
  return rms.map(v=>Math.round(Math.min(1,v/ref)*1000)/1000);
}
export async function startServer() {
  const {createServer}=await import('../../engine/node_modules/vite/dist/node/index.js');
  const server=await createServer({root:path.join(root,'engine'),configFile:false,base:'/',server:{host:'127.0.0.1',port:0,strictPort:true,open:false,hmr:false,fs:{strict:true}},logLevel:'error'});
  await server.listen();
  const port=server.httpServer.address().port;
  return {server,url:`http://127.0.0.1:${port}`};
}
async function deadline(promise,ms,label) {
  let timer;try{return await Promise.race([promise,new Promise((_,reject)=>{timer=setTimeout(()=>reject(new Error(`${label} timeout after ${ms}ms`)),ms);})]);}finally{clearTimeout(timer);}
}
export async function renderVideo(filename,output,{quality='med',stills=[],stillsOnly=false,startFrame=0,endFrame=null,silentOnly=false,timeoutMs=180000,onProgress,sfx=false,gpu=false,renderFps=null,frameFormat='png'}={}) {
  if(!['low','vox','med','high'].includes(quality))throw new Error('Quality must be low, vox, med, or high');
  if(!['png','jpeg'].includes(frameFormat))throw new Error('frameFormat must be png or jpeg');
  const t=await loadTimeline(filename),frames=frameCount(t);
  const sF=Math.max(0,Number.isInteger(startFrame)?startFrame:0);
  const eF=endFrame==null?frames:Math.min(frames,Number(endFrame));
  if(!stillsOnly&&(!Number.isInteger(eF)||eF<=sF))throw new Error(`Invalid frame range [${sF}, ${eF})`);
  if(stillsOnly&&!stills.length)throw new Error('--stills-only requires non-empty --stills');
  if(stills.some(n=>!Number.isFinite(n)||n<0||n>=t.duration))throw new Error('Still times must be >= 0 and < duration');
  output=path.resolve(output);
  if(!stillsOnly&&path.extname(output).toLowerCase()!=='.mp4')throw new Error('Output must be .mp4');
  if(output===t.audio||output===path.resolve(filename))throw new Error('Output cannot overwrite input');
  await mkdir(path.dirname(output),{recursive:true});
  const token=randomUUID(),partial=`${output}.${token}.partial.mp4`,metaPartial=`${output}.${token}.partial.json`;
  let server,browser,encoder,encoderDone;let stderr='',encoderError;const temporary=[];
  const signalController=new AbortController();
  const abort=()=>{signalController.abort();encoder?.kill('SIGKILL');void browser?.close().catch(()=>{});};
  process.once('SIGINT',abort);process.once('SIGTERM',abort);
  try {
    const service=await startServer();server=service.server;
    // Default: CPU SwiftShader (portable, slow at 1080p). --gpu uses the machine's GPU through ANGLE (much faster).
    const glArgs=gpu?(process.platform==='win32'?['--use-angle=d3d11','--ignore-gpu-blocklist','--enable-gpu-rasterization']:['--use-angle=default','--ignore-gpu-blocklist','--enable-gpu-rasterization']):['--use-angle=swiftshader','--enable-unsafe-swiftshader'];
    browser=await chromium.launch({headless:true,args:[...glArgs,'--disable-background-timer-throttling']});
    const context=await browser.newContext({viewport:{width:t.width,height:t.height},deviceScaleFactor:1,locale:'vi-VN',timezoneId:'UTC',reducedMotion:'reduce',serviceWorkers:'block'});
    await context.route('**/*',route=>new URL(route.request().url()).origin===service.url?route.continue():route.abort('blockedbyclient'));
    const page=await context.newPage();page.setDefaultTimeout(timeoutMs);const errors=[];
    page.on('pageerror',e=>errors.push(e.message));
    page.on('console',msg=>{if(msg.type()==='error')errors.push(msg.text());});
    await page.goto(`${service.url}/video.html`,{waitUntil:'networkidle',timeout:timeoutMs});
    await page.waitForFunction(()=>window.__papertrails?.ready);
    const envelope=await voiceEnvelope(t.audio,t.fps,frames);
    const ready=await deadline(page.evaluate(({t,quality,envelope,allowSeek})=>window.__papertrails.init(t,{quality,envelope,allowSeek}),{t,quality,envelope,allowSeek:stillsOnly}),timeoutMs,'Scene initialization');
    await deadline(page.screenshot({type:'jpeg',quality:10,clip:{x:0,y:0,width:16,height:16},animations:'disabled'}),timeoutMs,'Post-init compositor warmup');
    if(errors.length)throw new Error(errors.join('\n'));
    const stillFrames=new Set(stills.map(s=>Math.min(frames-1,Math.round(s*t.fps))));
    if(stillsOnly){
      const result={version:1,frames,duration:t.duration,fps:t.fps,width:t.width,height:t.height,seed:t.seed,quality,stillsOnly:true,assetSource:ready.assetSource,stills:[]};
      const sorted=[...stillFrames].sort((a,b)=>a-b);
      for(let idx=0;idx<sorted.length;idx++){
        const frame=sorted[idx];
        const sample=await deadline(page.evaluate(f=>window.__papertrails.renderFrame(f),frame),timeoutMs,`Still frame ${frame}`);
        if(errors.length)throw new Error(errors.join('\n'));
        const image=await page.screenshot({type:'png',animations:'disabled',timeout:timeoutMs});
        const target=`${output}.still-${String(frame).padStart(6,'0')}.png`,tmp=`${target}.${token}.partial`;
        await writeFile(tmp,image);temporary.push({tmp,target});
        result.stills.push({path:target,frame,time:frame/t.fps,scene:sample.scene,caption:sample.caption,sha256:hash(image)});
        onProgress?.({frame:idx+1,frames:sorted.length,scene:sample.scene});
      }
      for(const f of temporary)await rename(f.tmp,f.target);
      await writeFile(metaPartial,JSON.stringify(result,null,2));
      await rename(metaPartial,`${output}.stills.json`);
      return result;
    }
    const renderFrames=eF-sF;
    const frameStride=renderFps&&renderFps>0?Math.max(1,Math.round(t.fps/renderFps)):1;
    const pipeFps=frameStride>1?(t.fps/frameStride):t.fps;
    const pipeCodec=frameFormat==='jpeg'?'mjpeg':'png';
    // Optional paper-flip at each cut, synthesized here and mixed UNDER the untouched voice (opt-in: --sfx).
    const cuts=t.scenes.slice(1).map(s=>s.start);
    const audioArgs=silentOnly?['-map','0:v:0','-an']:
      (sfx&&cuts.length?['-f','lavfi','-i','anoisesrc=d=0.34:c=pink:r=48000:a=0.5','-filter_complex',
        `[2:a]highpass=f=900,lowpass=f=7000,afade=t=in:d=0.02,afade=t=out:st=0.05:d=0.27,volume=0.22,asplit=${cuts.length}${cuts.map((_,i)=>`[n${i}]`).join('')};`+
        cuts.map((c,i)=>`[n${i}]adelay=${Math.max(0,Math.round((c-.14)*1000))}:all=1[d${i}]`).join(';')+';'+
        `[1:a]aresample=48000[v];[v]${cuts.map((_,i)=>`[d${i}]`).join('')}amix=inputs=${cuts.length+1}:normalize=0:duration=first[aout]`,'-map','0:v:0','-map','[aout]']
        :['-map','0:v:0','-map','1:a:0']);
    const inputs=silentOnly?['-f','image2pipe','-vcodec',pipeCodec,'-framerate',String(pipeFps),'-i','pipe:0']:['-f','image2pipe','-vcodec',pipeCodec,'-framerate',String(pipeFps),'-i','pipe:0','-i',t.audio];
    const vfArgs=frameStride>1?['-vf',`fps=${t.fps}`,'-r',String(t.fps)]:[];
    const audioCodecArgs=silentOnly?[]:['-c:a','aac','-b:a','192k'];
    const args=['-hide_banner','-loglevel','error','-y',...inputs,...audioArgs,...vfArgs,'-c:v','libx264','-preset',quality==='high'?'medium':'veryfast','-crf',quality==='low'?'25':quality==='high'?'18':'21','-pix_fmt','yuv420p',...audioCodecArgs,'-frames:v',String(renderFrames),'-movflags','+faststart',partial];
    encoder=spawn('ffmpeg',args,{stdio:['pipe','ignore','pipe'],windowsHide:true});
    encoder.on('error',e=>{encoderError=e;});encoder.stdin.on('error',e=>{encoderError=e;});
    encoder.stderr.on('data',d=>{stderr=(stderr+d.toString()).slice(-16000);});
    encoderDone=new Promise(resolve=>{encoder.once('close',code=>resolve(code));encoder.once('error',()=>resolve(-1));});
    const result={version:1,frames:renderFrames,totalTimelineFrames:frames,startFrame:sF,endFrame:eF,duration:renderFrames/t.fps,fps:t.fps,renderFps:pipeFps,frameFormat,quality,width:t.width,height:t.height,seed:t.seed,sfx:!!(!silentOnly&&sfx&&cuts.length),gpu:!!gpu,audio:silentOnly?null:t.audio,assetSource:ready.assetSource,repeatFrameStable:false,stills:[],shots:t.scenes.map(s=>({id:s.id,start:s.start,end:s.end,prop:s.prop,action:s.action,camera:s.camera,visual:s.visual}))};
    const shotOpts=frameFormat==='jpeg'?{type:'jpeg',quality:92,animations:'disabled',timeout:timeoutMs}:{type:'png',animations:'disabled',timeout:timeoutMs};
    for(let frame=sF;frame<eF;frame+=frameStride) {
      if(signalController.signal.aborted)throw new Error('Render interrupted');
      const sample=await deadline(page.evaluate(f=>window.__papertrails.renderFrame(f),frame),timeoutMs,`Frame ${frame}`);
      if(errors.length)throw new Error(errors.join('\n'));
      const image=await page.screenshot(shotOpts);
      if(frame===0){await page.evaluate(f=>window.__papertrails.renderFrame(f),frame);const repeat=await page.screenshot(shotOpts);result.repeatFrameStable=hash(image)===hash(repeat);if(!result.repeatFrameStable)throw new Error('Repeated exact frame differs');}
      if(stillFrames.has(frame)) {
        const stillImg=frameFormat==='png'?image:await page.screenshot({type:'png',animations:'disabled',timeout:timeoutMs});
        const target=`${output}.still-${String(frame).padStart(6,'0')}.png`,tmp=`${target}.${token}.partial`;
        await writeFile(tmp,stillImg);temporary.push({tmp,target});result.stills.push({path:target,frame,time:frame/t.fps,scene:sample.scene,caption:sample.caption,sha256:hash(stillImg)});
      }
      if(encoderError)throw encoderError;
      if(encoder.exitCode!==null)throw new Error(`ffmpeg exited early: ${stderr}`);
      if(!encoder.stdin.write(image))await deadline(Promise.race([once(encoder.stdin,'drain'),encoderDone.then(()=>{throw new Error(`ffmpeg closed: ${stderr}`);})]),timeoutMs,'ffmpeg pipe');
      const doneOut=Math.min(renderFrames,frame-sF+frameStride);
      onProgress?.({frame:doneOut,frames:renderFrames,globalFrame:Math.min(eF,frame+frameStride),totalFrames:frames,scene:sample.scene});
    }
    encoder.stdin.end();
    const code=await deadline(encoderDone,timeoutMs,'ffmpeg finalization');
    if(code!==0||encoderError)throw new Error(`ffmpeg failed (${code}): ${encoderError?.message||stderr}`);
    const {stdout}=await run('ffprobe',['-v','error','-show_streams','-show_format','-of','json',partial],{timeout:30000,maxBuffer:2e6});
    const probe=JSON.parse(stdout),video=probe.streams.find(s=>s.codec_type==='video');
    const hasAudio=probe.streams.some(s=>s.codec_type==='audio');
    if(!video||video.width!==t.width||video.height!==t.height||Number(video.nb_frames)!==renderFrames||(!silentOnly&&!hasAudio))throw new Error(`Encoded output failed verification: video ${video?.width}x${video?.height}, ${video?.nb_frames} frames (expected ${t.width}x${t.height}, ${renderFrames}), audio ${hasAudio}`);
    result.output=output;result.encodedDuration=Number(probe.format.duration);result.bytes=(await stat(partial)).size;
    await writeFile(metaPartial,JSON.stringify(result,null,2));
    for(const f of temporary)await rename(f.tmp,f.target);
    await rename(partial,output);await rename(metaPartial,`${output}.json`);
    return result;
  } finally {
    process.removeListener('SIGINT',abort);process.removeListener('SIGTERM',abort);
    if(encoder&&encoder.exitCode===null){encoder.kill('SIGKILL');await deadline(encoderDone,5000,'encoder cleanup').catch(()=>{});}
    await browser?.close().catch(()=>{});await server?.close();
    await Promise.all([partial,metaPartial,...temporary.map(f=>f.tmp)].map(f=>rm(f,{force:true}).catch(()=>{})));
  }
}
