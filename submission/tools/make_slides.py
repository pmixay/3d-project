"""Build the 10-slide presentation (PDF, 16:9) for the 3D Profi application.

Fonts are not stored in the repository: put Benzin-*.ttf and Montserrat-*.ttf into
submission/tools/fonts/ before running.

Run:  python3 submission/tools/make_slides.py
Output: submission/Hercules_prezentaciya.pdf and slide PNGs in submission/materials/
"""
import pathlib
import re
import subprocess

import segno

from links import LINKS

TOOLS = pathlib.Path(__file__).resolve().parent
SUB = TOOLS.parent
BUILD = TOOLS / "build"
BUILD.mkdir(exist_ok=True)
FONTS = (TOOLS / "fonts").as_uri()
IMG = (SUB / "materials" / "img").as_uri()

TOTAL = 10


def short(url):
    return url.replace("https://", "")


def disp(url):
    u = short(url).replace("/blob/main", "").replace("/tree/main", "").replace("/raw/main", "")
    return u


CSS = f"""
@font-face{{font-family:'Benzin';src:url('{FONTS}/Benzin-Semibold.ttf');font-weight:600}}
@font-face{{font-family:'Benzin';src:url('{FONTS}/Benzin-Bold.ttf');font-weight:700}}
@font-face{{font-family:'Benzin';src:url('{FONTS}/Benzin-ExtraBold.ttf');font-weight:800}}
@font-face{{font-family:'Mont';src:url('{FONTS}/Montserrat-Regular.ttf');font-weight:400}}
@font-face{{font-family:'Mont';src:url('{FONTS}/Montserrat-Medium.ttf');font-weight:500}}
@font-face{{font-family:'Mont';src:url('{FONTS}/Montserrat-SemiBold.ttf');font-weight:600}}
@font-face{{font-family:'Mont';src:url('{FONTS}/Montserrat-Bold.ttf');font-weight:700}}
:root{{
  --bg:#101315; --glow:#1a3a3f; --text:#f2f4f5; --teal:#2bd1c2; --teal-d:#1f8f86;
  --orange:#ff7a1a; --card:#172024; --line:#2b373b;
}}
@page{{size:1280px 720px;margin:0}}
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{background:var(--bg)}}
body{{font-family:'Mont';color:var(--text);-webkit-print-color-adjust:exact;print-color-adjust:exact}}
.slide{{width:1280px;height:720px;position:relative;overflow:hidden;page-break-after:always;
  background:radial-gradient(ellipse 900px 600px at 78% 45%,var(--glow) 0%,var(--bg) 70%)}}
.pad{{position:absolute;left:64px;right:64px;top:56px;bottom:56px}}
h1{{font-family:'Benzin';font-weight:700;font-size:44px;line-height:1.12;letter-spacing:.005em}}
h2{{font-family:'Benzin';font-weight:700;font-size:32px;line-height:1.15;margin-bottom:34px}}
.o{{color:var(--orange)}} .t{{color:var(--teal)}}
p,li{{font-size:19px;line-height:1.42;font-weight:500}}
.lead{{font-size:23px;line-height:1.4;font-weight:500}}
.num-page{{position:absolute;right:64px;bottom:34px;font-family:'Benzin';font-weight:600;font-size:16px;color:var(--teal)}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:24px 26px}}
.big{{font-family:'Benzin';font-weight:700;color:var(--teal);font-size:40px;line-height:1.05;margin-bottom:14px;white-space:nowrap}}
.grid3{{display:grid;grid-template-columns:repeat(3,1fr);gap:22px}}
ul.dots{{list-style:none}}
ul.dots li{{position:relative;padding-left:30px;margin-bottom:16px}}
ul.dots li:before{{content:'';position:absolute;left:0;top:9px;width:12px;height:12px;border-radius:3px;background:var(--teal)}}
a{{color:var(--teal);text-decoration:none}}
a.u{{border-bottom:2px solid var(--teal-d)}}
.img{{position:absolute;display:block}}
table.cmp{{width:100%;border-collapse:collapse}}
table.cmp th{{font-family:'Benzin';font-weight:700;font-size:19px;text-align:left;padding:0 16px 14px 0}}
table.cmp td{{font-size:19px;font-weight:500;padding:11px 16px 11px 0;border-top:1px solid var(--line)}}
table.cmp td:first-child,table.cmp th:first-child{{width:260px}}
table.cmp td:nth-child(2),table.cmp th:nth-child(2){{width:380px}}
"""


