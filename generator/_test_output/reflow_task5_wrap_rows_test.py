"""Task 5 (original reflow plan) + Task 2 (2026-09-10 centering plan) + Task 2
(2026-09-10 columns plan): wrap_rows -- splits a row that doesn't fit target_width by
peeling trailing COLUMNS onto a new row (a column's own members, e.g. a stacked Up/Down
pair, always travel together -- see docs/superpowers/specs/
2026-09-10-reflow-columns-design.md), tagging each output row as a fragment (True, came
from a split) or untouched (False)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reflow import wrap_rows  # noqa: E402

def make(*specs):
    # specs: (id, left, width, top)
    return {eid: {"left": left, "width": width, "top": top} for eid, left, width, top in specs}

# --- A row that already fits: no split, untouched (False) ------------------------
# No overlapping left ranges -> every element is its own column.
elements = make(("a", 0, 100, 0), ("b", 110, 100, 0), ("c", 220, 100, 0), ("d", 330, 100, 0))
assert wrap_rows([["a", "b", "c", "d"]], elements, target_width=500) == [([["a"], ["b"], ["c"], ["d"]], False)]
print("already fits, no split, untouched (False), one column per element: OK")

# --- A row that needs exactly one split: both halves are fragments (True) --------
# span = (330+100) - 0 = 430 > 250; peeling c,d together (a,b alone span 210 <= 250 fits).
result = wrap_rows([["a", "b", "c", "d"]], elements, target_width=250)
assert result == [([["a"], ["b"]], True), ([["c"], ["d"]], True)], f"expected one split into two fragment rows, got {result}"
print("exactly one split, both halves fragments (True): OK")

# --- A row dense enough to need multiple splits: every resulting row is a fragment -
dense = make(*[(f"e{i}", i * 110, 100, 0) for i in range(6)])  # e0..e5, 100px wide, 10px gaps
result = wrap_rows([[f"e{i}" for i in range(6)]], dense, target_width=150)
assert result == [([[f"e{i}"]], True) for i in range(6)], f"expected 6 singleton fragment rows, got {result}"
print("multiple splits down to singletons, all fragments (True): OK")

# --- A single element wider than target_width on its own: left as a 1-column row,
#     never loops, untouched (False).
wide = make(("w", 0, 300, 0))
assert wrap_rows([["w"]], wide, target_width=250) == [([["w"]], False)]
print("single too-wide element left unsplit, untouched (False): OK")

# --- Multiple independent rows: only the offending row splits (fragments, True),
#     the other row is untouched (False).
mixed = make(("a", 0, 100, 0), ("b", 110, 100, 0), ("c", 220, 100, 0), ("d", 330, 100, 0), ("z", 0, 50, 0))
result = wrap_rows([["a", "b", "c", "d"], ["z"]], mixed, target_width=250)
assert result == [([["a"], ["b"]], True), ([["c"], ["d"]], True), ([["z"]], False)], f"expected only the first row to split, got {result}"
print("only the offending row splits (True), the other stays untouched (False): OK")

# --- NEW (Task 2, columns): a stacked pair (same left) always travels together -------
# Two columns: a pair at left=0 (two elements, same left) and a lone wide element at
# left=200 that doesn't fit alongside the pair. The peel must move the WHOLE pair or
# the WHOLE lone column, never split the pair's two members apart.
paired = make(("p1", 0, 80, 0), ("p2", 0, 80, 50), ("wide", 200, 300, 0))
result = wrap_rows([["p1", "p2", "wide"]], paired, target_width=150)
# columns: [["p1","p2"], ["wide"]] (span 0-500=500>150) -- must split into exactly these
# two columns, each a fragment; the pair's members must never be separated into
# different output rows.
assert result == [([["p1", "p2"]], True), ([["wide"]], True)], f"pair must travel together, got {result}"
print("a stacked pair (same left) always travels together through a peel: OK")

print("\nTASK 5/2/2: wrap_rows column-aware peeling -- ALL CHECKS PASSED")
