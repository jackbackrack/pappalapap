"""Littelfuse SMBJ5.0A - 600 W unidirectional TVS diode, SMB (DO-214AA).

Source: Littelfuse "TVS Diodes, Surface Mount - 600 W > SMBJ series",
revised JC.07/04/25 v4 (docs/datasheets/Littelfuse_SMBJ5.0A_C83333.pdf):

- Page 2, electrical table, row SMBJ5.0A (marking KE): VR 5.0 V, VBR
  6.40-7.00 V at IT 10 mA, VC 9.2 V at IPP 65.3 A, IR 800 uA at VR.
- Page 5, "Physical Specifications": "Uni-directional products are denoted
  with a cathode band".
- Page 5, "Dimensions, DO-214AA (SMB J-Bend)", millimetres (min/max): A lead
  width 1.930-2.200, B body length 4.060-4.750, C body width 3.300-3.940,
  D height 1.990-2.610, E lead length 0.760-1.520, G overall span
  5.210-5.590. Pad layout: I pad width >= 2.260, J = L pad length >= 2.160,
  K gap <= 2.740 (comparison target for the IPC generator output).

Channel evidence: LCSC C83333, "SMBJ5.0A (Littelfuse)", DO-214AA.

Ports: K (cathode, band end) on pad 1 at +y, marked with the silkscreen dot;
A (anode) on pad 2 at -y. Landpattern: the jitxlib molded two-pin IPC generator
via ``Pad1MoldedTwoPin`` (molded_diode.py), which marks pad 1.

Courtyard: ``COURTYARD_EXCESS`` (1.0 mm) around pads and body, set
explicitly. The molded generator has no lead profile to read, so its
default falls back to the generic per-density-level excess, 2.0 mm at the
level A used here for the pad sizes (a 7.9 x 11.4 mm courtyard for a
5.6 x 3.9 mm part). 1.0 mm is what the same generator gives at level B, as
on the SS54 and the fuse; IPC-7351B's own lead-fillet table puts this lead
type at 0.5 (A) / 0.25 (B).
"""

from jitx.circuit import Circuit
from jitx.component import Component
from jitx.landpattern import PadMapping
from jitx.net import Port
from jitx.sample import SampleDesign
from jitx.toleranced import Toleranced
from jitxlib.jlcpcb import LCSCPart
from jitxlib.landpatterns.courtyard import ExcessCourtyardGenerator
from jitxlib.landpatterns.ipc import DensityLevel
from jitxlib.landpatterns.leads import SMDLead
from jitxlib.landpatterns.package import RectanglePackage
from jitxlib.landpatterns.twopin.molded import MOLDED_DEFAULT_PROTRUSION
from jitxlib.symbols.diode import TVSDiodeSymbol

from pappalapap.components.molded_diode import Pad1MoldedTwoPin

COURTYARD_EXCESS = 1.0
"""Courtyard around pads and body (mm); see the module docstring."""


class SMBJ5V0A(Component):
    """5.0 V standoff unidirectional TVS (A anode, K cathode)."""

    manufacturer = "Littelfuse"
    mpn = "SMBJ5.0A"
    lcsc = LCSCPart("C83333")  # read by the JLCPCB exporter (jitxlib.jlcpcb)
    datasheet = (
        "https://datasheet.lcsc.com/datasheet/pdf/"
        "4ab84a227fae39f9eac85241b8264ead.pdf?productCode=C83333"
    )
    reference_designator_prefix = "D"

    A = Port()
    K = Port()

    # Page 5, "DO-214AA (SMB J-Bend)" table.
    landpattern = (
        Pad1MoldedTwoPin(
            lead_span=Toleranced.min_max(5.21, 5.59),  # G
            lead=SMDLead(
                length=Toleranced.min_max(0.76, 1.52),  # E
                width=Toleranced.min_max(1.93, 2.20),  # A
                lead_type=MOLDED_DEFAULT_PROTRUSION,
            ),
        )
        .package_body(
            RectanglePackage(
                width=Toleranced.min_max(3.30, 3.94),  # C
                length=Toleranced.min_max(4.06, 4.75),  # B
                height=Toleranced.min_max(1.99, 2.61),  # D
            )
        )
        # Density level A, not the B default: at B the IPC pads (2.10 x 1.83,
        # gap 2.92) miss all three page-5 pad-layout limits; at A they are
        # 2.22 x 2.23 with a 2.72 gap (J >= 2.16 and K <= 2.74 met, I >= 2.26
        # short by 0.04 mm).
        .density_level(DensityLevel.A)
        .courtyard(ExcessCourtyardGenerator(COURTYARD_EXCESS))
    )
    symbol = TVSDiodeSymbol()

    def __init__(self) -> None:
        lp = self.landpattern
        self.mappings = [PadMapping({self.K: [lp.p[1]], self.A: [lp.p[2]]})]


class SMBJ5V0AHarness(Circuit):
    """One TVS, unconnected."""

    tvs = SMBJ5V0A()


class TestDesign(SampleDesign):
    """Build harness: ``jitx build pappalapap.components.littelfuse_smbj5v0a.TestDesign``."""

    circuit = SMBJ5V0AHarness()
