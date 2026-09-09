# Multi-resolution reflow — design spec

Date: 2026-09-08
Status: approved by user, ready for implementation plan

## Problem

Construct projects are pixel-adaptive per resolution, not responsive: every component's
position and size is a fixed number of CSS pixels within one resolution's own `@media`
breakpoint (confirmed throughout Phases 3-4). A resolution's dedicated `@media` block
only gets a CSS rule for an element if that element was fit into that specific
resolution — today the generator only ever writes one device-specific block (the
resolution the element was authored against) plus the `99999px` catch-all. Two related
gaps follow from this, both covered by the same underlying mechanism:

1. When a project that only has, say, a 1280×800 landscape resolution gains a second,
   smaller or differently-oriented resolution, nothing about the existing pages/widgets
   adapts automatically — a component placed near the right/bottom edge of the original
   canvas can end up off the new, smaller canvas entirely. Today
   `generator/project.py::add_resolutions_to_project` (Phase 5, first slice) only
   updates the `.cuip`'s resolution list; it does nothing to the pages/widgets that
   already exist.
2. Real UI work isn't a one-time event: a project may get new controls added to an
   existing page long after its resolutions were set up (e.g. Apple TV controls today,
   Cable box controls added to the same page next week). Those new controls only get a
   CSS rule in whichever resolution they were authored against — every *other*
   resolution the project already supports has no rule for them at all, the identical
   "missing block" problem as case 1, just triggered by adding content instead of
   adding a resolution.

This design covers both: reflow is a general-purpose operation, callable any time a
resolution's dedicated block is missing rules for elements that exist elsewhere in the
same file — not a one-shot side effect tied only to the moment a resolution is added.

## Scope

**In scope:**
- A standalone `reflow_file` operation, callable whenever a target resolution's block
  is missing elements that exist in a source resolution's block — used by both trigger
  points below.
- **Trigger 1:** `add_resolutions_to_project` adding one or more new resolutions (the
  target block starts empty).
- **Trigger 2:** the skill adding new elements (controls) to a page/widget that already
  has multiple resolutions (the target block already has content for other elements).
- Two fit modes on the same function (see Algorithm): `pin_existing` (leave what's
  already in the target alone, fit only the new elements) and `full_refit` (recompute
  every element from the source, discarding whatever was in the target).
- Both landscape→landscape (or portrait→portrait) reflow (fit from that orientation's
  own existing primary) and the orientation-bootstrap case (first resolution ever added
  in an orientation the project didn't have yet — fit from the *other* orientation's
  primary).
- Both `.cuig` (pages) and `.cuiw` (widgets) — same CSS shape, same reflow logic.
- Fitting is per-axis but no longer symmetric between axes: **X** gets a 4-tier
  fallback — move, then **wrap** overflowing elements onto new rows below, then
  compact whitespace, then scale down as a last resort; **Y** keeps the original
  3-tier fallback (move, compact, scale) but operates on **rows** (inferred from
  source Y-overlap) rather than individual elements once wrapping has run (see
  Algorithm).
- Best-effort overlap flagging between newly-fit elements and pinned pre-existing
  elements in `pin_existing` mode (see Algorithm and Error handling) — reported, not
  silently accepted, but not guaranteed avoided.

**Out of scope (this design):**
- Real 2D obstacle-avoidance placement — guaranteeing new elements never overlap
  *pinned* pre-existing elements would need genuine bin-packing/placement logic, not
  just the per-axis math this design uses. Deferred; `pin_existing` mode instead fits
  new elements as their own group and flags conflicts for manual adjustment in
  Construct.
- Authoring a new element directly against a non-primary resolution and reflowing
  outward from *that* resolution. This design assumes new elements are authored
  against the project's primary resolution for their orientation (`devices.py`'s
  existing highest-width-per-orientation notion, reused via `pick_primary`) and
  reflowed from there into every other resolution missing them.
- Resolution *removal* — needs no reflow math, just deleting that resolution's `@media`
  block.
