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

#: Component types that deliberately expose NO contract signals by default. Each of these
#: HAS signals available -- this is the user's judgement (2026-09-10) that a generated
#: instance should not enable any, not an oversight or a component with nothing to offer.
NO_SIGNALS_BY_DESIGN = (
    "ch5-video",
    "ch5-video-switcher",
    "ch5-subpage-reference-list",
    "ch5-background",
    "ch5-datetime",
    "ch5-qrcode",
)

#: The signals a newly-generated component of each type exposes, transcribed from the
#: user's reference project (C:\Solutions\ClaudeSamples\Components), where they set the
#: intended contract signals on every component by hand on 2026-09-10. That project is
#: the ground truth: contracts_task6_defaults_test.py recomputes this table from those
#: files on every run, so if the user changes their mind in Construct the test says so.
#:
#: Names are the SDK's own contract names; see `resolve_signals` for how they resolve
#: (raw attribute names work too, and are required where a friendly name is ambiguous).
DEFAULT_SIGNALS: dict[str, tuple[str, ...]] = {
    "ch5-button": ("Press", "Selected"),
    "ch5-button-list": ("ItemPress",),
    "ch5-color-chip": ("Red Value", "Green Value", "Blue Value",
                       "RedValue_fb", "GreenValue_fb", "BlueValue_fb"),
    "ch5-color-picker": ("Red Value", "Green Value", "Blue Value",
                         "RedValue_fb", "GreenValue_fb", "BlueValue_fb"),
    "ch5-dpad": ("Digital Start",),
    "ch5-keypad": ("Digital Start",),
    "ch5-media-player": ("CRPC", "CRPC_FB", "Message_FB", "Refresh", "Offline",
                         "Use_Message", "Player_Name"),
    "ch5-segmented-gauge": ("Touch", "Touch fb"),
    "ch5-signal-level-gauge": ("Signal Value",),
    "ch5-slider": ("Lower Touch", "Lower Touch fb"),
    "ch5-tab-button": ("_Press", "_Selected"),
    "ch5-text": ("Indirect Rich Text",),
    "ch5-textinput": ("Output Text", "Indirect Text"),
    "ch5-toggle": ("Press", "Selected"),
    "ch5-wifi-signal-level-gauge": ("Signal Value",),
    **{tag: () for tag in NO_SIGNALS_BY_DESIGN},
}

#: Backwards-compatible alias for the button's entry (ch5_button.py's parameter default).
DEFAULT_BUTTON_SIGNALS = DEFAULT_SIGNALS["ch5-button"]


def default_signals_for(tag_name: str) -> tuple[str, ...]:
    """The default signal names for `tag_name`, or `()` for a type the reference project
    does not cover. `()` is the safe default: no signals enabled is always a valid
    component, whereas guessing would put joins in a contract nobody asked for."""
    return DEFAULT_SIGNALS.get(tag_name, ())


@dataclass(frozen=True)
class ContractSignal:
    """One contract-capable signal of one component type."""

    attribute: str          # the key as stored in the .cuig/.cuiw, prefix already applied
    friendly_name: str      # the name the contract uses, e.g. "Press", "Visibility_fb"
    direction: str          # "state" (receive/feedback) or "event" (send)
    category: str           # e.g. "Send Digital Command", "Receive Analog Feedback"
    event_type: str         # "boolean" | "numeric" | "string"
    extender_position: int  # 0 when the entry declares none (see _is_signal_entry)
    schema_backed: bool     # False for the context-only signals (see module docstring)
    remove_on_contract_use: bool  # Construct's own strategy supplies the join instead


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


