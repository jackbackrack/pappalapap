# Project Plan: pappalapap

Workflow tier: **complete-board**. See ARCHITECTURE.md for geometry, power, chain order and pinout.

> **2026-10-03, pitch change:** after the Möbius shape study (`mechanical/`), the user changed the LED pitch from 12.25 mm to **10.0 mm** (5 rows, 490 mm strip kept). The strip is now 490 x 50 mm with 49 column positions; top face cols 1..47 (235 LEDs), bottom face cols 0..48 (245 LEDs), 480 LEDs total; lap 10 mm, loop 480 mm, 96-column ring = 24 characters; ~5.5 A full white, ~29 ms frame (~34 fps). Task history below keeps the numbers each task was accepted with; follow-up notes dated 2026-10-03 (pitch change) give the current values.

> **2026-10-05, two-segment strip:** JLCPCB cannot assemble flex boards longer than a 240 mm panel side (5 mm rails all round, so a board ≤ 230 mm). The user chose to split the strip into **two segments joined by a soldered lap splice**, keeping the aspect ratio: pitch **9.1 mm**, 49 × 5 grid, strip 445.9 × 45.5 mm, 480 LEDs, 96 loop columns. Segment A = cols 0..23 (220.9 mm, with the tail), segment B = cols 24..48 (230.0 mm), 5 mm overlap centred on the column gap at 218.4 mm. See task [seg-01] below and ARCHITECTURE.md "Segments and splice".

## Architecture Summary

### Power Tree
| Rail | Voltage | Source | Regulator | Load | Current |
|------|---------|--------|-----------|------|---------|
| VDD_LED | 5 V | external 5 V/5 A via controller + ZIF | none | 480 x WS2816C | ~0.4 A idle, ~5.5 A full white (firmware brightness cap required) |

### Interface Map
| Interface | From | To | Protocol | SI Constrained | Impedance |
|-----------|------|----|----------|----------------|-----------|
| DIN | Controller (5 V buffer) | LED #1 | WS281x NZR 800 kbit/s | No | — |
| DO/DI + BO/BI chain | LED n | LED n+1 | same | No | — |
| DRET | LED #480 DO | connector | same (debug return) | No | — |

### Board
- Dimensions: 490 x 50 mm + connector tail (10 mm pitch; was 61.25 mm high at 12.25 mm)
- Layers: 2 (flex), LEDs both sides, back-to-back aligned
- Material: polyimide flex, JLCPCB, 1 oz Cu if available

## Data Sources (approved by user 2026-10-03: datasheet pads, compared against EasyEDA; ZIF part chosen on price/availability/reliability)

| Component | MPN | Package | Datasheet Source | Footprint Method | Status |
|-----------|-----|---------|-----------------|------------------|--------|
| Addressable LED | WS2816C-2121 (LCSC C965561) | 2.2x2.2 mm, 6 pads | LCSC datasheet, saved at `docs/datasheets/WS2816C-2121.pdf`; LCSC evidence in `docs/datasheets/C965561_lcsc.txt` (in stock, $0.1575) | Custom landpattern from the datasheet's recommended pads (0.70x0.32 mm, 0.63 mm row pitch, 1.19 mm gap); no EasyEDA data | Ready |
| Flex tail fingers | — (mechanical) | 16 x 1.0 mm | XFCN F1002-B datasheet (FFC spec) | Mechanical/vendor-defined pads | Ready |
| ZIF connector (controller side) | XFCN F1002-B-16-20T-R (C481251) | 16P 1.0 mm | LCSC datasheet | Board 2 | Chosen, deferred |

---

## Phase 1: Substrate + Components

### [sub-01] JLCPCB 2-layer flex substrate
- **Type:** substrate
- **Skill:** jitx-substrate-modeler
- **Description:** Custom 2-layer polyimide flex matching JLCPCB FPC capabilities: copper weight (prefer 1 oz), PI core, coverlay both sides, ENIG, through via, min trace/space and drill per JLC flex rules. Add a stiffener note/layer for the tail.
- **Inputs:** JLCPCB FPC capability page
- **Checklist:** Substrate
- **Verification:** `jitx build pappalapap.substrate.TestDesign`
- **Status:** accepted (2026-10-03). 1 oz, 0.2 mm adhesiveless, via 0.3/0.6 tented, 0.2 mm PI stiffener for 0.3 mm ZIF. Open risks: 490 mm + 5 mm panel rails exceeds the regular 490 limit (confirm with JLC); double-sided FPC assembly not confirmed; WS2816C pad rows will be single coverlay openings (0.31 mm gap < 0.5 mm bridge).

