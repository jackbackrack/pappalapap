# pappalapap: regenerate every derived file from source.
#
#   make            checks + boards + reports + mechanical (needs a running JITX runtime)
#   make mech       mechanical outputs only (no JITX needed)
#   make solve      re-solve the Möbius shape from scratch (~30 min); otherwise the
#                   committed mechanical/data/mobius_shape_10mm.npz is used
#
# Generated files are gitignored; only sources and data that can't be regenerated
# (JITX design-info, the solved shape) are committed. See docs/STATUS.md.

PY        := .venv/bin/python
MPY       := mechanical/.venv/bin/python
JITX      := .venv/bin/jitx
BOARDS    := pappalapap.designs.flex_strip.Pappalapap \
             pappalapap.designs.column_board.ColumnBoard \
             pappalapap.designs.interface_board.InterfaceBoard
SHAPE     := mechanical/data/mobius_shape_10mm.npz
OUT       := mechanical/out

.PHONY: all setup runtime check boards reports mech solve clean
all: check boards reports mech

setup:
	python3 -m venv .venv
	PIP_PRE=1 .venv/bin/pip install --extra-index-url https://pypi.jitx.com/jitx/main/+simple -e . ruff pyright click parts2jitx
	cd mechanical && uv venv .venv && uv pip install --python .venv/bin/python -r requirements.txt

runtime:
	$(JITX) runtime status >/dev/null 2>&1 || $(JITX) runtime start --background

check:
	.venv/bin/ruff check pappalapap scripts/check_zif_mating.py
	.venv/bin/pyright pappalapap
	$(PY) scripts/grep_gates.py pappalapap/
	$(PY) scripts/check_zif_mating.py

boards: runtime
	@for d in $(BOARDS); do echo "== $$d"; yes Y | $(JITX) build $$d | tail -1; done

reports: runtime
	@for d in $(BOARDS); do $(PY) scripts/design_report.py $$d; done

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
	rm -rf $(OUT) design-report-*.json design-report-*.txt layout/*-input.json
