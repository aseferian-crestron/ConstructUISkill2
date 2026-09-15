"""
Html-div -- Construct's own "pure HTML5" component, per design-system §7's rule
("Related controls grouped visually -- shared background, spacing, or a
border") the real mechanism that rule was missing. It is NOT a ch5-* custom
element and NOT in component-context.json's own schema at all (confirmed:
`sdk.read_sdk(...).component_context` carries 50 top-level tags, none named
"div"/"html-div") -- so unlike every other component this project builds, there
is no SDK schema to read attributes or style properties from. This module is
grounded directly against two real reference instances instead:

- `C:\\Solutions\\ClaudeSamples\\Components\\Component - DIV.cuig` (2026-09-15,
  one instance) -- treated as authoritative/current.
- `Component - HTML - DIV.cuig` (2026-09-03, two instances) -- its [[Elements]]
  block carries extra `Name=""`/`Status=""`/`Content=""` scalar fields the newer
  file omits entirely; treated as a stale serialization shape (same precedent
  this project already applies whenever two real files disagree -- most recent
  wins, see e.g. ButtonVariants.cuig's shape="custom" drift note in the plan).

Two real, confirmed quirks, neither guessable from the rest of this codebase:

1. The Html tag is literally `<div>` (the browser's own element, lowercase) --
   the TOML `[[Elements]]` block's `Type` is the separate literal `"html-div"`.
   Neither is schema-derived; both are hardcoded here, the same way
   `component.py::_CHILD_TYPE_NAMES` hardcodes child element type names no
   schema carries either.
2. `ccid_lteHTMLOnly` is a genuine HTML boolean attribute in the Html section
   (no `="value"` at all, confirmed against the real file byte-for-byte) but an
   ordinary `"true"`-valued key in the TOML `[Elements.Attributes]` table -- a
   real Html/TOML asymmetry unique to this component, not a bug to normalize
   away.

Styling: unlike every ch5-* component (styled via `--ch5-*` CSS custom
properties, see style.py, because that indirection is what the CH5 web
component's own property grid reads via `getNearestPropValue`), a div's
background-color/border-*/border-radius are PLAIN literal CSS declarations
written straight into its own `#id{...}` rule -- confirmed against the
reference's catch-all block. That is exactly the shape
`layout.py::build_position_css`'s existing `extra_vars` parameter already
produces (arbitrary `name: value;` pairs, no `--` prefix required) and
`layout.py::update_element_declarations`'s existing merge-by-name logic already
re-applies later for a restyle -- both reused as-is here, no new CSS-writing
mechanism needed. Also confirmed duplicated into the PRIMARY-resolution block
(the reference's second @media entry restates the full property set), matching
the already-established catch-all + primary rule every other themed property in
this project already follows -- `build_position_css` already does this for any
`extra_vars` passed to it, so a div gets this for free.
"""
from __future__ import annotations

from elements import Element
from layout import build_position_css, update_element_declarations

DEFAULT_DEVICES_VISITED = '["TSW-1070, TSW-1070"]'


def _div_style_vars(
    *,
    background_color: str | None,
    border_color: str | None,
    border_width: int | None,
    border_style: str,
    border_radius: int | tuple[int, int, int, int] | None,
) -> dict[str, str]:
    """Literal CSS declarations for a div's fill/border, in the reference's own
    order (background-color, border-style, border-width, border-color,
    border-radius last) -- order doesn't affect rendering, but matching it
    keeps a human diff against a real file easy to read. Every property is
    optional and touched only when given -- used both for a brand-new div
    (build_html_div, which also always adds white-space:normal, a fixed
    reference default) and for restyling an EXISTING one (style_html_div, which
    must leave anything not explicitly passed untouched).
    """
    style_vars: dict[str, str] = {}
    if background_color is not None:
        style_vars["background-color"] = background_color
    if border_color is not None or border_width is not None:
        style_vars["border-style"] = border_style
    if border_width is not None:
        style_vars["border-width"] = f"{border_width}px"
    if border_color is not None:
        style_vars["border-color"] = border_color
    if border_radius is not None:
        corners = (border_radius,) * 4 if isinstance(border_radius, int) else border_radius
        style_vars["border-radius"] = " ".join(f"{c}px" for c in corners)
    return style_vars


def build_html_div(
    *,
    component_name: str,
    element_id: str,
    x: int,
    y: int,
    width: int,
    height: int,
    z_index: int,
    resolution: tuple[int, int] | None = None,
    background_color: str | None = None,
    border_color: str | None = None,
    border_width: int | None = None,
    border_style: str = "solid",
    border_radius: int | tuple[int, int, int, int] | None = None,
    devices_visited: str = DEFAULT_DEVICES_VISITED,
) -> tuple[str, str, Element]:
    """(html, css, Element) for one html-div, ready for page.py::write_cuig --
    the same return shape as component.py::build_component, so it composes into
    a layout-pattern builder's assembly (see layout_patterns.py) with zero
    friction. Used to group other components with a shared background/border
    (design-system §7): place this BEHIND the controls it groups (a lower
    z_index) since it is a flat sibling element, not a parent that reparents
    them in the [[Elements]] tree -- confirmed from the reference, which has no
    nested [[Elements.Components]] at all.
    """
    html = (
        f'<div labelmode="advanced" ccid_lteHTMLOnly componentName="{component_name}" '
        f'id="{element_id}" ccid_ComponentType="Html-div" devicesVisited="{devices_visited}">'
        f"</div>"
    )
    attributes = [
        ("labelmode", "advanced"),
        ("ccid_lteHTMLOnly", "true"),
        ("componentName", component_name),
        ("id", element_id),
        ("ccid_ComponentType", "Html-div"),
        ("devicesVisited", devices_visited),
    ]
    style_vars = _div_style_vars(
        background_color=background_color, border_color=border_color,
        border_width=border_width, border_style=border_style, border_radius=border_radius,
    )
    # Fixed reference default for a brand-new div (present in both real
    # instances regardless of fill/border) -- not a caller-configurable knob,
    # and deliberately not part of _div_style_vars (style_html_div's restyle
    # path must never touch a property the caller didn't ask about).
    style_vars["white-space"] = "normal"
    css = build_position_css(
        element_id, x=x, y=y, width=width, height=height, z_index=z_index,
        resolution=resolution, extra_vars=style_vars,
    )
    element = Element(type="html-div", attributes=attributes)
    return html, css, element


def style_html_div(
    css_text: str,
    element_id: str,
    *,
    background_color: str | None = None,
    border_color: str | None = None,
    border_width: int | None = None,
    border_style: str = "solid",
    border_radius: int | tuple[int, int, int, int] | None = None,
    primary_query: str | None = None,
) -> tuple[str, int]:
    """Restyle an EXISTING div in place -- only the keys given are touched (an
    omitted style property is left as whatever it already was), reusing
    `layout.py::update_element_declarations` directly since a div's properties
    are already plain CSS with no ch5-specific sector-prefix pseudo-property to
    also write (that mechanism is for a CH5 web component's own property grid;
    a native `<div>` carries none of that). `primary_query`, when given (the
    project's primary resolution's own query -- see theme_chat.py::
    _primary_query_for), gets the same catch-all + primary duplication every
    other themed property in this project follows.

    Returns `(new_css_text, blocks_updated)`.
    """
    style_vars = _div_style_vars(
        background_color=background_color, border_color=border_color,
        border_width=border_width, border_style=border_style, border_radius=border_radius,
    )
    extra_queries = (primary_query,) if primary_query else ()
    return update_element_declarations(css_text, element_id, style_vars, extra_queries=extra_queries)
