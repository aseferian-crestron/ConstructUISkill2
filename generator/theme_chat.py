"""
Chat-described theming (Stage 3, source #1): translate a natural-language style
description ("dark blue buttons with white text and an orange border") into real
palette.py calls, applied across every matching component instance in a project --
"theme my project" in the whole-project sense the feature was originally asked for,
not one component at a time.

Scope: ch5-button only, matching palette.py's own PALETTE_MAPPING (Stage 2) --
extending to more types is the same per-type-verified work already used throughout
this project, not automatic just because a description happens to mention one.

Parsing is intentionally simple and inspectable, not an LLM/black box: split the
description on "and"/"with"/commas into segments, resolve each segment's color
word via color_words.py (the real CSS named-color table), and match a property
keyword (background/text/border/icon) within the SAME segment. A segment naming a
color with no recognized property keyword defaults to background_color -- the
natural reading of "make the buttons X" or "X buttons".
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


def apply_chat_style(
    description: str,
    project_dir: Path,
    sdk: UiSdk,
    *,
    tag_name: str = "ch5-button",
) -> tuple[dict[str, str], list[str]]:
    """Parse `description` and apply the resulting palette to EVERY `tag_name`
    instance across every *.cuig/*.cuiw in `project_dir`. Returns
    `(parsed_palette, warnings)` -- warnings note any element a mapping doesn't
    cover (see palette.apply_palette), never raises for them; raises ValueError
    up front only if the description itself named no recognizable color/property
    at all, before touching any file.
    """
    parsed_palette = parse_style_description(description)
    if not parsed_palette:
        raise ValueError(f"no recognized color/property found in {description!r}")

    warnings: list[str] = []
    for page_path in list(project_dir.glob("*.cuig")) + list(project_dir.glob("*.cuiw")):
        raw = page_path.read_text(encoding="utf-8")
        parsed = compare.split_sections(raw, page_path.suffix.lower())
        if parsed is None:
            warnings.append(f"{page_path.name}: not a recognized section-based file -- skipped")
            continue
        html_text = next((c for n, _, c in parsed.sections if n == "Html"), "")
        css_text = next((c for n, _, c in parsed.sections if n == "Css"), None)
        if css_text is None:
            continue
        tag_index = reflow._tag_index(html_text)
        target_ids = [eid for eid, (tag, _) in tag_index.items() if tag == tag_name]
        if not target_ids:
            continue

        new_css = css_text
        for element_id in target_ids:
            try:
                new_css = palette.apply_palette(new_css, element_id, sdk, tag_name, parsed_palette)
            except KeyError as e:
                warnings.append(f"{page_path.name}: {element_id!r} -- {e}")

        new_sections = [
            (name, header, new_css if name == "Css" else content)
            for name, header, content in parsed.sections
        ]
        rebuilt = parsed.preamble + "".join(header + content for _, header, content in new_sections)
        page_path.write_text(rebuilt, encoding="utf-8", newline="")
    return parsed_palette, warnings
