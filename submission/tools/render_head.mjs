// Renders PNGs of the print head GLB (head coordinates) with three.js in headless Chromium.
// Usage:  node render_head.mjs <head.glb> <views.json> <out dir> [view ...]     (needs three@0.160.0 in ./node_modules)
// views.json: { name: { dir, target, span, up?, hide?, only?, size?: [w, h], fit?: width / height } } - see render_head_viewer.html
import { createRequire } from 'module'; const { chromium } = createRequire(import.meta.url)('playwright');
import http from 'http'; import fs from 'fs'; import path from 'path'; import { fileURLToPath } from 'url';
const [glb, viewsFile, outDir, ...only] = process.argv.slice(2);
const here = path.dirname(fileURLToPath(import.meta.url));
const views = JSON.parse(fs.readFileSync(viewsFile, 'utf8'));
const srv = http.createServer((q, r) => {
  const p = decodeURIComponent(q.url.split('?')[0]);
  const f = p === '/model.glb' ? glb : p.startsWith('/node_modules/') ? path.join(process.cwd(), p) : path.join(here, p);
  fs.readFile(f, (e, d) => { if (e) { r.writeHead(404); r.end(); return; }
    r.writeHead(200, { 'Content-Type': f.endsWith('.js') ? 'text/javascript' : f.endsWith('.html') ? 'text/html' : 'application/octet-stream' }); r.end(d); });
}).listen(0);
const b = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
fs.mkdirSync(outDir, { recursive: true });
for (const [name, v] of Object.entries(views)) {
  if (only.length && !only.includes(name)) continue;
  const [w, h] = v.size || [1000, 1000];
  const pg = await b.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: 2 });
  pg.on('pageerror', e => console.log('pageerror:', e.message));
  await pg.goto(`http://localhost:${srv.address().port}/render_head_viewer.html`);
  await pg.waitForFunction('window.ready===true', null, { timeout: 180000 });
  await pg.evaluate(v => window.setView(v), v);
  let clip;
  if (v.fit) {   // crop to the model with a margin, then widen or heighten the crop to the aspect ratio fit = width / height
    const [x0, y0, x1, y1] = await pg.evaluate(() => window.drawnBox()), m = 6;
    if (x0 <= 0 || y0 <= 0 || x1 >= w || y1 >= h) console.log('warning:', name, 'touches the frame edge, increase span');
    let cw = x1 - x0 + 2 * m, ch = y1 - y0 + 2 * m;
    if (cw / ch < v.fit) cw = ch * v.fit; else ch = cw / v.fit;
    clip = { x: (x0 + x1 - cw) / 2, y: (y0 + y1 - ch) / 2, width: cw, height: ch };
  }
  await pg.screenshot({ path: path.join(outDir, name + '.png'), omitBackground: true, clip });
  await pg.close(); console.log('wrote', name);
}
await b.close(); srv.close();
