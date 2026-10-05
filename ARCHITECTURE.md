# Architecture: pappalapap

A 445.9 mm two-sided flex strip of WS2816C-2121 addressable LEDs, made as two flex
boards soldered together in a lap splice and joined into a Möbius strip, scrolling
"PAPPALAPAP" in a 3x5 font. A separate controller board (or an
off-the-shelf MCU plus a breakout) drives it through a ZIF connector.

## Display Geometry

**Design rules (user, 2026-10-03; assembly limit 2026-10-05):** each flex board JLCPCB assembles must be
≤ 230 mm long (240 mm panel side including 5 mm rails), hence two segments (below); the whole strip
stays ≤ 490 mm. The number of
**loop columns**, 2 × (strip columns − 1), i.e. LED columns met going once round the Möbius surface,
must be divisible by 3. Current: 49 strip columns → 96 loop columns = 3 × 32 = 24 characters × 4.

| Parameter | Value | Notes |
|---|---|---|
| Strip length (flat) | 445.9 mm | 49 × 9.1; two boards (segments A and B, below) |
| LED pitch (x and y) | 9.1 mm | 2026-10-05, same 49 × 5 grid and aspect ratio (was 10.0 mm from 2026-10-03, 12.25 mm before) |
| Rows | 5 | 3x5 font |
| Strip height | 45.5 mm | 5 x pitch; half a pitch of margin above and below the outer rows |
| Möbius lap overlap | 9.1 mm (one pitch) | loop circumference = 436.8 mm = 48 pitches |
| Column centers | x = (k + 0.5) * 9.1, k = 0..48 | y = (r + 0.5) * 9.1, r = 0..4 |
| Top-face columns | k = 1..47 (47 cols, 235 LEDs) | top face is hidden inside both lap zones |
| Bottom-face columns | k = 0..48 (49 cols, 245 LEDs) | |
| Total LEDs | 480 | |
| Visible loop | 96 columns = 2 x 48 | constant pitch all the way round, seam included; 24 characters at 4 columns each (3x5 glyph + 1 space) |

### Why the seam is seamless

On a Möbius strip, end A's top face continues into end B's bottom face, with the
width mirrored (y -> H - y). For a lap joint of one pitch:

- The two **top** faces of the lap zones (x in [0, 9.1] and [436.8, 445.9]) face each
  other and are hidden. They carry no LEDs; that's where the bond goes.
- The two **bottom** faces of the lap zones face outward. Each has one LED column,
  column 0 and column 48, sitting exactly one pitch from its neighbors on the loop.
- The 5 rows are symmetric about the centerline, so the y-mirror maps row r -> 4 - r
  and the grid stays aligned. The firmware handles the row flip and column mapping.

### Lap joint is insulated (power ring dropped 2026-10-03)

With row-major lanes, each net gets about 14.7 mm of copper per layer (see Power
Tree), so a one-ended feed already drops only tens of mV and the ring isn't
needed. The lap-zone top faces carry the power **spines**: GND at end A, VDD at
end B. In the lap these face each other, so **the joint must stay insulated**:
keep the coverlay closed over the lap zones and bond with non-conductive adhesive
or tape. (If a ring is ever wanted, matching VDD/GND islands can be added
symmetrically about the centerline; see the cir-01 notes.)

## Segments and splice (2026-10-05)

JLCPCB cannot assemble a flex board longer than a 240 mm panel side (5 mm rails on all
sides), so each board is ≤ 230 mm. The strip is two boards, keeping the one-piece chain:

| | Segment A (`FlexSegmentA`) | Segment B (`FlexSegmentB`) |
|---|---|---|
| Columns | 0..23 (`SEGMENT_A`) | 24..48 (`SEGMENT_B`) |
| Board x from end A | 0 .. 220.9 mm (+ 50 mm tail in y) | 215.9 .. 445.9 mm |
| Length | 220.9 mm | 230.0 mm |
| LEDs | 235 (115 top, 120 bottom) | 245 (120 top, 125 bottom) |
| Carries | tail, GND spine, DIN/DRET entries, end-A U-turns | VDD spine, top→bottom crossover, end-B U-turns |

- **Joint:** the column gap x_j = 24 × 9.1 = 218.4 mm from end A. The boards overlap
  by 5 mm centred on it. B lies on top of A with no twist: A's TOP face meets B's
  BOTTOM face. LED bodies stay 0.95 mm clear of the overlap edges.
