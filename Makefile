# pappalapap: regenerate every derived file from source.
#
#   make            checks + boards + reports + mechanical (needs a running JITX runtime)
#   make jlcpcb     JLCPCB fab + assembly packets for the orderable boards (jlcpcb/<name>)
#   make full-strip build + report the one-piece strip (reference only, not orderable)
#   make mech       mechanical outputs only (no JITX needed)
#   make solve      re-solve the Möbius shape from scratch (~30 min); otherwise the
#                   committed mechanical/data/mobius_shape_10mm.npz is used
#
# Generated files are gitignored; only sources and data that can't be regenerated
# (JITX design-info, the solved shape) are committed. See docs/STATUS.md.

PY        := .venv/bin/python
MPY       := mechanical/.venv/bin/python
JITX      := .venv/bin/jitx
# Orderable boards. The flex strip is two segments (JLC assembles flex boards
# only up to 230 mm + rails); the one-piece strip is FULL_STRIP, optional.
FLEX_A    := pappalapap.designs.flex_strip.FlexSegmentA
FLEX_B    := pappalapap.designs.flex_strip.FlexSegmentB
# What is ordered: each segment on its JLC assembly panel (rails, tabs,
# mouse bites, fiducials, tooling holes; designs/flex_panel.py).
PANEL_A   := pappalapap.designs.flex_panel.FlexPanelA
PANEL_B   := pappalapap.designs.flex_panel.FlexPanelB
# One-board variant (4.69 mm pitch, whole strip on one 230 mm board;
# designs/one_segment.py): the board and its JLC assembly panel (ordered).
ONE_SEG   := pappalapap.designs.one_segment.FlexOneSegment
ONE_PANEL := pappalapap.designs.one_segment.FlexOnePanel
COLUMN    := pappalapap.designs.column_board.ColumnBoard
INTERFACE := pappalapap.designs.interface_board.InterfaceBoard
FULL_STRIP := pappalapap.designs.flex_strip.Pappalapap
BOARDS    := $(FLEX_A) $(FLEX_B) $(PANEL_A) $(PANEL_B) $(ONE_SEG) $(ONE_PANEL) \
             $(COLUMN) $(INTERFACE)
# Export name for each orderable board: jlcpcb/<name>
JLC_NAMES := $(PANEL_A)=flex_panel_a $(PANEL_B)=flex_panel_b $(ONE_PANEL)=flex_one_panel \
             $(COLUMN)=column_board $(INTERFACE)=interface_board
SHAPE     := mechanical/data/mobius_shape_9p1mm.npz
OUT       := mechanical/out

.PHONY: all setup runtime check boards reports jlcpcb full-strip mech solve clean
all: check boards reports mech

setup:
	python3 -m venv .venv
	PIP_PRE=1 .venv/bin/pip install --extra-index-url https://pypi.jitx.com/jitx/main/+simple -e . ruff pyright click parts2jitx
	cd mechanical && uv venv .venv && uv pip install --python .venv/bin/python -r requirements.txt

runtime:
	$(JITX) runtime status >/dev/null 2>&1 || $(JITX) runtime start --background

CHECKS    := scripts/check_zif_mating.py scripts/check_splice.py scripts/check_strip_fit.py

check:
	.venv/bin/ruff check pappalapap $(CHECKS) mechanical/variants.py
	.venv/bin/pyright --pythonpath $(PY) pappalapap $(CHECKS)
	$(PY) scripts/grep_gates.py pappalapap/
	@for c in $(CHECKS); do echo "== $$c"; $(PY) $$c || exit 1; done

boards: runtime
	@for d in $(BOARDS); do echo "== $$d"; yes n | $(JITX) build $$d | tail -1; done

reports: runtime
	@for d in $(BOARDS); do $(PY) scripts/design_report.py $$d; done

# JLCPCB packets (gerbers, drill, BOM, CPL, order notes) for each orderable board.
jlcpcb: runtime
	@for pair in $(JLC_NAMES); do d=$${pair%%=*}; n=$${pair##*=}; echo "== $$d -> jlcpcb/$$n"; \
	  $(JITX) design export jlcpcb $$d --output jlcpcb/$$n --overwrite || exit 1; done

full-strip: runtime
	yes n | $(JITX) build $(FULL_STRIP) | tail -1
	$(PY) scripts/design_report.py $(FULL_STRIP)

# Mechanical pipeline, from the committed solved shape.
mech:
	mkdir -p $(OUT)
	cp $(SHAPE) $(OUT)/mobius_shape.npz
	cd mechanical && ../$(MPY) orient.py && ../$(MPY) frame.py && ../$(MPY) column.py \
	  && ../$(MPY) render.py && ../$(MPY) paper_template.py

# Re-solve the shape: coarse from scratch, then the fine mesh, then store it.
solve:
	cd mechanical && MOBIUS_NU=96 MOBIUS_NV=8 MOBIUS_TAG=_coarse ../$(MPY) mobius_shape.py
	cd mechanical && ../$(MPY) mobius_shape.py --init-from out/mobius_shape_coarse.npz
	cp $(OUT)/mobius_shape.npz $(SHAPE)

clean:
	rm -rf $(OUT) jlcpcb design-report-*.json design-report-*.txt layout/*-input.json
