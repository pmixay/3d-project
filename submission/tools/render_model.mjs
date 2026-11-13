// Renders preview PNGs of a GLB with three.js in headless Chromium (Playwright).
// Usage:  cd model/tools && npm i three@0.160.0 && node render.mjs ../out/hercules_printer.glb ../out/renders [view ...]
// Needs the 'playwright' package to be resolvable (globally installed is fine).
import { createRequire } from 'module'; const { chromium } = createRequire(import.meta.url)('playwright');
import http from 'http'; import fs from 'fs'; import path from 'path';
const [glb, outDir, ...only] = process.argv.slice(2);
const root = process.cwd();
const srv = http.createServer((q, r) => {
  let p = decodeURIComponent(q.url.split('?')[0]);
  let f = p === '/model.glb' ? glb : path.join(root, p);
  fs.readFile(f, (e, d) => { if (e) { r.writeHead(404); r.end(); return; }
    const t = f.endsWith('.js') ? 'text/javascript' : f.endsWith('.html') ? 'text/html' : 'application/octet-stream';
    r.writeHead(200, { 'Content-Type': t }); r.end(d); });
}).listen(0);
const port = srv.address().port;
const views = {
  // name: [camera position, target, hidden-part regex]   (printer coords: X right, Y back, Z up)
  front_iso: [[732, -778, 814], [182, 170, 250], 'toolhead_placeholder|psu|ghost'],
  front: [[182, -900, 330], [182, 170, 250], null],
  top: [[182, 170, 1300], [182, 177, 300], null],
  right_iso: [[1044, -454, 694], [182, 170, 250], 'toolhead_placeholder|psu|ghost'],
  tray_underside: [[182, 178, -620], [182, 178, 60], null],
  gantry_close: [[330, -90, 600], [182, 185, 400], 'toolhead_placeholder|psu|ghost'],
  rear_iso: [[-420, 900, 420], [182, 170, 200], null],
};
const b = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const pg = await b.newPage({ viewport: { width: 1400, height: 1100 }, deviceScaleFactor: 1 });
pg.on('console', m => console.log('page:', m.text()));
pg.on('pageerror', e => console.log('pageerror:', e.message));
await pg.goto(`http://localhost:${port}/render_viewer.html`);
await pg.waitForFunction('window.ready===true', null, { timeout: 120000 });
for (const [name, [pos, tgt, hide]] of Object.entries(views)) {
  if (only.length && !only.includes(name)) continue;
  await pg.evaluate(([pos, tgt, hide, up]) => window.setView(pos, tgt, hide, up), [pos, tgt, hide, name === 'top' ? [0, 1, 0] : name === 'tray_underside' ? [-1, 0, 0] : [0, 0, 1]]);
  await pg.screenshot({ path: path.join(outDir, name + '.png'), omitBackground: true });
  console.log('wrote', name);
}
await b.close(); srv.close();
