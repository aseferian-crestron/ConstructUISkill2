# Page & Widget Creation, `[[Elements]]` Nesting, Add-Widget-to-Page

Covers Phase 3: create page, create widget, add widget to page.

## Source grounding

- `UiEditor.Server\Helpers\PersistenceHelper.cs`:
  - `CreatePageSource(UiEditorProject, PageDto)` (~line 112) — page `{PageAttributes}`
    key order: `Name, PageMode, Id, StartPage, PreloadPage, CachePage, VisibilityJoin,
    DisplayBackgroundColor, [BackgroundColor if set], [TransitionIn/Out/Duration/Delay
    only if CachePage=true]`.
  - `CreatePageSource(UiEditorProject, WidgetDto)` (~line 178) — widget
    `{PageAttributes}` key order: `Name, PageMode, Id, DisplayBackgroundColor,
    [BackgroundColor if set]`. No `StartPage`/`PreloadPage`/`CachePage`/
    `VisibilityJoin`/`Transition*` — **confirmed to match the real
    `Widget.cuiw`'s `[Attributes]` table exactly, 4/4 keys, same order.**
- `UiEditor.Server\Commands\HtmlViews\CreateNewPageHandler.cs` — a brand-new page has
  **zero** elements and empty `Html`/`Css` (`HtmlViewRenderContextDto("", "")`).
- `UiEditor.Server\Commands\HtmlViews\CreateNewWidgetHandler.cs` — a brand-new widget's
  default `Html` is `<div id="{id}"></div>`; default `Css` is two `@media` blocks sizing
  that div at the requested width/height, `left:0;top:0;position:absolute`. The
  corresponding `PageElementDto` is `Type="widgetContainer"` with **only** `Id` +
  `DevicesVisited` attributes. **Not yet traced**: when/how the `widget-container` CSS
  class and checkerboard background (present on the fully-built `Widget.cuiw` reference
  file) get added — not part of this initial creation payload. Flagged, not blocking.
- `UiEditor.Server\Commands\HtmlViews\AddHtmlViewDependencyHandler.cs` — "add widget to
  page" registers a page→widget dependency in the **in-memory** `ProjectStructureDto`
  graph (`PageHandleDto.Dependencies`) — it does **not** itself write the `<ch5-template>`
  element. That element — the actual on-disk, persisted proof the widget is placed on
  the page — is inserted the same way any component is dropped onto a page (a generic,
  schema-driven flow not traced in this phase). Its exact attribute set/order was instead
  confirmed directly against a real sample.

## `[[Elements]]` nesting rule (`ElementSource.cs` field order → real serialization order)

`ElementSource.cs` field declaration order: `Name, Type, Status, Content, Removable,
Draggable, Highlightable, Copyable, Editable, Selectable, Hoverable, _InnerText,
Components, Attributes, Style, Classes`.

Confirmed by direct, byte-level reading of `Widget.cuiw` (not guessed): the real
emission order is **every non-null scalar field first** (in the order above, with
`Classes` — despite being declared last — emitted alongside the other scalars, since
TOML syntax requires every plain key/inline-array to precede any subtable in the same
table body), **then every non-null table-typed field in declaration order**: `Components`
(nested `[[...Components]]` blocks, recursively), then `Attributes`
(`[...Attributes]`), then `Style` (`[...Style]`).

A **blank line precedes each present table-region** of an element (before `Components`
starts, before `Attributes` starts, before `Style` starts) — but **no** blank line
separates consecutive sibling entries within the same `Components` array. This exactly
reproduces the pattern v1 discovered empirically and called "BUG #2" (a widget
container's own `[Elements.Attributes]` table lands *after* all of its children's
`[[Elements.Components]]` blocks) — here it falls out of the field-order rule by
construction, so a correct writer never has to special-case it. Verified: a synthetic
`widgetContainer → Ch5 Button (Attributes) → textnode (leaf, Content only)` tree,
rendered by `generator/elements.py::Element.to_toml_lines`, reproduces this exact shape
and round-trips through `tomllib` with the right values landing on the right table paths.

Also confirmed: string values in `Attributes`/`Style` tables must escape control
characters, not just `\` and `"` — real `Content = "\n              "` values have a
literal backslash-n. **Bug found and fixed in this phase**: the first version of the
TOML string escaper only handled `\`/`"`; a raw embedded newline produced invalid TOML
tomllib refused to parse. Fixed by centralizing escaping in `generator/toml_util.py`
(full TOML basic-string escape table), imported by every writer instead of each having
its own copy.

## Add widget to page: the `<ch5-template>` element

Confirmed directly against `C:\Solutions\ClaudeSamples\Components\Widget on Page.cuig`:

```
<ch5-template transitionduration="1s" transitiondelay="0s"
  templateid="w434e1f2d-49c8-4f46-9432-b227dcf84f85" id="ic0t"
  componentName="Widget" ccid_ComponentType="Widget" ccid_WidgetName="Widget"
  devicesVisited="[...]"></ch5-template>
```

`templateid` = `"w" + <the widget's own Id>` — confirmed by direct match against
`Widget.cuiw`'s own `Id` (`434e1f2d-...`). `{PageAttributes}` for this element is a
single flat `[Elements.Attributes]` table (`Type = "Ch5 Template"`, no `Components`
nesting — the widget's own content lives in its own file, not duplicated onto the
referencing page).

