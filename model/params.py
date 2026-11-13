"""Shared dimensions for the Imprinta Hercules model (plain constants, no CAD imports).

Units: millimetres.
Origin: front-left-bottom OUTER corner of the enclosure.
Axes:   +X to the right (viewed from the front), +Y to the back, +Z up.

Source of each number is marked:
  [SPEC]  published figure (Habr review of the original Hercules / build volume)
  [STD]   standard catalogue dimension of the part (MGN12, NEMA17, GT2, PCB ...)
  [EST]   ESTIMATE read off the photos - replace with a caliper measurement
  [DOC]   taken from the project documents, not visible/confirmable in the photos

Everything marked [EST] is good to roughly +/-5..10 mm at best.  The values the
print-head design depends on are collected in the "GANTRY / HEAD INTERFACE"
block and repeated in HEAD_INTERFACE at the bottom of the file.
"""

# --------------------------------------------------------------------------- #
# Enclosure
# --------------------------------------------------------------------------- #
W = 365.0                 # [SPEC] outer width  (X)
D = 355.0                 # [SPEC] outer depth  (Y)
H = 430.0                 # [SPEC] outer height (Z)
SHEET_T = 1.5             # [EST] steel sheet thickness
CORNER_CHAMFER = 30.0     # [EST] plan-view chamfer of the four vertical corners
BASE_H = 72.0             # [EST] height of the electronics base (floor of the print chamber)

FRONT_PILLAR_W = 58.0     # [EST] width of the front corner pillars, measured on the front face
FRONT_TOP_BAND_H = 58.0   # [EST] height of the crossbar above the front opening
FRONT_TOP_BAND_DROP = 16.0  # [EST] the crossbar top edge sits this far below the rim
FRONT_SILL_H = 6.0        # [EST] lip between the base top and the front opening

SIDE_WIN_Y0 = 52.0        # [EST] side window opening, front edge
SIDE_WIN_Y1 = D - 40.0    # [EST] side window opening, rear edge
SIDE_WIN_Z0 = BASE_H + 28.0   # [EST]
SIDE_WIN_Z1 = H - 62.0        # [EST]
SIDE_WIN_CUT = 55.0       # [EST] diagonal cut on the upper-front corner of the window
WINDOW_T = 3.0            # [EST] clear side panel thickness

# Front control panel (on the base, between the pillars)
LCD_WIN_X0, LCD_WIN_X1 = 133.0, 207.0   # [EST] 20x4 character LCD window
LCD_WIN_Z0, LCD_WIN_Z1 = 23.0, 49.0     # [EST]
KNOB_X, KNOB_Z, KNOB_D, KNOB_L = 238.0, 36.0, 22.0, 16.0   # [EST] aluminium encoder knob
SWITCH_X, SWITCH_Z = 110.0, 36.0        # [EST] small toggle switch left of the LCD
LCD_PCB = (150.0, 56.0, 1.6)            # [STD] RepRapDiscount 2004 smart controller PCB (X, Z, thickness)

# --------------------------------------------------------------------------- #
# Top frame plate (black plate carrying the Y rails, motors and Z rod tops)
# --------------------------------------------------------------------------- #
TOP_PLATE_T = 3.0                 # [EST]
TOP_PLATE_Z = 392.0               # [EST] Z of its TOP face
TOP_OPEN_X0, TOP_OPEN_X1 = 60.0, W - 60.0   # [EST] central opening the head/X-rail moves in
TOP_OPEN_Y0, TOP_OPEN_Y1 = 20.0, 292.0      # [EST]

