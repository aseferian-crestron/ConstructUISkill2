"""Phase 8 (fonts): "go find me a font" -- search and download real files from Google
Fonts. Verified against the REAL, live Google endpoints, not mocks -- consistent with
this project's standing practice (fonts_library_webfonts_test.py does the same against
the real Documents/Webfonts folder) of testing against real behavior wherever the real
thing is reachable and stable, rather than inventing a fixture that can drift from it.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import google_fonts as gf  # noqa: E402

# --- search: exact match ranks first ---------------------------------------------------
matches = gf.search_google_fonts("Roboto")
assert matches, "expected real matches for 'Roboto'"
assert matches[0] == "Roboto", f"exact match must rank first, got {matches}"
assert "Roboto Slab" in matches and "Roboto Mono" in matches, matches
print(f"search('Roboto'): {matches[:6]}... exact match ranks first: OK")

# --- search: case-insensitive, substring, no match is an empty list not an error -------
assert gf.search_google_fonts("roboto slab") == gf.search_google_fonts("Roboto Slab")
assert gf.search_google_fonts("robotoslab") == [], "no substring match, must not fuzzy-match"
assert gf.search_google_fonts("this-is-not-a-real-font-query-xyz123") == []
assert gf.search_google_fonts("") == [], "an empty query is not an error"
print("search is case-insensitive, substring-only, and empty/no-match returns []: OK")

# --- search: limit is honoured ----------------------------------------------------------
short = gf.search_google_fonts("a", limit=3)
assert len(short) == 3, short
print("limit is honoured: OK")

# --- download: a real family returns real TrueType bytes -------------------------------
data = gf.download_google_font_file("Roboto Slab")
assert len(data) > 10_000, f"suspiciously small for a real font file: {len(data)} bytes"
# TrueType/OpenType files start with one of a small set of real magic numbers.
assert data[:4] in (b"\x00\x01\x00\x00", b"OTTO", b"true", b"ttcf"), data[:4]
print(f"download_google_font_file('Roboto Slab'): {len(data)} real bytes, valid font magic: OK")

# --- download: a nonexistent family raises ValueError, not a silent empty/garbage result -
try:
    gf.download_google_font_file("Definitely Not A Real Google Font XYZ123")
except ValueError as e:
    assert "Definitely Not A Real Google Font XYZ123" in str(e), str(e)
    print("a nonexistent family raises ValueError naming it: OK")
else:
    raise AssertionError("downloading a font Google does not have must raise, not succeed")

# --- the metadata cache is real: a second search is fast and does not re-fetch ---------
import time
start = time.monotonic()
gf.search_google_fonts("Open Sans")
cached_elapsed = time.monotonic() - start
assert cached_elapsed < 1.0, f"second search took {cached_elapsed:.2f}s -- cache is not working"
print(f"cached search took {cached_elapsed*1000:.0f}ms (metadata reused, not refetched): OK")

print("\nGoogle Fonts search/download: all assertions passed.")
