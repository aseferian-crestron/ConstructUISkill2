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

import color_words
import compare
import palette
import reflow
from sdk import UiSdk

SEGMENT_SPLIT_RE = re.compile(r"\band\b|\bwith\b|,", re.IGNORECASE)

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
) -> list[str]:
    """Apply an ALREADY-RESOLVED palette dict to EVERY `tag_name` instance on
    ONE page/widget file. "Every `tag_name` instance", not "every object" --
    palette.py's PALETTE_MAPPING (Stage 2) only covers `ch5-button` so far, so a
    page with OTHER real component types (a dpad, a slider, ...) only gets its
    buttons styled; those other types are named in `warnings` rather than
    silently skipped, since "style everything on this page" is what was asked
    for and a caller needs to know what didn't happen and why.

    Returns `warnings` -- covers both unmapped types present on the page and any
    element `tag_name`'s own mapping doesn't cover (see palette.apply_palette);
    never raises for them.
    """
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
        unmapped = [t for t in other_tags if t not in palette.PALETTE_MAPPING]
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
            new_css = palette.apply_palette(new_css, element_id, sdk, tag_name, resolved_palette)
        except KeyError as e:
            warnings.append(f"{page_path.name}: {element_id!r} -- {e}")

    new_sections = [
        (name, header, new_css if name == "Css" else content)
        for name, header, content in parsed.sections
    ]
    rebuilt = parsed.preamble + "".join(header + content for _, header, content in new_sections)
    page_path.write_text(rebuilt, encoding="utf-8", newline="")
    return warnings


def apply_palette_project_wide(
    resolved_palette: dict[str, str],
    project_dir: Path,
    sdk: UiSdk,
    *,
    tag_name: str = "ch5-button",
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

    Just apply_palette_to_page over every page/widget file -- returns the
    combined warnings.
    """
    warnings: list[str] = []
    for page_path in list(project_dir.glob("*.cuig")) + list(project_dir.glob("*.cuiw")):
        warnings.extend(apply_palette_to_page(resolved_palette, page_path, sdk, tag_name=tag_name))
    return warnings


def apply_chat_style(
    description: str,
    project_dir: Path,
    sdk: UiSdk,
    *,
    tag_name: str = "ch5-button",
) -> tuple[dict[str, str], list[str]]:
    """Parse `description` for LITERAL color words (see module docstring -- this
    is the narrow, inspectable path, not a general theme-name resolver) and
    apply the result via apply_palette_project_wide. Returns
    `(parsed_palette, warnings)`; raises ValueError up front if the description
    named no recognizable color/property at all, before touching any file --
    a broad/named description ("Halloween theme") is expected to hit this and
    should be resolved to real colors by the caller instead (see
    apply_palette_project_wide's docstring).
    """
    parsed_palette = parse_style_description(description)
    if not parsed_palette:
        raise ValueError(f"no recognized color/property found in {description!r}")
    warnings = apply_palette_project_wide(parsed_palette, project_dir, sdk, tag_name=tag_name)
    return parsed_palette, warnings