- **Splice pads** (`components/splice_pads.py`, the same field on both boards at the
  same strip (x, y)): plated through-holes, soldered through the stacked holes after
  assembly, so both copper layers of both boards reach every joint.
  - 20 data pads, 0.4 / 0.9 mm (hole / pad): per row the top-face DO→DI and BO→BI hops
    at x_j − 1.0 and the bottom-face hops at x_j + 1.0, DO→DI at row − 0.8 mm, BO→BI
    at row + 0.8 mm; inside the ±2 mm row data band (0.75 mm to the lanes).
  - 15 VDD + 15 GND pads, 0.6 / 1.2 mm, in the six power lanes on the lane's net: 3
    columns at x_j − 1.5, x_j, x_j + 1.5, 2 rows (±1.0 mm) in the 5.1 mm gap lanes,
    1 row in the 2.25 mm margin lanes.
- **Power** still enters only through A's tail and crosses the splice into B (B's 245
  LEDs draw at most ~2.8 A full white). The lanes run through the joint on both layers.
- `scripts/check_splice.py` proves the pads match 1:1 by position and signal, nothing
  else touches in the overlap, and A + splice + B reproduce the one-piece chain (480
  LEDs, 479 + 479 hops: 229 in A, 240 in B, 10 through the splice per data path).
- The one-piece `Pappalapap` design still builds, for reference only (not orderable).

## Variants (2026-10-05)

The strip geometry is a parameter, not module constants: a frozen `StripVariant`
(`pappalapap/variants.py`: pitch, columns, rows, joint columns, tail offset/length,
data band, tongue margin, trace/clearance rules, splice overlap, lap columns) feeds
`LedStrip`, `FlexStrip`, `FlexStripDesign` and `FlexPanelDesign`. No string keys; two
instances, same code:

| | `TWO_SEGMENT` (above) | `ONE_SEGMENT` ("1seg") |
|---|---|---|
| Designs | `flex_strip.FlexSegmentA/B`, `flex_panel.FlexPanelA/B` | `one_segment.FlexOneSegment`, `one_segment.FlexOnePanel` |
| Pitch / strip | 9.1 mm, 445.9 × 45.5 mm | 230/49 = 4.6939 mm, 230.0 × 23.47 mm |
| Boards | 2 (220.9 + 230.0 mm), splice | 1 (230.0 mm), no splice |
| Data band / rules | ±2.0 mm, 0.2/0.2 mm | ±1.0 mm (pads ±0.79 + 0.15), 0.15/0.15 mm |
| Lanes per layer (margin / gap) | 2.25 / 5.1 mm | 1.05 / 2.69 mm |
| Feed-lane current, 10 °C | 3.6 A | 2.0 A → firmware cap 2.0 A (~32 % white) |
| End channels top / bottom | 2.76 / 2.46 mm | 1.05 / 0.75 mm (need 0.75–0.9 / 0.6) |
| Tail offset, GND riser | 10.35 mm, 7.25 mm | 10.35 mm, 2.84 mm (clipped to the spine) |
| Panel | 240 × 105.5, 240 × 70 | 240 × 85.5 |

