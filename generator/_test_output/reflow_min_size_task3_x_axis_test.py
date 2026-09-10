"""Task 3: _fit_group derives each COLUMN's width floor (max over its members) and
hands it to fit_axis's minimum-aware Tier 3. See docs/superpowers/specs/
2026-09-10-reflow-min-size-design.md.

IMPORTANT scope note, established while implementing this task (the spec assumed the
X axis was symmetric with the Y axis -- it isn't): a row can only ever reach X-axis
Tier 3 with a SINGLE column. wrap_rows' peel loop exits only when the remainder
passes _columns_fit (i.e. Tier 2 compaction alone will fit it, so Tier 3 is never
reached) or when one column is left (which can't be peeled further). So the
freeze-some-items-and-redistribute behavior is genuinely unreachable on X through
_fit_group; what the floor does here is turn "silently emit a component narrower than
its own technical minimum" into an AxisFitError -- the spec's chosen failure mode --
which _fit_group already reports as a warning and a skipped block. The reported
28px-tall-button bug is a Y-axis (stack_rows) case; see task 4."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reflow import _fit_group, wrap_rows, detect_rows, FALLBACK_MIN_SIZE_PX  # noqa: E402
from sdk import read_sdk  # noqa: E402

ui_sdk = read_sdk("2.18.0")
PATH = Path("Fake.cuig")

# --- The unreachability above is a property of wrap_rows, so pin it -----------------
elements = {
    f"b{i}": {"left": i * 210, "top": 0, "width": 200, "height": 100, "extra_vars": {}}
    for i in range(4)
}
wrapped = wrap_rows(detect_rows(elements), elements, 160)
assert all(len(columns) == 1 for columns, _ in wrapped), (
    f"a row reaching X Tier 3 always has exactly one column, got {wrapped}")
print("wrap_rows leaves single-column rows for Tier 3 (multi-item X freeze unreachable): OK")

# --- A component whose own schema floor can't be met on X -> warn and skip ----------
# A ch5-keypad (schema minWidth 210px) authored 400px wide, into a 150px-wide target:
# Tier 3 would silently emit a 150px keypad, which Construct itself won't render at
# that size. With the SDK wired in, the block is skipped with a warning instead.
elements = {"pad": {"left": 0, "top": 0, "width": 400, "height": 300, "extra_vars": {}}}
warnings: list[str] = []
fitted = _fit_group(
    elements, target_width=150, target_height=400, source_width=1280, source_height=800,
    path=PATH, query="q", warnings=warnings, id_to_tag={"pad": "ch5-keypad"}, sdk=ui_sdk,
)
assert fitted is None, f"expected the block to be skipped, got {fitted}"
assert len(warnings) == 1 and "minimum size" in warnings[0], warnings
assert "210px total" in warnings[0], f"the keypad's own schema floor, got {warnings[0]}"
print(f"keypad below its 210px schema floor -> skipped with a warning: OK ({warnings[0]})")

# --- Same shape without an SDK: today's behavior, silently under the floor ----------
warnings = []
legacy = _fit_group(
    elements, target_width=150, target_height=400, source_width=1280, source_height=800,
    path=PATH, query="q", warnings=warnings,
)
assert legacy is not None and warnings == [], (legacy, warnings)
assert legacy["pad"]["width"] == 150, legacy
print("legacy no-sdk call unchanged (still emits the 150px keypad): OK")

# --- A satisfiable floor is a no-op: the fit is identical to legacy's ---------------
# Same keypad into a 300px target: 300 >= its 210px floor, so nothing freezes and the
# floors must not perturb the result at all.
warnings = []
with_sdk = _fit_group(
    elements, target_width=300, target_height=400, source_width=1280, source_height=800,
    path=PATH, query="q", warnings=warnings, id_to_tag={"pad": "ch5-keypad"}, sdk=ui_sdk,
)
warnings_legacy: list[str] = []
no_sdk = _fit_group(
    elements, target_width=300, target_height=400, source_width=1280, source_height=800,
    path=PATH, query="q", warnings=warnings_legacy,
)
assert warnings == [] and warnings_legacy == []
assert with_sdk["pad"]["width"] == no_sdk["pad"]["width"] == 300, (with_sdk, no_sdk)
assert with_sdk["pad"]["width"] >= 210
print("a satisfiable floor changes nothing vs. legacy: OK")

# --- Column floors are the MAX over the column's members ---------------------------
# A dpad (floor 100) stacked with a button (floor 30) in one column: the column's
# single fitted width has to satisfy the dpad, so 100 is what gets reserved.
elements = {
    "pad":  {"left": 0, "top": 0, "width": 300, "height": 300, "extra_vars": {}},
    "btn":  {"left": 0, "top": 320, "width": 300, "height": 80, "extra_vars": {}},
}
warnings = []
fitted = _fit_group(
    elements, target_width=60, target_height=800, source_width=1280, source_height=800,
    path=PATH, query="q", warnings=warnings,
    id_to_tag={"pad": "ch5-dpad", "btn": "ch5-button"}, sdk=ui_sdk,
)
assert fitted is None and len(warnings) == 1, (fitted, warnings)
assert "100px total" in warnings[0], f"the dpad's floor, not the button's, got {warnings[0]}"
print(f"column floor is the max over its members (dpad's 100, not the button's "
      f"{FALLBACK_MIN_SIZE_PX}): OK")

# --- Stacked column members still share one left, floors or not --------------------
warnings = []
fitted = _fit_group(
    elements, target_width=200, target_height=800, source_width=1280, source_height=800,
    path=PATH, query="q", warnings=warnings,
    id_to_tag={"pad": "ch5-dpad", "btn": "ch5-button"}, sdk=ui_sdk,
)
assert fitted is not None and warnings == [], (fitted, warnings)
assert fitted["pad"]["left"] == fitted["btn"]["left"], "a column travels together"
assert fitted["pad"]["width"] >= 100, fitted["pad"]
print("stacked column keeps a shared left and clears the dpad's floor: OK")

print("\nTask 3: all assertions passed.")
