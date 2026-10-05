# pappalapap: project status and handoff (as of 2026-10-05)

A scrolling-text LED sculpture. A two-sided flex PCB of addressable LEDs, closed into a
**Möbius strip**, floats on a hollow **column** that holds the controller board, standing on
a small **base**. The text is "PAPPALAPAP" in a 3×5 font. Read this first, then `PLAN.md`
(task history and acceptance records) and `ARCHITECTURE.md` (electrical architecture).

## 1. Hard rules (from the user)
- **JLC flex assembly: panel side ≤ 240 mm including 5 mm rails on all sides, so each
  assembled flex board ≤ 230 mm** (2026-10-05). The strip (445.9 mm) is therefore two
  boards, segment A 220.9 mm and segment B 230.0 mm, soldered in a lap splice. The
  segment designs assert ≤ 230 mm. (Whole strip still ≤ 490 mm.) Full panel rule
  (2026-10-05): one panel side exactly 79, 119 or 240 mm, the other ≥ 70 mm, ≤ 240 mm,
  rails ≥ 5 mm on all four sides; asserted by `designs/flex_panel.py` `PanelSize`.
- **Loop columns** = 2 × (strip columns − 1) must be divisible by **3**. Currently 96.
- Clean up JITX processes you start (viewers, extra runtimes). Stop the runtime with
  `jitx runtime stop` when work ends. Per-design `interactive-client` processes respawn and
  belong to the runtime; don't kill them individually.
- Ask before big structural changes; the user makes the aesthetic and product calls.

## 2. Current design (all decided with the user)
| Item | Value |
|---|---|
| LED | Worldsemi WS2816C-2121 (LCSC C965561), 16-bit RGB, 5 V, dual data (DI/BI, DO/BO) |
| Pitch / grid | **9.1 mm** (2026-10-05, was 10.0), 49 strip columns × 5 rows, strip 445.9 × 45.5 mm |
| Segments | **A** = cols 0..23 (tail, GND spine, DIN/DRET, end-A U-turns), board 0..220.9 mm from end A; **B** = cols 24..48 (VDD spine, crossover, end-B U-turns), board 215.9..445.9 mm. 5 mm overlap centred on the joint at 218.4 mm; B lies on A (A top face to B bottom face) |
| Splice | same plated-hole field on both boards (`components/splice_pads.py`): 20 data pads 0.4/0.9 mm (top/bottom DO→DI and BO→BI per row, 2 × 2 in each ±2 mm row band) + 15 VDD + 15 GND pads 0.6/1.2 mm in the six lanes; hand-soldered through the stacked holes. Power crosses into B only here. Proof: `scripts/check_splice.py` |
| Faces | LEDs on both faces, aligned back to back: top cols 1..47 (235), bottom cols 0..48 (245), **480 LEDs** |
| Möbius joint | one-pitch (9.1 mm) lap; the top faces glue together (insulated, non-conductive adhesive); the outer lap faces show bottom cols 0 and 48 at full pitch, so the seam is seamless |
| Loop | 96 columns around = 24 characters (4 cols/char) |
| Chain | one row-major serpentine: top rows 0→4 (even rows A→B), crossover at end B (top c47 r4 → via → bottom c48 r4), bottom rows 4→0; ends at bottom c0 r0 (end A). Last DO = DRET back to the connector |
| Power | 6 horizontal lanes alternating VDD/GND on both layers (12.45 mm per net per layer), GND spine at end A, VDD spine at end B, stitching vias (none in the splice overlap). Full white ≈ 5.5 A, so a **firmware brightness cap is mandatory** |
| Flex tail | 16 positions at 1.0 mm, **50 mm long** (straight drop through the column's tapered neck into the column board's ZIF), fingers on the **bottom** copper, 0.2 mm PI stiffener on top. Pinout: 1–7 VDD, 8 DRET, 9 DIN, 10–16 GND. Tail centre 10.35 mm from end A (was 11.25). Segment A outline 220.9 × 95.5 mm |
| ZIF | XFCN F1002-B-16-20T-R (LCSC C481251), 1 A/contact, bottom contact |
| Controller | Seeed **XIAO ESP32S3 Sense, soldered flat** (castellated), camera not fitted (mic only). DIN = D0/GPIO1 via 74AHCT1G125 + 33 Ω; DRET = D1/GPIO2 via 10k/20k divider |
| Speech detection plan | ESP-SR VADNet or WebRTC VAD on the S3 (firmware not started) |
| Flex substrate | custom JLC 2-layer FPC, 1 oz, 0.2 mm, coverlay (`pappalapap/substrate.py`) |
| Rigid substrate | custom JLC 2-layer 1.6 mm FR-4 (`pappalapap/substrate_rigid.py`) |
| **Variant "1seg"** (2026-10-05, alongside the above) | same 49 × 5 grid / 480 LEDs / 96 loop columns / laps / chain / tail, pitch **230/49 = 4.6939 mm**, strip **230.0 × 23.47 mm on ONE board**, no splice (`ONE_SEGMENT` in `pappalapap/variants.py`, designs in `designs/one_segment.py`). Data band ±1.0 mm, trace/clearance 0.15/0.15, pad-wide tongues. Power lanes 2.69 mm between rows, 1.05 mm margins per layer; the VDD bottom-margin lane carries the whole load at end A → **firmware cap 2.0 A total (~32 % of full white)** (IPC-2221, 10 °C, internal k for coverlaid flex). Tail at 10.35 mm, GND riser clipped to the 4.69 mm spine (2.84 mm, 10 vias), DIN rises through the 1.05 mm channel between spine and top col 1 |