- Reflowing hand-authored/non-generator CSS (e.g. the reference project's own
  `Component - Button.cuig`, which has complex, manually-edited rules). Reflow only
  understands the flat, one-`#id{...}`-rule-per-component shape this generator itself
  produces (`layout.py::build_position_css`'s output).
- Full 2D bin-packing/rearrangement — reading order (top-to-bottom, then
  left-to-right within a row) is always preserved; the one rearrangement this design
  performs is row-wrap (an overflowing row's trailing elements move to a new row
  directly below it, never reordered, never merged into an earlier or later row) —
  see Algorithm.
- Column-wrap (the height-constrained mirror of row-wrap: moving elements sideways
  when horizontal room is available but vertical room isn't). Row-wrap only.

## Data model

Position/size is CSS-only (never TOML — confirmed in Phase 4). A page/widget's
`{Css}` `99999px` catch-all block is the single source of truth for "where is
everything right now" for whichever resolution an element was last authored/fit
against, because a resolution's own dedicated `@media` block always mirrors the
catch-all block's values exactly at creation/fit time (confirmed against real Button1
and `Widget.cuiw`).

**A given `@media` query is not one block.** `layout.py::build_position_css` is called
once per element, so the real generator emits one `@media {query}{...}` pair *per
element*, not one shared block containing every element's rule — confirmed against a
real 3-button page (`ButtonVariants.cuig`): three separate `@media (max-width:
99999px){...}` blocks, one per button, all with the byte-identical query string, not
one block with three `#id{...}` rules inside it. (Found late — during the final
whole-branch review, 2026-09-09 — because every earlier task's tests hand-authored a
single combined block for convenience, a shape the generator itself never produces;
see Components below for the fix.) Reflow therefore parses **every** block matching a
given query, not just the first, merging their rules into one dict:

```python
{element_id: {"left": int, "top": int, "width": int, "height": int,
              "z_index": int | None, "extra_vars": {css_var_name: int}}}
```

`extra_vars` covers component-specific size-mirroring custom properties (e.g.
`--ch5-button--regular-width`/`-height`, see Phase 4) — scaled identically to the
`width`/`height` they mirror when (and only when) tier 3 scaling applies to that axis,
carried through unset (default → unset) otherwise.

Only the flat `#id{ prop: value; ... }` top-level rules are parsed; nested/child
selectors (e.g. the `.ch5-button :not(i):not(svg)` theme font-family rule) are left
alone — they carry no position data and don't need scaling.

## Algorithm

### Choosing which elements to fit: `pin_existing` vs `full_refit`

Given a file's already-parsed **source** elements (from the resolution the elements
were authored/last fit against — see Scope) and the **target** resolution's own
current block (empty if the target is brand new, per Trigger 1):

- **`pin_existing`** (default): diff element ids between source and the target's
  current block. Ids present in *both* are **pinned** — re-emitted into the new block
  with their existing target-resolution values completely unchanged, no tier logic
  applied. Ids present in source but *not* in the target's current block are **new** —
  these are the only elements that go through row detection and fitting (below),
  computed as their own group against the target's canvas dimensions (the pinned
  elements' space is not considered by the fit math). After fitting, a pairwise AABB overlap check runs
  between every new element's fitted rectangle and every pinned element's rectangle;
  any conflicts are collected as warnings (see Error handling) but do not block writing
  the file. Adding a brand-new resolution (Trigger 1) is the degenerate case where the
  target's current block is empty, so *every* source element is "new" and there are no
  pinned elements to check against — no special-casing needed, the same function
  handles both triggers.
- **`full_refit`**: the target's current block (if any) is ignored entirely; every
  element in source is treated as one group and goes through row detection and
  fitting, exactly as `pin_existing` does for brand-new targets. Carries the same full
  overlap-safety guarantee as before, since it's still "everyone moves together" with
  nothing pinned.

### Row detection

Before any fitting, the group being fit (all of source in `full_refit`, or just the
new elements in `pin_existing`) is partitioned into **rows**: sort the group by `top`,
then greedily cluster — an element joins the current row if its `[top, top + height]`
range overlaps the row's accumulated range so far; otherwise it starts a new row. Rows
are ordered top-to-bottom; within a row, elements keep their original left-to-right
order. This is the same "sort, preserve order" primitive the fit tiers already use,
just applied once up front on the Y axis to establish row membership. Row detection
looks only at the group's own source positions — pinned elements (in `pin_existing`
mode) are never part of a row and never participate in wrapping (see the Scope note on
2D obstacle avoidance).

