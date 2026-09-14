"""
Chat-described theming (Stage 3, source #1). Deliberately split into two
concerns, corrected 2026-09-13 after the user pointed out the original design's
real limit: "most of the time, users arent goign to know they exact colors they
want. they will describe things in broad terms... I want to style my user
interface using colors from the NY Giants football team." No lookup table this
generator could maintain covers every sports team, holiday, brand, or mood a
user might name -- that resolution is a knowledge/reasoning task, which belongs
to whatever chat AI is driving this skill (it already knows the Giants are blue
and red), not a hardcoded table here.

So the two concerns are kept separate:

  - `parse_style_description` / `apply_chat_style`: a small, literal, inspectable
    parser for descriptions that already name real CSS colors directly ("dark
    blue buttons with white text") -- useful on its own for the common literal
    case, not a general theme-name resolver.
  - `apply_palette_project_wide`: takes an ALREADY-RESOLVED palette dict (however
    it was produced -- parsed here, reasoned about by the driving chat AI for
    "Halloween"/"NY Giants colors"/anything else, or a later Stage-3 source) and
    applies it across every matching component instance in the project. This is
    the actual reusable mechanism; `apply_chat_style` is just
    `parse_style_description` followed by a call to it.

Scope: ch5-button only, matching palette.py's own PALETTE_MAPPING (Stage 2) --
extending to more types is the same per-type-verified work already used throughout
this project, not automatic just because a description happens to mention one.
"""
from __future__ import annotations

import re
from pathlib import Path

import background
import color_words
import compare
import layout
import palette
import reflow
from sdk import UiSdk

SEGMENT_SPLIT_RE = re.compile(r"\band\b|\bwith\b|,", re.IGNORECASE)


def _primary_query_for(project_dir: Path) -> str | None:
    """The project's primary resolution's own media query (see layout.py's
    orientation_media_query), or None if no `.cuip` is found in `project_dir` or the
    project has no resolutions configured yet. Passed to palette.apply_palette so a
    themed value reaches the primary resolution's own block, not just the catch-all
    -- matching Construct's real behavior (see layout.update_element_declarations'
    docstring). Looks for exactly one `*.cuip` in `project_dir`, the same
    one-project-per-folder convention this whole generator already assumes."""
    cuip_candidates = list(project_dir.glob("*.cuip"))
    if len(cuip_candidates) != 1:
        return None
    resolutions = background._project_resolutions(cuip_candidates[0])
    primary = reflow.pick_primary(resolutions, "landscape") or reflow.pick_primary(resolutions, "portrait")
    if primary is None:
        return None
    orientation = reflow._orientation_name(primary)
    return layout.orientation_media_query(orientation, primary["width"], primary["height"])

#: property keyword -> palette key, checked in this order (first match wins per
#: segment) -- matches palette.py's own PALETTE_MAPPING keys.
PROPERTY_KEYWORDS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bbackground\b|\bfill\b", re.IGNORECASE), "background_color"),
    (re.compile(r"\btext\b|\blabel\b|\bfont\b", re.IGNORECASE), "text_color"),
    (re.compile(r"\bborder\b|\boutline\b", re.IGNORECASE), "border_color"),
    (re.compile(r"\bicon\b", re.IGNORECASE), "icon_color"),
]

_WORD_RE = re.compile(r"[a-zA-Z]+")


def _find_color_in_segment(segment: str) -> str | None:
    """The first color phrase found in `segment`, preferring a 2-word match
    (e.g. "dark blue") over a 1-word one starting at the same position."""
    words = _WORD_RE.findall(segment.lower())
    for i in range(len(words)):
        two = " ".join(words[i:i + 2])
        color = color_words.resolve_color_phrase(two)
        if color:
            return color
        color = color_words.resolve_color_phrase(words[i])
        if color:
            return color
    return None


def parse_style_description(description: str) -> dict[str, str]:
    """A style description to a palette dict (see palette.py's PALETTE_MAPPING
    keys) -- e.g. "dark blue buttons with white text and an orange border" ->
    {"background_color": "#00008b", "text_color": "#ffffff",
    "border_color": "#ffa500"}. A segment naming no color at all contributes
    nothing (not an error -- most descriptions have filler words)."""
    result: dict[str, str] = {}
    for segment in SEGMENT_SPLIT_RE.split(description):
        color = _find_color_in_segment(segment)
        if color is None:
            continue
        key = "background_color"
        for pattern, palette_key in PROPERTY_KEYWORDS:
            if pattern.search(segment):
                key = palette_key
                break
        result[key] = color
    return result


