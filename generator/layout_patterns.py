"""
Design-system layout patterns (ConstructUISkill_DesignSystem.md §1) -- the one
genuinely new orchestration layer this project builds: no header/footer/menu-
widget-building code existed before this phase. Starts with ONE pattern end-to-end
(the footer half of Header-Content-Footer, "the default, safest... fallback when no
other pattern is a clearly better fit") -- the other four patterns and
build_header_widget follow the same shape once this one is proven, same
incremental precedent as palette.py's "one verified type at a time."
"""
from __future__ import annotations

from uuid import uuid4

import component
import spacing
from elements import Element
from page import build_widget_attributes, default_widget_html_css, generate_element_id
from sdk import UiSdk


def choose_layout(item_count: int, *, is_commercial: bool, panel_is_landscape: bool) -> str:
    """Design-system §1's "Choosing a Layout" decision order: item count is the
    strongest structural constraint (design doc §1), audience/orientation nudge the
    choice within what item count allows. A judgment call where the doc names a
    role but not a formula (same precedent as palette.py's derived-state deltas):

    - <=5 items: header-content-footer, the doc's own universal default.
    - 6-7 items, landscape: tabbed (commercial) / card-based (residential) -- the
      doc explicitly says "Tabbed and Card-Based... skew commercial" and
      Card-Based's own description ("a list of rooms/areas") reads residential.
    - 6-7 items, portrait: card-based -- tabbed needs landscape width it doesn't have.
    - >7 items, landscape: left-side-menu, audience-neutral (the doc doesn't tie it
      to one audience).
    - >7 items, portrait: card-based -- left-side-menu needs landscape width it
      doesn't have, same fallback reasoning as the 6-7 item portrait case.
    """
    if item_count <= 5:
        return "header-content-footer"
    if item_count <= 7:
        if panel_is_landscape:
            return "tabbed" if is_commercial else "card-based"
        return "card-based"
    return "left-side-menu" if panel_is_landscape else "card-based"


def _layout_row(
    item_count: int, footer_width: int, footer_height: int,
) -> list[tuple[int, int, int, int]]:
    """`(x, y, width, height)` for `item_count` items evenly spaced in a single row
    spanning `footer_width`, honoring spacing.EDGE_PADDING at both ends and
    spacing.SPACING_UNIT gaps between items. Item height fills the footer minus edge
    padding, floored at spacing.MIN_TOUCH_TARGET; item width is an even division of
    the remaining space, also floored at the touch-target minimum and snapped to the
    spacing unit. Raises ValueError if `item_count` doesn't fit within `footer_width`
    even at the touch-target floor -- this is exactly what design doc §1's own
    item-count ceiling (the footer's ~5-item cap) exists to prevent; a caller that
    hits this should reduce item_count or use a different layout pattern
    (see choose_layout), not have the row silently overflow or shrink below the floor.
    """
    item_height = max(footer_height - 2 * spacing.EDGE_PADDING, spacing.MIN_TOUCH_TARGET)
    usable_width = footer_width - 2 * spacing.EDGE_PADDING
    gap_total = spacing.SPACING_UNIT * (item_count - 1)
    naive_width = (usable_width - gap_total) // item_count
    item_width, _ = spacing.enforce_touch_target(naive_width, item_height)
    item_width = spacing.snap_to_spacing(item_width)
    total_row_width = item_width * item_count + gap_total
    if total_row_width > usable_width:
        raise ValueError(
            f"{item_count} items at the {spacing.MIN_TOUCH_TARGET}px touch-target floor "
            f"need {total_row_width + 2 * spacing.EDGE_PADDING}px, but the footer is only "
            f"{footer_width}px wide -- reduce item_count or use a different layout pattern "
            f"(see choose_layout)"
        )
    positions = []
    x = spacing.EDGE_PADDING
    for _ in range(item_count):
        positions.append((x, spacing.EDGE_PADDING, item_width, item_height))
        x += item_width + spacing.SPACING_UNIT
    return positions


def build_footer_widget(
    sdk: UiSdk, *, items: list[str], footer_width: int, footer_height: int = 120,
    widget_name: str = "Footer", resolution: tuple[int, int] | None = None,
) -> tuple[list[tuple[str, str]], str, str, list[Element]]:
    """A common (all-pages) footer widget -- §1's Header-Content-Footer pattern's
    footer. `items` are the footer's menu-selection labels (e.g. ["Power", "Lights",
    "Shades"]), laid out as evenly-spaced buttons per §4's spacing/touch-target
    rules (_layout_row). Built with is_global=True (§5's hard requirement: a widget
    added to every page must have Global Contract set true -- a footer always is).

    Returns `(widget_attrs, html, css, elements)` ready for page.py::write_cuig,
    the same assembly precedent as contracts_task4_end_to_end_test.py's multi-button
    page: each piece's html/css concatenated in order, elements concatenated as a
    flat list (write_cuig itself never nests -- the widgetContainer and each button
    are peer entries in one flat [[Elements]] list).
    """
    widget_id = str(uuid4())
    widget_attrs = build_widget_attributes(name=widget_name, widget_id=widget_id)
    container_html, container_css, container_element = default_widget_html_css(
        generate_element_id(), footer_width, footer_height, resolution, is_global=True)

    positions = _layout_row(len(items), footer_width, footer_height)
    buttons = [
        component.build_component(
            sdk, "ch5-button", component_name=label, element_id=generate_element_id(),
            x=x, y=y, width=w, height=h, z_index=1, resolution=resolution, label=label,
        )
        for label, (x, y, w, h) in zip(items, positions)
    ]

    html = container_html + "".join(html for html, _, _ in buttons)
    css = container_css + "".join(css for _, css, _ in buttons)
    elements = [container_element] + [element for _, _, element in buttons]
    return widget_attrs, html, css, elements
