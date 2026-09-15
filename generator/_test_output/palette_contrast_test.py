import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from palette import check_contrast

# White text on Cornell Carnelian red -- the real palette from this project's live
# Cornell theming session (README.md, 2026-09-13 entry). Passes AA normal text.
passing = {"background_color": "#B31B1B", "text_color": "#FFFFFF"}
ok, ratio = check_contrast(passing)
assert ok is True and ratio >= 4.5, (ok, ratio)
print(f"check_contrast: white on Cornell Carnelian passes AA normal text ({ratio:.2f}:1): OK")

# Near-white text on white -- a real failure case, must report False with its actual ratio.
failing = {"background_color": "#FFFFFF", "text_color": "#F7F7F7"}
ok2, ratio2 = check_contrast(failing)
assert ok2 is False and ratio2 < 4.5, (ok2, ratio2)
print(f"check_contrast: near-white text on white correctly fails AA ({ratio2:.2f}:1): OK")

# A palette missing either key can't be checked -- must return (None, None) rather
# than raise or silently assume a default color.
incomplete = {"background_color": "#B31B1B"}
assert check_contrast(incomplete) == (None, None)
print("check_contrast: missing background_color or text_color returns (None, None): OK")

print("Palette contrast check: all assertions passed.")
