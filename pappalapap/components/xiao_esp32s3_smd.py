"""Seeed Studio XIAO ESP32S3 Sense, soldered flat on its 14 castellated edge pads (SMD).

What this component is: the XIAO ESP32S3 Sense module itself (Seeed SKU
113991115), reflowed or hand-soldered directly to the carrier board through
the 14 castellated half-holes along its two long edges. No sockets. The
camera module is NOT fitted (user decision 2026-10-03); the Sense expansion
board (microphone + microSD) stays plugged onto the XIAO's B2B connector.
Same port names as the socket version (``xiao_esp32s3.XiaoESP32S3Socket``),
so the interface circuit takes either.

The module is bought from Seeed (not an LCSC/JLC part): BOM line "consigned /
hand-soldered", qty 1.

Sources:

- Seeed official KiCad library, New_XIAO_Series_Footprints.zip
  (https://files.seeedstudio.com/wiki/XIAO-KiCad-Library/New_XIAO_Series_Footprints.zip,
  read 2026-10-03) -> ``XIAO-ESP32-S3-SMD.kicad_mod`` (KiCad 9, copy in
  docs/datasheets/Seeed_XIAO-ESP32-S3-SMD.kicad_mod). Pads (KiCad frame, mm,
  y down):

  - 1-7: roundrect 2.75 x 2.00, rratio 0.25, at x = 0.835, y = -18.12,
    -15.58, ..., -2.88 (2.54 pitch); 8-14: same at x = 17.00, y = -2.88 ...
    -18.12. So the two castellated rows are **16.165 mm apart** (centre to
    centre) and each pad reaches 0.54 mm beyond the module edge.
  - 15-22: circle 1.7 at x 7.62 / 10.16, y -19.132 / -16.592 / -14.052 /
    -11.512; 23, 24: roundrect 2.5 x 1.1 at (4.445, -10.882), (4.445,
    -12.787); 25: roundrect 2.75 x 2.5 at (10.01, -8.5). These are the
    module's **underside** pads (Seeed symbol XIAO-ESP32-S3-SMD: 15 MTDI,
    16 MTDO, 17 EN, 18 GND, 19 MTMS, 20 MTCK, 21 USB_DN, 22 USB_DP,
    23 VBAT, 24 GND, 25 PAD).
  - F.Fab / F.CrtYd rectangle x -0.005..17.779, y -21.022..-0.071 (the
    21 x 17.8 module); F.SilkS USB-C receptacle outline to y = -22.547
    between x = 4.395 and 13.394.
- Seeed symbol library XIAO_Series_SCH_Symbols.zip, symbol
  XIAO-ESP32-S3-SMD: pins 1-11 D0..D10, 12 3V3_OUT, 13 GND, 14 VBUS (and
  the underside pads above).
- Seeed wiki "Getting Started with Seeed Studio XIAO ESP32S3 (Sense)",
  https://wiki.seeedstudio.com/xiao_esp32s3_getting_started/ (read
  2026-10-03): "Dimensions 21 x 17.8mm" (XIAO ESP32S3), "21 x 17.8 x 15mm
  (with expansion board)" (Sense, camera fitted); Sense product page
  https://www.seeedstudio.com/XIAO-ESP32S3-Sense-p-5639.html (SKU 113991115
  in the product image name).
- Seeed 3D model seeed-studio-xiao-esp32s3-sense-3d_model.zip ->
  "Seeed Studio XIAO-ESP32-S3-Sense.step" (wiki "3D Model" link), measured
  2026-10-03 with OpenCascade, heights above the XIAO's bottom face
  (the face that sits on this board):

  ========================================  =========
  XIAO PCB top                               1.25 mm
  USB-C receptacle top                       4.46 mm
  Sense expansion PCB top                    5.43 mm
  camera FPC connector (JUSHUO AFC01) top    7.88 mm
  microSD socket (Amphenol 10067099) top     8.04 mm
  microSD card, when inserted, top           8.50 mm
  camera module top (NOT FITTED)            13.96 mm
  ========================================  =========

  So the **Sense stack without the camera is 8.04 mm tall** (8.5 mm with a
  card in the slot). An inserted microSD card sticks out 3.1 mm beyond the
  XIAO's USB end, i.e. 1.58 mm beyond the USB-C receptacle face. Nothing on
  the XIAO's underside protrudes below its bottom face (castellations and
  pads only).

Pin map (same as the socket version):

    D0  D[0]  GPIO1   1      VBUS (5V)  VBUS  -       14
    D1  D[1]  GPIO2   2      GND        GND   -       13
    D2  D[2]  GPIO3   3      3V3        V3V3  -       12
    D3  D[3]  GPIO4   4      D10        D[10] GPIO9   11
    D4  D[4]  GPIO5   5      D9         D[9]  GPIO8   10
    D5  D[5]  GPIO6   6      D8         D[8]  GPIO7    9
    D6  D[6]  GPIO43  7      D7         D[7]  GPIO44   8

Coordinate frame (top view, y up), chosen to match the socket version: origin
at the centre of the 2 x 7 pad field, the USB-C end toward +x. Pads 1..7
(D0..D6) run along y = +8.0825 from x = +7.62 (pad 1) to -7.62; pads 8..14
(D7..D10, 3V3, GND, VBUS) along y = -8.0825 from x = -7.62 to +7.62. From the
KiCad frame: x = -10.5 - y_kicad, y = 8.9175 - x_kicad (a 90 degree
rotation of the y-up KiCad view, no mirror; pad 1 lands at (+7.62, +8.0825),
next to the USB end, as on the DIP footprint).

Underside pads (15-25): NOT soldered and not modelled as pads. They face this
board's top layer, so the landpattern carries a top-layer ``KeepOut`` (pour,
via and route) over each of them grown by ``UNDERSIDE_KEEPOUT_MARGIN``: no
trace, via or pour of ours can sit under an exposed XIAO pad (EN, JTAG,
USB D+/D-, VBAT, the GND pad), which would otherwise rely on one layer of
soldermask alone. Routing between the castellated rows elsewhere is allowed.

Design choices (not from Seeed): pads exactly Seeed's (corner radius =
rratio x short side = 0.5 mm), default soldermask / paste from the pad;
silkscreen = the two module end lines (the long edges run through the pads)
plus the USB-C outline and a pin-1 dot; courtyard = module + pad overhang +
USB-C receptacle, 0.25 mm excess.
"""

