// Build Hefest_golova_poyasnitelnaya_zapiska.pdf from head/README.md (without section 6 "Файлы").
// Markdown -> HTML with pandoc, then printed to A4 PDF in Chromium (Playwright). Fonts: Montserrat from fonts/.
// Run from anywhere:  node submission/tools/make_head_pdf.mjs
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");

const TOOLS = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(TOOLS, "../..");
const HEAD = path.join(REPO, "head");
const BUILD = path.join(TOOLS, "build");
const OUT = path.join(REPO, "submission", "Hefest_golova_poyasnitelnaya_zapiska.pdf");

let md = fs.readFileSync(path.join(HEAD, "README.md"), "utf8");
md = md.split(/^## 6\. Файлы/m)[0];
// image paths in the note are relative to head/
md = md.replace(/src="([^"]+)"/g, (_, src) => `src="${pathToFileURL(path.resolve(HEAD, src)).href}"`);

const body = execFileSync("pandoc", ["-f", "gfm", "-t", "html"], { input: md, encoding: "utf8" });

const font = (file, weight) =>
  `@font-face{font-family:"Montserrat";font-weight:${weight};src:url("${pathToFileURL(path.join(TOOLS, "fonts", file)).href}")}`;

const css = `
${font("Montserrat-Regular.ttf", 400)}
${font("Montserrat-Medium.ttf", 500)}
${font("Montserrat-SemiBold.ttf", 600)}
${font("Montserrat-Bold.ttf", 700)}
@page { size: A4; margin: 18mm 17mm 18mm 17mm; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { font-family: "Montserrat", sans-serif; font-size: 9.6pt; line-height: 1.5; color: #1d2327; margin: 0; }
h1 { color: #0f5a63; font-size: 17pt; font-weight: 700; line-height: 1.3; margin: 0 0 10pt; }
h2 { color: #0f5a63; font-size: 12.5pt; font-weight: 700; margin: 16pt 0 8pt; padding-bottom: 4pt;
     border-bottom: 1px solid #c9d8db; break-after: avoid; }
p { margin: 0 0 7pt; }
h2 + p { break-after: avoid; }
strong { font-weight: 700; }
em { color: #5b6770; }
ol, ul { margin: 0 0 8pt; padding-left: 18pt; }
li { margin: 0 0 2pt; }
p:has(> img) { text-align: center; margin: 10pt 0 6pt; break-inside: avoid; }
img { vertical-align: middle; width: auto; height: auto; max-width: 48%; max-height: 74mm; margin: 0 1%; }
table { width: 100%; border-collapse: collapse; margin: 4pt 0 10pt; font-size: 8.4pt; line-height: 1.45; }
thead { display: table-header-group; }
tr { break-inside: avoid; }
table:last-of-type { break-inside: avoid; }
th, td { border: 1px solid #cfd9dc; padding: 5pt 7pt; vertical-align: top; text-align: left; }
th { background: #e8f0f1; font-weight: 700; }
td:first-child, th:first-child { width: 27%; }
th[style*="right"], td[style*="right"] { text-align: right; }
`;

const html = `<!doctype html><html lang="ru"><head><meta charset="utf-8">
<title>Печатная голова Hefest - пояснительная записка</title><style>${css}</style></head>
<body>${body}</body></html>`;

fs.mkdirSync(BUILD, { recursive: true });
const htmlPath = path.join(BUILD, "head_note.html");
fs.writeFileSync(htmlPath, html);

const browser = await chromium.launch();
const page = await browser.newPage();
await page.goto(pathToFileURL(htmlPath).href, { waitUntil: "load" });
await page.evaluate(() => document.fonts.ready);
await page.pdf({ path: OUT, format: "A4", printBackground: true, preferCSSPageSize: true });
await browser.close();
console.log("saved", OUT);
