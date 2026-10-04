"""Two solder-in wire pads (+5V, GND) for 18 AWG supply wires, with a cable-tie hole pair.

What this component is: board copper, not a bought part (``in_bom = False``).
The column board's supply arrives as two 18 AWG wires (up to ~5.5 A) running
up the hollow column from the base; each is stripped, pushed through a plated
hole and soldered. A cable tie through the two non-plated holes below the
pads clamps both wires to the board so the solder joints carry no pull.

Sources and design choices (no vendor drawing exists; these are the numbers
to check):

- 18 AWG: 1.024 mm conductor diameter (AWG definition, 0.127 mm x 92^((36 -
  18) / 39)). Stranded 18 AWG (16 x 30 AWG, the usual hook-up wire) bundles
  to about 1.2 mm. ``HOLE`` = 1.4 mm leaves about 0.2 mm for tinned
  strands (the user's starting point was 1.3 mm hole / 2.6 mm pad;
  enlarged by 0.1 / 0.2 mm for stranded wire). ``PAD`` = 2.8 mm keeps a
  0.7 mm annular ring for the fillet and the 5 A joint.
- ``PITCH`` = 5.08 mm: 2.28 mm copper gap between the two pads; the PVC
  insulation of 18 AWG hook-up wire (about 2.0-2.4 mm outer diameter) still
  fits side by side.
- Cable-tie holes: ``TIE_HOLE`` = 3.0 mm non-plated, enough for a 2.5 mm
  wide x 1 mm thick miniature tie (its diagonal is 2.7 mm); centres
  ``TIE_DX`` either side of the pair centre, outside both wires' insulation,
  and ``TIE_DY`` below the pad row (toward the wire entry).

Coordinate frame (top view, y up): origin midway between the two pads; pad 1
(+5V, square) at x = +PITCH / 2, pad 2 (GND, round) at x = -PITCH / 2; the
wires arrive from -y, where the tie holes are. Silkscreen "+5V" / "GND" sit
above the pads; the courtyard is a "T": pads + 0.25 mm, widening to the tie
holes + 0.25 mm only below the pads.
"""

from typing import ClassVar

import shapely
from jitx.circuit import Circuit
from jitx.component import Component
from jitx.feature import Courtyard, Cutout, Silkscreen
from jitx.landpattern import Landpattern, PadMapping
from jitx.net import Port
from jitx.sample import SampleDesign
from jitx.shapes.composites import rectangle
from jitx.shapes.primitive import Circle, Text
from jitx.shapes.shapely import ShapelyGeometry
from jitxlib.landpatterns.pads import THPad
from jitxlib.symbols.box import BoxSymbol, PinGroup, Row

# --- Design choices (see docstring) ----------------------------------------------
HOLE = 1.4
PAD = 2.8
PITCH = 5.08
TIE_HOLE = 3.0
TIE_DX = 5.5
TIE_DY = 4.0
LABEL_SIZE = 1.0
LABEL_GAP = 0.6
"""Pad edge to the near edge of its silkscreen label (mm)."""
COURTYARD_EXCESS = 0.25


class WirePadsLandpattern(Landpattern):
    """Two 1.4 / 2.8 mm plated holes at 5.08 mm, cable-tie holes below."""

    def __init__(self) -> None:
        hole = Circle(diameter=HOLE)
        self.p = {
            1: THPad(rectangle(PAD, PAD), hole).at(PITCH / 2, 0.0),
            2: THPad(Circle(diameter=PAD), hole).at(-PITCH / 2, 0.0),
        }
        self.tie_holes = [
            Cutout(Circle(diameter=TIE_HOLE).at(sx * TIE_DX, -TIE_DY)) for sx in (-1, 1)
        ]
        y_label = PAD / 2 + LABEL_GAP + LABEL_SIZE / 2
        self.labels = [
            Silkscreen(Text("+5V", LABEL_SIZE).at(PITCH / 2, y_label)),
            Silkscreen(Text("GND", LABEL_SIZE).at(-PITCH / 2, y_label)),
        ]
        # T-shaped: narrow around the pads, full width only down at the tie
        # holes, so parts beside the pads (the fuse) may sit above the holes.
        e = COURTYARD_EXCESS
        x_pads = PITCH / 2 + PAD / 2 + e
        x_ties = TIE_DX + TIE_HOLE / 2 + e
        y_pads = -PAD / 2 - e
        y_ties_top = -TIE_DY + TIE_HOLE / 2 + e
        tee = shapely.union_all(
            [
                shapely.box(-x_pads, y_pads, x_pads, PAD / 2 + e),
                shapely.box(-x_ties, -TIE_DY - TIE_HOLE / 2 - e, x_ties, y_ties_top),
                shapely.box(-x_pads, y_ties_top, x_pads, y_pads),
            ]
        )
        assert isinstance(tee, shapely.Polygon), tee.geom_type
        self.courtyard = Courtyard(ShapelyGeometry(tee))


class WirePads(Component):
    """Solder pads for the +5V / GND supply wires; ``VIN`` = pad 1 (square)."""

    manufacturer = "n/a (board copper)"
    mpn = "WIRE-PADS-2P-18AWG"
    reference_designator_prefix = "J"
    in_bom = False
    wire_gauge_awg: ClassVar[int] = 18
    WIRE_ENTRY_DIRECTION: ClassVar[str] = "-y"
    PITCH: ClassVar[float] = PITCH
    PAD: ClassVar[float] = PAD

    VIN = Port()
    GND = Port()

    landpattern = WirePadsLandpattern()
    symbol = BoxSymbol(rows=Row(left=PinGroup(VIN, GND)))

    def __init__(self) -> None:
        lp = self.landpattern
        self.mappings = [PadMapping({self.VIN: [lp.p[1]], self.GND: [lp.p[2]]})]


class WirePadsHarness(Circuit):
    """One wire-pad pair, unconnected."""

    pads = WirePads()


class TestDesign(SampleDesign):
    """Build harness: ``jitx build pappalapap.components.wire_pads.TestDesign``."""

    circuit = WirePadsHarness()