from typing import ClassVar

import shapely
from jitx.circuit import Circuit
from jitx.component import Component
from jitx.feature import Courtyard, KeepOut, Silkscreen
from jitx.landpattern import Landpattern, PadMapping
from jitx.layerindex import LayerSet
from jitx.net import Port
from jitx.sample import SampleDesign
from jitx.shapes.composites import rectangle
from jitx.shapes.primitive import Circle, Polyline
from jitx.shapes.shapely import ShapelyGeometry
from jitxlib.landpatterns.pads import SMDPad
from jitxlib.symbols.box import BoxSymbol, Column, PinGroup, Row

# --- Seeed XIAO-ESP32-S3-SMD.kicad_mod (converted to this frame) ---------------
PITCH = 2.54
PINS_PER_ROW = 7
ROW_Y = 8.0825  # (17.00 - 0.835) / 2
FIRST_X = (PINS_PER_ROW - 1) / 2 * PITCH  # 7.62
PAD_ALONG_ROW = 2.00  # KiCad size 2.75 x 2.00, the 2.00 runs along the row
PAD_ACROSS_ROW = 2.75
PAD_RRATIO = 0.25
XIAO_MIN_X = -10.429  # F.Fab rectangle, y_kicad -0.071
XIAO_MAX_X = 10.522  # y_kicad -21.022 (USB end)
XIAO_MIN_Y = -8.8615  # x_kicad 17.779
XIAO_MAX_Y = 8.9225  # x_kicad -0.005
USB_MAX_X = 12.047  # F.SilkS USB-C outline, y_kicad -22.547
USB_MIN_Y = -4.4765  # x_kicad 13.394
USB_MAX_Y = 4.5225  # x_kicad 4.395


def circle_pad(x: float, y: float) -> shapely.Polygon:
    """Seeed's 1.7 mm round underside pad."""
    return shapely.Point(x, y).buffer(1.7 / 2)


def rect_pad(x: float, y: float, w: float, h: float) -> shapely.Polygon:
    """Seeed's rectangular underside pad, w along x, h along y (this frame)."""
    return shapely.box(x - w / 2, y - h / 2, x + w / 2, y + h / 2)


