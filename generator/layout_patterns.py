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
import modal
import palette
import shape
import spacing
import style
import typography
from elements import Element
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
    item_count: int, row_width: int, row_height: int,
) -> list[tuple[int, int, int, int]]:
    """`(x, y, width, height)` for `item_count` items evenly spaced in a
    single row spanning `row_width`, honoring spacing.EDGE_PADDING at both
    ends and spacing.SPACING_UNIT gaps between items -- the same shape as
    `_layout_row`, deliberately NOT reusing it: `_layout_row`'s own
    `snap_to_spacing` step rounds each item's width up to the nearest
    spacing-unit multiple, which can push the summed row width a few pixels
    over `row_width` in cases `_layout_row`'s existing callers never hit
    (verified directly: both a 2-tile splash row at a full panel size and a
    3-button footer subsystem zone overflow this way with real Phase 1
    numbers -- `_layout_row(3, 1280 // 3, 120)` and `_layout_row(2, 1280,
    800)` both raise `ValueError` on numbers that clearly ought to fit).
    Floor division only, no snapping -- items come out a few px narrower
    than `_layout_row` would produce, never wider than the row, so the
    summed width can never exceed it. Raises ValueError if `item_count`
    doesn't fit at the touch-target floor.
    """
    item_height = max(row_height - 2 * spacing.EDGE_PADDING, spacing.MIN_TOUCH_TARGET)
    usable_width = row_width - 2 * spacing.EDGE_PADDING
    gap_total = spacing.SPACING_UNIT * (item_count - 1)
    item_width = (usable_width - gap_total) // item_count
    if item_width < spacing.MIN_TOUCH_TARGET:
        raise ValueError(
            f"{item_count} items at the {spacing.MIN_TOUCH_TARGET}px touch-target floor "
            f"need more than the {row_width}px available width -- reduce item_count "
            f"or use a wider row"
        )
    positions = []
    x = spacing.EDGE_PADDING
    for _ in range(item_count):
        positions.append((x, spacing.EDGE_PADDING, item_width, item_height))
        x += item_width + spacing.SPACING_UNIT
    return positions


def _is_camera_subsystem(label: str) -> bool:
    """Case/pluralization-insensitive match for the Camera subsystem -- the
    reference spec's own Generic Specifications example uses "Cameras"
    (plural), which a bare `label == "Camera"` check would silently miss,
    producing an empty modal with `camera_presets` discarded and no error.
    See the Final review fix note in
    docs/superpowers/plans/2026-09-17-tabbed-layout-commercial.md.
    """
    return label.strip().rstrip("s").lower() == "camera"


#: Splash page visual treatment -- default styling taken directly from the
#: stakeholder-reviewed reference mockup (docs/construct-tabbed-ui-screens-
#: commercial.pdf, "Tabbed Panel -- Splash" page), per the user's direction
#: (2026-09-17): when the caller hasn't supplied their own design/color
#: scheme, the default IS that reviewed mockup, not a separately-invented
#: persona palette. Light neutral page background, white bordered cards,
#: warm amber accent on the icon/label.
SPLASH_BACKGROUND_COLOR = "#EEF1F5"
SPLASH_TEXT_COLOR = "#1A1D23"
SPLASH_MUTED_TEXT_COLOR = "#6B7280"
SPLASH_TILE_BACKGROUND_COLOR = "#FFFFFF"
SPLASH_TILE_BORDER_COLOR = "#E2E5EA"
SPLASH_ACCENT_COLOR = "#C9822E"
SPLASH_HEADLINE_TOP = 200
SPLASH_ROOM_NAME_HEIGHT = 24
SPLASH_HEADLINE_HEIGHT = 48
SPLASH_TILES_GAP_ABOVE = 40
SPLASH_TILE_WIDTH = 220
SPLASH_TILE_HEIGHT = 260


