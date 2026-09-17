"""layout_patterns.py::build_tabbed_shell -- the Tabbed layout pattern's
navigational shell (Phase 1: splash->main-panel, tab strip <-> per-mode
content-swap widgets, 3-zone footer, one real modal). See
docs/superpowers/specs/2026-09-17-tabbed-layout-commercial-design.md."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))

import compare  # noqa: E402
import layout  # noqa: E402
import sdk as sdk_module  # noqa: E402
from layout_patterns import build_tabbed_shell  # noqa: E402
from page import write_cuig  # noqa: E402

ui_sdk = sdk_module.read_sdk("2.18.0")
OUT = Path(__file__).resolve().parent / "TabbedShell"
OUT.mkdir(parents=True, exist_ok=True)

result = build_tabbed_shell(
    ui_sdk, room_name="Boardroom A",
    splash_tiles=[("Join Video Call", "fa-solid fa-video"), ("Join Audio Call", "fa-solid fa-phone")],
    additional_system_modes=["Presentation", "Video Call", "Audio Call"],
    subsystems=["Environment", "Audio", "Camera"],
    camera_presets=["Wide", "Speaker Track", "Presenter"],
    panel_width=1280, panel_height=800,
)

# --- System Power is always first, ahead of the caller-supplied modes --------------
splash_attrs, splash_html, splash_css, splash_elements = result["splash_page"]
main_attrs, main_html, main_css, main_elements = result["main_panel_page"]
tab_content_widgets = result["tab_content_widgets"]
assert list(tab_content_widgets.keys()) == ["System Power", "Presentation", "Video Call", "Audio Call"]
print("build_tabbed_shell: 'System Power' is always the first system mode: OK")

# --- header: tab strip carries every mode's own label -------------------------------
header_widget_id, header_attrs, header_html, header_css, header_elements = result["header_widget"]
for mode in tab_content_widgets:
    assert f'labelinnerhtml="{mode}"' in header_html
assert "<ch5-datetime " in header_html
assert "<ch5-image " in header_html
print("build_tabbed_shell: header carries room name, date/time, logo, and every mode's tab label: OK")

# --- header: the room-name/date-time stack must not overlap the tab strip below it -
# (real geometry check, not just string presence -- this is the class of bug that
# slipped through review once already: the stack's height budget must account for
# the top EDGE_PADDING inset it's actually drawn at, not just its own content)
header_rects = layout.parse_all_position_rules(header_css, "(max-width: 99999px)")
datetime_id = dict(header_elements[2].attributes)["id"]
tab_strip_id = dict(header_elements[4].attributes)["id"]
datetime_rect = header_rects[datetime_id]
tab_strip_rect = header_rects[tab_strip_id]
assert datetime_rect["top"] + datetime_rect["height"] <= tab_strip_rect["top"], (
    f"date/time (bottom={datetime_rect['top'] + datetime_rect['height']}) must not "
    f"overlap the tab strip (top={tab_strip_rect['top']}) below it"
)
print("build_tabbed_shell: date/time stack doesn't overlap the tab strip below it: OK")

# --- footer: one button per subsystem + Privacy Mute + volume + mute ---------------
footer_widget_id, footer_attrs, footer_html, footer_css, footer_elements = result["footer_widget"]
for label in ["Environment", "Audio", "Camera"]:
    assert f'componentName="Footer {label}"' in footer_html
assert 'componentName="Privacy Mute"' in footer_html
assert "<ch5-slider " in footer_html  # volume
assert 'componentName="Volume Mute"' in footer_html
print("build_tabbed_shell: footer carries one button per subsystem, Privacy Mute, and volume+mute: OK")

# --- modals: Camera gets real content, everything else stays empty this phase ------
modal_widgets = result["modal_widgets"]
assert set(modal_widgets.keys()) == {"Environment", "Audio", "Camera"}
_, _, camera_modal_html, _, camera_modal_elements = modal_widgets["Camera"]
assert "<ch5-dpad " in camera_modal_html
_, _, environment_modal_html, _, environment_modal_elements = modal_widgets["Environment"]
assert "<ch5-dpad " not in environment_modal_html
# camera's modal has real content elements beyond the modal chrome itself; an empty
# modal has exactly the chrome (container + backdrop + dismiss + card + title + close)
assert len(camera_modal_elements) > len(environment_modal_elements)
print("build_tabbed_shell: Camera modal has real content, other modals stay empty this phase: OK")

# --- Main Panel page references every widget exactly once --------------------------
widget_ref_count = main_html.count("<ch5-template ")
expected_widgets = 2 + len(tab_content_widgets) + len(modal_widgets)  # header + footer + N tabs + N modals
assert widget_ref_count == expected_widgets, (widget_ref_count, expected_widgets)
print(f"build_tabbed_shell: Main Panel page references all {expected_widgets} widgets exactly once: OK")

# --- Main Panel page: real per-widget-reference position CSS (Fix 1 regression) -----
# main_elements' order matches widget_placements' own build order: header, footer,
# then each tab-content widget in dict order, then each modal in dict order.
main_rects = layout.parse_all_position_rules(main_css, "(max-width: 99999px)")
header_ref_id = dict(main_elements[0].attributes)["id"]
footer_ref_id = dict(main_elements[1].attributes)["id"]
n_tabs = len(tab_content_widgets)
tab_ref_ids = [dict(main_elements[2 + i].attributes)["id"] for i in range(n_tabs)]
modal_ref_ids = [dict(main_elements[2 + n_tabs + i].attributes)["id"] for i in range(len(modal_widgets))]

assert main_rects[header_ref_id]["top"] == 0
print("build_tabbed_shell: Main Panel's header widget reference is positioned at top=0: OK")

DEFAULT_FOOTER_HEIGHT = 120
DEFAULT_PANEL_HEIGHT = 800
assert main_rects[footer_ref_id]["top"] == DEFAULT_PANEL_HEIGHT - DEFAULT_FOOTER_HEIGHT
print("build_tabbed_shell: Main Panel's footer widget reference is positioned at "
      "top=panel_height-footer_height: OK")

DEFAULT_HEADER_HEIGHT = 160
for tab_ref_id in tab_ref_ids:
    assert main_rects[tab_ref_id]["top"] == DEFAULT_HEADER_HEIGHT
print("build_tabbed_shell: every tab-content widget reference is positioned at "
      "top=header_height: OK")

content_z = max(main_rects[header_ref_id]["z_index"], main_rects[footer_ref_id]["z_index"],
                 *(main_rects[tab_ref_id]["z_index"] for tab_ref_id in tab_ref_ids))
for modal_ref_id in modal_ref_ids:
    assert main_rects[modal_ref_id]["z_index"] > content_z
print("build_tabbed_shell: every modal widget reference has a higher z-index than "
      "the content layer (header/footer/tabs): OK")

# --- every page/widget round-trips byte-identical -----------------------------------
write_cuig(OUT / "Splash.cuig", splash_attrs, html=splash_html, css=splash_css, elements=splash_elements)
assert compare.round_trip_check(OUT / "Splash.cuig")
write_cuig(OUT / "MainPanel.cuig", main_attrs, html=main_html, css=main_css, elements=main_elements)
assert compare.round_trip_check(OUT / "MainPanel.cuig")
write_cuig(OUT / "Header.cuiw", header_attrs, html=header_html, css=header_css, elements=header_elements)
assert compare.round_trip_check(OUT / "Header.cuiw")
write_cuig(OUT / "Footer.cuiw", footer_attrs, html=footer_html, css=footer_css, elements=footer_elements)
assert compare.round_trip_check(OUT / "Footer.cuiw")
for mode, (wid, attrs, html, css, elements) in tab_content_widgets.items():
    path = OUT / f"Tab_{mode.replace(' ', '')}.cuiw"
    write_cuig(path, attrs, html=html, css=css, elements=elements)
    assert compare.round_trip_check(path), mode
for label, (wid, attrs, html, css, elements) in modal_widgets.items():
    path = OUT / f"Modal_{label}.cuiw"
    write_cuig(path, attrs, html=html, css=css, elements=elements)
    assert compare.round_trip_check(path), label
print("build_tabbed_shell: every page/widget round-trips byte-identical: OK")

# --- an empty subsystems list raises rather than building a footer with nothing ----
try:
    build_tabbed_shell(
        ui_sdk, room_name="Empty", splash_tiles=[], additional_system_modes=[],
        subsystems=[], camera_presets=[], panel_width=1280, panel_height=800,
    )
    raise AssertionError("expected ValueError for an empty subsystems list")
except ValueError:
    pass
print("build_tabbed_shell: an empty subsystems list raises ValueError: OK")

# --- "Cameras" (plural, matching the spec's own example) still gets real content ---
plural_result = build_tabbed_shell(
    ui_sdk, room_name="Boardroom B", splash_tiles=[], additional_system_modes=[],
    subsystems=["Environment", "Cameras"], camera_presets=["Wide", "Speaker Track"],
    panel_width=1280, panel_height=800,
)
plural_modal_widgets = plural_result["modal_widgets"]
_, _, plural_camera_modal_html, _, _ = plural_modal_widgets["Cameras"]
assert "<ch5-dpad " in plural_camera_modal_html
print("build_tabbed_shell: a plural 'Cameras' subsystem still gets real Camera content "
      "(case/pluralization-insensitive match): OK")

# --- camera_presets given with no Camera-like subsystem raises rather than silently -
# discarding them ---------------------------------------------------------------------
try:
    build_tabbed_shell(
        ui_sdk, room_name="No Camera", splash_tiles=[], additional_system_modes=[],
        subsystems=["Environment"], camera_presets=["Wide"], panel_width=1280, panel_height=800,
    )
    raise AssertionError("expected ValueError for camera_presets with no Camera-like subsystem")
except ValueError:
    pass
print("build_tabbed_shell: camera_presets given with no Camera-like subsystem raises "
      "ValueError instead of silently discarding them: OK")

print("Tabbed Shell: all assertions passed.")
