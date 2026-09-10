# Reflow: preserve centering — design spec

Amends `docs/superpowers/specs/2026-09-08-multi-resolution-reflow-design.md` (the
move → wrap → compact → scale algorithm, `generator/reflow.py`). That spec's `fit_axis`,
`wrap_rows`, and `stack_rows` are unchanged in their existing tiers; this adds one new
behavior layered on top of their output.

## Problem

Found 2026-09-10 by the user, live-testing multi-resolution reflow in Construct: adding a
TST-1080 Portrait resolution to a real page (`ReflowTest.cuig`, hand-authored in
Construct, not by this generator) reflowed a button row that was centered in the 1280px
landscape source (left margin 265px, right margin 266px) into a portrait row flush
against the target canvas's right edge (left margin 52px, right margin 0px). The Y axis
has the identical problem: the row stack was left pinned near the top of the 1280px-tall
portrait canvas instead of being vertically centered, with ~600px of empty space below.

Root cause: none of `fit_axis`'s three tiers ever center a result. Tier 1 (move) only
translates a group that overflows an edge — one that already fits untouched is left at
its *original absolute position*, which is meaningless once the canvas width changed.
Tiers 2/3 (compact/scale) both pack from a fixed left/top anchor (position 0 after
translating the leading edge there), leaving all freed-up space on the trailing side.
`stack_rows` reuses `fit_axis` for the Y axis (rows as pseudo-items), so it inherits the
same gap.

## Scope

Only affects the *placement* of a fitted row (X) or the fitted row-stack (Y) within its
target dimension — never their internal relative layout, sizes, or the overlap-safety
argument (a uniform shift of an already-non-overlapping group can't introduce a new
overlap, the same property Tier 1's existing translate already relies on).

Out of scope: coordinating centering decisions across rows — each row (X) makes its own
independent centered/not-centered call and centers within its own leftover space; there's
no attempt to align multiple rows' centers with each other beyond what naturally falls
out of each one individually preserving its source alignment.

## Detection

"Centered" is evaluated against the **source** canvas dimension (`source_dim`) the
absolute item positions were authored against — `source_resolution`'s width for X,
height for Y. One rule, used identically by both axes and both callers (`_fit_group`'s
per-row X calls and `stack_rows`'s single Y call): margins are computed directly from
whatever `items` list is passed into `fit_axis`, no separate "original bounds" tracking:

```
left_margin  = min(item.pos for item in group)
right_margin = source_dim - max(item.pos + item.size for item in group)
centered = abs(left_margin - right_margin) <= max(4, round(0.01 * source_dim))
```

The tolerance (1% of the source dimension, floored at 4px — the same floor `min_gap`
already uses elsewhere in this module, for consistency) absorbs ordinary off-by-a-few-px
authoring noise (e.g. the real 265/266 case) without falsely centering a group that was
genuinely off-center.

For the Y axis, `items` is `stack_rows`'s existing row-pseudo-item list (anchors +
natural heights) — its bounding box matches the true source element group's vertical
extent exactly, *except* in the rare case where `wrap_rows` produced sibling rows with a
tied/negative source gap, where `stack_rows`'s existing pre-stacking step already
substitutes the `min_gap` floor for that one inter-row gap (see its docstring) — the same
already-accepted few-px imprecision, not a new one this feature introduces.

## Algorithm change

### `fit_axis`

New signature: `fit_axis(items, target_dim, min_gap=4, source_dim=None, center=None)`.

- `center=True` / `center=False`: explicit override, skips detection entirely.
- `center=None` (default): auto-detect using `source_dim` (required in this mode — a
  caller passing neither `source_dim` nor an explicit `center` gets today's unchanged
  edge-anchored behavior, so any caller not yet updated for this feature keeps working
  exactly as before).

After whichever tier (1/2/3) computes the fitted span, if centering applies: compute
`leftover = target_dim - fitted_span`, then shift every item's `pos` by
`leftover // 2 - current_min_pos` (one uniform translate, applied last, on top of
whatever tier produced the span — not a fourth tier, a final placement step every tier's
output passes through).

### X axis (`_fit_group`, per row)

`wrap_rows`'s return type changes from `list[list[str]]` to
`list[tuple[list[str], bool]]` — the bool is `is_fragment`: `True` for a row produced by
peeling (both the shrunk remainder and every peeled-off piece), `False` for a row that
passed through untouched (including a naturally single-element row, and a row that was
checked but already fit with no peeling needed).

`_fit_group` then calls, per row:
- untouched row (`is_fragment=False`): `fit_axis(row_items, target_width,
  source_dim=page_width)` — auto-detect against the row's own original margins.
- fragment row (`is_fragment=True`): `fit_axis(row_items, target_width, center=True)` —
  always center, per the approved decision (treat each wrapped line like a fresh
  flex-wrap line; a subset of a once-centered row has no meaningful "was it centered"
  answer of its own).

### Y axis (`stack_rows`)

One detection for the whole row-stack, independent of X-axis wrap fragmentation (a row
being wrap-split on X doesn't change what it contributes to the Y-axis `items` list —
`stack_rows` already builds that list from each row's own source anchor/natural-height,
unchanged by this feature). `stack_rows` calls `fit_axis(row_items, target_height,
source_dim=page_height, center=None)` — auto-detection, using the Detection section's
one rule directly against `row_items`' own bounding box.

### `reflow_file`

Passes `source_resolution["width"]`/`["height"]` down into `_fit_group` (which forwards
to `wrap_rows`'s row-fit calls and `stack_rows`), so both axes have what they need.
`choose_source_resolution`'s existing output already carries these.

## Error handling

No new failure modes: `fit_axis` already validates fit-ability (raises `AxisFitError` on
an over-crowded axis) before this step runs; the centering shift is applied to output
that already fit, and can only ever move the whole group further from an edge it wasn't
touching, never introduce a new one.

## Testing

- `fit_axis` unit tests: a centered source (`source_dim` given, symmetric margins) comes
  back centered in `target_dim`; an off-center source comes back with today's unchanged
  edge-anchored behavior; explicit `center=True`/`center=False` bypass detection in both
  directions; no `source_dim` and no `center` reproduces today's exact behavior
  (regression guard for every existing caller/test).
- `wrap_rows` unit test: confirms fragment tagging — an untouched row is `False`, both
  halves of a split row are `True`.
- `stack_rows` unit test: a vertically-centered source row-stack comes back centered in
  `target_height`.
- End-to-end: a synthetic page replaying `ReflowTest.cuig`'s actual shape (a centered
  multi-button row that needs Tier 2 compaction to fit a narrower target) confirms the
  reflowed row is centered, not edge-anchored — the regression case that motivated this
  spec.
