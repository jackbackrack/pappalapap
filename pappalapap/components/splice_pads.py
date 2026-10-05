"""Splice pads: the plated through-holes that solder two flex segments together.

What this is: board copper, not a bought part. The LED strip is two boards
(segment A, columns 0..23, and segment B, columns 24..48; see
``pappalapap.circuits.led_strip``) joined by a lap splice: segment B lies on
top of segment A over an ``overlap`` (5 mm) centred on the column gap between
columns 23 and 24, A's TOP face against B's BOTTOM face, no twist. Each board
carries this same pad field at the same strip (x, y). Solder flowed into the
stacked holes joins the two pads of each pair, and since the holes are plated,
both copper layers of both boards reach every joint.

``in_bom = False``: JLC does not place anything here. ``soldered`` is left at
its default (True) because the pads ARE soldered, by hand, after assembly. The
jitxlib.jlcpcb exporter logs "soldered but not in the bill of materials;
omitting it from both fab files" for that combination, which is the wanted
result: no BOM line, no CPL line (accepted 2026-10-05).

Pad field, in the component frame (origin on the joint line x_j, y = the strip
centreline, top view; placed at rotation 0 on the top side of both segments):

- Data pads, ``DATA_HOLE`` / ``DATA_PAD`` (0.4 / 0.9 mm), four per LED row, one
  per chain hop that crosses the joint: top-face DO->DI and BO->BI at
  x = -``DATA_DX``, bottom-face DO->DI and BO->BI at x = +``DATA_DX``;
  primary (DO->DI) at y = row - ``DATA_DY``, backup (BO->BI) at row +
  ``DATA_DY``. So each row's 2 x 2 group sits inside the row's data band (the
  copper-free +/-2 mm strip between the power lanes): pad copper reaches
  +/-1.25 mm, leaving 0.75 mm to the lanes, room for one 0.2 mm trace with
  0.2 mm clearance outside each pad column and one between its two pads.
  Pads are 1.6 mm apart vertically and 2.0 mm horizontally.
- Power pads, ``POWER_HOLE`` / ``POWER_PAD`` (0.6 / 1.2 mm), inside each of the
  six power lanes on the lane's own net: as many columns at
  ``POWER_PITCH_X`` as fit in the overlap's copper span (3) and as many rows
  at ``POWER_PITCH_Y`` as fit in the lane (2 in the 5.1 mm gap lanes, 1 in
  the 2.25 mm margin lanes): 15 VDD + 15 GND pads. Each VDD/GND net has three
  lanes in parallel, so up to 5.5 A crosses on 15 joints per rail.

Every coordinate comes from the strip (its lanes and row centres) and the
splice overlap; the asserts check that every pad lies inside the copper span
of the overlap on both boards and inside its band or lane.
"""

from collections.abc import Sequence

from jitx.component import Component
from jitx.feature import Courtyard, Custom
from jitx.landpattern import Landpattern, PadMapping
from jitx.layerindex import Side
from jitx.net import Port
from jitx.shapes.composites import rectangle
from jitx.shapes.primitive import Circle
from jitxlib.landpatterns.pads import THPad
from jitxlib.symbols.box import BoxSymbol, Column, PinGroup, Row

from ..circuits.led_strip import Lane, LedStrip
from .worldsemi_ws2816c import DataPath

# --- Design choices (see module docstring) ----------------------------------------
DATA_HOLE = 0.4
DATA_PAD = 0.9
"""0.25 mm annular ring: JLC's recommended PTH ring."""
DATA_DX = 1.0
"""Data pad column offset from the joint line (mm)."""
DATA_DY = 0.8
"""Data pad offset from the row centreline (mm)."""
POWER_HOLE = 0.6
POWER_PAD = 1.2
POWER_PITCH_X = 1.5
POWER_PITCH_Y = 2.0
LANE_MARGIN = 0.3
"""Least distance from a power pad's copper to its lane's edge (mm)."""
OUTLINE_WIDTH = 0.1
"""Stroke of the overlap outline on the fab-drawing layer (mm)."""


class SpliceOverlap(Custom):
    """Fab-drawing layer: the lap-splice overlap, where the other segment lies."""


def centred(count: int, pitch: float) -> list[float]:
    """``count`` offsets at ``pitch``, centred on zero."""
    return [(i - (count - 1) / 2) * pitch for i in range(count)]


