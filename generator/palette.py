"""
Palette layer (Stage 2) sitting on top of generator/style.py's raw per-property
catalog: a small, curated set of logical "theme" keys (background_color,
border_color, text_color, ...) mapped per component type onto the REAL catalog
entries Stage 1 already discovered from the schema -- no new data invented, just
naming already-real properties (this differs from the earlier request for a
hand-styled reference project, which the user correctly rejected: that would have
been trying to LEARN what properties exist; this is organizing properties Stage 1
already fully discovered).

Deliberately NOT a generic auto-derivation across tags: checked ch5-button,
ch5-toggle, ch5-slider, ch5-textinput side by side (2026-09-11) and their real
`classToVariableMapping` shapes are not uniform enough to name generically --
ch5-toggle has no `background-color` concept at all (it's an on/off switch styled
by label/icon color only, with `.ch5-toggle__on-label`/`__off-label`/`__on-icon`/
`__off-icon` selectors, no fill); ch5-slider has THREE separate background-color-
bearing selectors (`.noUi-target`/`.noUi-connect`/`.noUi-handle` -- track/filled
portion/draggable handle) with no single "the" background without knowing what
each part visually is. Built incrementally, one verified type at a time, same
precedent as component.py::PROFILES.

EXTENDED 2026-09-13 (user: "what other components dont have palette mapping?
that should be addressed now") to every OTHER real component type this project's
own test pages contain that has ANY targetProperty-backed style property at all
(surveyed directly via style.style_property_catalog for each, not guessed) --
`ch5-button-list`/`ch5-tab-button` (button-family types, share ch5-button's own
`--ch5-button--*` var namespace for their default/unpressed/unselected state),
`ch5-toggle` (label/on-icon only, no fill -- see above), `ch5-signal-level-gauge`/
`ch5-wifi-signal-level-gauge` (mapped to their own "selected"/active-segment
color, the most visually prominent state), `ch5-slider` (background/border/text
mapped to the FILLED "connect" portion -- the part most associated with "the
slider's color"; the track and handle are real but distinct parts, not exposed
under these generic keys, a deliberate initial scope limit, not an oversight),
`ch5-dpad`/`ch5-keypad` (their own default/unpressed button-like state),
`ch5-animation` (its one `color` property, mapped to icon_color -- closer to a
tinted glyph than to text), `ch5-subpage-reference-list` (Widget List,
background only), `ch5-video-switcher`, `ch5-color-chip`, `ch5-datetime`,
`ch5-qrcode` (border only -- no fill/text properties exist for it),
`ch5-textinput`, `ch5-text`, `ch5-image` (border only -- an image has no
separate background fill from the image itself).

NOT extended -- and never will be via this mechanism, not a gap to fill later --
`ch5-button-list-individual-button`, `ch5-tab-button-individual-button`,
`ch5-segmented-gauge`, `ch5-dpad-button`, `ch5-keypad-button`, `ch5-video`,
`ch5-video-switcher-screen`, `ch5-video-switcher-source`, `ch5-media-player`,
`ch5-color-picker`, `ch5-template`: each has a genuinely EMPTY
`classToVariableMapping` (confirmed via style.style_property_catalog, zero
entries) -- there is no `--ch5-*` custom property this mechanism could ever
write for them, not an unmapped type still waiting on curation. See
NO_STYLABLE_PROPERTIES.
"""
from __future__ import annotations

import style
from sdk import UiSdk

# Logical palette key -> (class_name, source_property) in ch5-button's own Stage-1
# catalog (verified against the real schema by this module's own test). Scoped to
# the DEFAULT state only for v1 (not pressed/selected) -- matches "theme the base
# look"; pressed/selected-state palettes are a named follow-up.
_BUTTON_PALETTE: dict[str, tuple[str, str]] = {
    "background_color": (".ch5-button--default", "background-color"),
    "border_color": (".ch5-button--default", "border-color"),
    "border_width": (".ch5-button--default", "border-width"),
    "border_style": (".ch5-button--default", "border-style"),
    "text_color": (".ch5-button--default .ch5-button--label", "color"),
    "icon_color": (".ch5-button--default .ch5-button--icon", "color"),
}

# Button-family types: same shape as _BUTTON_PALETTE, own selector prefix, but
# targeting ch5-button's OWN --ch5-button--* vars (confirmed real, not a typo --
# button-list/tab-button share that namespace for their default/unpressed/
# unselected state).
_BUTTON_LIST_PALETTE: dict[str, tuple[str, str]] = {
    "background_color": (".ch5-button-list--button-type-default", "background-color"),
    "border_color": (".ch5-button-list--button-type-default", "border-color"),
    "border_width": (".ch5-button-list--button-type-default", "border-width"),
    "border_style": (".ch5-button-list--button-type-default", "border-style"),
    "text_color": (".ch5-button-list--button-type-default .ch5-button--span .ch5-button--label", "color"),
    "icon_color": (".ch5-button-list--button-type-default .ch5-button--span .ch5-button--icon", "color"),
}

