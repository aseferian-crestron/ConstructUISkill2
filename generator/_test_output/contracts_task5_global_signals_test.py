"""Phase 6 task 5: signals inherited from component-context.json's `global` entry.

A component's contract-capable signals are not only the ones listed under its own tag.
`JoinNameProviderHelper.GetAttributeContractInfo` (UiEditor.Server\\Helpers) looks up the
component's own `attributeProperties` first and falls back to `global` -- its own comment
reads "search more specific first, then global".

Missing that fallback is not academic: ch5-color-picker has NO per-tag signal entries at
all, yet the user enabled six signals on it in the reference project. This pins the
fallback, and pins that a tag's own entry still wins where both define the same signal.
"""
import re
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from contracts import contract_signals, signal_map  # noqa: E402
from sdk import read_sdk  # noqa: E402

sdk = read_sdk("2.18.0")

# --- the case that exposed the gap ----------------------------------------------------
picker = signal_map(sdk, "ch5-color-picker")
for attribute, friendly in [
    # the receive side contracts under its own _fb name, not the display name
    ("pd-receivestateredvalue", "RedValue_fb"),
    ("pd-receivestategreenvalue", "GreenValue_fb"),
    ("pd-receivestatebluevalue", "BlueValue_fb"),
    ("sendeventcolorredonchange", "Red Value"),
    ("sendeventcolorgreenonchange", "Green Value"),
    ("sendeventcolorblueonchange", "Blue Value"),
]:
    assert attribute in picker, f"{attribute} must be discoverable via the global entry"
    assert picker[attribute].friendly_name == friendly, (attribute, picker[attribute].friendly_name)
own_picker = sdk.component_context.get("ch5-color-picker", {}).get("attributeProperties") or {}
assert not [k for k, v in own_picker.items() if isinstance(v, dict) and "extenderPosition" in v], \
    "premise: ch5-color-picker declares no SIGNAL entries of its own (it does have other " \
    "attributeProperties -- they just carry no extenderPosition)"
print("ch5-color-picker's six signals resolve entirely through `global`: OK")

# --- global only contributes what the tag's own schema actually supports -------------
# ch5-button has no color joins, so the global color signals must NOT leak onto it.
button = signal_map(sdk, "ch5-button")
for leaked in ("sendeventcolorredonchange", "pd-receivestateredvalue", "pd-receivestateanimate"):
    assert leaked not in button, f"{leaked} leaked onto ch5-button from the global entry"
print("global signals do not leak onto components whose schema lacks the join: OK")

# ...and every global-sourced signal corresponds to a real join attribute of that tag.
by_tag = {e["tagName"]: e for e in sdk.schema["ch5Elements"]["elements"] if e.get("tagName")}
checked = 0
for tag, element in by_tag.items():
    joins = {a["name"] for a in element["attributes"] if (a.get("join") or {}).get("direction")}
    own = set((sdk.component_context.get(tag, {}).get("attributeProperties") or {}))
    for signal in contract_signals(sdk, tag):
        if signal.attribute in own:
            continue  # the tag's own entry, already covered by task 1's test
        base = signal.attribute[3:] if signal.attribute.startswith("pd-") else signal.attribute
        assert base in joins, f"{tag}: global-sourced {signal.attribute!r} is not a join of this tag"
        checked += 1
assert checked > 0, "expected the global entry to contribute signals somewhere"
print(f"all {checked} global-sourced signals map to a real join of their own tag: OK")

# --- a tag's own entry wins over global ----------------------------------------------
# ch5-button defines pd-receivestateshow itself (contract name "Visibility_fb"); the
# global entry defines the same key as plain "Visibility". More specific must win.
assert button["pd-receivestateshow"].friendly_name == "Visibility_fb", \
    button["pd-receivestateshow"].friendly_name
global_props = sdk.component_context["global"]["attributeProperties"]
assert global_props["pd-receivestateshow"].get("friendlyName") == "Visibility", \
    "premise: the global entry names this signal differently"
print("a tag's own signal entry wins over the global one: OK")

# --- every signal the user enabled in the reference project is discoverable ----------
# The real point of the fix: if a signal is set in a hand-authored file, we must be able
# to name it. Anything unreachable here is a component we could not reproduce.
REF = Path(r"C:\Solutions\ClaudeSamples\Components")
HEADER_RE = re.compile(r"^\{(\w+)\}[ \t]*\r?\n?", re.MULTILINE)
name_to_tag = {e.get("name"): e.get("tagName") for e in sdk.schema["ch5Elements"]["elements"]}

def page_attributes(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    headers = list(HEADER_RE.finditer(raw))
    for i, m in enumerate(headers):
        if m.group(1) == "PageAttributes":
            end = headers[i + 1].start() if i + 1 < len(headers) else len(raw)
            return tomllib.loads(raw[m.end():end])
    return {}

unreachable: list[tuple[str, str]] = []
total = 0

def walk(elements: list[dict]) -> None:
    global total
    for element in elements:
        attributes = element.get("Attributes", {})
        tag = attributes.get("tagName") or name_to_tag.get(element.get("Type", "")) or ""
        enabled = [k for k, v in attributes.items() if v == "Contract Enabled"]
        if enabled and tag:
            known = signal_map(sdk, tag)
            for attribute in enabled:
                total += 1
                if attribute not in known:
                    unreachable.append((tag, attribute))
        walk(element.get("Elements", []))

for path in sorted(REF.glob("*.cuig")) + sorted(REF.glob("*.cuiw")):
    walk(page_attributes(path).get("Elements", []))

assert total > 20, f"expected the reference project to have many enabled signals, found {total}"
assert not unreachable, f"signals set in the reference project that we cannot name: {sorted(set(unreachable))}"
print(f"all {total} signals enabled across the reference project are discoverable: OK")

print("\nGlobal signal inheritance: all assertions passed.")
