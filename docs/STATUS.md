# pappalapap: project status and handoff (as of 2026-10-03 evening)

A scrolling-text LED sculpture. A two-sided flex PCB of addressable LEDs, closed into a
**Möbius strip**, floats on a hollow **column** that holds the controller board, standing on
a small **base**. The text is "PAPPALAPAP" in a 3×5 font. Read this first, then `PLAN.md`
(task history and acceptance records) and `ARCHITECTURE.md` (electrical architecture).

## 1. Hard rules (from the user)
- Flex strip length ≤ **490 mm** (JLCPCB flex limit). Currently exactly 490.0 mm.
  JLC adds 5 mm panel rails, so confirm a 490 mm FPC with JLC (or shrink to 480) before ordering.
- **Loop columns** = 2 × (strip columns − 1) must be divisible by **3**. Currently 96.
- Clean up JITX processes you start (viewers, extra runtimes). Stop the runtime with
  `jitx runtime stop` when work ends. Per-design `interactive-client` processes respawn and
  belong to the runtime; don't kill them individually.
- Ask before big structural changes; the user makes the aesthetic and product calls.

## 2. Current design (all decided with the user)
| Item | Value |
|---|---|
| LED | Worldsemi WS2816C-2121 (LCSC C965561), 16-bit RGB, 5 V, dual data (DI/BI, DO/BO) |
| Pitch / grid | **10.0 mm**, 49 strip columns × 5 rows, strip 490 × 50 mm |
| Faces | LEDs on both faces, aligned back to back: top cols 1..47 (235), bottom cols 0..48 (245), **480 LEDs** |
| Möbius joint | one-pitch (10 mm) lap; the top faces glue together (insulated, non-conductive adhesive); the outer lap faces show bottom cols 0 and 48 at full pitch, so the seam is seamless |
| Loop | 96 columns around = 24 characters (4 cols/char) |
| Chain | one row-major serpentine: top rows 0→4 (even rows A→B), crossover at end B (top c47 r4 → via → bottom c48 r4), bottom rows 4→0; ends at bottom c0 r0 (end A). Last DO = DRET back to the connector |
| Power | 6 horizontal lanes alternating VDD/GND on both layers (14.7 mm per net per layer), GND spine at end A, VDD spine at end B, 600 stitching vias. Full white ≈ 5.5 A, so a **firmware brightness cap is mandatory** |
| Flex tail | 16 positions at 1.0 mm, **50 mm long** (straight drop through the column's tapered neck into the column board's ZIF), fingers on the **bottom** copper, 0.2 mm PI stiffener on top. Pinout: 1–7 VDD, 8 DRET, 9 DIN, 10–16 GND. Flex outline 490 × 100 mm |
| ZIF | XFCN F1002-B-16-20T-R (LCSC C481251), 1 A/contact, bottom contact |
| Controller | Seeed **XIAO ESP32S3 Sense, soldered flat** (castellated), camera not fitted (mic only). DIN = D0/GPIO1 via 74AHCT1G125 + 33 Ω; DRET = D1/GPIO2 via 10k/20k divider |
| Speech detection plan | ESP-SR VADNet or WebRTC VAD on the S3 (firmware not started) |
| Flex substrate | custom JLC 2-layer FPC, 1 oz, 0.2 mm, coverlay (`pappalapap/substrate.py`) |
| Rigid substrate | custom JLC 2-layer 1.6 mm FR-4 (`pappalapap/substrate_rigid.py`) |

## 3. Boards (JITX Python, package `pappalapap/`)
| Design | Build target | Status |
|---|---|---|
| Flex strip | `pappalapap.designs.flex_strip.Pappalapap` (`main.py` re-exports it) | placed, pours/vias done. The user autorouted the **top layer only**; the bottom layer (245 LEDs, U-turns, DIN/DRET) still needs routing. Report shows 961 routes captured |
| Column board (current controller) | `pappalapap.designs.column_board.ColumnBoard` | 24 × 66 mm, placed, unrouted. ZIF at the top edge, USB-C flush right, 18 AWG wire pads at the bottom, 1 mm groove strips on the long edges |
| Interface board (superseded flat base board) | `pappalapap.designs.interface_board.InterfaceBoard` | 56 × 42 mm, placed, unrouted. Kept building; shares `circuits/interface.py` |

Key code: `circuits/led_strip.py` (parametric LED grid + chain), `circuits/interface.py`
(XiaoInterface, parameterised by XIAO type / power input / placement), `components/*`
(each with a TestDesign), `designs/layout_placements.py` (copied from ~/socialbadge-ai).

**Pin-1 safety proof (run it after any tail/ZIF/placement change):**
`python scripts/check_zif_mating.py`. It proves tail finger k lands on ZIF contact k with
matching nets on both rigid boards; a mirror would swap 5 V and GND at 5 A.

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
- `design-report-pappalapap.designs.<Design>.{json,txt}` in the project root, written by
  `python scripts/design_report.py <module.path.Design>` (copied from ~/socialbadge-ai). These
  are the **full** design: components, pads, courtyards, nets, vias, pours, routes, stackup,
  rules. Regenerate after every change.
- `layout/<design>-input.json`: placements-only round-trip file written on every build by
  `layout_placements()`. An edited `layout/<design>.json` is read back in.

## 6. Open items / next steps
1. Route the flex **bottom layer** (include both layers in the autorouter), then the column board (DIN/DRET cross once → one via).
2. Confirm with JLC: 490 mm FPC + rails, double-sided FPC assembly, the 0.2 mm PI stiffener on the tail (set manually when ordering).
3. Buy/verify: panel-mount 5.5×2.1 DC jack ≥ 6 A (Ø8 hole), 5 V 6 A supply, 18 AWG wire, XIAO ESP32S3 Sense.
4. Firmware: WS2816 16-bit driver (RMT + DMA), Möbius ring mapping (row-major chain → 96-column virtual ring with the row flip across the half-twist), brightness cap, VAD trigger, WiFi text update.
5. Check on real parts: ZIF cable height (assumed 0.9 mm above the board, `column.py`), column fit, USB-C slot.
6. Optional: 470 µF 8 mm bulk cap to slim the column board; heavier base.

## 7. Gotchas learned
- The JITX autorouter only routes the selected/active layer; select both layers.
- `jitx ui open` is single-instance: close the viewer before opening another design.
- Builds that rename instances prompt interactively; agents used `yes Y | jitx build …`.
- jitxlib's `PolarizedMoldedTwoPin` marks the anode; `components/molded_diode.py` puts the dot on the cathode.
- `jitxlib-parts` 2.x is a dependency; passives come from `parts/jlc-basic-passives.csv` (JLC Basic, verified in stock).

## 8. Repository and regeneration (git, `Makefile`)
- Committed: sources, docs, datasheets, `parts/`, `mechanical/data/*.npz` (the solved shape, about 30 min to recompute), and JITX `designs/**/design-info/` (editor state such as routing). That follows the JITX `.gitignore` convention.
- Gitignored and regenerated by `make`: `designs/**/cache`, design-info backups, `design-report-*.{json,txt}`, `layout/*-input.json`, `mechanical/out/`.
- `make check` (lint, types, grep gates, pin-1 proof) · `make boards` · `make reports` · `make mech` · `make solve` · `make all`.
