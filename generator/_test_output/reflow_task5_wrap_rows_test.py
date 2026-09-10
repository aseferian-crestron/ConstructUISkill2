"""Task 5 (original reflow plan) + Task 2 (2026-09-10 centering plan): wrap_rows --
splits a row that doesn't fit target_width by peeling trailing elements onto a new row,
recursively, and tags each output row as a fragment (True, came from a split) or
untouched (False) -- see docs/superpowers/specs/2026-09-10-reflow-centering-design.md's
X axis section: a fragment row is always centered later, an untouched row is only
centered if its own original margins were symmetric."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reflow import wrap_rows  # noqa: E402

def make(*specs):
    # specs: (id, left, width)
    return {eid: {"left": left, "width": width} for eid, left, width in specs}

# --- A row that already fits: no split, untouched (False) ------------------------
elements = make(("a", 0, 100), ("b", 110, 100), ("c", 220, 100), ("d", 330, 100))
assert wrap_rows([["a", "b", "c", "d"]], elements, target_width=500) == [(["a", "b", "c", "d"], False)]
print("already fits, no split, untouched (False): OK")

# --- A row that needs exactly one split: both halves are fragments (True) --------
# span = (330+100) - 0 = 430 > 250; peeling c,d together (a,b alone span 210 <= 250 fits).
result = wrap_rows([["a", "b", "c", "d"]], elements, target_width=250)
assert result == [(["a", "b"], True), (["c", "d"], True)], f"expected one split into two fragment rows, got {result}"
print("exactly one split, both halves fragments (True): OK")

# --- A row dense enough to need multiple splits: every resulting row is a fragment -
dense = make(*[(f"e{i}", i * 110, 100) for i in range(6)])  # e0..e5, 100px wide, 10px gaps
result = wrap_rows([[f"e{i}" for i in range(6)]], dense, target_width=150)
assert result == [([f"e{i}"], True) for i in range(6)], f"expected 6 singleton fragment rows, got {result}"
print("multiple splits down to singletons, all fragments (True): OK")

# --- A single element wider than target_width on its own: left as a 1-element row,
#     never loops, untouched (False) -- it falls through to fit_axis's own
#     compact/scale tiers later.
wide = make(("w", 0, 300))
assert wrap_rows([["w"]], wide, target_width=250) == [(["w"], False)]
print("single too-wide element left unsplit, untouched (False): OK")

# --- Multiple independent rows: only the offending row splits (fragments, True),
#     the other row is untouched (False).
mixed = make(("a", 0, 100), ("b", 110, 100), ("c", 220, 100), ("d", 330, 100), ("z", 0, 50))
result = wrap_rows([["a", "b", "c", "d"], ["z"]], mixed, target_width=250)
assert result == [(["a", "b"], True), (["c", "d"], True), (["z"], False)], f"expected only the first row to split, got {result}"
print("only the offending row splits (True), the other stays untouched (False): OK")

print("\nTASK 5/2: wrap_rows fragment tagging -- ALL CHECKS PASSED")