UNDERSIDE_PADS = [
    circle_pad(8.632, 1.2975),  # 15 MTDI
    circle_pad(8.632, -1.2425),  # 16 MTDO
    circle_pad(6.092, 1.2975),  # 17 EN
    circle_pad(6.092, -1.2425),  # 18 GND
    circle_pad(3.552, 1.2975),  # 19 MTMS
    circle_pad(3.552, -1.2425),  # 20 MTCK
    circle_pad(1.012, 1.2975),  # 21 USB_DN
    circle_pad(1.012, -1.2425),  # 22 USB_DP
    rect_pad(0.382, 4.4725, 1.1, 2.5),  # 23 VBAT
    rect_pad(2.287, 4.4725, 1.1, 2.5),  # 24 GND (battery -)
    rect_pad(-2.0, -1.0925, 2.5, 2.75),  # 25 PAD
]
"""The module's underside pads in this frame (Seeed pads 15-25)."""

PAD_V3V3 = 12  # Seeed symbol XIAO-ESP32-S3-SMD: 12 3V3_OUT, 13 GND, 14 VBUS
PAD_GND = 13
PAD_VBUS = 14

# --- Seeed 3D model (heights above the XIAO's bottom face) -----------------------
STACK_HEIGHT_NO_CAMERA = 8.04  # microSD socket top
STACK_HEIGHT_WITH_CARD = 8.50  # inserted microSD card top
STACK_HEIGHT_WITH_CAMERA = 13.96  # camera module top (not fitted)
SD_CARD_BEYOND_USB = 1.58  # inserted card past the USB-C receptacle face

# --- Design choices --------------------------------------------------------------
UNDERSIDE_KEEPOUT_MARGIN = 0.5
"""Growth of each underside pad into the top-layer keepout (mm)."""
SILK_WIDTH = 0.12
COURTYARD_EXCESS = 0.25
PIN1_DOT_RADIUS = 0.25


def pad_position(n: int) -> tuple[float, float]:
    """Centre of castellated pad ``n`` (1..14) in the landpattern frame."""
    if 1 <= n <= PINS_PER_ROW:
        return FIRST_X - (n - 1) * PITCH, ROW_Y
    if PINS_PER_ROW < n <= 2 * PINS_PER_ROW:
        return -FIRST_X + (n - PINS_PER_ROW - 1) * PITCH, -ROW_Y
    raise ValueError(f"XIAO castellated pad number {n} not in 1..14")


def underside_keepout() -> list[ShapelyGeometry]:
    """Underside pads grown by ``UNDERSIDE_KEEPOUT_MARGIN``: one hole-free
    polygon per merged cluster (a multi-polygon, or a polygon with holes,
    reaches the router as its bounding box). Filling the small gaps enclosed
    between four grown pads only enlarges the keepout."""
    region = shapely.union_all(
        [p.buffer(UNDERSIDE_KEEPOUT_MARGIN) for p in UNDERSIDE_PADS]
    )
    parts = list(region.geoms) if isinstance(region, shapely.MultiPolygon) else [region]
    out: list[ShapelyGeometry] = []
    for g in parts:
        assert isinstance(g, shapely.Polygon), g.geom_type
        out.append(ShapelyGeometry(shapely.Polygon(g.exterior)))
    return out