_counter = [1]


def page(_n, body, extra_class=""):
    _counter[0] += 1
    n = _counter[0]
    return f'<section class="slide {extra_class}">{body}<div class="num-page">{n:02d} / {TOTAL}</div></section>'


slides = []

# 1 ─ Title
slides.append(f"""<section class="slide">
 <img class="img" src="{IMG}/printer_front.png" style="right:40px;top:-10px;height:740px">
 <div class="pad" style="width:660px">
  <h1 style="margin-top:104px">Imprinta <span class="o">Hercules</span>: новый принтер на старой раме</h1>
  <p class="lead" style="margin-top:28px;width:570px">Пересобрали серийный принтер 2016 года — от оригинала остались только рама и&nbsp;механика осей</p>
  <div style="position:absolute;bottom:0;left:0">
   <p style="font-weight:700;font-size:21px" class="t">Команда «[Название команды]»</p>
   <p style="margin-top:6px">Чемпионат «3D Профи»</p>
   <p>Направление «Оборудование для 3D-печати»</p>
  </div>
 </div>
</section>""")

# 1b ─ Why it matters
need = [
    ("Устаревший парк принтеров", "Школы, «Кванториумы», «Точка роста», «IT-кубы», ЦМИТ и вузы массово закупали 3D-принтеры в 2015–2020 годах. Первое поколение уже не справляется с современными задачами."),
    ("Замена стоит дорого", "Новый быстрый закрытый принтер — от 70 000 ₽. Для школы это бюджет на целый кабинет, а исправная механика старого принтера уходит в утиль."),
    ("Закрытые экосистемы", "Современные быстрые принтеры — это фирменные запчасти и облачные сервисы производителя. Klipper и открытая документация дают ремонт на месте и любые серийные компоненты."),
    ("Кадры для отрасли", "Пересборка — готовый учебный проект: электроника, CAD, прошивка, калибровка. Студенты понимают устройство оборудования, а не только нажимают «Печать»."),
]
need_html = "".join(
    f'<div style="border-top:2px solid var(--line);padding-top:16px"><div style="font-family:Benzin;font-weight:700;font-size:22px;color:var(--teal);margin-bottom:12px">{t}</div><p style="font-size:19px">{d}</p></div>'
    for t, d in need)
slides.append(page(0, f"""<div class="pad">
 <h2>Почему это нужно сейчас</h2>
 <div style="display:grid;grid-template-columns:1fr 1fr;gap:34px 56px">{need_html}</div>
 <p class="lead" style="position:absolute;left:0;right:0;bottom:24px">Наш подход превращает списанный принтер в&nbsp;современный — <span class="t">на&nbsp;той же механике и за&nbsp;долю цены нового</span></p>
</div>"""))

# 2 ─ Only the frame is left
def chip(t, color):
    return (f'<span style="display:inline-block;border:1.5px solid {color};border-radius:999px;padding:8px 18px;'
            f'margin:0 10px 12px 0;font-weight:600;font-size:17px">{t}</span>')


kept_parts = ["Стальная рама 2 мм", "Рельсы X и Y", "Ось Z", "Стол и стекло", "Моторы NEMA17", "Ремни GT2", "Дисплей"]
new_parts = ["Плата SKR 3 EZ", "Плата на голове EBB42 GEN2", "Печатная голова Hefest", "Хотенд CHC Pro",
             "Экструдер K3D Minifeeder + NEMA14", "Драйверы TMC", "Блок питания 350 Вт", "Один кабель CAN",
             "Обдув 5015 и 3010", "Датчик стола MicroProbe", "Сопло Volcano NCB", "Чистка сопла",
             "Klipper и ИИ-контроль"]
