# ConstructUISkill2 — Status

This file reflects current status in realtime. It is updated in the same turn as any
work it describes — never batched for later. Newest entries at the top of the Log.

See `docs/ConstructUISkill.md` for the feature spec and
`docs/architecture/` for the source-grounded architecture documentation this project is
built on (see **Approach** below).

## Current phase

**Phase 4 — add a CH5 component: button DONE (plain + icon + image + checkbox
variants).** A freshly-created "Ch5 Button" matches real Construct-authored buttons
exactly for the plain and icon configurations, and produces a clean (intentionally
edit-history-free) result for image; checkbox is sanity-checked only since no real sample
exists to confirm against. All schema-driven from the installed SDK's
`component-context.json` + `sass-schema.json` (see `docs/architecture/04-ch5-schema.md`).
**Next**: multi-mode/advanced buttons, another component type, or Phase 5 (resolutions),
per the user's direction.

## Approach

This is a from-scratch rebuild of the Construct UI project generator (previous attempt:
`C:\ClaudeProjects\ConstructUISkill`, kept as-is, not reused). The key change: file-format
rules are being confirmed by reading Construct's own source
(`C:\Git\CCIDE\Crestron.IDE\Projects\UiEditor`), not inferred from sample files by
trial and error. Every phase is proven against a known-good reference project
(`C:\Solutions\ClaudeSamples\Components`) with an automated diff (`harness/compare.py`)
before any manual testing inside Construct itself.

## Log

- 2026-09-08: **`--ch5-button--regular-{width,height}` CSS var bug found and fixed.** User
  checked again after the `size="custom"` fix and the adorner still mismatched the actual
  button, asking directly: "are you 100% sure the CSS values match the property grid or
  vice versa and the TOML as well? check the sample project to be sure." Re-verified —
  property grid/CSS/TOML DID all agree; the remaining issue was that `ch5-button`'s own
  shadow-DOM rendering reads its visual size from CSS custom properties, not the plain
  outer `width`/`height` the adorner uses. Found the exact mechanism in
  `component-context.json`'s `classToVariableMapping` "idSelector" entry (already read
  once for the sync-attribute work, but this entry unused until now): `width` ->
  `--ch5-button--regular-width`, `height` -> `--ch5-button--regular-height` (swapped for
  vertical orientation, unconfirmed — no vertical button in the reference project). New
  `ch5_button.py::button_size_css_vars` derives these from that schema entry; wired into
  `layout.py::build_position_css`'s new `extra_vars` param, written in both `@media`
  blocks. Verified value-for-value against real ButtonWithIcon (190x58 ->
  `--ch5-button--regular-width: 190px`/`-height: 58px`, exact match). Rebuilt
  `MainPage.cuig`/`ButtonVariants.cuig` again for the user to re-check. Full writeup in
  `docs/architecture/04-ch5-schema.md`.
