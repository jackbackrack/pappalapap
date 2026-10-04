"""3D-printable edge rail that holds a strip in the computed Möbius shape.

A Möbius band has a single boundary curve, which goes round the loop twice. The
frame is one slotted rail swept along that curve (from out/mobius_shape.npz), so
the strip's edge sits in the slot and the band is forced into its natural
developable shape. The rail is cut into printable segments. A 1.75 mm filament
offcut slides through a channel running the whole length of the rail and pins
neighbouring segments together. The rail is a closed loop. Where the
connector tail leaves the strip, a window cut through the rail's back wall
(slot height only) lets the tail out without breaking the loop.

Profile, in the plane normal to the edge (b = into the strip, n = strip normal), mm:
  body b in [-BACK, LIP], n in [-THICK/2, THICK/2]
  slot b in [-SLOT_EXTRA, LIP], n in [-SLOT/2, SLOT/2]   (strip edge sits at b = 0)
  pin channel: circle at (b = -BACK/2 - SLOT_EXTRA/2, n = 0), diameter PIN_D

Writes out/frame_segment_XX.stl, out/frame_all.stl, out/mobius_surface.stl.
Run: mechanical/.venv/bin/python mechanical/frame.py
"""

from pathlib import Path

import mapbox_earcut as earcut
import numpy as np
import trimesh
from scipy.interpolate import CubicSpline

from geometry import HEIGHT, LOOP, TAIL_OFFSET, TAIL_WIDTH

OUT = Path(__file__).parent / "out"

LIP = 2.5  # how far the rail covers the strip face (at 10 mm pitch LED bodies start 3.9 mm in)
BACK = 4.0  # rail material behind the strip edge
THICK = 5.0
SLOT = 1.0  # paper 0.1, flex 0.2, lap joint up to ~0.6
SLOT_EXTRA = 0.5  # slot clearance beyond the strip edge
PIN_D = 1.95  # for a 1.75 mm filament pin
SEGMENTS = 8
STEP = 1.0  # sweep resolution along the rail, mm
TAIL_CLEARANCE = 3.0  # extra gap on each side of the connector tail


def profile():
    s = SLOT / 2
    outer = np.array(
        [
            (-BACK, -THICK / 2),
            (LIP, -THICK / 2),
            (LIP, -s),
            (-SLOT_EXTRA, -s),
            (-SLOT_EXTRA, s),
            (LIP, s),
            (LIP, THICK / 2),
            (-BACK, THICK / 2),
        ]
    )
    k = 16
    a = np.linspace(0, 2 * np.pi, k, endpoint=False)
    pc = (-(BACK + SLOT_EXTRA) / 2, 0.0)
    hole = np.stack([pc[0] + PIN_D / 2 * np.cos(-a), pc[1] + PIN_D / 2 * np.sin(-a)], axis=1)
    return outer, hole  # outer CCW, hole CW


