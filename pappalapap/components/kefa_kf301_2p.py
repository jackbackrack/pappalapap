"""Cixi Kefa KF301-5.0-2P - 2-position screw terminal block, 5.0 mm pitch, THT.

Source: Kefa drawing "KF301-5.0", rev A, 2021-03-13, one sheet
(docs/datasheets/Kefa_KF301-5.0-2P_C474881.pdf):

- "PCB LAYOUT": pitch 5.00 +/- 0.03, hole dia 1.20 +0.10 / -0.00, holes
  4.00 from the body's rear edge.
- Front / side views: body P x 5.0 = 10.0 wide for 2P, 7.60 deep, 10.0 tall;
  pin dia 1.00, 3.60 +/- 0.30 long below the body; in the side view the pins
  sit 4.0 from the rear face, so 3.6 from the wire-entry (front) face.
  Interlock dovetail 0.67 beyond one end face (top view, right end).
- "UL/CUL Technical Data": 300 V / 16 A (use group B); "IEC Technical
  Data": 17 A; wire 22-14 AWG, 1.5 mm2; strip 4-5 mm; screw M2.5, 0.4 N.m.

Channel evidence: LCSC C474881, "KF301-5.0-2P (Cixi Kefa Elec)", THT 5 mm.

Coordinate frame (top view, y up): origin midway between the pins; pin 1 at
x = -2.5 (square pad), pin 2 at x = +2.5; the wire-entry face is toward -y
(y = -3.6), the rear face at y = +4.0; the dovetail side is +x.

Design choices (not from the drawing): finished hole 1.25 mm, the middle of
the 1.20-1.30 range; pad copper 1.80 mm from ``jitxlib``
``compute_pad_diameter`` (IPC-2222 rule, defaults); body outline on
silkscreen with a thicker line on the wire-entry face; courtyard = body +
dovetail + wire-entry mark + 0.25 mm.
"""

from typing import ClassVar

from jitx.circuit import Circuit
from jitx.component import Component
from jitx.feature import Courtyard, Silkscreen
from jitx.landpattern import Landpattern, PadMapping
from jitx.net import Port
from jitx.sample import SampleDesign
from jitx.shapes.composites import rectangle
from jitx.shapes.primitive import Circle, Polyline
from jitxlib.jlcpcb import LCSCPart
from jitxlib.landpatterns.pads import THPad, compute_pad_diameter
from jitxlib.symbols.box import BoxSymbol, PinGroup, Row

# --- Kefa KF301-5.0 drawing ----------------------------------------------------
PITCH = 5.00
HOLE_MIN = 1.20
HOLE_MAX = 1.30
BODY_WIDTH = 10.0  # P x 5.0, P = 2
BODY_DEPTH = 7.60
PIN_TO_REAR = 4.00
PIN_TO_FRONT = BODY_DEPTH - PIN_TO_REAR  # 3.60, wire-entry face
DOVETAIL = 0.67

# --- Design choices ------------------------------------------------------------
HOLE = (HOLE_MIN + HOLE_MAX) / 2  # 1.25
SILK_WIDTH = 0.12
ENTRY_SILK_WIDTH = 0.30
COURTYARD_EXCESS = 0.25


class KF301Landpattern(Landpattern):
    """Two 1.25 mm plated holes at 5.0 mm; body outline, wire entry toward -y."""

    def __init__(self) -> None:
        copper = compute_pad_diameter(HOLE)
        hole = Circle(diameter=HOLE)
        self.p = {
            1: THPad(rectangle(copper, copper), hole).at(-PITCH / 2, 0.0),
            2: THPad(Circle(diameter=copper), hole).at(PITCH / 2, 0.0),
        }

        half = SILK_WIDTH / 2
        x = BODY_WIDTH / 2 + half
        y_rear = PIN_TO_REAR + half
        y_front = -PIN_TO_FRONT - half
        self.body_outline = Silkscreen(
            Polyline(
                SILK_WIDTH, [(-x, y_front), (-x, y_rear), (x, y_rear), (x, y_front)]
            )
        )
        y_entry = -PIN_TO_FRONT - ENTRY_SILK_WIDTH / 2
        self.wire_entry = Silkscreen(
            Polyline(ENTRY_SILK_WIDTH, [(-x, y_entry), (x, y_entry)])
        )

        cx0 = -BODY_WIDTH / 2 - COURTYARD_EXCESS
        cx1 = BODY_WIDTH / 2 + DOVETAIL + COURTYARD_EXCESS
        cy0 = y_entry - ENTRY_SILK_WIDTH / 2 - COURTYARD_EXCESS
        cy1 = PIN_TO_REAR + COURTYARD_EXCESS
        self.courtyard = Courtyard(
            rectangle(cx1 - cx0, cy1 - cy0).at((cx0 + cx1) / 2, (cy0 + cy1) / 2)
        )


class KF301_2P(Component):
    """2-position 5.0 mm screw terminal; P1 = pin 1 (square pad)."""

    manufacturer = "Cixi Kefa Elec"
    mpn = "KF301-5.0-2P"
    lcsc = LCSCPart("C474881")  # read by the JLCPCB exporter (jitxlib.jlcpcb)
    datasheet = (
        "https://datasheet.lcsc.com/datasheet/pdf/"
        "dbe48a1bef5e997cc12dba31bc0ac67e.pdf?productCode=C474881"
    )
    reference_designator_prefix = "J"
    rated_current_a: ClassVar[float] = 16.0  # UL use group B; IEC 17 A
    WIRE_ENTRY_DIRECTION: ClassVar[str] = "-y"

    P1 = Port()
    P2 = Port()

    landpattern = KF301Landpattern()
    symbol = BoxSymbol(rows=Row(left=PinGroup(P1, P2)))

    def __init__(self) -> None:
        lp = self.landpattern
        self.mappings = [PadMapping({self.P1: [lp.p[1]], self.P2: [lp.p[2]]})]


class KF301Harness(Circuit):
    """One terminal block, unconnected."""

    term = KF301_2P()


class TestDesign(SampleDesign):
    """Build harness: ``jitx build pappalapap.components.kefa_kf301_2p.TestDesign``."""

    circuit = KF301Harness()
