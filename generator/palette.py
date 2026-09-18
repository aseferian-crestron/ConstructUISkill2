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

import color_words
import style
from sdk import UiSdk

# Logical palette key -> (class_name, source_property) in ch5-button's own Stage-1
# catalog (verified against the real schema by this module's own test).
#
# EXTENDED 2026-09-13 (user: "you are not styling the 3 states of a button.
# normal, pressed and selected. this needs to be covered when you style
# components"): the real schema carries a FULL parallel set of pressed_/
# selected_ properties (confirmed via style.style_property_catalog --
# `[pressed="true"] .ch5-button--default,.ch5-button--default.ch5-button--
# pressed` etc., its own background/border/label/icon set, sectorPrefix
# "pressedAppearance_"/"pressedLabel_"/"pressedIcon_" and the "selected"
# equivalents) -- not guessed, the same schema-survey discipline as every
# other entry here. See derive_states() for filling these in automatically
# from a normal-state-only palette using standard UI convention (pressed =
# darker, selected = lighter/highlighted) when the caller hasn't set them
# explicitly.
_BUTTON_PALETTE: dict[str, tuple[str, str]] = {
    "background_color": (".ch5-button--default", "background-color"),
    "border_color": (".ch5-button--default", "border-color"),
    "border_width": (".ch5-button--default", "border-width"),
    "border_style": (".ch5-button--default", "border-style"),
    "text_color": (".ch5-button--default .ch5-button--label", "color"),
    "icon_color": (".ch5-button--default .ch5-button--icon", "color"),
    "pressed_background_color": (
        '[pressed="true"] .ch5-button--default,.ch5-button--default.ch5-button--pressed', "background-color"),
    "pressed_border_color": (
        '[pressed="true"] .ch5-button--default,.ch5-button--default.ch5-button--pressed', "border-color"),
    "pressed_border_width": (
        '[pressed="true"] .ch5-button--default,.ch5-button--default.ch5-button--pressed', "border-width"),
    "pressed_border_style": (
        '[pressed="true"] .ch5-button--default,.ch5-button--default.ch5-button--pressed', "border-style"),
    "pressed_text_color": (
        '[pressed="true"] .ch5-button--default.ch5-button--pressed .ch5-button--label,'
        '.ch5-button--default.ch5-button--pressed .ch5-button--label', "color"),
    "pressed_icon_color": (
        '[pressed="true"] .ch5-button--default.ch5-button--pressed .ch5-button--icon,'
        '.ch5-button--default.ch5-button--pressed .ch5-button--icon', "color"),
    "selected_background_color": (
        '[selected="true"] .ch5-button--default,.ch5-button--default.ch5-button--selected', "background-color"),
    "selected_border_color": (
        '[selected="true"] .ch5-button--default,.ch5-button--default.ch5-button--selected', "border-color"),
    "selected_border_width": (
        '[selected="true"] .ch5-button--default,.ch5-button--default.ch5-button--selected', "border-width"),
    "selected_border_style": (
        '[selected="true"] .ch5-button--default,.ch5-button--default.ch5-button--selected', "border-style"),
    "selected_text_color": (
        '[selected="true"] .ch5-button--default.ch5-button--selected .ch5-button--label,'
        '.ch5-button--default.ch5-button--selected .ch5-button--label', "color"),
    "selected_icon_color": (
        '[selected="true"] .ch5-button--default.ch5-button--selected .ch5-button--icon,'
        '.ch5-button--default.ch5-button--selected .ch5-button--icon', "color"),
}

