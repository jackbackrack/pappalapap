"""Equilibrium shape of an inextensible strip closed into a Möbius band.

A flat strip of loop length LOOP and width HEIGHT is meshed in its flat chart
(u along the strip, v across it). The ends are identified with a half-twist,
(LOOP, v) ~ (0, -v). The 3D shape minimises a discrete-shell energy: very stiff
edge springs (the strip must not stretch) plus a hinge bending energy. The
start is the textbook parametric Möbius band, which stretches the edges. Raising
the stretch stiffness in steps relaxes it into a developable band, the shape
paper or polyimide flex takes on its own.

Writes out/mobius_shape.npz: vertices, faces, the (u, v) chart and the
boundary polyline.
Run: mechanical/.venv/bin/python mechanical/mobius_shape.py
"""

import os
from pathlib import Path

import autograd.numpy as anp
import numpy as np
from autograd import hessian_vector_product, value_and_grad
from scipy.optimize import minimize

from geometry import HEIGHT, LOOP

OUT = Path(__file__).parent / "out"
# Mesh size; MOBIUS_NU / MOBIUS_NV override it (e.g. a coarse pre-solve).
# MOBIUS_TAG suffixes every output file so parallel runs don't collide.
NU = int(os.environ.get("MOBIUS_NU", 192))  # ~2.5 mm along
NV = int(os.environ.get("MOBIUS_NV", round(HEIGHT / 4.4) + 1))  # ~4.4 mm across
TAG = os.environ.get("MOBIUS_TAG", "")
# Optional shape preferences (0 = off, the natural elastic band):
#   MOBIUS_SYM=k     k-fold rotational symmetry about z (k odd, NU divisible by k):
#                    X(u + L/k, v) = Rz(360/k) X(u, -v)
#   MOBIUS_ROUND=w   pull the centre line toward a flat circle, weight w per mm^2
SYM = int(os.environ.get("MOBIUS_SYM", 0))
ROUND = float(os.environ.get("MOBIUS_ROUND", 0.0))
SYM_WEIGHT = 1.0


def out_file(stem: str) -> Path:
    return OUT / f"{stem}{TAG}.npz"


def vid(i: int, j: int) -> int:
    """Vertex index with the Möbius wrap: u index i past the end flips v."""
    if i >= NU:
        return (i - NU) * NV + (NV - 1 - j)
    return i * NV + j


def build_mesh():
    us = np.arange(NU) * (LOOP / NU)
    vs = np.linspace(-HEIGHT / 2, HEIGHT / 2, NV)
    chart = np.array([(u, v) for u in us for v in vs])
    faces, face_chart = [], []
    for i in range(NU):
        for j in range(NV - 1):
            a, b = vid(i, j), vid(i + 1, j)
            c, d = vid(i + 1, j + 1), vid(i, j + 1)
            # Chart coordinates of this quad's corners. At the wrap, u = LOOP
            # and v is taken unflipped, so the quad is a flat rectangle.
            pa = (us[i], vs[j])
            pb = ((i + 1) * LOOP / NU, vs[j])
            pc = ((i + 1) * LOOP / NU, vs[j + 1])
            pd = (us[i], vs[j + 1])
            if (i + j) % 2 == 0:
                tris = (((a, b, c), (pa, pb, pc)), ((a, c, d), (pa, pc, pd)))
            else:
                tris = (((a, b, d), (pa, pb, pd)), ((b, c, d), (pb, pc, pd)))
            for t, p in tris:
                faces.append(t)
                face_chart.append(p)
    faces = np.array(faces)
    face_chart = np.array(face_chart)
    # Unique edges with rest lengths, and hinges (edge shared by two faces).
    edge_faces: dict[tuple[int, int], list[tuple[int, int]]] = {}
    rest: dict[tuple[int, int], float] = {}
    for f, (t, p) in enumerate(zip(faces, face_chart)):
        for k in range(3):
            i0, i1 = t[k], t[(k + 1) % 3]
            key = (min(i0, i1), max(i0, i1))
            rest[key] = float(np.linalg.norm(p[k] - p[(k + 1) % 3]))
            edge_faces.setdefault(key, []).append((f, (k + 2) % 3))
    edges = np.array(list(rest.keys()))
    rest_len = np.array(list(rest.values()))
    hinges = []
    for (i0, i1), fl in edge_faces.items():
        if len(fl) == 2:
            (f0, k0), (f1, k1) = fl
            hinges.append((i0, i1, faces[f0][k0], faces[f1][k1]))
    hinges = np.array(hinges)
    return chart, faces, edges, rest_len, hinges


