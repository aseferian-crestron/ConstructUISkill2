"""Global font swap -- Phase 8 (fonts), first slice.

Scope decision (2026-09-11, with the user): global font-swap only. Webfont IMPORT (a
non-system font added as a project asset) is deliberately deferred -- no project on this
machine has ever done it, so there is no real file to verify a `webfonts/` folder's
shape against, and shipping that unverified is exactly the mistake this project's own
README now calls out (see its Approach section).

**CORRECTION (2026-09-11, user-caught):** the first version of this module accepted any
string as `new_font` and wrote it everywhere. The user applied it (Roboto -> Montserrat)
and every component's Font Family field showed EMPTY in the Properties Grid -- the
attribute and CSS were written correctly, but Construct had nowhere to display them.

The Font Family trait is a CLOSED dropdown (`addFontFamilyTrait` in
`pd-ch5-components\\mixins\\common\\commonDynamicLabelMixins.ts`, `type: 'select'`), whose
options come from exactly three sources (`pd-utils\\src\\utilities.ts::getAllFonts`):
  1. `GlobalVars.SystemDefaultFont` -- **not** the project's own `DefaultFontFamily`.
     It is hardcoded from the SDK's `component-context.json`
     `global.defaults.attributes.UiEditorFont`, confirmed to be `"Roboto"` for SDK
     2.18.0 (`apiV1.ts::createEditorInstance`). Renaming a project's `DefaultFontFamily`
     does not move this.
  2. `GlobalVars.CrestronCustomFonts` -- the SDK's own `global.defaults.attributes.
     CrestronCustomFont` array, exactly 4 names for SDK 2.18.0: "Crestron AV",
     "Crestron General", "Crestron Lighting-HVAC", "Crestron Simple Icons".
  3. `editor.CustomWebFonts` -- fonts actually imported as project/machine webfonts,
     which is the deferred half of this phase.

So a font not in (1) or (2), and not actually present as a webfont, has NO dropdown
entry to select -- the value being written is not wrong, there is simply nothing for
Construct to show it as. `set_page_font`/`set_project_font` now validate `new_font`
against `available_fonts(sdk)` (system default + the SDK's Crestron custom list) and
raise, naming the valid choices, rather than silently writing a value the Properties
Grid can never display. The user's own edit to the reference project (`Component -
Button.cuig`, two buttons set to "Crestron AV" and "Stylish Comic") is what proved
`ccid_ActiveFont` legitimately varies PER COMPONENT, independent of the project
default -- "Crestron AV" is catalog source (2) above; "Stylish Comic" is presumably a
webfont, outside this phase's scope.

Grounded in `C:\\Git\\CCIDE\\Crestron.IDE\\Projects\\UiEditor\\UiEditor.Server\\Helpers\\
FontUpgradeHelper.cs`, which is Construct's own font-family-writing code (its `AddFontSupport`
upgrade path, not a live editing command, but the same two things it writes are what
every real component in the reference project already carries):

1. **`ccid_ActiveFont`**, a plain HTML/TOML attribute (`HandleActiveFont` ->
   `UpgradeHelper.AddAttributeHTML`), value `'FontName'` (single-quoted).
2. **A `font-family:"FontName"` CSS declaration**, whose SELECTOR shape depends on the
   component's label pattern (`GetFontFamilyDeclaration`, `FontSupportConstants` in
   `UiEditor.Server\\Constants.cs:262`). Four literal patterns, confirmed byte-for-byte
   against real reference files:
     - `#{id} .{tag} :not(i):not(svg)`           (ch5-button and most labeled components)
     - `#{id} :not(i):not(svg)`                  (no wrapper class -- e.g. html-header/text)
     - `#{id} span:not(.has-icon, .has-icon span)`  (keypad)
     - `#{id} span:not(.dpad-btn-icon)`          (dpad)
   This module does not need to choose which pattern applies per component (that is
   `generator/component.py`'s `theme_selectors`, already correct) -- swapping an
   EXISTING project's font only needs to find-and-replace whichever of these four
   selector shapes are already present, keyed by them being followed by
   `{font-family:"..."}`kind text, not by re-deriving them from the SDK.

**Not handled**, flagged rather than silently mishandled: user-authored inline HTML/CSS
that happens to embed its own `font-family` (Construct's own font scan treats this as a
separate case, `customHtmlContent`, see `ServerThemeAndFontHelper.cs`'s
`GetComponentFonts`). A global swap here only touches Construct's OWN generated
attribute/CSS, not arbitrary user content.
"""
from __future__ import annotations

