"""AOS AO4407A - P-channel enhancement MOSFET, -30 V / -12 A, SOIC-8.

Sources:

- AO4407A datasheet, LCSC copy Rev 3 Jan 2008
  (docs/datasheets/AOS_AO4407A_C16072.pdf) and the current manufacturer copy
  Rev 11.1 March 2024 (docs/datasheets/AOS_AO4407A_aosmd.pdf,
  https://www.aosmd.com/sites/default/files/res/datasheets/AO4407A.pdf).
  Page 1, "SOIC-8 Top View": pins 1, 2, 3 S; 4 G; 5, 6, 7, 8 D. Page 1
  "Absolute Maximum Ratings": VDS -30 V, VGS +/-25 V, ID -12 A (10 s, TA 25 C)
  / -9.2 A steady state, PD 3.1 W (10 s). RDS(on) < 13 mOhm at VGS -10 V.
- Neither datasheet copy has a package drawing; the package is AOS document
  PO-00004 version L, "SO8(SOP-8L) PACKAGE OUTLINE"
  (docs/datasheets/AOS_SO8_package_outline.pdf,
  https://www.aosmd.com/sites/default/files/res/packaging_information/SO8.pdf),
  table "DIMENSION IN MM" (min/max): A 1.35-1.75, b 0.31-0.51, D 4.80-5.00,
  E 3.80-4.00, E1 5.80-6.20, e 1.27 BSC, L 0.40-1.27. Its "RECOMMENDED LAND
  PATTERN" (0.80 x 2.20 pads, 5.74 between pad-row centres) is the comparison
  target for the IPC generator output (see the [ib-comp] report).

Channel evidence: LCSC C16072, "AO4407A (AOS)", SOIC-8.

Ports: ``S`` and ``D`` are single ports mapped to all of their pads (S: 1-3,
D: 5-8), so the circuit wires one net per terminal and every pad carries it.

Not modelled (no JITX field): the ratings above; VGS(th) -1.7 to -3 V
(page 2). Used as a reverse-polarity switch: VGS = -5 V from a 5 V input
is inside the +/-25 V rating.
"""

from jitx.circuit import Circuit
from jitx.component import Component
from jitx.landpattern import PadMapping
from jitx.net import Port
from jitx.sample import SampleDesign
from jitx.toleranced import Toleranced
from jitxlib.jlcpcb import LCSCPart
from jitxlib.landpatterns.generators.soic import SOIC
from jitxlib.landpatterns.ipc import DensityLevel
from jitxlib.landpatterns.leads import LeadProfile, SMDLead
from jitxlib.landpatterns.leads.protrusions import BigGullWingLeads
from jitxlib.landpatterns.package import RectanglePackage
from jitxlib.symbols.box import BoxSymbol, Column, PinGroup, Row


class AO4407A(Component):
    """P-channel MOSFET: G gate, S source (pins 1-3), D drain (pins 5-8)."""

    manufacturer = "Alpha & Omega Semiconductor"
    mpn = "AO4407A"
    lcsc = LCSCPart("C16072")  # read by the JLCPCB exporter (jitxlib.jlcpcb)
    datasheet = "https://www.aosmd.com/sites/default/files/res/datasheets/AO4407A.pdf"
    reference_designator_prefix = "Q"

    G = Port()
    S = Port()
    D = Port()

    # AOS PO-00004 rev L, "DIMENSION IN MM" table.
    landpattern = (
        SOIC(num_leads=8)
        .lead_profile(
            LeadProfile(
                span=Toleranced.min_max(5.80, 6.20),  # E1
                pitch=1.27,  # e
                type=SMDLead(
                    length=Toleranced.min_max(0.40, 1.27),  # L
                    width=Toleranced.min_max(0.31, 0.51),  # b
                    lead_type=BigGullWingLeads,
                ),
            )
        )
        .package_body(
            RectanglePackage(
                width=Toleranced.min_max(3.80, 4.00),  # E
                length=Toleranced.min_max(4.80, 5.00),  # D
                height=Toleranced.min_max(1.35, 1.75),  # A
            )
        )
        .density_level(DensityLevel.B)
    )
    symbol = BoxSymbol(
        rows=Row(left=PinGroup(G), right=PinGroup(D)),
        columns=Column(down=PinGroup(S)),
    )

    def __init__(self) -> None:
        lp = self.landpattern
        self.mappings = [
            PadMapping(
                {
                    self.S: [lp.p[1], lp.p[2], lp.p[3]],
                    self.G: [lp.p[4]],
                    self.D: [lp.p[5], lp.p[6], lp.p[7], lp.p[8]],
                }
            )
        ]


class AO4407AHarness(Circuit):
    """One MOSFET, unconnected."""

    fet = AO4407A()


class TestDesign(SampleDesign):
    """Build harness: ``jitx build pappalapap.components.aos_ao4407a.TestDesign``."""

    circuit = AO4407AHarness()
