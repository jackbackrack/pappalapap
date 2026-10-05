"""XIAO-to-flex interface circuit, shared by both controller boards (PLAN task ib-cir).

Bridges a Seeed XIAO ESP32S3 (Sense) and the flex LED strip's 16-contact tail.
One block holds the boards' whole electrical content. Two board designs use
it:

- ``pappalapap.designs.interface_board.InterfaceBoard`` (flat board in the
  base): XIAO in two female sockets (``XiaoESP32S3Socket``), 5 V on a KF301
  screw terminal.
- ``pappalapap.designs.column_board.ColumnBoard`` (narrow vertical board in
  the sculpture's column): XIAO soldered on its castellations
  (``XiaoESP32S3SMD``), 5 V on two solder-in wire pads (``WirePads``).

The circuit takes the XIAO part, the power-input part and an
``InterfacePlacement`` (where each part goes, in the circuit frame) as
arguments; the placement is the board design's data and lives there. The
designs add the outline, pours, vias, silkscreen and design rules.

Power path (ARCHITECTURE.md "Power Tree"; PLAN.md "Board 2 (revised)"):

    input + (+5V IN) -> VIN -> 6.3 A fuse -> VFUSE -> AO4407A D ... S -> VLED
    input - -> GND

- Reverse-polarity protection: high-side P-FET. D on the fuse output, S on the
  protected rail VLED, G to GND through 10 kOhm. With correct polarity the body
  diode conducts first, S rises to ~5 V, VGS = -5 V and the channel turns on
  (RDS(on) < 13 mOhm at -10 V, VGS(th) -1.7..-3 V). Reversed, G is at +5 V
  relative to D/S, the channel stays off and the body diode blocks. The input
  is 5 V nominal, so |VGS| <= 5.5 V stays far inside the AO4407A's +/-25 V
  rating (datasheet "Absolute Maximum Ratings"); no gate zener is needed.
- On VLED: SMBJ5.0A TVS (K to VLED, A to GND), bulk storage (``BulkCan`` or
  ``MlccBank``, the board's choice, see below), and a 10 uF + 100 nF ceramic
  pair at the ZIF's VLED contacts.
- XIAO supply: VLED -> SS54 Schottky (A at VLED, K at the XIAO "5V"/VBUS pin),
  so a USB cable on the XIAO cannot back-feed VLED (and the LED supply feeds
  the XIAO when no USB is attached).

Bulk storage on VLED (``XiaoInterface``'s ``bulk`` argument):

- ``BulkCan``: one 1000 uF 16 V radial electrolytic (``CX1000uF16V``,
  D10 x 13, 14.5 mm tall max). The flat ``InterfaceBoard`` keeps it.
- ``MlccBank`` (column board, user decision 2026-10-05): ``count`` (4) x
  100 uF 6.3 V X5R 1206 MLCCs (``BULK_MLCC``), resolved through the project
  parts chain (JLCPCBParts, basic library). On 2026-10-05 it resolved to
  Samsung CL31A107MQHNNNE, LCSC C15008, JLCPCB basic, ~1.3-1.9 M in stock;
  thickness code Q = 1.6 +/- 0.2 mm, so <= 1.8 mm tall. Nominal 400 uF, but
  a 6.3 V X5R part on the 5 V rail loses most of it to DC bias: about
  25-30 uF effective each, so ~100-120 uF effective for the bank, at a few
  milliohm ESR each (vs ~100 mOhm for the can). That is enough: VLED comes
  from a regulated supply over short 18 AWG wire, the WS2816C's PWM edges
  want low ESR/ESL near the ZIF more than bulk microfarads, and the 10 uF at
  the ZIF still sits next to the contacts. The 6.3 V rating covers the
  SMBJ5.0A-clamped rail in normal use (5.0 V standoff); a surge the TVS
  clamps above 6.3 V is brief.

ZIF pinout (approved 2026-10-03, same as ``FpcTail16``): contacts 1-7 VLED,
8 DRET, 9 DIN, 10-16 GND (``ZIF_PINOUT``); the fixing tabs (MNT) to GND.
``scripts/check_zif_mating.py`` proves, from the tail as placed in the flex
design, that tail finger k lands on ZIF contact k with the same net, on
both boards.

Data: XIAO D0 (GPIO1) -> 74AHCT1G125 A (10 kOhm pull-down, so the buffer
drives LOW while the ESP32 boots and its pin floats) -> Y -> 33 Ohm -> DIN.
OE_n tied to GND, VCC = VLED with 100 nF.

DRET: ZIF contact 8 -> 10 kOhm -> XIAO D1 (GPIO2), 20 kOhm from D1 to GND:
5 V x 20 / 30 = 3.33 V at the GPIO.

Passives are ``jitxlib.parts`` queries (value only here, except the
self-contained ``BULK_MLCC``); the designs set the JLC basic / 0603 defaults
and the project chain (``pyproject.toml`` ``[tool.jitx.parts]``, provider
``jitxlib.jlcpcb.parts.JLCPCBParts``) resolves them and attaches each part's
LCSC number.
"""

