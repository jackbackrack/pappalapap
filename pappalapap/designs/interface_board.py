"""XIAO interface board: top-level assembly (PLAN task ib-asm).

``jitx build pappalapap.designs.interface_board.InterfaceBoard``

A 2-layer 1.6 mm JLCPCB board (``JLC2L16``) carrying ``XiaoInterface``
(``pappalapap.circuits.interface``): the XIAO ESP32S3 sockets, the 16-contact
ZIF for the flex tail, the 5 V screw terminal and the protected power path.
This module draws the outline and mounting holes, joins the power nets to
their pours and schematic symbols, places the high-current stitching vias,
adds the silkscreen labels and sets the design rules. Routing is left to the
routing step.

Frame: the circuit sits at the origin, so the origin is the board centre
(top view, x right, y up). Layer 0 = top copper, layer -1 = bottom.

Edges (see ``interface_board_placement``): ZIF entry face on the bottom edge (the flex
comes straight in from -y), XIAO USB-C flush with the right edge, screw
terminal wire entry on the left edge. The 1000 uF can sits 13 mm above the
ZIF's entry face, clear of the flip lid.

Bulk storage: this board keeps the 1000 uF can (``BulkCan``). It is
superseded by the column board (which switched to a ``MlccBank`` of four
100 uF 1206 MLCCs on 2026-10-05) and is only kept building, so it was not
re-laid out.

Mounting: 4 x M2.5 clearance holes, NON-plated, 2.7 mm, 3.5 mm in from each
side, with a 6.0 mm copper/via/route keepout on both layers for the screw head
(M2.5 pan head <= 5.0 mm). NPTH because the base it screws into is not a
ground reference and a floating plated ring would add nothing; plate them and
tie to GND only if the enclosure becomes metal.

Copper (1 oz outer, see ``substrate_rigid``):

- GND: bottom layer, the whole board (a solid plane broken only by holes,
  vias and THT pads); top layer, every area the power pours do not claim.
- VLED (top, rank 1): the hull of every VLED pad (FET source, TVS cathode,
  bulk +, Schottky anode, buffer VCC, ZIF contacts 1-7), grown by
  ``VLED_MARGIN``, minus the GND band behind ZIF contacts 8-16 and minus the
  VIN/VFUSE regions. At its narrowest (the feed to ZIF contacts 1-7) it is
  over 6 mm wide.
- VIN (terminal + to fuse) and VFUSE (fuse to FET drain), top, rank 1: hulls
  of the two pads at each end grown by ``POWER_PAD_MARGIN``, at least 3.4 mm
  wide.
- For scale: IPC-2152 puts 5 A on 1 oz outer copper at roughly 2.5-3 mm for a
  10 C rise, so every 5 A path is at or above that before counting the
  bottom GND plane, which carries the whole return.
- The ZIF's GND contacts (10-16) drop to the bottom plane through
  ``GND_VIA_ROWS`` rows of vias right behind the contacts, one per contact
  per row.
"""

from typing import Protocol

import shapely
from jitx.board import Board
from jitx.circuit import Circuit
from jitx.constraints import (
    BinaryDesignConstraint,
    IsCopper,
    IsPad,
    IsTrace,
    Tag,
    UnaryDesignConstraint,
)
from jitx.copper import Pour
from jitx.design import Design
from jitx.feature import Courtyard, KeepOut, Silkscreen
from jitx.inspect import extract
from jitx.landpattern import Landpattern, Pad, PadMapping
from jitx.layerindex import LayerSet
from jitx.net import Net, Port
from jitx.placement import Placement
from jitx.shapes import Shape
from jitx.shapes.primitive import Circle, Text
from jitx.shapes.shapely import ShapelyGeometry
from jitx.transform import Transform
from jitxlib.parts import Capacitor, Resistor
from jitxlib.symbols.net_symbols import GroundSymbol, PowerSymbol
from shapely.geometry.base import BaseGeometry

