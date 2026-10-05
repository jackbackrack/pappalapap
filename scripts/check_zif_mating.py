"""Pin-1 proof: the flex tail mates each controller board's ZIF finger k -> contact k.

Run:  python scripts/check_zif_mating.py      (prints the mating table, exits
      non-zero on any failure; also runs under ``python -m unittest``)

Boards checked (``BOARDS``): the flat interface board
(``pappalapap.designs.interface_board.InterfaceLayout``) and the column board
(``pappalapap.designs.column_board.ColumnLayout``). Each is built as designed
and its own placed ZIF and nets are used.

Why: the 16-contact pinout is asymmetric (1-7 VDD/VLED, 8 DRET, 9 DIN, 10-16
GND). A mirrored mating swaps 5 V and GND at up to 5 A.

Inputs, all read from the owning objects (no restated coordinates):

- Flex side, every tail (``TAILS``): segment A of the two-segment strip
  (``FlexStrip(TWO_SEGMENT, segment A)``, the circuit of ``FlexSegmentA``)
  and the one-board strip (``FlexStrip(ONE_SEGMENT)``, the circuit of
  ``FlexOneSegment``), from ``pappalapap.designs.flex_strip``. Each is built
  and its placed ``FpcTail16`` (``FlexStrip.tail``) is used as is: its placement
  (Side.Bottom, i.e. x-mirrored about the tail centreline) and each finger's
  pad, through ``flex_strip.pad_footprints``, give every finger's centre in the
  flex board's TOP-VIEW frame.
- ZIF side: ``XFCN_F1002B16`` orientation constants (``pin_x``,
  ``CABLE_STOP_Y``, ``CONTACT_LINE_Y``, ``INSERTION_DIRECTION``,
  ``CONTACT_SIDE``), in the connector's landpattern frame, top view of the
  interface board.
- Nets: each board's ``XiaoInterface`` (its ZIF contact ports and its
  VLED / DRET / DIN / GND nets) and the tail's own port groups.
- Board entry: each board's outline and its ZIF placement (the board
  layout's own objects).

The mating transform (flex top-view frame -> ZIF landpattern frame):

1. Which face touches the contacts. The fingers are on the flex's BOTTOM
   copper (the tail is placed on Side.Bottom); the ZIF is bottom-contact (its
   contacts touch the cable's lower face). So the flex goes in fingers-down,
   i.e. with its top face up. Looking down on the interface board we therefore
   see the flex's TOP face, which is exactly the view its design coordinates
   describe. Both frames are top views of upward-facing surfaces, so the map
   between them is a proper rigid motion (rotation + translation, determinant
   +1, NO mirror). (If the fingers were on the top copper, the flex would have
   to be turned over to face them down, and the map would gain a mirror.)
2. Rotation. The tail's free end leads into the connector: the free-end
   direction in the flex frame (from the flex body toward the cut end, i.e. the
   tail landpattern's -y carried through the tail's placement) must map onto
   the ZIF's INSERTION_DIRECTION (0, +1). The angle between the two is the
   rotation (180 degrees for this flex).
3. Translation. The tail's cut-end centre (the tail landpattern origin, carried
   through its placement) maps onto (0, CABLE_STOP_Y): centred in the slot and
   pushed home against the stop.

Assertions, for every finger: it lands within the contact-pitch tolerance of
exactly one ZIF contact and that contact's number equals the finger's own
number; the finger copper spans the ZIF contact line (so the contact really
touches it); and the ZIF contact is on the interface net that matches the
tail's net for that finger (VDD -> VLED, DRET, DIN, GND).

The finger-to-contact map is relative (tail frame -> ZIF frame), so it holds
for any ZIF placement; what does depend on the board is checked separately,
per board: the ZIF's cable-entry face sits on the board edge (within
``ENTRY_EDGE_TOLERANCE``), the cable arrives from outside the outline, and the
insertion direction in the board frame is the one the board was designed for
(flat board: +y, from the bottom edge; column board: -y, the flex dropping
straight down into the top edge).
"""

import math
import sys
import unittest
from dataclasses import dataclass