# --------------------------------------------------------------------------- #
# Linear rails - assumed MGN12 with MGN12H blocks (red end seals)
# --------------------------------------------------------------------------- #
RAIL_W = 12.0             # [STD] MGN12 rail width          ([EST] that it is size 12)
RAIL_H = 8.0              # [STD] MGN12 rail height
RAIL_HOLE_PITCH = 25.0    # [STD]
BLOCK_W = 27.0            # [STD] MGN12H block width
BLOCK_L = 45.4            # [STD] MGN12H block length (without end seals ~34.7 for the C type)
BLOCK_TOTAL_H = 13.0      # [STD] rail bottom -> block top
BLOCK_GAP = 3.0           # [STD] rail bottom -> block bottom (H1)
BLOCK_HOLES = (20.0, 20.0)  # [STD] M3 mounting pattern on the block top (across, along)

# Y rails (one each side, on top of the top plate, running front-back)
Y_RAIL_X_L = 22.0                 # [EST] X of the left Y-rail centre line
Y_RAIL_X_R = W - 22.0             # [EST]
Y_RAIL_Y0, Y_RAIL_Y1 = 28.0, 328.0   # [EST] 300 mm rails
Y_RAIL_TOP_Z = TOP_PLATE_Z + RAIL_H
Y_BLOCK_TOP_Z = TOP_PLATE_Z + BLOCK_TOTAL_H     # 405

# X-end plates: two aluminium plates per side, idlers sandwiched between them
XEND_PLATE_T = 4.0                # [EST]
XEND_PLATE_X = (6.0, 64.0)        # [EST] X envelope of the LEFT plates (mirror for the right)
XEND_PLATE_HALF_Y = 36.0          # [EST] plates span gantry_y +/- this
XEND_LOWER_Z0 = Y_BLOCK_TOP_Z                       # 405  lower plate bottom
XEND_LOWER_Z1 = XEND_LOWER_Z0 + XEND_PLATE_T        # 409  lower plate top = X rail seat
XEND_GAP = 14.0                   # [EST] gap between the plates (idler height incl. flanges)
XEND_UPPER_Z0 = XEND_LOWER_Z1 + XEND_GAP            # 423
XEND_UPPER_Z1 = XEND_UPPER_Z0 + XEND_PLATE_T        # 427

# --------------------------------------------------------------------------- #
# GANTRY / HEAD INTERFACE
# --------------------------------------------------------------------------- #
# The X rail is a bare MGN12 rail spanning between the two lower X-end plates
# (it IS the X beam - nothing supports it in between).  Mounting holes face up
# and the carriage block rides on its top face.              [EST: orientation]
X_RAIL_X0, X_RAIL_X1 = 40.0, W - 40.0        # [EST] rail ends (rail passes between the idlers)
X_RAIL_BOTTOM_Z = XEND_LOWER_Z1              # 409
X_RAIL_TOP_Z = X_RAIL_BOTTOM_Z + RAIL_H      # 417
X_BLOCK_BOTTOM_Z = X_RAIL_BOTTOM_Z + BLOCK_GAP        # 412
X_BLOCK_TOP_Z = X_RAIL_BOTTOM_Z + BLOCK_TOTAL_H       # 422  <- head mounting face

# Gantry position used for the exported model (rail centre line Y) and limits
GANTRY_Y_REF = 190.0                          # [EST] reference pose
GANTRY_Y_MIN = Y_RAIL_Y0 + XEND_PLATE_HALF_Y  # 64   mechanical limits of the rail centre
GANTRY_Y_MAX = Y_RAIL_Y1 - XEND_PLATE_HALF_Y  # 292
CARRIAGE_X_REF = W / 2.0                      # reference pose: carriage centred
CARRIAGE_X_MIN = XEND_PLATE_X[1] + BLOCK_L / 2.0          # 86.7  block touching the left plates
CARRIAGE_X_MAX = W - XEND_PLATE_X[1] - BLOCK_L / 2.0      # 278.3