def hinge_angles(X, hinges):
    """Dihedral angle (degrees) at every interior edge; 0 = flat."""
    a, b, c, d = (X[h] for h in hinges.T)
    e = b - a
    n1 = np.cross(e, c - a)
    n2 = np.cross(d - a, e)
    cos_t = np.sum(n1 * n2, axis=1) / (np.linalg.norm(n1, axis=1) * np.linalg.norm(n2, axis=1))
    return np.degrees(np.arccos(np.clip(cos_t, -1.0, 1.0)))


def resample(Xc, nu_c, nv_c, chart):
    """Bilinear lookup of chart (u, v) points on another solve's grid, with the Möbius wrap."""

    def cvid(i, j):
        i = i % (2 * nu_c)
        return np.where(i >= nu_c, (i - nu_c) * nv_c + (nv_c - 1 - j), i * nv_c + j)

    fi = chart[:, 0] / (LOOP / nu_c)
    fj = (chart[:, 1] + HEIGHT / 2) / (HEIGHT / (nv_c - 1))
    i0 = np.floor(fi).astype(int)
    j0 = np.minimum(np.floor(fj).astype(int), nv_c - 2)
    a, b = (fi - i0)[:, None], (fj - j0)[:, None]
    return (
        (1 - a) * (1 - b) * Xc[cvid(i0, j0)] + a * (1 - b) * Xc[cvid(i0 + 1, j0)]
        + (1 - a) * b * Xc[cvid(i0, j0 + 1)] + a * b * Xc[cvid(i0 + 1, j0 + 1)]
    )


def initial_guess(chart):
    R = LOOP / (2 * np.pi)
    phi = 2 * np.pi * chart[:, 0] / LOOP
    v = chart[:, 1]
    return np.stack(
        [
            (R + v * np.cos(phi / 2)) * np.cos(phi),
            (R + v * np.cos(phi / 2)) * np.sin(phi),
            v * np.sin(phi / 2),
        ],
        axis=1,
    )


