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

import camera_control
import component
import layout
import modal
import palette
import shape
import spacing
import style
import styleguide
import typography
from elements import Element
from html_div import build_html_div
from page import (
    add_widget_reference_to_page, build_page_attributes, build_widget_attributes,
    default_widget_html_css, generate_element_id, widget_reference_position_css,
)
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


#: ch5-datetime's real fixed reference size, transcribed from a real instance
#: (Component-Widgets-DateTime.cuig), not guessed -- see build_header_widget.
_DATETIME_WIDTH, _DATETIME_HEIGHT = 200, 35


def _layout_header_row(
    item_widths: list[int | None], header_width: int, header_height: int,
) -> list[tuple[int, int, int, int]]:
    """`(x, y, width, height)` for header content laid out left to right.

    Unlike the footer's evenly-divided N-equal-buttons (_layout_row), a header's
    content is heterogeneous in width: a logo has its own intrinsic square width, a
    datetime component has a real fixed reference width, and only the status-text
    items should flex to fill whatever space is left. `item_widths` gives each
    item's width in the same left-to-right order the caller will build components
    in -- `None` means "divide the remaining space evenly among all `None` entries"
    after every fixed width and the gaps/edge-padding between all items are
    reserved.

    Item height fills the header minus edge padding, the same vertical rule the
    footer uses. Raises `ValueError` if the fixed widths alone (plus gaps/edge
    padding) exceed the available space -- same "raise rather than silently
    overflow" discipline as `_layout_row`. Does NOT apply
    `spacing.MIN_TOUCH_TARGET` to flexible items: header content here is
    informational (logo/clock/status text), not an interactive control, so §4's
    touch-target floor -- which exists for tappable targets -- doesn't apply; a
    flexible item only needs to come out a positive width.
    """
    item_height = max(header_height - 2 * spacing.EDGE_PADDING, 1)
    usable_width = header_width - 2 * spacing.EDGE_PADDING
    gap_total = spacing.SPACING_UNIT * (len(item_widths) - 1) if item_widths else 0
    fixed_total = sum(w for w in item_widths if w is not None)
    flexible_count = sum(1 for w in item_widths if w is None)
    reserved = fixed_total + gap_total
    if reserved > usable_width:
        raise ValueError(
            f"header content needs {reserved + 2 * spacing.EDGE_PADDING}px "
            f"(fixed widths + gaps + edge padding), but the header is only "
            f"{header_width}px wide"
        )
    if flexible_count:
        flexible_width = (usable_width - reserved) // flexible_count
        if flexible_width <= 0:
            raise ValueError(
                f"no room left for {flexible_count} flexible header item(s) after "
                f"fixed widths, gaps, and edge padding reserve {reserved}px of the "
                f"{usable_width}px usable width"
            )
    else:
        flexible_width = 0

    positions = []
    x = spacing.EDGE_PADDING
    for width in item_widths:
        w = flexible_width if width is None else width
        positions.append((x, spacing.EDGE_PADDING, w, item_height))
        x += w + spacing.SPACING_UNIT
    return positions


def build_header_widget(
    sdk: UiSdk, *, is_commercial: bool, status_items: list[str], header_width: int,
    header_height: int = 120, widget_name: str = "Header",
    resolution: tuple[int, int] | None = None, logo_asset_id: str = "0",
) -> tuple[list[tuple[str, str]], str, str, list[Element]]:
    """A common (all-pages) header widget -- §1's Header-Content-Footer pattern's
    header. Design doc §1: "Residential -- time, weather, area status, active
    source. Commercial -- date/time, active source, corporate logo." Only two of
    those are real, distinct component types: `ch5-datetime` (time/date) and
    `ch5-image` (logo, commercial only per the doc's own line). "Weather," "area
    status," and "active source" have no dedicated component -- each is just live
    text content on a `ch5-text`, supplied by the caller via `status_items` (this
    generator doesn't know what a project's own area-status text should read, same
    reasoning `theme_chat.py` uses for leaving color *resolution* to the driving
    chat AI).

    Composition, left to right: logo (`ch5-image`, square, commercial only) ->
    `ch5-datetime` (fixed real reference size) -> one `ch5-text` per
    `status_items` entry (flexible width, evenly split). Built with
    is_global=True (§5's hard requirement, same as the footer).

    Returns `(widget_attrs, html, css, elements)`, the same assembly shape as
    `build_footer_widget`.
    """
    widget_id = str(uuid4())
    widget_attrs = build_widget_attributes(name=widget_name, widget_id=widget_id)
    container_html, container_css, container_element = default_widget_html_css(
        generate_element_id(), header_width, header_height, resolution, is_global=True)

    item_height = max(header_height - 2 * spacing.EDGE_PADDING, 1)
    item_widths: list[int | None] = []
    if is_commercial:
        item_widths.append(item_height)  # square logo
    item_widths.append(_DATETIME_WIDTH)  # datetime
    item_widths.extend([None] * len(status_items))

    positions = _layout_header_row(item_widths, header_width, header_height)
    pos_iter = iter(positions)
    parts: list[tuple[str, str, Element]] = []

    if is_commercial:
        x, y, w, h = next(pos_iter)
        parts.append(component.build_component(
            sdk, "ch5-image", component_name="Logo", element_id=generate_element_id(),
            x=x, y=y, width=w, height=h, z_index=1, resolution=resolution,
            overrides={"assetid": logo_asset_id},
        ))

    x, y, w, h = next(pos_iter)
    parts.append(component.build_component(
        sdk, "ch5-datetime", component_name="DateTime", element_id=generate_element_id(),
        x=x, y=y, width=w, height=h, z_index=1, resolution=resolution,
    ))

    for label, (x, y, w, h) in zip(status_items, pos_iter):
        parts.append(component.build_component(
            sdk, "ch5-text", component_name=label, element_id=generate_element_id(),
            x=x, y=y, width=w, height=h, z_index=1, resolution=resolution, label=label,
            overrides={"labelinnerhtml": label},
        ))

    html = container_html + "".join(html for html, _, _ in parts)
    css = container_css + "".join(css for _, css, _ in parts)
    elements = [container_element] + [element for _, _, element in parts]
    return widget_attrs, html, css, elements


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


#: §1's Bento Box sizing rule ("2-3 card sizes max... 2x2, 2x1, 1x1 grid units")
#: taken literally as exactly these 3 named tiers -- (columns_spanned,
#: rows_spanned), not a free-form per-card width/height.
TIER_SPANS: dict[str, tuple[int, int]] = {"large": (2, 2), "wide": (2, 1), "small": (1, 1)}

#: Bento Box label/icon sizing is PROPORTIONAL to the card's own footprint, not a
#: fixed typography.TYPE_SCALE role -- a real user screenshot (2026-09-16) showed
#: TYPE_SCALE["heading"] (28px) still reading as tiny on a 492x492 "large" card:
#: 28px is a sensible HEADING size for ordinary page text, but a dashboard tile
#: spanning half the screen is a fundamentally bigger UI element than a heading
#: was ever calibrated for. `_bento_card_type_sizes` below computes label/icon
#: px from the card's own geometric-mean size (`sqrt(width*height)`, not just
#: height -- "wide" and "small" share the same height but "wide" has double the
#: footprint, and that size difference should still read in the type, matching
#: §1's own "size communicates importance"). BENTO_LABEL_FRACTION/
#: BENTO_ICON_LABEL_RATIO are judgment calls (not a Construct spec), same
#: precedent as TIER_SPANS itself; TYPE_SCALE["label"]/ICON_SCALE["label"] are
#: still respected as an absolute floor so a very small card never drops below
#: the design system's own §3 readability floor.
BENTO_LABEL_FRACTION = 0.08
BENTO_ICON_LABEL_RATIO = 1.4


def _bento_card_type_sizes(width: int, height: int) -> tuple[int, int]:
    """`(label_px, icon_px)` proportional to this card's own footprint -- see
    the module-level comment above `BENTO_LABEL_FRACTION`."""
    card_metric = (width * height) ** 0.5
    label_px = max(round(card_metric * BENTO_LABEL_FRACTION), typography.TYPE_SCALE["label"])
    icon_px = max(round(label_px * BENTO_ICON_LABEL_RATIO), typography.ICON_SCALE["label"])
    return label_px, icon_px


#: Gap between an icon and its label when they're laid out as a block (icon
#: margin-bottom when the icon sits above the label) -- a real, confirmed
#: `.ch5-button--icon`-scoped style property (style.style_property_catalog),
#: not a guess. 2 spacing units, same discipline as every other gap in this
#: project (spacing.py's own SPACING_UNIT).
BENTO_ICON_LABEL_GAP = 2 * spacing.SPACING_UNIT