slides.append(page(2, f"""
 <img class="img" src="{IMG}/printer_right.png" style="left:30px;top:150px;height:560px;opacity:.95">
 <div class="pad">
  <h2>Механика осталась, остальное — новое</h2>
  <div style="position:absolute;left:500px;top:92px;width:652px">
   <div style="font-family:Benzin;font-weight:700;font-size:21px;color:var(--orange);margin-bottom:14px">Оставили механику</div>
   <div style="margin-bottom:22px">{"".join(chip(t, "var(--orange)") for t in kept_parts)}</div>
   <div style="font-family:Benzin;font-weight:700;font-size:21px;color:var(--teal);margin-bottom:14px">Сделали заново</div>
   <div>{"".join(chip(t, "var(--teal)") for t in new_parts)}</div>
  </div>
 </div>"""))

# 3 ─ Baseline comparison with the stock Hercules
rows = [
    ("Электроника", "8-битная плата, ~99 000 шагов/с", "32-битная SKR 3 EZ, 1 800 000+ шагов/с"),
    ("Хотенд", "UniHOT, до 260 °C", "CHC Pro 115 Вт, до 300 °C"),
    ("Сопло", "латунное 0,5 мм", "биметаллическое, для композитов"),
    ("Скорость печати", "заявлено до 150 мм/с", "цель — до 300 мм/с"),
    ("Калибровка стола", "ручная, по трём точкам", "автоматическая, 0,002 мм"),
    ("Вибрации", "не компенсируются", "Input Shaper по акселерометру"),
    ("Проводка к голове", "многожильный жгут", "один кабель CAN, 4 провода"),
    ("Обслуживание", "вручную", "автоочистка сопла, ИИ-контроль"),
]
trs = "".join(
    f'<tr><td style="font-weight:700">{a}</td><td>{b}</td><td class="t" style="font-weight:700">{c}</td></tr>' for a, b, c in rows)
slides.append(page(3, f"""<div class="pad">
 <h2>Сравнение с серийным Hercules</h2>
 <table class="cmp">
  <tr><th></th><th>Hercules 2016</th><th class="t">Наш Hercules</th></tr>
  {trs}
 </table>
</div>"""))

# 4 ─ Architecture diagram
def box(x, y, w, h, title, sub="", main=False):
    border = "var(--teal)" if main else "var(--line)"
    bw = "2px" if main else "1px"
    s = f'<div style="font-size:15.5px;font-weight:600;color:var(--teal);margin-top:4px;line-height:1.3">{sub}</div>' if sub else ""
    fs = "21px" if main else "17px"
    return (f'<div style="position:absolute;left:{x}px;top:{y}px;width:{w}px;height:{h}px;background:var(--card);'
            f'border:{bw} solid {border};border-radius:14px;padding:12px 16px;display:flex;flex-direction:column;justify-content:center">'
            f'<div style="font-weight:700;font-size:{fs};line-height:1.2">{title}</div>{s}</div>')


def label(x, y, text, w=140, align="center"):
    return (f'<div style="position:absolute;left:{x}px;top:{y}px;width:{w}px;text-align:{align};'
            f'font-size:16px;font-weight:700;color:var(--teal)">{text}</div>')


c1x, c1w = 0, 236
skx, skw = 346, 230
ebx, ebw = 712, 196
c4x, c4w = 960, 192
rows1 = [(20, "Ноутбук", "хост Klipper"), (152, "Дисплей", "с энкодером"), (284, "MeanWell 350 Вт", "24 В")]
diagram = []
svg = []
for y, t, s in rows1:
    diagram.append(box(c1x, y, c1w, 92, t, s))
    cy = y + 46
    svg.append(f'<line x1="{c1w}" y1="{cy}" x2="{skx}" y2="{cy}" stroke="#2bd1c2" stroke-width="2"/>')
