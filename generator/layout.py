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

import re


def orientation_media_query(orientation: str, width: int, height: int) -> str:
    """Device-specific breakpoint for a WxH resolution in the given orientation.
    Confirmed against C:\\Git\\CCIDE's breakpoint.ts::createRawQuery (the real
    client-side source that generates these) and cross-checked against two real
    portrait sample files (Bug_CCIDE_5225_Widget2.cuiw / Widget5.cuiw, both
    1024x1322): landscape leads with max-width, portrait leads with max-height --
    same +-1px pattern either way, just which dimension is named first/alone differs.
    See docs/architecture/10-reflow.md for the full derivation."""
    if orientation == "landscape":
        return (
            f"(orientation: landscape) and (max-width: {width + 1}px) and (max-height: {height + 1}px), "
            f"(orientation: landscape) and (max-width: {width - 1}px)"
        )
    elif orientation == "portrait":
        return (
            f"(orientation: portrait) and (max-height: {height + 1}px) and (max-width: {width + 1}px), "
            f"(orientation: portrait) and (max-height: {height - 1}px)"
        )
    else:
        raise ValueError(f"unsupported orientation {orientation!r} -- expected 'landscape' or 'portrait'")


def landscape_media_query(width: int, height: int) -> str:
    """Confirmed formula (see module docstring) -- device-specific landscape breakpoint
    for a WxH primary landscape resolution. Kept as a thin wrapper so existing callers
    (page.py, this module's own build_position_css) are unaffected."""
    return orientation_media_query("landscape", width, height)


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


# `\s*` before the brace, never anything else: Construct writes both compact
# (`#it8l{...}`) and spaced (`#it8l { ... }`) CSS, but a descendant selector such as
# `#id .ch5-button :not(i){...}` has SELECTOR text between the id and the brace and must
# still not match -- it carries no element position (see parse_position_rules).
_FLAT_RULE_RE = re.compile(r"#(?P<id>[A-Za-z0-9_]+)\s*\{(?P<decls>[^{}]*)\}")


def find_media_block_span(css_text: str, query: str, start: int = 0) -> tuple[int, int] | None:
    """(start, end) char indices of the whole `@media {query}{...}` block, brace-depth
    matched since the inner rules themselves contain braces (a plain regex can't find
    the correct closing brace). Searches from `start` onward (default: the beginning).
    None if no block with this exact query exists from `start` onward.

    ADDED the `start` parameter 2026-09-09 (final whole-branch review): confirmed
    against a real 3-button page that the generator emits ONE @media block PER
    ELEMENT even when several elements share the identical query string, not one
    block containing every element's rule -- so a query can legitimately match more
    than once. `start` lets a caller walk forward past a match to find the next one
    (see find_media_block_spans, and the Data model section of the spec)."""
    # The brace may be separated from the query by whitespace (`@media (...) {`), so
    # locate the query text and then skip forward to its opening brace rather than
    # matching one literal spelling.
    needle = f"@media {query}"
    idx = start
    while True:
        idx = css_text.find(needle, idx)
        if idx == -1:
            return None
        after = idx + len(needle)
        rest = css_text[after:]
        stripped = rest.lstrip()
        if stripped.startswith("{"):
            open_brace = after + (len(rest) - len(stripped))
            break
        idx = after  # a longer query that merely starts with this one; keep looking
    depth = 0
    for i in range(open_brace, len(css_text)):
        if css_text[i] == "{":
            depth += 1
        elif css_text[i] == "}":
            depth -= 1
            if depth == 0:
                return idx, i + 1
    raise ValueError(f"unterminated @media block for query {query!r}")


def find_media_block_spans(css_text: str, query: str) -> list[tuple[int, int]]:
    """ADDED 2026-09-09 (final whole-branch review). ALL (start, end) spans of `@media
    {query}{...}` blocks matching this exact query string, in document order -- see
    find_media_block_span's note above for why a query can match more than once.
    Callers that need every element for a query (almost every reflow caller) must use
    this, not find_media_block_span, which only finds the first."""
    spans: list[tuple[int, int]] = []
    pos = 0
    while True:
        span = find_media_block_span(css_text, query, start=pos)
        if span is None:
            break
        spans.append(span)
        pos = span[1]
    return spans


