# Reflow: column-aware row fitting — design spec

Amends `docs/superpowers/specs/2026-09-08-multi-resolution-reflow-design.md` (the
move → wrap → compact → scale algorithm) and
`docs/superpowers/specs/2026-09-10-reflow-centering-design.md` (centering). Neither
`fit_axis`'s three tiers, `stack_rows`' Y-axis stacking, nor centering change in this
amendment — this adds a new grouping step that runs *before* `fit_axis` is ever called
for the X axis, so everything downstream keeps working exactly as already specced,
just fed columns instead of raw elements.

## Problem

Found 2026-09-10, live-testing TSW-570 (640x360) in Construct: a `ch5-dpad` shares a
`detect_rows` row with two Up/Down button pairs (the D-pad's own height Y-overlaps both
pairs, bridging them into one row). Each pair is two elements stacked at the exact same
source `left` (confirmed: `iha5b0tdmap0q`/`i4rvpkl9kjg7k` both `left=292`) — they don't
compete for horizontal space at all; they're a vertical stack occupying one visual
column. But `_fit_group`'s X-loop feeds `wrap_rows`/`fit_axis` one item per *element*,
which has no concept of this:

- Without wrapping, `fit_axis` would try to place the two same-`left` elements
  side-by-side (their sort-by-`left` tie doesn't stop it from assigning them different
  X positions), corrupting the pair's stacked layout.
- With wrapping (the actual TSW-570 case, row span too wide for the target), `wrap_rows`
  peels elements off the row's trailing end one at a time — which tears the right pair's
  two members apart from each other only by accident (they happen to be adjacent in
  peel order), and in general nothing stops a peel from splitting a pair mid-stack. The
  peeled member(s) land in a wrapped row below, wasting vertical space the row-stack
  didn't need to spend — which is what forced Tier 3 to over-compress the other rows'
  buttons down to an illegibly small height in the reported symptom.

## Scope

Only changes how a row's members are *grouped* for X-axis purposes, and how a peel
(wrap) treats that grouping. Y-axis stacking (`stack_rows`) is unaffected — see below.
Centering (`fit_axis`'s `source_dim`/`center`) is unaffected — it operates on whatever
items it's given, columns included, exactly as it already does for elements.

Out of scope: recognizing 2D grid structure beyond one level (a column's own members
are never further sub-grouped); a column is always atomic for wrap purposes (never
split across a peel boundary), which the "no unrequested complexity" default already
covers — if a single column is itself wider than the target, it falls through to
`fit_axis`'s own compact/scale tiers exactly like any single flat item does today, no
new tier needed.

## Algorithm

### `detect_columns` (new, transposes `detect_rows` onto the X axis)

```
detect_columns(elements, row: list[str]) -> list[list[str]]
```

Given one already-detected row's member ids, sort by `left`, then greedily cluster by
**X-range overlap** — the exact transpose of `detect_rows`'s own Y-overlap clustering
(`detect_rows` sorts by `top`/clusters by `[top, top+height)` overlap; this sorts by
`left`/clusters by `[left, left+width)` overlap, growing the accumulated
`[column_left, column_right)` range the same way `row_bottom` grows today). Returns
columns left-to-right; within a column, ids are ordered top-to-bottom by `top` (natural
reading order for a vertical stack — the transpose of `detect_rows`' own left-to-right
member ordering).

For the reported row: `[iha5b0(left 292-398), i4rvpkl(292-398), ilqek(474-806),
im68at(876-982), i66ouw(876-982)]` sorted by left → cluster: `iha5b0`/`i4rvpkl` overlap
(identical range) → one column; `ilqek`'s range doesn't overlap that column's
accumulated `[292,398)` → new column; `im68at`/`i66ouw` overlap each other, don't
overlap `ilqek`'s `[474,806)` → third column. Result: `[[iha5b0,i4rvpkl], [ilqek],
[im68at,i66ouw]]` — matches the visual grouping exactly.

A row with no same-`left`-range members produces one single-element column per
element — the degenerate case, identical in effect to today's flat per-element
behavior. So this is additive, not a behavior change, for every row shape this
project's existing samples/tests already cover.

**Confirmed by hand-tracing the real TSW-570 (640px) numbers**: with the 5 elements
grouped into 3 columns (widths 106/332/106, positions translated to 0/182/584), Tier 2
compaction alone — no wrapping at all — fits the row exactly: `needed_reduction=50`,
`slack=138` (comfortably enough), producing a final span of exactly 640px. The row
never needed to wrap in the first place; the flat 5-element model's tied-position pair
was throwing off the gap math (two elements at the same `left` produce a nonsensical
negative gap in a flat, order-preserving fitter) badly enough that `wrap_rows` decided
splitting was necessary when it wasn't. This directly confirms the reported
symptom's own root cause and the fix's effect on it, not just the general mechanism.

### Wiring into `_fit_group`'s X-loop

Today (`generator/reflow.py:483`, `_fit_group`):

```python
for row, is_fragment in wrapped_rows:
    row_items = [(eid, elements[eid]["left"], elements[eid]["width"]) for eid in row]
    ...
    x_fit.update(fit_axis(row_items, target_width, ...))
