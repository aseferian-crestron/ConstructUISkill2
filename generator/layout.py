"""
Default position/size CSS for a newly-placed page element -- confirmed against real files
after a user-reported bug: a first cut of Phase 4 (add a CH5 component) wrote button
elements with NO {Css} rule at all, so Construct's Properties panel showed Left/Top/
Width/Height as "auto" for every button (size can never legitimately be "auto" -- even a
component using a fixed/explicit size still needs an explicit CSS rule).

Two @media blocks, confirmed identically shaped in both a real button page
(Component - Button.cuig) and a real widget containing a button (Widget.cuiw):

  1. `@media (max-width: 99999px){ ... }` -- the catch-all/undefined-viewport block.
  2. A device-specific landscape block. Formula confirmed by direct comparison of two real
     files against two different device widths/heights:
       - Widget.cuiw / Component - Button.cuig (project has a TSW-1070, 1280x800 landscape,
         defined): `(max-width: 1281px) and (max-height: 801px), (max-width: 1279px)`
       - generator/page.py's PRE-EXISTING widget fallback (2560x1440, for a project with NO
         devices defined yet -- CreateNewWidgetHandler.cs's own fallback, Phase 3): (max-width:
         2561px) and (max-height: 1441px), (max-width: 2559px)
     Both match `(max-width: {W+1}px) and (max-height: {H+1}px), (max-width: {W-1}px)` for
     the relevant width/height W x H -- confirmed as a real formula, not a guess, though only
     ever observed for a *landscape* primary resolution so far (portrait/other orientations
     unconfirmed -- Phase 5 territory).

Per-element CSS in the 99999 block: `display: block; left; top; position: absolute;
z-index; width; height` (+ any extra `--{cssVarPrefix}-regular-{width,height}` custom
properties the caller supplies, confirmed present on some but not all real button
instances -- likely only written once a component's size has been explicitly touched;
omitted here as a result, matching a truly *fresh* component). The device-specific block
repeats the same properties MINUS z-index (confirmed omitted there in both real files).

A component-type's extra "theme selector" rule (e.g. `#id .ch5-button :not(i):not(svg){
font-family: "..."}` for buttons) is schema-driven, not button-specific: SDK
`component-context.json`'s `<tag>.componentProperties.customThemeRequiredSelectors` (see
generator/sdk.py). Pass `theme_selectors` explicitly (built by the caller from that data)
rather than hardcoding a button-only string here.

NOT covered (flagged): the real reference files' CSS reflects components that were also
manually dragged/resized after creation (inconsistent `display`/`z-index` presence between
the two blocks, non-round left/top values) -- this module produces a clean, internally
consistent result for a component's *initial* placement, not a byte-identical reproduction
of a hand-edited sample.
"""
from __future__ import annotations


def landscape_media_query(width: int, height: int) -> str:
    """Confirmed formula (see module docstring) -- device-specific landscape breakpoint
    for a WxH primary landscape resolution."""
    return (
        f"(orientation: landscape) and (max-width: {width + 1}px) and (max-height: {height + 1}px), "
        f"(orientation: landscape) and (max-width: {width - 1}px)"
    )


def build_position_css(
    element_id: str,
    *,
    x: int,
    y: int,
    width: int,
    height: int,
    z_index: int,
    theme_selectors: list[str] | None = None,
    active_font: str = "Roboto",
    resolution: tuple[int, int] | None = None,
    extra_vars: dict[str, str] | None = None,
) -> str:
    """Two-@media-block position/size CSS for one newly-placed element. `resolution`, if
    given, is the project's primary landscape (width, height) in px -- omit (None) to fall
    back to the no-devices-yet 2560x1440 block (matches generator/page.py's pre-existing
    widget default, CreateNewWidgetHandler.cs).

    `extra_vars`: extra `--custom-property: value;` declarations appended to the #id{...}
    rule in BOTH blocks (confirmed present in both for real "custom size" button instances).
    For ch5-button specifically these are `--ch5-button--regular-width`/`-height`, driven
    by the SDK's own `component-context.json` classToVariableMapping "idSelector" entry --
    see ch5_button.py::button_size_css_vars. Found necessary after a user-reported bug: the
    outer #id{width;height} alone sizes the canvas selection adorner correctly, but
    ch5-button's own internal (web component) rendering reads its actual visual size from
    these CSS custom properties, not the plain width/height -- omitting them left the
    adorner and the actual rendered button visibly mismatched even with size="custom".
    """
    theme_selectors = theme_selectors or []
    extra_vars = extra_vars or {}
    extra_decls = "".join(f" {name}: {value};" for name, value in extra_vars.items())

    base_rule = f"display: block; left: {x}px; top: {y}px; position: absolute; z-index: {z_index}; width: {width}px; height: {height}px;{extra_decls}"
    device_rule = f"display: block; left: {x}px; top: {y}px; position: absolute; width: {width}px; height: {height}px;{extra_decls}"
    theme_rules = "".join(
        f"#{element_id} {selector} {{font-family: \"{active_font}\";}}" for selector in theme_selectors
    )

    w, h = resolution if resolution else (2560, 1440)

    catch_all = f"@media (max-width: 99999px){{#{element_id}{{{base_rule}}}{theme_rules}}}"
    device = (
        f"@media {landscape_media_query(w, h)}"
        f"{{#{element_id}{{{device_rule}}}}}"
    )
    return catch_all + device
