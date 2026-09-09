# Multi-resolution reflow — design spec

Date: 2026-09-08
Status: approved by user, ready for implementation plan

## Problem

Construct projects are pixel-adaptive per resolution, not responsive: every component's
position and size is a fixed number of CSS pixels within one resolution's own `@media`
breakpoint (confirmed throughout Phases 3-4). When a project that only has, say, a
1280×800 landscape resolution gains a second, smaller or differently-oriented resolution
(a smaller landscape panel, or a portrait resolution added to a landscape-only project),
nothing about the existing pages/widgets adapts automatically — a component placed near
the right or bottom edge of the original canvas can end up positioned off the new,
smaller canvas entirely. Today `generator/project.py::add_resolutions_to_project`
(Phase 5, first slice) only updates the `.cuip`'s resolution list; it does nothing to the
pages/widgets that already exist. This design covers making that automatic and correct.

## Scope

**In scope:**
- Reflowing existing pages' and widgets' component positions/sizes when
  `add_resolutions_to_project` adds one or more new resolutions.
- Both landscape→landscape (or portrait→portrait) reflow (scale from that orientation's
  own existing primary) and the orientation-bootstrap case (first resolution ever added
  in an orientation the project didn't have yet — scale from the *other* orientation's
  primary).
- Both `.cuig` (pages) and `.cuiw` (widgets) — same CSS shape, same reflow logic.
- Fitting a smaller canvas via a 3-tier fallback (move, then compact whitespace, then
  scale down as a last resort — see Algorithm below), rather than always scaling first.

**Out of scope (this design):**
- Resolution *removal* — needs no reflow math, just deleting that resolution's `@media`
  block.
- Reflowing hand-authored/non-generator CSS (e.g. the reference project's own
  `Component - Button.cuig`, which has complex, manually-edited rules). Reflow only
  understands the flat, one-`#id{...}`-rule-per-component shape this generator itself
  produces (`layout.py::build_position_css`'s output).
- Re-reflowing on every edit (e.g. after a user moves a component in Construct) — this
  design only covers the moment a resolution is *added*.
- 2D bin-packing/rearrangement — elements never change relative order (left-to-right,
  top-to-bottom) on either axis; see Algorithm.

## Data model

Position/size is CSS-only (never TOML — confirmed in Phase 4). A page/widget's
`{Css}` `99999px` catch-all block is the single source of truth for "where is
everything right now," because a resolution's own dedicated `@media` block always
mirrors the catch-all block's values exactly at creation time (confirmed against real
Button1 and `Widget.cuiw`). Reflow parses that block back into:

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

Given a page/widget's parsed catch-all elements, a **source** resolution (width×height)
and a **target** (the newly-added resolution, width×height), each axis (X: `left`/
`width`; Y: `top`/`height`) is fit **independently**, in a 3-tier fallback. Tiers are
tried in order per axis; an axis stops at the first tier that fits. A minimum visual gap
of **4px** applies between neighboring elements on an axis wherever gaps are involved
(tiers 2 and 3) — elements may end up exactly 4px apart but never closer, and never
overlapping.

**Tier 1 — Move (rigid group translate).** Compute the bounding-box span of all
elements' source positions on this axis: `span = max(pos_i + size_i) - min(pos_i)`. If
`span <= target_dim`, shift every element by one constant offset so the bounding box
lands inside `[0, target_dim]` (same clamp direction as the prior design: clamp the
low edge to 0, or the high edge to `target_dim`, whichever the offset requires). Every
element's relative position to every other element is preserved exactly — no resize, no
gap change. This is the only tier that can leave original (non-4px-multiple) gaps
untouched.

**Tier 2 — Reduce whitespace (order-preserving compaction).** If tier 1's span doesn't
fit, sort elements by position on this axis and reduce the gaps between them (and the
leading margin, if any) proportionally until the span fits — down to a floor of 4px
between neighbors. Sizes and order are untouched. Concretely: with elements sorted and
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