def _pack_bento_grid(spans: list[tuple[int, int]], columns: int) -> list[tuple[int, int]]:
    """`(col, row)` top-left grid cell for each item in `spans`, in order.

    CSS Grid's own default "sparse" row-major auto-placement algorithm (a
    well-known, standard algorithm, not invented for this project): for each
    item, scan rows top-to-bottom then columns left-to-right for the first
    position where its full `w x h` block of cells is unoccupied; mark those
    cells occupied and move to the next item. This is what a browser's own
    `grid-auto-flow: row` does, chosen because Bento Box's own "asymmetric
    grid" composition is exactly a CSS grid problem, and because it's simple
    enough to verify directly (no overlaps, every item within the column
    count) rather than inventing a bespoke packer.

    Raises `ValueError` for an item wider than the grid itself -- can never
    fit at any row, not something to silently clip.
    """
    occupied: set[tuple[int, int]] = set()
    positions: list[tuple[int, int]] = []
    for w, h in spans:
        if w > columns:
            raise ValueError(f"a {w}x{h} card cannot fit in a {columns}-column grid")
        row = 0
        while True:
            placed = False
            for col in range(columns - w + 1):
                cells = {(col + dc, row + dr) for dc in range(w) for dr in range(h)}
                if occupied.isdisjoint(cells):
                    occupied |= cells
                    positions.append((col, row))
                    placed = True
                    break
            if placed:
                break
            row += 1
    return positions


def build_bento_box_page(
    sdk: UiSdk, *, name: str, items: list[tuple[str, str]], page_width: int, page_height: int,
    columns: int, resolution: tuple[int, int] | None = None,
    icons: dict[str, tuple[str, str]] | None = None, active_font: str = "Roboto",
    primary_query: str | None = None,
) -> tuple[list[tuple[str, str]], str, str, list[Element]]:
    """One page containing an asymmetric grid of card components -- §1's Bento
    Box pattern. `items` is `(label, size_tier)` pairs, `size_tier` one of
    `TIER_SPANS`; a card's SIZE communicates its importance (§1: "size
    communicates importance without needing a color or label to say so").

    Each card is an ordinary `ch5-button` -- opening a subsystem/area page or
    popup is the CONTROL SYSTEM's job via that target page's own
    Visibility=Contract join (see `page.py::build_page_attributes`), not
    anything local to the button, so a card needs no navigation wiring beyond
    the default contract signals `component.build_component` already applies
    to every button. Styling (background/border/shape) is deliberately NOT
    applied here -- that's `palette.py`/`shape.py`'s job, same as every other
    layout-pattern builder leaves it to the caller.

    Cells are SQUARE (`page_width`/`columns` derive one `cell_size`, reused for
    height too) -- "grid units" is one measure in both dimensions, not
    independent width/height scales. Raises `ValueError` if `cell_size` would
    fall below `spacing.MIN_TOUCH_TARGET` (too many columns for the page
    width) or if the resulting grid needs more height than `page_height`
    provides (too many/large cards) -- same "raise rather than silently
    overflow" discipline as the footer's `_layout_row`.

    §7's density ceiling is NOT checked here -- `density.py::check_density`
    already exists as a standalone advisory a caller runs itself
    (`check_density(len(items), panel_diagonal_in)`); wiring it into this
    function would force a return-shape change no other layout-pattern builder
    needs for something the caller can already do with `len(items)` alone.

    Returns `(page_attrs, html, css, elements)`, ready for `page.py::write_cuig`
    -- `page.build_page_attributes` rather than `build_widget_attributes`,
    since §1's own composition is explicit: Bento Box lives on ONE PAGE, not a
    common (every-page) widget.

    `icons`: optional `label -> (icon_class, icon_library)` (real Font Awesome
    values, e.g. `("fa-solid fa-play", "FA Classic Solid")` -- see
    `ch5_button.py::build_default_button_attributes`). On a touch panel, icons
    are the primary at-a-glance visual language (every real residential/
    commercial touch-panel UI leans on them), so a card WITH an icon is laid
    out icon-above-label rather than the schema's default dead-centered label
    alone: `iconposition="top"`, `halignlabel="left"`, `valignlabel="bottom"`
    -- all 3 real, confirmed schema enum values (`component._schema_element(sdk,
    "ch5-button")`), set via `style.set_html_attribute` (the same mechanism
    `shape.apply_radius_preset` already uses to flip a button attribute
    post-build). A card with no entry in `icons` keeps the schema's own
    centered default.

    `orientation="vertical"` is ADDITIONALLY set, but ONLY on SQUARE cards
    (large/small tiers, where `width == height`) -- a real user screenshot
    (2026-09-16) showed the intended icon-above-label stacking NOT rendering
    (icon and label appeared inline instead), and the schema's own
    documentation for `orientation` states plainly that "vertical" applies a
    CSS class that "will rotate the component -90 degrees." That rotation is
    harmless on a SQUARE card (a square rotated 90 degrees has the same
    bounding box) but would visibly corrupt a non-square "wide" card (492x242
    rotated is NOT the same shape) -- confirmed real risk, not a guess, so
    "wide" cards deliberately do NOT get `orientation="vertical"`, leaving
    them at the schema default ("horizontal") until this is confirmed live.
    Whether "vertical" is actually what makes `iconposition="top"` stack
    rather than lay out inline is NOT independently confirmed from source
    alone (Construct's own editor code ties an icon-position sync workaround
    to `orientation === "vertical"`, suggesting a real connection, but this
    project cannot render a CH5 web component to verify) -- this split
    (square: try vertical; non-square: don't risk it) is deliberately a
    controlled, revertible experiment pending the user's live confirmation,
    not a settled fix.

    `active_font`: forwarded to every card, same as `component.build_component`'s
    own `active_font` kwarg -- one font choice for the whole grid, not
    per-card (a Bento Box grid reads as one surface, not mixed type families).
    `component.build_component` validates this against `fonts.available_fonts`
    and raises if it isn't a real, currently-selectable font -- a real font
    name is not enough; it must be one Construct can actually resolve and
    render (see `component.py::build_component`'s docstring for why this
    validation exists).

    Label font-size and icon size are ALWAYS scaled PROPORTIONALLY to each
    card's own footprint (`_bento_card_type_sizes`, see the module-level
    comment above `BENTO_LABEL_FRACTION`) via `typography.apply_font_size`/
    `apply_icon_size` -- not left to a separate caller styling pass, and NOT a
    fixed typography.TYPE_SCALE role (a role calibrated for ordinary UI text
    still reads as tiny on a dashboard tile spanning half the screen -- see
    typography.py's own 2026-09-16 correction). An icon-bearing card also gets
    `BENTO_ICON_LABEL_GAP` of margin between icon and label (a real, confirmed
    `.ch5-button--icon` margin-bottom property) so the two don't render
    crowded together. `primary_query`: forwarded to every styling call, same
    "catch-all + primary resolution only" rule every other styling call in
    this project follows (see `layout.py::update_element_declarations`) --
    pass the project's own primary resolution query (e.g. via
    `theme_chat._primary_query_for`) so the property grid and canvas agree;
    `None` (the default) writes catch-all only.
    """
    spans = []
    for label, tier in items:
        if tier not in TIER_SPANS:
            raise ValueError(f"unknown Bento Box size tier {tier!r} for {label!r} -- valid: {sorted(TIER_SPANS)}")
        spans.append(TIER_SPANS[tier])
    grid_positions = _pack_bento_grid(spans, columns)

    usable_width = page_width - 2 * spacing.EDGE_PADDING
    cell_size = (usable_width - (columns - 1) * spacing.SPACING_UNIT) // columns
    if cell_size < spacing.MIN_TOUCH_TARGET:
        raise ValueError(
            f"{columns} columns in a {page_width}px-wide page leaves only {cell_size}px "
            f"per cell, below the {spacing.MIN_TOUCH_TARGET}px touch-target floor -- "
            f"use fewer columns"
        )

    icons = icons or {}
    max_row = 0
    buttons = []
    for (label, tier), (col, row) in zip(items, grid_positions):
        span_w, span_h = TIER_SPANS[tier]
        x = spacing.EDGE_PADDING + col * (cell_size + spacing.SPACING_UNIT)
        y = spacing.EDGE_PADDING + row * (cell_size + spacing.SPACING_UNIT)
        w = span_w * cell_size + (span_w - 1) * spacing.SPACING_UNIT
        h = span_h * cell_size + (span_h - 1) * spacing.SPACING_UNIT
        max_row = max(max_row, row + span_h)
        icon = icons.get(label)
        icon_kwargs = {"icon_class": icon[0], "icon_library": icon[1]} if icon else {}
        html, css, element = component.build_component(
            sdk, "ch5-button", component_name=label, element_id=generate_element_id(),
            x=x, y=y, width=w, height=h, z_index=1, resolution=resolution, label=label,
            active_font=active_font, **icon_kwargs,
        )
        element_id = dict(element.attributes)["id"]
        is_square = span_w == span_h
        if icon:
            flip_attrs = [("iconposition", "top"), ("halignlabel", "left"), ("valignlabel", "bottom")]
            if is_square:
                flip_attrs.insert(0, ("orientation", "vertical"))
            for attr, value in flip_attrs:
                html = style.set_html_attribute(html, element_id, attr, value)
        label_px, icon_px = _bento_card_type_sizes(w, h)
        css = typography.apply_font_size(css, element_id, sdk, "ch5-button", label_px, primary_query=primary_query)
        if icon:
            css = typography.apply_icon_size(css, element_id, sdk, "ch5-button", icon_px, primary_query=primary_query)
            css = style.set_component_style(
                css, element_id, sdk, "ch5-button",
                [(".ch5-button--default .ch5-button--icon", "margin-bottom", f"{BENTO_ICON_LABEL_GAP}px")],
                primary_query=primary_query)
        buttons.append((html, css, element))

    total_height = 2 * spacing.EDGE_PADDING + max_row * cell_size + (max_row - 1) * spacing.SPACING_UNIT
    if total_height > page_height:
        raise ValueError(
            f"{len(items)} cards at {columns} columns need {total_height}px of height, "
            f"but the page is only {page_height}px tall -- use more columns or fewer/smaller cards"
        )

    page_attrs = build_page_attributes(name=name)
    html = "".join(html for html, _, _ in buttons)
    css = "".join(css for _, css, _ in buttons)
    elements = [element for _, _, element in buttons]
    return page_attrs, html, css, elements


