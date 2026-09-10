"""Regression test for a real bug found 2026-09-10, live-testing in Construct: a
ch5-dpad (a square, single-CSS-var component) sharing a row with other content got
independently fit on X and Y, ending up non-square (width unchanged, height scaled
down) -- the box math was non-overlapping, but the D-pad's actual rendered size is
driven by ONE CSS var (--ch5-dpad--regular-size, sourced from width per the SDK
schema), which reflow's old scaling logic never recognized (it only matched var names
containing "width"/"height") and left unscaled at the original size -- so the REAL
render stayed full-size and visibly overlapped its neighbors, even though the computed
box didn't. Reproduces the real shape: a D-pad sharing a row with two side buttons,
reflowed into a resolution too short to fit the D-pad's full height alongside them."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))

from reflow import reflow_file  # noqa: E402
from devices import ORIENTATION_ENUM  # noqa: E402
from sdk import read_sdk  # noqa: E402
import layout  # noqa: E402
import compare  # noqa: E402

OUT = Path(__file__).resolve().parent / "ReflowAspectLockDpad"
OUT.mkdir(parents=True, exist_ok=True)
ui_sdk = read_sdk("2.18.0")


def make_file(path: Path, html: str, css: str, elements_toml: str) -> None:
    path.write_text(
        "{FileMetadata}\nSchema = \"1.0.0.0\"\n"
        f"\n{{Html}}\n{html}\n"
        f"\n{{Css}}\n{css}\n"
        f"\n{{PageAttributes}}\n\n[Attributes]\nName = \"P\"\n{elements_toml}",
        encoding="utf-8",
    )


source = {"width": 1280, "height": 800, "orientation": ORIENTATION_ENUM["landscape"]}
# Short target: plenty of width for the row (600px is way more than the row needs),
# but not enough height for the D-pad's full 300px alongside a comfortable stack --
# forces Y-axis Tier 3 scaling while X-axis needs no scaling at all (span already
# fits), exactly the asymmetric-scaling shape that produced the real bug.
target = {"width": 600, "height": 200, "orientation": ORIENTATION_ENUM["landscape"]}

source_query = layout.orientation_media_query("landscape", 1280, 800)

html = (
    '<ch5-button id="left"></ch5-button>'
    '<ch5-dpad id="dpad" size="custom"></ch5-dpad>'
    '<ch5-button id="right"></ch5-button>'
)
css = (
    f"@media {source_query}{{"
    "#left{display: block; left: 20px; top: 100px; position: absolute; width: 80px; height: 40px;}"
    "#dpad{display: block; left: 150px; top: 20px; position: absolute; width: 300px; height: 300px; --ch5-dpad--regular-size: 300px;}"
    "#right{display: block; left: 500px; top: 100px; position: absolute; width: 80px; height: 40px;}"
    "}"
)
elements_toml = (
    '\n[[Elements]]\nType = "Ch5 Button"\nEditable = true\n\n'
    '[Elements.Attributes]\nid = "left"\nsize = "regular"\n'
    '\n[[Elements]]\nType = "Ch5 Dpad"\nEditable = true\n\n'
    '[Elements.Attributes]\nid = "dpad"\nsize = "custom"\n'
    '\n[[Elements]]\nType = "Ch5 Button"\nEditable = true\n\n'
    '[Elements.Attributes]\nid = "right"\nsize = "regular"\n'
)
path = OUT / "DpadRow.cuig"
make_file(path, html, css, elements_toml)

result = reflow_file(path, target_resolution=target, source_resolution=source, mode="pin_existing", sdk=ui_sdk)
# UPDATED 2026-09-10 (minimum-size floors): this shape now reports one expected
# warning. Its single row pairs a 300px D-pad with 40px buttons whose own 30px floor
# only lets them shrink 25%, which would force the row to stay 225px tall against a
# 200px target -- so stack_rows relaxes that row's floor (see its docstring) and lays
# it out exactly as before rather than skipping the block. The layout assertions below
# are unchanged and still pass, which is the point: relaxation degrades to today's
# behavior, it doesn't lose the block.
assert len(result.warnings) == 1 and "too crowded to honor" in result.warnings[0], (
    f"expected only the minimum-size relaxation warning, got {result.warnings}")
assert compare.round_trip_check(path)

new_css = compare.parse_file(path).sections[2][2]
target_query = layout.orientation_media_query("landscape", 600, 200)
new_block = layout.find_media_block(new_css, target_query)
assert new_block is not None
fitted = layout.parse_position_rules(new_block)
assert set(fitted) == {"left", "dpad", "right"}

dpad = fitted["dpad"]
assert dpad["width"] == dpad["height"], f"D-pad must stay square, got {dpad['width']}x{dpad['height']}"
assert dpad["width"] < 300, f"D-pad must actually be scaled down (was 300), got {dpad['width']}"
assert dpad["extra_vars"]["--ch5-dpad--regular-size"] == f"{dpad['width']}px", (
    f"--ch5-dpad--regular-size must match the final (reconciled) width/height exactly, "
    f"got var={dpad['extra_vars']['--ch5-dpad--regular-size']!r} vs width={dpad['width']}"
)
print(f"D-pad correctly reconciled to square {dpad['width']}x{dpad['height']}, var matches: OK")

# The actual point of the fix: no pairwise overlap between any of the 3 elements.
def overlaps(a, b):
    return not (
        a["left"] + a["width"] <= b["left"] or b["left"] + b["width"] <= a["left"]
        or a["top"] + a["height"] <= b["top"] or b["top"] + b["height"] <= a["top"]
    )

ids = list(fitted)
for i in range(len(ids)):
    for j in range(i + 1, len(ids)):
        assert not overlaps(fitted[ids[i]], fitted[ids[j]]), f"overlap: {ids[i]} vs {ids[j]} -- {fitted[ids[i]]} / {fitted[ids[j]]}"
for eid in ids:
    e = fitted[eid]
    assert e["left"] + e["width"] <= 600 and e["top"] + e["height"] <= 200, f"{eid} off-canvas: {e}"
print("No overlaps between the D-pad and its neighbors, everything on-canvas: OK")

print("\nD-pad aspect-lock reconciliation -- ALL CHECKS PASSED")