import re
from pathlib import Path

from project import override_attr, read_cuip, write_cuip
from sdk import UiSdk


def available_fonts(sdk: UiSdk) -> list[str]:
    """The fonts a component's Font Family dropdown can actually show a selection for,
    without webfont import: the SDK's fixed system default plus its Crestron-bundled
    custom fonts (`component-context.json`'s `global.defaults.attributes`,
    `UiEditorFont` + `CrestronCustomFont` -- see module docstring for the client-side
    trace that pins these as the two non-webfont sources `getAllFonts` draws from).
    """
    attributes = sdk.component_context["global"]["defaults"]["attributes"]
    return [attributes["UiEditorFont"], *attributes.get("CrestronCustomFont", [])]

#: Same section-splitting convention as project.py::read_cuip / reflow.py's own copy --
#: kept local per this project's precedent of each writer owning its small section
#: reader rather than depending on harness/compare.py.
_SECTION_RE = re.compile(r"^\{(\w+)\}[ \t]*\r?\n?", re.MULTILINE)

#: `ccid_ActiveFont` as it appears in BOTH the Html view (`ccid_ActiveFont="'Font'"`) and
#: the mirrored TOML [Elements.Attributes] block (`ccid_ActiveFont = "'Font'"`) -- one
#: pattern serves both, since the only difference is the `=` spacing the two serializers
#: happen to use, which `\s*=\s*` absorbs.
#: Case-insensitive on the ATTRIBUTE NAME, not the value. Construct's own Html view
#: lowercases attribute names on save (confirmed: every real reference file's Html
#: section has `ccid_activefont`, its mirrored PageAttributes TOML has `ccid_ActiveFont`
#: -- 0 exceptions across 12 files checked), while our own generator currently writes
#: camelCase into both. Matching case-insensitively handles either source without
#: re-casing the key that is actually there (see the replacement callback below).
_ACTIVE_FONT_RE = re.compile(r"""(ccid_activefont\s*=\s*")'[^']*'(")""", re.IGNORECASE)

#: Construct's own generated font-family declaration -- see FontSupportConstants above.
#: Matches any of the four selector shapes, so this module does not need to re-derive
#: which one applies to which component; it only replaces the font NAME already present.
#:
#: Quote character is ['"], not hardcoded to one: `layout.py::build_position_css` always
#: writes double quotes WITH a space (`font-family: "Roboto"`), but a real file
#: (ReflowTest.cuig, predating this generator) carries single quotes with NO space
#: (`font-family:'Roboto'`) in 21 places -- both are valid CSS and Construct evidently
#: accepts either. The replacement re-uses whichever quote character was actually
#: matched (``) rather than normalizing it, so a file's existing style survives.
_FONT_FAMILY_RE = re.compile(r"""(font-family\s*:\s*)(['"])[^'"]*\2""")


def _read_sections(path: Path) -> tuple[str, list[tuple[str, str, str]]]:
    """See reflow.py's identical helper for why `newline=""` matters: it is what keeps
    a rewrite byte-identical outside the parts actually changed, regardless of whether
    the file already uses CRLF or bare LF."""
    with open(path, "r", encoding="utf-8", newline="") as f:
        raw = f.read()
    matches = list(_SECTION_RE.finditer(raw))
    preamble = raw[: matches[0].start()] if matches else raw
    sections = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
        sections.append((m.group(1), m.group(0), raw[start:end]))
    return preamble, sections