diagram.append(label(c1w, 20 + 18, "USB", skx - c1w))
diagram.append(label(c1w, 152 + 18, "EXP1/2", skx - c1w))
diagram.append(label(c1w, 284 + 18, "24 В", skx - c1w))
diagram.append(box(skx, 20, skw, 356, "BTT SKR 3 EZ", "STM32H7, 480 МГц<br>драйверы X, Y, Z<br>в отсеке электроники", main=True))
# CAN link
ey, eh = 120, 156
svg.append(f'<line x1="{skx+skw}" y1="{ey+eh/2}" x2="{ebx}" y2="{ey+eh/2}" stroke="#2bd1c2" stroke-width="6"/>')
diagram.append(label(skx + skw, ey + eh / 2 - 34, "CAN + 24 В", ebx - skx - skw))
diagram.append(label(skx + skw, ey + eh / 2 + 12, "4 провода", ebx - skx - skw))
diagram.append(box(ebx, ey, ebw, eh, "EBB42 GEN2", "плата на печатной голове", main=True))
rows4 = [("Хотенд CHC Pro", "115 Вт"), ("Экструдер", "NEMA14, 5:1"), ("Датчик стола", "MicroProbe V2"),
         ("Вентиляторы", "5015 и 3010"), ("Акселерометр", "на плате")]
for i, (t, s) in enumerate(rows4):
    y = 6 + i * 76
    diagram.append(box(c4x, y, c4w, 64, t, s).replace("padding:12px 16px", "padding:6px 14px"))
    svg.append(f'<path d="M{ebx+ebw} {ey+eh/2} C {ebx+ebw+30} {ey+eh/2}, {c4x-30} {y+32}, {c4x} {y+32}" fill="none" stroke="#2bd1c2" stroke-width="2"/>')
slides.append(page(3, f"""<div class="pad">
 <h2>Архитектура: один кабель к голове</h2>
 <div style="position:relative;height:390px">
  <svg width="1152" height="390" style="position:absolute;left:0;top:0">{''.join(svg)}</svg>
  {''.join(diagram)}
 </div>
 <p style="margin-top:20px;width:1060px">Разъём XT30 рассчитан на <b class="t">15 А</b> при рабочем токе <b class="t">2,94 А</b> — запас более чем в 5 раз.
 Выходы платы защищены от короткого замыкания, температура контролируется в Klipper.</p>
</div>"""))

# 4 ─ Hefest head
slides.append(page(4, f"""
 <img class="img" src="{IMG}/hefest_parts_front.png" style="left:48px;top:170px;height:370px">
 <img class="img" src="{IMG}/hefest_parts_rear.png" style="left:338px;top:200px;height:370px">
 <div class="pad">
  <h2>Печатная голова Hefest — наша разработка</h2>
  <div style="position:absolute;left:640px;top:96px;width:512px">
   <ul class="dots">
    <li>Спроектирована командой с нуля в КОМПАС-3D под каретку MGN12H</li>
    <li>Шесть печатных деталей: рама, крышка ремня, ферма, две обоймы хотенда, воздуховод</li>
    <li>Объединяет хотенд CHC Pro, экструдер K3D Minifeeder, плату EBB42 GEN2, датчик MicroProbe и обдув 5015 + 3010</li>
    <li>Зазоры до ремней проверяем собственным скриптом по STL-моделям</li>
   </ul>
   <p style="margin-top:18px"><a class="u" href="{LINKS['head']}">Подробнее о голове на GitHub</a></p>
  </div>
 </div>"""))

# 5 ─ Automation
steps = ["Нагрев сопла до 150 °C без подтёков", "Чистка сопла о силиконовую щётку", "Точный Z-offset контактным датчиком",
         "Карта высот только под деталью (KAMP)", "Печать под контролем ИИ-камеры"]
step_html = "".join(
    f'<div class="card" style="padding:24px 22px;min-height:250px"><div class="big" style="font-size:40px;margin-bottom:22px">{i+1:02d}</div><p style="font-size:20px">{t}</p></div>'
    for i, t in enumerate(steps))
tools_ = [("Shake&amp;Tune", "натяжение ремней и фильтры Input Shaper по встроенному акселерометру"),
          ("TMC Autotune", "тихие моторы без вертикальных артефактов на стенках"),
          ("Pressure Advance", "чёткие углы на высокой скорости в OrcaSlicer")]
