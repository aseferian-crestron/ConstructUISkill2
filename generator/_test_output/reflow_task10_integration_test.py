# Task 10: add_resolutions_to_project now reflows existing pages/widgets, end-to-end,
# including the orientation-bootstrap case and a genuine row-wrap scenario.
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))

from project import build_project_attributes, write_cuip, add_resolutions_to_project  # noqa: E402
from devices import read_catalog, to_project_resolution  # noqa: E402
from page import write_cuig  # noqa: E402
from elements import Element  # noqa: E402
import layout  # noqa: E402
import compare  # noqa: E402

OUT = Path(__file__).resolve().parent / "Phase5bReflowIntegration"
OUT.mkdir(parents=True, exist_ok=True)
catalog = read_catalog()

tsw = to_project_resolution(catalog.by_id_name("TSW-1070"))  # 1280x800 landscape
attrs, drs = build_project_attributes(name="ReflowIntegration", sdk_id="CH5:2.18.0", resolutions=[tsw])
cuip_path = OUT / "ReflowIntegration.cuip"
write_cuip(cuip_path, attrs, drs)

# A page with one element deliberately near the right/bottom edge of the 1280x800 canvas.
primary_query = layout.orientation_media_query("landscape", 1280, 800)
element_id = "iedge1"
css = (
    f"@media (max-width: 99999px){{#{element_id}{{display: block; left: 1100px; top: 700px; position: absolute; z-index: 1; width: 150px; height: 90px;}}}}"
    f"@media {primary_query}{{#{element_id}{{display: block; left: 1100px; top: 700px; position: absolute; width: 150px; height: 90px;}}}}"
)
page_path = OUT / "EdgePage.cuig"
write_cuig(page_path, [("Name", "EdgePage"), ("PageMode", "absolute"), ("Id", "p1"), ("StartPage", "True"), ("PreloadPage", "True"), ("CachePage", "False"), ("VisibilityJoin", "0"), ("DisplayBackgroundColor", "False")], html=f'<div id="{element_id}"></div>', css=css, elements=[Element(type="Ch5 Button", attributes=[("id", element_id)])])

# --- Scenario 1: add a smaller landscape resolution (forces move/compact) -----------
smaller = to_project_resolution(catalog.by_id_name("TST-1080", orientation="landscape"))
smaller["width"], smaller["height"] = 640, 360  # deliberately smaller than the element's own position, to force tier 1/2 to actually do something
warnings = add_resolutions_to_project(cuip_path, [smaller])
assert isinstance(warnings, list), "add_resolutions_to_project must now return a list of warnings"
assert compare.round_trip_check(cuip_path)
assert compare.round_trip_check(page_path), "reflow must not corrupt the page file"

new_css = compare.parse_file(page_path).sections[2][2]
smaller_query = layout.orientation_media_query("landscape", 640, 360)
new_block = layout.find_media_block(new_css, smaller_query)
assert new_block is not None, "expected a new @media block for the smaller resolution"
fitted = layout.parse_position_rules(new_block)
assert element_id in fitted
assert fitted[element_id]["left"] + fitted[element_id]["width"] <= 640, "element must be on-canvas (right edge)"
assert fitted[element_id]["top"] + fitted[element_id]["height"] <= 360, "element must be on-canvas (bottom edge)"
print("Scenario 1 (edge element, smaller landscape resolution): on-canvas -- OK")

# --- Scenario 2: orientation-bootstrap -- add a portrait resolution to a landscape-only project
portrait = to_project_resolution(catalog.by_id_name("TST-1080", orientation="portrait"))
warnings2 = add_resolutions_to_project(cuip_path, [portrait])
assert compare.round_trip_check(page_path)
# Real catalog-sourced width/height are the confirmed real-.cuip "Npx" string form (see
# devices.py::to_project_resolution / project.py::_numeric_dim) -- unlike `smaller`/
# `narrow` above (deliberately overridden with plain ints), `portrait` is used verbatim
# from the catalog, so it needs the same int coercion here purely for this test's own
# local query-building/comparison arithmetic (add_resolutions_to_project already
# coerces internally for its own reflow math).
portrait_w = int(portrait["width"][:-2]) if isinstance(portrait["width"], str) else portrait["width"]
portrait_h = int(portrait["height"][:-2]) if isinstance(portrait["height"], str) else portrait["height"]
portrait_query = layout.orientation_media_query("portrait", portrait_w, portrait_h)
portrait_css = compare.parse_file(page_path).sections[2][2]
portrait_block = layout.find_media_block(portrait_css, portrait_query)
assert portrait_block is not None, "orientation-bootstrap must still produce a block (source = the other orientation's primary)"
portrait_fitted = layout.parse_position_rules(portrait_block)
assert element_id in portrait_fitted
assert portrait_fitted[element_id]["left"] + portrait_fitted[element_id]["width"] <= portrait_w
assert portrait_fitted[element_id]["top"] + portrait_fitted[element_id]["height"] <= portrait_h
print("Scenario 2 (orientation-bootstrap, portrait added to landscape-only project): OK")

