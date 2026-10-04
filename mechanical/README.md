# Mechanical: paper mock-up and Möbius frame

Separate Python environment (no jitx): `uv venv .venv && uv pip install --python .venv/bin/python -r requirements.txt`.
Strip geometry is mirrored from the board design in `geometry.py`. Keep the two in sync.
Current design: **10 mm LED pitch**, 49 columns × 5 rows, strip 490 × 50 mm, loop 480 mm (chosen 2026-10-03 after the shape study below). `MOBIUS_PITCH` overrides it for studies.

| Script | Output |
|---|---|
| `paper_template.py` | `out/paper_template_{letter,a4}.pdf`: 1:1 strip, front (2 pages) + optional back (2 pages) |
| `mobius_shape.py` | `out/mobius_shape.npz`: unstretched Möbius equilibrium (discrete shell; `--refine` continues with trust-region Newton) |
| `orient.py` | rolls and rotates the solved band so the connector tail is at the very bottom, exiting straight down (z = 0); keeps the unoriented solve in `out/mobius_shape_solved.npz` |
| `frame.py` | `out/frame/frame_segment_01..08.stl`, `frame_all.stl` (closed rail with the tail window), `out/mobius_surface.stl` (+ `python -c "import frame; frame.clearance_report()"`) |
| `render.py` | `out/mobius_views.png` |
| `compare_shapes.py` | boundary-curve difference between two solves |

## Frame print notes
- 8 segments, 119 mm each along the rail, each under 120 mm long. PLA/PETG, 0.2 mm layers, tree supports **outside** the slot only.
- Slot is 1.0 mm wide and 3.0 mm deep. The strip edge goes to the bottom of the slot, and the rail covers 2.5 mm of each face (the LED bodies start 3.9 mm in).
- Join segments with a 1.75 mm filament pin through the length-wise channel (about 15 mm per joint), plus a drop of CA glue.
- The rail is a closed loop. Segment 1 has a 24 mm window through the back wall (slot height) where the flex connector tail exits. It's harmless for the paper model. Segment 1 is centred on the window so no joint falls inside it.
- Assembly: thread the closed paper (or flex) band into the segments one at a time, then pin.

Pipeline: `mobius_shape.py` → `orient.py` (balance mode: tail straight down with the centre of mass above it) → `frame.py` → `column.py` → `render.py`.

## Shape study (2026-10-03, coarse 96×8 mesh)
`out/variants.png`. Every result is a true single-twist band (linking number −1, `linking.py`):

| Variant | Size W×D×H mm | Tightest bend | Note |
|---|---|---|---|
| 12.25 mm pitch, organic | 125×173×121 | ~21 mm | original |
| **10 mm pitch, organic** | 123×170×119 | ~25 mm | **chosen** |
| 8.75 mm pitch, organic | 124×166×117 | ~27 mm | |
| 12.25 mm + roundness 0.0003 | 150×154×128 | ~12 mm | rounder, but much more stress |

Roundness ≥ 0.001 and exact 3-fold symmetry (`MOBIUS_SYM=3`) creased (rejected by the solver's 30° hinge check).
For a final shape: coarse solve (`MOBIUS_NU=96 MOBIUS_NV=8`), then `--init-from` on the default fine mesh.

## Column, frame socket and base (`column.py` → `out/column/`)
Cylindrical, one-piece column (2026-10-03). The sculpture floats on it; the column board (`pappalapap/designs/column_board.py`) sits inside in two internal slots, and only two 18 AWG power wires run down to the base.

| File | Part | Size | Print |
|---|---|---|---|
| `column.stl` | Ø33.5 mm cylinder whose top **morphs into a cup that cradles frame segment 1 along the rail's real path** (`cup.py`: signed-distance field + marching cubes; the column's top edge follows the rail's curve and blends into the cup with a 4 mm smooth-min fillet; the rail is glued in with a 0.2 mm gap); the tail passes through a slot in the cup bottom; two internal ribs with slots for the board's 1 mm edge strips (slot tops stop the board); front access window at the ZIF (26 × 18 mm) with two M2 screw tabs; USB-C opening (+x) and mic vents (front) at the XIAO | Ø33.5 × 130 | upright (taper is self-supporting) |
| `hatch_cover.stl` | flush curved cover for the access window, 2 countersunk holes (screws 3.3 mm in from its edges) | 26 × 9.5 × 17 | outside face down, or on edge |
| `board_pusher.stl` | plain rectangular block (20 × 4.6 × 22.2 mm) that stands on the base socket floor under the board and pushes it up against the slot tops; the power wires run down in front of it | 20 × 4.6 × 22.2 | on end |
| `base_body.stl` | Ø100 × 30 shell, 4 mm round-over on the top edge, 6 mm concave fillet collar around the column, column socket, wire pass, Ø8 DC-jack hole, 4 insert posts | Ø100 × 36 (incl. collar) | upside down |
| `base_plate.stl` | bottom disc, 4 × M3 | Ø100 × 3 | flat |
| `assembly.stl`, `assembly_views.png` | everything, plus a cutaway | ~272 mm tall | |

The column diameter comes from the smallest circle around the board's cross-section (component courtyards + heights from the ColumnBoard design report): r 14.25 + 0.5 clearance + 2 mm wall. `column.py` prints an interference check (board and tall-part envelope vs column), currently 0.
Stack-up (z = 0 at the tail exit): rail back wall −4; cup bottom −6 (follows the rail); morph from round to the rail band −46…−8; board top (slot stop) −46.5; ZIF cable stop −49.65; board bottom −112.5; base top −125; base bottom −158. The column axis lies in the strip plane, so the neck is centred. The board's ZIF cable plane is 4.55 mm behind it, and the tail makes a gentle S-bend over the 36 mm taper (it uses 0.35 mm of the 50 mm tail, which the board position compensates for).
Assembly: (1) thread the strip into the rail with the tail out of the window; (2) feed the tail down through the slot in the column's cup and glue frame segment 1 (plain, `out/frame/frame_segment_01.stl`) into the cup; (3) solder the power wires to the board and slide the board up into the slots from below until it stops; (4) through the front hatch, push the tail into the ZIF and close the latch; (5) screw the hatch cover on (2 × M2); (6) drop the board pusher into the column under the board; (7) wires through the base socket to the DC jack, column into the base socket (glue).

### Fasteners (heat-set inserts, 2026-10-03)
| Joint | Insert (in) | Screw | Qty |
|---|---|---|---|
| hatch cover → column tabs | M2 × 3 insert, Ø3.2 × 3.5 hole (column tabs) | M2 × 5 countersunk | 2 |
| column → base | M3 × 5.7 insert, Ø4.0 × 6 hole in 3 bosses inside the column's bottom end | M3 × 6 countersunk, from inside the base up through the socket floor | 3 |
| base plate → base | M3 × 5.7 insert in each post | M3 × 6 countersunk, flush under the plate | 4 |

The column's bottom bosses sit outside the space the board sweeps through as it slides in from below. `column.py` checks that ("board insertion sweep vs column: 0").

## Regenerating
From the project root: `make mech` rebuilds every file in `mechanical/out/` from the committed solved shape
(`mechanical/data/mobius_shape_10mm.npz`). `make solve` re-solves the shape (~30 min) and updates that file.
