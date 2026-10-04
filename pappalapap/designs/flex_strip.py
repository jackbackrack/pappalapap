"""Pappalapap flex strip: top-level assembly (PLAN task asm-01).

The board is the 490 x 50 mm LED strip (``LedStrip``) plus a connector tail
(``FpcTail16``) hanging off the bottom long edge at end A. This module draws the
outline, places the tail, joins the tail to the strip's nets, sets the design
rules, and lays down the structural power copper. Data routing (479 + 479 hops,
U-turns, the end-B crossover, DIN/DRET, a handful of LED power stubs) is left to
the routing task.

Frame: the strip circuit sits at the board origin, so the origin is the strip
centre, end A is x = -length/2, the bottom edge y = -height/2 (see
``pappalapap.circuits.led_strip``). Layer 0 = top copper (LED face A),
layer -1 = bottom copper (LED face B).

Power copper (ARCHITECTURE.md "Power Tree"):

- Six horizontal lanes, one per gap between LED rows plus the two margins,
  alternating VDD, GND, VDD, ... from the bottom, on both layers. A lane spans
  the gap between two rows minus ``data_band`` either side of each row
  centreline, which stays free for the LED pads and the two data traces
  (DO->DI, BO->BI) running along each row. The margin lanes stop at the
  copper-to-edge rule.
- Every lane runs into its spine at one end and stops short of the other, where
  data U-turns cross it: VDD lanes are crossed at end A, GND lanes at end B. A
  lane's cut end is the pad edge of the outermost LED on that face, so the
  U-turns have the strip end (beyond the outermost LED) to themselves.
- Spines live on the top layer inside the lap zones (no top LEDs there): GND at
  end A, VDD at end B. Bottom-layer lanes run under the spines on their spine
  end and are stitched to them.
- LED power pads join their lane through a short "tongue" of pour from the pad
  to the lane edge, drawn on the LED's own layer. The tongue covers the pad
  column only (VDD and GND are always in opposite pad columns of a WS2816C, so
  a tongue never reaches the data pads beside it), and the pour engine's
  clearance pulls it back from the other pads. A pad whose tongue would not
  land on its lane (only bottom col 0 row 0 VDD, next to the tail entry) is
  reported in ``FlexStrip.unlanded_pads`` and left for the router.
- Stitching vias join each lane's top and bottom copper on a half-pitch grid
  wherever both layers carry the same net.

Tail (connector) power. The tail sits on the BOTTOM side, so its gold fingers
are bottom copper and its PI stiffener is on the top face. Mirrored like this,
the finger order read along +x is GND, DIN, DRET, VDD, which matches the order
of the destinations along the strip's bottom edge at end A: the GND spine (lap
zone), DIN (top col 1, row 0), DRET (bottom col 0, row 0), and the VDD margin
lane. With the fingers on top, the order is reversed and every net would have to
cross the others inside the tail.

- VDD: the bottom-layer finger copper widens into a riser up the tail and into
  the bottom-margin VDD lane. That lane starts to the right of the DRET entry
  on the bottom layer (``entry_keepout``), and the top-layer margin lane starts
  at top col 1, to the right of the DIN entry.
- GND: the finger copper widens into a bottom-layer bus just past the
  stiffener. A via array joins it to a top-layer riser, which runs up the tail
  into the GND spine.
- DIN: finger -> one via just past the stiffener -> top layer -> top col 1 DI.
- DRET: stays on the bottom layer, from the finger to the DO of bottom col 0.

The lap joint must stay insulated: the two spines face each other once the
strip is closed (ARCHITECTURE.md "Lap joint is insulated").
"""

from collections.abc import Iterable, Iterator
from dataclasses import dataclass

import shapely
from jitx.board import Board
from jitx.circuit import Circuit
from jitx.constraints import (
    BinaryDesignConstraint,
    IsCopper,
    IsPad,
    IsTrace,
    UnaryDesignConstraint,
)
from jitx.copper import Pour
from jitx.design import Design
from jitx.landpattern import Pad
from jitx.layerindex import Side
from jitx.net import Net, Port
from jitx.shapes import Shape
from jitx.shapes.shapely import ShapelyGeometry
from jitx.transform import Transform
from jitxlib.symbols.net_symbols import GroundSymbol, PowerSymbol
from shapely.geometry.base import BaseGeometry

