"""Phase 3 end-to-end smoke test: empty page, empty widget, add-widget-to-page --
verified both via harness round-trip and structural comparison against real reference
files (C:\\Solutions\\ClaudeSamples\\Components\\Widget.cuiw / Widget on Page.cuig)."""
import sys
import tomllib
import re
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))

from page import (  # noqa: E402
    build_page_attributes, build_widget_attributes, default_widget_html_css,
    make_widget_reference, write_cuig,
)
import compare  # noqa: E402

OUT = Path(__file__).resolve().parent / "Phase3Smoke"
OUT.mkdir(parents=True, exist_ok=True)

REF_DIR = Path(r"C:\Solutions\ClaudeSamples\Components")


def parse_page_attrs(path: Path) -> dict:
    raw = Path(path).read_text(encoding="utf-8")
    headers = list(re.finditer(r"^\{(\w+)\}[ \t]*\r?\n?", raw, re.MULTILINE))
    sections = {}
    for i, m in enumerate(headers):
        start = m.end()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(raw)
        sections[m.group(1)] = raw[start:end]
    return tomllib.loads(sections["PageAttributes"])


# --- 1. empty page -----------------------------------------------------------------
page_attrs = build_page_attributes(name="EmptyPage")
page_path = OUT / "EmptyPage.cuig"
write_cuig(page_path, page_attrs, html="", css="", elements=[])
assert compare.round_trip_check(page_path), "empty page round-trip failed"

parsed = parse_page_attrs(page_path)
assert list(parsed["Attributes"].keys()) == [
    "Name", "PageMode", "Id", "StartPage", "PreloadPage", "CachePage",
    "VisibilityJoin", "DisplayBackgroundColor",
], parsed["Attributes"].keys()
assert "Elements" not in parsed, "empty page must have zero [[Elements]] blocks"
print("empty page: round-trip OK, attribute order OK, zero Elements OK")

# --- 2. empty widget, structurally compared to the real Widget.cuiw ----------------
widget_id = str(uuid4())
w_attrs = build_widget_attributes(name="EmptyWidget", widget_id=widget_id)
html, css, element = default_widget_html_css("itest01", width=500, height=500)
widget_path = OUT / "EmptyWidget.cuiw"
write_cuig(widget_path, w_attrs, html=html, css=css, elements=[element])
assert compare.round_trip_check(widget_path), "empty widget round-trip failed"

gen_widget = parse_page_attrs(widget_path)
ref_widget = parse_page_attrs(REF_DIR / "Widget.cuiw")
gen_keys = list(gen_widget["Attributes"].keys())
ref_keys = list(ref_widget["Attributes"].keys())
assert gen_keys == ref_keys, f"widget attribute order mismatch: {gen_keys} vs {ref_keys}"
print(f"empty widget: round-trip OK, attribute order matches real Widget.cuiw exactly: {gen_keys}")

gen_el = gen_widget["Elements"][0]
ref_bkd_widget = parse_page_attrs(REF_DIR / "Widget with Bkd Color.cuiw")
ref_el_full = ref_bkd_widget["Elements"][0]  # a from-creation widgetContainer, full field set
gen_el_full_keys = {k: v for k, v in gen_el.items() if k != "Attributes"}
ref_el_full_keys = {k: v for k, v in ref_el_full.items() if k != "Attributes"}
assert gen_el_full_keys == ref_el_full_keys, (gen_el_full_keys, ref_el_full_keys)
assert set(gen_el["Attributes"].keys()) == {"id", "devicesVisited"}
print(f"empty widget: root Element full scalar field set matches real CreateNewWidgetHandler "
      f"payload exactly (Name/Status/Content/Draggable/Copyable included): {gen_el_full_keys}")

# --- 3. add widget to page, structurally compared to the real Widget on Page.cuig --
html_tag, ref_element = make_widget_reference(widget_id, "EmptyWidget", element_id="itest02")
page2_attrs = build_page_attributes(name="PageWithWidget")
page2_path = OUT / "PageWithWidget.cuig"
write_cuig(page2_path, page2_attrs, html=html_tag, css="", elements=[ref_element])
assert compare.round_trip_check(page2_path), "page-with-widget round-trip failed"

