# Заявка на чемпионат «3D Профи» — Hefest: новый принтер на базе старого

Направление: **оборудование для 3D-печати**. Команда: **[Название команды]**.

## Основные документы

| Файл | Что это |
| :--- | :--- |
| [Hefest_prezentaciya.pptx](Hefest_prezentaciya.pptx) | Презентация проекта (9 слайдов) — **рабочая версия**, правится вручную в PowerPoint (нужны шрифты Benzin и Montserrat) |
| [Hefest_prezentaciya.pdf](Hefest_prezentaciya.pdf) | Экспорт текущей версии презентации в PDF (9 слайдов); после правок в PowerPoint пересохранить |
| [Hefest_opisanie_proekta.docx](Hefest_opisanie_proekta.docx) | Краткое текстовое описание проекта (до 5 страниц, Times New Roman 12 пт) |

## Что осталось сделать в презентации

- **Слайд 7 «Стоимость»** — суммы этапов и итог оценочные (со знаком ≈): в этапе 1 — пять цен, в этапе 2 — камера, которую предстоит купить: вписать фактические цены покупки в жёлтые ячейки [таблицы комплектующих](../Hefest_komplektuyushchie.xlsx) и обновить числа на слайде.
- **Слайд 5 «Печатная голова»** — заменить картинку на новый рендер головы с компонентами.
- **Слайд 9 «Команда»** — каждый участник пишет свою роль; добавить фото.
- **Ссылки и QR-код на слайде 9** ведут на ветку `main` и заработают после слияния рабочей ветки в `main`.

## Вспомогательные материалы

**Схемы и графики** (экспорт слайдов текущей презентации)

- [Актуальность и необходимость](materials/slides/relevance.png)
- [Сравнение с серийным Hercules H18](materials/slides/baseline.png)
- [Что осталось от Hercules и что сделано заново](materials/slides/rebuild.png)
- [Автоматизация и калибровка на Klipper](materials/slides/automation.png)
- [Стоимость пересборки](materials/slides/budget.png)

**Печатная голова Hefest (собственная разработка команды)**

- [Печатные детали — вид спереди](materials/img/hefest_parts_front.png) и [вид сзади](materials/img/hefest_parts_rear.png)
- [Описание конструкции и проверка зазоров до ремней](../head/README.md)

**Рендеры принтера** (без жгута проводов)

- [Вид спереди](materials/img/printer_front.png), [вид справа](materials/img/printer_right.png), [портал X/Y крупно](materials/img/gantry_close.png)

**Спецификация и закупки**

- [Технический план и обоснование решений](../README.md)
- [Единая таблица комплектующих с ценами и итогами по этапам (xlsx)](../Hefest_komplektuyushchie.xlsx)

**Фото и видео** — будут добавлены по мере сборки.

## Как пересобрать

```bash
cd submission/tools
python3 make_docx.py      # описание .docx
soffice --headless --convert-to pdf --outdir .. ../Hefest_prezentaciya.pptx   # PDF из презентации; шрифты из tools/fonts/ должны быть установлены
# рендеры: node render_model.mjs ../../model/out/hefest_printer.glb <папка> front_iso right_iso gantry_close (нужен three@0.160.0)
```

Шрифты Benzin и Montserrat лежат в `tools/fonts/`. Презентация правится вручную в PowerPoint; старые скрипты сборки слайдов удалены.