def make_energy(edges, rest_len, hinges, ks):
    e0, e1 = edges[:, 0], edges[:, 1]
    h0, h1, h2, h3 = hinges.T
    if SYM:
        assert SYM % 2 == 1 and NU % SYM == 0, "need odd k dividing NU"
        src = np.array([vid(i, j) for i in range(NU) for j in range(NV)])
        dst = np.array([vid(i + NU // SYM, NV - 1 - j) for i in range(NU) for j in range(NV)])
        ang = 2 * np.pi / SYM
        Rz = np.array([[np.cos(ang), -np.sin(ang), 0], [np.sin(ang), np.cos(ang), 0], [0, 0, 1]])
    if ROUND:
        # Centre line: middle row, or the mean of the two middle rows.
        jm = [(NV - 1) // 2, NV // 2]
        mid = [np.array([vid(i, j) for i in range(NU)]) for j in jm]

    def energy(x):
        X = anp.reshape(x, (-1, 3))
        d = X[e1] - X[e0]
        ln = anp.sqrt(anp.sum(d * d, axis=1))
        stretch = anp.sum((ln - rest_len) ** 2 / rest_len)
        a, b, c, dd = X[h0], X[h1], X[h2], X[h3]
        e = b - a
        n1 = anp.cross(e, c - a)
        n2 = anp.cross(dd - a, e)
        a1 = anp.sqrt(anp.sum(n1 * n1, axis=1))
        a2 = anp.sqrt(anp.sum(n2 * n2, axis=1))
        # Hinge bending 2(1 - cos θ) ≈ θ² for small θ, and it keeps rising to
        # a maximum at a 180° fold. (An earlier sin²θ form fell back to zero
        # at 180°, which let the solver crease the sheet for free.) The
        # n1/n2 construction measures the geometric dihedral angle whatever
        # the face winding, so the Möbius seam needs no special case.
        cos_t = anp.sum(n1 * n2, axis=1) / (a1 * a2)
        el2 = anp.sum(e * e, axis=1)
        bend = anp.sum(2.0 * (1.0 - cos_t) * el2 / (0.5 * (a1 + a2)))
        total = ks * stretch + bend
        if SYM:
            d = X[dst] - anp.dot(X[src], Rz.T)
            total = total + SYM_WEIGHT * anp.sum(d * d)
        if ROUND:
            c = 0.5 * (X[mid[0]] + X[mid[1]])
            c = c - anp.mean(c, axis=0)
            rho = anp.sqrt(c[:, 0] ** 2 + c[:, 1] ** 2)
            total = total + ROUND * (anp.sum((rho - anp.mean(rho)) ** 2) + anp.sum(c[:, 2] ** 2))
        return total

    return value_and_grad(energy), hessian_vector_product(energy)


def main() -> None:
    import sys

    OUT.mkdir(exist_ok=True)
    chart, faces, edges, rest_len, hinges = build_mesh()
    if "--refine" in sys.argv:
        # Continue from a saved state (default: the last progress snapshot).
        src = out_file("mobius_shape_resume")
        x = np.load(src if src.exists() else out_file("mobius_shape"))["vertices"].ravel()
        schedule = ((1e4, 1000),)
    elif "--finalize-progress" in sys.argv:
        # Accept the last progress snapshot as the result (e.g. after a time cap).
        x = np.load(out_file("mobius_shape_progress"))["vertices"].ravel()
        schedule = ()
    elif "--init-from" in sys.argv:
        # Start from another solve (e.g. a coarse mesh), resampled onto this grid.
        coarse = np.load(sys.argv[sys.argv.index("--init-from") + 1])
        x = resample(coarse["vertices"], int(coarse["nu"]), int(coarse["nv"]), chart).ravel()
        schedule = ((1e3, 2000), (1e4, 1000))
    else:
        x = initial_guess(chart).ravel()
        schedule = ((100.0, 3000), (1e3, 3000), (1e4, 1000))
    x_start = x.copy()
    X = x.reshape(-1, 3)
    for ks, maxiter in schedule:
        newton = ks >= 1e4
        f, hvp = make_energy(edges, rest_len, hinges, ks)
        if newton:
            # Trust-region Newton with exact Hessian-vector products: L-BFGS
            # crawls on this stiff problem (inextensible sheet).
            import time

            t0, it = time.time(), [0]

            def progress(xk, *_):
                it[0] += 1
                if it[0] % 10 == 0:
                    e, g = f(xk)
                    print(
                        f"  ks={ks:g} iter {it[0]} t={time.time() - t0:.0f}s E={e:.6g} "
                        f"|g|max={np.abs(g).max():.2e}",
                        flush=True,
                    )
                    np.savez(out_file("mobius_shape_progress"), vertices=xk.reshape(-1, 3))

            res = minimize(
                f, x, jac=True, hessp=hvp, method="trust-krylov", callback=progress,
                options={"maxiter": maxiter, "gtol": 1e-4},
            )
        else:
            res = minimize(
                f, x, jac=True, method="L-BFGS-B",
                options={"maxiter": maxiter, "maxfun": 2 * maxiter, "gtol": 1e-7, "ftol": 1e-14},
            )
        x = res.x
        X = x.reshape(-1, 3)
        ln = np.linalg.norm(X[edges[:, 1]] - X[edges[:, 0]], axis=1)
        strain = np.abs(ln - rest_len) / rest_len
        np.savez(out_file("mobius_shape_progress"), vertices=x.reshape(-1, 3))
        print(
            f"ks={ks:g}: E={res.fun:.4g} iters={res.nit} "
            f"max strain={strain.max():.2e} mean={strain.mean():.2e} "
            f"|grad|max={np.abs(res.jac).max():.2e} {res.message}",
            flush=True,
        )
    print(f"max vertex move this run: {np.abs(x - x_start).reshape(-1, 3).max():.2f} mm")
    X = x.reshape(-1, 3)
    X -= X.mean(axis=0)
    max_fold = hinge_angles(X, hinges).max()
    print(f"largest hinge angle: {max_fold:.1f} deg")
    assert max_fold < 30.0, "sheet has creased; the shape is not a smooth band"
    # Boundary: v = -H/2 edge then v = +H/2 edge; together one closed curve.
    lo = np.array([vid(i, 0) for i in range(NU)])
    hi = np.array([vid(i, NV - 1) for i in range(NU)])
    boundary = np.concatenate([X[lo], X[hi]])
    np.savez(
        out_file("mobius_shape"), vertices=X, faces=faces, chart=chart, boundary=boundary,
        nu=NU, nv=NV,
    )
    print("wrote", out_file("mobius_shape"))


if __name__ == "__main__":
    main()