def apply_palette_to_page(
    resolved_palette: dict[str, str],
    page_path: Path,
    sdk: UiSdk,
    *,
    tag_name: str = "ch5-button",
    derive_states: bool = True,
    primary_query: str | None = "auto",
) -> list[str]:
    """Apply an ALREADY-RESOLVED palette dict to EVERY `tag_name` instance on
    ONE page/widget file. "Every `tag_name` instance", not "every object" --
    palette.py's PALETTE_MAPPING (Stage 2) only covers `ch5-button` so far, so a
    page with OTHER real component types (a dpad, a slider, ...) only gets its
    buttons styled; those other types are named in `warnings` rather than
    silently skipped, since "style everything on this page" is what was asked
    for and a caller needs to know what didn't happen and why.

    `derive_states=True` (default): a normal-state-only palette is expanded via
    palette.derive_states to also cover pressed/selected, using standard UI
    convention, before applying -- see that function's docstring. Pass False
    for exact, no-magic control (e.g. a test asserting precisely which keys got
    written) or when `resolved_palette` already fully specifies every state
    itself.

    `primary_query`: the project's primary resolution's own media query, so its
    block also gets the value (matching Construct's real behavior -- see
    layout.update_element_declarations' docstring). Left at the sentinel
    `"auto"` (default), this is computed once via `_primary_query_for(page_path.
    parent)`; pass an explicit query string to reuse one already computed
    (project-wide callers do this to avoid recomputing per page), or `None` to
    skip it entirely (catch-all only).

    Returns `warnings` -- covers both unmapped types present on the page and any
    element `tag_name`'s own mapping doesn't cover (see palette.apply_palette);
    never raises for them.
    """
    if primary_query == "auto":
        primary_query = _primary_query_for(page_path.parent)
    if derive_states:
        resolved_palette = palette.derive_states(resolved_palette)
    warnings: list[str] = []
    raw = page_path.read_text(encoding="utf-8")
    parsed = compare.split_sections(raw, page_path.suffix.lower())
    if parsed is None:
        return [f"{page_path.name}: not a recognized section-based file -- skipped"]
    html_text = next((c for n, _, c in parsed.sections if n == "Html"), "")
    css_text = next((c for n, _, c in parsed.sections if n == "Css"), None)
    if css_text is None:
        return [f"{page_path.name}: no {{Css}} section -- skipped"]

    tag_index = reflow._tag_index(html_text)
    target_ids = [eid for eid, (tag, _) in tag_index.items() if tag == tag_name]
    other_tags = sorted({tag for _, (tag, _) in tag_index.items() if tag != tag_name})
    if other_tags:
        # NO_STYLABLE_PROPERTIES types are excluded from this warning -- there is
        # nothing this mechanism could ever do for them (empty schema), so
        # naming them here would be noise, not a real gap to flag.
        unmapped = [t for t in other_tags
                   if t not in palette.PALETTE_MAPPING and t not in palette.NO_STYLABLE_PROPERTIES]
        if unmapped:
            warnings.append(
                f"{page_path.name}: no palette mapping yet for {unmapped} -- "
                f"left unstyled (see palette.py::supported_tags())"
            )
    if not target_ids:
        return warnings

    new_css = css_text
    for element_id in target_ids:
        try:
            new_css = palette.apply_palette(new_css, element_id, sdk, tag_name, resolved_palette,
                                            primary_query=primary_query)
        except KeyError as e:
            warnings.append(f"{page_path.name}: {element_id!r} -- {e}")

    new_sections = [
        (name, header, new_css if name == "Css" else content)
        for name, header, content in parsed.sections
    ]
    rebuilt = parsed.preamble + "".join(header + content for _, header, content in new_sections)
    page_path.write_text(rebuilt, encoding="utf-8", newline="")
    return warnings


def apply_palette_to_page_all_types(
    resolved_palette: dict[str, str], page_path: Path, sdk: UiSdk, *,
    derive_states: bool = True, primary_query: str | None = "auto",
) -> list[str]:
    """Apply an ALREADY-RESOLVED palette across EVERY MAPPED component type on
    ONE page/widget -- "style all objects on this page" in the literal sense,
    not one tag at a time (see apply_palette_to_page, which only ever touches
    `tag_name`). For each real type present, only the palette keys THAT TYPE's
    own mapping actually supports are applied (palette.applicable_subset) --
    e.g. `icon_color` is silently skipped for `ch5-text`, which has no icon;
    that is normal filtering, not an error.

    `derive_states=True` (default): see apply_palette_to_page's docstring --
    expands a normal-only palette to cover pressed/selected first (types that
    don't support those keys simply filter them back out via
    applicable_subset, so this is harmless for e.g. `ch5-text`).

    Returns `warnings`: a type with no mapping at all is reported UNLESS it's in
    palette.NO_STYLABLE_PROPERTIES (nothing this mechanism could ever do for it,
    not a real gap); any element an applicable mapping still doesn't cover is
    also reported. Never raises for them.
    """
    if primary_query == "auto":
        primary_query = _primary_query_for(page_path.parent)
    if derive_states:
        resolved_palette = palette.derive_states(resolved_palette)
    warnings: list[str] = []
    raw = page_path.read_text(encoding="utf-8")
    parsed = compare.split_sections(raw, page_path.suffix.lower())
    if parsed is None:
        return [f"{page_path.name}: not a recognized section-based file -- skipped"]
    html_text = next((c for n, _, c in parsed.sections if n == "Html"), "")
    css_text = next((c for n, _, c in parsed.sections if n == "Css"), None)
    if css_text is None:
        return [f"{page_path.name}: no {{Css}} section -- skipped"]

    tag_index = reflow._tag_index(html_text)
    ids_by_tag: dict[str, list[str]] = {}
    for eid, (tag, _) in tag_index.items():
        ids_by_tag.setdefault(tag, []).append(eid)

    new_css = css_text
    for tag_name, ids in sorted(ids_by_tag.items()):
        if tag_name not in palette.PALETTE_MAPPING:
            if tag_name not in palette.NO_STYLABLE_PROPERTIES:
                warnings.append(
                    f"{page_path.name}: no palette mapping yet for {tag_name!r} -- "
                    f"left unstyled (see palette.py::supported_tags())"
                )
            continue
        subset = palette.applicable_subset(tag_name, resolved_palette)
        if not subset:
            continue
        for element_id in ids:
            try:
                new_css = palette.apply_palette(new_css, element_id, sdk, tag_name, subset,
                                                primary_query=primary_query)
            except KeyError as e:
                warnings.append(f"{page_path.name}: {element_id!r} -- {e}")

    new_sections = [
        (name, header, new_css if name == "Css" else content)
        for name, header, content in parsed.sections
    ]
    rebuilt = parsed.preamble + "".join(header + content for _, header, content in new_sections)
    page_path.write_text(rebuilt, encoding="utf-8", newline="")
    return warnings


