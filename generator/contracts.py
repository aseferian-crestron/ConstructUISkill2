"""Contract enablement -- Phase 6.

Construct does NOT need us to author the `.cuic` contract file. Two much smaller things
produce a correct contract, both confirmed in C:\\Git\\CCIDE source:

1. **Per-signal enablement on the component.** A join-carrying attribute whose value is
   the sentinel string `"Contract Enabled"` becomes a contract signal. Construct writes
   that literal itself (`Helpers\\ContractGenerationHelper.cs:1177`), and
   `Services\\Contract\\ComponentStrategies\\SimpleComponentStrategy.cs` ->
   `ContractGenerationHelper.GetJoinsFromAttributes` turns every such attribute into a
   join. (That method actually accepts any non-empty, non-numeric value -- a user-typed
   signal name is the other case -- but `"Contract Enabled"` is the contract path.)

2. **`ContractIsStale = "true"` in the `.cuip`.** `Behaviors\\ProjectOpenBehavior.cs:72-99`
   reads it on project open, schedules contract generation, then clears the flag and
   saves. See `mark_contract_stale` below; `project.py::build_project_attributes` already
   writes `"true"` for newly-created projects.

**Which attributes can carry a signal, and under what name**, is pure SDK data -- this
module hardcodes no component-specific knowledge:

  - `component-context.json`'s per-tag `attributeProperties` entries that carry an
    `extenderPosition` ARE the contract-capable signals. That matches Construct's own gate
    in `ContractGenerationHelper.CreateProjectComponent` (`SignalDetails.ExtenderPosition
    > 0`), and those keys already have the storage prefix applied.
  - The prefix rule itself (`PageDesigner.Server\\Providers\\JoinPropertyProvider.cs:151`,
    and `pd-metadata-resolver\\MetaDataResolver.ts:201`): a `direction="state"` join is
    stored as `pd-<name>` so the design-time canvas is not driven by live CH5 signals;
    a `direction="event"` join is stored under its bare name. Verified to hold for every
    schema-backed signal in SDK 2.18.0 (see contracts_task1_signals_test.py), so the two
    sources agree and either could be used -- we read the context keys and cross-check
    them against the schema rather than deriving them, because the context is also the
    only source for the friendly names the contract is keyed by.

One signal in SDK 2.18.0 is context-only: `ch5-media-player`'s `pd-receivestateusemessage`
has no `schema.json` attribute at all, yet the hand-authored reference project
(C:\\Solutions\\ClaudeSamples\\ClaudeCustomModeProject\\Page3.cuig) writes it as a live
`"Contract Enabled"` signal. So a schema entry is treated as corroboration, not a
requirement -- `ContractSignal.schema_backed` records which.
"""
from __future__ import annotations

from dataclasses import dataclass

from sdk import UiSdk
from toml_util import override_attr

CONTRACT_ENABLED = "Contract Enabled"

#: Written by default on a new button -- the two signals a programmer nearly always
#: wires, and (minus `enable`) exactly what the real hand-authored button in
#: "C:\Solutions\CustomerIssues\i12 Multicam\IV Auto-Switch Set ID.cuig" carries.
#: Everything else stays opt-in: an enabled signal a nobody wires still consumes joins.
DEFAULT_BUTTON_SIGNALS = ("Press", "Selected")


@dataclass(frozen=True)
class ContractSignal:
    """One contract-capable signal of one component type."""

    attribute: str          # the key as stored in the .cuig/.cuiw, prefix already applied
    friendly_name: str      # the name the contract uses, e.g. "Press", "Visibility_fb"
    direction: str          # "state" (receive/feedback) or "event" (send)
    category: str           # e.g. "Send Digital Command", "Receive Analog Feedback"
    event_type: str         # "boolean" | "numeric" | "string"
    extender_position: int
    schema_backed: bool     # False for the context-only signals (see module docstring)


def _signal_order(signal: "ContractSignal") -> tuple:
    """Sort key: extenderPosition, then the send event ahead of its own feedback.

    Several signals share one extenderPosition because they are one logical group -- a
    button's Press (sendeventontouch) and Selected (pd-receivestateselected) are both
    position 3, and the receive side names the send side as its `groupName`. Emitting the
    command before the feedback it reports keeps a group readable in the file; the
    alternative (alphabetical) would split groups arbitrarily.
    """
    return (signal.extender_position, signal.direction != "event", signal.attribute)


def _schema_element(sdk: UiSdk, tag_name: str) -> dict:
    for el in sdk.schema["ch5Elements"]["elements"]:
        if el.get("tagName") == tag_name:
            return el
    raise KeyError(
        f"{tag_name!r} is not a CH5 element in schema.json -- component-context.json's "
        f"'global' pseudo-entry, for instance, holds shared attribute metadata rather "
        f"than an element of its own")


