"""Task 4: stack_rows derives each ROW's height floor from its most-constrained member
(the member whose own minimum forces the largest row-level scale) and passes it into
the same minimum-aware Tier 3. This is the axis the real reported bug lives on --
buttons scaled to 28px tall at TSW-570. See docs/superpowers/specs/
2026-09-10-reflow-min-size-design.md."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reflow import stack_rows, FALLBACK_MIN_SIZE_PX  # noqa: E402
from sdk import read_sdk  # noqa: E402

ui_sdk = read_sdk("2.18.0")

# --- Four rows of 100px-tall buttons squeezed far too hard on Y --------------------
rows = [["a"], ["b"], ["c"], ["d"]]
elements = {
    eid: {"left": 0, "top": i * 150, "width": 200, "height": 100}
    for i, eid in enumerate(["a", "b", "c", "d"])
}
id_to_tag = {eid: "ch5-button" for eid in elements}

legacy = stack_rows(rows, elements, target_height=100)
assert min(v["height"] for v in legacy.values()) < FALLBACK_MIN_SIZE_PX, legacy
print(f"legacy (no sdk) still squeezes below the floor: OK "
      f"{[legacy[e]['height'] for e in 'abcd']}")

floored = stack_rows(rows, elements, target_height=160, id_to_tag=id_to_tag, sdk=ui_sdk)
heights = [floored[e]["height"] for e in "abcd"]
assert all(h >= FALLBACK_MIN_SIZE_PX for h in heights), f"floored at 30px, got {heights}"
bottom = max(v["top"] + v["height"] for v in floored.values())
assert bottom <= 160, f"must still fit target_height, got {bottom}"
print(f"buttons floored at {FALLBACK_MIN_SIZE_PX}px tall: OK {heights}")

# --- A tall component and short buttons: the tall one absorbs the shrink -----------
# The real TSW-570 shape in miniature. A dpad row (natural 400, floor 100 -- so it can
# afford to shrink to 0.25 of itself) plus two button rows (natural 100, floor 30 --
# they can't go past 0.30). Naive Tier 3 applies ONE factor to all three, so at
# target 180 the buttons land at exactly the 28px the user reported. With floors, the
# buttons freeze at 30 and the dpad absorbs the difference -- the tradeoff the user
# asked for. (Note the dpad has to be the LESS constrained row proportionally for the
# buttons to be the binding constraint; with a 300px dpad its own 100px floor binds
# first and the buttons never reach 28px before the whole stack is infeasible.)
rows = [["pad"], ["b1"], ["b2"]]
elements = {
    "pad": {"left": 0, "top": 0, "width": 400, "height": 400},
    "b1": {"left": 0, "top": 450, "width": 200, "height": 100},
    "b2": {"left": 0, "top": 600, "width": 200, "height": 100},
}
tags = {"pad": "ch5-dpad", "b1": "ch5-button", "b2": "ch5-button"}
naive = stack_rows(rows, elements, target_height=180)
floored = stack_rows(rows, elements, target_height=180, id_to_tag=tags, sdk=ui_sdk)
assert naive["b1"]["height"] == 28, f"the exact reported symptom, got {naive['b1']}"
assert naive["b1"]["height"] < FALLBACK_MIN_SIZE_PX, naive
assert floored["b1"]["height"] >= FALLBACK_MIN_SIZE_PX, floored["b1"]
assert floored["b2"]["height"] >= FALLBACK_MIN_SIZE_PX, floored["b2"]
assert floored["pad"]["height"] >= 100, f"dpad's own schema floor, got {floored['pad']}"
assert floored["pad"]["height"] < naive["pad"]["height"], (
    "the tall row is what pays for the buttons' floor", floored["pad"], naive["pad"])
bottom = max(v["top"] + v["height"] for v in floored.values())
assert bottom <= 180, f"must still fit target_height, got {bottom}"
print(f"buttons {naive['b1']['height']}px -> {floored['b1']['height']}px, dpad "
      f"{naive['pad']['height']}px -> {floored['pad']['height']}px: OK")

# --- A multi-member row: the floor comes from whoever hits their minimum first -----
# Row natural height 300 (the dpad); the 40px button needs scale 0.75 to clear its own
# 30px floor, the dpad only needs 100/300 = 0.33 -> the button decides the row's floor.
rows = [["pad", "small"]]
elements = {
    "pad": {"left": 0, "top": 0, "width": 300, "height": 300},
    "small": {"left": 400, "top": 100, "width": 100, "height": 40},
}
floored = stack_rows(
    rows, elements, target_height=280,
    id_to_tag={"pad": "ch5-dpad", "small": "ch5-button"}, sdk=ui_sdk,
)
assert floored["small"]["height"] >= FALLBACK_MIN_SIZE_PX, floored["small"]
assert max(v["top"] + v["height"] for v in floored.values()) <= 280
print(f"most-constrained member sets the row floor: OK (small "
      f"{floored['small']['height']}px, pad {floored['pad']['height']}px)")

# --- Shrink-only: a row already shorter than its derived floor is left alone -------
rows = [["tiny"]]
elements = {"tiny": {"left": 0, "top": 0, "width": 100, "height": 10}}
r = stack_rows(rows, elements, target_height=200, id_to_tag={"tiny": "ch5-button"}, sdk=ui_sdk)
assert r["tiny"]["height"] == 10, f"never grow an already-tiny element, got {r['tiny']}"
print("already-undersized row is not grown: OK")

# --- A satisfiable floor is a no-op vs. legacy ------------------------------------
rows = [["a"], ["b"]]
elements = {
    "a": {"left": 0, "top": 0, "width": 200, "height": 100},
    "b": {"left": 0, "top": 150, "width": 200, "height": 100},
}
tags = {"a": "ch5-button", "b": "ch5-button"}
assert stack_rows(rows, elements, target_height=400) == \
       stack_rows(rows, elements, target_height=400, id_to_tag=tags, sdk=ui_sdk), \
       "a fit that never reaches the floor must be byte-identical to legacy"
print("satisfiable floor is byte-identical to legacy: OK")

# --- Infeasible stack: floors are relaxed, never turned into a skipped block -------
# A single row pairing a 300px dpad with 40px buttons (floor 30 -> they may only shrink
# 25%) demands a 225px row against a 200px target. Raising AxisFitError here (the
# spec's plain failure mode) would make _fit_group drop the whole device block, i.e.
# missing components -- so the floor is relaxed and the row scales as it does today,
# with a warning saying so.
rows = [["pad", "b1", "b2"]]
elements = {
    "pad": {"left": 150, "top": 0, "width": 300, "height": 300},
    "b1": {"left": 20, "top": 100, "width": 80, "height": 40},
    "b2": {"left": 500, "top": 100, "width": 80, "height": 40},
}
tags = {"pad": "ch5-dpad", "b1": "ch5-button", "b2": "ch5-button"}
warns: list[str] = []
relaxed = stack_rows(rows, elements, target_height=200, id_to_tag=tags, sdk=ui_sdk, warnings=warns)
no_floor = stack_rows(rows, elements, target_height=200)
assert min(v["height"] for v in relaxed.values()) >= min(v["height"] for v in no_floor.values()), (
    "a relaxed stack must never crush anything below what no floor at all would give",
    relaxed, no_floor)
assert len(warns) == 1 and "can't honor every component's minimum size" in warns[0], warns
print(f"infeasible stack relaxes instead of failing: OK ({warns[0]})")

# --- Partial relaxation: only the offending row loses its floor --------------------
# Row 0 is the impossible dpad+small-button row above; rows 1/2 are ordinary button
# rows whose own floors still fit, so they must KEEP them.
rows = [["pad", "b1"], ["c1"], ["c2"]]
elements = {
    "pad": {"left": 150, "top": 0, "width": 300, "height": 300},
    "b1": {"left": 20, "top": 100, "width": 80, "height": 40},
    "c1": {"left": 0, "top": 350, "width": 200, "height": 100},
    "c2": {"left": 0, "top": 500, "width": 200, "height": 100},
}
tags = {"pad": "ch5-dpad", "b1": "ch5-button", "c1": "ch5-button", "c2": "ch5-button"}
warns = []
r = stack_rows(rows, elements, target_height=260, id_to_tag=tags, sdk=ui_sdk, warnings=warns)
assert len(warns) == 1 and "can't honor every component's minimum size" in warns[0], warns
assert r["c1"]["height"] >= FALLBACK_MIN_SIZE_PX and r["c2"]["height"] >= FALLBACK_MIN_SIZE_PX, r
assert max(v["top"] + v["height"] for v in r.values()) <= 260, r
print(f"only the offending row is relaxed, the others keep their floors: OK "
      f"(c1={r['c1']['height']}px)")

# --- The invariant the first relaxation design violated ---------------------------
# Measured against the real ReflowTest.cuig at 400x240, relaxation-by-dropping produced
# 1px buttons where NO floor at all gave 16-30px: the rows still frozen at their full
# floor ate everything and starved the relaxed ones. A floor must never be able to make
# a layout worse than having no floor, at any target height -- sweep and prove it.
rows = [["pad", "up"], ["r1"], ["r2"], ["r3"], ["r4"]]
elements = {
    "pad": {"left": 200, "top": 0, "width": 228, "height": 228},
    "up":  {"left": 20, "top": 40, "width": 106, "height": 79},
    "r1":  {"left": 0, "top": 260, "width": 500, "height": 42},
    "r2":  {"left": 0, "top": 320, "width": 500, "height": 42},
    "r3":  {"left": 0, "top": 380, "width": 500, "height": 42},
    "r4":  {"left": 0, "top": 440, "width": 500, "height": 42},
}
tags = {"pad": "ch5-dpad", "up": "ch5-button", "r1": "ch5-button",
        "r2": "ch5-button", "r3": "ch5-button", "r4": "ch5-button"}
for target_height in range(120, 420, 10):
    with_floor = stack_rows(rows, elements, target_height, id_to_tag=tags, sdk=ui_sdk, warnings=[])
    without = stack_rows(rows, elements, target_height)
    assert min(v["height"] for v in with_floor.values()) >= min(v["height"] for v in without.values()), (
        f"at target_height={target_height} the floor made the smallest component SMALLER: "
        f"{min(v['height'] for v in with_floor.values())} vs {min(v['height'] for v in without.values())}")
    assert max(v["top"] + v["height"] for v in with_floor.values()) <= target_height, target_height
print("swept 30 target heights: a floor never crushes anything below the no-floor result: OK")

print("\nTask 4: all assertions passed.")
