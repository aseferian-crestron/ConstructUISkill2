# ConstructUISkill2 — Status

This file reflects current status in realtime. It is updated in the same turn as any
work it describes — never batched for later. Newest entries at the top of the Log.

See `docs/ConstructUISkill.md` for the feature spec and
`docs/architecture/` for the source-grounded architecture documentation this project is
built on (see **Approach** below).

## Current phase

**Phase 3 — Create page / create widget / add widget to page: DONE.** `[[Elements]]`
nesting rules (including the trailing-attributes-after-children pattern) confirmed from
`ElementSource.cs`'s field order and verified against real files (see Log). **Next:
Phase 4 — add a CH5 component**, starting with a button, driven by the SDK's
`schema.json`/`component-context.json`. See the plan file (this session) for the full
phased roadmap.

## Approach

This is a from-scratch rebuild of the Construct UI project generator (previous attempt:
`C:\ClaudeProjects\ConstructUISkill`, kept as-is, not reused). The key change: file-format
rules are being confirmed by reading Construct's own source
(`C:\Git\CCIDE\Crestron.IDE\Projects\UiEditor`), not inferred from sample files by
trial and error. Every phase is proven against a known-good reference project
(`C:\Solutions\ClaudeSamples\Components`) with an automated diff (`harness/compare.py`)
before any manual testing inside Construct itself.

## Log

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
