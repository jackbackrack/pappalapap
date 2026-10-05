"""Pappalapap flex strip: top-level assembly (PLAN task asm-01), one piece or in segments.

The strip is the 445.9 x 45.5 mm LED grid (``LedStrip``, 9.1 mm pitch) plus a
connector tail (``FpcTail16``) hanging off the bottom long edge at end A. This
module draws the outline, places the tail, joins the tail to the strip's nets,
sets the design rules, and lays down the structural power copper. Data routing
(479 + 479 hops, U-turns, the end-B crossover, DIN/DRET, a handful of LED power
stubs) is left to the routing task.

Segments (2026-10-05). JLCPCB assembles flex boards only up to a 240 mm panel
side including its 5 mm rails, so each orderable board is at most
``MAX_ASSEMBLY_LENGTH`` = 230 mm long. The strip is therefore built as two
boards joined by a soldered lap splice:

- ``FlexSegmentA``: columns 0..23 (``TWO_SEGMENT.segments[0]``), end A with the tail, the
  GND spine, the DIN/DRET entries and the end-A U-turns. Board x from end A to
  the joint + ``splice_overlap`` / 2: 220.9 mm.
- ``FlexSegmentB``: columns 24..48 (``TWO_SEGMENT.segments[1]``), end B with the VDD spine,
  the top-to-bottom crossover and the end-B U-turns. Board x from the joint -
  ``splice_overlap`` / 2 to end B: 230.0 mm.
- The joint is the column gap at x_j = 24 x 9.1 = 218.4 mm from end A. The
  boards overlap by ``splice_overlap`` (5 mm) centred on it; B lies on top of A
  (A's top face against B's bottom face). Both carry the same ``SplicePads``
  field at the same strip (x, y): one plated hole per chain hop that crosses the
  joint (20) and 15 VDD + 15 GND holes in the six power lanes. Power enters
  only through A's tail and crosses the splice into B; the lanes simply run
  through the joint on both layers of both boards.
- ``Pappalapap`` is the one-piece strip (445.9 mm), kept building for reference
  and viewing. It is NOT orderable at JLC with assembly.

Variants (2026-10-05). All geometry comes from a ``StripVariant``
(``pappalapap/variants.py``): the numbers above are ``TWO_SEGMENT``. The
one-board variant ``ONE_SEGMENT`` (4.69 mm pitch, 230.0 x 23.47 mm, no splice)
is built by the same ``FlexStrip`` from ``designs/one_segment.py``. The rules
below that only matter at its pitch (GND riser clipped to the spine, narrow
lane stitching, U-turn/DIN channel asserts, via-to-pad clearance) are general
and leave the two-segment boards unchanged.

Frame: the strip circuit sits at the board origin in every variant, so the
origin is the strip centre, end A is x = -length/2, the bottom edge y =
-height/2 (see ``pappalapap.circuits.led_strip``). Segment boards are therefore
off-centre, and both segments use the same coordinates for the same strip
point (what ``scripts/check_splice.py`` relies on). Layer 0 = top copper (LED
face A), layer -1 = bottom copper (LED face B).

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
  U-turns have the strip end (beyond the outermost LED) to themselves. A
  segment keeps the part of each lane that lies on its board.
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
  wherever both layers carry the same net, except inside the splice overlap
  (the splice pads' plated holes join the layers there).

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

The Möbius lap joint (end A over end B) must stay insulated: the two spines
face each other once the strip is closed (ARCHITECTURE.md "Lap joint is
insulated"). The splice joint is the opposite: it is soldered.
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

from ..circuits.led_strip import (
    GroundTag,
    Lane,
    LedSite,
    LedStrip,
    PowerTag,
)
from ..components.fpc_tail import FpcTail16
from ..components.splice_pads import SplicePads
from ..components.worldsemi_ws2816c import PAD_OUTER_X, WS2816C
from ..substrate import JLCFlex2L, JLCFlexRules
from ..variants import TWO_SEGMENT, StripVariant
from .layout_placements import layout_placements

# --- Design parameters ---------------------------------------------------------

LAYOUT_FILE = "layout/flex_strip.json"
"""Layout round-trip file of the one-piece strip (relative to the project root,
where jitx builds run)."""
LAYOUT_FILE_A = "layout/flex_segment_a.json"
LAYOUT_FILE_B = "layout/flex_segment_b.json"

MAX_ASSEMBLY_LENGTH = 230.0
"""Longest board JLCPCB can assemble on a flex panel: 240 mm panel side minus
two 5 mm rails (mm). Asserted for every orderable board."""

# Tail placement. The tail centreline is ``StripVariant.tail_offset`` from end
# A. Its 7 GND fingers (bottom copper, nearest end A) widen into a bottom bus,
# a via field takes GND to a top-layer riser, and the riser runs up the tail
# into the GND spine (top layer, end-A lap zone, one pitch wide). The riser is
# the GND finger span clipped to the spine (x <= lap-zone edge). DIN (finger 9,
# just right of the GND fingers) goes to the top layer through one via past
# the stiffener and rises to top col 1's DI through the "DIN channel" between
# the spine and the first top-face VDD copper. Asserted in ``FlexStrip``:
#
# - fillet: the tail's left edge (8.5 mm left of the centreline) more than
#   ``TAIL_FILLET`` from end A: offset > 10.0, whatever the pitch;
# - GND riser: at least ``MIN_GND_RISER`` of it overlaps the spine, so offset
#   <= pitch + 8.5 - MIN_GND_RISER (15.2 at 9.1 mm pitch, 10.79 at 4.69 mm);
# - DIN channel: >= one trace plus two clearances wide.
#
# At 9.1 mm the GND finger span ends exactly on the lap-zone edge (offset
# 10.35 = pitch + 1.25), so the clip changes nothing: riser 7.25 mm wide, DIN
# rises straight up from its via. At 4.69 mm (one-board variant) the clip
# leaves a 2.84 mm riser (2 x 5 transition vias) and DIN jogs left on the top
# layer inside the tail (free there: the riser stops at the spine edge) into
# the 1.05 mm DIN channel between the spine and top col 1.

TAIL_FILLET = 1.5
"""Radius at the two tail-to-strip inside corners, against tearing (mm)."""

MIN_GND_RISER = 2.4
"""Least width of the tail's top-layer GND riser where it joins the spine:
two via columns (2 x ``VIA_INSET`` + ``VIA_PITCH``) (mm)."""

TAIL_SIDE = Side.Bottom
"""Fingers on the bottom copper; see the module docstring for why."""

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


def _via_diameter() -> float:
    diameter = JLCFlex2L.THVia.diameter
    assert isinstance(diameter, float), "THVia diameter must be a plain number"
    return diameter


VIA_DIAMETER = _via_diameter()
"""Pad diameter of the stitching / crossover via (substrate's THVia, 0.6 mm)."""

NARROW_VIA_INSET = 0.45
"""Via centre to copper edge in a lane narrower than 2 x ``VIA_INSET``: the
0.6 mm via pad plus a 0.15 mm copper ring. Such a lane is stitched on its
copper centreline (the 4.69 mm variant's 1.05 mm margin lanes)."""

UTURN_TRACES = 2
"""Data traces in each U-turn (DO->DI and BO->BI)."""

# --- Design rules (JLC flex floor is 0.1016 mm trace / space) -------------------
# Data trace width and clearance are per variant (StripVariant.trace_width,
# .clearance).
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
    component: WS2816C | FpcTail16 | SplicePads,
    port: Port,
    frame: Transform | None = None,
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


@dataclass(frozen=True)
class Channel:
    """A copper-free x span (board frame) that traces must pass through."""

    x0: float
    x1: float
    required: float
    """Least width for what runs through it, from the variant's rules (mm)."""

    @property
    def width(self) -> float:
        return self.x1 - self.x0


@dataclass(frozen=True)
class UTurnChannel(Channel):
    """The channel at one strip end on one face (``FlexStrip.end_channels``)."""

    at_end_a: bool
    face: Side


class FlexStripBoard(Board):
    """Strip plus tail outline; signal area inset by the copper-to-edge rule."""

    def __init__(self, outline: BaseGeometry, edge: float) -> None:
        self.shape = as_shape(outline)
        self.signal_area = as_shape(outline.buffer(-edge, join_style="mitre"))


class FlexStrip(Circuit):
    """LED strip (or one segment of it), connector tail on the end-A segment,
    splice pads at each joint, rail nets and power copper (module docstring).

    ``variant`` sets the geometry (``pappalapap/variants.py``). ``segment`` is
    a column range of the strip; ``None`` builds the one-piece strip. A
    segment edge that is not a strip end is a joint: the board runs
    ``variant.splice_overlap`` / 2 past the column gap and carries a
    ``SplicePads``.
    """

    def __init__(self, variant: StripVariant, segment: range | None = None) -> None:
        assert TAIL_SIDE == Side.Bottom, "tail power copper assumes bottom fingers"
        self.variant = variant
        self.strip = LedStrip(variant, segment).at(0.0, 0.0)
        strip = self.strip
        cols = strip.segment
        self.edge = JLCFlexRules.min_copper_edge_space
        self.overlap = overlap = variant.splice_overlap
        tail_length = variant.tail_length
        tail_offset = variant.tail_offset
        data_band = variant.data_band

        # Strip extents (the whole strip, whatever the segment).
        self.x_a = -strip.length / 2
        self.x_b = strip.length / 2
        self.y_bottom = -strip.height / 2
        self.y_top = strip.height / 2
        self.has_end_a = cols.start == 0
        self.has_end_b = cols.stop == strip.columns

        # Joints: the column gaps at segment edges that are not strip ends.
        self.joint_cols = [
            c
            for c, inner in (
                (cols.start, not self.has_end_a),
                (cols.stop, not self.has_end_b),
            )
            if inner
        ]
        """Column right of each joint (the joint is the gap before it)."""
        self.board_x0 = (
            self.x_a
            if self.has_end_a
            else strip.column_edge_x(cols.start) - overlap / 2
        )
        self.board_x1 = (
            self.x_b if self.has_end_b else strip.column_edge_x(cols.stop) + overlap / 2
        )

        strip_rect = box(self.board_x0, self.y_bottom, self.board_x1, self.y_top)
        self.lanes: list[Lane] = strip.lanes(data_band)

        # Lap zones: the strip ends beyond the outermost top-face columns.
        top_cols = strip.top_columns
        self.lap_a_edge = strip.column_x(top_cols[0]) - strip.pitch / 2
        self.lap_b_edge = strip.column_x(top_cols[-1]) + strip.pitch / 2

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

        # Spines (top layer, lap zones), on the segments holding the strip ends.
        if self.has_end_a:
            top_gnd.append(box(self.x_a, self.y_bottom, self.lap_a_edge, self.y_top))
        if self.has_end_b:
            top_vdd.append(box(self.lap_b_edge, self.y_bottom, self.x_b, self.y_top))

        # Nets. The strip's internal nets carry the names and tags; these join
        # the tail and the splice pads and carry the schematic symbols.
        self.vdd = Net([strip.VDD], symbol=PowerSymbol())
        self.gnd = Net([strip.GND], symbol=GroundSymbol())
        PowerTag().assign(self.vdd)
        GroundTag().assign(self.gnd)

        # Tail (end-A segment only).
        self.tail: FpcTail16 | None = None
        self.entry_keepout: BaseGeometry = shapely.Polygon()
        """Bottom-layer area kept free of VDD copper for the DRET entry."""
        gnd_bus = None
        gnd_riser = None
        outline = strip_rect
        if self.has_end_a:
            tail = FpcTail16()
            self.tail = tail
            tail_width = FpcTail16.TAIL_WIDTH
            self.tail_x = self.x_a + tail_offset
            self.y_cut = self.y_bottom - tail_length
            assert self.tail_x - tail_width / 2 > self.x_a + TAIL_FILLET, (
                "tail too close to end A"
            )
            tail.at(self.tail_x, self.y_cut, on=TAIL_SIDE)
            tail_rect = box(
                self.tail_x - tail_width / 2,
                self.y_cut,
                self.tail_x + tail_width / 2,
                self.y_bottom,
            )
            # Closing (grow, then shrink) fills only the concave tail corners.
            outline = (
                union([strip_rect, tail_rect])
                .buffer(TAIL_FILLET, join_style="round")
                .buffer(-TAIL_FILLET, join_style="round")
            )
            for port in tail.VDD:
                self.vdd += port
            for port in tail.GND:
                self.gnd += port
            assert strip.DIN is not None and strip.DRET is not None, (
                "the end-A segment must hold both ends of the chain"
            )
            self.din = Net([tail.DIN, strip.DIN])
            self.dret = Net([tail.DRET, strip.DRET])

            # Tail power copper.
            gnd_fingers = self.finger_span(tail, tail.GND)
            vdd_fingers = self.finger_span(tail, tail.VDD)
            y_open = self.y_cut + FpcTail16.EXPOSED_LENGTH
            y_stiff = self.y_cut + FpcTail16.STIFFENER_LENGTH + STIFFENER_CLEARANCE
            y_transition = y_stiff + GND_TRANSITION_LENGTH
            gnd_bus = box(gnd_fingers[0], y_open, gnd_fingers[1], y_transition)
            # The riser is the GND finger span clipped to the spine (see
            # "Tail placement" above the constants).
            riser_x1 = min(gnd_fingers[1], self.lap_a_edge)
            self.gnd_riser_width = riser_x1 - gnd_fingers[0]
            assert self.gnd_riser_width >= MIN_GND_RISER - 1e-9, (
                f"GND riser {self.gnd_riser_width:.2f} mm wide in the spine"
            )
            gnd_riser = box(gnd_fingers[0], y_stiff, riser_x1, self.y_bottom)
            vdd_riser = box(vdd_fingers[0], y_open, vdd_fingers[1], self.lanes[0].y_hi)
            assert self.lanes[0].is_vdd, "bottom-margin lane must be VDD"
            bot_gnd.append(gnd_bus)
            top_gnd.append(gnd_riser)
            bot_vdd.append(vdd_riser)

            # DRET entry on the bottom layer: nothing on that layer between end
            # A and the VDD riser, below the row-0 data band.
            self.entry_keepout = box(
                self.x_a, self.y_bottom, vdd_fingers[0], self.lanes[0].y_hi
            )
        self.outline = outline
        self.copper_area = outline.buffer(-self.edge, join_style="mitre")

        # Splice pads at each joint, joined to the strip's splice ports.
        self.splices: dict[int, SplicePads] = {
            col: SplicePads(strip, overlap, data_band, self.edge, variant.clearance).at(
                strip.column_edge_x(col), 0.0
            )
            for col in self.joint_cols
        }
        """Pad field per joint, keyed by the column right of the joint."""
        for splice in self.splices.values():
            self.vdd += splice.VDD
            self.gnd += splice.GND
        self.splice_nets = [
            Net(
                [
                    port,
                    self.splices[hop.joint_col].data_port(hop.face, hop.row, hop.path),
                ]
            )
            for hop, port in zip(strip.splice_hops, strip.splice_ports, strict=True)
        ]
        """Strip splice port -> splice pad, in the strip's chain order."""
        self.splice_zones = [
            box(
                strip.column_edge_x(col) - overlap / 2,
                self.y_bottom,
                strip.column_edge_x(col) + overlap / 2,
                self.y_top,
            )
            for col in self.joint_cols
        ]
        """Board area of each splice overlap (the other segment lies here)."""

        # Pad tongues, per layer.
        self.unlanded_pads: list[UnlandedPad] = []
        lane_union = {
            RailFace(True, Side.Top): union(top_vdd),
            RailFace(False, Side.Top): union(top_gnd),
            RailFace(True, Side.Bottom): union(bot_vdd).difference(self.entry_keepout),
            RailFace(False, Side.Bottom): union(bot_gnd),
        }
        tongues: dict[RailFace, list[shapely.Polygon]] = {key: [] for key in lane_union}
        for site, led in zip(strip.sites, strip.leds, strict=True):
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

        # Strip-end channels (U-turns, crossover, DIN entry), asserted wide
        # enough for the variant's trace and clearance rules.
        self.uturn_channels = self.end_channels()
        for channel in self.uturn_channels:
            assert channel.width >= channel.required - 1e-9, (
                f"U-turn channel {channel} too narrow"
            )
        self.din_channel: Channel | None = None
        if self.has_end_a:
            self.din_channel = self.entry_channel()
            assert self.din_channel.width >= self.din_channel.required - 1e-9, (
                f"DIN channel {self.din_channel} too narrow"
            )

        # Vias: lane stitching on a half-pitch grid (not in a splice overlap),
        # plus the tail GND transition. A through via must clear every LED pad
        # of another net on both faces.
        led_centres = [strip.position(site) for site in strip.sites]
        foreign_pads = {
            is_vdd: union(
                pad
                for led in strip.leds
                for port in (
                    led.DI,
                    led.DO,
                    led.BI,
                    led.BO,
                    led.GND if is_vdd else led.VDD,
                )
                for pad in pad_footprints(led, port, strip.transform)
            )
            for is_vdd in (True, False)
        }
        no_via = union(self.splice_zones)
        self.vdd_vias: list[JLCFlex2L.THVia] = []
        self.gnd_vias: list[JLCFlex2L.THVia] = []
        steps = 2 * strip.columns
        for lane in self.lanes:
            both = (
                copper[RailFace(lane.is_vdd, Side.Top)]
                .intersection(copper[RailFace(lane.is_vdd, Side.Bottom)])
                .difference(no_via)
            )
            vias = self.vdd_vias if lane.is_vdd else self.gnd_vias
            y, inset = self.via_row(lane)
            for j in range(1, steps):
                x = self.x_a + j * strip.length / steps
                if self.via_fits(
                    both, x, y, inset, led_centres, foreign_pads[lane.is_vdd]
                ):
                    vias.append(JLCFlex2L.THVia().at(x, y))
        self.gnd_transition_vias: list[JLCFlex2L.THVia] = []
        if gnd_bus is not None and gnd_riser is not None:
            gnd_field = gnd_bus.intersection(gnd_riser)
            self.gnd_transition_vias = [
                JLCFlex2L.THVia().at(x, y) for x, y in self.via_grid(gnd_field)
            ]
        for via in self.vdd_vias:
            self.vdd += via
        for via in [*self.gnd_vias, *self.gnd_transition_vias]:
            self.gnd += via

    # --- geometry helpers ----------------------------------------------------

    @property
    def board_length(self) -> float:
        """Board extent along the strip (x), mm; the tail lies within it."""
        x0, _, x1, _ = self.outline.bounds
        return x1 - x0

    def lane_region(self, lane: Lane, face: Side) -> shapely.Polygon:
        """A lane's copper on one face before clipping: full length at its spine
        end, cut at the outermost LED's pad edge at the U-turn end. VDD lanes have
        their spine at end B, GND lanes at end A. Strip-global: a segment clips it
        to its own board."""
        strip = self.strip
        cols = strip.top_columns if face == Side.Top else strip.bottom_columns
        reach = PAD_OUTER_X
        if lane.is_vdd:
            x0 = strip.column_x(cols[0]) - reach
            x1 = self.x_b
        else:
            x0 = self.x_a
            x1 = strip.column_x(cols[-1]) + reach
        if face == Side.Top:
            # The cut end must stay clear of the other rail's spine.
            if lane.is_vdd:
                assert x0 > self.lap_a_edge, "VDD lane reaches the GND spine"
            else:
                assert x1 < self.lap_b_edge, "GND lane reaches the VDD spine"
        return box(x0, lane.y_lo, x1, lane.y_hi)

    def finger_span(
        self, tail: FpcTail16, ports: Iterable[Port]
    ) -> tuple[float, float]:
        """x-extent of a finger group's copper, widened to the nearer tail edge."""
        bounds = [pad.bounds for port in ports for pad in pad_footprints(tail, port)]
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
        led_y = self.strip.row_y(site.row)
        pad_y = (y0 + y1) / 2
        below = pad_y < led_y
        lane = self.lanes[site.row if below else site.row + 1]
        is_vdd = port is led.VDD
        assert lane.is_vdd == is_vdd, f"{site}: power pad faces the wrong lane"
        if below:
            ya, yb = lane.y_hi - TONGUE_OVERLAP, pad_y
        else:
            ya, yb = pad_y, lane.y_lo + TONGUE_OVERLAP
        margin = self.variant.tongue_side_margin
        return box(x0 - margin, ya, x1 + margin, yb)

    def via_row(self, lane: Lane) -> tuple[float, float]:
        """Stitching-via centreline and inset for a lane: its centreline and
        ``VIA_INSET`` when its copper is wide enough, else the centre of its
        copper (inside the edge rule) and ``NARROW_VIA_INSET``."""
        lo = max(lane.y_lo, self.y_bottom + self.edge)
        hi = min(lane.y_hi, self.y_top - self.edge)
        if hi - lo >= 2 * VIA_INSET:
            return lane.y_mid, VIA_INSET
        assert hi - lo >= 2 * NARROW_VIA_INSET, (
            f"lane {lane.index} too narrow for a via"
        )
        return (lo + hi) / 2, NARROW_VIA_INSET

    def via_fits(
        self,
        region: BaseGeometry,
        x: float,
        y: float,
        inset: float,
        led_centres: list[tuple[float, float]],
        foreign_pads: BaseGeometry,
    ) -> bool:
        """True if a via at (x, y) sits inside ``region`` with ``inset``
        margin, at least LED_VIA_CLEARANCE from every LED centre and the
        clearance rule from every pad of another net (``foreign_pads``)."""
        point = shapely.Point(x, y)
        if not region.contains(point.buffer(inset)):
            return False
        if not all(
            (x - cx) ** 2 + (y - cy) ** 2 >= LED_VIA_CLEARANCE**2
            for cx, cy in led_centres
        ):
            return False
        reach = VIA_DIAMETER / 2 + self.variant.clearance
        return not point.buffer(reach).intersects(foreign_pads)

    def column_pads(self, face: Side, col: int) -> BaseGeometry:
        """Union of every pad of the LEDs in one column on one face."""
        strip = self.strip
        return union(
            pad
            for site, led in zip(strip.sites, strip.leds, strict=True)
            if site.face == face and site.col == col
            for port in (led.DI, led.DO, led.BI, led.BO, led.VDD, led.GND)
            for pad in pad_footprints(led, port, strip.transform)
        )

    def end_channels(self) -> list["UTurnChannel"]:
        """The copper-free x span at each strip end on this board, per face,
        where the U-turns run: from the spine (top) or the copper-to-edge
        limit (bottom) to the outermost LED's pads and the cut lane copper of
        the rail the U-turns cross (VDD at end A, GND at end B). At end B on
        the top face it also holds the two crossover vias."""
        strip = self.strip
        v = self.variant
        traces = UTURN_TRACES * v.trace_width + (UTURN_TRACES - 1) * v.clearance
        result = []
        for face in (Side.Top, Side.Bottom):
            cols = strip.top_columns if face == Side.Top else strip.bottom_columns
            on_top = face == Side.Top
            if self.has_end_a:
                inner = union(
                    [self.column_pads(face, cols[0]), self.copper[RailFace(True, face)]]
                ).bounds[0]
                outer = self.lap_a_edge if on_top else self.x_a + self.edge
                need = traces + (2 if on_top else 1) * v.clearance
                result.append(UTurnChannel(outer, inner, need, True, face))
            if self.has_end_b:
                inner = union(
                    [
                        self.column_pads(face, cols[-1]),
                        self.copper[RailFace(False, face)],
                    ]
                ).bounds[2]
                outer = self.lap_b_edge if on_top else self.x_b - self.edge
                need = traces + (2 if on_top else 1) * v.clearance
                if on_top:  # the crossover vias share this channel
                    need = max(need, VIA_DIAMETER + 2 * v.clearance)
                result.append(UTurnChannel(inner, outer, need, False, face))
        return result

    def entry_channel(self) -> "Channel":
        """Top-layer x span between the GND spine and the first top-face VDD
        copper or LED pad below the row-0 centreline, where DIN rises from the
        tail to top col 1's DI."""
        strip = self.strip
        below_row0 = box(self.x_a, self.y_bottom, self.x_b, strip.row_y(0))
        blockers = union(
            [
                self.copper[RailFace(True, Side.Top)],
                self.column_pads(Side.Top, strip.top_columns[0]),
            ]
        ).intersection(below_row0)
        v = self.variant
        return Channel(
            self.lap_a_edge, blockers.bounds[0], v.trace_width + 2 * v.clearance
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


class FlexStripDesign(Design):
    """Flex strip design for one variant and column range (parameterised;
    build one of the subclasses below or in ``designs/one_segment.py``)."""

    def __init__(
        self,
        variant: StripVariant,
        segment: range | None,
        layout_file: str,
        orderable: bool,
    ) -> None:
        self.substrate = JLCFlex2L()
        self.circuit = FlexStrip(variant, segment)
        if orderable:
            length = self.circuit.board_length
            assert length <= MAX_ASSEMBLY_LENGTH + 1e-9, (
                f"board {length:.2f} mm long; JLC assembly limit {MAX_ASSEMBLY_LENGTH}"
            )
        self.board = self.make_board(self.circuit)
        self.rules = [
            UnaryDesignConstraint(IsTrace).trace_width(variant.trace_width),
            BinaryDesignConstraint(IsCopper, IsCopper).clearance(variant.clearance),
            UnaryDesignConstraint(IsPad).thermal_relief(
                THERMAL_GAP, THERMAL_SPOKE_WIDTH, THERMAL_SPOKES
            ),
            UnaryDesignConstraint(PowerTag() | GroundTag(), priority=1).trace_width(
                POWER_TRACE_WIDTH
            ),
        ]
        self.apply_layout(layout_file)

    def make_board(self, strip: FlexStrip) -> Board:
        """The board: the strip (segment) outline. The panel designs
        (``designs/flex_panel.py``) put a panel frame around it instead."""
        return FlexStripBoard(strip.outline, strip.edge)

    def apply_layout(self, layout_file: str) -> None:
        """Every build writes <layout_file stem>-input.json (board shape,
        components, vias, routes); layout_file, if present, is read back
        (format: designs/layout_placements.py, from socialbadge-ai)."""
        layout_placements(layout_file)


class Pappalapap(FlexStripDesign):
    """One-piece strip, 445.9 mm, for reference and viewing only: longer than
    JLC can assemble. ``jitx build pappalapap.designs.flex_strip.Pappalapap``."""

    def __init__(self) -> None:
        super().__init__(TWO_SEGMENT, None, LAYOUT_FILE, orderable=False)


class FlexSegmentA(FlexStripDesign):
    """Segment A (columns 0..23, tail, end A), orderable:
    ``jitx build pappalapap.designs.flex_strip.FlexSegmentA``."""

    def __init__(self) -> None:
        super().__init__(
            TWO_SEGMENT, TWO_SEGMENT.segments[0], LAYOUT_FILE_A, orderable=True
        )


class FlexSegmentB(FlexStripDesign):
    """Segment B (columns 24..48, end B), orderable:
    ``jitx build pappalapap.designs.flex_strip.FlexSegmentB``."""

    def __init__(self) -> None:
        super().__init__(
            TWO_SEGMENT, TWO_SEGMENT.segments[1], LAYOUT_FILE_B, orderable=True
        )
