"""Seeed XIAO ESP32S3 (Sense) socket: two HCTL PM254-1-07-Z-8.5 1x7 female headers.

What this component is: the two 2.54 mm 1x7 female headers (HCTL
PM254-1-07-Z-8.5, LCSC C2897370, **two per board**) that a Seeed Studio XIAO
ESP32S3 or XIAO ESP32S3 Sense plugs into, modelled as ONE component with 14
through-hole pads so the circuit can wire the XIAO's pins by their silkscreen
names. The XIAO module itself is bought separately from Seeed and is not
soldered to this board; it is not on the board BOM. The ``mpn`` is the socket's.
BOM note: one instance of this class needs **qty 2** of PM254-1-07-Z-8.5.

Sources:

- HCTL drawing "2.54 单排 排母 直针 塑高8.5", part no. PM254-1-N-Z-8.5-XX
  (L11.7), rev A, one sheet (docs/datasheets/HCTL_PM254-1-07-Z-8.5_C2897370.pdf):
  "Recommended P.C.B Layout (Top Side)": pitch 2.54, hole dia 1.02
  (PCB tolerance +/-0.05); body 2.54 x N + 0.40 +/-0.30 long (18.18 for 7P),
  2.50 +/-0.15 wide, 8.5 +/-0.15 tall above the board; pin 0.64 x 0.40,
  3.2 +/-0.25 below the body. "SPECIFICATIONS": rated current 3.0 A.
- Seeed wiki, "Getting Started with Seeed Studio XIAO ESP32S3 (Sense)",
  https://wiki.seeedstudio.com/xiao_esp32s3_getting_started/ (read
  2026-10-03): pin list table (XIAO pin -> GPIO below), "Dimensions:
  21 x 17.8mm", Sense camera / microphone / SD-card GPIO lists, and the front
  pinout graphic XIAO_ESP32-S3_front_pinout.png (left column top to bottom
  D0..D6 next to the USB-C end first; right column VBUS, GND, 3.3V-OUT,
  D10, D9, D8, D7).
- Seeed official KiCad library, New_XIAO_Series_Footprints.zip ->
  XIAO-ESP32-S3-DIP.kicad_mod: 14 plated holes, pads 1-7 at y = -7.62 and
  8-14 at y = +7.62 (KiCad y-down), x from +7.62 (pads 1 and 14) to -7.62
  (pads 7 and 8) at 2.54 pitch: **row spacing 15.24 mm**; Fab/courtyard
  rectangle x -10.425..10.55, y -8.9..8.9 (the 21 x 17.8 board); the USB-C
  receptacle silkscreen reaches x = 12.05 between y = +/-4.5. Seeed's
  XIAO_Series_SCH_Symbols, symbol XIAO-ESP32-S3-SMD: pins 1-11 D0..D10,
  12 3V3_OUT, 13 GND, 14 VBUS.

Pin map (XIAO silkscreen -> port -> ESP32-S3 GPIO -> pad):

    D0  D[0]  GPIO1   1      VBUS (5V)  VBUS  -       14
    D1  D[1]  GPIO2   2      GND        GND   -       13
    D2  D[2]  GPIO3   3      3V3        V3V3  -       12
    D3  D[3]  GPIO4   4      D10        D[10] GPIO9   11
    D4  D[4]  GPIO5   5      D9         D[9]  GPIO8   10
    D5  D[5]  GPIO6   6      D8         D[8]  GPIO7    9
    D6  D[6]  GPIO43  7      D7         D[7]  GPIO44   8

(The "5V" pin is VBUS, tied to USB VBUS on the XIAO; "3V3" is the XIAO's
3.3 V regulator output.)

XIAO ESP32S3 Sense expansion-board usage (Seeed wiki + expansion-board
schematic XIAO_ESP32S3_ExpBoard_v1.0_SCH.pdf, sheet "SD card / MIC"):

- Camera (DVP): GPIO10-18, 38, 39, 40, 47, 48 -- none on the 14 header pins.
- Digital PDM microphone: CLK GPIO42, DATA GPIO41 -- the D11/D12 pads on the
  back, not on the header.
- microSD (SPI): SCK D8/GPIO7, MISO D9/GPIO8, MOSI D10/GPIO9; CS = GPIO21
  through R12 (0R) on ExpBoard v1.0, with D2/GPIO3 as the DNP alternative
  (R11); the wiki pinout graphic labels D2 "SD_CS".
- GPIO3 (D2) is also an ESP32-S3 strapping pin; D6/D7 are UART0 TX/RX
  (boot-ROM log on GPIO43).

Free on a Sense with the SD card fitted: D0, D1, D3, D4, D5 (D4/D5 are the
default I2C pair), plus D6/D7 if the UART console is not needed.
Recommendation for the interface board: **DIN on D0 (GPIO1)**, **DRET on D1
(GPIO2, ADC1_CH1)**.

Coordinate frame (top view, y up): origin at the centre of the 2 x 7 pin
field; the XIAO's USB-C end points to +x. Pads 1..7 (D0..D6) run along
y = +7.62 from x = +7.62 (pad 1, square) to x = -7.62; pads 8..14
(D7, D8, D9, D10, 3V3, GND, VBUS) run along y = -7.62 from x = -7.62 to
x = +7.62. This is Seeed's DIP footprint with KiCad's y axis flipped.

Design choices (not from a drawing): pad copper 1.57 mm from
``jitxlib`` ``compute_pad_diameter`` (IPC-2222 rule, defaults) on the 1.02 mm
hole; pad 1 square; courtyard = XIAO outline plus the USB-C receptacle
overhang, 0.25 mm excess. The USB-C cable plug needs further clearance
beyond +x that no courtyard here captures.
"""