def apply_palette_project_wide_all_types(
    resolved_palette: dict[str, str], project_dir: Path, sdk: UiSdk, *, derive_states: bool = True,
) -> list[str]:
    """apply_palette_to_page_all_types over every page/widget file in `project_dir`
    -- "theme my whole project, every object" in the fullest sense. Derives
    pressed/selected once here (not per-page) so it's computed a single time; same
    for the project's primary-resolution query (see _primary_query_for). Pass
    `derive_states=False` to skip state derivation."""
    if derive_states:
        resolved_palette = palette.derive_states(resolved_palette)
    primary_query = _primary_query_for(project_dir)
    warnings: list[str] = []
    for page_path in list(project_dir.glob("*.cuig")) + list(project_dir.glob("*.cuiw")):
        warnings.extend(apply_palette_to_page_all_types(
            resolved_palette, page_path, sdk, derive_states=False, primary_query=primary_query))
    return warnings


def apply_palette_project_wide(
    resolved_palette: dict[str, str],
    project_dir: Path,
    sdk: UiSdk,
    *,
    tag_name: str = "ch5-button",
    derive_states: bool = True,
) -> list[str]:
    """Apply an ALREADY-RESOLVED palette dict (see palette.py's PALETTE_MAPPING
    keys, e.g. {"background_color": "#0b2265", "text_color": "#a71930"} for "NY
    Giants colors") to EVERY `tag_name` instance across every *.cuig/*.cuiw in
    `project_dir` -- "theme my project" in the whole-project sense the feature
    was originally asked for, not one component at a time. Where the palette
    values themselves come from is entirely up to the caller: a literal
    description via parse_style_description, or a chat AI's own knowledge of
    what "Halloween" or a sports team's colors are -- this function only knows
    how to apply values it's given, never how to invent them.

    `derive_states=True` (default): expands a normal-only palette to also cover
    pressed/selected via palette.derive_states, computed ONCE here rather than
    per-page. Pass False for exact, no-magic control.

    Just apply_palette_to_page over every page/widget file -- returns the
    combined warnings.
    """
    if derive_states:
        resolved_palette = palette.derive_states(resolved_palette)
    primary_query = _primary_query_for(project_dir)
    warnings: list[str] = []
    for page_path in list(project_dir.glob("*.cuig")) + list(project_dir.glob("*.cuiw")):
        warnings.extend(apply_palette_to_page(
            resolved_palette, page_path, sdk, tag_name=tag_name, derive_states=False, primary_query=primary_query))
    return warnings


def apply_chat_style(
    description: str,
    project_dir: Path,
    sdk: UiSdk,
    *,
    tag_name: str = "ch5-button",
    derive_states: bool = True,
) -> tuple[dict[str, str], list[str]]:
    """Parse `description` for LITERAL color words (see module docstring -- this
    is the narrow, inspectable path, not a general theme-name resolver) and
    apply the result via apply_palette_project_wide (which, by default, also
    derives pressed/selected states -- see palette.derive_states). Returns
    `(parsed_palette, warnings)` -- `parsed_palette` is the palette AS PARSED
    from the description, before state derivation, so callers see exactly what
    was read from the text. Raises ValueError up front if the description named
    no recognizable color/property at all, before touching any file -- a broad/
    named description ("Halloween theme") is expected to hit this and should be
    resolved to real colors by the caller instead (see
    apply_palette_project_wide's docstring).
    """
    parsed_palette = parse_style_description(description)
    if not parsed_palette:
        raise ValueError(f"no recognized color/property found in {description!r}")
    warnings = apply_palette_project_wide(parsed_palette, project_dir, sdk, tag_name=tag_name, derive_states=derive_states)
    return parsed_palette, warnings
