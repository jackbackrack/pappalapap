"""Column board: narrow vertical controller board inside the sculpture's column.

``jitx build pappalapap.designs.column_board.ColumnBoard``

Replaces the flat interface board (user decision 2026-10-03): the sculpture
floats on a hollow column, the controller slides into grooves in the two
column halves, the flex strip's tail drops straight down into the ZIF at this
board's top edge, and only two 18 AWG wires (+5 V, GND, up to ~5.5 A) come up
the column from the base. Same circuit as the flat board (``XiaoInterface``),
with the XIAO ESP32S3 Sense soldered on its castellations
(``XiaoESP32S3SMD``, camera not fitted) and two solder-in wire pads
(``WirePads``) in place of the screw terminal.

A 2-layer 1.6 mm JLCPCB board (``JLC2L16``), ``BOARD_WIDTH`` x
``BOARD_HEIGHT`` (24 x 66 mm), corners rounded ``CORNER_RADIUS``. Unrouted;
routing is the next step.

Frame: origin at the board centre, x right, y up, top view; the ZIF edge is
the TOP edge (+y), the wire pads sit at the BOTTOM edge. Layer 0 = top copper,
layer -1 = bottom. All parts on the top side.

Placement, top to bottom (see ``column_board_placement``):

- ZIF (XFCN F1002-B-16) rotated 180 degrees, so its cable-entry face (local
  -y) faces +y, ``ZIF_EDGE_INSET`` inside the top edge, and the insertion
  direction points down (-y) into the board: the flex drops straight in.
  Rotating 180 puts contact 1 at +x. ``scripts/check_zif_mating.py`` proves
  pin 1 against the flex tail as built and checks the entry face / insertion
  direction against this outline.
- Data band right under the ZIF: VLED / GND stitching vias behind the
  contacts, the 10 uF + 100 nF at the VLED contacts, then one row with the
  33 Ohm, DRET 10 k / 20 k divider, 74AHCT1G125 and its 10 k pull-down.
- XIAO with its USB-C receptacle face flush with the RIGHT long edge
  (nothing in front of it), pin rows across the board: D0/D1 face the data
  band, VBUS/GND face the power section.
- Power section: SS54 (straight below the XIAO's VBUS pad), SMBJ5.0A TVS,
  gate resistor, AO4407A, 1000 uF bulk can, fuse.
- Wire pads at the bottom edge, cable-tie holes below them.

Edge strips: the board slides into grooves in the column halves, so a
``EDGE_STRIP`` (1.0 mm) strip along BOTH long edges carries no copper (the
pour / signal area is the outline inset by 1.0 mm on the long sides) and no
part courtyard, with one deliberate exception: the XIAO's USB-C receptacle
(and, if a card is inserted, the microSD card above it) overhangs the right
strip, where the column wall needs its USB slot anyway, which interrupts the
groove over ``XiaoESP32S3SMD.USB_HALF_WIDTH`` either side of the USB centre.

Copper (1 oz outer, 35 um):

- Bottom: GND everywhere except ``VLED_STRIP``: VLED from the power section
  to the top edge, ``VLED_SPLIT_X`` .. +11 mm (4.5 mm of copper less
  clearances, ~4.1 mm), widening behind the ZIF. The GND return (left of the
  split) is over 16 mm wide.
- Top: VIN (wire pad + to fuse) and VFUSE (fuse to FET drain) hulls,
  ``POWER_PAD_MARGIN`` around their pads; VLED around the FET source / TVS /
  bulk + / Schottky anode and its stitching vias; the VLED band behind ZIF
  contacts 1-7 (``ZIF_BAND_DEPTH`` = 3.2 mm deep) with its vias; GND
  (rank 0) everywhere else, including the GND band behind contacts 9-16.
- For scale (same reference as the flat board): IPC-2152 puts 5 A on 1 oz
  outer copper at roughly 2.5-3 mm for a 10 C rise; every 5.5 A path here is
  >= 3 mm: bottom VLED strip ~4.1 mm, top VLED band 3.2 mm (it carries at
  most 5 of the 7 contacts' current, ~3.9 A, sideways), VIN / VFUSE hulls
  >= 3.4 mm, GND > 16 mm.

Heights (top side, above the board): 1000 uF can 14.5 mm max (13 + 1.5,
Chengx drawing) -- the tallest; XIAO ESP32S3 Sense stack without camera
8.04 mm (8.50 mm with a microSD card, 13.96 mm if the camera were fitted;
Seeed 3D model); fuse 2.94; TVS 2.61; SS54 2.45; ZIF 2.0 (lid closed);
FET 1.75; 0603s < 1. Bottom side: no parts, only the THT leads of the bulk
can (trim to <= 1.5 mm) and the two wire solder joints.
"""

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
from jitx.feature import Silkscreen
from jitx.net import Net
from jitx.shapes.primitive import Text
from jitxlib.symbols.net_symbols import GroundSymbol, PowerSymbol
from shapely.geometry.base import BaseGeometry

