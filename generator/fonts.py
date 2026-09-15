"""Global font swap -- Phase 8 (fonts), first slice.

Scope decision (2026-09-11, with the user): global font-swap only, but "font" now
includes fonts already sitting in Construct's own application-level font library --
NOT only its 5 hardcoded system/Crestron names. Genuinely NEW webfont IMPORT (adding a
font FILE the library does not have yet -- copying it in, and everything the packaging
step needs to bundle it for a build) is still deliberately deferred: this session has
not created a real project that does that, so there is nothing to verify a fresh
import's shape against.

What "already in the library" means, and why it is NOT the deferred case: the user
asked to swap to "Stylish Comic that is in my library" -- a font that is ALREADY a
`.ttf` file sitting in Construct's own webfont folder (see `global_webfonts_path`),
verified present on this machine before any code was written. Discovering and USING an
existing library font is a read-only filesystem check against a folder location fully
traced from source (`EnvironmentUtility.cs` + `ThemeAndFontUpdateHandler.cs`) and
confirmed against this machine's real, running install (its own log, and the folder's
real contents) -- a fundamentally smaller, lower-risk claim than "we can correctly
import and package a brand-new font," which is what stays deferred.

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

import os
import re
import sys
from pathlib import Path

from project import override_attr, read_cuip, write_cuip
from sdk import UiSdk

#: `CommonThemeAndFontHelper.cs::GetValidWebfontExtensions` -- the file types Construct's
#: own font scan recognizes.
VALID_WEBFONT_EXTENSIONS = (".woff2", ".woff", ".ttf", ".eot", ".svg")


def documents_path() -> Path:
    """The equivalent of .NET's `Environment.GetFolderPath(SpecialFolder.MyDocuments)`,
    which is what `EnvironmentUtility.cs` resolves `myDocumentsPath` from on both
    platforms (same call, same "Crestron"/"Crestron Construct" suffix appended
    afterward for each -- see `global_webfonts_path`'s docstring).

    Windows: the registry value Explorer itself uses, `HKCU\\Software\\Microsoft\\
    Windows\\CurrentVersion\\Explorer\\User Shell Folders\\Personal`. NOT simply
    `~/Documents` -- confirmed on this machine, where OneDrive's "back up your Documents
    folder" redirects that registry value, and Construct's own log
    (`EnvironmentUtility solutionsPath: ...`) shows it resolving the redirected path,
    not the plain profile folder. Falls back to `~/Documents` if the registry is
    unreadable (a fresh/non-Windows-profile edge case, not expected in practice).

    macOS: `~/Documents` -- Apple's `NSDocumentDirectory`, which is what .NET's
    `SpecialFolder.MyDocuments` maps to there; no OneDrive-style redirection concept
    exists on that platform.
    """
    if sys.platform == "win32":
        try:
            import winreg

            key_path = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                value, _ = winreg.QueryValueEx(key, "Personal")
            return Path(os.path.expandvars(value))
        except OSError:
            pass
    return Path.home() / "Documents"


def global_webfonts_path() -> Path:
    """Construct's own, machine-wide webfont library: `<Documents>/Crestron/
    Crestron Construct/Webfonts`. Fonts here are APPLICATION-scoped, not tied to any one
    project -- confirmed both from source and from this machine's real folder contents.

    Traced in `C:\\Git\\CCIDE\\Crestron.IDE\\AppHost\\Crestron.IDE\\Common\\Utils\\
    EnvironmentUtility.cs::CombineStoragePaths`: `solutionsPath = myDocumentsPath +
    "/Solutions"` (same `myDocumentsPath` on both platforms: `Environment.
    GetFolderPath(SpecialFolder.MyDocuments)/Crestron/Crestron Construct`), and in
    `PageDesigner.Server\\Commands\\Handler\\StylingAssets\\ThemeAndFontUpdateHandler.cs`:
    `webFontDirectory = Path.Combine(Path.GetDirectoryName(_appEnvironment.
    SolutionsPath), _uiEditorSettings.WebFonts)` -- i.e. `Solutions`'s own SIBLING
    folder, named `"Webfonts"` per `uieditor.appsettings.json`.

    Confirmed against this machine's real, running Construct install: its own log
    (`AppStorage\\Logs\\jsonlog_*.json`, `"EnvironmentUtility solutionsPath: ..."`) shows
    `solutionsPath` resolving to `.../Crestron/Crestron Construct/Solutions`, and the
    computed sibling `.../Crestron Construct/Webfonts` exists on disk with real font
    files in it -- including `Stylish Comic.ttf`.
    """
    return documents_path() / "Crestron" / "Crestron Construct" / "Webfonts"


def project_webfonts_path(cuip_path) -> Path:
    """A project's OWN `webfonts/` subfolder, sibling of `assets/`/`languages/` --
    named in `ProjectArchiveHelper.cs` ("Project 'webfonts' folder"). On archive/export,
    Construct copies any font here into the global library if it is not already there;
    for our purposes it is simply a SECOND place a font name can legitimately come from.
    """
    return Path(cuip_path).parent / "webfonts"


def webfont_names(*directories) -> set[str]:
    """Font family names available from webfont files in `directories` (any that do not
    exist are skipped, not an error -- most projects have no local `webfonts/` folder at
    all). A file's font family is its name without extension, matching
    `ThemeAndFontUpdateHandler.cs`'s own grouping (`GroupBy(f =>
    Path.GetFileNameWithoutExtension(f))`), filtered to `VALID_WEBFONT_EXTENSIONS`.
    """
    names: set[str] = set()
    for directory in directories:
        directory = Path(directory)
        if not directory.is_dir():
            continue
        for file in directory.iterdir():
            if file.suffix.lower() in VALID_WEBFONT_EXTENSIONS:
                names.add(file.stem)
    return names


def available_fonts(sdk: UiSdk, *webfont_directories) -> list[str]:
    """Every font a component's Font Family dropdown can actually show a selection for:
    the SDK's fixed system default and Crestron-bundled custom fonts
    (`component-context.json`'s `global.defaults.attributes`, `UiEditorFont` +
    `CrestronCustomFont` -- see module docstring for the client-side trace pinning these
    as two of `getAllFonts`'s three sources), plus the name of every webfont file found
    in `webfont_directories` (the third source, `editor.CustomWebFonts` -- typically
    `global_webfonts_path()` and/or `project_webfonts_path(cuip_path)`).
    """
    attributes = sdk.component_context["global"]["defaults"]["attributes"]
    sdk_fonts = [attributes["UiEditorFont"], *attributes.get("CrestronCustomFont", [])]
    return sdk_fonts + sorted(webfont_names(*webfont_directories) - set(sdk_fonts))


#: `App.Common.Constants.cs::AssetNameValidationRegex`, confirmed against
#: `CommonThemeAndFontHelper.cs::InvalidFontCharacter`, which is what actually gates a
#: font's filename. Must start with a letter; the rest is letters/digits/spaces/
#: underscores/hyphens. Documented in docs/ConstructUISkill_FontImport.md.
FONT_FAMILY_NAME_RE = re.compile(r"(^[a-zA-Z\s]+[a-zA-Z]|^[a-zA-Z]+[a-zA-Z0-9 _-])[a-zA-Z0-9-_ ]*$")

#: `PageDesigner.Common\Constants.cs::WebFontConstants.MinLength/MaxLength`.
FONT_FAMILY_NAME_MIN_LENGTH = 2
FONT_FAMILY_NAME_MAX_LENGTH = 31


def validate_font_family_name(name: str) -> None:
    """Raises ValueError if `name` cannot be a webfont's filename (and so its exposed
    Font Family name -- see `import_font_file`'s docstring for why filename IS the
    name). Both the character rule and the length bound come from Construct's own
    validation, not an assumption -- see `FONT_FAMILY_NAME_RE`."""
    if not (FONT_FAMILY_NAME_MIN_LENGTH <= len(name) <= FONT_FAMILY_NAME_MAX_LENGTH):
        raise ValueError(
            f"{name!r} is {len(name)} characters; a font family name must be "
            f"{FONT_FAMILY_NAME_MIN_LENGTH}-{FONT_FAMILY_NAME_MAX_LENGTH}")
    if not FONT_FAMILY_NAME_RE.match(name):
        raise ValueError(
            f"{name!r} is not a valid font family name -- it must start with a letter "
            f"and contain only letters, digits, spaces, underscores and hyphens")


def sanitize_font_family_name(name: str) -> str:
    """Best-effort repair of a name that fails `validate_font_family_name`, rather than
    only ever rejecting one outright -- most real font names need no change at all, and
    this covers docs/ConstructUISkill_FontImport.md's "the filename must be modified
    before import if it starts with an invalid character" case automatically. Strips
    anything outside [a-zA-Z0-9 _-], strips leading characters until the name starts
    with a letter, then trims to the length bound. Raises ValueError only if nothing
    resembling a name survives (e.g. the input was entirely digits/punctuation).
    """
    cleaned = re.sub(r"[^a-zA-Z0-9 _-]", "", name)
    cleaned = re.sub(r"^[^a-zA-Z]+", "", cleaned)
    cleaned = cleaned[:FONT_FAMILY_NAME_MAX_LENGTH].rstrip()
    if len(cleaned) < FONT_FAMILY_NAME_MIN_LENGTH:
        raise ValueError(f"{name!r} has no usable font family name after sanitizing")
    validate_font_family_name(cleaned)
    return cleaned


def import_font_file(data: bytes, family_name: str, *, target_dir=None,
                     extension: str = ".ttf") -> Path:
    """Install a font FILE (already-downloaded bytes) into a webfont folder, named
    after `family_name` -- validated first, never sanitized silently here (call
    `sanitize_font_family_name` yourself if you want that; a caller installing a
    specific, deliberately-chosen name should not have it silently altered).

    The filename IS what Construct exposes as the Font Family name (see the module
    docstring and `webfont_names`'s own note) -- NOT any name embedded in the font
    file itself, and not whatever filename the source (a download, a user's own file)
    happened to carry. So this always writes `<family_name><extension>`, discarding
    any original filename entirely.

    `target_dir` defaults to `global_webfonts_path()` -- the shared, application-level
    library every project's Font Family dropdown draws from, matching how a user
    describes "a font in my library". Pass `project_webfonts_path(cuip_path)` for a
    project-local copy instead.

    Raises ValueError for an invalid family name or unsupported extension (see
    `VALID_WEBFONT_EXTENSIONS`) -- checked BEFORE writing anything, so a rejected
    import never leaves a partial file behind.
    """
    validate_font_family_name(family_name)
    extension = extension.lower()
    if extension not in VALID_WEBFONT_EXTENSIONS:
        raise ValueError(f"{extension!r} is not a supported webfont extension -- "
                         f"valid: {', '.join(VALID_WEBFONT_EXTENSIONS)}")

    directory = Path(target_dir) if target_dir is not None else global_webfonts_path()
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / f"{family_name}{extension}"
    destination.write_bytes(data)
    return destination


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
#:
#: The value can also carry NO quotes at all -- a theme-selector rule in the live
#: project's ReflowTest.cuig has `font-family:Creepster;` unquoted, unlike every other
#: occurrence in the project. The unquoted alternative matches up to the next quote,
#: `;`, or `}` and is replaced staying unquoted (see `_font_family_repl`).
_FONT_FAMILY_RE = re.compile(r"""(font-family\s*:\s*)(?:(['"])[^'"]*\2|[^'";}]+)""")


def _font_family_repl(match: "re.Match[str]", new_font: str) -> str:
    prefix, quote = match.group(1), match.group(2)
    if quote:
        return f"{prefix}{quote}{new_font}{quote}"
    return f"{prefix}{new_font}"


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
    text, n2 = _FONT_FAMILY_RE.subn(lambda m: _font_family_repl(m, new_font), text)
    return text, n1 + n2


def _validate_font(sdk: UiSdk, new_font: str, *webfont_directories) -> None:
    valid = available_fonts(sdk, *webfont_directories)
    if new_font not in valid:
        raise ValueError(
            f"{new_font!r} is not selectable in the Font Family dropdown -- it is "
            f"not the SDK's system default, not one of its Crestron-bundled fonts, and "
            f"not a webfont found in {', '.join(str(d) for d in webfont_directories) or '(no folders checked)'}. "
            f"Valid choices: {', '.join(valid)}")


def set_page_font(path: Path, new_font: str, sdk: UiSdk, *webfont_directories) -> int:
    """Rewrite one .cuig/.cuiw's Html and Css sections (never FileMetadata or
    PageAttributes' non-attribute parts) to use `new_font`. Returns the replacement
    count; 0 means the file mentioned no font at all and was left untouched on disk
    (no spurious write, no spurious `Modified` timestamp bump).

    PageAttributes IS touched -- component elements' `ccid_ActiveFont` lives in its
    `[Elements.Attributes]` tables, mirroring the Html view (see replace_font_in_text).

    `webfont_directories`: folders to additionally accept a font name from (see
    `available_fonts`) -- typically `global_webfonts_path()` and/or
    `project_webfonts_path(cuip_path)`. None by default: a bare page file, called
    directly rather than through `set_project_font`, is not assumed to belong to any
    particular project.

    Raises ValueError if `new_font` is not a selectable choice -- writing it anyway
    would produce a Font Family field with nothing to show.
    """
    _validate_font(sdk, new_font, *webfont_directories)
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

    `new_font` may be the SDK's system default, one of its Crestron-bundled fonts, OR
    the name of any webfont file found in Construct's global font library
    (`global_webfonts_path()`) or this project's own `webfonts/` folder
    (`project_webfonts_path`) -- e.g. "please replace the font everywhere with Stylish
    Comic that is in my library" resolves against the global folder, matching how a user
    picking from the real Font Family dropdown would see it.

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
    webfont_directories = (global_webfonts_path(), project_webfonts_path(cuip_path))
    _validate_font(sdk, new_font, *webfont_directories)

    attrs, device_resolution_source, metadata = read_cuip(cuip_path)
    changed = dict(attrs).get("DefaultFontFamily") != new_font
    if changed:
        override_attr(attrs, "DefaultFontFamily", new_font)
        write_cuip(cuip_path, attrs, device_resolution_source, metadata=metadata)

    results: dict[str, int] = {cuip_path.name: 1 if changed else 0}
    for page in sorted(cuip_path.parent.glob("*.cuig")) + sorted(cuip_path.parent.glob("*.cuiw")):
        results[page.name] = set_page_font(page, new_font, sdk, *webfont_directories)
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
