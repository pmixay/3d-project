"""Build an editable PPTX from the same HTML slides as the PDF.

Each slide gets a picture of everything except text (background, cards, images, diagram lines)
and native PowerPoint text boxes on top, placed where the browser laid the text out.
Run make_slides.py first (it writes build/slides.html).

Run:  python3 submission/tools/make_pptx.py
Output: submission/Hercules_prezentaciya.pptx
"""
import json
import pathlib
import subprocess

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.util import Emu, Pt

TOOLS = pathlib.Path(__file__).resolve().parent
BUILD = TOOLS / "build"
OUT = TOOLS.parent / "Hercules_prezentaciya.pptx"
PX = 9525  # EMU per CSS pixel (1280 px = 13.333 in)

JS = r"""
const { chromium } = require('playwright');
(async () => {
  const [html, outDir] = process.argv.slice(2);
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 2 });
  await p.goto('file://' + html); await p.evaluate(() => document.fonts.ready); await p.waitForTimeout(300);
  const data = await p.evaluate(() => {
    const isInline = el => getComputedStyle(el).display === 'inline';
    const hasDirectText = el => [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
    const slides = [...document.querySelectorAll('section.slide')];
    return slides.map(sec => {
      const base = sec.getBoundingClientRect();
      const blocks = [];
      const all = [...sec.querySelectorAll('*')];
      for (const el of all) {
        if (isInline(el) || el.tagName === 'BR') continue;
        // a block holds text either directly or through inline children only
        const inlineText = [...el.childNodes].some(n => (n.nodeType === 3 && n.textContent.trim()) ||
          (n.nodeType === 1 && isInline(n) && n.textContent.trim()));
        if (!inlineText) continue;
        const runs = [];
        const walk = (node) => {
          for (const n of node.childNodes) {
            if (n.nodeType === 3) {
              const t = n.textContent.replace(/[ \t\n\r]+/g, ' ');
              if (!t) continue;
              const pe = n.parentElement, cs = getComputedStyle(pe);
              const a = pe.closest('a');
              runs.push({ text: t, font: cs.fontFamily, size: parseFloat(cs.fontSize), weight: parseInt(cs.fontWeight),
                          color: cs.color, href: a ? a.href : null });
            } else if (n.nodeType === 1) {
              if (n.tagName === 'BR') runs.push({ br: true });
              else if (isInline(n)) walk(n);
            }
          }
        };
        walk(el);
        if (!runs.some(r => r.text && r.text.trim())) continue;
        const cs = getComputedStyle(el);
        const r = document.createRange(); r.selectNodeContents(el);
        const rects = [...r.getClientRects()].filter(q => q.width > 0);
        const box = el.getBoundingClientRect();
        const pl = parseFloat(cs.paddingLeft), pr = parseFloat(cs.paddingRight), pt = parseFloat(cs.paddingTop), pb = parseFloat(cs.paddingBottom);
        let top = box.top + pt, bottom = box.bottom - pb;
        if (rects.length) { top = Math.min(...rects.map(q => q.top)); bottom = Math.max(...rects.map(q => q.bottom)); }
        let lh = parseFloat(cs.lineHeight); if (isNaN(lh)) lh = parseFloat(cs.fontSize) * 1.2;
        blocks.push({ x: box.left + pl - base.left, y: top - base.top, w: box.width - pl - pr, h: bottom - top,
                      align: cs.textAlign, lineHeight: lh, fontSize: parseFloat(cs.fontSize), runs });
      }
      return blocks;
    });
  });
  require('fs').writeFileSync(outDir + '/text.json', JSON.stringify(data));
  await p.addStyleTag({ content: '*{color:transparent !important;-webkit-text-fill-color:transparent !important}' });
  await p.waitForTimeout(200);
  const secs = await p.$$('section.slide');
  for (let i = 0; i < secs.length; i++) await secs[i].screenshot({ path: `${outDir}/bg_${String(i + 1).padStart(2, '0')}.jpg`, type: 'jpeg', quality: 92 });
  await b.close();
})();
"""


def rgb(css):
    nums = css[css.index("(") + 1:css.index(")")].split(",")
    return RGBColor(*[int(float(v)) for v in nums[:3]])


