"""FPC tail gold fingers, 16 positions at 1.0 mm pitch (mechanical footprint).

There is no purchasable part here: the "component" is the exposed ENIG finger
field at the end of the flex tail. It plugs into an XFCN F1002-B-16-20T-R
(LCSC C481251) 1.0 mm, bottom-contact, flip-lock ZIF connector on the future
controller board.

Source: XFCN family drawing "FPC1.0mmPitch 掀盖卧式下接(H=2.0)", part no.
F1002-B-xx-20T-R, rev A1, dated 2024-05-28, one sheet
(docs/datasheets/XFCN_F1002-B-12-20T-R_C481250.pdf). Values come from the
view captioned "适用扁平线 (Applicable Flat Cable)" and the CKT/DIM table:

- Cable width ``(DIMB - 0.1) +/- 0.05``; table row 16: DIM A 15.00, DIM B
  17.10, so the tail is 17.00 +/- 0.05 mm wide.
- Conductor pitch ``1.00 +/- 0.05``; first-to-last conductor centre
  ``DIMA +/- 0.05`` = 15.00 mm (the DIMA arrows land on the conductor centres).
- Conductor width ``0.5`` (no tolerance shown; sheet general tolerance for
  .X is +/-0.25).
- Exposed conductor length ``3.5 Min.`` from the cable end.
- Stiffener ``4.0 Min.`` from the cable end; total thickness ``0.30 +/- 0.03``
  over the stiffened end.
- Connector contacts are ``N-0.20 +/- 0.02`` wide (PCB-layout view), so a
  0.5 mm finger leaves +/-0.15 mm lateral margin beyond the 0.05 pitch
  tolerance.

Design choices made here (not in the XFCN drawing; each is labelled):

- Finger setback from the tail end, 0.30 mm: JLC needs gold fingers >= 0.2 mm
  from the board edge, and ``JLCFlexRules.min_copper_edge_space`` is 0.3 mm.
  0.30 satisfies both, so the outline needs no DRC waiver. The XFCN drawing
  draws conductors to the cable end, but the connector contact lands well
  inside the end (Section A-A: 2.7 mm insertion, contact 1.2 mm from the
  stop), so the setback costs nothing.
- Coverlay opening 4.00 mm from the tail end (>= the 3.5 mm minimum) across
  the full tail width; the 16 fingers have no per-pad mask, the one landpattern
  Soldermask feature is the opening.
- Finger copper runs 0.50 mm under the coverlay (to 4.50 mm from the end) so
  the coverlay edge anchors the fingers against peeling where the tail flexes.
- PI stiffener 5.00 mm long (>= the 4.0 mm minimum), extended 1.0 mm past the
  coverlay edge so the stiffener's stress edge is not at the opening edge.

Thickness: ``JLCFlex2L.finger_thickness()`` (0.115 mm: 0.2 mm build minus the
removed top coverlay and the absent bottom copper) plus
``JLCFlex2L.pi_stiffener_for(0.30)`` (0.20 mm PI) = 0.315 mm, inside
0.30 +/- 0.03. JLC's gold-finger thickness tolerance is +/-0.03 mm.

Fabrication facts with no JITX field (must be specified when ordering at JLC):

- PI stiffener, 0.20 mm, on the BOTTOM face behind the fingers, from the tail
  end 5.00 mm inward, full tail width. Drawn here on the custom layer
  ``PIStiffener`` (bottom side) for the fab drawing only.
- ENIG finish over the fingers (the board's finish).
- No copper on the bottom layer behind the stiffened area (enforced by a
  bottom-layer pour/via/route KeepOut).

Coordinate frame (top view, top layer = flex top / LED face A): origin at the
centre of the tail's cut end; the flex body extends toward +y; pin 1 is at
x = -7.5, pin 16 at x = +7.5.
"""

from typing import ClassVar