from ..circuits.interface import (
    JLC_BASIC_CAPACITOR,
    JLC_BASIC_RESISTOR,
    At,
    InterfacePlacement,
    XiaoInterface,
    XiaoSupplyTag,
)
from ..circuits.led_strip import GroundTag, PowerTag
from ..components.wire_pads import WirePads
from ..components.xfcn_f1002b16 import XFCN_F1002B16
from ..components.xiao_esp32s3_smd import XiaoESP32S3SMD
from ..substrate_rigid import JLC2L16
from .interface_board import (
    DEFAULT_CLEARANCE,
    DEFAULT_TRACE_WIDTH,
    HIGH_CURRENT_SPOKE_WIDTH,
    NET_GAP,
    POWER_PAD_MARGIN,
    POWER_TRACE_WIDTH,
    THERMAL_GAP,
    THERMAL_SPOKE_WIDTH,
    THERMAL_SPOKES,
    TVS_VIA_GAP,
    XIAO_SUPPLY_WIDTH,
    HighCurrentPadTag,
    all_pad_footprints,
    as_shape,
    hull,
    nearest,
    pad_footprints,
)
from .layout_placements import layout_placements

# --- Outline ------------------------------------------------------------------------

BOARD_WIDTH = 24.0
"""Target <= 24 mm: the ZIF's fixing pads span 21.4 mm, plus the two 1.0 mm
groove strips and 0.3 mm of copper margin each side."""
BOARD_HEIGHT = 66.0
"""Set by the stack-up of courtyards, top to bottom: ZIF 7.1 mm (incl. edge
inset), data band 8.9 mm, XIAO 19.4 mm, power section 25.6 mm (TVS / SS54
row 8.5, FET + bulk 7.6-14.5, fuse 9.2), wire pads + tie holes 5 mm."""
CORNER_RADIUS = 1.0
EDGE_STRIP = 1.0
"""Copper- and component-free strip along both long edges (groove engagement)."""
ZIF_EDGE_INSET = 0.5
"""ZIF cable-entry face to the top edge: just inside, so the entry-face
silkscreen line (0.12 mm) stays on the board."""
USB_EDGE_INSET = 0.0
"""XIAO USB-C receptacle face to the right edge: flush."""

# --- Placement (y from the BOTTOM edge, "yb"; x from the centre) ----------------------

WIRE_PADS_YB = 6.5
"""Wire-pad row: tie holes (TIE_DY = 4.0 below, 3.0 mm) end 1.0 mm above the
bottom edge."""
FUSE_XYB = (7.5, 9.5)
FET_XYB = (7.5, 17.9)
BULK_XYB = (-3.75, 15.4)
GATE_R_XYB = (2.6, 24.4)
TVS_XYB = (-5.3, 26.62)
SCHOTTKY_YB = 25.95
"""SS54 centre height: courtyard clears the FET below and the XIAO above."""
XIAO_YB = 40.3
"""XIAO pad-field centre: courtyard (+/-9.71) clears the TVS row below."""
DATA_ROW_YB = 51.9
"""Centre of the 33 Ohm / divider / buffer row, between the XIAO courtyard
(top at yb 50.0) and the decoupling-cap row."""
CAP_ROW_YB = 55.35
"""Centre of the decoupling-cap row; each cap's top (VLED) pad reaches into
the VLED band behind the ZIF."""

# --- Copper -----------------------------------------------------------------------------

