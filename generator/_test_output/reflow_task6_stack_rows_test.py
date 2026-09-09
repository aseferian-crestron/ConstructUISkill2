# generator/_test_output/reflow_task6_stack_rows_test.py
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
# CORRECTED 2026-09-09 (Task 6's own TDD cycle caught this): "a"'s height above is
# PROVABLY int()-based, not round()-based -- a's own top/height exactly span row0's
# natural extent, so a's own height*scale is the identical expression to row0's own
# fit_axis-computed size, which fit_axis's Tier 3 always computes via int() (never
# round(), per Task 3's own fix). "b" must use the same int() convention for
# consistency -- round() here (as an earlier draft of this test had it) is provably
# inconsistent with the "a" assertion above for this exact scale0 (round(100*scale0)
# == 26 but int(100*scale0) == 25; no single per-element rounding function satisfies
# both assertions except int()).
assert result2["b"]["top"] == round(expected2["__row0"]["pos"] + (20 - 0) * scale0)
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

# --- Regression guard: ordinary (non-wrap-split) rows with a TIGHT natural gap must
#     be a true no-op -- the original gap is preserved exactly, even below min_gap,
#     never forced up to the floor. An earlier version of stack_rows unconditionally
#     forced every inter-row gap to >=min_gap, which pushed rows with a genuinely tight
#     (but non-degenerate) original gap further apart than they ever were.
elements4 = make(("p", 0, 50), ("q", 52, 50), ("r", 104, 50))  # rows separated by 2px each
rows4 = [["p"], ["q"], ["r"]]
result4 = stack_rows(rows4, elements4, target_height=300)  # ample room -- pure Tier 1 (move)
assert result4["p"]["scale"] == result4["q"]["scale"] == result4["r"]["scale"] == 1.0
assert result4["q"]["top"] - (result4["p"]["top"] + result4["p"]["height"]) == 2, (
    "ordinary rows' original 2px gap must be preserved exactly, not forced to the "
    f"4px floor, got {result4}"
)
assert result4["r"]["top"] - (result4["q"]["top"] + result4["q"]["height"]) == 2
print("ordinary rows with a tight original gap: true no-op regression guard: OK")

# --- Same regression, but flush-stacked (0px gap) rows -- must also be preserved
#     exactly, not forced to 4px, and must NOT be spuriously pushed into Tier 2/3.
elements5 = make(("s", 0, 50), ("t", 50, 50), ("u", 100, 50))  # 0px gaps, span 150 exactly
rows5 = [["s"], ["t"], ["u"]]
result5 = stack_rows(rows5, elements5, target_height=150)  # exactly the natural span
assert result5["s"]["scale"] == result5["t"]["scale"] == result5["u"]["scale"] == 1.0, (
    "flush rows fitting target_height exactly must stay at Tier 1 (move); an "
    f"unconditional 4px floor would force unnecessary Tier 3 scaling here: {result5}"
)
assert result5["t"]["top"] - (result5["s"]["top"] + result5["s"]["height"]) == 0
assert result5["u"]["top"] - (result5["t"]["top"] + result5["t"]["height"]) == 0
print("flush-stacked rows: true no-op, no spurious tier escalation: OK")

# --- Empty input --------------------------------------------------------------------
assert stack_rows([], {}, target_height=100) == {}
print("empty input: OK")

print("\nTASK 6: stack_rows -- ALL CHECKS PASSED")
