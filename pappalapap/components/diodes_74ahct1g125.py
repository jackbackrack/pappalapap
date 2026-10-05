"""Diodes Inc 74AHCT1G125W5-7 - single buffer, 3-state output, TTL inputs, SOT-25.

Source: Diodes Inc 74AHCT1G125 datasheet, DS35186 Rev. 1-2, May 2011
(docs/datasheets/Diodes_74AHCT1G125W5-7_C842287.pdf):

- Page 1, "Pin Assignments" (top view, SOT25 / SOT353): 1 OE, 2 A, 3 GND down
  the left side, 4 Y bottom-right, 5 VCC top-right.
- Page 2, "Pin Descriptions": 1 OE Output Enable (active low: "The output
  enters a high impedance state when a HIGH-level is applied to the output
  enable (OE) pin", page 1), 2 A Data Input, 3 GND, 4 Y Data Output, 5 VCC.
- Page 7, "Ordering Information": 74AHCT1G125W5-7 = SOT25, 3000/tape & reel.
- Page 8, "Package Outline Dimensions (1) Package Type: SOT25" (min/max):
  A lead width 0.35-0.50, B body width 1.50-1.70, C lead tip to lead tip
  2.70-3.00, D pitch 0.95 typ, H body length 2.90-3.10, K height 1.00-1.30,
  L foot length 0.35-0.55.

Channel evidence: LCSC C842287, "74AHCT1G125W5-7 (DIODES)", SOT-25-5.

Not modelled (no JITX field): VCC 4.5-5.5 V; TTL-level inputs (VIH 2.0 V), so
a 3.3 V MCU output drives it directly; +/-8 mA output drive at 5 V.
"""

from jitx.circuit import Circuit
from jitx.component import Component
from jitx.landpattern import PadMapping
from jitx.net import Port
from jitx.sample import SampleDesign
from jitx.toleranced import Toleranced
from jitxlib.jlcpcb import LCSCPart
from jitxlib.landpatterns.generators.sot import SOT23_5, SOTLead, SOTLeadProfile
from jitxlib.landpatterns.ipc import DensityLevel
from jitxlib.landpatterns.package import RectanglePackage
from jitxlib.symbols.box import BoxSymbol, Column, PinGroup, Row


class AHCT1G125(Component):
    """Single non-inverting buffer with active-low output enable (OE_n)."""

    manufacturer = "Diodes Incorporated"
    mpn = "74AHCT1G125W5-7"
    lcsc = LCSCPart("C842287")  # read by the JLCPCB exporter (jitxlib.jlcpcb)
    datasheet = (
        "https://datasheet.lcsc.com/datasheet/pdf/"
        "9555fe94df3a7068be57bf68a997ca90.pdf?productCode=C842287"
    )
    reference_designator_prefix = "U"

    OE_n = Port()
    A = Port()
    GND = Port()
    Y = Port()
    VCC = Port()

    # Page 8, SOT25 table; generator default density level B made explicit.
    landpattern = (
        SOT23_5()
        .lead_profile(
            SOTLeadProfile(
                span=Toleranced.min_max(2.70, 3.00),  # C
                pitch=0.95,  # D
                type=SOTLead(
                    length=Toleranced.min_max(0.35, 0.55),  # L
                    width=Toleranced.min_max(0.35, 0.50),  # A
                ),
            )
        )
        .package_body(
            RectanglePackage(
                width=Toleranced.min_max(1.50, 1.70),  # B
                length=Toleranced.min_max(2.90, 3.10),  # H
                height=Toleranced.min_max(1.00, 1.30),  # K
            )
        )
        .density_level(DensityLevel.B)
    )
    symbol = BoxSymbol(
        rows=Row(left=PinGroup(A, OE_n), right=PinGroup(Y)),
        columns=Column(up=PinGroup(VCC), down=PinGroup(GND)),
    )

    def __init__(self) -> None:
        lp = self.landpattern
        self.mappings = [
            PadMapping(
                {
                    self.OE_n: [lp.p[1]],
                    self.A: [lp.p[2]],
                    self.GND: [lp.p[3]],
                    self.Y: [lp.p[4]],
                    self.VCC: [lp.p[5]],
                }
            )
        ]


class AHCT1G125Harness(Circuit):
    """One buffer, unconnected."""

    buf = AHCT1G125()


class TestDesign(SampleDesign):
    """Build harness: ``jitx build pappalapap.components.diodes_74ahct1g125.TestDesign``."""

    circuit = AHCT1G125Harness()
