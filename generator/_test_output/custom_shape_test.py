"""Button shape="custom" + per-corner border-radius styling (style.py extension):
`shape` is not in ch5-button's real schema enum (rounded-rectangle/rectangle/tab/
circle/oval), the same undocumented-but-real "custom" pattern already established
for `size`. Covers set_html_attribute in isolation, then the full flow (flip shape
+ write the 4 real border-radius CSS vars) against a real button in a scratch copy
of GenTestProject2.
"""
import re
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

# --- shape isn't in the real schema enum, same undocumented pattern as size="custom" --
el = ui_sdk.schema["ch5Elements"]["elements"]
btn_def = next(e for e in el if e.get("name") == "Ch5 Button")
shape_attr = next(a for a in btn_def["attributes"] if a["name"] == "shape")
assert "custom" not in shape_attr["value"], shape_attr["value"]
print("confirmed: 'custom' is not in ch5-button's real shape enum: OK")

# --- border-radius corners ARE targetProperty-backed (Stage 1 already covers them) ----
catalog = style.style_property_catalog(ui_sdk, "ch5-button")
tl = style.find_property(catalog, ".ch5-button--rounded-rectangle", "border-top-left-radius")
tr = style.find_property(catalog, ".ch5-button--rounded-rectangle", "border-top-right-radius")
bl = style.find_property(catalog, ".ch5-button--rounded-rectangle", "border-bottom-left-radius")
br = style.find_property(catalog, ".ch5-button--rounded-rectangle", "border-bottom-right-radius")
assert tl["target_property"] == "--ch5-button--rounded-rectangle-border-radius-top-left"
assert tr["target_property"] == "--ch5-button--rounded-rectangle-border-radius-top-right"
assert bl["target_property"] == "--ch5-button--rounded-rectangle-border-radius-bottom-left"
assert br["target_property"] == "--ch5-button--rounded-rectangle-border-radius-bottom-right"
print("all 4 border-radius corners resolve to real CSS vars via the existing Stage-1 catalog: OK")

# --- set_html_attribute: isolated behavior ---------------------------------------------
SRC = Path(r"C:\Solutions\ClaudeGenTest\GenTestProject2")
OUT = Path(__file__).resolve().parent / "CustomShape"
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

html_after = style.set_html_attribute(html_before, "ibtncheck", "shape", "custom")
after_tag = re.search(r'<ch5-button\b[^>]*\bid="ibtncheck"[^>]*>', html_after).group(0)
assert 'shape="custom"' in after_tag
print("set_html_attribute replaced shape=\"rounded-rectangle\" with shape=\"custom\": OK")

# sibling elements' own shape attribute (and every other attribute) is untouched
for sibling_id in ("ibtnicon", "ibtnimage"):
    before_sib = re.search(rf'<ch5-button\b[^>]*\bid="{sibling_id}"[^>]*>', html_before).group(0)
    after_sib = re.search(rf'<ch5-button\b[^>]*\bid="{sibling_id}"[^>]*>', html_after).group(0)
    assert before_sib == after_sib, f"{sibling_id}'s tag changed unexpectedly"
print("sibling buttons' tags are completely unaffected: OK")

# inserting a brand-new attribute that doesn't already exist on the tag
html_with_new_attr = style.set_html_attribute(html_after, "ibtncheck", "ccid_customTestAttr", "hello")
new_tag = re.search(r'<ch5-button\b[^>]*\bid="ibtncheck"[^>]*>', html_with_new_attr).group(0)
assert 'ccid_customTestAttr="hello"' in new_tag
print("set_html_attribute inserts a brand-new attribute when it wasn't already present: OK")

try:
    style.set_html_attribute(html_before, "not-a-real-id", "shape", "custom")
    raise AssertionError("expected KeyError for a nonexistent element id")
except KeyError:
    pass
print("a nonexistent element id raises KeyError rather than silently no-op'ing: OK")

# --- full flow: flip shape to custom, then write real per-corner radius values --------
css_after = style.set_component_style(
    css_before, "ibtncheck", ui_sdk, "ch5-button",
    [
        (".ch5-button--rounded-rectangle", "border-top-left-radius", "20px"),
        (".ch5-button--rounded-rectangle", "border-top-right-radius", "0px"),
        (".ch5-button--rounded-rectangle", "border-bottom-left-radius", "0px"),
        (".ch5-button--rounded-rectangle", "border-bottom-right-radius", "20px"),
    ],
)
elements_after = layout.parse_all_position_rules(css_after, "(max-width: 99999px)")["ibtncheck"]
assert elements_after["extra_vars"]["--ch5-button--rounded-rectangle-border-radius-top-left"] == "20px"
assert elements_after["extra_vars"]["--ch5-button--rounded-rectangle-border-radius-top-right"] == "0px"
assert elements_after["extra_vars"]["--ch5-button--rounded-rectangle-border-radius-bottom-left"] == "0px"
assert elements_after["extra_vars"]["--ch5-button--rounded-rectangle-border-radius-bottom-right"] == "20px"
# pre-existing size vars/position untouched
assert elements_after["extra_vars"]["--ch5-button--regular-width"] == "150px"
assert elements_after["left"] == 420 and elements_after["top"] == 20
print("full flow: 4 asymmetric per-corner radii written, pre-existing position/size preserved: OK")

# --- write back to disk and confirm the file still round-trips ------------------------
new_sections = [
    (name, header, html_with_new_attr if name == "Html" else (css_after if name == "Css" else content))
    for name, header, content in parsed.sections
]
# use html_after (shape flip only, no test-only attribute) for the real on-disk file
new_sections = [
    (name, header, html_after if name == "Html" else (css_after if name == "Css" else content))
    for name, header, content in parsed.sections
]
rebuilt = parsed.preamble + "".join(header + content for _, header, content in new_sections)
page_path.write_text(rebuilt, encoding="utf-8", newline="")
assert compare.round_trip_check(page_path)
print("the rewritten .cuig still round-trips section-for-section: OK")

print("\nCustom button shape + border-radius: all assertions passed.")
