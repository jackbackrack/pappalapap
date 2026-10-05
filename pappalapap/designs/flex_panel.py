"""JLCPCB flex assembly panels around the two strip segments (2026-10-05).

JLCPCB assembles flex boards only on a panel whose one side is exactly one of
``PANEL_SIDES`` (79, 119 or 240 mm), whose other side is at least
``PANEL_MIN_SHORT`` (70 mm), no side longer than ``PANEL_LONG`` (240 mm), with
edge rails of at least ``MIN_RAIL`` (5 mm) on all four sides. ``FlexPanelA``
and ``FlexPanelB`` are the orderable designs: each is the segment design
(``designs/flex_strip.py``) with the same circuit, unchanged, at the same
coordinates, and a panel board around it.

Panel size (``PanelSize.fit``), from the segment outline's bounding box
(L along the strip, W across, tail included):

- the side along the strip is the smallest allowed side >= L + 2 x MIN_RAIL;
- the other side is max(W + 2 x MIN_RAIL, PANEL_MIN_SHORT);
- the segment is centred, so the rails are half the slack on each axis.

  ========  =============  =============  =======================
  segment   outline (mm)   panel (mm)     rails (end / top+bottom)
  ========  =============  =============  =======================
  A         220.9 x 95.5   240.0 x 105.5  9.55 / 5.0
  B         230.0 x 45.5   240.0 x 70.0   5.0 / 12.25
  ========  =============  =============  =======================

A rail is measured from the panel edge to the segment outline, as JLC states
it; the separation slot (``SLOT_WIDTH``) lies inside it, so the solid frame
beyond the slot is rail - 2 mm (3 mm on A's long sides and B's ends).

Segment A's tail hangs below the strip, and the bottom rail is measured from
the tail's cut end. The area between the strip's bottom edge and that rail,
left and right of the tail, is panel material (not open): it stiffens the
panel, carries tabs along the strip's bottom edge, and holds one fiducial.

Board shape = panel rectangle minus the slot: the segment outline grown by
``SLOT_WIDTH``, minus the segment, minus the breakaway tabs. The tabs bridge
the slot, so the board is one polygon whose holes are the slot pieces (JITX
turns board holes into cutouts; the gerber profile strokes them). The signal
area stays the segment's own (outline inset by the copper-to-edge rule), so
pours, routing and placement stay on the segment: a holed board shape reaches
the router as its outer boundary, which would otherwise be the whole panel.

Tabs (``TAB_WIDTH`` wide, at most ``TAB_PITCH`` apart along each straight
edge, ``TAB_CORNER_MARGIN`` clear of corners) never land:

- on the Möbius lap zones' long edges (the strip ends that glue together; the
  strip-end edge itself does get tabs, its nub is in plane),
- on the splice overlap or its end edge (the splice pads sit 0.9 mm from that
  edge, and segment B lies on A there),
- on the tail fingers or the PI stiffener (``FpcTail16.STIFFENER_LENGTH`` from
  the cut end, plus ``TAB_KEEPOFF``).

Each tab carries a row of mouse-bite holes (NPTH ``MOUSE_BITE_HOLE`` at
``MOUSE_BITE_PITCH`` = hole + the fab's 0.4 mm hole-to-hole rule = 0.9 mm,
so 3 per 3 mm tab; 0.8 mm would break that rule) along the segment
edge, set back into the tab (rail side) by ``MOUSE_BITE_SETBACK`` so the
segment outline itself is not perforated and its copper keeps >= 0.4 mm to
the holes.

Rails carry 3 fiducials on each face (``FIDUCIAL_COPPER`` copper in a
``FIDUCIAL_MASK`` mask/coverlay opening, an asymmetric L: top-left, top-right,
bottom-left further in) and 4 tooling holes (NPTH ``TOOLING_HOLE``) near the
panel corners. The fiducials are netless copper (``OverlappableCopper``) plus
mask openings added to the circuit, not components, so they are not in the BOM
or CPL (a JITX Board carries only non-copper features: the holes live there). Every rail feature is asserted to lie in the solid frame
with the copper-to-edge rule (fiducials) or ``TOOLING_CLEARANCE`` (holes) to
the slot and panel edges.

Routing: the panel's circuit is the segment's ``FlexStrip`` with the same
instance paths, and the panel reads the segment's layout file
(``layout/flex_segment_[ab].json``: placements, vias, route sketches), so
code-side layout carries over. JITX editor state (interactive routing) lives
in each design's own ``designs/<design>/design-info``; route the panel designs
(they are what is ordered).
"""

