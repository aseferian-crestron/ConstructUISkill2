"""Phase 6 task 2: turning named signals into "Contract Enabled" attributes."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from contracts import CONTRACT_ENABLED, enable_contract_signals, resolve_signals, signal_map  # noqa: E402
from sdk import read_sdk  # noqa: E402

sdk = read_sdk("2.18.0")

# --- naming: friendly name, raw attribute, and case all resolve to the same signal ----
for name in ("Press", "press", "sendeventontouch", "SendEventOnTouch"):
    (signal,) = resolve_signals(sdk, "ch5-button", [name])
    assert signal.attribute == "sendeventontouch", (name, signal.attribute)
print("friendly name / raw attribute / any case all resolve: OK")

# A name given twice yields one signal, not a duplicated attribute.
assert len(resolve_signals(sdk, "ch5-button", ["Press", "sendeventontouch"])) == 1
print("de-duplicated across naming styles: OK")

# signal_map keys friendly names in the SDK's own spelling, not lower-cased. (It briefly
# did the latter, which made `"Enable" in signal_map(...)` false for every component.)
mapping = signal_map(sdk, "ch5-dpad")
assert "Enable" in mapping and "enable" not in mapping, sorted(mapping)
assert mapping["Enable"].attribute == "pd-receivestateenable"
assert mapping["Digital Start"].attribute == "sendeventonclickstart"
print("signal_map keys friendly names in their real spelling: OK")

# --- an unknown name fails loudly, listing what IS valid -----------------------------
try:
    resolve_signals(sdk, "ch5-button", ["Pressed"])
except KeyError as e:
    message = str(e)
    assert "Pressed" in message, message
    for valid in ("Press", "Selected", "Visibility_fb", "Mode"):
        assert valid in message, f"error should list valid signal {valid!r}: {message}"
    print("unknown signal name raises and lists the valid options: OK")
else:
    raise AssertionError("a misspelled signal name must raise, not be silently dropped")

# --- enabling appends the sentinel, in extenderPosition order ------------------------
attrs = [("id", "i9nb"), ("componentName", "Button1")]
enable_contract_signals(attrs, sdk, "ch5-button", ["Selected", "Press"])
assert attrs[:2] == [("id", "i9nb"), ("componentName", "Button1")], "existing attrs disturbed"
assert attrs[2:] == [
    ("sendeventontouch", CONTRACT_ENABLED),
    ("pd-receivestateselected", CONTRACT_ENABLED),
], attrs[2:]
print("signals appended as 'Contract Enabled' in extenderPosition order: OK")

# --- idempotent: re-enabling overwrites in place, never appends a duplicate ----------
before = list(attrs)
enable_contract_signals(attrs, sdk, "ch5-button", ["Press", "Selected"])
assert attrs == before, f"re-enabling must be a no-op, got {attrs}"
print("re-enabling the same signals is a no-op: OK")

# A signal already holding a user-typed join name is overwritten where it sits, so the
# attribute order a real file already has is preserved.
attrs = [("sendeventontouch", "MyCustomSignal"), ("id", "i9nb")]
enable_contract_signals(attrs, sdk, "ch5-button", ["Press"])
assert attrs == [("sendeventontouch", CONTRACT_ENABLED), ("id", "i9nb")], attrs
print("an existing signal attribute is overridden in place, not re-appended: OK")

# --- the empty case writes nothing ----------------------------------------------------
attrs = [("id", "i9nb")]
enable_contract_signals(attrs, sdk, "ch5-button", [])
assert attrs == [("id", "i9nb")], attrs
print("no signals requested writes no attributes: OK")

# --- generic across component types, not button-specific -----------------------------
# A slider's analog feedback is named "Lower Touch fb", NOT the "Value" its attribute
# spells -- exactly why signals resolve by the SDK's own names rather than by guesswork.
attrs = [("id", "ila3")]
enable_contract_signals(attrs, sdk, "ch5-slider", ["Lower Touch fb", "sendeventonchange"])
assert attrs == [
    ("id", "ila3"),
    ("sendeventonchange", CONTRACT_ENABLED),
    ("pd-receivestatevalue", CONTRACT_ENABLED),
], attrs
print("works on another component type (ch5-slider analog pair): OK")

print("\nContract enablement: all assertions passed.")