Rules added for 1seg are general and leave the two-segment outputs byte-identical
(design reports, layout snapshots, gerbers/BOM/CPL compared): the tail's GND riser is
the GND finger span clipped to the spine (≥ 2.4 mm asserted; at 9.1 mm the span already
ends on the spine edge); asserted U-turn, crossover and DIN channels; lanes narrower
than 1.2 mm are stitched on their copper centreline (0.45 mm inset); stitching vias
keep the clearance rule to every other-net LED pad on both faces; `PanelSize.fit` grows
the top/bottom rails to 6 mm when the end rails cannot hold the tooling holes and rounds
the panel to 0.5 mm. Note on power for both variants: the VDD lanes join only at the end-B
spine, so the bottom-margin VDD lane (where the tail's VDD riser lands) carries the
whole load at end A; it, not the per-net copper total, sets the current limit.
`scripts/check_strip_fit.py` proves hops, channels, lanes/current, panel and the
`mechanical/variants.py` mirror for every variant.

## Power Tree

| Rail | Voltage | Source | Regulator | Load | Current |
|---|---|---|---|---|---|
| VDD_LED | 5.0 V (3.7-5.5 V allowed) | External 5 V / 5 A supply via controller | none | 480 x WS2816C | ~0.4 A idle; ~5.5 A full white (11.5 mA max each) |

- Firmware caps global brightness so total current stays under the connector rating
  (7 VDD pins at 1 A each; target a 2-3 A cap). Full white (~5.5 A) also exceeds
  the 5 A supply, so the cap is mandatory, not optional.
- Power distribution: 6 horizontal lanes (bottom margin, 4 gaps between rows, top
  margin) alternating VDD, GND, VDD, GND, VDD, GND from the bottom, on both layers,
  stitched with vias. The data band is ±2.0 mm around each row centreline, so the
  gap lanes are 5.1 mm wide and the margin lanes 2.55 mm (2.25 mm of copper after
  the 0.3 mm edge clearance); each net has 5.1 + 5.1 + 2.25 = 12.45 mm of copper per layer
  (14.7 mm at the old 10 mm pitch). Lanes join through vertical spines on the top face of
  the lap zones: GND spine at end A, VDD spine at end B. Each lane is crossed only by
  data U-turns at the opposite end from its spine.
- Drop estimate (1 oz ≈ 0.49 mΩ/sq, ~24.9 mm total per net over 446 mm ≈ 8.8 mΩ, full
  white 5.5 A distributed): ~25-30 mV per rail, plus the splice (15 soldered joints per
  rail, negligible).
- The WS2816C needs no decoupling (datasheet: "no need any external components").
  A small 0402 100 nF every few LEDs is optional and stays out of v1.

## Interface Map

| Interface | From | To | Protocol | Speed | SI Constrained |
|---|---|---|---|---|---|
| DIN | Controller (5 V buffered) | LED #1 DI | WS281x NZR, 48 bit/LED | 800 kbit/s (1.25 µs/bit) | No |
| BI chain | LED n BO | LED n+1 BI | backup data | same | No |
| DO chain | LED n DO | LED n+1 DI | data | same | No |
| DRET | Last LED DO | Connector | chain-integrity return (debug) | same | No |

- LED #1 BI is tied to GND (datasheet).
- Frame time: 480 x 60 µs + 280 µs reset ≈ 29.1 ms → ~34 fps.
- VIH = 0.7 * VDD = 3.5 V, so a 3.3 V MCU **must** go through a 5 V buffer
  (e.g. 74AHCT1G125) on the controller side.

### Chain order (row-major serpentine, changed from column-major 2026-10-03)

1. DIN enters top col 1 row 0 (end A, near the bottom edge) from the tail.
2. Top face rows 0 → 4: even rows run A → B, odd rows B → A. U-turns happen only at the strip ends.
3. Top col 47 row 4 (end B) → via → bottom col 48 row 4.
4. Bottom face rows 4 → 0, each running opposite to the top row at the same y.
5. The last LED is bottom col 0 row 0 (end A, bottom edge); its DO goes back to the connector as DRET.

Column-major would have needed a U-turn at every column (~48 per face), each crossing
the power distribution. Row-major has 4 U-turns per face, all at the strip ends,
so the interior is just straight data rows between straight power lanes.

## Connector (flex tail)

- Mating connector (on the future controller board): XFCN F1002-B-16-20T-R, LCSC C481251,
  16P 1.0 mm, bottom contact, flip-lock, 1 A/contact (verified in datasheet), $0.14.
  Datasheet: docs/datasheets/XFCN_F1002-B-12-20T-R_C481250.pdf (family drawing).
- The flex tail leaves the long edge at end A and ends in 16 fingers at 1.0 mm pitch.
  Tail width 17.00 ±0.05 mm, fingers 0.50 mm wide (XFCN drawing), exposed ≥ 3.5 mm, 0.30 ±0.03 mm
  thick (0.115 mm flex + 0.20 mm PI stiffener, stiffener ≥ 4 mm long), no copper behind
  the fingers.
- Pinout (approved 2026-10-03): 1-7 VDD, 8 DRET, 9 DIN, 10-16 GND.
- Fingers are on the **bottom copper face** (stiffener on the top face), tail centreline 10.35 mm from end A (was 11.25 at 10 mm pitch), spanning 1.85…18.85 mm from end A, 50 mm long, on segment A. The GND finger copper's outer edge sits on the lap-zone edge (9.1 mm from end A); the DIN finger is just outside it. Valid window 10.0 < offset ≤ 10.35 (fillet clearance / GND riser in the spine). The controller board's ZIF must take the flex with that face against its contacts. Check pin 1 there: a mirror swaps 5 V and GND.
  That's ~0.79 A/pin at 5.5 A full white (inside 1 A, but the firmware cap still applies).
- The tail runs in y, so segment A's x-extent stays 220.9 mm.

## Board

- **Dimensions:** 445.9 x 45.5 mm strip as two boards: segment A 220.9 x 45.5 mm plus the 50 mm tail, segment B 230.0 x 45.5 mm
- **Layers:** 2 (flex), LEDs on both sides, aligned back-to-back (top col k directly over bottom col k)
- **Material:** polyimide flex, 1 oz copper if JLCPCB offers it for 2-layer FPC, coverlay both sides, ENIG
- **Fab house:** JLCPCB flex
- **Substrate:** custom, see `pappalapap/substrate.py`

### Mechanical Constraints
- No LEDs on the top face inside either Möbius lap zone (x < 9.1, x > 436.8).
- No LED body in the 5 mm splice overlap (215.9..220.9 mm from end A).
- Möbius with a 436.8 / 45.5 = 9.6 aspect ratio: the twist is spread out and curvature is mild. Keep traces running along the strip and avoid big copper shapes that stiffen the twist.
- Stiffener only under the tail fingers.

## Voltage Domains

| Domain | Voltage | Components/Pins |
|---|---|---|
| VDD_LED | 5 V | all LED VDD, all LED data (DI/BI/DO/BO), DIN/DRET at the connector |
| Controller 3.3 V | 3.3 V | MCU only, never on the flex |

## Module Hierarchy

```
pappalapap/
├── substrate.py                  # 2-layer JLCPCB flex stackup + vias + fab rules
├── variants.py                   # StripVariant: TWO_SEGMENT, ONE_SEGMENT (strip geometry)
├── components/
│   ├── worldsemi_ws2816c.py      # WS2816C-2121 LED (+ DataPath: DO->DI / BO->BI)
│   ├── splice_pads.py            # lap-splice plated-hole field joining segments A and B
│   └── fpc_tail.py               # 16-pos 1.0 mm ZIF finger pads (mechanical footprint)
├── circuits/
│   └── led_strip.py              # parametric two-face LED grid + chain wiring + placement, segments
├── main.py                       # entry point, re-exports designs.flex_strip.Pappalapap
└── designs/
    ├── flex_strip.py             # FlexSegmentA / FlexSegmentB (orderable), Pappalapap (one piece)
    ├── flex_panel.py             # FlexPanelA / FlexPanelB: JLC assembly panels (ordered)
    ├── one_segment.py            # FlexOneSegment / FlexOnePanel: the 1seg variant
    └── controller.py             # (Board 2, deferred) controller / adapter
```

## Object-Hierarchy Decisions

- **LED grid (`circuits/led_strip.py`):** `LedStrip(Circuit)` holds
  `self.leds: list[WS2816C]` **in chain order**. The order is built from the
  geometry: a frozen dataclass `LedSite(face: Side, col: int, row: int)` describes each
  site. One loop places each LED (`.at(x, y, on=face)`) and joins it to the previous
  one (`prev.DO + cur.DI`, `prev.BO + cur.BI`). No string-keyed dicts, no `getattr`.
- **Segments:** `LedStrip(segment=range(...))` instantiates only that column range but
  walks the global chain (`chain_sites()`), so order, rotation and lane parity are
  identical to the one-piece strip. A hop with one end outside the segment becomes a
  splice port (`splice_hops: list[SpliceHop]` in chain order, `splice_ports` aligned;
  `SpliceHop(path, upstream, downstream)` is frozen, so both segments build equal
  values). `FlexStrip(segment)` places one `SplicePads` per joint (`splices`, keyed by
  the joint column) and nets each splice port to `data_port(face, row, path)`.
  Lanes (`Lane`, `LedStrip.lanes(data_band)`) live on the strip, which owns the rows.
- **Geometry knobs:** pitch, rows, columns and lap-zone columns come from the
  `StripVariant` passed to `LedStrip` (see "Variants"). Board outline and lap pads in `main.py` come from the same
  values, with no duplicate constants.
- **Power:** `VDD` and `GND` nets on `LedStrip` ports, tagged PowerTag/GroundTag for
  the wide-trace rule.

## Design Notes
- The back-to-back LEDs have pads on both layers at the same xy. Vias have to sit
  between LED sites, which is easy at a 9.1 mm pitch (stitching vias sit on a
  half-pitch grid at the lane centrelines, ≥ 3.5 mm from every LED centre).
- Alternating rows run in opposite directions. LED rotation is 0/180 by row and face
  (see led_strip.py), which also puts every LED's VDD and GND pads on the correct lane.
- Firmware mapping (not in this repo yet): row-major chain index → (face, col, row) →
  position on the 96-column virtual ring, including the row flip across the half-twist.
