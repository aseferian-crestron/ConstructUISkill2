"""Regression test for a real bug found 2026-09-10 while trying to refresh the user's
own ReflowTest.cuig: reflow_file treated a non-empty SOURCE device block as the
complete source layout, when a device block is really an OVERRIDE of the catch-all.
Construct only restates a rule in a device block when it differs there, so the real
file's 1280x800 block held exactly one rule -- the D-pad's left/top, identical to the
catch-all's -- while the other 20 elements were positioned only by the catch-all.
Reflowing from that source produced a ONE-element target block and silently dropped
the other twenty."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))

from reflow import reflow_file  # noqa: E402
from devices import ORIENTATION_ENUM  # noqa: E402
import layout  # noqa: E402
import compare  # noqa: E402

OUT = Path(__file__).resolve().parent / "ReflowSourceUnion"
OUT.mkdir(parents=True, exist_ok=True)

source = {"width": 1280, "height": 800, "orientation": ORIENTATION_ENUM["landscape"]}
target = {"width": 640, "height": 360, "orientation": ORIENTATION_ENUM["landscape"]}
source_query = layout.orientation_media_query("landscape", 1280, 800)
target_query = layout.orientation_media_query("landscape", 640, 360)

ids = ["a", "b", "c"]
html = "".join(f'<div id="{eid}"></div>' for eid in ids)
# Catch-all positions all three; the 1280x800 block restates only `b`, and moves it.
css = (
    "@media (max-width: 99999px){"
    "#a{display: block; left: 10px; top: 10px; position: absolute; width: 100px; height: 50px;}"
    "#b{display: block; left: 200px; top: 10px; position: absolute; width: 100px; height: 50px;}"
    "#c{display: block; left: 400px; top: 10px; position: absolute; width: 100px; height: 50px;}"
    "}"
    f"@media {source_query}{{"
    "#b{display: block; left: 250px; top: 60px; position: absolute; width: 120px; height: 70px;}"
    "}"
)
path = OUT / "PartialSource.cuig"
path.write_text(
    "{FileMetadata}\nSchema = \"1.0.0.0\"\n"
    f"\n{{Html}}\n{html}\n"
    f"\n{{Css}}\n{css}\n"
    "\n{PageAttributes}\n\n[Attributes]\nName = \"P\"\n",
    encoding="utf-8",
)

result = reflow_file(path, target_resolution=target, source_resolution=source, mode="full_refit")
assert result.warnings == [], f"expected no warnings, got {result.warnings}"
assert compare.round_trip_check(path)

new_css = compare.parse_file(path).sections[2][2]
block = layout.find_media_block(new_css, target_query)
assert block is not None, "target block missing"
fitted = layout.parse_position_rules(block)
assert set(fitted) == {"a", "b", "c"}, (
    f"every element positioned at the source resolution must reach the target block, "
    f"got {sorted(fitted)}")
print(f"all 3 elements carried over, not just the one the device block restated: OK")

# The device block's own override wins over the catch-all for the element it restates.
assert fitted["b"]["width"] == 120 and fitted["b"]["height"] == 70, (
    f"b must be sourced from its 1280x800 override (120x70), not the catch-all's "
    f"100x50, got {fitted['b']}")
assert fitted["a"]["width"] == 100 and fitted["c"]["width"] == 100, (fitted["a"], fitted["c"])
print("the restated element still wins over the catch-all for its own rule: OK")

print("\nSource-block union: all assertions passed.")
