"""
Generic modal/dialog widget (primitive tier) -- reusable by any layout
pattern, not Tabbed-specific. Construct's CH5 SDK schema defines
ch5-modal-dialog and ch5-overlay-panel with plausible-looking attributes, but
neither carries `viewProperties.showOnUI: true` in component-context.json
(confirmed 2026-09-17 against the installed 2.18.0 SDK, cross-checked against
zero real authored .cuig/.cuiw files anywhere in C:\\Solutions\\ClaudeSamples or
C:\\Git\\CCIDE using either tag) -- neither is actually exposed in Construct's
own editor, so neither can be used (user, 2026-09-17: "you cant use components
that are not exposed in Construct").

Built instead entirely from primitives already confirmed real: a full-panel
backdrop html-div (semi-transparent, low z-index), a centered card html-div
(the visible dialog box), a title ch5-text, an optional close-icon ch5-button,
and -- since the real html-div reference files carry no click/tap signal of
their own (confirmed: no sendevent* attribute anywhere in
`Component - DIV.cuig`) -- a transparent full-panel ch5-button behind the card
for backdrop-tap dismiss. The whole thing is a WIDGET; its own
Visibility=Contract (set by the caller when referencing it from a page, see
page.py::add_widget_reference_to_page) is the open/close signal -- reuses the
project's already-proven mechanism (ConstructUISkill.md §5), not a new one.

See docs/superpowers/specs/2026-09-17-tabbed-layout-commercial-design.md.
"""
from __future__ import annotations

from typing import Callable
from uuid import uuid4

import component
import palette
import spacing
from elements import Element
from html_div import build_html_div
from page import build_widget_attributes, default_widget_html_css, generate_element_id
from sdk import UiSdk

#: Judgment calls (not a Construct spec), consistent with every other named
#: constant in this project's layout-pattern modules.
TITLE_BAR_HEIGHT = 56
CARD_PADDING = spacing.EDGE_PADDING
CLOSE_BUTTON_SIZE = spacing.MIN_TOUCH_TARGET
BACKDROP_COLOR = "rgba(0, 0, 0, 0.5)"
CARD_BACKGROUND_COLOR = "#ffffff"
CARD_TEXT_COLOR = "#1a1a1a"
CARD_RADIUS = 12

#: (x, y, width, height, z_index) -> (html, css, list[Element]), called once
#: with the content area already computed inside the card.
ContentBuilder = Callable[[int, int, int, int, int], "tuple[str, str, list[Element]]"]


def content_area(card_width: int, card_height: int) -> tuple[int, int, int, int]:
    """(x, y, width, height) of the content region INSIDE a card_width x
    card_height card, relative to the card's own top-left corner -- below the
    title bar, inset by CARD_PADDING on every side. Raises ValueError if the
    card is too small to leave a positive content area."""
    content_x = CARD_PADDING
    content_y = TITLE_BAR_HEIGHT + CARD_PADDING
    content_width = card_width - 2 * CARD_PADDING
    content_height = card_height - TITLE_BAR_HEIGHT - 2 * CARD_PADDING
    if content_width <= 0 or content_height <= 0:
        raise ValueError(
            f"a {card_width}x{card_height} card leaves no room for content below "
            f"the {TITLE_BAR_HEIGHT}px title bar and {CARD_PADDING}px padding on "
            f"every side -- use a larger card_width/card_height"
        )
    return content_x, content_y, content_width, content_height


