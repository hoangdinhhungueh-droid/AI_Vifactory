import { build } from '../../engine/node_modules/vite/dist/node/index.js';
import { fileURLToPath } from 'node:url';
import { existsSync } from 'node:fs';
const engine=fileURLToPath(new URL('../../engine/',import.meta.url));
await build({root:engine,configFile:false,base:'./',build:{target:'es2022',outDir:'dist',assetsInlineLimit:0,chunkSizeWarningLimit:1500,rolldownOptions:{input:{...(existsSync(`${engine}index.html`)?{game:`${engine}index.html`}:{}),video:`${engine}video.html`}}}});
// The lite package ships without the interactive game entry (engine/index.html); only the video entry is built then.
