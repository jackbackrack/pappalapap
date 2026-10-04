"""Column top: the round column morphs into a cup that cradles the frame rail.

Built as a signed-distance field (SDF) on a voxel grid and meshed with
marching cubes, so the shape can follow the rail's real path. Near the tail
the rail curves in plan (about +-4 mm over +-20 mm) as well as rising.

  morph(p)  plan-view SDF that blends, with height, from the column circle
            (at z_start) into a band around the rail path's plan projection
            (at z_end), using smoothstep weights so the walls stay vertical
            where they meet the cylinder and where they become the cup.
  core      morph, clipped to stay below the cup's bottom surface. The clip
            follows the rail, so the column's top mirrors the rail's curve.
  cup       a rounded box swept along the rail path (local b/n frame): it
            wraps the rail's back wall and sides up to CUP_TOP.
  F         smooth-min(core, cup): the fillet between column and cup. Then
            the rail cavity (+ clearance) and a hollow interior are removed.

The rail sits in the cup and is glued. The flex tail passes through a slot.
"""

import numpy as np
from scipy.spatial import cKDTree
from skimage.measure import marching_cubes

import frame


def smoothstep(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def smin(a, b, k):
    """Polynomial smooth minimum (fillet radius about k)."""
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b * (1 - h) + a * h - k * h * (1 - h)


def build(*, ax, ay, r_out, wall, z_start, z_end, s_center, half_len, shell, cup_top, fillet,
          clearance, tail_slot, voxel=0.35):
    """Return (vertices, faces) of the column top, from z_start - 2 up to the cup's rim."""
    sp, bp, total, *_ = frame.boundary_frames()
    # Dense rail path around the tail (extended so the end caps are rounded by the band ends).
    ts = np.arange(s_center - half_len - 15, s_center + half_len + 15, 0.25)
    P, B, N = frame.frame_at(sp, bp, ts)
    T = sp(ts, 1)
    T /= np.linalg.norm(T, axis=1)[:, None]
    in_cup = np.abs(ts - s_center) <= half_len
    tree3 = cKDTree(P)
    tree2 = cKDTree(P[in_cup][:, :2])
    n_half = frame.THICK / 2 + shell
    back = frame.BACK

    pad = 4.0
    lo = np.array([ax - r_out - pad, ay - r_out - pad, z_start - 2.0])
    hi = np.array([max(ax + r_out, P[in_cup, 0].max() + n_half) + pad,
                   max(ay + r_out, P[in_cup, 1].max() + n_half) + pad,
                   P[in_cup, 2].max() + cup_top + 3.0])
    lo[0] = min(lo[0], P[in_cup, 0].min() - n_half - pad)
    lo[1] = min(lo[1], P[in_cup, 1].min() - n_half - pad)
    shape = np.ceil((hi - lo) / voxel).astype(int) + 1
    gx, gy, gz = (lo[i] + voxel * np.arange(shape[i]) for i in range(3))
    X, Y, Z = np.meshgrid(gx, gy, gz, indexing="ij")
    pts = np.stack([X.ravel(), Y.ravel(), Z.ravel()], axis=1)

    # Plan morph: circle -> band around the rail path.
    d_circle = np.hypot(pts[:, 0] - ax, pts[:, 1] - ay) - r_out
    d_band = tree2.query(pts[:, :2])[0] - n_half
    w = smoothstep((pts[:, 2] - z_start) / (z_end - z_start))
    morph = (1 - w) * d_circle + w * d_band

    # Local rail frame at the nearest path sample.
    idx = tree3.query(pts)[1]
    rel = pts - P[idx]
    b = np.einsum("ij,ij->i", rel, B[idx])
    n = np.einsum("ij,ij->i", rel, N[idx])
    t = np.abs(ts[idx] - s_center) - half_len  # > 0 beyond the cup's ends

    cup_bottom = -back - shell
    core = np.maximum(morph, b - (cup_bottom + 0.5))  # stays under the cup's bottom surface
    # Cup: rounded box in (b, n), limited along the rail with rounded ends.
    r = 1.5
    qb = np.abs(b - (cup_bottom + cup_top) / 2) - ((cup_top - cup_bottom) / 2 - r)
    qn = np.abs(n) - (n_half - r)
    qt = t
    q = np.stack([qb, qn, qt], axis=1)
    cup = np.linalg.norm(np.maximum(q, 0), axis=1) + np.minimum(q.max(axis=1), 0) - r
    F = smin(core, cup, fillet)
    # Rail cavity with clearance, open upward.
    rail = np.maximum(np.maximum(-(b - (-back - clearance)), np.abs(n) - (frame.THICK / 2 + clearance)), t - 12.0)
    F = np.maximum(F, -rail)
    # Hollow interior (shrunken morph, kept under the cup bottom).
    hollow = np.maximum(morph + wall, b - (cup_bottom - wall))
    F = np.maximum(F, -hollow)
    # Tail slot straight down through the cup bottom.
    tw, th = tail_slot
    slot = np.maximum(np.abs(pts[:, 0] - ax) - tw / 2, np.abs(pts[:, 1] - ay) - th / 2)
    F = np.maximum(F, -np.maximum(slot, b - 0.5))
    # Cut the field flat at the bottom so it joins the cylinder below.
    F = np.maximum(F, -(pts[:, 2] - (z_start - 1.0)))

    vol = F.reshape(shape)
    verts, faces, _, _ = marching_cubes(vol, level=0.0, spacing=(voxel, voxel, voxel))
    verts += lo
    # Keep the one real body (marching cubes also leaves zero-area slivers).
    import trimesh

    mesh = trimesh.Trimesh(verts, faces)
    mesh.merge_vertices()
    body = max(mesh.split(only_watertight=True), key=lambda b: abs(b.volume))
    if body.volume < 0:
        body.invert()
    return np.asarray(body.vertices), np.asarray(body.faces)