def build_modal_widget(
    sdk: UiSdk, *, widget_width: int, widget_height: int, widget_name: str,
    title: str, card_width: int, card_height: int, content_builder: ContentBuilder,
    resolution: tuple[int, int] | None = None, active_font: str = "Roboto",
    closable: bool = True, dismissable: bool = True,
) -> tuple[str, list[tuple[str, str]], str, str, list[Element]]:
    """One modal, as a WIDGET (see module docstring for why -- no native
    ch5-modal-dialog is available). `widget_width`/`widget_height` are the full
    panel's own size (the backdrop covers all of it); `card_width`/
    `card_height` the visible dialog box, centered within that.
    `content_builder` is called once with the content area INSIDE the card
    (below the title bar -- see content_area()), already offset to the card's
    real on-widget position; its own return is merged into this widget's
    assembly.

    `closable` adds a close-icon ch5-button in the card's top-right corner.
    `dismissable` adds a transparent, full-panel ch5-button BEHIND the card so
    a tap anywhere on the backdrop closes the modal too (see module
    docstring). This module only builds the buttons -- wiring a press to the
    widget's own Visibility signal is the caller's job (same division of
    responsibility as every other button-driven contract signal in this
    project, ConstructUISkill.md §6).

    Returns `(widget_id, widget_attrs, html, css, elements)` -- the widget_id
    is returned (unlike build_footer_widget/build_header_widget) since a
    modal may be referenced from more than one page.

    Raises ValueError if the card doesn't fit within the panel, or is too
    small to leave a positive content area (see content_area()).
    """
    if card_width > widget_width or card_height > widget_height:
        raise ValueError(
            f"a {card_width}x{card_height} card doesn't fit within the "
            f"{widget_width}x{widget_height} panel it's centered in"
        )
    inner_x, inner_y, inner_w, inner_h = content_area(card_width, card_height)
    card_x = (widget_width - card_width) // 2
    card_y = (widget_height - card_height) // 2

    widget_id = str(uuid4())
    widget_attrs = build_widget_attributes(name=widget_name, widget_id=widget_id)
    container_html, container_css, container_element = default_widget_html_css(
        generate_element_id(), widget_width, widget_height, resolution, is_global=False)

    parts: list[tuple[str, str, Element]] = []

    backdrop_html, backdrop_css, backdrop_element = build_html_div(
        component_name=f"{widget_name} Backdrop", element_id=generate_element_id(),
        x=0, y=0, width=widget_width, height=widget_height, z_index=1,
        resolution=resolution, background_color=BACKDROP_COLOR,
    )
    parts.append((backdrop_html, backdrop_css, backdrop_element))

    if dismissable:
        dismiss_html, dismiss_css, dismiss_element = component.build_component(
            sdk, "ch5-button", component_name=f"{widget_name} Dismiss",
            element_id=generate_element_id(), x=0, y=0, width=widget_width,
            height=widget_height, z_index=2, resolution=resolution, label="",
            active_font=active_font, overrides={"labelinnerhtml": ""},
        )
        dismiss_css = palette.apply_palette(
            dismiss_css, dict(dismiss_element.attributes)["id"], sdk, "ch5-button",
            {"background_color": "transparent", "border_width": "0px"},
        )
        parts.append((dismiss_html, dismiss_css, dismiss_element))

    card_html, card_css, card_element = build_html_div(
        component_name=f"{widget_name} Card", element_id=generate_element_id(),
        x=card_x, y=card_y, width=card_width, height=card_height, z_index=3,
        resolution=resolution, background_color=CARD_BACKGROUND_COLOR,
        border_radius=CARD_RADIUS,
    )
    parts.append((card_html, card_css, card_element))

    title_width = card_width - 2 * CARD_PADDING - (CLOSE_BUTTON_SIZE + CARD_PADDING if closable else 0)
    title_html, title_css, title_element = component.build_component(
        sdk, "ch5-text", component_name=f"{widget_name} Title",
        element_id=generate_element_id(), x=card_x + CARD_PADDING, y=card_y + CARD_PADDING,
        width=title_width, height=TITLE_BAR_HEIGHT - 2 * CARD_PADDING, z_index=4,
        resolution=resolution, active_font=active_font, label=title,
        overrides={"labelinnerhtml": title},
    )
    title_css = palette.apply_palette(
        title_css, dict(title_element.attributes)["id"], sdk, "ch5-text",
        {"text_color": CARD_TEXT_COLOR},
    )
    parts.append((title_html, title_css, title_element))

    if closable:
        close_html, close_css, close_element = component.build_component(
            sdk, "ch5-button", component_name=f"{widget_name} Close",
            element_id=generate_element_id(),
            x=card_x + card_width - CARD_PADDING - CLOSE_BUTTON_SIZE, y=card_y + CARD_PADDING,
            width=CLOSE_BUTTON_SIZE, height=CLOSE_BUTTON_SIZE, z_index=4,
            resolution=resolution, active_font=active_font, label="",
            icon_class="fa-solid fa-xmark", icon_library="FA Classic Solid",
            overrides={"labelinnerhtml": ""},
        )
        parts.append((close_html, close_css, close_element))

    content_html, content_css, content_elements = content_builder(
        card_x + inner_x, card_y + inner_y, inner_w, inner_h, 5)

    html = container_html + "".join(h for h, _, _ in parts) + content_html
    css = container_css + "".join(c for _, c, _ in parts) + content_css
    elements = [container_element] + [e for _, _, e in parts] + list(content_elements)
    return widget_id, widget_attrs, html, css, elements
