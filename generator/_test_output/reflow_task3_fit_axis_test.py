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

# --- Tier 2, genuine interpolation (0 < r < 1), not the r==1.0 boundary above -------
items = [("a", 0, 100), ("b", 150, 100), ("c", 300, 100)]  # same items, looser target
result = fit_axis(items, target_dim=320)  # needed_reduction=80 < slack=92 -- strict interpolation
assert result["a"]["scale"] == 1.0 and result["b"]["scale"] == 1.0 and result["c"]["scale"] == 1.0
span = result["c"]["pos"] + result["c"]["size"] - result["a"]["pos"]
assert span <= 320, f"tier 2 interpolation must still fit target_dim, got span={span}"
gap_ab = result["b"]["pos"] - (result["a"]["pos"] + result["a"]["size"])
gap_bc = result["c"]["pos"] - (result["b"]["pos"] + result["b"]["size"])
assert gap_ab >= 4 and gap_bc >= 4, f"gaps must never go below the 4px floor, got {gap_ab}, {gap_bc}"
print("tier 2 (compact), genuine interpolation path: OK")

# --- Tier 2 with a sub-floor/overlapping input gap -- regression guard. A naive
#     "max_possible_reduction = total_gap - (n-1)*min_gap" formula credits a
#     below-floor (or negative/overlapping) gap as if it were reducible slack, which
#     silently returns a layout WIDER than target_dim. b and c below overlap by 20px
#     in the source (b covers 150-250, c starts at 230).
items = [("a", 0, 100), ("b", 150, 100), ("c", 230, 100)]
result = fit_axis(items, target_dim=315)
span = result["c"]["pos"] + result["c"]["size"] - result["a"]["pos"]
assert span <= 315, f"tier 2 must still fit target_dim even with a sub-floor input gap, got span={span}"
gap_ab = result["b"]["pos"] - (result["a"]["pos"] + result["a"]["size"])
gap_bc = result["c"]["pos"] - (result["b"]["pos"] + result["b"]["size"])
assert gap_ab >= 4 and gap_bc >= 4, f"gaps must never go below the 4px floor, got {gap_ab}, {gap_bc}"
print("tier 2 (compact), sub-floor input gap regression guard: OK")

# --- Tier 2 with many gaps -- regression guard for rounding drift COMPOUNDING across
#     several gaps. An earlier fix rounded each position incrementally off the
#     previous ROUNDED position, which still let up to ~0.5px of error per gap
#     accumulate across many gaps and occasionally push the final span a few px over
#     target_dim even though each individual gap still met the 4px floor -- caught by
#     this exact case during that fix's own re-review. Flooring (not rounding) each
#     gap before accumulating positions closes this for good (see the implementation's
#     comment).
items = [("i0", 0, 100), ("i1", 149, 69), ("i2", 254, 56), ("i3", 346, 106), ("i4", 509, 94), ("i5", 622, 56)]
result = fit_axis(items, target_dim=637)
span = max(v["pos"] + v["size"] for v in result.values()) - min(v["pos"] for v in result.values())
assert span <= 637, f"tier 2 must not overshoot target_dim via rounding drift across many gaps, got span={span}"
sorted_ids = sorted(result, key=lambda i: result[i]["pos"])
for i in range(len(sorted_ids) - 1):
    a, b = result[sorted_ids[i]], result[sorted_ids[i + 1]]
    gap = b["pos"] - (a["pos"] + a["size"])
    assert gap >= 4, f"gap must never go below the 4px floor, got {gap}"
print("tier 2 (compact), many-gaps rounding-drift regression guard: OK")

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
    span = max(v["pos"] + v["size"] for v in result.values()) - min(v["pos"] for v in result.values())
    assert span <= target, f"fitted group must fit target_dim={target}, got span={span}"
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = result[ids[i]], result[ids[j]]
            assert not overlaps(a["pos"], a["size"], b["pos"], b["size"]), f"overlap at target_dim={target}: {ids[i]} vs {ids[j]}"
print("no-overlap guarantee AND target_dim-fit across all tiers: OK")

# --- fit_axis is a generic (id, pos, size) fitter -- it works identically on row
#     pseudo-items (Task 6 will feed it "__row0"-style keys), not just element ids.
row_items = [("__row0", 0, 90), ("__row1", 114, 90)]
row_result = fit_axis(row_items, target_dim=300)
assert row_result["__row0"]["scale"] == 1.0 and row_result["__row1"]["scale"] == 1.0
print("generic over row pseudo-items too: OK")

print("\nTASK 3: fit_axis -- ALL CHECKS PASSED")
