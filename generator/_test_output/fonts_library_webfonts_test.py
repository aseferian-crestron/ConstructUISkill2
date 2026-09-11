"""Phase 8 (fonts): using a font already in Construct's application-level webfont
library -- not the SDK's hardcoded system/Crestron names, and not a brand-new import.

The user asked: "please replace the font everywhere with Stylish Comic that is in my
library". "Stylish Comic" is not one of the 5 SDK-catalog fonts, but it IS a real .ttf
file sitting in Construct's own machine-wide webfont folder. Discovering that folder
correctly -- and NOT mistaking it for a Windows-system-font question -- is what this
file verifies, against the real, running Construct install on this machine rather than
an invented fixture.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import fonts  # noqa: E402
from sdk import read_sdk  # noqa: E402

sdk = read_sdk("2.18.0")

# --- documents_path resolves the REAL, possibly-redirected folder --------------------
# Confirmed on this machine: OneDrive's "back up your Documents folder" rewrites the
# registry value Explorer (and .NET's SpecialFolder.MyDocuments) reads, so a naive
# `Path.home() / "Documents"` would be WRONG here specifically -- Construct's own log
# resolves to the OneDrive-redirected path, not the plain profile folder.
docs = fonts.documents_path()
assert docs.is_dir(), f"documents_path() does not exist: {docs}"
print(f"documents_path(): {docs}")

# --- global_webfonts_path: sibling of Solutions, confirmed against Construct's own log -
webfonts_dir = fonts.global_webfonts_path()
assert webfonts_dir.is_dir(), (
    f"expected Construct's own webfont library at {webfonts_dir} -- if this machine's "
    f"install has moved, documents_path()/global_webfonts_path() need re-checking "
    f"against a fresh EnvironmentUtility log rather than assumed unchanged")
assert webfonts_dir.parent.name == "Crestron Construct"
assert (webfonts_dir.parent / "Solutions").is_dir(), \
    "Webfonts should be a sibling of Solutions, per ThemeAndFontUpdateHandler.cs"
print(f"global_webfonts_path(): {webfonts_dir}")

# --- webfont_names: filename without extension, valid extensions only ----------------
names = fonts.webfont_names(webfonts_dir)
assert "Stylish Comic" in names, \
    f"Stylish Comic.ttf is expected in the real webfont library; found: {sorted(names)}"
assert len(names) >= 10, f"expected a real, populated library, found only {len(names)}"
print(f"webfont_names(): {len(names)} fonts found, including 'Stylish Comic': OK")

# A nonexistent directory is skipped, not an error -- most projects have no local
# webfonts/ folder at all.
assert fonts.webfont_names(Path("Z:/does/not/exist")) == set()
assert fonts.webfont_names(Path("Z:/does/not/exist"), webfonts_dir) == names
print("a missing directory is skipped rather than raising: OK")

# --- available_fonts: SDK catalog + real library fonts, de-duplicated ----------------
combined = fonts.available_fonts(sdk, webfonts_dir)
assert "Roboto" in combined and "Crestron AV" in combined and "Stylish Comic" in combined
# The SDK's 5 names come first, in their own order, so a caller printing "valid choices"
# still leads with the always-available ones.
assert combined[:5] == fonts.available_fonts(sdk), combined[:5]
print(f"available_fonts(sdk, library): {len(combined)} total, SDK names first: OK")

# --- validation now accepts a real library font, and still rejects a fake one --------
fonts._validate_font(sdk, "Stylish Comic", webfonts_dir)
print("'Stylish Comic' validates against the real library: OK")

try:
    fonts._validate_font(sdk, "Not A Real Font", webfonts_dir)
except ValueError as e:
    assert "Not A Real Font" in str(e) and "Stylish Comic" in str(e), str(e)
    print("a font in neither the SDK nor the library still raises, listing the real choices: OK")
else:
    raise AssertionError("a font that exists nowhere must still be rejected")

# --- project_webfonts_path: sibling of a project's own .cuip -------------------------
fake_cuip = Path(r"C:\Solutions\SomeProject\SomeProject.cuip")
assert fonts.project_webfonts_path(fake_cuip) == Path(r"C:\Solutions\SomeProject\webfonts")
print("project_webfonts_path is the project's own sibling folder: OK")

print("\nLibrary webfont discovery: all assertions passed.")