gen_p2 = parse_page_attrs(page2_path)
ref_p2 = parse_page_attrs(REF_DIR / "Widget on Page.cuig")
gen_el2 = gen_p2["Elements"][0]
ref_el2 = ref_p2["Elements"][0]
assert gen_el2["Type"] == ref_el2["Type"] == "Ch5 Template"
assert set(gen_el2["Attributes"].keys()) == set(ref_el2["Attributes"].keys()), (
    set(gen_el2["Attributes"].keys()), set(ref_el2["Attributes"].keys())
)
assert gen_el2["Attributes"]["templateid"].startswith("w") and gen_el2["Attributes"]["templateid"][1:] == widget_id
print("add-widget-to-page: round-trip OK, Ch5 Template element Type + Attributes key set "
      "matches real Widget on Page.cuig exactly, templateid = 'w' + widget Id confirmed")

# --- 4. background color (page + widget), structurally compared to real reference --
# User-added reference files 2026-09-03: "Page with Bkd Color.cuig" / "Widget with Bkd
# Color.cuiw" -- confirms BackgroundColor placement/order AND (unexpectedly) that a
# brand-new page's {Html}/{Css} sections are truly empty (not just zero Elements) even
# with a background color set -- i.e. DisplayBackgroundColor/BackgroundColor do NOT
# translate into any {Css} rule at the file level; rendering must read {PageAttributes}
# directly at runtime. See docs/architecture/03-page-widget-creation.md.
bkd_page_attrs = build_page_attributes(name="Page with Bkd Color", display_background_color=True, background_color="#ff0000")
bkd_page_path = OUT / "PageBkdColor.cuig"
write_cuig(bkd_page_path, bkd_page_attrs, html="", css="", elements=[])
assert compare.round_trip_check(bkd_page_path), "bkd-color page round-trip failed"

gen_bkd_page = parse_page_attrs(bkd_page_path)
ref_bkd_page = parse_page_attrs(REF_DIR / "Page with Bkd Color.cuig")
gen_bkd_page_keys = list(gen_bkd_page["Attributes"].keys())
ref_bkd_page_keys = list(ref_bkd_page["Attributes"].keys())
assert gen_bkd_page_keys == ref_bkd_page_keys, (gen_bkd_page_keys, ref_bkd_page_keys)
assert ref_bkd_page["Attributes"]["DisplayBackgroundColor"] == "True"
assert ref_bkd_page["Attributes"]["BackgroundColor"] == "#ff0000"  # confirms 6-hex-digit RGB, no alpha, when opaque
print(f"page background color: attribute order matches real file exactly: {gen_bkd_page_keys}")

bkd_widget_attrs = build_widget_attributes(name="Widget with Bkd Color", display_background_color=True, background_color="#1900ffff")
bkd_widget_path = OUT / "WidgetBkdColor.cuiw"
write_cuig(bkd_widget_path, bkd_widget_attrs, html="<div></div>", css="", elements=[])
assert compare.round_trip_check(bkd_widget_path), "bkd-color widget round-trip failed"

gen_bkd_widget = parse_page_attrs(bkd_widget_path)
ref_bkd_widget_keys = list(ref_bkd_widget["Attributes"].keys())  # from section 2 above
gen_bkd_widget_keys = list(gen_bkd_widget["Attributes"].keys())
assert gen_bkd_widget_keys == ref_bkd_widget_keys, (gen_bkd_widget_keys, ref_bkd_widget_keys)
print(f"widget background color: attribute order matches real file exactly: {gen_bkd_widget_keys}")
print("NOTE (flagged, non-blocking): real widget BackgroundColor value is '#1900ffff' (8 hex "
      "digits) vs the page's 6-digit '#ff0000' -- suggests an optional alpha channel, format "
      "(RRGGBBAA vs AARRGGBB) unconfirmed. Not a generator bug: this module never interprets "
      "the color string, it only passes through whatever the caller supplies.")

print("\nPHASE 3 SMOKE TEST: ALL CHECKS PASSED")
