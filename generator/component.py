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
import fonts
import style
from ch5_button import build_sync_attributes
from elements import Element
from layout import build_position_css
from sdk import UiSdk

#: Tags whose instances carry nested [[Components]] children (see build_children).
#: ch5-subpage-reference-list is NOT one: its only child in the reference is a textnode,
#: so it builds as a flat component.
CONTAINER_TAGS = (
    "ch5-dpad",
    "ch5-keypad",
    "ch5-button-list",
    "ch5-tab-button",
    "ch5-video-switcher",
)

#: The dpad's five buttons, verbatim from `pd-metadata-resolver\MetaDataResolver.ts:107-111`,
#: which pushes these child tags when the schema tag is ch5-dpad. `center` deliberately
#: has no icon there. componentName/pressed/ccid_imageIconType are added by the dpad's
#: own mixins afterwards, and are confirmed against the reference instance.
DPAD_KEYS = (
    ("up", "Up", "fas fa-caret-up"),
    ("down", "Down", "fas fa-caret-down"),
    ("left", "Left", "fas fa-caret-left"),
    ("right", "Right", "fas fa-caret-right"),
    ("center", "Center", None),
)

#: The keypad's thirteen buttons, verbatim from `MetaDataResolver.ts:120-132`.
#: `buttonextra` is the phone key, iconclass rather than labels.
KEYPAD_KEYS = (
    ("button1", "1", ""), ("button2", "2", "ABC"), ("button3", "3", "DEF"),
    ("button4", "4", "GHI"), ("button5", "5", "JKL"), ("button6", "6", "MNO"),
    ("button7", "7", "PQRS"), ("button8", "8", "TUV"), ("button9", "9", "WXYZ"),
    ("button0", "0", "+"), ("buttonstar", "*", None), ("buttonhash", "#", None),
    ("buttonextra", None, None),
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



#: Transcribed from C:\Solutions\ClaudeSamples\Components (2026-09-10), except
#: ch5-background (C:\Solutions\ClaudeSamples\Components\Component - Images -
#: Background.cuig) and ch5-image (no real instance in that project --
#: C:\Solutions\ClaudeSamples\ClaudeCustomModeProject\Page1.cuig instead), both added
#: 2026-09-11 for the "page background" rule -- see generator/background.py. Recomputed
#: and asserted by component_flat_types_test.py -- if a reference component changes, the test
#: reports it rather than the generator quietly drifting.
PROFILES: dict[str, ComponentProfile] = {
    "ch5-animation": ComponentProfile("Animation", vstheme="theme"),
    "ch5-button": ComponentProfile("Button", vstheme="custom", active_font=True, label=True),
    "ch5-color-chip": ComponentProfile("Color Chip"),
    "ch5-color-picker": ComponentProfile("Color Picker"),
    "ch5-background": ComponentProfile("Background", extras=(("assetid", "0"),)),
    "ch5-datetime": ComponentProfile("Date Time", active_font=True,
                                     extras=(("ccid_themeCSSSet", "true"),)),
    "ch5-image": ComponentProfile("Image", vstheme="custom", extras=(("assetid", "0"),)),
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
    # Containers (see CONTAINER_TAGS / build_children), plus the subpage reference list,
    # whose only child is a textnode so it builds flat.
    "ch5-dpad": ComponentProfile("Dpad", vstheme="theme"),
    "ch5-keypad": ComponentProfile("Keypad", vstheme="theme", active_font=True,
                                   extras=(("ccid_customSizeSet", "true"),)),
    "ch5-button-list": ComponentProfile("Button List", vstheme="theme", active_font=True,
                                        label=True, extras=(("assetid", "0"),
                                                            ("ccid_imageIconType", "iconclass"))),
    "ch5-tab-button": ComponentProfile("Tab Button", vstheme="theme", active_font=True,
                                       label=True, extras=(("assetid", "0"),
                                                           ("ccid_imageIconType", "iconclass"))),
    "ch5-video-switcher": ComponentProfile("Video Switcher", active_font=True,
                                           extras=(("assetid", "0"),)),
    "ch5-subpage-reference-list": ComponentProfile("Widget List", vstheme="theme"),
}


#: Tags whose instances carry the `ccid_sync_*` Advanced Style Manager block. ONLY
#: ch5-button does, across the entire reference project -- sass-schema.json defines
#: sectors for 20 more types, but no real instance of any of them carries a single sync
#: attribute, so generating from the sass schema alone over-produced badly (72 attributes
#: on a datetime whose real instance has 17). Theme mode is NOT the gate: a theme-mode
#: button still carries 78 of them. `setSyncData` lives in commonButtonTraitsMixins, the
#: button family's own mixin, which is consistent with what the files show.
SYNC_TAGS = ("ch5-button",)


#: Attributes that are instance STATE rather than a default, so a fresh component never
#: carries them even though they are traits with a non-null schema default. `disabled`
#: settles it by contradiction: the reference dpad and signal gauge have it, the
#: reference video switcher does not -- it records what the user set in the properties
#: panel, not what a component is born with.
NEVER_EMIT = frozenset({"disabled"})



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


def widget_reference_id(widget_guid: str) -> str:
    """A widget's `Id` GUID as a `ch5-subpage-reference-list`'s `widgetid` refers to it:
    the GUID with a literal "w" in front. Confirmed in the reference project --
    WidgetListReference.cuiw has Id `eb72224e-90b4-4804-8c0a-4c347600530a` and the widget
    lists pointing at it carry `widgetid="web72224e-90b4-4804-8c0a-4c347600530a"`. It is
    the same `w{GUID}` convention a ch5-template uses for its `templateid`.

    An empty widgetid is legitimate -- Construct creates a widget list that way and you
    pick the widget afterwards -- and is NOT why an earlier version of this generator
    produced a wrongly-sized one. That was the explicit CSS box; see CONTENT_SIZED_TAGS.
    """
    return f"w{widget_guid}"


def can_resize(sdk: UiSdk, tag_name: str) -> bool:
    """Whether this type can be given a size at all.

    `componentProperties.canResize` is the SDK's own answer, and it names exactly the
    four types the user identified as fixed-size: ch5-animation, ch5-segmented-gauge,
    ch5-signal-level-gauge, ch5-wifi-signal-level-gauge ("signal level and wifi only
    support fixed sizes"). An earlier version inferred this from an empty render-size
    `propertyMapping`, which happened to pick the same four -- this is the published
    flag rather than a proxy for it.
    """
    properties = (sdk.component_context.get(tag_name) or {}).get("componentProperties") or {}
    return bool(properties.get("canResize", True))


def is_aspect_locked(sdk: UiSdk, tag_name: str) -> bool:
    """True when the rendered size is driven by a SINGLE axis -- the type's render-size
    variables are all sourced from `width` (or all from `height`), with nothing driving
    the other axis. See reflow.py::_is_aspect_locked, which uses the same test.

    ch5-dpad, ch5-keypad, ch5-toggle and ch5-video are all in this class: their height
    follows from their width, so an explicit height in CSS is a guess that sizes the
    canvas adorner around a component that ignored it.
    """
    mapping = ((sdk.component_context.get(tag_name) or {}).get("classToVariableMapping") or [])
    id_selector = next((e for e in mapping if e.get("className") == "idSelector"), None)
    sources = {m.get("sourceProperty") for m in (id_selector or {}).get("propertyMapping", [])}
    return sources in ({"width"}, {"height"})


#: The one aspect-locked type that still gets an explicit height: a dpad is locked at
#: 1:1, so its height IS its width and stating it is not a guess (see build_component,
#: which squares a non-square request rather than emitting a box the dpad will ignore).
SQUARE_TAGS = ("ch5-dpad",)

#: Types whose rendered size comes from their CONTENT, so no explicit box belongs in
#: their CSS. A ch5-subpage-reference-list is as tall and wide as the widget it
#: references multiplied by its item count -- and a small placeholder when it references
#: nothing -- which this generator cannot compute. The user established it by dropping an
#: empty one in Construct: it was "much smaller than yours".
#:
#: Transcribed rather than derived: `canResize` is True for it and its componentProperties
#: differ from ch5-button-list's (which DOES lay out to its box, confirmed good in
#: Construct) only in ways too incidental to hang a rule on.
CONTENT_SIZED_TAGS = ("ch5-subpage-reference-list",)


def _mode(value: str | None) -> bool | str:
    """A defaults.style value as a write-mode: absent -> False, "auto" -> "auto",
    anything else -> True (write our own pixel value)."""
    if value is None:
        return False
    return "auto" if value == "auto" else True


def default_style_size(sdk: UiSdk, tag_name: str) -> dict[str, str]:
    """`component-context.json`'s `defaults.style` width/height for a tag -- the size and
    shape Construct gives a component when you DROP it.

    This is the authority for both questions, and it was overlooked for a long time in
    favour of reading sizes off the reference project's instances. Those instances have
    been configured and resized, so they answer a different question: a widget list
    reads 816px wide there but drops at 200px, which is exactly the "much smaller than
    yours" the user reported.

    Values are verbatim, including the literal "auto" (a widget list and a video
    switcher derive their height; a wifi gauge derives both).
    """
    style = ((sdk.component_context.get(tag_name) or {}).get("defaults") or {}).get("style") or {}
    return {k: str(v) for k, v in style.items() if k in ("width", "height")}


def writes_css_size(sdk: UiSdk, tag_name: str) -> tuple[bool | str, bool | str]:
    """(write width, write height) for this type's `#id` rule.

    Three rules, and every one of them came from a component rendering at a different
    size than its selection adorner:

    1. A type that cannot be resized gets NEITHER. `canResize: False` in the SDK names
       animation and the three gauges -- they lay themselves out from their own
       attributes, so any box we state is one they ignore. CONTENT_SIZED_TAGS (the
       widget list) is the same outcome for a different reason: its size comes from the
       widget it references, which we cannot compute.
    2. An ASPECT-LOCKED type gets width only. Its rendered size is driven by a single
       axis (see is_aspect_locked), so its height follows from its width and an explicit
       one is a guess. This covers the toggle, keypad, video, video switcher and text
       input -- the user reported the first three independently before the class was
       recognised as one thing.
    3. The dpad is aspect-locked but at 1:1, so its height is known exactly and is
       written (SQUARE_TAGS).

    Everything else -- button, slider, media player, the lists, the colour components --
    lays out to its CSS box and gets both.
    """
    # `defaults.style` first, and it wins outright: it names exactly which dimensions a
    # dropped component carries and says "auto" for the ones it derives -- including for
    # ch5-wifi-signal-level-gauge, which is canResize:False yet still carries
    # `width:auto;height:auto` in every real instance.
    default_style = default_style_size(sdk, tag_name)
    if default_style:
        return (_mode(default_style.get("width")), _mode(default_style.get("height")))

    if not can_resize(sdk, tag_name):
        return False, False

    # Aspect-locked without a defaults.style: the reference instances of ch5-keypad,
    # ch5-textinput and ch5-video all carry `height: auto` -- they state the height and
    # state that it is derived. Omitting it entirely (an earlier version of this fix)
    # is NOT the same thing, and the CSS diff against the reference is what caught it.
    if is_aspect_locked(sdk, tag_name) and tag_name not in SQUARE_TAGS:
        return True, "auto"
    return True, True


def size_css_vars(sdk: UiSdk, tag_name: str, *, width: int, height: int,
                  attributes: dict[str, str]) -> dict[str, str]:
    """The CSS custom properties a component reads its RENDERED size from.

    A CH5 web component does not lay itself out from the plain `width`/`height` on its
    `#id` rule -- those size the canvas selection adorner. Its own rendering reads these
    custom properties, so writing one without the other leaves the adorner and the
    component visibly mismatched. That was found and fixed for ch5-button in Phase 4
    (see build_position_css's docstring) and reintroduced for every OTHER type when the
    generic builder did not carry the fix across; the user caught it on a toggle.

    Driven by `component-context.json`'s `classToVariableMapping` "idSelector" entry, so
    it is per-type data rather than a table: a toggle maps width ->
    `--ch5-toggle--handle-size-regular`, a dpad width -> `--ch5-dpad--regular-size`, a
    button width AND height -> `--ch5-button--regular-{width,height}`. Two condition
    kinds appear and both are honoured: `swaptarget` (a vertical button's width drives
    the HEIGHT variable) and `ignore` (a horizontal slider ignores its height mapping).
    """
    mapping = sdk.component_context.get(tag_name, {}).get("classToVariableMapping") or []
    id_selector = next((e for e in mapping if e.get("className") == "idSelector"), None)
    if not id_selector:
        return {}

    values = {"width": width, "height": height}
    variables: dict[str, str] = {}
    for entry in id_selector.get("propertyMapping", []):
        target = entry.get("targetProperty")
        source = entry.get("sourceProperty")
        if target is None or source not in values:
            continue
        skip = False
        for condition in entry.get("condition", []):
            if attributes.get(condition.get("property")) != condition.get("value"):
                continue
            if condition.get("action") == "swaptarget":
                target = condition.get("alternateTargetProperty", target)
            elif condition.get("action") == "ignore":
                skip = True
        if not skip:
            variables[target] = f"{values[source]}px"
    return variables


def _attr_str(value) -> str:
    """A JSON value as Construct stores it in the file. component-context.json holds real
    JSON booleans for some defaults (ch5-subpage-reference-list's `centeritems`), and
    Python's str() would write those as "True"/"False" -- the file, and CH5, want
    "true"/"false"."""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def base_attributes(sdk: UiSdk, tag_name: str) -> list[tuple[str, str]]:
    """Layer 1: what a freshly-dropped instance carries before any wiring.

    `component-context.json`'s `defaults.attributes` when the tag declares them,
    otherwise the tag's schema attributes that are exposed as a context trait AND have a
    non-null schema default, in schema order (see the module docstring for why both
    conditions are needed).
    """
    context = sdk.component_context.get(tag_name) or {}
    defaults = (context.get("defaults") or {}).get("attributes") or {}

    # Trait set = the tag's own attributeProperties UNION global's, which is exactly
    # MetaDataResolver.ts::supportsAttribute ("global" checked first, then the tag) --
    # the same own-then-global pattern the contract signal lookup follows. Reading only
    # the tag's own entry under-produces badly: it loses a signal gauge's numberofbars
    # and value, a toggle's labelon/labeloff, and more.
    global_traits = set((sdk.component_context.get("global") or {}).get("attributeProperties") or {})
    traits = set(context.get("attributeProperties") or {}) | global_traits

    # `defaults.attributes` and the trait defaults are BOTH written, not either/or. An
    # earlier version returned the context defaults alone when a tag declared them, which
    # cost a slider its min/max/step and a signal gauge its numberofbars/value: those come
    # from the trait pass, and the tags that miss them are precisely the ones that DO
    # declare defaults.attributes. Context defaults come first and win on value, matching
    # the key order of every real instance checked.
    attributes: list[tuple[str, str]] = [(k, _attr_str(v)) for k, v in defaults.items()]
    for attribute in _schema_element(sdk, tag_name)["attributes"]:
        name = attribute["name"]
        if name in defaults or name in NEVER_EMIT:
            continue
        if name not in traits and f"pd-{name}" not in traits:
            continue
        default = TRAIT_DEFAULT_OVERRIDES.get(tag_name, {}).get(name, attribute.get("default"))
        if default in (None, "null", ""):
            continue
        attributes.append((name, _attr_str(default)))
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
    icon_class: str | None = None,
    icon_library: str | None = None,
) -> list[tuple[str, str]]:
    """The full `[Elements.Attributes]` list for one flat component.

    `contract_signals` defaults to the type's entry in `contracts.DEFAULT_SIGNALS`; pass
    `()` for none. `overrides` sets or adds any attribute after the base layer, for the
    per-instance values a caller actually chose (a slider's `value`, a gauge's
    `numberofsegments`). `icon_class`/`icon_library` are ch5-button-only (see
    `ch5_button.py::build_default_button_attributes`) -- ignored for every other type,
    same as `label`/`active_font` are accepted uniformly but not every type renders them.
    """
    if tag_name == "ch5-button":
        # The button already has a builder confirmed attribute-for-attribute against the
        # reference (Phase 4), including the icon/image/checkbox variants this generic
        # path knows nothing about. Delegate rather than reimplement it worse.
        from ch5_button import build_default_button_attributes

        button_attributes = build_default_button_attributes(
            sdk, component_name=component_name, element_id=element_id,
            devices_visited=devices_visited, active_font=active_font, label=label,
            icon_class=icon_class, icon_library=icon_library,
            **({} if contract_signals is None else {"contract_signals": contract_signals}),
        )
        # FIXED 2026-09-18 -- real bug, found while building design_ideas_
        # subsystem.py: `overrides` was silently dropped for every ch5-button
        # ever built through this function (build_default_button_attributes
        # has no `overrides` parameter at all) -- confirmed directly, an
        # `overrides={"type": "info"}` call had zero effect. Applied here,
        # after the button's own real attribute set exists, same "set in
        # place or append" semantics as the generic path below.
        for key, value in (overrides or {}).items():
            _set(button_attributes, key, value)
        return button_attributes
    profile = PROFILES.get(tag_name)
    if profile is None:
        raise KeyError(
            f"no ComponentProfile for {tag_name!r} -- its per-type wiring "
            f"(ccid_ComponentType and friends) is not derivable from the SDK and has to "
            f"be transcribed from a real instance; see PROFILES")

    attributes = base_attributes(sdk, tag_name)

    # An explicit width/height is only honoured when `size` says "custom". "custom" is
    # not in the schema's own enum of presets -- it is a Construct-level mode, and the
    # real button/keypad/toggle instances all carry it. Left alone for ch5-qrcode, whose
    # `size` is a number (160) rather than a preset name.
    # ...and only for a type that HAS render-size variables to drive. The three gauges
    # have an empty propertyMapping: nothing in CSS can resize them, they lay themselves
    # out from their own attributes. Writing "custom" there sets a preset that does not
    # exist and leaves the adorner disagreeing with the render -- the user's second
    # report, after the first fix over-applied this to every preset-sized type.
    # Both conditions: the type must HAVE a preset `size` attribute (ch5-color-chip has
    # render-size variables but no size attribute at all -- setting one would invent an
    # attribute no real instance carries), and must be resizable at all.
    has_preset_size = any(a["name"] == "size" and a.get("value")
                          for a in _schema_element(sdk, tag_name)["attributes"])
    if has_preset_size and can_resize(sdk, tag_name):
        _set(attributes, "size", "custom")

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

    # FIXED 2026-09-18 -- real bug, found twice (first for ch5-button's
    # `customvstheme`, now for ch5-image's `assetid` via `profile.extras`):
    # `overrides` used to apply BEFORE all of the above profile-driven
    # defaults, so any key this function also sets afterward silently
    # clobbered a caller's explicit override. Moved to run LAST, after every
    # profile default but BEFORE sync-attribute computation below (so sync
    # attributes reflect the actually-final, overridden state) -- matches
    # this function's own docstring: "overrides sets or adds any attribute
    # after the base layer."
    for key, value in (overrides or {}).items():
        _set(attributes, key, value)

    if tag_name in SYNC_TAGS:
        attributes.extend(build_sync_attributes(sdk, tag_name, dict(attributes)))

    signals = (contracts.default_signals_for(tag_name)
               if contract_signals is None else contract_signals)
    contracts.enable_contract_signals(attributes, sdk, tag_name, signals)
    return attributes


