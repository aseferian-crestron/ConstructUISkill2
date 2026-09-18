"""
Design-system elevation/shape (ConstructUISkill_DesignSystem.md §6).

Border-radius: confirmed 2026-09-15 via style.style_property_catalog that all 4
corners are stylable for ch5-button, ch5-button-list, ch5-datetime, ch5-text --
but only ch5-button also has its shape="custom" gate confirmed end-to-end
(custom_shape_test.py: "custom" is not in the real schema's shape enum, so it must
be force-written via style.set_html_attribute before the corner CSS vars take
visible effect). apply_radius_preset is scoped to ch5-button only for that reason --
button-list/datetime/text are confirmed corner-stylable but NOT yet confirmed to use
the same shape-gate mechanism (or need one at all); extending to them needs that
checked first, not assumed identical (Phase 3's disabled-state lesson).

Elevation: confirmed 2026-09-15 that ZERO shadow/elevation-scoped style properties
exist in any mapped type's schema -- the design doc's own anticipated fallback
applies: "a border/background-contrast substitute where CH5 doesn't support real
shadows." border_width is already one of palette.py's existing per-tag keys, so
ELEVATION_LEVELS needs no new writer at all -- a caller passes one of these values
as palette.apply_palette's border_width, reusing that already-proven mechanism.
"""
from __future__ import annotations

import style
from sdk import UiSdk

#: sharp/subtle/rounded, in px -- design doc §6's own "2-3 options total" rule, a
#: judgment call like every other named-preset scale in this project (not a
#: Construct spec).
RADIUS_PRESETS: dict[str, int] = {
    "sharp": 0,
    "subtle": 4,
    "rounded": 12,
}

#: Confirmed corner-stylable but NOT yet confirmed to share ch5-button's shape="custom"
#: gate mechanism -- see module docstring. Not wired into apply_radius_preset yet.
CORNER_STYLABLE_UNCONFIRMED_GATE = ("ch5-button-list", "ch5-datetime", "ch5-text")

#: Real corner-radius selectors for the one confirmed-end-to-end tag --
#: normal/pressed/selected are THREE DISTINCT selectors with their own
#: separate target properties (confirmed via style.style_property_catalog:
#: `--ch5-button--rounded-rectangle-border-radius-*` for normal,
#: `--ch5-button--pressed-rounded-rectangle-border-radius-*` for pressed,
#: `--ch5-button--selected-rounded-rectangle-border-radius-*` for selected --
#: NOT one shared property). ADDED 2026-09-18 after a live report that
#: pressed/selected didn't keep the same radius as normal -- apply_radius_px
#: previously wrote only the normal selector, leaving pressed/selected to
#: whatever CH5's own un-set default is (visibly inconsistent with normal).
_BUTTON_RADIUS_CLASSES = (
    ".ch5-button--rounded-rectangle",
    ".ch5-button--rounded-rectangle.ch5-button--pressed",
    ".ch5-button--rounded-rectangle.ch5-button--selected",
)
_CORNERS = ("border-top-left-radius", "border-top-right-radius",
            "border-bottom-left-radius", "border-bottom-right-radius")

#: border/background-contrast substitute for real shadows (design doc §6) -- flat/
#: raised/raised_more border-width steps, applied via palette.apply_palette's
#: existing border_width key. A judgment call, not a Construct spec.
ELEVATION_LEVELS: dict[str, str] = {
    "flat": "0px",
    "raised": "2px",
    "raised_more": "4px",
}


def apply_radius_px(
    html_text: str, css_text: str, element_id: str, sdk: UiSdk, tag_name: str, radius_px: int | float,
) -> tuple[str, str]:
    """`(html_text, css_text)` with `element_id` flipped to `shape="custom"` and all
    4 corners set to an EXPLICIT `radius_px` value -- on the NORMAL, PRESSED, and
    SELECTED selectors alike (see _BUTTON_RADIUS_CLASSES), so a button's shape
    stays visually consistent across all 3 interaction states instead of only the
    normal one. Low-level primitive behind `apply_radius_preset` (a named
    RADIUS_PRESETS role) -- exists separately for callers that need a value
    outside the 3-preset scale, e.g.
    docs/ConstructUISkill_Tabbed-Layout-Styleguide.md §5's real measured radii
    (10px btn-group, 14px tile/PTZ, 999px pill), none of which is one of the
    generic sharp/subtle/rounded presets. Scoped to ch5-button only -- see module
    docstring. Raises KeyError up front for an unsupported tag, before writing
    anything."""
    if tag_name != "ch5-button":
        raise KeyError(
            f"apply_radius_px only supports ch5-button so far -- {tag_name!r}'s "
            f"shape=\"custom\" gate is not yet confirmed, see CORNER_STYLABLE_UNCONFIRMED_GATE")
    value = f"{radius_px}px"
    new_html = style.set_html_attribute(html_text, element_id, "shape", "custom")
    new_css = style.set_component_style(
        css_text, element_id, sdk, tag_name,
        [(class_name, corner, value) for class_name in _BUTTON_RADIUS_CLASSES for corner in _CORNERS],
    )
    return new_html, new_css


def apply_radius_preset(
    html_text: str, css_text: str, element_id: str, sdk: UiSdk, tag_name: str, preset: str,
) -> tuple[str, str]:
    """`(html_text, css_text)` with `element_id` flipped to `shape="custom"` and all
    4 corners set to RADIUS_PRESETS[preset]. Named-role wrapper around
    `apply_radius_px` (see that function's docstring for when a caller needs an
    explicit value instead). Raises KeyError up front for an unknown preset,
    before writing anything."""
    if preset not in RADIUS_PRESETS:
        raise KeyError(f"{preset!r} is not a design-system radius preset -- see RADIUS_PRESETS")
    return apply_radius_px(html_text, css_text, element_id, sdk, tag_name, RADIUS_PRESETS[preset])
