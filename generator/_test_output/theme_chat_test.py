"""Chat-described theming (generator/theme_chat.py): parse_style_description unit
cases, then apply_chat_style applied whole-project against a scratch copy of
GenTestProject2 -- every real ch5-button instance across every page/widget gets
the parsed palette, everything else is untouched.
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))

import compare  # noqa: E402
import layout  # noqa: E402
import reflow  # noqa: E402
import sdk as sdk_module  # noqa: E402
import theme_chat  # noqa: E402

ui_sdk = sdk_module.read_sdk("2.18.0")

# --- parse_style_description: real CSS colors, property keywords, defaults -----------
parsed = theme_chat.parse_style_description("dark blue buttons with white text and an orange border")
assert parsed == {
    "background_color": "#00008b",  # real darkblue, not blue darkened
    "text_color": "#ffffff",
    "border_color": "#ffa500",
}, parsed
print("parse_style_description: color+property extraction across 3 segments: OK")

assert theme_chat.parse_style_description("make the buttons navy") == {"background_color": "#000080"}
print("a color with no property keyword defaults to background_color: OK")

assert theme_chat.parse_style_description("light gray icon") == {"icon_color": "#d3d3d3"}
print("icon keyword resolves to icon_color: OK")

assert theme_chat.parse_style_description("make it nice and modern") == {}
print("a description with no recognizable color resolves to an empty palette: OK")

try:
    theme_chat.apply_chat_style("make it nice and modern", Path("."), ui_sdk)
    raise AssertionError("expected ValueError for a description with no color")
except ValueError:
    pass
print("apply_chat_style raises up front for an unparseable description, before touching files: OK")

# --- apply_chat_style: whole-project application against a scratch copy --------------
SRC = Path(r"C:\Solutions\ClaudeGenTest\GenTestProject2")
OUT = Path(__file__).resolve().parent / "ThemeChat"
if OUT.exists():
    shutil.rmtree(OUT)
shutil.copytree(SRC, OUT)

# Baseline: every real ch5-button instance across the whole project, before.
before_buttons: dict[str, list[str]] = {}
for page_path in list(OUT.glob("*.cuig")) + list(OUT.glob("*.cuiw")):
    idx = reflow._tag_index(page_path.read_text(encoding="utf-8"))
    ids = [eid for eid, (tag, _) in idx.items() if tag == "ch5-button"]
    if ids:
        before_buttons[page_path.name] = ids
total_before = sum(len(v) for v in before_buttons.values())
assert total_before == 24, f"expected 24 real button instances, found {total_before}"
print(f"baseline: {total_before} real ch5-button instances across {len(before_buttons)} pages: OK")

applied_palette, warnings = theme_chat.apply_chat_style(
    "dark blue buttons with white text and an orange border", OUT, ui_sdk)
print(f"apply_chat_style warnings: {warnings or '(none)'}")
assert applied_palette == {
    "background_color": "#00008b", "text_color": "#ffffff", "border_color": "#ffa500",
}

# Every single one of those 24 buttons, across every page, got all 3 values.
checked = 0
for page_name, ids in before_buttons.items():
    css = compare.split_sections((OUT / page_name).read_text(encoding="utf-8"),
                                 Path(page_name).suffix.lower()).sections[2][2]
    elements = layout.parse_all_position_rules(css, "(max-width: 99999px)")
    for eid in ids:
        v = elements[eid]["extra_vars"]
        assert v.get("--ch5-button--default-background-color") == "#00008b", (page_name, eid, v)
        assert v.get("--ch5-button--default-label-font-color") == "#ffffff", (page_name, eid, v)
        assert v.get("--ch5-button--default-border-color") == "#ffa500", (page_name, eid, v)
        checked += 1
assert checked == 24
print(f"all {checked} real button instances across every page got the full palette: OK")

# Non-button elements are completely unaffected -- spot-check ReflowTest.cuig's dpad.
css_reflow = compare.split_sections((OUT / "ReflowTest.cuig").read_text(encoding="utf-8"), ".cuig").sections[2][2]
non_button_ids = [eid for eid, (tag, _) in reflow._tag_index(
    (OUT / "ReflowTest.cuig").read_text(encoding="utf-8")).items() if tag != "ch5-button"]
assert non_button_ids, "expected at least one non-button element on ReflowTest.cuig"
catch_all_elements = layout.parse_all_position_rules(css_reflow, "(max-width: 99999px)")
for eid in non_button_ids:
    # Not every element necessarily has a catch-all rule (e.g. content-sized types
    # with no explicit size) -- only assert on ones that do; theme_chat.py only
    # ever touches real ch5-button ids, so absence here is not itself a signal.
    assert "--ch5-button--default-background-color" not in catch_all_elements.get(eid, {}).get("extra_vars", {})
print(f"{len(non_button_ids)} non-button elements on ReflowTest.cuig are completely unaffected: OK")

# Every touched file still round-trips.
for page_name in before_buttons:
    assert compare.round_trip_check(OUT / page_name)
print("every touched file still round-trips section-for-section: OK")

# --- apply_palette_project_wide: an ALREADY-RESOLVED palette (broad descriptions -----
# --- like "NY Giants colors" or "Halloween" are resolved by the driving chat AI's -----
# --- own knowledge, not a lookup table here -- see the module's own 2026-09-13 note) --
OUT2 = Path(__file__).resolve().parent / "ThemeChatResolved"
if OUT2.exists():
    shutil.rmtree(OUT2)
shutil.copytree(SRC, OUT2)

ny_giants_colors = {"background_color": "#0b2265", "text_color": "#a71930"}  # Giants Blue / Giants Red
resolved_warnings = theme_chat.apply_palette_project_wide(ny_giants_colors, OUT2, ui_sdk)
print(f"apply_palette_project_wide warnings: {resolved_warnings or '(none)'}")

checked2 = 0
for page_name, ids in before_buttons.items():
    css = compare.split_sections((OUT2 / page_name).read_text(encoding="utf-8"),
                                 Path(page_name).suffix.lower()).sections[2][2]
    elements = layout.parse_all_position_rules(css, "(max-width: 99999px)")
    for eid in ids:
        v = elements[eid]["extra_vars"]
        assert v.get("--ch5-button--default-background-color") == "#0b2265", (page_name, eid, v)
        assert v.get("--ch5-button--default-label-font-color") == "#a71930", (page_name, eid, v)
        checked2 += 1
assert checked2 == 24
print(f"apply_palette_project_wide: an already-resolved palette (no parsing involved) "
      f"applies to all {checked2} real button instances the same way: OK")

print("\nChat-described theming: all assertions passed.")