from dataclasses import dataclass
from typing import assert_never

from jitx.board import Board
from jitx.circuit import Circuit
from jitx.component import Component
from jitx.constraints import Tag
from jitx.design import Design
from jitx.net import Net, Port, ShortTrace
from jitx.shapes.composites import rectangle
from jitx.units import V, kohm, nF, ohm, uF
from jitxlib.parts import AtLeast, Capacitor, CapacitorQuery, Resistor, ResistorQuery

from ..components.aos_ao4407a import AO4407A
from ..components.cx_1000uf16v import CX1000uF16V
from ..components.diodes_74ahct1g125 import AHCT1G125
from ..components.kefa_kf301_2p import KF301_2P
from ..components.littelfuse_0451_6a3 import Fuse451_6A3
from ..components.littelfuse_smbj5v0a import SMBJ5V0A
from ..components.mdd_ss54 import SS54
from ..components.wire_pads import WirePads
from ..components.xfcn_f1002b16 import XFCN_F1002B16
from ..components.xiao_esp32s3 import XiaoESP32S3Socket
from ..components.xiao_esp32s3_smd import XiaoESP32S3SMD
from ..substrate_rigid import JLC2L16
from .led_strip import GroundTag, PowerTag

JLC_BASIC_RESISTOR = ResistorQuery(case="0603").update(library="basic")
"""Design-level resistor default: 0603 from the JLCPCB basic library (the
``library`` filter served by jitxlib.jlcpcb's JLCPCBParts provider)."""

BULK_MLCC = CapacitorQuery(
    capacitance=100 * uF,
    case="1206",
    rated_voltage_dc=AtLeast(6.3 * V),
    temperature_coefficient_code=("X5R", "X7R"),
).update(library="basic")
"""One capacitor of the ``MlccBank``: 100 uF >= 6.3 V X5R/X7R 1206, JLCPCB
basic (resolved 2026-10-05 to CL31A107MQHNNNE, LCSC C15008)."""

JLC_BASIC_CAPACITOR = CapacitorQuery(
    case="0603", temperature_coefficient_code=("X7R", "X5R")
).update(library="basic")
"""Design-level capacitor default: 0603 X7R/X5R ceramic, JLCPCB basic library."""


@dataclass(frozen=True)
class ZifPinout:
    """Contact numbers (1-based) of each signal on the 16-contact flex connector."""

    vled: tuple[int, ...]
    dret: int
    din: int
    gnd: tuple[int, ...]

    def contacts(self) -> list[int]:
        """Every contact, in the order vled, dret, din, gnd."""
        return [*self.vled, self.dret, self.din, *self.gnd]


ZIF_PINOUT = ZifPinout(vled=tuple(range(1, 8)), dret=8, din=9, gnd=tuple(range(10, 17)))
"""Approved 2026-10-03 (ARCHITECTURE.md "Connector"); identical to the
``FpcTail16`` port order (VDD x7, DRET, DIN, GND x7). The tail cannot be read
here (its port lists are class templates), so ``scripts/check_zif_mating.py``
cross-checks this against the placed tail, finger by finger."""

assert sorted(ZIF_PINOUT.contacts()) == list(range(1, XFCN_F1002B16.NUM_PINS + 1))


@dataclass(frozen=True)
class BulkCan:
    """Bulk storage: one 1000 uF 16 V radial can (``CX1000uF16V``)."""

    count = 1


@dataclass(frozen=True)
class MlccBank:
    """Bulk storage: ``count`` x ``BULK_MLCC`` (100 uF 1206) in parallel."""

    count: int = 4


BulkStorage = BulkCan | MlccBank
"""VLED bulk capacitance choice; see the module docstring."""


@dataclass(frozen=True)
class At:
    """One part's placement in the circuit frame (mm, degrees)."""

    x: float
    y: float
    rotate: float = 0.0


