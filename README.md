# ConstructUISkill2 — Status

This file reflects current status in realtime. It is updated in the same turn as any
work it describes — never batched for later. Newest entries at the top of the Log.

See `docs/ConstructUISkill.md` for the feature spec and
`docs/architecture/` for the source-grounded architecture documentation this project is
built on (see **Approach** below).

## Current phase

**Phase 5 continuation — multi-resolution reflow design REVISED AGAIN (X axis gains a
row-wrap tier), approved, implementation plan is now STALE and needs to be rewritten.**
User revisited the design before answering the execution-approach question from the
prior session, pointing out the algorithm was pinned to pure per-axis scaling and
should behave like a real responsive layout — when horizontal space is tight but
vertical space is available, elements should wrap onto new rows below rather than only
ever compact/scale in place. Worked through the shape via clarifying questions: rows
are inferred from source elements' Y-overlap (not authored explicitly), the new wrap
tier sits between move and compact/scale (`move -> wrap -> compact -> scale` on X),
wrapping is row-only (no symmetric column-wrap for height-constrained cases), and
wrapping preserves source row groupings — only an overflowing row splits, trailing
elements peel onto a new row directly below it, rather than a full greedy re-pack that
could merge/reorder rows. The Y axis keeps its original 3-tier fallback but now
operates on the row list (as pseudo-items) instead of individual elements, so rows
stack top-to-bottom the same way elements used to. The "no new overlaps within the
fitted group" proof still holds without new 2D collision checks: same-row elements
stay disjoint on X (unchanged argument), different-row elements stay disjoint on Y
since each row's Y-extent is self-contained and rows themselves never overlap. Full
rewrite at `docs/superpowers/specs/2026-09-08-multi-resolution-reflow-design.md`
(Scope, Algorithm, Components, Error handling, and Testing sections all updated; new
`detect_rows`/`wrap_rows`/`stack_rows` components added to `generator/reflow.py`'s
planned shape). **The previously-written 7-task implementation plan
(`docs/superpowers/plans/2026-09-08-multi-resolution-reflow.md`) was written against
the old per-axis-only algorithm and is now stale — it has NOT been rewritten yet.**
**Next**: get the user's review/sign-off on the revised spec (asked, awaiting answer),
then invoke writing-plans to redo the implementation plan, then get the
execution-approach answer (Subagent-Driven vs. Inline) that was never answered last
session either.

