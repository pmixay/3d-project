# Hefest — a new 3D printer on the frame of an Imprinta Hercules H18

Technical plan for the Hefest project: an Imprinta Hercules H18 (2018) rebuilt with new electronics, a new print head and Klipper firmware.

- **Base platform:** Imprinta Hercules H18 (2018) — rigid steel enclosure, linear rails on X and Y, cantilevered bed on Z.
- **Firmware and control:** Klipper, with the host running on a BigTreeTech BTT Pi v1.2 single-board computer. The printer was moved from Marlin to Klipper.
- **Goal:** bring print accuracy, speed and automation close to the level of Bambu Lab printers.
- **New electronics:** BigTreeTech SKR 3 EZ mainboard (bought as a kit with 5 EZ2209 drivers) + BIGTREETECH EBB42 GEN2 V1.0 toolhead board.

## Cost of the rebuild

All components, prices and order numbers are in one spreadsheet, [`Hefest_komplektuyushchie.xlsx`](Hefest_komplektuyushchie.xlsx) (in Russian). It replaces every component table that used to be in this repository.

| Stage | What it covers | Total |
| :--- | :--- | ---: |
| Stage 1 | Hotend, extruder, power supply, part cooling, lighting | ≈ 8 600 ₽ |
| Stage 2 | Mainboard with 5 drivers, toolhead board, bed probe, nozzle, nozzle cleaning, hotend fan, camera | ≈ 14 100 ₽ |
| **Total** | | **≈ 22 700 ₽** |

- **Stage 2:** 11 865 ₽ is what was actually paid (five orders of November 10, 2026, delivery November 22–24, plus the hotend fan). The camera is still to be bought; its price (about 2 200 ₽) is an estimate from AliExpress listings.
- **Stage 1** purchase prices were not recorded. The power supply uses a retail price found on November 14, 2026; the other five prices are estimates, marked yellow in the spreadsheet, to be replaced with the real purchase prices.
- The BTT Pi board and the new belts are listed in the spreadsheet but not counted in the totals until it is confirmed they were bought for the project.

## Team

| Member | Role |
| :--- | :--- |
| Еремей | Programmer and electronics: moved the mainboard and the BTT Pi v1.2 host from Marlin to Klipper, did the wiring on the board and found the pins for the connections, including the drivers. |
| Андрей | Mechanic: the mechanical side — frame and axes, belt replacement, design and assembly of the Hefest print head, fitting the new units. |
| Паша | AI print monitoring: the camera system that recognises print defects with machine learning. |
| Илья | Components and documentation: selecting and buying components, cost calculation, 3D-printing the parts, the project description and the presentation. |

## Repository contents

| File | What it is |
| :--- | :--- |
| `Hefest_komplektuyushchie.xlsx` | The single list of components with prices, status and order numbers, split into two stages, with totals (in Russian). |
| `Hefest_Spec_and_Plan-v3.docx` | Upgrade plan (v3): architecture of the new boards and notes from photos of the build. |
| `model/` | Parametric CadQuery model of the whole printer (`printer.py`, dimensions in `params.py`), exported to STEP / GLB / STL in `model/out/`, with renders and the list of components seen on the machine (`COMPONENTS.md`). Only the outer size and build volume are published figures; the rest is estimated from photos. |
| `head/` | Review of the Hefest print head design, including a belt-clearance check and a frame proposal. |
| `submission/` | Application for the "3D Profi" championship: presentation and project description (in Russian). |

---

## 1. What is kept and what is new

**Kept from the Hercules H18:** steel frame, X and Y rails, Z axis, bed with its 4 mm borosilicate glass on clips, `NEMA17` axis motors, the display with encoder (`EXP1` and `EXP2` ribbon cables) and the green fuse board in the electronics tray.

**New:**