tools_html = "".join(f'<p style="border-top:2px solid var(--line);padding-top:16px"><b class="t">{a}</b> — {b}</p>' for a, b in tools_)
slides.append(page(0, f"""<div class="pad">
 <h2>Автоматизация уровня флагманов</h2>
 <p class="lead" style="margin:-12px 0 22px">Каждая печать начинается одинаково — без ручной калибровки:</p>
 <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:16px">{step_html}</div>
 <div class="grid3" style="position:absolute;left:0;right:0;bottom:30px;gap:34px">{tools_html}</div>
</div>"""))

# 7 ─ Budget
slides.append(page(7, f"""<div class="pad">
 <h2>Стоимость пересборки</h2>
 <div style="position:absolute;left:0;top:96px;width:760px">
  <div style="display:flex;justify-content:space-between;align-items:baseline"><p>Этап 1: хотенд, экструдер, драйверы, питание, обдув</p><div style="font-family:Benzin;font-weight:700;font-size:24px">[сумма] ₽</div></div>
  <div style="height:16px;border-radius:8px;background:repeating-linear-gradient(45deg,#1f8f86 0 10px,#176a64 10px 20px);margin-top:10px"></div>
  <div style="display:flex;justify-content:space-between;align-items:baseline;margin-top:34px"><p>Этап 2: электроника, датчик, автоматизация</p><div style="font-family:Benzin;font-weight:700;font-size:24px">15 315 ₽</div></div>
  <div style="display:flex;height:58px;margin-top:10px;border:1.5px solid var(--teal-d);border-radius:10px;overflow:hidden">
   <div style="width:57.8%;background:var(--teal);color:#06201e;font-weight:700;font-size:18px;display:flex;align-items:center;padding-left:18px">Платы: 8 857 ₽</div>
   <div style="width:17.2%;background:#7fe3d9;color:#06201e;font-weight:700;font-size:18px;display:flex;align-items:center;padding-left:12px">2 628 ₽</div>
   <div style="width:25%;background:repeating-linear-gradient(45deg,#1f8f86 0 10px,#176a64 10px 20px);font-weight:700;font-size:18px;display:flex;align-items:center;padding-left:14px">3 830 ₽</div>
  </div>
  <ul class="dots" style="margin-top:34px">
   <li>Плата SKR 3 EZ с драйверами — 6 129 ₽, плата на голове EBB42 GEN2 — 2 728 ₽</li>
   <li>Датчик MicroProbe V2 — 1 669 ₽, сопло и щётки для чистки — 959 ₽</li>
   <li>Карбоновая балка X, вентилятор, шестерня экструдера — 3 830 ₽</li>
  </ul>
 </div>
 <div style="position:absolute;left:840px;top:96px;width:312px">
  <div class="big" style="font-size:44px;white-space:normal">[итого] ₽</div>
  <p class="lead">полная стоимость нового принтера на раме Hercules</p>
  <p style="margin-top:26px">Новый закрытый CoreXY-принтер класса Bambu Lab P1S Combo — <b class="o">от 70 000 ₽</b> в рознице РФ</p>
 </div>
</div>"""))

# 9 ─ Why us
why = [
    ("Оригинальность", "Пересобрали принтер 2016 года, оставив только механику: собственная печатная голова Hefest, новая электроника, питание и автоматизация. Контактный датчик по стеклу 4 мм — там, где вихретоковые датчики не работают."),
    ("Реализуемость", "Только серийные компоненты, доступные в России. Архитектура «плата на голове + один кабель» — стандарт Bambu Lab, Prusa и Creality. Токи и нагрев рассчитаны, зазоры головы проверены."),
    ("Коммерциализация", "Пересборка устаревших принтеров на их собственной механике: готовый комплект, установка «под ключ», открытые файлы. Клиенты — школы, вузы, кванториумы, мастерские со списанной техникой."),
    ("Преимущества", "По сравнению с серийным Hercules — 32-битная электроника, хотенд до 300 °C, автокалибровка, Input Shaper, автоочистка сопла и ИИ-контроль. Прочная механика получает вторую жизнь."),
]
why_html = "".join(
    f'<div style="border-top:2px solid var(--line);padding-top:18px"><div style="font-family:Benzin;font-weight:700;font-size:24px;color:var(--teal);margin-bottom:14px">{t}</div><p style="font-size:19px">{s}</p></div>'
    for t, s in why)
