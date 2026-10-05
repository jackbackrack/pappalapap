"""Shared strip geometry for the mechanical scripts (paper template, Möbius solver, frame).

These numbers mirror the JITX design (pappalapap/circuits/led_strip.py,
pappalapap/designs/flex_strip.py and ARCHITECTURE.md). They are repeated here
because the mechanical scripts run in their own venv (mechanical/.venv) without
jitx. If the board geometry changes, update both places.

Board coordinates in this package: origin at end A, bottom edge; x along the
strip (0..LENGTH), y across it (0..HEIGHT), viewed from the top (front) face.
"""

import os

# MOBIUS_PITCH / MOBIUS_COLUMNS override the LED pitch and column count for
# design studies.
PITCH = float(os.environ.get("MOBIUS_PITCH", 9.1))  # 9.1 mm chosen 2026-10-05 (was 10)
ROWS = 5
COLUMNS = int(os.environ.get("MOBIUS_COLUMNS", 49))
LENGTH = COLUMNS * PITCH  # 445.9, flat strip length
HEIGHT = ROWS * PITCH  # 50.0
LAP = PITCH  # one-pitch lap joint
LOOP = LENGTH - LAP  # 480.0, Möbius loop length (centerline)
TOP_COLUMNS = range(1, COLUMNS - 1)  # top face is hidden inside both lap zones
BOTTOM_COLUMNS = range(0, COLUMNS)
LED_SIZE = 2.2

# Two-board strip (2026-10-05): JLC assembles flex boards <= 240 mm panel side
# (230 mm board + 5 mm rails), so the strip is segment A (columns 0..23, with the
# tail) and segment B (columns 24..48), soldered in a lap splice centred on the
# column gap at JOINT_X from end A (flex_strip.py SPLICE_OVERLAP, led_strip.py
# JOINT_COLUMN). B lies on top of A (A's top face against B's bottom face).
JOINT_X = 218.4  # 24 * PITCH
OVERLAP = 5.0
SEGMENTS = ((0, 23), (24, 48))  # inclusive column ranges of segments A and B

TAIL_OFFSET = 10.35  # tail centre, from end A (flex_strip.py TAIL_OFFSET)
TAIL_WIDTH = 17.0
TAIL_LENGTH = 50.0  # flex_strip.py TAIL_LENGTH: through the tapered neck into the column board ZIF


def led_x(col: int) -> float:
    return (col + 0.5) * PITCH


def led_y(row: int) -> float:
    return (row + 0.5) * PITCH


# Ring order around the Möbius loop: top cols 1..COLUMNS-2, then bottom cols 0..COLUMNS-1.
def ring_index(face: str, col: int) -> int:
    return col - 1 if face == "top" else len(TOP_COLUMNS) + col


RING_COLUMNS = len(TOP_COLUMNS) + len(BOTTOM_COLUMNS)  # 96 at 10 mm pitch
# Design rules (ARCHITECTURE.md): strip <= 490 mm, loop columns divisible by 3.
assert LENGTH <= 490.0 + 1e-9, "flex strip longer than the 490 mm JLCPCB limit"
assert RING_COLUMNS % 3 == 0 or "MOBIUS_PITCH" in os.environ, "loop columns must be divisible by 3"