def _child(child_tag: str, attributes: list[tuple[str, str | None]]) -> Element:
    """One nested child element, dropping any attribute whose value is None."""
    from page import generate_element_id

    resolved = [(k, generate_element_id() if v is _AUTO_ID else v)
                for k, v in attributes if v is not None]
    return Element(type=_CHILD_TYPE_NAMES[child_tag], editable=child_tag != "ch5-dpad-button",
                   attributes=resolved)


_AUTO_ID = object()

#: `Type` as written in the file for each child tag -- the schema `name`, which for these
#: is the tag title-cased ("Ch5 Dpad Button"), confirmed against the reference.
_CHILD_TYPE_NAMES = {
    "ch5-dpad-button": "Ch5 Dpad Button",
    "ch5-keypad-button": "Ch5 Keypad Button",
    "ch5-button-list-individual-button": "Ch5 Button List Individual Button",
    "ch5-tab-button-individual-button": "Ch5 Tab Button Individual Button",
    "ch5-video-switcher-source": "Ch5 Video Switcher Source",
    "ch5-video-switcher-screen": "Ch5 Video Switcher Screen",
}


_CHILD_TAGS = {name: tag for tag, name in _CHILD_TYPE_NAMES.items()}


def build_children(
    sdk: UiSdk,
    tag_name: str,
    parent_attributes: dict[str, str],
    *,
    devices_visited: str = '["TSW-1070, TSW-1070"]',
) -> list[Element]:
    """The nested [[Components]] a container carries.

    How MANY comes from the parent's own attributes, not from a guess: a button list has
    `numberofitems` (10 by default), a tab button `numberofitems` (3), a video switcher
    `numberofsources` (5) and `numberofscreens` (2) -- each matching its reference
    instance's child count exactly. The dpad and keypad instead have FIXED child sets,
    hardcoded in MetaDataResolver.ts rather than described in the SDK (see DPAD_KEYS /
    KEYPAD_KEYS).

    Per-child attribute order follows the reference instances.
    """
    def count(key: str) -> int:
        return int(parent_attributes.get(key, 0) or 0)

    if tag_name == "ch5-dpad":
        return [_child("ch5-dpad-button", [
            ("componentName", name), ("key", key), ("iconclass", icon),
            ("pressed", "false"), ("ccid_imageIconType", "iconclass"), ("id", _AUTO_ID),
        ]) for key, name, icon in DPAD_KEYS]

    if tag_name == "ch5-keypad":
        return [_child("ch5-keypad-button", [
            ("pressed", "false"), ("key", key), ("labelmajor", major),
            ("labelminor", minor), ("componentName", key),
            ("iconclass", "fas fa-phone" if key == "buttonextra" else None),
        ]) for key, major, minor in KEYPAD_KEYS]

    if tag_name == "ch5-button-list":
        return [_child("ch5-button-list-individual-button", [
            ("ccid_imageIconType", "iconclass"),
            ("componentName", f"Individual Button {n}"), ("componentNumber", str(n)),
            ("id", _AUTO_ID),
        ]) for n in range(1, count("numberofitems") + 1)]

    if tag_name == "ch5-tab-button":
        return [_child("ch5-tab-button-individual-button", [
            ("ccid_imageIconType", "iconclass"),
            ("componentName", f"Individual Button {n}"), ("componentNumber", str(n)),
            ("id", _AUTO_ID), ("devicesVisited", devices_visited),
            ("pageFlipAttributeName", "onRelease"), ("onRelease", "0"),
            ("ccid_Label", f"Tab{n}"), ("labelinnerhtml", f"Tab{n}"),
        ]) for n in range(1, count("numberofitems") + 1)]

    if tag_name == "ch5-video-switcher":
        sources = [_child("ch5-video-switcher-source", [
            ("ccid_imageIconType", "iconclass"), ("id", _AUTO_ID),
            ("componentName", f"Source {n}"), ("componentNumber", str(n)),
        ]) for n in range(1, count("numberofsources") + 1)]
        screens = [_child("ch5-video-switcher-screen", [
            ("id", _AUTO_ID), ("componentName", f"Screen {n}"),
            ("componentNumber", str(n)), ("alignlabel", "center"),
        ]) for n in range(1, count("numberofscreens") + 1)]
        return sources + screens

    return []


