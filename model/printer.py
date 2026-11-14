"""Parametric CadQuery model of the Imprinta Hercules as seen in the team photos.

Run:   python model/printer.py            (needs `pip install cadquery`)
Out:   model/out/hefest_printer.step    assembly with named, coloured parts
       model/out/hefest_printer.glb     same, for web viewers
       model/out/hefest_printer.stl     everything merged into one mesh

All dimensions come from params.py.  Most are estimates from photos - see the
[EST] markers there and COMPONENTS.md.  The toolhead is only an envelope
(`toolhead_placeholder`); the real head is modelled separately.
"""
import os
import sys

import cadquery as cq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import params as P  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")

# Pose of the exported model
GY = P.GANTRY_Y_REF          # X-rail centre line
CX = P.CARRIAGE_X_REF        # carriage centre
BT = P.BED_TOP_Z_SHOWN       # top of the print surface

INCLUDE_PLANNED_PSU = True   # PSU is NOT fitted in the photos; shown translucent where its leads end

# ----------------------------------------------------------------------------- colours
C = {
    "teal": cq.Color(0.20, 0.47, 0.52, 1),
    "black": cq.Color(0.07, 0.07, 0.08, 1),
    "dark": cq.Color(0.16, 0.16, 0.18, 1),
    "steel": cq.Color(0.78, 0.80, 0.82, 1),
    "alu": cq.Color(0.86, 0.87, 0.88, 1),
    "red": cq.Color(0.80, 0.10, 0.12, 1),
    "white": cq.Color(0.93, 0.93, 0.90, 1),
    "belt": cq.Color(0.88, 0.88, 0.84, 1),
    "glass": cq.Color(0.70, 0.85, 0.90, 0.25),
    "bedglass": cq.Color(0.25, 0.30, 0.32, 0.55),
    "pcb_green": cq.Color(0.20, 0.60, 0.25, 1),
    "lcd": cq.Color(0.62, 0.72, 0.15, 1),
    "brass": cq.Color(0.80, 0.62, 0.20, 1),
    "grey": cq.Color(0.55, 0.56, 0.58, 1),
    "ghost": cq.Color(1.00, 0.55, 0.10, 0.30),
    "psu": cq.Color(0.75, 0.75, 0.78, 0.30),
    "wire_red": cq.Color(0.80, 0.10, 0.10, 1),
    "wire_blue": cq.Color(0.10, 0.25, 0.80, 1),
    "wire_brown": cq.Color(0.45, 0.25, 0.10, 1),
}


# ----------------------------------------------------------------------------- helpers
def box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def cyl_z(cx, cy, z0, z1, r):
    return cq.Workplane("XY").circle(r).extrude(z1 - z0).translate((cx, cy, z0))


def cyl_y(cx, cz, y0, y1, r):
    return cq.Workplane("XZ").circle(r).extrude(-(y1 - y0)).translate((cx, y0, cz))


def tube(pts, r):
    """Round cable/sleeve swept along a spline through pts."""
    edge = cq.Edge.makeSpline([cq.Vector(*p) for p in pts])
    plane = cq.Plane(origin=cq.Vector(*pts[0]), normal=edge.tangentAt(0))
    path = cq.Workplane("XY").add(cq.Wire.assembleEdges([edge]))
    return cq.Workplane(plane).circle(r).sweep(path)


def union(items):
    out = items[0]
    for it in items[1:]:
        out = out.union(it)
    return out


def mirror_x(x):
    return P.W - x


def outline(inset=0.0):
    """Plan-view outline of the enclosure (rectangle with chamfered corners)."""
    c = P.CORNER_CHAMFER
    i = inset
    k = i * 0.4142  # keeps the chamfer faces parallel when insetting
    return [
        (c + k, i), (P.W - c - k, i), (P.W - i, c + k), (P.W - i, P.D - c - k),
        (P.W - c - k, P.D - i), (c + k, P.D - i), (i, P.D - c - k), (i, c + k),
    ]