@dataclass(frozen=True)
class InterfacePlacement:
    """Where every part of ``XiaoInterface`` goes, in the circuit frame.

    Built by each board design from its own geometry; a part left at
    ``None`` floats (``InterfacePlacement()`` leaves every part floating, for
    the circuit build harness).
    """

    power_input: At | None = None
    fuse: At | None = None
    fet: At | None = None
    gate_r: At | None = None
    tvs: At | None = None
    bulk: tuple[At | None, ...] = ()
    """One entry per bulk capacitor, in ``XiaoInterface.bulk`` order (empty:
    all floating)."""
    schottky: At | None = None
    xiao: At | None = None
    zif: At | None = None
    buffer: At | None = None
    buffer_c: At | None = None
    pulldown: At | None = None
    din_r: At | None = None
    zif_c10u: At | None = None
    zif_c100n: At | None = None
    dret_r: At | None = None
    dret_div: At | None = None


def placed[ComponentT: Component](component: ComponentT, at: At | None) -> ComponentT:
    """``component`` placed at ``at`` (left floating when ``at`` is None)."""
    if at is None:
        return component
    return component.at(at.x, at.y, rotate=at.rotate)


XiaoPart = type[XiaoESP32S3Socket] | type[XiaoESP32S3SMD]
"""The XIAO as plugged into sockets, or soldered on its castellations."""
PowerInputPart = type[KF301_2P] | type[WirePads]
"""The 5 V input: screw terminal, or solder-in wire pads."""


class XiaoSupplyTag(Tag):
    """XIAO 5 V feed (Schottky cathode to the XIAO "5V" pin), ~0.5 A peak."""


