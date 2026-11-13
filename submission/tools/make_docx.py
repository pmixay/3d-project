"""Build the project description for the 3D Profi application.

Requirements: .docx, at most 5 A4 pages, Times New Roman 12 pt.
Run:  python3 submission/tools/make_docx.py
"""
import pathlib

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from links import LINKS

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "Hercules_opisanie_proekta.docx"
FONT = "Times New Roman"

doc = Document()

# ---------- page and base style ----------
for s in doc.sections:
    s.page_height, s.page_width = Cm(29.7), Cm(21.0)
    s.top_margin = s.bottom_margin = Cm(2.0)
    s.left_margin, s.right_margin = Cm(2.5), Cm(1.5)

st = doc.styles["Normal"]
st.font.name = FONT
st.font.size = Pt(12)
rpr = st.element.get_or_add_rPr()
rf = rpr.find(qn("w:rFonts"))
if rf is None:
    rf = OxmlElement("w:rFonts")
    rpr.append(rf)
for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
    rf.set(qn(a), FONT)
pf = st.paragraph_format
pf.space_before = Pt(0)
pf.space_after = Pt(3)
pf.line_spacing = 1.0
pf.first_line_indent = Cm(1.0)
pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

for name in ("List Bullet", "Table Grid"):
    doc.styles[name].font.name = FONT
    doc.styles[name].font.size = Pt(12)


def _font(run, bold=False, italic=False):
    run.font.name = FONT
    run.font.size = Pt(12)
    run.bold = bold
    run.italic = italic
    r = run._element.get_or_add_rPr()
    f = r.find(qn("w:rFonts"))
    if f is None:
        f = OxmlElement("w:rFonts")
        r.append(f)
    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        f.set(qn(a), FONT)
    return run


def para(text="", bold=False, align=None, indent=True, after=3, before=0, keep=False):
    p = doc.add_paragraph()
    if not indent:
        p.paragraph_format.first_line_indent = Cm(0)
    if align is not None:
        p.alignment = align
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.space_before = Pt(before)
    if keep:
        p.paragraph_format.keep_with_next = True
    _rich(p, text, bold)
    return p


def _rich(p, text, bold=False):
    """**bold** fragments inside text."""
    parts = text.split("**")
    for i, chunk in enumerate(parts):
        if chunk:
            _font(p.add_run(chunk), bold=bold or i % 2 == 1)


def h(text):
    return para(text, bold=True, indent=False, before=6, after=3, keep=True)


def bullet(text):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.space_after = Pt(1)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    _rich(p, text)
    return p


