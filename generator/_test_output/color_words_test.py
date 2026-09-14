"""color_words.py: CSS named-color resolution, real spec values + light/dark HSL
fallback for combinations CSS itself doesn't name."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import color_words  # noqa: E402

# --- exact real CSS names -------------------------------------------------------------
assert color_words.resolve_color_phrase("navy") == "#000080"
assert color_words.resolve_color_phrase("white") == "#ffffff"
assert color_words.resolve_color_phrase("Orange") == "#ffa500"  # case-insensitive
print("exact CSS named colors resolve to their real spec hex: OK")

# --- a real CSS name that IS "modifier + base" already has its own EXACT hex, --------
# --- not a computed one -- "dark blue" -> darkblue's real value, not blue darkened ----
assert color_words.resolve_color_phrase("dark blue") == color_words.CSS_COLORS["darkblue"]
assert color_words.resolve_color_phrase("dark blue") != color_words.adjust_lightness(
    color_words.CSS_COLORS["blue"], -0.20)
print("a real 'darkX' CSS name wins over computing one: OK")

# --- a combination CSS has no distinct name for falls back to HSL adjustment ---------
computed = color_words.resolve_color_phrase("dark yellow")
assert computed is not None and computed != color_words.CSS_COLORS["yellow"]
assert "darkyellow" not in color_words.CSS_COLORS  # confirms this really is the fallback path
print("a combination with no real CSS name computes a darkened/lightened value: OK")

light_gray = color_words.resolve_color_phrase("light gray")
assert light_gray == color_words.CSS_COLORS["lightgray"]  # this one DOES have a real name
print("'light gray' correctly resolves to the real lightgray, not a computed one: OK")

# --- unknown words resolve to None, never a guess -------------------------------------
assert color_words.resolve_color_phrase("cromulent") is None
assert color_words.resolve_color_phrase("") is None
print("an unrecognized color word resolves to None rather than guessing: OK")

# --- adjust_lightness clamps rather than overflowing ----------------------------------
assert color_words.adjust_lightness("#000000", -0.5) == "#000000"  # already black, can't go darker
assert color_words.adjust_lightness("#ffffff", 0.5) == "#ffffff"  # already white, can't go lighter
print("adjust_lightness clamps at the extremes instead of wrapping/erroring: OK")

print("\nColor words: all assertions passed.")
