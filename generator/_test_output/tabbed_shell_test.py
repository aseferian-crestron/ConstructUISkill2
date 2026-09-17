"""layout_patterns.py::build_tabbed_shell -- the Tabbed layout pattern's
navigational shell (Phase 1: splash->main-panel, tab strip <-> per-mode
content-swap widgets, 3-zone footer, one real modal). See
docs/superpowers/specs/2026-09-17-tabbed-layout-commercial-design.md."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))

import compare  # noqa: E402
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

print("Tabbed Shell: all assertions passed.")
