"""LedStrip: parametric two-face grid of WS2816C LEDs, wired as one serpentine chain.

Geometry (ARCHITECTURE.md, "Display Geometry"):

- Pitch ``p`` (variant: 9.1 or 4.69 mm) in both x and y. Column ``k`` is
  centered half a pitch in from end A, row ``r`` half a pitch up from the
  strip's bottom edge. The strip is ``columns * p`` long (445.9 / 230.0 mm)
  and ``rows * p`` high (45.5 / 23.47 mm).
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

Variants and segments (2026-10-05): the grid (pitch, rows, columns, lap
columns) comes from a ``StripVariant`` (``pappalapap/variants.py``); the
two-segment strip (9.1 mm pitch) and the one-board strip (4.69 mm pitch) are
the same code with different variants. JLCPCB cannot assemble a flex board
longer than a 240 mm panel side (230 mm board + 5 mm rails), so the 9.1 mm
strip is built as two boards joined by a soldered lap splice.
``LedStrip(variant, segment=range(...))`` builds only the LEDs whose column
lies in ``segment``, keeping the GLOBAL chain order, rotation and lane parity
exactly as in the one-piece strip. A chain hop with one LED inside the segment
and the other outside becomes a splice port: ``splice_hops`` lists each such
``SpliceHop`` (data path, upstream site, downstream site) in chain order and
``splice_ports`` the matching port, wired to the LED's output (the segment
drives the hop) or input (it receives it). Two-segment: segment A = columns
0..23, segment B = columns 24..48 (``TWO_SEGMENT.segments``); every row
crosses the joint once per face and per data path, so each segment has
5 x 2 x 2 = 20 splice ports.
"""

from collections.abc import Iterator
from dataclasses import dataclass, replace

from jitx.board import Board
from jitx.circuit import Circuit
from jitx.constraints import Tag
from jitx.design import Design
from jitx.layerindex import Side
from jitx.net import Net, Port
from jitx.shapes.composites import rectangle

from ..components.worldsemi_ws2816c import WS2816C, DataPath
from ..substrate import JLCFlex2L, JLCFlexRules
from ..variants import TWO_SEGMENT, StripVariant

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


@dataclass(frozen=True)
class SpliceHop:
    """A chain hop between two LEDs on different segments (see module docstring).

    Identified by the global sites at both ends, so the two segments that share
    a hop build equal ``SpliceHop`` values."""

    path: DataPath
    upstream: LedSite
    """The LED whose output (DO/BO) drives the hop."""
    downstream: LedSite
    """The LED whose input (DI/BI) receives it."""

    @property
    def face(self) -> Side:
        return self.upstream.face

    @property
    def row(self) -> int:
        return self.upstream.row

    @property
    def joint_col(self) -> int:
        """The column just past the joint the hop crosses (the joint is the
        gap before this column)."""
        return max(self.upstream.col, self.downstream.col)


@dataclass(frozen=True)
class Lane:
    """One horizontal power lane: the strip-wide band between two LED rows (or a
    row and the strip edge), minus the data bands. Strip frame."""

    index: int
    """0 = bottom margin, ``rows`` = top margin."""
    y_lo: float
    y_hi: float
    is_vdd: bool

    @property
    def y_mid(self) -> float:
        return (self.y_lo + self.y_hi) / 2