### `fit_axis` (the core per-axis 3-tier fitter, unchanged)

The core fitter from the previous revision is unchanged in behavior, and is now reused
in two places: fitting elements *within a row* on the X axis, and fitting the *row
list itself* (rows treated as pseudo-elements) on the Y axis. Given a group of `(id,
pos, size)` items and a `target_dim`, `fit_axis` tries three tiers in order, stopping
at the first that fits, with a minimum visual gap of **4px** between neighbors wherever
gaps are involved (tiers 2 and 3):

**Tier 1 — Move (rigid group translate).** Compute the bounding-box span of the
group's source positions: `span = max(pos_i + size_i) - min(pos_i)`. If `span <=
target_dim`, shift every item by one constant offset so the bounding box lands inside
`[0, target_dim]` (clamp the low edge to 0, or the high edge to `target_dim`, whichever
the offset requires). Every item's relative position to every other item is preserved
exactly — no resize, no gap change. This is the only tier that can leave original
(non-4px-multiple) gaps untouched.

**Tier 2 — Reduce whitespace (order-preserving compaction).** If tier 1's span doesn't
fit, sort by position and reduce the gaps between items (and the leading margin, if
any) proportionally until the span fits — down to a floor of 4px between neighbors.
Sizes and order are untouched. Concretely: with the group sorted and translated so the
first item's leading edge is 0, `total_gap = span - sum(sizes)`; the amount that must
be removed is `span - target_dim`; each internal gap is shrunk by the same proportion,
clamped so no gap goes below 4px. If proportional shrinking to the 4px floor on every
gap is still not enough to fit, tier 2 does as much as it can (every gap at 4px) and
hands off to tier 3.

**Tier 3 — Scale down (uniform factor, last resort).** With every gap already at the
4px floor, if the span still exceeds `target_dim`, the items' own sizes are too big
regardless of spacing. Reserve room for the mandatory gaps first:
`available_for_sizes = target_dim - (n - 1) * 4`. Compute one scale factor:
`scale = available_for_sizes / sum(sizes)`. Apply `scale` to every item's size (and,
for elements specifically — not synthesized row pseudo-items — to any `extra_vars`
entry that mirrors this axis's size, see Data model) and re-pack in original order with
exactly 4px between neighbors: `new_pos[0] = 0`, `new_pos[i] = new_pos[i-1] +
new_size[i-1] + 4`.

**Insufficient-room edge case:** if `target_dim < (n - 1) * 4` (not even the mandatory
4px floor gaps fit for this many items), this call cannot fit at all. Handled by the
same policy as other unparseable/unfittable cases (see Error handling) — skipped with a
clear message identifying the file, axis, and item count; never a silent drop, never a
hard crash.

### X axis: wrap tier, inserted between move and compact

The X axis runs one extra tier, **between** `fit_axis`'s Tier 1 and Tier 2, working on
the *row list* rather than the whole group at once:

**Tier 1 (per row) — Move.** For each row independently, check whether that row's own
natural span (bounding box of just its own elements) fits `target_dim` via translate
alone — the same test as `fit_axis` Tier 1, scoped to one row. A row that passes needs
nothing further on X.

**Tier 2 — Wrap (new).** A row that fails the per-row Tier 1 check splits: peel
elements off its trailing end (rightmost, in original left-to-right order) one at a
time onto a brand-new row inserted directly after it, until the elements remaining in
the original row *do* pass the Tier 1 check. The peeled-off elements form a new row and
recursively go through the same Tier-1-then-wrap check — a very crowded row can split
into more than two. This terminates because peeling always shrinks the row by at least
one element, down to a single-element row in the worst case.

**Tiers 3/4 — Compact / scale.** A row that's down to a single element which *still*
doesn't fit target_dim on its own cannot wrap further. This is the only case where a
row falls through to `fit_axis`'s Tier 2/3 on the X axis — a no-op compaction (nothing
to compact with `n=1`) followed by scale-down, exactly like today's last-resort
behavior, scoped to that one element.

In practice, X positions are finalized by calling `fit_axis` once per row (against
`target_dim`) *after* wrapping has settled the row membership: every normal row
resolves via its own Tier 1 (trivial move, already guaranteed to fit by construction),
and the single-too-wide-element edge case resolves via `fit_axis`'s own Tier 2/3 — no
separate code path is needed for "apply the tiers within a row."

### Y axis: row-stacking

Once X-axis wrapping has finalized row membership, each row gets a natural height,
`max(top_i + height_i) - min(top_i)` over its own members.

A row's **anchor** is *not* simply its own `min(top_i)` — a row created by an X-axis
wrap split shares the exact same source `top` values as the row it split from
(splitting rearranges which elements belong to which row, but doesn't move anything
vertically by itself), so two sibling rows can tie (or, more generally, land at a
non-increasing gap) on raw `min(top)` even though they must end up on different lines.
To keep the row sequence valid before `fit_axis`'s own tiers run, rows are pre-stacked
sequentially: row 0's anchor is its own `min(top_i)`; each later row's anchor is its
predecessor's anchor plus the predecessor's natural height, plus that pair's own
**original** gap (`this row's min(top_i) - (previous row's min(top_i) + previous row's
natural height)`) when that gap is non-negative, or the 4px floor when it isn't
(covering both the wrap-split tie, gap exactly 0, and any other degenerate case where a
row's natural position would otherwise overlap or precede its predecessor).

This distinction matters: an earlier revision of this section used `max(its own
min(top_i), previous anchor + previous height + 4px)`, i.e. unconditionally forcing
*every* inter-row gap up to at least 4px — found and fixed during implementation
(2026-09-09) to be a real behavioral regression, not the harmless "no-op for ordinary
rows" it was assumed to be. `detect_rows` only guarantees a *non-negative* inter-row
gap (`top >= row_bottom`, not `top >= row_bottom + 4px`), so two rows separated by, say,
2px in the source — an entirely ordinary case, not a wrap-split artifact — would be
pushed 2px further apart than the source ever had them, contradicting the same
"preserve original gaps exactly, only enforce the 4px floor where compaction is
actually needed" principle `fit_axis`'s own Tier 1 already establishes (see the 3-tier
fit above: "the only tier that can leave original (non-4px-multiple) gaps untouched").
Worse, that injected spacing can push a row list that fit `target_height` perfectly
into needing Tier 2/3 compaction or scaling it never needed. The corrected formula
preserves the original gap exactly whenever it's already non-negative (a true no-op for
every ordinary row, matching Tier 1's own philosophy) and clamps only the genuinely
degenerate case (a non-positive or tied gap) to the 4px floor.

The row list — ordered top-to-bottom, unchanged from Row detection except for any
splits the wrap tier introduced — is fed to `fit_axis` as pseudo-items (`pos = anchor`
as computed above, `size = natural height`) against `target_height`. This is the *only*
Y-axis fitting that happens: no per-element Y tiers, no column-wrap (see Scope).

Whatever `fit_axis` computes for a row (`new_pos`, and `scale` — 1.0 unless the row
list needed Tier 3) is then applied to every element inside that row: `new_top =
row_new_pos + (element.top - row_anchor) * scale`, and if `scale != 1.0`, `new_height =
element.height * scale` (plus the matching `extra_vars` scaling, as in `fit_axis`
Tier 3). A row is a rigid sub-group for this purpose — elements keep their relative
vertical offsets within it, scaled uniformly if the row itself scales, since nothing
splits vertically within a row.

### Why this still can't introduce new overlaps within the fitted group

Two elements in the **same row** are disjoint on X by the same argument as before:
within-row X positions come from `fit_axis`, which never reorders and never lets a gap
go negative, so a monotonically non-decreasing, order-preserving sequence of positions
stays pairwise non-overlapping on X by construction.

Two elements in **different rows** are disjoint on Y without needing any per-element Y
check: the pre-stacking step guarantees rows enter `fit_axis` already in a valid,
non-decreasing, non-overlapping order — `anchor_i >= anchor_{i-1} + height_{i-1}`
always (the pair's own original, non-negative gap when there was one, else the 4px
floor; either way the next anchor never lands before the previous row's bottom) — and
`fit_axis` itself never reorders or lets a gap go negative, so rows stay pairwise
non-overlapping on Y by the same argument as any other group it fits, just applied one
level up to the row list. (The 4px *minimum visual gap* is guaranteed only where
`fit_axis`'s own tiers actually introduce or adjust a gap — Tier 1's rigid translate
still preserves whatever original gap a row list had, exactly like it does for
elements, per the "no-op" note above.) Every element's `top`/`height` stays within its
own row's Y-extent (`anchor` to `anchor + height`) by definition, so two elements in
different rows inherit their rows' Y-separation.

So every pair in the fitted group is separated on at least one axis — X within a row,
Y across rows — with no 2D collision detection required. This guarantee does **not**
extend to pinned elements in `pin_existing` mode — see the Out-of-scope note above and
Error handling below.

## Choosing the source resolution

- If the project already has at least one resolution in the *new* resolution's
  orientation, the source is that orientation's own primary (highest width in that
  orientation) — its already-fitted content is the right basis.
- If this is the first resolution ever added in that orientation (a brand-new
  orientation for the project), the source is the *other* orientation's primary instead.
  The per-axis algorithm above handles the swap correctly on its own (landscape's
  width-axis becomes portrait's own width-axis, etc.) — no special-cased math, just a
  different source block chosen once per call.
- "Primary" resolution selection (highest width per orientation) reuses
  `generator/devices.py`-shaped resolution dicts already stored in the project's
  `{DeviceResolutionSource}` (read via `project.py::read_cuip`).
- This is also the resolution new elements (Trigger 2) are assumed authored against —
  see the Out-of-scope note on non-primary authoring.

## Integration

- **Trigger 1 (unchanged entry point):** `add_resolutions_to_project(cuip_path,
  new_resolutions)` — after writing the updated `.cuip` (existing behavior, unchanged)
  — walks every `*.cuig`/`*.cuiw` file in the project's own folder and, for each
  *newly-added* resolution, calls `reflow.reflow_file(path, target_resolution,
  source_resolution, mode="pin_existing")`. Since the target block is empty, this is
  equivalent to fitting every source element fresh — the general function needs no
  special-casing for this trigger.
- **Trigger 2 (new):** when the skill adds new elements to a page/widget in a project
  that has more than one resolution in the relevant orientation, the skill asks the
  user how to handle the project's *other* resolutions before finishing: leave existing
  controls alone and fit just the new ones (`pin_existing`, the recommended default),
  fully re-fit the whole page/widget (`full_refit`), or skip reflow for now. Whichever
  the user picks, the skill calls `reflow.reflow_file` once per other resolution that
  doesn't yet have the new elements, with the corresponding mode. This is a
  conversational/process step at the skill layer, not new logic inside
  `reflow_file` itself — `mode` is the only thing that changes.

## Components (new/changed code)

- **`generator/layout.py`** (extend, don't replace): add `parse_position_rules(css_text)
  -> dict[element_id, ParsedElement]` (the flat-rule parser described above) and
  `build_reflow_block(elements, resolution) -> str` (the N-element `@media` block
  builder, factored so `build_position_css`'s device-block logic can share it for the
  single-element case it already handles — this factoring, called for here since the
  spec's first draft, was actually done as part of the final-review fix, 2026-09-09,
  see `_device_rule_decls` below). Also add `find_media_block_spans(css_text, query) ->
  list[tuple[int, int]]` and `parse_all_position_rules(css_text, query) -> dict[element_id,
  ParsedElement]` (added 2026-09-09, final whole-branch review): per the Data model
  note above, a query can match more than one block, so every reflow caller that needs
  "every element for this query" must use these, not the single-match
  `find_media_block_span`/`find_media_block`, which remain for callers that
  deliberately want only the first (none currently do, post-fix, but the distinction
  is kept explicit rather than removing the single-match functions).
- **`generator/reflow.py`** (new):
  - `reflow_file(path, target_resolution, source_resolution, mode="pin_existing") ->
    ReflowResult` — the general entry point for both triggers. Reads the file's
    `{Css}` (and `{PageAttributes}`/`{Html}` — needed to re-write the file, but
    untouched), parses **every** block matching the source query and every block
    matching the target query (via `find_media_block_spans`/`parse_all_position_rules`
    — not just the first, see Data model), splits into pinned/new per `mode`, fits the
    new group via `fit_axis`, runs the pinned/new overlap check when
    `mode="pin_existing"`, then on write: replaces the *first* matching target span
    with the one consolidated new `@media` block and deletes every other matching
    target span entirely (splicing from the end backward so earlier indices stay
    valid) — added 2026-09-09 (final whole-branch review) once multi-block-per-query
    was confirmed; the original design assumed one block per query and would leave
    duplicate `#id{}` rules under the same query if left unfixed. `ReflowResult`
    carries `warnings: list[str]` (overlap conflicts, skipped-axis messages) so
    callers/the skill can surface them instead of assuming a silently clean result.
  - `fit_axis(items, target_dim, min_gap=4) -> dict[item_id, {"pos": int, "size":
    int, "scale": float}]` — the core 3-tier fitter described in Algorithm
    (`fit_axis` section). `items` is `[(item_id, pos, size)]` — either elements (X
    axis, within one row) or row pseudo-items (Y axis, the row list). `scale` is `1.0`
    unless tier 3 applied, so callers know whether to also scale that item's
    `extra_vars`/height entries.
  - `detect_rows(elements) -> list[list[element_id]]` — the row-detection primitive
    described in Algorithm: sorts by `top` and greedily clusters by Y-overlap into
    ordered rows.
  - `wrap_rows(rows, target_width, min_gap=4) -> list[list[element_id]]` — the X-axis
    wrap tier: for each row, checks the per-row Tier-1 move test and, if it fails,
    peels trailing elements onto new rows (recursively) until every row either passes
    Tier 1 or is down to a single still-too-wide element. Returns the finalized
    (possibly longer) row list; actual positions are then computed by calling
    `fit_axis` once per row.
  - `stack_rows(rows, target_height, min_gap=4) -> dict[element_id, {"top": int,
    "height": int, "scale": float}]` — the Y-axis row-stacking step: builds row
    pseudo-items from `rows` (natural height per row, plus the pre-stacked anchor —
    each row's own original inter-row gap when non-negative, else the `min_gap` floor;
    a true no-op for ordinary rows, only clamping the degenerate wrap-created-sibling
    tie, see Algorithm — corrected 2026-09-09 from an earlier, unconditional-4px-floor
    version found to be a real behavioral regression during implementation), calls
    `fit_axis` against `target_height`, then maps each row's `(pos, scale)` back onto
    its elements (`new_top = row_pos + (element.top - row's_own_min_top) * scale`,
    `new_height = int(element.height * scale)` when `scale != 1.0` — `int()`
    truncation, not `round()`, matching `fit_axis`'s own Tier 3 convention exactly,
    since the element spanning a row's full natural extent must equal that row's own
    `fit_axis`-computed size bit-for-bit) — note the per-element offset is taken from
    the row's *own* raw `min(top)`, not its pre-stacked anchor, since that offset only
    needs to preserve each element's position relative to its row's other members.
  - `find_new_elements(source_elements, target_elements) -> tuple[set[str],
    set[str]]` — returns `(new_ids, pinned_ids)`, the id-set diff described above.
  - `check_overlaps(pinned_elements, new_elements) -> list[tuple[str, str]]` — pairwise
    AABB overlap check between two element-rect dicts, used only for `pin_existing`
    mode's warning surface.
  - `pick_primary(resolutions, orientation) -> dict | None` and
    `choose_source_resolution(existing_resolutions, new_resolution) -> dict` implement
    the "which resolution do we fit from" rule above, generic over
    `devices.py`-shaped resolution dicts.