### [comp-01] WS2816C-2121
- **Type:** component
- **Skill:** jitx-component-modeler
- **Data source:** datasheet recommended pads (page 2), pinout BI/DI/VDD/DO/BO/GND (pins 1-6)
- **Description:** 6-pad 2x3 landpattern, pad 0.70 x 0.32 mm, row pitch 0.63 mm, inner gap 1.19 mm; body 2.2 x 2.2 x 1.05 mm; pin-1 silk dot (note: the body's chamfer is at pin 4/DO, not pin 1). BoxSymbol. LCSC C965561 as the MPN property.
- **Checklist:** Component
- **Verification:** `jitx build pappalapap.components.worldsemi_ws2816c.TestDesign`
- **Status:** accepted (2026-10-03). Matches EasyEDA within 5 µm. Open: mask web is 0.21 mm at 0.05 mm registration; recheck against the flex coverlay rules from sub-01.

### [comp-02] FPC tail fingers (16P, 1.0 mm); placed on the BOTTOM face by asm-01
- **Type:** component (mechanical footprint)
- **Skill:** jitx-component-modeler / jitx-physical-layout
- **Dependencies:** sub-01
- **Description:** 16 exposed ENIG finger pads sized to the XFCN F1002-B FFC spec; pinout 1-7 VDD, 8 DRET, 9 DIN, 10-16 GND.
- **Verification:** `jitx build pappalapap.components.fpc_tail.TestDesign`
- **Status:** accepted (2026-10-03). 0.50 mm fingers, 0.3 mm edge setback, 4.0 mm coverlay opening, 5.0 mm bottom PI stiffener (0.20 mm, gives 0.315 mm total). Board 2 must verify pin-1 orientation: flex goes in fingers-down, and a mirrored mapping would swap 5 V and GND.

---

## Phase 2: Circuits

### [cir-01] LedStrip (parametric two-face grid)
- **Type:** circuit
- **Skill:** jitx-circuit-builder + jitx-physical-layout
- **Dependencies:** comp-01, sub-01
- **Description:** Build 480 LEDs (was 390 at 12.25 mm pitch) in chain order from the `LedSite` geometry (row-major serpentine over top cols 1..47, then bottom cols 0..48). Wire DO→DI and BO→BI between consecutive LEDs; LED #1 BI → GND; expose ports VDD, GND, DIN, DRET. Place every LED explicitly at its pitch position and face.
- **Engineering questions:** Is the first BI tied to GND? Does every LED have VDD/GND? Is the last DO exposed?
- **Architectural questions:** `self.leds: list[WS2816C]` in chain order; frozen `LedSite`; no `getattr` or string keys; geometry knobs are constructor params.
- **Verification:** `jitx build pappalapap.circuits.led_strip.TestDesign` (small 3x5 instance)
- **Status:** accepted (2026-10-03). Orchestrator changed the chain to a row-major serpentine (4 U-turns per face) and verified 390 LEDs, 389+389 hops, and VDD/GND pad sides matching the alternating lanes on every LED. TestDesign and FullStripDesign build OK.
- **Update (2026-10-03, pitch change to 10 mm):** defaults now pitch 10.0, 49 columns, top `range(1, DEFAULT_COLUMNS - 1)`, bottom `range(DEFAULT_COLUMNS)`; FullStripDesign asserts the derived count. Re-verified: 480 LEDs, 479 + 479 hops; first LED top col 1 row 0, last top LED col 47 row 4, first bottom LED col 48 row 4, last LED bottom col 0 row 0; VDD/GND pad sides match the lane parity on all 480 LEDs. TestDesign and FullStripDesign build OK.

---

## Phase 3: Top-Level Assembly

### [asm-01] Flex strip design
- **Type:** assembly
- **Dependencies:** cir-01, comp-02, sub-01
- **Description:** Board outline (490 x 50 mm plus tail from the long edge at end A; 61.25 mm at the old pitch), tail fingers + stiffener, GND spine (end A) and VDD spine (end B) on the top face of the lap zones, insulated lap (no bond pads), PowerTag/GroundTag wide-trace rules, design rules for JLC flex. Replace the seeded sample design.
- **Verification:** `jitx build pappalapap.designs.flex_strip.Pappalapap`
- **Status:** accepted (2026-10-03). Design moved to `pappalapap/designs/flex_strip.py` (main.py re-exports it; build `pappalapap.designs.flex_strip.Pappalapap`). The tail fingers ended up on the **bottom** copper face, because that order (GND, DIN, DRET, VDD) matches the end-A layout without crossings; the stiffener is on the top face. 6 lanes × 2 layers as 9 pours, 492 tented vias, 779 of 780 LED power pads joined by pour tongues (bottom col 0 row 0 VDD needs a routed stub). Rules: 0.2/0.2 default, 1.0 mm power, thermal relief.
- **Update (2026-10-03, pitch change to 10 mm):** TAIL_OFFSET 13.5 → 11.25 mm (the GND riser must land in the now 10 mm lap zone; the window is 10.0 < offset ≤ 11.25), tail now spans 2.75..19.75 mm from end A. Lanes: gap lanes 6.0 mm, margin lanes 2.7 mm of copper, 14.7 mm per net per layer (was ~20). U-turn channels 3.7 mm (top) / 3.4 mm (bottom, to the edge rule). 9 pours, 600 tented vias (285 VDD + 285 GND stitching + 30 tail GND transition), 959 of 960 LED power pads joined by tongues (bottom col 0 row 0 VDD still needs a routed stub). Builds OK.

### [lay-01] Routing
- **Type:** layout
- **Skill:** jitx-physical-layout (code Routes) + autorouter/manual cleanup
- **Dependencies:** asm-01
- **Description:** Route 479 DO→DI + 479 BO→BI hops inside the ±2 mm row bands, 4+4 end U-turns, the end-B crossover (top col 47 row 4 → 2 vias → bottom col 48 row 4), DIN (finger → via → top col 1 row 0), DRET (bottom only), and the bottom col 0 row 0 VDD stub. Prefer deterministic code-generated routes for the regular hops.
- **Status:** pending

## Phase 3b: Design audit (voltage domains, chain continuity, lap symmetry, current/connector rating)

## Phase 4: Build + verify (DRC, route, check ratsnest, export)

---

## Board 2 (deferred by user 2026-10-03): Controller / adapter
Recommended scope: 2-layer JLC rigid board with a 5 V/5 A barrel jack, bulk cap + polyfuse,
a Seeed XIAO ESP32-S3 module (WiFi to change the text), a 74AHCT1G125 5 V data buffer with a
33 Ω series resistor, and a 12P 1.0 mm ZIF connector. About 8 parts. Planned in detail
once the flex is accepted.

---

## Board 2 (revised 2026-10-03): XIAO interface board, data sources APPROVED 2026-10-03 (screw terminal, XIAO in female sockets)
Replaces the deferred controller board. The user chose an off-the-shelf Seeed XIAO ESP32S3 Sense
(ESP32-S3, 8 MB PSRAM, on-board digital mic) and asked for a small rigid board that bridges the
XIAO and the flex display. It lives in the sculpture's base.

### Function
- 5 V in (≥ 5 A supply; full white ≈ 5.5 A, so the firmware brightness cap is mandatory) → fuse → reverse-polarity P-FET → TVS → bulk cap → ZIF VDD ×7
- XIAO powered from the same 5 V through a Schottky to its 5V pin (stops back-feeding USB VBUS)
- XIAO GPIO → 74AHCT1G125 (VCC 5 V, OE tied low, input 10 kΩ pull-down so the LEDs stay dark while the ESP32 boots) → 33 Ω → DIN (ZIF pin 9)
- DRET (ZIF pin 8) → 10 kΩ / 20 kΩ divider → XIAO GPIO (chain-integrity check)
- ZIF: XFCN F1002-B-16-20T-R, 16P 1.0 mm bottom contact. **Pin-1 orientation must be verified geometrically against the flex tail (fingers on the flex's bottom copper). A mirror swaps 5 V and GND at 5 A.**
- 2-layer 1.6 mm FR-4 at JLCPCB, 56 × 42 mm, M2.5 mounting holes, wide 5 V/GND pours

### Data sources (proposed)
| Part | MPN | LCSC | Package | Footprint source |
|---|---|---|---|---|
| XIAO sockets ×2 | HCTL PM254-1-07-Z-8.5 | C2897370 | 1×7 female 2.54 mm | JITX header generator; row spacing from the Seeed XIAO drawing |
| Buffer | Diodes 74AHCT1G125W5-7 | C842287 | SOT-25 | JITX SOT generator + datasheet |
| ZIF connector | XFCN F1002-B-16-20T-R | C481251 | SMD RA | datasheet recommended PCB layout, compared against EasyEDA (same approach as the LED) |
| Power input | Kefa KF301-5.0-2P screw terminal | C474881 | THT 5.0 mm | datasheet |
| Fuse 6.3 A | Littelfuse 045106.3MRL | C178982 | 2410 | JITX chip generator + datasheet |
| Reverse-polarity P-FET | AOS AO4407A (12 A) | C16072 | SOIC-8 | JITX SOIC generator |
| TVS | Littelfuse SMBJ5.0A | C83333 | SMB | JITX generator + datasheet |
| Schottky | MDD SS54 | C22452 (Basic) | SMA | JITX generator |
| Bulk cap | 1000 µF 16 V | C439782 | radial D10 × 13 | datasheet |
| Passives | 33 Ω, 10 k, 20 k, 100 nF | JLC Basic | 0603 | jitxlib queries |

### Tasks
- [ib-sub] 2-layer 1.6 mm JLC rigid substrate (`pappalapap/substrate_rigid.py`): accepted 2026-10-03 (custom JLC2L16; jitxlib.jlcpcb has 4/6-layer only; via 0.3/0.6 tented; rules from the JLC capabilities page)
- [ib-comp] components: accepted 2026-10-03 (9 parts + molded_diode helper, all TestDesigns build; ZIF from XFCN drawing, matches EasyEDA on pitch, pin-1 side and entry side; pin 1 at -x, cable enters from -y, contacts face down)
- [ib-cir] interface circuit + ZIF pin-1 geometric check against FpcTail16: accepted 2026-10-03 (`scripts/check_zif_mating.py`: tail finger k → contact k for all 16, nets match, mirror sanity test; DIN on D0/GPIO1, DRET on D1/GPIO2)
- [ib-asm] `pappalapap/designs/interface_board.py`: accepted 2026-10-03, unrouted. 56 × 42 mm (not 45 × 35: the courtyards of the 1000 µF, TVS and SS54 set the size), 4 × M2.5 NPTH, VLED/VIN/VFUSE top pours ≥ 4.2 mm, GND both layers. Passives from `parts/jlc-basic-passives.csv` via jitxlib-parts 2.x (added to pyproject). To do: routing, and the BOM note that the XIAO socket = 2 × PM254-1-07 headers.

## Board 3 (2026-10-03): column board, replaces the base interface board
The user chose to float the sculpture on a hollow column with the controller inside it. The XIAO ESP32S3 Sense is soldered directly (castellated SMD), mic only, no camera.
- [cb-comp] `xiao_esp32s3_smd.py` (Seeed's official SMD footprint, all 25 pads match 0.000 mm; underside pads under a keepout) and `wire_pads.py` (1.4/2.8 mm PTH for 18 AWG + cable-tie holes): accepted.
- [cb-asm] `designs/column_board.py` `ColumnBoard`: 24 × 66 mm, ZIF entry face at the top edge (insertion down), USB-C flush with the right edge, wire pads at the bottom, 1 mm groove strips along both long edges, tallest part the 1000 µF (14.5 mm). Pin-1 proof passes for both boards. Unrouted. Accepted 2026-10-03.
- `circuits/interface.py` refactored: XIAO type, power input and placement are parameters; `InterfaceBoard` (flat) still builds.
- Flex tail shortened to 16 mm (straight drop into the column board's ZIF). Mechanical orientation switched to the balance point (centre of mass 3.2° off the column axis).
- Layout JSON export (format from ~/socialbadge-ai `layout_placements.py`): every build writes `layout/<design>-input.json`; `layout/<design>.json`, if present, is read back. Only code-declared routes are exported; routes made in the JITX UI are not.
- Next: column, frame foot and base (mechanical/column.py); routing of the column board.
- [mech-col] `mechanical/column.py` (2026-10-03): frame foot fused to segment 1, two-part column 28.5 × 23.6 × 120 mm clamping the column board in grooves (USB-C slot, mic vents), base 110 × 90 × 32 mm with a panel DC-jack hole. All parts watertight. Overall height about 266 mm.
- [mech-col v2] (2026-10-03, user request): cylindrical one-piece column Ø33.5 mm with a 35 mm taper to a 23 × 6 mm neck plugging into a socket under the frame's tail window; internal slotted ribs hold the column board (slot tops = stop, 2 slot keys below); round base Ø100 × 30. Flex tail lengthened to 50 mm (outline 490 × 100). Pin-1 proof and flex design report regenerated.
- [mech-col v3] (2026-10-03, user request): neck centred on the column axis (tail S-bends 4.55 mm over the 36 mm taper; the board sits 0.35 mm higher to compensate); front access hatch at the ZIF with a flush screwed cover. Assembly order fixed: the tail goes through the neck first, the board slides into the slots, and the ZIF is closed through the hatch. All parts watertight, zero interference.
- [mech-col v4] (2026-10-03): heat-set inserts everywhere (hatch tabs M2, neck ends M2, column bottom bosses M3, base posts M3), countersunk cover, socket-floor and base-plate holes; hatch screws moved 3.3 mm in from the cover edges (they used to break out); neck inner 18.5 mm with 4.25 mm end walls for the inserts. Paper template regenerated (10 mm, 50 mm tail).
- [mech-col v5] (2026-10-03): slot keys replaced by one rectangular board pusher (20 × 4.6 × 22.2 mm); base top edge 4 mm round-over; 6 mm concave fillet collar where the column meets the base.
- [mech-col v6] (2026-10-03): smooth column-to-frame joint. The column taper now ends at the socket's outer size (flush seam); the socket flares into the rail (6 mm concave fillet along the rail, cosine narrowing to the 5 mm rail thickness); neck engagement 5 mm. Render: mechanical/out/column/frame_joint_closeup.png.

## 2026-10-05: two-segment flex strip (JLC 240 mm assembly limit)

### [seg-01] Segment the strip, lap splice, pitch 9.1 mm
- **Type:** circuit + component + assembly
- **Skill:** jitx-circuit-builder, jitx-physical-layout, jitx-code-review
- **Why:** JLCPCB flex assembly is limited to a 240 mm panel side including 5 mm rails, so each board ≤ 230 mm. User decision: two segments, same aspect ratio, soldered lap splice.
- **Changes:**
  - `circuits/led_strip.py`: `DEFAULT_PITCH = 9.1`; `JOINT_COLUMN = 24`, `SEGMENT_A = range(24)`, `SEGMENT_B = range(24, 49)`; `LedStrip(segment=...)` builds only that column range while walking the global chain; crossing hops become splice ports (`splice_hops: list[SpliceHop]`, `splice_ports`, `splice_nets`); `DIN`/`DRET` exist only on the segment holding the chain ends; `Lane`/`lanes()`, `column_x`, `column_edge_x`, `row_y` moved onto the strip.
  - `components/worldsemi_ws2816c.py`: `DataPath` enum (PRIMARY DO→DI, BACKUP BO→BI) and `WS2816C.output(path)` / `input(path)`.
  - New `components/splice_pads.py` `SplicePads`: 20 data PTH pads 0.4/0.9 mm (2 × 2 per row band, x_j ± 1.0, row ± 0.8) and 15 VDD + 15 GND PTH pads 0.6/1.2 mm (3 columns at 1.5 mm, 2 rows in gap lanes / 1 in margin lanes), all derived from the strip's rows and lanes and the overlap. `in_bom = False`, soldered left default: the jitxlib.jlcpcb exporter warns "soldered but not in the bill of materials" and omits it from BOM and CPL (accepted; hand-soldered).
  - `designs/flex_strip.py`: `FlexStrip(segment)`; `FlexStripDesign` base with `Pappalapap` (one piece, not orderable), `FlexSegmentA`, `FlexSegmentB` (assert length ≤ `MAX_ASSEMBLY_LENGTH` 230 mm); layouts `layout/flex_segment_a.json` / `flex_segment_b.json`; no stitching vias in the overlap; spines/tail only on the segment holding that strip end. **TAIL_OFFSET 11.25 → 10.35** (window 10.0 < offset ≤ pitch + 1.25 = 10.35; the lower bound is the fillet and does not depend on the pitch).
  - `scripts/check_zif_mating.py` uses segment A; new `scripts/check_splice.py`; Makefile `BOARDS` = segments A/B, column board, interface board; `make jlcpcb`, `make full-strip`; `make check` runs the splice check and points pyright at the venv; `jlcpcb/` gitignored; `mechanical/geometry.py` constants (PITCH 9.1, COLUMNS 49, TAIL_OFFSET 10.35, JOINT_X, OVERLAP, SEGMENTS).
- **Verification:** builds OK, no warnings: led_strip TestDesign + FullStripDesign, FlexSegmentA, FlexSegmentB, Pappalapap, ColumnBoard (unchanged). `make check` passes (ruff, pyright 0 errors, grep gates hard-fail clean, pin-1 proof, splice proof). Splice proof: 50 pads per side matched 1:1 by position and signal, 50 same-signal pad contacts in the overlap and no others, LED bodies 0.95 mm from the overlap edges, chain 229 (A) + 240 (B) + 10 (splice) = 479 per data path, 235 + 245 = 480 LEDs. JLCPCB exports: A 235 placements (115 top / 120 bottom), B 245 (120 / 125); BOM = WS2816C-2121 C965561 only (2 lines each, the exporter splits designator lists); tail and splice pads excluded.
- **Open:** the brief asked ≥ 1 mm LED-body-to-overlap clearance; 5 mm overlap at 9.1 mm pitch gives 0.95 mm (a 4.8 mm overlap would give 1.05 mm, B = 229.9 mm). The one-piece design's 961 old routes (10 mm pitch) are stale. Margin lanes hold 3 power pads (not 4): 2.25 mm of lane copper fits one row.
- **Status:** done by sub-agent, awaiting orchestrator acceptance.


### [seg-02] JLCPCB flex assembly panels (2026-10-05)
- **Type:** assembly / physical layout · **Skill:** jitx-physical-layout, jitx-substrate-modeler (fab rules), jitx-code-review
- **Changes:** new `designs/flex_panel.py`: `PanelSize.fit` derives the panel from the segment outline and `PANEL_LONG`/`PANEL_SIDES`/`PANEL_MIN_SHORT`/`MIN_RAIL` and asserts the rule; `FlexPanelBoard` = panel minus a 2 mm slot around the segment, tabs placed per straight edge (≤ 30 mm apart, none on lap-zone long edges, splice overlap/end, tail stiffener), 3 mouse bites per tab, 4 tooling holes, 3 fiducials per face (added to the circuit; a Board cannot carry copper); signal area = the segment's. `FlexPanelA` 240 × 105.5, `FlexPanelB` 240 × 70. `FlexStripDesign.make_board`/`apply_layout` hooks; `layout_placements(output=, apply_board_shape=)`; panels read the segment layout files. Makefile: `jlcpcb` exports the panels, `BOARDS` builds both.
- **Verification:** all four flex designs build clean; exports: 240.00 × 105.50 / 240.00 × 70.00, 235 / 245 placements, BOM = C965561 only, NPTH = 75 + 4 / 57 + 4 holes, PTH unchanged; check_splice and check_zif_mating pass; ruff/pyright/grep gates clean. Panel design-info seeded from the segments: all segment object ids preserved.
- **Open:** JLC to confirm the slot inside the 5 mm rail and fiducials 1.5 mm from A's edge; route the panels (or copy segment routing as in STATUS 2a).
- **Status:** done by sub-agent, awaiting acceptance.

### [var-01] One-board 1seg variant alongside the two-segment strip (2026-10-05)
- **Type:** circuit + assembly / physical layout · **Skill:** jitx-circuit-builder, jitx-physical-layout, jitx-code-review
- **Why:** user: a variant with the whole strip on ONE JLC-assemblable board (≤ 230 mm), same 49 × 5 grid, so pitch 230/49 = 4.6939 mm; the two-segment design must stay exactly as is.
- **Changes:**
  - New `pappalapap/variants.py`: frozen `StripVariant` (pitch, columns, rows, joint columns, tail offset/length, data band, tongue margin, trace/clearance, splice overlap, lap columns; asserts loop columns % 3) with `TWO_SEGMENT` and `ONE_SEGMENT`. Replaces `DEFAULT_*`, `JOINT_COLUMN`, `SEGMENT_A/B`, `TAIL_OFFSET`, `TAIL_LENGTH`, `DATA_BAND`, `SPLICE_OVERLAP`, `TONGUE_SIDE_MARGIN`, `DEFAULT_TRACE_WIDTH/CLEARANCE`.
  - `LedStrip(variant, segment)`, `FlexStrip(variant, segment)`, `FlexStripDesign(variant, …)`, `FlexPanelDesign(variant, …)`.
  - `FlexStrip`: GND riser = GND finger span clipped to the spine (≥ `MIN_GND_RISER` 2.4 mm); `Channel`/`UTurnChannel` + `end_channels()`/`entry_channel()` asserted against the variant's rules (U-turns, crossover vias, DIN); narrow-lane stitching (`NARROW_VIA_INSET` 0.45 on the copper centreline); via-to-foreign-pad clearance on both faces; `VIA_DIAMETER` read from the substrate.
  - `flex_panel.PanelSize.fit`: float tolerance, `TOOLING_RAIL` 6 mm on one axis, `PANEL_STEP` 0.5 mm.
  - New `designs/one_segment.py`: `FlexOneSegment`, `FlexOnePanel` (240 × 85.5). Design-info of the panel seeded from the board.
  - `scripts/check_zif_mating.py` covers both tails (`TAILS`); new `scripts/check_strip_fit.py`; `check_splice.py` on the new API. New `mechanical/variants.py` (`MechVariant` per variant; `geometry.py` untouched). Makefile: `ONE_SEG`/`ONE_PANEL` in `BOARDS`, `flex_one_panel` in `make jlcpcb`, `CHECKS` incl. the fit proof.
- **1seg numbers:** strip 230.0 × 23.47 (outline with tail 230.0 × 73.47); data band ±1.0; lanes 1.047 (margins) / 2.694 (gaps) mm per layer; feed lane 2 × 1.047 mm → 2.04 A at 10 °C (internal k; 4.09 A external k) → cap 2.0 A ≈ 32 % of full white, ~54 mΩ / ~0.1 V along the lane; channels top 1.052 (need 0.75 U-turns / 0.9 crossover), bottom 0.752 (need 0.6), DIN 1.052 (need 0.45); hops: least clearance 0.297 mm at 0.15 traces, copper within ±0.703 mm; vias 236 VDD + 237 GND stitching (93 of them in the margin lanes) + 10 tail transition; unlanded pads bottom c0/c1 r0 VDD.
- **Verification:** builds clean: FlexOneSegment, FlexOnePanel, FlexSegmentA/B, FlexPanelA/B, Pappalapap, led_strip TestDesign/FullStripDesign. Two-segment unchanged: design reports of FlexSegmentA/B and FlexPanelA/B byte-identical before/after (JSON and txt), layout `-input.json` snapshots identical, panel A/B re-exports identical (BOM, CPL, order sheet; gerbers differ only in the creation timestamp). `make check` passes (ruff, pyright 0 errors, grep gates hard-fail clean, pin-1 proof 2 tails × 2 boards, splice proof, strip fit proof). Export `jlcpcb/flex_one_panel`: 480 placements (235 top / 245 bottom), BOM C965561 only (3 lines), order sheet 240.00 × 85.50 mm, NPTH 81 + 4, PTH 483.
- **Open:** 1seg routing (tight end channels, crossover via bottom lane 4); two unlanded VDD pads; mechanical pipeline not yet switched to a variant; JLC to confirm the panel as for A/B; user to choose the variant.
- **Status:** done by sub-agent, awaiting acceptance.
