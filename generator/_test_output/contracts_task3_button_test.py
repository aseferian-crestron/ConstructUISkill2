"""Phase 6 task 3: the button builder's contract signals, and mark_contract_stale."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ch5_button import build_default_button_attributes, build_default_button_element  # noqa: E402
from contracts import CONTRACT_ENABLED, DEFAULT_BUTTON_SIGNALS, mark_contract_stale  # noqa: E402
from project import build_project_attributes, write_cuip  # noqa: E402
from sdk import read_sdk  # noqa: E402

sdk = read_sdk("2.18.0")

OUT = Path(__file__).resolve().parent / "ContractsTask3"
OUT.mkdir(parents=True, exist_ok=True)


def signal_attrs(attrs: list[tuple[str, str]]) -> dict[str, str]:
    return {k: v for k, v in attrs if v == CONTRACT_ENABLED}


# --- the default button: Press + Selected, and nothing else --------------------------
attrs = build_default_button_attributes(sdk, component_name="Button1", element_id="i9nb")
assert signal_attrs(attrs) == {
    "sendeventontouch": CONTRACT_ENABLED,
    "pd-receivestateselected": CONTRACT_ENABLED,
}, signal_attrs(attrs)
assert DEFAULT_BUTTON_SIGNALS == ("Press", "Selected")
print("default button carries exactly Press + Selected: OK")

# No attribute is written twice -- the signal keys must not collide with the base payload.
keys = [k for k, _ in attrs]
assert len(keys) == len(set(keys)), f"duplicate attribute keys: {sorted({k for k in keys if keys.count(k) > 1})}"
print(f"{len(keys)} attributes, all unique: OK")

# Signals come LAST, after everything including the ccid_sync_* block -- which is where
# Construct itself puts them: all six real buttons in the reference project end with
# exactly `sendeventontouch`, `pd-receivestateselected` (verified 2026-09-10; before that
# the position was a guess, and it was the wrong one).
assert keys[-2:] == ["sendeventontouch", "pd-receivestateselected"], keys[-4:]
sync_first = next(i for i, k in enumerate(keys) if k.startswith("ccid_sync_"))
sync_last = max(i for i, k in enumerate(keys) if k.startswith("ccid_sync_"))
assert all(keys[i].startswith("ccid_sync_") for i in range(sync_first, sync_last + 1)), \
    "the ccid_sync_* block must stay contiguous"
print("signals emitted last, after an unbroken ccid_sync_* block: OK")

# --- opting out, and opting in to more ------------------------------------------------
attrs = build_default_button_attributes(
    sdk, component_name="Button1", element_id="i9nb", contract_signals=())
assert signal_attrs(attrs) == {}, signal_attrs(attrs)
print("contract_signals=() writes no signals: OK")

attrs = build_default_button_attributes(
    sdk, component_name="Button1", element_id="i9nb",
    contract_signals=("Press", "Selected", "Visibility_fb", "Mode"))
assert set(signal_attrs(attrs)) == {
    "sendeventontouch", "pd-receivestateselected", "pd-receivestateshow", "pd-receivestatemode",
}, signal_attrs(attrs)
print("extra signals opt in by name: OK")

# --- the element builder passes them through -----------------------------------------
html, css, element = build_default_button_element(
    sdk, component_name="Button1", element_id="i9nb",
    x=58, y=58, width=84, height=42, z_index=1, resolution=(1280, 800),
    contract_signals=("Press",))
assert 'sendeventontouch="Contract Enabled"' in html, html[:400]
assert 'pd-receivestateselected' not in html
assert signal_attrs(element.attributes) == {"sendeventontouch": CONTRACT_ENABLED}
print("build_default_button_element passes signals into html + element: OK")

# --- mark_contract_stale --------------------------------------------------------------
cuip = OUT / "Task3.cuip"
project_attrs, resolution_source = build_project_attributes(
    name="Task3", sdk_id="CH5:2.18.0", contract_is_stale=False)
write_cuip(cuip, project_attrs, resolution_source)
before = cuip.read_text(encoding="utf-8")
assert 'ContractIsStale = "false"' in before

mark_contract_stale(cuip)
text = cuip.read_text(encoding="utf-8")
assert 'ContractIsStale = "true"' in text, text[-400:]
assert text.count("ContractIsStale") == 1, "the flag must be overridden, not appended twice"
print("mark_contract_stale flips the .cuip flag in place: OK")

# Every other byte of the file -- including the FileMetadata timestamps, which a
# careless rewrite would silently refresh -- survives unchanged.
assert text == before.replace('ContractIsStale = "false"', 'ContractIsStale = "true"'),     "mark_contract_stale changed something other than the flag"
print("no other project attribute or metadata timestamp disturbed: OK")

# Idempotent.
mark_contract_stale(cuip)
assert cuip.read_text(encoding="utf-8") == text, "re-marking a stale project must be a no-op"
print("mark_contract_stale is idempotent: OK")

print("\nButton contract wiring: all assertions passed.")
