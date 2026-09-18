"""design_ideas_subsystem.py -- DESIGN IDEAS TEMPLATE ONLY subsystem popup
builder, entirely from scratch (no donor file read/cloned), values
transcribed from docs/DesignIdeasTemplate.md §2. Replaces the old v1
(C:\\ClaudeProjects\\ConstructUISkill\\design_ideas_subsystem.py) donor-
cloning implementation."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))

import compare  # noqa: E402
import sdk as sdk_module  # noqa: E402
from design_ideas_subsystem import (  # noqa: E402
    CONTROL_INSET, GROUP_WIDTH,
    design_ideas_build_subsystem_popup, design_ideas_button_list_group,
    design_ideas_dpad_group, design_ideas_keypad_group,
)
from page import write_cuig  # noqa: E402

ui_sdk = sdk_module.read_sdk("2.18.0")
OUT = Path(__file__).resolve().parent / "DesignIdeasSubsystem"
OUT.mkdir(parents=True, exist_ok=True)

widget_id, attrs, html, css, elements = design_ideas_build_subsystem_popup(
    ui_sdk, widget_name="Popup - Lights", title="Lights", icon_class="fa-solid fa-lightbulb",
    groups=[
        ("Zone 1", ["Full", "75%", "50%", "25%", "Off"]),
        ("Zone 2", ["Full", "75%", "50%", "25%", "Off"]),
    ],
    panel_width=1048, panel_height=590, resolution=(1280, 800),
)

assert "<ch5-button " in html
assert "<ch5-text " in html
assert 'componentName="Subsystem_Icon"' in html
assert 'componentName="Controls_Close"' in html
assert 'componentName="Subsystem_Title"' in html
assert 'labelinnerhtml="Lights"' in html
for label in ("Full", "75%", "50%", "25%", "Off"):
    assert f'componentName="{label}"' in html
print("design_ideas_build_subsystem_popup: header + both groups' controls present: OK")

# --- Element ORDER: real, confirmed live bug (2026-09-18) -- Construct's Layer -------
# Manager (and its actual click hit-testing) treats FIRST in the components list as
# FRONTMOST, not z-index alone -- a backdrop built first blocks everything drawn
# after it. Confirmed against the real `Popup - SubsystemTemplate.cuiw`'s own order:
# `Control, Group_Title, Group_Container, Controls_Close, Subsystem_Title,
# Subsystem_Icon, Container_Controls` -- content before its own group's container,
# and Container_Controls dead LAST overall.
component_order = [dict(e.attributes).get("componentName") for e in elements]
component_order = [n for n in component_order if n]
assert component_order.index("Full") < component_order.index("Group_Container_Zone 1"), component_order
assert component_order.index("Group_Container_Zone 1") < component_order.index("Controls_Close"), component_order
assert component_order[-1] == "Container_Controls", component_order
print("design_ideas_build_subsystem_popup: element order is front-to-back (content"
      " before its group container, Container_Controls dead last): OK")

# Group control buttons are THEME mode -- no custom background/border color written.
assert 'customvstheme="theme"' in html
print("design_ideas_build_subsystem_popup: group control buttons left in theme mode: OK")

path = OUT / "PopupLights.cuiw"
write_cuig(path, attrs, html=html, css=css, elements=elements)
assert compare.round_trip_check(path), "subsystem popup widget failed round-trip"
print("design_ideas_build_subsystem_popup: written .cuiw round-trips byte-identical: OK")

# --- too many groups for the panel width raises -------------------------------------
try:
    design_ideas_build_subsystem_popup(
        ui_sdk, widget_name="Popup - Wide", title="Wide", icon_class="fa-solid fa-lightbulb",
        groups=[("A", ["1"]), ("B", ["1"]), ("C", ["1"]), ("D", ["1"]), ("E", ["1"])],
        panel_width=1048, panel_height=590,
    )
    raise AssertionError("expected ValueError for groups too wide for the panel")
except ValueError:
    pass
print("design_ideas_build_subsystem_popup: too many groups for the panel width raises ValueError: OK")

# --- too many controls in one group for the panel height raises ---------------------
try:
    design_ideas_build_subsystem_popup(
        ui_sdk, widget_name="Popup - Tall", title="Tall", icon_class="fa-solid fa-lightbulb",
        groups=[("A", [str(i) for i in range(20)])],
        panel_width=1048, panel_height=590,
    )
    raise AssertionError("expected ValueError for a group too tall for the panel")
except ValueError:
    pass
print("design_ideas_build_subsystem_popup: too many controls for the panel height raises ValueError: OK")

# --- device_controls=True uses the wider 84x72 close button --------------------------
_, _, dc_html, _, _ = design_ideas_build_subsystem_popup(
    ui_sdk, widget_name="Device Controls - TV", title="TV", icon_class="fa-solid fa-tv",
    groups=[("Power", ["On", "Off"])], panel_width=1048, panel_height=590,
    device_controls=True,
)
assert "<ch5-button " in dc_html
print("design_ideas_build_subsystem_popup: device_controls=True builds without error: OK")

# --- D-pad group: 5-button cross + background, distinct from a plain button list ----
_, _, dpad_html, dpad_css, _ = design_ideas_build_subsystem_popup(
    ui_sdk, widget_name="Popup - Apple TV", title="Apple TV", icon_class="fa-solid fa-tv",
    groups=[("Navigation", design_ideas_dpad_group())],
    panel_width=1048, panel_height=590, resolution=(1280, 800),
)
for key in ("Up", "Down", "Left", "Right", "Ok"):
    assert f'componentName="Dpad_{key}"' in dpad_html
assert 'componentName="Dpad_Background"' in dpad_html
assert 'shape="custom"' in dpad_html  # apply_radius_px flips shape to custom
print("design_ideas_build_subsystem_popup: DpadGroup builds all 5 cross buttons + background: OK")

dpad_id, dpad_attrs, dpad_html, dpad_css, dpad_elements = design_ideas_build_subsystem_popup(
    ui_sdk, widget_name="Popup - Apple TV", title="Apple TV", icon_class="fa-solid fa-tv",
    groups=[("Navigation", design_ideas_dpad_group())],
    panel_width=1048, panel_height=590, resolution=(1280, 800),
)
path = OUT / "PopupAppleTV.cuiw"
write_cuig(path, dpad_attrs, html=dpad_html, css=dpad_css, elements=dpad_elements)
assert compare.round_trip_check(path), "D-pad popup failed round-trip"
print("design_ideas_build_subsystem_popup: DpadGroup round-trips: OK")

# --- Button-list group: single ch5-button-list, sized to num_items -------------------
_, _, list_html, _, _ = design_ideas_build_subsystem_popup(
    ui_sdk, widget_name="Popup - Recordings", title="Recordings", icon_class="fa-solid fa-video",
    groups=[("Recordings", design_ideas_button_list_group(6))],
    panel_width=1048, panel_height=590,
)
assert '<ch5-button-list ' in list_html
assert 'numberofitems="6"' in list_html
print("design_ideas_build_subsystem_popup: ButtonListGroup builds a sized ch5-button-list: OK")

# --- Keypad group: native ch5-keypad, optional display ------------------------------
_, _, keypad_html, _, _ = design_ideas_build_subsystem_popup(
    ui_sdk, widget_name="Popup - Gate", title="Gate", icon_class="fa-solid fa-door-closed",
    groups=[("Code Entry", design_ideas_keypad_group(display=True))],
    panel_width=1048, panel_height=590,
)
assert '<ch5-keypad ' in keypad_html
assert 'componentName="Keypad_Display"' in keypad_html
print("design_ideas_build_subsystem_popup: KeypadGroup builds ch5-keypad + display: OK")

_, _, keypad_no_display_html, _, _ = design_ideas_build_subsystem_popup(
    ui_sdk, widget_name="Popup - Gate2", title="Gate", icon_class="fa-solid fa-door-closed",
    groups=[("Code Entry", design_ideas_keypad_group())],
    panel_width=1048, panel_height=590,
)
assert 'componentName="Keypad_Display"' not in keypad_no_display_html
print("design_ideas_build_subsystem_popup: KeypadGroup(display=False) omits the display: OK")

# --- Message: warning/alert dialog shape (header + message + Close, no groups) ------
_, _, msg_html, msg_css, _ = design_ideas_build_subsystem_popup(
    ui_sdk, widget_name="Popup - Warning", title="Warning", icon_class="fa-solid fa-triangle-exclamation",
    groups=[], panel_width=1048, panel_height=590,
    message="Message text will appear here.",
)
assert 'componentName="Message"' in msg_html
assert 'labelinnerhtml="Message text will appear here."' in msg_html
print("design_ideas_build_subsystem_popup: message= builds a warning-dialog Message element: OK")

no_msg_widget_id, no_msg_attrs, no_msg_html, no_msg_css, no_msg_elements = design_ideas_build_subsystem_popup(
    ui_sdk, widget_name="Popup - NoMessage", title="No Message", icon_class="fa-solid fa-tv",
    groups=[("Power", ["On", "Off"])], panel_width=1048, panel_height=590,
)
assert 'componentName="Message"' not in no_msg_html
print("design_ideas_build_subsystem_popup: message=None (default) omits the Message element: OK")

path = OUT / "PopupWarning.cuiw"
w_id, w_attrs, w_html, w_css, w_elements = design_ideas_build_subsystem_popup(
    ui_sdk, widget_name="Popup - Warning", title="Warning", icon_class="fa-solid fa-triangle-exclamation",
    groups=[], panel_width=1048, panel_height=590,
    message="Message text will appear here.",
)
write_cuig(path, w_attrs, html=w_html, css=w_css, elements=w_elements)
assert compare.round_trip_check(path), "warning dialog popup failed round-trip"
print("design_ideas_build_subsystem_popup: warning dialog (groups=[], message=...) round-trips: OK")

# --- Group_Container sized to CONTENT, not the popup's full available height -------
# Real live bug, 2026-09-18: a screenshot of a real "Pool" popup (4-button "Pool"
# group beside a 2-button "Filter" group) showed BOTH group boxes stretched to the
# popup's full height regardless of actual control count, leaving a large empty band
# below the real content in both.
import re as _re  # noqa: E402
_, _, sized_html, sized_css, sized_elements = design_ideas_build_subsystem_popup(
    ui_sdk, widget_name="Popup - Pool", title="Pool", icon_class="fa-solid fa-water",
    groups=[
        ("Pool", ["Pump On", "Pump Off", "Heater On", "Heater Off"]),
        ("Filter", ["Start Cycle", "Stop Cycle"]),
    ],
    panel_width=1048, panel_height=590,
)
heights = {}
for el in sized_elements:
    d = dict(el.attributes)
    name = d.get("componentName", "")
    if name.startswith("Group_Container_"):
        m = _re.search(r"#" + _re.escape(d["id"]) + r"\{[^{}]*height:\s*([0-9]+)px", sized_css)
        heights[name] = int(m.group(1))
assert heights["Group_Container_Pool"] == 367, heights  # 17 + (3*86+75) + 17
assert heights["Group_Container_Filter"] == 195, heights  # 17 + (1*86+75) + 17
assert heights["Group_Container_Pool"] != heights["Group_Container_Filter"]
print("design_ideas_build_subsystem_popup: Group_Container height fits each group's own"
      " content, not the popup's full available height: OK")

# --- Plain-list buttons EXPAND to fill their group's width, symmetric margin -------
# Real live bug, 2026-09-18: a screenshot of the same real "Pool" popup showed each
# button at a fixed width, leaving a large, uneven gap on the RIGHT only (left margin
# -- CONTROL_INSET -- was already correct).
pool_group_width = GROUP_WIDTH  # both groups here use the standard slot
button_widths = set()
for el in sized_elements:
    d = dict(el.attributes)
    if d.get("componentName") in ("Pump On", "Start Cycle"):
        m = _re.search(r"#" + _re.escape(d["id"]) + r"\{[^{}]*width:\s*([0-9]+)px", sized_css)
        button_widths.add(int(m.group(1)))
assert button_widths == {pool_group_width - 2 * CONTROL_INSET}, button_widths
print("design_ideas_build_subsystem_popup: plain-list buttons expand to fill their"
      " group width with a symmetric CONTROL_INSET margin on both sides: OK")

# --- control_icons: single-component icon+label, halignlabel left at its default ---
# (center) so the icon+label PAIR centers together -- a real live bug: an earlier
# version used the icon's own `margin-left` to try to move it independently of the
# label, but a real screenshot showed that drags the label along too (flush left,
# not centered) -- corrected to `apply_icon_gap` (icon-to-label spacing, `margin-
# right` on the icon) instead, with no halignlabel/margin-left override at all.
_, _, icon_html, icon_css, icon_elements = design_ideas_build_subsystem_popup(
    ui_sdk, widget_name="Popup - Pool Icons", title="Pool", icon_class="fa-solid fa-water",
    groups=[("Pool", ["Pump On", "Pump Off"])],
    panel_width=1048, panel_height=590,
    control_icons={"Pump On": "fa-solid fa-toggle-on"},
)
assert 'iconclass="fa-solid fa-toggle-on"' in icon_html
assert "halignlabel=\"left\"" not in icon_html  # label(s) never re-aligned
on_id = next(dict(e.attributes)["id"] for e in icon_elements
             if dict(e.attributes).get("componentName") == "Pump On")
assert _re.search(r"#" + _re.escape(on_id) + r"\{[^{}]*icon-margin-right:\s*[0-9]+px", icon_css), \
    "expected a real icon-to-label gap (margin-right) for Pump On"
assert not _re.search(r"#" + _re.escape(on_id) + r"\{[^{}]*icon-margin-left", icon_css)
# Pump Off has no entry in control_icons -- no icon, no gap written at all.
off_id = next(dict(e.attributes)["id"] for e in icon_elements
              if dict(e.attributes).get("componentName") == "Pump Off")
assert not _re.search(r"#" + _re.escape(off_id) + r"\{[^{}]*icon-margin", icon_css)
print("design_ideas_build_subsystem_popup: control_icons= builds icon+label in one"
      " component for only the labels given, icon-label gap via margin-right,"
      " halignlabel left at its default so the pair centers together, others"
      " unaffected: OK")

# --- Fixed header title width (TITLE_WIDTH, not stretched to the close button) ------
from design_ideas_subsystem import TITLE_WIDTH  # noqa: E402
assert f'width:{TITLE_WIDTH}px' in css or f'width: {TITLE_WIDTH}px' in css
print("design_ideas_build_subsystem_popup: header title uses the real fixed TITLE_WIDTH: OK")

print("Design Ideas Subsystem: all assertions passed.")