**Phase 5 continuation (superseded above) — multi-resolution reflow IMPLEMENTATION
PLAN WRITTEN, ready to build.** 7-task TDD plan at
`docs/superpowers/plans/2026-09-08-multi-resolution-reflow.md`, source-grounded like
every prior phase: confirmed the previously-unconfirmed portrait media-query formula by
reading `C:\Git\CCIDE`'s `breakpoint.ts::createRawQuery` directly and cross-checking two
real portrait `.cuiw` sample files elsewhere in that repo (`(orientation: portrait) and
(max-height: {H+1}px) and (max-width: {W+1}px), (orientation: portrait) and (max-height:
{H-1}px)` — same `±1px` shape as the already-confirmed landscape formula, just leading
with height instead of width), closing a gap flagged unconfirmed since Phase 4. Tasks:
(1) `orientation_media_query` + doc writeup, (2) CSS block parse/find/build helpers in
`layout.py`, (3) `fit_axis` (the 3-tier algorithm itself, unit-tested per tier plus the
insufficient-room edge case, with direct pairwise AABB checks proving no overlap across
a range of target sizes), (4) `find_new_elements`/`check_overlaps`, (5)
`pick_primary`/`choose_source_resolution`, (6) `reflow_file` tying both modes together
against a hand-built minimal file, (7) wiring into `add_resolutions_to_project` plus
end-to-end scenarios (an edge-placed element landing on-canvas, the
orientation-bootstrap case, zero regression on projects with no pages yet) and manual
Construct verification against the existing `GenTestProject`. Trigger 2 (the skill
prompting for `pin_existing`/`full_refit` when adding elements to an existing
multi-resolution page) is explicitly noted as NOT built by this plan — it's a
skill-layer conversational step that calls the same `reflow_file` this plan builds, not
new generator code. **RESUME POINT (session paused 2026-09-08, picking up next
session):** user was offered the execution choice (Subagent-Driven vs. Inline, per the
writing-plans skill's handoff) and hasn't answered yet — ask that question first, don't
re-derive it. No implementation code has been written yet; the plan file is the only
new artifact. **Next**: get the execution-approach answer, then start Task 1.

**Phase 5 continuation — multi-resolution reflow design spec REVISED AGAIN (reflow
generalized into a standalone, repeatable operation with two fit modes), approved,
ready for an implementation plan.** User pointed out UI work isn't a one-time event —
new controls get added to existing pages long after resolutions are set up (e.g. Apple
TV controls today, Cable box controls next week), and every resolution besides the one
they're authored against needs the same "missing block" fix reflow already solves for
newly-added resolutions. Reflow is now a standalone `reflow_file` operation with two
callers: `add_resolutions_to_project` (target starts empty) and a new skill-level
trigger when new elements are added to an already-multi-resolution page (target already
has content) — the skill asks the user which of two modes to use: `pin_existing`
(default — leave existing controls alone, fit only the new ones; the new elements are
guaranteed not to overlap each other but only best-effort/flagged against pre-existing
pinned elements, since real 2D obstacle avoidance was explicitly ruled out of scope) or
`full_refit` (recompute everything from the source resolution, discarding whatever was
in the target — same full overlap-safety guarantee as the original single-shot design).
Adding a brand-new resolution turns out to be `pin_existing` with zero pinned elements —
no special-casing needed, one mechanism covers both triggers. The still-approved 3-tier
per-axis fit math (move, then compact whitespace to a 4px floor, then scale down) is
unchanged from the previous revision; see
`docs/superpowers/specs/2026-09-08-multi-resolution-reflow-design.md` for the full,
current design. **Next**: write the implementation plan and build it.

**Phase 9 (assets) pulled forward — local image import DONE, confirmed live in
Construct.** User caught that the Phase 4 image-button variant couldn't actually be
verified without a real asset behind it. Built `generator/assets.py`, confirmed exactly
against the real `CrimsonSilk.cuia`/`.jpg` (which is also the exact asset the reference
project's own image-type button already references), wired it into the on-disk
verification project, and the user confirmed the image now renders correctly on the
button in Construct. See `docs/architecture/09-assets.md`. Phase 4's button work (plain +
icon + image + checkbox variants) is now fully closed out end-to-end. **Next**: back to
Phase 5 (full reflow) or another component type, per user direction.

**Phase 5 — resolutions: catalog + add-resolutions-to-a-project DONE.** User chose the
smaller first slice over bundling in full reflow math. Confirmed the real
device/resolution catalog (74 entries, `resolutionData.json`), resolved both
previously-flagged open questions (catalog-vs-per-project-selection, orientation enum
semantics), corrected an unconfirmed guess in `project.py`'s own example (no real
"TSW-1070 Portrait" catalog entry exists — TSW-1070 is landscape-only hardware), and built
`generator/devices.py` + `generator/project.py::add_resolutions_to_project`. See
`docs/architecture/05-resolutions.md`. **Next**: full multi-resolution reflow (deliberately
deferred, bigger/separate slice), another component type, or user's direction.

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