def font_name(family, weight):
    fam = family.split(",")[0].strip().strip("'\"")
    if fam == "Benzin":
        return ("Benzin-Semibold", False) if weight < 700 else ("Benzin-Bold", False)
    if weight >= 700:
        return "Montserrat", True
    if weight >= 600:
        return "Montserrat SemiBold", False
    if weight >= 500:
        return "Montserrat Medium", False
    return "Montserrat", False


def add_link_area(slide, x, y, w, h, href):
    """Invisible clickable rectangle: keeps the design colours instead of PowerPoint's blue link style."""
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.oxml.ns import qn
    shp = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Emu(int(x * PX)), Emu(int(y * PX)), Emu(int(w * PX)), Emu(int(h * PX)))
    shp.fill.solid()
    shp.fill.fore_color.rgb = RGBColor(0, 0, 0)
    srgb = shp.fill._xPr.find(qn("a:solidFill")).find(qn("a:srgbClr"))
    alpha = srgb.makeelement(qn("a:alpha"), {"val": "0"})
    srgb.append(alpha)
    shp.line.fill.background()
    shp.shadow.inherit = False
    shp.click_action.hyperlink.address = href
    shp.name = "link"


def main():
    js = BUILD / "pptx_extract.js"
    js.write_text(JS)
    work = BUILD / "pptx"
    work.mkdir(exist_ok=True)
    subprocess.run(["node", str(js), str(BUILD / "slides.html"), str(work)], check=True)
    data = json.loads((work / "text.json").read_text())

    prs = Presentation()
    prs.slide_width, prs.slide_height = Emu(1280 * PX), Emu(720 * PX)
    blank = prs.slide_layouts[6]
    for i, blocks in enumerate(data, start=1):
        s = prs.slides.add_slide(blank)
        s.shapes.add_picture(str(work / f"bg_{i:02d}.jpg"), 0, 0, prs.slide_width, prs.slide_height)
        for b in blocks:
            pad = 3
            extra = 0.05 * b["w"] + 8  # slack for font metric differences between browser and PowerPoint
            shift = {"center": extra / 2, "right": extra, "end": extra}.get(b["align"], 0)
            bx, bw = b["x"] - pad - shift, b["w"] + 2 * pad + extra
            tb = s.shapes.add_textbox(Emu(int(bx * PX)), Emu(int(b["y"] * PX)),
                                      Emu(int(bw * PX)), Emu(int(max(b["h"], 10) * PX)))
            tf = tb.text_frame
            tf.word_wrap = True
            tf.auto_size = MSO_AUTO_SIZE.NONE
            tf.vertical_anchor = MSO_ANCHOR.TOP
            tf.margin_left = tf.margin_right = Emu(pad * PX)
            tf.margin_top = tf.margin_bottom = 0
            para = tf.paragraphs[0]
            first = True
            links = set()

            def setup(pg):
                pg.alignment = {"center": PP_ALIGN.CENTER, "right": PP_ALIGN.RIGHT, "end": PP_ALIGN.RIGHT}.get(b["align"], PP_ALIGN.LEFT)
                pg.line_spacing = Pt(b["lineHeight"] * 0.75)
                pg.space_before = pg.space_after = 0

            setup(para)
            runs = b["runs"]
            # trim leading/trailing spaces of the block
            texts = [r for r in runs if "text" in r]
            if texts:
                texts[0]["text"] = texts[0]["text"].lstrip()
                texts[-1]["text"] = texts[-1]["text"].rstrip()
            for r in runs:
                if r.get("br"):
                    para = tf.add_paragraph()
                    setup(para)
                    first = True
                    continue
                t = r["text"]
                if first:
                    t = t.lstrip()
                if not t:
                    continue
                first = False
                run = para.add_run()
                run.text = t
                name, bold = font_name(r["font"], r["weight"])
                run.font.name = name
                run.font.bold = bold
                run.font.size = Pt(round(r["size"] * 0.75 * 2) / 2)
                run.font.color.rgb = rgb(r["color"])
                if r.get("href"):
                    links.add(r["href"])
            for href in links:
                add_link_area(s, b["x"], b["y"], b["w"], b["h"], href)
    prs.save(OUT)
    print("saved", OUT)


if __name__ == "__main__":
    main()
