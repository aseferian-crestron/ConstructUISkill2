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


def apply_type_scale(
    css_text: str, element_id: str, sdk: UiSdk, tag_name: str, role: str,
    *, primary_query: str | None = None,
) -> str:
    """Apply TYPE_SCALE[role]'s font-size to `tag_name`'s text-bearing element.
    Reuses the SAME class_name palette.PALETTE_MAPPING already has for that tag's
    text_color -- confirmed identical for every checked type: font-size and color
    share one selector, the label/text element itself -- paired with the real
    'font-size' source property (see module docstring)."""
    if role not in TYPE_SCALE:
        raise KeyError(f"{role!r} is not a design-system type-scale role -- see TYPE_SCALE")
    mapping = palette.PALETTE_MAPPING.get(tag_name)
    if mapping is None or "text_color" not in mapping:
        raise KeyError(f"No text-bearing selector known for {tag_name!r} -- see palette.PALETTE_MAPPING")
    class_name, _ = mapping["text_color"]
    value = f"{TYPE_SCALE[role]}px"
    return style.set_component_style(
        css_text, element_id, sdk, tag_name, [(class_name, "font-size", value)],
        primary_query=primary_query)


def apply_icon_scale(
    css_text: str, element_id: str, sdk: UiSdk, tag_name: str, role: str,
    *, primary_query: str | None = None,
) -> str:
    """Apply ICON_SCALE[role]'s font-size to `tag_name`'s icon element -- a
    DISTINCT property from the label's own font-size (see module docstring).
    Reuses the SAME class_name palette.PALETTE_MAPPING already has for that
    tag's icon_color, paired with the real 'font-size' source property."""
    if role not in ICON_SCALE:
        raise KeyError(f"{role!r} is not a design-system type-scale role -- see ICON_SCALE")
    mapping = palette.PALETTE_MAPPING.get(tag_name)
    if mapping is None or "icon_color" not in mapping:
        raise KeyError(f"No icon-bearing selector known for {tag_name!r} -- see palette.PALETTE_MAPPING")
    class_name, _ = mapping["icon_color"]
    value = f"{ICON_SCALE[role]}px"
    return style.set_component_style(
        css_text, element_id, sdk, tag_name, [(class_name, "font-size", value)],
        primary_query=primary_query)
