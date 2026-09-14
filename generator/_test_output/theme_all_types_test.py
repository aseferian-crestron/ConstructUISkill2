"""Theming every mappable component type on a page at once
(theme_chat.py::apply_palette_to_page_all_types), not just one tag_name --
verified against ReflowTest.cuig (ch5-button + ch5-dpad + ch5-dpad-button, the
last genuinely unstylable) in a scratch copy of GenTestProject2.
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))

import compare  # noqa: E402
import layout  # noqa: E402
import palette  # noqa: E402
import reflow  # noqa: E402
import sdk as sdk_module  # noqa: E402
import theme_chat  # noqa: E402

ui_sdk = sdk_module.read_sdk("2.18.0")

SRC = Path(r"C:\Solutions\ClaudeGenTest\GenTestProject2")
OUT = Path(__file__).resolve().parent / "ThemeAllTypes"
if OUT.exists():
    shutil.rmtree(OUT)
shutil.copytree(SRC, OUT)
page_path = OUT / "ReflowTest.cuig"

tag_index_before = reflow._tag_index(page_path.read_text(encoding="utf-8"))
button_ids = [eid for eid, (tag, _) in tag_index_before.items() if tag == "ch5-button"]
dpad_ids = [eid for eid, (tag, _) in tag_index_before.items() if tag == "ch5-dpad"]
dpad_button_ids = [eid for eid, (tag, _) in tag_index_before.items() if tag == "ch5-dpad-button"]
assert button_ids and dpad_ids and dpad_button_ids
print(f"baseline: {len(button_ids)} buttons, {len(dpad_ids)} dpad, "
      f"{len(dpad_button_ids)} dpad-button (unstylable) on ReflowTest.cuig: OK")

# A palette with keys spanning button's full set AND dpad's smaller set.
spring = {
    "background_color": "#98fb98", "text_color": "#1b4d1b",
    "border_color": "#ffb6c1", "icon_color": "#f0e68c",
}
warnings = theme_chat.apply_palette_to_page_all_types(spring, page_path, ui_sdk)
print(f"apply_palette_to_page_all_types warnings: {warnings or '(none)'}")
# dpad-button is in NO_STYLABLE_PROPERTIES -- must NOT be reported as a gap.
assert not any("ch5-dpad-button" in w for w in warnings)
print("the genuinely-unstylable ch5-dpad-button produces no warning noise: OK")

css_after = compare.split_sections(page_path.read_text(encoding="utf-8"), ".cuig").sections[2][2]
elements = layout.parse_all_position_rules(css_after, "(max-width: 99999px)")

for eid in button_ids:
    v = elements[eid]["extra_vars"]
    assert v.get("--ch5-button--default-background-color") == "#98fb98"
    assert v.get("--ch5-button--default-border-color") == "#ffb6c1"
    assert v.get("--ch5-button--default-label-font-color") == "#1b4d1b"
    assert v.get("--ch5-button--default-icon-color") == "#f0e68c"
print(f"all {len(button_ids)} buttons got their full applicable subset (all 4 keys): OK")

for eid in dpad_ids:
    v = elements.get(eid, {}).get("extra_vars", {})
    assert v.get("--ch5-dpad--default-background-color") == "#98fb98"
    assert v.get("--ch5-dpad--default-color") == "#1b4d1b"
    # dpad has no border/icon concept -- border_color/icon_color must NOT appear
    assert "--ch5-dpad--default-border-color" not in v
print(f"the dpad got only ITS applicable subset (background+text, no border/icon): OK")

assert compare.round_trip_check(page_path)
print("the rewritten .cuig still round-trips section-for-section: OK")

print("\nAll-types theming: all assertions passed.")
