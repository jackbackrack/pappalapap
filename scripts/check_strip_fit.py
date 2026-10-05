"""Strip fit proof for every variant: hops, end channels, lanes, current, panel, rules.

Run:  python scripts/check_strip_fit.py      (prints a table per variant, exits
      non-zero on any failure; also runs under ``python -m unittest``)

For each ``StripVariant`` (``pappalapap/variants.py``) the one-piece
``FlexStrip(variant)`` is built (same LEDs, copper and channels as its boards)
and checked, reading every number from the built objects:

- Hops: every in-row chain hop (DO->DI and BO->BI between neighbouring LEDs on
  one face) routes as one straight trace from output pad centre to input pad
  centre, at the variant's trace width: each trace keeps the variant's
  clearance to every other pad of both LEDs and to the power copper of its
  face, and the two traces of a hop keep it to each other. Reports the least
  clearance and the largest excursion from the row centreline.
- End channels (U-turns, crossover vias, DIN entry): widths and the width the
  rules need (``FlexStrip.uturn_channels`` / ``din_channel``, asserted there
  too).
- Lanes: copper width of each power lane per layer, and the current the VDD
  bottom-margin lane can carry. All VDD current enters that lane at end A
  (the tail's VDD riser lands in it; the VDD lanes join only at the end-B
  spine), so it carries the whole load at end A and is the strip's
  bottleneck. IPC-2221: I = k x dT^0.44 x A^0.725 (A in mil^2), with the
  internal-conductor k = 0.024 for coverlaid flex (conservative; the
  external k = 0.048 is printed too); the lane's top and bottom copper are
  stitched 25 um apart, so they are one conductor of twice the section.
- Board and panel: every board <= ``MAX_ASSEMBLY_LENGTH``, loop columns
  divisible by 3, the panel around each orderable board passes
  ``PanelSize.check``.
- ``mechanical/variants.py`` holds the same numbers as ``pappalapap/variants.py``.
"""

import importlib.util
import math
import sys
import unittest
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path
from types import ModuleType

import shapely
from jitx.layerindex import Side
from jitx.net import Port
from jitx.substrate import SubstrateContext
from jitx.test import TestCase
from jitx.transform import Transform

from pappalapap.circuits.led_strip import LedSite
from pappalapap.components.worldsemi_ws2816c import WS2816C, DataPath
from pappalapap.designs.flex_panel import PanelSize
from pappalapap.designs.flex_strip import (
    MAX_ASSEMBLY_LENGTH,
    FlexStrip,
    RailFace,
    pad_footprints,
)
from pappalapap.substrate import COPPER_THICKNESS, JLCFlex2L
from pappalapap.variants import ONE_SEGMENT, TWO_SEGMENT, StripVariant

VARIANTS = [("two-segment", TWO_SEGMENT), ("one-segment", ONE_SEGMENT)]
"""(display name, variant)."""

TEMPERATURE_RISE = 10.0
"""Allowed conductor temperature rise for the current rating (degC)."""
IPC_K_INTERNAL = 0.024
IPC_K_EXTERNAL = 0.048
MM_PER_MIL = 0.0254
COPPER_RESISTIVITY = 1.72e-8
"""Ohm m, annealed copper at 20 degC."""
LED_FULL_WHITE = 0.0115
"""Per LED, all three channels on (A); ARCHITECTURE.md Power Tree."""
LED_IDLE = 0.4 / 480
"""Per LED, all off (A)."""
TOLERANCE = 1e-6

MECHANICAL_VARIANTS = (
    Path(__file__).resolve().parent.parent / "mechanical" / "variants.py"
)


def ipc2221_current(width_mm: float, layers: int, k: float) -> float:
    """IPC-2221 current (A) for ``layers`` stacked 1 oz conductors ``width_mm``
    wide at ``TEMPERATURE_RISE``."""
    area = layers * (width_mm / MM_PER_MIL) * (COPPER_THICKNESS / MM_PER_MIL)
    return k * TEMPERATURE_RISE**0.44 * area**0.725


@dataclass(frozen=True)
class HopResult:
    least_clearance: float
    """Smallest gap from a hop trace's copper to foreign copper (mm)."""
    max_excursion: float
    """Largest |y - row centre| reached by trace copper (mm)."""
    hops: int


def pad_of(led: WS2816C, port: Port, frame: Transform | None) -> shapely.Polygon:
    """Board-frame copper of the one pad mapped to ``port``."""
    (pad,) = pad_footprints(led, port, frame)
    return pad


