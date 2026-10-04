"""JLCPCB 2-layer flexible PCB (FPC) substrate.

Source: JLCPCB "Flexible PCB Capabilities" page,
https://jlcpcb.com/capabilities/flex-pcb-capabilities (retrieved 2026-10-03).
Every number below traces to that page unless a comment says otherwise.

Construction chosen from the page's 2-layer options: 25 um polyimide core,
1 oz (35 um) copper both sides, 25 um PI + 25 um adhesive coverlay both sides,
ENIG, finished thickness 0.2 mm. The page's other 2-layer builds (1/3 oz or
1/2 oz copper with 12.5 um PI + 15 um adhesive coverlay, 0.11/0.12 mm; or the
50 um core at 0.19 mm) are not modelled.

The predefined ``jitxlib.jlcpcb`` substrates are rigid FR-4 and do not apply.
"""

from jitx.board import Board
from jitx.circuit import Circuit
from jitx.design import Design
from jitx.feature import Soldermask
from jitx.layerindex import Side
from jitx.shapes.composites import rectangle
from jitx.stackup import Conductor, Dielectric, Stackup
from jitx.substrate import FabricationConstraints, Substrate
from jitx.via import Via, ViaType

MIL = 0.0254
"""Millimetres per mil."""

COVERLAY_THICKNESS = 0.050
"""JLC coverlay on 1 oz copper: 25 um PI + 25 um adhesive (mm)."""

COPPER_THICKNESS = 0.035
"""1 oz copper, "35 um (1 oz)" (mm)."""


# --- Materials ---------------------------------------------------------------


class Coverlay(Dielectric):
    """Polyimide coverlay with its bonding adhesive, modelled as one layer.

    JLC: "PI: 25um, Adhesive: 25um (on 1oz copper)", total 0.050 mm per side.
    JLC quotes one permittivity for the coverlay as a whole ("Coverlay er: 2.9"),
    so PI and adhesive are not split into separate layers. Colour options:
    yellow (recommended) / black / white / transparent; white is quoted 10-18 um
    thicker per side, so this thickness applies to yellow or black only.
    Df is not stated by JLC and is left unset.
    The coverlay is the FPC's solder mask, so this layer represents Soldermask.
    """

    dielectric_coefficient = 2.9
    representing = Soldermask


class PolyimideCore(Dielectric):
    """Polyimide base film. JLC: "Inner PI thickness: 25 um", "Core polyimide er: 3.3".

    Adhesive and adhesiveless bases are both offered; adhesiveless is JLC's
    recommendation for bending life and is what reconciles with the 0.2 mm
    finished thickness (no base-adhesive layer modelled). Df not stated.
    """

    dielectric_coefficient = 3.3


class Copper1oz(Conductor):
    """1 oz copper, 35 um ("35 um (1 oz)"). Foil kind (RA or ED) and Rz not stated by JLC."""

    thickness = COPPER_THICKNESS


# --- Stackup -----------------------------------------------------------------


class JLCFlex2LStackup(Stackup):
    """Explicit top-to-bottom 2-layer FPC build.

    Sum: 0.050 + 0.035 + 0.025 + 0.035 + 0.050 = 0.195 mm against JLC's stated
    0.2 mm finished thickness (excluding stiffeners); the 5 um residual is
    within ENIG/via plating and the page's rounding to one decimal place.
    """

    top_coverlay = Coverlay(thickness=COVERLAY_THICKNESS)
    top = Copper1oz(name="Top (LED face A)")
    core = PolyimideCore(thickness=0.025)
    bottom = Copper1oz(name="Bottom (LED face B)")
    bottom_coverlay = Coverlay(thickness=COVERLAY_THICKNESS)


# --- Fabrication rules -------------------------------------------------------


