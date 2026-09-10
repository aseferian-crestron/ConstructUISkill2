"""Task 4: end-to-end -- replays the real bug (found 2026-09-10 in the user's
ReflowTest.cuig): a button row centered in a 1280px landscape source, reflowed into an
800px portrait target via fit_axis's Tier 1 path (the row already fits, so today's code
never moves it at all -- exactly the shape that produced a flush-right result in
Construct instead of a centered one)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))

from reflow import reflow_file  # noqa: E402
from devices import ORIENTATION_ENUM  # noqa: E402
import layout  # noqa: E402
import compare  # noqa: E402

OUT = Path(__file__).resolve().parent / "ReflowCenteringE2E"
OUT.mkdir(parents=True, exist_ok=True)


def make_file(path: Path, css: str) -> None:
    path.write_text(
        "{FileMetadata}\nSchema = \"1.0.0.0\"\n"
        "\n{Html}\n<div id=\"a\"></div><div id=\"b\"></div><div id=\"c\"></div>\n"
        f"\n{{Css}}\n{css}\n"
        "\n{PageAttributes}\n\n[Attributes]\nName = \"P\"\n",
        encoding="utf-8",
    )


source = {"width": 1280, "height": 800, "orientation": ORIENTATION_ENUM["landscape"]}
target = {"width": 800, "height": 1280, "orientation": ORIENTATION_ENUM["portrait"]}

source_query = layout.orientation_media_query("landscape", 1280, 800)
target_query = layout.orientation_media_query("portrait", 800, 1280)

# 3 buttons, 100px wide, centered in the 1280px-wide source: lefts 450, 590, 730 (gaps
# of 40), spanning 450-830 -- left_margin=450, right_margin=1280-830=450, centered.
css = (
    f"@media {source_query}{{"
    "#a{display: block; left: 450px; top: 20px; position: absolute; width: 100px; height: 50px;}"
    "#b{display: block; left: 590px; top: 20px; position: absolute; width: 100px; height: 50px;}"
    "#c{display: block; left: 730px; top: 20px; position: absolute; width: 100px; height: 50px;}"
    "}"
)
path = OUT / "CenteredRow.cuig"
make_file(path, css)

result = reflow_file(path, target_resolution=target, source_resolution=source, mode="pin_existing")
assert result.warnings == [], f"expected no warnings, got {result.warnings}"
assert compare.round_trip_check(path)

new_css = compare.parse_file(path).sections[2][2]
new_block = layout.find_media_block(new_css, target_query)
assert new_block is not None, "expected a new @media block for the target resolution"
fitted = layout.parse_position_rules(new_block)

assert set(fitted) == {"a", "b", "c"}
# Hand-traced expected result (see the design spec / Task 1's fit_axis-level test for
# the same arithmetic): Tier 1 first clamps the group flush against the target's right
# edge (span 380 <= 800, but original max_pos 830 > 800 -- old behavior would stop
# here, flush right at left=70,210,350... wait -- offset = 800-830 = -30, so
# 450-30=420, 590-30=560, 730-30=700). Centering then re-centers within the 800px
# target: leftover = 800 - 380 = 420, shift so the group starts at 420 // 2 = 210.
assert fitted["a"]["left"] == 210, fitted["a"]
assert fitted["b"]["left"] == 350, fitted["b"]
assert fitted["c"]["left"] == 490, fitted["c"]
for eid in ("a", "b", "c"):
    assert fitted[eid]["width"] == 100 and fitted[eid]["height"] == 50, fitted[eid]

# Explicitly prove it's no longer flush against either edge (the exact symptom reported).
min_left = min(fitted[eid]["left"] for eid in fitted)
max_right = max(fitted[eid]["left"] + fitted[eid]["width"] for eid in fitted)
assert min_left > 0, f"must not be flush against the left edge, got min_left={min_left}"
assert max_right < 800, f"must not be flush against the right edge, got max_right={max_right}"
assert min_left == 800 - max_right, f"left and right margins must be equal (centered), got {min_left} vs {800 - max_right}"

print("End-to-end: centered source row reflows into a centered (not edge-anchored) target row: OK")
print("\nTASK 4: end-to-end centering -- ALL CHECKS PASSED")