- 2026-09-08: **`size="custom"` bug found and fixed.** User checked the CSS fix in
  Construct and caught a follow-on bug: the canvas selection adorner was visibly larger
  than the button's actual rendered size. Cause: `size="regular"` (the raw SDK default,
  used verbatim until now) renders the button at its theme's fixed preset dimensions,
  ignoring whatever explicit width/height CSS is written — didn't show up in the earlier
  "112/112 exact match" claim only because Button1's chosen size (84x42) happened to equal
  that preset exactly. Fixed at the user's direction: `size` is now always forced to
  `"custom"` in `ch5_button.py::build_default_button_attributes` (`ccid_lastSizeSelected`
  left untouched, a separate "restore" bookkeeping field, confirmed distinct from `size`
  in the real file's own resized instances) — also consistent with every real button
  instance in the reference file that had actually been resized. Smoke test's plain-button
  comparison updated to exclude `size` from the exact-match assertion (documented as
  intentional). Rebuilt `MainPage.cuig`/`ButtonVariants.cuig` again for the user to
  re-check. Full writeup in `docs/architecture/04-ch5-schema.md`.
- 2026-09-08: **Position/size CSS bug found and fixed.** User checked the icon/checkbox
  button variants in Construct and reported "size can never be auto, even when you are
  using a fixed size" — the Properties panel showed Left/Top/Width/Height as "auto" for
  every generated button. Root cause: `build_default_button_element` never wrote any
  `{Css}` rule at all, only `[[Elements]]` TOML attributes — position/size lives entirely
  in CSS. Fixed with new `generator/layout.py::build_position_css`, confirmed against real
  Button1's CSS rule in `Component - Button.cuig` (two `@media` blocks: 99999px catch-all
  + device-specific landscape breakpoint; theme-selector child rule sourced from the SDK's
  own `componentProperties.customThemeRequiredSelectors`, schema-driven not hardcoded).
  While fixing this, **also found and fixed a related Phase 3 gap**: widget's default CSS
  (`page.py::default_widget_html_css`) always used a hardcoded 2560x1440 "no devices yet"
  fallback breakpoint, flagged unconfirmed at the time — now confirmed wrong by direct
  inspection of a real widget in a project WITH a device defined (`Widget.cuiw`, which
  contains a button): it uses the real device breakpoint, not the fallback. Both now share
  one confirmed formula (`layout.py::landscape_media_query`, matched against two
  independent real files at two different widths/heights). `x`/`y`/`width`/`height`/
  `z_index`/`resolution` are now required parameters on `build_default_button_element`
  (matches the widget function's existing "explicit size, no invented default"
  precedent). All Phase 3/4 smoke tests updated with position-CSS regression checks (`"auto"
  not in css`). Rebuilt `MyWidget.cuiw`/`MainPage.cuig`/`ButtonVariants.cuig` in the real
  on-disk verification project with correct CSS for the user to re-check. Full writeup in
  `docs/architecture/04-ch5-schema.md`.
- 2026-09-08: **Phase 4 — button icon/image/checkbox variants added.** User confirmed the
  plain button looked correct on the canvas in Construct, then asked to cover the
  variants. Turned out nearly free once the sync-attribute derivation existed:
  `build_sync_attributes` already selects sectors purely from `showWhen` matching on
  current attribute values, so a variant is just different input values, not new logic.
  **Icon** (`icon_class`/`icon_library` params): exact match against the real
  "ButtonWithIcon" instance, excluding 2 confirmed UI-state artifacts (`oldID`,
  `ccid_customSizeSet`) and 1 independent `size` customization. **Image**
  (`image_icon_type="imageasset"`): found and deliberately did NOT reproduce a real
  discrepancy — the reference file's image-type button also carries a stale, unused Icon
  sync sector (16 keys), traced to `setSyncData`'s "only add, never remove" attribute
  guard combined with that specific instance's edit history (authored as icon-type, later
  switched to image-type); a single fresh "add as image button" would never produce that,
  so the generator emits the clean result instead (sanity-checked: exactly 16 new
  `imagesector` keys). **Checkbox** (`checkbox_show=True`): same mechanism, but no real
  checkbox-enabled button exists anywhere in the reference project, so this one is
  sanity-checked only, not confirmed — flagged as needing a real reference file the same
  way the user added one for background-color in Phase 3, if/when it matters. All 4
  configurations round-trip clean in `generator/_test_output/phase4_smoke_test.py`.
  `docs/architecture/04-ch5-schema.md` updated with the full derivation writeup.