def find_media_block(css_text: str, query: str) -> str | None:
    """Inner content of the FIRST `@media {query}{...}` block (between its outer
    braces). Only the first -- see find_media_block_span's note; callers needing every
    element for a query must use parse_all_position_rules instead."""
    span = find_media_block_span(css_text, query)
    if span is None:
        return None
    start, end = span
    open_brace = css_text.index("{", start)
    return css_text[open_brace + 1:end - 1]


def parse_position_rules(block_css: str) -> dict[str, dict]:
    """Parse one block's flat `#id{...}` rules into position/size dicts. The regex
    requires `{` immediately after the id -- a nested/child selector like
    `#id .ch5-button :not(i):not(svg) {...}` has a space before its `{`, so it never
    matches here and is correctly left alone (it carries no position data).

    Only `left`/`top` are required. `width`/`height`/`z_index` come back as `None` when
    absent -- CORRECTED 2026-09-10: confirmed against a real page authored directly in
    Construct (not by this generator) that a device-specific block only restates
    `width`/`height`/`z-index` when they differ from the catch-all block's value for that
    element; most of that page's elements had never been resized away from their
    catch-all size, so their device block was just `left:Npx;top:Npx;position:absolute;`.
    Requiring `width` here (the original version) silently dropped those elements
    entirely rather than treating them as "unchanged size" -- reflow.py::reflow_file is
    responsible for filling in `None` width/height/z_index from the catch-all block's own
    value for that element id before doing any size-dependent math.
    """
    elements: dict[str, dict] = {}
    for m in _FLAT_RULE_RE.finditer(block_css):
        decls: dict[str, str] = {}
        for decl in m.group("decls").split(";"):
            decl = decl.strip()
            if not decl or ":" not in decl:
                continue
            key, _, value = decl.partition(":")
            decls[key.strip()] = value.strip()
        if "left" not in decls or "top" not in decls:
            continue
        extra_vars = {k: v for k, v in decls.items() if k.startswith("--")}
        elements[m.group("id")] = {
            "left": int(decls["left"].rstrip("px")),
            "top": int(decls["top"].rstrip("px")),
            "width": int(decls["width"].rstrip("px")) if "width" in decls else None,
            "height": int(decls["height"].rstrip("px")) if "height" in decls else None,
            "z_index": int(decls["z-index"]) if "z-index" in decls else None,
            "extra_vars": extra_vars,
        }
    return elements


def parse_all_position_rules(css_text: str, query: str) -> dict[str, dict]:
    """ADDED 2026-09-09 (final whole-branch review). Parse EVERY element's flat
    `#id{...}` rule for `query`, merging across however many separate @media blocks
    the real generator split them into (see find_media_block_spans). Later blocks win
    on a duplicate id, matching normal CSS cascade order -- in practice no id should
    ever appear in more than one block for the same query."""
    elements: dict[str, dict] = {}
    for start, end in find_media_block_spans(css_text, query):
        open_brace = css_text.index("{", start)
        block = css_text[open_brace + 1:end - 1]
        elements.update(parse_position_rules(block))
    return elements


def build_reflow_block(elements: dict[str, dict], orientation: str, width: int, height: int) -> str:
    """One @media block, one flat #id{} rule per element -- same device-specific shape
    build_position_css already produces (no z-index), generalized to N elements."""
    query = orientation_media_query(orientation, width, height)
    rules = []
    for element_id, e in elements.items():
        extra_decls = "".join(f" {name}: {value};" for name, value in e.get("extra_vars", {}).items())
        rules.append(
            f"#{element_id}{{display: block; left: {e['left']}px; top: {e['top']}px; "
            f"position: absolute; width: {e['width']}px; height: {e['height']}px;{extra_decls}}}"
        )
    return f"@media {query}{{{''.join(rules)}}}"
