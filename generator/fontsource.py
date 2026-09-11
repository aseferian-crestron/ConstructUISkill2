"""Search and download real font FILES from Fontsource -- the second "go find me a
font" source, added at the user's direction with one deliberate restriction.

**Only the fonts genuinely NOT already reachable through `google_fonts.py`.**
Fontsource's own catalog (2,100 fonts as of this writing) is `{"type": "google", ...}`
for 1,980 of them -- literal duplicates of the same Google Fonts `google_fonts.py`
already searches, just re-served through Fontsource's own CDN. Only 120 carry
`"type": "other"`: real fonts (checked several licenses -- OFL-1.1, Apache-2.0,
CC0-1.0, all real open licenses) that Fontsource hosts and Google Fonts does not. The
user's own call, once that overlap was measured: "if they are duplicates of Google
Fonts no reason to add this." `search_fontsource` filters to exactly that 120-ish
subset, so a caller never gets a duplicate result from two different "sources" for
the same actual font.

**Two endpoints, both verified live (2026-09-11), neither needing an API key:**

1. `https://api.fontsource.org/v1/fonts` -- the full catalog, including each entry's
   `type` (`"google"` vs `"other"`), `weights`, `styles`, `subsets`, `license`.
2. `https://cdn.jsdelivr.net/fontsource/fonts/<id>@latest/<subset>-<weight>-<style>.ttf`
   -- jsDelivr (a well-known, stable public CDN for npm packages) serving Fontsource's
   own published font files directly. Verified against both a Google-type font
   (Roboto, 45,080 bytes) and an "other"-type one (Adwaita Sans, 513,028 bytes) --
   though the latter is filtered OUT of this module's search results by the
   no-duplicates rule above, the download path itself works identically either way.

Same independence rule as `google_fonts.py`: this module makes network calls and does
not import `fonts.py` (or vice versa); composing search -> download -> install is the
skill layer's job, proven to compose cleanly in
`_test_output/fonts_find_and_install_test.py`.
"""
from __future__ import annotations

import urllib.error
import urllib.request

FONTS_URL = "https://api.fontsource.org/v1/fonts"
CDN_URL = "https://cdn.jsdelivr.net/fontsource/fonts"
USER_AGENT = "Mozilla/5.0"

#: In-process cache, same reasoning as google_fonts.py's: ~540KB as of this writing,
#: no reason to refetch per search within one run. Never written to disk.
_catalog_cache: list[dict] | None = None


def _get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=15) as response:
        return response.read()


def _catalog() -> list[dict]:
    """The full Fontsource catalog, fetched once per process and cached -- see
    `_UNIQUE_ONLY` for why callers should use `_unique_catalog()` instead of this
    directly for anything user-facing."""
    global _catalog_cache
    if _catalog_cache is not None:
        return _catalog_cache

    import json

    try:
        entries = json.loads(_get(FONTS_URL))
    except (urllib.error.URLError, TimeoutError) as e:
        raise RuntimeError(f"could not reach Fontsource to search ({e})") from e
    except (json.JSONDecodeError, TypeError) as e:
        raise RuntimeError(
            f"Fontsource's catalog endpoint returned something this code does not "
            f"recognize -- its shape may have changed. ({e})") from e

    if not entries:
        raise RuntimeError("Fontsource's catalog endpoint returned zero fonts -- "
                           "that is not a real catalog state, treat as unreachable")
    _catalog_cache = entries
    return entries


def _unique_catalog() -> list[dict]:
    """The catalog filtered to fonts NOT also available via Google Fonts (`type` !=
    `"google"`) -- what `search_fontsource` actually searches. Kept as its own
    function so the exclusion rule is visible and testable on its own, not buried
    inside the search/ranking logic."""
    return [entry for entry in _catalog() if entry.get("type") != "google"]


def search_fontsource(query: str, *, limit: int = 10) -> list[str]:
    """Real Fontsource family names matching `query` (case-insensitive substring),
    EXCLUDING anything also available via Google Fonts (see module docstring) --
    ranked exact match, then starts-with, then contains, same convention as
    `google_fonts.search_google_fonts`. Empty list means no unique match (the query
    may still exist as a Google-duplicated font; that is `google_fonts`'s job to
    find). Querying the catalog itself failing raises, same distinction as
    `search_google_fonts`.
    """
    query_lower = query.strip().lower()
    if not query_lower:
        return []

    def rank(family: str) -> tuple[int, str]:
        lowered = family.lower()
        if lowered == query_lower:
            tier = 0
        elif lowered.startswith(query_lower):
            tier = 1
        else:
            tier = 2
        return (tier, family)

    matches = [entry["family"] for entry in _unique_catalog()
              if query_lower in entry["family"].lower()]
    return sorted(matches, key=rank)[:limit]


def _entry_for_family(family_name: str) -> dict:
    for entry in _unique_catalog():
        if entry["family"] == family_name:
            return entry
    raise ValueError(
        f"{family_name!r} is not a Fontsource family that is unique from Google "
        f"Fonts -- either it does not exist, or it is a Google-duplicated font (see "
        f"google_fonts.py instead)")


def download_fontsource_file(family_name: str, *, weight: int = 400,
                             style: str = "normal", subset: str | None = None) -> bytes:
    """The real font file bytes for `family_name` (an EXACT match from
    `search_fontsource` -- this does not itself search), downloaded from Fontsource's
    own CDN. `weight`/`style`/`subset` must be values the font actually publishes
    (checked against its catalog entry before requesting anything); `subset` defaults
    to the font's own `defSubset`.

    Raises ValueError for an unknown family, or a weight/style/subset the font does
    not actually have (checked locally against the catalog, not discovered via a
    failed download) -- listing the real, valid choices in the error. Raises
    RuntimeError if the CDN request itself fails.
    """
    entry = _entry_for_family(family_name)
    if weight not in entry["weights"]:
        raise ValueError(f"{family_name!r} has no weight {weight} -- "
                         f"valid: {entry['weights']}")
    if style not in entry["styles"]:
        raise ValueError(f"{family_name!r} has no style {style!r} -- "
                         f"valid: {entry['styles']}")
    subset = subset or entry["defSubset"]
    if subset not in entry["subsets"]:
        raise ValueError(f"{family_name!r} has no subset {subset!r} -- "
                         f"valid: {entry['subsets']}")

    url = f"{CDN_URL}/{entry['id']}@latest/{subset}-{weight}-{style}.ttf"
    try:
        return _get(url)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Fontsource's CDN returned HTTP {e.code} for {family_name!r} "
                           f"({subset}-{weight}-{style})") from e
    except (urllib.error.URLError, TimeoutError) as e:
        raise RuntimeError(f"could not download {family_name!r} from Fontsource's CDN ({e})") from e


if __name__ == "__main__":
    import sys

    query = sys.argv[1] if len(sys.argv) > 1 else "Adwaita"
    matches = search_fontsource(query)
    print(f"{len(matches)} Fontsource-unique matches for {query!r}: {matches}")
    if matches:
        data = download_fontsource_file(matches[0])
        print(f"downloaded {matches[0]!r}: {len(data)} bytes")
