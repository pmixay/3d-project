// Studio renders of a GLB with three.js in headless Chromium (Playwright); the look is defined in viewer.html.
// Usage (from a directory that has node_modules/three, e.g. after `npm i three@0.160.0` in model/tools):
//   NODE_PATH=$(npm root -g) node /path/to/model/tools/render.mjs ../out/hercules_printer.glb ../out/renders [view ...]
// Needs the 'playwright' package to be resolvable (globally installed is fine).
import { createRequire } from 'module'; const { chromium } = createRequire(import.meta.url)('playwright');
import http from 'http'; import fs from 'fs'; import path from 'path'; import { fileURLToPath } from 'url';
const [glb, outDir, ...only] = process.argv.slice(2);
const here = path.dirname(fileURLToPath(import.meta.url));
const modRoot = fs.existsSync(path.join(process.cwd(), 'node_modules/three')) ? process.cwd() : here;
const srv = http.createServer((q, r) => {
  const p = decodeURIComponent(q.url.split('?')[0]);
  const f = p === '/model.glb' ? glb : p === '/viewer.html' ? path.join(here, 'viewer.html') : path.join(modRoot, p);
  fs.readFile(f, (e, d) => { if (e) { r.writeHead(404); r.end(); return; }
    const t = f.endsWith('.js') ? 'text/javascript' : f.endsWith('.html') ? 'text/html' : 'application/octet-stream';
    r.writeHead(200, { 'Content-Type': t }); r.end(d); });
}).listen(0);
const port = srv.address().port;
const Z = [0, 0, 1];
const views = {
  // name: [camera position, target, up vector, field of view, hidden-part regex]   (printer coords: X right, Y back, Z up; mm)
  hero: [[930, -960, 760], [182, 170, 270], Z, 26, null],
  front_iso: [[760, -1150, 900], [182, 170, 262], Z, 26, null],
  front: [[182, -1420, 360], [182, 170, 285], Z, 26, null],
  top: [[182, 170, 1500], [182, 177, 300], [0, 1, 0], 26, null],
  right_iso: [[1330, -600, 760], [182, 170, 262], Z, 26, null],
  rear_iso: [[-740, 1300, 760], [182, 180, 262], Z, 26, null],
  gantry_close: [[400, -130, 640], [182, 185, 395], Z, 32, null],
  tray_underside: [[182, 178, -860], [182, 178, 60], [-1, 0, 0], 30, null],
};
const W = 1600, H = 1200;
const b = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const pg = await b.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
pg.on('console', m => { const t = m.text(); if (!/GL Driver Message/.test(t)) console.log('page:', t); });
pg.on('pageerror', e => console.log('pageerror:', e.message));
await pg.goto(`http://localhost:${port}/viewer.html?ss=2`);   // rendered at 2x and downsampled by the browser
await pg.waitForFunction('window.ready===true', null, { timeout: 180000 });
for (const [name, [pos, tgt, up, fov, hide]] of Object.entries(views)) {
  if (only.length && !only.includes(name)) continue;
  await pg.evaluate(([pos, tgt, hide, up, fov]) => window.setView(pos, tgt, hide, up, fov), [pos, tgt, hide, up, fov]);
  await pg.screenshot({ path: path.join(outDir, name + '.png') });
  console.log('wrote', name);
}
await b.close(); srv.close();