def _layout_tabbed_row(
    item_count: int, row_width: int, row_height: int, *,
    item_height: int | None = None, edge_padding: int | None = None,
    gap: int | None = None, min_item_width: int = spacing.MIN_TOUCH_TARGET,
) -> list[tuple[int, int, int, int]]:
    """`(x, y, width, height)` for `item_count` items evenly spaced in a
    single row spanning `row_width`, honoring `edge_padding` at both ends and
    `gap` between items -- the same shape as `_layout_row`, deliberately NOT
    reusing it: `_layout_row`'s own `snap_to_spacing` step rounds each item's
    width up to the nearest spacing-unit multiple, which can push the summed
    row width a few pixels over `row_width` in cases `_layout_row`'s existing
    callers never hit (verified directly: both a 2-tile splash row at a full
    panel size and a 3-button footer subsystem zone overflow this way with
    real Phase 1 numbers -- `_layout_row(3, 1280 // 3, 120)` and
    `_layout_row(2, 1280, 800)` both raise `ValueError` on numbers that
    clearly ought to fit). Floor division only, no snapping -- items come out
    a few px narrower than `_layout_row` would produce, never wider than the
    row, so the summed width can never exceed it. Raises ValueError if
    `item_count` doesn't fit at `min_item_width`.

    `item_height`/`edge_padding`/`gap` default to the generic design-system
    spacing scale (row_height minus 2x EDGE_PADDING / EDGE_PADDING / SPACING_
    UNIT) when omitted, but a caller with its own real measured numbers (e.g.
    the footer's own styleguide.FOOTER_NAV_BUTTON_HEIGHT/FOOTER_PADDING_X) can
    override any of them; items are vertically CENTERED within `row_height`,
    not top-aligned at `edge_padding`, so an explicit `item_height` smaller
    than the row's own available height still looks intentional rather than
    pinned to the top.
    """
    edge_padding = spacing.EDGE_PADDING if edge_padding is None else edge_padding
    gap = spacing.SPACING_UNIT if gap is None else gap
    if item_height is None:
        item_height = max(row_height - 2 * edge_padding, spacing.MIN_TOUCH_TARGET)
    y = (row_height - item_height) // 2
    usable_width = row_width - 2 * edge_padding
    gap_total = gap * (item_count - 1)
    item_width = (usable_width - gap_total) // item_count
    if item_width < min_item_width:
        raise ValueError(
            f"{item_count} items at the {min_item_width}px minimum width "
            f"need more than the {row_width}px available width -- reduce item_count "
            f"or use a wider row"
        )
    positions = []
    x = edge_padding
    for _ in range(item_count):
        positions.append((x, y, item_width, item_height))
        x += item_width + gap
    return positions


#: Default icon per common system-mode/subsystem label -- the reviewed PDF
#: mockup (docs/construct-tabbed-ui-screens-commercial.pdf, rendered directly
#: 2026-09-18 after a real user report that the header/footer "doesn't look
#: like the design") shows a small icon on every header tab AND every footer
#: subsystem button; neither was ever wired with one before this fix, a real
#: gap. Keyed case-insensitively; a label with no match gets no icon (same
#: "caller supplies content this generator can't invent" precedent as
#: ConstructUISkill.md's splash-tile rule) rather than guessing at an
#: arbitrary glyph for a subsystem name this generator doesn't control.
DEFAULT_CHROME_ICONS: dict[str, str] = {
    "power": "fa-solid fa-power-off",
    "system power": "fa-solid fa-power-off",
    "presentation": "fa-solid fa-desktop",
    "video call": "fa-solid fa-video",
    "audio call": "fa-solid fa-microphone",
    "environment": "fa-solid fa-lightbulb",
    "audio": "fa-solid fa-sliders",
    "camera": "fa-solid fa-video",
}


def _default_icon(label: str) -> str | None:
    return DEFAULT_CHROME_ICONS.get(label.strip().lower())


#: Rough px-per-character estimate for an auto-width header tab's label at
#: styleguide.TAB_LABEL_FONT_SIZE (13.76px) -- this project has no real font-
#: metrics access, so a tab's true auto-content-width (styleguide §2: "auto
#: width (content + padding)") can't be measured exactly. A judgment call,
#: same discipline as every other named estimate in this project. Bumped
#: 8->9 2026-09-18 after a live-confirmed icon/label overlap on the Privacy
#: Mute pill (which also uses this estimate) -- 8 ran too tight for a real
#: bold 12.8-13.76px label.
TAB_CHAR_WIDTH_ESTIMATE = 9



def _is_camera_subsystem(label: str) -> bool:
    """Case/pluralization-insensitive match for the Camera subsystem -- the
    reference spec's own Generic Specifications example uses "Cameras"
    (plural), which a bare `label == "Camera"` check would silently miss,
    producing an empty modal with `camera_presets` discarded and no error.
    See the Final review fix note in
    docs/superpowers/plans/2026-09-17-tabbed-layout-commercial.md.
    """
    return label.strip().rstrip("s").lower() == "camera"


#: Shared visual token set across Splash/Header/Footer. Originally hand-picked
#: from the stakeholder-reviewed reference mockups
#: (docs/construct-tabbed-ui-screens-commercial.pdf); as of 2026-09-17 sourced
#: from styleguide.py instead -- a separate Claude AI session measured these
#: same mockups directly and produced
#: docs/ConstructUISkill_Tabbed-Layout-Styleguide.md, a more precise source
#: than this project's own earlier by-eye hex picks (values shifted slightly,
#: e.g. PANEL_TEXT_COLOR #1A1D23 -> #171a1f). Matches the design spec's own
#: §7 role names (amber=on/active, coral=live/urgent/call-related).
SPLASH_BACKGROUND_COLOR = styleguide.BACKGROUND
PANEL_TEXT_COLOR = styleguide.TEXT_PRIMARY
PANEL_MUTED_TEXT_COLOR = styleguide.TEXT_MUTED
PANEL_SURFACE_COLOR = styleguide.SURFACE
PANEL_SURFACE_ALT_COLOR = styleguide.SURFACE_ALT
PANEL_BORDER_COLOR = styleguide.DIVIDER
PANEL_ACCENT_COLOR = styleguide.ACCENT_AMBER  # amber -- on/active
PANEL_CORAL_COLOR = styleguide.ACCENT_CORAL  # coral -- live/urgent/call-related, active mute state
PANEL_CORAL_DIM_COLOR = styleguide.ACCENT_CORAL_DIM
SPLASH_HEADLINE_TOP = 200
SPLASH_ROOM_NAME_HEIGHT = 24
SPLASH_HEADLINE_HEIGHT = 48
SPLASH_TILES_GAP_ABOVE = 40

#: Splash tile icon badge/label geometry -- REBUILT 2026-09-18 after a live
#: report that ch5-button's own `iconposition="top"` does not actually stack
#: the icon above the label (confirmed live: identical icon-left-of-label
#: rendering with and without `orientation="vertical"` -- ch5-button's real
#: internal icon-layout behavior does not match this project's earlier
#: assumption, and this project cannot render a CH5 web component itself to
#: keep guessing at it). Rebuilt as 4 explicitly-positioned pieces instead of
#: trusting ch5-button's internal icon+label auto-layout: a plain card button
#: (background/border/radius/tap target, empty label, no native icon) +
#: a circular html-div badge (same mechanism modal.py's card/backdrop
#: already use) + a small icon-only button centered on the badge + a
#: separate bold ch5-text label below -- the same non-interactive-overlay-
#: over-a-real-button technique already proven for the subtitle just below
#: this (`pointer-events: none` so every tap still reaches the card).
#:
#: SPLASH_TILE_WIDTH/HEIGHT specifically: NEITHER markdown spec defines a
#: splash action-tile size -- confirmed by direct search (2026-09-18, a real
#: user question: "does the markdown correctly define the splash page
#: buttons?"). The styleguide's only "Tile" row (§5, 193x49px) is a smaller,
#: different single-select tile used INSIDE MODALS (camera presets, quick-
#: level grids), and its own §7 explicitly disclaims one-off layouts like
#: this ("infer from the 8/10/14/16/20px rhythm... rather than introducing
#: new arbitrary values"). The previous 220x260 (TALLER than wide) predates
#: this session and was never derived from anything -- it's what produced
#: the user-reported "height is larger than the width" mismatch against the
#: reviewed design's clearly landscape cards. HEIGHT is now computed from
#: this tile's own real content stack (top padding + badge + gap + label +
#: gap + subtitle + bottom padding) instead of a second independent guess
#: that could drift out of sync with it; WIDTH is set to a 1.25x landscape
#: ratio off that computed height, matching the reviewed design's proportions
#: (still a judgment call, not a spec -- same discipline as every other named
#: constant in this project, e.g. BENTO_LABEL_FRACTION).
SPLASH_TILE_PADDING_TOP = 40
SPLASH_BADGE_SIZE = 64
SPLASH_BADGE_ICON_SIZE = 28
SPLASH_BADGE_LABEL_GAP = 16
SPLASH_TILE_LABEL_HEIGHT = 24
SPLASH_LABEL_SUBTITLE_GAP = 8
SPLASH_SUBTITLE_HEIGHT = 20
#: Smaller than the label (TYPE_SCALE["label"]=18px) -- a caption/subtitle
#: line should read distinctly smaller, not just one step down; TYPE_SCALE's
#: own smallest role ("caption"=16px) wasn't different enough from the label
#: to read as a visual hierarchy (real user feedback, 2026-09-18). Matches
#: this project's other small-caption sizes (e.g. FOOTER_NAV_LABEL_FONT_SIZE
#: 12.8px), a judgment call like every other explicit-value override in this
#: module.
SPLASH_SUBTITLE_FONT_SIZE = 13
SPLASH_TILE_PADDING_BOTTOM = 32
SPLASH_TILE_HEIGHT = (
    SPLASH_TILE_PADDING_TOP + SPLASH_BADGE_SIZE + SPLASH_BADGE_LABEL_GAP
    + SPLASH_TILE_LABEL_HEIGHT + SPLASH_LABEL_SUBTITLE_GAP + SPLASH_SUBTITLE_HEIGHT
    + SPLASH_TILE_PADDING_BOTTOM
)
SPLASH_TILE_WIDTH = round(SPLASH_TILE_HEIGHT * 1.25)