from typing import ClassVar

from jitx.circuit import Circuit
from jitx.component import Component
from jitx.feature import Courtyard, Silkscreen
from jitx.landpattern import Landpattern, PadMapping
from jitx.net import Port
from jitx.sample import SampleDesign
from jitx.shapes.composites import rectangle
from jitx.shapes.primitive import Circle, Polyline
from jitxlib.jlcpcb import LCSCPart
from jitxlib.landpatterns.pads import THPad, compute_pad_diameter
from jitxlib.symbols.box import BoxSymbol, Column, PinGroup, Row

# --- HCTL PM254 drawing ------------------------------------------------------
PITCH = 2.54
HOLE = 1.02  # "Recommended P.C.B Layout", dia 1.02
PINS_PER_ROW = 7
HEADER_BODY_WIDTH = 2.50  # 2.50 +/- 0.15
HEADER_BODY_LENGTH = PITCH * PINS_PER_ROW + 0.40  # 18.18
HEADER_HEIGHT = 8.5  # 8.5 +/- 0.15, plastic height above the board

# --- Seeed XIAO-ESP32-S3-DIP.kicad_mod ---------------------------------------
ROW_SPACING = 15.24  # pads 1-7 at y = -7.62, 8-14 at y = +7.62
XIAO_MIN_X = -10.425  # Fab / courtyard rectangle
XIAO_MAX_X = 10.55
XIAO_HALF_Y = 8.9  # 17.8 mm board
USB_MAX_X = 12.051  # USB-C receptacle silkscreen extent
USB_HALF_Y = 4.5

# --- Drawing rules -----------------------------------------------------------
SILK_WIDTH = 0.12
COURTYARD_EXCESS = 0.25
PIN1_DOT_RADIUS = 0.25

ROW_Y = ROW_SPACING / 2  # 7.62
FIRST_X = (PINS_PER_ROW - 1) / 2 * PITCH  # 7.62


def pad_position(n: int) -> tuple[float, float]:
    """Centre of pad ``n`` (1..14) in the landpattern frame (see docstring)."""
    if 1 <= n <= PINS_PER_ROW:
        return FIRST_X - (n - 1) * PITCH, ROW_Y
    if PINS_PER_ROW < n <= 2 * PINS_PER_ROW:
        return -FIRST_X + (n - PINS_PER_ROW - 1) * PITCH, -ROW_Y
    raise ValueError(f"XIAO pad number {n} not in 1..14")