import shapely
import shapely.affinity
from jitx.events import EventContext
from jitx.landpattern import Pad
from jitx.layerindex import Side
from jitx.net import Net, Port
from jitx.placement import Placement
from jitx.substrate import SubstrateContext
from jitx.test import TestCase
from jitx.transform import Transform

from pappalapap.circuits.interface import XiaoInterface
from pappalapap.components.fpc_tail import FpcTail16
from pappalapap.components.xfcn_f1002b16 import XFCN_F1002B16
from pappalapap.designs.column_board import ColumnLayout
from pappalapap.designs.flex_strip import FlexStrip, pad_footprints
from pappalapap.designs.interface_board import InterfaceLayout, compose
from pappalapap.substrate import JLCFlex2L
from pappalapap.substrate_rigid import JLC2L16
from pappalapap.variants import ONE_SEGMENT, TWO_SEGMENT, StripVariant

LATERAL_TOLERANCE = 0.05
"""Finger-to-contact centre offset allowed (mm): the XFCN pitch tolerance."""
ENTRY_EDGE_TOLERANCE = 1.0
"""Largest allowed gap from the ZIF's cable-entry face to the board edge (mm)."""
OUTSIDE_STEP = 1.5
"""Step from the entry face against the insertion direction that must land
outside the board (mm): the cable arrives from beyond the edge."""


@dataclass(frozen=True)
class BoardCase:
    """One controller board to check."""

    name: str
    layout: type[InterfaceLayout] | type[ColumnLayout]
    insertion: tuple[float, float]
    """Designed insertion direction of the flex, board frame (unit vector)."""


BOARDS = [
    BoardCase("interface_board", InterfaceLayout, (0.0, 1.0)),
    BoardCase("column_board", ColumnLayout, (0.0, -1.0)),
]


@dataclass(frozen=True)
class TailCase:
    """One flex board that carries the tail."""

    name: str
    """Display name only."""
    variant: StripVariant
    segment: range | None
    """Column range of the board holding end A (None: the whole strip)."""


TAILS = [
    TailCase("two-segment A", TWO_SEGMENT, TWO_SEGMENT.segments[0]),
    TailCase("one-segment", ONE_SEGMENT, None),
]


@dataclass(frozen=True)
class FingerLanding:
    """Where one tail finger lands in the ZIF landpattern frame."""

    finger: int
    """Finger number, 1..16, from the tail landpattern."""
    contact: int
    """ZIF contact nearest the finger centre."""
    dx: float
    """Finger centre minus contact centre, along the contact row (mm)."""
    y_span: tuple[float, float]
    """Finger copper extent along the insertion axis (mm)."""
    flex_net: Net
    zif_port: Port


def angle_of(dx: float, dy: float) -> float:
    """Direction angle in degrees."""
    return math.degrees(math.atan2(dy, dx))


def mating_transform(tail_placement: Placement) -> Transform:
    """Flex top-view board frame -> ZIF landpattern frame (see module docstring)."""
    # Step 1: fingers down onto a bottom-contact ZIF means no mirror.
    assert tail_placement.side == Side.Bottom, "fingers must be on the flex bottom"
    assert XFCN_F1002B16.CONTACT_SIDE == "bottom"
    # Step 2: rotation taking the tail's free-end direction to the insertion
    # direction. Free end = tail landpattern -y (the body extends toward +y).
    origin = tail_placement * (0.0, 0.0)
    toward_free_end = tail_placement * (0.0, -1.0)
    free_dir = (toward_free_end[0] - origin[0], toward_free_end[1] - origin[1])
    ins = XFCN_F1002B16.INSERTION_DIRECTION
    rotation = angle_of(*ins) - angle_of(*free_dir)
    # Step 3: cut-end centre onto the cable stop, centred in the slot.
    return (
        Transform((0.0, XFCN_F1002B16.CABLE_STOP_Y))
        * Transform((0.0, 0.0), rotation)
        * Transform((-origin[0], -origin[1]))
    )


def tail_of(flex: FlexStrip) -> FpcTail16:
    """The flex's tail (segment A has one)."""
    assert flex.tail is not None, "this flex segment has no tail"
    return flex.tail


