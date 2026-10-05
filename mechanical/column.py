"""Cylindrical column, frame socket and round base: the sculpture floats on a
one-piece hollow column that holds the column board
(pappalapap/designs/column_board.py) in two internal slots. The column's top
tapers into a slim neck around the flex tail, and the neck plugs into a socket
under the frame's tail window. Only two power wires run down to the base.

World frame: the balanced, oriented band from orient.py. The tail exits
straight down at the origin, the strip's +x at the tail is world +x, the strip
plane there is world x-z, and the flex contact face looks toward +y. The
column board stands upright on the +y side of the tail, component side facing
-y, ZIF at its top edge. The column axis lies in the strip plane (the neck is
centred); the tail S-bends about 4.5 mm inside the taper to reach the ZIF. Board frame -> world: x_pcb -> +x, y_pcb -> +z,
component normal -> -y (proper rotation; see scripts/check_zif_mating.py).

Stack-up (z, mm; 0 = strip edge at the tail):
   -4.0          bottom of the rail's back wall (frame.BACK)
   -3.5 .. -11   socket boss fused under frame segment 1
   -5   .. -11   neck inside the socket (stadium around the tail)
  -11   .. -46   taper: neck -> full cylinder (convex hull)
  -46.8          board top edge = top end of the internal slots (board stop)
  -50            ZIF cable stop = flex tail cut end (TAIL_LENGTH)
  -112.5         board bottom; the board pusher below it holds the board up
  -125           base top; the column sits SOCKET_DEPTH into the base

Writes out/column/: frame_segment_01_socket.stl (segment 1 + socket; it
replaces out/frame/frame_segment_01.stl when printing), column.stl,
hatch_cover.stl (front access hatch, 2 x M2 screws), board_pusher.stl (block under the board), base_body.stl, base_plate.stl, assembly.stl and
assembly_views.png (via column_render). Run after orient.py and frame.py.
"""

from pathlib import Path

import manifold3d as m3
import numpy as np
import trimesh

import cup
import frame
from geometry import LOOP, TAIL_LENGTH, TAIL_OFFSET

OUT = Path(__file__).parent / "out"

# --- Column board (designs/column_board.py) and ZIF ------------------------
BOARD_W = 24.0
BOARD_H = 66.0
BOARD_T = 1.6
ZIF_EDGE_INSET = 0.5  # entry face below the board's top edge
ZIF_ENTRY_TO_STOP = 2.7  # XFCN: CABLE_STOP_Y - ENTRY_FACE_Y
ZIF_CABLE_HEIGHT = 0.9  # cable mid-plane above the board surface (ZIF body 2.0 tall)
EDGE_STRIP = 1.0  # copper-free strip on both long edges, held in the slots
USB_Y = (2.8, 11.8)  # USB-C span along the board (board frame, origin at centre)
USB_DEPTH = 5.0  # USB-C body above the board surface
XIAO_Y = 7.3
# Smallest circle around the board's cross-section (component courtyards and
# heights from design-report-...ColumnBoard.json; since 2026-10-05 the bulk is
# four 1206 MLCCs, so the XIAO stack (8.5 mm with microSD) and the board edges in
# their slots set it): radius 12.80, centred on the board's centreline, 1.95 mm
# in front of the component surface.
FRONT_TALLEST = 8.5  # XIAO ESP32S3 Sense stack (no camera) with a microSD card
BOARD_CIRCLE_R = 12.80
BOARD_CIRCLE_DEPTH = 1.95

# --- Column -----------------------------------------------------------------
CLEAR = 0.25
WALL = 2.0
NECK_INNER = (18.5, 3.0)  # stadium around the tail (17 mm wide, 0.2 mm thick)
NECK_WALL = 1.5
NECK_END_WALL = 4.25  # thicker stadium ends take the M2 inserts for the frame socket
SOCKET_TOP = -6.0  # neck top end inside the frame socket (5 mm engagement)
SOCKET_BOTTOM = -11.0
TAPER_END = -46.0  # full cylinder from here down
SLOT_DEPTH_EXTRA = 0.15  # slot clearance beyond the board edge
RIB_FRONT = 1.2  # rib material in front of the board surface
RIB_BACK = 1.5  # rib material behind the board
BASE_TOP = -125.0
SOCKET_DEPTH = 10.0

