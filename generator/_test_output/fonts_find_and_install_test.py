"""Phase 8 (fonts): the full "go find me a font named X" chain, end to end against the
real Google Fonts service -- search -> download -> import -> discoverable by the
existing library-font mechanism. Writes only to a scratch directory, never the real
global webfont library.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import fonts  # noqa: E402
import google_fonts as gf  # noqa: E402
from sdk import read_sdk  # noqa: E402

sdk = read_sdk("2.18.0")
SCRATCH = Path(__file__).resolve().parent / "FontsFindAndInstall"
SCRATCH.mkdir(exist_ok=True)


def find_and_install(query: str, target_dir: Path) -> str:
    """What the skill layer will actually call: resolve a query to one real Google
    Fonts family, download it, install it under its own name. Deliberately NOT a
    function in fonts.py or google_fonts.py -- promoting it into either would give
    google_fonts.py a dependency on fonts.py (or the reverse), breaking the "neither
    depends on the other" split google_fonts.py's own docstring commits to. This test
    proves the three-call composition works cleanly with that split intact, so the
    glue belongs at the future skill layer, not inside either module."""
    matches = gf.search_google_fonts(query)
    if not matches:
        raise ValueError(f"Google Fonts has nothing matching {query!r}")
    family = matches[0]
    data = gf.download_google_font_file(family)
    fonts.import_font_file(data, family, target_dir=target_dir)
    return family


# --- the exact scenario from the user's own phrasing: "go find me a font" -------------
installed = find_and_install("Roboto Slab", SCRATCH)
assert installed == "Roboto Slab"
path = SCRATCH / "Roboto Slab.ttf"
assert path.is_file() and path.stat().st_size > 10_000
print(f"find_and_install('Roboto Slab') -> {installed!r}, {path.stat().st_size} bytes: OK")

# --- a fuzzy/partial query still resolves to a real, usable install --------------------
installed2 = find_and_install("open sans", SCRATCH)
assert installed2 == "Open Sans", f"expected the exact match to win, got {installed2!r}"
print(f"a partial/lowercase query resolves to the exact match {installed2!r}: OK")

# --- once installed, it is a first-class citizen of the EXISTING library mechanism ----
# The whole point of import is that the result plugs into what "use a library font"
# (the earlier slice) already validates against -- no separate code path needed.
names = fonts.webfont_names(SCRATCH)
assert {"Roboto Slab", "Open Sans"} <= names, names
available = fonts.available_fonts(sdk, SCRATCH)
assert "Roboto Slab" in available and "Open Sans" in available
fonts._validate_font(sdk, "Roboto Slab", SCRATCH)  # must not raise
print("newly-installed fonts validate as selectable, via the same code path as any "
      "other library font: OK")

# --- a query with no real match fails clearly, before any network download attempt ----
try:
    find_and_install("ThisIsDefinitelyNotARealFontXYZ123", SCRATCH)
except ValueError as e:
    assert "ThisIsDefinitelyNotARealFontXYZ123" in str(e), str(e)
    print("a query matching nothing fails clearly, without attempting a download: OK")
else:
    raise AssertionError("a nonexistent query must not silently install nothing")

# --- the real, global webfont library is never touched by any of this -----------------
real_library = fonts.global_webfonts_path()
for name in ("Roboto Slab.ttf", "Open Sans.ttf"):
    assert not (real_library / name).exists(), \
        f"{name} must not have been written to the user's real font library"
print("the real global webfont library is untouched: OK")

print("\nFind-and-install chain: all assertions passed.")