def build_tabbed_shell(
    sdk: UiSdk, *, room_name: str, splash_tiles: list[tuple[str, str] | tuple[str, str, str]],
    additional_system_modes: list[str], subsystems: list[str],
    camera_presets: list[str], panel_width: int, panel_height: int,
    header_height: int = styleguide.HEADER_HEIGHT_WITH_TABS,
    footer_height: int = styleguide.FOOTER_HEIGHT,
    splash_headline: str = "What would you like to do?",
    resolution: tuple[int, int] | None = None, active_font: str = "Roboto",
    logo_asset_id: str = "0",
) -> dict:
    """Tabbed layout pattern, commercial, Phase 1 shell (design-system §2's
    Tabbed pattern) -- Splash page, Main Panel page (2-row header + tab-strip-
    driven per-mode content widgets + 3-zone footer), and one modal widget per
    footer subsystem (Camera's is real content, the rest are empty this
    phase). See docs/superpowers/specs/2026-09-17-tabbed-layout-commercial-design.md.

    "System Power" is always the first system mode -- the reference spec's
    own "always included by default" rule, baked in here rather than left to
    caller discipline. `additional_system_modes` are whichever of
    Presentation/Video Call/Audio Call (or a future project's own set) the
    caller asked the user for, per ConstructUISkill.md §11.

    Returns a dict: `splash_page`/`main_panel_page` ->
    `(page_attrs, html, css, elements)`; `header_widget`/`footer_widget` ->
    `(widget_id, widget_attrs, html, css, elements)`; `tab_content_widgets`/
    `modal_widgets` -> `{name: (widget_id, widget_attrs, html, css,
    elements)}`, keyed by system mode / subsystem name respectively. The
    caller writes each entry with page.py::write_cuig.

    Raises ValueError for a panel too narrow for the header's logo + tab
    strip, a header too short for the room-name/date-time stack, a footer
    zone too narrow for its content, or an empty `subsystems` list.
    """
    system_modes = ["System Power", *additional_system_modes]
    if not subsystems:
        raise ValueError("build_tabbed_shell needs at least one footer subsystem")

    # --- header: identity row (room name/date-time stack + right-aligned logo) on
    # top, a full-width tab strip below -- sizes/positions from
    # docs/ConstructUISkill_Tabbed-Layout-Styleguide.md §2 (Boardroom column).
    # The logo is a small FIXED-size slot in the identity row only (26x26,
    # vertically centered in that row), not a full-header-height square spanning
    # both rows -- that was this function's own earlier, unmeasured guess.
    logo_size = styleguide.LOGO_SIZE
    identity_row_height = header_height - styleguide.TAB_ROW_HEIGHT
    identity_content_width = (
        panel_width - 2 * styleguide.IDENTITY_ROW_PADDING_X
        - logo_size - styleguide.IDENTITY_ROW_GAP_BOARDROOM
    )
    if identity_content_width <= 0:
        raise ValueError(
            f"a {panel_width}px wide panel is too narrow for the identity row's "
            f"room-name/date-time column plus a {logo_size}px logo slot"
        )
    # The room-name/date-time stack starts at y=IDENTITY_ROW_PADDING_TOP (not
    # y=0), so that top inset has to come out of the same identity_row_height
    # budget too, or the stack's real bottom edge silently overlaps the tab
    # strip below it.
    stack_height = (
        styleguide.IDENTITY_ROW_PADDING_TOP + styleguide.ROOM_NAME_LINE_HEIGHT
        + styleguide.DATETIME_LINE_HEIGHT + styleguide.IDENTITY_ROW_PADDING_BOTTOM
    )
    if identity_row_height < stack_height:
        raise ValueError(
            f"a {header_height}px header leaves only {identity_row_height}px for "
            f"the identity row, but the room-name/date-time stack needs "
            f"{stack_height}px+ (styleguide §2)"
        )

    header_widget_id = str(uuid4())
    header_widget_attrs = build_widget_attributes(name="Header", widget_id=header_widget_id)
    header_container_html, header_container_css, header_container_element = default_widget_html_css(
        generate_element_id(), panel_width, header_height, resolution, is_global=True)
    # The widget's own root container is a plain <div> (default_widget_html_css),
    # same mechanism html_div.py uses -- a literal CSS declaration, not a
    # --ch5-* schema var.
    header_container_css, _ = layout.update_element_declarations(
        header_container_css, dict(header_container_element.attributes)["id"],
        {"background-color": PANEL_SURFACE_COLOR})
    header_parts: list[tuple[str, str, Element]] = []

    room_name_html, room_name_css, room_name_element = component.build_component(
        sdk, "ch5-text", component_name="Room Name", element_id=generate_element_id(),
        x=styleguide.IDENTITY_ROW_PADDING_X, y=styleguide.IDENTITY_ROW_PADDING_TOP,
        width=identity_content_width, height=styleguide.ROOM_NAME_LINE_HEIGHT,
        z_index=1, resolution=resolution, active_font=active_font, label=room_name,
        overrides={"labelinnerhtml": room_name},
    )
    room_name_id = dict(room_name_element.attributes)["id"]
    room_name_css = typography.apply_font_size(room_name_css, room_name_id, sdk, "ch5-text", styleguide.ROOM_NAME_FONT_SIZE)
    room_name_css = palette.apply_palette(
        room_name_css, room_name_id, sdk, "ch5-text",
        palette.applicable_subset("ch5-text", palette.derive_states({"text_color": PANEL_TEXT_COLOR})))
    header_parts.append((room_name_html, room_name_css, room_name_element))

    # No gap beyond normal line spacing between the room name and date/time
    # (styleguide §2: "sits directly under the room name with no gap") -- the
    # date/time starts immediately at the room name's own line-box bottom.
    datetime_html, datetime_css, datetime_element = component.build_component(
        sdk, "ch5-datetime", component_name="Header DateTime", element_id=generate_element_id(),
        x=styleguide.IDENTITY_ROW_PADDING_X,
        y=styleguide.IDENTITY_ROW_PADDING_TOP + styleguide.ROOM_NAME_LINE_HEIGHT,
        width=identity_content_width, height=styleguide.DATETIME_LINE_HEIGHT,
        z_index=1, resolution=resolution, active_font=active_font,
    )
    datetime_id = dict(datetime_element.attributes)["id"]
    datetime_css = typography.apply_font_size(datetime_css, datetime_id, sdk, "ch5-datetime", styleguide.DATETIME_FONT_SIZE)
    datetime_css = palette.apply_palette(
        datetime_css, datetime_id, sdk, "ch5-datetime",
        palette.applicable_subset("ch5-datetime", palette.derive_states({"text_color": PANEL_MUTED_TEXT_COLOR})))
    header_parts.append((datetime_html, datetime_css, datetime_element))

    logo_html, logo_css, logo_element = component.build_component(
        sdk, "ch5-image", component_name="Logo", element_id=generate_element_id(),
        x=panel_width - styleguide.IDENTITY_ROW_PADDING_X - logo_size,
        y=(identity_row_height - logo_size) // 2, width=logo_size, height=logo_size,
        z_index=1, resolution=resolution, active_font=active_font,
        overrides={"assetid": logo_asset_id},
    )
    header_parts.append((logo_html, logo_css, logo_element))

    # Individually-built, auto-width, left-aligned buttons -- NOT a single
    # ch5-tab-button stretched evenly across the full width. FIXED 2026-09-18
    # after a real user report ("you can't use a tab component to replicate
    # the design") and rendering the actual reviewed PDF mockup directly
    # (docs/construct-tabbed-ui-screens-commercial.pdf, page 4): the real
    # design's tabs sit left-aligned right after the row's own padding, each
    # sized to its own label+icon content, with the rest of the row empty --
    # not evenly divided across the panel. This also sidesteps ch5-tab-
    # button's internal per-child layout entirely (the same class of problem
    # already found with ch5-button's iconposition -- an all-in-one
    # component's internal rendering isn't something this project can verify
    # independently), the same fix already applied to the splash tiles.
    # Icon-left-of-label is the SCHEMA'S OWN DEFAULT layout for ch5-button --
    # no iconposition/orientation attribute needed at all here.
    x_cursor = styleguide.TAB_ROW_PADDING_X
    tab_right_limit = panel_width - styleguide.TAB_ROW_PADDING_X
    for mode_label in system_modes:
        # Auto-width isn't measurable without real font metrics -- estimated
        # from the label's own character count (a judgment call, not a
        # Construct spec, same discipline as every other named estimate in
        # this project, e.g. BENTO_LABEL_FRACTION).
        text_width = round(len(mode_label) * TAB_CHAR_WIDTH_ESTIMATE)
        icon = _default_icon(mode_label)
        tab_width = 2 * styleguide.TAB_ROW_PADDING_X + text_width
        if icon:
            tab_width += styleguide.TAB_ICON_SIZE + spacing.SPACING_UNIT
        if x_cursor + tab_width > tab_right_limit:
            raise ValueError(
                f"system mode tabs {system_modes!r} don't fit within a "
                f"{panel_width}px header -- fewer/shorter tab labels needed"
            )
        tab_html, tab_css, tab_element = component.build_component(
            sdk, "ch5-button", component_name=f"Tab {mode_label}", element_id=generate_element_id(),
            x=x_cursor, y=identity_row_height, width=tab_width, height=styleguide.TAB_ROW_HEIGHT,
            z_index=1, resolution=resolution, active_font=active_font, label=mode_label,
            icon_class=icon, icon_library="FA Classic Solid",
        )
        tab_id = dict(tab_element.attributes)["id"]
        # Unselected tabs blend into the header bar (same surface, muted
        # text). FIXED 2026-09-18 -- real bug: the active tab's TEXT/ICON
        # were set to amber, misreading styleguide §6's "amber bottom border
        # + full-opacity text" as amber-colored text. A direct pixel sample
        # of the reviewed PDF (page 4) gives the active "Video Call" label as
        # `#171a25`, an exact match for PANEL_TEXT_COLOR (`#171a1f`) -- "full-
        # opacity text" means full-strength dark text (vs. the muted/lighter
        # inactive look), not amber. Only the underline is amber (pixel-
        # confirmed `#e8a33d`, an exact match for PANEL_ACCENT_COLOR).
        tab_css = palette.apply_palette(
            tab_css, tab_id, sdk, "ch5-button",
            palette.applicable_subset("ch5-button", palette.derive_states({
                "background_color": PANEL_SURFACE_COLOR,
                "border_color": PANEL_SURFACE_COLOR,
                "border_width": "0px",
                "text_color": PANEL_MUTED_TEXT_COLOR,
                "icon_color": PANEL_MUTED_TEXT_COLOR,
                "selected_background_color": PANEL_SURFACE_COLOR,
                "selected_text_color": PANEL_TEXT_COLOR,
                "selected_icon_color": PANEL_TEXT_COLOR,
                "selected_border_color": PANEL_ACCENT_COLOR,
                "selected_border_width": f"{styleguide.TAB_SELECTED_UNDERLINE_WIDTH}px",
            })),
        )
        tab_css = typography.apply_font_size(tab_css, tab_id, sdk, "ch5-button", styleguide.TAB_LABEL_FONT_SIZE)
        if icon:
            tab_css = typography.apply_icon_size(tab_css, tab_id, sdk, "ch5-button", styleguide.TAB_ICON_SIZE)
            tab_css = typography.apply_icon_gap(tab_css, tab_id, sdk, "ch5-button", spacing.SPACING_UNIT)
        header_parts.append((tab_html, tab_css, tab_element))
        x_cursor += tab_width + styleguide.TAB_GAP

    header_html = header_container_html + "".join(h for h, _, _ in header_parts)
    header_css = header_container_css + "".join(c for _, c, _ in header_parts)
    header_elements = [header_container_element] + [e for _, _, e in header_parts]

    # --- one tab-content widget per system mode, placeholder text this phase --------
    content_area_height = panel_height - header_height - footer_height
    if content_area_height <= 0:
        raise ValueError(
            f"a {panel_height}px panel has no room left for tab content after a "
            f"{header_height}px header and {footer_height}px footer"
        )
    tab_content_widgets: dict[str, tuple] = {}
    for mode in system_modes:
        widget_id = str(uuid4())
        widget_attrs = build_widget_attributes(name=f"{mode} Content", widget_id=widget_id)
        container_html, container_css, container_element = default_widget_html_css(
            generate_element_id(), panel_width, content_area_height, resolution, is_global=False)
        placeholder_html, placeholder_css, placeholder_element = component.build_component(
            sdk, "ch5-text", component_name=f"{mode} Placeholder", element_id=generate_element_id(),
            x=spacing.EDGE_PADDING, y=spacing.EDGE_PADDING,
            width=panel_width - 2 * spacing.EDGE_PADDING, height=spacing.MIN_TOUCH_TARGET,
            z_index=1, resolution=resolution, active_font=active_font, label=mode,
            overrides={"labelinnerhtml": f"{mode} (placeholder -- follow-on phase)"},
        )
        html = container_html + placeholder_html
        css = container_css + placeholder_css
        elements = [container_element, placeholder_element]
        tab_content_widgets[mode] = (widget_id, widget_attrs, html, css, elements)

    # --- footer: N subsystem buttons (left) + Privacy Mute (center) + volume (right) -
    footer_widget_id = str(uuid4())
    footer_widget_attrs = build_widget_attributes(name="Footer", widget_id=footer_widget_id)
    footer_container_html, footer_container_css, footer_container_element = default_widget_html_css(
        generate_element_id(), panel_width, footer_height, resolution, is_global=True)
    footer_container_css, _ = layout.update_element_declarations(
        footer_container_css, dict(footer_container_element.attributes)["id"],
        {"background-color": PANEL_SURFACE_COLOR})
    footer_parts: list[tuple[str, str, Element]] = []

    #: "Footer nav button / tab / dropdown trigger" row (styleguide §6):
    #: surface-alt background, divider border, muted text in the normal
    #: state. FIXED 2026-09-18 -- real bug: icon_color was PANEL_ACCENT_COLOR
    #: (amber), a guess this project called "already reviewed live" without
    #: actually pixel-checking it; a direct pixel sample of the reviewed PDF
    #: (docs/construct-tabbed-ui-screens-commercial.pdf, page 4) gives the
    #: Environment icon as `#5c6573`, an exact match for PANEL_MUTED_TEXT_
    #: COLOR (`#5b6472`), not amber at all -- footer nav icons match their
    #: own label's muted color, full stop.
    #:
    #: `emphasis` (Volume Mute only): gray normal state, coral ONLY when
    #: actually muted (a real selected-state distinction -- confirmed in the
    #: reviewed PDF, Volume Mute renders as a plain gray circle there).
    #: `always_coral` (Privacy Mute only): CORRECTED 2026-09-18 -- real
    #: mistake, direct user correction ("this has nothing to do with selected
    #: state. the design has the privacy button at a normal state with fill,
    #: border and icon colors"): Privacy Mute's coral look is its own
    #: permanent NORMAL-state design, not a toggled/selected look at all --
    #: unlike Volume Mute, it has no separate muted gray look in this design.
    #: The coral hex values themselves were always pixel-exact
    #: (`#d97757`/`#fbe0d5`, confirmed against ACCENT_CORAL/ACCENT_CORAL_DIM)
    #: -- they were just wired to the wrong palette KEYS (selected_* instead
    #: of the base state).
    def _footer_button_palette(*, emphasis: bool = False, always_coral: bool = False) -> dict[str, str]:
        if always_coral:
            base = {
                "background_color": PANEL_CORAL_DIM_COLOR,
                "border_color": PANEL_CORAL_COLOR,
                "border_width": "1px",
                "border_style": "solid",
                "text_color": PANEL_CORAL_COLOR,
                "icon_color": PANEL_CORAL_COLOR,
                # Pinned explicitly rather than left to derive_states' default
                # lighten -- CORAL_DIM is already a very pale fill, so the
                # standard +12% lighten clips to pure white (#ffffff),
                # washing the coral out entirely. There's no distinct
                # "selected" LOOK for this button in the design (it's a
                # single, permanent coral treatment, per the user's
                # correction above) -- pressed still derives normally
                # (darkens fine from a pale base), only selected is pinned.
                "selected_background_color": PANEL_CORAL_DIM_COLOR,
                "selected_border_color": PANEL_CORAL_COLOR,
                "selected_text_color": PANEL_CORAL_COLOR,
                "selected_icon_color": PANEL_CORAL_COLOR,
            }
            return palette.applicable_subset("ch5-button", palette.derive_states(base))
        base = {
            "background_color": PANEL_SURFACE_ALT_COLOR,
            "border_color": PANEL_BORDER_COLOR,
            "border_width": "1px",
            "border_style": "solid",
            "text_color": PANEL_MUTED_TEXT_COLOR,
            "icon_color": PANEL_MUTED_TEXT_COLOR,
        }
        if emphasis:
            base.update({
                "selected_background_color": PANEL_CORAL_DIM_COLOR,
                "selected_border_color": PANEL_CORAL_COLOR,
                "selected_text_color": PANEL_CORAL_COLOR,
                "selected_icon_color": PANEL_CORAL_COLOR,
            })
        return palette.applicable_subset("ch5-button", palette.derive_states(base))

    # Privacy Mute is a PILL with a visible label, not a small icon-only
    # circle -- CORRECTED 2026-09-18 after rendering the actual reviewed PDF
    # directly (docs/construct-tabbed-ui-screens-commercial.pdf, page 4):
    # the styleguide doc's own §4 text groups it with Volume Mute as "Footer
    # icon-only button... 37x37 circle," but the real mockup pixels clearly
    # show Privacy Mute as a labeled pill (icon + "Privacy Mute" text,
    # matching the OTHER footer nav buttons' own pill treatment) -- the
    # actual reference image is the ground truth here, not the styleguide's
    # prose summary of it. Width estimated the same way as the header's
    # auto-width tabs (no real font-metrics access).
    privacy_label = "Privacy Mute"
    privacy_width = (
        2 * styleguide.FOOTER_NAV_BUTTON_PADDING_X + styleguide.TAB_ICON_SIZE + spacing.SPACING_UNIT
        + round(len(privacy_label) * TAB_CHAR_WIDTH_ESTIMATE)
    )
    volume_slider_width = styleguide.VOLUME_CONTROL_WIDTH
    volume_icon_size = styleguide.TAB_ICON_SIZE + 2 * spacing.SPACING_UNIT
    right_content_width = (
        volume_icon_size + spacing.SPACING_UNIT + volume_slider_width + spacing.SPACING_UNIT
        + styleguide.FOOTER_ICON_BUTTON_SIZE
    )
    right_x = panel_width - styleguide.FOOTER_PADDING_X - right_content_width

    def _footer_subsystem_width(label: str) -> int:
        w = 2 * styleguide.FOOTER_NAV_BUTTON_PADDING_X + round(len(label) * TAB_CHAR_WIDTH_ESTIMATE)
        if _default_icon(label):
            w += styleguide.TAB_ICON_SIZE + spacing.SPACING_UNIT
        return w

    left_content_width = (
        sum(_footer_subsystem_width(label) for label in subsystems)
        + spacing.SPACING_UNIT * (len(subsystems) - 1)
    )
    left_content_end = styleguide.FOOTER_PADDING_X + left_content_width

    # FIXED 2026-09-18 -- real bug, live-reported ("why is the privacy mute
    # button not centered like the design?"): Privacy Mute was centered
    # within a leftover "center zone" (whatever width remained after the
    # left/right content-driven zones), NOT the panel's actual horizontal
    # center -- those two only coincide when left_content_width happens to
    # equal right_content_width, which they don't in general (this project's
    # own styleguide §4 describes three EQUAL flex:1 zones for exactly this
    # reason -- a real, genuine 3-way split, not the content-driven
    # zone-width scheme this function used instead). Privacy Mute is now
    # positioned at the panel's true center; raises if that would overlap
    # either side's real content instead of silently sliding off-center.
    privacy_x = (panel_width - privacy_width) // 2
    if privacy_x < left_content_end + spacing.SPACING_UNIT or privacy_x + privacy_width + spacing.SPACING_UNIT > right_x:
        raise ValueError(
            f"a {panel_width}px panel can't center a {privacy_width}px Privacy Mute "
            f"pill without overlapping the left subsystem buttons (ending at "
            f"{left_content_end}px) or the right volume/mute cluster (starting at "
            f"{right_x}px) -- fewer/shorter subsystem labels needed"
        )

    # Auto-width per label, left-aligned -- NOT evenly divided across a
    # zone. FIXED 2026-09-18 -- real bug, live-reported ("the pill buttons
    # in the footer are all the same size. why? thats not in the design"):
    # the reviewed PDF clearly shows Environment/Audio/Camera each sized to
    # their own label+icon content (same as the header tabs, already fixed
    # the same way earlier this session) -- an even-division
    # `_layout_tabbed_row` call was still left here instead of applying the
    # exact same auto-width fix.
    footer_x_cursor = styleguide.FOOTER_PADDING_X
    for label in subsystems:
        icon = _default_icon(label)
        w = _footer_subsystem_width(label)
        y = (footer_height - styleguide.FOOTER_NAV_BUTTON_HEIGHT) // 2
        html, css, element = component.build_component(
            sdk, "ch5-button", component_name=f"Footer {label}", element_id=generate_element_id(),
            x=footer_x_cursor, y=y, width=w, height=styleguide.FOOTER_NAV_BUTTON_HEIGHT, z_index=1,
            resolution=resolution, active_font=active_font, label=label,
            icon_class=icon, icon_library="FA Classic Solid",
        )
        footer_x_cursor += w + spacing.SPACING_UNIT
        sub_id = dict(element.attributes)["id"]
        html, css = shape.apply_radius_px(html, css, sub_id, sdk, "ch5-button", styleguide.FOOTER_NAV_BUTTON_RADIUS)
        css = palette.apply_palette(css, sub_id, sdk, "ch5-button", _footer_button_palette())
        css = typography.apply_font_size(css, sub_id, sdk, "ch5-button", styleguide.FOOTER_NAV_LABEL_FONT_SIZE)
        css = typography.apply_icon_size(css, sub_id, sdk, "ch5-button", styleguide.TAB_ICON_SIZE)
        css = typography.apply_icon_gap(css, sub_id, sdk, "ch5-button", spacing.SPACING_UNIT)
        footer_parts.append((html, css, element))

    # Privacy Mute: a labeled pill (see the module comment above privacy_width
    # for why this isn't a small icon-only circle), using
    # ch5-button's own "Selected" state/signal (already one of its DEFAULT_
    # SIGNALS) for its persistent on/off look, same mechanism a toggle would
    # use, just styled as a button to match its footer-nav-button siblings.
    privacy_html, privacy_css, privacy_element = component.build_component(
        sdk, "ch5-button", component_name="Privacy Mute", element_id=generate_element_id(),
        x=privacy_x,
        y=(footer_height - styleguide.FOOTER_NAV_BUTTON_HEIGHT) // 2,
        width=privacy_width, height=styleguide.FOOTER_NAV_BUTTON_HEIGHT, z_index=1, resolution=resolution,
        active_font=active_font, label=privacy_label, icon_class="fa-solid fa-video-slash",
        icon_library="FA Classic Solid",
    )
    privacy_id = dict(privacy_element.attributes)["id"]
    privacy_html, privacy_css = shape.apply_radius_px(
        privacy_html, privacy_css, privacy_id, sdk, "ch5-button", styleguide.FOOTER_NAV_BUTTON_RADIUS)
    privacy_css = palette.apply_palette(privacy_css, privacy_id, sdk, "ch5-button", _footer_button_palette(always_coral=True))
    privacy_css = typography.apply_font_size(privacy_css, privacy_id, sdk, "ch5-button", styleguide.FOOTER_NAV_LABEL_FONT_SIZE)
    privacy_css = typography.apply_icon_size(privacy_css, privacy_id, sdk, "ch5-button", styleguide.TAB_ICON_SIZE)
    privacy_css = typography.apply_icon_gap(privacy_css, privacy_id, sdk, "ch5-button", spacing.SPACING_UNIT)
    footer_parts.append((privacy_html, privacy_css, privacy_element))

    # Speaker icon before the track -- present in the reviewed PDF ("Volume
    # control: ... 10px gap between icon/track/label," styleguide §4) but
    # never built before this fix. Icon-only, transparent, non-interactive
    # (the slider itself is the real control).
    volume_icon_html, volume_icon_css, volume_icon_element = component.build_component(
        sdk, "ch5-button", component_name="Volume Icon", element_id=generate_element_id(),
        x=right_x, y=(footer_height - volume_icon_size) // 2,
        width=volume_icon_size, height=volume_icon_size, z_index=1, resolution=resolution,
        active_font=active_font, label="", icon_class="fa-solid fa-volume-high",
        icon_library="FA Classic Solid", overrides={"labelinnerhtml": ""},
    )
    volume_icon_id = dict(volume_icon_element.attributes)["id"]
    volume_icon_css = palette.apply_palette(volume_icon_css, volume_icon_id, sdk, "ch5-button", palette.applicable_subset(
        "ch5-button", palette.derive_states({
            "background_color": "transparent", "pressed_background_color": "transparent",
            "selected_background_color": "transparent", "border_width": "0px",
            "icon_color": PANEL_MUTED_TEXT_COLOR,
        })))
    volume_icon_css = typography.apply_icon_size(volume_icon_css, volume_icon_id, sdk, "ch5-button", styleguide.TAB_ICON_SIZE)
    volume_icon_css, _ = layout.update_element_declarations(volume_icon_css, volume_icon_id, {"pointer-events": "none"})
    footer_parts.append((volume_icon_html, volume_icon_css, volume_icon_element))

    volume_x = right_x + volume_icon_size + spacing.SPACING_UNIT
    # CORRECTED 2026-09-18 -- real bugs, live-reported ("the slider is using
    # a square handle and it is not centred with the speaker and mute
    # buttons"): the previous fix wrongly assumed handle shape/size wasn't
    # controllable and tried to fake it by shrinking the component's own
    # bounding box -- that broke vertical centering with its siblings AND
    # never touched the actual shape. `handleshape`/`handlesize` are REAL,
    # direct ch5-slider ATTRIBUTES (confirmed against the real CH5 component
    # library's own metadata, @crestron/ch5-crcomlib's sass-metadata.json --
    # the schema's own default is `handleshape="rounded-rectangle"`, which is
    # the actual, confirmed cause of the square-ish handle, not a styling
    # gap). Height restored to match every other footer element
    # (FOOTER_NAV_BUTTON_HEIGHT), so its own `(footer_height - height) // 2`
    # centering is identical to the speaker icon and mute button beside it.
    volume_height = styleguide.FOOTER_NAV_BUTTON_HEIGHT
    volume_html, volume_css, volume_element = component.build_component(
        sdk, "ch5-slider", component_name="Volume", element_id=generate_element_id(),
        x=volume_x, y=(footer_height - volume_height) // 2,
        width=volume_slider_width, height=volume_height, z_index=1, resolution=resolution,
        active_font=active_font, overrides={"handleshape": "circle", "handlesize": "small"},
    )
    volume_id = dict(volume_element.attributes)["id"]
    # Volume's own designated color (styleguide §4: "handle... in the sky
    # accent (volume's designated color)") -- a real, distinct role from the
    # amber "on/active" accent used everywhere else in this footer. FIXED
    # 2026-09-18 -- real bug, pixel-confirmed against the reviewed PDF: the
    # filled bar has NO separate border of its own (a clean solid fill, the
    # previous PANEL_BORDER_COLOR/1px border was never in the reference at
    # all), and the handle needs its OWN white-fill + sky-ring treatment
    # (newly added palette.py handle_* keys) -- it was previously left
    # entirely unstyled, scaling to a disproportionately large default.
    volume_css = palette.apply_palette(
        volume_css, volume_id, sdk, "ch5-slider",
        palette.applicable_subset("ch5-slider", palette.derive_states({
            "background_color": styleguide.ACCENT_SKY,
            "border_width": "0px",
            "text_color": PANEL_TEXT_COLOR,
            "handle_background_color": styleguide.SURFACE,
            "handle_border_color": styleguide.ACCENT_SKY,
            "handle_border_width": "2px",
            "handle_border_style": "solid",
        })),
    )
    footer_parts.append((volume_html, volume_css, volume_element))

    # Volume Mute: same button-not-toggle correction as Privacy Mute, same
    # 37x37 circle spec.
    mute_html, mute_css, mute_element = component.build_component(
        sdk, "ch5-button", component_name="Volume Mute", element_id=generate_element_id(),
        x=volume_x + volume_slider_width + spacing.SPACING_UNIT,
        y=(footer_height - styleguide.FOOTER_ICON_BUTTON_SIZE) // 2,
        width=styleguide.FOOTER_ICON_BUTTON_SIZE, height=styleguide.FOOTER_ICON_BUTTON_SIZE, z_index=1,
        resolution=resolution, active_font=active_font, label="", icon_class="fa-solid fa-volume-xmark",
        icon_library="FA Classic Solid", overrides={"labelinnerhtml": ""},
    )
    mute_id = dict(mute_element.attributes)["id"]
    mute_html, mute_css = shape.apply_radius_px(
        mute_html, mute_css, mute_id, sdk, "ch5-button", styleguide.FOOTER_NAV_BUTTON_RADIUS)
    mute_css = palette.apply_palette(mute_css, mute_id, sdk, "ch5-button", _footer_button_palette(emphasis=True))
    mute_css = typography.apply_icon_size(mute_css, mute_id, sdk, "ch5-button", 17)
    footer_parts.append((mute_html, mute_css, mute_element))

    footer_html = footer_container_html + "".join(h for h, _, _ in footer_parts)
    footer_css = footer_container_css + "".join(c for _, c, _ in footer_parts)
    footer_elements = [footer_container_element] + [e for _, _, e in footer_parts]

    # --- modals: one per subsystem, Camera gets real content, everything else empty -
    modal_widgets: dict[str, tuple] = {}
    # Styleguide §5 "Modal sheet": max-width 640px, max-height 82vh -- capped
    # against the panel's own size so a narrower/shorter panel than the
    # 1280x800 target viewport still gets a card that actually fits.
    modal_card_width = min(round(panel_width * 0.6), modal.MAX_WIDTH)
    modal_card_height = min(round(panel_height * 0.85), round(panel_height * modal.MAX_HEIGHT_VH_FRACTION))
    if camera_presets and not any(_is_camera_subsystem(s) for s in subsystems):
        raise ValueError(
            f"camera_presets given but no subsystem in {subsystems!r} matches "
            f"'Camera' (case/pluralization-insensitive) -- rename the subsystem "
            f"or drop camera_presets"
        )
    for label in subsystems:
        if _is_camera_subsystem(label):
            def content_builder(x, y, width, height, z_index, _presets=camera_presets):
                return camera_control.build_camera_control(
                    sdk, x=x, y=y, width=width, height=height, z_index=z_index,
                    resolution=resolution, presets=_presets, active_font=active_font)
        else:
            def content_builder(x, y, width, height, z_index):
                return "", "", []
        widget_id, widget_attrs, html, css, elements = modal.build_modal_widget(
            sdk, widget_width=panel_width, widget_height=panel_height,
            widget_name=f"{label} Modal", title=label, card_width=modal_card_width,
            card_height=modal_card_height, content_builder=content_builder,
            resolution=resolution, active_font=active_font,
        )
        modal_widgets[label] = (widget_id, widget_attrs, html, css, elements)

    # --- splash page: room name + headline + caller-supplied action tiles -----------
    splash_page_attrs = build_page_attributes(
        name="Splash", is_start_page=True,
        display_background_color=True, background_color=SPLASH_BACKGROUND_COLOR,
    )
    splash_parts: list[tuple[str, str, Element]] = []
    if splash_tiles:
        room_html, room_css, room_element = component.build_component(
            sdk, "ch5-text", component_name="Splash Room Name", element_id=generate_element_id(),
            x=0, y=SPLASH_HEADLINE_TOP, width=panel_width, height=SPLASH_ROOM_NAME_HEIGHT,
            z_index=1, resolution=resolution, active_font=active_font, label=room_name,
            overrides={"labelinnerhtml": room_name, "horizontalalignment": "center"},
        )
        room_id = dict(room_element.attributes)["id"]
        room_css = typography.apply_font_size(room_css, room_id, sdk, "ch5-text", typography.TYPE_SCALE["caption"])
        room_css = typography.apply_font_weight(room_css, room_id, sdk, "ch5-text", 700)
        room_palette = palette.applicable_subset(
            "ch5-text", palette.derive_states({"text_color": PANEL_MUTED_TEXT_COLOR}))
        room_css = palette.apply_palette(room_css, room_id, sdk, "ch5-text", room_palette)
        splash_parts.append((room_html, room_css, room_element))

        headline_y = SPLASH_HEADLINE_TOP + SPLASH_ROOM_NAME_HEIGHT + spacing.SPACING_UNIT
        # Reviewed design's headline is bold + uppercase. No text-transform
        # property exists for ch5-text (confirmed via style.style_property_
        # catalog -- font-weight/letter-spacing/etc. are real, text-transform
        # is not), so uppercase is applied to the literal string instead.
        headline_text = splash_headline.upper()
        headline_html, headline_css, headline_element = component.build_component(
            sdk, "ch5-text", component_name="Splash Headline", element_id=generate_element_id(),
            x=0, y=headline_y, width=panel_width, height=SPLASH_HEADLINE_HEIGHT,
            z_index=1, resolution=resolution, active_font=active_font, label=headline_text,
            overrides={"labelinnerhtml": headline_text, "horizontalalignment": "center"},
        )
        headline_id = dict(headline_element.attributes)["id"]
        headline_css = typography.apply_font_size(
            headline_css, headline_id, sdk, "ch5-text", typography.TYPE_SCALE["heading"])
        headline_css = typography.apply_font_weight(headline_css, headline_id, sdk, "ch5-text", 800)
        headline_palette = palette.applicable_subset(
            "ch5-text", palette.derive_states({"text_color": PANEL_TEXT_COLOR}))
        headline_css = palette.apply_palette(headline_css, headline_id, sdk, "ch5-text", headline_palette)
        splash_parts.append((headline_html, headline_css, headline_element))

        tiles_y = headline_y + SPLASH_HEADLINE_HEIGHT + SPLASH_TILES_GAP_ABOVE
        tiles_total_width = len(splash_tiles) * SPLASH_TILE_WIDTH + (len(splash_tiles) - 1) * spacing.SPACING_UNIT
        if tiles_total_width > panel_width:
            raise ValueError(
                f"{len(splash_tiles)} splash tiles at {SPLASH_TILE_WIDTH}px each don't "
                f"fit within a {panel_width}px panel -- fewer tiles or a narrower tile"
            )
        tiles_x = (panel_width - tiles_total_width) // 2
        for i, tile in enumerate(splash_tiles):
            label, icon_class, subtitle = tile if len(tile) == 3 else (*tile, None)
            x = tiles_x + i * (SPLASH_TILE_WIDTH + spacing.SPACING_UNIT)

            # Card: the real tap target (contract signals live here), no
            # native label/icon of its own -- see the module comment above
            # SPLASH_TILE_PADDING_TOP for why this is 4 explicit pieces
            # instead of one ch5-button with iconposition="top".
            html, css, element = component.build_component(
                sdk, "ch5-button", component_name=f"Splash {label}", element_id=generate_element_id(),
                x=x, y=tiles_y, width=SPLASH_TILE_WIDTH, height=SPLASH_TILE_HEIGHT,
                z_index=1, resolution=resolution, active_font=active_font, label="",
                overrides={"labelinnerhtml": ""},
            )
            tile_id = dict(element.attributes)["id"]
            html, css = shape.apply_radius_px(html, css, tile_id, sdk, "ch5-button", styleguide.CARD_RADIUS)
            tile_palette = palette.applicable_subset("ch5-button", palette.derive_states({
                "background_color": PANEL_SURFACE_COLOR,
                "border_color": PANEL_BORDER_COLOR,
                "border_width": "1px",
                "border_style": "solid",
            }))
            css = palette.apply_palette(css, tile_id, sdk, "ch5-button", tile_palette)
            splash_parts.append((html, css, element))

            # Badge: circular html-div, amber-dim fill, centered horizontally,
            # a fixed offset from the tile's top -- non-interactive (a flat
            # sibling div, same technique modal.py's card/backdrop use).
            badge_x = x + (SPLASH_TILE_WIDTH - SPLASH_BADGE_SIZE) // 2
            badge_y = tiles_y + SPLASH_TILE_PADDING_TOP
            badge_html, badge_css, badge_element = build_html_div(
                component_name=f"Splash {label} Badge", element_id=generate_element_id(),
                x=badge_x, y=badge_y, width=SPLASH_BADGE_SIZE, height=SPLASH_BADGE_SIZE, z_index=2,
                resolution=resolution, background_color=styleguide.ACCENT_AMBER_DIM,
                border_radius=SPLASH_BADGE_SIZE // 2,
            )
            splash_parts.append((badge_html, badge_css, badge_element))

            # Icon: a small icon-only button centered on the badge, transparent
            # everywhere so only the icon glyph itself shows, pointer-events:
            # none so the tap falls through to the card underneath (same
            # proven technique as the subtitle overlay below).
            icon_size = SPLASH_BADGE_ICON_SIZE + 2 * spacing.SPACING_UNIT
            icon_html, icon_css, icon_element = component.build_component(
                sdk, "ch5-button", component_name=f"Splash {label} Icon", element_id=generate_element_id(),
                x=badge_x + (SPLASH_BADGE_SIZE - icon_size) // 2, y=badge_y + (SPLASH_BADGE_SIZE - icon_size) // 2,
                width=icon_size, height=icon_size, z_index=3, resolution=resolution,
                active_font=active_font, label="", icon_class=icon_class, icon_library="FA Classic Solid",
                overrides={"labelinnerhtml": ""},
            )
            icon_id = dict(icon_element.attributes)["id"]
            icon_palette = palette.applicable_subset("ch5-button", palette.derive_states({
                "background_color": "transparent",
                "pressed_background_color": "transparent",
                "selected_background_color": "transparent",
                "border_width": "0px",
                "icon_color": PANEL_ACCENT_COLOR,
            }))
            icon_css = palette.apply_palette(icon_css, icon_id, sdk, "ch5-button", icon_palette)
            icon_css = typography.apply_icon_size(icon_css, icon_id, sdk, "ch5-button", SPLASH_BADGE_ICON_SIZE)
            icon_css, _ = layout.update_element_declarations(icon_css, icon_id, {"pointer-events": "none"})
            splash_parts.append((icon_html, icon_css, icon_element))

            # Label: bold, centered, below the badge -- non-interactive overlay,
            # same technique as the subtitle below.
            label_y = badge_y + SPLASH_BADGE_SIZE + SPLASH_BADGE_LABEL_GAP
            label_html, label_css, label_element = component.build_component(
                sdk, "ch5-text", component_name=f"Splash {label} Label", element_id=generate_element_id(),
                x=x, y=label_y, width=SPLASH_TILE_WIDTH, height=SPLASH_TILE_LABEL_HEIGHT,
                z_index=2, resolution=resolution, active_font=active_font, label=label,
                overrides={"labelinnerhtml": label, "horizontalalignment": "center"},
            )
            label_id = dict(label_element.attributes)["id"]
            label_css = typography.apply_font_size(label_css, label_id, sdk, "ch5-text", typography.TYPE_SCALE["label"])
            label_css = typography.apply_font_weight(label_css, label_id, sdk, "ch5-text", 700)
            label_css = palette.apply_palette(
                label_css, label_id, sdk, "ch5-text",
                palette.applicable_subset("ch5-text", palette.derive_states({"text_color": PANEL_TEXT_COLOR})))
            label_css, _ = layout.update_element_declarations(label_css, label_id, {"pointer-events": "none"})
            splash_parts.append((label_html, label_css, label_element))

            if subtitle:
                # Non-interactive overlay (pointer-events:none, same mechanism
                # Room Card uses -- Construct's own wifi-gauge component does
                # this for exactly this reason) so the tap still reaches the
                # button underneath, not a separate control. Positioned right
                # after the label (SPLASH_LABEL_SUBTITLE_GAP), not pinned to
                # the tile's bottom edge -- real user feedback (2026-09-18):
                # "the second line of text is supposed to be closer to the
                # label," smaller than it too (see SPLASH_SUBTITLE_FONT_SIZE).
                sub_html, sub_css, sub_element = component.build_component(
                    sdk, "ch5-text", component_name=f"Splash {label} Subtitle",
                    element_id=generate_element_id(),
                    x=x, y=label_y + SPLASH_TILE_LABEL_HEIGHT + SPLASH_LABEL_SUBTITLE_GAP,
                    width=SPLASH_TILE_WIDTH, height=SPLASH_SUBTITLE_HEIGHT, z_index=2, resolution=resolution,
                    active_font=active_font, label=subtitle,
                    overrides={"labelinnerhtml": subtitle, "horizontalalignment": "center"},
                )
                sub_id = dict(sub_element.attributes)["id"]
                sub_css = typography.apply_font_size(sub_css, sub_id, sdk, "ch5-text", SPLASH_SUBTITLE_FONT_SIZE)
                sub_css = palette.apply_palette(
                    sub_css, sub_id, sdk, "ch5-text",
                    palette.applicable_subset("ch5-text", palette.derive_states({"text_color": PANEL_MUTED_TEXT_COLOR})))
                sub_css, _ = layout.update_element_declarations(sub_css, sub_id, {"pointer-events": "none"})
                splash_parts.append((sub_html, sub_css, sub_element))
    splash_html = "".join(h for h, _, _ in splash_parts)
    splash_css = "".join(c for _, c, _ in splash_parts)
    splash_elements = [e for _, _, e in splash_parts]

    # --- main panel page: header/footer/tab-content/modal widget references ---------
    # FIXED 2026-09-18 -- real bug, user caught it directly ("why didnt you
    # set the page background color? this was already covered in a previous
    # session"): unlike Splash (which explicitly sets display_background_
    # color/background_color above), this page never had a background color
    # at all -- it fell back to Construct's raw canvas default (black),
    # visible anywhere no widget's own opaque div happens to cover it.
    main_panel_attrs = build_page_attributes(
        name="Main Panel", display_background_color=True, background_color=styleguide.BACKGROUND,
    )
    main_panel_html = ""
    main_panel_css_parts: list[str] = []
    main_panel_elements: list[Element] = []
    widget_placements = [
        (header_widget_id, "Header", 0, 0, 1),
        (footer_widget_id, "Footer", 0, panel_height - footer_height, 1),
        *[(wid, f"{mode} Content", 0, header_height, 1) for mode, (wid, *_rest) in tab_content_widgets.items()],
        *[(wid, f"{label} Modal", 0, 0, 2) for label, (wid, *_rest) in modal_widgets.items()],
    ]
    for widget_id, widget_name, wx, wy, wz in widget_placements:
        main_panel_html, main_panel_elements = add_widget_reference_to_page(
            sdk, main_panel_html, main_panel_elements, widget_id, widget_name)
        ref_element = main_panel_elements[-1]
        ref_id = dict(ref_element.attributes)["id"]
        main_panel_css_parts.append(
            widget_reference_position_css(ref_id, x=wx, y=wy, z_index=wz, resolution=resolution))
    main_panel_css = "".join(main_panel_css_parts)

    return {
        "splash_page": (splash_page_attrs, splash_html, splash_css, splash_elements),
        "main_panel_page": (main_panel_attrs, main_panel_html, main_panel_css, main_panel_elements),
        "header_widget": (header_widget_id, header_widget_attrs, header_html, header_css, header_elements),
        "footer_widget": (footer_widget_id, footer_widget_attrs, footer_html, footer_css, footer_elements),
        "tab_content_widgets": tab_content_widgets,
        "modal_widgets": modal_widgets,
    }