from ..circuits.interface import (
    JLC_BASIC_CAPACITOR,
    JLC_BASIC_RESISTOR,
    At,
    BulkCan,
    InterfacePlacement,
    XiaoInterface,
    XiaoSupplyTag,
)
from ..circuits.led_strip import GroundTag, PowerTag
from ..components.cx_1000uf16v import CX1000uF16V
from ..components.kefa_kf301_2p import KF301_2P, PIN_TO_FRONT
from ..components.littelfuse_0451_6a3 import Fuse451_6A3
from ..components.xfcn_f1002b16 import XFCN_F1002B16
from ..components.xiao_esp32s3 import USB_MAX_X, XiaoESP32S3Socket
from ..substrate_rigid import JLC2L16, JLC2LRules
from jitx_design_tools.layout_placements import layout_placements

# --- Board frame and placement (mm) -------------------------------------------------

BOARD_WIDTH = 56.0
BOARD_HEIGHT = 42.0
"""56 x 42 mm. PLAN.md asked for about 45 x 35; the part courtyards (the
1000 uF can alone is 14.5 mm across, the XIAO 23 x 18.3 mm, the ZIF 22 x 7 mm)
plus four M2.5 screw-head keepouts do not fit in less without overlaps."""

EDGE_INSET = 0.6
"""Gap from a connector's mating face (ZIF entry face, terminal wire-entry face)
to the board edge, so the face's silkscreen line stays on the board."""

ZIF_X = -10.0
"""ZIF centre x. Leaves the bottom-left M2.5 screw head clear of the ZIF body."""

TERMINAL_Y = 6.0
"""Screw-terminal centre y: leaves room above it for the "+5V IN" label below
the top-left screw head."""


def interface_board_placement() -> InterfacePlacement:
    """Part placement for the flat board, origin at the board centre.

    ZIF on the bottom edge (cable enters from -y), XIAO on the right edge
    (USB-C at +x), screw terminal on the left edge (wires enter from -x).
    """
    left, right = -BOARD_WIDTH / 2, BOARD_WIDTH / 2
    bottom = -BOARD_HEIGHT / 2
    return InterfacePlacement(
        # Screw terminal on the left edge, wire entry (-y in its frame) facing
        # -x: rotate -90. P1 (local -x) lands at +y, so "+5V" is the upper pin.
        power_input=At(left + PIN_TO_FRONT + EDGE_INSET, TERMINAL_Y, -90),
        # Fuse along x, p1 (local +y) toward the terminal (-x): rotate 90.
        fuse=At(-14.4, 8.5, 90),
        # SOIC-8 pins 5-8 (D) are at local +x; rotate 180 puts D toward the fuse.
        fet=At(-5.6, 8.5, 180),
        gate_r=At(-2.9, 13.2, 90),
        # TVS lying along x above the XIAO; K (local +y) toward the FET.
        tvs=At(5.7, 13.3, 90),
        bulk=(At(-12.15, -1.6),),
        # Schottky upright; rotate 180 puts K (local +y) at the bottom, toward
        # the XIAO's 5V pin, and A at the top, inside the VLED pour.
        schottky=At(2.0, 0.5, 180),
        # XIAO on the right edge, USB-C (+x) flush with it.
        xiao=At(right - USB_MAX_X, 0.0),
        # ZIF on the bottom edge, entry face (local -y) EDGE_INSET from it.
        zif=At(ZIF_X, bottom - XFCN_F1002B16.ENTRY_FACE_Y + EDGE_INSET),
        buffer=At(-2.6, -9.9),
        buffer_c=At(1.2, -9.9, 90),
        pulldown=At(-7.0, -10.3),
        din_r=At(-9.5, -12.0, 90),
        zif_c10u=At(-17.4, -12.3),
        zif_c100n=At(-14.2, -12.3),
        dret_r=At(9.0, -13.0),
        dret_div=At(9.0, -16.0),
    )


# --- Outline and mounting --------------------------------------------------------

CORNER_RADIUS = 2.0
HOLE_INSET = 3.5
"""Mounting-hole centre to the two nearest board edges (mm)."""
HOLE_DIAMETER = 2.7
"""M2.5 clearance (medium fit), non-plated."""
SCREW_KEEPOUT_DIAMETER = 6.0
"""M2.5 pan/cheese head <= 5.0 mm, plus 0.5 mm all round."""

# --- Copper ------------------------------------------------------------------------

