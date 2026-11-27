"""Shared dimensions for the Imprinta Hercules model (plain constants, no CAD imports).

Units: millimetres.
Origin: front-left-bottom OUTER corner of the enclosure.
Axes:   +X to the right (viewed from the front), +Y to the back, +Z up.

Source of each number is marked:
  [SPEC]  published figure (Habr review of the original Hercules / build volume)
  [STD]   standard catalogue dimension of the part (MGN12, NEMA17, GT2, PCB ...)
  [EST]   ESTIMATE read off the photos - replace with a caliper measurement
  [FIT]   measured on the front photo with a camera fitted to the enclosure corners
          (outer size taken as published); typically good to +/-5..10 mm
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
BASE_H = 120.0            # [FIT] height of the electronics base (floor of the print chamber)

FRONT_PILLAR_W = 58.0     # [EST] width of the front corner pillars, measured on the front face
FRONT_TOP_BAND_H = 32.0   # [FIT] height of the crossbar above the front opening
FRONT_TOP_BAND_DROP = 0.0  # [FIT] the crossbar top edge is flush with the rim
FRONT_SILL_H = 6.0        # [EST] lip between the base top and the front opening

SIDE_WIN_Y0 = 90.0        # [FIT] side window opening, front edge
SIDE_WIN_Y1 = D - 40.0    # [EST] side window opening, rear edge
SIDE_WIN_Z0 = 85.0            # [FIT] the clear panel reaches below the chamber floor
SIDE_WIN_Z1 = H - 62.0        # [EST]
SIDE_WIN_CUT = 70.0       # [FIT] diagonal cut on the upper-front corner of the window
WINDOW_T = 3.0            # [EST] clear side panel thickness

# Front control panel (on the base, between the pillars)
LCD_WIN_X0, LCD_WIN_X1 = 140.0, 212.0   # [FIT] 20x4 character LCD window
LCD_WIN_Z0, LCD_WIN_Z1 = 45.0, 71.0     # [FIT]
KNOB_X, KNOB_Z, KNOB_D, KNOB_L = 244.0, 58.0, 30.0, 18.0   # [FIT] aluminium encoder knob
SWITCH_X, SWITCH_Z = 119.0, 60.0        # [FIT] small toggle switch left of the LCD
LCD_PCB = (150.0, 56.0, 1.6)            # [STD] RepRapDiscount 2004 smart controller PCB (X, Z, thickness)

# --------------------------------------------------------------------------- #
# Top frame plate (black plate carrying the Y rails, motors and Z rod tops)
# --------------------------------------------------------------------------- #
TOP_PLATE_T = 3.0                 # [EST]
TOP_PLATE_Z = 392.0               # [EST] Z of its TOP face
TOP_OPEN_X0, TOP_OPEN_X1 = 60.0, W - 60.0   # [EST] central opening the head/X-rail moves in
TOP_OPEN_Y0, TOP_OPEN_Y1 = -5.0, 322.0      # [FIT] open at the front; only a narrow strip of the plate is left at the rear

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
XEND_PLATE_X = (6.0, 66.0)        # [FIT] X envelope of the LEFT plates (mirror for the right)
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
GANTRY_Y_REF = 166.0                          # [FIT] reference pose (as in the front photo)
GANTRY_Y_MIN = Y_RAIL_Y0 + XEND_PLATE_HALF_Y  # 64   mechanical limits of the rail centre
GANTRY_Y_MAX = Y_RAIL_Y1 - XEND_PLATE_HALF_Y  # 292
CARRIAGE_X_REF = 150.0                       # reference pose: carriage a little left of centre, as in the photo
CARRIAGE_X_MIN = XEND_PLATE_X[1] + BLOCK_L / 2.0          # 88.7  block touching the left plates
CARRIAGE_X_MAX = W - XEND_PLATE_X[1] - BLOCK_L / 2.0      # 276.3

# Belts: GT2, 6 mm wide, white, all runs in ONE horizontal plane between the X-end plates,
# top edge level with the top of the X rail (as the Hefest head's belt clamp expects).
# Along X: one run close in front of the rail and one close behind it.  The rear run is
# clamped in the head; the front run passes freely through the head.
# Along Y (each side, inboard of the Y rail): an outer run from the front idler straight to
# the rear motor pulley, and an inner run that turns at the X-end idlers.
BELT_W = 6.0              # [STD] belt width (vertical extent)
BELT_T = 1.4              # [STD] belt thickness
BELT_Z1 = X_RAIL_TOP_Z               # 417  top edge of the belt = top of the X rail
BELT_Z0 = BELT_Z1 - BELT_W           # 411
BELT_FRONT_RUN_DY = -14.9 # [DOC] X-direction run in front of the rail (Hefest head design)
BELT_REAR_RUN_DY = 18.5   # [DOC] X-direction run behind the rail, clamped in the head
BELT_TOOTH_PITCH = 2.0    # [STD] GT2
IDLER_PITCH_R = 6.0       # [STD] 20T GT2 idler/pulley pitch radius (~6.1)
IDLER_FLANGE_R = 8.0      # [EST]
BELT_Y_RUN_X_OUT = 45.0   # [FIT] X of the outer Y-direction run, left side (mirror for right)
BELT_Y_RUN_X_IN = 57.0    # [FIT] X of the inner Y-direction run, left side
PULLEY_X = (BELT_Y_RUN_X_OUT + BELT_Y_RUN_X_IN) / 2   # 51: motor pulley / front corner idler axis, left side
XEND_IDLER_X = BELT_Y_RUN_X_IN + IDLER_PITCH_R          # 63: X-end idler axes, left side
XEND_IDLER_DY_FRONT = BELT_FRONT_RUN_DY - IDLER_PITCH_R  # -20.9: front X-end idler, relative to the rail centre
XEND_IDLER_DY_REAR = BELT_REAR_RUN_DY + IDLER_PITCH_R    # 24.5: rear X-end idler
FRONT_IDLER_Y = 20.0      # [EST] Y of the front corner idler axes (white printed blocks)
MOTOR_Y = 326.0           # [EST] Y of the X/Y motor shafts (rear corners, motors hang under the plate)
Y_RAIL_STOP = (14.0, 12.0, 10.0)   # [FIT] black stop block at the front end of each Y rail (X, Y, Z)

NEMA17 = 42.3             # [STD] NEMA17 flange size
NEMA17_L = 40.0           # [EST] X/Y/Z motor body length

# Print head: the Hefest head (model/parts/hefest_head.glb, head coordinates) is merged into
# the GLB on the carriage.  Head origin = carriage centre, head +Y up with the rail top at
# head y = 4, head +Z along the X rail, hotend on the -X (front) side.
HEAD_ORIGIN_Z = X_RAIL_TOP_Z - 4.0          # 413
NOZZLE_Y_OFFSET = -38.4   # [DOC] nozzle tip in FRONT of the X-rail centre line (Hefest head)
NOZZLE_Z = HEAD_ORIGIN_Z - 69.8             # [DOC] 343.2: nozzle tip (head y = -69.8)
XT30_HEAD = (1.6, 66.9, -31.0)              # [DOC] XT30 plug on the EBB42 GEN2, head coordinates (x, y, z); see head/v3/board.py

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
BED_TOP_Z_MIN = BED_TOP_Z_HOME - BUILD[2]     # 133  bed fully down
BED_TOP_Z_SHOWN = 290.0            # [FIT] bed height in the exported pose (as in the front photo)

Z_ROD_D = 12.0            # [EST] smooth rod diameter
Z_ROD_SPACING = 110.0     # [FIT] centre distance between the two rods (lead screw in the middle)
Z_ROD_Y = 333.0           # [FIT]
Z_SCREW_D = 8.0           # [EST] lead screw (T8 assumed)
Z_CARRIAGE = (150.0, 28.0, 60.0)   # [EST] Z carriage block envelope
Z_COVER = (160.0, 60.0, 46.0)      # [FIT] teal "HERCULES" cover on the Z carriage (X, Y, Z)
Z_COVER_Y0 = 289.0                 # [FIT] front face of the cover

# Nozzle-reachable area (nozzle tip), given the limits above
REACH_X = (CARRIAGE_X_MIN, CARRIAGE_X_MAX)
REACH_Y = (GANTRY_Y_MIN + NOZZLE_Y_OFFSET, GANTRY_Y_MAX + NOZZLE_Y_OFFSET)
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
    "carriage_top_centre": (CARRIAGE_X_REF, GANTRY_Y_REF, X_BLOCK_TOP_Z),
    "carriage_block_size": (BLOCK_L, BLOCK_W, BLOCK_TOTAL_H - BLOCK_GAP),   # along X, across Y, height
    "carriage_hole_pattern": BLOCK_HOLES,
    "x_rail_centre_y": GANTRY_Y_REF,
    "x_rail_z": (X_RAIL_BOTTOM_Z, X_RAIL_TOP_Z),
    "x_rail_width": RAIL_W,
    "belt_front_run_y": GANTRY_Y_REF + BELT_FRONT_RUN_DY,
    "belt_back_run_y": GANTRY_Y_REF + BELT_REAR_RUN_DY,
    "belt_z": (BELT_Z0, BELT_Z1),
    "belt_thickness": BELT_T,
    "xend_plate_inner_x": (XEND_PLATE_X[1], W - XEND_PLATE_X[1]),
    "xend_plate_z": (XEND_LOWER_Z0, XEND_UPPER_Z1),
    "top_plate_top_z": TOP_PLATE_Z,
    "top_opening_x": (TOP_OPEN_X0, TOP_OPEN_X1),
    "top_opening_y": (TOP_OPEN_Y0, TOP_OPEN_Y1),
    "enclosure_rim_z": H,
    "nozzle_z": NOZZLE_Z,
    "nozzle_y_offset": NOZZLE_Y_OFFSET,
    "bed_top_z_home": BED_TOP_Z_HOME,
    "print_area_x": PRINT_AREA_X,
    "print_area_y": PRINT_AREA_Y,
}
