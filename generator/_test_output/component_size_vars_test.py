"""Regression: a component must RENDER at the size its selection adorner shows.

A CH5 web component does not lay itself out from the plain `width`/`height` on its
`#id` rule -- those only size the canvas adorner. Its own rendering reads CSS custom
properties (`--ch5-toggle--handle-size-regular`, `--ch5-button--regular-width`, ...) and
only honours an explicit size at all when `size="custom"`. Write one without the other
and Construct draws a selection box visibly larger than the component inside it.

This was found and fixed for ch5-button in Phase 4. The generic builder then
reintroduced it for every type -- including ch5-button, whose attributes delegate to the
confirmed builder but whose CSS came from the generic path, which emitted no variables
at all. The user caught it on a toggle and a button.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from component import PROFILES, build_component, size_css_vars  # noqa: E402
from sdk import read_sdk  # noqa: E402

sdk = read_sdk("2.18.0")


def id_rule(css: str, element_id: str) -> str:
    return re.search(r"#" + element_id + r"\{([^}]*)\}", css).group(1)


# --- the two types the user reported --------------------------------------------------
for tag, expected_vars in (
    ("ch5-toggle", {"--ch5-toggle--handle-size-regular": "200px"}),
    ("ch5-button", {"--ch5-button--regular-width": "200px",
                    "--ch5-button--regular-height": "100px"}),
):
    html, css, element = build_component(
        sdk, tag, component_name="X", element_id="ix1",
        x=10, y=10, width=200, height=100, z_index=1, resolution=(1280, 800))
    attributes = dict(element.attributes)
    assert attributes["size"] == "custom", (tag, attributes.get("size"))
    rule = id_rule(css, "ix1")
    for name, value in expected_vars.items():
        assert f"{name}: {value}" in rule, f"{tag}: {name} missing from {rule}"
    # BOTH @media blocks carry them, not just the catch-all.
    assert css.count("--ch5-") >= 2 * len(expected_vars), css
print("toggle and button carry size=custom and their render-size variables: OK")

# --- a toggle writes no explicit height ----------------------------------------------
# Its height follows its handle size; an explicit one makes the adorner taller than the
# component, which is exactly the reported symptom. The reference toggle has width only.
_, toggle_css, _ = build_component(
    sdk, "ch5-toggle", component_name="T", element_id="it1",
    x=0, y=0, width=180, height=90, z_index=1, resolution=(1280, 800))
toggle_rule = id_rule(toggle_css, "it1")
assert "width: 180px" in toggle_rule, toggle_rule
assert "height:" not in toggle_rule, f"a toggle must not carry an explicit height: {toggle_rule}"
print("a toggle writes width and no height, matching its reference instance: OK")

# --- every type that can be sized says so ---------------------------------------------
for tag in sorted(PROFILES):
    _, css, element = build_component(
        sdk, tag, component_name="X", element_id="iz9",
        x=0, y=0, width=150, height=150, z_index=1, resolution=(1280, 800))
    attributes = dict(element.attributes)
    if "size" not in attributes:
        continue
    # ch5-qrcode's `size` is a NUMBER (160), not a preset name, so "custom" is wrong there.
    if tag == "ch5-qrcode":
        assert attributes["size"] != "custom", attributes["size"]
        continue
    assert attributes["size"] == "custom", f"{tag} has a preset size attribute but is not custom"

    # Whatever variables the SDK says this type renders from must be in BOTH blocks.
    expected = size_css_vars(sdk, tag, width=150, height=150, attributes=attributes)
    for name, value in expected.items():
        assert css.count(f"{name}: {value}") == 2, f"{tag}: {name} not in both @media blocks"
print("every preset-sized type is size=custom and carries its variables in both blocks: OK")

# --- the conditions in the mapping are honoured ---------------------------------------
# A horizontal slider IGNORES its height mapping; a vertical button SWAPS width into the
# height variable. Both condition kinds appear in the SDK and both change the output.
horizontal = size_css_vars(sdk, "ch5-slider", width=300, height=60,
                           attributes={"orientation": "horizontal"})
assert horizontal == {"--ch5-slider--width-regular": "300px"}, horizontal
vertical = size_css_vars(sdk, "ch5-slider", width=60, height=300,
                         attributes={"orientation": "vertical"})
assert vertical == {"--ch5-slider--width-regular": "300px"}, vertical
print("slider: the horizontal/vertical `ignore` conditions pick the right dimension: OK")

swapped = size_css_vars(sdk, "ch5-button", width=200, height=100,
                        attributes={"orientation": "vertical"})
assert swapped == {"--ch5-button--regular-height": "200px",
                   "--ch5-button--regular-width": "100px"}, swapped
print("button: the vertical `swaptarget` condition swaps width and height: OK")

print("\nRender-size variables: all assertions passed.")
