# Project Plan: pappalapap

Workflow tier: **complete-board**. See ARCHITECTURE.md for geometry, power, chain order and pinout.

> **2026-10-03, pitch change:** after the Möbius shape study (`mechanical/`), the user changed the LED pitch from 12.25 mm to **10.0 mm** (5 rows, 490 mm strip kept). The strip is now 490 x 50 mm with 49 column positions; top face cols 1..47 (235 LEDs), bottom face cols 0..48 (245 LEDs), 480 LEDs total; lap 10 mm, loop 480 mm, 96-column ring = 24 characters; ~5.5 A full white, ~29 ms frame (~34 fps). Task history below keeps the numbers each task was accepted with; follow-up notes dated 2026-10-03 (pitch change) give the current values.

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
