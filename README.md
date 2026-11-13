# Imprinta Hercules 3D Printer Upgrade

Technical plan and purchase specification for modernising an Imprinta Hercules 3D printer.

- **Base platform:** Imprinta Hercules — rigid steel enclosure, linear rails on X and Y, cantilevered bed on Z.
- **Firmware and control:** Klipper, with the host running on an external Lenovo laptop.
- **Goal:** bring print accuracy, speed and automation close to the level of Bambu Lab printers.
- **Budget for additional purchases:** 15 000 – 20 000 ₽.
- **New electronics (ordered):** BigTreeTech SKR 3 EZ mainboard + BIGTREETECH EBB42 GEN2 V1.0 toolhead board.

## Status (orders as of November 10, 2026)

| | Amount |
| :--- | ---: |
| Already ordered and paid (5 orders, delivery November 22–24) | **11 485 ₽** |
| Remaining to buy in the mandatory core (RIDGA V2 gear shaft only) | 650 ₽ |
| Tier 1 total (full mandatory core) | 12 135 ₽ |
| Tier 1 + 2 total (with carbon X-beam reinforcement and heatsink fan) | 15 315 ₽ |
| Maximum total with Tier 3 (reserve X/Y motors) | 18 615 ₽ |
| Left under the 20 000 ₽ limit after Tier 1 + 2 | +4 685 ₽ |

## Repository contents

| File | What it is |
| :--- | :--- |
| `Hercules_3D_Printer_Upgrade_Spec_and_Plan-v3.docx` | Current purchase specification and upgrade plan (v3), with order numbers and notes from photos of the build. |
| `3D_Printer_Upgrade_Components-v7.xlsx` | Purchase list v7 with formulas: items, status, order numbers, delivery dates, tier totals and budget control. |
| `Components.xlsx` | The original components list (parts bought in the first round), with shop links. |

---

## 1. Components already installed or purchased

These are on the printer or were bought under the original list, and are not part of the purchase list below.

1. **Hotend:** TriangleLab CHC Pro (24 V, 115 W ceramic PTC heater, stock NTC 100K thermistor `ATC Semitec 104NT-4`, up to 300 °C).
2. **Feeder (housing and motor):** printed `K3D Minifeeder` extruder + `NEMA14` 36 mm stepper (round pancake, 10T gear, 98 g) + basic BMG gear set (50:10 reduction, 5:1 ratio).
3. **Part cooling:** one 24 V `5015` blower fan — enough airflow for current needs.
4. **Drivers from the first purchase:** 1 × `TMC2209` and a set of `TMC2130` (StepStick format). The ordered SKR 3 EZ takes EZ-format drivers and ships with its own, so these stay as spares.
5. **Accelerometer from the first purchase:** `BTT ADXL345 S2DW` board with USB-C, currently on a printed bracket on the toolhead. Once the EBB42 GEN2 with its on-board accelerometer is installed it can be removed, or moved to the bed to measure Z-axis vibration.
6. **Power and lighting:** `MeanWell LRS-350-24` power supply (24 V, 350 W) and `Navigator SMD 2835` LED strip (24 V).
7. **Stock printer parts that are kept:**
   - GT2 belts on X and Y (in working condition).
   - 4 mm borosilicate glass on clips (kept to hold the plane over the thin aluminium bed).
   - The green fuse board with power terminals in the electronics tray.
   - The stock display with encoder on the front panel (`EXP1` and `EXP2` ribbon cables).

---

## 2. Purchase list (revision v7)

Standoffs are not on the list: a team member already has them.

### Tier 1 — Mandatory core (electronics, bed auto-leveling, precision)