TOP_LAYER = 0
BOTTOM_LAYER = -1
VLED_SPLIT_X = 6.5
"""Bottom layer: VLED to the right of this x, GND to the left (mm)."""
ZIF_BAND_DEPTH = 3.2
"""Depth of the top-layer VLED / GND bands behind the ZIF contacts, from the
contacts' rear pad edge (mm)."""
ZIF_VIA_ROWS = (1.0, 2.2)
"""ZIF GND / VLED via rows, distance from the contacts' rear pad edge (mm)."""
ZIF_VLED_VIAS = ((7.0, 8.2, 9.4, 10.6), (9.4, 10.6))
"""VLED via columns in the band behind the ZIF, per row of ``ZIF_VIA_ROWS``,
over the bottom VLED strip (contacts 1 and 2 are at x 7.5 / 6.5). The
second row stops short of the buffer's 100 nF top pad."""
POWER_VLED_VIAS_XYB = [(10.3, 22.2), (10.3, 23.4), (10.3, 24.6), (10.3, 25.8)]
"""VLED vias from the top power-section VLED region (FET source, SS54 anode)
to the bottom strip; one column right of the FET source pads and the SS54
anode, clear of both courtyards."""
VLED_MARGIN = 0.8
"""Growth of the power-section VLED pad hull (mm)."""

# --- Silkscreen -------------------------------------------------------------------------

TITLE_LINES = ("pappalapap", "column v1")
TITLE_SIZE = 0.9
TITLE_XYB = (-6.5, 53.0)
LABEL_SIZE = 1.0
PIN_LABEL_DX = 1.4
"""ZIF contact 1 / 16 pad centre to its "1" / "16" label, outward along x (mm)."""
PIN_LABEL_DY = 0.4
"""ZIF contacts' rear pad edge to the label centre, toward the contacts (mm)."""


def yb(y_from_bottom: float) -> float:
    """Board-frame y of a height measured from the bottom edge."""
    return y_from_bottom - BOARD_HEIGHT / 2


def at_yb(x: float, y_from_bottom: float, rotate: float = 0.0) -> At:
    """Placement from (x, height above the bottom edge)."""
    return At(x, yb(y_from_bottom), rotate)


def column_board_placement() -> InterfacePlacement:
    """Part placement for the column board, origin at the board centre."""
    right, top = BOARD_WIDTH / 2, BOARD_HEIGHT / 2
    # ZIF: rotate 180 -> entry face (local ENTRY_FACE_Y < 0) toward +y, at
    # the top edge less the inset; insertion direction (local +y) -> -y.
    zif_y = top - ZIF_EDGE_INSET + XFCN_F1002B16.ENTRY_FACE_Y
    # XIAO: USB-C (local +x) flush with the right edge.
    xiao_x = right - USB_EDGE_INSET - XiaoESP32S3SMD.USB_MAX_X
    data, caps = DATA_ROW_YB, CAP_ROW_YB
    return InterfacePlacement(
        # Wire pads: +5V (pad 1) at +x below the fuse, GND at -x; wires and
        # tie holes toward the bottom edge.
        power_input=at_yb(0.0, WIRE_PADS_YB),
        # Fuse upright; rotate 180 puts p1 (VIN, local +y) at the bottom,
        # next to the +5V pad, and p2 (VFUSE) at the top, under the FET.
        fuse=at_yb(*FUSE_XYB, 180),
        # SOIC-8 drain pins 5-8 are at local +x; rotate -90 turns them down
        # toward the fuse, source pins 1-3 up toward the SS54 / VLED vias,
        # gate (pin 4) top-left toward the gate resistor.
        fet=at_yb(*FET_XYB, -90),
        gate_r=at_yb(*GATE_R_XYB),
        # TVS lying along x on the left; rotate -90 puts K (local +y) at +x,
        # toward the VLED region, A at the left (GND).
        tvs=at_yb(*TVS_XYB, -90),
        # Bulk can bottom-left, + (local +y) up toward the VLED region.
        bulk=at_yb(*BULK_XYB),
        # Schottky upright straight below the XIAO's VBUS pad (pad 14):
        # K (local +y) up to VBUS, A down into the VLED region.
        schottky=at_yb(xiao_x + XiaoESP32S3SMD.vbus_position()[0], SCHOTTKY_YB),
        xiao=At(xiao_x, yb(XIAO_YB)),
        zif=At(0.0, zif_y, 180),
        # Data row, left to right: 33 Ohm (under ZIF contact 9 = DIN),
        # DRET 10 k (under contact 8), DRET 20 k, buffer, buffer pull-down.
        din_r=at_yb(-1.2, data),
        dret_r=at_yb(0.6, data),
        dret_div=at_yb(2.4, data),
        # Buffer rotate 0: VCC top-right (toward the VLED band and its
        # 100 nF), GND bottom-left (over bottom GND), A left, Y bottom-right.
        buffer=at_yb(5.5, data),
        pulldown=at_yb(8.9, data),
        # Cap row: 100 nF at contact 7, 10 uF toward contact 1, buffer 100 nF.
        zif_c100n=at_yb(2.0, caps),
        zif_c10u=at_yb(5.5, caps),
        buffer_c=at_yb(7.9, caps),
    )


