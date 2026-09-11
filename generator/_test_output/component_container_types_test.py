"""Container component types: parents AND their nested children, diffed against the
reference project.

A container is only right if its children are right -- a dpad with four buttons instead
of five, or a keypad whose `buttonstar` carries the wrong label, is a component that
looks plausible and behaves wrong. So this checks the child count, each child's
attributes, and each child's values, not just the parent.

How many children a container has comes from the parent's own attributes
(`numberofitems`, `numberofsources`, `numberofscreens`); the dpad's and keypad's fixed
sets come from MetaDataResolver.ts, which hardcodes them.
"""
import re
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from component import (  # noqa: E402
    CONTAINER_TAGS, DPAD_KEYS, KEYPAD_KEYS, build_children, build_component,
    build_component_attributes,
)
from sdk import read_sdk  # noqa: E402

sdk = read_sdk("2.18.0")
REF = Path(r"C:\Solutions\ClaudeSamples\Components")
HEADER_RE = re.compile(r"^\{(\w+)\}[ \t]*\r?\n?", re.MULTILINE)
name_to_tag = {e.get("name"): e.get("tagName") for e in sdk.schema["ch5Elements"]["elements"]}

UNIVERSAL_DELTAS = {"oldID"}

#: Parent attributes in the reference instance that a freshly-built container does not
#: carry -- all of them configuration the user applied after creating it.
PARENT_DELTAS: dict[str, set[str]] = {
    # Signal fields the user opened and left blank. An empty value is not an enabled
    # signal, so a fresh component simply has no such attribute.
    "ch5-button-list": {"pd-buttonreceivestateiconurl", "pd-receivestateselectedbutton"},
    # Set from the properties panel; see component.py's NEVER_EMIT for why `disabled`
    # cannot be a default (the reference video switcher does NOT have it).
    "ch5-dpad": {"disabled"},
    # The label text typed onto the instance (its ccid_Label is "Tab" to match).
    "ch5-tab-button": {"buttonlabelinnerhtml"},
}

#: Per-child deltas, keyed (tag, child index). Same reasoning: instance edits.
#: The keypad's first TEN children match exactly. Its last three (star, hash, extra)
#: carry an `id` and an empty `labelminor` -- MetaDataResolver.ts writes no labelMinor
#: for those keys at all, and Construct assigns a child an id once it has been touched,
#: so this is instance state rather than a difference in what we generate.
CHILD_DELTAS: dict[tuple[str, int], set[str]] = {
    ("ch5-dpad", 4): {"ccid_ActiveFont"},        # the centre button, styled by hand
    ("ch5-keypad", 10): {"id", "labelminor"},    # buttonstar
    ("ch5-keypad", 11): {"id", "labelminor"},    # buttonhash
    ("ch5-keypad", 12): {"id", "labelmajor", "labelminor"},  # buttonextra (icon, no labels)
}

reference: dict[str, dict] = {}


def walk(elements: list[dict]) -> None:
    for element in elements:
        attributes = element.get("Attributes", {})
        tag = attributes.get("tagName") or name_to_tag.get(element.get("Type", ""))
        if tag in CONTAINER_TAGS and tag not in reference and element.get("Components"):
            reference[tag] = element
        walk(element.get("Components", []))


for path in sorted(REF.glob("*.cuig")):
    raw = path.read_text(encoding="utf-8")
    headers = list(HEADER_RE.finditer(raw))
    for i, m in enumerate(headers):
        if m.group(1) == "PageAttributes":
            end = headers[i + 1].start() if i + 1 < len(headers) else len(raw)
            walk(tomllib.loads(raw[m.end():end]).get("Elements", []))

missing = sorted(set(CONTAINER_TAGS) - set(reference))
assert not missing, f"no reference instance with children found for {missing}"
print(f"reference project: an instance of all {len(reference)} container types")

# --- the fixed child sets match their source -----------------------------------------
assert [k for k, _, _ in DPAD_KEYS] == ["up", "down", "left", "right", "center"], DPAD_KEYS
assert len(KEYPAD_KEYS) == 13, len(KEYPAD_KEYS)
assert KEYPAD_KEYS[9] == ("button0", "0", "+"), KEYPAD_KEYS[9]
assert KEYPAD_KEYS[12][0] == "buttonextra", KEYPAD_KEYS[12]
print("dpad/keypad fixed child sets match MetaDataResolver.ts: OK")

for tag, element in sorted(reference.items()):
    real = element["Attributes"]
    ours = dict(build_component_attributes(
        sdk, tag, component_name=real.get("componentName", "X"),
        element_id=real.get("id", "i0"), label=real.get("ccid_Label")))

    expected = PARENT_DELTAS.get(tag, set())
    parent_missing = set(real) - set(ours) - UNIVERSAL_DELTAS - expected
    parent_extra = set(ours) - set(real)
    assert not parent_missing, f"{tag} parent: reference has {sorted(parent_missing)}, we do not"
    assert not parent_extra, f"{tag} parent: we emit {sorted(parent_extra)}, reference does not"
    stale = expected - set(real)
    assert not stale, f"{tag}: PARENT_DELTAS lists {sorted(stale)}, no longer in the reference"

    # --- children -----------------------------------------------------------------
    real_children = element["Components"]
    ours_children = build_children(sdk, tag, ours)
    assert len(ours_children) == len(real_children), (
        f"{tag}: {len(ours_children)} children generated, reference has {len(real_children)} "
        f"-- the count comes from the parent's own attributes, so this means we read the "
        f"wrong one")

    for index, (real_child, our_child) in enumerate(zip(real_children, ours_children)):
        real_attributes = real_child.get("Attributes", {})
        our_attributes = dict(our_child.attributes)
        assert our_child.type == real_child.get("Type"), (tag, index, our_child.type)

        child_expected = CHILD_DELTAS.get((tag, index), set())
        child_missing = set(real_attributes) - set(our_attributes) - child_expected
        child_extra = set(our_attributes) - set(real_attributes)
        assert not child_missing, f"{tag} child[{index}]: reference has {sorted(child_missing)}"
        assert not child_extra, f"{tag} child[{index}]: we emit {sorted(child_extra)}"

        for key, value in our_attributes.items():
            if key == "id":  # freshly generated per child
                continue
            assert real_attributes[key] == value, (
                f"{tag} child[{index}].{key}: generated {value!r}, "
                f"reference has {real_attributes[key]!r}")

print("every container's parent attributes, child count, child keys and child values "
      "match the reference: OK")

# --- children reach the html too, not only the TOML ----------------------------------
html, _, element = build_component(
    sdk, "ch5-dpad", component_name="Nav", element_id="inav1",
    x=0, y=0, width=150, height=150, z_index=1, resolution=(1280, 800))
assert html.count("<ch5-dpad-button") == 5, html[:200]
assert html.endswith("</ch5-dpad>"), html[-40:]
assert len(element.components) == 5
for key, _, _ in DPAD_KEYS:
    assert f'key="{key}"' in html, key
print("children are emitted into the html view as well as the element tree: OK")

# Child ids are unique -- they are generated per child, and a duplicate would give two
# components the same identity in the page and the contract.
ids = [dict(c.attributes)["id"] for c in element.components]
assert len(set(ids)) == len(ids), ids
print("generated child ids are unique: OK")

print("\nContainer component types: all assertions passed.")
