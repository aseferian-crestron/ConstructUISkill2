import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from spacing import (
    SPACING_UNIT, MIN_TOUCH_TARGET, EDGE_PADDING,
    snap_to_spacing, meets_touch_target, enforce_touch_target,
)

assert SPACING_UNIT == 8
assert MIN_TOUCH_TARGET == 44
assert EDGE_PADDING == 16  # a spacing-scale multiple, per §4's edge/safe-zone rule

assert snap_to_spacing(0) == 0
assert snap_to_spacing(3) == 0
assert snap_to_spacing(4) == 8
assert snap_to_spacing(5) == 8
assert snap_to_spacing(12) == 16
assert snap_to_spacing(20) == 24
print("snap_to_spacing: rounds to nearest 8px multiple: OK")

assert meets_touch_target(44, 44) is True
assert meets_touch_target(60, 44) is True
assert meets_touch_target(43, 44) is False
assert meets_touch_target(44, 43) is False
print("meets_touch_target: both axes checked independently: OK")

assert enforce_touch_target(30, 30) == (44, 44)
assert enforce_touch_target(44, 20) == (44, 44)
assert enforce_touch_target(60, 60) == (60, 60)
assert enforce_touch_target(60, 30) == (60, 44)
print("enforce_touch_target: clamps up to the floor, never shrinks an already-larger axis: OK")

print("Spacing scale: all assertions passed.")