TOP_LAYER = 0
BOTTOM_LAYER = -1
VLED_MARGIN = 1.0
"""Growth of the VLED pad hull into the pour region (mm)."""
POWER_PAD_MARGIN = 0.8
"""Growth of the VIN / VFUSE pad hulls (mm)."""
NET_GAP = 0.5
"""Gap left between two power regions of different nets on one layer (mm);
the pour engine adds the copper clearance on top."""
GND_BAND_DEPTH = 3.2
"""Depth of the top-layer GND band behind the ZIF's DRET/DIN/GND contacts,
measured from the contacts' rear pad edge (mm)."""
GND_VIA_ROWS = (1.0, 2.2)
"""Distances of the ZIF GND via rows from the contacts' rear pad edge (mm)."""
TVS_VIA_GAP = 0.7
"""TVS anode pad edge to its GND via centres (mm)."""

# --- Silkscreen ----------------------------------------------------------------------

TITLE = "pappalapap interface"
TITLE_SIZE = 1.2
LABEL_SIZE = 1.0
TERMINAL_LABEL_GAP = 1.4
"""Screw-terminal courtyard edge to the centre of the "+5V IN" (above) and
"GND" (below) labels (mm)."""
TITLE_XY = (-9.5, 18.0)
PIN_LABEL_DX = 2.0
"""ZIF contact 1 / 16 pad centre to its "1" / "16" label, outward along x (mm)."""
PIN_LABEL_DY = 2.0
"""ZIF contacts' rear pad edge to the "1" / "16" labels (mm)."""
FLEX_LABEL_GAP = 4.0
"""ZIF courtyard edge to the centre of the "FLEX" label beside the entry (mm)."""

# --- Design rules (JLC 2-layer floor is 0.10 / 0.10 mm) ------------------------------

DEFAULT_TRACE_WIDTH = 0.25
DEFAULT_CLEARANCE = 0.2
POWER_TRACE_WIDTH = 1.5
"""VIN / VFUSE / VLED / GND traces, wherever the router draws them."""
XIAO_SUPPLY_WIDTH = 0.5
"""XIAO 5 V feed, <= 0.5 A."""
THERMAL_GAP = 0.25
THERMAL_SPOKE_WIDTH = 0.4
THERMAL_SPOKES = 4
"""Default pad-to-pour relief: 4 x 0.4 mm spokes (1.6 mm of copper)."""
HIGH_CURRENT_SPOKE_WIDTH = 1.0
"""Power-path pads: 4 x 1.0 mm spokes (4 mm of copper) for 5 A."""


class HighCurrentPadTag(Tag):
    """Pads on the 5 A power path; wider thermal-relief spokes."""


def as_shape(geometry: BaseGeometry) -> ShapelyGeometry:
    """Wrap a polygonal shapely result for a JITX feature, refusing anything else."""
    assert not geometry.is_empty, "empty shape"
    assert geometry.geom_type in ("Polygon", "MultiPolygon"), geometry.geom_type
    return ShapelyGeometry(geometry)


def compose(*transforms: Transform | None) -> Transform:
    """Product of a chain of optional transforms, outermost first."""
    result = Transform.identity()
    for xf in transforms:
        if xf is not None:
            result = result * xf
    return result


class MappedComponent(Protocol):
    """A placed component with an explicit pad mapping."""

    @property
    def mappings(self) -> list[PadMapping]: ...
    @property
    def landpattern(self) -> Landpattern: ...
    @property
    def transform(self) -> Placement | None: ...


def pad_footprints(
    component: MappedComponent, ports: list[Port], frame: Transform | None
) -> list[shapely.Polygon]:
    """Board-frame copper outline of every pad mapped to any of ``ports``.

    Pads come from the component's own pad mapping and landpattern; ``frame``
    is the placement of the component's parent circuit.
    """
    out: list[shapely.Polygon] = []
    for mapping in component.mappings:
        for port in ports:
            if port not in mapping:
                continue
            pads = mapping[port]
            for pad in [pads] if isinstance(pads, Pad) else pads:
                out.append(pad_outline(pad, component, frame))
    return out


def all_pad_footprints(
    component: Fuse451_6A3, frame: Transform | None
) -> list[shapely.Polygon]:
    """Board-frame copper outline of every pad of a component's landpattern."""
    return [
        pad_outline(pad, component, frame)
        for pad in extract(component.landpattern, Pad)
    ]