# Belts: GT2, 6 mm wide, all runs in ONE horizontal plane between the X-end plates.
# Two runs flank the X rail (front and back); two runs flank each Y side.
BELT_W = 6.0              # [STD] belt width (vertical extent)
BELT_T = 1.4              # [STD] belt thickness
BELT_Z0 = XEND_LOWER_Z1 + 4.0        # [EST] 413  bottom edge of the belt
BELT_Z1 = BELT_Z0 + BELT_W           # [EST] 419  top edge of the belt
BELT_X_RUN_OFFSET = 20.0  # [EST] |Y| distance of each X-direction run from the rail centre line
                          #       front run at gantry_y - 20, back run at gantry_y + 20
IDLER_PITCH_R = 6.0       # [STD] 20T GT2 idler/pulley pitch radius (~6.1)
IDLER_FLANGE_R = 8.0      # [EST]
BELT_Y_RUN_X_OUT = 38.0   # [EST] X of the outer Y-direction run, left side (mirror for right)
BELT_Y_RUN_X_IN = 50.0    # [EST] X of the inner Y-direction run, left side
PULLEY_X = 44.0           # [EST] X of the motor pulley / front corner idler axis, left side
XEND_IDLER_X = 56.0       # [EST] X of the two idler axes on the left X-end (mirror for right)
XEND_IDLER_DY = BELT_X_RUN_OFFSET + IDLER_PITCH_R   # [EST] 26: idler axes at gantry_y -/+ this
FRONT_IDLER_Y = 20.0      # [EST] Y of the front corner idler axes
MOTOR_Y = 326.0           # [EST] Y of the X/Y motor shafts (rear corners, motors hang under the plate)

NEMA17 = 42.3             # [STD] NEMA17 flange size
NEMA17_L = 40.0           # [EST] X/Y/Z motor body length

# Toolhead envelope currently on the machine (placeholder only - see Hefest repo)
NOZZLE_Y_OFFSET = -40.0   # [EST] nozzle is this far in FRONT of the X-rail centre line
NOZZLE_DROP = 64.0        # [EST] nozzle tip below the X-rail bottom face
NOZZLE_Z = X_RAIL_BOTTOM_Z - NOZZLE_DROP     # 345
HEAD_ENV_X = (-30.0, 30.0)     # [EST] envelope relative to carriage centre X
HEAD_ENV_Y = (-72.0, 30.0)     # [EST] relative to the rail centre line
HEAD_ENV_Z = (NOZZLE_Z, 445.0)  # [EST] absolute

# --------------------------------------------------------------------------- #
# Bed and Z axis (cantilevered bed on two rods + lead screw at the rear centre)
# --------------------------------------------------------------------------- #
BUILD = (200.0, 200.0, 210.0)      # [SPEC]
BED_PLATE = (220.0, 215.0, 3.0)    # [EST] aluminium heater plate (X, Y, thickness)
BED_GLASS = (200.0, 200.0, 4.0)    # [DOC] 4 mm borosilicate glass on clips (not distinguishable in photos)
BED_CX = W / 2.0                   # [EST] bed centred in X
BED_Y0 = 40.0                      # [EST] front edge of the bed plate
BED_CY = BED_Y0 + BED_PLATE[1] / 2.0          # 147.5
BED_TOP_Z_HOME = NOZZLE_Z          # [EST] top of the print surface with the bed fully up (Z = 0)
BED_TOP_Z_MIN = BED_TOP_Z_HOME - BUILD[2]     # 135  bed fully down
BED_TOP_Z_SHOWN = 250.0            # [EST] bed height in the exported pose (about as in the photos)

Z_ROD_D = 12.0            # [EST] smooth rod diameter
Z_ROD_SPACING = 56.0      # [EST] centre distance between the two rods
Z_ROD_Y = 314.0           # [EST]
Z_SCREW_D = 8.0           # [EST] lead screw (T8 assumed)
Z_CARRIAGE = (104.0, 42.0, 60.0)   # [EST] Z carriage block envelope
Z_COVER = (100.0, 40.0, 46.0)      # [EST] teal "HERCULES" cover on the Z carriage