from ..circuits.led_strip import GroundTag, LedSite, LedStrip, PowerTag
from ..components.fpc_tail import FpcTail16
from ..components.worldsemi_ws2816c import PAD_OUTER_X, WS2816C
from ..substrate import JLCFlex2L, JLCFlexRules
from .layout_placements import layout_placements

# --- Design parameters ---------------------------------------------------------

LAYOUT_FILE = "layout/flex_strip.json"
"""Layout round-trip file (relative to the project root, where jitx builds run)."""

TAIL_LENGTH = 50.0
"""Tail length from the strip's bottom edge to the cut end (mm). 50 mm
(2026-10-03): the tail drops straight through the column's tapered neck into the
ZIF at the top edge of the column board (designs/column_board.py). Stack-up:
mechanical/column.py."""

TAIL_OFFSET = 11.25
"""Tail centreline, measured from end A (mm). Puts the GND fingers under the
end-A lap zone (so the GND riser lands in the spine) and the DIN finger just
outside it (so DIN rises clear of the spine). At 11.25 the GND finger copper's
outer edge sits exactly on the lap-zone edge (one pitch, 10 mm, from end A) and
the tail spans 2.75..19.75 mm from end A. The window is narrow: the riser
assertion needs <= 11.25, the tail-corner fillet needs > 10.0."""

TAIL_FILLET = 1.5
"""Radius at the two tail-to-strip inside corners, against tearing (mm)."""

TAIL_SIDE = Side.Bottom
"""Fingers on the bottom copper; see the module docstring for why."""

DATA_BAND = 2.0
"""Half-width of the copper-free band along each LED row centreline (mm). LED
pads reach +/-0.79 mm; two 0.2 mm data traces with 0.2 mm spacing fit inside
+/-1.6 mm."""

TONGUE_SIDE_MARGIN = 0.5
"""A tongue is this much wider than its pad on each side, so the pour's thermal
relief spokes have copper to land on (mm)."""

TONGUE_OVERLAP = 0.1
"""How far a tongue reaches into its lane (mm)."""

GND_TRANSITION_LENGTH = 7.0
"""Length of the tail's GND bottom-to-top via field, measured along the tail (mm)."""

STIFFENER_CLEARANCE = 0.5
"""Gap from the stiffener edge to the first via or top copper in the tail (mm)."""

VIA_PITCH = 1.2
"""Pitch of the tail's GND via array (mm)."""

VIA_INSET = 0.6
"""Via centre to copper-region edge, for code-placed vias (mm)."""

LED_VIA_CLEARANCE = 2.0
"""Minimum distance from a stitching via to any LED centre (mm)."""

# --- Design rules (JLC flex floor is 0.1016 mm trace / space) -------------------
DEFAULT_TRACE_WIDTH = 0.2
DEFAULT_CLEARANCE = 0.2
POWER_TRACE_WIDTH = 1.0
THERMAL_GAP = 0.125
THERMAL_SPOKE_WIDTH = 0.2
THERMAL_SPOKES = 4

TOP_LAYER = 0
BOTTOM_LAYER = -1


def layer_of(side: Side) -> int:
    """Copper layer index of a board face."""
    return TOP_LAYER if side == Side.Top else BOTTOM_LAYER


def compose(*transforms: Transform | None) -> Transform:
    """Product of a chain of optional transforms, outermost first."""
    result = Transform.identity()
    for xf in transforms:
        if xf is not None:
            result = result * xf
    return result


def box(x0: float, y0: float, x1: float, y1: float) -> shapely.Polygon:
    """Axis-aligned rectangle from two corners, in any order."""
    return shapely.box(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))


def union(shapes: Iterable[BaseGeometry]) -> BaseGeometry:
    """Union of shapely geometries."""
    return shapely.union_all(list(shapes))


