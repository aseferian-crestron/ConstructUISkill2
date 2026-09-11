"""Phase 8 (fonts): installing a font FILE into the webfont library -- validation,
sanitization, and the filename-IS-the-family-name rule.

`import_font_file` writes into a scratch directory here, never the real
`global_webfonts_path()` -- a test run must not pollute the user's actual font
library with test fonts.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import fonts  # noqa: E402

SCRATCH = Path(__file__).resolve().parent / "FontsImport"
SCRATCH.mkdir(exist_ok=True)
FAKE_TTF = b"\x00\x01\x00\x00" + b"fake but non-empty font bytes for a unit test"

# --- validate_font_family_name: the exact source rule -----------------------------------
for good in ("Roboto", "Roboto Slab", "IBM Plex Sans", "My-Font_2"):
    fonts.validate_font_family_name(good)
print("valid names accepted: OK")

for bad, why in (
    ("1Bad", "starts with a digit"),
    ("-Bad", "starts with a hyphen"),
    ("!Weird!", "contains punctuation outside the allowed set"),
    ("a", "too short (1 char, min is 2)"),
    ("x" * 32, "too long (32 chars, max is 31)"),
    ("", "empty"),
):
    try:
        fonts.validate_font_family_name(bad)
    except ValueError:
        pass
    else:
        raise AssertionError(f"{bad!r} should be rejected ({why})")
print("invalid names rejected for the right reasons: OK")

# Exactly at the boundary: 2 and 31 characters are both valid.
fonts.validate_font_family_name("Ab")
fonts.validate_font_family_name("A" * 31)
print("length boundary (2 and 31 chars) accepted: OK")

# --- sanitize_font_family_name: best-effort repair, not a silent pass-through ----------
assert fonts.sanitize_font_family_name("123 Cool Font!!") == "Cool Font"
assert fonts.sanitize_font_family_name("Roboto Slab") == "Roboto Slab", \
    "an already-valid name must come back unchanged"
assert fonts.sanitize_font_family_name("  Weird__Spacing  ") == "Weird__Spacing"
long_name = "A" + "b" * 40
assert len(fonts.sanitize_font_family_name(long_name)) <= 31
try:
    fonts.sanitize_font_family_name("!!!123!!!")
except ValueError as e:
    assert "no usable" in str(e), str(e)
    print("a name with nothing usable after sanitizing raises rather than returning junk: OK")
else:
    raise AssertionError("'!!!123!!!' has no letters at all and must not sanitize to something")
print("sanitize repairs common problems and leaves valid names untouched: OK")

# --- import_font_file: filename IS the family name, not any original filename ---------
destination = fonts.import_font_file(FAKE_TTF, "Test Import Font", target_dir=SCRATCH)
assert destination == SCRATCH / "Test Import Font.ttf", destination
assert destination.read_bytes() == FAKE_TTF
print(f"import_font_file writes '<family_name>.ttf': {destination.name}: OK")

# The written file is immediately visible to the discovery mechanism already built for
# the "use a library font" slice -- the two halves of this feature must agree on shape.
assert "Test Import Font" in fonts.webfont_names(SCRATCH)
print("the imported font is immediately discoverable by webfont_names(): OK")

# --- import_font_file validates BEFORE writing anything --------------------------------
before = set(SCRATCH.iterdir())
try:
    fonts.import_font_file(FAKE_TTF, "1Bad", target_dir=SCRATCH)
except ValueError:
    assert set(SCRATCH.iterdir()) == before, "a rejected import must not write a file"
    print("an invalid family name is rejected before any file is written: OK")
else:
    raise AssertionError("'1Bad' must be rejected")

try:
    fonts.import_font_file(FAKE_TTF, "Valid Name But Bad Extension",
                           target_dir=SCRATCH, extension=".exe")
except ValueError as e:
    assert ".exe" in str(e), str(e)
    assert set(SCRATCH.iterdir()) == before, "a rejected extension must not write a file"
    print("an unsupported extension is rejected before any file is written: OK")
else:
    raise AssertionError("'.exe' must be rejected -- not a supported webfont extension")

# --- import_font_file does NOT touch the real, global webfont library ------------------
real_library = fonts.global_webfonts_path()
assert not (real_library / "Test Import Font.ttf").exists(), \
    "a test import must never land in the user's real font library"
print("the real global webfont library is untouched by this test: OK")

print("\nFont import (validation, sanitize, install): all assertions passed.")
