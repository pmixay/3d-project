# Для команды: правка и пересборка материалов заявки

## Что осталось сделать

- **Камера** ещё не куплена: после покупки поменять статус в [таблице комплектующих](../../Hefest_komplektuyushchie.xlsx); если цена отличится от 1 600 ₽, обновить итоги на слайде 7 и в разделе 6 описания.
- **Тон материалов на Диске:** описывать сделанное, без открытых вопросов и ссылок на GitHub; открытые пункты ведутся только в README репозитория.
- **Ссылки и QR-код** (слайды 5 и 9, раздел 11 описания) ведут на папку с материалами на Google Диске (`links.py`). После каждой пересборки заново загрузить в папку PDF презентации и описание.

## Стенд

Стенд - один баннер 1600 × 1000 мм: створки по 40 см, центр 80 см, сгибы на 400 и 1200 мм. Исходник - `../stand/stand.html` (все размеры в миллиметрах), картинки - в `../stand/img/`. Фото в блоках «Фото» - файлы `photo_1.jpg` и `photo_2.jpg`: заменить на актуальные и пересобрать. Скрипт сообщает, если текст не помещается в блок. На превью сгибы показаны пунктиром, в печатном PDF их нет.

## Как пересобрать

`Hefest_golova_poyasnitelnaya_zapiska.pdf` - это `head/README.md` без последнего раздела «Файлы», переведённый в PDF (pandoc → HTML → печать в Chromium) скриптом `make_head_pdf.mjs`.

**Оформление текста:** в материалах заявки не используются длинное и среднее тире (только обычный дефис «-») и маркеры списков в виде точек: списки в описании нумерованные.

Презентация правится вручную в PowerPoint; нужны шрифты Benzin и Montserrat из папки `fonts/`. После правок пересохранить PDF.

```bash
cd submission/tools
python3 make_docx.py      # описание проекта .docx
node make_head_pdf.mjs    # пояснительная записка к голове .pdf (нужны pandoc и playwright)
node make_stand.mjs       # стенд: ../Hefest_stend.pdf (баннер 1600 x 1000 мм) и ../stand/preview.png из ../stand/stand.html
python3 cutout_bg.py in.jpg out.png preview.png   # убрать серый фон со скриншота из САПР
soffice --headless --convert-to pdf --outdir .. ../Hefest_prezentaciya.pptx   # PDF из презентации; шрифты из fonts/ должны быть установлены
# рендеры головы: node render_head.mjs <голова.glb> head_views.json ../materials/img   (голова.glb: python3 ../../model/tools/head_glb.py <parts_dir> голова.glb --by-part --board=<официальная CAD-модель EBB42 GEN2>)
# схема крепления крышки: голова.glb с ключом --exploded, вид hefest_head_cover_mount, затем python3 head_cover_mount.py <рендер.png> ../materials/img/hefest_head_cover_mount.png
# рендеры: node render_model.mjs ../../model/out/hefest_printer.glb <папка> front_iso right_iso gantry_close (нужен three@0.160.0)
```
