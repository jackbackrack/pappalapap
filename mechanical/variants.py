"""Strip variants for the mechanical scripts (no jitx; mechanical/.venv).

Mirrors ``pappalapap/variants.py`` (the JITX side owns the numbers);
``scripts/check_strip_fit.py`` asserts the two agree. ``geometry.py`` still
describes the two-segment strip on its own and is not changed by this file;
wiring a variant into the mechanical pipeline is a separate step.

Board coordinates as in ``geometry.py``: origin at end A, bottom edge; x along
the strip, y across it, top (front) face view.
"""

from dataclasses import dataclass
from itertools import pairwise


@dataclass(frozen=True)
class MechVariant:
    """Strip geometry the mechanical scripts need, for one variant."""

    pitch: float
    """LED pitch in x and y (mm)."""
    columns: int
    rows: int
    tail_offset: float
    """Tail centreline from end A (mm)."""
    tail_length: float
    """Strip bottom edge to the tail's cut end (mm)."""
    joint_columns: tuple[int, ...]
    """Column right of each soldered splice joint; empty for one board."""
    splice_overlap: float = 5.0
    lap_columns: int = 1

    @property
    def length(self) -> float:
        """Flat strip length (mm)."""
        return self.columns * self.pitch

    @property
    def height(self) -> float:
        return self.rows * self.pitch

    @property
    def lap(self) -> float:
        """Möbius lap overlap (mm)."""
        return self.lap_columns * self.pitch

    @property
    def loop(self) -> float:
        """Möbius loop length along the centreline (mm)."""
        return self.length - self.lap

    @property
    def joints_x(self) -> tuple[float, ...]:
        """Splice joint positions from end A (mm)."""
        return tuple(c * self.pitch for c in self.joint_columns)

    @property
    def board_lengths(self) -> tuple[float, ...]:
        """Length of each board, end A first: joints add half the splice
        overlap to both neighbours (mm)."""
        edges = (0.0, *self.joints_x, self.length)
        half = self.splice_overlap / 2
        return tuple(
            (b + (half if b < self.length else 0.0)) - (a - (half if a > 0 else 0.0))
            for a, b in pairwise(edges)
        )

    @property
    def ring_columns(self) -> int:
        """LED columns once round the loop (top cols + bottom cols)."""
        return (self.columns - 2 * self.lap_columns) + self.columns


TWO_SEGMENT = MechVariant(
    pitch=9.1,
    columns=49,
    rows=5,
    tail_offset=10.35,
    tail_length=50.0,
    joint_columns=(24,),
)
"""445.9 x 45.5 mm, two boards spliced at 218.4 mm from end A."""

ONE_SEGMENT = MechVariant(
    pitch=230.0 / 49,
    columns=49,
    rows=5,
    tail_offset=10.35,
    tail_length=50.0,
    joint_columns=(),
)
"""230.0 x 23.47 mm, one board, pitch 4.6939 mm."""

VARIANTS = (TWO_SEGMENT, ONE_SEGMENT)

MAX_BOARD_LENGTH = 230.0
"""JLC flex assembly: 240 mm panel side minus two 5 mm rails (mm)."""

for _v in VARIANTS:
    assert _v.ring_columns % 3 == 0, "loop columns must be divisible by 3"
    assert max(_v.board_lengths) <= MAX_BOARD_LENGTH + 1e-9, "board too long for JLC"
