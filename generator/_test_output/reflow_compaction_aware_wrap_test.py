"""Regression test for a real bug found 2026-09-10, live-testing TSW-570 in Construct:
wrap_rows decided whether to peel a row using its RAW (uncompacted) span vs.
target_width, never checking whether Tier 2 compaction alone (fit_axis's own next
tier, tried after wrap in the approved move -> wrap -> compact -> scale order) would
have been enough on its own. The real D-pad row (columns of width 106/332/106, raw
span 690) has a minimum ACHIEVABLE span (full compaction, gaps squeezed to the 4px
floor) of only 552px -- comfortably under a 640px target -- but was still being peeled,
splitting the row into two Y-stacking slots instead of one and forcing every other row
on the page to compress harder than necessary (21px, illegibly small, button height)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reflow import wrap_rows  # noqa: E402


def make(*specs):
    # specs: (id, left, width, top)
    return {eid: {"left": left, "width": width, "top": top} for eid, left, width, top in specs}


# --- The real reported shape: raw span (690) exceeds target (640), but the minimum
#     achievable (fully-compacted) span (552) doesn't -- must NOT wrap at all now.
elements = make(
    ("iha5b0", 292, 106, 311), ("i4rvpkl", 292, 106, 409),
    ("ilqek", 474, 332, 234),
    ("im68at", 876, 106, 311), ("i66ouw", 876, 106, 409),
)
row = ["iha5b0", "i4rvpkl", "ilqek", "im68at", "i66ouw"]
result = wrap_rows([row], elements, target_width=640)
assert result == [([["iha5b0", "i4rvpkl"], ["ilqek"], ["im68at", "i66ouw"]], False)], (
    f"expected no split (compaction alone suffices) and the row marked untouched, got {result}"
)
print("real reported shape: no wrap needed once compaction-feasibility is checked, untouched (False): OK")

# --- Regression: a row that STILL can't fit even fully compacted must still split ----
# 4 elements, 100px wide each, target=250: even fully compacted (400 + 3*4=412) doesn't
# fit -- unchanged from before this fix (see reflow_task5_wrap_rows_test.py's own
# "exactly one split" case, re-derived here to confirm this fix didn't loosen that).
tight = make(("a", 0, 100, 0), ("b", 110, 100, 0), ("c", 220, 100, 0), ("d", 330, 100, 0))
result_tight = wrap_rows([["a", "b", "c", "d"]], tight, target_width=250)
assert result_tight == [([["a"], ["b"]], True), ([["c"], ["d"]], True)], (
    f"a row that can't fit even fully compacted must still split, got {result_tight}"
)
print("a row that can't fit even fully compacted still splits (unchanged): OK")

# --- Boundary: exactly at the minimum achievable span must NOT split ----------------
# 2 columns, width 100 each, target = 100+100+4 = 204 exactly.
boundary = make(("a", 0, 100, 0), ("b", 300, 100, 0))
result_boundary = wrap_rows([["a", "b"]], boundary, target_width=204)
assert result_boundary == [([["a"], ["b"]], False)], f"expected no split at the exact boundary, got {result_boundary}"
print("exact minimum-achievable-span boundary: no split: OK")

print("\nCompaction-aware wrap fit-check -- ALL CHECKS PASSED")