def tail_nets(flex: FlexStrip) -> list[tuple[Port, Net]]:
    """Each tail finger port with its flex net (VDD, DRET, DIN or GND)."""
    tail = tail_of(flex)
    return [
        *[(p, flex.vdd) for p in tail.VDD],
        (tail.DRET, flex.dret),
        (tail.DIN, flex.din),
        *[(p, flex.gnd) for p in tail.GND],
    ]


def finger_number(tail: FpcTail16, port: Port) -> int:
    """Landpattern pad number (= finger number) of the pad mapped to ``port``."""
    (mapping,) = tail.mappings
    pads = mapping[port]
    (pad,) = [pads] if isinstance(pads, Pad) else list(pads)
    (number,) = [n for n, p in tail.landpattern.p.items() if p is pad]
    return number


def landings(flex: FlexStrip, iface: XiaoInterface) -> list[FingerLanding]:
    """Land every tail finger on the ZIF."""
    tail = tail_of(flex)
    assert isinstance(tail.transform, Placement)
    mate = mating_transform(tail.transform)
    result = []
    for port, net in tail_nets(flex):
        (footprint,) = list(pad_footprints(tail, port))
        mated = shapely.affinity.affine_transform(footprint, affine(mate))
        cx = mated.centroid.x
        contact = min(
            range(1, XFCN_F1002B16.NUM_PINS + 1),
            key=lambda k: abs(cx - XFCN_F1002B16.pin_x(k)),
        )
        _, y0, _, y1 = mated.bounds
        result.append(
            FingerLanding(
                finger=finger_number(tail, port),
                contact=contact,
                dx=cx - XFCN_F1002B16.pin_x(contact),
                y_span=(y0, y1),
                flex_net=net,
                zif_port=iface.zif.P[contact - 1],
            )
        )
    return result


def affine(xf: Transform) -> list[float]:
    """Shapely affine coefficients [a, b, d, e, xoff, yoff] of a JITX transform."""
    o = xf * (0.0, 0.0)
    ex = xf * (1.0, 0.0)
    ey = xf * (0.0, 1.0)
    return [ex[0] - o[0], ey[0] - o[0], ex[1] - o[1], ey[1] - o[1], o[0], o[1]]


def on_net(port: Port, net: Net) -> bool:
    """Whether ``port`` was wired directly into ``net``."""
    return any(member is port for member in net.connected)


@dataclass(frozen=True)
class ZifEntry:
    """Where and how the flex enters a board's ZIF, in the board frame."""

    face_centre: tuple[float, float]
    insertion: tuple[float, float]


def zif_entry(layout: InterfaceLayout | ColumnLayout) -> ZifEntry:
    """The placed ZIF's entry-face centre and insertion direction."""
    zif = layout.iface.zif
    xf = compose(layout.iface.transform, zif.transform, zif.landpattern.transform)
    face = xf * (0.0, XFCN_F1002B16.ENTRY_FACE_Y)
    ix, iy = XFCN_F1002B16.INSERTION_DIRECTION
    tip = xf * (ix, XFCN_F1002B16.ENTRY_FACE_Y + iy)
    return ZifEntry(face, (tip[0] - face[0], tip[1] - face[1]))


