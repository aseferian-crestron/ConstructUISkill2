"""Regression test for a real bug found 2026-09-10, live-testing in Construct: a
"Source 2" button's adorner correctly showed its new, smaller (21px) height after
reflow, but the button itself rendered much larger. Root cause: the button was a plain
size="regular" button in the source (confirmed: real "regular" buttons never carry
--ch5-button--regular-width/height -- that pair only appears once a button has actually
been custom-resized in Construct), so its source extra_vars was empty. The size-var fix
from the D-pad bug only RECOMPUTED vars that already existed in the source's own
extra_vars -- it never ADDED a missing one. When reflow forces such a button to
size="custom" (see reflow_force_custom_size_test.py), Construct needs those vars to
constrain the actual render; without them it falls back to a larger default while the
outer box (and the adorner) correctly reflects the smaller size reflow computed."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))

from reflow import reflow_file  # noqa: E402
from devices import ORIENTATION_ENUM  # noqa: E402
from sdk import read_sdk  # noqa: E402
import layout  # noqa: E402
import compare  # noqa: E402

OUT = Path(__file__).resolve().parent / "ReflowMissingSizeVars"
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
# 4 same-row buttons, narrow enough after wrap that each wrapped singleton still needs
# Tier 3 scaling -- a genuine resize, matching the real "Source 2" shape exactly: a
# plain size="regular" button with NO extra_vars at all in its source CSS.
target = {"width": 60, "height": 400, "orientation": ORIENTATION_ENUM["landscape"]}

source_query = layout.orientation_media_query("landscape", 1280, 800)

html = '<ch5-button id="s2" size="regular" componentName="Source2"></ch5-button>'
css = (
    f"@media {source_query}{{"
    "#s2{display: block; left: 363px; top: 44px; position: absolute; width: 84px; height: 42px;}"
    "}"
)
elements_toml = (
    '\n[[Elements]]\nType = "Ch5 Button"\nEditable = true\n\n'
    '[Elements.Attributes]\nid = "s2"\ncomponentName = "Source2"\nsize = "regular"\n'
)
path = OUT / "MissingSizeVars.cuig"
make_file(path, html, css, elements_toml)

result = reflow_file(path, target_resolution=target, source_resolution=source, mode="pin_existing", sdk=ui_sdk)
assert result.warnings == [], f"expected no warnings, got {result.warnings}"
assert compare.round_trip_check(path)

new_css = compare.parse_file(path).sections[2][2]
target_query = layout.orientation_media_query("landscape", 60, 400)
new_block = layout.find_media_block(new_css, target_query)
assert new_block is not None
fitted = layout.parse_position_rules(new_block)
s2 = fitted["s2"]
assert s2["width"] < 84, f"expected s2 to actually be scaled down, got {s2}"

# The actual point of the fix: the size vars must exist AND match the final box exactly,
# even though the source had none at all.
assert "--ch5-button--regular-width" in s2["extra_vars"], f"missing size var entirely: {s2['extra_vars']}"
assert "--ch5-button--regular-height" in s2["extra_vars"], f"missing size var entirely: {s2['extra_vars']}"
assert s2["extra_vars"]["--ch5-button--regular-width"] == f"{s2['width']}px", s2["extra_vars"]
assert s2["extra_vars"]["--ch5-button--regular-height"] == f"{s2['height']}px", s2["extra_vars"]

raw = path.read_text(encoding="utf-8")
assert 'id="s2" size="custom"' in raw or 'size="custom"' in [
    m.group(0) for m in __import__("re").finditer(r'size="[^"]*"', raw)
], "s2 was resized and was regular -- must be forced to custom"

print(f"s2: resized to {s2['width']}x{s2['height']}, size vars synthesized fresh and match exactly: OK")
print("\nMissing size vars on a newly-custom element -- ALL CHECKS PASSED")
