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
precedent as component.py::PROFILES -- ch5-button is the only mapping built so
far; extending to other types is follow-up work, not guessed at here.
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

PALETTE_MAPPING: dict[str, dict[str, tuple[str, str]]] = {
    "ch5-button": _BUTTON_PALETTE,
}


def supported_tags() -> list[str]:
    """Component types with a real, verified palette mapping so far -- see the
    module docstring for why this is curated per-type rather than generic."""
    return list(PALETTE_MAPPING)


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