def _write_sections(path: Path, preamble: str, sections: list[tuple[str, str, str]]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(preamble + "".join(header + content for _, header, content in sections))


def replace_font_in_text(text: str, new_font: str) -> tuple[str, int]:
    """Replace every `ccid_ActiveFont` value and Construct-generated `font-family`
    declaration in `text` with `new_font`. Returns (new_text, replacement_count).

    Works directly on the raw file text rather than parsing HTML/CSS/TOML separately --
    the two patterns are specific enough (an attribute name, and a CSS property name)
    that they cannot collide with unrelated content, and this keeps the Html view and
    the mirrored TOML attribute (which must always agree -- see contracts.py's own
    Html/TOML-agreement precedent) updated by the same single pass.
    """
    text, n1 = _ACTIVE_FONT_RE.subn(rf"\g<1>'{new_font}'\g<2>", text)
    text, n2 = _FONT_FAMILY_RE.subn(rf"\g<1>\g<2>{new_font}\g<2>", text)
    return text, n1 + n2


def _validate_font(sdk: UiSdk, new_font: str) -> None:
    valid = available_fonts(sdk)
    if new_font not in valid:
        raise ValueError(
            f"{new_font!r} is not selectable in the Font Family dropdown -- it is "
            f"neither the SDK's system default nor one of its Crestron-bundled fonts, "
            f"and webfont import is not built yet (see fonts.py's module docstring). "
            f"Valid choices for {sdk.version}: {', '.join(valid)}")


def set_page_font(path: Path, new_font: str, sdk: UiSdk) -> int:
    """Rewrite one .cuig/.cuiw's Html and Css sections (never FileMetadata or
    PageAttributes' non-attribute parts) to use `new_font`. Returns the replacement
    count; 0 means the file mentioned no font at all and was left untouched on disk
    (no spurious write, no spurious `Modified` timestamp bump).

    PageAttributes IS touched -- component elements' `ccid_ActiveFont` lives in its
    `[Elements.Attributes]` tables, mirroring the Html view (see replace_font_in_text).

    Raises ValueError if `new_font` is not a selectable choice (see `available_fonts`)
    -- writing it anyway would produce a Font Family field with nothing to show.
    """
    _validate_font(sdk, new_font)
    preamble, sections = _read_sections(path)
    total = 0
    new_sections = []
    for name, header, content in sections:
        if name == "FileMetadata":
            new_sections.append((name, header, content))
            continue
        new_content, count = replace_font_in_text(content, new_font)
        total += count
        new_sections.append((name, header, new_content))
    if total:
        _write_sections(path, preamble, new_sections)
    return total


def set_project_font(cuip_path: Path, new_font: str, sdk: UiSdk) -> dict[str, int]:
    """Change a project's font everywhere: the `.cuip`'s `DefaultFontFamily`, and every
    `*.cuig`/`*.cuiw` sitting beside it. Returns {filename: replacement_count} for every
    file actually touched (the `.cuip` itself keyed as its own filename, count 1 if the
    attribute changed, 0 if it already held `new_font`).

    Raises ValueError if `new_font` is not a selectable choice -- see `set_page_font`;
    checked ONCE up front so a partially-applied project (the `.cuip` changed but only
    some pages) can never happen.

    Does NOT mark the project's contract stale -- a font is not a contract-relevant
    change (no component added/removed, no signal enabled/disabled, no rename; see
    contracts.py's own list of what DOES require it). `write_cuig` is deliberately
    bypassed here (going straight to the section read/write) for exactly that reason: it
    marks unconditionally on every write, which is the right default for component
    changes and the wrong one for this.
    """
    _validate_font(sdk, new_font)

    attrs, device_resolution_source, metadata = read_cuip(cuip_path)
    changed = dict(attrs).get("DefaultFontFamily") != new_font
    if changed:
        override_attr(attrs, "DefaultFontFamily", new_font)
        write_cuip(cuip_path, attrs, device_resolution_source, metadata=metadata)

    results: dict[str, int] = {cuip_path.name: 1 if changed else 0}
    for page in sorted(cuip_path.parent.glob("*.cuig")) + sorted(cuip_path.parent.glob("*.cuiw")):
        results[page.name] = set_page_font(page, new_font, sdk)
    return results


if __name__ == "__main__":
    import sys

    from sdk import read_sdk

    if len(sys.argv) != 3:
        print("usage: python fonts.py <project.cuip> <NewFontName>")
        raise SystemExit(1)
    sdk = read_sdk("2.18.0")
    for name, count in set_project_font(Path(sys.argv[1]), sys.argv[2], sdk).items():
        print(f"  {name}: {count} replacement(s)")