- **`generator/project.py::add_resolutions_to_project`** (extend): after the existing
  `.cuip` write, call `reflow.reflow_file(..., mode="pin_existing")` for every
  `*.cuig`/`*.cuiw` in `cuip_path.parent`, once per newly-added resolution.

## Error handling

- A page/widget whose catch-all block doesn't parse cleanly (non-generator CSS, or a
  component with no position rule at all) is skipped with a clear message identifying
  the file and element — never silently dropped, never a hard crash that aborts
  reflowing the *rest* of the project's files.
- If the chosen source resolution's own dedicated block is missing from a given file
  (added 2026-09-09, final whole-branch review) — the realistic case being a page
  authored before the project had *any* resolution, which only ever gets the
  `99999px` catch-all block (see `layout.py`'s no-devices-yet fallback) — `reflow_file`
  falls back to the `99999px` catch-all block as the source before giving up. Without
  this, a page that predates the project's first resolution can never gain a device
  block for any *later*-added resolution either: the first add has no source to
  reflow from (nothing existing yet) and skips it outright, so the file never gets a
  device-specific block for that first resolution to source *subsequent* adds from.
  The catch-all is always a valid source per the Data model note above (a device
  block always mirrors it exactly at creation/fit time), so this fallback never
  changes the algorithm, only which existing block supplies the starting data.
- A `fit_axis` call that can't fit even the mandatory 4px-floor gaps for its item count
  (see the `fit_axis` section's insufficient-room edge case) is skipped the same way —
  clear message naming the file, axis, and item count, rest of the project's files
  still processed. This applies both to a single-element row that's still too wide
  after wrapping (X) and to the row list itself not fitting `target_height` even at
  4px floor gaps between rows (Y) — same underlying check, two different callers.
- In `pin_existing` mode, any new element whose fitted rectangle overlaps a pinned
  element's rectangle is reported in `ReflowResult.warnings` (file, both element ids,
  both rectangles) — the file is still written with the best-effort fit; this is a
  known limitation (see Scope), not an error, and the skill is responsible for
  surfacing it to the user as something to check in Construct.
- Adding a resolution that's already orientation-primary-less on both sides (a
  brand-new project with zero prior resolutions) is not a reflow case at all — nothing
  to fit from, nothing to reflow; `add_resolutions_to_project` already handles the
  "starts with zero resolutions" case for the `.cuip` itself (Phase 5 first slice) and
  reflow simply does nothing when there are no *existing* resolutions to have placed
  content at.