HATCH_HALF_W = 13.0  # window half-width (x)
HATCH_Y_CUT = 5.0  # window cut extends from the front to this distance in front of the axis
HATCH_ABOVE_TOP = 1.0  # window top above the board's top edge (just under the taper)
HATCH_BELOW_TOP = 17.0  # window bottom below the board's top edge (ZIF body + latch)
HATCH_GAP = 0.15  # cover clearance
TAB_HALF_W = 3.0
TAB_DEPTH = 4.5  # tab reaches this far inside the wall (front parts are >= 5.7 mm away)
TAB_H = 9.0
TAB_OVERLAP = 7.0  # how much of a tab sits behind the cover (screw 3.5 mm in from its edge)

# Heat-set inserts (Ruthex-style): hole diameter, hole depth.
M2_INSERT = (3.2, 3.5)  # M2 x 3
M3_INSERT = (4.0, 6.0)  # M3 x 5.7
M2_CLEAR, M2_HEAD = 2.3, 4.2  # countersunk M2 (90 deg)
M3_CLEAR, M3_HEAD = 3.4, 6.4  # countersunk M3 (90 deg)

# Column-to-base: M3 inserts in three bosses inside the column's bottom end,
# placed outside the space the board and its parts sweep through when the
# board slides in from below (checked in main()).
BOTTOM_BOSSES = ((8.5, -10.5), (-7.0, -12.9), (0.0, 13.0))  # (x, y) from the column axis
BOTTOM_BOSS_R = 3.0
BOTTOM_BOSS_H = 8.0
SOCKET_FLOOR = 3.0

# --- Column top: cup around the frame rail (cup.py) -----------------------------
CUP_MORPH_END = -8.0  # the morph from round to the rail band completes here
CUP_HALF_LEN = 20.0  # cup length along the rail, each side of the tail
CUP_SHELL = 2.0  # cup wall around the rail
CUP_TOP = 1.0  # cup walls rise to this height on the rail sides (rail lip ends at 2.5; LEDs start at 3.9)
CUP_FILLET = 4.0  # smooth-min blend between the column and the cup
CUP_CLEAR = 0.2  # rail-to-cup clearance (glue gap)

# --- Frame socket (superseded by the cup) --------------------------------------
BOSS_TOP = -frame.BACK + 0.5  # 0.5 mm into the rail's back wall
BOSS_WALL = 1.5
FLARE_RADIUS = 6.0  # concave fillet where the socket flares along the rail
FLARE_Y_ZONE = 2.5  # height (above the socket pocket) over which it narrows to the rail thickness
RAIL_HALF_THICK = frame.THICK / 2

# --- Base -------------------------------------------------------------------
BASE_TOP_FILLET = 4.0  # round-over on the base's top outer edge
COLLAR_FILLET = 6.0  # concave fillet collar where the column enters the base
PUSHER_W = 20.0  # board pusher: rectangular block under the board, in its plane
PUSHER_MARGIN = 1.5  # in front of and behind the board
BASE_DIAMETER = 100.0
BASE_HEIGHT = 30.0
BASE_WALL = 2.5
BASE_PLATE = 3.0
POWER_JACK_HOLE = 8.0  # panel 5.5 x 2.1 DC jack, >= 6 A
SCREW_RADIUS = 40.0


def tail_center_x() -> float:
    d = np.load(OUT / "mobius_shape.npz")
    du = LOOP / int(d["nu"])
    return TAIL_OFFSET - round(TAIL_OFFSET / du) * du


def stadium(cx, cy, w, h) -> m3.CrossSection:
    r = h / 2
    core = m3.CrossSection.square((w - h, 1e-3)).translate((cx - (w - h) / 2, cy))
    return core.offset(r, m3.JoinType.Round, circular_segments=48)


def circle(cx, cy, r) -> m3.CrossSection:
    return m3.CrossSection.circle(r, 96).translate((cx, cy))


def prism(cs: m3.CrossSection, z0: float, z1: float) -> m3.Manifold:
    return m3.Manifold.extrude(cs, z1 - z0).translate((0, 0, z0))


