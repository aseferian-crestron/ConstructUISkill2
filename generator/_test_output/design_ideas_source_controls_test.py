"""design_ideas_subsystem.py -- source-controls widget (reuses
design_ideas_build_subsystem_popup(device_controls=True), same shape as
Controls - Template.cuiw) + design_ideas_add_source_control_ref (wiring
onto a real Presentation.cuig), tested against a disposable COPY of the
real master template file."""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))

import compare  # noqa: E402
import sdk as sdk_module  # noqa: E402
from design_ideas_subsystem import (  # noqa: E402
    design_ideas_add_source_control_ref, design_ideas_build_subsystem_popup,
)
from page import write_cuig  # noqa: E402

ui_sdk = sdk_module.read_sdk("2.18.0")
OUT = Path(__file__).resolve().parent / "DesignIdeasSourceControls"
OUT.mkdir(parents=True, exist_ok=True)

REAL_PRESENTATION = Path(r"C:\Solutions\CrestronDesignIdeas\BasicTemplate_v1_0_2\Presentation.cuig")
TEST_DIR = Path(__file__).resolve().parent / "source_controls_test"
PAGE = TEST_DIR / "Presentation.cuig"
TEST_DIR.mkdir(exist_ok=True)
shutil.copy(REAL_PRESENTATION, PAGE)

# --- 1. build a Controls widget the same way a subsystem popup is built ------------
widget_id, w_attrs, w_html, w_css, w_elements = design_ideas_build_subsystem_popup(
    ui_sdk, widget_name="Controls - Roku", title="Roku", icon_class="fa-solid fa-tv",
    groups=[("Navigation", ["Up", "Down", "Left", "Right", "OK"])],
    panel_width=1048, panel_height=590, device_controls=True,
)
widget_path = OUT / "ControlsRoku.cuiw"
write_cuig(widget_path, w_attrs, html=w_html, css=w_css, elements=w_elements)
assert compare.round_trip_check(widget_path)
print("design_ideas_build_subsystem_popup(device_controls=True): Controls widget"
      " round-trips: OK")

# --- 2. wire it onto the real Presentation page -------------------------------------
added = design_ideas_add_source_control_ref(PAGE, ui_sdk, widget_id, "Controls - Roku")
assert added is True
assert compare.round_trip_check(PAGE)
print("design_ideas_add_source_control_ref: adds the ref, round-trips: OK")

text = PAGE.read_text(encoding="utf-8")
assert 'ccid_WidgetName="Controls - Roku"' in text
print("design_ideas_add_source_control_ref: real ref present with the correct"
      " ccid_WidgetName: OK")

# order: new ref must come BEFORE "Sources - Center" (frontmost)
attrs = text.split("{PageAttributes}", 1)[-1]
import re  # noqa: E402
names = re.findall(r'componentName = "([^"]+)"', attrs)
assert names.index("Controls - Roku") < names.index("Sources - Center"), names
print("design_ideas_add_source_control_ref: new ref listed before Sources - Center"
      " (frontmost, matching this project's real z-order rule): OK")

# position: same as Sources - Center's own real catch-all left/top
css = text.split("{Css}", 1)[-1].split("{PageAttributes}", 1)[0]
catchall = css.split("@media (max-width: 99999px)", 1)[-1]
catchall = catchall[:catchall.find("} @media")]
new_id = None
for cid, cname in re.findall(r'id = "([^"]+)"\s*\ncomponentName = "([^"]+)"', attrs):
    if cname == "Controls - Roku":
        new_id = cid
        break
assert new_id, "could not find the new ref's own id"
m = re.search(r"#" + re.escape(new_id) + r"\s*\{([^}]*)\}", catchall)
assert m and "left:168px" in m.group(1).replace(" ", "") and "top:248px" in m.group(1).replace(" ", ""), m
print("design_ideas_add_source_control_ref: new ref positioned exactly where"
      " Sources - Center's own ref sits: OK")

# --- 3. idempotent: calling again with the same widget name is a no-op -------------
added_again = design_ideas_add_source_control_ref(PAGE, ui_sdk, widget_id, "Controls - Roku")
assert added_again is False
assert compare.round_trip_check(PAGE)
print("design_ideas_add_source_control_ref: calling again for the same widget is a"
      " true no-op: OK")

print("Design Ideas Source Controls: all assertions passed.")
