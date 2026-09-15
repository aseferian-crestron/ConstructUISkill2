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
