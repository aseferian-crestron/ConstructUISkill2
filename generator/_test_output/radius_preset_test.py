"""shape.py::apply_radius_preset applied to a real button in a scratch copy --
same discipline as custom_shape_test.py, whose confirmed shape="custom" + 4-corner
mechanism this reuses."""
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))

import compare  # noqa: E402
import layout  # noqa: E402
import sdk as sdk_module  # noqa: E402
import shape  # noqa: E402

ui_sdk = sdk_module.read_sdk("2.18.0")

assert shape.RADIUS_PRESETS == {"sharp": 0, "subtle": 4, "rounded": 12}, shape.RADIUS_PRESETS
print("RADIUS_PRESETS: sharp < subtle < rounded, in px: OK")

try:
    shape.apply_radius_preset("", "", "ibtncheck", ui_sdk, "ch5-toggle", "rounded")
    raise AssertionError("expected KeyError for an unsupported tag")
except KeyError:
    pass
print("apply_radius_preset: an unsupported tag raises KeyError before writing anything: OK")

try:
    shape.apply_radius_preset("", "", "ibtncheck", ui_sdk, "ch5-button", "square")
    raise AssertionError("expected KeyError for an unknown preset")
except KeyError:
    pass
print("apply_radius_preset: an unknown preset raises KeyError before writing anything: OK")

# --- applied to a real button in a scratch copy -----------------------------------------
SRC = Path(r"C:\Solutions\ClaudeGenTest\GenTestProject2")
OUT = Path(__file__).resolve().parent / "RadiusPreset"
if OUT.exists():
    shutil.rmtree(OUT)
shutil.copytree(SRC, OUT)
page_path = OUT / "ButtonVariants.cuig"

raw_before = page_path.read_text(encoding="utf-8")
parsed = compare.split_sections(raw_before, ".cuig")
html_before = next(c for n, _, c in parsed.sections if n == "Html")
css_before = next(c for n, _, c in parsed.sections if n == "Css")

before_tag = re.search(r'<ch5-button\b[^>]*\bid="ibtncheck"[^>]*>', html_before).group(0)
assert 'shape="rounded-rectangle"' in before_tag
print("baseline: ibtncheck starts with shape=\"rounded-rectangle\": OK")

html_after, css_after = shape.apply_radius_preset(
    html_before, css_before, "ibtncheck", ui_sdk, "ch5-button", "rounded")

after_tag = re.search(r'<ch5-button\b[^>]*\bid="ibtncheck"[^>]*>', html_after).group(0)
assert 'shape="custom"' in after_tag
print("apply_radius_preset flips shape to \"custom\": OK")

after = layout.parse_all_position_rules(css_after, "(max-width: 99999px)")["ibtncheck"]
for corner in ("top-left", "top-right", "bottom-left", "bottom-right"):
    assert after["extra_vars"][f"--ch5-button--rounded-rectangle-border-radius-{corner}"] == "12px", after["extra_vars"]
assert after["extra_vars"]["--ch5-button--regular-width"] == "150px"
assert after["left"] == 420 and after["top"] == 20
print("all 4 corners get the same preset value (12px), pre-existing position/size preserved: OK")

# --- round-trips the whole file byte-identical outside the edited values --------------
new_full = raw_before.replace(html_before, html_after).replace(css_before, css_after)
page_path.write_text(new_full, encoding="utf-8", newline="")
assert compare.round_trip_check(page_path), "radius-preset edit broke the file's round-trip"

sibling_before = re.search(r'<ch5-button\b[^>]*\bid="ibtnicon"[^>]*>', html_before).group(0)
sibling_after = re.search(r'<ch5-button\b[^>]*\bid="ibtnicon"[^>]*>', html_after).group(0)
assert sibling_before == sibling_after, "an untouched sibling button's tag changed"
print("a sibling button not passed to apply_radius_preset is completely unaffected: OK")

print("Radius preset: all assertions passed.")
