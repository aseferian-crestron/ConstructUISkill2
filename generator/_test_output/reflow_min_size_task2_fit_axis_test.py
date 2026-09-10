"""Task 2: fit_axis's Tier 3 becomes minimum-size-aware -- iterative freeze-and-
redistribute (the same shape as CSS flexbox's shrink-with-min-width), gated so that
omitting `min_sizes` runs the untouched legacy one-shot formula. See
docs/superpowers/specs/2026-09-10-reflow-min-size-design.md."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reflow import fit_axis, AxisFitError  # noqa: E402

# --- The spec's hand-traced example: one item freezes, two don't --------------------
# 3x100px items, target 100, min_gap 4 -> available_for_sizes = 92; mins a=60.
# Round 1: scale 92/300=0.307 -> a would be 30.7 < 60, freezes at 60.
# Round 2: free 32 over 200 -> scale 0.16 -> b,c = 16 each, no new freezes.
items = [("a", 0, 100), ("b", 200, 100), ("c", 400, 100)]
result = fit_axis(items, target_dim=100, min_sizes={"a": 60, "b": 1, "c": 1})
assert result["a"]["size"] == 60, f"frozen at its own minimum, got {result['a']['size']}"
assert result["b"]["size"] == 16 and result["c"]["size"] == 16, result
assert (result["a"]["pos"], result["b"]["pos"], result["c"]["pos"]) == (0, 64, 84), result
assert result["c"]["pos"] + result["c"]["size"] == 100, "packs to exactly target_dim"
assert abs(result["a"]["scale"] - 0.6) < 1e-9, "a frozen item reports its OWN ratio"
assert abs(result["b"]["scale"] - 0.16) < 1e-9, result["b"]["scale"]
print("hand-traced freeze example (60/16/16, packed to exactly 100): OK")

# --- No item needs freezing -> identical to plain Tier 3 (regression guard) ---------
items = [("a", 0, 100), ("b", 200, 100), ("c", 400, 100)]
legacy = fit_axis(items, target_dim=200)
with_mins = fit_axis(items, target_dim=200, min_sizes={"a": 10, "b": 10, "c": 10})
assert legacy == with_mins, f"no freeze must match legacy exactly\n{legacy}\n{with_mins}"
print("no-freeze case matches legacy output exactly: OK")

# --- Omitting min_sizes entirely reproduces today's exact output --------------------
# (Crowded enough that the flat 1px floor and the iterative algorithm would genuinely
# disagree -- the legacy branch must not change.)
items = [("a", 0, 100), ("b", 200, 100), ("c", 400, 100)]
before = fit_axis(items, target_dim=10)   # available_for_sizes = 2 over 300
assert [before[i]["size"] for i in "abc"] == [1, 1, 1], before
assert all(abs(before[i]["scale"] - 2 / 300) < 1e-9 for i in "abc"), "flat group scale"
# The legacy path's documented, deliberate overshoot: three 1px items at a 4px floor
# span 11px against a target of 10. The dict branch does NOT overshoot -- which is
# exactly why omitting min_sizes has to stay a separate code path.
assert before["c"]["pos"] + before["c"]["size"] == 11, before
print("legacy branch (min_sizes omitted) unchanged, 1px floor + flat scale: OK")

# --- Unsatisfiable: every minimum together doesn't fit -> AxisFitError --------------
try:
    fit_axis(items, target_dim=100, min_sizes={"a": 60, "b": 60, "c": 60})
except AxisFitError as e:
    assert "minimum size" in str(e), f"error must name the new cause, got {e!r}"
    print(f"unsatisfiable minimums raise AxisFitError: OK ({e})")
else:
    raise AssertionError("expected AxisFitError when sum(mins) > available_for_sizes")

# --- Cascading freeze: freezing one item pushes a second under its own floor --------
# 4 items, sizes 100/100/100/100, target 250 -> available = 250 - 3*4 = 238.
# Round 1: scale .595 -> a (min 100) freezes. Round 2: free 138/300 = .46 -> b (min 50)
# freezes. Round 3: free 88/200 = .44 -> c,d = 44 each, no more freezes.
items4 = [("a", 0, 100), ("b", 200, 100), ("c", 400, 100), ("d", 600, 100)]
r = fit_axis(items4, target_dim=250, min_sizes={"a": 100, "b": 50, "c": 1, "d": 1})
assert r["a"]["size"] == 100 and r["b"]["size"] == 50, r
assert r["c"]["size"] == 44 and r["d"]["size"] == 44, r
assert r["d"]["pos"] + r["d"]["size"] == 250, (
    "the dict branch reserves each frozen floor exactly, so it packs to target_dim "
    "with no overshoot -- unlike the legacy branch's independent 1px floors")
print("cascading freeze (a then b, c/d absorb the rest): OK")

# --- Shrink-only clamp: a floor above the item's own size never grows it ------------
# `b` is 20px in the source but its component type's floor is 60 -- Tier 3 must leave
# it at (or below) 20, never inflate it, and the pre-check must not reject the axis.
items = [("a", 0, 100), ("b", 200, 20), ("c", 400, 100)]
r = fit_axis(items, target_dim=120, min_sizes={"a": 30, "b": 60, "c": 30})
assert r["b"]["size"] <= 20, f"an already-undersized item must never grow, got {r['b']}"
assert r["a"]["size"] >= 30 and r["c"]["size"] >= 30, r
assert r["c"]["pos"] + r["c"]["size"] <= 120, r
print("shrink-only clamp on an already-undersized item: OK")

# --- An id absent from the dict defaults to a floor of 1 (not the fallback) ---------
items = [("a", 0, 100), ("b", 200, 100)]
r = fit_axis(items, target_dim=80, min_sizes={"a": 60})
assert r["a"]["size"] == 60 and r["b"]["size"] == 16, r
print("id absent from min_sizes defaults to 1: OK")

# --- min_sizes={} is the dict branch, not the legacy branch, and still fits ---------
r = fit_axis(items, target_dim=80, min_sizes={})
assert r["b"]["pos"] + r["b"]["size"] <= 80, r
print("empty dict takes the dict branch without error: OK")

# --- Tiers 1/2 are unaffected by min_sizes -----------------------------------------
items = [("a", 800, 100), ("b", 950, 100)]  # span 250, fits 300 -> Tier 1
r = fit_axis(items, target_dim=300, min_sizes={"a": 999, "b": 999})
assert r["a"]["size"] == 100 and r["b"]["size"] == 100 and r["a"]["scale"] == 1.0
assert r["b"]["pos"] - (r["a"]["pos"] + r["a"]["size"]) == 50, "Tier 1 gap preserved"
print("Tier 1 ignores min_sizes entirely (nothing shrinks there): OK")

# --- Centering still applies on top of a frozen result ------------------------------
items = [("a", 0, 100), ("b", 200, 100), ("c", 400, 100)]
r = fit_axis(items, target_dim=140, min_sizes={"a": 40, "b": 40, "c": 40}, center=True)
left = min(v["pos"] for v in r.values())
right = 140 - max(v["pos"] + v["size"] for v in r.values())
assert abs(left - right) <= 1, f"centered result, got margins {left}/{right}"
print("centering composes with frozen sizes: OK")

print("\nTask 2: all assertions passed.")
