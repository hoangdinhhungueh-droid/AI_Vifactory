#!/usr/bin/env node
import { renderVideo } from './lib/renderer.mjs';
const usage='Usage: node scripts/render.mjs timeline.json out.mp4 [--stills seconds-csv] [--stills-only] [--start-frame N] [--end-frame M] [--silent-only] [--quality low|med|high] [--sfx] [--gpu]';
async function main(){
  const [timeline,output,...args]=process.argv.slice(2);
  if(timeline==='--help'||timeline==='-h'){process.stdout.write(`${usage}\n\nTimeline scenes must cover the complete real audio duration.\nStills are sampled at the nearest output frame; quality never changes output dimensions.\nBrowser API: window.__papertrails.init(timeline, {quality}); renderFrame(frameIndex).\nOutputs: out.mp4, out.mp4.json, optional out.mp4.still-NNNNNN.png\n`);return;}
  if(!timeline||!output)throw new Error(usage);
  const options={quality:'med',stills:[]};
  for(let i=0;i<args.length;i++){
    if(args[i]==='--quality'&&args[i+1])options.quality=args[++i];
    else if(args[i]==='--sfx')options.sfx=true;
    else if(args[i]==='--gpu')options.gpu=true;
    else if(args[i]==='--stills-only')options.stillsOnly=true;
    else if(args[i]==='--silent-only')options.silentOnly=true;
    else if(args[i]==='--start-frame'&&args[i+1])options.startFrame=Number(args[++i]);
    else if(args[i]==='--end-frame'&&args[i+1])options.endFrame=Number(args[++i]);
    else if(args[i]==='--stills'&&args[i+1]){const value=args[++i];if(value.split(',').some(s=>!s.trim()))throw new Error('Empty still time');options.stills=value.split(',').map(Number);}
    else throw new Error(`Unknown/missing option: ${args[i]}\n${usage}`);
  }
  options.onProgress=({frame,frames,scene})=>{if(frame===1||frame===frames||frame%30===0)process.stderr.write(`[render] ${frame}/${frames} ${scene}\n`);};
  const result=await renderVideo(timeline,output,options);
  process.stdout.write(`${JSON.stringify(result,null,2)}\n`);
}
main().catch(e=>{console.error(`[render] ${e.message}`);process.exitCode=1;});
