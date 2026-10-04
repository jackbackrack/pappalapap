# pappalapap

Möbius-strip LED sculpture: a two-sided WS2816C flex PCB (490 × 50 mm, 480 LEDs) on a
3D-printed rail frame, floating on a column that holds a XIAO ESP32S3 controller board.
JITX Python project (package `pappalapap/`) plus a mechanical toolchain (`mechanical/`).

**Start by reading `docs/STATUS.md`** (current state, decisions, open items), then `PLAN.md`
and `ARCHITECTURE.md`.

## Rules
- Flex strip ≤ 490 mm long; loop columns 2 × (strip columns − 1) divisible by 3.
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
jitx build pappalapap.designs.flex_strip.Pappalapap
jitx build pappalapap.designs.column_board.ColumnBoard
python scripts/grep_gates.py pappalapap/ && ruff check pappalapap/ && pyright pappalapap/
mechanical/.venv/bin/python mechanical/<script>.py   # see mechanical/README.md
```