class ZifMatingTest(TestCase):
    """Tail finger k lands on ZIF contact k, with matching nets, on every board."""

    flexes: list[tuple[TailCase, FlexStrip]]
    layouts: list[tuple[BoardCase, InterfaceLayout | ColumnLayout]]

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        with SubstrateContext(JLCFlex2L()):
            cls.flexes = [
                (tail, FlexStrip(tail.variant, tail.segment)) for tail in TAILS
            ]
        # EventContext: the jitxlib.parts passives register for the design's
        # Initialized event; outside a design they simply stay unresolved,
        # which this check never needs (it reads ports, nets and the
        # non-passive placements only).
        with SubstrateContext(JLC2L16()), EventContext():
            cls.layouts = [(case, case.layout()) for case in BOARDS]

    def expected_net(
        self, flex: FlexStrip, iface: XiaoInterface, landing: FingerLanding
    ) -> Net:
        """Interface net the ZIF contact must carry, given the tail's net."""
        if landing.flex_net is flex.vdd:
            return iface.VLED
        if landing.flex_net is flex.dret:
            return iface.DRET
        if landing.flex_net is flex.din:
            return iface.DIN
        assert landing.flex_net is flex.gnd
        return iface.GND

    def flex_label(self, flex: FlexStrip, landing: FingerLanding) -> str:
        """Display name of the finger's flex net (the flex nets are unnamed)."""
        if landing.flex_net is flex.vdd:
            return "VDD"
        if landing.flex_net is flex.dret:
            return "DRET"
        if landing.flex_net is flex.din:
            return "DIN"
        return "GND"

    def test_mating(self) -> None:
        for tail, flex in self.flexes:
            for case, layout in self.layouts:
                with self.subTest(tail=tail.name, board=case.name):
                    self.check_mating(tail, flex, case, layout.iface)

    def check_mating(
        self, tail: TailCase, flex: FlexStrip, case: BoardCase, iface: XiaoInterface
    ) -> None:
        found = landings(flex, iface)
        self.assertEqual(
            sorted(f.finger for f in found), list(range(1, FpcTail16.NUM_FINGERS + 1))
        )
        print()
        print(f" [{tail.name} tail -> {case.name}]")
        print(" finger  flex net  ->  contact   dx (mm)   y span (mm)    ZIF net")
        for f in sorted(found, key=lambda f: f.finger):
            print(
                f"   {f.finger:2d}    {self.flex_label(flex, f):5s}  ->    {f.contact:2d}"
                f"     {f.dx:+.3f}   {f.y_span[0]:+.2f}..{f.y_span[1]:+.2f}"
                f"   {self.expected_net(flex, iface, f).name}"
            )
        print(f" contact line y = {XFCN_F1002B16.CONTACT_LINE_Y:+.2f}")
        for f in found:
            with self.subTest(tail=tail.name, board=case.name, finger=f.finger):
                self.assertEqual(f.contact, f.finger, "finger on the wrong contact")
                self.assertLessEqual(abs(f.dx), LATERAL_TOLERANCE)
                y0, y1 = f.y_span
                self.assertTrue(
                    y0 < XFCN_F1002B16.CONTACT_LINE_Y < y1,
                    "finger does not cross the contact line",
                )
                self.assertTrue(
                    on_net(f.zif_port, self.expected_net(flex, iface, f)),
                    f"ZIF contact {f.contact} not on the matching net",
                )

    def test_board_entry(self) -> None:
        """The flex reaches each ZIF from outside its board, as designed."""
        for case, layout in self.layouts:
            with self.subTest(board=case.name):
                entry = zif_entry(layout)
                outline = layout.outline
                fx, fy = entry.face_centre
                ix, iy = entry.insertion
                gap = outline.boundary.distance(shapely.Point(fx, fy))
                outside = shapely.Point(fx - OUTSIDE_STEP * ix, fy - OUTSIDE_STEP * iy)
                print(
                    f" [{case.name}] entry face centre ({fx:+.2f}, {fy:+.2f}),"
                    f" insertion ({ix:+.2f}, {iy:+.2f}), {gap:.2f} mm inside the edge"
                )
                self.assertAlmostEqual(ix, case.insertion[0], places=6)
                self.assertAlmostEqual(iy, case.insertion[1], places=6)
                self.assertTrue(outline.contains(shapely.Point(fx, fy)))
                self.assertLessEqual(gap, ENTRY_EDGE_TOLERANCE)
                self.assertFalse(
                    outline.contains(outside),
                    "cable would arrive from inside the board",
                )

    def test_mirror_would_be_caught(self) -> None:
        """Sanity: a mirrored mating (fingers facing up) puts finger 1 on 16."""
        for case, flex in self.flexes:
            with self.subTest(tail=case.name):
                tail = tail_of(flex)
                assert isinstance(tail.transform, Placement)
                mirror = Transform((0.0, 0.0), 0.0, (-1.0, 1.0)) * mating_transform(
                    tail.transform
                )
                (footprint,) = list(pad_footprints(tail, tail.VDD[0]))
                mated = shapely.affinity.affine_transform(footprint, affine(mirror))
                self.assertAlmostEqual(
                    mated.centroid.x, XFCN_F1002B16.pin_x(16), places=6
                )


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=2).result
    sys.exit(0 if result.wasSuccessful() else 1)
