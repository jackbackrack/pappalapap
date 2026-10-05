"""MDD (Microdiode) SS54 - 40 V / 5 A Schottky barrier rectifier, SMA (DO-214AC).

Source: MDD "SS52 THRU SS5200" datasheet, Rev 2024A4
(docs/datasheets/MDD_SS54_C22452.pdf):

- Page 1, "Maximum Ratings": SS54 (marking SS54) VRRM 40 V, IF(AV) 5.0 A,
  IFSM 120 A, VF 0.55 V max at 5.0 A, TJ -55 to +125 C.
- Page 1, "Mechanical Data": "Polarity: Color band denotes cathode end".
- Page 1, "DO-214AC/SMA" outline, inches (mm), max/min: lead width
  0.067/0.051 (1.70/1.30), body width 0.110/0.090 (2.80/2.30), body length
  0.177/0.150 (4.50/3.80), height 0.097/0.073 (2.45/1.85), lead length
  0.061/0.029 (1.55/0.75), overall span 0.209/0.184 (5.30/4.70).
- Page 3, "Suggested Pad Layout" (mm): A pad width 1.68, B pad length 1.52,
  C pad-centre spacing 3.93, D gap 2.41, E overall 5.45 (comparison target
  for the IPC generator output).

Channel evidence: LCSC C22452 (JLC Basic part), "SS54 (MDD)", SMA(DO-214AC).

Ports: K (cathode, band end) on pad 1 at +y, marked with the silkscreen dot;
A (anode) on pad 2 at -y. Landpattern: the jitxlib molded two-pin IPC generator
via ``Pad1MoldedTwoPin`` (molded_diode.py), which marks pad 1.
"""

from jitx.circuit import Circuit
from jitx.component import Component
from jitx.landpattern import PadMapping
from jitx.net import Port
from jitx.sample import SampleDesign
from jitx.toleranced import Toleranced
from jitxlib.jlcpcb import LCSCPart
from jitxlib.landpatterns.ipc import DensityLevel
from jitxlib.landpatterns.leads import SMDLead
from jitxlib.landpatterns.package import RectanglePackage
from jitxlib.landpatterns.twopin.molded import MOLDED_DEFAULT_PROTRUSION
from jitxlib.symbols.diode import SchottkyDiodeSymbol

from pappalapap.components.molded_diode import Pad1MoldedTwoPin


class SS54(Component):
    """40 V 5 A Schottky rectifier (A anode, K cathode)."""

    manufacturer = "MDD (Microdiode Semiconductor)"
    mpn = "SS54"
    lcsc = LCSCPart("C22452")  # read by the JLCPCB exporter (jitxlib.jlcpcb)
    datasheet = (
        "https://datasheet.lcsc.com/datasheet/pdf/"
        "3d29bdcdc3c46ec127d6db22edd72e83.pdf?productCode=C22452"
    )
    reference_designator_prefix = "D"

    A = Port()
    K = Port()

    # Page 1, "DO-214AC/SMA" outline.
    landpattern = (
        Pad1MoldedTwoPin(
            lead_span=Toleranced.min_max(4.70, 5.30),
            lead=SMDLead(
                length=Toleranced.min_max(0.75, 1.55),
                width=Toleranced.min_max(1.30, 1.70),
                lead_type=MOLDED_DEFAULT_PROTRUSION,
            ),
        )
        .package_body(
            RectanglePackage(
                width=Toleranced.min_max(2.30, 2.80),
                length=Toleranced.min_max(3.80, 4.50),
                height=Toleranced.min_max(1.85, 2.45),
            )
        )
        .density_level(DensityLevel.B)
    )
    symbol = SchottkyDiodeSymbol()

    def __init__(self) -> None:
        lp = self.landpattern
        self.mappings = [PadMapping({self.K: [lp.p[1]], self.A: [lp.p[2]]})]


class SS54Harness(Circuit):
    """One Schottky, unconnected."""

    diode = SS54()


class TestDesign(SampleDesign):
    """Build harness: ``jitx build pappalapap.components.mdd_ss54.TestDesign``."""

    circuit = SS54Harness()