def fit(span: float, size: float, pitch: float) -> int:
    """How many features of ``size`` at ``pitch`` fit inside ``span``."""
    return int((span - size) // pitch) + 1 if span >= size else 0


class SplicePadsLandpattern(Landpattern):
    """Data pads per row and face, power pads per lane (module docstring)."""

    def __init__(
        self,
        row_ys: Sequence[float],
        lanes: Sequence[Lane],
        overlap: float,
        edge: float,
        clearance: float,
    ) -> None:
        half_span = overlap / 2 - edge
        """Copper must stay this close to the joint line on both boards."""
        assert DATA_DX + DATA_PAD / 2 <= half_span, "data pads leave the overlap"

        data_hole = Circle(diameter=DATA_HOLE)
        data_copper = Circle(diameter=DATA_PAD)

        def data_pads(face: Side, path: DataPath) -> list[THPad]:
            x = -DATA_DX if face == Side.Top else DATA_DX
            dy = -DATA_DY if path == DataPath.PRIMARY else DATA_DY
            return [THPad(data_copper, data_hole).at(x, y + dy) for y in row_ys]

        self.top_primary = data_pads(Side.Top, DataPath.PRIMARY)
        self.top_backup = data_pads(Side.Top, DataPath.BACKUP)
        self.bottom_primary = data_pads(Side.Bottom, DataPath.PRIMARY)
        self.bottom_backup = data_pads(Side.Bottom, DataPath.BACKUP)
        # Each row's pads stay inside the data band between its two lanes.
        reach = DATA_DY + DATA_PAD / 2
        for row, y in enumerate(row_ys):
            assert lanes[row].y_hi + clearance <= y - reach, "data pad on a lane"
            assert y + reach <= lanes[row + 1].y_lo - clearance, "data pad on a lane"

        power_hole = Circle(diameter=POWER_HOLE)
        power_copper = Circle(diameter=POWER_PAD)
        y_min = lanes[0].y_lo + edge
        y_max = lanes[-1].y_hi - edge
        xs = centred(fit(2 * half_span, POWER_PAD, POWER_PITCH_X), POWER_PITCH_X)
        self.vdd_pads: list[THPad] = []
        self.gnd_pads: list[THPad] = []
        for lane in lanes:
            lo = max(lane.y_lo, y_min) + LANE_MARGIN
            hi = min(lane.y_hi, y_max) - LANE_MARGIN
            ys = centred(fit(hi - lo, POWER_PAD, POWER_PITCH_Y), POWER_PITCH_Y)
            assert xs and ys, f"no power pad fits in lane {lane.index}"
            pads = self.vdd_pads if lane.is_vdd else self.gnd_pads
            pads.extend(
                THPad(power_copper, power_hole).at(x, (lo + hi) / 2 + dy)
                for x in xs
                for dy in ys
            )

        height = lanes[-1].y_hi - lanes[0].y_lo
        centre_y = (lanes[-1].y_hi + lanes[0].y_lo) / 2
        self.courtyard = Courtyard(rectangle(overlap, height).at(0.0, centre_y))
        self.overlap_outline = [
            SpliceOverlap(
                rectangle(OUTLINE_WIDTH, height).at(sx * overlap / 2, centre_y),
                side=side,
            )
            for sx in (-1, 1)
            for side in (Side.Top, Side.Bottom)
        ]

    def data_pad(self, face: Side, row: int, path: DataPath) -> THPad:
        """The pad for one face's hop on one data path in one row."""
        if face == Side.Top:
            pads = self.top_primary if path == DataPath.PRIMARY else self.top_backup
        else:
            pads = (
                self.bottom_primary if path == DataPath.PRIMARY else self.bottom_backup
            )
        return pads[row]


class SplicePads(Component):
    """Lap-splice pad field for one joint of the segmented LED strip.

    Ports: per row, one per crossing hop (``top_primary[r]`` = top-face DO->DI,
    ``top_backup[r]`` = top-face BO->BI, ``bottom_*`` likewise), and ``VDD`` /
    ``GND`` mapped to all power pads of that rail. Built from the strip that
    owns the geometry; place it at ``(strip.column_edge_x(joint_col), 0)``.
    """

    manufacturer = "n/a (board copper)"
    mpn = "SPLICE-PADS"
    reference_designator_prefix = "J"
    in_bom = False
    # soldered: default (True), hand-soldered after assembly; see module docstring.

    VDD = Port()
    GND = Port()

    def __init__(
        self,
        strip: LedStrip,
        overlap: float,
        data_band: float,
        edge: float,
        clearance: float,
    ) -> None:
        rows = range(strip.rows)
        self.overlap = overlap
        self.landpattern = SplicePadsLandpattern(
            [strip.row_y(r) for r in rows],
            strip.lanes(data_band),
            overlap,
            edge,
            clearance,
        )
        self.top_primary = [Port() for _ in rows]
        self.top_backup = [Port() for _ in rows]
        self.bottom_primary = [Port() for _ in rows]
        self.bottom_backup = [Port() for _ in rows]
        lp = self.landpattern
        mapping = {self.VDD: lp.vdd_pads, self.GND: lp.gnd_pads}
        for r in rows:
            for face in (Side.Top, Side.Bottom):
                for path in DataPath:
                    mapping[self.data_port(face, r, path)] = [
                        lp.data_pad(face, r, path)
                    ]
        self.mappings = [PadMapping(mapping)]
        self.symbol = BoxSymbol(
            rows=Row(
                left=PinGroup(*self.top_primary, *self.top_backup),
                right=PinGroup(*self.bottom_primary, *self.bottom_backup),
            ),
            columns=Column(up=PinGroup(self.VDD), down=PinGroup(self.GND)),
        )

    def data_port(self, face: Side, row: int, path: DataPath) -> Port:
        """The port for one face's hop on one data path in one row."""
        if face == Side.Top:
            ports = self.top_primary if path == DataPath.PRIMARY else self.top_backup
        else:
            ports = (
                self.bottom_primary if path == DataPath.PRIMARY else self.bottom_backup
            )
        return ports[row]


# No standalone TestDesign: the pad field is built from a strip and the splice
# overlap, so it is exercised by the FlexSegmentA / FlexSegmentB builds and
# checked by scripts/check_splice.py.