def two_pin_pad_footprints(
    component: Capacitor | Resistor, frame: Transform | None
) -> tuple[shapely.Polygon, shapely.Polygon]:
    """Board-frame pads of a parts-chain two-pin passive, as (p1, p2).

    Such a part has no explicit pad mapping, so JITX's default applies: ports
    in declaration order onto pads in landpattern order (``jitx.component``).
    Reading the landpattern resolves the part (its batch flushes on demand).
    """
    ports = list(extract(component, Port))
    assert ports == [component.p1, component.p2], "two-pin port order"
    first, second = (
        pad_outline(pad, component, frame)
        for pad in extract(component.landpattern, Pad)
    )
    return first, second


def bulk_vled_pads(
    iface: XiaoInterface, frame: Transform | None
) -> list[shapely.Polygon]:
    """Board-frame VLED pad of every bulk capacitor (can +, MLCC p1)."""
    pads: list[shapely.Polygon] = []
    for cap in iface.bulk:
        if isinstance(cap, CX1000uF16V):
            pads += pad_footprints(cap, [cap.pos], frame)
        else:
            pads.append(two_pin_pad_footprints(cap, frame)[0])
    return pads


def pad_outline(
    pad: Pad,
    component: MappedComponent | Fuse451_6A3 | Capacitor | Resistor,
    frame: Transform | None,
) -> shapely.Polygon:
    """Board-frame copper outline of one pad of a placed component."""
    assert isinstance(pad.shape, Shape)
    xf = compose(
        frame, component.transform, component.landpattern.transform, pad.transform
    )
    geometry = (xf * pad.shape).to_shapely().g
    assert isinstance(geometry, shapely.Polygon)
    return geometry


def courtyard(component: MappedComponent, frame: Transform | None) -> BaseGeometry:
    """Board-frame union of a placed component's courtyard features."""
    lp = component.landpattern
    xf = compose(frame, component.transform, lp.transform)
    return shapely.union_all(
        [(xf * c.shape).to_shapely().g for c in extract(lp, Courtyard)]
    )


def nearest(
    candidates: list[shapely.Polygon], to: list[shapely.Polygon]
) -> shapely.Polygon:
    """The candidate pad closest to any of ``to``."""
    target = shapely.union_all(to)
    return min(candidates, key=lambda c: c.distance(target))


def hull(shapes: list[shapely.Polygon], margin: float) -> BaseGeometry:
    """Convex hull of some pad outlines, grown by ``margin``."""
    return shapely.union_all(shapes).convex_hull.buffer(margin, join_style="round")


class InterfaceBoardShape(Board):
    """Rounded rectangle with the mounting holes cut out.

    The signal area is the outline inset by the copper-to-edge rule but WITHOUT
    the holes: a holed polygon reaches the router as a bounding box. The screw
    keepouts already keep copper away from the holes.
    """

    def __init__(self, outline: BaseGeometry, signal_area: BaseGeometry) -> None:
        self.shape = as_shape(outline)
        self.signal_area = as_shape(signal_area)


