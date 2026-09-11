"""Phase 8 (fonts): Fontsource composes into the same install/discovery pipeline as
Google Fonts, end to end against the real service. Writes only to a scratch
directory, never the real global webfont library.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import fonts  # noqa: E402
import fontsource as fs  # noqa: E402
from sdk import read_sdk  # noqa: E402

sdk = read_sdk("2.18.0")
SCRATCH = Path(__file__).resolve().parent / "FontsourceFindAndInstall"
SCRATCH.mkdir(exist_ok=True)


def find_and_install(query: str, target_dir: Path) -> str:
    """Same shape as fonts_find_and_install_test.py's helper for Google Fonts --
    proves Fontsource plugs into the identical downstream pipeline (validate/install/
    discover) without fonts.py knowing or caring which search module produced the
    bytes."""
    matches = fs.search_fontsource(query)
    if not matches:
        raise ValueError(f"Fontsource has nothing unique matching {query!r}")
    family = matches[0]
    data = fs.download_fontsource_file(family)
    fonts.import_font_file(data, family, target_dir=target_dir)
    return family


installed = find_and_install("Adwaita Sans", SCRATCH)
assert installed == "Adwaita Sans"
path = SCRATCH / "Adwaita Sans.ttf"
assert path.is_file() and path.stat().st_size > 10_000
print(f"find_and_install('Adwaita Sans') via Fontsource -> {path.stat().st_size} bytes: OK")

# Once installed, it is indistinguishable from any other library font -- the whole
# point of the filename-is-the-name rule fonts.py already enforces.
assert "Adwaita Sans" in fonts.webfont_names(SCRATCH)
assert "Adwaita Sans" in fonts.available_fonts(sdk, SCRATCH)
fonts._validate_font(sdk, "Adwaita Sans", SCRATCH)  # must not raise
print("a Fontsource-installed font validates as selectable, via the exact same "
      "code path as a Google Fonts or user-supplied one: OK")

# A query that only matches Google-covered fonts correctly finds nothing HERE --
# proving the exclusion is enforced at the point of use, not just in isolation.
try:
    find_and_install("Open Sans", SCRATCH)
except ValueError as e:
    assert "Open Sans" in str(e), str(e)
    print("a Google-covered query correctly finds nothing via Fontsource: OK")
else:
    raise AssertionError("'Open Sans' is Google-sourced; Fontsource must not claim it")

real_library = fonts.global_webfonts_path()
assert not (real_library / "Adwaita Sans.ttf").exists(), \
    "must never write to the user's real font library"
print("the real global webfont library is untouched: OK")

print("\nFontsource find-and-install chain: all assertions passed.")