**Why this can't introduce new overlaps:** two elements that don't overlap in the source
layout are guaranteed disjoint (non-touching or separated) on at least one axis. Tier 1
shifts every element by the same constant, so relative positions — and thus whichever
axis was already the separating one for any given pair — are unchanged. Tiers 2 and 3
never reorder elements and never let a gap go negative (floor of 4px, or 0 only in the
degenerate n=1 case where there is no neighbor) — a monotonically non-decreasing,
order-preserving sequence of positions with non-negative gaps stays pairwise
non-overlapping on that axis by construction. No 2D collision detection is needed.

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

## Integration

`add_resolutions_to_project(cuip_path, new_resolutions)` — after writing the updated
`.cuip` (existing behavior, unchanged) — walks every `*.cuig`/`*.cuiw` file in the
project's own folder and, for each *newly-added* resolution, adds a correctly-reflowed
`@media` block to that file (one call per file per new resolution). One user-facing
operation, matching the spec's own wording ("add/remove resolutions and reflow the
project as required") and your explicit choice not to split it into two steps.

## Components (new/changed code)

- **`generator/layout.py`** (extend, don't replace): add `parse_position_rules(css_text)
  -> dict[element_id, ParsedElement]` (the flat-rule parser described above) and
  `build_reflow_block(elements, resolution) -> str` (the N-element `@media` block
  builder, factored so `build_position_css`'s device-block logic can share it for the
  single-element case it already handles).
- **`generator/reflow.py`** (new):
  - `reflow_file(path, source_resolution, target_resolution) -> None` — read the file's
    `{Css}` (and `{PageAttributes}`/`{Html}` — needed to re-write the file, but
    untouched), parse, fit both axes, append the new block, write back.
  - `fit_axis(items, target_dim, min_gap=4) -> dict[element_id, {"pos": int, "size":
    int, "scale": float}]` — the core 3-tier fitter described in Algorithm. `items` is
    `[(element_id, pos, size)]` for one axis of one element group. `scale` is `1.0`
    unless tier 3 applied, so callers know whether to also scale that element's
    `extra_vars` entries for this axis.
  - `pick_primary(resolutions, orientation) -> dict | None` and
    `choose_source_resolution(existing_resolutions, new_resolution) -> dict` implement
    the "which resolution do we scale from" rule above, generic over
    `devices.py`-shaped resolution dicts.
- **`generator/project.py::add_resolutions_to_project`** (extend): after the existing
  `.cuip` write, call `reflow.reflow_file` for every `*.cuig`/`*.cuiw` in
  `cuip_path.parent`, once per newly-added resolution.

## Error handling

- A page/widget whose catch-all block doesn't parse cleanly (non-generator CSS, or a
  component with no position rule at all) is skipped with a clear message identifying
  the file and element — never silently dropped, never a hard crash that aborts
  reflowing the *rest* of the project's files.
- An axis that can't fit even the mandatory 4px-floor gaps for its element count (see
  Algorithm's insufficient-room edge case) is skipped the same way — clear message
  naming the file, axis, and element count, rest of the project's files still processed.
- Adding a resolution that's already orientation-primary-less on both sides (a
  brand-new project with zero prior resolutions) is not a reflow case at all — nothing
  to scale from, nothing to reflow; `add_resolutions_to_project` already handles the
  "starts with zero resolutions" case for the `.cuip` itself (Phase 5 first slice) and
  reflow simply does nothing when there are no *existing* resolutions to have placed
  content at.

## Testing

- Unit-level: `parse_position_rules` round-trips a known CSS string into the expected
  dict; `build_reflow_block` produces the expected CSS for a known element dict +
  resolution; `choose_source_resolution` picks the right primary for same-orientation vs.
  bootstrap-new-orientation cases.
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
- Manual Construct verification: add a real second (smaller or portrait) resolution to
  the on-disk `C:\Solutions\ClaudeGenTest\GenTestProject` verification project and have
  the user confirm in Construct that switching to the new resolution shows components
  correctly positioned on-canvas, not clipped off the edge, and not overlapping.