def check_hops(flex: FlexStrip) -> HopResult:
    """Straight-trace check of every in-row hop (module docstring)."""
    strip = flex.strip
    v = flex.variant
    frame = strip.transform
    half = v.trace_width / 2
    least = math.inf
    excursion = 0.0
    hops = 0
    pairs = list(zip(strip.sites, strip.leds, strict=True))
    face_copper = {
        face: shapely.union_all(
            [flex.copper[RailFace(True, face)], flex.copper[RailFace(False, face)]]
        )
        for face in (Side.Top, Side.Bottom)
    }
    for (up_site, up), (down_site, down) in pairwise(pairs):
        if not neighbours(up_site, down_site):
            continue
        hops += 1
        traces = []
        used = []
        for path in DataPath:
            out_pad = pad_of(up, up.output(path), frame)
            in_pad = pad_of(down, down.input(path), frame)
            used += [out_pad, in_pad]
            line = shapely.LineString([out_pad.centroid, in_pad.centroid])
            traces.append(line.buffer(half, cap_style="flat"))
        others = [
            pad
            for led in (up, down)
            for port in (led.DI, led.DO, led.BI, led.BO, led.VDD, led.GND)
            for pad in pad_footprints(led, port, frame)
            if not any(pad.equals(u) for u in used)
        ]
        obstacles = shapely.union_all([*others, face_copper[up_site.face]])
        row_y = strip.row_y(up_site.row)
        for trace in traces:
            least = min(least, trace.distance(obstacles))
            _, y0, _, y1 = trace.bounds
            excursion = max(excursion, abs(y0 - row_y), abs(y1 - row_y))
        least = min(least, traces[0].distance(traces[1]))
    return HopResult(least, excursion, hops)


def neighbours(a: LedSite, b: LedSite) -> bool:
    """Consecutive chain sites that are an in-row hop (not a U-turn or the
    crossover)."""
    return a.face == b.face and a.row == b.row and abs(a.col - b.col) == 1


def lane_widths(flex: FlexStrip) -> list[float]:
    """Copper width of each lane per layer, bottom to top (mm)."""
    lo_limit = flex.y_bottom + flex.edge
    hi_limit = flex.y_top - flex.edge
    return [min(lane.y_hi, hi_limit) - max(lane.y_lo, lo_limit) for lane in flex.lanes]