from jitx.circuit import Circuit
from jitx.component import Component
from jitx.feature import Courtyard, Custom, KeepOut, Silkscreen, Soldermask
from jitx.landpattern import Landpattern, PadMapping
from jitx.layerindex import LayerSet, Side
from jitx.net import Port
from jitx.sample import SampleDesign
from jitx.shapes.composites import rectangle
from jitx.shapes.primitive import Circle, Polyline
from jitxlib.landpatterns.pads import SMDPad
from jitxlib.symbols.box import BoxSymbol, Column, PinGroup, Row

from pappalapap.substrate import JLCFlex2L

# --- XFCN F1002-B drawing, "Applicable Flat Cable" view, row N = 16 ----------
NUM_FINGERS = 16
PITCH = 1.00  # "1.00 +/- 0.05"
TAIL_WIDTH = 17.00  # (DIMB - 0.1) +/- 0.05, DIM B = 17.10 for 16P
TAIL_WIDTH_TOL = 0.05
FINGER_WIDTH = 0.50  # conductor width "0.5"
MIN_EXPOSED_LENGTH = 3.5  # "3.5 Min."
MIN_STIFFENER_LENGTH = 4.0  # "4.0 Min."
TOTAL_THICKNESS = 0.30  # "0.30 +/- 0.03"
TOTAL_THICKNESS_TOL = 0.03

# --- Design choices (see module docstring) ----------------------------------
FINGER_EDGE_SETBACK = 0.30  # >= JLC gold-finger-to-edge 0.2 and copper-to-edge 0.3
EXPOSED_LENGTH = 4.00  # coverlay opening depth from the tail end
COVERLAY_OVERLAP = 0.50  # finger copper tucked under the coverlay edge
FINGER_END = EXPOSED_LENGTH + COVERLAY_OVERLAP  # 4.50 from the tail end
FINGER_LENGTH = FINGER_END - FINGER_EDGE_SETBACK  # 4.20 copper length
STIFFENER_LENGTH = 5.00
STIFFENER_THICKNESS = JLCFlex2L.pi_stiffener_for(TOTAL_THICKNESS)  # 0.20 PI

# --- Drawing rules ----------------------------------------------------------
ANNOTATION_WIDTH = 0.10  # outline stroke on the custom annotation layer
SILK_CLEARANCE = 0.15  # JLC "Character to Pad Clearance >= 0.15mm"
PIN1_DOT_RADIUS = 0.25

FIRST_FINGER_X = -(NUM_FINGERS - 1) / 2 * PITCH  # -7.5

assert EXPOSED_LENGTH >= MIN_EXPOSED_LENGTH
assert STIFFENER_LENGTH >= MIN_STIFFENER_LENGTH
assert STIFFENER_LENGTH >= FINGER_END
assert (
    abs(JLCFlex2L.finger_thickness() + STIFFENER_THICKNESS - TOTAL_THICKNESS)
    <= TOTAL_THICKNESS_TOL
)


class PIStiffener(Custom):
    """Fab-drawing layer: polyimide stiffener outline (place on the bottom side)."""


class FpcTailOutline(Custom):
    """Fab-drawing layer: tail cut edge and sides over the stiffened end."""


