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
``BOARD_HEIGHT`` (24 x 54 mm), corners rounded ``CORNER_RADIUS``. Unrouted:
the power section was re-placed on 2026-10-05 to shorten the board from
66 mm (user request), which invalidated the earlier routes; routing is the
next step.

Frame: origin at the board centre, x right, y up, top view; the ZIF edge is
the TOP edge (+y), the wire pads sit at the BOTTOM edge. Layer 0 = top copper,
layer -1 = bottom. All parts on the top side. Heights are given from the
edge they hang off: "yt" from the top edge for the ZIF / data band / XIAO
(their distances to the top edge are what the column's neck and USB slot are
built around, and did not change when the board was shortened), "yb" from
the bottom edge for the power section and wire pads.

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
- Power section (re-placed 2026-10-05 for length), two tiers across the
  22 mm between the edge strips:

  - Tier 1, beside and above the wire pads: SMBJ5.0A TVS upright in the
    left column (anode down, next to the GND wire pad; cathode up), fuse
    upright in the right column (VIN pad down, next to the +5V wire pad;
    VFUSE pad up), AO4407A lying across the middle above the wire pads
    (drain pins right, facing the fuse's VFUSE pad; source pins left), the
    gate resistor between TVS and FET (GND end down, gate end up).
  - Tier 2, under the XIAO: the bulk ``MlccBank`` (4 x 100 uF 1206, user
    decision 2026-10-05, replacing the 14.5 mm 1000 uF can) in a row,
    VLED pads down into the VLED pour, GND pads up with a GND via beside
    each; the SS54 lying along x at the right with its cathode straight
    below the XIAO's VBUS pad.

  The 5.5 A VLED path leaves the FET source pins through the via cluster
  just left of them into a bottom-layer VLED "tongue" that joins the bottom
  VLED strip (see Copper).
- Wire pads at the bottom edge, cable-tie holes below them.

Edge strips: the board slides into grooves in the column halves, so a
``EDGE_STRIP`` (1.0 mm) strip along BOTH long edges carries no copper (the
pour / signal area is the outline inset by 1.0 mm on the long sides) and no
part courtyard, with one deliberate exception: the XIAO's USB-C receptacle
(and, if a card is inserted, the microSD card above it) overhangs the right
strip, where the column wall needs its USB slot anyway, which interrupts the
groove over ``XiaoESP32S3SMD.USB_HALF_WIDTH`` either side of the USB centre.

Copper (1 oz outer, 35 um):

- Bottom: GND everywhere except VLED: the tongue ``VLED_TONGUE_YB`` (3.3 mm
  tall) from the FET-source via cluster right to ``VLED_SPLIT_X``, then the
  strip ``VLED_SPLIT_X`` .. +11 mm (4.5 mm of copper less clearances,
  ~4.1 mm) up to the top edge, widening behind the ZIF. The GND return runs
  left of the tongue (5.6 mm) and left of the strip (over 16 mm).
- Top: VIN (wire pad + to fuse) and VFUSE (fuse to FET drain) hulls,
  ``POWER_PAD_MARGIN`` around their pads; VLED around the FET source / TVS /
  bulk MLCC VLED pads / Schottky anode and its stitching vias; the VLED
  band behind ZIF contacts 1-7 (``ZIF_BAND_DEPTH`` = 3.2 mm deep) with its
  vias; GND (rank 0) everywhere else, including the GND band behind contacts
  9-16. Each power pour is kept ``NET_GAP`` clear of the other nets' pads and
  vias inside its hull, so the GND pour reaches the gate resistor's GND end.
- For scale (same reference as the flat board): IPC-2152 puts 5 A on 1 oz
  outer copper at roughly 2.5-3 mm for a 10 C rise; every 5.5 A path here is
  >= 3 mm: bottom VLED tongue 3.3 mm and strip ~4.1 mm, top VLED band
  3.2 mm (it carries at most 5 of the 7 contacts' current, ~3.9 A,
  sideways), VIN / VFUSE hulls >= 3.4 mm, GND >= 5.6 mm.

Thermal relief: the bulk MLCCs keep the default 4 x 0.4 mm relief (not
``HighCurrentPadTag``): they carry only the LED PWM ripple, not the 5 A DC,
and a symmetric light relief on both ends keeps a 1206 from tombstoning in
reflow.

Heights (top side, above the board): XIAO ESP32S3 Sense stack without camera
8.04 mm -- the tallest (8.50 mm with a microSD card, 13.96 mm if the camera
were fitted; Seeed 3D model); fuse 2.94; TVS 2.61; SS54 2.45; ZIF 2.0 (lid
closed); bulk MLCCs 1.8 (1.6 +/- 0.2, Samsung thickness code Q); FET 1.75;
0603s < 1. Bottom side: no parts and no component leads (every part is
SMD); only the two 18 AWG wire solder joints (trim the strands to <= 1.5 mm).
"""

import math

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
from jitxlib.parts import Capacitor
from jitxlib.symbols.net_symbols import GroundSymbol, PowerSymbol
from shapely.geometry.base import BaseGeometry

from ..circuits.interface import (
    JLC_BASIC_CAPACITOR,
    JLC_BASIC_RESISTOR,
    At,
    InterfacePlacement,
    MlccBank,
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
    bulk_vled_pads,
    hull,
    nearest,
    pad_footprints,
    two_pin_pad_footprints,
)
from .layout_placements import layout_placements

# --- Outline ------------------------------------------------------------------------

BOARD_WIDTH = 24.0
"""Target <= 24 mm: the ZIF's fixing pads span 21.4 mm, plus the two 1.0 mm
groove strips and 0.3 mm of copper margin each side."""
BOARD_HEIGHT = 54.0
"""Set by the stack-up of courtyards, top to bottom: ZIF + data band + XIAO
35.41 mm (fixed: the ZIF edge, the data band and the XIAO's distance to
the top edge stay as they were on the 66 mm board), then the power section
18.59 mm from the XIAO courtyard (yb 18.59) down to the bottom edge:

- tie-hole band of the wire pads, yb 0.75 .. 4.25 (holes 1.0 mm from the
  edge);
- tier 1, 9.39 mm: the TVS (left) and the fuse (right) stand upright on the
  tie-hole band beside the wire pads, the FET (5.4 mm) sits on the pads'
  courtyard (yb 8.15) between them;
- tier 2, 4.8 mm: the 1206 MLCCs upright, the SS54 lying (4.55 mm).

What limits it: across the 22 mm between the edge strips, tier 1 is full
(TVS 5.94 + gate resistor 1.65 + FET 7.6 + fuse 5.14 = 20.3 mm of
courtyard) and tier 2 nearly so (4 x 2.5 + 3 x 0.6 via gaps + SS54 8.5).
Every other arrangement tried (rectangle packing over all rotations and
wire-pad x offsets) that keeps the power path short came out longer; the
shortest packing found that ignores the wiring (~1 mm shorter) strands the
fuse away from the +5V pad or the TVS / MLCCs away from VLED."""
CORNER_RADIUS = 1.0
EDGE_STRIP = 1.0
"""Copper- and component-free strip along both long edges (groove engagement)."""
ZIF_EDGE_INSET = 0.5
"""ZIF cable-entry face to the top edge: just inside, so the entry-face
silkscreen line (0.12 mm) stays on the board."""
USB_EDGE_INSET = 0.0
"""XIAO USB-C receptacle face to the right edge: flush."""

# --- Placement, top section (y from the TOP edge, "yt"; x from the centre) -------------

XIAO_YT = 25.7
"""XIAO pad-field centre below the top edge; its courtyard (+/-9.71) clears
the data band above and ends at yt 35.41 (yb 18.59)."""
DATA_ROW_YT = 14.1
"""Centre of the 33 Ohm / divider / buffer row, between the XIAO courtyard
(top at yt 15.99) and the decoupling-cap row."""
CAP_ROW_YT = 10.65
"""Centre of the decoupling-cap row; each cap's top (VLED) pad reaches into
the VLED band behind the ZIF."""

# --- Placement, power section (y from the BOTTOM edge, "yb") ---------------------------

WIRE_PADS_YB = 6.5
"""Wire-pad row: tie holes (TIE_DY = 4.0 below, 3.0 mm) end 1.0 mm above the
bottom edge. The pads' courtyard is a "T": tie-hole band to yb 4.25 across
+/-7.25, pads to yb 8.15 across +/-4.19."""
TVS_XYB = (-7.98, 9.0)
"""TVS upright in the left column: courtyard (5.94 x 9.39) from the tie-hole
band (yb 4.3) to 13.7, 0.05 inside the left edge strip."""
FUSE_XYB = (8.38, 8.9)
"""Fuse upright in the right column: courtyard (5.14 x 9.2) yb 4.3 .. 13.5,
0.05 inside the right edge strip."""
FET_XYB = (1.91, 10.9)
"""FET lying across the middle on the wire pads' courtyard (yb 8.2 .. 13.6),
right courtyard edge 0.1 short of the fuse's."""
GATE_R_XYB = (-3.45, 9.78)
"""Gate resistor upright in the 3.1 mm between the TVS and FET courtyards."""
TIER2_YB = 13.745
"""Floor of tier 2: just above the TVS courtyard (the tallest of tier 1)."""
BULK_XS = (-9.7, -6.6, -3.5, -0.4)
"""Bulk MLCC centres, x: 3.1 mm pitch (1206 courtyards 2.5 mm wide) leaves
1.3 mm between neighbouring pads for each MLCC's GND via."""
BULK_YB = TIER2_YB + 2.4
"""Bulk MLCC row height: courtyards (+/-2.4) from the tier-2 floor up to
0.05 below the XIAO courtyard."""
BULK_VIA_DX = 1.55
"""Bulk MLCC GND pad centre to its GND via, toward +x (half the pitch)."""
SCHOTTKY_YB = TIER2_YB + 2.275
"""SS54 centre height: lying along x, courtyard (+/-2.275) on the tier-2 floor."""
SCHOTTKY_K_DX = 2.2
"""SS54 centre to its cathode pad centre (half the 4.4 mm pad pitch); rotate
-90 puts the cathode at +x."""

# --- Copper -----------------------------------------------------------------------------

TOP_LAYER = 0
BOTTOM_LAYER = -1
VLED_SPLIT_X = 6.5
"""Bottom layer: VLED to the right of this x (above the tongue), GND to the
left (mm)."""
VLED_TONGUE_YB = (10.8, 14.1)
"""Bottom-layer VLED tongue, yb range (3.3 mm): carries the 5.5 A from the
FET-source vias right to the strip; runs under the FET and fuse."""
VLED_TONGUE_X0 = -5.4
"""Left end of the tongue, just past the leftmost FET-source via."""
ZIF_BAND_DEPTH = 3.2
"""Depth of the top-layer VLED / GND bands behind the ZIF contacts, from the
contacts' rear pad edge (mm)."""
ZIF_VIA_ROWS = (1.0, 2.2)
"""ZIF GND / VLED via rows, distance from the contacts' rear pad edge (mm)."""
ZIF_VLED_VIAS = ((7.0, 8.2, 9.4, 10.6), (9.4, 10.6))
"""VLED via columns in the band behind the ZIF, per row of ``ZIF_VIA_ROWS``,
over the bottom VLED strip (contacts 1 and 2 are at x 7.5 / 6.5). The
second row stops short of the buffer's 100 nF top pad."""
POWER_VLED_VIAS_XYB = [
    (-2.25, 11.7),
    (-2.25, 12.9),
    (-3.45, 11.85),
    (-3.45, 13.05),
    (-4.6, 11.85),
    (-4.6, 13.05),
]
"""VLED vias from the top power-section VLED region to the bottom tongue: a
column just left of the FET source pins, two more above the gate resistor
(clear of its top pad and of the MLCC VLED pads above)."""
VLED_MARGIN = 0.8
"""Growth of the power-section VLED pad hull (mm)."""

# --- Silkscreen -------------------------------------------------------------------------

TITLE_LINES = ("pappalapap", "column v1")
TITLE_SIZE = 0.9
TITLE_XYT = (-6.5, 13.0)
LABEL_SIZE = 1.0
PIN_LABEL_DX = 1.4
"""ZIF contact 1 / 16 pad centre to its "1" / "16" label, outward along x (mm)."""
PIN_LABEL_DY = 0.4
"""ZIF contacts' rear pad edge to the label centre, toward the contacts (mm)."""


def yb(y_from_bottom: float) -> float:
    """Board-frame y of a height measured from the bottom edge."""
    return y_from_bottom - BOARD_HEIGHT / 2


def yt(y_from_top: float) -> float:
    """Board-frame y of a depth measured down from the top edge."""
    return BOARD_HEIGHT / 2 - y_from_top


def at_yb(x: float, y_from_bottom: float, rotate: float = 0.0) -> At:
    """Placement from (x, height above the bottom edge)."""
    return At(x, yb(y_from_bottom), rotate)


def at_yt(x: float, y_from_top: float, rotate: float = 0.0) -> At:
    """Placement from (x, depth below the top edge)."""
    return At(x, yt(y_from_top), rotate)


def column_board_placement() -> InterfacePlacement:
    """Part placement for the column board, origin at the board centre."""
    right, top = BOARD_WIDTH / 2, BOARD_HEIGHT / 2
    # ZIF: rotate 180 -> entry face (local ENTRY_FACE_Y < 0) toward +y, at
    # the top edge less the inset; insertion direction (local +y) -> -y.
    zif_y = top - ZIF_EDGE_INSET + XFCN_F1002B16.ENTRY_FACE_Y
    # XIAO: USB-C (local +x) flush with the right edge.
    xiao_x = right - USB_EDGE_INSET - XiaoESP32S3SMD.USB_MAX_X
    vbus_x = xiao_x + XiaoESP32S3SMD.vbus_position()[0]
    data, caps = DATA_ROW_YT, CAP_ROW_YT
    return InterfacePlacement(
        # Wire pads: +5V (pad 1) at +x, GND at -x; wires and tie holes
        # toward the bottom edge.
        power_input=at_yb(0.0, WIRE_PADS_YB),
        # Fuse upright; rotate 180 puts p1 (VIN, local +y) at the bottom,
        # level with the +5V pad, and p2 (VFUSE) at the top, level with the
        # FET's drain pins.
        fuse=at_yb(*FUSE_XYB, 180),
        # SOIC-8 rotate 0: drain pins 5-8 at +x facing the fuse, source pins
        # 1-3 at -x facing the via cluster, gate (pin 4) bottom-left toward
        # the gate resistor.
        fet=at_yb(*FET_XYB),
        # Gate resistor rotate 0: p1 (gate, local +y) up, p2 (GND) down onto
        # the GND pour around the GND wire pad.
        gate_r=at_yb(*GATE_R_XYB),
        # TVS upright, rotate 0: K (local +y) up toward the VLED region, A
        # down, next to the GND wire pad (short clamp-current return).
        tvs=at_yb(*TVS_XYB),
        # Bulk MLCCs in a row on tier 2, rotate 180: p1 (VLED, the chip
        # landpattern's first pad, local +y) down into the VLED region, p2
        # (GND) up (asserted in ColumnLayout).
        bulk=tuple(at_yb(x, BULK_YB, 180) for x in BULK_XS),
        # Schottky lying along x, rotate -90: K (local +y) at +x, straight
        # below the XIAO's VBUS pad (pad 14); A at -x in the VLED region.
        schottky=at_yb(vbus_x - SCHOTTKY_K_DX, SCHOTTKY_YB, -90),
        xiao=At(xiao_x, yt(XIAO_YT)),
        zif=At(0.0, zif_y, 180),
        # Data row, left to right: 33 Ohm (under ZIF contact 9 = DIN),
        # DRET 10 k (under contact 8), DRET 20 k, buffer, buffer pull-down.
        din_r=at_yt(-1.2, data),
        dret_r=at_yt(0.6, data),
        dret_div=at_yt(2.4, data),
        # Buffer rotate 0: VCC top-right (toward the VLED band and its
        # 100 nF), GND bottom-left (over bottom GND), A left, Y bottom-right.
        buffer=at_yt(5.5, data),
        pulldown=at_yt(8.9, data),
        # Cap row: 100 nF at contact 7, 10 uF toward contact 1, buffer 100 nF.
        zif_c100n=at_yt(2.0, caps),
        zif_c10u=at_yt(5.5, caps),
        buffer_c=at_yt(7.9, caps),
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
            XiaoESP32S3SMD, WirePads, MlccBank(), column_board_placement()
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

        # --- Power-section pads, by net ------------------------------------------
        # The fuse is unpolarized with no explicit pad mapping: its pads are
        # told apart by position (the one nearer the +5V wire pad is VIN).
        wire_vin = pad_footprints(iface.power_in, [iface.input_plus()], frame)
        wire_gnd = pad_footprints(iface.power_in, [iface.input_minus()], frame)
        fet_drain = pad_footprints(iface.fet, [iface.fet.D], frame)
        fet_source = pad_footprints(iface.fet, [iface.fet.S], frame)
        fet_gate = pad_footprints(iface.fet, [iface.fet.G], frame)
        fuse_pads = all_pad_footprints(iface.fuse, frame)
        fuse_in = nearest(fuse_pads, wire_vin)
        fuse_out = nearest(fuse_pads, fet_drain)
        assert fuse_in is not fuse_out, "fuse pads do not face wire pad and FET"
        (tvs_cathode,) = pad_footprints(iface.tvs, [iface.tvs.K], frame)
        (tvs_anode,) = pad_footprints(iface.tvs, [iface.tvs.A], frame)
        gate_r_gate, gate_r_gnd = two_pin_pad_footprints(iface.r_gate, frame)
        (schottky_k,) = pad_footprints(iface.schottky, [iface.schottky.K], frame)
        bulk_pads: list[tuple[shapely.Polygon, shapely.Polygon]] = []
        for cap in iface.bulk:
            assert isinstance(cap, Capacitor), "column board bulk is an MlccBank"
            vled_pad, gnd_pad = two_pin_pad_footprints(cap, frame)
            assert vled_pad.centroid.y < gnd_pad.centroid.y, "MLCC VLED pad below"
            bulk_pads.append((vled_pad, gnd_pad))
        (xiao_vbus,) = pad_footprints(iface.xiao, [iface.xiao.VBUS], frame)
        assert abs(schottky_k.centroid.x - xiao_vbus.centroid.x) < 0.01, (
            "SS54 cathode not under the XIAO VBUS pad"
        )

        # --- Power-section vias ------------------------------------------------------
        via = JLC2L16.THVia
        via_pad = via.diameter
        assert isinstance(via_pad, float), "THVia pad is a plain diameter"
        power_vled_via_xy = [(x, yb(y)) for x, y in POWER_VLED_VIAS_XYB]
        # TVS anode: two GND vias beyond the anode pad, away from the cathode.
        ax, ay = tvs_anode.centroid.x, tvs_anode.centroid.y
        kx, ky = tvs_cathode.centroid.x, tvs_cathode.centroid.y
        span = math.hypot(ax - kx, ay - ky)
        ux, uy = (ax - kx) / span, (ay - ky) / span
        assert min(abs(ux), abs(uy)) < 1e-9, "TVS lies along x or y"
        x0, y0, x1, y1 = tvs_anode.bounds
        reach = (x1 - x0) / 2 if ux else (y1 - y0) / 2
        bx, by = ax + ux * (reach + TVS_VIA_GAP), ay + uy * (reach + TVS_VIA_GAP)
        tvs_gnd_via_xy = [(bx - uy * s, by + ux * s) for s in (-0.6, 0.6)]
        # Bulk MLCCs: one GND via beside each GND pad, between it and the
        # next MLCC's.
        bulk_gnd_via_xy = [
            (gnd.centroid.x + BULK_VIA_DX, gnd.centroid.y) for _, gnd in bulk_pads
        ]

        def dots(xys: list[tuple[float, float]]) -> list[shapely.Polygon]:
            return [shapely.Point(x, y).buffer(via_pad / 2) for x, y in xys]

        gnd_via_dots = dots(tvs_gnd_via_xy + bulk_gnd_via_xy)

        # --- Power section, top: VIN, VFUSE, VLED -------------------------------
        # Each region is kept NET_GAP clear of every other net's pads and vias
        # inside its hull, so no pad is swallowed by a foreign pour.
        vled_features = [
            *fet_source,
            tvs_cathode,
            *bulk_vled_pads(iface, frame),
            *pad_footprints(iface.schottky, [iface.schottky.A], frame),
            *dots(power_vled_via_xy),
        ]
        gnd_features = [
            *wire_gnd,
            tvs_anode,
            gate_r_gnd,
            *(gnd for _, gnd in bulk_pads),
            *gnd_via_dots,
        ]
        other_features = [*fet_gate, gate_r_gate, schottky_k]
        vin_features = [*wire_vin, fuse_in]
        vfuse_features = [fuse_out, *fet_drain]

        def clear_of(
            region: BaseGeometry, *foreign: list[shapely.Polygon]
        ) -> shapely.Polygon:
            """``region`` less ``NET_GAP`` around the other nets' features,
            inside the copper area; one connected piece."""
            keepout = shapely.union_all([f for fs in foreign for f in fs])
            out = region.difference(keepout.buffer(NET_GAP)).intersection(copper_area)
            assert isinstance(out, shapely.Polygon), "power pour is in pieces"
            return out

        vin_region = clear_of(
            hull(vin_features, POWER_PAD_MARGIN),
            vfuse_features,
            vled_features,
            gnd_features,
            other_features,
        )
        vfuse_region = clear_of(
            hull(vfuse_features, POWER_PAD_MARGIN),
            [vin_region],
            vled_features,
            gnd_features,
            other_features,
        )
        power_vled_region = clear_of(
            hull(vled_features, VLED_MARGIN),
            [vin_region, vfuse_region],
            gnd_features,
            other_features,
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

        # --- Bottom: VLED tongue + strip (right), GND (rest) ------------------------
        tongue_y0, tongue_y1 = (yb(y) for y in VLED_TONGUE_YB)
        assert all(
            VLED_TONGUE_X0 + via_pad / 2 < x
            and tongue_y0 + via_pad / 2 < y < tongue_y1 - via_pad / 2
            for x, y in power_vled_via_xy
        ), "FET-source vias outside the bottom VLED tongue"
        vled_strip = shapely.union_all(
            [
                shapely.box(VLED_TONGUE_X0, tongue_y0, VLED_SPLIT_X, tongue_y1),
                shapely.box(VLED_SPLIT_X, tongue_y0, cx, top_copper),
                shapely.box(vx0 - NET_GAP, band_bottom, cx, top_copper),
            ]
        ).intersection(copper_area)
        self.vled_strip = vled_strip

        # Pours are members of this circuit and of their nets.
        self.vin_pour = Pour(as_shape(vin_region), TOP_LAYER, rank=1)
        self.vfuse_pour = Pour(as_shape(vfuse_region), TOP_LAYER, rank=1)
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
        self.power_vled_vias = [via().at(x, y) for x, y in power_vled_via_xy]
        self.tvs_gnd_vias = [via().at(x, y) for x, y in tvs_gnd_via_xy]
        self.bulk_gnd_vias = [via().at(x, y) for x, y in bulk_gnd_via_xy]
        for v in [*self.power_vled_vias, *self.zif_vled_vias]:
            self.vled += v
        for v in [*self.zif_gnd_vias, *self.tvs_gnd_vias, *self.bulk_gnd_vias]:
            self.gnd += v

        # --- High-current pads (bulk MLCCs: default relief, see docstring) -------
        HighCurrentPadTag().assign(iface.power_in, iface.fuse, iface.fet, iface.tvs)

        # --- Silkscreen -------------------------------------------------------------
        contact_1, *_, contact_16 = all_contacts
        assert contact_1.centroid.x > contact_16.centroid.x, "ZIF pin 1 must be at +x"
        label_y = rear + PIN_LABEL_DY
        tx, ty = TITLE_XYT
        self.labels = [
            Silkscreen(Text(line, TITLE_SIZE).at(tx, yt(ty) - k * 1.6 * TITLE_SIZE))
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
