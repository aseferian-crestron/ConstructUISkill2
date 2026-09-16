"""
Design-system typography scale (ConstructUISkill_DesignSystem.md §3).

Font-size stylability confirmed 2026-09-15 via style.style_property_catalog for
every currently label/text-bearing type in palette.PALETTE_MAPPING (ch5-button,
ch5-text, ch5-textinput, ch5-toggle, ch5-button-list, ch5-tab-button, ch5-datetime):
each carries a real `font-size` -> `--ch5-*` targetProperty entry. NOTE: each of
these types' schema ALSO carries a second, unrelated `custom-font-size` source
property (target e.g. "custom-normal-label-font-size", no `--` prefix, no sector) --
that is NOT the real CSS var and must never be used; apply_type_scale below always
resolves the real `font-size` source property, the same name style.py's other
callers already use for every other property.

TYPE_SCALE values: caption/heading/title are a judgment call (not a Construct spec,
same precedent as palette.py's PRESSED_LIGHTNESS_DELTA) -- body (22) and label (18)
are the design doc's own explicit floors; the rest fill out a strictly-ascending
scale from there.

Icon-size stylability confirmed 2026-09-16 via style.style_property_catalog for the
three button-family types (ch5-button, ch5-button-list, ch5-tab-button): each carries
a DISTINCT `.ch5-button--icon` selector with its own `font-size` -> `--ch5-button--
regular-icon-size` targetProperty, entirely separate from the label's own font-size
entry -- confirmed as two independent knobs, not one shared size. This is the real
mechanism behind the first Bento Box run's icons reading "too small": nothing ever
wrote this property, so every icon rendered at CH5's own small built-in default
regardless of card size. `apply_icon_scale` reuses the SAME class_name
`palette.PALETTE_MAPPING[tag_name]["icon_color"]` already has for that tag's icon
selector -- confirmed identical selector shape to the catalog entry above.
ICON_SCALE values are a judgment call paired to TYPE_SCALE's roles (an icon reads
correctly when it's visually a bit larger than the label sitting next to it, not the
same size), not a Construct spec.

**2026-09-16 correction:** TYPE_SCALE's roles are calibrated for ORDINARY, normally-
sized UI text/icons (buttons, labels, headings in the usual sense) -- a real user
screenshot showed a Bento Box "large" card (492x492px) styled with TYPE_SCALE["heading"]
(28px) still reading as disproportionately tiny: 28px is a sensible HEADING size for a
normal page, but a dashboard tile spanning half the screen is a fundamentally bigger UI
element than a heading was ever calibrated for. `apply_type_scale`/`apply_icon_scale`
are now named-role wrappers around new explicit-value primitives (`apply_font_size`/
`apply_icon_size`) so a caller whose element's size scales with its own container (a
Bento Box card, not a fixed-role text element) can compute a size proportional to that
container instead of borrowing a role meant for something much smaller -- see
`layout_patterns.py`'s own card-proportional formula.
"""
from __future__ import annotations

import palette
import style
from sdk import UiSdk

TYPE_SCALE: dict[str, int] = {
    "caption": 16,
    "label": 18,
    "body": 22,
    "heading": 28,
    "title": 34,
}

ICON_SCALE: dict[str, int] = {
    "caption": 20,
    "label": 24,
    "body": 32,
    "heading": 40,
    "title": 48,
}


def apply_font_size(
    css_text: str, element_id: str, sdk: UiSdk, tag_name: str, size_px: int,
    *, primary_query: str | None = None,
) -> str:
    """Apply an EXPLICIT font-size (in px) to `tag_name`'s text-bearing element.
    Low-level primitive behind `apply_type_scale` (a named TYPE_SCALE role) --
    exists separately for callers that need a value outside the fixed named
    scale, e.g. `layout_patterns.py`'s Bento Box cards, whose type needs to
    scale with the CARD's own footprint, not a role meant for ordinary,
    normally-sized UI text. Reuses the SAME class_name palette.PALETTE_MAPPING
    already has for that tag's text_color -- confirmed identical for every
    checked type: font-size and color share one selector, the label/text
    element itself -- paired with the real 'font-size' source property (see
    module docstring)."""
    mapping = palette.PALETTE_MAPPING.get(tag_name)
    if mapping is None or "text_color" not in mapping:
        raise KeyError(f"No text-bearing selector known for {tag_name!r} -- see palette.PALETTE_MAPPING")
    class_name, _ = mapping["text_color"]
    return style.set_component_style(
        css_text, element_id, sdk, tag_name, [(class_name, "font-size", f"{size_px}px")],
        primary_query=primary_query)


def apply_icon_size(
    css_text: str, element_id: str, sdk: UiSdk, tag_name: str, size_px: int,
    *, primary_query: str | None = None,
) -> str:
    """Apply an EXPLICIT icon size (in px) to `tag_name`'s icon element -- a
    DISTINCT property from the label's own font-size (see module docstring).
    Low-level primitive behind `apply_icon_scale`, see `apply_font_size`'s
    docstring for why a caller would want an explicit value instead of a named
    ICON_SCALE role. Reuses the SAME class_name palette.PALETTE_MAPPING already
    has for that tag's icon_color, paired with the real 'font-size' source
    property."""
    mapping = palette.PALETTE_MAPPING.get(tag_name)
    if mapping is None or "icon_color" not in mapping:
        raise KeyError(f"No icon-bearing selector known for {tag_name!r} -- see palette.PALETTE_MAPPING")
    class_name, _ = mapping["icon_color"]
    return style.set_component_style(
        css_text, element_id, sdk, tag_name, [(class_name, "font-size", f"{size_px}px")],
        primary_query=primary_query)


def apply_type_scale(
    css_text: str, element_id: str, sdk: UiSdk, tag_name: str, role: str,
    *, primary_query: str | None = None,
) -> str:
    """Apply TYPE_SCALE[role]'s font-size to `tag_name`'s text-bearing element --
    a named-role wrapper around `apply_font_size` for ordinary, normally-sized
    UI text (see that function's docstring for when a caller needs an explicit
    value instead)."""
    if role not in TYPE_SCALE:
        raise KeyError(f"{role!r} is not a design-system type-scale role -- see TYPE_SCALE")
    return apply_font_size(css_text, element_id, sdk, tag_name, TYPE_SCALE[role], primary_query=primary_query)


def apply_icon_scale(
    css_text: str, element_id: str, sdk: UiSdk, tag_name: str, role: str,
    *, primary_query: str | None = None,
) -> str:
    """Apply ICON_SCALE[role]'s size to `tag_name`'s icon element -- a named-role
    wrapper around `apply_icon_size` for ordinary, normally-sized UI icons (see
    that function's docstring for when a caller needs an explicit value
    instead)."""
    if role not in ICON_SCALE:
        raise KeyError(f"{role!r} is not a design-system type-scale role -- see ICON_SCALE")
    return apply_icon_size(css_text, element_id, sdk, tag_name, ICON_SCALE[role], primary_query=primary_query)
