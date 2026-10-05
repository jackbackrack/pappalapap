"""Worldsemi WS2816C-2121 - 16-bit RGB addressable LED, 2.2 x 2.2 mm, 6 pads.

Source: Worldsemi WS2816C-2121 datasheet (docs/datasheets/WS2816C-2121.pdf),
page 2:
- "Mechanical Dimensions": body 2.20 +/- 0.1 x 2.20 +/- 0.1 mm, height
  1.05 +/- 0.1 mm.
- "PIN Configuration" (top view): pins 1 BI, 2 DI, 3 VDD down the left side
  (pin 1 at the top), pins 4 DO, 5 BO, 6 GND up the right side (pin 6 at the
  top). The body's only physical polarity mark is the corner chamfer at the
  bottom-right, next to pin 4 (DO) -- not at pin 1.
- "Recommended pad size": 2 columns x 3 rows, each pad 0.7 (x) x 0.32 (y),
  row pitch 0.63 (1.26 between outer-row centers), 1.19 between the inner edges
  of the two pad columns. Column centers are therefore +/-(1.19 / 2 + 0.7 / 2)
  = +/-0.945 mm.
- "PIN Function" table: pin numbers and symbols.

Channel evidence: LCSC C965561 (docs/datasheets/C965561_lcsc.txt), pinout
1 BI, 2 DI, 3 VDD, 4 DO, 5 BO, 6 GND -- agrees with the datasheet.

The EasyEDA footprint for C965561 was compared, not used: it puts the pad
columns at +/-0.94 mm (the datasheet arithmetic gives 0.945) and otherwise
matches pad size, row pitch, and numbering.

LCSC part number: ``lcsc = LCSCPart(...)`` (jitxlib.jlcpcb, read by the JLCPCB
exporter); electrical ratings (VDD 3.7-5.5 V) live in the datasheet.
"""

from enum import Enum

from jitx.circuit import Circuit
from jitx.component import Component
from jitx.feature import Courtyard, Silkscreen
from jitx.landpattern import Landpattern, PadMapping
from jitx.net import Port
from jitx.sample import SampleDesign
from jitx.shapes.composites import rectangle
from jitx.shapes.primitive import Circle, Polyline
from jitxlib.jlcpcb import LCSCPart
from jitxlib.landpatterns.pads import SMDPad
from jitxlib.symbols.box import BoxSymbol, Column, PinGroup, Row

# Datasheet page 2, "Recommended pad size".
PAD_X = 0.70
PAD_Y = 0.32
ROW_PITCH = 0.63
COLUMN_INNER_GAP = 1.19
COLUMN_X = COLUMN_INNER_GAP / 2 + PAD_X / 2  # 0.945

# Datasheet page 2, "Mechanical Dimensions" (nominal; height 1.05 mm has no
# landpattern field).
BODY = 2.20

# Drawing rules for this footprint (not from the datasheet).
SILK_WIDTH = 0.12
SILK_PAD_CLEARANCE = 0.25  # silkscreen centerline to pad copper edge, minimum
COURTYARD_EXCESS = 0.25  # IPC-7351 nominal courtyard excess

PAD_OUTER_X = COLUMN_X + PAD_X / 2  # 1.295, pads overhang the 1.10 body edge


class WS2816CLandpattern(Landpattern):
    """Datasheet-recommended 2 x 3 pad layout, top view, pin 1 top-left."""

    def __init__(self) -> None:
        pad_shape = rectangle(PAD_X, PAD_Y)
        # Left column, top to bottom: pins 1, 2, 3.
        # Right column, bottom to top: pins 4, 5, 6.
        self.p = {
            1: SMDPad(pad_shape).at(-COLUMN_X, ROW_PITCH),
            2: SMDPad(pad_shape).at(-COLUMN_X, 0.0),
            3: SMDPad(pad_shape).at(-COLUMN_X, -ROW_PITCH),
            4: SMDPad(pad_shape).at(COLUMN_X, -ROW_PITCH),
            5: SMDPad(pad_shape).at(COLUMN_X, 0.0),
            6: SMDPad(pad_shape).at(COLUMN_X, ROW_PITCH),
        }

        # Body outline on silkscreen: top and bottom edges only, between the
        # pad columns (the pads overhang the body on the left and right).
        silk_y = BODY / 2 + SILK_WIDTH / 2
        silk_x = BODY / 2
        self.silkscreen = [
            Silkscreen(Polyline(SILK_WIDTH, [(-silk_x, silk_y), (silk_x, silk_y)])),
            Silkscreen(Polyline(SILK_WIDTH, [(-silk_x, -silk_y), (silk_x, -silk_y)])),
        ]

        # Pin-1 dot outboard of pad 1.
        dot_radius = 0.10
        self.pin1_marker = Silkscreen(
            Circle(radius=dot_radius).at(
                -(PAD_OUTER_X + SILK_PAD_CLEARANCE + dot_radius), ROW_PITCH
            )
        )

        extent_x = max(PAD_OUTER_X, BODY / 2) + COURTYARD_EXCESS
        extent_y = max(ROW_PITCH + PAD_Y / 2, BODY / 2) + COURTYARD_EXCESS
        self.courtyard = Courtyard(rectangle(2 * extent_x, 2 * extent_y))


class DataPath(Enum):
    """The WS2816C's two daisy-chain data paths (datasheet p.6 application
    circuit): primary DI -> DO and backup BI -> BO. A chain hop joins LED n's
    output to LED n+1's input on the same path."""

    PRIMARY = "DO->DI"
    BACKUP = "BO->BI"


class WS2816C(Component):
    """Worldsemi WS2816C-2121 addressable RGB LED with backup data path."""

    manufacturer = "Worldsemi"
    mpn = "WS2816C-2121"
    lcsc = LCSCPart("C965561")  # read by the JLCPCB exporter (jitxlib.jlcpcb)
    datasheet = (
        "https://datasheet.lcsc.com/datasheet/pdf/"
        "0a49b02030eefff1ce6215b403f19c6e.pdf?productCode=C965561"
    )
    reference_designator_prefix = "D"

    BI = Port()
    DI = Port()
    VDD = Port()
    DO = Port()
    BO = Port()
    GND = Port()

    landpattern = WS2816CLandpattern()
    symbol = BoxSymbol(
        rows=Row(left=PinGroup(DI, BI), right=PinGroup(DO, BO)),
        columns=Column(up=PinGroup(VDD), down=PinGroup(GND)),
    )

    def __init__(self) -> None:
        lp = self.landpattern
        self.mappings = [
            PadMapping(
                {
                    self.BI: [lp.p[1]],
                    self.DI: [lp.p[2]],
                    self.VDD: [lp.p[3]],
                    self.DO: [lp.p[4]],
                    self.BO: [lp.p[5]],
                    self.GND: [lp.p[6]],
                }
            )
        ]

    def output(self, path: DataPath) -> Port:
        """Output port of a data path (DO or BO)."""
        return self.DO if path == DataPath.PRIMARY else self.BO

    def input(self, path: DataPath) -> Port:
        """Input port of a data path (DI or BI)."""
        return self.DI if path == DataPath.PRIMARY else self.BI


class WS2816CHarness(Circuit):
    """One WS2816C, unconnected."""

    led = WS2816C()


class TestDesign(SampleDesign):
    """Build harness: one WS2816C on the sample board."""

    circuit = WS2816CHarness()
