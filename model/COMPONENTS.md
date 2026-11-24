# Imprinta Hercules — components seen in the photos and their model parts

The model in this folder is built by `printer.py` from the dimensions in `params.py`.
Only the outer size (365 × 355 × 430 mm) and the build volume (200 × 200 × 210 mm) are published
figures; **every other dimension is read off the photos**. Values marked `[FIT]` in `params.py` were measured on P2
with a camera fitted to the enclosure corners and checked by overlaying the model on P1 and P2 (good to about
±5–10 mm); values marked `[EST]` are plain estimates. The model is good for layout and renders, not for cutting parts.

The GLB also carries the **Hefest print head** on the X carriage (`model/parts/hefest_head.glb`, see below);
the STEP and STL hold the printer without the head.

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
| Teal sheet-steel enclosure with chamfered vertical corners, open top | P1, P2 | `enclosure_shell` | Clear. Outer size from the published spec. The crossbar above the front opening is about 32 mm high and flush with the rim. Rear wall was not photographed — modelled plain. Bottom cover not modelled (tray is open, as in P3). |
| Chamber floor (top of the electronics base) | P1, P2 | `chamber_floor` | Clear. The base is about 120 mm high (measured on P2). |
| Clear side panels with a diagonal upper-front corner | P1 | `side_window_left`, `side_window_right` | Right panel clear; left assumed identical. The opening starts about 90 mm behind the front face and reaches below the chamber floor. |
| 20×4 character LCD | P2, P3 | `lcd_screen`, `lcd_controller_board` | Clear. Window position measured on P2; board size is the standard 2004 smart-controller PCB. |
| Aluminium encoder knob | P1, P2 | `encoder_knob` | Clear. About 30 mm in diameter. |
| Small toggle switch left of the LCD | P1, P2 | `front_toggle_switch` | Partial — function unknown. |

## Top frame, gantry and motion

| Component | Seen in | Model part | Confidence / notes |
| :--- | :--- | :--- | :--- |
| Black top frame plate carrying the rails | P1, P2 | `top_frame_plate` | Partial. Open at the front; only a narrow strip is left at the rear, where the Z rods end. |
| Y linear rails, one per side | P1, P2, P4 | `y_rail_left`, `y_rail_right` | Clear. Size assumed MGN12, length 300 mm. |
| Y carriage blocks with red end seals | P1, P2 | `y_carriage_*`, `y_carriage_*_end_seals` | Clear. Assumed MGN12H. |
| Black stop blocks at the front ends of the Y rails | P2 | `y_rail_stop_*` | Partial — size estimated. |
| X-end aluminium plates (an upper and a lower plate each side) | P1, P2, P6 | `x_end_plate_*_lower`, `x_end_plate_*_upper`, `x_end_plate_*_screws` | Clear that they are double plates; outer corners chamfered, six screws on top. Width (60 mm) measured on P2. |
| Idler pulleys between the X-end plates (two per side) | P2, P6 | `x_end_idlers_left`, `x_end_idlers_right` | Partial — count clear; placed where the belt runs turn. |
| X linear rail used as the X beam (unsupported between the plates) | P1, P2, P4, P5 | `x_rail` | Clear. Mounting holes face up; carriage assumed on top. |
| X carriage block with red end seals | P1, P4 | `x_carriage`, `x_carriage_end_seals` | Partial — mostly hidden by the head. |
| GT2 belts, 6 mm, white | P1, P2, P4, P5 | `belts_gt2`, `belts_gt2_teeth` (GLB only) | Clear. Along X one run passes close in front of the rail (14.9 mm from its centre line) and one close behind it (18.5 mm), as the Hefest head expects; their top edge is level with the top of the rail. Along Y two runs per side, inboard of the rail (45 and 57 mm from the side, measured on P2). |
| Front corner idlers on white printed blocks | P1, P2 | `front_corner_idler_*`, `front_idler_block_*` | Partial. |
| X/Y stepper motors at the rear corners | P2 (right rear, dark block) | `xy_motor_*`, `xy_motor_pulley_*` | Inferred — bodies assumed NEMA17 hanging under the top plate. |
| Endstop microswitch at the rear of the right rail | P2 | `y_endstop_switch` | Partial. No X endstop could be identified. |

The project document calls the machine CoreXY. The photos show two belt runs flanking the X rail in one plane
and two idlers on each X-end; the rear run is clamped in the head and the front run passes freely through it.
The model draws each run as a straight belt between its pulleys, in one plane, to show where the belts are.

## Bed and Z axis

