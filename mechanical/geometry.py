"""Shared strip geometry for the mechanical scripts (paper template, Möbius solver, frame).

These numbers mirror the JITX design (pappalapap/circuits/led_strip.py,
pappalapap/designs/flex_strip.py and ARCHITECTURE.md). They are repeated here
because the mechanical scripts run in their own venv (mechanical/.venv) without
jitx. If the board geometry changes, update both places.

Board coordinates in this package: origin at end A, bottom edge; x along the
strip (0..LENGTH), y across it (0..HEIGHT), viewed from the top (front) face.
"""

import os

# MOBIUS_PITCH overrides the LED pitch for design studies; the strip stays 490 mm
# long with 5 rows, so a smaller pitch means more columns and a narrower strip.
PITCH = float(os.environ.get("MOBIUS_PITCH", 10.0))  # 10 mm chosen 2026-10-03
ROWS = 5
COLUMNS = round(490.0 / PITCH)
LENGTH = COLUMNS * PITCH  # 490.0, flat strip length
HEIGHT = ROWS * PITCH  # 50.0
LAP = PITCH  # one-pitch lap joint
LOOP = LENGTH - LAP  # 480.0, Möbius loop length (centerline)
TOP_COLUMNS = range(1, COLUMNS - 1)  # top face is hidden inside both lap zones
BOTTOM_COLUMNS = range(0, COLUMNS)
LED_SIZE = 2.2

TAIL_OFFSET = 11.25  # tail centre, from end A (flex_strip.py TAIL_OFFSET)
TAIL_WIDTH = 17.0
TAIL_LENGTH = 50.0  # flex_strip.py TAIL_LENGTH: through the tapered neck into the column board ZIF


def led_x(col: int) -> float:
    return (col + 0.5) * PITCH


def led_y(row: int) -> float:
    return (row + 0.5) * PITCH


# Ring order around the Möbius loop: top cols 1..38, then bottom cols 0..39 (78 columns).
def ring_index(face: str, col: int) -> int:
    return col - 1 if face == "top" else len(TOP_COLUMNS) + col


RING_COLUMNS = len(TOP_COLUMNS) + len(BOTTOM_COLUMNS)  # 96 at 10 mm pitch
# Design rules (ARCHITECTURE.md): strip <= 490 mm, loop columns divisible by 3.
assert LENGTH <= 490.0 + 1e-9, "flex strip longer than the 490 mm JLCPCB limit"
assert RING_COLUMNS % 3 == 0 or "MOBIUS_PITCH" in os.environ, "loop columns must be divisible by 3"