```

`wrap_rows` (`generator/reflow.py:206`) itself currently peels/checks-fit against
*elements*. Both must move to operate on **columns**:

1. Before calling `wrap_rows`, replace each `detect_rows` row (a flat element-id list)
   with its column grouping: `columns = detect_columns(elements, row)`. A column's own
   `left`/`width` for fit purposes is `(min(left) across members, max(left+width) -
   min(left) across members)` — i.e. the column's own bounding box, matching how
   `_row_fits` already computes a row's bounding box today (`max(rights) - min(lefts)`),
   just scoped to one column's members instead of a whole row.
2. `wrap_rows` peels/keeps **columns** (not elements) — its existing peel-from-the-
   trailing-end logic is unchanged in shape, just operating on a list of columns
   instead of a list of elements; a peeled or kept "row" in its return value is now a
   list of *columns*, each itself a list of element ids.
3. `_fit_group`'s X-loop builds `row_items` as one `(column_key, left, width)` tuple per
   column (not per element) and calls `fit_axis` on those, exactly as it calls it on
   elements today (including the existing fragment/`center=True` vs.
   untouched/`source_dim=` branch, unchanged — a fragment COLUMN is always centered,
   an untouched column auto-detects, precisely mirroring today's per-element rule).
4. After `fit_axis` returns each column's `{pos, size, scale}`, every MEMBER of that
   column gets `left = pos` (the column's shared X position) and `width =
   max(1, int(member's own original width * scale))` (each member scales by the
   column's own scale factor, applied to its OWN width — handles both the common case
   here, where every member already shares the same width, and a future column whose
   members have different original widths, without forcing them to a shared width).

### Y-axis: unchanged

`stack_rows` already computes each element's `top`/`height` purely from that element's
own source `top` offset within the row (`(e["top"] - own_min_top[i]) * row_scale`,
`generator/reflow.py:251`) and the ROW's own natural height/anchor — none of that reads
`left`/`width` or cares about column membership. Column grouping only changes what
`row_items` `_fit_group` builds for the X loop; `stack_rows` is called with the same
flat row-of-element-ids list it already receives today (`row_lists = [row for row, _ in
wrapped_rows]` — after this change, still the flat per-row element list, columns are
purely an X-axis fitting-time construct, never persisted into the row/wrap-rows
representation `stack_rows` consumes).

## Why this still can't introduce new overlaps

Extends the existing proof (`docs/superpowers/specs/2026-09-08-...` "Why this still
can't introduce new overlaps") one level: `fit_axis`'s own non-overlap guarantee, now
applied to columns instead of elements, means no two DIFFERENT columns' fitted X-ranges
overlap.

WITHIN a column, members share the same final X position by construction — safe
precisely because `detect_columns` only ever puts two elements in the same column when
their SOURCE X-ranges already overlap. If those same two elements also had overlapping
source Y-ranges, they would already be overlapping in the untouched source file, before
this algorithm (or any reflow) ever runs — a pre-existing data condition this change
doesn't create, and one every other part of this reflow subsystem already assumes away
(e.g. `check_overlaps`'s whole purpose in `pin_existing` mode is to flag NEW overlaps
introduced by reflow against a baseline that's assumed clean going in). So for any
well-formed source: two same-column members are guaranteed Y-disjoint (or the source
was already broken), which is exactly what makes sharing an X position safe.

## Components (new/changed code)

- **`generator/reflow.py::detect_columns`** (new) — the X-axis transpose of
  `detect_rows`.
- **`generator/reflow.py::wrap_rows`** (changed) — operates on columns instead of
  elements; return type becomes `list[tuple[list[list[str]], bool]]` (a "row" is now a
  list of columns, each a list of element ids) instead of `list[tuple[list[str],
  bool]]`. Its existing "a single-element row is always left as-is, wrapping can't
  help one element" shortcut becomes "a single-COLUMN row" — same reasoning, one level
  up (a row that's already down to one column, however many elements that column
  itself contains, can't be split further by this tier; an over-wide single column
  falls through to `fit_axis`'s own compact/scale tiers, per Scope above).
- **`generator/reflow.py::_fit_group`** (changed) — builds `detect_columns` groupings
  per row before calling `wrap_rows`; X-loop iterates columns, applying each column's
  fitted position/scale to all its members; `row_lists` fed to `stack_rows` flattens
  back to plain element-id rows (unchanged shape for `stack_rows`).
- **`generator/reflow.py::_row_fits`** (changed or superseded) — needs a column-aware
  equivalent (bounding box over a list-of-columns' members) since `wrap_rows` now
  checks fit for a *row of columns*, not a row of elements; the bounding-box math
  itself (`max(rights) - min(lefts)`) is unchanged, just computed over every member of
  every column in the candidate grouping rather than every element directly.

## Testing

- `detect_columns` unit tests: the reported 5-element shape (two same-left pairs +
  one disjoint element) groups into 3 columns exactly as traced above; a row with no
  overlapping `left` ranges produces one column per element (degenerate case); a row
  where 3+ elements share overlapping ranges clusters into one column (transitive
  closure, matching `detect_rows`' own transitive behavior).
- `wrap_rows` (updated) unit tests: peeling now moves whole columns, never splits one
  column's members across the peel boundary — a column-shaped version of the existing
  peel test.
- `_fit_group`/`reflow_file` end-to-end: a synthetic page replaying the exact reported
  shape (two same-left-position button pairs flanking a wide/tall element, reflowed
  into a resolution too narrow for the flat row but wide enough for column-aware
  wrapping to avoid it) — confirms both pair members always end up at the same final
  `left`, both travel together (or both stay) under wrapping, and the D-pad/pairs no
  longer need a wrapped-row-below at all where column-awareness makes the original row
  fit. Re-verify against the real `ReflowTest.cuig` at TSW-570 afterward, the actual
  case that motivated this spec.