_TAB_BUTTON_PALETTE: dict[str, tuple[str, str]] = {
    "background_color": (".ch5-tab-button--button-type-default", "background-color"),
    "border_color": (".ch5-tab-button--button-type-default", "border-color"),
    "border_width": (".ch5-tab-button--button-type-default", "border-width"),
    "border_style": (".ch5-tab-button--button-type-default", "border-style"),
    "text_color": (".ch5-tab-button--button-type-default .ch5-button--span .ch5-button--label", "color"),
    "icon_color": (".ch5-tab-button--button-type-default .ch5-button--span .ch5-button--icon", "color"),
}

# No background-color concept at all -- an on/off switch styled by label/icon
# color only. text_color -> the toggle's own descriptive label (not the
# separate on/off state labels); icon_color -> the "on" state icon.
_TOGGLE_PALETTE: dict[str, tuple[str, str]] = {
    "text_color": (".ch5-toggle .ch5-toggle__label", "color"),
    "icon_color": (".ch5-toggle .ch5-toggle__on-icon", "color"),
}

# Mapped to the active/"selected" segment color -- the most visually prominent
# state at a glance, matching what a user styling "the gauge" most likely means.
_SIGNAL_LEVEL_GAUGE_PALETTE: dict[str, tuple[str, str]] = {
    "background_color": (".ch5-signal-level-gauge .ch5-signal-level-gauge--selected-bar-color", "background-color"),
}

_WIFI_SIGNAL_LEVEL_GAUGE_PALETTE: dict[str, tuple[str, str]] = {
    "background_color": (
        ".ch5-wifi-signal-level-gauge--gauge-style-light .ch5-wifi-signal-level-gauge--selected-true", "color"),
}

# Three real, distinct parts (track/filled-portion/handle) -- mapped to the
# FILLED "connect" portion, the part most associated with "the slider's color".
# Track and handle are real but not exposed under these generic keys -- a
# deliberate initial scope limit (see module docstring), not an oversight.
_SLIDER_PALETTE: dict[str, tuple[str, str]] = {
    "background_color": (".ch5-slider .noUi-connect", "background-color"),
    "border_color": (".ch5-slider .noUi-connect", "border-color"),
    "border_width": (".ch5-slider .noUi-connect", "border-width"),
    "border_style": (".ch5-slider .noUi-connect", "border-style"),
    "text_color": (".ch5-slider.ch5-advanced-slider-container .ch5-title-container .ch5-label", "color"),
}

_DPAD_PALETTE: dict[str, tuple[str, str]] = {
    "background_color": (".ch5-dpad.ch5-dpad--type-default .ch5-dpad-child", "background-color"),
    "text_color": (".ch5-dpad.ch5-dpad--type-default .ch5-dpad-child", "color"),
}

_KEYPAD_PALETTE: dict[str, tuple[str, str]] = {
    "background_color": (".ch5-keypad.ch5-keypad--type-default .keypad-btn button", "background-color"),
    "text_color": (".ch5-keypad.ch5-keypad--type-default .keypad-btn button", "color"),
    "border_color": (".ch5-keypad.ch5-keypad--type-default .keypad-btn button", "border-color"),
    "border_width": (".ch5-keypad.ch5-keypad--type-default .keypad-btn button", "border-width"),
    "border_style": (".ch5-keypad.ch5-keypad--type-default .keypad-btn button", "border-style"),
}

# Its only real property -- mapped to icon_color, closer to a tinted glyph than
# to text for a decorative animation component.
_ANIMATION_PALETTE: dict[str, tuple[str, str]] = {
    "icon_color": (".ch5-animation", "color"),
}

_SUBPAGE_REFERENCE_LIST_PALETTE: dict[str, tuple[str, str]] = {  # "Widget List"
    "background_color": (".ch5-subpage-reference-list", "background-color"),
}

_VIDEO_SWITCHER_PALETTE: dict[str, tuple[str, str]] = {
    "background_color": (".ch5-video-switcher", "background-color"),
    "border_color": (".ch5-video-switcher", "border-color"),
    "border_width": (".ch5-video-switcher", "border-width"),
    "border_style": (".ch5-video-switcher", "border-style"),
    "text_color": (".ch5-video-switcher--source-list-label", "color"),
}

_COLOR_CHIP_PALETTE: dict[str, tuple[str, str]] = {
    "background_color": (".ch5-color-chip", "background-color"),
}

_DATETIME_PALETTE: dict[str, tuple[str, str]] = {
    "background_color": (".ch5-datetime", "background-color"),
    "border_color": (".ch5-datetime", "border-color"),
    "border_width": (".ch5-datetime", "border-width"),
    "border_style": (".ch5-datetime", "border-style"),
    "text_color": (".ch5-datetime", "color"),
}

# Border only -- no fill/text property exists for it in the real schema.
_QRCODE_PALETTE: dict[str, tuple[str, str]] = {
    "border_color": (".ch5-qrcode canvas", "border-color"),
    "border_width": (".ch5-qrcode canvas", "border-width"),
    "border_style": (".ch5-qrcode canvas", "border-style"),
}

