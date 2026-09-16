"""layout_patterns.py::build_bento_box_page -- §1's Bento Box pattern: an
asymmetric grid of variously-sized cards on one page. Verified both
structurally (pure _pack_bento_grid math) and end-to-end (a real written .cuig,
round-tripped)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))

import compare  # noqa: E402
import layout  # noqa: E402
import sdk as sdk_module  # noqa: E402
import spacing  # noqa: E402
import typography  # noqa: E402
from layout_patterns import TIER_SPANS, TIER_TYPE_ROLE, _pack_bento_grid, build_bento_box_page  # noqa: E402
from page import write_cuig  # noqa: E402

ui_sdk = sdk_module.read_sdk("2.18.0")


def _no_overlap(spans, positions):
    occupied = set()
    for (w, h), (col, row) in zip(spans, positions):
        cells = {(col + dc, row + dr) for dc in range(w) for dr in range(h)}
        assert occupied.isdisjoint(cells), (spans, positions)
        occupied |= cells


# --- _pack_bento_grid: pure placement math -------------------------------------------
spans = [(2, 2), (2, 1), (1, 1), (1, 1)]
positions = _pack_bento_grid(spans, columns=4)
assert len(positions) == 4
for (col, row), (w, h) in zip(positions, spans):
    assert col + w <= 4, (col, row, w, h)
_no_overlap(spans, positions)
print("_pack_bento_grid: 4 mixed-size cards in a 4-column grid, no overlap, all in bounds: OK")

# a card wider than the grid itself -> raises, not silently clipped
try:
    _pack_bento_grid([(3, 1)], columns=2)
    raise AssertionError("expected ValueError for a card wider than the grid")
except ValueError:
    pass
print("_pack_bento_grid: a card wider than the column count raises ValueError: OK")

# many small cards pack densely (first-fit should not leave needless gaps at the front)
dense_spans = [(1, 1)] * 8
dense_positions = _pack_bento_grid(dense_spans, columns=4)
assert set(dense_positions) == {(c, r) for r in range(2) for c in range(4)}, dense_positions
print("_pack_bento_grid: 8 uniform 1x1 cards fill a 4-column grid with zero gaps: OK")

# --- build_bento_box_page: a real .cuig page, written and round-tripped --------------
OUT = Path(__file__).resolve().parent / "LayoutPatterns"
OUT.mkdir(parents=True, exist_ok=True)

items = [
    ("Currently Playing", "large"),
    ("Living Room", "wide"),
    ("Guest Bathroom Lights", "small"),
    ("Front Door", "small"),
]
page_attrs, html, css, elements = build_bento_box_page(
    ui_sdk, name="Home", items=items, page_width=960, page_height=960, columns=4,
    resolution=(1280, 800),
)

page_path = OUT / "BentoBox.cuig"
write_cuig(page_path, page_attrs, html=html, css=css, elements=elements)
assert compare.round_trip_check(page_path), "bento box page failed round-trip"
print("build_bento_box_page: written .cuig round-trips byte-identical: OK")

assert html.count("<ch5-button") == 4, html
for label in ("Currently Playing", "Living Room", "Guest Bathroom Lights", "Front Door"):
    assert f'labelinnerhtml="{label}"' in html, label
print("build_bento_box_page: all 4 cards present with correct labels: OK")

positions_after = layout.parse_all_position_rules(css, "(max-width: 99999px)")
button_ids = [dict(e.attributes).get("id") for e in elements]
assert len(button_ids) == 4

# size hierarchy: the "large" card is strictly bigger than "wide", which is
# strictly bigger (by area) than either "small" card -- §1's own sizing intent
# ("size communicates importance") verified directly on the written geometry.
rects = {label: positions_after[eid] for (label, _tier), eid in zip(items, button_ids)}
area = lambda r: r["width"] * r["height"]
assert area(rects["Currently Playing"]) > area(rects["Living Room"]) > area(rects["Guest Bathroom Lights"])
assert area(rects["Guest Bathroom Lights"]) == area(rects["Front Door"])
print("build_bento_box_page: size hierarchy (large > wide > small) holds on real written geometry: OK")

# every card still meets the touch-target floor
for rect in rects.values():
    assert spacing.meets_touch_target(rect["width"], rect["height"]), rect
print("build_bento_box_page: every card meets the touch-target floor: OK")

# label font-size is scaled by tier -- not left at CH5's own small built-in default
for label, tier in items:
    role = TIER_TYPE_ROLE[tier]
    expected = f"--ch5-button--regular-font-size: {typography.TYPE_SCALE[role]}px"
    assert expected in css, (label, tier, expected)
print("build_bento_box_page: label font-size scaled per tier (large > wide > small): OK")

# too many columns for the page width -> raises rather than silently shrinking below the floor
try:
    build_bento_box_page(
        ui_sdk, name="TooNarrow", items=[("A", "small")], page_width=200, page_height=800,
        columns=10, resolution=(1280, 800))
    raise AssertionError("expected ValueError for cells below the touch-target floor")
except ValueError:
    pass
print("build_bento_box_page: too many columns for the page width raises ValueError: OK")

# too many/large cards for the page height -> raises rather than silently overflowing
try:
    build_bento_box_page(
        ui_sdk, name="TooShort",
        items=[("A", "large"), ("B", "large"), ("C", "large")],
        page_width=960, page_height=300, columns=4, resolution=(1280, 800))
    raise AssertionError("expected ValueError for a grid taller than the page")
except ValueError:
    pass
print("build_bento_box_page: cards needing more height than the page raises ValueError: OK")

# --- icons + active_font: icon-bearing cards get the icon-above-label layout ---------
icon_items = [("Currently Playing", "large"), ("Living Room", "wide"), ("Kitchen", "small")]
icon_page_attrs, icon_html, icon_css, icon_elements = build_bento_box_page(
    ui_sdk, name="IconGrid", items=icon_items, page_width=960, page_height=960, columns=4,
    resolution=(1280, 800), active_font="Manrope",
    icons={"Currently Playing": ("fa-solid fa-play", "FA Classic Solid"),
           "Kitchen": ("fa-solid fa-utensils", "FA Classic Solid")},
)
icon_page_path = OUT / "BentoBoxIcons.cuig"
write_cuig(icon_page_path, icon_page_attrs, html=icon_html, css=icon_css, elements=icon_elements)
assert compare.round_trip_check(icon_page_path), "icon bento box page failed round-trip"

assert 'iconclass="fa-solid fa-play"' in icon_html, icon_html
assert 'ccid_iconlibrary="FA Classic Solid"' in icon_html, icon_html
assert icon_html.count("orientation=\"vertical\"") == 2  # only the 2 icon-bearing cards
assert icon_html.count('iconposition="top"') == 2
assert "ccid_ActiveFont=\"'Manrope'\"" in icon_html
# exactly 2 cards got the icon-layout attrs (Currently Playing + Kitchen) -- Living
# Room, with no icons[] entry, keeps the schema default untouched (already proven by
# the counts above being 2, not 3)
print("build_bento_box_page: icon-bearing cards get icon+layout attrs, others keep the default, active_font applied: OK")

# icon-bearing cards get icon-size scaled by tier too (a distinct property from
# label font-size); Living Room (no icon) gets none
assert f"--ch5-button--regular-icon-size: {typography.ICON_SCALE['heading']}px" in icon_css  # Currently Playing (large)
assert f"--ch5-button--regular-icon-size: {typography.ICON_SCALE['label']}px" in icon_css  # Kitchen (small)
assert icon_css.count("--ch5-button--regular-icon-size:") == 2, "only the 2 icon-bearing cards should get icon-size"
print("build_bento_box_page: icon-bearing cards get icon-size scaled per tier, non-icon cards untouched: OK")

# primary_query threads through to both label and icon sizing
primary_query = layout.landscape_media_query(1280, 800)
_, _, primary_css, primary_elements = build_bento_box_page(
    ui_sdk, name="PrimaryQuery", items=[("Solo", "large")], page_width=960, page_height=960,
    columns=4, resolution=(1280, 800), primary_query=primary_query,
    icons={"Solo": ("fa-solid fa-play", "FA Classic Solid")},
)
primary_block = layout.find_media_block(primary_css, primary_query)
assert primary_block is not None
assert "--ch5-button--regular-font-size: 28px" in primary_block
assert "--ch5-button--regular-icon-size: 40px" in primary_block
print("build_bento_box_page: primary_query duplicates label+icon size into that resolution's own block: OK")

print("Bento Box: all assertions passed.")