class JLCFlexRules(FabricationConstraints):
    """JLCPCB FPC rules for the 1 oz, 2-layer build.

    Capabilities with no JITX field (enforced by review, not by the engine):

    - Finished thickness tolerance: +/-0.05 mm (stiffened area <= 0.3 mm),
      +/-0.03 mm in gold-finger areas.
    - Trace width tolerance +/-20 %. Hole diameter tolerance +/-0.08 mm.
    - Hole range 0.1-6.5 mm (PTH > 5 mm risky). Min plated slot 0.50 mm.
    - Extreme 2-layer via 0.10/0.30 mm (hole/pad) at extra cost; not used here.
    - PTH annular ring: 0.25 mm recommended, 0.18 mm absolute (component PTH pads).
    - Exposed pad to trace >= 0.15 mm; via ring to trace >= 0.1 mm.
    - Coverlay opening to trace >= 0.15 mm. Keep coverlay over vias (tented).
    - Gold-finger pad to board edge 0.2 mm (fingers are cut back otherwise).
    - Copper to slots >= 0.3 mm. Outline tolerance +/-0.1 mm (laser).
    - Bend radius: multi-layer >= 10x total thickness (2 mm for this 0.2 mm build).
    - Panel: 5 mm handling edges on all four sides, 2 mm board spacing
      (3 mm with metal stiffeners); max panel 234 x 490 mm.
    - Max dimensions: regular 234 x 490 mm; absolute 250 x 600 mm with edge
      rails, "confirm with customer support before ordering".
    - Surface finish ENIG, 1 u" or 2 u". Impedance control not offered.
    - Stiffeners (no JITX field; see ``JLCFlex2L.PI_STIFFENER_THICKNESSES``):
      PI 0.1/0.15/0.2/0.225/0.25 mm; FR4 0.1-1.6 mm; stainless 0.1/0.2/0.3 mm;
      tapes 3M9077 0.05, 3M468 0.13, tesa8854 0.1 mm.
    """

    min_copper_width = 4 * MIL  # "35 um (1 oz) copper: 4/4 mil"
    min_copper_copper_space = 4 * MIL  # "35 um (1 oz) copper: 4/4 mil"
    min_copper_hole_space = 0.2  # "NPTH to copper clearance >= 0.20 mm"
    min_copper_edge_space = 0.3  # "Copper to board edge >= 0.3mm"

    # "Via diameter must be at least 0.2mm larger than via hole size" -> 0.1 per side.
    min_annular_ring = 0.1
    min_drill_diameter = 0.3  # "Regular: 0.3mm/0.55mm" (extreme 0.10 mm costs extra)

    # Not stated for FPC ("same requirements as rigid PCBs"). Derived, not quoted:
    # leaded pitch = min trace + min space; BGA pitch = min BGA pad 0.25 + min space.
    min_pitch_leaded = 2 * 4 * MIL
    min_pitch_bga = 0.25 + 4 * MIL

    max_board_width = 490.0  # "Regular: 234 x 490 mm"
    max_board_height = 234.0  # "Regular: 234 x 490 mm"

    min_silkscreen_width = 0.15  # "Character Line Width >= 0.15mm"
    min_silk_solder_mask_space = 0.15  # "Character to Pad Clearance >= 0.15mm"
    min_silkscreen_text_height = 1.0  # "Character Height >= 1mm"
    solder_mask_registration = 0.1  # "Coverlay expansion (one-sided): 0.1 mm"
    min_soldermask_opening = 0.0  # not stated by JLC; 0 = no constraint
    min_soldermask_bridge = 0.5  # "Minimum solder bridge width 0.5 mm"

    min_th_pad_expand_outer = 0.1  # coverlay expansion 0.1 mm, applied to TH pads
    min_hole_to_hole = (
        0.4  # only FPC figure stated: "Castellated hole to hole >= 0.4 mm"
    )
    min_pth_pin_solder_clearance = 0.1  # coverlay expansion 0.1 mm


# --- Substrate ---------------------------------------------------------------


class JLCFlex2L(Substrate):
    """JLCPCB 2-layer 1 oz polyimide FPC, 0.2 mm, ENIG, coverlay both sides.

    One through via, sized above JLC's regular minimum. No routing structure:
    JLC flex has no impedance control, and the board-wide trace/clearance
    defaults belong on the Design (rules set above this fab floor).
    """

    stackup = JLCFlex2LStackup()
    constraints = JLCFlexRules()

    FINISHED_THICKNESS = 0.2
    """JLC finished FPC thickness for this build, excluding stiffeners (mm)."""

    PI_STIFFENER_THICKNESSES = (0.1, 0.15, 0.2, 0.225, 0.25)
    """JLC PI stiffener options (mm), the stiffener used under gold fingers."""

    class THVia(Via):
        """Tented through via. JLC regular minimum is 0.30/0.55 mm (hole/pad);
        this uses 0.30/0.60 mm so pad - hole = 0.30 mm, above JLC's preferred
        ">= 0.25 mm". JLC recommends keeping coverlay over vias, hence tented."""

        type = ViaType.MechanicalDrill
        start_layer = Side.Top
        stop_layer = Side.Bottom
        hole_diameter = 0.3
        diameter = 0.6
        tented = True

    @classmethod
    def finger_thickness(cls) -> float:
        """FPC thickness under top-side gold fingers with no copper behind them.

        Follows JLC's PI-stiffener calculator method: subtract the coverlay
        removed over the fingers and the absent back-side copper.
        """
        return cls.FINISHED_THICKNESS - COVERLAY_THICKNESS - COPPER_THICKNESS

    @classmethod
    def pi_stiffener_for(cls, total_thickness: float) -> float:
        """Smallest JLC PI stiffener that brings the finger area to at least
        ``total_thickness`` (JLC's calculator rounds up, as here)."""
        needed = total_thickness - cls.finger_thickness()
        return min(
            (t for t in cls.PI_STIFFENER_THICKNESSES if t >= needed),
            default=max(cls.PI_STIFFENER_THICKNESSES),
        )


# --- Build harness -----------------------------------------------------------

STRIP_LENGTH = 490.0
STRIP_HEIGHT = 50.0  # 5 rows x 10 mm pitch (see circuits.led_strip)
EDGE_KEEPOUT = JLCFlexRules.min_copper_edge_space


class TestBoard(Board):
    """Full-size strip outline, to exercise the max-dimension rule."""

    shape = rectangle(STRIP_LENGTH, STRIP_HEIGHT)
    signal_area = rectangle(
        STRIP_LENGTH - 2 * EDGE_KEEPOUT, STRIP_HEIGHT - 2 * EDGE_KEEPOUT
    )


class EmptyCircuit(Circuit):
    """No parts: the harness only proves the substrate translates."""


class TestDesign(Design):
    """Substrate smoke test: ``jitx build pappalapap.substrate.TestDesign``."""

    board = TestBoard()
    substrate = JLCFlex2L()
    circuit = EmptyCircuit()
