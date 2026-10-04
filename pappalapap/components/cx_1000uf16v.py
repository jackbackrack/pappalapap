"""Chengx KM108M016G13RR0VH2FP0 - 1000 uF 16 V radial aluminium electrolytic, D10 x L13.

Source: Chengx (Dongguan Cheng Xing Electronics) approval sheet for LCSC
C439782, "1000uF/16v 10*13", version A-0, 2025-03-19
(docs/datasheets/Chengx_1000uF16V_C439782.pdf):

- Page 1: customer part C439782 = Chengx part KM108M016G13RR0VH2FP0.
- Page 5, "KM Series" specifications: -40 to +105 C, +/-20 %, tan d 0.18
  at 16 V (+0.02 per 1000 uF above 1000 uF), 2000 h load life at 105 C.
- Page 5, "CASE SIZE TABLE": for D 10, lead pitch F 5 (+/-0.5), lead
  diameter d 0.6 (+/-0.05), alpha (L < 20) 1.5, beta (D < 20) 0.5; leads
  "15min." / "4min."; the minus lead is marked on the sleeve.
- Page 6, parameter table row C439782: 1000 uF, +/-20 %, 16 V, surge 18.4 V,
  ripple 680 mArms at 120 Hz / 105 C, D 10 x L 13. Size drawing on the same
  page: D 10, L 13, F 5.0 +/- 0.5, d 0.6 +/- 0.05, alpha 1.5, beta 0.5.

So the body is at most D + beta = 10.5 mm across and L + alpha = 14.5 mm
tall.

Channel evidence: LCSC C439782, "1000uF 16V (Chengx)", Through Hole,
D10xL13mm.

Landpattern: jitxlib ``PolarizedRadialTwoPin`` (IPC-2222 hole and pad from the
0.6 mm lead), pads ``a`` (+, at +y) and ``c`` (-, at -y); the generator's
polarized outline draws the body circle, a "+" beside the anode and a
thickened arc. Courtyard from the 10.5 mm maximum body.
"""

from typing import ClassVar

from jitx.circuit import Circuit
from jitx.component import Component
from jitx.landpattern import PadMapping
from jitx.net import Port
from jitx.sample import SampleDesign
from jitx.toleranced import Toleranced
from jitxlib.landpatterns.ipc import DensityLevel
from jitxlib.landpatterns.leads import THLead
from jitxlib.landpatterns.package import CylinderPackage
from jitxlib.landpatterns.twopin.radial import PolarizedRadialTwoPin
from jitxlib.symbols.capacitor import PolarizedCapacitorSymbol


class CX1000uF16V(Component):
    """1000 uF 16 V radial electrolytic, D10 x 13, 5.0 mm lead pitch."""

    manufacturer = "Chengx"
    mpn = "KM108M016G13RR0VH2FP0"
    lcsc: ClassVar[str] = "C439782"
    datasheet = (
        "https://datasheet.lcsc.com/datasheet/pdf/"
        "c4fd22258d6f7116b203df2d4ecd7eec.pdf?productCode=C439782"
    )
    reference_designator_prefix = "C"
    value = "1000uF 16V"

    pos = Port()
    neg = Port()

    # Page 6 size drawing / page 5 case size table, D = 10 row.
    landpattern = (
        PolarizedRadialTwoPin(
            lead=THLead(
                length=Toleranced.exact(15.0),  # "15min."; no pad effect
                width=Toleranced(0.6, 0.05),  # d
            ),
            lead_spacing=Toleranced(5.0, 0.5),  # F
        )
        .package_body(
            CylinderPackage(
                diameter=Toleranced.min_max(10.0, 10.5),  # D .. D + beta
                height=Toleranced.min_max(13.0, 14.5),  # L .. L + alpha
            )
        )
        .density_level(DensityLevel.A)  # A: courtyard from the 10.5 max body
    )
    symbol = PolarizedCapacitorSymbol()

    def __init__(self) -> None:
        lp = self.landpattern
        # The generator types its anode/cathode pads as optional (unset before
        # build); narrow them rather than suppress the type check.
        if lp.a is None or lp.c is None:
            raise AssertionError("radial generator built without a/c pads")
        self.mappings = [PadMapping({self.pos: [lp.a], self.neg: [lp.c]})]


class CX1000uF16VHarness(Circuit):
    """One capacitor, unconnected."""

    cap = CX1000uF16V()


class TestDesign(SampleDesign):
    """Build harness: ``jitx build pappalapap.components.cx_1000uf16v.TestDesign``."""

    circuit = CX1000uF16VHarness()