def box(x0, x1, y0, y1, z0, z1) -> m3.Manifold:
    return m3.Manifold.cube((x1 - x0, y1 - y0, z1 - z0)).translate((x0, y0, z0))


def loft(cs_top, z_top, cs_bottom, z_bottom) -> m3.Manifold:
    """Convex taper between two convex sections (hull of two thin slices)."""
    eps = 0.01
    return m3.Manifold.batch_hull([prism(cs_top, z_top - eps, z_top), prism(cs_bottom, z_bottom, z_bottom + eps)])


def revolve_profile(points, segments: int = 128) -> m3.Manifold:
    """Solid of revolution about +z from a (radius, height) profile polygon."""
    return m3.Manifold.revolve(m3.CrossSection([np.asarray(points, dtype=float)]), segments)


def arc(cx, cy, r, a0, a1, n=16):
    a = np.radians(np.linspace(a0, a1, n))
    return [(cx + r * np.cos(t), cy + r * np.sin(t)) for t in a]


def countersunk(clear: float, head: float, length: float) -> m3.Manifold:
    """Countersunk (90 deg) screw hole along +z, head face at z = 0."""
    cone = m3.Manifold.cylinder((head - clear) / 2, head / 2, clear / 2, 32)
    return cone + m3.Manifold.cylinder(length, clear / 2, clear / 2, 32) + m3.Manifold.cylinder(1.0, head / 2, head / 2, 32).translate((0, 0, -1.0))


def along_y(man: m3.Manifold) -> m3.Manifold:
    """Re-orient a +z feature to point along +y."""
    return man.rotate((-90, 0, 0))


def along_x(man: m3.Manifold, sign: int) -> m3.Manifold:
    """Re-orient a +z feature to point along sign * x."""
    return man.rotate((0, 90 * sign, 0))


def to_trimesh(man: m3.Manifold) -> trimesh.Trimesh:
    """Convert, dropping zero-volume slivers that coplanar booleans can leave."""
    mesh = man.to_mesh()
    tm = trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts))
    bodies = [b for b in tm.split(only_watertight=False) if abs(b.volume) > 1e-3]
    return trimesh.util.concatenate(bodies) if len(bodies) > 1 else bodies[0]


def from_trimesh(tm: trimesh.Trimesh) -> m3.Manifold:
    return m3.Manifold(m3.Mesh(vert_properties=np.asarray(tm.vertices, dtype=np.float32),
                               tri_verts=np.asarray(tm.faces, dtype=np.uint32)))


