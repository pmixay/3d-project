# Imprinta Hercules — components seen in the photos and their model parts

The model in this folder is built by `printer.py` from the dimensions in `params.py`.
Only the outer size (365 × 355 × 430 mm) and the build volume (200 × 200 × 210 mm) are published
figures; **every other dimension is an estimate read off the photos** and is marked `[EST]` in `params.py`.
The model is good for layout and for discussing the head, not yet for cutting parts.

Photos referred to below:

| Ref | Photo |
| :--- | :--- |
| P1 | Whole printer, three-quarter view from the front-right |
| P2 | Whole printer, straight from the front |
| P3 | Electronics tray seen from underneath |
| P4 | Toolhead close-up, accelerometer side, harness in the foreground |
| P5 | Toolhead close-up, green breakout board and its connectors |
| P6 | Toolhead close-up from below/behind (green board edge-on, accelerometer on its arm) |

Confidence: **clear** = plainly visible; **partial** = visible but size/position guessed; **inferred** = not directly visible, placed by reasoning.

## Enclosure and front panel

| Component | Seen in | Model part | Confidence / notes |
| :--- | :--- | :--- | :--- |
| Teal sheet-steel enclosure with chamfered vertical corners, open top | P1, P2 | `enclosure_shell` | Clear. Outer size from the published spec; pillar widths, chamfer and opening sizes estimated. Rear wall was not photographed — modelled plain. Bottom cover not modelled (tray is open, as in P3). |
| Chamber floor (top of the electronics base) | P2 | `chamber_floor` | Clear. Height of the base (72 mm) estimated. |
| Clear side panels with a diagonal upper-front corner | P1 | `side_window_left`, `side_window_right` | Right panel clear; left assumed identical. |
| 20×4 character LCD | P2, P3 | `lcd_screen`, `lcd_controller_board` | Clear. Board size is the standard 2004 smart-controller PCB. |
| Aluminium encoder knob | P1, P2 | `encoder_knob` | Clear. |
| Small toggle switch left of the LCD | P1, P2 | `front_toggle_switch` | Partial — function unknown. |

## Top frame, gantry and motion

| Component | Seen in | Model part | Confidence / notes |
| :--- | :--- | :--- | :--- |
| Black top frame plate carrying the rails | P1, P2 | `top_frame_plate` | Partial — shape of the central opening estimated. |
| Y linear rails, one per side | P1, P2, P4 | `y_rail_left`, `y_rail_right` | Clear. Size assumed MGN12, length 300 mm. |
| Y carriage blocks with red end seals | P1, P2 | `y_carriage_*`, `y_carriage_*_end_seals` | Clear. Assumed MGN12H. |
| X-end aluminium plates (an upper and a lower plate each side) | P1, P2, P6 | `x_end_plate_*_lower`, `x_end_plate_*_upper` | Clear that they are double plates; outline simplified to a rounded rectangle. |
| Idler pulleys between the X-end plates (two per side) | P2, P6 | `x_end_idlers_left`, `x_end_idlers_right` | Partial — count clear, positions estimated. |
| X linear rail used as the X beam (unsupported between the plates) | P1, P2, P4, P5 | `x_rail` | Clear. Mounting holes face up; carriage assumed on top. |
| X carriage block with red end seals | P1, P4 | `x_carriage`, `x_carriage_end_seals` | Partial — mostly hidden by the head. |
| GT2 belts (white) | P1, P2, P4, P5 | `belts_gt2` | Clear that one run passes each side of the X rail and that belts run along both Y sides. Exact path, heights and offsets estimated. |
| Front corner idlers on white printed brackets | P1, P2 | `front_corner_idler_*`, `front_idler_bracket_*` | Partial. |
| X/Y stepper motors at the rear corners | P2 (right rear, dark block) | `xy_motor_*`, `xy_motor_pulley_*` | Inferred — bodies assumed NEMA17 hanging under the top plate. |
| Endstop microswitch at the rear of the right rail | P2 | `y_endstop_switch` | Partial. No X endstop could be identified. |

**Kinematics could not be determined from the photos.** The project document calls the machine CoreXY.
What the photos show is two belt runs flanking the X rail in one plane and two idlers on each X-end,
which also fits an H-bot layout. The model draws the belts as a single-plane loop
(front corner idler → X-end → across → X-end → motor, each side) purely to show where belts occupy space.

## Bed and Z axis

| Component | Seen in | Model part | Confidence / notes |
| :--- | :--- | :--- | :--- |
| Bed plate (dark, heated) | P1, P2 | `bed_heater_plate` | Clear. Size estimated at 220 × 215 mm. |
| 4 mm glass on the bed | — | `bed_glass` | From the project document. The photos show a dark matte surface; glass cannot be confirmed. |
| Two metal clips on the front edge | P1, P2 | `bed_clips` | Clear. |
| Screw in the centre front of the bed | P2 | `bed_centre_screw` | Clear. |
| Black knob under the front of the bed | P2 | `bed_levelling_knob` | Partial — assumed to be a levelling knob. |
| Cantilever bed support | P1 (through left opening) | `bed_support_arms` | Inferred shape. |
| Two polished Z rods and a lead screw at the rear centre | P1, P2 | `z_rods`, `z_lead_screw`, `z_coupler` | Rods clear; screw partial. Diameters and spacing estimated. |
| Z carriage with the teal "HERCULES" cover | P1, P2 | `z_carriage`, `z_carriage_cover_hercules` | Cover clear; carriage inside inferred. |
| Z stepper motor (protrudes into the tray at the rear centre) | P3 | `z_motor` | Clear. |

