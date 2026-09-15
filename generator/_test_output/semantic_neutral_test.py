import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from color_words import _relative_luminance
from palette import SEMANTIC_COLORS, NEUTRAL_SCALE

# --- SEMANTIC_COLORS: fixed status-color convention, 4 distinct keys -------------------
assert set(SEMANTIC_COLORS) == {"success", "warning", "error", "info"}, SEMANTIC_COLORS
for key, value in SEMANTIC_COLORS.items():
    assert value.startswith("#") and len(value) == 7, (key, value)
assert len(set(SEMANTIC_COLORS.values())) == 4, "all 4 semantic colors must be distinct"
print(f"SEMANTIC_COLORS: 4 distinct valid hex values: {SEMANTIC_COLORS}: OK")

# --- NEUTRAL_SCALE: 3 grays, ordered light -> mid -> dark by real luminance ------------
assert set(NEUTRAL_SCALE) == {"neutral_light", "neutral_mid", "neutral_dark"}, NEUTRAL_SCALE
light_lum = _relative_luminance(NEUTRAL_SCALE["neutral_light"])
mid_lum = _relative_luminance(NEUTRAL_SCALE["neutral_mid"])
dark_lum = _relative_luminance(NEUTRAL_SCALE["neutral_dark"])
assert light_lum > mid_lum > dark_lum, (light_lum, mid_lum, dark_lum)
print(f"NEUTRAL_SCALE: light > mid > dark by real relative luminance: {NEUTRAL_SCALE}: OK")

print("Semantic + neutral colors: all assertions passed.")