class FpcTail16Landpattern(Landpattern):
    """16 top-layer gold fingers, one full-width coverlay opening, no paste."""

    def __init__(self) -> None:
        finger_y = (FINGER_EDGE_SETBACK + FINGER_END) / 2
        finger = rectangle(FINGER_WIDTH, FINGER_LENGTH)
        # Fingers are not soldered: no per-pad mask (the opening below covers
        # them all) and no paste.
        self.p = {
            i + 1: SMDPad(finger, soldermask=None, paste=None).at(
                FIRST_FINGER_X + i * PITCH, finger_y
            )
            for i in range(NUM_FINGERS)
        }

        self.coverlay_opening = Soldermask(
            rectangle(TAIL_WIDTH, EXPOSED_LENGTH).at(0.0, EXPOSED_LENGTH / 2)
        )

        stiffener = rectangle(TAIL_WIDTH, STIFFENER_LENGTH).at(
            0.0, STIFFENER_LENGTH / 2
        )
        self.stiffener = PIStiffener(stiffener, side=Side.Bottom)
        half = TAIL_WIDTH / 2
        self.tail_outline = FpcTailOutline(
            Polyline(
                ANNOTATION_WIDTH,
                [
                    (-half, STIFFENER_LENGTH),
                    (-half, 0.0),
                    (half, 0.0),
                    (half, STIFFENER_LENGTH),
                ],
            )
        )

        # Nothing on the bottom copper behind the stiffened end; no vias or
        # pour inside the coverlay opening on top.
        self.bottom_keepout = KeepOut(
            stiffener, LayerSet(-1), pour=True, via=True, route=True
        )
        self.top_keepout = KeepOut(
            rectangle(TAIL_WIDTH, EXPOSED_LENGTH).at(0.0, EXPOSED_LENGTH / 2),
            LayerSet(0),
            pour=True,
            via=True,
        )

        dot_y = FINGER_END + SILK_CLEARANCE + PIN1_DOT_RADIUS
        self.pin1_marker = Silkscreen(
            Circle(radius=PIN1_DOT_RADIUS).at(FIRST_FINGER_X, dot_y)
        )

        courtyard_top = max(STIFFENER_LENGTH, dot_y + PIN1_DOT_RADIUS)
        self.courtyard = Courtyard(
            rectangle(TAIL_WIDTH, courtyard_top).at(0.0, courtyard_top / 2)
        )


class FpcTail16(Component):
    """Flex-tail gold fingers mating an XFCN F1002-B-16-20T-R (16P, 1.0 mm).

    Pinout (approved 2026-10-03): 1-7 VDD, 8 DRET, 9 DIN, 10-16 GND.
    Geometry constants are exposed so the board outline can be drawn from them.
    """

    manufacturer = "n/a (flex tail fingers)"
    mpn = "FPC-TAIL-16P-1.0"
    reference_designator_prefix = "J"
    datasheet = "docs/datasheets/XFCN_F1002-B-12-20T-R_C481250.pdf"
    mating_connector: ClassVar[str] = "XFCN F1002-B-16-20T-R (LCSC C481251)"

    NUM_FINGERS: ClassVar[int] = NUM_FINGERS
    PITCH: ClassVar[float] = PITCH
    TAIL_WIDTH: ClassVar[float] = TAIL_WIDTH
    TAIL_WIDTH_TOL: ClassVar[float] = TAIL_WIDTH_TOL
    FINGER_WIDTH: ClassVar[float] = FINGER_WIDTH
    FINGER_EDGE_SETBACK: ClassVar[float] = FINGER_EDGE_SETBACK
    FINGER_LENGTH: ClassVar[float] = FINGER_LENGTH
    EXPOSED_LENGTH: ClassVar[float] = EXPOSED_LENGTH
    STIFFENER_LENGTH: ClassVar[float] = STIFFENER_LENGTH
    STIFFENER_THICKNESS: ClassVar[float] = STIFFENER_THICKNESS
    TOTAL_THICKNESS: ClassVar[float] = TOTAL_THICKNESS

    # Class-scope port arrays are the JITX structural idiom (each instance gets
    # its own ports), not shared mutable state; hence the RUF012 waivers.
    VDD = [Port() for _ in range(7)]  # noqa: RUF012
    DRET = Port()
    DIN = Port()
    GND = [Port() for _ in range(7)]  # noqa: RUF012

    landpattern = FpcTail16Landpattern()
    symbol = BoxSymbol(
        rows=Row(left=PinGroup(DIN), right=PinGroup(DRET)),
        columns=Column(up=PinGroup(*VDD), down=PinGroup(*GND)),
    )

    def __init__(self) -> None:
        lp = self.landpattern
        pins = [*self.VDD, self.DRET, self.DIN, *self.GND]
        self.mappings = [
            PadMapping({port: [lp.p[n]] for n, port in enumerate(pins, start=1)})
        ]


class FpcTail16Harness(Circuit):
    """One finger field, unconnected."""

    tail = FpcTail16()


class TestDesign(SampleDesign):
    """Build harness: ``jitx build pappalapap.components.fpc_tail.TestDesign``."""

    circuit = FpcTail16Harness()
