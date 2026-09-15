import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from color_words import contrast_ratio

assert abs(contrast_ratio("#ffffff", "#000000") - 21.0) < 0.01, "white/black must be the maximum 21:1"
assert abs(contrast_ratio("#000000", "#ffffff") - 21.0) < 0.01, "order must not matter"
assert abs(contrast_ratio("#ffffff", "#ffffff") - 1.0) < 0.01, "identical colors must be the minimum 1:1"

# #767676 on white is the textbook "just barely passes AA normal text" gray (~4.54:1)
ratio = contrast_ratio("#767676", "#ffffff")
assert 4.5 <= ratio < 4.6, ratio
print(f"contrast_ratio: known WCAG reference pairs match (white/black=21:1, #767676/white={ratio:.2f}:1): OK")

print("Contrast ratio: all assertions passed.")
