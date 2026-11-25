// Build the exhibition stand from submission/stand/stand.html:
//   submission/Hefest_stend.pdf          one banner 1600 x 1000 mm for print (fold lines at 400 and 1200 mm are not drawn)
//   submission/stand/preview.png         the same banner with the fold lines shown, for checking on screen
// Run from anywhere:  node submission/tools/make_stand.mjs      (needs playwright)
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");

const TOOLS = path.dirname(fileURLToPath(import.meta.url));
const STAND = path.resolve(TOOLS, "../stand");
const OUT = path.resolve(TOOLS, "../Hefest_stend.pdf");
const MM = 96 / 25.4;                                   // CSS pixels per millimetre
const W = Math.round(1600 * MM), H = Math.round(1000 * MM);

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 0.5 });
await page.goto(pathToFileURL(path.join(STAND, "stand.html")).href, { waitUntil: "load" });
await page.evaluate(() => document.fonts.ready);

// anything that does not fit its block is a layout error: report it instead of printing it cut off
const clipped = await page.evaluate(() => [...document.querySelectorAll(".card, .panel, .title")]
  .filter(e => e.scrollHeight > e.clientHeight + 2 || e.scrollWidth > e.clientWidth + 2)
  .map(e => `${e.className}: content ${e.scrollWidth}x${e.scrollHeight} in ${e.clientWidth}x${e.clientHeight}`));
for (const c of clipped) console.log("does not fit:", c);

await page.pdf({ path: OUT, width: "1600mm", height: "1000mm", printBackground: true, preferCSSPageSize: true });
await page.evaluate(() => document.body.classList.add("preview"));
await page.screenshot({ path: path.join(STAND, "preview.png") });
await browser.close();
console.log("saved", OUT, "and preview.png");
process.exit(clipped.length ? 1 : 0);
