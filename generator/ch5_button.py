"""
Default "Ch5 Button" element builder -- Phase 4 (add a CH5 component), first slice.

Source-grounded against SDK 2.18.0's data files (matches the SdkId in
C:\\Solutions\\ClaudeSamples\\Components\\Components.cuip) and confirmed attribute-for-
attribute against that project's real plain button instance ("Button1", id "i9nb", in
Component - Button.cuig) -- see docs/architecture/04-ch5-schema.md for the full derivation.

Three layers, in the order a freshly-dropped button's attributes actually appear:

1. **component-context.json**'s `ch5-button.defaults.attributes` (24 keys, `orientation`
   through `truncatetext`) -- the literal base payload GrapesJS applies when the button is
   first dropped on a page. Confirmed order-for-order identical to Button1's first 24 keys.

2. **Common "add component" wiring** (`customvstheme` through `devicesVisited`, 10 keys) --
   not button-specific data in the SDK; inferred from being identical across every button
   instance in the reference file regardless of customization, matching the same
   "id/Name/label/devicesVisited" wiring pattern already confirmed for widgets in Phase 3
   (see generator/page.py's default_widget_html_css). `customvstheme`'s default ("custom")
   IS schema-confirmed: component-context.json's `ch5-button.attributeProperties.customvstheme.default`.

3. **Advanced Style Manager "sync" attributes** (`ccid_sync_{state}_{sector}sector_{prop}`,
   ~57-76 keys depending on which sectors are active) -- derived from **sass-schema.json**'s
   `ch5-button` sector list (16 entries: Appearance/Label/Icon/Checkbox/Image x
   normal/pressed/selected), cross-checked against the actual write algorithm in
   pd-ch5-components/mixins/common/commonButtonTraitsMixins.ts::setSyncData (~line 670):
     - a sector is active for a fresh button only if its `showWhen` matches the button's
       current attributes (previewstate="normal" by default, so only the *normal*-keyed
       sass-schema entries for Appearance/Label/Icon are active -- Checkbox needs
       checkboxshow=true, Image needs ccid_imageIconType=imageasset, neither true by default)
     - each active sector writes `ccid_sync_{state}_{sector}sector_{support}` = "syncEnabled"
       for state in (normal, pressed, selected), EXCEPT `background-color` which is always
       forced "syncDisabled" (hardcoded special case in setSyncData)
     - a second pass appends one `_toggle` key per (sector, support) pair, "normal"-keyed
       only, value "1" for everything except `background-color` (whose toggle, "0", is
       written inline with its per-state value instead, not in this second pass) --
       confirmed by trace against Button1's exact key order.
"""
from __future__ import annotations

from elements import Element
from layout import build_position_css
from sdk import UiSdk
from toml_util import override_attr

DEFAULT_LABEL_SECTOR_PREFIX = "Default"  # button `type` attribute default is "default" -> "Default" (Ch5ElementDef's own convention, confirmed via componentButtonMixins.ts's firstLetterUpper(type))


def _sass_showwhen_matches(entry: dict, attrs: dict[str, str]) -> bool:
    for key, allowed in (entry.get("showWhen") or {}).items():
        if attrs.get(key) not in allowed:
            return False
    return True


def build_sync_attributes(sdk: UiSdk, tag_name: str, attrs: dict[str, str]) -> list[tuple[str, str]]:
    """Derive the ccid_sync_* Advanced Style Manager attributes for a component, given its
    OTHER already-decided attributes (previewstate/customvstheme/ccid_imageIconType/
    checkboxshow, whichever the sass-schema sectors' showWhen clauses key off). Generic
    across component types -- not button-specific -- since it only depends on the sector
    shape sass-schema.json already describes for the given tag.
    """
    sectors = sdk.sass_sectors_for(tag_name)
    active = [
        e for e in sectors
        if e.get("sectorPrefix") and _sass_showwhen_matches(e, attrs)
    ]

    states = ["normal", "pressed", "selected"]
    value_pairs: list[tuple[str, str]] = []
    toggle_pairs: list[tuple[str, str]] = []
    for entry in active:
        sector_name = entry["sectorPrefix"].lower() + "sector"
        supports = entry["supports"]
        for support in supports:
            for state in states:
                key = f"ccid_sync_{state}_{sector_name}_{support}"
                if support == "background-color":
                    value_pairs.append((key, "syncDisabled"))
                    value_pairs.append((f"{key}_toggle", "0"))
                else:
                    value_pairs.append((key, "syncEnabled"))
            if support != "background-color":
                toggle_pairs.append((f"ccid_sync_normal_{sector_name}_{support}_toggle", "1"))

    return value_pairs + toggle_pairs


