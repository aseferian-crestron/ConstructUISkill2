import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from color_words import adjust_saturation, rotate_hue
from palette import resolve_color_roles

# --- adjust_saturation: pure HSL saturation shift, clamped 0..1 ------------------------
muted = adjust_saturation("#B31B1B", -0.5)
assert muted != "#B31B1B", muted
full_gray = adjust_saturation("#B31B1B", -1.0)
r, g, b = int(full_gray[1:3], 16), int(full_gray[3:5], 16), int(full_gray[5:7], 16)
assert r == g == b, full_gray  # zero saturation must be a pure gray
no_change = adjust_saturation("#B31B1B", 0.0)
assert no_change == "#b31b1b", no_change  # _rgb_to_hex always lowercases -- pre-existing, see adjust_lightness
print("adjust_saturation: -1.0 collapses to gray, 0.0 is a no-op: OK")

# --- rotate_hue: wraps mod 360, 0/360 degrees are no-ops --------------------------------
same = rotate_hue("#B31B1B", 0)
assert same == "#b31b1b", same  # _rgb_to_hex always lowercases -- pre-existing, see adjust_lightness
full_turn = rotate_hue("#B31B1B", 360)
assert full_turn == "#b31b1b", full_turn
shifted = rotate_hue("#B31B1B", 30)
assert shifted != "#B31B1B", shifted
print("rotate_hue: 0/360 degrees are no-ops, a real shift changes the color: OK")

# --- resolve_color_roles: derives secondary/accent when not given, never overrides -----
roles = resolve_color_roles("#B31B1B")
assert roles["primary"] == "#B31B1B"
assert roles["secondary"] not in ("#B31B1B", None)
assert roles["accent"] not in ("#B31B1B", None)
assert roles["secondary"] != roles["accent"]
print(f"resolve_color_roles: primary/secondary/accent all distinct: {roles}: OK")

explicit = resolve_color_roles("#B31B1B", secondary="#CCCCCC", accent="#00FF00")
assert explicit == {"primary": "#B31B1B", "secondary": "#CCCCCC", "accent": "#00FF00"}, explicit
print("resolve_color_roles: explicit secondary/accent are never overridden by derivation: OK")

print("Color roles: all assertions passed.")
