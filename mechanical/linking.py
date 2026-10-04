"""Topology check for a solved band: Gauss linking number of the centre line with the boundary.

A true Möbius band (one half-twist) gives |Lk| = 1; a band with three
half-twists (trefoil-shaped edge) gives 3. Since the solver has no self-contact
term, a different number means the band passed through itself.

Usage: mechanical/.venv/bin/python mechanical/linking.py out/mobius_shape_X.npz [...]
"""

import sys

import numpy as np


def curves(path):
    d = np.load(path)
    X, nu, nv = d["vertices"], int(d["nu"]), int(d["nv"])

    def vid(i, j):
        return (i - nu) * nv + (nv - 1 - j) if i >= nu else i * nv + j

    jm = [(nv - 1) // 2, nv // 2]
    centre = np.array([0.5 * (X[vid(i, jm[0])] + X[vid(i, jm[1])]) for i in range(nu)])
    edge = np.array([X[vid(i, 0)] for i in range(2 * nu)])
    return centre, edge


def linking(a, b):
    """Discrete Gauss linking integral of two closed polylines."""
    da = np.roll(a, -1, 0) - a
    db = np.roll(b, -1, 0) - b
    ma = a + 0.5 * da
    mb = b + 0.5 * db
    r = ma[:, None, :] - mb[None, :, :]
    cr = np.cross(da[:, None, :], db[None, :, :])
    num = np.sum(cr * r, axis=2)
    return float(np.sum(num / np.linalg.norm(r, axis=2) ** 3) / (4 * np.pi))


if __name__ == "__main__":
    for p in sys.argv[1:]:
        c, e = curves(p)
        print(f"{p}: linking number {linking(c, e):+.2f}")