class LedStrip(Circuit):
    """Two-face LED grid, one serpentine WS2816C chain, every LED explicitly placed.

    Ports: VDD, GND (common rails), DIN (first LED DI) and DRET (last LED DO),
    which exist only on the segment holding that LED (else ``None``), and
    ``splice_ports`` for the hops that leave the segment (``splice_hops``).
    ``self.leds`` is in chain order and ``self.sites`` holds the matching sites.
    """

    VDD = Port()
    GND = Port()

    def __init__(
        self,
        variant: StripVariant,
        segment: range | None = None,
    ) -> None:
        self.variant = variant
        self.pitch = variant.pitch
        self.rows = variant.rows
        self.columns = columns = variant.columns
        self.top_columns = tuple(variant.top_columns)
        self.bottom_columns = tuple(variant.bottom_columns)
        self.segment = range(columns) if segment is None else segment
        assert self.segment.step == 1 and len(self.segment) > 0, "bad segment"
        assert 0 <= self.segment.start and self.segment.stop <= columns, (
            "segment outside the strip"
        )

        self.vdd_net = Net([self.VDD], name="VDD_LED")
        self.gnd_net = Net([self.GND], name="GND_LED")
        PowerTag().assign(self.vdd_net)
        GroundTag().assign(self.gnd_net)

        self.leds: list[WS2816C] = []
        self.sites: list[LedSite] = []
        """Site of each LED in ``self.leds`` (same order)."""
        self.dout_nets: list[Net] = []
        """DO(n) -> DI(n+1) nets inside the segment, in chain order."""
        self.bout_nets: list[Net] = []
        """BO(n) -> BI(n+1) nets inside the segment, in chain order."""
        self.splice_hops: list[SpliceHop] = []
        """Hops that leave the segment, in chain order."""
        self.splice_ports: list[Port] = []
        """Port of each hop in ``splice_hops`` (same order)."""
        self.splice_nets: list[Net] = []
        """Splice port -> LED output or input, one per splice port."""

        chain = list(self.chain_sites())
        prev: tuple[LedSite, WS2816C | None] | None = None
        for site in chain:
            led = None
            if site.col in self.segment:
                x, y = self.position(site)
                led = WS2816C().at(x, y, on=site.face, rotate=site.rotation)
                self.vdd_net += led.VDD
                self.gnd_net += led.GND
                self.leds.append(led)
                self.sites.append(site)
            if prev is not None:
                self.join(prev[0], prev[1], site, led)
            prev = (site, led)

        self.DIN: Port | None = None
        self.DRET: Port | None = None
        self.din_net: Net | None = None
        self.dret_net: Net | None = None
        if self.sites[0] == chain[0]:
            first = self.leds[0]
            self.DIN = Port()
            self.din_net = self.DIN + first.DI
            self.gnd_net += first.BI  # datasheet p.6: first LED's BI tied to GND
        if self.sites[-1] == chain[-1]:
            # The last LED's BO is intentionally unconnected (no downstream LED).
            self.DRET = Port()
            self.dret_net = self.leds[-1].DO + self.DRET

    def join(
        self,
        up_site: LedSite,
        up: WS2816C | None,
        down_site: LedSite,
        down: WS2816C | None,
    ) -> None:
        """Wire one chain hop on both data paths, or expose it as splice ports
        when exactly one of its LEDs is in the segment."""
        for path in DataPath:
            if up is not None and down is not None:
                net = up.output(path) + down.input(path)
                nets = self.dout_nets if path == DataPath.PRIMARY else self.bout_nets
                nets.append(net)
            elif up is not None or down is not None:
                assert up_site.face == down_site.face, "splice on a face crossover"
                assert up_site.row == down_site.row, "splice on a U-turn"
                port = Port()
                self.splice_hops.append(SpliceHop(path, up_site, down_site))
                self.splice_ports.append(port)
                if up is not None:
                    inner = up.output(path)
                else:
                    assert down is not None
                    inner = down.input(path)
                self.splice_nets.append(Net([port, inner]))

    def drives(self, hop: SpliceHop) -> bool:
        """True when this segment holds the hop's upstream LED (its port is an
        LED output); False when it receives the hop."""
        return hop.upstream.col in self.segment

    @property
    def length(self) -> float:
        """Strip length along x (end A to end B), mm."""
        return self.columns * self.pitch

    @property
    def height(self) -> float:
        """Strip height along y, mm."""
        return self.rows * self.pitch

    @property
    def chain_length(self) -> int:
        """LEDs in the whole (one-piece) chain."""
        return self.rows * (len(self.top_columns) + len(self.bottom_columns))

    def column_x(self, col: int) -> float:
        """Column centre x in the circuit frame (origin at the strip centre)."""
        return (col + 0.5) * self.pitch - self.length / 2

    def column_edge_x(self, col: int) -> float:
        """x of the boundary between column ``col - 1`` and column ``col``."""
        return col * self.pitch - self.length / 2

    def row_y(self, row: int) -> float:
        """Row centre y in the circuit frame."""
        return (row + 0.5) * self.pitch - self.height / 2

    def position(self, site: LedSite) -> tuple[float, float]:
        """Site center in the circuit frame (origin at the strip center)."""
        return (self.column_x(site.col), self.row_y(site.row))

    def lanes(self, data_band: float) -> list[Lane]:
        """Power lanes bottom to top. Lane i lies below row i; VDD for even i,
        which matches the LED pad orientation (module docstring); ``data_band``
        is the copper-free half-width around each row centreline."""
        result = []
        for i in range(self.rows + 1):
            y_lo = -self.height / 2 if i == 0 else self.row_y(i - 1) + data_band
            y_hi = self.height / 2 if i == self.rows else self.row_y(i) - data_band
            assert y_hi > y_lo, "data band leaves no room for a lane"
            result.append(Lane(i, y_lo, y_hi, is_vdd=i % 2 == 0))
        return result

    def chain_sites(self) -> Iterator[LedSite]:
        """All sites of the one-piece strip in chain order (segment ignored):
        row-major serpentine, top face rows ascending, then bottom face rows
        descending (see module docstring)."""
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


TEST_VARIANT = replace(TWO_SEGMENT, columns=4, joint_columns=())
"""Four columns, top face cols 1..2, bottom face cols 0..3 (6 loop columns)."""


class TestDesign(Design):
    """Small 4-column strip, both faces: ``jitx build pappalapap.circuits.led_strip.TestDesign``."""

    def __init__(self) -> None:
        self.substrate = JLCFlex2L()
        self.circuit = LedStrip(TEST_VARIANT)
        self.board = StripBoard(self.circuit.length, self.circuit.height)


class FullStripDesign(Design):
    """Full 480-LED strip on a 445.9 x 45.5 mm rectangle."""

    def __init__(self) -> None:
        self.substrate = JLCFlex2L()
        self.circuit = LedStrip(TWO_SEGMENT)
        self.board = StripBoard(self.circuit.length, self.circuit.height)
        strip = self.circuit
        assert len(strip.leds) == strip.chain_length
        assert len(strip.dout_nets) == len(strip.bout_nets) == strip.chain_length - 1
        assert not strip.splice_hops