class InterfaceLayout(Circuit):
    """Interface circuit plus board-level copper, holes and silkscreen."""

    def __init__(self) -> None:
        self.iface = XiaoInterface(
            XiaoESP32S3Socket, KF301_2P, BulkCan(), interface_board_placement()
        ).at(0.0, 0.0)
        iface = self.iface
        frame = iface.transform
        width, height = BOARD_WIDTH, BOARD_HEIGHT
        self.edge = JLC2LRules.min_copper_edge_space

        # --- Outline, mounting holes ------------------------------------------
        rect = shapely.box(-width / 2, -height / 2, width / 2, height / 2)
        rounded = rect.buffer(-CORNER_RADIUS).buffer(CORNER_RADIUS)
        hx, hy = width / 2 - HOLE_INSET, height / 2 - HOLE_INSET
        self.hole_centres = [(sx * hx, sy * hy) for sx in (-1, 1) for sy in (-1, 1)]
        holes = [shapely.Point(c).buffer(HOLE_DIAMETER / 2) for c in self.hole_centres]
        self.outline = rounded.difference(shapely.union_all(holes))
        self.screw_keepouts = [
            KeepOut(
                Circle(diameter=SCREW_KEEPOUT_DIAMETER).at(x, y),
                LayerSet(TOP_LAYER, BOTTOM_LAYER),
                pour=True,
                via=True,
                route=True,
            )
            for x, y in self.hole_centres
        ]
        self.screw_marks = [
            Silkscreen(Circle(diameter=SCREW_KEEPOUT_DIAMETER).at(x, y))
            for x, y in self.hole_centres
        ]
        # Copper area: no holes (a holed polygon reaches the router as its
        # bounding box); the screw keepouts clear the pours around the holes.
        copper_area = rounded.buffer(-self.edge, join_style="mitre")
        self.copper_area = copper_area

        # --- Nets: symbols here, tags on the circuit's own nets -----------------
        self.vin = Net([iface.vin], symbol=PowerSymbol())
        self.vfuse = Net([iface.vfuse], symbol=PowerSymbol())
        self.vled = Net([iface.vled], symbol=PowerSymbol())
        self.gnd = Net([iface.gnd], symbol=GroundSymbol())

        # --- Power regions (top) ------------------------------------------------
        # The fuse is unpolarized and has no explicit pad mapping, so its two
        # pads are told apart by position: the one nearer the terminal's +5V
        # pin is the VIN side.
        terminal_vin = pad_footprints(iface.power_in, [iface.input_plus()], frame)
        fet_drain = pad_footprints(iface.fet, [iface.fet.D], frame)
        fuse_pads = all_pad_footprints(iface.fuse, frame)
        fuse_in = nearest(fuse_pads, terminal_vin)
        fuse_out = nearest(fuse_pads, fet_drain)
        assert fuse_in is not fuse_out, "fuse pads do not face terminal and FET"
        vin_region = hull([*terminal_vin, fuse_in], POWER_PAD_MARGIN)
        vfuse_region = hull([fuse_out, *fet_drain], POWER_PAD_MARGIN)
        vled_pads = (
            pad_footprints(iface.fet, [iface.fet.S], frame)
            + pad_footprints(iface.tvs, [iface.tvs.K], frame)
            + bulk_vled_pads(iface, frame)
            + pad_footprints(iface.schottky, [iface.schottky.A], frame)
            + pad_footprints(iface.buffer, [iface.buffer.VCC], frame)
            + pad_footprints(iface.zif, iface.zif_vled(), frame)
        )
        # GND band behind ZIF contacts 8-16: from the DRET contact's left pad
        # edge rightwards, from the board bottom to GND_BAND_DEPTH behind the
        # contacts' rear pad edges.
        rear_pads = pad_footprints(
            iface.zif, [iface.zif_dret(), iface.zif_din(), *iface.zif_gnd()], frame
        )
        x_band, _, _, rear = shapely.union_all(rear_pads).bounds
        gnd_band = shapely.box(
            x_band - NET_GAP, -height / 2, width / 2, rear + GND_BAND_DEPTH
        )
        vled_region = (
            hull(vled_pads, VLED_MARGIN)
            .difference(gnd_band)
            .difference(vin_region.buffer(NET_GAP))
            .difference(vfuse_region.buffer(NET_GAP))
            .intersection(copper_area)
        )

        # Pours are members of this circuit (so the structural walk owns them)
        # and of their nets.
        self.vin_pour = Pour(
            as_shape(vin_region.intersection(copper_area)), TOP_LAYER, rank=1
        )
        self.vfuse_pour = Pour(
            as_shape(vfuse_region.intersection(copper_area)), TOP_LAYER, rank=1
        )
        self.vled_pour = Pour(as_shape(vled_region), TOP_LAYER, rank=1)
        # GND: rank 0 everywhere the power pours leave free on top; whole bottom.
        self.gnd_pours = [
            Pour(as_shape(copper_area), TOP_LAYER, rank=0),
            Pour(as_shape(copper_area), BOTTOM_LAYER, rank=0),
        ]
        self.vin += self.vin_pour
        self.vfuse += self.vfuse_pour
        self.vled += self.vled_pour
        for pour in self.gnd_pours:
            self.gnd += pour

        # --- GND vias -------------------------------------------------------------
        via = JLC2L16.THVia
        gnd_contacts = pad_footprints(iface.zif, iface.zif_gnd(), frame)
        self.zif_gnd_vias = [
            via().at(pad.centroid.x, rear + row)
            for row in GND_VIA_ROWS
            for pad in gnd_contacts
        ]
        (tvs_anode,) = pad_footprints(iface.tvs, [iface.tvs.A], frame)
        _, ty0, tx1, ty1 = tvs_anode.bounds
        self.tvs_gnd_vias = [
            via().at(tx1 + TVS_VIA_GAP, y) for y in (ty0 + 0.5, ty1 - 0.5)
        ]
        for v in [*self.zif_gnd_vias, *self.tvs_gnd_vias]:
            self.gnd += v

        # --- High-current pads --------------------------------------------------
        HighCurrentPadTag().assign(
            iface.power_in, iface.fuse, iface.fet, iface.tvs, *iface.bulk
        )

        # --- Silkscreen -------------------------------------------------------------
        # "+5V IN" above the terminal on the P1 side, "GND" below on the P2
        # side (asserted, so a terminal rotation cannot swap the labels).
        (p1,) = pad_footprints(iface.power_in, [iface.input_plus()], frame)
        (p2,) = pad_footprints(iface.power_in, [iface.input_minus()], frame)
        assert p1.centroid.y > p2.centroid.y, "terminal +5V pin must be the upper one"
        tx0, ty0, tx1, ty1 = courtyard(iface.power_in, frame).bounds
        # ZIF pin-1 / pin-16 labels behind the outer contacts; "FLEX" beside
        # the entry face.
        contact_1, *_, contact_16 = pad_footprints(iface.zif, iface.zif.P, frame)
        label_y = rear + PIN_LABEL_DY
        _, zy0, zx1, _ = courtyard(iface.zif, frame).bounds
        self.labels = [
            Silkscreen(Text(TITLE, TITLE_SIZE).at(*TITLE_XY)),
            Silkscreen(
                Text("+5V IN", LABEL_SIZE).at((tx0 + tx1) / 2, ty1 + TERMINAL_LABEL_GAP)
            ),
            Silkscreen(
                Text("GND", LABEL_SIZE).at((tx0 + tx1) / 2, ty0 - TERMINAL_LABEL_GAP)
            ),
            Silkscreen(
                Text("FLEX", LABEL_SIZE).at(zx1 + FLEX_LABEL_GAP, zy0 + LABEL_SIZE)
            ),
            Silkscreen(
                Text("1", LABEL_SIZE).at(contact_1.centroid.x - PIN_LABEL_DX, label_y)
            ),
            Silkscreen(
                Text("16", LABEL_SIZE).at(contact_16.centroid.x + PIN_LABEL_DX, label_y)
            ),
        ]


