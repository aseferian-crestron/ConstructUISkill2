"""Phase 6 task 1: contract-signal discovery from the SDK.

Pins three things:
  1. ch5-button's exact five contract-capable signals (the set Construct's own UI offers),
     with the pd- prefix rule applied as the file actually stores them.
  2. Catalog-wide: for EVERY tag in component-context.json, a signal key's pd- prefix
     agrees with its schema.json join direction -- the invariant that makes the lookup
     safe for component types we have not hand-checked.
  3. The one real exception found while building this (ch5-media-player's
     pd-receivestateusemessage is context-only, absent from schema.json, yet written as a
     live "Contract Enabled" signal in the reference project) stays supported.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from contracts import contract_signals, signal_map  # noqa: E402
from sdk import read_sdk  # noqa: E402

sdk = read_sdk("2.18.0")

# --- 1. ch5-button's exact signal set ------------------------------------------------
signals = contract_signals(sdk, "ch5-button")
by_attr = {s.attribute: s for s in signals}

expected = {
    "sendeventonshow": ("Visibility", "event", 1),
    "pd-receivestateshow": ("Visibility_fb", "state", 1),
    "sendeventontouch": ("Press", "event", 3),
    "pd-receivestateselected": ("Selected", "state", 3),
    "pd-receivestatemode": ("Mode", "state", 9),
}
assert set(by_attr) == set(expected), (
    f"ch5-button's contract signals changed: {sorted(set(by_attr) ^ set(expected))}")
for attr, (friendly, direction, position) in expected.items():
    s = by_attr[attr]
    assert s.friendly_name == friendly, (attr, s.friendly_name, friendly)
    assert s.direction == direction, (attr, s.direction, direction)
    assert s.extender_position == position, (attr, s.extender_position, position)
print(f"ch5-button: {len(signals)} contract signals, names/directions/positions exact: OK")

# Returned in extenderPosition order, so emitted attributes land in a stable order.
positions = [s.extender_position for s in signals]
assert positions == sorted(positions), f"signals must be ordered by extenderPosition, got {positions}"
print("ordered by extenderPosition: OK")

# `pd-receivestateshow`'s contract name differs from its display name -- the contract
# (and therefore the programmer) sees "Visibility_fb", so that is what we key on.
assert by_attr["pd-receivestateshow"].friendly_name == "Visibility_fb"
assert by_attr["sendeventonshow"].friendly_name == "Visibility"
print("contractFriendlyName wins over friendlyName where they differ: OK")

# --- 2. catalog-wide prefix-rule agreement -------------------------------------------
by_tag = {e["tagName"]: e for e in sdk.schema["ch5Elements"]["elements"] if e.get("tagName")}
checked = 0
context_only: list[tuple[str, str]] = []
for tag in by_tag:
    for s in contract_signals(sdk, tag):
        base = s.attribute[3:] if s.attribute.startswith("pd-") else s.attribute
        attr_def = next((a for a in by_tag[tag]["attributes"] if a["name"] == base), None)
        if attr_def is None or not (attr_def.get("join") or {}).get("direction"):
            context_only.append((tag, s.attribute))
            continue
        direction = attr_def["join"]["direction"]
        want = f"pd-{base}" if direction == "state" else base
        assert s.attribute == want, (
            f"{tag}: component-context key {s.attribute!r} disagrees with schema.json's "
            f"join direction {direction!r} (expected {want!r}) -- Construct would ignore "
            f"the attribute we write")
        assert s.direction == direction, (tag, s.attribute, s.direction, direction)
        checked += 1
assert checked > 100, f"expected the whole catalog to be exercised, only checked {checked}"
print(f"prefix rule agrees with schema join direction for all {checked} schema-backed signals: OK")

# --- 3. the one known context-only signal --------------------------------------------
assert context_only == [("ch5-media-player", "pd-receivestateusemessage")], (
    f"the set of context-only (schema-unbacked) signals changed: {context_only}")
mp = signal_map(sdk, "ch5-media-player")
assert "pd-receivestateusemessage" in mp, "a context-only signal must still be usable"
assert mp["pd-receivestateusemessage"].schema_backed is False
assert mp["pd-receivestatecrpc"].schema_backed is True
print("context-only signal (media-player usemessage) supported and flagged: OK")

# The `global` pseudo-entry in component-context.json is not an element and has no
# schema counterpart -- asking for it is a caller error, not an empty list.
try:
    contract_signals(sdk, "global")
except KeyError:
    print("'global' pseudo-tag rejected: OK")
else:
    raise AssertionError("contract_signals('global') must raise -- it is not an element")

print("\nContract signal discovery: all assertions passed.")
