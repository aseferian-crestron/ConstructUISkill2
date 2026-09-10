"""Task 3: end-to-end -- replays the real bug (found 2026-09-10 in the user's
ReflowTest.cuig, TSW-570/640x360): a D-pad flanked by two same-left Up/Down button
pairs, reflowed into a target narrow enough that the flat 5-element model wrapped
(tearing pairs apart and forcing extra vertical compression), but the column-aware
model fits via Tier 2 compaction alone -- no wrap needed at all (hand-traced in the
design spec: needed_reduction=50, slack=138)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))

from reflow import reflow_file  # noqa: E402
from devices import ORIENTATION_ENUM  # noqa: E402
import layout  # noqa: E402
import compare  # noqa: E402

OUT = Path(__file__).resolve().parent / "ReflowColumnsE2E"
OUT.mkdir(parents=True, exist_ok=True)


def make_file(path: Path, html: str, css: str) -> None:
    path.write_text(
        "{FileMetadata}\nSchema = \"1.0.0.0\"\n"
        f"\n{{Html}}\n{html}\n"
        f"\n{{Css}}\n{css}\n"
        "\n{PageAttributes}\n\n[Attributes]\nName = \"P\"\n",
        encoding="utf-8",
    )


source = {"width": 1280, "height": 800, "orientation": ORIENTATION_ENUM["landscape"]}
target = {"width": 640, "height": 360, "orientation": ORIENTATION_ENUM["landscape"]}

source_query = layout.orientation_media_query("landscape", 1280, 800)

ids = ["iha5b0", "i4rvpkl", "ilqek", "im68at", "i66ouw"]
html = "".join(f'<div id="{eid}"></div>' for eid in ids)
css = (
    f"@media {source_query}{{"
    "#iha5b0{display: block; left: 292px; top: 311px; position: absolute; width: 106px; height: 79px;}"
    "#i4rvpkl{display: block; left: 292px; top: 409px; position: absolute; width: 106px; height: 79px;}"
    "#ilqek{display: block; left: 474px; top: 234px; position: absolute; width: 332px; height: 332px;}"
    "#im68at{display: block; left: 876px; top: 311px; position: absolute; width: 106px; height: 79px;}"
    "#i66ouw{display: block; left: 876px; top: 409px; position: absolute; width: 106px; height: 79px;}"
    "}"
)
path = OUT / "DpadPairs.cuig"
make_file(path, html, css)

result = reflow_file(path, target_resolution=target, source_resolution=source, mode="pin_existing")
assert result.warnings == [], f"expected no warnings, got {result.warnings}"
assert compare.round_trip_check(path)

new_css = compare.parse_file(path).sections[2][2]
target_query = layout.orientation_media_query("landscape", 640, 360)
new_block = layout.find_media_block(new_css, target_query)
assert new_block is not None
fitted = layout.parse_position_rules(new_block)
assert set(fitted) == set(ids)

# The actual point of the fix: each pair's two members always share the same left.
assert fitted["iha5b0"]["left"] == fitted["i4rvpkl"]["left"], (
    f"Up/Down pair must share left, got {fitted['iha5b0']['left']} vs {fitted['i4rvpkl']['left']}"
)
assert fitted["im68at"]["left"] == fitted["i66ouw"]["left"], (
    f"Up/Down pair must share left, got {fitted['im68at']['left']} vs {fitted['i66ouw']['left']}"
)
print("Both Up/Down pairs share a left position after reflow: OK")

# Hand-traced in the design spec: Tier 2 compaction alone fits this -- no wrap needed,
# so every element keeps its original TOP-level row structure (no element scaled down).
for eid in ids:
    assert fitted[eid]["width"] in (106, 332), f"{eid} must not be scaled (Tier 2 alone should suffice), got {fitted[eid]}"
print("No scaling needed -- Tier 2 compaction alone fits the row (confirms the spec's hand-trace): OK")

# Zero overlaps, everything on-canvas.
def overlaps(a, b):
    return not (
        a["left"] + a["width"] <= b["left"] or b["left"] + b["width"] <= a["left"]
        or a["top"] + a["height"] <= b["top"] or b["top"] + b["height"] <= a["top"]
    )

for i in range(len(ids)):
    for j in range(i + 1, len(ids)):
        assert not overlaps(fitted[ids[i]], fitted[ids[j]]), f"overlap: {ids[i]} vs {ids[j]}"
for eid in ids:
    e = fitted[eid]
    assert e["left"] + e["width"] <= 640 and e["top"] + e["height"] <= 360, f"{eid} off-canvas: {e}"
print("Zero overlaps, everything on-canvas: OK")

print("\nTASK 3: column-aware end-to-end -- ALL CHECKS PASSED")