class InterfaceBoard(Design):
    """XIAO interface board (``jitx build pappalapap.designs.interface_board.InterfaceBoard``)."""

    resistor_defaults = JLC_BASIC_RESISTOR
    capacitor_defaults = JLC_BASIC_CAPACITOR

    def __init__(self) -> None:
        self.substrate = JLC2L16()
        self.circuit = InterfaceLayout()
        self.board = InterfaceBoardShape(self.circuit.outline, self.circuit.copper_area)
        self.rules = [
            UnaryDesignConstraint(IsTrace).trace_width(DEFAULT_TRACE_WIDTH),
            BinaryDesignConstraint(IsCopper, IsCopper).clearance(DEFAULT_CLEARANCE),
            UnaryDesignConstraint(IsPad).thermal_relief(
                THERMAL_GAP, THERMAL_SPOKE_WIDTH, THERMAL_SPOKES
            ),
            UnaryDesignConstraint(HighCurrentPadTag(), priority=1).thermal_relief(
                THERMAL_GAP, HIGH_CURRENT_SPOKE_WIDTH, THERMAL_SPOKES
            ),
            UnaryDesignConstraint(PowerTag() | GroundTag(), priority=1).trace_width(
                POWER_TRACE_WIDTH
            ),
            UnaryDesignConstraint(XiaoSupplyTag(), priority=1).trace_width(
                XIAO_SUPPLY_WIDTH
            ),
        ]
        layout_placements(
            "layout/interface_board.json"
        )  # writes layout/interface_board-input.json