- 2026-09-08: **Phase 4 (add a CH5 component) — "Ch5 Button", default configuration,
  DONE.** User asked "if you do not address the 90 additional attributes how can I fully
  test component integration?" after an initial pass found a real button carries ~112
  attributes from 3 different sources, not 1 — pushed the research further rather than
  shipping a partial slice. Findings: `schema.json` (the ch5-button web component's own 60
  runtime attributes) is NOT what a freshly-dropped button's `[Elements.Attributes]` looks
  like; `component-context.json`'s `ch5-button.defaults.attributes` (24 keys) IS the real
  base payload (confirmed order-for-order against a real button); the ~80
  `ccid_sync_{state}_{sector}sector_{property}` "Advanced Style Manager" attributes are
  generated by **client-side TypeScript**
  (`pd-ch5-components/mixins/common/commonButtonTraitsMixins.ts::setSyncData`, real source
  present in `C:\Git\CCIDE`, not compiled/obfuscated) — traced the exact algorithm and
  found its authoritative data source is `sass-schema.json`'s per-tag sector list (NOT
  `component-context.json`'s `classToVariableMapping`, which has a different, over-broad
  property shape). Built `generator/sdk.py` (locates and reads an installed SDK's
  `schema.json`/`component-context.json`/`sass-schema.json` from
  `%APPDATA%\crestron-construct\AppStorage\data\ui\sdk\<version>\data\`) and
  `generator/ch5_button.py` (`build_default_button_element` /
  `build_sync_attributes` — the sync-attribute derivation is written generically off
  `sass-schema.json`'s shape, not button-specific, so should carry over to other component
  types). Verified: `generator/_test_output/phase4_smoke_test.py` — page-with-button
  round-trips byte-identical, AND the generated button's 112 attributes match a real
  Construct-authored plain button (`Component - Button.cuig`'s "Button1", id `i9nb`)
  **exactly** — same 112 keys in the same order, 0 value mismatches. Written up in
  `docs/architecture/04-ch5-schema.md` (includes the full derivation + flagged gaps: only
  the plain/default button variant is covered, not icon/image/checkbox/advanced-mode
  buttons; common wiring keys' universality across component types is unconfirmed beyond
  button). `01-index.md` updated. Also generated one into the real on-disk verification
  project (`C:\Solutions\ClaudeGenTest\GenTestProject\MainPage.cuig`) for the user to
  check in Construct.
- 2026-09-08: **End-to-end manual verification project generated in Construct's own
  Solutions folder**, at the user's request, to sanity-check Phases 1-3 outside the
  harness before starting Phase 4: `C:\Solutions\ClaudeGenTest\ClaudeGenTest.csln` ->
  project `GenTestProject` (CH5:2.18.0 SDK, light theme, TSW-1070 landscape resolution,
  matching real `Components.cuip` values) -> page `MainPage.cuig` (start page) -> widget
  `MyWidget.cuiw` (400x300) added to the page via the real `<ch5-template>` reference.
  Every step passed `harness/compare.py`'s round-trip check. User confirmed it looks good
  after opening in Construct. User also asked about adding multiple landscape/portrait
  resolutions to a project; deferred to Phase 5 (device catalog / orientation semantics
  are explicitly out of scope until then) at the user's direction, rather than guessing at
  unconfirmed device dimensions.
- 2026-09-03: **Background color verification against user-added reference files.**
  User added `Page with Bkd Color.cuig` / `Widget with Bkd Color.cuiw` to
  `C:\Solutions\ClaudeSamples\Components` specifically to test this. Confirmed
  `DisplayBackgroundColor`/`BackgroundColor` attribute placement was already correct
  (matches source exactly, no fix needed) — but the test **did** catch a real bug:
  `generator/page.py::default_widget_html_css`'s root `widgetContainer` element was
  missing `Name=""`/`Status=""`/`Content=""`/`Draggable=False`/`Copyable=False`, all of
  which `CreateNewWidgetHandler.cs`'s real payload sets explicitly (not null) — fixed
  and now matches the real file's element field-for-field. Also resolved (partially) an
  open question: even with a background color set, a page's `{Html}`/`{Css}` stay
  completely empty — the previously-unexplained `#<id>{background-color:#ffffff;}` rule
  seen on other pages is confirmed **unrelated** to this feature (still don't know what
  it is, but now know it's not this). One new open, non-blocking flag: the widget's
  color value has 8 hex digits (`#1900ffff`) vs. the page's 6 (`#ff0000`) — an alpha
  channel is suspected but its byte order (`RRGGBBAA` vs `AARRGGBB`) is unconfirmed;
  doesn't matter for the generator since color strings are passed through verbatim,
  never interpreted. All of this is now permanent regression coverage in
  `generator/_test_output/phase3_smoke_test.py`, not just a one-off check. Written up
  in `docs/architecture/03-page-widget-creation.md`.
- 2026-09-03: **Phase 3 (create page / create widget / add widget to page) complete.**
  Source-grounded in `PersistenceHelper.CreatePageSource` (two overloads: page vs.
  widget — confirmed the widget overload's 4-key `{PageAttributes}` order matches the
  real `Widget.cuiw` exactly), `CreateNewPageHandler.cs` (brand-new page = zero
  elements, empty Html/Css), `CreateNewWidgetHandler.cs` (brand-new widget's default
  `<div id="...">` + sizing CSS + bare `widgetContainer` element), and
  `AddHtmlViewDependencyHandler.cs` (the page→widget dependency graph is in-memory
  bookkeeping only — the actual persisted proof of "widget added to page" is the
  `<ch5-template>` element itself, confirmed attribute-for-attribute against the real
  `Widget on Page.cuig`, including `templateid = "w" + widget's own Id`). Derived —
  not guessed — the `[[Elements]]` nesting/blank-line rule directly from
  `ElementSource.cs`'s field declaration order: this **structurally explains** v1's
  empirically-discovered "BUG #2" (a widget container's own trailing
  `[Elements.Attributes]` landing after all its children's blocks) as a natural
  consequence of `Components` being declared before `Attributes`, rather than a
  special case to patch around. Built `generator/elements.py` (`Element` +
  `to_toml_lines`), `generator/page.py` (page/widget attribute builders, widget-default
  HTML/CSS, `make_widget_reference`, `write_cuig`). **Found and fixed a real bug while
  building a nested-element test**: the TOML string escaper only handled `\`/`"`, not
  control characters — a raw embedded newline (as in a real `Content = "\n..."` value)
  produced invalid TOML that `tomllib` refused to parse. Fixed by centralizing escaping
  in a new `generator/toml_util.py`, now imported by every writer instead of each
  module keeping its own copy. Verified: empty page/widget both round-trip and match
  real reference-file attribute order exactly; add-widget-to-page's `Ch5 Template`
  element matches the real file's `Type`/`Attributes` key set exactly; a synthetic
  3-level nested tree (`widgetContainer → Button → textnode`) proves the nesting +
  blank-line + escaping rules generally, not just against the one sample file. Written
  up in `docs/architecture/03-page-widget-creation.md`; `01-index.md` updated.
  Remaining known gap (flagged, not blocking): exactly when/how the `widget-container`
  CSS class + checkerboard background get added to a widget after its bare creation
  payload is untraced.
- 2026-09-03: **Phase 2 (create solution / create project) complete.** Source-grounded
  in `UiEditor.Server\Helpers\PersistenceHelper.cs::WriteProject` (exact ordered
  `{ProjectAttributes}` key list + omission rules), `CreateProjectHandler.cs` (defaults:
  SDK auto-detect, theme color, component mode, schema version), and
  `Solution.Server\Dao\SolutionDao.cs`/`AddProjectHandler.cs` for `.csln`. Built
  `generator/project.py` (`build_project_attributes` + `write_cuip`) and
  `generator/solution.py` additions (`write_solution`, `create_solution`,
  `add_project_to_solution`). **User caught a gap**: project creation must support
  *multiple* themes and *multiple* device resolutions selected at once, not just one of
  each — reworked `build_project_attributes` to take `themes: list[str]` (+
  `default_theme`) and `resolutions: list[dict]`, correctly producing comma-joined
  `ProjectThemeIds`/`DeviceResolutionIds` and a multi-entry `{DeviceResolutionSource}`
  JSON array. Verified programmatically (not eyeballed): generated `.cuip`'s
  `{ProjectAttributes}` key **order** matches
  `C:\Solutions\ClaudeSamples\Components\Components.cuip` exactly (17/17 keys), and
  `{DeviceResolutionSource}` entry key set matches exactly. Generated `.csln`'s
  structure matches `ClaudeSamples.csln` exactly (top-level, `_fileMetadata`,
  `_solution`, `_projects[0]` keys). Full end-to-end smoke test
  (`generator/_test_output/phase2_smoke_test.py`: create solution → create project with
  2 themes + 1 resolution → add to solution → re-read and confirm correct folder
  resolution) passed. Also resolved the Phase 1 "active project persisted state" open
  question while reading `CreateSolutionHandler.cs`: Construct has a `.cse` sidecar
  file, but it's Explorer-tree open/closed UI bookkeeping, not a single "active
  project" flag — our own `select_active_project` remains the right owner of that
  concept for this skill. Written up in
  `docs/architecture/02-project-creation.md`; `01-index.md` updated. Remaining known
  gap (flagged, not blocking): the device catalog and `orientation` enum semantics
  are unconfirmed — deferred to Phase 5.
- 2026-09-03: **Phase 1 (Foundation) complete.** Built `harness/compare.py`: a
  section-header splitter for `.cuip`/`.cuig`/`.cuiw`/`.cuia` based on the exact
  header-per-line convention confirmed in every known-good file examined (not yet
  stress-tested against Construct's more permissive in-content header scan — see the
  file's own docstring). Round-trip identity (parse -> reassemble -> byte-compare)
  verified **byte-for-byte across every file** in three real projects: all of
  `C:\Solutions\ClaudeSamples\Components` (23 `.cuig`, 2 `.cuiw`, 1 `.cuip`, 1 `.cuia`),
  all of `C:\Solutions\ClaudeSamples\ClaudeCustomModeProject` (4 `.cuig`, 1 `.cuiw`,
  1 `.cuip`), and all 36 files of v1's
  `ConstructUISkill\samples\CrestronDesignIdeas\BasicTemplate_v1_0_2` — including
  several files well over 400,000 characters, far past the 70,000-char threshold where
  Construct's own `UiEditorPageDao` has to work around a real Nett TOML
  stack-overflow bug (see `docs/architecture/00-overview.md`). Also built
  `generator/solution.py` (`.csln` JSON reader + `select_active_project`, spec §7):
  verified against `C:\Solutions\ClaudeSamples\ClaudeSamples.csln` — correctly resolves
  a named project to its real folder, and correctly refuses to guess when a solution
  has multiple projects and none was named.
- 2026-09-03: Planning session completed and approved. Folder structure created
  (`docs/architecture/`, `harness/`, `generator/`, `skills/`). Two source-code research
  passes over `C:\Git\CCIDE` confirmed the serialization mechanics for `.csln`/`.cuip`/
  `.cuig`/`.cuiw`/`.cuia`/`.cuib`/`.cuic` (DAOs, models, TOML library = Nett 0.15.0,
  JSON via `System.Text.Json`), plus contract generation, CH5 SDK schema
  (`schema.json`/`component-context.json`, machine-readable per-SDK-version), themes,
  fonts, hard buttons, and language files. Findings written to
  `docs/architecture/00-overview.md` and `01-index.md`. Decisions locked: fully
  independent codebase from v1; architecture docs written just-in-time per phase, not
  all upfront; generator language is Python (default, flagged to user given source is
  C#). Full plan on file at `C:\Users\aseferian\.claude\plans\jolly-coalescing-quiche.md`.
