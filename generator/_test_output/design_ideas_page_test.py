"""design_ideas_subsystem.py -- design_ideas_learn_project_shared +
design_ideas_build_subsystem_page, tested against the REAL copied Design
Ideas template (C:\\Solutions\\ClaudeGenTest\\DesignIdeasCopy)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))

import compare  # noqa: E402
import sdk as sdk_module  # noqa: E402
from design_ideas_subsystem import (  # noqa: E402
    design_ideas_learn_project_shared, design_ideas_build_subsystem_page,
    design_ideas_build_subsystem_popup,
)
from page import write_cuig  # noqa: E402

ui_sdk = sdk_module.read_sdk("2.18.0")
OUT = Path(__file__).resolve().parent / "DesignIdeasPage"
OUT.mkdir(parents=True, exist_ok=True)

REAL_PROJECT = Path(r"C:\Solutions\ClaudeGenTest\DesignIdeasCopy")

shared = design_ideas_learn_project_shared(REAL_PROJECT)
for key in ("header_widget_id", "footer_widget_id", "volume_widget_id", "background_asset_id"):
    assert shared.get(key), key
print("design_ideas_learn_project_shared: all 4 shared identifiers learned from the real project: OK")

popup_widget_id, popup_attrs, popup_html, popup_css, popup_elements = design_ideas_build_subsystem_popup(
    ui_sdk, widget_name="Popup - Fireplace", title="Fireplace", icon_class="fa-solid fa-fire",
    groups=[("Flame", ["On", "Off"]), ("Fan", ["High", "Low", "Off"])],
    panel_width=1048, panel_height=590,
)
write_cuig(OUT / "PopupFireplace.cuiw", popup_attrs, html=popup_html, css=popup_css, elements=popup_elements)
assert compare.round_trip_check(OUT / "PopupFireplace.cuiw")
print("design_ideas_build_subsystem_popup: new popup widget round-trips: OK")

page_attrs, page_html, page_css, page_elements = design_ideas_build_subsystem_page(
    ui_sdk, page_name="Fireplace", project_shared=shared,
    popup_widget_id=popup_widget_id, popup_widget_name="Popup - Fireplace",
)

# --- structural checks ---------------------------------------------------------------
assert 'componentName="Background"' in page_html
assert f'assetid="{shared["background_asset_id"]}"' in page_html
assert 'pd-receivestateurl="Contract Enabled"' in page_html
print("design_ideas_build_subsystem_page: Background image present with the real shared assetid + contract URL: OK")

assert 'componentName="CenterDIV"' in page_html
print("design_ideas_build_subsystem_page: CenterDIV backdrop present: OK")

assert f'templateid="w{shared["header_widget_id"]}"' in page_html
assert f'templateid="w{shared["footer_widget_id"]}"' in page_html
assert f'templateid="w{shared["volume_widget_id"]}"' in page_html
assert f'templateid="w{popup_widget_id}"' in page_html
print("design_ideas_build_subsystem_page: Header/Footer/Volume (shared) + new Popup widget refs all present: OK")

# every ch5-template ref carries Visibility=Contract (the project's own standing rule)
import re  # noqa: E402
refs = re.findall(r"<ch5-template[^>]*>", page_html)
assert len(refs) == 4, len(refs)
for ref in refs:
    assert 'sendeventonshow="Contract Enabled"' in ref
    assert 'pd-receivestateshow="Contract Enabled"' in ref
print("design_ideas_build_subsystem_page: all 4 widget refs have Visibility=Contract set: OK")

# --- Element ORDER: real, confirmed live bug (2026-09-18) -- Construct's Layer -------
# Manager (and its actual click hit-testing) treats FIRST in the components list as
# FRONTMOST -- Background built first would make the full-canvas image block the
# entire page. Confirmed against the real `Lights.cuig`'s own order: Popup(-More)/
# Popup, Footer-Volume, Footer, CenterDIV, Header, Background dead LAST.
page_order = [dict(e.attributes).get("componentName") for e in page_elements]
assert page_order[0] == "Popup - Fireplace", page_order
assert page_order[-1] == "Background", page_order
assert page_order.index("Header") < page_order.index("Background"), page_order
print("design_ideas_build_subsystem_page: element order is front-to-back (Popup ref"
      " first, Background dead last): OK")

path = OUT / "Fireplace.cuig"
write_cuig(path, page_attrs, html=page_html, css=page_css, elements=page_elements)
assert compare.round_trip_check(path), "new subsystem page failed round-trip"
print("design_ideas_build_subsystem_page: written .cuig round-trips byte-identical: OK")

print("Design Ideas Page: all assertions passed.")
