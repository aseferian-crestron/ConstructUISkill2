"""Create a real Construct project (TabbedCommercial, in the existing
ClaudeGenTest solution) populated with build_tabbed_shell's real output, so
the user can open it in Construct. Content is the same real example already
reviewed in docs/construct-tabbed-ui-screens-commercial.pdf -- room
"Boardroom A", Video Call + Audio Call system modes, Environment/Audio/Camera
footer subsystems, Wide/Speaker Track/Presenter camera presets.
"""
import sys
from pathlib import Path

GEN = Path(r"C:\ClaudeProjects\ConstructUISkill2\generator")
sys.path.insert(0, str(GEN))
sys.path.insert(0, str(GEN.parent / "harness"))

import compare  # noqa: E402
import sdk as sdk_module  # noqa: E402
from solution import read_solution, add_project_to_solution  # noqa: E402
from project import build_project_attributes, write_cuip  # noqa: E402
from page import write_cuig  # noqa: E402
from layout_patterns import build_tabbed_shell  # noqa: E402

ui_sdk = sdk_module.read_sdk("2.18.0")

SOLUTION_DIR = Path(r"C:\Solutions\ClaudeGenTest")
CSLN = SOLUTION_DIR / "ClaudeGenTest.csln"
PROJECT_NAME = "TabbedCommercial"
PROJECT_DIR = SOLUTION_DIR / PROJECT_NAME
PROJECT_DIR.mkdir(parents=True, exist_ok=True)

RESOLUTION = {
    "IsCustom": True, "IsSelected": True, "VisitedName": "TSW-1070",
    "id": "D-L-TSW1070-1280-0800", "idName": "TSW-1070",
    "resolutionId": "L-1280-800", "resolutionName": "TSW-1070",
    "resolutionType": "generic", "deviceSpecId": "TSW-1070",
    "width": "1280px", "height": "800px", "widthMedia": "1280px",
    "heightMedia": "800px", "orientation": 1, "supportedDevices": "",
    "displayNameSuffix": "", "componentKeys": ["UiEditor"],
    "modes": [], "IsMode": False,
}

# --- 1. create the project + add it to the existing solution -----------------------
cuip_path = PROJECT_DIR / f"{PROJECT_NAME}.cuip"
attrs, device_resolution_source = build_project_attributes(
    name=PROJECT_NAME, sdk_id="CH5:2.18.0", resolutions=[RESOLUTION],
)
write_cuip(cuip_path, attrs, device_resolution_source)
print(f"created project: {cuip_path}")

sol = read_solution(CSLN)
if sol.find_project(PROJECT_NAME) is None:
    add_project_to_solution(sol, PROJECT_NAME, cuip_path)
    print(f"added {PROJECT_NAME!r} to solution {CSLN}")
else:
    print(f"{PROJECT_NAME!r} already registered in {CSLN} -- not re-added")

# --- 2. build the Tabbed shell with the PDF's own real content ----------------------
result = build_tabbed_shell(
    ui_sdk,
    room_name="Boardroom A",
    splash_tiles=[
        ("Start Presentation", "fa-solid fa-desktop"),
        ("Join Video Call", "fa-solid fa-video"),
        ("Join Audio Call", "fa-solid fa-microphone"),
    ],
    additional_system_modes=["Video Call", "Audio Call"],
    subsystems=["Environment", "Audio", "Camera"],
    camera_presets=["Wide", "Speaker Track", "Presenter"],
    panel_width=1280, panel_height=800,
    resolution=(1280, 800),
)

files_written = []


def write_and_check(path: Path, attrs, html, css, elements):
    write_cuig(path, attrs, html=html, css=css, elements=elements)
    ok = compare.round_trip_check(path)
    files_written.append((path, ok))
    print(f"  {'OK' if ok else 'ROUND-TRIP FAILED'}: {path.name}")


print("\nwriting pages/widgets:")
write_and_check(PROJECT_DIR / "Splash.cuig", *result["splash_page"])
write_and_check(PROJECT_DIR / "MainPanel.cuig", *result["main_panel_page"])

_, header_attrs, header_html, header_css, header_elements = result["header_widget"]
write_and_check(PROJECT_DIR / "Header.cuiw", header_attrs, header_html, header_css, header_elements)

_, footer_attrs, footer_html, footer_css, footer_elements = result["footer_widget"]
write_and_check(PROJECT_DIR / "Footer.cuiw", footer_attrs, footer_html, footer_css, footer_elements)

for mode, (wid, w_attrs, w_html, w_css, w_elements) in result["tab_content_widgets"].items():
    safe = mode.replace(" ", "")
    write_and_check(PROJECT_DIR / f"{safe} Content.cuiw", w_attrs, w_html, w_css, w_elements)

for label, (wid, w_attrs, w_html, w_css, w_elements) in result["modal_widgets"].items():
    write_and_check(PROJECT_DIR / f"{label} Modal.cuiw", w_attrs, w_html, w_css, w_elements)

failed = [p for p, ok in files_written if not ok]
print(f"\n{len(files_written)} files written, {len(failed)} round-trip failures.")
if failed:
    print("FAILED:", failed)
    sys.exit(1)
print(f"\nProject ready: {cuip_path}")
print(f"Solution: {CSLN}")
