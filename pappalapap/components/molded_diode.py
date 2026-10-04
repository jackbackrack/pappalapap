"""Molded-body two-terminal diode landpattern: pad 1 = cathode, marked.

``jitxlib.landpatterns.twopin.molded.PolarizedMoldedTwoPin`` (jitxlib-standard
4.5.0a1) names its pads ``a`` (anode, +y) and ``c`` (cathode, -y), but puts its
pad-1 silkscreen dot beside ``a``, the anode. For a diode the board mark belongs
at the cathode (the body's band end).

``Pad1MoldedTwoPin`` composes the same library mixins the way
``PolarizedMoldedTwoPin`` does, with ``LinearNumbering`` in place of the
cathode/anode numbering: pads ``p[1]`` (+y, dotted) and ``p[2]`` (-y), the
IPC-7351 convention of pin 1 = cathode. Pad geometry is the generator's.
Components map their cathode to ``p[1]``.
"""

from jitxlib.landpatterns.grid_layout import LinearNumbering
from jitxlib.landpatterns.silkscreen.marker import Pad1Marker
from jitxlib.landpatterns.twopin.molded import MoldedTwoPinDecorated


class Pad1MoldedTwoPin(LinearNumbering, Pad1Marker, MoldedTwoPinDecorated):
    """Molded two-pin landpattern, pads numbered 1 (+y, marked) and 2 (-y)."""
