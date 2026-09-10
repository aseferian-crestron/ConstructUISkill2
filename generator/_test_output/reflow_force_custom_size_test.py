"""Regression test for a real bug found 2026-09-10, live-testing in Construct: reflow
computed a smaller size for a real user-authored button (not created by this
generator), but the button had size="regular" -- which ignores explicit width/height
CSS entirely and renders at the theme's fixed preset size regardless -- so the computed
shrink was silently invisible in Construct, and the wrapped second line of buttons ran
past the canvas the math assumed it would fit within. Per the user's direction: reflow
must force size="custom" on any element it actually resizes, mirroring the same fix
this generator's own element-creation code already applies at creation time -- but must
NOT touch size on an element it only repositions, and must leave an already-"custom"
element alone (no-op, not an error)."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))

from reflow import reflow_file  # noqa: E402
from devices import ORIENTATION_ENUM  # noqa: E402
import layout  # noqa: E402
import compare  # noqa: E402

OUT = Path(__file__).resolve().parent / "ReflowForceCustomSize"
OUT.mkdir(parents=True, exist_ok=True)


def make_file(path: Path, html: str, css: str, elements_toml: str) -> None:
    path.write_text(
        "{FileMetadata}\nSchema = \"1.0.0.0\"\n"
        f"\n{{Html}}\n{html}\n"
        f"\n{{Css}}\n{css}\n"
        f"\n{{PageAttributes}}\n\n[Attributes]\nName = \"P\"\n{elements_toml}",
        encoding="utf-8",
    )


def html_size_of(raw: str, element_id: str) -> str | None:
    for m in re.finditer(r"<[\w-]+[^>]*>", raw):
        if f'id="{element_id}"' in m.group(0):
            sm = re.search(r'size="([^"]*)"', m.group(0))
            return sm.group(1) if sm else None
    return None


def toml_size_of(raw: str, element_id: str) -> str | None:
    blocks = re.split(r"(?=\[\[Elements\]\])", raw)
    for block in blocks:
        if f'id = "{element_id}"' in block:
            sm = re.search(r'size = "([^"]*)"', block)
            return sm.group(1) if sm else None
    return None


source = {"width": 1280, "height": 800, "orientation": ORIENTATION_ENUM["landscape"]}
# Narrow enough (60px) that any wrapped single-item row of a 100px-wide button can't
# even fit via Tier 1 alone -- forces real Tier 3 scaling (a genuine resize), not just
# repositioning. "c" (10px wide) fits trivially at 60px with no scaling at all -- the
# repositioned-but-not-resized control case.
target = {"width": 60, "height": 400, "orientation": ORIENTATION_ENUM["landscape"]}

source_query = layout.orientation_media_query("landscape", 1280, 800)

html = (
    '<ch5-button id="a" size="regular" componentName="A"></ch5-button>'
    '<ch5-button id="b" size="custom" componentName="B"></ch5-button>'
    '<ch5-button id="c" size="regular" componentName="C"></ch5-button>'
)
css = (
    f"@media {source_query}{{"
    "#a{display: block; left: 20px; top: 20px; position: absolute; width: 100px; height: 50px;}"
    "#b{display: block; left: 140px; top: 20px; position: absolute; width: 100px; height: 50px;}"
    "#c{display: block; left: 5px; top: 200px; position: absolute; width: 10px; height: 10px;}"
    "}"
)
elements_toml = (
    '\n[[Elements]]\nType = "Ch5 Button"\nEditable = true\n\n'
    '[Elements.Attributes]\nid = "a"\ncomponentName = "A"\nsize = "regular"\n'
    '\n[[Elements]]\nType = "Ch5 Button"\nEditable = true\n\n'
    '[Elements.Attributes]\nid = "b"\ncomponentName = "B"\nsize = "custom"\n'
    '\n[[Elements]]\nType = "Ch5 Button"\nEditable = true\n\n'
    '[Elements.Attributes]\nid = "c"\ncomponentName = "C"\nsize = "regular"\n'
)
path = OUT / "MixedSizeModes.cuig"
make_file(path, html, css, elements_toml)

result = reflow_file(path, target_resolution=target, source_resolution=source, mode="pin_existing")
assert result.warnings == [], f"expected no warnings, got {result.warnings}"
assert compare.round_trip_check(path)

new_css = compare.parse_file(path).sections[2][2]
target_query = layout.orientation_media_query("landscape", 60, 400)
new_block = layout.find_media_block(new_css, target_query)
assert new_block is not None
fitted = layout.parse_position_rules(new_block)
assert set(fitted) == {"a", "b", "c"}
assert fitted["a"]["width"] < 100, f"expected a to actually be scaled down, got {fitted['a']}"
assert fitted["b"]["width"] < 100, f"expected b to actually be scaled down, got {fitted['b']}"
assert fitted["c"]["width"] == 10 and fitted["c"]["height"] == 10, f"expected c to be untouched in size, got {fitted['c']}"

raw = path.read_text(encoding="utf-8")
assert html_size_of(raw, "a") == "custom", f"a: resized + was regular -> must become custom in Html, got {html_size_of(raw, 'a')!r}"
assert toml_size_of(raw, "a") == "custom", f"a: resized + was regular -> must become custom in TOML, got {toml_size_of(raw, 'a')!r}"
assert html_size_of(raw, "b") == "custom", f"b: already custom -> must stay custom (no-op) in Html, got {html_size_of(raw, 'b')!r}"
assert toml_size_of(raw, "b") == "custom", f"b: already custom -> must stay custom (no-op) in TOML, got {toml_size_of(raw, 'b')!r}"
assert html_size_of(raw, "c") == "regular", f"c: only repositioned, never resized -> size must stay regular in Html, got {html_size_of(raw, 'c')!r}"
assert toml_size_of(raw, "c") == "regular", f"c: only repositioned, never resized -> size must stay regular in TOML, got {toml_size_of(raw, 'c')!r}"

print("a (regular, resized) forced to custom in both Html and TOML: OK")
print("b (already custom, resized) stays custom, no-op: OK")
print("c (regular, only repositioned) stays regular, untouched: OK")
print("\nsize=regular -> size=custom forcing -- ALL CHECKS PASSED")
