"""Task 3: fit_axis -- one test per tier, plus the insufficient-room edge case."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reflow import fit_axis, AxisFitError  # noqa: E402

# --- Tier 1: bounding box already fits once translated -- gaps byte-for-byte unchanged.
items = [("a", 800, 100), ("b", 950, 100)]  # span 800..1050, gap 50
result = fit_axis(items, target_dim=300)  # span (250) <= 300
assert result["a"]["scale"] == 1.0 and result["b"]["scale"] == 1.0
assert result["b"]["pos"] - (result["a"]["pos"] + result["a"]["size"]) == 50, "tier 1 must preserve the original gap exactly"
assert result["a"]["pos"] >= 0 and result["b"]["pos"] + result["b"]["size"] <= 300
print("tier 1 (move): OK")

# --- Tier 2: span too big to move, but compaction to the 4px floor fits.
items = [("a", 0, 100), ("b", 150, 100), ("c", 300, 100)]  # span 400, two 50px gaps
result = fit_axis(items, target_dim=308)
assert result["a"]["scale"] == 1.0 and result["b"]["scale"] == 1.0 and result["c"]["scale"] == 1.0, "tier 2 must never resize"
assert result["a"]["size"] == 100 and result["b"]["size"] == 100 and result["c"]["size"] == 100
gap_ab = result["b"]["pos"] - (result["a"]["pos"] + result["a"]["size"])
gap_bc = result["c"]["pos"] - (result["b"]["pos"] + result["b"]["size"])
assert gap_ab >= 4 and gap_bc >= 4, f"gaps must never go below the 4px floor, got {gap_ab}, {gap_bc}"
assert result["c"]["pos"] + result["c"]["size"] - result["a"]["pos"] <= 308
print("tier 2 (compact): OK")

# --- Tier 3: even at the 4px floor, sizes alone exceed target_dim -- must scale down.
items = [("a", 0, 100), ("b", 150, 100)]  # sizes sum 200, 1 gap -> floor-packed min = 204
result = fit_axis(items, target_dim=100)  # too small even for floor-packed sizes
assert result["a"]["scale"] < 1.0 and result["a"]["scale"] == result["b"]["scale"], "tier 3 must apply one shared scale factor"
assert result["a"]["size"] + result["b"]["size"] + 4 <= 100 + 1, "packed (with 4px gap) must fit target_dim (+-1 for rounding)"
gap = result["b"]["pos"] - (result["a"]["pos"] + result["a"]["size"])
assert gap == 4, f"tier 3 must repack at exactly the 4px floor, got gap={gap}"
print("tier 3 (scale): OK")

# --- Edge case: not even the mandatory floor gaps fit for this many elements.
items = [("a", 0, 1), ("b", 10, 1), ("c", 20, 1), ("d", 30, 1)]  # 4 elements, 3 mandatory 4px gaps = 12px minimum just for gaps
try:
    fit_axis(items, target_dim=5)  # smaller than the 3*4=12px of mandatory gaps alone
    assert False, "expected AxisFitError"
except AxisFitError:
    pass
print("insufficient-room edge case: OK")

# --- No-overlap guarantee, direct AABB check, for a denser tier-2/3-forcing scenario.
def overlaps(a_pos, a_size, b_pos, b_size):
    return not (a_pos + a_size <= b_pos or b_pos + b_size <= a_pos)

items = [(f"e{i}", i * 60, 55) for i in range(6)]  # 6 elements, span 0..355 (last starts at 300, size 55)
for target in (308, 200, 100, 50):
    result = fit_axis(items, target_dim=target)
    ids = list(result)
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = result[ids[i]], result[ids[j]]
            assert not overlaps(a["pos"], a["size"], b["pos"], b["size"]), f"overlap at target_dim={target}: {ids[i]} vs {ids[j]}"
print("no-overlap guarantee across all tiers: OK")

# --- fit_axis is a generic (id, pos, size) fitter -- it works identically on row
#     pseudo-items (Task 6 will feed it "__row0"-style keys), not just element ids.
row_items = [("__row0", 0, 90), ("__row1", 114, 90)]
row_result = fit_axis(row_items, target_dim=300)
assert row_result["__row0"]["scale"] == 1.0 and row_result["__row1"]["scale"] == 1.0
print("generic over row pseudo-items too: OK")

print("\nTASK 3: fit_axis -- ALL CHECKS PASSED")