def button_size_css_vars(sdk: UiSdk, *, width: int, height: int, orientation: str = "horizontal") -> dict[str, str]:
    """The `--ch5-button--regular-{width,height}` CSS custom properties a "custom"-size
    button needs alongside its plain width/height (see layout.py::build_position_css's
    `extra_vars`). Schema-driven, not hardcoded: derived from component-context.json's
    `ch5-button.classToVariableMapping`'s "idSelector" entry, which maps `width` ->
    `--ch5-button--regular-width` and `height` -> `--ch5-button--regular-height`, swapped
    when `orientation="vertical"` (confirmed by reading that entry's `condition` block --
    not yet exercised for a vertical button, flagged).
    """
    id_selector = next(
        e for e in sdk.context_for("ch5-button")["classToVariableMapping"] if e["className"] == "idSelector"
    )
    values = {"width": width, "height": height}
    css_vars: dict[str, str] = {}
    for mapping in id_selector["propertyMapping"]:
        target = mapping["targetProperty"]
        for cond in mapping.get("condition", []):
            if cond["property"] == "orientation" and cond["value"] == orientation and cond["action"] == "swaptarget":
                target = cond["alternateTargetProperty"]
        css_vars[target] = f"{values[mapping['sourceProperty']]}px"
    return css_vars


def build_default_button_attributes(
    sdk: UiSdk,
    *,
    component_name: str,
    element_id: str,
    devices_visited: str = '["TSW-1070, TSW-1070"]',
    active_font: str = "Roboto",
    label: str | None = None,
    image_icon_type: str = "iconclass",
    icon_class: str | None = None,
    icon_library: str | None = None,
    asset_id: str = "0",
    checkbox_show: bool = False,
) -> list[tuple[str, str]]:
    """A brand-new 'Ch5 Button' element's [Elements.Attributes], as GrapesJS would apply
    on drop, for the default button type (`type=default`, `customvstheme=custom`) --
    confirmed key-for-key and value-for-value against 4 real instances in
    Component - Button.cuig (see docs/architecture/04-ch5-schema.md):

      - plain (image_icon_type="iconclass", no icon_class): "Button1"/"Button2", id i9nb/iiif
      - icon (image_icon_type="iconclass", icon_class + icon_library set): "ButtonWithIcon",
        id i2yz3h60yx -- adds `ccid_iconlibrary`/`iconclass` right after the sync block
      - image (image_icon_type="imageasset", asset_id set): "Button" (a.k.a. ButtonWithImage),
        id ixef8vumrm -- swaps the Icon sync sector for the Image one automatically (both
        are driven by sass-schema.json's showWhen on ccid_imageIconType, see
        build_sync_attributes) and drops the icon-only iconclass/ccid_iconlibrary keys
      - checkbox (checkbox_show=True): NOT present in the reference project (no real sample
        to confirm against) -- mechanically identical derivation (sass-schema.json's
        Checkbox sector, showWhen checkboxshow=true) as the confirmed icon/image cases, but
        flagged as unconfirmed against a real Construct-authored file.
    """
    label = label if label is not None else component_name
    ctx = sdk.context_for("ch5-button")

    attrs: list[tuple[str, str]] = list(ctx["defaults"]["attributes"].items())
    override_attr(attrs, "ccid_imageIconType", image_icon_type)
    if checkbox_show:
        override_attr(attrs, "checkboxshow", "true")
    # size="regular" (the raw schema default) renders the button at its theme's fixed
    # "regular" preset dimensions, ignoring whatever width/height CSS this module writes
    # (see build_default_button_element -- width/height are always required/explicit here)
    # -- confirmed as the cause of a user-reported bug where the canvas selection adorner
    # (sized to our explicit width/height) no longer matched the button's actual rendered
    # size. "custom" makes the button honor the explicit CSS size instead, at the user's
    # direction -- also consistent with every real button instance in the reference file
    # that had actually been resized away from the theme's regular preset (84x42): all of
    # them are size="custom" too (ccid_lastSizeSelected, unlike size, stays "regular" in
    # those real instances -- left untouched here, it's a separate "size to restore if
    # switched back" bookkeeping field, not the active render mode).
    override_attr(attrs, "size", "custom")

    common_wiring: list[tuple[str, str]] = [
        ("customvstheme", ctx["attributeProperties"]["customvstheme"]["default"]),
        ("id", element_id),
        ("componentName", component_name),
        ("ccid_ActiveFont", f"'{active_font}'"),
        ("ccid_Label", label),
        ("labelinnerhtml", label),
        ("assetid", asset_id),
        ("pageflip", "0"),
        ("ccid_ComponentType", "Button"),
        ("devicesVisited", devices_visited),
    ]
    attrs.extend(common_wiring)

    current = dict(attrs)
    attrs.extend(build_sync_attributes(sdk, "ch5-button", current))

    if image_icon_type == "iconclass" and icon_class is not None:
        attrs.append(("ccid_iconlibrary", icon_library or ""))
        attrs.append(("iconclass", icon_class))

    return attrs