def rail(length, holes=True):
    """MGN rail along +X, bottom at z=0, centred on y=0, starting at x=0."""
    r = cq.Workplane("XY").box(length, P.RAIL_W, P.RAIL_H, centered=(False, True, False))
    if holes:
        n = int((length - 20) // P.RAIL_HOLE_PITCH) + 1
        pts = [(10 + i * P.RAIL_HOLE_PITCH, 0) for i in range(n)]
        r = r.faces(">Z").workplane(origin=(0, 0, P.RAIL_H)).pushPoints(pts).cboreHole(3.5, 6.0, 4.5)
    return r


def block():
    """MGN12H block along +X centred at origin; returns (body, end_caps). z=0 is the rail bottom."""
    body = cq.Workplane("XY").box(P.BLOCK_L - 6, P.BLOCK_W, P.BLOCK_TOTAL_H - P.BLOCK_GAP,
                                  centered=(True, True, False)).translate((0, 0, P.BLOCK_GAP))
    slot = cq.Workplane("XY").box(P.BLOCK_L, P.RAIL_W + 0.6, P.RAIL_H + 0.5,
                                  centered=(True, True, False))
    body = body.cut(slot)
    caps = None
    for sx in (-1, 1):
        cap = cq.Workplane("XY").box(3, P.BLOCK_W, P.BLOCK_TOTAL_H - P.BLOCK_GAP - 1,
                                     centered=(True, True, False)).translate(
            (sx * (P.BLOCK_L / 2 - 1.5), 0, P.BLOCK_GAP)).cut(slot)
        caps = cap if caps is None else caps.union(cap)
    return body, caps


def nema17(length=P.NEMA17_L):
    """NEMA17 body hanging below z=0 with the shaft pointing up, centred on the shaft."""
    s = P.NEMA17
    body = cq.Workplane("XY").box(s, s, length, centered=(True, True, False)).translate((0, 0, -length))
    body = body.edges("|Z").chamfer(4)
    return body


parts = []  # (name, shape, colour)


def add(name, shape, colour):
    parts.append((name, shape, C[colour]))


# ============================================================================= ENCLOSURE
def build_enclosure():
    T = P.SHEET_T
    shell = (cq.Workplane("XY").polyline(outline()).close().extrude(P.H)
             .cut(cq.Workplane("XY").polyline(outline(T)).close().extrude(P.H)))

    # front opening between the pillars, and the notch above the front crossbar
    band_top = P.H - P.FRONT_TOP_BAND_DROP
    band_bot = band_top - P.FRONT_TOP_BAND_H
    x0, x1 = P.FRONT_PILLAR_W, P.W - P.FRONT_PILLAR_W
    shell = shell.cut(box(x0, x1, -1, 12, P.BASE_H + P.FRONT_SILL_H, band_bot))
    shell = shell.cut(box(x0, x1, -1, 12, band_top, P.H + 1))
    # foot relief at the bottom of the front panel
    shell = shell.cut(box(P.W / 2 - 55, P.W / 2 + 55, -1, 12, -1, 7))

    # side windows (same shape both sides): diagonal cut on the upper-front corner
    y0, y1, z0, z1, k = P.SIDE_WIN_Y0, P.SIDE_WIN_Y1, P.SIDE_WIN_Z0, P.SIDE_WIN_Z1, P.SIDE_WIN_CUT
    win = [(y0, z0), (y1, z0), (y1, z1), (y0 + k, z1), (y0, z1 - k)]
    cutter = cq.Workplane("YZ").polyline(win).close().extrude(P.W + 20).translate((-10, 0, 0))
    shell = shell.cut(cutter)

    # front panel cut-outs: LCD window, knob shaft, switch
    shell = shell.cut(box(P.LCD_WIN_X0, P.LCD_WIN_X1, -1, 5, P.LCD_WIN_Z0, P.LCD_WIN_Z1))
    add("enclosure_shell", shell, "teal")

    # chamber floor (top of the electronics base)
    floor = cq.Workplane("XY").polyline(outline(T)).close().extrude(T).translate((0, 0, P.BASE_H - T))
    add("chamber_floor", floor, "teal")

    # clear side panels, slightly larger than the opening, inside the walls
    m = 8
    pan = [(y0 - m, z0 - m), (y1 + m, z0 - m), (y1 + m, z1 + m), (y0 + k - m * 0.4, z1 + m),
           (y0 - m, z1 - k + m * 0.4)]
    panel = cq.Workplane("YZ").polyline(pan).close().extrude(P.WINDOW_T)
    add("side_window_left", panel.translate((T, 0, 0)), "glass")
    add("side_window_right", panel.translate((P.W - T - P.WINDOW_T, 0, 0)), "glass")

    # front panel controls
    add("lcd_screen", box(P.LCD_WIN_X0, P.LCD_WIN_X1, 0.2, T + 0.5, P.LCD_WIN_Z0, P.LCD_WIN_Z1), "lcd")
    knob = cyl_y(P.KNOB_X, P.KNOB_Z, -P.KNOB_L, 0, P.KNOB_D / 2)
    add("encoder_knob", knob, "alu")
    sw = box(P.SWITCH_X - 4, P.SWITCH_X + 4, -1.5, 0, P.SWITCH_Z - 7, P.SWITCH_Z + 7).union(
        cyl_y(P.SWITCH_X, P.SWITCH_Z + 1, -9, 0, 1.6))
    add("front_toggle_switch", sw, "steel")
    px, pz, pt = P.LCD_PCB
    lx = (P.LCD_WIN_X0 + P.LCD_WIN_X1) / 2
    lcd_pcb = box(lx - px / 2 + 10, lx + px / 2 + 10, 12, 12 + pt, 8, 8 + pz).union(
        box(P.LCD_WIN_X0 - 12, P.LCD_WIN_X1 + 12, T + 0.5, 12, P.LCD_WIN_Z0 - 8, P.LCD_WIN_Z1 + 8))
    add("lcd_controller_board", lcd_pcb, "pcb_green")


# ============================================================================= TOP FRAME + GANTRY
def build_gantry():
    T = P.SHEET_T
    plate = (cq.Workplane("XY").polyline(outline(T + 0.2)).close().extrude(P.TOP_PLATE_T)
             .translate((0, 0, P.TOP_PLATE_Z - P.TOP_PLATE_T)))
    plate = plate.cut(box(P.TOP_OPEN_X0, P.TOP_OPEN_X1, P.TOP_OPEN_Y0, P.TOP_OPEN_Y1,
                          P.TOP_PLATE_Z - 10, P.TOP_PLATE_Z + 10))
    add("top_frame_plate", plate, "black")

    ylen = P.Y_RAIL_Y1 - P.Y_RAIL_Y0
    for side, xr in (("left", P.Y_RAIL_X_L), ("right", P.Y_RAIL_X_R)):
        sgn = 1 if side == "left" else -1
        r = rail(ylen).rotate((0, 0, 0), (0, 0, 1), 90).translate((xr, P.Y_RAIL_Y0, P.TOP_PLATE_Z))
        add(f"y_rail_{side}", r, "steel")
        body, caps = block()
        mv = lambda s: s.rotate((0, 0, 0), (0, 0, 1), 90).translate((xr, GY, P.TOP_PLATE_Z))  # noqa: E731
        add(f"y_carriage_{side}", mv(body), "steel")
        add(f"y_carriage_{side}_end_seals", mv(caps), "red")

        # X-end plates (lower + upper) with two idlers between them
        px0, px1 = P.XEND_PLATE_X
        if side == "right":
            px0, px1 = mirror_x(px1), mirror_x(px0)
        hy = P.XEND_PLATE_HALF_Y

        def xplate(z0, z1):
            return box(px0, px1, GY - hy, GY + hy, z0, z1).edges("|Z").fillet(7)

        add(f"x_end_plate_{side}_lower", xplate(P.XEND_LOWER_Z0, P.XEND_LOWER_Z1), "alu")
        up = xplate(P.XEND_UPPER_Z0, P.XEND_UPPER_Z1)
        ix = P.XEND_IDLER_X if side == "left" else mirror_x(P.XEND_IDLER_X)
        idlers = None
        for dy in (-P.XEND_IDLER_DY, P.XEND_IDLER_DY):
            up = up.cut(cyl_z(ix, GY + dy, P.XEND_UPPER_Z0 - 1, P.XEND_UPPER_Z1 + 1, 1.7))
            idl = (cyl_z(ix, GY + dy, P.BELT_Z0 - 0.5, P.BELT_Z1 + 0.5, P.IDLER_PITCH_R)
                   .union(cyl_z(ix, GY + dy, P.XEND_LOWER_Z1 + 1.5, P.BELT_Z0 - 0.5, P.IDLER_FLANGE_R))
                   .union(cyl_z(ix, GY + dy, P.BELT_Z1 + 0.5, P.XEND_UPPER_Z0 - 1.5, P.IDLER_FLANGE_R))
                   .union(cyl_z(ix, GY + dy, P.XEND_LOWER_Z1, P.XEND_UPPER_Z1 + 2.5, 1.5)))
            idlers = idl if idlers is None else idlers.union(idl)
        # plate screws (4 per plate) - cosmetic
        for sx in (px0 + 9, px1 - 9):
            for sy in (GY - hy + 9, GY + hy - 9):
                up = up.union(cyl_z(sx, sy, P.XEND_UPPER_Z1, P.XEND_UPPER_Z1 + 2, 3))
        add(f"x_end_plate_{side}_upper", up, "alu")
        add(f"x_end_idlers_{side}", idlers, "steel")

        # rear motor (hangs under the top plate) with pulley, front corner idler on a printed bracket
        mx = P.PULLEY_X if side == "left" else mirror_x(P.PULLEY_X)
        add(f"xy_motor_{side}", nema17().translate((mx, P.MOTOR_Y, P.TOP_PLATE_Z - P.TOP_PLATE_T)), "black")
        pul = (cyl_z(mx, P.MOTOR_Y, P.TOP_PLATE_Z - P.TOP_PLATE_T, P.BELT_Z1 + 3, 2.5)
               .union(cyl_z(mx, P.MOTOR_Y, P.BELT_Z0 - 0.5, P.BELT_Z1 + 0.5, P.IDLER_PITCH_R))
               .union(cyl_z(mx, P.MOTOR_Y, P.BELT_Z0 - 9, P.BELT_Z0 - 0.5, P.IDLER_FLANGE_R))
               .union(cyl_z(mx, P.MOTOR_Y, P.BELT_Z1 + 0.5, P.BELT_Z1 + 1.5, P.IDLER_FLANGE_R)))
        add(f"xy_motor_pulley_{side}", pul, "alu")
        bx0, bx1 = (mx - 13, mx + 15) if side == "left" else (mx - 15, mx + 13)
        brk = box(bx0, bx1, 7, P.FRONT_IDLER_Y + 13, P.TOP_PLATE_Z, P.BELT_Z0 - 2).edges("|Z").fillet(4)
        add(f"front_idler_bracket_{side}", brk, "white")
        fid = (cyl_z(mx, P.FRONT_IDLER_Y, P.BELT_Z0 - 0.5, P.BELT_Z1 + 0.5, P.IDLER_PITCH_R)
               .union(cyl_z(mx, P.FRONT_IDLER_Y, P.BELT_Z0 - 2, P.BELT_Z0 - 0.5, P.IDLER_FLANGE_R))
               .union(cyl_z(mx, P.FRONT_IDLER_Y, P.BELT_Z1 + 0.5, P.BELT_Z1 + 2, P.IDLER_FLANGE_R)))
        add(f"front_corner_idler_{side}", fid, "steel")
        _ = sgn

    # X rail = the X beam, resting on the lower X-end plates, carriage on top
    xr = rail(P.X_RAIL_X1 - P.X_RAIL_X0).translate((P.X_RAIL_X0, GY, P.X_RAIL_BOTTOM_Z))
    add("x_rail", xr, "steel")
    body, caps = block()
    add("x_carriage", body.translate((CX, GY, P.X_RAIL_BOTTOM_Z)), "steel")
    add("x_carriage_end_seals", caps.translate((CX, GY, P.X_RAIL_BOTTOM_Z)), "red")

    # belts (single plane): two X runs flanking the rail, two Y runs per side
    t, z0, z1 = P.BELT_T, P.BELT_Z0, P.BELT_Z1
    segs = []
    for xo, xi, ixx in ((P.BELT_Y_RUN_X_OUT, P.BELT_Y_RUN_X_IN, P.XEND_IDLER_X),
                        (mirror_x(P.BELT_Y_RUN_X_OUT), mirror_x(P.BELT_Y_RUN_X_IN), mirror_x(P.XEND_IDLER_X))):
        segs.append(box(xo - t / 2, xo + t / 2, P.FRONT_IDLER_Y, P.MOTOR_Y, z0, z1))               # outer run
        segs.append(box(xi - t / 2, xi + t / 2, P.FRONT_IDLER_Y, GY - P.XEND_IDLER_DY, z0, z1))    # front idler -> X-end
        segs.append(box(xi - t / 2, xi + t / 2, GY + P.XEND_IDLER_DY, P.MOTOR_Y, z0, z1))          # X-end -> motor
        _ = ixx
    for dy in (-P.BELT_X_RUN_OFFSET, P.BELT_X_RUN_OFFSET):
        segs.append(box(P.XEND_IDLER_X, mirror_x(P.XEND_IDLER_X), GY + dy - t / 2, GY + dy + t / 2, z0, z1))
    add("belts_gt2", union(segs), "belt")

    # Y endstop microswitch at the rear of the right rail
    es = box(P.W - 36, P.W - 16, P.Y_RAIL_Y1 + 3, P.Y_RAIL_Y1 + 13, P.TOP_PLATE_Z, P.TOP_PLATE_Z + 6.5).union(
        box(P.W - 33, P.W - 19, P.Y_RAIL_Y1 + 1, P.Y_RAIL_Y1 + 3, P.TOP_PLATE_Z + 2, P.TOP_PLATE_Z + 5))
    add("y_endstop_switch", es, "dark")

    # toolhead envelope (placeholder) and the braided cable harness
    hx, hy_, hz = P.HEAD_ENV_X, P.HEAD_ENV_Y, P.HEAD_ENV_Z
    ghost = box(CX + hx[0], CX + hx[1], GY + hy_[0], GY + hy_[1], hz[0] + 8, hz[1])
    nozzle = cq.Workplane("XY").circle(0.5).workplane(offset=8).circle(4).loft().translate(
        (CX, GY + P.NOZZLE_Y_OFFSET, P.NOZZLE_Z))
    add("toolhead_placeholder", ghost.union(nozzle), "ghost")
    harness = tube([
        (CX + 5, GY + 15, hz[1]),
        (CX + 10, GY + 25, hz[1] + 70),
        (CX + 35, GY + 55, hz[1] + 140),
        (P.W - 110, P.D - 95, hz[1] + 150),
        (P.W - 62, P.D - 50, hz[1] + 70),
        (P.W - 52, P.D - 34, P.TOP_PLATE_Z + 4),
    ], 5.5)
    add("toolhead_cable_harness", harness, "dark")


# ============================================================================= BED + Z AXIS
def build_bed_z():
    cx = P.BED_CX
    bx, by, bt_ = P.BED_PLATE
    gx, gy, gt = P.BED_GLASS
    plate_top = BT - gt
    add("bed_heater_plate", box(cx - bx / 2, cx + bx / 2, P.BED_Y0, P.BED_Y0 + by, plate_top - bt_, plate_top)
        .edges("|Z").fillet(4), "black")
    add("bed_glass", box(cx - gx / 2, cx + gx / 2, P.BED_CY - gy / 2, P.BED_CY + gy / 2, plate_top, BT), "bedglass")
    clips = None
    for dx in (-48, 48):
        c = box(cx + dx - 8, cx + dx + 8, P.BED_Y0 - 1.5, P.BED_Y0 + 11, plate_top - bt_ - 1.2, BT + 1.2).cut(
            box(cx + dx - 9, cx + dx + 9, P.BED_Y0, P.BED_Y0 + 12, plate_top - bt_, BT))
        clips = c if clips is None else clips.union(c)
    add("bed_clips", clips, "steel")
    add("bed_centre_screw", cyl_z(cx, P.BED_Y0 + 12, BT - 0.5, BT + 0.4, 3.2), "steel")
    add("bed_levelling_knob", cyl_z(cx, P.BED_Y0 + 14, plate_top - bt_ - 22, plate_top - bt_ - 10, 10)
        .union(cyl_z(cx, P.BED_Y0 + 14, plate_top - bt_ - 10, plate_top - bt_, 2)), "black")

    # cantilever arms from the Z carriage
    arm_top = plate_top - bt_ - 8
    zy = P.Z_ROD_Y
    cw, cd, ch = P.Z_CARRIAGE
    arms = None
    for dx in (-70, 70):
        a = box(cx + dx - 6, cx + dx + 6, P.BED_Y0 + 20, zy - cd / 2 + 2, arm_top - 22, arm_top)
        arms = a if arms is None else arms.union(a)
    arms = arms.union(box(cx - 76, cx + 76, zy - cd / 2 - 14, zy - cd / 2 + 2, arm_top - 22, arm_top))
    arms = arms.union(box(cx - 76, cx + 76, P.BED_Y0 + 20, P.BED_Y0 + 32, arm_top - 22, arm_top - 8))
    add("bed_support_arms", arms, "black")

    rods = None
    for dx in (-P.Z_ROD_SPACING / 2, P.Z_ROD_SPACING / 2):
        r = cyl_z(cx + dx, zy, P.BASE_H, P.TOP_PLATE_Z - P.TOP_PLATE_T, P.Z_ROD_D / 2)
        rods = r if rods is None else rods.union(r)
    add("z_rods", rods, "steel")
    add("z_lead_screw", cyl_z(cx, zy, P.BASE_H, P.TOP_PLATE_Z - 20, P.Z_SCREW_D / 2), "grey")
    holes = None
    for dx in (-P.Z_ROD_SPACING / 2, 0, P.Z_ROD_SPACING / 2):
        h = cyl_z(cx + dx, zy, 0, P.H, (P.Z_ROD_D if dx else P.Z_SCREW_D) / 2 + 0.6)
        holes = h if holes is None else holes.union(h)
    car = box(cx - cw / 2, cx + cw / 2, zy - cd / 2, zy + cd / 2, arm_top - ch, arm_top).cut(holes)
    add("z_carriage", car, "black")
    vw, vd, vh = P.Z_COVER
    cov = box(cx - vw / 2, cx + vw / 2, zy - cd / 2 - 8, zy - cd / 2 - 8 + vd + 30, arm_top, arm_top + vh)
    cov = cov.edges("|Z").fillet(3).cut(holes)
    try:
        txt = (cq.Workplane("XZ", origin=(cx, zy - cd / 2 - 8, arm_top + vh / 2))
               .text("HERCULES", 13, 1.2, kind="bold", halign="center", valign="center"))
        cov = cov.union(txt)
    except Exception as e:  # font problems must not break the build
        print("text skipped:", e)
    add("z_carriage_cover_hercules", cov, "teal")

    # Z motor under the chamber floor (visible in the tray photo at the rear centre)
    zm = nema17().translate((cx, zy, P.BASE_H - P.SHEET_T))
    add("z_motor", zm, "black")
    add("z_coupler", cyl_z(cx, zy, P.BASE_H, P.BASE_H + 25, 9.5), "alu")


# ============================================================================= ELECTRONICS TRAY
def build_tray():
    zt = P.BASE_H - P.SHEET_T - P.TRAY_PLATE_T          # underside of the mounting plate
    add("tray_mounting_plate", box(42, P.W - 42, 28, P.D - 28, zt, zt + P.TRAY_PLATE_T), "dark")

    def pcb(pos, size):
        (px, py), (sx, sy, st) = pos, size
        zb = zt - P.PCB_STANDOFF
        b = box(px - sx / 2, px + sx / 2, py - sy / 2, py + sy / 2, zb - st, zb)
        posts = None
        for dx in (-sx / 2 + 4, sx / 2 - 4):
            for dy in (-sy / 2 + 4, sy / 2 - 4):
                p_ = cyl_z(px + dx, py + dy, zb, zt, 2.5)
                posts = p_ if posts is None else posts.union(p_)
        return b, posts, zb - st

    # --- MKS Gen V1.4 (long side front-back, driver row along the left edge)
    b, posts, zc = pcb(P.MKS_GEN_POS, P.MKS_GEN)
    mx, my = P.MKS_GEN_POS
    add("mks_gen_v1_4_board", b, "black")
    add("mks_gen_v1_4_standoffs", posts, "brass")
    drv = None
    for i in range(5):
        d = box(mx - 34, mx - 14, my - 46 + i * 19, my - 46 + i * 19 + 15, zc - 11, zc).union(
            box(mx - 29, mx - 19, my - 44 + i * 19, my - 44 + i * 19 + 9, zc - 17, zc - 11))
        drv = d if drv is None else drv.union(d)
    add("mks_stepper_drivers", drv, "dark")
    extras = (box(mx + 18, mx + 38, my + 30, my + 52, zc - 14, zc)            # power terminals (green/blue)
              .union(box(mx + 20, mx + 36, my - 6, my + 12, zc - 13, zc))     # bed/heater terminals
              .union(box(mx - 6, mx + 6, my + 38, my + 54, zc - 11, zc))      # USB-B socket
              .union(box(mx + 4, mx + 16, my - 10, my + 2, zc - 3, zc))       # ATmega2560
              .union(box(mx + 12, mx + 36, my - 53, my - 44, zc - 9, zc))     # EXP1/EXP2 headers
              .union(cyl_z(mx - 2, my + 22, zc - 12, zc, 5))                  # electrolytic caps
              .union(cyl_z(mx + 10, my + 22, zc - 12, zc, 5)))
    add("mks_gen_v1_4_connectors", extras, "grey")

    # --- green fuse / distribution board with 6 fuses
    b, posts, zc = pcb(P.FUSE_BOARD_POS, P.FUSE_BOARD)
    fx, fy = P.FUSE_BOARD_POS
    add("fuse_board", b, "pcb_green")
    add("fuse_board_standoffs", posts, "brass")
    fz = None
    for i in range(6):
        f = box(fx - 10, fx + 10, fy - 40 + i * 13, fy - 40 + i * 13 + 8, zc - 8, zc)
        fz = f if fz is None else fz.union(f)
    fz = fz.union(box(fx - 19, fx - 12, fy - 46, fy + 30, zc - 10, zc))       # screw terminals row
    add("fuse_board_fuses_and_terminals", fz, "white")

    # --- rear panel: IEC C14 inlet with switch, round connector
    T = P.SHEET_T
    iec = box(P.IEC_INLET_X - 24, P.IEC_INLET_X + 24, P.D - T - 26, P.D + 2.5, 18, 52)
    add("iec_power_inlet", iec, "black")
    add("rear_round_connector", cyl_y(P.ROUND_CONN_X, 36, P.D - T - 18, P.D + 5, 8), "steel")

    # --- spare brass standoffs (no board fitted)
    so = None
    for (sx, sy) in P.SPARE_STANDOFFS:
        s = cyl_z(sx, sy, zt - 8, zt, 2.6)
        so = s if so is None else so.union(s)
    add("spare_brass_standoffs", so, "brass")

    # --- EXP1/EXP2 ribbons from the LCD board to the mainboard
    rz = zt - 3
    rib = None
    for k_, x in enumerate((mx + 15, mx + 30)):
        r = box(x - 6, x + 6, 14, my - 53, rz - 1 - k_ * 1.5, rz - k_ * 1.5)
        rib = r if rib is None else rib.union(r)
    rib = rib.union(box(mx + 9, 175, 14, 26, rz - 2.5, rz))
    add("exp_ribbon_cables", rib, "grey")

    # --- loose leads
    usb = box(mx - 7, mx + 7, my + 54, my + 72, zc - 12, zc - 1).union(
        tube([(mx, my + 72, zc - 6), (mx + 20, my + 95, zc - 4), (mx + 90, my + 80, zt - 6),
              (P.W - 120, 150, zt - 6), (P.W - 75, 60, zt - 6)], 2.4))
    add("usb_lead", usb, "white")
    rj = box(235, 249, 196, 218, zt - 12, zt - 3).union(
        tube([(242, 196, zt - 7), (246, 160, zt - 7), (262, 110, zt - 7), (285, 62, zt - 7)], 2.6))
    add("rj45_lead", rj, "grey")
    for i, (name, col) in enumerate((("red", "wire_red"), ("black", "black"), ("blue", "wire_blue"),
                                     ("brown", "wire_brown"))):
        x0 = fx - 16 + i * 10
        xe = P.PSU_POS[0] - 45 + i * 22
        w = tube([(x0, fy - 50, zt - 10), (x0 + 6, fy - 78, zt - 12),
                  (xe - 20, fy - 60, zt - 16), (xe, fy - 30, zt - 20)], 1.6)
        w = w.union(box(xe - 3.5, xe + 3.5, fy - 31, fy - 20, zt - 21, zt - 19.5))   # fork terminal
        add(f"psu_lead_{name}", w, col)

    if INCLUDE_PLANNED_PSU:
        sx, sy, sz = P.PSU
        px, py = P.PSU_POS
        add("psu_lrs_350_24_planned", box(px - sx / 2, px + sx / 2, py - sy / 2, py + sy / 2, zt - sz, zt), "psu")


# ============================================================================= BUILD + EXPORT
def build():
    build_enclosure()
    build_gantry()
    build_bed_z()
    build_tray()
    assy = cq.Assembly(name="hefest_printer")
    for name, shape, colour in parts:
        assy.add(shape, name=name, color=colour)
    return assy


def main():
    os.makedirs(OUT, exist_ok=True)
    assy = build()
    assy.export(os.path.join(OUT, "hefest_printer.step"))
    assy.export(os.path.join(OUT, "hefest_printer.glb"), tolerance=0.1, angularTolerance=0.3)
    comp = cq.Compound.makeCompound([solid for _, sh, _ in parts for solid in sh.vals()])
    cq.exporters.export(cq.Workplane("XY").add(comp), os.path.join(OUT, "hefest_printer.stl"),
                        tolerance=0.1, angularTolerance=0.3)
    bb = comp.BoundingBox()
    print(f"{len(parts)} parts; bbox X {bb.xmin:.1f}..{bb.xmax:.1f}  Y {bb.ymin:.1f}..{bb.ymax:.1f}  "
          f"Z {bb.zmin:.1f}..{bb.zmax:.1f}")
    for n, _, _ in parts:
        print("  ", n)


if __name__ == "__main__":
    main()
