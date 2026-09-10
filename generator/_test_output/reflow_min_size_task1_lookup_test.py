"""Task 1: _component_min_size -- per-component minimum size from the SDK's own
`minSizes` schema entry, with a module-constant fallback for the (many) types the
schema doesn't constrain. See docs/superpowers/specs/2026-09-10-reflow-min-size-design.md."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reflow import FALLBACK_MIN_SIZE_PX, _component_min_size, _parse_min_size  # noqa: E402
from sdk import read_sdk  # noqa: E402

ui_sdk = read_sdk("2.18.0")

# --- Real, schema-published technical floors ---------------------------------------
assert _component_min_size(ui_sdk, "ch5-dpad") == 100, "ch5-dpad's schema minWidth is '100px'"
assert _component_min_size(ui_sdk, "ch5-keypad") == 210, "ch5-keypad's schema minWidth is '210px'"
print("schema-published minWidth (dpad 100, keypad 210): OK")

# --- No minSizes entry at all -> the tunable fallback constant ----------------------
assert _component_min_size(ui_sdk, "ch5-button") == FALLBACK_MIN_SIZE_PX
assert _component_min_size(ui_sdk, "ch5-slider") == FALLBACK_MIN_SIZE_PX
print(f"unconstrained types fall back to {FALLBACK_MIN_SIZE_PX}px: OK")

# --- An unknown tag must never raise -- it's the fallback, same as no entry ---------
assert _component_min_size(ui_sdk, "div") == FALLBACK_MIN_SIZE_PX
assert _component_min_size(ui_sdk, "ch5-not-a-real-tag") == FALLBACK_MIN_SIZE_PX
print("unknown tag falls back without raising: OK")

# --- Value-format robustness: the schema is NOT uniformly "Npx" strings -------------
# ch5-qrcode's is the unit-less string "160"; ch5-video-switcher's is a raw JSON int.
assert _component_min_size(ui_sdk, "ch5-qrcode") == 160, "unit-less string minWidth"
assert _component_min_size(ui_sdk, "ch5-video-switcher") == 300, "raw int minWidth"
assert _parse_min_size("100px") == 100 and _parse_min_size("40") == 40
assert _parse_min_size(300) == 300 and _parse_min_size(12.7) == 12
assert _parse_min_size(None) is None and _parse_min_size("auto") is None
assert _parse_min_size("0px") == 1, "never return a 0/negative floor"
print("value parsing (px string / bare string / int / float / junk): OK")

# --- Per-axis: minHeight wins on the height axis, minWidth is its fallback ----------
assert _component_min_size(ui_sdk, "ch5-tab-button", "width") == 110
assert _component_min_size(ui_sdk, "ch5-tab-button", "height") == 68, "own minHeight"
assert _component_min_size(ui_sdk, "ch5-dpad", "height") == 100, "no minHeight -> minWidth"
assert _component_min_size(ui_sdk, "ch5-button", "height") == FALLBACK_MIN_SIZE_PX
print("per-axis lookup (minHeight preferred, minWidth fallback): OK")

print("\nTask 1: all assertions passed.")
