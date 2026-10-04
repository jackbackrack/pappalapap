"""Full-scale printable paper template of the LED strip, for a Möbius mock-up.

Writes out/paper_template_letter.pdf and out/paper_template_a4.pdf:
  pages 1-2  FRONT (top face) with the connector tail, split in two halves with a glue tab
  pages 3-4  BACK (bottom face), optional: glue it to the back of the front strip

LED squares are drawn at true size (2.2 mm). The ones that would be lit for a
snapshot of "PAPPALAPAP " (3x5 font) are filled, using the same ring order the
firmware will use, so the assembled band shows how the text wraps through the
half-twist.

Run: mechanical/.venv/bin/python mechanical/paper_template.py
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

from geometry import (  # noqa: E402
    BOTTOM_COLUMNS,
    HEIGHT,
    LAP,
    LED_SIZE,
    LENGTH,
    PITCH,
    ROWS,
    TAIL_LENGTH,
    TAIL_OFFSET,
    TAIL_WIDTH,
    TOP_COLUMNS,
    led_x,
    led_y,
    ring_index,
)

MM = 1 / 25.4
OUT = Path(__file__).parent / "out"

GLYPHS = {
    "P": ["###", "#.#", "###", "#..", "#.."],
    "A": ["###", "#.#", "###", "#.#", "#.#"],
    "L": ["#..", "#..", "#..", "#..", "###"],
    " ": ["...", "...", "...", "...", "..."],
}
MESSAGE = "PAPPALAPAP "
CELL = 4  # 3 glyph columns + 1 space


def lit(face: str, col: int, row: int) -> bool:
    j = ring_index(face, col) % (len(MESSAGE) * CELL)
    ch, gc = MESSAGE[j // CELL], j % CELL
    if gc == 3:
        return False
    # Glyph row 0 is the top of the letter. Top face: up is +y. Bottom face is
    # flipped by the half-twist, so up is -y there.
    g = (ROWS - 1 - row) if face == "top" else row
    return GLYPHS[ch][g][gc] == "#"


PAGE_SIZES = {"letter": (279.4, 215.9), "a4": (297.0, 210.0)}
SPLIT = LENGTH / 2  # 245
TAB = 8.0  # glue tab on the first half


def draw_page(pdf, page_w, page_h, x0, x1, face, title, glue_tab_right, cut_left):
    fig = plt.figure(figsize=(page_w * MM, page_h * MM))
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set_xlim(0, page_w)
    ax.set_ylim(0, page_h)
    ax.set_aspect("equal")
    ax.axis("off")

    # Page frame: board x in [x0, x1] is drawn with this offset.
    span = x1 - x0 + (TAB if glue_tab_right else 0)
    left = x0 if face == "top" else LENGTH - x1  # leftmost drawn coordinate
    ox = (page_w - span) / 2 - left
    oy = (page_h - (HEIGHT + TAIL_LENGTH)) / 2 + TAIL_LENGTH + 8

    def X(x):
        # Back face is drawn as seen from behind: mirrored in x.
        return (LENGTH - x if face == "bottom" else x) + ox

    def rect(xa, ya, w, h, **kw):
        xs = sorted((X(xa), X(xa + w)))
        ax.add_patch(Rectangle((xs[0], ya + oy), xs[1] - xs[0], h, **kw))

    def vline(x, **kw):
        ax.plot([X(x), X(x)], [oy, oy + HEIGHT], **kw)

    # Lap zones (hatched).
    for lx in (0.0, LENGTH - LAP):
        if lx + LAP > x0 and lx < x1:
            a, b = max(lx, x0), min(lx + LAP, x1)
            rect(a, 0, b - a, HEIGHT, facecolor="#eeeeee", edgecolor="none", hatch="///")
            ax.text(
                (X(a) + X(b)) / 2, oy + HEIGHT + 2, "LAP", ha="center", va="bottom", fontsize=6
            )

    # Glue tab beyond the split (front/back first half only).
    if glue_tab_right:
        rect(x1, 0, TAB, HEIGHT, facecolor="#dde8ff", edgecolor="#335", lw=0.4, ls="--")
        ax.text(
            (X(x1) + X(x1 + TAB)) / 2, oy + HEIGHT / 2, "GLUE TAB\nunder next half",
            rotation=90, ha="center", va="center", fontsize=5,
        )

    # Strip outline (cut lines).
    ax.plot([X(x0), X(x1)], [oy, oy], color="k", lw=0.5)
    ax.plot([X(x0), X(x1)], [oy + HEIGHT, oy + HEIGHT], color="k", lw=0.5)
    if x0 == 0 or x1 == LENGTH:
        vline(0 if x0 == 0 else LENGTH, color="k", lw=0.5)
    if cut_left:
        vline(x0, color="k", lw=0.5)
        label = "cut, overlap onto tab" if face == "top" else "cut, butt against other half"
        ax.text(X(x0), oy - 4, label, fontsize=5, ha="center", va="top")

    # Connector tail (front only).
    if face == "top" and x0 <= TAIL_OFFSET <= x1:
        tl, tr = TAIL_OFFSET - TAIL_WIDTH / 2, TAIL_OFFSET + TAIL_WIDTH / 2
        ax.plot(
            [X(tl), X(tl), X(tr), X(tr)],
            [oy, oy - TAIL_LENGTH, oy - TAIL_LENGTH, oy],
            color="k", lw=0.5,
        )
        ax.text(X(TAIL_OFFSET), oy - TAIL_LENGTH / 2, "TAIL\n(optional)", ha="center",
                va="center", fontsize=5)

    # LEDs.
    cols = TOP_COLUMNS if face == "top" else BOTTOM_COLUMNS
    other = BOTTOM_COLUMNS if face == "top" else TOP_COLUMNS
    for col in range(0, 40):
        cx = led_x(col)
        if not (x0 <= cx <= x1):
            continue
        for row in range(ROWS):
            cy = led_y(row)
            if col in cols:
                on = lit(face, col, row)
                rect(cx - LED_SIZE / 2, cy - LED_SIZE / 2, LED_SIZE, LED_SIZE,
                     facecolor="#e8461e" if on else "white",
                     edgecolor="#e8461e" if on else "#999999", lw=0.3)
            elif col in other:
                rect(cx - LED_SIZE / 2, cy - LED_SIZE / 2, LED_SIZE, LED_SIZE,
                     facecolor="none", edgecolor="#bbbbbb", lw=0.3, ls=":")
        ax.text(X(cx), oy - 1.5, str(col), ha="center", va="top", fontsize=4, color="#666")
    for row in range(ROWS):
        ax.text(X(x0) - 3 if face == "top" else X(x0) + 3, oy + led_y(row), f"r{row}",
                ha="right" if face == "top" else "left", va="center", fontsize=4, color="#666")

    # End labels.
    for ex, name in ((0, "END A"), (LENGTH, "END B")):
        if x0 <= ex <= x1:
            ax.text(X(ex), oy + HEIGHT + 6, name, ha="center", fontsize=6, weight="bold")

    # Scale check + title.
    sx, sy = 15, 12
    ax.plot([sx, sx + 100], [sy, sy], color="k", lw=0.8)
    for t in (0, 50, 100):
        ax.plot([sx + t, sx + t], [sy - 1.5, sy + 1.5], color="k", lw=0.6)
    ax.text(sx + 50, sy + 2.5, "100 mm: print at 100% / Actual size, check this bar",
            ha="center", fontsize=6)
    ax.text(15, page_h - 12, title, fontsize=9, weight="bold", va="top")
    ax.text(
        15, page_h - 18,
        "Filled squares = lit in a snapshot of 'PAPPALAPAP '. Dotted = LED on the other face. "
        "LAP zones: after one half-twist, glue end A's LAP to end B's LAP, front sides together.",
        fontsize=5.5, va="top",
    )
    pdf.savefig(fig)
    plt.close(fig)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    for name, (pw, ph) in PAGE_SIZES.items():
        path = OUT / f"paper_template_{name}.pdf"
        with PdfPages(path) as pdf:
            draw_page(pdf, pw, ph, 0, SPLIT, "top", "FRONT (top face) 1/2: end A",
                      glue_tab_right=True, cut_left=False)
            draw_page(pdf, pw, ph, SPLIT, LENGTH, "top", "FRONT (top face) 2/2: end B",
                      glue_tab_right=False, cut_left=True)
            # Back sheet, seen from behind. Its first half covers end B.
            draw_page(pdf, pw, ph, SPLIT, LENGTH, "bottom",
                      "BACK (bottom face, optional) 1/2: end B, glue to back of front",
                      glue_tab_right=False, cut_left=True)
            draw_page(pdf, pw, ph, 0, SPLIT, "bottom",
                      "BACK (bottom face, optional) 2/2: end A, glue to back of front",
                      glue_tab_right=False, cut_left=True)
        print("wrote", path)


if __name__ == "__main__":
    main()
