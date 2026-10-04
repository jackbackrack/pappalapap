"""LedStrip: parametric two-face grid of WS2816C LEDs, wired as one serpentine chain.

Geometry (ARCHITECTURE.md, "Display Geometry"):

- Pitch ``p`` (10.0 mm) in both x and y. Column ``k`` is centered half a pitch in
  from end A, row ``r`` half a pitch up from the strip's bottom edge. The strip is
  ``columns * p`` long (490 mm) and ``rows * p`` high (50 mm).
- Top face carries columns 1..47, bottom face columns 0..48; a bottom LED sits
  directly behind the top LED with the same column/row (same board xy).

Coordinate frame of this circuit: **origin at the center of the strip**, x along
the strip from end A (x = -length/2) to end B (x = +length/2), y from the bottom
edge (y = -height/2) to the top edge (y = +height/2), viewed from the top face.
So ``rectangle(strip.length, strip.height)`` is exactly the strip outline when the
circuit is placed at the board origin. ``LedStrip.position(site)`` gives a site's
xy in this frame.

Chain order (ARCHITECTURE.md, "Chain order"): a row-major serpentine. The top
face is visited row 0 -> row (rows-1); the bottom face row (rows-1) -> row 0.
Top row r runs +x (end A -> end B) when r is even and -x when odd; bottom row r
runs the opposite way to top row r. With the defaults the chain starts at top
col 1 row 0 (end A, next to the bottom edge), ends the top face at top col 47
row 4 (end B), crosses through a via to bottom col 48 row 4 (one pitch away),
and finishes at bottom col 0 row 0 (end A, bottom edge). Row-to-row hops are
U-turns at the strip ends only: 4 per face instead of one per column.

LED orientation: in the WS2816C footprint frame the inputs (BI, DI) are the left
pad column and the outputs (DO, BO) the right one, with VDD bottom-left and GND
top-right. Each LED is rotated so its outputs face the direction of travel: on
the top face 0 deg for +x and 180 deg for -x; on the bottom face (placement
mirrors x before rotating) 180 deg for +x and 0 deg for -x.

Power-lane consequence: for every LED in row r (either face), VDD is on the side
facing row r-1 when r is even and row r+1 when r is odd, and GND is the
opposite. So the horizontal lanes between rows alternate VDD/GND, starting
with VDD under row 0 and ending with GND above the top row (for 5 rows). Top
and bottom face share the same assignment at the same y, so the lanes can be
stitched between layers. Each lane is crossed only by the U-turns at one end
of the strip: VDD lanes at end A and GND lanes at end B. So the GND spine
goes at end A and the VDD spine at end B, on the top face of the lap zones,
which are free of top LEDs.

Chain wiring follows the datasheet application circuit (page 6): LED n DO ->
LED n+1 DI, LED n BO -> LED n+1 BI, first LED BI -> GND, all VDD and all GND
common, no external components. The last LED's DO is the DRET port; its BO is
left unconnected (nothing downstream needs the backup data path).
"""

from collections.abc import Iterator, Sequence
from dataclasses import dataclass

from jitx.board import Board
from jitx.circuit import Circuit
from jitx.constraints import Tag
from jitx.design import Design
from jitx.layerindex import Side
from jitx.net import Net, Port
from jitx.shapes.composites import rectangle

from ..components.worldsemi_ws2816c import WS2816C
from ..substrate import JLCFlex2L, JLCFlexRules

# Defaults from ARCHITECTURE.md "Display Geometry".
DEFAULT_PITCH = 10.0
DEFAULT_ROWS = 5
DEFAULT_COLUMNS = 49
# Top face is hidden inside both one-column lap zones (first and last column).
DEFAULT_TOP_COLUMNS = range(1, DEFAULT_COLUMNS - 1)
DEFAULT_BOTTOM_COLUMNS = range(DEFAULT_COLUMNS)

# Rotations (degrees) so the output pads face the direction of travel.
# Footprint outputs point along local +x; Side.Bottom placement mirrors x first.
_ROTATION_POS_X = {Side.Top: 0.0, Side.Bottom: 180.0}
_ROTATION_NEG_X = {Side.Top: 180.0, Side.Bottom: 0.0}


class PowerTag(Tag):
    """LED supply rail (VDD). Rule (wide trace) is declared in the top-level design."""


class GroundTag(Tag):
    """LED ground rail (GND). Rule (wide trace) is declared in the top-level design."""


@dataclass(frozen=True)
class LedSite:
    """One LED position: face, grid column/row, and direction of travel in its row."""

    face: Side
    col: int
    row: int
    forward: bool
    """True when the chain runs +x (end A -> end B) through this LED's row."""

    @property
    def rotation(self) -> float:
        """LED rotation in degrees so outputs face the direction of travel."""
        table = _ROTATION_POS_X if self.forward else _ROTATION_NEG_X
        return table[self.face]