def _is_signal_entry(props) -> bool:
    """Whether a component-context `attributeProperties` entry describes a contract signal.

    The gate is the entry's `category`, not `extenderPosition`. An earlier version
    required `extenderPosition`, copying
    `ContractGenerationHelper.CreateProjectComponent`'s `ExtenderPosition > 0` -- but that
    gate governs only the project-level extender, not what a component can expose.
    `GetJoinsFromAttributes`, the method that actually turns attributes into joins, needs
    nothing more than a resolvable `SignalDetails`. It cost two real signals: `ch5-dpad`
    and `ch5-keypad`'s `sendeventonclickstart` ("Digital Start") carry no
    `extenderPosition` -- they are marked `removeOnContractUse` instead -- yet the
    reference project enables them.

    Merely HAVING a category is not enough either: 179 entries in SDK 2.18.0 are
    categorised "Interactions" (others "Button Attributes"/"Transitions") -- ordinary
    design-time properties like `orientation`, `customvstheme` and `z-index` that carry a
    friendlyName too. Every real signal's category names a direction and a type instead:
    "Send Digital Command", "Receive Analog Feedback", "Receive Serial Feedback", and so
    on. That prefix is the discriminator.
    """
    if not isinstance(props, dict):
        return False
    category = props.get("category", "")
    return category.startswith(("Send ", "Receive "))


def contract_signals(sdk: UiSdk, tag_name: str) -> list[ContractSignal]:
    """Every contract-capable signal of `tag_name`, ordered by `extenderPosition` so that
    emitted attributes land in a stable, Construct-like order.

    Signals come from TWO places, exactly as Construct resolves them in
    `Helpers\\JoinNameProviderHelper.cs::GetAttributeContractInfo` -- "search more specific
    first, then global": the tag's own `attributeProperties`, then `component-context`'s
    shared `global` entry for anything the tag's own entry does not define. The global
    half is not optional -- `ch5-color-picker` has no per-tag entries whatsoever, and all
    six signals the reference project enables on it resolve through `global`.

    A global entry only applies where the tag's own `schema.json` actually has that join
    (the global list spans colour, animation, focus and url signals that most components
    do not have), which is the same restriction Construct gets from
    `JoinPropertyProvider.GetElementsJoinProperties` driving which attributes it consults.

    Raises KeyError if `tag_name` is not a real CH5 element (see `_schema_element`).
    """
    element = _schema_element(sdk, tag_name)
    attr_defs = {a["name"]: a for a in element["attributes"]}

    # Not every schema element has a component-context entry: the nested sub-element types
    # (ch5-button-list-mode, ch5-button-label, ...) are configured through their parent's
    # traits and have no signals of their own. No context means no contract signals.
    context = sdk.component_context.get(tag_name) or {}

    def is_join_key(key: str) -> bool:
        """A contract signal must be a JOIN. Plenty of ordinary attributes (orientation,
        shape, size, ...) carry a friendlyName and category in component-context too, and
        admitting those would offer the caller signals Construct cannot generate. An
        attribute absent from schema.json ENTIRELY is the context-only case and is kept
        (see the module docstring's ch5-media-player note)."""
        base = key[3:] if key.startswith("pd-") else key
        if base not in attr_defs:
            return True
        return bool((attr_defs[base].get("join") or {}).get("direction"))

    own = {
        k: v for k, v in (context.get("attributeProperties") or {}).items()
        if _is_signal_entry(v) and is_join_key(k)
    }

    # Global entries, keyed the way this tag would store them, minus anything the tag
    # defines itself (more specific wins).
    inherited: dict[str, dict] = {}
    global_props = (sdk.component_context.get("global") or {}).get("attributeProperties") or {}
    for name, attr_def in attr_defs.items():
        direction = (attr_def.get("join") or {}).get("direction")
        if not direction:
            continue
        key = f"pd-{name}" if direction == "state" else name
        if key in own:
            continue
        props = global_props.get(key)
        if _is_signal_entry(props):
            inherited[key] = props

    signals: list[ContractSignal] = []
    for key, props in {**own, **inherited}.items():
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
            extender_position=int(props.get("extenderPosition", 0)),
            schema_backed=bool(join),
            remove_on_contract_use=bool(props.get("removeOnContractUse", False)),
        ))

    signals.sort(key=_signal_order)
    return signals