## 3. Boards (JITX Python, package `pappalapap/`)
| Design | Build target | Status |
|---|---|---|
| Flex segment A (build/view; ordered as panel A) | `pappalapap.designs.flex_strip.FlexSegmentA` | 220.9 × 45.5 mm + 50 mm tail, 235 LEDs, splice pads; placed, pours/vias done, unrouted. Layout file `layout/flex_segment_a.json` |
| Flex segment B (build/view; ordered as panel B) | `pappalapap.designs.flex_strip.FlexSegmentB` | 230.0 × 45.5 mm, 245 LEDs, splice pads; placed, pours/vias done, unrouted. Layout file `layout/flex_segment_b.json` |
| **Flex panel A (what is ordered)** | `pappalapap.designs.flex_panel.FlexPanelA` | segment A unchanged on a 240 × 105.5 mm panel (rails 9.55 ends / 5.0 top+bottom, bottom rail measured from the tail end; the area beside the tail is panel material). 2 mm slot, 25 tabs × 3 mm with 3 mouse bites each (NPTH 0.5 @ 0.9), 3 fiducials per face, 4 tooling holes Ø2 |
| **Flex panel B (what is ordered)** | `pappalapap.designs.flex_panel.FlexPanelB` | segment B unchanged on a 240 × 70 mm panel (rails 5.0 ends / 12.25 top+bottom), 19 tabs, same rail features |
| Flex one-board strip, 1seg (build/view) | `pappalapap.designs.one_segment.FlexOneSegment` | 230.0 × 23.47 mm + 50 mm tail (outline 230.0 × 73.47), 480 LEDs (235 top / 245 bottom), 483 vias, 9 pours; placed, pours/vias done, unrouted. Layout file `layout/flex_one_segment.json` |
| **Flex one-board panel, 1seg (what is ordered for that variant)** | `pappalapap.designs.one_segment.FlexOnePanel` | the board on a **240 × 85.5 mm** panel (rails 5.0 ends / 6.02 top+bottom: the corner tooling holes need 6 mm on one axis), 27 tabs × 3 mouse bites, 3 fiducials per face, 4 tooling holes. Design-info seeded from `FlexOneSegment` |
| Flex strip, one piece (reference only, **not orderable**) | `pappalapap.designs.flex_strip.Pappalapap` (`main.py` re-exports it) | builds; still carries the user's 961 top-layer routes from the 10 mm pitch, now stale |
| Column board (current controller) | `pappalapap.designs.column_board.ColumnBoard` | 24 × 66 mm, placed, unrouted. ZIF at the top edge, USB-C flush right, 18 AWG wire pads at the bottom, 1 mm groove strips on the long edges |
| Interface board (superseded flat base board) | `pappalapap.designs.interface_board.InterfaceBoard` | 56 × 42 mm, placed, unrouted. Kept building; shares `circuits/interface.py` |

Key code: `variants.py` (`StripVariant`: `TWO_SEGMENT`, `ONE_SEGMENT`; every geometry knob of the strip), `circuits/led_strip.py` (parametric LED grid + chain, column-range segments with splice ports), `components/splice_pads.py`, `designs/flex_strip.py` (`FlexStrip(segment)`), `designs/flex_panel.py` (JLC panels), `circuits/interface.py`
(XiaoInterface, parameterised by XIAO type / power input / placement), `components/*`
(each with a TestDesign), `designs/layout_placements.py` (copied from ~/socialbadge-ai).

