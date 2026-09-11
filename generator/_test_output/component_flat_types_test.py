"""Generic component builder: every flat type diffed against the reference project.

The reference project (C:\\Solutions\\ClaudeSamples\\Components) holds a real,
Construct-authored instance of each component type, which is the only oracle for what a
generated one should look like. This test recomputes the comparison from those files on
every run rather than restating expectations by hand, so a change the user makes in
Construct shows up here instead of drifting silently.

EXPECTED_DELTAS records, per type, what a generated component legitimately does NOT
share with its reference instance, and why. Everything else must match exactly.
"""
import re
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from component import CONTAINER_TAGS, PROFILES, SYNC_TAGS, build_component_attributes  # noqa: E402
from sdk import read_sdk  # noqa: E402

sdk = read_sdk("2.18.0")
REF = Path(r"C:\Solutions\ClaudeSamples\Components")
HEADER_RE = re.compile(r"^\{(\w+)\}[ \t]*\r?\n?", re.MULTILINE)
name_to_tag = {e.get("name"): e.get("tagName") for e in sdk.schema["ch5Elements"]["elements"]}

#: Universal: every reference instance carries `oldID`, which records the id a component
#: had before it was duplicated. A freshly-created component has no previous id.
UNIVERSAL_DELTAS = {"oldID"}

#: Per-type, `(in the reference but not generated, generated but not in the reference)`.
EXPECTED_DELTAS: dict[str, tuple[set[str], set[str]]] = {
    # Content the user typed into the instance; a fresh component has none of it.
    "ch5-qrcode": ({"qrcode", "size"}, set()),
    "ch5-text": ({"labelinnerhtml"}, set()),
    "ch5-toggle": ({"label", "labeloff", "labelon", "ccid_customSizeSet"}, set()),
    # State flags Construct sets when the user acts on the instance: demoMode is the
    # media player's preview toggle, disabled is set from the properties panel.
    "ch5-media-player": ({"demoMode"}, set()),
    "ch5-signal-level-gauge": ({"disabled"}, set()),
    # We emit showtickvalues from its non-null schema default; the reference slider does
    # not carry it. UNEXPLAINED -- the slider mixin is the likeliest place it is dropped,
    # and this is the one delta here that is a suspected defect rather than instance state.
    "ch5-slider": (set(), {"showtickvalues"}),
    # The reference's first childless button is the IMAGE variant (assetid, pageflip,
    # image sync sectors); build_component delegates to ch5_button.py, whose variants are
    # covered exactly by phase4_smoke_test against the plain Button1.
    "ch5-button": ({"ccid_customSizeSet", "pd-receivestateiconclass"}, set()),
}

reference: dict[str, dict] = {}


FLAT_TAGS = set(PROFILES) - set(CONTAINER_TAGS)


def walk(elements: list[dict]) -> None:
    for element in elements:
        attributes = element.get("Attributes", {})
        tag = attributes.get("tagName") or name_to_tag.get(element.get("Type", ""))
        # "Flat" means no COMPONENT children; ch5-subpage-reference-list carries a lone
        # textnode, which is not a component and does not make it a container.
        component_children = [c for c in element.get("Components", [])
                              if c.get("Type") != "textnode"]
        if tag in FLAT_TAGS and not component_children and tag not in reference:
            reference[tag] = attributes
        walk(element.get("Components", []))


for path in sorted(REF.glob("*.cuig")):
    raw = path.read_text(encoding="utf-8")
    headers = list(HEADER_RE.finditer(raw))
    for i, m in enumerate(headers):
        if m.group(1) == "PageAttributes":
            end = headers[i + 1].start() if i + 1 < len(headers) else len(raw)
            walk(tomllib.loads(raw[m.end():end]).get("Elements", []))

missing_types = sorted(FLAT_TAGS - set(reference))
assert not missing_types, f"no reference instance found for {missing_types}"
print(f"reference project: a flat instance of all {len(reference)} profiled types")