1. **Hotend:** TriangleLab CHC Pro (24 V, 115 W ceramic PTC heater, stock NTC 100K thermistor `ATC Semitec 104NT-4`, up to 300 °C) with a TriangleLab Volcano NCB nozzle.
2. **Feeder:** printed `K3D Minifeeder` extruder + `NEMA14` 36 mm stepper (round pancake, 10T gear, 98 g) + BMG gear set (50:10 reduction, 5:1 ratio).
3. **Electronics:** SKR 3 EZ mainboard with `EZ2209` drivers, EBB42 GEN2 toolhead board (extruder driver and accelerometer on board), BTT Pi v1.2 host.
4. **Cooling:** one 24 V `5015` blower for the part and a `3010` fan for the hotend heatsink.
5. **Power and lighting:** `MeanWell LRS-350-24` power supply (24 V, 350 W) and `Navigator SMD 2835` LED strip (24 V). The stock printer ran on 12 V; the rebuild moves it to 24 V.
6. **Belts:** the GT2 belts on X and Y are replaced with new ones.
7. **Bed probe and nozzle cleaning:** BIQU MicroProbe V2 and silicone wiper brushes.
8. **Camera (to buy):** Creality Nebula Camera for machine-learning defect detection — see section 4.3.

Standoffs for the toolhead board are not bought: a team member already has them.

---

## 3. Engineering rationale

### 3.1. Why the old `MKS Gen v1.4` has to be replaced

1. **Step rate limit.** The `MKS Gen v1.4` uses an 8-bit `ATmega2560` at 16 MHz with 8 KB of RAM. Under Klipper its ceiling with three or more motors running is about 99 000 steps/s.
   - On CoreXY both motors run for any X or Y move (160 steps/mm per motor at 1/32 microstepping).
   - The peak load comes from the geared `K3D Minifeeder` (5:1): feeding 1 mm of filament takes 705.5 steps at 1/16 microstepping or 1 411 steps at 1/32. On sharp corners, with Pressure Advance moving at 100 mm/s, the extruder motor alone asks for 70 550 – 141 100 steps/s.
   - The `ATmega2560` is flooded with interrupts and aborts the print with `MCU 'mcu' shutdown: Rescheduled timer in the past`.
2. **Narrow link and micro-stutters.** The USB-UART link (250 000 baud) and the tiny RAM buffer cannot keep up with the command stream when printing arcs with Input Shaper enabled, causing `Timer too close` errors and blobs on curves.
3. **No UART for the drivers.** The board has no UART routing under the driver slots, so without soldering wires to the driver pins it is impossible to set current in software or run `klipper_tmc_autotune` against vertical fine artifacts (VFA).
4. **What the `BTT SKR 3 EZ` gives instead:**
   - A 32-bit `STM32H7` MCU (480–550 MHz) with a limit above 1 800 000 steps/s.
   - A built-in CAN transceiver, so the toolhead board connects directly without a separate `BTT U2C` adapter.
   - `EXP1`/`EXP2` connectors for the stock display.
   - EZ-format driver slots: the pinless `EZ2209` drivers slide into enclosed slots like memory cards and cannot be inserted the wrong way round. The ordered kit (6 129 ₽) corresponds to the board with 5 `EZ2209` drivers; three are needed (X, Y, Z), since the extruder is driven from the toolhead board.
   - If the order arrives as a bare board without drivers, it will need `EZ2209`-format drivers.

### 3.2. What the toolhead board replaces

The `BTT EBB42` format (the GEN2 board is 40×45 mm with a 31×31 mm mounting pattern) was chosen over the elongated `EBB36` (51.5×38 mm) because it fits in the place of the stock green breakout board without touching the belts.

One toolhead board removes six old parts and problems:

