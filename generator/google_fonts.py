"""Search and download real font FILES from Google Fonts -- the "go find me a font"
half of Phase 8's font import feature.

Kept separate from `fonts.py`: that module manages font files already on disk (the
local webfont library, global-swap, validation); this module is the only thing in the
generator that makes a network call. Neither depends on the other.

**Two endpoints, both verified live (2026-09-11), neither needing an API key:**

1. `https://fonts.google.com/metadata/fonts` -- the full Google Fonts catalog, 1,946
   real family names as of this writing. This is what `search_google_fonts` matches
   against. **Not an official, documented API** -- it is what fonts.google.com's own
   website uses internally, discovered by inspection rather than published in Google's
   developer docs. It could change or disappear without notice; `search_google_fonts`
   raises a clear, distinguishable error if the response shape it expects is gone,
   rather than failing silently or crashing on a KeyError deep in the call stack.

   The DOCUMENTED alternative is the official Developer API
   (`https://developers.google.com/fonts/docs/developer_api`,
   `/webfonts/v1/webfonts?key=...&search=...`), which needs a Google API key the user
   would have to create and manage. Chosen against, with the user, in favor of zero
   setup -- worth revisiting if the metadata endpoint ever breaks.

2. `https://fonts.googleapis.com/css2?family=<name>` -- IS an official, documented,
   stable Google Fonts endpoint (this is literally what a `<link>` tag in any webpage
   using Google Fonts points at). Given an exact family name it returns CSS containing
   `@font-face { ... src: url(https://fonts.gstatic.com/.../Font.ttf) ... }`; this
   module downloads that real, direct file. A name Google does not have returns
   HTTP 400 with a "Font family not found" body -- a clean, detectable failure, not a
   silent empty response.
"""
from __future__ import annotations

import re
import urllib.error
import urllib.request

METADATA_URL = "https://fonts.google.com/metadata/fonts"
CSS_URL = "https://fonts.googleapis.com/css2"
#: Real browsers get real font data; Google's endpoints have been observed to behave
#: differently (or refuse) for an unrecognized/empty User-Agent.
USER_AGENT = "Mozilla/5.0"

#: In-process cache for the metadata response -- 2.7MB as of this writing, no reason to
#: refetch it for every search within one run. Never written to disk: font search
#: results are not something later runs need to reproduce exactly, unlike this
#: project's other caches (the installed SDK, the resolution catalog), which are.
_metadata_cache: list[str] | None = None


def _get(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=15) as response:
        return response.read().decode("utf-8")


def _all_family_names() -> list[str]:
    """Every Google Fonts family name, fetched once per process and cached."""
    global _metadata_cache
    if _metadata_cache is not None:
        return _metadata_cache

    import json

    try:
        payload = json.loads(_get(METADATA_URL))
        names = [entry["family"] for entry in payload["familyMetadataList"]]
    except (urllib.error.URLError, TimeoutError) as e:
        raise RuntimeError(f"could not reach Google Fonts to search ({e})") from e
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        raise RuntimeError(
            f"Google Fonts' metadata endpoint returned something this code does not "
            f"recognize -- it is an undocumented endpoint (see module docstring) and "
            f"may have changed shape. ({e})") from e

    if not names:
        raise RuntimeError("Google Fonts' metadata endpoint returned zero families -- "
                           "that is not a real catalog state, treat as unreachable")
    _metadata_cache = names
    return names


def search_google_fonts(query: str, *, limit: int = 10) -> list[str]:
    """Real Google Fonts family names matching `query` (case-insensitive substring),
    ranked exact match, then starts-with, then contains -- so searching "Roboto" puts
    the family literally named "Roboto" first, ahead of "Roboto Slab", "Roboto Mono",
    etc. Empty list means no match, not an error; querying the catalog itself failing
    (network down, endpoint changed shape) raises instead, since that is a different
    situation a caller needs to handle differently (retry / tell the user / fall back).
    """
    query_lower = query.strip().lower()
    if not query_lower:
        return []

    def rank(name: str) -> tuple[int, str]:
        lowered = name.lower()
        if lowered == query_lower:
            tier = 0
        elif lowered.startswith(query_lower):
            tier = 1
        else:
            tier = 2
        return (tier, name)

    matches = [name for name in _all_family_names() if query_lower in name.lower()]
    return sorted(matches, key=rank)[:limit]


def download_google_font_file(family_name: str) -> bytes:
    """The real `.ttf` bytes for `family_name`, downloaded from Google's own CDN via
    the official css2 endpoint. `family_name` must be an EXACT Google Fonts family
    name (as returned by `search_google_fonts`) -- this does not itself search.

    Raises ValueError if Google does not have this family (HTTP 400, "Font family not
    found" -- verified live against a real nonexistent name), or RuntimeError if the
    css2 response no longer contains a recognizable `url(...)` (same "endpoint shape
    changed" concern as the metadata call, though this one -- unlike metadata -- is
    Google's documented, stable API, so this should be rare).
    """
    url = f"{CSS_URL}?family={family_name.replace(' ', '+')}"
    try:
        css = _get(url)
    except urllib.error.HTTPError as e:
        if e.code == 400:
            raise ValueError(f"Google Fonts has no family named {family_name!r}") from e
        raise RuntimeError(f"Google Fonts returned HTTP {e.code} for {family_name!r}") from e
    except (urllib.error.URLError, TimeoutError) as e:
        raise RuntimeError(f"could not reach Google Fonts to download {family_name!r} ({e})") from e

    match = re.search(r"url\((https://fonts\.gstatic\.com/[^)]+)\)", css)
    if not match:
        raise RuntimeError(
            f"Google Fonts' css2 response for {family_name!r} did not contain a "
            f"recognizable font file URL -- response shape may have changed")
    font_url = match.group(1)

    try:
        return urllib.request.urlopen(
            urllib.request.Request(font_url, headers={"User-Agent": USER_AGENT}),
            timeout=30,
        ).read()
    except (urllib.error.URLError, TimeoutError) as e:
        raise RuntimeError(f"could not download the font file for {family_name!r} ({e})") from e


if __name__ == "__main__":
    import sys

    query = sys.argv[1] if len(sys.argv) > 1 else "Roboto"
    matches = search_google_fonts(query)
    print(f"{len(matches)} matches for {query!r}: {matches}")
    if matches:
        data = download_google_font_file(matches[0])
        print(f"downloaded {matches[0]!r}: {len(data)} bytes")