import math
from collections.abc import Iterator
from dataclasses import dataclass
from itertools import pairwise

import shapely
from jitx.board import Board
from jitx.feature import Cutout, OverlappableCopper, Soldermask
from jitx.layerindex import Side
from jitx.shapes.primitive import Circle
from shapely.geometry.base import BaseGeometry
from shapely.geometry.polygon import orient

from ..components.fpc_tail import FpcTail16
from ..substrate import JLCFlexRules
from ..variants import TWO_SEGMENT, StripVariant
from .flex_strip import (
    BOTTOM_LAYER,
    LAYOUT_FILE_A,
    LAYOUT_FILE_B,
    TOP_LAYER,
    FlexStrip,
    FlexStripDesign,
    as_shape,
    box,
    union,
)
from .layout_placements import layout_placements

# --- JLCPCB flex assembly panel rule ----------------------------------------------
PANEL_LONG = 240.0
"""Longest panel side JLC assembles (mm)."""
PANEL_SIDES = (79.0, 119.0, PANEL_LONG)
"""One panel side must be exactly one of these (mm)."""
PANEL_MIN_SHORT = 70.0
"""The other panel side must be at least this (mm)."""
MIN_RAIL = 5.0
"""Least edge rail on every side, panel edge to board outline (mm)."""

LAYOUT_OUTPUT_A = "layout/flex_panel_a-input.json"
LAYOUT_OUTPUT_B = "layout/flex_panel_b-input.json"

# --- Panel features (design choices) ----------------------------------------------
SLOT_WIDTH = 2.0
"""Routed/lasered separation slot around the segment outline (mm)."""
TAB_WIDTH = 3.0
"""Breakaway tab width along the segment edge (mm)."""
TAB_PITCH = 30.0
"""Largest centre distance between neighbouring tabs on one edge (mm)."""
TAB_CORNER_MARGIN = 2.0
"""Tab edge to the end of its straight outline edge (mm)."""
TAB_KEEPOFF = 1.0
"""Extra clearance from a no-tab zone to a tab (mm)."""
EPS = 0.01
"""Tab overlap into the segment and the frame, so the shapes fuse (mm)."""

MOUSE_BITE_HOLE = 0.5
MOUSE_BITE_PITCH = MOUSE_BITE_HOLE + JLCFlexRules.min_hole_to_hole
"""0.9 mm: hole plus the fab's least hole-to-hole web (0.4 mm)."""
MOUSE_BITE_SETBACK = 0.1
"""Gap from the segment outline to the hole edge, on the rail side (mm)."""

FIDUCIAL_COPPER = 1.0
FIDUCIAL_MASK = 2.0
FIDUCIAL_END_OFFSET = 10.0
"""Fiducial centre to the panel's short edge, top-left and top-right (mm)."""
FIDUCIAL_ASYMMETRY = 10.0
"""The bottom-left fiducial sits this much further in, so the three are not
symmetric under a 180 degree turn (mm)."""

TOOLING_HOLE = 2.0
TOOLING_INSET = 2.5
"""Tooling-hole centre to both panel edges at its corner (mm)."""
TOOLING_CLEARANCE = 0.5
"""Least frame material around a tooling hole (mm)."""
TOOLING_RAIL = SLOT_WIDTH + TOOLING_INSET + TOOLING_HOLE / 2 + TOOLING_CLEARANCE
"""6.0 mm: the rail a corner tooling hole needs on at least one axis."""

PANEL_STEP = 0.5
"""The panel side across the strip is a multiple of this (mm)."""


