"""Palette layer (generator/palette.py, Stage 2): the curated ch5-button mapping
resolves against the real schema catalog (self-check, catching drift), then
apply_palette applied to a real button in a scratch copy of GenTestProject2.
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))

import color_words as color_words_module  # noqa: E402
import compare  # noqa: E402
import layout  # noqa: E402
import palette  # noqa: E402
import sdk as sdk_module  # noqa: E402
import style  # noqa: E402

ui_sdk = sdk_module.read_sdk("2.18.0")

# --- self-check: EVERY curated mapping (every tag in PALETTE_MAPPING) resolves --------
# --- against its own real schema catalog, catching drift if the SDK schema changes ----
for tag_name, mapping in palette.PALETTE_MAPPING.items():
    catalog = style.style_property_catalog(ui_sdk, tag_name)
    for key, (class_name, source_property) in mapping.items():
        entry = style.find_property(catalog, class_name, source_property)
        assert entry["target_property"], (tag_name, key, entry)
print(f"every entry across all {len(palette.PALETTE_MAPPING)} curated palette mappings "
      f"resolves against its own real schema: OK")

assert "ch5-button" in palette.supported_tags()
assert set(palette.supported_tags()) == set(palette.PALETTE_MAPPING)
print("supported_tags() correctly reports every curated type: OK")

# --- NO_STYLABLE_PROPERTIES types are confirmed to have a genuinely empty catalog -----
for tag_name in palette.NO_STYLABLE_PROPERTIES:
    assert style.style_property_catalog(ui_sdk, tag_name) == [], tag_name
    assert tag_name not in palette.PALETTE_MAPPING
print(f"every one of the {len(palette.NO_STYLABLE_PROPERTIES)} NO_STYLABLE_PROPERTIES "
      f"types genuinely has an empty style catalog (not just unmapped): OK")

# --- applicable_subset: filters a shared palette down to what each type supports ------
shared = {"background_color": "#123456", "text_color": "#abcdef", "icon_color": "#fedcba"}
assert palette.applicable_subset("ch5-button", shared) == shared  # button has all 3
assert palette.applicable_subset("ch5-qrcode", shared) == {}  # qrcode has none of these
assert palette.applicable_subset("ch5-toggle", shared) == {"text_color": "#abcdef", "icon_color": "#fedcba"}
print("applicable_subset correctly filters a shared palette per component type: OK")

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

# --- derive_states: standard-practice pressed/selected derivation from normal only ----
normal_only = {"background_color": "#204060", "border_color": "#80c0ff",
              "border_width": "2px", "text_color": "#ffffff", "icon_color": "#ffcc00"}
derived = palette.derive_states(normal_only)
assert derived["pressed_background_color"] == color_words_module.adjust_lightness(
    "#204060", palette.PRESSED_LIGHTNESS_DELTA)
assert derived["selected_background_color"] == color_words_module.adjust_lightness(
    "#204060", palette.SELECTED_LIGHTNESS_DELTA)
# border/text/icon carry over UNCHANGED to both states -- standard button practice
assert derived["pressed_border_color"] == derived["selected_border_color"] == "#80c0ff"
assert derived["pressed_border_width"] == derived["selected_border_width"] == "2px"
assert derived["pressed_text_color"] == derived["selected_text_color"] == "#ffffff"
assert derived["pressed_icon_color"] == derived["selected_icon_color"] == "#ffcc00"
print("derive_states: pressed darkens, selected lightens, everything else carries over: OK")

# An explicitly-set pressed_*/selected_* value is never overwritten by the derivation.
explicit = {"background_color": "#204060", "pressed_background_color": "#000000"}
derived2 = palette.derive_states(explicit)
assert derived2["pressed_background_color"] == "#000000"  # honored, not overwritten
assert derived2["selected_background_color"] == color_words_module.adjust_lightness(
    "#204060", palette.SELECTED_LIGHTNESS_DELTA)  # still derived
print("derive_states never overwrites an explicitly-set pressed_/selected_ key: OK")

# --- end-to-end: a derived 3-state palette applied to a real button -------------------
new_css2 = palette.apply_palette(css_before, "ibtnicon", ui_sdk, "ch5-button", derived)
after2 = layout.parse_all_position_rules(new_css2, "(max-width: 99999px)")["ibtnicon"]
v = after2["extra_vars"]
assert v["--ch5-button--default-background-color"] == "#204060"
assert v["--ch5-button--default-pressed-background-color"] == derived["pressed_background_color"]
assert v["--ch5-button--default-selected-background-color"] == derived["selected_background_color"]
assert v["--ch5-button--default-pressed-border-color"] == "#80c0ff"
assert v["--ch5-button--default-selected-label-font-color"] == "#ffffff"
print("a derived 3-state palette applies normal+pressed+selected vars to a real button: OK")

print("\nPalette (Stage 2): all assertions passed.")
