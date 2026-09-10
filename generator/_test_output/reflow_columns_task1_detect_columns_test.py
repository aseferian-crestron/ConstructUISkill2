"""Task 1: detect_columns -- the X-axis transpose of detect_rows, scoped to one
already-detected row's members. See docs/superpowers/specs/
2026-09-10-reflow-columns-design.md."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reflow import detect_columns  # noqa: E402


def make(*specs):
    # specs: (id, left, width, top)  -- top is only for verifying within-column order
    return {eid: {"left": left, "width": width, "top": top} for eid, left, width, top in specs}


# --- The real reported shape: two same-left pairs flanking a wide/tall element -------
# iha5b0/i4rvpkl share left=292 (a vertical Up/Down pair); ilqek (D-pad) is disjoint;
# im68at/i66ouw share left=876 (the other pair).
elements = make(
    ("iha5b0", 292, 106, 311), ("i4rvpkl", 292, 106, 409),
    ("ilqek", 474, 332, 234),
    ("im68at", 876, 106, 311), ("i66ouw", 876, 106, 409),
)
row = ["iha5b0", "i4rvpkl", "ilqek", "im68at", "i66ouw"]  # detect_rows' own left-to-right order
result = detect_columns(elements, row)
assert result == [["iha5b0", "i4rvpkl"], ["ilqek"], ["im68at", "i66ouw"]], (
    f"expected 2 pair-columns flanking the D-pad's own column, got {result}"
)
print("real reported shape: 3 columns, pairs grouped, D-pad alone: OK")

# --- Degenerate case: no overlapping left ranges -> one column per element -----------
disjoint = make(("a", 0, 100, 0), ("b", 110, 100, 0), ("c", 220, 100, 0))
result_disjoint = detect_columns(disjoint, ["a", "b", "c"])
assert result_disjoint == [["a"], ["b"], ["c"]], f"expected 3 singleton columns, got {result_disjoint}"
print("degenerate case (no X-overlap): one column per element: OK")

# --- Transitive closure: 3+ elements chained by overlapping (not identical) ranges ---
# a: [0,150), b: [100,250) overlaps a, c: [200,350) overlaps b but not a directly --
# still one column via the same accumulated-range growth detect_rows itself uses.
chained = make(("a", 0, 150, 0), ("b", 100, 150, 10), ("c", 200, 150, 20))
result_chained = detect_columns(chained, ["a", "b", "c"])
assert result_chained == [["a", "b", "c"]], f"expected one transitively-closed column, got {result_chained}"
print("transitive closure (chained overlaps): one column: OK")

# --- Within-column order is top-to-bottom, not input/left order ----------------------
# iha5b0 (top=311) must come before i4rvpkl (top=409) in the pair's own column.
assert result[0] == ["iha5b0", "i4rvpkl"], "within-column order must be top-to-bottom"
print("within-column order is top-to-bottom: OK")

# --- Empty row -------------------------------------------------------------------
assert detect_columns({}, []) == []
print("empty row: OK")

print("\nTASK 1: detect_columns -- ALL CHECKS PASSED")