def load_mechanical_variants() -> ModuleType:
    """Import mechanical/variants.py by path (it lives outside the package)."""
    spec = importlib.util.spec_from_file_location("mech_variants", MECHANICAL_VARIANTS)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class StripFitTest(TestCase):
    """Every variant fits its rules (module docstring)."""

    strips: list[tuple[str, StripVariant, FlexStrip, list[FlexStrip]]]

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        with SubstrateContext(JLCFlex2L()):
            cls.strips = [
                (
                    name,
                    variant,
                    FlexStrip(variant),
                    [FlexStrip(variant, segment) for segment in variant.segments],
                )
                for name, variant in VARIANTS
            ]

    def test_hops(self) -> None:
        print()
        for name, variant, flex, _ in self.strips:
            with self.subTest(variant=name):
                result = check_hops(flex)
                print(
                    f" [{name}] {result.hops} in-row hops x 2 traces at"
                    f" {variant.trace_width} mm: least clearance"
                    f" {result.least_clearance:.3f} mm (rule {variant.clearance}),"
                    f" trace copper within +/-{result.max_excursion:.3f} mm of the row"
                    f" (data band +/-{variant.data_band})"
                )
                self.assertEqual(
                    result.hops,
                    2 * variant.rows * (variant.columns - 1) - 2 * variant.rows,
                )
                self.assertGreaterEqual(
                    result.least_clearance, variant.clearance - TOLERANCE
                )
                self.assertLessEqual(
                    result.max_excursion, variant.data_band - variant.clearance
                )

    def test_channels(self) -> None:
        print()
        for name, variant, flex, _ in self.strips:
            with self.subTest(variant=name):
                print(
                    f" [{name}] pitch {variant.pitch:.4f} mm, strip"
                    f" {variant.length:.2f} x {variant.height:.2f} mm"
                )
                for c in flex.uturn_channels:
                    end = "A" if c.at_end_a else "B"
                    what = (
                        "U-turns + crossover vias"
                        if (not c.at_end_a and c.face == Side.Top)
                        else "U-turns"
                    )
                    print(
                        f"   end {end} {c.face.name:6s} channel {c.width:.3f} mm"
                        f" (needs {c.required:.3f}: {what})"
                    )
                    self.assertGreaterEqual(c.width, c.required - TOLERANCE)
                din = flex.din_channel
                assert din is not None
                print(
                    f"   DIN channel {din.width:.3f} mm (needs {din.required:.3f});"
                    f" tail at {variant.tail_offset} mm, GND riser in spine"
                    f" {flex.gnd_riser_width:.2f} mm, {len(flex.gnd_transition_vias)}"
                    " transition vias"
                )
                self.assertGreaterEqual(din.width, din.required - TOLERANCE)
                print(
                    "   unlanded LED power pads (router):",
                    ", ".join(
                        f"{u.site.face.name} c{u.site.col} r{u.site.row}"
                        f" {'VDD' if u.is_vdd else 'GND'}"
                        for u in flex.unlanded_pads
                    ),
                )

    def test_lanes_and_current(self) -> None:
        print()
        for name, variant, flex, _ in self.strips:
            with self.subTest(variant=name):
                widths = lane_widths(flex)
                vdd = sum(
                    w for w, lane in zip(widths, flex.lanes, strict=True) if lane.is_vdd
                )
                gnd = sum(
                    w
                    for w, lane in zip(widths, flex.lanes, strict=True)
                    if not lane.is_vdd
                )
                print(
                    f" [{name}] lane copper per layer, bottom to top: "
                    + ", ".join(
                        f"{'VDD' if lane.is_vdd else 'GND'} {w:.3f}"
                        for w, lane in zip(widths, flex.lanes, strict=True)
                    )
                    + f" mm; per net per layer VDD {vdd:.2f} / GND {gnd:.2f} mm"
                )
                self.assertTrue(flex.lanes[0].is_vdd)
                feed = widths[0]
                internal = ipc2221_current(feed, 2, IPC_K_INTERNAL)
                external = ipc2221_current(feed, 2, IPC_K_EXTERNAL)
                full = variant.leds * LED_FULL_WHITE
                idle = variant.leds * LED_IDLE
                cap = (internal - idle) / (full - idle)
                sheet = COPPER_RESISTIVITY / (COPPER_THICKNESS * 1e-3)
                resistance = sheet * variant.length / (2 * feed)
                print(
                    f"   bottleneck: VDD bottom-margin lane, {feed:.3f} mm x 2 layers,"
                    f" carries the whole load at end A. {TEMPERATURE_RISE:.0f} degC rise:"
                    f" {internal:.2f} A (IPC-2221 internal k, coverlaid flex),"
                    f" {external:.2f} A (external k)"
                )
                print(
                    f"   full white {full:.2f} A, idle {idle:.2f} A -> firmware cap"
                    f" {internal:.1f} A total = {100 * min(cap, 1.0):.0f} % of full white;"
                    f" lane end-to-end {1000 * resistance:.1f} mOhm,"
                    f" ~{0.9 * internal * resistance * 1000:.0f} mV drop at the cap"
                )
                self.assertGreater(internal, 1.0, "lane cannot carry 1 A")

    def test_boards_and_panels(self) -> None:
        print()
        for name, variant, _, boards in self.strips:
            with self.subTest(variant=name):
                self.assertEqual(variant.loop_columns % 3, 0)
                self.assertEqual(variant.leds, 480)
                for board in boards:
                    x0, y0, x1, y1 = board.outline.bounds
                    size = PanelSize.fit(x1 - x0, y1 - y0)
                    size.check()
                    print(
                        f" [{name}] board {x1 - x0:.2f} x {y1 - y0:.2f} mm,"
                        f" {len(board.strip.leds)} LEDs -> panel {size.width:.2f} x"
                        f" {size.height:.2f} mm, rails {size.rail_x:.2f} / {size.rail_y:.2f}"
                    )
                    self.assertLessEqual(board.board_length, MAX_ASSEMBLY_LENGTH + 1e-9)
                self.assertEqual(sum(len(b.strip.leds) for b in boards), 480)

    def test_mechanical_mirror(self) -> None:
        mech = load_mechanical_variants()
        for (name, variant), mv in zip(VARIANTS, mech.VARIANTS, strict=True):
            with self.subTest(variant=name):
                self.assertAlmostEqual(mv.pitch, variant.pitch, places=9)
                self.assertEqual(mv.columns, variant.columns)
                self.assertEqual(mv.rows, variant.rows)
                self.assertAlmostEqual(mv.tail_offset, variant.tail_offset, places=9)
                self.assertAlmostEqual(mv.tail_length, variant.tail_length, places=9)
                self.assertEqual(mv.joint_columns, variant.joint_columns)
                self.assertAlmostEqual(mv.splice_overlap, variant.splice_overlap)
                self.assertEqual(mv.lap_columns, variant.lap_columns)
                self.assertAlmostEqual(mv.length, variant.length, places=9)


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=2).result
    sys.exit(0 if result.wasSuccessful() else 1)