class XiaoSocketLandpattern(Landpattern):
    """Two 1x7 2.54 mm socket rows, 15.24 mm apart; XIAO outline on silkscreen."""

    def __init__(self) -> None:
        copper = compute_pad_diameter(HOLE)
        hole = Circle(diameter=HOLE)
        self.p = {
            n: THPad(
                rectangle(copper, copper) if n == 1 else Circle(diameter=copper),
                hole,
            ).at(*pad_position(n))
            for n in range(1, 2 * PINS_PER_ROW + 1)
        }

        # XIAO board outline plus the USB-C receptacle at +x.
        half = SILK_WIDTH / 2
        x0, x1 = XIAO_MIN_X - half, XIAO_MAX_X + half
        y1 = XIAO_HALF_Y + half
        self.xiao_outline = Silkscreen(
            Polyline(SILK_WIDTH, [(x0, -y1), (x1, -y1), (x1, y1), (x0, y1), (x0, -y1)])
        )
        self.usb_outline = Silkscreen(
            Polyline(
                SILK_WIDTH,
                [
                    (x1, USB_HALF_Y),
                    (USB_MAX_X, USB_HALF_Y),
                    (USB_MAX_X, -USB_HALF_Y),
                    (x1, -USB_HALF_Y),
                ],
            )
        )
        # Pin-1 dot inside the outline, between pad 1 and the USB end.
        x_pin1, y_pin1 = pad_position(1)
        self.pin1_marker = Silkscreen(
            Circle(radius=PIN1_DOT_RADIUS).at(
                (x_pin1 + copper / 2 + XIAO_MAX_X) / 2, y_pin1
            )
        )

        cx0 = XIAO_MIN_X - COURTYARD_EXCESS
        cx1 = USB_MAX_X + COURTYARD_EXCESS
        cy = XIAO_HALF_Y + COURTYARD_EXCESS
        self.courtyard = Courtyard(
            rectangle(cx1 - cx0, 2 * cy).at((cx0 + cx1) / 2, 0.0)
        )


class XiaoESP32S3Socket(Component):
    """Socket pair for a Seeed XIAO ESP32S3 (Sense); ports named by XIAO pin.

    ``D[k]`` is XIAO pin Dk (k = 0..10); ``VBUS`` is the "5V" pin, ``V3V3``
    the "3V3" pin. Geometry constants are class attributes for the board
    layout task.
    """

    manufacturer = "HCTL"
    mpn = "PM254-1-07-Z-8.5"
    lcsc = LCSCPart("C2897370")  # read by the JLCPCB exporter (jitxlib.jlcpcb)
    socket_qty: ClassVar[int] = 2
    module: ClassVar[str] = (
        "Seeed Studio XIAO ESP32S3 Sense (bought separately, plugs in)"
    )
    datasheet = (
        "https://datasheet.lcsc.com/datasheet/pdf/"
        "87e2b5b113f4df247d2b8d5758217346.pdf?productCode=C2897370"
    )
    reference_designator_prefix = "J"

    PITCH: ClassVar[float] = PITCH
    ROW_SPACING: ClassVar[float] = ROW_SPACING
    HOLE: ClassVar[float] = HOLE
    HEADER_HEIGHT: ClassVar[float] = HEADER_HEIGHT
    USB_DIRECTION: ClassVar[str] = "+x"

    # Class-scope port arrays are the JITX structural idiom (each instance gets
    # its own ports), not shared mutable state; hence the RUF012 waiver.
    D = [Port() for _ in range(11)]  # noqa: RUF012
    VBUS = Port()
    GND = Port()
    V3V3 = Port()

    landpattern = XiaoSocketLandpattern()
    symbol = BoxSymbol(
        rows=Row(left=PinGroup(*D[:7]), right=PinGroup(*D[7:])),
        columns=Column(up=PinGroup(VBUS, V3V3), down=PinGroup(GND)),
    )

    def __init__(self) -> None:
        lp = self.landpattern
        # Pads 1-11 are D0-D10 in order; 12 3V3, 13 GND, 14 VBUS (Seeed symbol).
        mapping = {port: [lp.p[k + 1]] for k, port in enumerate(self.D)}
        mapping[self.V3V3] = [lp.p[12]]
        mapping[self.GND] = [lp.p[13]]
        mapping[self.VBUS] = [lp.p[14]]
        self.mappings = [PadMapping(mapping)]


class XiaoSocketHarness(Circuit):
    """One socket pair, unconnected."""

    xiao = XiaoESP32S3Socket()


class TestDesign(SampleDesign):
    """Build harness: ``jitx build pappalapap.components.xiao_esp32s3.TestDesign``."""

    circuit = XiaoSocketHarness()
