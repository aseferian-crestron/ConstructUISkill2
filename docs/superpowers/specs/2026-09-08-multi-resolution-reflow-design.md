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
- Fitting via a 3-tier fallback per axis: move, then compact whitespace, then scale
  down as a last resort (see Algorithm).
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
- 2D bin-packing/rearrangement — elements never change relative order (left-to-right,
  top-to-bottom) on either axis; see Algorithm.

## Data model

Position/size is CSS-only (never TOML — confirmed in Phase 4). A page/widget's
`{Css}` `99999px` catch-all block is the single source of truth for "where is
everything right now" for whichever resolution an element was last authored/fit
against, because a resolution's own dedicated `@media` block always mirrors the
catch-all block's values exactly at creation/fit time (confirmed against real Button1
and `Widget.cuiw`). Reflow parses a block (catch-all or any one resolution's
device-specific block) back into:

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
  these are the only elements that go through the 3-tier fit (below), computed as
  their own group against the target's canvas dimensions (the pinned elements' space
  is not considered by the fit math). After fitting, a pairwise AABB overlap check runs
  between every new element's fitted rectangle and every pinned element's rectangle;
  any conflicts are collected as warnings (see Error handling) but do not block writing
  the file. Adding a brand-new resolution (Trigger 1) is the degenerate case where the
  target's current block is empty, so *every* source element is "new" and there are no
  pinned elements to check against — no special-casing needed, the same function
  handles both triggers.
- **`full_refit`**: the target's current block (if any) is ignored entirely; every
  element in source is treated as one group and fit via the 3-tier algorithm, exactly
  as `pin_existing` does for brand-new targets. Carries the same full overlap-safety
  guarantee as before, since it's still "everyone moves together" with nothing pinned.

### 3-tier fit (per axis)

Each axis (X: `left`/`width`; Y: `top`/`height`) is fit **independently**, in a 3-tier
fallback, for whichever group of elements is being fit (all of source in `full_refit`,
or just the new elements in `pin_existing`). Tiers are tried in order per axis; an axis
stops at the first tier that fits. A minimum visual gap of **4px** applies between
neighboring elements *within the group being fit* wherever gaps are involved (tiers 2
and 3) — elements may end up exactly 4px apart but never closer, and never overlapping
each other.

**Tier 1 — Move (rigid group translate).** Compute the bounding-box span of the
group's source positions on this axis: `span = max(pos_i + size_i) - min(pos_i)`. If
`span <= target_dim`, shift every element in the group by one constant offset so the
bounding box lands inside `[0, target_dim]` (clamp the low edge to 0, or the high edge
to `target_dim`, whichever the offset requires). Every element's relative position to
every other element *in the group* is preserved exactly — no resize, no gap change.
This is the only tier that can leave original (non-4px-multiple) gaps untouched.

**Tier 2 — Reduce whitespace (order-preserving compaction).** If tier 1's span doesn't
fit, sort the group by position on this axis and reduce the gaps between them (and the
leading margin, if any) proportionally until the span fits — down to a floor of 4px
between neighbors. Sizes and order are untouched. Concretely: with the group sorted and
translated so the first element's leading edge is 0, `total_gap = span - sum(sizes)`;
the amount that must be removed is `span - target_dim`; each internal gap is shrunk by
the same proportion, clamped so no gap goes below 4px. If proportional shrinking to the
4px floor on every gap is still not enough to fit, tier 2 does as much as it can (every
gap at 4px) and hands off to tier 3.

**Tier 3 — Scale down (uniform factor, last resort).** With every gap already at the
4px floor, if the span still exceeds `target_dim`, the elements' own sizes are too big
regardless of spacing. Reserve room for the mandatory gaps first:
`available_for_sizes = target_dim - (n - 1) * 4`. Compute one scale factor for this
axis: `scale = available_for_sizes / sum(sizes)`. Apply `scale` to every element's size
on this axis (and to any `extra_vars` entry that mirrors this axis's size — see Data
model) and re-pack them in original order with exactly 4px between neighbors:
`new_pos[0] = 0`, `new_pos[i] = new_pos[i-1] + new_size[i-1] + 4`.

