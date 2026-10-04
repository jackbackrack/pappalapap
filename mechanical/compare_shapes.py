"""Compare the boundary curves of two solved Möbius shapes, ignoring rigid motion.

Usage: mechanical/.venv/bin/python mechanical/compare_shapes.py out/a.npz out/b.npz

The boundary is compared as a set of points (aligned by ICP). Material sliding
along the band costs no energy, so a plain vertex comparison would overstate
how much the shape itself changed.
"""

import sys

import numpy as np
from scipy.interpolate import CubicSpline
from scipy.spatial import cKDTree


def dense(boundary):
    P = np.vstack([boundary, boundary[:1]])
    s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    return CubicSpline(s, P, bc_type="periodic")(np.arange(0, s[-1], 0.5))


def main() -> None:
    A = dense(np.load(sys.argv[1])["boundary"])
    B = dense(np.load(sys.argv[2])["boundary"])
    A -= A.mean(0)
    B -= B.mean(0)
    tree = cKDTree(B)
    for _ in range(60):
        _, idx = tree.query(A)
        M = B[idx]
        H = (A - A.mean(0)).T @ (M - M.mean(0))
        U, _, Vt = np.linalg.svd(H)
        D = np.diag([1, 1, np.sign(np.linalg.det(Vt.T @ U.T))])
        R = Vt.T @ D @ U.T
        A = (A - A.mean(0)) @ R.T + M.mean(0)
    d, _ = tree.query(A)
    d2, _ = cKDTree(A).query(B)
    print(
        f"boundary shape change: max {max(d.max(), d2.max()):.2f} mm, "
        f"rms {np.sqrt((d**2).mean()):.2f} mm"
    )


if __name__ == "__main__":
    main()