class XiaoSMDLandpattern(Landpattern):
    """14 castellated pads in two rows 16.165 mm apart; underside-pad keepout."""

    def __init__(self) -> None:
        radius = PAD_RRATIO * min(PAD_ALONG_ROW, PAD_ACROSS_ROW)
        shape = rectangle(PAD_ALONG_ROW, PAD_ACROSS_ROW, radius=radius)
        self.p = {
            n: SMDPad(shape).at(*pad_position(n))
            for n in range(1, 2 * PINS_PER_ROW + 1)
        }

        self.underside_keepouts = [
            KeepOut(shape, layers=LayerSet(0), pour=True, via=True, route=True)
            for shape in underside_keepout()
        ]

        # Module end lines (the long edges run through the pads) + USB-C.
        half = SILK_WIDTH / 2
        x0, x1 = XIAO_MIN_X - half, XIAO_MAX_X + half
        y0, y1 = XIAO_MIN_Y - half, XIAO_MAX_Y + half
        self.module_ends = [
            Silkscreen(Polyline(SILK_WIDTH, [(x0, y0), (x0, y1)])),
            Silkscreen(Polyline(SILK_WIDTH, [(x1, y0), (x1, y1)])),
        ]
        self.usb_outline = Silkscreen(
            Polyline(
                SILK_WIDTH,
                [(x1, USB_MAX_Y), (USB_MAX_X, USB_MAX_Y)]
                + [(USB_MAX_X, USB_MIN_Y), (x1, USB_MIN_Y)],
            )
        )
        # Pin-1 dot inside the outline, between pad 1 and the USB end.
        x_pin1, y_pin1 = pad_position(1)
        self.pin1_marker = Silkscreen(
            Circle(radius=PIN1_DOT_RADIUS).at(
                (x_pin1 + PAD_ALONG_ROW / 2 + XIAO_MAX_X) / 2, y_pin1
            )
        )

        cx0 = XIAO_MIN_X - COURTYARD_EXCESS
        cx1 = USB_MAX_X + COURTYARD_EXCESS
        cy = ROW_Y + PAD_ACROSS_ROW / 2 + COURTYARD_EXCESS
        self.courtyard = Courtyard(
            rectangle(cx1 - cx0, 2 * cy).at((cx0 + cx1) / 2, 0.0)
        )


class XiaoESP32S3SMD(Component):
    """Seeed XIAO ESP32S3 Sense soldered on its castellated pads.

    ``D[k]`` is XIAO pin Dk (k = 0..10); ``VBUS`` is the "5V" pin, ``V3V3``
    the "3V3" pin. Geometry and height facts are class attributes for the
    board layout.
    """

    manufacturer = "Seeed Studio"
    mpn = "113991115"  # Seeed SKU, XIAO ESP32S3 Sense
    module: ClassVar[str] = (
        "Seeed Studio XIAO ESP32S3 Sense, camera not fitted (consigned, soldered)"
    )
    datasheet = "https://wiki.seeedstudio.com/xiao_esp32s3_getting_started/"
    reference_designator_prefix = "U"

    PITCH: ClassVar[float] = PITCH
    ROW_SPACING: ClassVar[float] = 2 * ROW_Y
    USB_DIRECTION: ClassVar[str] = "+x"
    USB_MAX_X: ClassVar[float] = USB_MAX_X
    USB_HALF_WIDTH: ClassVar[float] = (USB_MAX_Y - USB_MIN_Y) / 2
    STACK_HEIGHT: ClassVar[float] = STACK_HEIGHT_NO_CAMERA
    STACK_HEIGHT_WITH_CARD: ClassVar[float] = STACK_HEIGHT_WITH_CARD
    SD_CARD_BEYOND_USB: ClassVar[float] = SD_CARD_BEYOND_USB

    # Class-scope port arrays are the JITX structural idiom (each instance gets
    # its own ports), not shared mutable state; hence the RUF012 waiver.
    D = [Port() for _ in range(11)]  # noqa: RUF012
    VBUS = Port()
    GND = Port()
    V3V3 = Port()

    landpattern = XiaoSMDLandpattern()
    symbol = BoxSymbol(
        rows=Row(left=PinGroup(*D[:7]), right=PinGroup(*D[7:])),
        columns=Column(up=PinGroup(VBUS, V3V3), down=PinGroup(GND)),
    )

    def __init__(self) -> None:
        lp = self.landpattern
        # Pads 1-11 are D0-D10 in order; 12 3V3, 13 GND, 14 VBUS (Seeed symbol).
        mapping = {port: [lp.p[k + 1]] for k, port in enumerate(self.D)}
        mapping[self.V3V3] = [lp.p[PAD_V3V3]]
        mapping[self.GND] = [lp.p[PAD_GND]]
        mapping[self.VBUS] = [lp.p[PAD_VBUS]]
        self.mappings = [PadMapping(mapping)]

    @classmethod
    def vbus_position(cls) -> tuple[float, float]:
        """Centre of the VBUS ("5V") pad in the landpattern frame, for
        placement code that runs before the part exists."""
        return pad_position(PAD_VBUS)


class XiaoSMDHarness(Circuit):
    """One module, unconnected."""

    xiao = XiaoESP32S3SMD()


class TestDesign(SampleDesign):
    """Build harness: ``jitx build pappalapap.components.xiao_esp32s3_smd.TestDesign``."""

    circuit = XiaoSMDHarness()