def polygons(geometry: BaseGeometry) -> list[shapely.Polygon]:
    """The polygons of a polygonal shapely result."""
    if isinstance(geometry, shapely.Polygon):
        return [geometry]
    assert isinstance(geometry, shapely.MultiPolygon), geometry.geom_type
    return list(geometry.geoms)


def as_shape(geometry: BaseGeometry) -> ShapelyGeometry:
    """Wrap a polygonal shapely result for a JITX feature, refusing anything else."""
    assert not geometry.is_empty, "empty copper shape"
    assert geometry.geom_type in ("Polygon", "MultiPolygon"), geometry.geom_type
    return ShapelyGeometry(geometry)


def pad_footprints(
    component: WS2816C | FpcTail16, port: Port, frame: Transform | None = None
) -> Iterator[shapely.Polygon]:
    """Board-frame copper outline of every pad mapped to ``port``.

    Pads and their positions come from the component's own pad mapping and
    landpattern; ``frame`` is the placement of the component's parent circuit.
    """
    for mapping in component.mappings:
        if port not in mapping:
            continue
        pads = mapping[port]
        for pad in [pads] if isinstance(pads, Pad) else pads:
            assert isinstance(pad.shape, Shape)
            xf = compose(
                frame,
                component.transform,
                component.landpattern.transform,
                pad.transform,
            )
            geometry = (xf * pad.shape).to_shapely().g
            assert isinstance(geometry, shapely.Polygon)
            yield geometry


@dataclass(frozen=True)
class Lane:
    """One horizontal power lane: the strip-wide band between two LED rows
    (or a row and the strip edge), minus the data bands."""

    index: int
    """0 = bottom margin, ``rows`` = top margin."""
    y_lo: float
    y_hi: float
    is_vdd: bool

    @property
    def y_mid(self) -> float:
        return (self.y_lo + self.y_hi) / 2


@dataclass(frozen=True)
class RailFace:
    """One rail's copper on one board face (the key for per-layer power copper)."""

    is_vdd: bool
    face: Side


@dataclass(frozen=True)
class UnlandedPad:
    """An LED power pad whose tongue would not reach its lane; the router must
    connect it."""

    site: LedSite
    is_vdd: bool


class FlexStripBoard(Board):
    """Strip plus tail outline; signal area inset by the copper-to-edge rule."""

    def __init__(self, outline: BaseGeometry, edge: float) -> None:
        self.shape = as_shape(outline)
        self.signal_area = as_shape(outline.buffer(-edge, join_style="mitre"))


