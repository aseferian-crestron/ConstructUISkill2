"""design_ideas_subsystem.py::design_ideas_footer_layout -- the real footer
subsystem-icon group/divider reflow rhythm, transcribed directly from
C:\\Solutions\\ClaudeGenTest\\DesignIdeasCopy\\Footer - Main.cuiw's own
catch-all CSS (every constant is a direct measurement, not a guess)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from design_ideas_subsystem import (  # noqa: E402
    design_ideas_footer_layout, design_ideas_footer_layout_portrait, FOOTER_DEFAULT_GROUPS,
)

# --- the template's own real, unmodified default groups reproduce the real ---------
# measured x positions EXACTLY (Menu_Power=10, DividerGroup1=107, Menu_Lights=120,
# Menu_Shades=213, DividerGroup2=310, Menu_Camera=323, Menu_Phone=416,
# Menu_VideoCall=509, DividerGroup3=606, Menu_Audio=619 -- DividerGroup4/
# Privacy_Mute are Privacy_Mute's own concern, not a subsystem group, so this
# function doesn't place them; a caller positions Privacy_Mute at wherever this
# layout's own last entry ends + FOOTER_GROUP_GAP + FOOTER_DIVIDER_WIDTH +
# FOOTER_GROUP_GAP, same rhythm).
REAL_POSITIONS = {
    "Power": 10, "DividerGroup1": 107, "Lights": 120, "Shades": 213,
    "DividerGroup2": 310, "Camera": 323, "Phone": 416, "VideoCall": 509,
    "DividerGroup3": 606, "Audio": 619,
}
layout = design_ideas_footer_layout(FOOTER_DEFAULT_GROUPS)
computed = {name: x for name, _kind, x in layout}
assert computed == REAL_POSITIONS, (computed, REAL_POSITIONS)
print("design_ideas_footer_layout: default groups reproduce the real measured positions exactly: OK")

# --- removing one item from a multi-item group closes the gap, later groups shift --
groups = [["Power"], ["Lights"], ["Camera", "Phone", "VideoCall"], ["Audio"]]  # Shades removed
computed = {name: x for name, _kind, x in design_ideas_footer_layout(groups)}
expected = {
    "Power": 10, "DividerGroup1": 107, "Lights": 120,
    "DividerGroup2": 217, "Camera": 230, "Phone": 323, "VideoCall": 416,
    "DividerGroup3": 513, "Audio": 526,
}
assert computed == expected, (computed, expected)
print("design_ideas_footer_layout: removing one item from a group closes the gap correctly: OK")

# --- removing an ENTIRE group (both its items) leaves no orphan divider -------------
groups = [["Power"], [], ["Camera", "Phone", "VideoCall"], ["Audio"]]  # Environment emptied
computed = {name: x for name, _kind, x in design_ideas_footer_layout(groups)}
expected = {
    "Power": 10, "DividerGroup1": 107,
    "Camera": 120, "Phone": 213, "VideoCall": 306,
    "DividerGroup2": 403, "Audio": 416,
}
assert computed == expected, (computed, expected)
assert len([1 for name, kind, _ in design_ideas_footer_layout(groups) if kind == "divider"]) == 2
print("design_ideas_footer_layout: removing an entire group leaves no orphan divider "
      "(divider count drops from 3 to 2): OK")

# --- adding an item to a group shifts everything after it, using the same rhythm ---
groups = [["Power"], ["Lights", "Shades", "Fan"], ["Camera", "Phone", "VideoCall"], ["Audio"]]
computed = {name: x for name, _kind, x in design_ideas_footer_layout(groups)}
assert computed["Fan"] == 213 + 87 + 6  # right after Shades, within-group gap
assert computed["DividerGroup2"] == computed["Fan"] + 87 + 10
print("design_ideas_footer_layout: adding an item to a group extends it with the same rhythm: OK")

# --- a single-group project (no dividers at all) -------------------------------------
computed = list(design_ideas_footer_layout([["Power"]]))
assert computed == [("Power", "button", 10)]
print("design_ideas_footer_layout: a single group produces zero dividers: OK")

# --- PORTRAIT: structurally different (vertical stack, rotated divider, its own --
# gap rhythm) -- default groups reproduce the real measured portrait y positions ---
# exactly too (DividerGroup1's own gap is 10px, every other gap is 12px -- a real,
# confirmed one-time quirk in the original template, not noise).
REAL_PORTRAIT_POSITIONS = {
    "Power": 14, "DividerGroup1": 94, "Lights": 109, "Shades": 191,
    "DividerGroup2": 273, "Camera": 288, "Phone": 370, "VideoCall": 452,
    "DividerGroup3": 534, "Audio": 549,
}
computed = {name: y for name, _kind, y in design_ideas_footer_layout_portrait(FOOTER_DEFAULT_GROUPS)}
assert computed == REAL_PORTRAIT_POSITIONS, (computed, REAL_PORTRAIT_POSITIONS)
print("design_ideas_footer_layout_portrait: default groups reproduce the real measured "
      "portrait positions exactly: OK")

# Privacy_Mute/DividerGroup4 are never produced by this function (left fixed,
# per the user's explicit decision) -- confirmed absent regardless of groups.
names = {name for name, _kind, _y in design_ideas_footer_layout_portrait(FOOTER_DEFAULT_GROUPS)}
assert "Privacy_Mute" not in names and "DividerGroup4" not in names
print("design_ideas_footer_layout_portrait: Privacy_Mute/DividerGroup4 never produced "
      "(left fixed, not reflowed): OK")

# removing an item in portrait closes the gap correctly too (direction differs from
# landscape -- y increases downward -- but the same edge-case discipline applies).
groups = [["Power"], ["Lights"], ["Camera", "Phone", "VideoCall"], ["Audio"]]  # Shades removed
computed = {name: y for name, _kind, y in design_ideas_footer_layout_portrait(groups)}
expected = {
    "Power": 14, "DividerGroup1": 94, "Lights": 109,
    "DividerGroup2": 191, "Camera": 206, "Phone": 288, "VideoCall": 370,
    "DividerGroup3": 452, "Audio": 467,
}
assert computed == expected, (computed, expected)
print("design_ideas_footer_layout_portrait: removing one item from a group closes the gap: OK")

print("Design Ideas Footer Layout: all assertions passed.")