# --- Scenario 3: genuine row-wrap -- a 4-button single row onto a much narrower resolution
button_specs = [("b0", 0), ("b1", 180), ("b2", 360), ("b3", 540)]  # left offsets; all top=20, width150, height90
catch_all_rules = "".join(
    f"#{bid}{{display: block; left: {left}px; top: 20px; position: absolute; z-index: 1; width: 150px; height: 90px;}}"
    for bid, left in button_specs
)
device_rules = "".join(
    f"#{bid}{{display: block; left: {left}px; top: 20px; position: absolute; width: 150px; height: 90px;}}"
    for bid, left in button_specs
)
css3 = f"@media (max-width: 99999px){{{catch_all_rules}}}" f"@media {primary_query}{{{device_rules}}}"
html3 = "".join(f'<div id="{bid}"></div>' for bid, _ in button_specs)
elements3 = [Element(type="Ch5 Button", attributes=[("id", bid)]) for bid, _ in button_specs]
page_path3 = OUT / "WrapPage.cuig"
write_cuig(page_path3, [("Name", "WrapPage"), ("PageMode", "absolute"), ("Id", "p2"), ("StartPage", "False"), ("PreloadPage", "True"), ("CachePage", "False"), ("VisibilityJoin", "0"), ("DisplayBackgroundColor", "False")], html=html3, css=css3, elements=elements3)

narrow = to_project_resolution(catalog.by_id_name("TST-1080", orientation="landscape"))
narrow["width"], narrow["height"] = 400, 300
warnings4 = add_resolutions_to_project(cuip_path, [narrow])
assert compare.round_trip_check(page_path3)

narrow_query = layout.orientation_media_query("landscape", 400, 300)
narrow_css = compare.parse_file(page_path3).sections[2][2]
narrow_block = layout.find_media_block(narrow_css, narrow_query)
assert narrow_block is not None
fitted3 = layout.parse_position_rules(narrow_block)
assert set(fitted3) == {"b0", "b1", "b2", "b3"}

# No element scaled down -- wrap must be preferred over scaling, per the approved tier order.
for bid in fitted3:
    assert fitted3[bid]["width"] == 150 and fitted3[bid]["height"] == 90, f"{bid} was scaled, expected wrap instead: {fitted3[bid]}"

# The row actually split -- more than one distinct top value among the 4 elements.
tops = {fitted3[bid]["top"] for bid in fitted3}
assert len(tops) > 1, f"expected the row to wrap onto more than one line, got a single top value: {tops}"

# On-canvas and pairwise non-overlapping (direct AABB check across ALL elements, not
# just within a row -- proving the cross-row Y-separation argument holds in practice).
def overlaps(r1, r2):
    return not (
        r1["left"] + r1["width"] <= r2["left"] or r2["left"] + r2["width"] <= r1["left"]
        or r1["top"] + r1["height"] <= r2["top"] or r2["top"] + r2["height"] <= r1["top"]
    )

ids3 = list(fitted3)
for bid in ids3:
    assert fitted3[bid]["left"] + fitted3[bid]["width"] <= 400
    assert fitted3[bid]["top"] + fitted3[bid]["height"] <= 300
for i in range(len(ids3)):
    for j in range(i + 1, len(ids3)):
        assert not overlaps(fitted3[ids3[i]], fitted3[ids3[j]]), f"overlap: {ids3[i]} vs {ids3[j]}"
print("Scenario 3 (row-wrap, 4-button row onto a much narrower resolution): OK")

# --- Regression: existing Phase 5 behavior (no .cuig/.cuiw files present) unaffected -
attrs0, drs0 = build_project_attributes(name="NoPages", sdk_id="CH5:2.18.0")
zero_path = OUT / "NoPages.cuip"
write_cuip(zero_path, attrs0, drs0)
warnings3 = add_resolutions_to_project(zero_path, [tsw])
assert warnings3 == [], "adding a resolution to a project with no pages/widgets must produce no warnings"
assert compare.round_trip_check(zero_path)
print("Regression: add_resolutions_to_project with zero pages/widgets still works: OK")

print("\nTASK 10: end-to-end integration -- ALL CHECKS PASSED")