**Pin-1 safety proof (run it after any tail/ZIF/placement change):**
`python scripts/check_zif_mating.py`. It proves tail finger k lands on ZIF contact k with
matching nets on both rigid boards, for every tail (two-segment A and the 1seg board); a mirror would swap 5 V and GND at 5 A.

**Strip fit proof (run it after any variant/strip/copper change):** `python scripts/check_strip_fit.py`.
Per variant: every in-row hop routes as two straight traces within the data band at the
variant's rules, U-turn/crossover/DIN channels are wide enough, lane widths and the
current capacity of the VDD feed lane, board ≤ 230 mm and panel rule, and
`mechanical/variants.py` matches `pappalapap/variants.py`.

**Splice proof (run it after any strip/segment/splice change):** `python scripts/check_splice.py`.
Every splice pad of A matches one of B by position and signal, nothing else touches in the
overlap, and A + splice + B is the one-piece chain (480 LEDs, 479 + 479 hops).

## 4. Mechanical (`mechanical/`, separate venv `mechanical/.venv`, no jitx)
Pipeline: `mobius_shape.py` → `orient.py` → `frame.py` → `column.py` → `render.py`.
- `geometry.py` mirrors the board geometry (pitch, tail offset/length) and **asserts the two
  hard rules**. Keep it in sync with the JITX design.
- `mobius_shape.py`: discrete-shell solver for an inextensible Möbius band (stiff edges plus
  2(1−cos θ) hinge bending; it refuses creased results over 30°). Coarse first
  (`MOBIUS_NU=96 MOBIUS_NV=8`), then `--init-from` on the fine mesh. `--finalize-progress`
  accepts a time-capped snapshot. Shape study: README "Shape study" and `out/variants.png`.
  The natural "organic" shape was chosen; roundness and 3-fold symmetry terms crease.
- `orient.py`: **balance mode** (default). Slides the tail (rolling is free) to the edge
  point where the centre of mass sits above the tail (3.2° off axis), tail straight down at
  the origin, strip +x = world +x.
- `frame.py`: closed slotted edge rail (1.0 mm slot, 2.5 mm lip), 8 segments of ~120 mm,
  pin channel for 1.75 mm filament, tail window in segment 1.
- `column.py`: **cylindrical one-piece column** Ø33.5 mm (smallest circle around the board +
  clearance + wall) whose top **morphs into a cup that cradles frame segment 1 along the rail's real path**
  (`cup.py`, SDF + marching cubes; the rail is glued in). The tail S-bends 4.55 mm inside the column to reach the ZIF. A **front access hatch**
  (26 × 18 mm, flush cover, 2 × M2) gives access to plug the tail into the ZIF.  The board slides into two internal slots (the slot tops
  are its stop; a printed rectangular board pusher holds it from below). Round base Ø100 × 30 with a 4 mm top round-over, a 6 mm fillet collar around the column, and a
  DC-jack hole. Heat-set inserts everywhere (see the mechanical README). Overall height about 272 mm. Interference check prints 0. Renders + cutaway:
  `out/column/assembly_views.png`.
- `paper_template.py`: 1:1 printable strip (letter/A4), front + optional back.
- `linking.py`: topology check (linking number −1 = true single-twist Möbius band).

