"""Custom-mode component styling (generator/style.py, Stage 1): catalog correctness
against the real SDK schema, then applying real style values to a real component's
CSS in a scratch copy of GenTestProject2, verified on disk.
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))

import compare  # noqa: E402
import layout  # noqa: E402
import sdk as sdk_module  # noqa: E402
import style  # noqa: E402

ui_sdk = sdk_module.read_sdk("2.18.0")

# --- style_property_catalog: real schema shape, no invented properties ----------------
catalog = style.style_property_catalog(ui_sdk, "ch5-button")

bg = style.find_property(catalog, ".ch5-button--default", "background-color")
assert bg["target_property"] == "--ch5-button--default-background-color", bg
border_color = style.find_property(catalog, ".ch5-button--default", "border-color")
assert border_color["target_property"] == "--ch5-button--default-border-color"
border_width = style.find_property(catalog, ".ch5-button--default", "border-width")
assert border_width["target_property"] == "--ch5-button--default-border-width"
label_color = style.find_property(catalog, ".ch5-button--default .ch5-button--label", "color")
assert label_color["target_property"] == "--ch5-button--default-label-font-color"
icon_color = style.find_property(catalog, ".ch5-button--default .ch5-button--icon", "color")
assert icon_color["target_property"] == "--ch5-button--default-icon-color"
print("style_property_catalog matches the real ch5-button schema: OK")

assert not any(e["source_property"] in ("width", "height") for e in catalog), \
    "width/height belong to component.py's sizing mechanism, not the style catalog"
print("width/height are correctly excluded from the style catalog: OK")

try:
    style.find_property(catalog, ".ch5-button--default", "not-a-real-property")
    raise AssertionError("expected KeyError for a nonexistent property")
except KeyError:
    pass
print("a nonexistent property raises KeyError rather than silently matching: OK")

# --- set_component_style: applied to a real component in a scratch copy ---------------
SRC = Path(r"C:\Solutions\ClaudeGenTest\GenTestProject2")
OUT = Path(__file__).resolve().parent / "CustomStyle"
if OUT.exists():
    shutil.rmtree(OUT)
shutil.copytree(SRC, OUT)
page_path = OUT / "ButtonVariants.cuig"

raw_before = page_path.read_text(encoding="utf-8")
parsed = compare.split_sections(raw_before, ".cuig")
css_before = next(c for n, _, c in parsed.sections if n == "Css")

elements_before = layout.parse_all_position_rules(css_before, "(max-width: 99999px)")
before = elements_before["ibtnicon"]
assert before["width"] == 150 and before["height"] == 50 and before["left"] == 20 and before["top"] == 20
print("baseline: ibtnicon's existing position/size confirmed before any style edit: OK")

new_css = style.set_component_style(
    css_before, "ibtnicon", ui_sdk, "ch5-button",
    [
        (".ch5-button--default", "background-color", "#112233"),
        (".ch5-button--default", "border-color", "#445566"),
        (".ch5-button--default .ch5-button--label", "color", "#ffffff"),
    ],
)

# --- verify the target element gained exactly the new declarations, nothing else lost -
after = layout.parse_all_position_rules(new_css, "(max-width: 99999px)")["ibtnicon"]
assert after["left"] == before["left"] and after["top"] == before["top"]
assert after["width"] == before["width"] and after["height"] == before["height"]
assert after["extra_vars"]["--ch5-button--regular-width"] == "150px"
assert after["extra_vars"]["--ch5-button--regular-height"] == "50px"
assert after["extra_vars"]["--ch5-button--default-background-color"] == "#112233"
assert after["extra_vars"]["--ch5-button--default-border-color"] == "#445566"
assert after["extra_vars"]["--ch5-button--default-label-font-color"] == "#ffffff"
print("ibtnicon: new style vars added, pre-existing position/size/size-vars preserved: OK")

# --- a sibling element the caller did NOT touch is completely unaffected --------------
sibling_before = elements_before["ibtnimage"]
sibling_after = layout.parse_all_position_rules(new_css, "(max-width: 99999px)")["ibtnimage"]
assert sibling_before == sibling_after
print("ibtnimage (untouched sibling): completely unaffected: OK")

# --- applying again with a different value UPDATES in place, no duplicate declaration -
newer_css = style.set_component_style(
    new_css, "ibtnicon", ui_sdk, "ch5-button",
    [(".ch5-button--default", "background-color", "#000000")],
)
final = layout.parse_all_position_rules(newer_css, "(max-width: 99999px)")["ibtnicon"]
assert final["extra_vars"]["--ch5-button--default-background-color"] == "#000000"
# NOTE: count WITHIN ibtnicon's own #id{} rule specifically, not across the whole file --
# the same var NAME can legitimately appear once per differently-styled button (each in
# its own #id{} rule); a whole-file substring count would be a false positive once more
# than one real button in the project has ever been given a custom background live.
ibtnicon_span = layout.find_media_block_spans(newer_css, "(max-width: 99999px)")
ibtnicon_rule = next(
    newer_css[s:e] for s, e in ibtnicon_span if '#ibtnicon{' in newer_css[s:e] or '#ibtnicon {' in newer_css[s:e]
)
raw_rule_count = ibtnicon_rule.count("--ch5-button--default-background-color")
assert raw_rule_count == 1, f"expected the var written exactly once within ibtnicon's own rule, found {raw_rule_count}"
print("re-applying a style property updates in place, no duplicate declaration: OK")

# --- per-resolution device block is untouched -- style is not resolution-dependent ----
device_query = layout.landscape_media_query(1280, 800)
device_elements = layout.parse_all_position_rules(newer_css, device_query)
if "ibtnicon" in device_elements:
    assert "--ch5-button--default-background-color" not in device_elements["ibtnicon"].get("extra_vars", {}), \
        "style properties must live only in the catch-all block, not per-resolution device blocks"
print("device block (if any) carries no style vars -- catch-all only, per design: OK")

# --- write back to disk and confirm the file still round-trips section-for-section ----
new_sections = [
    (name, header, newer_css if name == "Css" else content)
    for name, header, content in parsed.sections
]
rebuilt = parsed.preamble + "".join(header + content for _, header, content in new_sections)
page_path.write_text(rebuilt, encoding="utf-8", newline="")
assert compare.round_trip_check(page_path)
print("the rewritten .cuig still round-trips section-for-section: OK")

# --- a style property Stage 1 deliberately excludes (no targetProperty) is refused, ----
# --- not silently applied wrong (ch5-text's letter-spacing has no targetProperty) -----
text_catalog = style.style_property_catalog(ui_sdk, "ch5-text")
try:
    style.find_property(text_catalog, "idSelector", "letter-spacing")
    raise AssertionError("expected letter-spacing (no targetProperty) to be excluded from the Stage-1 catalog")
except KeyError:
    pass
print("a no-targetProperty property (Stage 1's own deferred scope) is correctly excluded: OK")

print("\nCustom-mode style (Stage 1): all assertions passed.")
