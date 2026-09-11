"""Phase 8 (fonts): Fontsource as a second "go find me a font" source -- restricted to
fonts genuinely NOT already reachable via google_fonts.py, per the user's own call once
the overlap was measured: "if they are duplicates of Google Fonts no reason to add
this." Verified against the real, live Fontsource API and CDN, not mocks -- same
standard as the Google Fonts module.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import fontsource as fs  # noqa: E402

# --- the exclusion rule is the whole point: verify it holds, not just trust the code --
matches = fs.search_fontsource("Adwaita")
assert "Adwaita Sans" in matches and "Adwaita Mono" in matches, matches
print(f"search('Adwaita') finds real Fontsource-unique fonts: {matches}: OK")

# A handful of real, common Google Fonts family names must return NOTHING here -- they
# are covered by google_fonts.py, and showing them again would be a duplicate result.
for google_family in ("Roboto", "Open Sans", "Lato", "Montserrat", "Poppins"):
    result = fs.search_fontsource(google_family)
    assert result == [], f"{google_family!r} is a Google Font and must not appear here: {result}"
print("common Google Fonts families are correctly excluded from Fontsource search: OK")

# --- ranking: exact match first, same convention as google_fonts.py -------------------
exact = fs.search_fontsource("Adwaita Sans")
assert exact and exact[0] == "Adwaita Sans", exact
print("exact match ranks first: OK")

# --- empty/no-match query behaves the same as google_fonts.py -------------------------
assert fs.search_fontsource("") == []
assert fs.search_fontsource("zzz-not-a-real-query-xyz123") == []
print("empty and no-match queries return [], not an error: OK")

# --- download: a real, unique-to-Fontsource family returns real bytes -----------------
data = fs.download_fontsource_file("Adwaita Sans")
assert len(data) > 10_000, f"suspiciously small: {len(data)} bytes"
assert data[:4] in (b"\x00\x01\x00\x00", b"OTTO", b"true", b"ttcf"), data[:4]
print(f"download_fontsource_file('Adwaita Sans'): {len(data)} real bytes, valid font magic: OK")

# --- download validates weight/style/subset against the font's REAL published values --
try:
    fs.download_fontsource_file("Adwaita Sans", weight=999)
except ValueError as e:
    assert "999" in str(e) and "100" in str(e), str(e)  # lists the real valid weights
    print("an unpublished weight is rejected, listing the real valid ones: OK")
else:
    raise AssertionError("weight 999 does not exist and must be rejected")

try:
    fs.download_fontsource_file("Adwaita Sans", style="handwriting")
except ValueError as e:
    assert "handwriting" in str(e), str(e)
    print("an unpublished style is rejected: OK")
else:
    raise AssertionError("style 'handwriting' does not exist and must be rejected")

# --- download refuses a Google-duplicated family, even if the caller names it exactly -
try:
    fs.download_fontsource_file("Roboto")
except ValueError as e:
    assert "Roboto" in str(e) and "Google" in str(e), str(e)
    print("downloading a Google-duplicated family via Fontsource is refused: OK")
else:
    raise AssertionError("'Roboto' is Google-sourced and must be refused here")

# --- download refuses a family that does not exist anywhere on Fontsource -------------
try:
    fs.download_fontsource_file("Definitely Not A Real Font Anywhere XYZ123")
except ValueError:
    print("a genuinely nonexistent family is rejected: OK")
else:
    raise AssertionError("a nonexistent family must be rejected")

# --- the catalog cache is real: a second search is fast --------------------------------
import time
start = time.monotonic()
fs.search_fontsource("Bagnard")
elapsed = time.monotonic() - start
assert elapsed < 1.0, f"second search took {elapsed:.2f}s -- cache is not working"
print(f"cached search took {elapsed*1000:.0f}ms: OK")

print("\nFontsource search/download: all assertions passed.")
