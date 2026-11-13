# Заявка на чемпионат «3D Профи» — Imprinta Hercules: новый принтер на старой раме

Направление: **оборудование для 3D-печати**. Команда: **[Название команды]**.

## Основные документы

| Файл | Что это |
| :--- | :--- |
| [Hercules_prezentaciya.pdf](Hercules_prezentaciya.pdf) | Презентация проекта (10 слайдов) |
| [Hercules_prezentaciya.pptx](Hercules_prezentaciya.pptx) | Та же презентация в PowerPoint, текст редактируется (нужны шрифты Benzin и Montserrat) |
| [Hercules_opisanie_proekta.docx](Hercules_opisanie_proekta.docx) | Краткое текстовое описание проекта (до 5 страниц, Times New Roman 12 пт) |

## Вспомогательные материалы

**Схемы и графики**

- [Актуальность и необходимость](materials/slides/relevance.png)
- [Архитектура электроники: один кабель к печатной голове](materials/slides/architecture.png)
- [Сравнение с серийным Hercules 2016](materials/slides/baseline.png)
- [Что осталось от Hercules и что сделано заново](materials/slides/rebuild.png)
- [Стоимость пересборки](materials/slides/budget.png)

**Печатная голова Hefest (собственная разработка команды)**

- [Печатные детали — вид спереди](materials/img/hefest_parts_front.png) и [вид сзади](materials/img/hefest_parts_rear.png)
- [Описание конструкции и проверка зазоров до ремней](../head/README.md)

**Рендеры принтера**

- [Вид спереди](materials/img/printer_front.png), [вид справа](materials/img/printer_right.png), [портал X/Y крупно](materials/img/gantry_close.png)

**Спецификация и закупки**

- [Технический план и обоснование решений](../README.md)
- [Список закупок v7 с формулами (xlsx)](../3D_Printer_Upgrade_Components-v7.xlsx)

**Фото и видео** — будут добавлены по мере сборки.

## Как пересобрать

```bash
cd submission/tools
python3 make_docx.py      # описание .docx
python3 make_slides.py    # презентация .pdf; шрифты Benzin и Montserrat положить в tools/fonts/
python3 make_pptx.py      # та же презентация в .pptx (после make_slides.py)
# рендеры: node render_model.mjs ../../model/out/hercules_printer.glb <папка> front_iso right_iso gantry_close (нужен three@0.160.0)
```