def boundary_frames():
    d = np.load(OUT / "mobius_shape.npz")
    X, nu, nv = d["vertices"], int(d["nu"]), int(d["nv"])

    def vid(i, j):
        return (i - nu) * nv + (nv - 1 - j) if i >= nu else i * nv + j

    # One closed boundary: the j = 0 edge then the j = nv - 1 edge.
    edge = [vid(i, 0) for i in range(nu)] + [vid(i, nv - 1) for i in range(nu)]
    inner = [vid(i, 1) for i in range(nu)] + [vid(i, nv - 2) for i in range(nu)]
    # Chart u for each boundary sample, and whether it is on the v = -H/2 edge.
    u = np.concatenate([np.arange(nu) * LOOP / nu] * 2)
    low_edge = np.array([True] * nu + [False] * nu)
    P = X[edge]
    B = X[inner] - X[edge]
    seg = np.linalg.norm(np.diff(np.vstack([P, P[:1]]), axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    total = s[-1]
    sp = CubicSpline(s, np.vstack([P, P[:1]]), bc_type="periodic")
    bp = CubicSpline(s, np.vstack([B, B[:1]]), bc_type="periodic")
    return sp, bp, total, s[:-1], u, low_edge


def frame_at(sp, bp, t):
    p = sp(t)
    tan = sp(t, 1)
    tan /= np.linalg.norm(tan, axis=-1, keepdims=True)
    b = bp(t)
    b = b - np.sum(b * tan, axis=-1, keepdims=True) * tan
    b /= np.linalg.norm(b, axis=-1, keepdims=True)
    n = np.cross(tan, b)
    return p, b, n


def sweep(sp, bp, t0, t1, outer=None, hole=None):
    """Sweep a profile (outer CCW loop, optional CW hole) along the rail from t0 to t1."""
    if outer is None:
        outer, hole = profile()
    loops = (outer,) if hole is None else (outer, hole)
    ts = np.linspace(t0, t1, max(2, int(np.ceil((t1 - t0) / STEP)) + 1))
    p, b, n = frame_at(sp, bp, ts)
    rings = []
    for loop in loops:
        rings.append(
            p[:, None, :] + loop[None, :, 0, None] * b[:, None, :] + loop[None, :, 1, None] * n[:, None, :]
        )
    verts, faces = [], []
    off = 0
    for R in rings:
        m, k, _ = R.shape
        verts.append(R.reshape(-1, 3))
        for i in range(m - 1):
            for j in range(k):
                a, c = off + i * k + j, off + i * k + (j + 1) % k
                a2, c2 = a + k, c + k
                faces += [(a, c, c2), (a, c2, a2)]
        off += m * k
    # End caps: polygon with hole, triangulated in profile coordinates.
    no = len(outer)
    nh = 0 if hole is None else len(hole)
    m = len(ts)
    poly = np.vstack(loops).astype(np.float64)
    tri = earcut.triangulate_float64(poly, np.array([no, no + nh], dtype=np.uint32)[: len(loops)]).reshape(-1, 3)

    def cap_index(ring_pos, idx):
        if idx < no:
            return ring_pos * no + idx
        return m * no + ring_pos * nh + (idx - no)

    for a, b2, c in tri:
        faces.append((cap_index(0, c), cap_index(0, b2), cap_index(0, a)))
        faces.append((cap_index(m - 1, a), cap_index(m - 1, b2), cap_index(m - 1, c)))
    mesh = trimesh.Trimesh(np.vstack(verts), np.array(faces), process=True)
    mesh.fix_normals()
    return mesh


def tail_window(sp, bp, t0, t1):
    """Cutter that opens the slot through the rail's back wall between t0 and t1,
    so the flex tail can leave in the strip's plane. Material above and below
    the slot stays continuous, so the rail stays a closed, rigid loop."""
    s = SLOT / 2
    rect = np.array([(-BACK - 1.0, -s), (0.0, -s), (0.0, s), (-BACK - 1.0, s)])
    return sweep(sp, bp, t0, t1, outer=rect)


def main() -> None:
    out = OUT / "frame"
    out.mkdir(exist_ok=True)
    sp, bp, total, s, u, low_edge = boundary_frames()
    # Tail window: on the v = -H/2 edge around u = TAIL_OFFSET.
    half = TAIL_WIDTH / 2 + TAIL_CLEARANCE
    in_win = low_edge & (np.abs(u - TAIL_OFFSET) < half)
    ws = s[in_win]
    win0, win1 = ws.min() - STEP, ws.max() + STEP
    # Segment 1 is centred on the window so no pinned joint falls inside it.
    seg_len = total / SEGMENTS
    start = (win0 + win1) / 2 - seg_len / 2
    cuts = start + seg_len * np.arange(SEGMENTS + 1)
    parts = []
    for k in range(SEGMENTS):
        part = sweep(sp, bp, cuts[k], cuts[k + 1])
        if k == 0:
            cutter = tail_window(sp, bp, win0, win1)
            part = trimesh.boolean.difference([part, cutter], engine="manifold")
        name = out / f"frame_segment_{k + 1:02d}.stl"
        part.export(name)
        ext = part.bounding_box_oriented.primitive.extents
        print(
            f"segment {k + 1}: {cuts[k + 1] - cuts[k]:.0f} mm along rail, watertight={part.is_watertight}, "
            f"oriented bbox {ext[0]:.0f} x {ext[1]:.0f} x {ext[2]:.0f} mm"
            + (f", tail window {win1 - win0:.1f} mm" if k == 0 else "")
        )
        parts.append(part)
    trimesh.util.concatenate(parts).export(out / "frame_all.stl")
    d = np.load(OUT / "mobius_shape.npz")
    trimesh.Trimesh(d["vertices"], d["faces"]).export(OUT / "mobius_surface.stl")
    print(f"boundary length {total:.1f} mm -> {out}")


if __name__ == "__main__":
    main()


def clearance_report() -> None:
    """Smallest distance between rail stretches that are far apart along the rail."""
    from scipy.spatial import cKDTree

    sp, _, total, _, _, _ = boundary_frames()
    t = np.arange(0, total, 1.0)
    P = sp(t)
    tree = cKDTree(P)
    best = (np.inf, 0, 0)
    for i, j in tree.query_pairs(r=40.0):
        arc = abs(t[i] - t[j])
        arc = min(arc, total - arc)
        if arc > 60.0:
            dist = float(np.linalg.norm(P[i] - P[j]))
            if dist < best[0]:
                best = (dist, t[i], t[j])
    print(
        f"closest approach of distant rail stretches: {best[0]:.1f} mm "
        f"(at {best[1]:.0f} and {best[2]:.0f} mm along the rail); "
        f"rail half-size ~{max(BACK, LIP) + THICK / 2:.1f} mm"
    )


if __name__ == "__main__" and "--clearance" in __import__("sys").argv:
    clearance_report()
