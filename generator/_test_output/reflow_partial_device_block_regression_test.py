"""Regression test for a real bug found 2026-09-10: a device-specific @media block
authored directly in Construct (not by this generator) often omits width/height/z-index
for an element whose size never changed from the catch-all block's value -- confirmed
against a real user page (ReflowTest.cuig) where 18 of 21 elements' landscape-block rules
were just `left:Npx;top:Npx;position:absolute;`. The original layout.py::
parse_position_rules required `width` to be present, silently dropping every such
element -- reflow then only ever fit the 3 elements that happened to redundantly restate
their size, producing a badly incomplete/overlapping portrait layout in Construct.
Fixed: parse_position_rules now only requires left/top (width/height/z_index come back as
None when absent); reflow.py::reflow_file fills in None width/height/z_index for both the
source and target element sets from the catch-all block's own values via the new
_fill_missing_size helper."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))

from reflow import reflow_file  # noqa: E402
from devices import ORIENTATION_ENUM  # noqa: E402
import layout  # noqa: E402
import compare  # noqa: E402

OUT = Path(__file__).resolve().parent / "ReflowPartialDeviceBlock"
OUT.mkdir(parents=True, exist_ok=True)


def make_file(path: Path, css: str) -> None:
    path.write_text(
        "{FileMetadata}\nSchema = \"1.0.0.0\"\n"
        "\n{Html}\n<div id=\"i1\"></div><div id=\"i2\"></div><div id=\"i3\"></div>\n"
        f"\n{{Css}}\n{css}\n"
        "\n{PageAttributes}\n\n[Attributes]\nName = \"P\"\n",
        encoding="utf-8",
    )


primary = {"width": 1280, "height": 800, "orientation": ORIENTATION_ENUM["landscape"]}
target = {"width": 640, "height": 400, "orientation": ORIENTATION_ENUM["landscape"]}

primary_query = layout.orientation_media_query("landscape", 1280, 800)
target_query = layout.orientation_media_query("landscape", 640, 400)

# i1: full rule in BOTH catch-all and landscape block (matches the generator's own output).
# i2/i3: full rule in the catch-all, but the landscape block ONLY has left/top/position --
# the real-world shape this bug missed. i2 additionally carries a custom var, which a
# real resized ch5-button would (--ch5-button--regular-width), to confirm extra_vars
# still pass through when width/height are inherited rather than restated.
css = (
    "@media (max-width: 99999px){"
    "#i1{display: block; left: 20px; top: 20px; position: absolute; z-index: 1; width: 100px; height: 50px;}"
    "#i2{display: block; left: 200px; top: 20px; position: absolute; z-index: 2; width: 80px; height: 60px; --ch5-button--regular-width: 80px;}"
    "#i3{display: block; left: 350px; top: 20px; position: absolute; z-index: 3; width: 90px; height: 40px;}"
    "}"
    f"@media {primary_query}{{"
    "#i1{display: block; left: 20px; top: 20px; position: absolute; width: 100px; height: 50px;}"
    "#i2{left: 200px; top: 20px; position: absolute;}"
    "#i3{left: 350px; top: 20px; position: absolute;}"
    "}"
)

path = OUT / "PartialDeviceBlock.cuig"
make_file(path, css)
result = reflow_file(path, target_resolution=target, source_resolution=primary, mode="full_refit")
assert result.warnings == [], f"expected no warnings, got {result.warnings}"
assert compare.round_trip_check(path), "reflow_file must not corrupt Html/PageAttributes/FileMetadata"

new_css = compare.parse_file(path).sections[2][2]
new_block = layout.find_media_block(new_css, target_query)
assert new_block is not None, "expected a new @media block for the target resolution"
new_elements = layout.parse_position_rules(new_block)

# The whole point: all 3 elements (not just i1, the one with a fully-restated device
# rule) must be present and correctly sized/positioned in the new block.
assert set(new_elements) == {"i1", "i2", "i3"}, f"expected all 3 elements, got {set(new_elements)}"
for eid, expected_wh in {"i1": (100, 50), "i2": (80, 60), "i3": (90, 40)}.items():
    assert (new_elements[eid]["width"], new_elements[eid]["height"]) == expected_wh, (
        f"{eid}: width/height inherited from the catch-all block incorrectly, "
        f"got {(new_elements[eid]['width'], new_elements[eid]['height'])}, expected {expected_wh}"
    )
# extra_vars (e.g. --ch5-button--regular-width) inherited from the catch-all must also
# survive and get rescaled consistently with the element's own width, not dropped.
assert "--ch5-button--regular-width" in new_elements["i2"]["extra_vars"]

print("Partial device-block regression: all 3 elements recovered and correctly fit -- OK")
