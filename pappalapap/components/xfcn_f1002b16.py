"""XFCN F1002-B-16-20T-R - 16P 1.0 mm FPC connector, bottom contact, flip lock, SMD RA.

Source: XFCN family drawing "FPC1.0mmPitch 掀盖卧式下接(H=2.0)", part no.
F1002-B-xx-20T-R, rev A1, drawn 2024-05-28, one sheet. The LCSC datasheet for
C481251 (docs/datasheets/XFCN_F1002-B-16-20T-R_C481251.pdf) is byte-identical
to the C481250 copy (docs/datasheets/XFCN_F1002-B-12-20T-R_C481250.pdf).
Values from:

- View captioned "适用线路板 (PCB LAYOUT)": signal pads 0.50 +/- 0.05 wide on
  1.00 +/- 0.05 pitch, 1.50 long; first-to-last pad centre DIMA +/- 0.05;
  fixing pads 2.00 x 1.70; fixing-pad outer edge 3.20 +/- 0.05 beyond the
  last signal-pad centre (so fixing-pad centre 2.20 beyond it); fixing-pad
  far edge 4.20 from the signal pads' outer (rear) end; the signal pads
  overhang the dashed CONN body outline by 1.2 at the rear.
- CKT table, row 16: DIM A 15.00, DIM B 17.10 (slot), DIM C 20.90 (body).
- Front view: contact tails "N-0.20 +/- 0.02" wide.
- Side view: 6.0 +/- 0.15 overall depth including the flip lid, tails
  0.85 +/- 0.05 beyond the body rear; height 2.00 +/- 0.15.
- "SECTION A-A": the cable enters the open face opposite the tails; the
  insertion stop is 2.7 from the entry face and the contact point 1.2 short
  of the stop. Bottom contact: the contacts touch the cable's lower face.
- "技术指标": 1 A AC/DC per contact, 50 V, contact resistance <= 0.03 Ohm,
  -25 to +85 C.

The XFCN drawing does not number the contacts. Pin numbering follows the
LCSC/EasyEDA footprint for C481251 (used for comparison only, never as
geometry source): pad 1 is the leftmost contact when viewed from above,
looking in the insertion direction. EasyEDA comparison (this model vs
EasyEDA, mm): signal pad 0.50 x 1.50 vs 0.30 x 1.30; pitch 1.00 vs 1.00;
pad 1 at x -7.50 vs -7.50; fixing pad 2.00 x 1.70 vs 2.00 x 2.50; fixing
centre x +/-9.70 vs +/-9.65; signal-row to fixing-centre offset 2.60 vs 2.60;
cable entry on the fixing-pad side of the signal row in both.

Coordinate frame and orientation facts (top view, y up), exposed as class
attributes for the ZIF/flex pin-1 proof:

- Origin at the centre of the signal-pad row; pad k (P[k-1]) centre at
  x = -7.50 + (k - 1) * 1.00, y = 0. **Pin 1 is at x = -7.50 (the -x end).**
- **The cable enters from -y and is pushed toward +y** (INSERTION_DIRECTION =
  (0, +1)). The entry face of the body is at y = -5.60; the tails are at the
  rear (+y), tail tips at y = +0.40.
- Derived (labelled, not drawn dimensions): body rear edge y = 0.75 - 1.2 =
  -0.45; entry face y = -0.45 - (6.0 - 0.85) = -5.60; cable end at the stop
  y = -5.60 + 2.7 = -2.90; contact line y = -2.90 - 1.2 = -4.10.
- **Bottom contact:** the flex's exposed conductors must face DOWN, toward
  this board, when inserted.
- Equivalently: looking down on the board from above, standing at the entry
  face and pushing the cable away from you, contact 1 is on your left.

Ports: ``P`` (16, pin 1..16 = P[0]..P[15]); ``MNT`` = both fixing tabs
(part 4 "焊片", tin-plated copper alloy, mechanical only). Decision: the tabs
get one port so the circuit ties them to GND; they then join the ground pour
(stronger anchoring, no floating copper). Nothing flows through them.

Design choices (not from the drawing): silkscreen = entry-face line plus a
pin-1 dot outboard of pad 1; courtyard = fixing pads, tails and the 5.60 mm
body depth plus 0.25 mm. The flip lid opens to 90 degrees above the body;
keep tall parts away from the entry face.
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
from jitxlib.landpatterns.pads import SMDPad
from jitxlib.symbols.box import BoxSymbol, Column, PinGroup, Row

# --- XFCN drawing, "PCB LAYOUT" and CKT row 16 ---------------------------------
NUM_PINS = 16
PITCH = 1.00
DIM_A = 15.00  # first-to-last pad centre
DIM_B = 17.10  # cable slot width
DIM_C = 20.90  # body width
SIGNAL_PAD_W = 0.50
SIGNAL_PAD_L = 1.50
FIX_PAD_W = 2.00
FIX_PAD_L = 1.70
FIX_OUTER_FROM_LAST = 3.20  # last signal-pad centre to fixing-pad outer edge
FIX_FAR_FROM_SIGNAL_END = 4.20  # signal-pad rear end to fixing-pad far edge
PAD_OVERHANG = 1.2  # signal pad beyond the body rear edge
OVERALL_DEPTH = 6.0  # side view, lid to tail tip
TAIL_OVERHANG = 0.85  # side view, tail beyond the body rear
INSERTION_DEPTH = 2.7  # section A-A, entry face to stop
CONTACT_FROM_STOP = 1.2  # section A-A

# --- Derived geometry (landpattern frame, see docstring) ------------------------
PIN1_X = -DIM_A / 2  # -7.50
SIGNAL_REAR_Y = SIGNAL_PAD_L / 2  # +0.75
FIX_X = DIM_A / 2 + FIX_OUTER_FROM_LAST - FIX_PAD_W / 2  # 9.70
FIX_Y = SIGNAL_REAR_Y - FIX_FAR_FROM_SIGNAL_END + FIX_PAD_L / 2  # -2.60
BODY_REAR_Y = SIGNAL_REAR_Y - PAD_OVERHANG  # -0.45
TAIL_TIP_Y = BODY_REAR_Y + TAIL_OVERHANG  # +0.40
ENTRY_FACE_Y = BODY_REAR_Y - (OVERALL_DEPTH - TAIL_OVERHANG)  # -5.60
CABLE_STOP_Y = ENTRY_FACE_Y + INSERTION_DEPTH  # -2.90
CONTACT_LINE_Y = CABLE_STOP_Y - CONTACT_FROM_STOP  # -4.10

# --- Drawing rules ---------------------------------------------------------------
SILK_WIDTH = 0.12
COURTYARD_EXCESS = 0.25
PIN1_DOT_RADIUS = 0.20
PIN1_DOT_X = PIN1_X - SIGNAL_PAD_W / 2 - 0.55  # 0.55 mm pad-to-dot-centre gap

assert abs(FIX_X - 9.70) < 1e-9
assert abs(FIX_Y + 2.60) < 1e-9


class F1002B16Landpattern(Landpattern):
    """16 signal pads on 1.0 mm + 2 fixing pads; cable enters from -y."""

    def __init__(self) -> None:
        signal = rectangle(SIGNAL_PAD_W, SIGNAL_PAD_L)
        self.p = {
            k: SMDPad(signal).at(PIN1_X + (k - 1) * PITCH, 0.0)
            for k in range(1, NUM_PINS + 1)
        }
        fixing = rectangle(FIX_PAD_W, FIX_PAD_L)
        self.fix = [SMDPad(fixing).at(-FIX_X, FIX_Y), SMDPad(fixing).at(FIX_X, FIX_Y)]

        # Cable-entry face of the body.
        y = ENTRY_FACE_Y - SILK_WIDTH / 2
        self.entry_face = Silkscreen(
            Polyline(SILK_WIDTH, [(-DIM_C / 2, y), (DIM_C / 2, y)])
        )
        self.pin1_marker = Silkscreen(
            Circle(radius=PIN1_DOT_RADIUS).at(PIN1_DOT_X, 0.0)
        )

        x = max(DIM_C / 2, FIX_X + FIX_PAD_W / 2) + COURTYARD_EXCESS
        y0 = ENTRY_FACE_Y - SILK_WIDTH - COURTYARD_EXCESS
        y1 = max(SIGNAL_REAR_Y, TAIL_TIP_Y) + COURTYARD_EXCESS
        self.courtyard = Courtyard(rectangle(2 * x, y1 - y0).at(0.0, (y0 + y1) / 2))


class XFCN_F1002B16(Component):
    """16P 1.0 mm bottom-contact flip-lock FPC connector.

    ``P[k - 1]`` is contact k. Orientation constants (landpattern frame) are
    class attributes; see the module docstring for their derivation.
    """

    manufacturer = "XFCN"
    mpn = "F1002-B-16-20T-R"
    lcsc: ClassVar[str] = "C481251"
    datasheet = (
        "https://datasheet.lcsc.com/datasheet/pdf/"
        "fbb3bfadf4d81cea0a7473fb34bffb99.pdf?productCode=C481251"
    )
    reference_designator_prefix = "J"
    rated_current_per_contact_a: ClassVar[float] = 1.0

    NUM_PINS: ClassVar[int] = NUM_PINS
    PITCH: ClassVar[float] = PITCH
    PIN1_X: ClassVar[float] = PIN1_X
    PIN_Y: ClassVar[float] = 0.0
    INSERTION_DIRECTION: ClassVar[tuple[float, float]] = (0.0, 1.0)
    CONTACT_SIDE: ClassVar[str] = "bottom"  # flex conductors face this board
    ENTRY_FACE_Y: ClassVar[float] = ENTRY_FACE_Y
    CABLE_STOP_Y: ClassVar[float] = CABLE_STOP_Y
    CONTACT_LINE_Y: ClassVar[float] = CONTACT_LINE_Y
    SLOT_WIDTH: ClassVar[float] = DIM_B

    # Class-scope port arrays are the JITX structural idiom (each instance gets
    # its own ports), not shared mutable state; hence the RUF012 waiver.
    P = [Port() for _ in range(NUM_PINS)]  # noqa: RUF012
    MNT = Port()

    landpattern = F1002B16Landpattern()
    symbol = BoxSymbol(
        rows=Row(left=PinGroup(*P)),
        columns=Column(down=PinGroup(MNT)),
    )

    def __init__(self) -> None:
        lp = self.landpattern
        mapping = {port: [lp.p[k]] for k, port in enumerate(self.P, start=1)}
        mapping[self.MNT] = [lp.fix[0], lp.fix[1]]
        self.mappings = [PadMapping(mapping)]

    @classmethod
    def pin_x(cls, pin: int) -> float:
        """x of contact ``pin`` (1..16) in the landpattern frame."""
        if not 1 <= pin <= NUM_PINS:
            raise ValueError(f"contact {pin} not in 1..{NUM_PINS}")
        return PIN1_X + (pin - 1) * PITCH


class F1002B16Harness(Circuit):
    """One connector, unconnected."""

    zif = XFCN_F1002B16()


class TestDesign(SampleDesign):
    """Build harness: ``jitx build pappalapap.components.xfcn_f1002b16.TestDesign``."""

    circuit = F1002B16Harness()