# Nozzle-reachable area (nozzle tip), given the limits above
REACH_X = (CARRIAGE_X_MIN, CARRIAGE_X_MAX)                                  # (86.7, 278.3)
REACH_Y = (GANTRY_Y_MIN + NOZZLE_Y_OFFSET, GANTRY_Y_MAX + NOZZLE_Y_OFFSET)  # (24, 252)
PRINT_AREA_X = (BED_CX - BUILD[0] / 2.0, BED_CX + BUILD[0] / 2.0)           # (82.5, 282.5)
PRINT_AREA_Y = (BED_CY - BUILD[1] / 2.0, BED_CY + BUILD[1] / 2.0)           # (47.5, 247.5)

# --------------------------------------------------------------------------- #
# Electronics tray (components hang from the underside of the chamber floor)
# Positions are (X centre, Y centre); read from the tray photo, all [EST].
# --------------------------------------------------------------------------- #
TRAY_PLATE_T = 2.0
PCB_STANDOFF = 6.0
MKS_GEN = (84.0, 110.0, 1.6)       # [STD] MKS Gen V1.4 PCB (X, Y, thickness) - long side front-back
MKS_GEN_POS = (82.0, 200.0)
FUSE_BOARD = (40.0, 100.0, 1.6)    # [EST] green fuse / distribution board, 6 fuses
FUSE_BOARD_POS = (172.0, 183.0)
IEC_INLET_X = 50.0                 # [EST] IEC C14 inlet with switch, on the rear wall
ROUND_CONN_X = 110.0               # [EST] round metal panel connector on the rear wall (unidentified)
SPARE_STANDOFFS = ((60.0, 80.0), (109.0, 80.0), (60.0, 138.0), (109.0, 138.0))  # brass standoffs, no board fitted
PSU = (115.0, 215.0, 30.0)         # [STD] MeanWell LRS-350-24 (X, Y, Z) - NOT fitted in the photo
PSU_POS = (290.0, 178.0)           # [EST] where the loose PSU leads end up

# --------------------------------------------------------------------------- #
# Summary for the head model
# --------------------------------------------------------------------------- #
HEAD_INTERFACE = {
    "carriage_top_centre": (CARRIAGE_X_REF, GANTRY_Y_REF, X_BLOCK_TOP_Z),   # (182.5, 190, 422)
    "carriage_block_size": (BLOCK_L, BLOCK_W, BLOCK_TOTAL_H - BLOCK_GAP),   # along X, across Y, height
    "carriage_hole_pattern": BLOCK_HOLES,
    "x_rail_centre_y": GANTRY_Y_REF,
    "x_rail_z": (X_RAIL_BOTTOM_Z, X_RAIL_TOP_Z),                            # (409, 417)
    "x_rail_width": RAIL_W,
    "belt_front_run_y": GANTRY_Y_REF - BELT_X_RUN_OFFSET,                   # 170
    "belt_back_run_y": GANTRY_Y_REF + BELT_X_RUN_OFFSET,                    # 210
    "belt_z": (BELT_Z0, BELT_Z1),                                           # (413, 419)
    "belt_thickness": BELT_T,
    "xend_plate_inner_x": (XEND_PLATE_X[1], W - XEND_PLATE_X[1]),           # (64, 301)
    "xend_plate_z": (XEND_LOWER_Z0, XEND_UPPER_Z1),                         # (405, 427)
    "top_plate_top_z": TOP_PLATE_Z,                                         # 392
    "top_opening_x": (TOP_OPEN_X0, TOP_OPEN_X1),
    "top_opening_y": (TOP_OPEN_Y0, TOP_OPEN_Y1),
    "enclosure_rim_z": H,                                                   # 430
    "nozzle_z": NOZZLE_Z,                                                   # 345
    "nozzle_y_offset": NOZZLE_Y_OFFSET,
    "bed_top_z_home": BED_TOP_Z_HOME,
    "print_area_x": PRINT_AREA_X,
    "print_area_y": PRINT_AREA_Y,
}