| Component | Seen in | Model part | Confidence / notes |
| :--- | :--- | :--- | :--- |
| Bed plate (dark, heated) | P1, P2 | `bed_heater_plate` | Clear. Size estimated at 220 × 215 mm. |
| 4 mm glass on the bed | — | `bed_glass` | From the project document. The photos show a dark matte surface; glass cannot be confirmed. |
| Two metal clips on the front edge | P1, P2 | `bed_clips` | Clear. |
| Screw in the centre front of the bed | P2 | `bed_centre_screw` | Clear. |
| Black knob under the front of the bed | P2 | `bed_levelling_knob` | Partial — assumed to be a levelling knob. |
| Cantilever bed support | P1 (through left opening) | `bed_support_arms` | Inferred shape. |
| Two polished Z rods and a lead screw at the rear centre | P1, P2 | `z_rods`, `z_lead_screw`, `z_coupler` | Rods clear; screw partial. Rods about 110 mm apart with the lead screw between them (measured on P2). |
| Z carriage with the teal "HERCULES" cover | P1, P2 | `z_carriage`, `z_carriage_cover_hercules` | Cover clear, about 160 mm wide, its bottom at bed level; carriage inside inferred. |
| Z stepper motor (protrudes into the tray at the rear centre) | P3 | `z_motor` | Clear. |

## Print head — the Hefest head (in the GLB)

The photos still show the previous head (green breakout board standing at the rear, S2DW accelerometer on a
printed arm, braided harness looping above the printer). The model shows the new **Hefest** head instead:
`model/parts/hefest_head.glb`, built by `tools/head_glb.py` from the team's assembly with the v3 parts
(`head/v3/`: frame, front hotend mount with the MicroProbe seat, front cover) and placed on the X carriage when `printer.py` writes the GLB.

| Component | Model part | Notes |
| :--- | :--- | :--- |
| Frame v3 (EBB42 GEN2 on the side wall), belt cover, triangle, hotend mounts, duct | `head_frame_v3`, `head_belt_cover`, `head_triangle`, `head_hotend_mount_*`, `head_duct` | From the team's CAD; printed parts shown in dark grey. |
| TriangleLab CHC Pro with Volcano nozzle | `head_chc_*`, `head_nozzle_volcano` | Nozzle tip 38.4 mm in front of the X-rail centre line, 69.8 mm below the head origin. |
| K3D Minifeeder, NEMA14 pancake motor | `head_minifeeder`, `head_nema14` | |
| 3010 hotend fan, 5015 part-cooling blower | `head_fans` | |
| BIGTREETECH EBB42 GEN2 V1.0 | `head_ebb42_gen2_*` | The board from the team's assembly; on the left side wall of the head, XT30 up. |
| BIQU MicroProbe V2 | `head_microprobe` | Official mockup, pin extended; under the front hotend mount, shown in orange. |
| Front cover with the printer name | `head_cover` | Over the hotend fan. |
| Single 24 V + CAN cable from the XT30 to the rear-right corner | `toolhead_cable_can` | Route approximate. Hidden in the presentation renders. |

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

Head-critical:

1. X rail: width and height (confirms MGN12).
2. X carriage block: length, width, mounting-hole pattern, and height of its mounting face above the rail.
3. X-end plates: inner edge to inner edge distance, and the height of the upper plate above the rail (the head must pass under or stop short of it).
4. Height of the enclosure rim and of the black top plate relative to the X rail; size of the opening in the top plate.
5. Space beside the head on the board side at the end of X travel (the EBB42 GEN2 sits on the side wall).

General:

6. Y rail centre distance, rail length, and usable X/Y travel end to end.
7. Bed plate size, its position relative to the front wall, and the top-of-bed height at Z = 0 and at full travel.
8. Z rod diameter and spacing, lead screw diameter.
9. Base (electronics tray) height, front opening and side window sizes.
10. Mounting-hole positions on the tray plate for the mainboard and the spare standoffs (needed to place the SKR 3 EZ).

## Re-running

```bash
pip install cadquery
```

```bash
python model/printer.py
```

Outputs go to `model/out/`: `hefest_printer.step`, `hefest_printer.glb` (with the Hefest head and the belt teeth), `hefest_printer.stl`.
To rebuild the head mesh from the team's assembly (split into `.brep` files by assembly node):
`python model/tools/head_glb.py <parts_dir> model/parts/hefest_head.glb` (`<parts_dir>` is the team's assembly STEP split by `model/tools/split_assy.py`).
The preview images in `model/out/renders/` are made with `model/tools/render.mjs` (see the comment at the top of that file).