# Button-family types: same shape as _BUTTON_PALETTE (now including pressed_/
# selected_ keys), own selector prefix, but targeting ch5-button's OWN
# --ch5-button--* vars (confirmed real, not a typo -- button-list/tab-button
# share that namespace for every state).
_BUTTON_LIST_PALETTE: dict[str, tuple[str, str]] = {
    "background_color": (".ch5-button-list--button-type-default", "background-color"),
    "border_color": (".ch5-button-list--button-type-default", "border-color"),
    "border_width": (".ch5-button-list--button-type-default", "border-width"),
    "border_style": (".ch5-button-list--button-type-default", "border-style"),
    "text_color": (".ch5-button-list--button-type-default .ch5-button--span .ch5-button--label", "color"),
    "icon_color": (".ch5-button-list--button-type-default .ch5-button--span .ch5-button--icon", "color"),
    "pressed_background_color": (".ch5-button-list--button-type-default.ch5-button--pressed", "background-color"),
    "pressed_border_color": (".ch5-button-list--button-type-default.ch5-button--pressed", "border-color"),
    "pressed_border_width": (".ch5-button-list--button-type-default.ch5-button--pressed", "border-width"),
    "pressed_border_style": (".ch5-button-list--button-type-default.ch5-button--pressed", "border-style"),
    "pressed_text_color": (
        ".ch5-button-list--button-type-default.ch5-button--pressed .ch5-button--span .ch5-button--label", "color"),
    "pressed_icon_color": (
        ".ch5-button-list--button-type-default.ch5-button--pressed .ch5-button--span .ch5-button--icon", "color"),
    "selected_background_color": (".ch5-button-list--button-type-default.ch5-button--selected", "background-color"),
    "selected_border_color": (".ch5-button-list--button-type-default.ch5-button--selected", "border-color"),
    "selected_border_width": (".ch5-button-list--button-type-default.ch5-button--selected", "border-width"),
    "selected_border_style": (".ch5-button-list--button-type-default.ch5-button--selected", "border-style"),
    "selected_text_color": (
        ".ch5-button-list--button-type-default.ch5-button--selected .ch5-button--span .ch5-button--label", "color"),
    "selected_icon_color": (
        ".ch5-button-list--button-type-default.ch5-button--selected .ch5-button--span .ch5-button--icon", "color"),
}