@dataclass(frozen=True)
class PanelSize:
    """Panel extent around a board outline, derived from the panel rule."""

    width: float
    """Along the strip (x), mm."""
    height: float
    """Across the strip (y), mm."""
    rail_x: float
    """Each end rail, panel edge to outline (mm)."""
    rail_y: float
    """Top and bottom rails (mm)."""

    @classmethod
    def fit(cls, length: float, breadth: float) -> "PanelSize":
        """Smallest panel around a ``length`` x ``breadth`` board, centred.
        The corner tooling holes need ``TOOLING_RAIL`` on one axis: when the
        end rails are thinner, the top and bottom rails grow to it. The side
        across the strip is rounded up to ``PANEL_STEP``."""
        width = min(s for s in PANEL_SIDES if s >= length + 2 * MIN_RAIL - 1e-9)
        rail_y = MIN_RAIL if (width - length) / 2 >= TOOLING_RAIL else TOOLING_RAIL
        height = max(breadth + 2 * rail_y, PANEL_MIN_SHORT)
        height = math.ceil(height / PANEL_STEP - 1e-9) * PANEL_STEP
        size = cls(width, height, (width - length) / 2, (height - breadth) / 2)
        size.check()
        return size

    def check(self) -> None:
        """Assert the JLC flex assembly panel rule."""
        sides = (self.width, self.height)
        assert any(
            math.isclose(side, allowed) for side in sides for allowed in PANEL_SIDES
        ), f"no panel side in {PANEL_SIDES}: {sides}"
        assert min(sides) >= PANEL_MIN_SHORT - 1e-9, f"panel too narrow: {sides}"
        assert max(sides) <= PANEL_LONG + 1e-9, f"panel too long: {sides}"
        assert min(self.rail_x, self.rail_y) >= MIN_RAIL - 1e-9, (
            f"rail under {MIN_RAIL} mm: {self.rail_x}, {self.rail_y}"
        )


