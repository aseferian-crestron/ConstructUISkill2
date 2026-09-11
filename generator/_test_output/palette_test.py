"""Palette layer (generator/palette.py, Stage 2): the curated ch5-button mapping
resolves against the real schema catalog (self-check, catching drift), then
apply_palette applied to a real button in a scratch copy of GenTestProject2.
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))

import compare  # noqa: E402
import layout  # noqa: E402
import palette  # noqa: E402
import sdk as sdk_module  # noqa: E402
import style  # noqa: E402

ui_sdk = sdk_module.read_sdk("2.18.0")

# --- self-check: every entry in the curated button palette resolves against the real --
# --- schema catalog, catching drift if the SDK's schema ever changes shape ------------
catalog = style.style_property_catalog(ui_sdk, "ch5-button")
for key, (class_name, source_property) in palette._BUTTON_PALETTE.items():
    entry = style.find_property(catalog, class_name, source_property)
    assert entry["target_property"].startswith("--ch5-button--"), entry
print("every _BUTTON_PALETTE entry resolves against the real ch5-button schema: OK")

assert palette.supported_tags() == ["ch5-button"]
print("supported_tags() correctly reports only the verified type: OK")

# --- unknown tag / unknown key raise clearly, before writing anything -----------------
try:
    palette.apply_palette("css", "ibtnicon", ui_sdk, "ch5-toggle", {"background_color": "#000"})
    raise AssertionError("expected KeyError for an unmapped tag")
except KeyError:
    pass
print("an unmapped component type raises KeyError: OK")

try:
    palette.apply_palette("css", "ibtnicon", ui_sdk, "ch5-button", {"not_a_real_key": "#000"})
    raise AssertionError("expected KeyError for an unmapped palette key")
except KeyError:
    pass
print("an unmapped palette key raises KeyError: OK")

# --- apply_palette against a real button in a scratch copy of GenTestProject2 ---------
SRC = Path(r"C:\Solutions\ClaudeGenTest\GenTestProject2")
OUT = Path(__file__).resolve().parent / "Palette"
if OUT.exists():
    shutil.rmtree(OUT)
shutil.copytree(SRC, OUT)
page_path = OUT / "ButtonVariants.cuig"

raw_before = page_path.read_text(encoding="utf-8")
parsed = compare.split_sections(raw_before, ".cuig")
css_before = next(c for n, _, c in parsed.sections if n == "Css")

before = layout.parse_all_position_rules(css_before, "(max-width: 99999px)")["ibtncheck"]
assert before["width"] == 150 and before["left"] == 420
print("baseline: ibtncheck's position/size confirmed before any palette edit: OK")

new_css = palette.apply_palette(
    css_before, "ibtncheck", ui_sdk, "ch5-button",
    {
        "background_color": "#204060",
        "border_color": "#80c0ff",
        "border_width": "2px",
        "text_color": "#ffffff",
        "icon_color": "#ffcc00",
    },
)

after = layout.parse_all_position_rules(new_css, "(max-width: 99999px)")["ibtncheck"]
assert after["left"] == before["left"] and after["width"] == before["width"]
assert after["extra_vars"]["--ch5-button--default-background-color"] == "#204060"
assert after["extra_vars"]["--ch5-button--default-border-color"] == "#80c0ff"
assert after["extra_vars"]["--ch5-button--default-border-width"] == "2px"
assert after["extra_vars"]["--ch5-button--default-label-font-color"] == "#ffffff"
assert after["extra_vars"]["--ch5-button--default-icon-color"] == "#ffcc00"
print("ibtncheck: all 5 palette keys resolved and written, position/size preserved: OK")

# --- write back to disk and confirm the file still round-trips ------------------------
new_sections = [
    (name, header, new_css if name == "Css" else content)
    for name, header, content in parsed.sections
]
rebuilt = parsed.preamble + "".join(header + content for _, header, content in new_sections)
page_path.write_text(rebuilt, encoding="utf-8", newline="")
assert compare.round_trip_check(page_path)
print("the rewritten .cuig still round-trips section-for-section: OK")

print("\nPalette (Stage 2): all assertions passed.")