1. **The stock green breakout board with hot-glued connectors.** Its JST-XH pin headers are rated for 2–3 A at most and would overheat with the 115 W `CHC Pro` hotend (4.79 A peak).
2. **The external accelerometer board on the toolhead and its USB cable.** The EBB42 GEN2 has an on-board `LIS2DW` accelerometer for Input Shaper.
3. **The separate extruder driver in the tray.** The `TMC2209` extruder driver is on the toolhead board, 5 cm from the `NEMA14` motor.
4. **The thick 12-wire braided harness.** Keeping the old breakout board while adding the probe (+5 wires) and the accelerometer (+4 wires) would grow the bundle to 21 wires. A stiff harness pulls on the carriage and distorts Input Shaper measurements. With the toolhead board, a single 4-wire cable goes to the head (24 V, GND, CAN_H, CAN_L).
5. **Long cable runs for the bed probe and fans.** The `BIQU MicroProbe V2` plugs into the 5-pin `PROBE` port on the toolhead board with its short lead; the heater, thermistor and fans connect with 5–15 cm leads.
6. **Extruder step generation on the mainboard.** The toolhead board's own 32-bit `STM32G0B1` MCU generates the extruder steps, including the 141 100 steps/s peaks on corners.

The `CHC Pro` uses a standard NTC 100K thermistor, which connects directly to the thermistor port; no PT100/PT1000 amplifier is needed.

### 3.3. Why the second-generation `EBB42 GEN2 V1.0`

Compared with the first-generation `EBB42 CAN v1.2` (Molex Micro-Fit 3.0 connector on the board, rated to 9 A), the ordered GEN2 has:

- A 15 A **XT30 (2+2)** power connector soldered on the toolhead board itself.
- Short-circuit, overload and ESD protection on all power outputs: shorting the `CHC Pro` heater wires trips the protection instead of destroying the board.
- A dedicated thermistor right under the extruder driver IC; the board is rated for ambient temperatures up to 75 °C.
- A 3-pin hotend fan port with tachometer, to detect a stalled fan.
- A factory 2.2 m shielded `MX3.0 to XT30` cable and a mating adapter board in the kit.

### 3.4. Thermal and current budget

A toolhead board with a single cable is the industry-standard architecture (Bambu Lab X1/P1/A1, Prusa XL, Creality K1/K2). For this build at 24 V:

1. **Peak current (first 10–15 s of a cold start):** the ceramic PTC element draws 115 W (4.79 A) only when cold. With the motor and fans the inrush is **5.44 A**.
2. **Operating current while printing:** as the PTC warms up its power drops to 45–65 W (about 2.3 A). With the `NEMA14` (about 0.35 A on the 24 V line) and two fans (0.25 A), the continuous current is **2.94 A** — more than a 5× margin against the 15 A XT30 rating. Losses over the whole cable stay under 0.44 W.
3. **Heat on the toolhead board:** at a motor current of 0.55–0.60 A the extruder driver dissipates about 0.29 W. The open-top Hercules enclosure lets heat escape freely.
4. **Monitoring in Klipper:** a temperature sensor section in `printer.cfg` plots the toolhead board temperature and shuts the printer down above the threshold:
   ```ini
   [temperature_sensor EBB42_toolhead]
   sensor_type: temperature_mcu
   sensor_mcu: EBBCan
   min_temp: 0
   max_temp: 85
   ```

### 3.5. Keeping the glass on clips and choosing a contact probe

- The stock aluminium bed plate is thin and warps when heated to 80–110 °C. A soft magnetic sticker with a 0.5 mm flexible PEI sheet would follow every irregularity of the aluminium, while rigid 4 mm borosilicate glass on clips holds the reference plane.
- Eddy-current scanners (`BTT Eddy`) and inductive probes **do not work through 4 mm of glass** — they only sense metal at 1.5–3 mm. Hence the contact probe **`BIQU MicroProbe V2`** (6 g, 0.002 mm repeatability), which touches the top surface of the glass with a metal pin.

---

## 4. Wiring and Klipper software

### 4.1. Assembly and wiring