def signal_map(sdk: UiSdk, tag_name: str) -> dict[str, ContractSignal]:
    """`contract_signals` keyed by BOTH the stored attribute name and the friendly name,
    so a caller can name a signal either way ("Press" or "sendeventontouch").

    Attribute keys are always present and always unambiguous. A friendly name shared by
    two signals of the same component is OMITTED rather than resolved arbitrarily -- see
    `_name_index`. Three exist in SDK 2.18.0 (`ch5-button-list`'s "ItemSelected",
    `ch5-spinner`'s "Selected Item", `ch5-video-switcher`'s "_Label").
    """
    mapping: dict[str, ContractSignal] = {}
    for signal in contract_signals(sdk, tag_name):
        mapping[signal.attribute] = signal
    for name, signals in _name_index(sdk, tag_name).items():
        if len(signals) == 1 and name not in mapping:
            mapping[name] = signals[0]
    return mapping


def _name_index(sdk: UiSdk, tag_name: str) -> dict[str, list[ContractSignal]]:
    """Lower-cased friendly name -> every signal of `tag_name` carrying it."""
    index: dict[str, list[ContractSignal]] = {}
    for signal in contract_signals(sdk, tag_name):
        index.setdefault(signal.friendly_name.lower(), []).append(signal)
    return index


def resolve_signals(sdk: UiSdk, tag_name: str, names) -> list[ContractSignal]:
    """Resolve caller-supplied signal names (friendly or raw attribute, case-insensitive)
    to `ContractSignal`s, in `extenderPosition` order and de-duplicated.

    Raises KeyError naming the valid options -- a typo'd signal name would otherwise
    produce a project whose contract is silently missing a signal, which is only
    discoverable by opening Construct. A friendly name shared by two signals raises the
    same way rather than picking one, since picking would silently enable the wrong
    signal: use the raw attribute name to disambiguate.
    """
    signals = contract_signals(sdk, tag_name)
    by_attribute = {s.attribute.lower(): s for s in signals}
    by_name = _name_index(sdk, tag_name)

    resolved: list[ContractSignal] = []
    for name in names:
        key = str(name).lower()
        signal = by_attribute.get(key)
        if signal is None:
            candidates = by_name.get(key, [])
            if len(candidates) > 1:
                raise KeyError(
                    f"{name!r} is ambiguous on {tag_name} -- it names "
                    f"{len(candidates)} signals ({', '.join(s.attribute for s in candidates)}); "
                    f"use the attribute name to say which")
            if not candidates:
                options = ", ".join(sorted({s.friendly_name for s in signals}))
                raise KeyError(f"{name!r} is not a contract signal of {tag_name} -- valid: {options}")
            signal = candidates[0]
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


CONTRACT_IS_STALE = "ContractIsStale"


def set_contract_stale(attrs: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Mark an already-in-memory project attribute list stale (see `mark_contract_stale`
    for the file-level version and for when to call either)."""
    override_attr(attrs, CONTRACT_IS_STALE, "true")
    return attrs


def mark_contract_stale(cuip_path) -> None:
    """Set `ContractIsStale = "true"` on an existing project, so Construct regenerates the
    contract the next time the project is opened (`ProjectOpenBehavior.cs:72-99`: it reads
    the flag, schedules generation, clears the flag and saves).

    Every byte of the file besides the flag is preserved, FileMetadata timestamps
    included -- `Modified` belongs to whoever actually edited the design, and a rewrite
    that refreshed it would misreport which of Construct and this generator touched the
    project last.

    Call this after ANY change to what the contract is derived from: signals enabled or
    disabled, components added or removed, pages/widgets renamed (object names ARE the
    contract's signal names). A newly-created project does not need it --
    `project.py::build_project_attributes` already defaults the flag to "true".
    """
    # Deferred to avoid a circular import: project.py calls into this module.
    import project

    attrs, device_resolution_source, metadata = project.read_cuip(cuip_path)
    if dict(attrs).get(CONTRACT_IS_STALE) == "true":
        return
    set_contract_stale(attrs)
    project.write_cuip(cuip_path, attrs, device_resolution_source, metadata=metadata)


if __name__ == "__main__":
    from sdk import read_sdk

    sdk = read_sdk("2.18.0")
    for tag in ("ch5-button", "ch5-slider"):
        print(f"{tag}:")
        for s in contract_signals(sdk, tag):
            flag = "" if s.schema_backed else "  (context-only)"
            print(f"  {s.extender_position:>2}  {s.friendly_name:<20} {s.attribute:<38} "
                  f"{s.category}{flag}")
