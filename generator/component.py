"""Generic CH5 component builder -- generalises Phase 4's ch5_button.py to every
component type, for the FLAT (childless) types first.

Phase 4 derived a button's attributes in three layers and confirmed them attribute-for-
attribute against a real Construct-authored button. Measuring the other component types
against those same layers showed the structure is shared: what a non-button instance
carries that the layers did not explain was, almost entirely, the same handful of
"common wiring" keys the button hardcoded. So the layers generalise; only the per-type
facts need supplying.

**The layers**, in emission order:

1. **Base attributes.** `component-context.json`'s `defaults.attributes` for the tag when
   it has them (ch5-button, ch5-slider, ...). Most tags have none, and for those the base
   is the tag's schema attributes that are BOTH exposed as a context trait AND carry a
   non-null schema default, in schema order. Verified to reproduce the exact attribute
   SET of real ch5-toggle / ch5-textinput / ch5-color-chip instances; using the schema's
   defaults alone would over-produce badly (it would add `noshowtype`, `show`, `debug`,
   `disabled`, `feedbackmode` ... which no real instance carries).
2. **Common wiring** -- `customvstheme`, `id`, `componentName`, `ccid_linkSendReceive`,
   optionally `ccid_ActiveFont`/`ccid_Label`, then `ccid_ComponentType` and
   `devicesVisited`. Which of the optional ones apply, and `ccid_ComponentType`'s value,
   are per-type facts that are NOT derivable from the SDK -- `ch5-text`'s is
   "Formatted-Text", `ch5-subpage-reference-list`'s is "Widget List",
   `ch5-signal-level-gauge`'s is "Signal Gauge" -- so they are transcribed from the
   reference project into `PROFILES` below, with a test that recomputes them from those
   files on every run.
3. **Sync attributes** (`ccid_sync_*`) from sass-schema.json -- `build_sync_attributes`
   was already generic across tags in Phase 4 and is reused unchanged.
4. **Contract signals**, last, per `contracts.DEFAULT_SIGNALS` (see
   docs/architecture/06-contracts.md for why last).

**Not covered yet:** container types whose instances carry nested children -- ch5-dpad,
ch5-keypad, ch5-button-list, ch5-tab-button, ch5-video-switcher,
ch5-subpage-reference-list, ch5-button (its mode states). Those need a child builder and
are the next slice; `build_component` raises for them rather than emitting a childless
shell that would look right and behave wrong.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import contracts
from ch5_button import build_sync_attributes
from elements import Element
from layout import build_position_css
from sdk import UiSdk

#: Tags whose real instances carry nested [[Components]] -- out of scope for this slice.
CONTAINER_TAGS = (
    "ch5-dpad",
    "ch5-keypad",
    "ch5-button-list",
    "ch5-tab-button",
    "ch5-video-switcher",
    "ch5-subpage-reference-list",
)


@dataclass(frozen=True)
class ComponentProfile:
    """The per-type facts the SDK does not carry, transcribed from the reference project.

    `component_type` is the `ccid_ComponentType` value -- Construct's own display name for
    the type, which is neither the tag nor the schema `name` for several types.
    `vstheme` is the `customvstheme` value, or None for the types that carry none.
    `active_font`/`label` say whether the type carries `ccid_ActiveFont`/`ccid_Label`.
    `extras` are further wiring keys the type carries (state flags such as
    `ccid_themeCSSSet`).
    """

    component_type: str
    vstheme: str | None = None
    active_font: bool = False
    label: bool = False
    extras: tuple[tuple[str, str], ...] = field(default_factory=tuple)


#: Transcribed from C:\Solutions\ClaudeSamples\Components (2026-09-10). Recomputed and
#: asserted by component_flat_types_test.py -- if a reference component changes, the test
#: reports it rather than the generator quietly drifting.
PROFILES: dict[str, ComponentProfile] = {
    "ch5-animation": ComponentProfile("Animation", vstheme="theme"),
    "ch5-button": ComponentProfile("Button", vstheme="custom", active_font=True, label=True),
    "ch5-color-chip": ComponentProfile("Color Chip"),
    "ch5-color-picker": ComponentProfile("Color Picker"),
    "ch5-datetime": ComponentProfile("Date Time", active_font=True,
                                     extras=(("ccid_themeCSSSet", "true"),)),
    "ch5-media-player": ComponentProfile("Media Player", vstheme="theme", active_font=True),
    "ch5-qrcode": ComponentProfile("QR Code"),
    "ch5-segmented-gauge": ComponentProfile("Segmented Gauge"),
    "ch5-signal-level-gauge": ComponentProfile("Signal Gauge", vstheme="theme"),
    "ch5-slider": ComponentProfile("Slider", vstheme="theme"),
    "ch5-text": ComponentProfile("Formatted-Text", active_font=True, label=True,
                                 extras=(("ccid_themeCSSSet", "true"),)),
    "ch5-textinput": ComponentProfile("Textinput", vstheme="theme", active_font=True, label=True,
                                      extras=(("ccid_sizeInitialized", "true"),)),
    "ch5-toggle": ComponentProfile("Toggle", vstheme="theme", active_font=True, label=True),
    "ch5-video": ComponentProfile("Video"),
    "ch5-wifi-signal-level-gauge": ComponentProfile("Wifi Signal Level Gauge", vstheme="theme"),
}


#: Defaults Construct overrides in code rather than reading from schema.json --
#: `pd-metadata-resolver\MetaDataResolver.ts:214-229`, which rewrites these while
#: building the tag's traits. Without them a generated slider has no min/max/step, since
#: schema.json leaves those null.
TRAIT_DEFAULT_OVERRIDES: dict[str, dict[str, str]] = {
    "ch5-slider": {"max": "100", "min": "0", "step": "1", "nohandle": ""},
}


def _schema_element(sdk: UiSdk, tag_name: str) -> dict:
    for element in sdk.schema["ch5Elements"]["elements"]:
        if element.get("tagName") == tag_name:
            return element
    raise KeyError(f"{tag_name!r} is not a CH5 element in schema.json")


def base_attributes(sdk: UiSdk, tag_name: str) -> list[tuple[str, str]]:
    """Layer 1: what a freshly-dropped instance carries before any wiring.

    `component-context.json`'s `defaults.attributes` when the tag declares them,
    otherwise the tag's schema attributes that are exposed as a context trait AND have a
    non-null schema default, in schema order (see the module docstring for why both
    conditions are needed).
    """
    context = sdk.component_context.get(tag_name) or {}
    defaults = (context.get("defaults") or {}).get("attributes") or {}
    if defaults:
        return list(defaults.items())

    # Trait set = the tag's own attributeProperties UNION global's, which is exactly
    # MetaDataResolver.ts::supportsAttribute ("global" checked first, then the tag) --
    # the same own-then-global pattern the contract signal lookup follows. Reading only
    # the tag's own entry under-produces badly: it loses a signal gauge's numberofbars
    # and value, a toggle's labelon/labeloff, and more.
    global_traits = set((sdk.component_context.get("global") or {}).get("attributeProperties") or {})
    traits = set(context.get("attributeProperties") or {}) | global_traits

    attributes: list[tuple[str, str]] = []
    for attribute in _schema_element(sdk, tag_name)["attributes"]:
        name = attribute["name"]
        if name not in traits and f"pd-{name}" not in traits:
            continue
        default = TRAIT_DEFAULT_OVERRIDES.get(tag_name, {}).get(name, attribute.get("default"))
        if default in (None, "null", ""):
            continue
        attributes.append((name, str(default)))
    return attributes


def build_component_attributes(
    sdk: UiSdk,
    tag_name: str,
    *,
    component_name: str,
    element_id: str,
    devices_visited: str = '["TSW-1070, TSW-1070"]',
    active_font: str = "Roboto",
    label: str | None = None,
    contract_signals: tuple[str, ...] | None = None,
    overrides: dict[str, str] | None = None,
) -> list[tuple[str, str]]:
    """The full `[Elements.Attributes]` list for one flat component.

    `contract_signals` defaults to the type's entry in `contracts.DEFAULT_SIGNALS`; pass
    `()` for none. `overrides` sets or adds any attribute after the base layer, for the
    per-instance values a caller actually chose (a slider's `value`, a gauge's
    `numberofsegments`).
    """
    if tag_name in CONTAINER_TAGS:
        raise NotImplementedError(
            f"{tag_name} instances carry nested child components (see CONTAINER_TAGS); "
            f"emitting one without them would produce a component that looks right and "
            f"behaves wrong. Container support is the next slice.")
    profile = PROFILES.get(tag_name)
    if profile is None:
        raise KeyError(
            f"no ComponentProfile for {tag_name!r} -- its per-type wiring "
            f"(ccid_ComponentType and friends) is not derivable from the SDK and has to "
            f"be transcribed from a real instance; see PROFILES")

    attributes = base_attributes(sdk, tag_name)
    for key, value in (overrides or {}).items():
        _set(attributes, key, value)

    _set(attributes, "customvstheme", profile.vstheme) if profile.vstheme else None
    _set(attributes, "id", element_id)
    _set(attributes, "componentName", component_name)
    _set(attributes, "ccid_linkSendReceive", "True")
    if profile.active_font:
        _set(attributes, "ccid_ActiveFont", f"'{active_font}'")
    if profile.label:
        _set(attributes, "ccid_Label", component_name if label is None else label)
    for key, value in profile.extras:
        _set(attributes, key, value)
    _set(attributes, "ccid_ComponentType", profile.component_type)
    _set(attributes, "devicesVisited", devices_visited)

    attributes.extend(build_sync_attributes(sdk, tag_name, dict(attributes)))

    signals = (contracts.default_signals_for(tag_name)
               if contract_signals is None else contract_signals)
    contracts.enable_contract_signals(attributes, sdk, tag_name, signals)
    return attributes


def _set(attributes: list[tuple[str, str]], key: str, value: str) -> None:
    """Set `key`, in place if it is already present (keeping its position) or appended."""
    for i, (existing, _) in enumerate(attributes):
        if existing == key:
            attributes[i] = (key, value)
            return
    attributes.append((key, value))


def build_component(
    sdk: UiSdk,
    tag_name: str,
    *,
    component_name: str,
    element_id: str,
    x: int,
    y: int,
    width: int,
    height: int,
    z_index: int,
    resolution: tuple[int, int] | None = None,
    **kwargs,
) -> tuple[str, str, Element]:
    """(html, css, Element) for one flat component, ready for page.py::write_cuig."""
    attributes = build_component_attributes(
        sdk, tag_name, component_name=component_name, element_id=element_id,
        active_font=kwargs.pop("active_font", "Roboto"), **kwargs)

    html = (f"<{tag_name} " + " ".join(f'{k}="{v}"' for k, v in attributes)
            + f"></{tag_name}>")
    element = Element(type=_schema_element(sdk, tag_name).get("name"), editable=True,
                      attributes=attributes)

    context = sdk.component_context.get(tag_name) or {}
    css = build_position_css(
        element_id, x=x, y=y, width=width, height=height, z_index=z_index,
        theme_selectors=(context.get("componentProperties") or {}).get(
            "customThemeRequiredSelectors", []),
        active_font=dict(attributes).get("ccid_ActiveFont", "'Roboto'").strip("'"),
        resolution=resolution,
    )
    return html, css, element


if __name__ == "__main__":
    from sdk import read_sdk

    sdk = read_sdk("2.18.0")
    for tag in sorted(PROFILES):
        attrs = build_component_attributes(
            sdk, tag, component_name=f"My{tag}", element_id="iabc")
        signals = [k for k, v in attrs if v == contracts.CONTRACT_ENABLED]
        print(f"{tag:<30}{len(attrs):>4} attrs, {len(signals)} signals")