- 2026-09-09: **Multi-resolution reflow — X axis redesigned with a row-wrap tier
  (`move -> wrap -> compact -> scale`), via the brainstorming skill.** User asked to
  revisit the reflow logic before answering the still-outstanding execution-approach
  question, objecting that the design was "pinned to a pure horizontal space" — pure
  per-axis scaling/compaction, never letting elements use available vertical room by
  moving below other elements. Classified as an architectural revision (changes an
  already-approved design's core algorithm, reopens a line explicitly marked
  out-of-scope). Resolved via one-at-a-time clarifying questions: rows are inferred
  from source Y-overlap (not authored explicitly); the wrap tier is inserted between
  move and compact (wrap preferred over shrinking); row-wrap only, no symmetric
  column-wrap; and wrapping splits only overflowing source rows (trailing elements
  peel onto a new row below), rather than a full greedy re-pack that could merge or
  reorder rows. Y axis keeps its original 3-tier fallback (move/compact/scale)
  unchanged in kind, but now operates on the row list as pseudo-items instead of
  individual elements. Reworked the "no new overlaps" proof to cover the new
  structure: same-row elements stay disjoint on X (original argument, unchanged
  wording only), different-row elements stay disjoint on Y since each row's Y-extent
  is self-contained and rows themselves never overlap — no new 2D collision detection
  needed. Rewrote Scope, Algorithm, Components, Error handling, and Testing sections
  of `docs/superpowers/specs/2026-09-08-multi-resolution-reflow-design.md` in place
  (same file, per this project's established revision pattern); self-review caught and
  fixed two stale "3-tier fit"/pre-wrap-tier-order wording spots left over from the
  previous revision. Committed (`fde5733`). **The existing 7-task implementation plan
  was written against the old algorithm and is now stale — not yet rewritten.**
  **Next**: user reviews the revised spec, then re-run writing-plans for a fresh
  implementation plan, then get the still-unanswered execution-approach choice.
- 2026-09-08: **Multi-resolution reflow — implementation plan written** (7 TDD tasks,
  `docs/superpowers/plans/2026-09-08-multi-resolution-reflow.md`), following the
  writing-plans skill against the now-approved spec. Before writing it, did the source
  research the spec's scenarios actually require but didn't yet have: the portrait
  media-query formula, unconfirmed project-wide since Phase 4 (flagged in `layout.py`'s
  own docstring and `04-ch5-schema.md`). Found and read `C:\Git\CCIDE`'s
  `breakpoint.ts::createRawQuery` directly (the real client-side source that generates
  these breakpoints) and cross-checked it against two real portrait `.cuiw` files
  elsewhere in that repo (`Bug_CCIDE_5225_Widget2.cuiw`/`Widget5.cuiw`, both a
  1024x1322 portrait resolution) — source and samples agree exactly, closing the gap
  rather than letting the plan bake in a guess. Also worked out concrete tier-2/tier-3
  math not fully nailed down in the spec's prose: whitespace compaction is a linear
  interpolation from each gap's original size toward the 4px floor (weighted by how
  much reduction is still needed), and tier-3 scaling reserves room for the mandatory
  `(n-1)*4px` floor gaps before computing the shared scale factor, then repacks at
  exactly 4px rather than edge-to-edge. Plan self-review passed: full spec coverage
  (every Components-section function has a task), no placeholders, and a
  cross-checked-against-the-actual-codebase pass confirming `Element`'s dataclass
  defaults, `write_cuig`'s signature, and `harness.compare`'s section-index ordering
  all match what the plan's own test code assumes. **Next**: execute the plan.
- 2026-09-08: **Multi-resolution reflow — generalized from a one-shot,
  resolution-add-only operation into a standalone `reflow_file` callable any time a
  resolution's block is missing elements that exist elsewhere in the file.** User
  pushed back on the spec's implicit assumption that reflow only ever happens at the
  moment a resolution is added — real projects gain new controls on existing pages long
  after resolutions are set up, and those controls hit the identical "other resolutions
  have no CSS rule for this element" gap. Resolved two design forks via clarifying
  questions: (1) when new controls are added to a page that already has fitted content
  in other resolutions, the user wants to be **prompted** each time (not a fixed
  policy) — leave the existing controls alone and fit just the new ones, or re-fit the
  whole page — so `reflow_file` gained a `mode` parameter (`pin_existing` default vs.
  `full_refit`) instead of one hardcoded behavior; (2) in `pin_existing` mode, new
  elements are only guaranteed not to overlap *each other* — guaranteeing they avoid
  the pinned pre-existing elements too would need real 2D obstacle-avoidance placement,
  which the user agreed to explicitly rule out of scope in favor of a best-effort fit
  plus a flagged warning (`check_overlaps`) for manual nudging in Construct. New
  components added to the spec: `find_new_elements` (id-set diff between source and
  target blocks) and `check_overlaps` (pairwise AABB check for the warning surface);
  `reflow_file` now returns a `ReflowResult` carrying `warnings` instead of assuming a
  silently-clean result. `add_resolutions_to_project` (Trigger 1) turns out to be the
  degenerate case of `pin_existing` with zero pinned elements, so it needed no special
  casing — one mechanism now covers both the resolution-add trigger and the new
  add-elements-to-an-existing-multi-resolution-page trigger. Full rewrite at
  `docs/superpowers/specs/2026-09-08-multi-resolution-reflow-design.md` (Problem,
  Scope, Algorithm, Integration, Components, Error handling, and Testing sections all
  updated). **Next**: user reviews the rewritten spec, then the implementation plan.
