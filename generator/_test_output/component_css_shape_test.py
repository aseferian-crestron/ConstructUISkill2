"""Every type's generated CSS is diffed against the reference project's instances.

The attribute comparison (component_flat_types_test / component_container_types_test)
has always run against the sample. The CSS never was -- and every sizing bug the user
had to find by eye lived there: the missing render-size variables, `size="custom"` on
components that cannot be custom-sized, an explicit height on aspect-locked types, and
a widget list 816px wide that drops at 200px.

What is compared is the SHAPE of the `#id` rule, not the numbers: which of
width/height a real instance carries, and whether each is a pixel value or the literal
`auto`. The numbers themselves are per-instance (the user resized those components),
but the shape is what the component type demands, and getting it wrong is what makes
Construct draw a selection adorner that does not match the component.
"""
import re
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import layout  # noqa: E402
from component import PROFILES, build_component, default_style_size  # noqa: E402
from sdk import read_sdk  # noqa: E402

sdk = read_sdk("2.18.0")
REF = Path(r"C:\Solutions\ClaudeSamples\Components")
HEADER_RE = re.compile(r"^\{(\w+)\}[ \t]*\r?\n?", re.MULTILINE)
name_to_tag = {e.get("name"): e.get("tagName") for e in sdk.schema["ch5Elements"]["elements"]}


def dimension_shape(declarations: str) -> dict[str, str]:
    """{"width": "px"|"auto", ...} for whichever dimensions a rule states."""
    shape = {}
    for name in ("width", "height"):
        m = re.search(rf"(?:^|;)\s*{name}\s*:\s*([^;]+)", declarations)
        if m:
            shape[name] = "auto" if m.group(1).strip() == "auto" else "px"
    return shape


#: Types whose real instances disagree with each other, or where the reference has no
#: instance to compare. Recorded rather than skipped silently.
NO_REFERENCE: set[str] = {
    # No instance anywhere in THIS reference project -- see component_flat_types_
    # test.py's NO_REFERENCE_IN_THIS_PROJECT (same gap, same reason, 2026-09-11).
    # Confirmed instead via component.py::writes_css_size(sdk, "ch5-image") ==
    # (True, True) -- resizable, writes both width and height, no aspect lock.
    "ch5-image",
}

reference_shapes: dict[str, dict[str, str]] = {}
for path in sorted(REF.glob("*.cuig")):
    raw = path.read_text(encoding="utf-8")
    headers = list(HEADER_RE.finditer(raw))
    sections = {}
    for i, m in enumerate(headers):
        end = headers[i + 1].start() if i + 1 < len(headers) else len(raw)
        sections[m.group(1)] = raw[m.end():end]
    if "PageAttributes" not in sections:
        continue
    block = layout.find_media_block(sections["Css"], "(max-width: 99999px)") or ""
    rules = dict(re.findall(r"#([A-Za-z0-9_]+)\s*\{([^{}]*)\}", block))

    def walk(elements):
        for element in elements:
            attributes = element.get("Attributes", {})
            tag = attributes.get("tagName") or name_to_tag.get(element.get("Type", ""))
            rule = rules.get(attributes.get("id", ""))
            if tag in PROFILES and rule is not None and tag not in reference_shapes:
                reference_shapes[tag] = dimension_shape(rule)
            walk(element.get("Components", []))

    walk(tomllib.loads(sections["PageAttributes"]).get("Elements", []))

missing = sorted(set(PROFILES) - set(reference_shapes) - NO_REFERENCE)
assert not missing, f"no reference CSS rule found for {missing}"
print(f"reference project: a CSS rule for all {len(reference_shapes)} types")

mismatches = []
for tag, expected in sorted(reference_shapes.items()):
    _, css, _ = build_component(
        sdk, tag, component_name="X", element_id="ix1",
        x=10, y=20, width=240, height=160, z_index=1, resolution=(1280, 800))
    ours = dimension_shape(re.search(r"#ix1\{([^}]*)\}", css).group(1))
    if ours != expected:
        mismatches.append((tag, ours, expected))

assert not mismatches, "generated CSS shape differs from the reference:\n" + "\n".join(
    f"  {tag}: generated {ours}, reference has {expected}" for tag, ours, expected in mismatches)
print(f"all {len(reference_shapes)} types emit the same width/height shape as the reference: OK")

# --- the drop size the SDK states is the one we use ----------------------------------
# Reading sizes off the reference instances answers the wrong question: they have been
# resized. A widget list reads 816px wide there and drops at 200px.
for tag, style in sorted((t, default_style_size(sdk, t)) for t in PROFILES):
    if not style:
        continue
    write_width, write_height = None, None
    _, css, _ = build_component(sdk, tag, component_name="X", element_id="ix2",
                                x=0, y=0, width=240, height=160, z_index=1,
                                resolution=(1280, 800))
    ours = dimension_shape(re.search(r"#ix2\{([^}]*)\}", css).group(1))
    expected = {k: ("auto" if v == "auto" else "px") for k, v in style.items()}
    assert ours == expected, f"{tag}: generated {ours}, defaults.style implies {expected}"
print("every type with a defaults.style matches its declared shape: OK")

# The specific regression the user reported twice.
assert default_style_size(sdk, "ch5-subpage-reference-list") == {"width": "200px", "height": "auto"}
_, list_css, _ = build_component(sdk, "ch5-subpage-reference-list", component_name="W",
                                 element_id="iw1", x=0, y=0, width=200, height=999,
                                 z_index=1, resolution=(1280, 800))
list_rule = re.search(r"#iw1\{([^}]*)\}", list_css).group(1)
assert "width: 200px" in list_rule and "height: auto" in list_rule, list_rule
print("an empty widget list is 200px wide with auto height, as it drops in Construct: OK")

print("\nCSS shape vs reference: all assertions passed.")