def _set(attributes: list[tuple[str, str]], key: str, value: str) -> None:
    """Set `key`, in place if it is already present (keeping its position) or appended."""
    for i, (existing, _) in enumerate(attributes):
        if existing == key:
            attributes[i] = (key, value)
            return
    attributes.append((key, value))


def _font_family_selectors(sdk: UiSdk, tag_name: str, context: dict) -> list[str]:
    """Real CSS selector(s) layout.py::build_position_css should target with a
    `font-family` rule for `tag_name` -- normally `component-context.json`'s
    own `customThemeRequiredSelectors` (confirmed real for ch5-button/ch5-
    tab-button/ch5-button-list/ch5-toggle/ch5-textinput/ch5-keypad/ch5-media-
    player). ROOT-CAUSED 2026-09-17 (a real bug reported live: the splash
    headline/room-name/date-time rendered in a fallback serif font despite a
    correctly-set `ccid_ActiveFont`): `customThemeRequiredSelectors` is simply
    ABSENT from the schema for ch5-text/ch5-datetime/ch5-video-switcher
    (confirmed directly against the SDK: `None`, not an empty list by
    omission) -- so `build_position_css` was silently never writing ANY font-
    family rule at all for those 3 types, not a font-loading or Construct-
    install-specific issue as first suspected.

    Falls back to `style.style_property_catalog`'s own `color`-property
    selector(s) -- the same real, schema-confirmed class Stage 1 already uses
    to color that type's text (`.ch5-text`/`.ch5-datetime`/`.ch5-video-
    switcher--source-list-label`+`.ch5-video-switcher--screen-list-label`,
    verified directly against the real SDK) -- on the reasoning that
    font-family belongs on the same element as text color, not a new guess.
    """
    required = (context.get("componentProperties") or {}).get("customThemeRequiredSelectors")
    if required:
        return required
    return sorted({
        entry["class_name"] for entry in style.style_property_catalog(sdk, tag_name)
        if entry["source_property"] == "color"
    })


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
    available_fonts: list[str] | None = None,
    **kwargs,
) -> tuple[str, str, Element]:
    """(html, css, Element) for one flat component, ready for page.py::write_cuig.

    `available_fonts`: the real font names Construct's Font Family dropdown can show a
    selection for (see `fonts.py::available_fonts`) -- checked against `active_font`
    before writing anything. Defaults to the zero-config baseline
    (`fonts.available_fonts(sdk)`: the SDK's system default + Crestron-bundled names,
    always present regardless of project) if the caller doesn't know the target
    project's own imported webfonts. A name outside this list is NOT a webfont import
    error to fix later -- it silently renders as CH5's own fallback typeface (confirmed
    2026-09-16: "Manrope", never validated, rendered as a default serif on a real Bento
    Box card) -- so this raises up front rather than writing a `ccid_ActiveFont`/
    `font-family` pair Construct has nothing to display or render it as. Pass the
    project's real list (`fonts.available_fonts(sdk, project_webfonts_path(...))`) when
    targeting a project with real imported webfonts.
    """
    active_font = kwargs.pop("active_font", "Roboto")
    valid_fonts = fonts.available_fonts(sdk) if available_fonts is None else available_fonts
    if active_font not in valid_fonts:
        raise ValueError(
            f"{active_font!r} is not a real selectable font -- Construct's Font Family "
            f"dropdown only shows: {valid_fonts}. See fonts.py module docstring.")
    attributes = build_component_attributes(
        sdk, tag_name, component_name=component_name, element_id=element_id,
        active_font=active_font, **kwargs)

    # A dpad is aspect-locked at 1:1 -- every real instance is square (118x118, 221x221)
    # and Construct never lets its box go otherwise. Honouring a non-square request would
    # render a square component inside a rectangular adorner, so square it here rather
    # than emit a size the component will not use. (reflow.py does the same thing when
    # fitting one to a new resolution.)
    if tag_name in SQUARE_TAGS and width != height:
        width = height = min(width, height)

    write_width, write_height = writes_css_size(sdk, tag_name)

    children = build_children(sdk, tag_name, dict(attributes),
                              devices_visited=kwargs.get("devices_visited", '["TSW-1070, TSW-1070"]'))
    child_html = "".join(
        "<" + _CHILD_TAGS[child.type] + "".join(f' {k}="{v}"' for k, v in child.attributes)
        + f"></{_CHILD_TAGS[child.type]}>"
        for child in children)

    html = (f"<{tag_name} " + " ".join(f'{k}="{v}"' for k, v in attributes)
            + f">{child_html}</{tag_name}>")
    element = Element(type=_schema_element(sdk, tag_name).get("name"), editable=True,
                      components=children, attributes=attributes)

    context = sdk.component_context.get(tag_name) or {}
    css = build_position_css(
        element_id, x=x, y=y, width=width, height=height, z_index=z_index,
        theme_selectors=_font_family_selectors(sdk, tag_name, context),
        active_font=dict(attributes).get("ccid_ActiveFont", "'Roboto'").strip("'"),
        resolution=resolution,
        extra_vars=size_css_vars(sdk, tag_name, width=width, height=height,
                                 attributes=dict(attributes)),
        write_width=write_width, write_height=write_height,
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