## 5. Exports for other tools
- `make jlcpcb` writes `jlcpcb/<board>/` (gerbers, BOM, CPL, order notes) for every
  orderable board via `jitx design export jlcpcb <design> --output jlcpcb/<name> --overwrite`.
  The flex packets are the **panels** (`jlcpcb/flex_panel_a`, `flex_panel_b`; order sheet
  240 × 105.5 and 240 × 70; 1seg: `jlcpcb/flex_one_panel`, 240 × 85.5, 480 placements
  235 top / 245 bottom, BOM C965561 only, NPTH 81 mouse bites + 4 tooling, PTH 483 vias); the bare segments are build/view targets only. Panel NPTH
  file: mouse bites (0.5) + tooling holes (2.0); fiducials are netless copper + mask
  openings, not components, so not in BOM/CPL. Order as "panel by customer", 1 design.
  Flex BOMs list only WS2816C-2121 (C965561); the tail fingers and splice pads are
  board copper and are omitted (the exporter warns that the splice pads are "soldered but
  not in the BOM": intended, they are hand-soldered). Placements are on both sides.
  The order sheet's surface finish defaults to HASL: set ENIG on the form.
- `design-report-pappalapap.designs.<Design>.{json,txt}` in the project root, written by
  `python scripts/design_report.py <module.path.Design>` (copied from ~/socialbadge-ai). These
  are the **full** design: components, pads, courtyards, nets, vias, pours, routes, stackup,
  rules. Regenerate after every change.
- `layout/<design>-input.json`: placements-only round-trip file written on every build by
  `layout_placements()`. An edited `layout/<design>.json` is read back in.

## 6. Open items / next steps
1. Route the flex **bottom layer** (include both layers in the autorouter), then the column board (DIN/DRET cross once → one via).
2. Confirm with JLC: double-sided FPC assembly on the customer panels (`FlexPanelA/B`): whether their 5 mm rail may include our 2 mm slot (A's long sides and B's ends keep only 3 mm solid; A's fiducials sit 1.5 mm from the panel edge), mouse-bite tabs on polyimide, the 0.2 mm PI stiffener on the tail (set manually when ordering), ENIG.
2a. Route the **panel designs** `FlexPanelA/B` (what is exported; same circuit and coordinates as the segments; their design-info was seeded from the segments' so the object ids match). To carry routing done on a segment instead, copy its `design-info/physical-layout.design` into the panel's before building (ids verified identical; replay not yet tried with real routes). Route both segments (data traces to the splice pads: top-face hops on the −x pad column, bottom-face hops on the +x column). Clear the stale 10 mm routes from the one-piece design. Splice assembly: align the stacked holes (pins through two power holes help), solder every hole from B's top side.
2b. LED body to splice-overlap edge is 0.95 mm (brief asked ≥ 1 mm); a 4.8 mm overlap would give 1.05 mm.
3. Buy/verify: panel-mount 5.5×2.1 DC jack ≥ 6 A (Ø8 hole), 5 V 6 A supply, 18 AWG wire, XIAO ESP32S3 Sense.
4. Firmware: WS2816 16-bit driver (RMT + DMA), Möbius ring mapping (row-major chain → 96-column virtual ring with the row flip across the half-twist), brightness cap, VAD trigger, WiFi text update.
5. Check on real parts: ZIF cable height (assumed 0.9 mm above the board, `column.py`), column fit, USB-C slot.
6. Optional: 470 µF 8 mm bulk cap to slim the column board; heavier base.
7. **1seg variant** (if chosen): route it (bottom U-turns at both ends have a 0.75 mm channel: 2 × 0.15 traces + 0.15 spaces; the end-B crossover's two vias go in the 1.05 mm top channel between col 47 and the VDD spine, and their bottom traces reach col 48's inputs on its end-B side by crossing VDD lane 4, re-fed by the spine's stitching vias); bottom c0 and c1 row-0 VDD pads are unlanded (DRET channel keepout) and need a ≤ 0.5 mm neck-down stub to the VDD riser; wire `mechanical/variants.py` into the mechanical pipeline; brightness cap 2.0 A in firmware; decide 2-seg vs 1seg with the user (1seg: half the size, no splice, one order, but ~2 A cap and tighter routing).

## 7. Gotchas learned
- The JITX autorouter only routes the selected/active layer; select both layers.
- A JITX `Board` translates only non-copper features (cutouts, mask...): copper on a Board fails ("Unhandled feature type OverlappableCopper"), so panel fiducial copper goes in the circuit. A board shape with holes becomes outline + cutouts; the signal area must be given explicitly or the router sees the outer boundary.
- `jitx ui open` is single-instance: close the viewer before opening another design.
- Builds that rename instances prompt interactively; agents used `yes Y | jitx build …`.
- jitxlib's `PolarizedMoldedTwoPin` marks the anode; `components/molded_diode.py` puts the dot on the cathode.
- `jitxlib-parts` 2.x is a dependency; passives come from `parts/jlc-basic-passives.csv` (JLC Basic, verified in stock).

## 8. Repository and regeneration (git, `Makefile`)
- Gitignored as well: `jlcpcb/` (export packets).
- Committed: sources, docs, datasheets, `parts/`, `mechanical/data/*.npz` (the solved shape, about 30 min to recompute), and JITX `designs/**/design-info/` (editor state such as routing). That follows the JITX `.gitignore` convention.
- Gitignored and regenerated by `make`: `designs/**/cache`, design-info backups, `design-report-*.{json,txt}`, `layout/*-input.json`, `mechanical/out/`.
- `make check` (lint, types, grep gates, pin-1 proof, splice proof, strip fit proof) · `make jlcpcb` · `make full-strip` · `make boards` · `make reports` · `make mech` · `make solve` · `make all`.
