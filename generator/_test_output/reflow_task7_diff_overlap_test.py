"""Task 7: find_new_elements (source/target id diff) and check_overlaps (pairwise AABB)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reflow import find_new_elements, check_overlaps  # noqa: E402

source = {"a": {}, "b": {}, "c": {}}
target = {"a": {}, "d": {}}
new_ids, pinned_ids = find_new_elements(source, target)
assert new_ids == {"b", "c"}
assert pinned_ids == {"a"}
print("find_new_elements: OK")

pinned = {"p1": {"left": 0, "top": 0, "width": 100, "height": 100}}
non_overlapping_new = {"n1": {"left": 200, "top": 0, "width": 50, "height": 50}}
overlapping_new = {"n2": {"left": 50, "top": 50, "width": 100, "height": 100}}
touching_new = {"n3": {"left": 100, "top": 0, "width": 50, "height": 50}}  # edges touch, not overlapping

assert check_overlaps(pinned, non_overlapping_new) == []
assert check_overlaps(pinned, overlapping_new) == [("n2", "p1")]
assert check_overlaps(pinned, touching_new) == [], "exactly-touching rectangles must NOT count as overlapping"
print("check_overlaps: OK")

print("\nTASK 7: find_new_elements / check_overlaps -- ALL CHECKS PASSED")
