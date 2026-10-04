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
"""

from typing import ClassVar

from jitx.circuit import Circuit
from jitx.component import Component
from jitx.landpattern import PadMapping
from jitx.net import Port
from jitx.sample import SampleDesign
from jitx.toleranced import Toleranced
from jitxlib.landpatterns.ipc import DensityLevel
from jitxlib.landpatterns.leads import SMDLead
from jitxlib.landpatterns.package import RectanglePackage
from jitxlib.landpatterns.twopin.molded import MOLDED_DEFAULT_PROTRUSION
from jitxlib.symbols.diode import TVSDiodeSymbol

from pappalapap.components.molded_diode import Pad1MoldedTwoPin


class SMBJ5V0A(Component):
    """5.0 V standoff unidirectional TVS (A anode, K cathode)."""

    manufacturer = "Littelfuse"
    mpn = "SMBJ5.0A"
    lcsc: ClassVar[str] = "C83333"
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