## Background color (`DisplayBackgroundColor`/`BackgroundColor`) — confirmed against user-added reference files

The user added two real reference files specifically to verify this (`Page with Bkd
Color.cuig`, `Widget with Bkd Color.cuiw`, both in
`C:\Solutions\ClaudeSamples\Components`, added 2026-09-03):

- **Attribute placement/order**: exactly as already transcribed from
  `PersistenceHelper.cs` — `BackgroundColor` immediately follows
  `DisplayBackgroundColor` in both the page and widget `[Attributes]` tables. No fix
  needed here; this was already correct from reading source alone, and the real files
  confirm it byte-for-byte (`gen_bkd_page_keys == ref_bkd_page_keys`, etc.).
- **A real, unexpected finding**: even with `DisplayBackgroundColor = "True"` and a real
  `BackgroundColor` set, the page's `{Html}` and `{Css}` sections are **both still
  completely empty**. This resolves the earlier open question about the
  `#<id>{background-color:#ffffff;}` rule seen on every other reference page —
  **that rule is unrelated to `DisplayBackgroundColor`/`BackgroundColor`** (some other,
  still-unidentified default page-wrapper styling, unconditionally white). The actual
  background-color feature must be realized by Construct's runtime reading
  `{PageAttributes}` directly, not by any CSS baked into the source file. Updates the
  "not yet traced" note below from *unknown* to *confirmed not a `{Css}`-level
  mechanism* — still don't know exactly how it's rendered, but now know where NOT to
  look.
- **Color value format, still open (flagged, non-blocking)**: the page's color is
  `#ff0000` (6 hex digits) while the widget's is `#1900ffff` (8 hex digits) — suggests
  an optional alpha channel, but whether the format is `RRGGBBAA` or `AARRGGBB` (and
  whether alpha is only appended/prepended when non-opaque) is unconfirmed from one
  example each. **Does not block anything**: `build_page_attributes`/
  `build_widget_attributes` never interpret the color string — they pass through
  whatever the caller supplies verbatim. Only matters if a future skill-layer feature
  needs to *construct* a color value from a named color or an opacity slider.
- **A real bug this caught**: `default_widget_html_css`'s root `widgetContainer`
  `Element` only set `type` and `attributes`, omitting `Name=""`, `Status=""`,
  `Content=""`, `Draggable=False`, `Copyable=False` — all of which
  `CreateNewWidgetHandler.cs`'s actual `PageElementDto` constructor call sets
  explicitly (not null), so the real file emits them too. Fixed directly against the
  real `Widget with Bkd Color.cuiw`'s root element, which — being from the same
  from-creation code path as the plain `Widget.cuiw` — incidentally also confirmed the
  bare `Widget.cuiw` reference file was never fully checked at the full-field level
  before (only `Type` + `Attributes` key set were checked in the original Phase 3
  pass). This is exactly the kind of gap the project's "verify against real files, not
  plausible-looking code" methodology exists to catch — recorded as a permanent
  regression check in `generator/_test_output/phase3_smoke_test.py`, not just fixed
  and forgotten.

## What's built

- `generator/toml_util.py` — shared, correct TOML string escaping (`toml_escape`,
  `toml_str`).
- `generator/elements.py` — `Element` dataclass mirroring `ElementSource.cs`, with
  `to_toml_lines(prefix)` implementing the confirmed field-order/blank-line rule.
- `generator/page.py` — `build_page_attributes`, `build_widget_attributes` (exact
  `PersistenceHelper.CreatePageSource` transcriptions), `default_widget_html_css`
  (brand-new-widget defaults), `make_widget_reference` (the `<ch5-template>` element,
  both HTML tag and TOML `Element`), `write_cuig` (shared `.cuig`/`.cuiw` writer),
  `add_widget_reference_to_page`.

## Verification performed

1. Empty page: round-trips, `{PageAttributes}` key order matches `CreatePageSource`
   exactly, **zero** `[[Elements]]` blocks (matching a brand-new page having no
   elements at all).
2. Empty widget: round-trips; `{PageAttributes}` key order matches the real
   `Widget.cuiw` exactly (4/4 keys); root `widgetContainer` element's `Type` +
   `Attributes` key set matches `CreateNewWidgetHandler`'s defaults exactly
   (`{id, devicesVisited}`).
3. Add widget to page: round-trips; the generated `Ch5 Template` element's `Type` and
   `Attributes` key set matches the real `Widget on Page.cuig` exactly; `templateid`
   correctly derived as `"w" + widget_id`.
4. Synthetic nested-element test (`widgetContainer → Button → textnode`) proves the
   trailing-attributes-after-children nesting rule and the blank-line placement rule
   both hold and parse correctly via `tomllib`, independent of the specific reference
   files (a general proof of the algorithm, not just a match against one sample).
5. Background color (page + widget): attribute order matches `Page with Bkd
   Color.cuig`/`Widget with Bkd Color.cuiw` exactly; empty `{Html}`/`{Css}` confirmed
   even with a background color set; the `default_widget_html_css` root-element field
   gap (above) was caught and fixed here.

All checks in `generator/_test_output/phase3_smoke_test.py`. Not yet tested: opening
any of this in Construct itself (manual verification checkpoint, deferred per project
convention until the user wants it).