_TAB_BUTTON_PALETTE: dict[str, tuple[str, str]] = {
    "background_color": (".ch5-tab-button--button-type-default", "background-color"),
    "border_color": (".ch5-tab-button--button-type-default", "border-color"),
    "border_width": (".ch5-tab-button--button-type-default", "border-width"),
    "border_style": (".ch5-tab-button--button-type-default", "border-style"),
    "text_color": (".ch5-tab-button--button-type-default .ch5-button--span .ch5-button--label", "color"),
    "icon_color": (".ch5-tab-button--button-type-default .ch5-button--span .ch5-button--icon", "color"),
    "pressed_background_color": (".ch5-tab-button--button-type-default.ch5-button--pressed", "background-color"),
    "pressed_border_color": (".ch5-tab-button--button-type-default.ch5-button--pressed", "border-color"),
    "pressed_border_width": (".ch5-tab-button--button-type-default.ch5-button--pressed", "border-width"),
    "pressed_border_style": (".ch5-tab-button--button-type-default.ch5-button--pressed", "border-style"),
    "pressed_text_color": (
        ".ch5-tab-button--button-type-default.ch5-button--pressed .ch5-button--span .ch5-button--label", "color"),
    "pressed_icon_color": (
        ".ch5-tab-button--button-type-default.ch5-button--pressed .ch5-button--span .ch5-button--icon", "color"),
    "selected_background_color": (".ch5-tab-button--button-type-default.ch5-button--selected", "background-color"),
    "selected_border_color": (".ch5-tab-button--button-type-default.ch5-button--selected", "border-color"),
    "selected_border_width": (".ch5-tab-button--button-type-default.ch5-button--selected", "border-width"),
    "selected_border_style": (".ch5-tab-button--button-type-default.ch5-button--selected", "border-style"),
    "selected_text_color": (
        ".ch5-tab-button--button-type-default.ch5-button--selected .ch5-button--span .ch5-button--label", "color"),
    "selected_icon_color": (
        ".ch5-tab-button--button-type-default.ch5-button--selected .ch5-button--span .ch5-button--icon", "color"),
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
# The unfilled "target" track is real but not exposed under these generic
# keys -- a deliberate initial scope limit (see module docstring), not an
# oversight. handle_* keys ADDED 2026-09-18 (confirmed real via style.
# style_property_catalog -- `.noUi-handle` has its own background-color/
# border-color/border-width/border-style, no width/height/radius entry) after
# a live pixel-comparison against a reviewed PDF showed the handle needs its
# own distinct white-fill + accent-colored-ring treatment, not the connect
# portion's fill color.
_SLIDER_PALETTE: dict[str, tuple[str, str]] = {
    "background_color": (".ch5-slider .noUi-connect", "background-color"),
    "border_color": (".ch5-slider .noUi-connect", "border-color"),
    "border_width": (".ch5-slider .noUi-connect", "border-width"),
    "border_style": (".ch5-slider .noUi-connect", "border-style"),
    "text_color": (".ch5-slider.ch5-advanced-slider-container .ch5-title-container .ch5-label", "color"),
    "handle_background_color": (".ch5-slider .noUi-handle", "background-color"),
    "handle_border_color": (".ch5-slider .noUi-handle", "border-color"),
    "handle_border_width": (".ch5-slider .noUi-handle", "border-width"),
    "handle_border_style": (".ch5-slider .noUi-handle", "border-style"),
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


#: Standard UI convention (not Construct-specific -- ordinary web/native button
#: practice) for deriving pressed/selected looks from a normal-state color when the
#: caller hasn't set one explicitly: pressed recedes (darker, "pushed in"), selected
#: stands out (lighter, "highlighted"). See derive_states.
#:
#: PRESSED_LIGHTNESS_DELTA updated 2026-09-17 from -0.15 to -0.08 to match
#: docs/ConstructUISkill_Tabbed-Layout-Styleguide.md §6's measured rule ("pressed =
#: an 8% black... overlay on top of whatever the control's current background is"
#: -- this module's flat-color derive_states can't layer a real overlay, so it
#: applies the doc's own named fallback, "a discrete color swap using the same
#: 'darken 8%' value... as a fixed color rather than a computed overlay"). Global,
#: not Tabbed-scoped, since a pressed state receding 15% vs. 8% is the same generic
#: web/native convention this constant already claimed to follow -- the styleguide
#: is just a more precisely measured source for a number that was always a
#: judgment call. SELECTED_LIGHTNESS_DELTA is intentionally left unchanged: §6's
#: selected treatment is genuinely per-component (a filled button has no selected
#: state at all, a tile gets a fill+border+icon change, a tab gets a border only),
#: not a single reusable lighten fraction -- applied directly at each Tabbed call
#: site in layout_patterns.py/camera_control.py instead of centralized here.
PRESSED_LIGHTNESS_DELTA = -0.08
SELECTED_LIGHTNESS_DELTA = 0.12

#: normal-state key -> its pressed_/selected_ counterparts, and whether that
#: counterpart's value should be DERIVED from the normal key when missing (colors)
#: or simply COPIED unchanged (border width/style, text/icon color -- standard
#: practice leaves these the same across states; only the fill visibly shifts).
_DERIVED_COLOR_KEYS = ("background_color",)
_COPIED_KEYS = ("border_color", "border_width", "border_style", "text_color", "icon_color")


def derive_states(resolved_palette: dict[str, str]) -> dict[str, str]:
    """Expand a NORMAL-state-only palette (background_color/border_color/border_width/
    border_style/text_color/icon_color) into a full normal+pressed+selected palette,
    using standard UI convention -- pressed = background darkened (recedes, "pushed
    in"), selected = background lightened (stands out, "highlighted"); every other
    property (border, text, icon) carries over UNCHANGED to both states, matching
    ordinary button behavior where only the fill visibly shifts between states.

    ADDED 2026-09-13, user: "you are not styling the 3 states of a button. normal,
    pressed and selected. this needs to be covered when you style components and you
    should apply standard practices for web components when you need to show a
    normal, pressed and selected state." This is that standard-practice derivation --
    a judgment call (there's no Construct spec for "what pressed should look like"),
    clearly distinct from the schema-grounded facts elsewhere in this module.

    Never overwrites a `pressed_*`/`selected_*` key the caller ALREADY set explicitly
    -- this only fills in what's missing, so an explicit request for "black when
    pressed" is always honored over the derived default. Keys for states a given
    component type doesn't support are harmless -- applicable_subset filters them
    out per type before writing.
    """
    derived = dict(resolved_palette)
    for key in _DERIVED_COLOR_KEYS:
        value = resolved_palette.get(key)
        if value is None:
            continue
        pressed_key, selected_key = f"pressed_{key}", f"selected_{key}"
        if pressed_key not in derived:
            derived[pressed_key] = color_words.adjust_lightness(value, PRESSED_LIGHTNESS_DELTA)
        if selected_key not in derived:
            derived[selected_key] = color_words.adjust_lightness(value, SELECTED_LIGHTNESS_DELTA)
    for key in _COPIED_KEYS:
        value = resolved_palette.get(key)
        if value is None:
            continue
        pressed_key, selected_key = f"pressed_{key}", f"selected_{key}"
        if pressed_key not in derived:
            derived[pressed_key] = value
        if selected_key not in derived:
            derived[selected_key] = value
    return derived


#: Judgment calls, not a Construct spec (same precedent as PRESSED_LIGHTNESS_DELTA/
#: SELECTED_LIGHTNESS_DELTA above) -- design doc §2's "primary vs. secondary vs.
#: accent" rule names the roles but not their derivation. Secondary: a desaturated
#: variant of primary -- still obviously brand-related but visually recedes, matching
#: "everything else uses a secondary/neutral treatment." Accent: a modest 30-degree
#: hue shift (an "analogous" scheme) rather than a complementary/triadic rotation --
#: a safe default absent full color-harmony theory, since a large rotation risks an
#: unpredictable clash for an arbitrary brand color.
SECONDARY_SATURATION_DELTA = -0.45
ACCENT_HUE_ROTATION_DEGREES = 30


def resolve_color_roles(
    primary: str, secondary: str | None = None, accent: str | None = None,
) -> dict[str, str]:
    """Design-system §2's primary/secondary/accent roles. `secondary`/`accent` are
    derived from `primary` when not given explicitly -- an explicit value is never
    overridden, same "fill in what's missing" contract as derive_states."""
    return {
        "primary": primary,
        "secondary": secondary or color_words.adjust_saturation(primary, SECONDARY_SATURATION_DELTA),
        "accent": accent or color_words.rotate_hue(primary, ACCENT_HUE_ROTATION_DEGREES),
    }


#: Fixed, well-known status-color convention (not Construct-specific, not derived from
#: any brand palette) -- reserved exclusively for status feedback (a receive-signal
#: indicator, a connection-lost state) so they're never ambiguous with a branded accent
#: color (design doc §2).
SEMANTIC_COLORS: dict[str, str] = {
    "success": "#2e7d32",
    "warning": "#f9a825",
    "error": "#c62828",
    "info": "#1565c0",
}

#: 2-3 grays for backgrounds/borders/disabled states (design doc §2) -- so "gray" is a
#: defined set of values, not whatever hex a page happened to get.
NEUTRAL_SCALE: dict[str, str] = {
    "neutral_light": "#f5f5f5",
    "neutral_mid": "#bdbdbd",
    "neutral_dark": "#424242",
}


#: WCAG AA normal-text minimum -- design-system §2's contrast rule. (Large-text's 3:1
#: floor is not checked here yet: this project has no notion of "large text" separate
#: from §3's type scale, which is a later phase -- see the design-system plan.)
MIN_CONTRAST_RATIO = 4.5


def check_contrast(resolved_palette: dict[str, str]) -> tuple[bool | None, float | None]:
    """Whether `resolved_palette`'s text_color meets MIN_CONTRAST_RATIO against its own
    background_color (design-system §2's contrast rule). Returns (None, None) if either
    key is missing -- there is nothing to check, not a failure."""
    background = resolved_palette.get("background_color")
    text = resolved_palette.get("text_color")
    if background is None or text is None:
        return None, None
    ratio = color_words.contrast_ratio(background, text)
    return ratio >= MIN_CONTRAST_RATIO, ratio


def apply_palette(
    css_text: str, element_id: str, sdk: UiSdk, tag_name: str, palette: dict[str, str],
    *, primary_query: str | None = None,
) -> str:
    """Apply a subset of `tag_name`'s palette keys (colors/border values) to
    `element_id`, resolved through the curated mapping and then Stage 1's real
    schema catalog (`style.set_component_style`). Raises `KeyError` up front --
    before writing anything -- if `tag_name` has no mapping yet, or if `palette`
    names a key this type's mapping doesn't cover; never silently drops a key the
    caller asked to set.

    `primary_query`: forwarded to style.set_component_style -- the project's
    primary resolution's own media query, so its block gets the value written
    too, matching Construct's real behavior (see that function's docstring).
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
    return style.set_component_style(css_text, element_id, sdk, tag_name, style_values, primary_query=primary_query)
