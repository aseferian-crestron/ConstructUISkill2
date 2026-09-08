# CH5 component schema (Phase 4) — "add a CH5 component"

Status: **Done for the "Ch5 Button" element — plain, icon, image, and checkbox variants**
(all default `type=default`, `customvstheme=custom`; multi-mode "advanced" buttons not
covered, see Known gaps). Confirmed end-to-end, machine-readable, schema-driven derivation
— not guessed — verified attribute-for-attribute against real Construct-authored buttons in
`C:\Solutions\ClaudeSamples\Components\Component - Button.cuig`:
- **plain**: 112/112 keys, 0 value mismatches vs "Button1" (id `i9nb`)
- **icon**: exact match vs "ButtonWithIcon" (id `i2yz3h60yx`), excluding 2 confirmed
  copy/paste-resize UI-state artifacts + 1 independent `size` customization
- **image**: intentionally diverges from "Button"/ButtonWithImage (id `ixef8vumrm`) — see
  the Image variant section below for why
- **checkbox**: no real sample exists in the reference project; sanity-checked only

See `generator/sdk.py`, `generator/ch5_button.py`,
`generator/_test_output/phase4_smoke_test.py`.

## Where the SDK's data files live

`PageDesigner.Server\Dao\UiSdkDao.cs::ReadSdkAsync` reads 5 JSON files per installed SDK
version from `<AppStoragePath>/data/ui/sdk/<version>/data/`:
`schema.json`, `schemaaddendum.json`, `component-context.json`, `icon-library.json`
(`Filenames.IconData` = `"icon-library"`), `sass-schema.json`. `AppStoragePath` itself is
not read from any Construct config file — it's Electron's per-OS userData path for the
`crestron-construct` app, confirmed on this machine at
`%APPDATA%\crestron-construct\AppStorage`. `generator/sdk.py::default_app_storage_path()`
reproduces this. A project's own `SdkId` attribute (e.g. `"CH5:2.18.0"`, see
`generator/project.py`) names which installed version to read.

## Three data files, three different jobs

A naive reading of the plan ("driven by schema.json/component-context.json") undersold
what's actually needed — a real button instance carries ~112 attributes, and they come
from **three genuinely different sources**, confirmed by direct comparison:

### 1. `schema.json` — the CH5 web component's own attributes (not used directly here)

`Ch5SchemaDef` → `ch5Elements.elements[]` → `Ch5ElementDef` (`name`, `tagName`, `role`,
`attributes[]`). Each `Ch5AttributeDef` has a `default` value. This is the **runtime**
`ch5-button` custom element's own 60 attributes (join names, `size`, `orientation`, etc.) —
the ones that matter to the CH5 SDK/compiler, not Construct's editor. **Not what a
freshly-dropped button's `[Elements.Attributes]` table actually looks like** — most of
these 60 are omitted entirely when unset (schema `default: "null"`), and Construct's own
editor-specific attributes (`ccid_*`) aren't in this file at all. Kept for later phases
(e.g. validating attribute names/types when a user edits a component), not consumed by
`build_default_button_element`.

### 2. `component-context.json` — the editor's own default payload (used directly)

Per-tag entry (e.g. `data["ch5-button"]`) has a `defaults.attributes` object — this **is**
the literal set GrapesJS applies the instant a button is dropped on a page. Confirmed
order-for-order identical to the first 24 keys of a real button
(`orientation` → `truncatetext`). `generator/ch5_button.py::build_default_button_attributes`
takes this as its base, verbatim, via `sdk.context_for("ch5-button")["defaults"]["attributes"]`.

Also used: `attributeProperties.customvstheme.default` (`"custom"`) for the theme-mode
attribute, which is NOT in `defaults.attributes` itself.