class XiaoInterface(Circuit):
    """XIAO-to-flex interface: power path, DIN buffer, DRET divider.

    Ports expose the four power nets for the top level's pours and symbols.
    """

    vin = Port()
    """+5 V from the power input, before the fuse."""
    vfuse = Port()
    """Fuse output, P-FET drain."""
    vled = Port()
    """Protected LED rail, P-FET source; ZIF contacts 1-7."""
    gnd = Port()

    def __init__(
        self,
        xiao: XiaoPart,
        power_input: PowerInputPart,
        bulk: BulkStorage,
        placement: InterfacePlacement,
    ) -> None:
        at = placement
        bulk_at = at.bulk or (None,) * bulk.count
        assert len(bulk_at) == bulk.count, "one bulk placement per capacitor"
        # --- Parts and placement (orientation notes live with each design) ----
        self.power_in = placed(power_input(), at.power_input)
        self.fuse = placed(Fuse451_6A3(), at.fuse)
        self.fet = placed(AO4407A(), at.fet)
        self.tvs = placed(SMBJ5V0A(), at.tvs)
        # Bulk storage: a structural list, VLED on each part's first terminal.
        self.bulk: list[CX1000uF16V] | list[Capacitor]
        match bulk:
            case BulkCan():
                self.bulk = [placed(CX1000uF16V(), a) for a in bulk_at]
            case MlccBank():
                self.bulk = [placed(Capacitor(BULK_MLCC), a) for a in bulk_at]
            case _:
                assert_never(bulk)
        self.schottky = placed(SS54(), at.schottky)
        self.xiao = placed(xiao(), at.xiao)
        self.zif = placed(XFCN_F1002B16(), at.zif)
        self.buffer = placed(AHCT1G125(), at.buffer)

        self.r_gate = placed(Resistor(resistance=10 * kohm), at.gate_r)
        self.r_pulldown = placed(Resistor(resistance=10 * kohm), at.pulldown)
        self.r_din = placed(Resistor(resistance=33 * ohm), at.din_r)
        self.r_dret = placed(Resistor(resistance=10 * kohm), at.dret_r)
        self.r_dret_div = placed(Resistor(resistance=20 * kohm), at.dret_div)
        self.c_buffer = placed(Capacitor(capacitance=100 * nF), at.buffer_c)
        self.c_zif_bulk = placed(
            Capacitor(capacitance=10 * uF, rated_voltage_dc=AtLeast(10 * V)),
            at.zif_c10u,
        )
        self.c_zif_hf = placed(Capacitor(capacitance=100 * nF), at.zif_c100n)

        # --- Nets -------------------------------------------------------------
        self.VIN = Net([self.vin, self.input_plus(), self.fuse.p1], name="VIN")
        self.VFUSE = Net([self.vfuse, self.fuse.p2, self.fet.D], name="VFUSE")
        self.VLED = Net(
            [
                self.vled,
                self.fet.S,
                self.tvs.K,
                *self.bulk_vled(),
                self.schottky.A,
                self.buffer.VCC,
                *self.zif_vled(),
            ],
            name="VLED",
        )
        self.GND = Net(
            [
                self.gnd,
                self.input_minus(),
                self.tvs.A,
                *self.bulk_gnd(),
                self.xiao.GND,
                self.buffer.GND,
                self.buffer.OE_n,
                self.r_gate.p2,
                self.r_pulldown.p2,
                self.r_dret_div.p2,
                *self.zif_gnd(),
                self.zif.MNT,
            ],
            name="GND",
        )
        self.GATE = Net([self.fet.G, self.r_gate.p1], name="FET_GATE")
        self.XIAO_5V = Net([self.schottky.K, self.xiao.VBUS], name="XIAO_5V")

        # DIN: XIAO D0 -> buffer A (pull-down) ; Y -> 33 Ohm -> ZIF contact 9.
        self.DIN_3V3 = Net(
            [self.xiao.D[0], self.buffer.A, self.r_pulldown.p1], name="DIN_3V3"
        )
        self.DIN_5V = Net([self.buffer.Y, self.r_din.p1], name="DIN_5V")
        self.DIN = Net([self.r_din.p2, self.zif_din()], name="DIN")
        # DRET: ZIF contact 8 -> 10 k -> XIAO D1, 20 k to GND at D1.
        self.DRET = Net([self.zif_dret(), self.r_dret.p1], name="DRET")
        self.DRET_3V3 = Net(
            [self.r_dret.p2, self.xiao.D[1], self.r_dret_div.p1], name="DRET_3V3"
        )

        # Decoupling: each cap's VLED end gets a short trace to the pin it
        # serves; the GND ends join GND (pour + via).
        self.decoupling = [
            ShortTrace(self.c_buffer.p1, self.buffer.VCC),
            ShortTrace(self.c_zif_bulk.p1, self.zif_vled()[0]),
            ShortTrace(self.c_zif_hf.p1, self.zif_vled()[-1]),
        ]
        self.GND += self.c_buffer.p2
        self.GND += self.c_zif_bulk.p2
        self.GND += self.c_zif_hf.p2

        PowerTag().assign(self.VIN, self.VFUSE, self.VLED)
        GroundTag().assign(self.GND)
        XiaoSupplyTag().assign(self.XIAO_5V)

    # --- Port groups -------------------------------------------------------------
    # Methods, not attributes or properties: the structural walk reads both,
    # and a port reached twice gets a second parent. Numbers are ZIF_PINOUT's.

    def input_plus(self) -> Port:
        """The power input's +5 V terminal (KF301 pin 1 / wire pad "+5V")."""
        if isinstance(self.power_in, KF301_2P):
            return self.power_in.P1
        return self.power_in.VIN

    def input_minus(self) -> Port:
        """The power input's GND terminal (KF301 pin 2 / wire pad "GND")."""
        if isinstance(self.power_in, KF301_2P):
            return self.power_in.P2
        return self.power_in.GND

    def bulk_vled(self) -> list[Port]:
        """Each bulk capacitor's VLED terminal (can +, MLCC p1)."""
        return [c.pos if isinstance(c, CX1000uF16V) else c.p1 for c in self.bulk]

    def bulk_gnd(self) -> list[Port]:
        """Each bulk capacitor's GND terminal (can -, MLCC p2)."""
        return [c.neg if isinstance(c, CX1000uF16V) else c.p2 for c in self.bulk]

    def zif_vled(self) -> list[Port]:
        """ZIF contacts 1-7."""
        return [self.zif.P[k - 1] for k in ZIF_PINOUT.vled]

    def zif_dret(self) -> Port:
        """ZIF contact 8."""
        return self.zif.P[ZIF_PINOUT.dret - 1]

    def zif_din(self) -> Port:
        """ZIF contact 9."""
        return self.zif.P[ZIF_PINOUT.din - 1]

    def zif_gnd(self) -> list[Port]:
        """ZIF contacts 10-16."""
        return [self.zif.P[k - 1] for k in ZIF_PINOUT.gnd]


TEST_BOARD_SIZE = 60.0
"""Side of the square bare board in the circuit build harness (mm)."""


class InterfaceTestBoard(Board):
    """Bare board square for the circuit harness."""

    shape = rectangle(TEST_BOARD_SIZE, TEST_BOARD_SIZE)


class TestDesign(Design):
    """Circuit build harness: ``jitx build pappalapap.circuits.interface.TestDesign``.

        Bare square, parts floating, both XIAO / input variants' electrical
        content is the same; this builds the column board's (SMD XIAO, wire pads,
    MLCC bank).
        No pours or rules (those are the board designs' job).
    """

    resistor_defaults = JLC_BASIC_RESISTOR
    capacitor_defaults = JLC_BASIC_CAPACITOR

    def __init__(self) -> None:
        self.substrate = JLC2L16()
        self.circuit = XiaoInterface(
            XiaoESP32S3SMD, WirePads, MlccBank(), InterfacePlacement()
        )
        self.board = InterfaceTestBoard()