def build_default_button_element(
    sdk: UiSdk,
    *,
    component_name: str,
    element_id: str,
    x: int,
    y: int,
    width: int,
    height: int,
    z_index: int,
    resolution: tuple[int, int] | None = None,
    devices_visited: str = '["TSW-1070, TSW-1070"]',
    active_font: str = "Roboto",
    label: str | None = None,
    image_icon_type: str = "iconclass",
    icon_class: str | None = None,
    icon_library: str | None = None,
    asset_id: str = "0",
    checkbox_show: bool = False,
) -> tuple[str, str, Element]:
    """Returns (html_tag, css, toml_element) for a brand-new Ch5 Button (see
    build_default_button_attributes for the variant parameters), ready to be inserted into
    a page's html/css/elements (see generator/page.py's write_cuig).

    `x`/`y`/`width`/`height`/`z_index` and `resolution` are required, not defaulted --
    matches generator/page.py's default_widget_html_css precedent (explicit size, no
    invented default). A first cut of this function omitted CSS entirely, which a user
    caught live in Construct: every button showed Left/Top/Width/Height as "auto" in the
    Properties panel. See generator/layout.py for the confirmed position-CSS shape/formula.
    """
    attrs = build_default_button_attributes(
        sdk, component_name=component_name, element_id=element_id,
        devices_visited=devices_visited, active_font=active_font, label=label,
        image_icon_type=image_icon_type, icon_class=icon_class, icon_library=icon_library,
        asset_id=asset_id, checkbox_show=checkbox_show,
    )
    html = "<ch5-button " + " ".join(f'{k}="{v}"' for k, v in attrs) + "></ch5-button>"
    element = Element(type="Ch5 Button", editable=True, attributes=attrs)

    theme_selectors = sdk.context_for("ch5-button").get("componentProperties", {}).get(
        "customThemeRequiredSelectors", []
    )
    css = build_position_css(
        element_id, x=x, y=y, width=width, height=height, z_index=z_index,
        theme_selectors=theme_selectors, active_font=active_font, resolution=resolution,
        extra_vars=button_size_css_vars(sdk, width=width, height=height, orientation="horizontal"),
    )
    return html, css, element


if __name__ == "__main__":
    from sdk import read_sdk

    sdk = read_sdk("2.18.0")
    html, css, element = build_default_button_element(
        sdk, component_name="Button1", element_id="i9nb",
        x=58, y=58, width=84, height=42, z_index=1, resolution=(1280, 800),
    )
    print(f"{len(element.attributes)} attributes")
    for k, v in element.attributes:
        print(f"  {k} = {v!r}")
