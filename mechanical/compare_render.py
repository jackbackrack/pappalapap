"""Side-by-side renders of several solved bands, each oriented tail-down.

Usage: mechanical/.venv/bin/python mechanical/compare_render.py name=out/a.npz[:pitch] ...
(pitch, default 12.25 mm, sets the loop length for placing the tail)
Writes out/variants.png.
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402

from linking import curves, linking  # noqa: E402
from orient import orient  # noqa: E402

OUT = Path(__file__).parent / "out"


def main() -> None:
    items = [a.split("=", 1) for a in sys.argv[1:]]
    views = [(20, 35), (90, -90), (0, -90)]
    fig = plt.figure(figsize=(4.2 * len(views), 4.0 * len(items)))
    light = np.array([0.3, -0.4, 0.85])
    light /= np.linalg.norm(light)
    for r, (name, spec) in enumerate(items):
        path, _, pitch = spec.partition(":")
        p = float(pitch or 12.25)
        loop = round(490.0 / p) * p - p
        d, _, _, _ = orient(dict(np.load(path)), loop)
        X, F = d["vertices"], d["faces"]
        c, e = curves(path)
        lk = linking(c, e)
        N = np.cross(X[F[:, 1]] - X[F[:, 0]], X[F[:, 2]] - X[F[:, 0]])
        N /= np.linalg.norm(N, axis=1)[:, None]
        shade = 0.35 + 0.65 * np.abs(N @ light)
        cols = plt.cm.YlOrBr(0.15 + 0.35 * shade)
        ctr = 0.5 * (X.max(0) + X.min(0))
        R = 0.5 * (X.max(0) - X.min(0)).max() + 5
        for k, (el, az) in enumerate(views):
            ax = fig.add_subplot(len(items), len(views), r * len(views) + k + 1, projection="3d")
            ax.add_collection3d(Poly3DCollection(X[F], facecolors=cols, edgecolor="none"))
            ax.set_xlim(ctr[0] - R, ctr[0] + R)
            ax.set_ylim(ctr[1] - R, ctr[1] + R)
            ax.set_zlim(ctr[2] - R, ctr[2] + R)
            ax.set_box_aspect((1, 1, 1))
            ax.view_init(el, az)
            ax.axis("off")
            if k == 0:
                size = X.max(0) - X.min(0)
                ax.set_title(
                    f"{name}\n{size[0]:.0f} x {size[1]:.0f} x {size[2]:.0f} mm (h), Lk {lk:+.0f}",
                    fontsize=10,
                )
    fig.tight_layout()
    fig.savefig(OUT / "variants.png", dpi=80)
    print("wrote", OUT / "variants.png")


if __name__ == "__main__":
    main()
