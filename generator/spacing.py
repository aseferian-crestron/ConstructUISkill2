"""
Design-system spacing/sizing scale (ConstructUISkill_DesignSystem.md §4) -- the
skill's own POLICY, not a Construct file-format fact, so there is nothing to confirm
against C:\\Git\\CCIDE here: these are defaults the generator applies when
placing/sizing components, the same way palette.py's derive_states applies a
standard-practice default rather than a schema-derived one.

SPACING_UNIT: every margin, padding, and gap a multiple of this.
MIN_TOUCH_TARGET: Apple HIG's 44pt floor (Material's 48dp is the other common
reference point; 44 is the doc's own default, kept as a single named constant so a
project can override it without touching call sites).
EDGE_PADDING: the minimum margin between the outermost controls and the panel's own
bezel -- one spacing-scale multiple, not an independent value.
"""
from __future__ import annotations

SPACING_UNIT = 8
MIN_TOUCH_TARGET = 44
EDGE_PADDING = SPACING_UNIT * 2


def snap_to_spacing(value: int) -> int:
    """`value` rounded to the nearest multiple of SPACING_UNIT (ties round up).

    Not `round(value / SPACING_UNIT) * SPACING_UNIT`: Python's `round()` is
    round-half-to-even ("banker's rounding"), so that expression sends 4 to 0, not
    8 -- wrong for a spacing scale, where ties should round up like everyday rounding.
    """
    return ((value + SPACING_UNIT // 2) // SPACING_UNIT) * SPACING_UNIT


def meets_touch_target(width: int, height: int) -> bool:
    """Whether a component's full tappable area (not just its visible icon/label)
    meets the minimum touch-target floor on BOTH axes independently."""
    return width >= MIN_TOUCH_TARGET and height >= MIN_TOUCH_TARGET


def enforce_touch_target(width: int, height: int) -> tuple[int, int]:
    """`(width, height)` clamped UP to MIN_TOUCH_TARGET on any axis below it. Never
    shrinks an axis that already meets the floor -- this is a floor, not a fixed
    size."""
    return max(width, MIN_TOUCH_TARGET), max(height, MIN_TOUCH_TARGET)
