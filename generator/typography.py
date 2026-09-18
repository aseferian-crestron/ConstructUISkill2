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

#: ch5-button's label/icon font-size, font-weight, and margin properties each
#: have THREE separate selectors/target-properties -- normal, pressed, and
#: selected (confirmed via style.style_property_catalog) -- not one shared
#: property. ADDED 2026-09-18 after a live report that icon SIZE and the
#: icon/label GAP looked wrong specifically in the pressed/selected states:
#: every call below was writing only the normal selector, so pressed/
#: selected fell back to CH5's own un-set default (visibly inconsistent),
#: exactly the same class of gap already found and fixed for border-radius
#: (shape.py::apply_radius_px). Scoped to ch5-button only, same discipline
#: as shape.py -- other types' pressed/selected label/icon selectors are not
#: yet confirmed to exist or share this shape.
_BUTTON_LABEL_SELECTORS = (
    ".ch5-button--default .ch5-button--label",
    '[pressed="true"] .ch5-button--default.ch5-button--pressed .ch5-button--label,'
    '.ch5-button--default.ch5-button--pressed .ch5-button--label',
    '[selected="true"] .ch5-button--default.ch5-button--selected .ch5-button--label,'
    '.ch5-button--default.ch5-button--selected .ch5-button--label',
)
_BUTTON_ICON_SELECTORS = (
    ".ch5-button--default .ch5-button--icon",
    '[pressed="true"] .ch5-button--default.ch5-button--pressed .ch5-button--icon,'
    '.ch5-button--default.ch5-button--pressed .ch5-button--icon',
    '[selected="true"] .ch5-button--default.ch5-button--selected .ch5-button--icon,'
    '.ch5-button--default.ch5-button--selected .ch5-button--icon',
)


def _write_all_button_states(
    css_text: str, element_id: str, sdk: UiSdk, tag_name: str, fallback_class_name: str,
    selectors: tuple[str, ...], prop: str, value: str, *, primary_query: str | None = None,
) -> str:
    """Write `prop: value` to `fallback_class_name` for any type, OR -- when
    `tag_name` is ch5-button, whose pressed/selected variants are confirmed
    real -- to all of `selectors` (normal + pressed + selected) so the value
    stays consistent across every interaction state."""
    targets = selectors if tag_name == "ch5-button" else (fallback_class_name,)
    return style.set_component_style(
        css_text, element_id, sdk, tag_name, [(t, prop, value) for t in targets],
        primary_query=primary_query)


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
    return _write_all_button_states(
        css_text, element_id, sdk, tag_name, class_name, _BUTTON_LABEL_SELECTORS,
        "font-size", f"{size_px}px", primary_query=primary_query)


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
    return _write_all_button_states(
        css_text, element_id, sdk, tag_name, class_name, _BUTTON_ICON_SELECTORS,
        "font-size", f"{size_px}px", primary_query=primary_query)


def apply_icon_gap(
    css_text: str, element_id: str, sdk: UiSdk, tag_name: str, gap_px: int,
    *, primary_query: str | None = None,
) -> str:
    """Apply the gap between an icon and its label (icon-LEFT-of-label
    layout) via the icon's own `margin-right` -- a real, confirmed property,
    with its own separate pressed/selected variants for ch5-button (see
    module comment above _BUTTON_LABEL_SELECTORS). Replaces layout_
    patterns.py's earlier ad hoc `_apply_icon_label_gap`, which only wrote
    the normal-state margin."""
    mapping = palette.PALETTE_MAPPING.get(tag_name)
    if mapping is None or "icon_color" not in mapping:
        raise KeyError(f"No icon-bearing selector known for {tag_name!r} -- see palette.PALETTE_MAPPING")
    class_name, _ = mapping["icon_color"]
    return _write_all_button_states(
        css_text, element_id, sdk, tag_name, class_name, _BUTTON_ICON_SELECTORS,
        "margin-right", f"{gap_px}px", primary_query=primary_query)


def apply_icon_offset(
    css_text: str, element_id: str, sdk: UiSdk, tag_name: str, offset_px: int,
    *, primary_query: str | None = None,
) -> str:
    """Write the icon's `margin-left` -- this IS the real property behind
    Construct's own "Icon Styles > Horizontal Offset" panel field (confirmed
    live, 2026-09-18, from a screenshot of that exact panel).

    **NOT an independent icon-only position knob -- tested live and
    falsified, 2026-09-18.** The icon and label are one flowing inline unit
    under `halignlabel`, not two independently-positioned elements: a large
    negative offset here (tried in `design_ideas_subsystem.py`, since
    reverted) dragged the LABEL along with the icon, flush against the
    button's left edge -- not "icon moves, label stays centered" as the
    property panel's own section grouping (separate "Label Styles" /"Icon
    Styles" blocks) suggested it might. A SMALL value may still be usable
    for a minor visual nudge without noticeably displacing the label, but
    that hasn't been confirmed either -- `design_ideas_subsystem.py`'s own
    control-icon layout uses `apply_icon_gap` instead (icon-to-label
    spacing, leaving `halignlabel` at its default so the pair centers
    together), not this function. Do not reach for this expecting the label
    to stay put -- verify live before trusting any specific offset here."""
    mapping = palette.PALETTE_MAPPING.get(tag_name)
    if mapping is None or "icon_color" not in mapping:
        raise KeyError(f"No icon-bearing selector known for {tag_name!r} -- see palette.PALETTE_MAPPING")
    class_name, _ = mapping["icon_color"]
    return _write_all_button_states(
        css_text, element_id, sdk, tag_name, class_name, _BUTTON_ICON_SELECTORS,
        "margin-left", f"{offset_px}px", primary_query=primary_query)


def apply_font_weight(
    css_text: str, element_id: str, sdk: UiSdk, tag_name: str, weight: int | str,
    *, primary_query: str | None = None,
) -> str:
    """Apply an EXPLICIT font-weight to `tag_name`'s text-bearing element.
    `font-weight` is a real, confirmed-stylable property for both ch5-text
    and ch5-button (style.style_property_catalog), sharing the SAME selector
    `apply_font_size` already uses for that type's text_color/font-size --
    added 2026-09-18 after a live design-fidelity report (headline/labels
    rendering at default weight when the reviewed design calls for bold)."""
    mapping = palette.PALETTE_MAPPING.get(tag_name)
    if mapping is None or "text_color" not in mapping:
        raise KeyError(f"No text-bearing selector known for {tag_name!r} -- see palette.PALETTE_MAPPING")
    class_name, _ = mapping["text_color"]
    return _write_all_button_states(
        css_text, element_id, sdk, tag_name, class_name, _BUTTON_LABEL_SELECTORS,
        "font-weight", str(weight),
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