## Toolhead (currently fitted) — placeholder only in this model

All of these are covered by the single envelope part `toolhead_placeholder`; the head itself is modelled separately.

| Component | Seen in | Confidence / notes |
| :--- | :--- | :--- |
| Printed extruder body (K3D Minifeeder per the project document), black | P1, P2, P4, P6 | Clear. |
| Round pancake stepper on the extruder (NEMA14 per the document) | P4, P5, P6 | Clear. |
| Extruder tension screw with spring | P2 | Clear. |
| Blue push-fit collet at the filament inlet | P2, P4, P6 | Clear. |
| Hotend with heatsink, orange silicone sock on the heater block (CHC Pro per the document) | P1 | Partial — mostly hidden by the fan and duct. |
| Hotend heatsink fan, axial, on the front | P2, P6 | Clear (3010 per the document). |
| Part-cooling blower (5015 per the document) and printed duct | P1, P5 | Partial. |
| Green breakout PCB with white JST connectors, standing vertically at the rear of the head | P2, P4, P5, P6 | Clear. |
| Accelerometer board with USB-C on a printed arm (BTT ADXL345 S2DW per the document) | P2, P4, P5, P6 | Clear. |
| Braided cable harness looping above the printer to the rear-right corner | P1, P2, P4 | Clear — modelled as `toolhead_cable_harness`. Route approximate. |
| Clip/ring gathering the harness at the top of the loop | P1, P2 | Clear — not modelled. |

## Electronics tray (underside)

| Component | Seen in | Model part | Confidence / notes |
| :--- | :--- | :--- | :--- |
| Black mounting plate | P3 | `tray_mounting_plate` | Clear. |
| MKS Gen V1.4 mainboard with five stepper drivers | P3 | `mks_gen_v1_4_board`, `mks_stepper_drivers`, `mks_gen_v1_4_connectors`, `mks_gen_v1_4_standoffs` | Clear (name printed on the board). On-board details schematic. |
| Green fuse / distribution board with six fuses and screw terminals | P3 | `fuse_board`, `fuse_board_fuses_and_terminals`, `fuse_board_standoffs` | Clear. Size estimated. |
| IEC mains inlet | P3 (rear-left corner) | `iec_power_inlet` | Partial. |
| Round metal panel connector on the rear wall | P3 | `rear_round_connector` | Partial — not identified (fuse holder or DC socket). |
| LCD controller board and two flat EXP ribbon cables (foil-wrapped) | P3 | `lcd_controller_board`, `exp_ribbon_cables` | Clear; routing simplified. In P3 the front panel is swung open; the model shows it closed. |
| USB lead from the mainboard | P3 | `usb_lead` | Partial — routing approximate. |
| Loose RJ45 lead | P3 | `rj45_lead` | Partial. |
| Four loose leads with fork terminals (red, black, blue, brown) | P3 | `psu_lead_red`, `psu_lead_black`, `psu_lead_blue`, `psu_lead_brown` | Clear. They are where a power supply would connect. |
| Unused brass standoffs on the plate | P3 | `spare_brass_standoffs` | Clear that they exist; pattern estimated. |
| Power supply | not in the photos | `psu_lrs_350_24_planned` | **Not fitted in P3.** Shown translucent at catalogue size (LRS-350-24 from the project document) where the loose leads end. Set `INCLUDE_PLANNED_PSU = False` in `printer.py` to drop it. |
| Wiring looms, cable-tie mounts | P3 | — | Not modelled. |

## Measurements needed to replace the estimates

Head-critical (these decide whether a head clears the belts):

1. X rail: width and height (confirms MGN12), and whether the carriage rides on top of the rail or under it.
2. X carriage block: length, width, mounting-hole pattern, and height of its mounting face above the rail.
3. Belts along X: distance from the rail centre line to the front run and to the back run; height of the belt's lower and upper edges relative to the top of the rail; belt width.
4. Which belt run(s) attach to the head, and where — this also settles CoreXY vs H-bot.
5. X-end plates: inner edge to inner edge distance, and the height of the upper plate above the rail (the head must pass under or stop short of it).
6. Vertical distance from the top of the X rail to the nozzle tip on the current head, and the nozzle's front/back offset from the rail centre.
7. Height of the enclosure rim and of the black top plate relative to the X rail; size of the opening in the top plate.

General:

8. Y rail centre distance, rail length, and usable X/Y travel end to end.
9. Bed plate size, its position relative to the front wall, and the top-of-bed height at Z = 0 and at full travel.
10. Z rod diameter and spacing, lead screw diameter.
11. Base (electronics tray) height, front opening and side window sizes.
12. Mounting-hole positions on the tray plate for the mainboard and the spare standoffs (needed to place the SKR 3 EZ).

## Re-running

```bash
pip install cadquery
```

```bash
python model/printer.py
```

Outputs go to `model/out/`: `hercules_printer.step`, `hercules_printer.glb`, `hercules_printer.stl`.
The preview images in `model/out/renders/` are made with `model/tools/render.mjs` (see the comment at the top of that file).
