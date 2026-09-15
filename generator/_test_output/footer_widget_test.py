"""layout_patterns.py::build_footer_widget -- the first genuinely new widget-
building orchestration in this project (§1's Header-Content-Footer pattern, footer
half). Verified both structurally (pure _layout_row math) and end-to-end (a real
written .cuiw file, round-tripped)."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))

import compare  # noqa: E402
import layout  # noqa: E402
import sdk as sdk_module  # noqa: E402
import spacing  # noqa: E402
from layout_patterns import _layout_row, build_footer_widget  # noqa: E402
from page import write_cuig  # noqa: E402

ui_sdk = sdk_module.read_sdk("2.18.0")

# --- _layout_row: pure positioning math -------------------------------------------------
positions = _layout_row(3, footer_width=960, footer_height=120)
assert len(positions) == 3
for x, y, w, h in positions:
    assert spacing.meets_touch_target(w, h), (x, y, w, h)
# no overlap: each item's x is at or past the previous item's right edge
for (x1, _, w1, _), (x2, _, _, _) in zip(positions, positions[1:]):
    assert x2 >= x1 + w1, (positions,)
# edge padding respected on the left of the first item and the right of the last
last_x, _, last_w, _ = positions[-1]
assert positions[0][0] == spacing.EDGE_PADDING
assert last_x + last_w <= 960 - spacing.EDGE_PADDING
print(f"_layout_row: 3 items, all meet touch-target floor, no overlap, edge padding respected: OK")

# too many items for the width even at the touch-target floor -> raises, not silent overflow
try:
    _layout_row(20, footer_width=200, footer_height=120)
    raise AssertionError("expected ValueError for an unsatisfiable row")
except ValueError:
    pass
print("_layout_row: too many items for the width raises ValueError rather than overflowing: OK")

# --- build_footer_widget: a real .cuiw file, written and round-tripped -----------------
OUT = Path(__file__).resolve().parent / "LayoutPatterns"
OUT.mkdir(parents=True, exist_ok=True)
widget_attrs, html, css, elements = build_footer_widget(
    ui_sdk, items=["Power", "Lights", "Shades"], footer_width=960, footer_height=120,
    resolution=(1280, 800))

widget_path = OUT / "Footer.cuiw"
write_cuig(widget_path, widget_attrs, html=html, css=css, elements=elements)
assert compare.round_trip_check(widget_path), "footer widget failed round-trip"
print("build_footer_widget: written .cuiw round-trips byte-identical: OK")

# the widget itself is global (§5's hard requirement: a widget added to every page)
assert 'globalControlContract="on"' in html, html
print("build_footer_widget: the widget root carries globalControlContract=\"on\" (§5): OK")

# 3 real buttons placed, correctly labeled, each meeting the touch-target floor
positions_after = layout.parse_all_position_rules(css, "(max-width: 99999px)")
button_ids = [e.attributes and dict(e.attributes).get("id") for e in elements
              if e.type != "widgetContainer"]
assert len(button_ids) == 3, elements
for bid in button_ids:
    rect = positions_after[bid]
    assert spacing.meets_touch_target(rect["width"], rect["height"]), (bid, rect)
print("build_footer_widget: 3 buttons placed, each meeting the touch-target floor: OK")

for label in ("Power", "Lights", "Shades"):
    assert f'ccid_Label="{label}"' in html or f"componentName=\"{label}\"" in html, label
print("build_footer_widget: all 3 item labels appear in the written Html: OK")

print("Footer widget: all assertions passed.")
