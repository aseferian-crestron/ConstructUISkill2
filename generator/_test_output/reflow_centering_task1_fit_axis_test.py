"""Task 1: fit_axis gains source_dim/center -- a centered source group comes back
centered in target_dim instead of left where it was / packed against one edge."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reflow import fit_axis  # noqa: E402

# --- Centered source, Tier 1 path (span <= target_dim): recentered -------------------
# Two 100px items at [400,500) and [500,600) in a 1000px source -- left_margin=400,
# right_margin=1000-600=400, exactly centered. Moving to target_dim=300: span=200<=300
# (Tier 1), but the group's OWN position (400-600) overflows target_dim's right edge, so
# today's behavior clamps it flush right at [100,300) -- NOT centered in the new 300px
# canvas. With centering: expected flush-centered result is [50,150) and [150,250).
items = [("a", 400, 100), ("b", 500, 100)]
result = fit_axis(items, target_dim=300, source_dim=1000)
assert result["a"] == {"pos": 50, "size": 100, "scale": 1.0}, result["a"]
assert result["b"] == {"pos": 150, "size": 100, "scale": 1.0}, result["b"]
print("Tier 1, centered source -> centered result: OK")

# --- Same items, NO source_dim/center given: today's exact edge-anchored behavior ----
# Backward-compatibility regression guard -- must match calling fit_axis before this task.
legacy = fit_axis(items, target_dim=300)
assert legacy["a"] == {"pos": 100, "size": 100, "scale": 1.0}, legacy["a"]
assert legacy["b"] == {"pos": 200, "size": 100, "scale": 1.0}, legacy["b"]
print("No source_dim/center -> unchanged legacy edge-anchored behavior: OK")

# --- Off-center source: auto-detection correctly does NOT center ---------------------
# left_margin=400, right_margin=1000-600=400 was centered above; shift b to break
# symmetry -- items at [400,500) and [700,800): left_margin=400, right_margin=200.
off_center_items = [("a", 400, 100), ("b", 700, 100)]
result_off = fit_axis(off_center_items, target_dim=500, source_dim=1000)
legacy_off = fit_axis(off_center_items, target_dim=500)
assert result_off == legacy_off, f"off-center source must NOT be recentered, got {result_off} vs legacy {legacy_off}"
print("Off-center source -> unchanged (not centered): OK")

# --- Explicit center=True forces centering even with no source_dim -------------------
forced = fit_axis(off_center_items, target_dim=500, center=True)
assert forced != legacy_off, "center=True must force centering even for an off-center source"
min_pos = min(v["pos"] for v in forced.values())
max_pos = max(v["pos"] + v["size"] for v in forced.values())
leftover = 500 - (max_pos - min_pos)
assert min_pos == leftover // 2, f"expected centered leftover split, got min_pos={min_pos}, leftover={leftover}"
print("Explicit center=True forces centering: OK")

# --- Explicit center=False suppresses centering even with a centered source_dim ------
suppressed = fit_axis(items, target_dim=300, source_dim=1000, center=False)
assert suppressed == legacy, "center=False must suppress centering even for a centered source"
print("Explicit center=False suppresses centering: OK")

print("\nTASK 1: fit_axis centering -- ALL CHECKS PASSED")
