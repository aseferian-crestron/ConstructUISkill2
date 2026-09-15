"""layout_patterns.py::build_header_widget -- the second layout-pattern widget
(§1's Header-Content-Footer pattern, header half). Heterogeneous content (logo /
datetime / status text), unlike the footer's N-equal-buttons -- verified both
structurally (pure _layout_header_row math) and end-to-end (a real written .cuiw
file, round-tripped)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))

import compare  # noqa: E402
import layout  # noqa: E402
import sdk as sdk_module  # noqa: E402
import spacing  # noqa: E402
from layout_patterns import _layout_header_row, build_header_widget  # noqa: E402
from page import write_cuig  # noqa: E402

ui_sdk = sdk_module.read_sdk("2.18.0")

# --- _layout_header_row: pure positioning math -------------------------------------------
# all-fixed: logo (square, =item_height) + datetime (200px) + no flexible items
positions = _layout_header_row([None, 200], header_width=960, header_height=120)
assert len(positions) == 2
item_height = 120 - 2 * spacing.EDGE_PADDING
x0, y0, w0, h0 = positions[0]
assert h0 == item_height and y0 == spacing.EDGE_PADDING
x1, y1, w1, h1 = positions[1]
assert w1 == 200 and h1 == item_height
assert x1 >= x0 + w0
assert x1 + w1 <= 960 - spacing.EDGE_PADDING
print("_layout_header_row: one flexible + one fixed item, no overlap, edge padding respected: OK")

# multiple flexible items divide remaining space evenly
positions2 = _layout_header_row([200, None, None], header_width=960, header_height=120)
assert len(positions2) == 3
_, _, fw, _ = positions2[0]
assert fw == 200
_, _, w_a, _ = positions2[1]
_, _, w_b, _ = positions2[2]
assert w_a == w_b, (w_a, w_b)
print("_layout_header_row: multiple flexible items split remaining space evenly: OK")

# fixed widths alone exceeding the available space -> raises, not silent overflow
try:
    _layout_header_row([500, 500], header_width=600, header_height=120)
    raise AssertionError("expected ValueError for fixed widths that don't fit")
except ValueError:
    pass
print("_layout_header_row: fixed widths exceeding available space raise ValueError: OK")

# --- build_header_widget: a real .cuiw file, written and round-tripped -------------------
OUT = Path(__file__).resolve().parent / "LayoutPatterns"
OUT.mkdir(parents=True, exist_ok=True)

# Commercial: logo + datetime + active-source text
widget_attrs, html, css, elements = build_header_widget(
    ui_sdk, is_commercial=True, status_items=["Living Room"], header_width=960,
    header_height=120, resolution=(1280, 800))

widget_path = OUT / "HeaderCommercial.cuiw"
write_cuig(widget_path, widget_attrs, html=html, css=css, elements=elements)
assert compare.round_trip_check(widget_path), "commercial header widget failed round-trip"
print("build_header_widget (commercial): written .cuiw round-trips byte-identical: OK")

assert 'globalControlContract="on"' in html, html
print("build_header_widget: the widget root carries globalControlContract=\"on\" (§5): OK")

assert html.count("<ch5-image") == 1, html
assert html.count("<ch5-datetime") == 1, html
assert 'labelinnerhtml="Living Room"' in html, html
print("build_header_widget (commercial): logo + datetime + 1 status text present: OK")

positions_after = layout.parse_all_position_rules(css, "(max-width: 99999px)")
non_container_ids = [dict(e.attributes).get("id") for e in elements if e.type != "widgetContainer"]
assert len(non_container_ids) == 3, elements
for eid in non_container_ids:
    rect = positions_after[eid]
    assert rect["width"] > 0 and rect["height"] > 0, (eid, rect)
print("build_header_widget (commercial): all 3 items placed with positive size: OK")

# Residential: no logo, datetime + weather/area-status/active-source text
widget_attrs_r, html_r, css_r, elements_r = build_header_widget(
    ui_sdk, is_commercial=False, status_items=["72°F", "Living Room", "Cable Box"],
    header_width=960, header_height=120, resolution=(1280, 800))

widget_path_r = OUT / "HeaderResidential.cuiw"
write_cuig(widget_path_r, widget_attrs_r, html=html_r, css=css_r, elements=elements_r)
assert compare.round_trip_check(widget_path_r), "residential header widget failed round-trip"
assert html_r.count("<ch5-image") == 0, html_r
assert html_r.count("<ch5-datetime") == 1, html_r
for label in ("72°F", "Living Room", "Cable Box"):
    assert f'labelinnerhtml="{label}"' in html_r, label
print("build_header_widget (residential): no logo, datetime + 3 status texts present, round-trips: OK")

print("Header widget: all assertions passed.")
