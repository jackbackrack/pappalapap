"""Place the connector tail at the bottom of the sculpture, exiting straight down.

Two free choices don't change the solved shape:
  * rotating the whole band in space;
  * sliding the material around the band (rolling). For a uniform strip this
    costs no energy, and on the solver's grid a shift by whole cells is an exact
    symmetry, because crossing the seam flips v.

For every point on the boundary this rotates the band so the strip's outward
edge direction there points straight down (-z), and measures how far that point
sits above the lowest point of the band. The best point becomes the tail
location: the material is rolled so the tail lands there, and the band is
rotated and translated so the tail exit is at z = 0 pointing down.

Reads and rewrites out/mobius_shape.npz (it keeps the unoriented solve in
out/mobius_shape_solved.npz). Run after mobius_shape.py, before frame.py.
"""

import os
from pathlib import Path

import numpy as np

from geometry import LOOP, TAIL_OFFSET

OUT = Path(__file__).parent / "out"
# Placement mode: balance the band on a column (centre of mass above the tail),
# or the older "tail at the lowest point" mode (MOBIUS_ORIENT=lowest).
BALANCE = os.environ.get("MOBIUS_ORIENT", "balance") == "balance"


def rotation_to(a, b):
    """Smallest rotation taking unit vector a to unit vector b."""
    v = np.cross(a, b)
    c = float(np.dot(a, b))
    if c < -1 + 1e-9:  # opposite: rotate pi about any axis perpendicular to a
        axis = np.cross(a, [1.0, 0, 0])
        if np.linalg.norm(axis) < 1e-6:
            axis = np.cross(a, [0, 1.0, 0])
        axis /= np.linalg.norm(axis)
        return 2 * np.outer(axis, axis) - np.eye(3)
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + vx + vx @ vx / (1 + c)


def orient(d: dict, loop: float = LOOP) -> tuple[dict, float, int, int]:
    """Return a copy of solve `d` rolled and rotated so the tail exits straight
    down at z = 0, plus (lift, chosen sample, roll shift). `loop` is the band's
    loop length (it differs between pitch studies)."""
    d = dict(d)
    X, nu, nv = d["vertices"], int(d["nu"]), int(d["nv"])

    def vid(i, j):
        i %= 2 * nu
        return (i - nu) * nv + (nv - 1 - j) if i >= nu else i * nv + j

    # Boundary sample k (0 .. 2nu-1): edge vertex and its inward neighbour.
    edge = np.array([vid(k, 0) for k in range(2 * nu)])
    inner = np.array([vid(k, 1) for k in range(2 * nu)])
    best = None
    for k in range(2 * nu):
        q = X[edge[k]]
        nxt, prv = X[edge[(k + 1) % (2 * nu)]], X[edge[k - 1]]
        t = nxt - prv
        t /= np.linalg.norm(t)
        o = q - X[inner[k]]  # outward, in the strip's plane
        o -= np.dot(o, t) * t
        o /= np.linalg.norm(o)
        R = rotation_to(o, np.array([0, 0, -1.0]))
        z = (X - q) @ R.T
        lift = -z[:, 2].min()  # how far other parts of the band hang below q
        if best is None or lift < best[0]:
            best = (lift, k, R)
    if BALANCE:
        # Balance on a column: among the samples where nothing hangs below the
        # tail (lift ~ 0), pick the one whose outward edge direction points
        # most nearly away from the centre of mass, so the centre of mass sits
        # right above the tail.
        F = d["faces"]
        area = 0.5 * np.linalg.norm(np.cross(X[F[:, 1]] - X[F[:, 0]], X[F[:, 2]] - X[F[:, 0]]), axis=1)
        com = (X[F].mean(1) * area[:, None]).sum(0) / area.sum()
        cands = []
        for k in range(2 * nu):
            q = X[edge[k]]
            t = X[edge[(k + 1) % (2 * nu)]] - X[edge[k - 1]]
            t /= np.linalg.norm(t)
            o = q - X[inner[k]]
            o -= np.dot(o, t) * t
            o /= np.linalg.norm(o)
            g = (q - com) / np.linalg.norm(q - com)
            R = rotation_to(o, np.array([0, 0, -1.0]))
            lift = -((X - q) @ R.T)[:, 2].min()
            if lift < 0.5:
                cands.append((float(np.degrees(np.arccos(np.clip(np.dot(o, g), -1, 1)))), k, R, lift))
        tilt, k_best, R, lift = min(cands, key=lambda c: c[0])
        print(f"balance point: sample {k_best}, centre of mass {tilt:.1f} deg off the column axis")
    else:
        lift, k_best, R = best
    # Roll the material so the tail (low edge, u = TAIL_OFFSET) lands on sample k_best.
    du = loop / nu
    k_tail = int(round(TAIL_OFFSET / du))
    shift = (k_best - k_tail) % (2 * nu)
    Xr = np.array([X[vid(i + shift, j)] for i in range(nu) for j in range(nv)])
    q = Xr[vid(k_tail, 0)]
    Xo = (Xr - q) @ R.T
    # Yaw about the vertical so the strip's +x direction at the tail is world +x
    # (the board and column are then axis-aligned).
    du = Xo[vid(k_tail + 1, 0)] - Xo[vid(k_tail - 1, 0)]
    yaw = -np.arctan2(du[1], du[0])
    Rz = np.array([[np.cos(yaw), -np.sin(yaw), 0], [np.sin(yaw), np.cos(yaw), 0], [0, 0, 1.0]])
    Xo = Xo @ Rz.T
    d["vertices"] = Xo
    lo = [vid(i, 0) for i in range(nu)]
    hi = [vid(i, nv - 1) for i in range(nu)]
    d["boundary"] = np.concatenate([Xo[lo], Xo[hi]])
    return d, lift, k_best, shift


def main() -> None:
    src = OUT / "mobius_shape.npz"
    d = dict(np.load(src))
    np.savez(OUT / "mobius_shape_solved.npz", **d)
    d, lift, k_best, shift = orient(d)
    Xo = d["vertices"]
    np.savez(src, **d)
    print(
        f"tail placed at boundary sample {k_best} (rolled {shift} cells); "
        f"lowest other point of the band is {lift:.2f} mm below the tail exit; "
        f"sculpture height {Xo[:, 2].max() - Xo[:, 2].min():.1f} mm"
    )


if __name__ == "__main__":
    main()