- 2026-09-08: **Multi-resolution reflow — fit-strategy redesigned to a 3-tier fallback
  (move, then compact whitespace, then scale), at the user's direction.** The
  just-approved spec (previous entry below) always scaled first and only repositioned
  as a last-resort clamp; the user asked for the opposite priority — try repositioning
  first, then reducing whitespace, and only scale down if neither works. Clarified two
  ambiguities before rewriting: (1) the "move" tier must be collision-aware, not
  independent per-element clamping — resolved by proving that rigid group translation
  (tier 1) plus order-preserving, never-negative-gap compaction (tiers 2/3) can never
  introduce a new overlap, since two elements non-overlapping in the source are always
  disjoint on at least one axis and that disjointness survives any monotonic shrink; (2)
  whitespace reduction preserves element order (no bin-packing/rearrangement) and the
  final scale is one uniform factor per axis, both per the user's explicit choice. User
  then set the minimum gap floor at 4px, applied through both tier 2 (compaction) and
  tier 3 (scale-down reserves `(n-1)*4px` for mandatory gaps before scaling the
  remainder) rather than allowing gaps to reach 0. Spec rewritten in place at
  `docs/superpowers/specs/2026-09-08-multi-resolution-reflow-design.md` (Algorithm,
  Components, Error handling, and Testing sections all updated; new insufficient-room
  edge case documented for when even 4px floor gaps don't fit the element count).
  **Next**: user reviews the rewritten spec, then the implementation plan.
- 2026-09-08: **Multi-resolution reflow — design spec written and approved.** Covers the
  gap left by Phase 5's first slice: `add_resolutions_to_project` updates the `.cuip`'s
  resolution list but does nothing to existing pages'/widgets' component
  positions/sizes, so content near the edge of an original canvas can land off-canvas on
  a newly-added smaller/differently-oriented resolution. Design: parse each file's
  `99999px` catch-all CSS block (the confirmed single source of truth for current
  position/size) into per-element `{left, top, width, height, extra_vars}`, scale
  per-axis from a chosen source resolution (same-orientation primary, or the other
  orientation's primary for the bootstrap case), then clamp any still-off-canvas element
  by repositioning only (never resizing). Emits one new `@media` block per newly-added
  resolution; the existing catch-all block is untouched. New components planned:
  `layout.py::parse_position_rules`/`build_reflow_block` (extending, not replacing, the
  existing single-element device-block logic) and a new `generator/reflow.py`
  (`reflow_file`, `pick_primary`, `choose_source_resolution`), wired into
  `add_resolutions_to_project`. Explicitly out of scope: resolution removal,
  shrink-to-fit, and reflowing hand-authored non-generator CSS. Full spec at
  `docs/superpowers/specs/2026-09-08-multi-resolution-reflow-design.md`. **Next**: write
  the implementation plan.
- 2026-09-08: **Phase 9 (assets) pulled forward — local image import DONE.** User was
  checking the image-button variant in the generated project and pointed out it couldn't
  really be called verified without an actual image asset imported and referenced —
  correctly identified that no asset-import code existed yet (it's Phase 9, unstarted).
  Found the real reference project's image-type button already references a specific real
  asset (`C:\Solutions\ClaudeSamples\Components\assets\CrimsonSilk.cuia`/`.jpg`, Id
  `498f8b9e-eade-4d9d-9475-49bb03d4324b`) — about as strong a ground truth as this project
  has had. Confirmed the `.cuia` format (`{FileMetadata}` + `{AssetAttributes}`, the
  latter a plain `Dictionary<string,string>` whose real key-insertion order — Id, Name,
  SourceUri, AspectRatio, AssetSourceType, Username, Password — was found in
  `SaveAssetMetadataHandler.cs`, confirmed 7/7 against the real file), that
  `MinimumProjectApp=""` for assets specifically (not a typo, a genuinely different
  default than every other file type), and that `AspectRatio` (`width/height` as a
  double) computed independently in Python via Pillow matches C#'s ImageSharp-computed
  value byte-for-byte (`1.588550983899821`) for the real file. Also confirmed no new code
  was needed to reference an asset from a button — `ch5_button.py`'s existing `asset_id`
  param already does the right thing (the real button has no static `iconurl` attribute at
  all; Construct resolves it dynamically from `assetid`). Built `generator/assets.py`
  (`import_asset`), verified via `phase9_assets_smoke_test.py` (imports the real
  CrimsonSilk.jpg, diffs the generated `.cuia` against the real one — exact match) plus a
  new dependency on Pillow. Imported the same real asset into the on-disk verification
  project and rewired `ButtonVariants.cuig`'s image button to use it, for the user to
  check in Construct. Full writeup in `docs/architecture/09-assets.md`.
- 2026-09-08: **Phase 5 — device/resolution catalog + add-resolutions-to-a-project DONE.**
  User asked whether the rest of the components or resolutions should come first;
  recommended resolutions first since `generator/layout.py` (built in Phase 4) is now a
  shared foundation every future component will call, and doing Phase 5 while only one
  component type exists avoids rework across many later. User agreed, then chose the
  smaller "catalog + add resolution" slice over bundling in full reflow math when asked.
  Research resolved both Phase 2-flagged open questions: (1) `UiEditorResolutionDao.cs`
  vs. inline `.cuip` `{DeviceResolutionSource}` are NOT overlapping — the DAO reads a
  global, not-per-project catalog file, the `.cuip` section stores which catalog entries a
  project has selected; (2) `DisplayOrientation` enum confirmed
  (`None=0,Landscape=1,Portrait=2,Both=3`), serialized as int inside `.cuip` but as a
  string in the global catalog file (two different JSON contexts for the same enum).
  Found the real catalog on disk (`%APPDATA%\crestron-construct\AppStorage\data\ui\
  resolution\resolutionData.json`, 74 entries) and confirmed/corrected a previously
  fabricated example in `project.py`'s own `__main__` block: no "TSW-1070 Portrait" exists
  in the real catalog (TSW-1070 is landscape-only hardware); TST-1080 genuinely supports
  both orientations and is used instead. Built `generator/devices.py` (catalog reader —
  found and worked around a real collision: this machine's own custom-resolutions file has
  a personal entry also named "TSW-1070", so `include_custom` defaults to False; also
  normalizes an orientation int-vs-string inconsistency between the two catalog files) and
  `generator/project.py::read_cuip`/`add_resolutions_to_project` (extends an existing
  project's resolutions, handles both the "already has resolutions" and "starts with zero"
  cases, the latter correctly inserting `DeviceResolutionIds` at the confirmed key
  position rather than just appending). Factored `override_attr` out of `ch5_button.py`
  into `toml_util.py` since `project.py` needed the identical operation. All verified via
  `generator/_test_output/phase5_smoke_test.py` (harness round-trip + structural checks;
  no real multi-resolution `.cuip` exists in the reference project to diff against, so
  verified against `build_project_attributes`' own confirmed shape instead, same standard
  used for Phase 2). Full writeup in `docs/architecture/05-resolutions.md`. Full
  multi-resolution reflow (the actual CSS math for non-primary resolutions) deliberately
  NOT built this slice — flagged as a separate, bigger follow-up.
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