slides.append(page(9, f"""<div class="pad">
 <h2>Почему стоит выбрать нас</h2>
 <div style="display:grid;grid-template-columns:1fr 1fr;gap:40px 56px;margin-top:6px">{why_html}</div>
</div>"""))

# 10 ─ Team and materials
qr = segno.make(LINKS["materials"], error="m")
qr_png = BUILD / "qr_materials.png"
qr.save(str(qr_png), scale=12, dark="#101315", light="#ffffff", border=4)
team = "".join(
    f'<div style="display:flex;justify-content:space-between;align-items:baseline;border-bottom:1px solid var(--line);padding:20px 0">'
    f'<span style="font-weight:700;font-size:20px">[Фамилия Имя]</span><span class="t" style="font-weight:600;font-size:17px">{r}</span></div>'
    for r in ["Капитан, электроника", "Конструктор головы", "Klipper и ПО", "3D-модель и печать", "Экономика и документы"])
links = [("Описание проекта (.docx)", "docx"), ("Все материалы заявки", "materials"), 
         ("Печатная голова Hefest", "head"), ("Спецификация и закупки", "spec")]
links_html = "".join(
    f'<a href="{LINKS[k]}" style="display:block;color:var(--text);margin-bottom:16px"><span style="font-weight:700;font-size:19px;border-bottom:2px solid var(--teal-d)">{t}</span>'
    f'<span style="display:block;color:var(--teal);font-size:14.5px;font-weight:600;margin-top:5px;white-space:nowrap">{disp(LINKS[k])}</span></a>'
    for t, k in links)
slides.append(page(10, f"""<div class="pad">
 <h2>Команда и материалы</h2>
 <div style="position:absolute;left:0;top:92px;width:520px">{team}</div>
 <div style="position:absolute;left:570px;top:96px;width:582px">{links_html}
</div>
 <div style="position:absolute;left:570px;bottom:10px;display:flex;align-items:center;gap:22px">
   <a href="{LINKS['materials']}" style="display:block;border-radius:12px;overflow:hidden;width:150px;line-height:0"><img src="{qr_png.as_uri()}" style="width:150px;height:150px;image-rendering:pixelated"></a>
   <p style="font-size:19px;font-weight:600;width:260px">Все материалы заявки — по&nbsp;QR-коду</p>
 </div>
</div>"""))

html = f'<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>Hercules: новый принтер на старой раме</title><style>{CSS}</style></head><body>{"".join(slides)}</body></html>'
html = re.sub(r"(\d) (\d{3})", "\\1\u00a0\\2", html)   # keep numbers like 15 315 ₽ on one line
html = re.sub(r"(\d) ₽", "\\1\u00a0₽", html)
(BUILD / "slides.html").write_text(html, encoding="utf-8")

js = BUILD / "render.js"
js.write_text("""
const { chromium } = require('playwright');
(async () => {
  const [html, pdf, pngDir] = process.argv.slice(2);
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 2 });
  await p.goto('file://' + html); await p.evaluate(() => document.fonts.ready); await p.waitForTimeout(400);
  await p.pdf({ path: pdf, width: '1280px', height: '720px', printBackground: true, preferCSSPageSize: true });
  if (pngDir) {
    const slides = await p.$$('section.slide');
    for (let i = 0; i < slides.length; i++) await slides[i].screenshot({ path: `${pngDir}/slide_${String(i+1).padStart(2,'0')}.png` });
  }
  await b.close();
})();
""")
PNG = BUILD / "png"
PNG.mkdir(exist_ok=True)
subprocess.run(["node", str(js), str(BUILD / "slides.html"), str(SUB / "Hercules_prezentaciya.pdf"), str(PNG)], check=True)
print("done")
