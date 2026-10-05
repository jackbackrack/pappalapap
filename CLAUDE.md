# pappalapap

Möbius-strip LED sculpture: a two-sided WS2816C flex PCB strip (445.9 × 45.5 mm, 9.1 mm pitch,
480 LEDs) made of **two flex segments joined by a soldered lap splice** (JLCPCB can't assemble
flex longer than 240 mm per panel), on a 3D-printed rail frame. The XIAO ESP32S3 controller
board (column board) is meant to sit in a column; the column/base mechanics are on hold.
JITX Python project (package `pappalapap/`) plus a mechanical toolchain (`mechanical/`).

**Start by reading `docs/STATUS.md`** (current state, decisions, open items), then `PLAN.md`
and `ARCHITECTURE.md`.

## Rules
- Each flex segment board ≤ 230 mm long (JLC flex assembly: panel side 79/119/240 mm incl. ≥5 mm rails).
  Loop columns 2 × (strip columns − 1) divisible by 3. After splice changes run `python scripts/check_splice.py`;
  after strip geometry changes run `python scripts/check_strip_fit.py` (both run in `make check`).
- Two strip variants live side by side (`pappalapap/variants.py`): `TWO_SEGMENT` (9.1 mm pitch,
  FlexPanelA/B) and `ONE_SEGMENT` (4.69 mm, FlexOnePanel). Route and export the *panel* designs.
- After any tail/ZIF/placement change run `python scripts/check_zif_mating.py` (pin-1
  proof: a mirror swaps 5 V and GND at 5 A).
- Regenerate `design-report-*.json` with `python scripts/design_report.py <module.Design>`
  after design changes. That full JSON is what the user hands to other tools.
- Clean up JITX processes you start; `jitx runtime stop` at the end. Don't run two builds
  of the same design at once.
- Keep `mechanical/geometry.py` in sync with the board geometry.

## Commands
`make all` regenerates everything (see Makefile); `make mech` covers the mechanical side only.
```
source .venv/bin/activate
jitx runtime status            # start: jitx runtime start --background
jitx build pappalapap.designs.flex_strip.FlexSegmentA   # and FlexSegmentB
jitx build pappalapap.designs.column_board.ColumnBoard
python scripts/grep_gates.py pappalapap/ && ruff check pappalapap/ && pyright pappalapap/
mechanical/.venv/bin/python mechanical/<script>.py   # see mechanical/README.md
```