_TEXT_PALETTE: dict[str, tuple[str, str]] = {
    "background_color": (".ch5-text", "background-color"),
    "border_color": (".ch5-text", "border-color"),
    "border_width": (".ch5-text", "border-width"),
    "border_style": (".ch5-text", "border-style"),
    "text_color": (".ch5-text", "color"),
}

_TEXTINPUT_PALETTE: dict[str, tuple[str, str]] = {
    "background_color": (".ch5-textinput .ch5-textinput-container", "background-color"),
    "border_color": (".ch5-textinput .ch5-textinput-container", "border-color"),
    "border_width": (".ch5-textinput .ch5-textinput-container", "border-width"),
    "border_style": (".ch5-textinput .ch5-textinput-container", "border-style"),
    "text_color": (".ch5-textinput .ch5-textinput--label", "color"),
    "icon_color": (".ch5-textinput .ch5-textinput-container .ch5-textinput--icon", "color"),
}

# Border only -- an image has no separate background fill from the image itself.
_IMAGE_PALETTE: dict[str, tuple[str, str]] = {
    "border_color": (".ch5-image", "border-color"),
    "border_width": (".ch5-image", "border-width"),
    "border_style": (".ch5-image", "border-style"),
}

PALETTE_MAPPING: dict[str, dict[str, tuple[str, str]]] = {
    "ch5-button": _BUTTON_PALETTE,
    "ch5-button-list": _BUTTON_LIST_PALETTE,
    "ch5-tab-button": _TAB_BUTTON_PALETTE,
    "ch5-toggle": _TOGGLE_PALETTE,
    "ch5-signal-level-gauge": _SIGNAL_LEVEL_GAUGE_PALETTE,
    "ch5-wifi-signal-level-gauge": _WIFI_SIGNAL_LEVEL_GAUGE_PALETTE,
    "ch5-slider": _SLIDER_PALETTE,
    "ch5-dpad": _DPAD_PALETTE,
    "ch5-keypad": _KEYPAD_PALETTE,
    "ch5-animation": _ANIMATION_PALETTE,
    "ch5-subpage-reference-list": _SUBPAGE_REFERENCE_LIST_PALETTE,
    "ch5-video-switcher": _VIDEO_SWITCHER_PALETTE,
    "ch5-color-chip": _COLOR_CHIP_PALETTE,
    "ch5-datetime": _DATETIME_PALETTE,
    "ch5-qrcode": _QRCODE_PALETTE,
    "ch5-text": _TEXT_PALETTE,
    "ch5-textinput": _TEXTINPUT_PALETTE,
    "ch5-image": _IMAGE_PALETTE,
}

#: Confirmed (style.style_property_catalog) to have an EMPTY classToVariableMapping
#: -- no --ch5-* custom property exists for them to write, ever, via this mechanism.
#: Not a coverage gap; see module docstring.
NO_STYLABLE_PROPERTIES: frozenset[str] = frozenset({
    "ch5-button-list-individual-button", "ch5-tab-button-individual-button",
    "ch5-segmented-gauge", "ch5-dpad-button", "ch5-keypad-button", "ch5-video",
    "ch5-video-switcher-screen", "ch5-video-switcher-source", "ch5-media-player",
    "ch5-color-picker", "ch5-template",
})


def supported_tags() -> list[str]:
    """Component types with a real, verified palette mapping so far -- see the
    module docstring for why this is curated per-type rather than generic."""
    return list(PALETTE_MAPPING)


def applicable_subset(tag_name: str, resolved_palette: dict[str, str]) -> dict[str, str]:
    """`resolved_palette` filtered down to only the keys `tag_name`'s own mapping
    actually supports -- e.g. `icon_color` is dropped for `ch5-text` (no icon).
    Used by theme_chat.py's "style every object on this page" mode, where one
    shared palette is applied across many DIFFERENT component types that don't
    all expose the same properties; filtering, not an error, since a key simply
    not applying to a given type is normal, not a mistake."""
    mapping = PALETTE_MAPPING.get(tag_name, {})
    return {k: v for k, v in resolved_palette.items() if k in mapping}


def apply_palette(css_text: str, element_id: str, sdk: UiSdk, tag_name: str, palette: dict[str, str]) -> str:
    """Apply a subset of `tag_name`'s palette keys (colors/border values) to
    `element_id`, resolved through the curated mapping and then Stage 1's real
    schema catalog (`style.set_component_style`). Raises `KeyError` up front --
    before writing anything -- if `tag_name` has no mapping yet, or if `palette`
    names a key this type's mapping doesn't cover; never silently drops a key the
    caller asked to set.
    """
    mapping = PALETTE_MAPPING.get(tag_name)
    if mapping is None:
        raise KeyError(f"No Stage-2 palette mapping yet for {tag_name!r} -- see palette.py::supported_tags()")
    unknown = set(palette) - set(mapping)
    if unknown:
        raise KeyError(
            f"{tag_name!r}'s palette mapping has no key(s) {sorted(unknown)} -- "
            f"supported: {sorted(mapping)}"
        )
    style_values = [(*mapping[key], value) for key, value in palette.items()]
    return style.set_component_style(css_text, element_id, sdk, tag_name, style_values)