class FlexStrip(Circuit):
    """LED strip, connector tail, rail nets and power copper (see module docstring)."""

    def __init__(
        self,
        tail_length: float = TAIL_LENGTH,
        tail_offset: float = TAIL_OFFSET,
        data_band: float = DATA_BAND,
    ) -> None:
        assert TAIL_SIDE == Side.Bottom, "tail power copper assumes bottom fingers"
        self.strip = LedStrip().at(0.0, 0.0)
        strip = self.strip
        tail_width = FpcTail16.TAIL_WIDTH
        self.edge = JLCFlexRules.min_copper_edge_space

        # Strip extents.
        self.x_a = -strip.length / 2
        self.x_b = strip.length / 2
        self.y_bottom = -strip.height / 2
        self.y_top = strip.height / 2

        # Tail: hangs off the bottom edge at end A; cut end at y_cut.
        self.tail_x = self.x_a + tail_offset
        self.y_cut = self.y_bottom - tail_length
        assert self.tail_x - tail_width / 2 > self.x_a + TAIL_FILLET, (
            "tail too close to end A"
        )
        self.tail = FpcTail16().at(self.tail_x, self.y_cut, on=TAIL_SIDE)
        tail_rect = box(
            self.tail_x - tail_width / 2,
            self.y_cut,
            self.tail_x + tail_width / 2,
            self.y_bottom,
        )
        strip_rect = box(self.x_a, self.y_bottom, self.x_b, self.y_top)
        # Closing (grow, then shrink) fills only the concave tail corners.
        self.outline = (
            union([strip_rect, tail_rect])
            .buffer(TAIL_FILLET, join_style="round")
            .buffer(-TAIL_FILLET, join_style="round")
        )
        self.copper_area = self.outline.buffer(-self.edge, join_style="mitre")

        # Nets. The strip's internal nets carry the names and tags; these join
        # the tail and carry the schematic symbols.
        self.vdd = Net([strip.VDD, *self.tail.VDD], symbol=PowerSymbol())
        self.gnd = Net([strip.GND, *self.tail.GND], symbol=GroundSymbol())
        PowerTag().assign(self.vdd)
        GroundTag().assign(self.gnd)
        self.din = Net([self.tail.DIN, strip.DIN])
        self.dret = Net([self.tail.DRET, strip.DRET])

        # Lap zones: the strip ends beyond the outermost top-face columns.
        top_cols = strip.top_columns
        self.lap_a_edge = self.column_x(top_cols[0]) - strip.pitch / 2
        self.lap_b_edge = self.column_x(top_cols[-1]) + strip.pitch / 2

        self.lanes = list(self.build_lanes(data_band))

        # Copper per (net, layer), as shapely, assembled below.
        top_vdd = [
            self.lane_region(lane, Side.Top) for lane in self.lanes if lane.is_vdd
        ]
        top_gnd = [
            self.lane_region(lane, Side.Top) for lane in self.lanes if not lane.is_vdd
        ]
        bot_vdd = [
            self.lane_region(lane, Side.Bottom) for lane in self.lanes if lane.is_vdd
        ]
        bot_gnd = [
            self.lane_region(lane, Side.Bottom)
            for lane in self.lanes
            if not lane.is_vdd
        ]

        # Spines (top layer, lap zones).
        gnd_spine = box(self.x_a, self.y_bottom, self.lap_a_edge, self.y_top)
        vdd_spine = box(self.lap_b_edge, self.y_bottom, self.x_b, self.y_top)
        top_gnd.append(gnd_spine)
        top_vdd.append(vdd_spine)

        # Tail power copper.
        gnd_fingers = self.finger_span(self.tail.GND)
        vdd_fingers = self.finger_span(self.tail.VDD)
        y_open = self.y_cut + FpcTail16.EXPOSED_LENGTH
        y_stiff = self.y_cut + FpcTail16.STIFFENER_LENGTH + STIFFENER_CLEARANCE
        y_transition = y_stiff + GND_TRANSITION_LENGTH
        gnd_bus = box(gnd_fingers[0], y_open, gnd_fingers[1], y_transition)
        gnd_riser = box(gnd_fingers[0], y_stiff, gnd_fingers[1], self.y_bottom)
        vdd_riser = box(vdd_fingers[0], y_open, vdd_fingers[1], self.lanes[0].y_hi)
        assert self.lanes[0].is_vdd, "bottom-margin lane must be VDD"
        assert gnd_fingers[1] <= self.lap_a_edge, "GND riser must land in the spine"
        bot_gnd.append(gnd_bus)
        top_gnd.append(gnd_riser)
        bot_vdd.append(vdd_riser)

        # DRET entry on the bottom layer: nothing on that layer between end A and
        # the VDD riser, below the row-0 data band.
        self.entry_keepout = box(
            self.x_a,
            self.y_bottom,
            vdd_fingers[0],
            self.lanes[0].y_hi,
        )

        # Pad tongues, per layer.
        self.unlanded_pads: list[UnlandedPad] = []
        lane_union = {
            RailFace(True, Side.Top): union(top_vdd),
            RailFace(False, Side.Top): union(top_gnd),
            RailFace(True, Side.Bottom): union(bot_vdd).difference(self.entry_keepout),
            RailFace(False, Side.Bottom): union(bot_gnd),
        }
        tongues: dict[RailFace, list[shapely.Polygon]] = {key: [] for key in lane_union}
        for site, led in zip(strip.chain_sites(), strip.leds, strict=True):
            for is_vdd, port in ((True, led.VDD), (False, led.GND)):
                key = RailFace(is_vdd, site.face)
                tongue = self.tongue(site, led, port)
                if lane_union[key].intersects(tongue):
                    tongues[key].append(tongue)
                else:
                    self.unlanded_pads.append(UnlandedPad(site, is_vdd))

        copper = {
            key: union([region, *tongues[key]]).intersection(self.copper_area)
            for key, region in lane_union.items()
        }
        self.copper = copper

        # One pour per connected copper region, on its rail's net.
        self.vdd_pours: list[Pour] = []
        self.gnd_pours: list[Pour] = []
        for key, geometry in copper.items():
            pours = self.vdd_pours if key.is_vdd else self.gnd_pours
            pours.extend(
                Pour(as_shape(part), layer_of(key.face)) for part in polygons(geometry)
            )
        for pour in self.vdd_pours:
            self.vdd += pour
        for pour in self.gnd_pours:
            self.gnd += pour

        # Vias: lane stitching on a half-pitch grid, plus the tail GND transition.
        led_centres = [strip.position(site) for site in strip.chain_sites()]
        self.vdd_vias: list[JLCFlex2L.THVia] = []
        self.gnd_vias: list[JLCFlex2L.THVia] = []
        steps = 2 * strip.columns
        for lane in self.lanes:
            both = copper[RailFace(lane.is_vdd, Side.Top)].intersection(
                copper[RailFace(lane.is_vdd, Side.Bottom)]
            )
            vias = self.vdd_vias if lane.is_vdd else self.gnd_vias
            for j in range(1, steps):
                x = self.x_a + j * strip.length / steps
                if self.via_fits(both, x, lane.y_mid, led_centres):
                    vias.append(JLCFlex2L.THVia().at(x, lane.y_mid))
        gnd_field = gnd_bus.intersection(gnd_riser)
        self.gnd_transition_vias = [
            JLCFlex2L.THVia().at(x, y) for x, y in self.via_grid(gnd_field)
        ]
        for via in self.vdd_vias:
            self.vdd += via
        for via in [*self.gnd_vias, *self.gnd_transition_vias]:
            self.gnd += via

    # --- geometry helpers ----------------------------------------------------

    def column_x(self, col: int) -> float:
        """Board x of an LED column centre (face does not matter)."""
        return self.strip.position(LedSite(Side.Top, col, 0, True))[0]

    def row_y(self, row: int) -> float:
        """Board y of an LED row centre."""
        return self.strip.position(LedSite(Side.Top, 0, row, True))[1]

    def build_lanes(self, data_band: float) -> Iterator[Lane]:
        """Lanes bottom to top. Lane i lies below row i; VDD for even i, which
        matches LedStrip's pad orientation (checked per LED by ``tongue``)."""
        rows = self.strip.rows
        for i in range(rows + 1):
            y_lo = self.y_bottom if i == 0 else self.row_y(i - 1) + data_band
            y_hi = self.y_top if i == rows else self.row_y(i) - data_band
            assert y_hi > y_lo, "data band leaves no room for a lane"
            yield Lane(i, y_lo, y_hi, is_vdd=i % 2 == 0)

    def lane_region(self, lane: Lane, face: Side) -> shapely.Polygon:
        """A lane's copper on one face before clipping: full length at its spine
        end, cut at the outermost LED's pad edge at the U-turn end. VDD lanes have
        their spine at end B, GND lanes at end A."""
        cols = self.strip.top_columns if face == Side.Top else self.strip.bottom_columns
        reach = PAD_OUTER_X
        if lane.is_vdd:
            x0 = self.column_x(cols[0]) - reach
            x1 = self.x_b
        else:
            x0 = self.x_a
            x1 = self.column_x(cols[-1]) + reach
        if face == Side.Top:
            # The cut end must stay clear of the other rail's spine.
            if lane.is_vdd:
                assert x0 > self.lap_a_edge, "VDD lane reaches the GND spine"
            else:
                assert x1 < self.lap_b_edge, "GND lane reaches the VDD spine"
        return box(x0, lane.y_lo, x1, lane.y_hi)

    def finger_span(self, ports: Iterable[Port]) -> tuple[float, float]:
        """x-extent of a finger group's copper, widened to the nearer tail edge."""
        bounds = [
            pad.bounds for port in ports for pad in pad_footprints(self.tail, port)
        ]
        lo = min(b[0] for b in bounds)
        hi = max(b[2] for b in bounds)
        half = FpcTail16.TAIL_WIDTH / 2
        if (lo + hi) / 2 < self.tail_x:
            return (self.tail_x - half, hi)
        return (lo, self.tail_x + half)

    def tongue(self, site: LedSite, led: WS2816C, port: Port) -> shapely.Polygon:
        """Pour strip from an LED power pad to the edge of the lane it faces."""
        (pad,) = pad_footprints(led, port, self.strip.transform)
        x0, y0, x1, y1 = pad.bounds
        _, led_y = self.strip.position(site)
        pad_y = (y0 + y1) / 2
        below = pad_y < led_y
        lane = self.lanes[site.row if below else site.row + 1]
        is_vdd = port is led.VDD
        assert lane.is_vdd == is_vdd, f"{site}: power pad faces the wrong lane"
        if below:
            ya, yb = lane.y_hi - TONGUE_OVERLAP, pad_y
        else:
            ya, yb = pad_y, lane.y_lo + TONGUE_OVERLAP
        return box(x0 - TONGUE_SIDE_MARGIN, ya, x1 + TONGUE_SIDE_MARGIN, yb)

    def via_fits(
        self,
        region: BaseGeometry,
        x: float,
        y: float,
        led_centres: list[tuple[float, float]],
    ) -> bool:
        """True if a via at (x, y) sits inside ``region`` with VIA_INSET margin
        and at least LED_VIA_CLEARANCE from every LED centre."""
        point = shapely.Point(x, y)
        if not region.contains(point.buffer(VIA_INSET)):
            return False
        return all(
            (x - cx) ** 2 + (y - cy) ** 2 >= LED_VIA_CLEARANCE**2
            for cx, cy in led_centres
        )

    def via_grid(self, region: BaseGeometry) -> Iterator[tuple[float, float]]:
        """VIA_PITCH grid of via centres inside a rectangle-ish region."""
        x0, y0, x1, y1 = region.bounds
        nx = int((x1 - x0 - 2 * VIA_INSET) // VIA_PITCH) + 1
        ny = int((y1 - y0 - 2 * VIA_INSET) // VIA_PITCH) + 1
        ox = (x0 + x1 - (nx - 1) * VIA_PITCH) / 2
        oy = (y0 + y1 - (ny - 1) * VIA_PITCH) / 2
        for i in range(nx):
            for k in range(ny):
                yield (ox + i * VIA_PITCH, oy + k * VIA_PITCH)


class Pappalapap(Design):
    """Flex strip: ``jitx build pappalapap.main.Pappalapap``."""

    def __init__(self) -> None:
        self.substrate = JLCFlex2L()
        self.circuit = FlexStrip()
        self.board = FlexStripBoard(self.circuit.outline, self.circuit.edge)
        self.rules = [
            UnaryDesignConstraint(IsTrace).trace_width(DEFAULT_TRACE_WIDTH),
            BinaryDesignConstraint(IsCopper, IsCopper).clearance(DEFAULT_CLEARANCE),
            UnaryDesignConstraint(IsPad).thermal_relief(
                THERMAL_GAP, THERMAL_SPOKE_WIDTH, THERMAL_SPOKES
            ),
            UnaryDesignConstraint(PowerTag() | GroundTag(), priority=1).trace_width(
                POWER_TRACE_WIDTH
            ),
        ]
        # Every build writes layout/flex_strip-input.json (board shape,
        # components, vias, routes); layout/flex_strip.json, if present, is read
        # back (format: designs/layout_placements.py, from socialbadge-ai).
        layout_placements(LAYOUT_FILE)