class ColumnBoardShape(Board):
    """Rounded rectangle; signal area inset ``EDGE_STRIP`` on the long edges."""

    def __init__(self, outline: BaseGeometry, signal_area: BaseGeometry) -> None:
        self.shape = as_shape(outline)
        self.signal_area = as_shape(signal_area)


class ColumnLayout(Circuit):
    """Interface circuit plus board-level copper, vias and silkscreen."""

    def __init__(self) -> None:
        self.iface = XiaoInterface(
            XiaoESP32S3SMD, WirePads, column_board_placement()
        ).at(0.0, 0.0)
        iface = self.iface
        frame = iface.transform
        w, h = BOARD_WIDTH, BOARD_HEIGHT

        # --- Outline and copper area -------------------------------------------
        rect = shapely.box(-w / 2, -h / 2, w / 2, h / 2)
        self.outline = rect.buffer(-CORNER_RADIUS).buffer(CORNER_RADIUS)
        # Long edges: EDGE_STRIP; short edges: the fab's copper-to-edge rule
        # (via the same inset, which is larger).
        cx = w / 2 - EDGE_STRIP
        cy = h / 2 - EDGE_STRIP
        copper_area = shapely.box(-cx, -cy, cx, cy)
        self.copper_area = copper_area

        # --- Nets: symbols here, tags on the circuit's own nets -----------------
        self.vin = Net([iface.vin], symbol=PowerSymbol())
        self.vfuse = Net([iface.vfuse], symbol=PowerSymbol())
        self.vled = Net([iface.vled], symbol=PowerSymbol())
        self.gnd = Net([iface.gnd], symbol=GroundSymbol())

        # --- Power section, top: VIN, VFUSE, VLED -------------------------------
        # The fuse is unpolarized with no explicit pad mapping: its pads are
        # told apart by position (the one nearer the +5V wire pad is VIN).
        wire_vin = pad_footprints(iface.power_in, [iface.input_plus()], frame)
        fet_drain = pad_footprints(iface.fet, [iface.fet.D], frame)
        fuse_pads = all_pad_footprints(iface.fuse, frame)
        fuse_in = nearest(fuse_pads, wire_vin)
        fuse_out = nearest(fuse_pads, fet_drain)
        assert fuse_in is not fuse_out, "fuse pads do not face wire pad and FET"
        vin_region = hull([*wire_vin, fuse_in], POWER_PAD_MARGIN)
        vfuse_region = hull([fuse_out, *fet_drain], POWER_PAD_MARGIN)

        via = JLC2L16.THVia
        self.power_vled_vias = [via().at(x, yb(y)) for x, y in POWER_VLED_VIAS_XYB]
        via_pad = via.diameter
        assert isinstance(via_pad, float), "THVia pad is a plain diameter"
        via_dots = [
            shapely.Point(x, yb(y)).buffer(via_pad / 2) for x, y in POWER_VLED_VIAS_XYB
        ]
        power_vled_pads = (
            pad_footprints(iface.fet, [iface.fet.S], frame)
            + pad_footprints(iface.tvs, [iface.tvs.K], frame)
            + pad_footprints(iface.bulk, [iface.bulk.pos], frame)
            + pad_footprints(iface.schottky, [iface.schottky.A], frame)
        )
        power_vled_region = (
            hull([*power_vled_pads, *via_dots], VLED_MARGIN)
            .difference(vin_region.buffer(NET_GAP))
            .difference(vfuse_region.buffer(NET_GAP))
            .intersection(copper_area)
        )

        # --- ZIF bands, top: VLED behind contacts 1-7, GND behind 9-16 ---------
        vled_contacts = pad_footprints(iface.zif, iface.zif_vled(), frame)
        all_contacts = pad_footprints(iface.zif, iface.zif.P, frame)
        # Rotated 180, the contacts' rear (inner) pad edge is their LOWER edge.
        _, rear, _, _ = shapely.union_all(all_contacts).bounds
        band_bottom = rear - ZIF_BAND_DEPTH
        vx0, _, _, _ = shapely.union_all(vled_contacts).bounds
        top_copper = h / 2 - EDGE_STRIP
        zif_vled_band = shapely.union_all(
            [shapely.box(vx0 - NET_GAP, band_bottom, cx, rear), *vled_contacts]
        ).intersection(copper_area)
        self.zif_vled_vias = [
            via().at(x, rear - row)
            for row, xs in zip(ZIF_VIA_ROWS, ZIF_VLED_VIAS, strict=True)
            for x in xs
        ]
        gnd_contacts = pad_footprints(iface.zif, iface.zif_gnd(), frame)
        self.zif_gnd_vias = [
            via().at(pad.centroid.x, rear - row)
            for row in ZIF_VIA_ROWS
            for pad in gnd_contacts
        ]
        # Behind contacts 9-16 the top layer is simply the rank-0 GND pour.

        # --- Bottom: VLED strip (right), GND (rest) -------------------------------
        strip_bottom = min(y for _, y in POWER_VLED_VIAS_XYB)
        vled_strip = shapely.union_all(
            [
                shapely.box(VLED_SPLIT_X, yb(strip_bottom) - 1.0, cx, top_copper),
                shapely.box(vx0 - NET_GAP, band_bottom, cx, top_copper),
            ]
        ).intersection(copper_area)
        self.vled_strip = vled_strip

        # Pours are members of this circuit and of their nets.
        self.vin_pour = Pour(
            as_shape(vin_region.intersection(copper_area)), TOP_LAYER, rank=1
        )
        self.vfuse_pour = Pour(
            as_shape(vfuse_region.intersection(copper_area)), TOP_LAYER, rank=1
        )
        self.vled_pours = [
            Pour(as_shape(power_vled_region), TOP_LAYER, rank=1),
            Pour(as_shape(zif_vled_band), TOP_LAYER, rank=1),
            Pour(as_shape(vled_strip), BOTTOM_LAYER, rank=1),
        ]
        self.gnd_pours = [
            Pour(as_shape(copper_area), TOP_LAYER, rank=0),
            Pour(as_shape(copper_area), BOTTOM_LAYER, rank=0),
        ]
        self.vin += self.vin_pour
        self.vfuse += self.vfuse_pour
        for pour in self.vled_pours:
            self.vled += pour
        for pour in self.gnd_pours:
            self.gnd += pour

        # --- Vias onto their nets --------------------------------------------------
        (tvs_anode,) = pad_footprints(iface.tvs, [iface.tvs.A], frame)
        tx0, ty0, _, ty1 = tvs_anode.bounds
        # TVS lies along x with its anode at -x: GND vias just left of it.
        self.tvs_gnd_vias = [
            via().at(tx0 - TVS_VIA_GAP, y) for y in (ty0 + 0.5, ty1 - 0.5)
        ]
        for v in [*self.power_vled_vias, *self.zif_vled_vias]:
            self.vled += v
        for v in [*self.zif_gnd_vias, *self.tvs_gnd_vias]:
            self.gnd += v

        # --- High-current pads --------------------------------------------------
        HighCurrentPadTag().assign(
            iface.power_in, iface.fuse, iface.fet, iface.tvs, iface.bulk
        )

        # --- Silkscreen -------------------------------------------------------------
        contact_1, *_, contact_16 = all_contacts
        assert contact_1.centroid.x > contact_16.centroid.x, "ZIF pin 1 must be at +x"
        label_y = rear + PIN_LABEL_DY
        tx, ty = TITLE_XYB
        self.labels = [
            Silkscreen(Text(line, TITLE_SIZE).at(tx, yb(ty) - k * 1.6 * TITLE_SIZE))
            for k, line in enumerate(TITLE_LINES)
        ] + [
            Silkscreen(
                Text("1", LABEL_SIZE).at(contact_1.centroid.x + PIN_LABEL_DX, label_y)
            ),
            Silkscreen(
                Text("16", LABEL_SIZE).at(contact_16.centroid.x - PIN_LABEL_DX, label_y)
            ),
        ]


class ColumnBoard(Design):
    """Column board (``jitx build pappalapap.designs.column_board.ColumnBoard``)."""

    resistor_defaults = JLC_BASIC_RESISTOR
    capacitor_defaults = JLC_BASIC_CAPACITOR

    def __init__(self) -> None:
        self.substrate = JLC2L16()
        self.circuit = ColumnLayout()
        self.board = ColumnBoardShape(self.circuit.outline, self.circuit.copper_area)
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
            "layout/column_board.json"
        )  # writes layout/column_board-input.json
