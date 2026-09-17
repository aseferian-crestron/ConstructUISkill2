"""camera_control.py -- the Camera subsystem-control composite (subsystem-
control tier): PTZ dpad + zoom buttons + preset tile group + power toggle.
Standalone, no knowledge of modals or pages -- matches modal.py's
ContentBuilder signature directly. See
docs/superpowers/specs/2026-09-17-tabbed-layout-commercial-design.md."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))

import compare  # noqa: E402
import sdk as sdk_module  # noqa: E402
from camera_control import build_camera_control  # noqa: E402
from page import build_page_attributes, write_cuig  # noqa: E402

ui_sdk = sdk_module.read_sdk("2.18.0")
OUT = Path(__file__).resolve().parent / "CameraControl"
OUT.mkdir(parents=True, exist_ok=True)

presets = ["Wide", "Speaker Track", "Presenter"]
html, css, elements = build_camera_control(
    ui_sdk, x=0, y=0, width=560, height=500, z_index=5, resolution=(1280, 800),
    presets=presets, active_font="Roboto",
)
# preset button-list + dpad + zoom in + zoom out + power toggle = 5 top-level elements
assert len(elements) == 5, len(elements)
print("build_camera_control: 5 top-level elements (presets, dpad, 2 zoom buttons, power): OK")

assert "<ch5-dpad " in html
assert html.count("<ch5-button ") >= 2  # zoom in + zoom out (button-list's own children are nested)
assert "<ch5-button-list " in html
assert "<ch5-toggle " in html
print("build_camera_control: dpad, button-list, 2 zoom buttons, and power toggle all present: OK")

for label in presets:
    assert f'labelinnerhtml="{label}"' in html
print("build_camera_control: every preset's own label present on its button-list child: OK")

page_attrs = build_page_attributes(name="CameraControlDemo")
page_path = OUT / "CameraControl.cuig"
write_cuig(page_path, page_attrs, html=html, css=css, elements=elements)
assert compare.round_trip_check(page_path), "camera control page failed round-trip"
print("build_camera_control: written .cuig round-trips byte-identical: OK")

# --- too short for the 3 bands raises ------------------------------------------------
try:
    build_camera_control(
        ui_sdk, x=0, y=0, width=560, height=120, z_index=5, resolution=(1280, 800),
        presets=presets,
    )
    raise AssertionError("expected ValueError for a box too short for the 3 bands")
except ValueError:
    pass
print("build_camera_control: a box too short for the 3 bands raises ValueError: OK")

# --- too narrow for the Zoom Out/In row (below the dpad) raises -----------------------
try:
    build_camera_control(
        ui_sdk, x=0, y=0, width=90, height=500, z_index=5, resolution=(1280, 800),
        presets=presets,
    )
    raise AssertionError("expected ValueError for a box too narrow for the zoom button row")
except ValueError:
    pass
print("build_camera_control: a box too narrow for the zoom button row raises ValueError: OK")

print("Camera Control: all assertions passed.")