**Not found here** (see #3): the ~80 `ccid_sync_*` Advanced Style Manager attributes.
`component-context.json`'s `classToVariableMapping` describes CSS-variable plumbing for the
*live* style manager UI (sector class selectors, CSS custom-property names) — real, but a
different shape than the flat `ccid_sync_{state}_{sector}sector_{property}` attribute keys
actually written to a page, and it over-lists properties (e.g. Label includes
`margin-right`/`margin-bottom`/`custom-font-size`, which a real button does NOT carry).

### 3. `sass-schema.json` — the sync-attribute source of truth (used directly)

Per-tag entry (e.g. `data["ch5-button"]`) is a flat list of 16 sector definitions:
`{sectorPrefix, supports: [...css properties...], showWhen: {...attribute conditions...}}`.
This is the file that actually matches the real, trimmed property lists (Label: `color`,
`font-size`, `font-weight`, `text-decoration`, `letter-spacing`, `margin-left`, `margin-top`
— 7, not `classToVariableMapping`'s 10). Confirmed against
`pd-ch5-components/mixins/common/commonButtonTraitsMixins.ts::setSyncData` (~line 670 in
`C:\Git\CCIDE\...\PageDesigner.Server\JS\src\`), which is the actual client-side function
that writes these attributes onto a component model — real TypeScript source present in the
repo (not compiled/obfuscated), so this is genuinely source-grounded, just client-side
instead of C#.

## The sync-attribute derivation algorithm (`build_sync_attributes`)

Confirmed by full trace against `setSyncData` and exact reproduction of Button1's key order:

1. Filter `sass-schema.json`'s sector list to entries whose `showWhen` clauses all match the
   component's current attribute values. For a fresh button (`previewstate="normal"`,
   `customvstheme="custom"`, `ccid_imageIconType="iconclass"`, `checkboxshow="false"`), only
   the *normal*-keyed **Appearance**, **Label**, **Icon** entries pass — **Checkbox**
   requires `checkboxshow=true`, **Image** requires `ccid_imageIconType=imageasset`, so both
   are correctly absent from a plain button (confirmed: Button1 has neither).
2. For each active sector, `sector_name = sectorPrefix.lower() + "sector"` (`Appearance` →
   `appearancesector`, etc.).
3. For each `support` property in that sector, for `state` in `(normal, pressed, selected)`
   — note **all 3 states are written even though only one sector `showWhen` passed** (the
   real `setSyncData` loops a fixed `stateMap` inside each active sector, it does not use
   separate `pressedAppearance`/`selectedAppearance` sass-schema entries at all for this) —
   emit `ccid_sync_{state}_{sector_name}_{support} = "syncEnabled"`, except
   `background-color` which is always forced `"syncDisabled"` (a hardcoded special case in
   `setSyncData`, confirmed) and additionally gets its own inline `_toggle = "0"` right after
   each state's value (not deferred like other properties).
4. After all sectors' state-values are written, append one more pass: for the same
   (sector, support) pairs (excluding `background-color`, whose toggle was already emitted
   in step 3), emit a single `ccid_sync_normal_{sector_name}_{support}_toggle = "1"` —
   confirmed this is `normal`-keyed only, regardless of the property, by exact order-match
   against the real file.

This is implemented generically in `generator/ch5_button.py::build_sync_attributes` — it
only depends on `sass-schema.json`'s shape for the given tag, not button-specific code, so
it should carry over to other component types with minimal changes (untested beyond button;
flagged for whichever component Phase 4 tackles next).

## Common "add component" wiring (not schema-derived, flagged)

Ten keys (`customvstheme` through `devicesVisited`, excluding `customvstheme` which IS
schema-confirmed) appear identically shaped across every button instance in the reference
file regardless of customization: `id`, `componentName`, `ccid_ActiveFont`, `ccid_Label`,
`labelinnerhtml`, `assetid`, `pageflip`, `ccid_ComponentType`, `devicesVisited`. These are
**not** found as static data in any of the 3 SDK JSON files or in C# source — inferred by
being identical across instances, following the same "id/Name/label/devicesVisited"
common-wiring pattern already established for widgets in Phase 3
(`generator/page.py::default_widget_html_css`). Not yet confirmed whether this wiring is
truly universal across component types (only button has been checked) — flagged for the
next component type Phase 4 tackles.

## Icon / image / checkbox variants (`build_default_button_attributes` parameters)

Added after the initial plain-button slice, at the user's request ("if you do not address
the 90 additional attributes how can I fully test component integration?" prompted the full
sync-attribute derivation; once that existed, the variants turned out to be nearly free —
`build_sync_attributes` already picks the right sectors purely from `showWhen` matching on
the button's current attributes, so a variant is just a different set of input attribute
values, not new sync-generation logic).

**Icon** (`icon_class`, `icon_library` params): appends `ccid_iconlibrary` then `iconclass`
right after the sync block. Confirmed exact match against the real "ButtonWithIcon" instance
— every key and value identical except 2 keys the real instance carries that no generator
output should reproduce (`oldID`, `ccid_customSizeSet` — confirmed elsewhere in this project,
e.g. Phase 3's widget-container gap, to be added by later UI interactions like copy/paste or
resize, never part of a component's initial creation payload) and one independent `size`
customization (`"custom"` vs the default `"regular"`) unrelated to the icon variant itself.

**Image** (`image_icon_type="imageasset"`, `asset_id` params): `ccid_imageIconType` flips
from the base default `"iconclass"` to `"imageasset"`, which automatically re-routes
`build_sync_attributes`'s `showWhen` filtering from the Icon sector to the Image sector (12
value + 4 toggle keys) — no variant-specific code needed beyond passing the right attribute
value in. **Deliberately does NOT byte-match** the real "Button"/ButtonWithImage instance:
that real instance carries a full, *unused* Icon sync sector (16 keys) alongside its Image
one. Traced this to `setSyncData`'s `if (!componentAttributes[syncAttribute])` guard (only
ever ADDS a sync attribute, never removes one) — the real instance was evidently authored as
an icon-type button first, then switched to image-type via the `ccid_imageIconType` trait,
leaving stale Icon-sector attributes behind. That's edit-history residue specific to how
that one sample was authored, not something a single fresh "add component as an image
button" ever produces — so the generator intentionally emits the clean result instead
(sanity-checked: exactly 16 new keys, all `imagesector`, in `phase4_smoke_test.py`).

**Checkbox** (`checkbox_show=True`): flips the base default's `checkboxshow` from `"false"`
to `"true"`, which activates the Checkbox sector (1 property × 3 states + 1 toggle = 4 keys)
the same schema-driven way. **No real sample exists** in
`C:\Solutions\ClaudeSamples\Components` to confirm against — every button instance in the
reference project has `checkboxshow=false`. Sanity-checked only (exactly the 4 expected keys
added, nothing else changes, round-trips cleanly) — flagged as the one variant without a
real-file confirmation; add a real checkbox-enabled reference file the same way the user did
for background-color in Phase 3 if/when this needs to move from "sanity-checked" to
"confirmed."

## Position/size CSS (user-caught bug, fixed)

User checked the plain button in Construct and confirmed the attributes were right, but
then caught a real bug on the icon/checkbox variants: the Properties panel showed
Left/Top/Width/Height as **"auto"** for every generated button. Root cause: the initial
`build_default_button_element` never wrote a `{Css}` rule at all — only the `[[Elements]]`
TOML attributes were built. A component's position/size is carried entirely in CSS, not in
its TOML attributes (confirmed: none of the real Button1's 112 attributes encode position),
so this was a genuine gap, not a cosmetic one.

Fixed in `generator/layout.py::build_position_css` — confirmed against real Button1's CSS
rule (`Component - Button.cuig`'s `{Css}` section): two `@media` blocks (a `max-width:
99999px` catch-all + a device-specific landscape breakpoint), each `#id{...}` rule carrying
`display: block; left; top; position: absolute; z-index (99999 block only); width; height`,
plus one theme-selector child rule per entry in the SDK's own
`component-context.json[tag].componentProperties.customThemeRequiredSelectors` (schema-
driven, not button-specific — button's is `.ch5-button :not(i):not(svg)`).

**Also fixed while here**: `generator/page.py::default_widget_html_css` (Phase 3) always
used a hardcoded 2560×1440 "no devices yet" fallback breakpoint for its second `@media`
block, regardless of whether the project actually had a device defined — flagged as
unconfirmed in Phase 3, now confirmed wrong by direct inspection of a real widget
(`Widget.cuiw`, which contains a button) in a project that DOES define a device: it uses
that device's real breakpoint, not the fallback. Added an optional `resolution` parameter
(defaults to the old fallback when omitted, so existing callers are unaffected) and had it
share the confirmed breakpoint formula with the button code
(`layout.py::landscape_media_query`).

**The formula** (confirmed by matching it against two independent real files at two
different widths/heights — the fallback 2560×1440 case and the real 1280×800 TSW-1070
case): `(max-width: {W+1}px) and (max-height: {H+1}px), (max-width: {W-1}px)`, landscape
only — portrait/other-orientation primary resolutions unconfirmed (Phase 5 territory).

**Not attempted**: byte-identical reproduction of the real files' CSS. Those reflect
components that were also manually dragged/resized after creation (inconsistent
`display`/`z-index` presence between the two blocks in the real file, non-round left/top
values) — this generator produces a clean, internally consistent result for a component's
*initial* placement instead, which is the right target for something a generator writes
programmatically. `x`/`y`/`width`/`height`/`z_index`/`resolution` are now required,
non-defaulted parameters on `build_default_button_element` (matches
`default_widget_html_css`'s existing "explicit size, no invented default" precedent) —
callers (the skill layer, eventually) own layout decisions, not this module.

## `size` forced to "custom" (user-caught bug, fixed)

After the position-CSS fix above, the user checked again and caught a follow-on bug: the
canvas selection adorner (drag handles) was visibly larger than the button's actual
rendered size. Cause: `size="regular"` (the raw `component-context.json` default, and what
this module originally used verbatim) makes CH5 render the button at its **theme's fixed
"regular" preset dimensions**, ignoring whatever explicit width/height CSS this module
writes — the adorner (sized to our CSS) and the actual render (sized to the theme preset)
diverge whenever our explicit size isn't coincidentally identical to the preset.

This didn't show up in the earlier "112/112 exact match" claim for the plain button because
Button1's chosen dimensions (84×42) happen to equal the theme's regular preset exactly — no
divergence was visible for that one case.

Fixed at the user's direction: `build_default_button_attributes` now always overrides
`size` to `"custom"` (`ccid_lastSizeSelected` — a separate "size to restore if switched back
from custom" bookkeeping field — is left as its schema default `"regular"`, unchanged; this
distinction is directly confirmed in the real file's own resized instances). This is also
consistent with the reference file's own evidence: every real button instance that had
actually been resized away from the 84×42 default is `size="custom"` too. Since this module
always requires explicit `width`/`height` now (see the position-CSS fix above), `"custom"`
is the functionally correct choice universally, not just for resized instances.

`phase4_smoke_test.py`'s plain-button comparison against real Button1 now excludes `size`
specifically (with the reasoning above), since forcing `"custom"` is an intentional
divergence from that one real file's `"regular"`, not an error.

## `--ch5-button--regular-{width,height}` CSS vars (user-caught bug, fixed)

User checked again after the `size="custom"` fix and still saw the adorner mismatch the
actual button, and asked directly: "are you 100% sure the CSS values match the property
grid or vice versa and the TOML as well? check the sample project to be sure." Re-checked —
the Property grid values (Left/Top/Width/Height) DID match the CSS and TOML exactly at
that point; the remaining bug was that the canvas adorner (driven by the outer `#id{width;
height}` rule) doesn't drive the button's own *internal* rendered size. `ch5-button` is a
web component with its own shadow-DOM rendering that reads its visual size from CSS custom
properties, not the plain `width`/`height` on its outer element.

Found the exact mechanism this time by going back to `component-context.json`'s
`classToVariableMapping` (previously read for the sync-attribute derivation, but its
`"idSelector"` entry — the button's own `#id` rule mapping — hadn't been used yet):
`width` maps to `--ch5-button--regular-width`, `height` to `--ch5-button--regular-height`
(swapped when `orientation="vertical"`, per that entry's `condition` block — unconfirmed
for a vertical button since none exists in the reference project). This exactly explains
why the plain button (Button1, `size="regular"`, no override) never needed these vars,
while every real *resized* instance in the reference file (ButtonWithIcon, Button/
ButtonWithImage, ButtonInThemeMode) carries them, matching their own width/height exactly.

Fixed: `generator/ch5_button.py::button_size_css_vars` derives these vars from that schema
entry (not hardcoded), passed into `layout.py::build_position_css`'s new `extra_vars`
parameter, written into the `#id{...}` rule in BOTH `@media` blocks (confirmed present in
both for real custom-size instances). Verified value-for-value against the real
ButtonWithIcon instance (190×58 → `--ch5-button--regular-width: 190px;
--ch5-button--regular-height: 58px`, exact match) in `phase4_smoke_test.py`.

## Known gaps (flagged, not blocking)

- Multi-mode "advanced" buttons (`ccid_advancedsyncproperties`, `Ch5 Button Mode`/
  `Ch5 Button Mode State` child elements — see "ButtonWithModes" in the reference file) are
  a genuinely different element structure, not a variant of the single-mode attribute set
  covered here. Not built.
- `Component - Button.cuig`'s real HTML has a stray whitespace-only `<ch5-button-mode>`-
  sibling `[[Elements.Components]] Type = "textnode"` under some buttons — an HTML
  formatting artifact (whitespace between multi-line closing tags), not reproduced; harmless.
- `sass-schema.json`'s sector list was read only for `ch5-button` — not yet confirmed
  whether every component type has an entry (`ch5-toggle`, `ch5-text`, etc. are absent from
  the top-level key dump but were not individually checked).
