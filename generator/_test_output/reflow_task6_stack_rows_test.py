"""Task 6: stack_rows -- Y-axis row-stacking, including the pre-stacked-anchor fix for
rows that share their original top (the wrap-split case)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reflow import stack_rows, fit_axis  # noqa: E402

def make(*specs):
    # specs: (id, top, height)
    return {eid: {"top": top, "height": height} for eid, top, height in specs}

# --- Rows with distinct natural anchors, fitting via row-level Tier 1 (move) ---------
# row0 = [a, b] (anchor 50, natural height 50: a covers 50-100, b covers 60-80)
# row1 = [c]    (anchor 150, natural height 60)
elements = make(("a", 50, 50), ("b", 60, 20), ("c", 150, 60))
rows = [["a", "b"], ["c"]]
expected_row_fit = fit_axis([("__row0", 50, 50), ("__row1", 150, 60)], target_dim=200)
result = stack_rows(rows, elements, target_height=200)
assert result["a"]["top"] == expected_row_fit["__row0"]["pos"], "a's offset from row0's anchor (0) must be preserved"
assert result["b"]["top"] == expected_row_fit["__row0"]["pos"] + (60 - 50), "b's 10px offset from row0's anchor must be preserved exactly"
assert result["c"]["top"] == expected_row_fit["__row1"]["pos"]
assert result["a"]["scale"] == result["b"]["scale"] == result["c"]["scale"] == 1.0
assert result["a"]["height"] == 50 and result["b"]["height"] == 20 and result["c"]["height"] == 60
print("row-level Tier 1 (move), per-element offsets preserved: OK")

# --- A row list needing Tier 3 (scale) -- every element in a scaled row must scale ---
elements2 = make(("a", 0, 100), ("b", 20, 30), ("c", 210, 80))
rows2 = [["a", "b"], ["c"]]  # row0 anchor 0 height 100, row1 anchor 210 height 80
expected2 = fit_axis([("__row0", 0, 100), ("__row1", 210, 80)], target_dim=50)
result2 = stack_rows(rows2, elements2, target_height=50)
scale0 = expected2["__row0"]["scale"]
scale1 = expected2["__row1"]["scale"]
assert scale0 < 1.0 and scale1 < 1.0, "target_height=50 must force Tier 3 scaling"
assert result2["a"]["scale"] == scale0 and result2["b"]["scale"] == scale0
assert result2["c"]["scale"] == scale1
assert result2["a"]["top"] == expected2["__row0"]["pos"]
assert result2["a"]["height"] == expected2["__row0"]["size"], "a alone determines row0's natural height, so a's scaled height must equal the row's own fitted size"
assert result2["b"]["top"] == round(expected2["__row0"]["pos"] + (20 - 0) * scale0)
# NOTE: int(), not round() -- corrected during this task's own RED/GREEN cycle. The
# assertion above (a's height must equal expected2["__row0"]["size"]) is a hard
# requirement: a spans row0's exact natural extent (its own top == row0's min(top) and
# its own bottom == row0's max(top+height)), so a's own height * scale0 is the *same
# expression* as fit_axis's row-item size (int(natural_height * scale)) by
# construction. round() diverges from that whenever the fractional part is >= 0.5 (as
# it is here: 100 * scale0 = 25.5555..., round -> 26, but the row itself floors to 25)
# -- so height must use int() truncation throughout, matching fit_axis's own
# documented Tier 3 rationale (int() never overshoots; round() can).
assert result2["b"]["height"] == max(1, int(30 * scale0))
assert result2["c"]["top"] == expected2["__row1"]["pos"]
assert result2["c"]["height"] == expected2["__row1"]["size"]
print("row-level Tier 3 (scale), per-element scaling: OK")

# --- The wrap-split case: two rows share the SAME source top (splitting a row doesn't
#     move anything vertically) -- must NOT tie/overlap when stacked. -------------------
elements3 = make(("x", 20, 90), ("y", 20, 90))  # x and y both originally at top=20
rows3 = [["x"], ["y"]]  # wrap_rows already split these into separate rows
result3 = stack_rows(rows3, elements3, target_height=300)
assert result3["y"]["top"] >= result3["x"]["top"] + result3["x"]["height"] + 4, (
    "wrap-split sibling rows sharing the same source top must still end up "
    f"non-overlapping on Y (min 4px gap), got x={result3['x']}, y={result3['y']}"
)
print("wrap-split sibling rows (tied source top) stack without overlap: OK")

# --- Empty input --------------------------------------------------------------------
assert stack_rows([], {}, target_height=100) == {}
print("empty input: OK")

print("\nTASK 6: stack_rows -- ALL CHECKS PASSED")
