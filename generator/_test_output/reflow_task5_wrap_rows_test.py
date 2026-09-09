"""Task 5: wrap_rows -- splits a row that doesn't fit target_width by peeling trailing
elements onto a new row, recursively."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reflow import wrap_rows  # noqa: E402

def make(*specs):
    # specs: (id, left, width)
    return {eid: {"left": left, "width": width} for eid, left, width in specs}

# --- A row that already fits: no split -------------------------------------------
elements = make(("a", 0, 100), ("b", 110, 100), ("c", 220, 100), ("d", 330, 100))
assert wrap_rows([["a", "b", "c", "d"]], elements, target_width=500) == [["a", "b", "c", "d"]]
print("already fits, no split: OK")

# --- A row that needs exactly one split -------------------------------------------
# span = (330+100) - 0 = 430 > 250; peeling c,d together (a,b alone span 210 <= 250 fits).
result = wrap_rows([["a", "b", "c", "d"]], elements, target_width=250)
assert result == [["a", "b"], ["c", "d"]], f"expected one split into two rows, got {result}"
print("exactly one split: OK")

# --- A row dense enough to need multiple splits -----------------------------------
dense = make(*[(f"e{i}", i * 110, 100) for i in range(6)])  # e0..e5, 100px wide, 10px gaps
result = wrap_rows([[f"e{i}" for i in range(6)]], dense, target_width=150)
assert result == [[f"e{i}"] for i in range(6)], f"expected 6 singleton rows, got {result}"
print("multiple splits down to singletons: OK")

# --- A single element wider than target_width on its own: left as a 1-element row,
#     never loops -- it falls through to fit_axis's own compact/scale tiers later.
wide = make(("w", 0, 300))
assert wrap_rows([["w"]], wide, target_width=250) == [["w"]]
print("single too-wide element left unsplit (no infinite loop): OK")

# --- Multiple independent rows: only the offending row splits, the other is untouched.
mixed = make(("a", 0, 100), ("b", 110, 100), ("c", 220, 100), ("d", 330, 100), ("z", 0, 50))
result = wrap_rows([["a", "b", "c", "d"], ["z"]], mixed, target_width=250)
assert result == [["a", "b"], ["c", "d"], ["z"]], f"expected only the first row to split, got {result}"
print("only the offending row splits, others untouched: OK")

print("\nTASK 5: wrap_rows -- ALL CHECKS PASSED")