def build_tabbed_shell(
    sdk: UiSdk, *, room_name: str, splash_tiles: list[tuple[str, str]],
    additional_system_modes: list[str], subsystems: list[str],
    camera_presets: list[str], panel_width: int, panel_height: int,
    header_height: int = 160, footer_height: int = 120,
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

    # --- header: 2 rows, logo spans both -------------------------------------------
    logo_size = header_height
    left_column_width = panel_width - logo_size - spacing.SPACING_UNIT
    if left_column_width <= 0:
        raise ValueError(
            f"a {panel_width}px wide panel is too narrow for a {logo_size}px "
            f"square logo spanning the full header height"
        )
    top_row_height = round(header_height * 0.6)
    bottom_row_height = header_height - top_row_height
    # The room-name/date-time stack starts at y=EDGE_PADDING (not y=0), so that
    # top inset has to come out of the same top_row_height budget too, or the
    # stack's real bottom edge lands EDGE_PADDING past top_row_height and
    # silently overlaps the tab strip below it.
    room_name_height = top_row_height - spacing.EDGE_PADDING - _DATETIME_HEIGHT - spacing.SPACING_UNIT
    if room_name_height <= 0:
        raise ValueError(
            f"a {header_height}px header is too short for the room-name/date-time "
            f"stack (needs {spacing.EDGE_PADDING + _DATETIME_HEIGHT + spacing.SPACING_UNIT}px+ "
            f"in the top row)"
        )

    header_widget_id = str(uuid4())
    header_widget_attrs = build_widget_attributes(name="Header", widget_id=header_widget_id)
    header_container_html, header_container_css, header_container_element = default_widget_html_css(
        generate_element_id(), panel_width, header_height, resolution, is_global=True)
    header_parts: list[tuple[str, str, Element]] = []

    room_name_html, room_name_css, room_name_element = component.build_component(
        sdk, "ch5-text", component_name="Room Name", element_id=generate_element_id(),
        x=spacing.EDGE_PADDING, y=spacing.EDGE_PADDING,
        width=left_column_width - 2 * spacing.EDGE_PADDING, height=room_name_height,
        z_index=1, resolution=resolution, active_font=active_font, label=room_name,
        overrides={"labelinnerhtml": room_name},
    )
    header_parts.append((room_name_html, room_name_css, room_name_element))

    datetime_html, datetime_css, datetime_element = component.build_component(
        sdk, "ch5-datetime", component_name="Header DateTime", element_id=generate_element_id(),
        x=spacing.EDGE_PADDING, y=spacing.EDGE_PADDING + room_name_height + spacing.SPACING_UNIT,
        width=_DATETIME_WIDTH, height=_DATETIME_HEIGHT, z_index=1, resolution=resolution,
        active_font=active_font,
    )
    header_parts.append((datetime_html, datetime_css, datetime_element))

    logo_html, logo_css, logo_element = component.build_component(
        sdk, "ch5-image", component_name="Logo", element_id=generate_element_id(),
        x=panel_width - logo_size, y=0, width=logo_size, height=logo_size,
        z_index=1, resolution=resolution, active_font=active_font,
        overrides={"assetid": logo_asset_id},
    )
    header_parts.append((logo_html, logo_css, logo_element))

    tab_strip_html, tab_strip_css, tab_strip_element = component.build_component(
        sdk, "ch5-tab-button", component_name="System Mode Tabs", element_id=generate_element_id(),
        x=0, y=top_row_height, width=left_column_width, height=bottom_row_height,
        z_index=1, resolution=resolution, active_font=active_font,
        overrides={"numberofitems": str(len(system_modes))},
    )
    tab_child_ids = [dict(child.attributes)["id"] for child in tab_strip_element.components]
    for child_id, mode_label in zip(tab_child_ids, system_modes):
        tab_strip_html = style.set_html_attribute(tab_strip_html, child_id, "labelinnerhtml", mode_label)
    header_parts.append((tab_strip_html, tab_strip_css, tab_strip_element))

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
    footer_parts: list[tuple[str, str, Element]] = []

    # Center/right zones are sized to their own real fixed content (a square
    # toggle, a comfortably-usable slider + a mute button), not an equal
    # 3-way split -- equal thirds starves the left zone at low subsystem
    # counts and wastes space at high ones. The left zone gets whatever's
    # left of the panel width.
    center_zone_width = max(footer_height, spacing.MIN_TOUCH_TARGET) + 2 * spacing.EDGE_PADDING
    volume_slider_width = 120  # judgment call: comfortably usable, not just the touch-target floor
    right_zone_width = (
        volume_slider_width + spacing.MIN_TOUCH_TARGET + spacing.SPACING_UNIT + 2 * spacing.EDGE_PADDING
    )
    left_zone_width = panel_width - center_zone_width - right_zone_width
    if left_zone_width <= 0:
        raise ValueError(
            f"a {panel_width}px panel has no room left for footer subsystem buttons "
            f"after the center Privacy Mute and right volume/mute zones"
        )

    left_positions = _layout_tabbed_row(len(subsystems), left_zone_width, footer_height)
    for label, (x, y, w, h) in zip(subsystems, left_positions):
        html, css, element = component.build_component(
            sdk, "ch5-button", component_name=f"Footer {label}", element_id=generate_element_id(),
            x=x, y=y, width=w, height=h, z_index=1, resolution=resolution,
            active_font=active_font, label=label,
        )
        footer_parts.append((html, css, element))

    center_size = max(min(center_zone_width, footer_height) - 2 * spacing.EDGE_PADDING, spacing.MIN_TOUCH_TARGET)
    privacy_html, privacy_css, privacy_element = component.build_component(
        sdk, "ch5-toggle", component_name="Privacy Mute", element_id=generate_element_id(),
        x=left_zone_width + (center_zone_width - center_size) // 2, y=(footer_height - center_size) // 2,
        width=center_size, height=center_size, z_index=1, resolution=resolution,
        active_font=active_font, label="Privacy Mute",
    )
    footer_parts.append((privacy_html, privacy_css, privacy_element))

    right_x = left_zone_width + center_zone_width
    volume_height = max(footer_height - 2 * spacing.EDGE_PADDING, spacing.MIN_TOUCH_TARGET)
    volume_html, volume_css, volume_element = component.build_component(
        sdk, "ch5-slider", component_name="Volume", element_id=generate_element_id(),
        x=right_x + spacing.EDGE_PADDING, y=(footer_height - volume_height) // 2,
        width=volume_slider_width, height=volume_height, z_index=1, resolution=resolution,
        active_font=active_font,
    )
    footer_parts.append((volume_html, volume_css, volume_element))
    mute_html, mute_css, mute_element = component.build_component(
        sdk, "ch5-toggle", component_name="Volume Mute", element_id=generate_element_id(),
        x=right_x + spacing.EDGE_PADDING + volume_slider_width + spacing.SPACING_UNIT,
        y=(footer_height - spacing.MIN_TOUCH_TARGET) // 2,
        width=spacing.MIN_TOUCH_TARGET, height=spacing.MIN_TOUCH_TARGET, z_index=1,
        resolution=resolution, active_font=active_font, label="Mute",
    )
    footer_parts.append((mute_html, mute_css, mute_element))

    footer_html = footer_container_html + "".join(h for h, _, _ in footer_parts)
    footer_css = footer_container_css + "".join(c for _, c, _ in footer_parts)
    footer_elements = [footer_container_element] + [e for _, _, e in footer_parts]

    # --- modals: one per subsystem, Camera gets real content, everything else empty -
    modal_widgets: dict[str, tuple] = {}
    modal_card_width = round(panel_width * 0.6)
    # Tall enough that Camera's real content (3 stacked bands, see
    # camera_control.py) fits its content area with room to spare -- verified
    # directly: a 0.6 fraction leaves Camera's content area 9px too short at
    # this plan's own default panel size, a 0.85 fraction leaves 11px margin.
    modal_card_height = round(panel_height * 0.85)
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
        room_css = palette.apply_palette(room_css, room_id, sdk, "ch5-text", {"text_color": SPLASH_MUTED_TEXT_COLOR})
        splash_parts.append((room_html, room_css, room_element))

        headline_y = SPLASH_HEADLINE_TOP + SPLASH_ROOM_NAME_HEIGHT + spacing.SPACING_UNIT
        headline_html, headline_css, headline_element = component.build_component(
            sdk, "ch5-text", component_name="Splash Headline", element_id=generate_element_id(),
            x=0, y=headline_y, width=panel_width, height=SPLASH_HEADLINE_HEIGHT,
            z_index=1, resolution=resolution, active_font=active_font, label=splash_headline,
            overrides={"labelinnerhtml": splash_headline, "horizontalalignment": "center"},
        )
        headline_id = dict(headline_element.attributes)["id"]
        headline_css = typography.apply_font_size(
            headline_css, headline_id, sdk, "ch5-text", typography.TYPE_SCALE["heading"])
        headline_css = palette.apply_palette(
            headline_css, headline_id, sdk, "ch5-text", {"text_color": SPLASH_TEXT_COLOR})
        splash_parts.append((headline_html, headline_css, headline_element))

        tiles_y = headline_y + SPLASH_HEADLINE_HEIGHT + SPLASH_TILES_GAP_ABOVE
        tiles_total_width = len(splash_tiles) * SPLASH_TILE_WIDTH + (len(splash_tiles) - 1) * spacing.SPACING_UNIT
        if tiles_total_width > panel_width:
            raise ValueError(
                f"{len(splash_tiles)} splash tiles at {SPLASH_TILE_WIDTH}px each don't "
                f"fit within a {panel_width}px panel -- fewer tiles or a narrower tile"
            )
        tiles_x = (panel_width - tiles_total_width) // 2
        for i, (label, icon_class) in enumerate(splash_tiles):
            x = tiles_x + i * (SPLASH_TILE_WIDTH + spacing.SPACING_UNIT)
            html, css, element = component.build_component(
                sdk, "ch5-button", component_name=f"Splash {label}", element_id=generate_element_id(),
                x=x, y=tiles_y, width=SPLASH_TILE_WIDTH, height=SPLASH_TILE_HEIGHT,
                z_index=1, resolution=resolution, active_font=active_font, label=label,
                icon_class=icon_class, icon_library="FA Classic Solid",
            )
            tile_id = dict(element.attributes)["id"]
            html, css = shape.apply_radius_preset(html, css, tile_id, sdk, "ch5-button", "rounded")
            css = palette.apply_palette(
                css, tile_id, sdk, "ch5-button",
                {
                    "background_color": SPLASH_TILE_BACKGROUND_COLOR,
                    "border_color": SPLASH_TILE_BORDER_COLOR,
                    "border_width": "1px",
                    "border_style": "solid",
                    "text_color": SPLASH_TEXT_COLOR,
                    "icon_color": SPLASH_ACCENT_COLOR,
                },
            )
            css = typography.apply_font_size(css, tile_id, sdk, "ch5-button", typography.TYPE_SCALE["body"])
            css = typography.apply_icon_size(css, tile_id, sdk, "ch5-button", typography.ICON_SCALE["body"])
            splash_parts.append((html, css, element))
    splash_html = "".join(h for h, _, _ in splash_parts)
    splash_css = "".join(c for _, c, _ in splash_parts)
    splash_elements = [e for _, _, e in splash_parts]

    # --- main panel page: header/footer/tab-content/modal widget references ---------
    main_panel_attrs = build_page_attributes(name="Main Panel")
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