## Testing

- Unit-level: `parse_position_rules` round-trips a known CSS string into the expected
  dict; `build_reflow_block` produces the expected CSS for a known element dict +
  resolution; `choose_source_resolution` picks the right primary for same-orientation vs.
  bootstrap-new-orientation cases; `find_new_elements` correctly splits a known
  source/target id set into new vs. pinned; `check_overlaps` correctly flags a
  deliberately-overlapping pair and correctly reports no conflicts for a
  non-overlapping pair.
- **Added 2026-09-09 (final whole-branch review): at least one scenario must build its
  test CSS the way the real generator actually does** — one `@media {query}{...}` pair
  per element via `layout.py::build_position_css` (or the equivalent
  `ch5_button.py::build_default_button_element`), concatenated, never a single
  hand-authored block containing multiple `#id{}` rules. Every earlier test in this
  plan used the latter (hand-idealized) shape, which is why the multi-block-per-query
  bug (see Data model) went undetected through nine tasks' worth of review plus a full
  integration suite. `parse_all_position_rules`/`find_media_block_spans` need their own
  direct unit tests too: a query matching zero, one, and three separate blocks;
  `reflow_file`'s write path consolidating three matching target spans down to exactly
  one with no id duplicated and no id lost.
- **Determinism:** `reflow_file`'s emitted rule order (and `ReflowResult.warnings`
  order) must not depend on Python's per-process string-hash randomization — iterate
  `source_elements`/`target_elements` (dict insertion order, deterministic) when
  building the `pinned`/`to_fit` groups, never the `new_ids`/`pinned_ids` sets
  `find_new_elements` returns. A regression test should run the same input twice (or
  compare against a hardcoded expected order) and assert identical output both times.
