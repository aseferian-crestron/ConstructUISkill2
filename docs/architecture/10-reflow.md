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

**CORRECTED same-day (2026-09-09, task review):** the `max(own min(top), previous
anchor + previous height + min_gap)` formula written above is itself wrong -- it
unconditionally forces EVERY inter-row gap up to at least `min_gap` (4px), even for
ordinary (non-wrap-split) rows that never needed it. `detect_rows` only guarantees a
*non-negative* inter-row gap, not a `>=4px` one, so two rows separated by, say, 2px in
the source were getting silently pushed to 4px+ apart -- contradicting this codebase's
own `fit_axis` Tier 1 principle (rigid translate preserves original gaps exactly, even
below `min_gap`; the floor only applies where compaction actually happens). Verified
repro: 3 rows flush-stacked at `top=0/50/100`, `target_height=150` (their exact natural
span) -- the buggy formula drifted anchors to `[0, 54, 108]`, pushing the span to 158px
and forcing an unnecessary Tier 3 scale-down on a layout that needed none. Fixed by
preserving each row's own original gap when it's non-negative, clamping to `min_gap`
only for the genuinely degenerate case (a tied or negative gap -- the wrap-split
sibling scenario this pre-stacking exists for): `anchors[i-1] + natural_height[i-1] +
(original_gap if original_gap >= 0 else min_gap)`. Both the design spec
(`docs/superpowers/specs/2026-09-08-multi-resolution-reflow-design.md`, Y axis section)
and the plan (`docs/superpowers/plans/2026-09-09-multi-resolution-reflow.md`, Task 6)
were corrected first; `generator/reflow.py::stack_rows` and its test now match. Two
regression tests guard this (tight 2px gap, and flush 0px gap) in
`generator/_test_output/reflow_task6_stack_rows_test.py`.

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

## Algorithm and integration summary

Full design: `docs/superpowers/specs/2026-09-08-multi-resolution-reflow-design.md`.
Implementation: `generator/reflow.py` (fit_axis, detect_rows, wrap_rows, stack_rows,
find_new_elements, check_overlaps, pick_primary, choose_source_resolution, reflow_file,
ReflowResult) plus new CSS parsing/building helpers in `generator/layout.py`
(find_media_block_span, find_media_block, parse_position_rules, build_reflow_block).
Wired into `generator/project.py::add_resolutions_to_project`, which now also returns
the aggregated list of any reflow warnings (previously returned None).

X-axis fitting runs per row (move -> wrap -> compact -> scale); Y-axis fitting stacks
the resulting row list (move -> compact -> scale), with the pre-stacked-anchor fix in
`stack_rows` (see the Task 6 section above) so wrap-created sibling rows never tie.

Confirmed via `generator/_test_output/reflow_task1..10_*.py` (all 15 smoke/task test
files pass, including Task 9's Case G/H, added by the 2026-09-09 final whole-branch
review, guarding against the real generator's one-`@media`-block-per-element CSS
shape) and by re-running
`generator/_test_output/reflow_manual_verification_setup.py` against
`C:\Solutions\ClaudeGenTest\GenTestProject`. Reading `ButtonVariants.cuig`'s new
640x360 `@media` block directly (`layout.parse_all_position_rules`) confirms the fix:
it now contains all 3 real elements (`ibtnicon`, `ibtnimage`, `ibtncheck`), each on-
canvas and non-overlapping, in exactly one consolidated block -- before this fix, the
single-match `find_media_block` this project used would have only ever found
`ibtnicon` (the first of the three per-element source blocks), silently dropping the
other two buttons with zero warnings. **Visual confirmation in Construct itself is
still pending the user opening the project** -- this check proves the on-disk CSS is
now correct, not that anyone has looked at it rendered.

**Not yet wired up:** Trigger 2 (the skill asking the user which mode to use when new
elements are added to an already-multi-resolution page) is a conversational/process
step at the skill layer per the spec's Integration section, not new code in
`generator/` -- `reflow_file`'s `mode` parameter is what a future skill-layer call would
choose between; this plan only builds and proves the underlying mechanism.

### Bug found wiring Task 10: catalog resolution width/height are strings, not ints

Task 10's own end-to-end test (using real catalog data via
`devices.py::to_project_resolution`, not the hand-built plain-int resolution dicts every
earlier task's unit tests used) immediately crashed `add_resolutions_to_project` with
`TypeError: can only concatenate str (not "int") to str` inside
`layout.orientation_media_query`. Root cause: a real `.cuip`'s `{DeviceResolutionSource}`
genuinely stores `width`/`height` as strings with a `px` suffix (confirmed against
`C:\Solutions\ClaudeSamples\Components\Components.cuip`: `"width": "1280px"`, not a bare
number) -- `to_project_resolution` correctly preserves that real-file shape, but
`reflow.py`/`layout.py` do plain arithmetic on `resolution["width"]`/`["height"]`
(`width + 1`, `pick_primary`'s `max(..., key=lambda r: r["width"])`), which only ever
worked in prior tasks' tests because their synthetic resolution dicts used plain ints
throughout, never exercising the real catalog's string shape.

Fixed at the `add_resolutions_to_project` wiring boundary (not in `devices.py`, which
must keep producing the confirmed real-file string shape, and not in `reflow.py`/
`layout.py`, whose own unit tests already pass against plain ints): new
`project.py::_numeric_dim`/`_numeric_resolution` coerce a resolution's width/height to
`int` (stripping a trailing `px` string suffix when present) for numeric copies fed into
`reflow.choose_source_resolution`/`reflow.reflow_file` only -- the dict actually appended
to `device_resolution_source` and written to disk is untouched, so the `.cuip` on disk
still gets the real, confirmed `"Npx"` string form. The Task 10 integration test's own
Scenario 2 (orientation-bootstrap, using the real TST-1080 portrait catalog entry
unmodified) needed the identical coercion applied locally, purely for that test's own
query-building/comparison arithmetic.
