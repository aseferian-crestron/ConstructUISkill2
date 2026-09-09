# Multi-resolution reflow

Source-grounded confirmations for `docs/superpowers/specs/2026-09-08-multi-resolution-reflow-design.md`.

## Portrait media-query formula (previously unconfirmed project-wide)

Confirmed by reading `C:\Git\CCIDE\Crestron.IDE\Projects\UiEditor\PageDesigner\PageDesigner.Server\JS\src\pd-utils\src\breakpoint.ts`'s `createRawQuery(devOrientation, devWidth, devHeight)` -- the real client-side TypeScript source that generates these breakpoints (same file/method family as the already-confirmed landscape formula).
Cross-checked against two real portrait sample files elsewhere in the CCIDE repo
(`CrestronConstruct_RIDE\Solutions\MySolution\SolutionCCIDE5225\Bug_CCIDE_5225_Widget2.cuiw` and `...Widget5.cuiw`, both a 1024x1322 portrait resolution) -- source and samples agree exactly:

```
(orientation: portrait) and (max-height: {H+1}px) and (max-width: {W+1}px), (orientation: portrait) and (max-height: {H-1}px)
```

Same `+-1px` shape as the already-confirmed landscape formula, just with height leading
(and being the sole clause in the second alternative) instead of width -- `createRawQuery` branches on orientation only to decide which dimension leads, not on any other logic.
`generator/layout.py::orientation_media_query` implements both branches;
`landscape_media_query` is now a thin wrapper for backward compatibility.

## Row-wrap redesign (2026-09-09) -- tied-anchor gap found and fixed during planning

The design was revised (2026-09-09) to add an X-axis wrap tier: a row of elements that
doesn't fit a target width via translate alone splits (trailing elements peel onto a
new row below) instead of only ever compacting/scaling in place. While turning this
into concrete code, a real gap surfaced: two rows produced by splitting the SAME
original row share the exact same source `top` (splitting doesn't move anything
vertically by itself), so using each row's raw `min(top)` as its Y-stacking anchor
would tie sibling rows at the same position and overlap them in the output.

Fixed in `stack_rows` with a pre-stacking pass: row i's anchor is `max(its own
min(top), row i-1's anchor + row i-1's natural height + 4px)`. For rows that already
had distinct source Y-positions (the ordinary case, no wrap split involved), this is a
no-op -- `detect_rows` already guarantees strictly increasing, non-overlapping natural
positions, so the `max` always resolves to the row's own anchor. It only changes
anything for wrap-created siblings, placing a split-off row naturally just below the
row it split from. See `docs/superpowers/specs/2026-09-08-multi-resolution-reflow-design.md`'s
Y axis section and Task 6 of `docs/superpowers/plans/2026-09-09-multi-resolution-reflow.md`.

### Second bug found by this task's own TDD cycle: per-element height must floor (int()), not round()

Separately from the tied-anchor gap above, writing this task's Tier-3 (scale) test
caught a second, unrelated rounding bug in the task's own draft implementation before
it shipped: per-element height was computed with `round(e["height"] * scale)`, which
can silently diverge from the row's own fitted size (`fit_axis`'s row-item `size`,
itself computed with `int()` truncation -- see `fit_axis`'s Tier 3 comment on why
`int()` and never `round()`). Concretely: whenever a row has one element that spans
its exact natural extent (its own `top` equals the row's `min(top)` and its own
`top + height` equals the row's `max(top + height)` -- always true for a
single-element row, and true for the tallest element in a multi-element row), that
element's own `height * scale` is *the same expression* as the row's own fitted size
by construction, and `round()` vs `int()` diverge whenever the fractional part is
`>= 0.5` (e.g. a 100px element scaled by `~0.2556`: `round()` gives 26px but the row
itself floors to 25px, a silent 1px mismatch/overshoot). Fixed by using `int()`
truncation for per-element height throughout `stack_rows`, matching `fit_axis`'s own
Tier 3 convention exactly.