@dataclass(frozen=True)
class Tab:
    """A breakaway tab across the slot at one point of a straight outline edge."""

    x: float
    y: float
    """Point on the segment outline (mm)."""
    normal: tuple[float, float]
    """Outward unit normal of the edge (axis-aligned)."""

    @property
    def tangent(self) -> tuple[float, float]:
        nx, ny = self.normal
        return (-ny, nx)

    def at(self, along: float, out: float) -> tuple[float, float]:
        """Point ``along`` the edge and ``out`` of the segment from the tab centre."""
        (tx, ty), (nx, ny) = self.tangent, self.normal
        return (self.x + along * tx + out * nx, self.y + along * ty + out * ny)

    def shape(self) -> shapely.Polygon:
        """The tab's bridge across the slot (with EPS overlap both ends)."""
        x0, y0 = self.at(-TAB_WIDTH / 2, -EPS)
        x1, y1 = self.at(TAB_WIDTH / 2, SLOT_WIDTH + EPS)
        return box(x0, y0, x1, y1)

    def mouse_bites(self) -> Iterator[tuple[float, float]]:
        """Centres of the tab's NPTH row, along the edge, set back into the tab."""
        count = int((TAB_WIDTH - MOUSE_BITE_HOLE) // MOUSE_BITE_PITCH) + 1
        out = MOUSE_BITE_SETBACK + MOUSE_BITE_HOLE / 2
        for k in range(count):
            yield self.at((k - (count - 1) / 2) * MOUSE_BITE_PITCH, out)


def no_tab_zones(strip: FlexStrip) -> BaseGeometry:
    """Where a tab must not land (module docstring): Möbius lap long edges,
    splice overlaps and their end edges, tail fingers and stiffener."""
    reach = SLOT_WIDTH + TAB_KEEPOFF
    zones: list[BaseGeometry] = []
    # Lap zones: an x band over the strip's long edges, starting just inside
    # the strip end (past a tab's EPS overlap) so the end edge stays allowed.
    y0, y1 = strip.y_bottom - reach, strip.y_top + reach
    if strip.has_end_a:
        zones.append(box(strip.x_a + 2 * EPS, y0, strip.lap_a_edge + TAB_KEEPOFF, y1))
    if strip.has_end_b:
        zones.append(box(strip.lap_b_edge - TAB_KEEPOFF, y0, strip.x_b - 2 * EPS, y1))
    # Splice overlaps, grown over their end edge.
    zones += [zone.buffer(reach, join_style="mitre") for zone in strip.splice_zones]
    if strip.tail is not None:
        half = FpcTail16.TAIL_WIDTH / 2
        stiffener = box(
            strip.tail_x - half,
            strip.y_cut,
            strip.tail_x + half,
            strip.y_cut + FpcTail16.STIFFENER_LENGTH,
        )
        zones.append(stiffener.buffer(reach, join_style="mitre"))
    return union(zones)


def place_tabs(outline: shapely.Polygon, blocked: BaseGeometry) -> list[Tab]:
    """Tabs along every straight, axis-aligned outline edge, at most
    TAB_PITCH apart, clear of corners and of ``blocked``."""
    ring = list(orient(outline, 1.0).exterior.coords)
    tabs: list[Tab] = []
    for (xa, ya), (xb, yb) in pairwise(ring):
        length = math.hypot(xb - xa, yb - ya)
        if length < TAB_WIDTH + 2 * TAB_CORNER_MARGIN:
            continue
        if not (math.isclose(xa, xb) or math.isclose(ya, yb)):
            continue
        tx, ty = (xb - xa) / length, (yb - ya) / length
        normal = (ty, -tx)  # outward for a counter-clockwise exterior
        # Free stretches of tab centres along the edge, parameter s from (xa, ya).
        lo = TAB_CORNER_MARGIN + TAB_WIDTH / 2
        free = [(lo, length - lo)]
        # The strip a tab would cover anywhere along this edge.
        band = box(
            *Tab(xa, ya, normal).at(0, -EPS),
            *Tab(xb, yb, normal).at(0, SLOT_WIDTH + EPS),
        )
        hit = band.intersection(blocked)
        for part in shapely.get_parts(hit):
            if part.is_empty or part.area <= 0:
                continue
            bx0, by0, bx1, by1 = part.bounds
            s = sorted(
                ((bx0 - xa) * tx + (by0 - ya) * ty, (bx1 - xa) * tx + (by1 - ya) * ty)
            )
            cut = (s[0] - TAB_WIDTH / 2, s[1] + TAB_WIDTH / 2)
            free = [
                piece
                for u, v in free
                for piece in ((u, min(v, cut[0])), (max(u, cut[1]), v))
                if piece[1] >= piece[0]
            ]
        for u, v in free:
            count = 1 if v - u < 2 * TAB_WIDTH else math.ceil((v - u) / TAB_PITCH) + 1
            spots = (
                [(u + v) / 2]
                if count == 1
                else [u + k * (v - u) / (count - 1) for k in range(count)]
            )
            tabs += [Tab(xa + s * tx, ya + s * ty, normal) for s in spots]
    return tabs


def disc(x: float, y: float, diameter: float) -> shapely.Polygon:
    return shapely.Point(x, y).buffer(diameter / 2, quad_segs=32)


class FlexPanelBoard(Board):
    """Panel rectangle minus the separation slot around the segment, with tabs,
    mouse bites, fiducials and tooling holes (module docstring). The signal
    area is the segment's."""

    def __init__(self, strip: FlexStrip) -> None:
        outline = strip.outline
        assert isinstance(outline, shapely.Polygon)
        x0, y0, x1, y1 = outline.bounds
        self.size = PanelSize.fit(x1 - x0, y1 - y0)
        px0, py0 = x0 - self.size.rail_x, y0 - self.size.rail_y
        px1, py1 = x1 + self.size.rail_x, y1 + self.size.rail_y
        self.panel = box(px0, py0, px1, py1)

        cleared = outline.buffer(SLOT_WIDTH, join_style="mitre")
        self.tabs = place_tabs(outline, no_tab_zones(strip))
        slot = cleared.difference(outline).difference(
            union(tab.shape() for tab in self.tabs)
        )
        board = self.panel.difference(slot)
        assert isinstance(board, shapely.Polygon), "panel must be one piece"
        self.shape = as_shape(board)
        self.signal_area = as_shape(strip.copper_area)

        frame = self.panel.difference(cleared)  # solid rail beyond the slot
        edge = strip.edge

        # Mouse bites (NPTH), clear of the segment's copper.
        bites = [xy for tab in self.tabs for xy in tab.mouse_bites()]
        for x, y in bites:
            hole = disc(x, y, MOUSE_BITE_HOLE)
            assert (
                hole.distance(strip.copper_area) >= JLCFlexRules.min_copper_hole_space
            )
            assert not hole.intersects(outline.buffer(-1e-6)), "bite inside the segment"
        self.mouse_bites = [
            Cutout(Circle(diameter=MOUSE_BITE_HOLE).at(x, y)) for x, y in bites
        ]

        # Tooling holes (NPTH) near the four corners.
        corners = [
            (px0 + TOOLING_INSET, py0 + TOOLING_INSET),
            (px1 - TOOLING_INSET, py0 + TOOLING_INSET),
            (px0 + TOOLING_INSET, py1 - TOOLING_INSET),
            (px1 - TOOLING_INSET, py1 - TOOLING_INSET),
        ]
        for x, y in corners:
            assert frame.contains(disc(x, y, TOOLING_HOLE + 2 * TOOLING_CLEARANCE)), (
                f"tooling hole at ({x:.2f}, {y:.2f}) not in the frame"
            )
        self.tooling_holes = [
            Cutout(Circle(diameter=TOOLING_HOLE).at(x, y)) for x, y in corners
        ]

        # Fiducials, the same three on both faces (top-left, top-right,
        # bottom-left further in: asymmetric).
        # Centred in the solid long-side rail (rail minus slot): 1.5 mm from
        # the panel edge on A, 5.125 mm on B.
        inset = (self.size.rail_y - SLOT_WIDTH) / 2
        self.fiducial_points = [
            (px0 + FIDUCIAL_END_OFFSET, py1 - inset),
            (px1 - FIDUCIAL_END_OFFSET, py1 - inset),
            (px0 + FIDUCIAL_END_OFFSET + FIDUCIAL_ASYMMETRY, py0 + inset),
        ]
        holes = [disc(x, y, TOOLING_HOLE) for x, y in corners]
        for x, y in self.fiducial_points:
            keep = disc(x, y, FIDUCIAL_MASK + 2 * edge)
            assert frame.contains(keep), (
                f"fiducial at ({x:.2f}, {y:.2f}) not in the frame"
            )
            assert not any(keep.intersects(hole) for hole in holes)

    def fiducials(self) -> list[OverlappableCopper | Soldermask]:
        """Fiducial copper and mask openings, the same three on both faces.
        Board objects cannot carry copper (JITX translates only non-copper
        features on a Board), so the design adds these to its circuit."""
        copper: list[OverlappableCopper | Soldermask] = [
            OverlappableCopper(Circle(diameter=FIDUCIAL_COPPER).at(x, y), layer)
            for layer in (TOP_LAYER, BOTTOM_LAYER)
            for x, y in self.fiducial_points
        ]
        masks = [
            Soldermask(Circle(diameter=FIDUCIAL_MASK).at(x, y), side=side)
            for side in (Side.Top, Side.Bottom)
            for x, y in self.fiducial_points
        ]
        return copper + masks


class FlexPanelDesign(FlexStripDesign):
    """A segment design on its JLC assembly panel: same circuit and
    coordinates, reads the segment's layout file (writes its own snapshot);
    panel board, fiducials added to the circuit."""

    def __init__(
        self,
        variant: StripVariant,
        segment: range | None,
        layout_file: str,
        layout_output: str,
    ) -> None:
        self.layout_output = layout_output
        super().__init__(variant, segment, layout_file, orderable=True)

    def make_board(self, strip: FlexStrip) -> Board:
        board = FlexPanelBoard(strip)
        # Added to the circuit after its own objects, so every segment
        # object keeps its instance path.
        for feature in board.fiducials():
            strip += feature
        return board

    def apply_layout(self, layout_file: str) -> None:
        # The segment's layout file, but not its board shape; the snapshot
        # goes to the panel's own -input file.
        layout_placements(
            layout_file, output=self.layout_output, apply_board_shape=False
        )


class FlexPanelA(FlexPanelDesign):
    """Segment A on its 240 x 105.5 mm panel, orderable:
    ``jitx build pappalapap.designs.flex_panel.FlexPanelA``."""

    def __init__(self) -> None:
        super().__init__(
            TWO_SEGMENT, TWO_SEGMENT.segments[0], LAYOUT_FILE_A, LAYOUT_OUTPUT_A
        )


class FlexPanelB(FlexPanelDesign):
    """Segment B on its 240 x 70 mm panel, orderable:
    ``jitx build pappalapap.designs.flex_panel.FlexPanelB``."""

    def __init__(self) -> None:
        super().__init__(
            TWO_SEGMENT, TWO_SEGMENT.segments[1], LAYOUT_FILE_B, LAYOUT_OUTPUT_B
        )