**Why this can't introduce new overlaps within the fitted group:** two elements in the
group that don't overlap at their source positions are guaranteed disjoint (non-
touching or separated) on at least one axis. Tier 1 shifts every element by the same
constant, so relative positions — and thus whichever axis was already the separating
one for any given pair — are unchanged. Tiers 2 and 3 never reorder elements and never
let a gap go negative (floor of 4px, or 0 only in the degenerate n=1 case where there
is no neighbor) — a monotonically non-decreasing, order-preserving sequence of
positions with non-negative gaps stays pairwise non-overlapping on that axis by
construction. No 2D collision detection is needed *for the group being fit*. This
guarantee does **not** extend to pinned elements in `pin_existing` mode — see the
Out-of-scope note above and Error handling below.

**Insufficient-room edge case:** if `target_dim < (n - 1) * 4` (not even the mandatory
4px floor gaps fit for this many elements), this axis cannot be reflowed at all. Handled
by the same policy as other unparseable/unfittable cases (see Error handling) — skipped
with a clear message identifying the file, axis, and element count; never a silent drop,
never a hard crash.

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
  single-element case it already handles).
- **`generator/reflow.py`** (new):
  - `reflow_file(path, target_resolution, source_resolution, mode="pin_existing") ->
    ReflowResult` — the general entry point for both triggers. Reads the file's
    `{Css}` (and `{PageAttributes}`/`{Html}` — needed to re-write the file, but
    untouched), parses source and (if present) the target's current dedicated block,
    splits into pinned/new per `mode`, fits the new group via `fit_axis`, runs the
    pinned/new overlap check when `mode="pin_existing"`, appends the new `@media`
    block, writes back. `ReflowResult` carries `warnings: list[str]` (overlap
    conflicts, skipped-axis messages) so callers/the skill can surface them instead of
    assuming a silently clean result.
  - `fit_axis(items, target_dim, min_gap=4) -> dict[element_id, {"pos": int, "size":
    int, "scale": float}]` — the core 3-tier fitter described in Algorithm. `items` is
    `[(element_id, pos, size)]` for one axis of the group being fit. `scale` is `1.0`
    unless tier 3 applied, so callers know whether to also scale that element's
    `extra_vars` entries for this axis.
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
- An axis that can't fit even the mandatory 4px-floor gaps for its element count (see
  Algorithm's insufficient-room edge case) is skipped the same way — clear message
  naming the file, axis, and element count, rest of the project's files still processed.
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
- `fit_axis` unit tests, one per tier plus the edge case:
  - Tier 1: elements whose bounding box already fits target_dim once translated —
    confirm relative gaps between elements are byte-for-byte unchanged, only a constant
    offset applied.
  - Tier 2: elements whose bounding box needs gap compaction — confirm sizes/order
    unchanged, gaps shrink proportionally, no gap ends up below 4px, final span equals
    target_dim.
  - Tier 3: elements whose combined sizes exceed target_dim even at the 4px floor —
    confirm sizes scale down by one shared factor, final layout is packed at exactly
    4px gaps, and `extra_vars` mirroring that axis scale identically.
  - Edge case: element count large enough that `(n-1)*4 > target_dim` — confirm the
    axis is skipped with a clear message, not a crash, and other elements/files still
    process.
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
- Round-trip every produced file through `harness/compare.py`, per this project's
  standing verification requirement.
- Manual Construct verification: (1) add a real second (smaller or portrait) resolution
  to the on-disk `C:\Solutions\ClaudeGenTest\GenTestProject` verification project and
  have the user confirm in Construct that switching to the new resolution shows
  components correctly positioned on-canvas, not clipped off the edge, and not
  overlapping; (2) add a new control to that project's page in `pin_existing` mode and
  have the user confirm in Construct that the other resolution's existing controls
  didn't move and the new control appears on-canvas.
