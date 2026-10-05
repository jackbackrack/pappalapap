"""One-board flex strip variant ("1seg", 2026-10-05): the whole strip on one board.

Same grid as the original 490 mm design (49 columns x 5 rows, top face cols
1..47, bottom face cols 0..48, 480 LEDs, 96 loop columns, one-pitch Möbius lap
at each end, row-major serpentine) at a pitch of 230 / 49 = 4.6939 mm, so the
strip (230.0 x 23.47 mm) is as long as JLCPCB assembles on a 240 mm panel side
with 5 mm rails. No splice. Same 16-finger tail, 50 mm long, centred 10.35 mm
from end A. Geometry: ``ONE_SEGMENT`` in ``pappalapap/variants.py``; the board
is built by the same ``FlexStrip`` as the two-segment strip
(``designs/flex_strip.py``) and panelised by the same machinery
(``designs/flex_panel.py``).

Build targets:

- ``FlexOneSegment``: the board (build/view), layout file
  ``layout/flex_one_segment.json``.
- ``FlexOnePanel``: what is ordered, the board on a 240 x 85.5 mm JLC assembly
  panel (end rails 5.0 mm, top/bottom 6.02 mm so the corner tooling holes fit,
  2 mm slot, tabs with mouse bites, 3 fiducials per face, 4 tooling holes).
  Reads the board's layout file; writes ``layout/flex_one_panel-input.json``.

What 4.69 mm costs (numbers from ``scripts/check_strip_fit.py``):

- Data band +/-1.0 mm (WS2816C pads reach +/-0.79, plus the 0.15 mm
  clearance). The hops between neighbouring LEDs (2.10 mm pad gap) route as
  two straight 0.15 mm diagonals 0.46 mm apart inside +/-0.71 mm.
- Power lanes: 2.69 mm between rows, 1.05 mm copper in the two margin lanes,
  per layer. All VDD current enters the bottom-margin lane at end A (the VDD
  lanes join only at the end-B spine), so that 1.05 mm lane, on both layers,
  is the bottleneck: about 2.0 A for a 10 degC rise (IPC-2221 internal-layer
  constant for coverlaid flex). Firmware cap: 2.0 A total.
- Strip-end channels 1.05 mm (top, spine to LED pads) and 0.75 mm (bottom, LED
  pads to the copper-edge limit): two U-turn traces at 0.15 / 0.15 mm; the
  end-B crossover's two vias (0.6 mm) fit the top channel at end B. Pour
  tongues are exactly pad-wide (``tongue_side_margin`` 0) so they do not eat
  the channels.
- Tail: the GND riser is clipped to the 4.69 mm spine (2.84 mm wide, 2 x 5
  transition vias); DIN jogs left in the tail and rises through the 1.05 mm
  channel between the spine and top col 1.
"""

from ..variants import ONE_SEGMENT
from .flex_panel import FlexPanelDesign
from .flex_strip import FlexStripDesign

LAYOUT_FILE = "layout/flex_one_segment.json"
"""Layout round-trip file of the one-board strip (relative to the project
root, where jitx builds run)."""
LAYOUT_OUTPUT_PANEL = "layout/flex_one_panel-input.json"


class FlexOneSegment(FlexStripDesign):
    """The one-board strip (all 49 columns, tail, both spines), orderable
    length: ``jitx build pappalapap.designs.one_segment.FlexOneSegment``."""

    def __init__(self) -> None:
        super().__init__(ONE_SEGMENT, None, LAYOUT_FILE, orderable=True)


class FlexOnePanel(FlexPanelDesign):
    """The one-board strip on its JLC assembly panel, what is ordered:
    ``jitx build pappalapap.designs.one_segment.FlexOnePanel``."""

    def __init__(self) -> None:
        super().__init__(ONE_SEGMENT, None, LAYOUT_FILE, LAYOUT_OUTPUT_PANEL)