def main() -> None:
    out = OUT / "column"
    out.mkdir(exist_ok=True)
    for old in ("frame_segment_01_foot.stl", "frame_segment_01_socket.stl", "column_front.stl", "column_back.stl",
                "slot_key.stl"):
        (out / old).unlink(missing_ok=True)
    xt = tail_center_x()

    # Board placement. The column axis (centre of the board's enclosing circle)
    # is put in the strip plane at the tail, so the neck and the taper are
    # centred on the column. The ZIF's cable plane then sits S_OFFSET behind
    # the strip plane, and the tail makes a gentle S-bend inside the taper to
    # reach it. The S-bend uses a little tail length, so the board moves up by
    # that much to keep the cut end at the ZIF's cable stop.
    surf_y = BOARD_CIRCLE_DEPTH  # component surface; parts toward -y
    back_y = surf_y + BOARD_T
    s_offset = surf_y - ZIF_CABLE_HEIGHT
    s_run = (-TAIL_LENGTH + ZIF_ENTRY_TO_STOP) - SOCKET_BOTTOM  # neck exit to ZIF entry (negative)
    t = np.linspace(0, 1, 2001)
    path = np.stack([s_offset / 2 * (1 - np.cos(np.pi * t)), s_run * t], axis=1)
    s_extra = np.sum(np.linalg.norm(np.diff(path, axis=0), axis=1)) - abs(s_run)
    stop_z = -TAIL_LENGTH + s_extra
    board_top = stop_z + ZIF_ENTRY_TO_STOP + ZIF_EDGE_INSET
    board_bottom = board_top - BOARD_H
    board_cz = board_top - BOARD_H / 2
    assert board_top < TAPER_END, "board must sit below the taper"
    ax, ay = xt, 0.0
    r_in = BOARD_CIRCLE_R + 0.5
    r_out = r_in + WALL
    col_bottom = BASE_TOP - SOCKET_DEPTH

    # Column top: the round column morphs into a cup that cradles the frame
    # rail along its real path (cup.py, SDF + marching cubes); the column's
    # top edge follows the rail's curve and blends into the cup with a fillet.
    sp_, bp_, total_, s_arr, u_arr, low_arr = frame.boundary_frames()
    s_tail = float(np.interp(TAIL_OFFSET, u_arr[low_arr], s_arr[low_arr]))
    verts, faces = cup.build(ax=ax, ay=ay, r_out=r_out, wall=WALL, z_start=TAPER_END, z_end=CUP_MORPH_END,
                             s_center=s_tail, half_len=CUP_HALF_LEN, shell=CUP_SHELL, cup_top=CUP_TOP,
                             fillet=CUP_FILLET, clearance=CUP_CLEAR, tail_slot=NECK_INNER)
    top = from_trimesh(trimesh.Trimesh(verts, faces))
    outer_clip = prism(circle(ax, ay, r_out), col_bottom, TAPER_END + 6)  # clip region for internal features
    outer = prism(circle(ax, ay, r_out), col_bottom, TAPER_END) + top
    inner = prism(circle(ax, ay, r_in), col_bottom - 1, TAPER_END + 0.01)
    column = outer - inner
    # Ribs with slots for the board's long edges; the slots end at the board's
    # top edge, which is the board's upward stop.
    rib_x0 = BOARD_W / 2 - EDGE_STRIP
    for side in (-1, 1):
        x0, x1 = sorted((xt + side * rib_x0, xt + side * (r_out + 1)))
        rib = box(x0, x1, surf_y - RIB_FRONT, back_y + RIB_BACK, col_bottom, board_top + 3.0)
        column += rib ^ outer_clip
        sx0, sx1 = sorted((xt + side * (rib_x0 - 0.05), xt + side * (BOARD_W / 2 + SLOT_DEPTH_EXTRA)))
        column -= box(sx0, sx1, surf_y - CLEAR / 2, back_y + CLEAR / 2, col_bottom - 1, board_top)
    # USB-C opening (+x wall, through the rib) and microphone vents (front, -y).
    usb_z = (board_cz + USB_Y[0] - 1.5, board_cz + USB_Y[1] + 1.5)
    column -= box(xt + rib_x0, xt + r_out + 2, surf_y - USB_DEPTH - 2.5, back_y, *usb_z)
    for dx in (-6, -2, 2, 6):
        for dz in (-4, 0, 4):
            column -= m3.Manifold.cylinder(r_out + 2, 0.8, 0.8, 16).rotate((90, 0, 0)).translate(
                (ax + dx, ay, board_cz + XIAO_Y + dz))

    # Front access hatch at the ZIF: a window in the front wall (-y) with a
    # flush cover held by two M2 screws into tabs above and below it.
    hz = (board_top - HATCH_BELOW_TOP, board_top + HATCH_ABOVE_TOP)
    hatch_box = box(ax - HATCH_HALF_W, ax + HATCH_HALF_W, ay - r_out - 1, ay - HATCH_Y_CUT, *hz)
    wall = prism(circle(ax, ay, r_out), col_bottom, TAPER_END) - prism(circle(ax, ay, r_in), col_bottom - 1, TAPER_END + 1)
    cover = wall ^ box(ax - HATCH_HALF_W + HATCH_GAP, ax + HATCH_HALF_W - HATCH_GAP, ay - r_out - 1,
                       ay - HATCH_Y_CUT, hz[0] + HATCH_GAP, hz[1] - HATCH_GAP)
    column -= hatch_box
    tab_y = (ay - r_in - 0.5, ay - r_in + TAB_DEPTH)
    screw_z = []
    for edge_z, sign in ((hz[1], 1), (hz[0], -1)):
        z0, z1 = sorted((edge_z - sign * TAB_OVERLAP, edge_z + sign * (TAB_H - TAB_OVERLAP)))
        tab = box(ax - TAB_HALF_W, ax + TAB_HALF_W, *tab_y, z0, z1) ^ outer_clip
        tab -= hatch_box ^ (outer_clip - prism(circle(ax, ay, r_in), col_bottom - 1, TAPER_END + 7))  # not where the cover goes
        zc = edge_z - sign * TAB_OVERLAP / 2
        screw_z.append(zc)
        insert = along_y(m3.Manifold.cylinder(M2_INSERT[1], M2_INSERT[0] / 2, M2_INSERT[0] / 2, 32)).translate((ax, ay - r_in, zc))
        column += tab - insert
        cover -= along_y(countersunk(M2_CLEAR, M2_HEAD, WALL + 2)).translate((ax, ay - r_out, zc))

    # Board pusher: a plain rectangular block standing on the base socket's
    # floor that pushes the board's bottom edge up against the slot tops. The
    # power wires run down in front of it.
    pusher_len = board_bottom - col_bottom - 0.3
    pusher_y = (surf_y - PUSHER_MARGIN, back_y + PUSHER_MARGIN)
    pusher_placed = box(xt - PUSHER_W / 2, xt + PUSHER_W / 2, *pusher_y, col_bottom, col_bottom + pusher_len)
    pusher = pusher_placed.translate((-xt, -pusher_y[0], -col_bottom))

    # Column-to-base bosses with M3 inserts (from below).
    for bx, by in BOTTOM_BOSSES:
        b = m3.Manifold.cylinder(BOTTOM_BOSS_H, BOTTOM_BOSS_R, BOTTOM_BOSS_R, 32).translate((ax + bx, ay + by, col_bottom))
        b = b ^ prism(circle(ax, ay, r_out), col_bottom - 1, col_bottom + BOTTOM_BOSS_H + 1)
        column += b - m3.Manifold.cylinder(M3_INSERT[1], M3_INSERT[0] / 2, M3_INSERT[0] / 2, 32).translate(
            (ax + bx, ay + by, col_bottom - 0.01))

    # Frame segment 1 is the plain rail segment (tail window); it is glued
    # into the column's cup.
    seg1 = from_trimesh(trimesh.load(OUT / "frame" / "frame_segment_01.stl"))

    # Round base.
    base_bottom = BASE_TOP - BASE_HEIGHT
    rb = BASE_DIAMETER / 2
    f = BASE_TOP_FILLET
    body = revolve_profile([(0, 0), (rb, 0), (rb, BASE_HEIGHT - f), *arc(rb - f, BASE_HEIGHT - f, f, 0, 90), (0, BASE_HEIGHT)]
                           ).translate((ax, ay, base_bottom))
    body -= prism(circle(ax, ay, rb - BASE_WALL), base_bottom - 1, BASE_TOP - BASE_WALL)
    body += prism(circle(ax, ay, r_out + CLEAR + 2.5), col_bottom - SOCKET_FLOOR, BASE_TOP - 0.01)  # socket boss
    r0, cf = r_out + CLEAR, COLLAR_FILLET
    body += revolve_profile([(r0 - 0.5, 0), (r0 + cf, 0), *arc(r0 + cf, cf, cf, 270, 180), (r0 - 0.5, cf)]
                            ).translate((ax, ay, BASE_TOP - 0.01))  # concave collar around the column
    body -= prism(circle(ax, ay, r0), col_bottom, BASE_TOP + cf + 1)  # socket
    body -= prism(circle(ax, ay, 6.0), col_bottom - SOCKET_FLOOR - 1, col_bottom + 0.5)  # wire pass
    for bx, by in BOTTOM_BOSSES:  # countersunk M3 from inside the base, into the column's inserts
        body -= countersunk(M3_CLEAR, M3_HEAD, SOCKET_FLOOR + 2).translate((ax + bx, ay + by, col_bottom - SOCKET_FLOOR))
    body -= m3.Manifold.cylinder(BASE_WALL + 4, POWER_JACK_HOLE / 2, POWER_JACK_HOLE / 2, 48).rotate(
        (-90, 0, 0)).translate((ax, ay + rb - BASE_WALL - 2, base_bottom + 12))
    screws = [(ax + SCREW_RADIUS * np.cos(a), ay + SCREW_RADIUS * np.sin(a)) for a in np.radians([45, 135, 225, 315])]
    for sx, sy in screws:
        post = m3.Manifold.cylinder(BASE_HEIGHT - BASE_WALL, 4.0, 4.0, 32).translate((sx, sy, base_bottom))
        body += post - m3.Manifold.cylinder(M3_INSERT[1], M3_INSERT[0] / 2, M3_INSERT[0] / 2, 32).translate((sx, sy, base_bottom - 0.01))
    plate = prism(circle(ax, ay, rb), base_bottom - BASE_PLATE, base_bottom)
    for sx, sy in screws:
        plate -= countersunk(M3_CLEAR, M3_HEAD, BASE_PLATE + 2).translate((sx, sy, base_bottom - BASE_PLATE))

    parts = {"column": column, "hatch_cover": cover, "board_pusher": pusher,
             "base_body": body, "base_plate": plate}
    for name, man in parts.items():
        tm = to_trimesh(man)
        tm.export(out / f"{name}.stl")
        e = tm.bounding_box.extents
        print(f"{name}: watertight={tm.is_watertight}, {e[0]:.1f} x {e[1]:.1f} x {e[2]:.1f} mm, {tm.volume / 1000:.1f} cm3")

    # Fit check: board slab and component envelope must sit inside the cavity.
    board = box(xt - BOARD_W / 2, xt + BOARD_W / 2, surf_y, back_y, board_bottom, board_top)
    envelope = box(xt - 10.7, xt + 11.0, surf_y - FRONT_TALLEST, surf_y, board_bottom + 30, board_bottom + 46)
    print(f"interference: board vs column {(board ^ column).volume():.3f} mm3, "
          f"tall-part envelope vs column {(envelope ^ column).volume():.3f} mm3, "
          f"envelope vs cover {(envelope ^ cover).volume():.3f} mm3, cover vs column {(cover ^ column).volume():.3f} mm3")
    print(f"tail S-bend {s_offset:.2f} mm sideways over {abs(s_run):.1f} mm (uses {s_extra:.2f} mm of tail); "
          f"hatch {2 * HATCH_HALF_W:.0f} mm wide, z {hz[0]:.1f}..{hz[1]:.1f}; screws at z {screw_z[0]:.1f}, {screw_z[1]:.1f}")
    # The board slides in from below, so check the whole column against the
    # space it sweeps (board slab + front part heights + back leads), full length.
    zr = (col_bottom - 1, board_top)
    sweep = (
        box(xt - BOARD_W / 2, xt + BOARD_W / 2, surf_y, back_y, *zr)
        + box(xt - 10.73, xt + 11.0, surf_y - FRONT_TALLEST, surf_y, *zr)  # XIAO Sense stack (+ microSD; USB end is in the opening)
        + box(xt - 11.0, xt + 11.0, surf_y - 3.0, surf_y, *zr)  # other parts
        + box(xt - 7.25, xt + 7.25, back_y, back_y + 1.5, *zr)  # wire joints behind
    )
    usb_free = box(xt + rib_x0, xt + r_out + 2, surf_y - USB_DEPTH - 2.5, back_y, *usb_z)
    print(f"pusher vs column (bosses, ribs): {(pusher_placed ^ column).volume():.3f} mm3")
    print(f"board insertion sweep vs column (outside the USB opening): {((sweep - usb_free) ^ column).volume():.3f} mm3")
    band = trimesh.load(OUT / "mobius_surface.stl")
    rest = [trimesh.load(p) for p in sorted((OUT / "frame").glob("frame_segment_0[2-8].stl"))]
    trimesh.util.concatenate([band, to_trimesh(seg1), *rest, to_trimesh(column), to_trimesh(cover), to_trimesh(body), to_trimesh(plate)]
                             ).export(out / "assembly.stl")
    height = np.load(OUT / "mobius_shape.npz")["vertices"][:, 2].max() - (base_bottom - BASE_PLATE)
    print(f"column: outer diameter {2 * r_out:.1f} mm, axis at ({ax:.2f}, {ay:.2f}); board z {board_bottom:.1f}..{board_top:.1f}; "
          f"board pusher {PUSHER_W:.0f} x {pusher_y[1] - pusher_y[0]:.1f} x {pusher_len:.1f} mm; overall height {height:.0f} mm")


if __name__ == "__main__":
    main()
