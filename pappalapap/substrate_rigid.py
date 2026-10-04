"""JLCPCB 2-layer 1.6 mm FR-4 rigid substrate (standard manufacturing).

Source: JLCPCB "Rigid PCB Manufacturing Capabilities" page,
https://jlcpcb.com/capabilities/pcb-capabilities (retrieved 2026-10-03).
Every number below traces to that page unless a comment says otherwise.

Build: 2 layers, 1.6 mm, 1 oz finished outer copper, LPI soldermask (green),
routed outline. No impedance control (JLC only offers it on 4+ layers), so
there are no routing structures; board-wide trace/clearance defaults belong
on the Design, above this fab floor.

The predefined ``jitxlib.jlcpcb`` substrates (4- and 6-layer only) are not
installed in this environment and have no 2-layer build, so this is custom.
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

BOARD_THICKNESS = 1.6
"""Nominal finished thickness (mm); JLC tolerance for >= 1.0 mm boards is +/-10 %."""

COPPER_THICKNESS = 0.035
"""1 oz finished outer copper (mm). "Finished Outer Layer Copper 2-layer: 1 oz"."""

SOLDERMASK_THICKNESS = 0.010
"""JLC: "Solder mask ink thickness >= 10 um" (mm); the stated minimum."""

CORE_THICKNESS = BOARD_THICKNESS - 2 * COPPER_THICKNESS - 2 * SOLDERMASK_THICKNESS
"""Derived, not quoted: JLC does not publish the 2-layer core thickness, so the
core takes up the remainder of the 1.6 mm nominal (1.51 mm)."""


# --- Materials ---------------------------------------------------------------


class JLCSoldermask(Dielectric):
    """LPI soldermask. JLC: "Solder mask dielectric constant 3.8",
    "Solder mask ink thickness >= 10 um". Df not stated by JLC and left unset."""

    dielectric_coefficient = 3.8
    representing = Soldermask


class JLCFR4Core(Dielectric):
    """FR-4 core, Grade A laminate (Nan Ya, KB, Shengyi, etc.).
    JLC: "FR-4 Dielectric Constants 4.5 (2-Layer PCB)". Quoted frequency and Df
    are not stated by JLC; Df left unset."""

    dielectric_coefficient = 4.5


class Copper1oz(Conductor):
    """1 oz finished outer copper, 35 um. Foil type and Rz not stated by JLC.
    Average hole plating thickness 18 um (no JITX field)."""

    thickness = COPPER_THICKNESS


# --- Stackup -----------------------------------------------------------------


class JLC2L16Stackup(Stackup):
    """Explicit top-to-bottom 2-layer 1.6 mm build.

    Sum: 0.010 + 0.035 + 1.510 + 0.035 + 0.010 = 1.600 mm, equal to the
    nominal by construction (core is the derived remainder).
    """

    top_mask = JLCSoldermask(thickness=SOLDERMASK_THICKNESS)
    top = Copper1oz(name="Top")
    core = JLCFR4Core(thickness=CORE_THICKNESS)
    bottom = Copper1oz(name="Bottom")
    bottom_mask = JLCSoldermask(thickness=SOLDERMASK_THICKNESS)


# --- Fabrication rules -------------------------------------------------------


class JLC2LRules(FabricationConstraints):
    """JLCPCB 2-layer, 1 oz FR-4 rules (standard pricing where it matters).

    Capabilities with no JITX field, or a stricter case the single engine
    field cannot express (enforced by review, not by the engine):

    - PTH annular ring (2-layer 1 oz): recommended >= 0.25 mm, absolute 0.18 mm
      (mapped to ``min_th_pad_expand_outer``; ``min_annular_ring`` carries the
      looser via rule). NPTH pad annular ring >= 0.45 mm recommended.
    - PTH to track 0.28 mm (0.35 mm recommended); NPTH to track 0.2 mm.
      ``min_copper_hole_space`` uses the PTH figure, which covers both.
    - Pad hole-to-hole spacing 0.45 mm (``min_hole_to_hole`` carries the via 0.2).
    - SMD pad to pad (different nets) 0.15 mm; pad to track 0.1 mm;
      min SMD pad 0.25 x 0.25 mm; same-net track spacing 0.25 mm.
    - Soldermask opening to neighbouring trace >= 0.09 mm. Bridge 0.13 mm for
      black/white mask (0.10 mm for green/red/yellow/blue/purple, mapped).
    - Drill range 0.15-6.3 mm; min NPTH 0.50 mm; min plated slot 0.5 mm
      (length >= 2x width); min non-plated slot 1.0 mm.
    - Hole tolerance +0.13/-0.08 mm; hole position +/-0.075 mm.
    - Via pricing: 0.15 mm holes, or 0.2/0.25 mm holes with pad < 0.45 mm, cost
      more. "Preferred Min. Via hole size: 0.2mm" -> ``min_drill_diameter``.
      Via pad should exceed hole by 0.1 mm (0.15 mm preferred).
    - V-cut edges need 0.4 mm copper clearance (routed edges 0.2 mm, mapped).
    - Track width tolerance +/-20 %. Thickness tolerance +/-10 % (1.44-1.76 mm).
    - Outline tolerance +/-0.2 mm regular, +/-0.1 mm precision routing.
    - Silkscreen character width:height 1:6 preferred.
    - Surface finish HASL (leaded / lead-free) or ENIG; 0.2-0.25 mm BGA pads
      need ENIG. Min board 3 x 3 mm. Panel spacing >= 2 mm.
    - Plugged (soldermask-filled) vias: no mask opening either side, <= 0.5 mm
      diameter, >= 0.35 mm from other mask openings.
    """

    min_copper_width = 0.10  # "1- and 2-layer: 0.10 / 0.10 mm (4 / 4 mil)"
    min_copper_copper_space = 0.10  # "1- and 2-layer: 0.10 / 0.10 mm (4 / 4 mil)"
    min_copper_hole_space = 0.28  # "PTH to Track ... minimum 0.28mm" (via hole 0.2)
    min_copper_edge_space = 0.2  # "Copper clearance from routed board edges: >= 0.2 mm"

    # "Via diameter should be 0.1mm (0.15mm preferred) larger than Via hole size."
    min_annular_ring = 0.1 / 2
    min_drill_diameter = 0.2  # "Preferred Min. Via hole size: 0.2mm"

    # Not stated by JLC. Derived, not quoted: min SMD pad (0.25) + SMD
    # pad-to-pad clearance (0.15); BGA: min BGA pad (0.25, no-ENIG bound) + 0.15.
    min_pitch_leaded = 0.25 + 0.15
    min_pitch_bga = 0.25 + 0.15

    max_board_width = 670.0  # "FR4(2-layer): 670 x 600 mm"
    max_board_height = 600.0  # "FR4(2-layer): 670 x 600 mm"

    min_silkscreen_width = 0.15  # "Minimum Line Width >= 0.15mm"
    min_silk_solder_mask_space = 0.15  # "Pad To Silkscreen 0.15mm"
    min_silkscreen_text_height = 1.0  # "Minimum text height 40 mil (1.0mm)"
    solder_mask_registration = 0.0  # "Soldermask Expansion 1:1" (LDI, June 2025)
    min_soldermask_opening = 0.0  # not stated by JLC; 0 = no constraint
    min_soldermask_bridge = 0.10  # "1oz: Min. pad spacing: 0.10 mm (green, ...)"

    min_th_pad_expand_outer = 0.18  # "2-layer: 1 oz: ... absolute minimum 0.18 mm"
    min_hole_to_hole = 0.2  # "Via Hole-to-Hole Spacing 0.2mm"
    min_pth_pin_solder_clearance = 0.0  # "Soldermask Expansion 1:1"


# --- Substrate ---------------------------------------------------------------


class JLC2L16(Substrate):
    """JLCPCB 2-layer 1.6 mm FR-4, 1 oz outer copper, LPI soldermask.

    One through via at standard pricing. No routing structures: no impedance
    control on 2-layer JLC boards.
    """

    stackup = JLC2L16Stackup()
    constraints = JLC2LRules()

    class THVia(Via):
        """Tented through via, 0.30/0.60 mm (hole/pad). JLC charges extra only
        for 0.15 mm holes or 0.2/0.25 mm holes with pad < 0.45 mm, so this is
        standard pricing. Annular ring (0.60 - 0.30) / 2 = 0.15 mm, above the
        preferred 0.075 mm (pad 0.15 mm over hole). Tenting is an order option."""

        type = ViaType.MechanicalDrill
        start_layer = Side.Top
        stop_layer = Side.Bottom
        hole_diameter = 0.3
        diameter = 0.6
        tented = True


# --- Build harness -----------------------------------------------------------

TEST_W, TEST_H = 45.0, 35.0  # interface-board size from PLAN.md
EDGE_KEEPOUT = JLC2LRules.min_copper_edge_space


class TestBoard(Board):
    """Interface-board-sized outline."""

    shape = rectangle(TEST_W, TEST_H)
    signal_area = rectangle(TEST_W - 2 * EDGE_KEEPOUT, TEST_H - 2 * EDGE_KEEPOUT)


class EmptyCircuit(Circuit):
    """No parts: the harness only proves the substrate translates."""


class TestDesign(Design):
    """Substrate smoke test: ``jitx build pappalapap.substrate_rigid.TestDesign``."""

    board = TestBoard()
    substrate = JLC2L16()
    circuit = EmptyCircuit()