def contract_signals(sdk: UiSdk, tag_name: str) -> list[ContractSignal]:
    """Every contract-capable signal of `tag_name`, ordered by `extenderPosition` so that
    emitted attributes land in a stable, Construct-like order.

    Raises KeyError if `tag_name` is not a real CH5 element (see `_schema_element`).
    """
    element = _schema_element(sdk, tag_name)
    attr_defs = {a["name"]: a for a in element["attributes"]}

    # Not every schema element has a component-context entry: the nested sub-element types
    # (ch5-button-list-mode, ch5-button-label, ...) are configured through their parent's
    # traits and have no signals of their own. No context means no contract signals.
    context = sdk.component_context.get(tag_name) or {}

    signals: list[ContractSignal] = []
    for key, props in (context.get("attributeProperties") or {}).items():
        if not isinstance(props, dict) or "extenderPosition" not in props:
            continue

        base = key[3:] if key.startswith("pd-") else key
        join = (attr_defs.get(base) or {}).get("join") or {}
        direction = join.get("direction")
        if direction:
            expected = f"pd-{base}" if direction == "state" else base
            if expected != key:
                raise ValueError(
                    f"{tag_name}: component-context.json stores {key!r} but schema.json's "
                    f"join direction {direction!r} means Construct reads {expected!r} -- "
                    f"writing the former would be silently ignored")
        else:
            # Context-only signal: no schema attribute to corroborate the prefix, so take
            # the direction from the stored key itself (which is what Construct does too --
            # GetCh5AttributeDef strips a leading "pd-" before looking anything up).
            direction = "state" if key.startswith("pd-") else "event"

        signals.append(ContractSignal(
            attribute=key,
            # `contractFriendlyName` is what the generated contract is keyed by where it
            # differs from the display name (ch5-button's receivestateshow shows as
            # "Visibility" but contracts as "Visibility_fb") -- see
            # ContractGenerationHelper.GetJoinsFromAttributes, which passes
            # signalDetails.ContractFriendlyName as the join's contract name.
            friendly_name=props.get("contractFriendlyName") or props.get("friendlyName") or key,
            direction=direction,
            category=props.get("category", ""),
            event_type=props.get("eventType", ""),
            extender_position=int(props["extenderPosition"]),
            schema_backed=bool(join),
        ))

    signals.sort(key=_signal_order)
    return signals


def signal_map(sdk: UiSdk, tag_name: str) -> dict[str, ContractSignal]:
    """`contract_signals` keyed by BOTH the stored attribute name and the friendly name,
    so a caller can name a signal either way ("Press" or "sendeventontouch")."""
    mapping: dict[str, ContractSignal] = {}
    for signal in contract_signals(sdk, tag_name):
        mapping[signal.attribute] = signal
        mapping[signal.friendly_name] = signal
    return mapping


def resolve_signals(sdk: UiSdk, tag_name: str, names) -> list[ContractSignal]:
    """Resolve caller-supplied signal names (friendly or raw attribute, case-insensitive)
    to `ContractSignal`s, in `extenderPosition` order and de-duplicated.

    Raises KeyError naming the valid options -- a typo'd signal name would otherwise
    produce a project whose contract is silently missing a signal, which is only
    discoverable by opening Construct.
    """
    mapping = signal_map(sdk, tag_name)
    lowered = {k.lower(): v for k, v in mapping.items()}

    resolved: list[ContractSignal] = []
    for name in names:
        signal = lowered.get(str(name).lower())
        if signal is None:
            options = ", ".join(sorted({s.friendly_name for s in contract_signals(sdk, tag_name)}))
            raise KeyError(f"{name!r} is not a contract signal of {tag_name} -- valid: {options}")
        if signal not in resolved:
            resolved.append(signal)

    resolved.sort(key=_signal_order)
    return resolved


def enable_contract_signals(
    attrs: list[tuple[str, str]],
    sdk: UiSdk,
    tag_name: str,
    names,
) -> list[tuple[str, str]]:
    """Set each named signal to `"Contract Enabled"` on an element's attribute list,
    in place, returning the same list for chaining.

    Idempotent: a signal already present (enabled, or holding a user-typed signal name)
    is overwritten where it sits rather than appended a second time, so attribute order
    stays stable across repeated calls.
    """
    keys = {k for k, _ in attrs}
    for signal in resolve_signals(sdk, tag_name, names):
        if signal.attribute in keys:
            override_attr(attrs, signal.attribute, CONTRACT_ENABLED)
        else:
            attrs.append((signal.attribute, CONTRACT_ENABLED))
    return attrs


if __name__ == "__main__":
    from sdk import read_sdk

    sdk = read_sdk("2.18.0")
    for tag in ("ch5-button", "ch5-slider"):
        print(f"{tag}:")
        for s in contract_signals(sdk, tag):
            flag = "" if s.schema_backed else "  (context-only)"
            print(f"  {s.extender_position:>2}  {s.friendly_name:<20} {s.attribute:<38} "
                  f"{s.category}{flag}")