def hyperlink(p, url, text):
    rid = p.part.relate_to(url, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink", is_external=True)
    hl = OxmlElement("w:hyperlink")
    hl.set(qn("r:id"), rid)
    r = OxmlElement("w:r")
    rp = OxmlElement("w:rPr")
    fonts = OxmlElement("w:rFonts")
    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        fonts.set(qn(a), FONT)
    rp.append(fonts)
    sz = OxmlElement("w:sz")
    sz.set(qn("w:val"), "24")
    rp.append(sz)
    c = OxmlElement("w:color")
    c.set(qn("w:val"), "1F5FA8")
    rp.append(c)
    u = OxmlElement("w:u")
    u.set(qn("w:val"), "single")
    rp.append(u)
    r.append(rp)
    t = OxmlElement("w:t")
    t.text = text
    t.set(qn("xml:space"), "preserve")
    r.append(t)
    hl.append(r)
    p._p.append(hl)


def table(rows, widths, header=True, bold_last=False, num_col=None):
    t = doc.add_table(rows=len(rows), cols=len(rows[0]))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    for j, w in enumerate(widths):
        t.columns[j].width = Cm(w)
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            cell = t.cell(i, j)
            cell.width = Cm(widths[j])
            p = cell.paragraphs[0]
            p.paragraph_format.first_line_indent = Cm(0)
            p.paragraph_format.space_after = Pt(0)
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT if (j == num_col and i > 0) else WD_ALIGN_PARAGRAPH.LEFT
            _font(p.add_run(val), bold=(header and i == 0) or (bold_last and i == len(rows) - 1))
    doc.add_paragraph().paragraph_format.space_after = Pt(0)
    return t


# ================= CONTENT =================
para("Отраслевой молодёжный чемпионат по аддитивным технологиям «3D Профи»", align=WD_ALIGN_PARAGRAPH.CENTER, indent=False, after=0)
para("МОДЕРНИЗАЦИЯ 3D-ПРИНТЕРА IMPRINTA HERCULES:", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, indent=False, after=0, before=6)
para("скорость, точность и автоматизация уровня современных CoreXY-принтеров в бюджете до 20 000 ₽",
     bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, indent=False, after=6)
para("**Направление:** оборудование для 3D-печати.   **Команда:** [Название команды].   "
     "**Капитан:** [Фамилия Имя], [учебное заведение], [e-mail / телефон].", indent=False, after=6)

h("1. Аннотация")
para("Проект превращает 3D-принтер прошлого поколения Imprinta Hercules в быстрый и автоматизированный "
     "принтер на прошивке Klipper. Жёсткий стальной корпус и линейные направляющие сохраняются, а всё, что "
     "ограничивает скорость и точность, заменяется: 8-битная плата управления — на 32-битную BigTreeTech "
     "SKR 3 EZ, жгут из 12 проводов к печатной голове — на плату EBB42 GEN2 с одним 4-жильным кабелем, "
     "ручная калибровка стола — на контактный датчик BIQU MicroProbe V2 с адаптивной картой высот. "
     "Печатная голова **Hefest** разработана командой с нуля под новую электронику. Бюджет докупаемых "
     "компонентов — 15 315 ₽ (рекомендуемая конфигурация), что примерно в 4,5 раза дешевле нового "
     "закрытого CoreXY-принтера сопоставимого класса.")

h("2. Актуальность и проблема")
para("В школах, вузах, центрах молодёжного творчества и небольших мастерских работает много принтеров "
     "первого поколения. У них, как правило, хорошая механика — металлический корпус, линейные рельсы, "
     "закрытая камера, — но устаревшая электроника. Покупка нового принтера каждые несколько лет обходится "
     "дорого, а исправная механика списывается вместе с платой. У Imprinta Hercules ограничения такие:")
bullet("**Скорость.** 8-битный контроллер ATmega2560 (16 МГц, 8 КБ ОЗУ) под Klipper выдаёт около 99 000 шагов/с. "
       "Экструдеру с редуктором 5:1 на поворотах с Pressure Advance нужно до 141 100 шагов/с только для одного мотора — "
       "контроллер перегружается и печать останавливается ошибкой «Timer too close».")
bullet("**Нет программной настройки драйверов.** На плате MKS Gen v1.4 нет линий UART к драйверам, поэтому ток "
       "и режимы TMC нельзя задавать из прошивки и подбирать автоматически.")
bullet("**Тяжёлый жгут.** К голове идут 12 проводов; добавление датчика и акселерометра увеличило бы жгут до 21 провода. "
       "Жёсткий жгут тянет каретку и искажает измерения резонансов.")
bullet("**Ручная калибровка.** Стол выставляется вручную; нет автоматической чистки сопла, контроля печати и "
       "компенсации резонансов.")

h("3. Цель и задачи")
para("**Цель** — довести точность, скорость и автоматизацию Hercules до уровня современных принтеров "
     "Bambu Lab, сохранив корпус и механику и уложившись в 20 000 ₽ дополнительных закупок. **Задачи:**")
bullet("перевести принтер на Klipper с 32-битной платой и шиной CAN к печатной голове;")
bullet("спроектировать и напечатать собственную печатную голову Hefest под новую электронику;")
bullet("внедрить автокалибровку стола, автоматическую чистку сопла и компенсацию резонансов (Input Shaper);")
bullet("построить цифровую модель принтера для проверки компоновки до изготовления деталей;")
bullet("оформить решение как воспроизводимый комплект: список закупок, конфигурации, печатные детали, инструкции.")

h("4. Техническое решение")
para("**4.1. Электроника.** Плата **BigTreeTech SKR 3 EZ** (STM32H7, 480–550 МГц) обеспечивает более "
     "1 800 000 шагов/с — в 18 раз больше прежнего. Драйверы EZ2209 вставляются в закрытые слоты и "
     "управляются по UART, что позволяет применить klipper_tmc_autotune. Встроенный CAN-трансивер "
     "подключает плату печатной головы без отдельного адаптера. Сохраняются штатный дисплей с энкодером "
     "(разъёмы EXP1/EXP2), блок питания MeanWell LRS-350-24 и плата предохранителей. Хостом Klipper служит "
     "ноутбук, подключённый по USB.")
para("**4.2. Плата на печатной голове.** **BIGTREETECH EBB42 GEN2** (40×45 мм) заменяет сразу шесть элементов: "
     "переходную плату с проводами на термоклее, внешний акселерометр с USB-кабелем, отдельный драйвер "
     "экструдера, 12-проводный жгут, длинные провода датчика и вентиляторов, генерацию шагов экструдера "
     "на основной плате. К голове идёт один кабель: 24 В, GND, CAN_H, CAN_L. Разъём XT30 рассчитан на 15 А "
     "при рабочем токе 2,94 А (пиковый при холодном старте керамического нагревателя — 5,44 А) — запас более "
     "чем в 5 раз. Выходы защищены от короткого замыкания и перегрузки, температура платы контролируется в Klipper.")
para("**4.3. Печатная голова Hefest (собственная разработка).** Голова спроектирована командой в КОМПАС-3D "
     "под каретку MGN12H. Состав: силовая рама с вертикальной плитой экструдера и зажимом ремня, крышка ремня, "
     "треугольная ферма под рельсом X, две полуобоймы хотенда TriangleLab CHC Pro (передняя несёт вентилятор "
     "3010), воздуховод обдува детали от вентилятора 5015 с выходами по обе стороны сопла. На голове "
     "размещаются экструдер K3D Minifeeder с мотором NEMA14 (редуктор 5:1), плата EBB42 GEN2 и датчик "
     "MicroProbe. Для проверки зазоров между деталями головы и ремнями написан собственный скрипт, "
     "проецирующий STL-модели вдоль рельса.")
para("**4.4. Автокалибровка стола.** Стол накрыт стеклом 4 мм на зажимах: оно держит плоскость лучше "
     "тонкой алюминиевой плиты, которая коробится при нагреве до 80–110 °C. Индуктивные и вихретоковые датчики "
     "сквозь 4 мм стекла не работают, поэтому выбран контактный **BIQU MicroProbe V2** (6 г, повторяемость "
     "0,002 мм), который касается поверхности стекла металлическим штоком.")
para("**4.5. Программное обеспечение.** Klipper + Klippain Shake&Tune (натяжение ремней по резонансным пикам, "
     "подбор фильтров Input Shaper по встроенному акселерометру), klipper_tmc_autotune, адаптивная карта стола "
     "KAMP, Adaptive Pressure Advance в OrcaSlicer, камера с ИИ-контролем Crowsnest + Obico (пауза при отрыве "
     "детали или «спагетти»). Макрос START_PRINT: нагрев сопла до 150 °C → чистка о силиконовую щётку → "
     "точное измерение Z-offset → карта высот только в области будущей детали → печать.")

h("5. Цифровой двойник и инженерная проверка")
para("Построена параметрическая модель всего принтера на CadQuery (Python): корпус, рама, направляющие, "
     "ремни, стол, ось Z, отсек электроники. Все размеры собраны в одном файле параметров с пометкой "
     "источника (паспортные, каталожные, оценённые по фото), поэтому модель уточняется по мере обмеров. "
     "Модель экспортирована в STEP, GLB и STL и используется для компоновки головы и платы. "
     "Тепловой и токовый расчёт кабеля к голове (п. 4.2) выполнен заранее: потери в кабеле — менее 0,44 Вт, "
     "нагрев драйвера экструдера — около 0,29 Вт.")

h("6. Бюджет")
table([
    ["Позиция", "Статус", "Стоимость, ₽"],
    ["Плата BTT SKR 3 EZ с драйверами EZ2209", "заказано", "6 129"],
    ["Плата печатной головы BTT EBB42 GEN2 V1.0", "заказано", "2 728"],
    ["Датчик автокалибровки BIQU MicroProbe V2", "заказано", "1 669"],
    ["Сопло TriangleLab Volcano NCB + щётки для чистки сопла", "заказано", "959"],
    ["Подающая шестерня RIDGA V2 для экструдера", "в плане", "650"],
    ["Вентилятор GDSTime 3010 + карбоновая балка X и PETG-CF", "в плане", "3 180"],
    ["Итого (рекомендуемая конфигурация)", "", "15 315"],
], widths=[10.5, 2.7, 3.3], bold_last=True, num_col=2)
para("Уже заказано на 11 485 ₽, остаток до лимита 20 000 ₽ — 4 685 ₽. Резерв (моторы X/Y NEMA17 48 мм, 3 300 ₽) "
     "закладывается только при необходимости, максимум — 18 615 ₽. Для сравнения: новый закрытый "
     "CoreXY-принтер класса Bambu Lab P1S Combo в российской рознице стоит около 70 000 ₽ и выше.")

h("7. Техническая реализуемость и план работ")
para("Все компоненты — серийные и доступные в России; основная электроника заказана и поступает 22–24 ноября 2026 г. "
     "Архитектура «плата на голове + один кабель» — отраслевой стандарт (Bambu Lab X1/P1/A1, Prusa XL, Creality K1/K2). "
     "Подход проверен расчётами и цифровой моделью ещё до сборки.")
table([
    ["Срок", "Этап"],
    ["до 22 ноября", "Печать деталей головы Hefest, переходная пластина под EBB42 GEN2, подготовка конфигурации Klipper"],
    ["22–26 ноября", "Монтаж SKR 3 EZ и EBB42 GEN2, прокладка CAN-кабеля, прошивка, первый запуск"],
    ["27–30 ноября", "Калибровка: Shake&Tune, Input Shaper, TMC autotune, Pressure Advance, карта стола"],
    ["1–2 декабря", "Тестовые печати, замеры скорости и точности, видеозапись"],
    ["3 и 5 декабря", "Демонстрация на соревновательных днях"],
], widths=[3.2, 13.3])

h("8. Оригинальность и преимущества")
bullet("**Собственная печатная голова Hefest**, спроектированная под конкретную связку CHC Pro + K3D Minifeeder + EBB42 GEN2 + MicroProbe.")
bullet("**Нестандартное решение для стекла:** контактный датчик вместо популярных вихретоковых, которые через 4 мм стекла не работают.")
bullet("**Инженерный подход:** параметрическая модель принтера, расчёт токов и тепла, скрипт проверки зазоров — до покупки и изготовления.")
bullet("**Сохранение ресурса:** корпус, рельсы, хотенд, блок питания, ремни и стекло остаются в работе; заменяется только то, что ограничивает характеристики.")
bullet("**Функции флагманов:** компенсация резонансов, автокалибровка, автоматическая чистка сопла, ИИ-контроль печати — на принтере прошлого поколения.")

h("9. Потенциал коммерциализации")
para("Продукт — **набор модернизации** для принтеров прошлого поколения с жёсткой механикой (Hercules и аналоги) "
     "стоимостью 12–20 тыс. ₽ вместо покупки нового принтера за 70 тыс. ₽ и выше. Целевые клиенты: школы, "
     "вузы, технопарки, ЦМИТ, кванториумы, небольшие мастерские и частные владельцы. Модели монетизации:")
bullet("готовый комплект: электроника, печатные детали головы, кабели и преднастроенная конфигурация Klipper;")
bullet("услуга модернизации «под ключ» с настройкой и обучением;")
bullet("открытая документация и файлы для самостоятельной сборки как канал привлечения клиентов.")
para("Масштабирование — адаптация головы и конфигураций под другие популярные модели принтеров прошлого поколения.")

h("10. Команда")
table([
    ["Участник", "Роль в проекте"],
    ["[Фамилия Имя Отчество], [учебное заведение]", "Капитан, архитектура и электроника"],
    ["[Фамилия Имя Отчество], [учебное заведение]", "Конструктор печатной головы (КОМПАС-3D)"],
    ["[Фамилия Имя Отчество], [учебное заведение]", "Программное обеспечение, Klipper"],
    ["[Фамилия Имя Отчество], [учебное заведение]", "3D-моделирование и печать деталей"],
    ["[Фамилия Имя Отчество], [учебное заведение]", "Экономика, презентация, документация"],
], widths=[9.0, 7.5])

h("11. Материалы проекта")
for label, key in [
    ("Все материалы заявки: ", "materials"),
    ("Репозиторий проекта: ", "repo"),
    ("Цифровая модель принтера (STEP, GLB, STL, рендеры): ", "model"),
    ("Печатная голова Hefest — описание и проверка: ", "head"),
    ("Спецификация и список закупок: ", "spec"),
]:
    p = para(label, indent=False, after=1, align=WD_ALIGN_PARAGRAPH.LEFT)
    hyperlink(p, LINKS[key], LINKS[key].replace("https://", ""))

doc.save(OUT)
print("saved", OUT)