- **Keep the stock fuse board in the tray.** Feed 24 V from the `MeanWell LRS-350-24` through it to the `BTT SKR 3 EZ` power inputs and to the toolhead cable.
- **Toolhead link.** The EBB42 GEN2 works over CAN or USB, selected by a jumper on the board; this plan uses CAN.
- **CAN bus termination.** Enable the 120 Ω termination resistors at both ends of the line (the `120R` jumpers on the mainboard and on the toolhead board).
- **Accelerometer orientation.** Set `axes_map` in the `[lis2dw]` section to match how the toolhead board is actually mounted.
- **Mounting the toolhead board.** A team member already has the standoffs; the team makes a flat adapter plate with a 31×31 mm mounting square (4 × M3).

### 4.2. Klipper stack

With the new mainboard and toolhead board the electronics are no longer the bottleneck: Klipper has headroom for high speeds, and new functions are added by configuration instead of new hardware. Calibration is done by the firmware as well.

1. **`Klippain Shake&Tune`** — spectral analysis of the mechanics through the toolhead board's accelerometer: symmetric tensioning of the A and B belts by frequency peaks, detection of carriage skew, and precise Input Shaper filter selection.
2. **`klipper_tmc_autotune`** — automatic calculation of TMC2209 registers and current tables for 24 V and the specific motors (less noise and heat, no VFA at 80–160 mm/s).
3. **Nozzle auto-cleaning and adaptive bed mesh (`Adaptive Bed Mesh` + `KAMP`)** — the `START_PRINT` macro heats the nozzle to 150 °C (so filament does not ooze), wipes it on the silicone brush at the edge of the bed, measures the Z-offset precisely, and meshes the glass with the MicroProbe only within the footprint of the printed part (`BED_MESH_CALIBRATE ADAPTIVE=1`).
4. **Extrusion tuning in `OrcaSlicer`** — a short `smooth_time: 0.02` and Adaptive Pressure Advance (for the short `K3D Minifeeder` + `CHC Pro` path, PA values around 0.015–0.035 are expected).
5. **Camera with machine-learning defect detection (`Crowsnest` + `Obico`)** — a webcam watches the print and pauses it when a defect is detected, such as a part detaching from the glass or "spaghetti".

### 4.3. Camera for defect detection

The camera feeds Obico, which recognises print defects and pauses the print. The pick is the **Creality Nebula Camera**, to be bought on AliExpress:

- **USB, 1920×1080:** plugs into a USB port of the BTT host; no camera connector on the board is needed.
- **Manual focus:** it can be set once for the 25–30 cm distance to the bed and does not hunt while the head moves.
- **95° horizontal field of view:** covers the whole 200 × 200 mm bed from a top corner of the enclosure.
- **Made for 3D printers:** compact (55 × 40 × 35 mm), with its own mount and infrared night vision.

Creality lists it only for its own printers and pads. On arrival, confirm that it shows up as a standard USB webcam under Crowsnest (`v4l2-ctl --list-formats-ext`). If it does not, the fallback is a Logitech C270, which is documented as working with Klipper but has a narrower view and 720p.

---

## 5. Next steps and open items

**Before the orders arrive (November 22–24):**

1. Prepare the adapter plate for the EBB42 GEN2 (the standoffs are already on hand).

**To verify on the hardware:**

- **Toolhead board orientation.** The plan assumed the EBB42 lies horizontally in place of the green breakout board, but photos of the current build show that board standing vertically at the rear of the toolhead. Check the fit and belt clearance before making the adapter plate; a vertical bracket may be needed.
- **SKR 3 EZ package.** Confirm on arrival that the kit includes the 5 `EZ2209` drivers.
- **EBB42 GEN2 pin names.** Take them from BigTreeTech's [sample config for the EBB42 GEN2](https://github.com/bigtreetech/EBB/blob/master/EBB_GEN2/EBB42_GEN2/sample-bigtreetech-ebb42-gen2-v1.0.cfg) when writing `printer.cfg`. Board dimensions are in `head/README.md`.
