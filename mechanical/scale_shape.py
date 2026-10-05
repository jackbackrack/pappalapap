"""Scale a solved Möbius shape to a new pitch.

An inextensible elastic strip's equilibrium shape depends only on its aspect
ratio (length / width): the bending energy is scale-invariant. So a strip with
the same column count and rows at a different pitch takes the same shape,
scaled uniformly, and no re-solve is needed.

Usage: mechanical/.venv/bin/python mechanical/scale_shape.py SRC.npz DST.npz FACTOR
e.g.   ... data/mobius_shape_10mm.npz data/mobius_shape_9p1mm.npz 0.91
"""

import sys

import numpy as np


def main() -> None:
    src, dst, factor = sys.argv[1], sys.argv[2], float(sys.argv[3])
    d = dict(np.load(src))
    for key in ("vertices", "chart", "boundary"):
        if key in d:
            d[key] = d[key] * factor
    np.savez(dst, **d)
    print(f"scaled {src} by {factor} -> {dst}")


if __name__ == "__main__":
    main()
