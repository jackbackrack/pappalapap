"""Littelfuse 045106.3MRL - NANO2 451 series very fast-acting fuse, 6.3 A, 2410.

Source: Littelfuse "Surface Mount Fuses, NANO2 > Very Fast-Acting Fuse >
451/453 Series", revised 06/15/17
(docs/datasheets/Littelfuse_045106.3MRL_C178982.pdf):

- Page 2, electrical table, row 6.30 A: amp code 06.3, 125 V, interrupting
  rating 50 A @ 125 VAC/VDC, cold resistance 0.0096 Ohm.
- Page 1, "Electrical Characteristics for Series": 100 % of rating for
  4 h minimum; 200 % opens within 5 s maximum (0.062-10 A).
- Page 3, temperature re-rating curve; note 1: additional to the standard
  25 % derating for continuous operation (so 6.3 A is a ~4.7 A continuous
  part at 25 C).
- Page 4, "Part Numbering System": 0451 (series) + 06.3 (amp code) + M
  (1000 pcs) + R (tape and reel) + L (RoHS/HF, gold caps) = 045106.3MRL.
  The "0451006.3MRL" spelling in PLAN.md does not follow this scheme; the
  LCSC listing and this class use 045106.3MRL.
- Page 4, "Dimensions": body 6.10 +/- .20 long, 2.69 +/- .25 wide,
  2.69 +/- .25 high, end cap 1.45 (no tolerance printed). "Recommended pad
  layout": pads 1.96 (along the body) x 3.15, gap 2.95, overall 6.86
  (comparison target for the IPC generator output).

Channel evidence: LCSC C178982, "045106.3MRL (Littelfuse)", 2410.

Landpattern: 2410 is not a key of ``SMT_CHIP_DEFS``, so the jitxlib molded
two-pin IPC generator is used with explicit datasheet dimensions and the
chip-termination protrusion (``BigRectangularLeads``: the end caps wrap the
body ends like a chip part). Unpolarized; pads ``p[1]`` (+y), ``p[2]`` (-y).
"""

from typing import ClassVar

from jitx.circuit import Circuit
from jitx.component import Component
from jitx.net import Port
from jitx.sample import SampleDesign
from jitx.toleranced import Toleranced
from jitxlib.landpatterns.ipc import DensityLevel
from jitxlib.landpatterns.leads import SMDLead
from jitxlib.landpatterns.leads.protrusions import BigRectangularLeads
from jitxlib.landpatterns.package import RectanglePackage
from jitxlib.landpatterns.twopin.molded import MoldedTwoPin
from jitxlib.symbols.box import BoxSymbol, PinGroup, Row


class Fuse451_6A3(Component):
    """6.3 A 125 V very fast-acting 2410 fuse."""

    manufacturer = "Littelfuse"
    mpn = "045106.3MRL"
    lcsc: ClassVar[str] = "C178982"
    datasheet = (
        "https://datasheet.lcsc.com/datasheet/pdf/"
        "ecd74ee295e2e3d7ddb74e9193c5d222.pdf?productCode=C178982"
    )
    reference_designator_prefix = "F"

    p1 = Port()
    p2 = Port()

    # Page 4, "Dimensions". The 1.45 mm cap length has no printed tolerance.
    landpattern = (
        MoldedTwoPin(
            lead_span=Toleranced(6.10, 0.20),
            lead=SMDLead(
                length=Toleranced.exact(1.45),
                width=Toleranced(2.69, 0.25),
                lead_type=BigRectangularLeads,
            ),
        )
        .package_body(
            RectanglePackage(
                width=Toleranced(2.69, 0.25),
                length=Toleranced(6.10, 0.20),
                height=Toleranced(2.69, 0.25),
            )
        )
        .density_level(DensityLevel.B)
    )
    # jitxlib-standard has no fuse symbol; a two-pin box.
    symbol = BoxSymbol(rows=Row(left=PinGroup(p1), right=PinGroup(p2)))


class Fuse451Harness(Circuit):
    """One fuse, unconnected."""

    fuse = Fuse451_6A3()


class TestDesign(SampleDesign):
    """Build harness: ``jitx build pappalapap.components.littelfuse_0451_6a3.TestDesign``."""

    circuit = Fuse451Harness()
