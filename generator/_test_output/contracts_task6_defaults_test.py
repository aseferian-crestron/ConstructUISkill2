"""Phase 6 task 6: the per-component default signal sets, checked against the reference.

The user set the intended contract signals on every component in
C:\\Solutions\\ClaudeSamples\\Components (2026-09-10). That project is the ground truth for
what a generated component should expose, so this test does not restate the defaults by
hand -- it recomputes them from the reference files and asserts DEFAULT_SIGNALS matches.
If the user changes their mind in Construct, this fails and tells us what changed.
"""
import re
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from contracts import (  # noqa: E402
    DEFAULT_SIGNALS, NO_SIGNALS_BY_DESIGN, default_signals_for, resolve_signals, signal_map,
)
from sdk import read_sdk  # noqa: E402

sdk = read_sdk("2.18.0")
REF = Path(r"C:\Solutions\ClaudeSamples\Components")
HEADER_RE = re.compile(r"^\{(\w+)\}[ \t]*\r?\n?", re.MULTILINE)
name_to_tag = {e.get("name"): e.get("tagName") for e in sdk.schema["ch5Elements"]["elements"]}

# --- recompute the defaults straight from the reference project ----------------------
from_reference: dict[str, set[str]] = {}

def walk(elements: list[dict]) -> None:
    for element in elements:
        attributes = element.get("Attributes", {})
        tag = attributes.get("tagName") or name_to_tag.get(element.get("Type", "")) or ""
        enabled = {k for k, v in attributes.items() if v == "Contract Enabled"}
        if tag and enabled:
            previous = from_reference.get(tag)
            assert previous is None or previous == enabled, (
                f"{tag} has two different signal sets in the reference project: "
                f"{sorted(previous)} vs {sorted(enabled)} -- the default is ambiguous")
            from_reference[tag] = enabled
        walk(element.get("Elements", []))

for path in sorted(REF.glob("*.cuig")) + sorted(REF.glob("*.cuiw")):
    raw = path.read_text(encoding="utf-8")
    headers = list(HEADER_RE.finditer(raw))
    for i, m in enumerate(headers):
        if m.group(1) == "PageAttributes":
            end = headers[i + 1].start() if i + 1 < len(headers) else len(raw)
            walk(tomllib.loads(raw[m.end():end]).get("Elements", []))

assert from_reference, "found no enabled signals in the reference project at all"
print(f"reference project: {len(from_reference)} component types carry signals")

# --- DEFAULT_SIGNALS must resolve to exactly those attributes ------------------------
assert set(DEFAULT_SIGNALS) - set(NO_SIGNALS_BY_DESIGN) == set(from_reference), (
    "DEFAULT_SIGNALS and the reference project disagree on WHICH types carry signals: "
    f"only in defaults {sorted(set(DEFAULT_SIGNALS) - set(NO_SIGNALS_BY_DESIGN) - set(from_reference))}, "
    f"only in reference {sorted(set(from_reference) - set(DEFAULT_SIGNALS))}")

for tag, expected in sorted(from_reference.items()):
    resolved = {s.attribute for s in resolve_signals(sdk, tag, DEFAULT_SIGNALS[tag])}
    assert resolved == expected, (
        f"{tag}: default resolves to {sorted(resolved)}, reference has {sorted(expected)}")
print("every default resolves to exactly the reference project's signals: OK")

# --- the types the user confirmed need none ------------------------------------------
for tag in NO_SIGNALS_BY_DESIGN:
    assert DEFAULT_SIGNALS[tag] == (), tag
    assert default_signals_for(tag) == (), tag
    # ...and this is a real decision, not a vacuous one: these types DO have signals
    # available, the user's judgement is that a generated instance should expose none.
    assert signal_map(sdk, tag), f"{tag} has no signals at all -- listing it says nothing"
print(f"{len(NO_SIGNALS_BY_DESIGN)} types explicitly default to no signals: OK")

# --- lookup behaviour -----------------------------------------------------------------
assert default_signals_for("ch5-button") == ("Press", "Selected")
assert default_signals_for("ch5-does-not-exist") == (), "an unknown type must default to none"
print("default_signals_for: known, explicitly-none, and unknown all behave: OK")

# --- an ambiguous friendly name must raise, not silently pick one --------------------
# ch5-button-list has two distinct signals both named "ItemSelected"
# (pd-buttonreceivestateselected and pd-receivestateselectedbutton).
try:
    resolve_signals(sdk, "ch5-button-list", ["ItemSelected"])
except KeyError as e:
    assert "pd-buttonreceivestateselected" in str(e) and "pd-receivestateselectedbutton" in str(e), str(e)
    print("an ambiguous friendly name raises and names both attributes: OK")
else:
    raise AssertionError("'ItemSelected' is ambiguous on ch5-button-list and must not resolve silently")

# The unambiguous half still works, and the raw attribute always works.
assert [s.attribute for s in resolve_signals(sdk, "ch5-button-list", ["pd-receivestateselectedbutton"])] \
    == ["pd-receivestateselectedbutton"]
print("the raw attribute name disambiguates: OK")

print("\nPer-component defaults: all assertions passed.")
