"""Task 4: detect_rows -- groups elements into rows by source Y-overlap."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reflow import detect_rows  # noqa: E402

# --- Single row: three elements whose Y-ranges all mutually overlap ------------------
elements = {
    "a": {"left": 0, "top": 20, "width": 50, "height": 50},
    "b": {"left": 60, "top": 30, "width": 50, "height": 20},
    "c": {"left": 120, "top": 25, "width": 50, "height": 45},
}
assert detect_rows(elements) == [["a", "b", "c"]]
print("single row: OK")

# --- Two cleanly separated rows -------------------------------------------------------
elements2 = {
    "a": {"left": 0, "top": 20, "width": 50, "height": 50},   # range 20-70
    "b": {"left": 0, "top": 100, "width": 50, "height": 50},  # range 100-150, no overlap with a
}
assert detect_rows(elements2) == [["a"], ["b"]]
print("two separate rows: OK")

# --- Row with differing (but Y-overlapping) top/height values ------------------------
elements3 = {
    "d": {"left": 0, "top": 0, "width": 200, "height": 100},   # range 0-100
    "e": {"left": 250, "top": 50, "width": 50, "height": 30},  # range 50-80, overlaps
    "f": {"left": 350, "top": 90, "width": 30, "height": 5},   # range 90-95, overlaps accumulated (0-100)
}
assert detect_rows(elements3) == [["d", "e", "f"]]
print("Y-overlapping-but-different top/height, single row: OK")

# --- Within a row, elements are ordered left-to-right, NOT by the order they were
#     encountered while sorting by top (this is the ordering wrap_rows relies on).
elements4 = {
    "g": {"left": 200, "top": 10, "width": 50, "height": 100},  # sorted-by-top first (top=10)
    "h": {"left": 0, "top": 15, "width": 50, "height": 90},     # sorted-by-top second, but leftmost
}
assert detect_rows(elements4) == [["h", "g"]], "row members must be left-to-right ordered by 'left'"
print("left-to-right ordering within a row: OK")

# --- Empty input ------------------------------------------------------------------
assert detect_rows({}) == []
print("empty input: OK")

print("\nTASK 4: detect_rows -- ALL CHECKS PASSED")