| No. | Printer unit | Item | Qty | Price | Status | Purpose |
| :--- | :--- | :--- | :--- | ---: | :--- | :--- |
| 1 | Mainboard + drivers | **BigTreeTech SKR 3 EZ** (kit with EZ2209 drivers) | 1 | 6 129 ₽ | Ordered — No. 5552 9359 2802 4601, by Nov 24 (to the post office) | Replaces the 8-bit `MKS Gen v1.4`. Separate axis drivers no longer need to be bought. |
| 2 | Toolhead board | **BIGTREETECH EBB42 GEN2 V1.0** (XT30 2+2 connector, short-circuit protection, cable) | 1 | 2 728 ₽ | Ordered — No. 5552 1863 3888 4601, by Nov 22 | Replaces the green breakout board, the wire harness, the external accelerometer and the extruder driver in the tray. |
| 3 | Bed auto-leveling probe | **BIQU MicroProbe V2** | 1 | 1 669 ₽ | Ordered — No. 5552 1863 3884 4601, by Nov 23 | Contact micro-probe; probes the glass directly and plugs into the 5-pin `PROBE` port on the EBB42 GEN2. |
| 4 | Hotend nozzle (high flow) | **TriangleLab Volcano NCB** bimetallic nozzle | 1 | 879 ₽ | Ordered — No. 5552 9359 2800 4601, by Nov 24 | Copper body with wear-resistant coating for the CHC Pro, instead of the budget brass Printfly nozzles. |
| 5 | Nozzle cleaning | **Silicone nozzle wiper brushes for Bambu Lab A1** (set of 3) | 1 | 80 ₽ | Ordered — No. 5552 1863 3886 4601, by Nov 23 | Automatic nozzle cleaning before Z-zero probing in the `START_PRINT` macro. |
| 6 | Extruder internals | **RIDGA V2 / IDGA integrated drive gear shaft** (for BMG) | 1 | 650 ₽ | **To buy** | Replaces the stock gear in the `K3D Minifeeder`; removes runout and periodic ripple on walls. |

**Tier 1 total: 12 135 ₽** (11 485 ₽ ordered + 650 ₽ to buy).

### Tier 2 — Cooling and X-beam stiffness (recommended)

| No. | Printer unit | Item | Qty | Price | Status | Purpose |
| :--- | :--- | :--- | :--- | ---: | :--- | :--- |
| 7 | Hotend heatsink fan | **GDSTime 24V 3010 Dual Ball Bearing** (12 000 RPM) | 1 | 380 ₽ | To buy | Dual ball bearing; guards against heat-creep clogs in the heat break better than a budget fan. |
| 8 | X-beam and carriages | **Carbon square tube 20×20 mm** (1.5–2 mm wall) + 1 kg of **PETG-CF / PA-CF** filament | 1 set | 2 800 ₽ | To buy | Removes the sag of the unsupported X rail and allows printing light carriages instead of the heavy double aluminium plates. |

**Tier 1 + 2 total: 15 315 ₽.**

### Tier 3 — Budget reserve (buy only after the first tests)

| No. | Printer unit | Item | Qty | Price | Status | Purpose |
| :--- | :--- | :--- | :--- | ---: | :--- | :--- |
| 9 | X and Y steppers | **NEMA17 48 mm 2.0 A** low-inductance (`StepperOnline 17HS19-2004S1` or `LDO-42STH48-2004AC`) | 2 | 1 650 ₽ each | To buy (reserve) | Only if the NEMA17 motors already purchased skip steps at high accelerations. |

**Maximum total, Tiers 1 + 2 + 3: 18 615 ₽.**

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
   - If the order arrives as a bare board without drivers, it will need `EZ2209`-format drivers, or EZ-Driver Connector adapters to use the StepStick drivers already owned.

### 3.2. What the toolhead board replaces

The square `BTT EBB42` format (40×40 mm, 31×31 mm mounting pattern) was chosen over the elongated `EBB36` (51.5×38 mm) because it fits in the place of the stock green breakout board without touching the belts.

One toolhead board removes six old parts and problems:

1. **The stock green breakout board with hot-glued connectors.** Its JST-XH pin headers are rated for 2–3 A at most and would overheat with the 115 W `CHC Pro` hotend (4.79 A peak).
2. **The external accelerometer board on the toolhead and its USB cable.** The EBB42 GEN2 has an on-board accelerometer for Input Shaper.
3. **The separate extruder driver in the tray.** The extruder driver is on the toolhead board, 5 cm from the `NEMA14` motor.
4. **The thick 12-wire braided harness.** Keeping the old breakout board while adding the probe (+5 wires) and the accelerometer (+4 wires) would grow the bundle to 21 wires. A stiff harness pulls on the carriage and distorts Input Shaper measurements. With the toolhead board, a single 4-wire cable goes to the head (24 V, GND, CAN_H, CAN_L).
5. **Long cable runs for the bed probe and fans.** The `BIQU MicroProbe V2` plugs into the 5-pin `PROBE` port on the toolhead board with its short lead; the heater, thermistor and fans connect with 5–15 cm leads.
6. **Extruder step generation on the mainboard.** The toolhead board's own 32-bit MCU generates the extruder steps, including the 141 100 steps/s peaks on corners.

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
- **CAN bus termination.** Enable the 120 Ω termination resistors at both ends of the line (the `120R` jumpers on the mainboard and on the toolhead board).
- **Accelerometer orientation.** Set `axes_map` in the accelerometer section to match how the toolhead board is actually mounted.
- **Mounting the toolhead board.** A team member already has the standoffs; the team makes a flat adapter plate with a 31×31 mm mounting square (4 × M3).

### 4.2. Klipper stack

1. **`Klippain Shake&Tune`** — spectral analysis of the mechanics through the toolhead board's accelerometer: symmetric tensioning of the A and B belts by frequency peaks, detection of carriage skew, and precise Input Shaper filter selection.
2. **`klipper_tmc_autotune`** — automatic calculation of TMC2209 registers and current tables for 24 V and the specific motors (less noise and heat, no VFA at 80–160 mm/s).
3. **Nozzle auto-cleaning and adaptive bed mesh (`Adaptive Bed Mesh` + `KAMP`)** — the `START_PRINT` macro heats the nozzle to 150 °C (so filament does not ooze), wipes it on the silicone brush at the edge of the bed, measures the Z-offset precisely, and meshes the glass with the MicroProbe only within the footprint of the printed part (`BED_MESH_CALIBRATE ADAPTIVE=1`).
4. **Extrusion tuning in `OrcaSlicer`** — a short `smooth_time: 0.02` and Adaptive Pressure Advance (for the short `K3D Minifeeder` + `CHC Pro` path, PA values around 0.015–0.035 are expected).
5. **Camera and AI monitoring (`Crowsnest` + `Obico`)** — a webcam that pauses the print automatically when a part detaches from the glass or "spaghetti" forms.

---

## 5. Next steps and open items

**Before the orders arrive (November 22–24):**

1. Order the RIDGA V2 drive gear shaft (~650 ₽) — the only mandatory part not yet ordered.
2. Prepare the adapter plate for the EBB42 GEN2 (the standoffs are already on hand).
3. Optionally, within the remaining 4 685 ₽: the GDSTime 3010 fan (380 ₽) and the carbon tube with PETG-CF filament (2 800 ₽).

**To verify on the hardware:**

- **Toolhead board orientation.** The plan assumed the EBB42 lies horizontally in place of the green breakout board, but photos of the current build show that board standing vertically at the rear of the toolhead. Check the fit and belt clearance before making the adapter plate; a vertical bracket may be needed.
- **SKR 3 EZ package.** Confirm on arrival that the kit includes the 5 `EZ2209` drivers.
- **EBB42 GEN2 details.** The interface, MCU and accelerometer details in sections 3.2 and 4 were written for the first-generation `EBB42 CAN v1.2` (CAN bus, `STM32G0B1`, `ADXL345`, on-board `TMC2209`). Check them against the GEN2 documentation before writing `printer.cfg`.