class LedStrip(Circuit):
    """Two-face LED grid, one serpentine WS2816C chain, every LED explicitly placed.

    Ports: VDD, GND (common rails), DIN (first LED DI), DRET (last LED DO).
    ``self.leds`` is in chain order; ``self.chain_sites()`` yields the matching sites.
    """

    VDD = Port()
    GND = Port()
    DIN = Port()
    DRET = Port()

    def __init__(
        self,
        pitch: float = DEFAULT_PITCH,
        rows: int = DEFAULT_ROWS,
        columns: int = DEFAULT_COLUMNS,
        top_columns: Sequence[int] = DEFAULT_TOP_COLUMNS,
        bottom_columns: Sequence[int] = DEFAULT_BOTTOM_COLUMNS,
    ) -> None:
        assert rows > 0 and columns > 0 and pitch > 0
        assert all(0 <= k < columns for k in top_columns), "top column out of range"
        assert all(0 <= k < columns for k in bottom_columns), (
            "bottom column out of range"
        )
        assert len(set(top_columns)) == len(top_columns), "duplicate top column"
        assert len(set(bottom_columns)) == len(bottom_columns), (
            "duplicate bottom column"
        )
        assert len(top_columns) + len(bottom_columns) > 0, "empty strip"
        self.pitch = pitch
        self.rows = rows
        self.columns = columns
        self.top_columns = tuple(sorted(top_columns))
        self.bottom_columns = tuple(sorted(bottom_columns))

        self.vdd_net = Net([self.VDD], name="VDD_LED")
        self.gnd_net = Net([self.GND], name="GND_LED")
        PowerTag().assign(self.vdd_net)
        GroundTag().assign(self.gnd_net)

        self.leds: list[WS2816C] = []
        self.dout_nets: list[Net] = []
        """DO(n) -> DI(n+1) nets, in chain order."""
        self.bout_nets: list[Net] = []
        """BO(n) -> BI(n+1) nets, in chain order."""

        for site in self.chain_sites():
            x, y = self.position(site)
            led = WS2816C().at(x, y, on=site.face, rotate=site.rotation)
            self.vdd_net += led.VDD
            self.gnd_net += led.GND
            if self.leds:
                prev = self.leds[-1]
                self.dout_nets.append(prev.DO + led.DI)
                self.bout_nets.append(prev.BO + led.BI)
            self.leds.append(led)

        first = self.leds[0]
        last = self.leds[-1]
        self.din_net = self.DIN + first.DI
        self.gnd_net += first.BI  # datasheet p.6: first LED's BI tied to GND
        self.dret_net = last.DO + self.DRET
        # last.BO intentionally unconnected (no downstream LED).

    @property
    def length(self) -> float:
        """Strip length along x (end A to end B), mm."""
        return self.columns * self.pitch

    @property
    def height(self) -> float:
        """Strip height along y, mm."""
        return self.rows * self.pitch

    def position(self, site: LedSite) -> tuple[float, float]:
        """Site center in the circuit frame (origin at the strip center)."""
        x = (site.col + 0.5) * self.pitch - self.length / 2
        y = (site.row + 0.5) * self.pitch - self.height / 2
        return (x, y)

    def chain_sites(self) -> Iterator[LedSite]:
        """Sites in chain order: row-major serpentine, top face rows ascending,
        then bottom face rows descending (see module docstring)."""
        for r in range(self.rows):
            forward = r % 2 == 0
            cols = self.top_columns if forward else reversed(self.top_columns)
            for col in cols:
                yield LedSite(Side.Top, col, r, forward)
        for r in reversed(range(self.rows)):
            forward = r % 2 == 1
            cols = self.bottom_columns if forward else reversed(self.bottom_columns)
            for col in cols:
                yield LedSite(Side.Bottom, col, r, forward)


Device = LedStrip


# --- Build harnesses ---------------------------------------------------------


class StripBoard(Board):
    """Plain rectangle matching a strip's outline (no tail; that is asm-01's job)."""

    def __init__(self, length: float, height: float) -> None:
        edge = JLCFlexRules.min_copper_edge_space
        self.shape = rectangle(length, height)
        self.signal_area = rectangle(length - 2 * edge, height - 2 * edge)


class TestDesign(Design):
    """Small 4-column strip, both faces: ``jitx build pappalapap.circuits.led_strip.TestDesign``."""

    def __init__(self) -> None:
        self.substrate = JLCFlex2L()
        self.circuit = LedStrip(
            columns=4, top_columns=range(1, 3), bottom_columns=range(4)
        )
        self.board = StripBoard(self.circuit.length, self.circuit.height)


class FullStripDesign(Design):
    """Full 480-LED strip on a 490 x 50 mm rectangle."""

    def __init__(self) -> None:
        self.substrate = JLCFlex2L()
        self.circuit = LedStrip()
        self.board = StripBoard(self.circuit.length, self.circuit.height)
        strip = self.circuit
        faces = len(strip.top_columns) + len(strip.bottom_columns)
        assert len(strip.leds) == strip.rows * faces