- `fit_axis` unit tests, one per tier plus the edge case:
  - Tier 1: items whose bounding box already fits target_dim once translated — confirm
    relative gaps between items are byte-for-byte unchanged, only a constant offset
    applied.
  - Tier 2: items whose bounding box needs gap compaction — confirm sizes/order
    unchanged, gaps shrink proportionally, no gap ends up below 4px, final span equals
    target_dim.
  - Tier 3: items whose combined sizes exceed target_dim even at the 4px floor —
    confirm sizes scale down by one shared factor, final layout is packed at exactly
    4px gaps, and `extra_vars` mirroring that axis scale identically (elements only —
    row pseudo-items carry no `extra_vars`).
  - Edge case: item count large enough that `(n-1)*4 > target_dim` — confirm the call
    is skipped with a clear message, not a crash, and other items/files still process.
- `detect_rows` unit tests: a single row (all elements' Y-ranges mutually overlap), two
  cleanly separated rows, and a row containing elements with different (but
  Y-overlapping) `top`/`height` values — confirm row membership and top-to-bottom,
  left-to-right ordering.
- `wrap_rows` unit tests: a row that already fits (no split), a row that needs exactly
  one split, a row dense enough to need multiple splits, and a single element wider
  than `target_width` on its own (confirm it's left as a one-element row rather than
  looping forever).
- `stack_rows` unit tests: multiple rows that fit via row-level Tier 1 (move) —
  confirm each element's offset from its row's anchor is preserved exactly; a row list
  needing Tier 3 (scale) — confirm every element in a scaled row has its `top` offset
  and `height` scaled by the same factor as its row.
- Mode scenario tests:
  - `pin_existing` with an empty target block (Trigger 1's case) — confirm identical
    output to fitting the whole source group fresh (proves the unification claim).
  - `pin_existing` with a non-empty target block — confirm pinned elements are
    byte-for-byte unchanged in the output, new elements are on-canvas and
    non-overlapping *among themselves*, and a deliberately-crowded case produces a
    `check_overlaps` warning rather than silently proceeding.
  - `full_refit` on a target that already had different (e.g. hand-adjusted) positions
    — confirm the previous target positions are NOT preserved and the whole group is
    refit fresh from source, proving the two modes actually differ.
- Scenario tests (the real point of this feature): build a synthetic page with a
  component deliberately placed near the right/bottom edge of a 1280×800 landscape
  canvas, add a smaller landscape resolution (e.g. 640×360, TSW-570) and confirm the
  component's new coordinates are on-canvas via the cheapest tier that applies (assert
  which tier fired); separately, build a case dense enough to force tier 2 (compaction)
  and a case dense enough to force tier 3 (scaling), and confirm no two elements'
  resulting rectangles overlap (a direct AABB check across all pairs, not just a
  trust-the-math assertion) in every scenario. Also add a portrait resolution to a
  landscape-only project and confirm the bootstrap case produces sane on-canvas
  coordinates.
- Wrap scenario test: build a synthetic single-row source layout (e.g. 4 buttons side
  by side on a 1280px-wide canvas) that fits comfortably at the source width but
  doesn't fit a much narrower target width via translate alone (i.e. a case that would
  previously have fallen through to compaction/scaling); reflow to that narrower
  target and confirm the row actually splits (more than one
  row in the output), the split-off elements land below the original row with at least
  a 4px vertical gap, no element is scaled down (proving wrap was preferred over
  scale, per the approved tier order), and a direct pairwise AABB check across every
  element (not just within a row) confirms no overlaps anywhere in the result.
- Round-trip every produced file through `harness/compare.py`, per this project's
  standing verification requirement.
- Manual Construct verification: (1) add a real second (smaller or portrait) resolution
  to the on-disk `C:\Solutions\ClaudeGenTest\GenTestProject` verification project and
  have the user confirm in Construct that switching to the new resolution shows
  components correctly positioned on-canvas, not clipped off the edge, and not
  overlapping; (2) add a new control to that project's page in `pin_existing` mode and
  have the user confirm in Construct that the other resolution's existing controls
  didn't move and the new control appears on-canvas.