exact = 0
for tag, real in sorted(reference.items()):
    ours = dict(build_component_attributes(
        sdk, tag, component_name=real.get("componentName", "X"),
        element_id=real.get("id", "i0"), label=real.get("ccid_Label")))

    expected_missing, expected_extra = EXPECTED_DELTAS.get(tag, (set(), set()))
    # The image-sector sync keys on the button are part of its image variant.
    expected_missing = expected_missing | {
        k for k in real if k.startswith("ccid_sync_") and "imagesector" in k
    } if tag == "ch5-button" else expected_missing

    missing = set(real) - set(ours) - UNIVERSAL_DELTAS - expected_missing
    extra = set(ours) - set(real) - expected_extra
    assert not missing, f"{tag}: reference has attributes we do not generate: {sorted(missing)}"
    assert not extra, f"{tag}: we generate attributes the reference lacks: {sorted(extra)}"

    # A recorded delta that stops being true is also a failure -- it means the reference
    # changed and the note is now misleading.
    stale = (expected_missing - set(real)) | (expected_extra - set(ours))
    assert not stale, f"{tag}: EXPECTED_DELTAS lists {sorted(stale)}, no longer true -- update it"

    if not expected_missing and not expected_extra:
        exact += 1
print(f"every flat type matches its reference instance ({exact} with no recorded delta at all): OK")

# --- values, not just keys, across EVERY type -----------------------------------------
# Matching key sets while getting the values wrong would sail through the check above.
#: Values that legitimately differ: the instance was configured by hand after creation.
VALUE_DELTAS = {
    # The reference's first childless button is the image variant.
    ("ch5-button", "ccid_imageIconType"), ("ch5-button", "assetid"),
    # `size`: we always write "custom", because an explicit width/height is only
    # honoured in that mode (see component.py -- it is what makes the canvas adorner
    # match what the component actually renders). The reference instances that were
    # never resized still carry the preset they were dropped with, and the text input
    # carries the "small" preset its user chose.
    ("ch5-animation", "size"), ("ch5-dpad", "size"), ("ch5-signal-level-gauge", "size"),
    ("ch5-slider", "size"), ("ch5-textinput", "size"), ("ch5-video", "size"),
    ("ch5-wifi-signal-level-gauge", "size"),
    # The reference widget list was configured: 5 items, pointed at a real widget.
    ("ch5-subpage-reference-list", "numberofitems"),
    ("ch5-subpage-reference-list", "widgetid"),
}
#: Per-instance identity/state, never expected to match.
PER_INSTANCE = {"devicesVisited", "ccid_Label", "componentName", "id"}

checked = 0
for tag, real in sorted(reference.items()):
    ours = dict(build_component_attributes(
        sdk, tag, component_name=real.get("componentName", "X"),
        element_id=real.get("id", "i0"), label=real.get("ccid_Label")))
    for key, value in ours.items():
        if key in PER_INSTANCE or key not in real:
            continue
        if (tag, key) in VALUE_DELTAS:
            assert real[key] != value, \
                f"({tag}, {key}) is recorded as differing but now matches -- drop it from VALUE_DELTAS"
            continue
        assert real[key] == value, f"{tag}.{key}: generated {value!r}, reference has {real[key]!r}"
        checked += 1
print(f"{checked} attribute VALUES match the reference across all {len(reference)} types: OK")

# --- the sync block is button-only ----------------------------------------------------
assert SYNC_TAGS == ("ch5-button",), SYNC_TAGS
for tag, real in reference.items():
    has_sync = any(k.startswith("ccid_sync_") for k in real)
    assert has_sync == (tag in SYNC_TAGS), \
        f"{tag}: reference {'has' if has_sync else 'has no'} ccid_sync_* but SYNC_TAGS says otherwise"
print("only ch5-button carries the ccid_sync_* block, in reference and generator alike: OK")

# Container types are covered by component_container_types_test.py.

print("\nFlat component types: all assertions passed.")
