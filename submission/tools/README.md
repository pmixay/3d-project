# Для команды: правка и пересборка материалов заявки

## Что осталось сделать

- **Камера** ещё не куплена: после покупки поменять статус в [таблице комплектующих](../../Hefest_komplektuyushchie.xlsx); если цена отличится от 1 600 ₽, обновить итоги на слайде 7 и в разделе 6 описания.
- **Папка «Рендеры» на Google Диске** - кроме рендеров принтера, положить туда рендеры головы `materials/img/hefest_head_board.png` и `materials/img/hefest_head_extruder.png`.
- **Ссылки и QR-код** (слайды 5 и 9, раздел 11 описания) ведут на папку с материалами на Google Диске (`links.py`). После каждой пересборки заново загрузить в папку PDF презентации и описание.

## Как пересобрать

`Hefest_golova_poyasnitelnaya_zapiska.pdf` - это `head/README.md` без раздела «Файлы», переведённый в PDF (pandoc → HTML → печать в Chromium) скриптом `make_head_pdf.mjs`.

**Оформление текста:** в материалах заявки не используются длинное и среднее тире (только обычный дефис «-») и маркеры списков в виде точек: списки в описании нумерованные.

Презентация правится вручную в PowerPoint; нужны шрифты Benzin и Montserrat из папки `fonts/`. После правок пересохранить PDF.

```bash
cd submission/tools
python3 make_docx.py      # описание проекта .docx
node make_head_pdf.mjs    # пояснительная записка к голове .pdf (нужны pandoc и playwright)
python3 cutout_bg.py in.jpg out.png preview.png   # убрать серый фон со скриншота из САПР (рендеры головы на слайде 5)
soffice --headless --convert-to pdf --outdir .. ../Hefest_prezentaciya.pptx   # PDF из презентации; шрифты из fonts/ должны быть установлены
# рендеры: node render_model.mjs ../../model/out/hefest_printer.glb <папка> front_iso right_iso gantry_close (нужен three@0.160.0)
```
