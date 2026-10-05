"""Strip variants: the per-variant geometry of the flex LED strip (2026-10-05).

The same code (``circuits/led_strip.py``, ``designs/flex_strip.py``,
``designs/flex_panel.py``) builds every variant; a ``StripVariant`` carries the
numbers that differ. Both variants share the grid shape of the original 490 mm
design: 49 strip columns x 5 rows, top face cols 1..47, bottom face cols 0..48
(480 LEDs), a one-pitch Möbius lap at each end, 96 loop columns, the row-major
serpentine chain, the 16-finger tail 50 mm long. What changes:

==================  ======================  =============================
                    ``TWO_SEGMENT``         ``ONE_SEGMENT``
==================  ======================  =============================
pitch               9.1 mm                  230 / 49 = 4.6939 mm
strip               445.9 x 45.5 mm         230.0 x 23.47 mm
boards              A cols 0..23, B 24..48  one board, cols 0..48
                    (soldered lap splice)   (no splice)
data band           +/-2.0 mm               +/-1.0 mm (pads +/-0.79 +
                                            0.15 clearance, rounded up)
tongue side margin  0.5 mm                  0 (end channels, see below)
trace / clearance   0.2 / 0.2 mm            0.15 / 0.15 mm (JLC floor
                                            0.1016)
tail offset         10.35 mm                10.35 mm
==================  ======================  =============================

Design files: two-segment ``designs/flex_strip.py`` (``FlexSegmentA/B``,
``Pappalapap``) and ``designs/flex_panel.py`` (``FlexPanelA/B``); one-segment
``designs/one_segment.py`` (``FlexOneSegment``, ``FlexOnePanel``).

Pure data, no jitx import: ``mechanical/variants.py`` mirrors these numbers for
the mechanical venv (``scripts/check_strip_fit.py`` compares the two).
"""

from dataclasses import dataclass
from itertools import pairwise


@dataclass(frozen=True)
class StripVariant:
    """Geometry and layout knobs of one strip variant (module docstring)."""

    pitch: float
    """LED pitch in x and y (mm)."""
    columns: int
    """Strip columns, end A to end B."""
    rows: int
    joint_columns: tuple[int, ...]
    """Column right of each splice joint (the joint is the column gap before
    it); empty for a one-board strip."""
    tail_offset: float
    """Tail centreline from end A (mm); ``FlexStrip`` asserts its window."""
    tail_length: float
    """Strip bottom edge to the tail's cut end (mm)."""
    data_band: float
    """Copper-free half-width around each LED row centreline (mm)."""
    tongue_side_margin: float
    """How much wider than its pad each pad-to-lane pour tongue is, per side
    (mm)."""
    trace_width: float
    """Board-wide data trace width rule (mm)."""
    clearance: float
    """Board-wide copper-to-copper clearance rule (mm)."""
    splice_overlap: float = 5.0
    """Lap-splice overlap centred on each joint (mm); unused without joints."""
    lap_columns: int = 1
    """Columns at each end whose top face is hidden in the Möbius lap."""

    def __post_init__(self) -> None:
        assert self.pitch > 0 and self.rows > 0
        assert 0 < self.lap_columns and 2 * self.lap_columns < self.columns
        assert all(0 < c < self.columns for c in self.joint_columns)
        assert list(self.joint_columns) == sorted(set(self.joint_columns))
        assert self.loop_columns % 3 == 0, (
            f"loop columns {self.loop_columns} not divisible by 3"
        )

    @property
    def top_columns(self) -> range:
        """Top-face columns: all but the lap zones."""
        return range(self.lap_columns, self.columns - self.lap_columns)

    @property
    def bottom_columns(self) -> range:
        """Bottom-face columns: all of them."""
        return range(self.columns)

    @property
    def loop_columns(self) -> int:
        """LED columns met once round the Möbius surface: 2 x (columns - 1)
        for a one-column lap."""
        return len(self.top_columns) + len(self.bottom_columns)

    @property
    def leds(self) -> int:
        return self.rows * self.loop_columns

    @property
    def length(self) -> float:
        """Flat strip length (mm)."""
        return self.columns * self.pitch

    @property
    def height(self) -> float:
        """Strip height (mm)."""
        return self.rows * self.pitch

    @property
    def segments(self) -> tuple[range, ...]:
        """Column range of each board, end A first."""
        edges = (0, *self.joint_columns, self.columns)
        return tuple(range(a, b) for a, b in pairwise(edges))


TWO_SEGMENT = StripVariant(
    pitch=9.1,
    columns=49,
    rows=5,
    joint_columns=(24,),
    tail_offset=10.35,
    tail_length=50.0,
    data_band=2.0,
    tongue_side_margin=0.5,
    trace_width=0.2,
    clearance=0.2,
)
"""The 445.9 mm strip as two boards (segments A and B) soldered in a lap splice."""

ONE_SEGMENT_LENGTH = 230.0
"""The one-board strip is as long as JLC assembles: a 240 mm panel side minus
two 5 mm rails (mm)."""

ONE_SEGMENT = StripVariant(
    pitch=ONE_SEGMENT_LENGTH / 49,
    columns=49,
    rows=5,
    joint_columns=(),
    tail_offset=10.35,
    tail_length=50.0,
    data_band=1.0,
    tongue_side_margin=0.0,
    trace_width=0.15,
    clearance=0.15,
)
"""The whole strip on one 230.0 x 23.47 mm board, pitch 4.6939 mm."""
