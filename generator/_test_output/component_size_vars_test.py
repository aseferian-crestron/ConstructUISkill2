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

from component import (  # noqa: E402
    PROFILES, build_component, can_resize, is_aspect_locked, size_css_vars,
)
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

# --- custom sizing applies ONLY where the SDK gives variables to drive it -------------
# A type with an empty propertyMapping cannot be resized by CSS at all: it lays itself
# out from its own attributes. The user confirmed this for the signal and wifi gauges --
# "signal level and wifi only support fixed sizes". Writing size="custom" there sets a
# preset that does not exist and leaves the adorner disagreeing with the render, which
# is what the first version of this fix did by applying custom to every preset-sized
# type.
# `canResize` is the SDK's own published flag and names exactly those four.
assert [t for t in sorted(PROFILES) if not can_resize(sdk, t)] == [
    "ch5-animation", "ch5-segmented-gauge", "ch5-signal-level-gauge",
    "ch5-wifi-signal-level-gauge"], [t for t in sorted(PROFILES) if not can_resize(sdk, t)]

customisable, fixed = [], []
for tag in sorted(PROFILES):
    _, css, element = build_component(
        sdk, tag, component_name="X", element_id="iz9",
        x=0, y=0, width=150, height=150, z_index=1, resolution=(1280, 800))
    attributes = dict(element.attributes)
    expected = size_css_vars(sdk, tag, width=150, height=150, attributes=attributes)

    if can_resize(sdk, tag) and expected:
        customisable.append(tag)
        assert attributes.get("size") in (None, "custom"),             f"{tag} has render-size variables, so its size must be custom, not {attributes.get('size')!r}"
        for name, value in expected.items():
            assert css.count(f"{name}: {value}") == 2, f"{tag}: {name} not in both @media blocks"
    else:
        fixed.append(tag)
        assert attributes.get("size") != "custom",             f"{tag} has no render-size variables, so it cannot be custom-sized"
        # ...and nothing may claim a CSS box it does not render into.
        rule = id_rule(css, "iz9")
        profile = PROFILES[tag]
        assert ("width:" in rule) == profile.css_width, (tag, rule)
        assert ("height:" in rule) == profile.css_height, (tag, rule)

assert "ch5-signal-level-gauge" in fixed and "ch5-wifi-signal-level-gauge" in fixed, fixed
assert "ch5-segmented-gauge" in fixed, fixed
assert {"ch5-button", "ch5-toggle", "ch5-slider", "ch5-dpad", "ch5-keypad"} <= set(customisable), customisable
print(f"{len(customisable)} custom-sizable types carry their variables; "
      f"{len(fixed)} fixed-size types keep their preset: OK")

# The three gauges write NO explicit box at all -- they size themselves.
for tag in ("ch5-segmented-gauge", "ch5-signal-level-gauge", "ch5-wifi-signal-level-gauge"):
    _, css, _ = build_component(sdk, tag, component_name="G", element_id="ig1",
                                x=5, y=5, width=300, height=200, z_index=1,
                                resolution=(1280, 800))
    rule = id_rule(css, "ig1")
    assert "width:" not in rule and "height:" not in rule, f"{tag}: {rule}"
    assert "left: 5px" in rule and "top: 5px" in rule, rule
print("the three gauges are positioned but never given a size: OK")

# --- aspect-locked types do not assert a height they cannot know ---------------------
# A keypad's height follows its container width, so an explicit one sizes the adorner
# around a component that ignored it -- the user's third report. A dpad is the same
# class but locked 1:1, so it is squared instead: every real instance is square, and
# honouring a non-square request would render a square inside a rectangle.
assert is_aspect_locked(sdk, "ch5-keypad") and is_aspect_locked(sdk, "ch5-dpad")

_, keypad_css, _ = build_component(sdk, "ch5-keypad", component_name="K", element_id="ik1",
                                   x=0, y=0, width=310, height=200, z_index=1,
                                   resolution=(1280, 800))
keypad_rule = id_rule(keypad_css, "ik1")
assert "width: 310px" in keypad_rule and "height:" not in keypad_rule, keypad_rule
print("a keypad writes width and no height: OK")

_, dpad_css, _ = build_component(sdk, "ch5-dpad", component_name="D", element_id="id1",
                                 x=0, y=0, width=310, height=200, z_index=1,
                                 resolution=(1280, 800))
dpad_rule = id_rule(dpad_css, "id1")
assert "width: 200px" in dpad_rule and "height: 200px" in dpad_rule, dpad_rule
assert "--ch5-dpad--regular-size: 200px" in dpad_rule, dpad_rule
print("a dpad squares a non-square request rather than rendering inside a wrong box: OK")

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
