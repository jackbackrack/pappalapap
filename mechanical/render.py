"""Preview renders of the solved Möbius band, its LEDs and the edge rail.

Writes out/mobius_views.png. Run after mobius_shape.py and frame.py.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import trimesh  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402

from geometry import (  # noqa: E402
    BOTTOM_COLUMNS,
    HEIGHT,
    LOOP,
    ROWS,
    TOP_COLUMNS,
    led_x,
    led_y,
)
from paper_template import lit  # noqa: E402

OUT = Path(__file__).parent / "out"


def surface_point(X, nu, nv, u, v):
    """Bilinear lookup of chart (u, v) on the solved grid, with the Möbius wrap."""
    du = LOOP / nu
    dv = HEIGHT / (nv - 1)
    fi, fj = u / du, (v + HEIGHT / 2) / dv
    i0, j0 = int(np.floor(fi)), min(int(np.floor(fj)), nv - 2)
    a, b = fi - i0, fj - j0

    def vid(i, j):
        i %= 2 * nu
        return (i - nu) * nv + (nv - 1 - j) if i >= nu else i * nv + j

    p00, p10 = X[vid(i0, j0)], X[vid(i0 + 1, j0)]
    p01, p11 = X[vid(i0, j0 + 1)], X[vid(i0 + 1, j0 + 1)]
    p = (1 - a) * (1 - b) * p00 + a * (1 - b) * p10 + (1 - a) * b * p01 + a * b * p11
    n = np.cross(p10 - p00, p01 - p00)
    return p, n / np.linalg.norm(n)


def leds(X, nu, nv):
    pts = []
    for face, cols in (("top", TOP_COLUMNS), ("bottom", BOTTOM_COLUMNS)):
        for c in cols:
            for r in range(ROWS):
                x, v = led_x(c), led_y(r) - HEIGHT / 2
                if x >= LOOP:  # bottom col 39 sits in end B's lap, i.e. at the start, flipped
                    x, v = x - LOOP, -v
                    face_here = "top"  # B's bottom face lies on the chart's top side there
                else:
                    face_here = face
                p, n = surface_point(X, nu, nv, x, v)
                side = 1.0 if face_here == "top" else -1.0
                pts.append((p + side * 0.8 * n, lit(face, c, r)))
    return pts


def main() -> None:
    d = np.load(OUT / "mobius_shape.npz")
    X, F, nu, nv = d["vertices"], d["faces"], int(d["nu"]), int(d["nv"])
    rail = trimesh.load(OUT / "frame" / "frame_all.stl")
    pts = leds(X, nu, nv)
    P = np.array([p for p, _ in pts])
    on = np.array([o for _, o in pts])
    views = [(25, 30, "perspective"), (90, -90, "top view"), (0, -90, "side view")]
    fig = plt.figure(figsize=(18, 6.5))
    for k, (elev, azim, title) in enumerate(views):
        ax = fig.add_subplot(1, 3, k + 1, projection="3d")
        ax.add_collection3d(
            Poly3DCollection(X[F], facecolor="#f2efe6", edgecolor="none", alpha=0.85)
        )
        ax.add_collection3d(
            Poly3DCollection(
                rail.vertices[rail.faces][::3], facecolor="#4a6fa5", edgecolor="none", alpha=0.9
            )
        )
        ax.scatter(*P[~on].T, s=2, c="#bbbbbb", depthshade=False)
        ax.scatter(*P[on].T, s=6, c="#e8461e", depthshade=False)
        lim = np.abs(X).max() + 8
        ax.set_xlim(-lim, lim)
        ax.set_ylim(-lim, lim)
        ax.set_zlim(-lim, lim)
        ax.set_box_aspect((1, 1, 1))
        ax.view_init(elev=elev, azim=azim)
        ax.set_title(title)
        ax.set_xlabel("mm")
    fig.tight_layout()
    fig.savefig(OUT / "mobius_views.png", dpi=110)
    print("wrote", OUT / "mobius_views.png")


if __name__ == "__main__":
    main()
