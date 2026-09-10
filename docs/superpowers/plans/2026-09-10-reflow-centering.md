# Reflow: Preserve Centering — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When a row (X axis) or the whole row-stack (Y axis) was centered in its source
canvas, reflow should preserve that centering in the target canvas instead of leaving it
pinned to its original absolute position or packed against one edge.

**Architecture:** Add an optional final "recenter" step to `fit_axis` (the single shared
per-axis fitter both the X-axis per-row loop and the Y-axis row-stacking already funnel
through) — a uniform post-shift of whichever tier's output, safe by the same argument
Tier 1's existing translate already relies on. Detection compares the group's original
margins against the *source* canvas dimension, with an explicit override for wrap-split
row fragments (always centered, since a subset of a once-centered row has no meaningful
"was it centered" answer of its own).

**Tech Stack:** Python 3, no new dependencies. Existing test convention: standalone
scripts under `generator/_test_output/`, run directly with `python <file>.py`, asserting
and printing rather than a test framework.

**Spec:** `docs/superpowers/specs/2026-09-10-reflow-centering-design.md`

## Global Constraints

- Backward compatibility: a caller passing neither `source_dim` nor `center` to
  `fit_axis` must get byte-identical output to today's behavior (existing tests in
  `reflow_task3_fit_axis_test.py`, `reflow_task9_reflow_file_test.py`,
  `reflow_task10_integration_test.py`, `phase5_smoke_test.py`, and
  `reflow_partial_device_block_regression_test.py` must all keep passing unmodified,
  except `reflow_task5_wrap_rows_test.py`, whose assertions must be updated for
  `wrap_rows`'s new return shape — see Task 2).
- Tolerance: `max(4, round(0.01 * source_dim))` — 1% of the source dimension, floored at
  4px (matches `min_gap`'s existing floor elsewhere in this module).
- A uniform shift must never move any item outside `[0, target_dim]` — `_center_result`
  relies on `leftover = target_dim - fitted_span` always being `>= 0` (guaranteed by
  every tier already only ever producing a span `<= target_dim`, or raising
  `AxisFitError` beforehand).

---

### Task 1: `fit_axis` gains `source_dim`/`center` and a final recenter step

**Files:**
- Modify: `generator/reflow.py:18-132` (the `AxisFitError` class through the end of
  `fit_axis`)
- Test: `generator/_test_output/reflow_centering_task1_fit_axis_test.py` (new)

**Interfaces:**
- Produces: `fit_axis(items: list[tuple[str, int, int]], target_dim: int, min_gap: int = 4, source_dim: int | None = None, center: bool | None = None) -> dict[str, dict]` — same return shape as today (`{item_id: {"pos": int, "size": int, "scale": float}}`).
- Produces: `_center_result(result: dict[str, dict], target_dim: int) -> dict[str, dict]` — internal helper, one uniform shift.

- [ ] **Step 1: Write the failing tests**

Create `generator/_test_output/reflow_centering_task1_fit_axis_test.py`:

```python
"""Task 1: fit_axis gains source_dim/center -- a centered source group comes back
centered in target_dim instead of left where it was / packed against one edge."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reflow import fit_axis  # noqa: E402

# --- Centered source, Tier 1 path (span <= target_dim): recentered -------------------
# Two 100px items at [400,500) and [500,600) in a 1000px source -- left_margin=400,
# right_margin=1000-600=400, exactly centered. Moving to target_dim=300: span=200<=300
# (Tier 1), but the group's OWN position (400-600) overflows target_dim's right edge, so
# today's behavior clamps it flush right at [100,300) -- NOT centered in the new 300px
# canvas. With centering: expected flush-centered result is [50,150) and [150,250).
items = [("a", 400, 100), ("b", 500, 100)]
result = fit_axis(items, target_dim=300, source_dim=1000)
assert result["a"] == {"pos": 50, "size": 100, "scale": 1.0}, result["a"]
assert result["b"] == {"pos": 150, "size": 100, "scale": 1.0}, result["b"]
print("Tier 1, centered source -> centered result: OK")

# --- Same items, NO source_dim/center given: today's exact edge-anchored behavior ----
# Backward-compatibility regression guard -- must match calling fit_axis before this task.
legacy = fit_axis(items, target_dim=300)
assert legacy["a"] == {"pos": 100, "size": 100, "scale": 1.0}, legacy["a"]
assert legacy["b"] == {"pos": 200, "size": 100, "scale": 1.0}, legacy["b"]
print("No source_dim/center -> unchanged legacy edge-anchored behavior: OK")

# --- Off-center source: auto-detection correctly does NOT center ---------------------
# left_margin=400, right_margin=1000-600=400 was centered above; shift b to break
# symmetry -- items at [400,500) and [700,800): left_margin=400, right_margin=200.
off_center_items = [("a", 400, 100), ("b", 700, 100)]
result_off = fit_axis(off_center_items, target_dim=500, source_dim=1000)
legacy_off = fit_axis(off_center_items, target_dim=500)
assert result_off == legacy_off, f"off-center source must NOT be recentered, got {result_off} vs legacy {legacy_off}"
print("Off-center source -> unchanged (not centered): OK")

# --- Explicit center=True forces centering even with no source_dim -------------------
forced = fit_axis(off_center_items, target_dim=500, center=True)
assert forced != legacy_off, "center=True must force centering even for an off-center source"
min_pos = min(v["pos"] for v in forced.values())
max_pos = max(v["pos"] + v["size"] for v in forced.values())
leftover = 500 - (max_pos - min_pos)
assert min_pos == leftover // 2, f"expected centered leftover split, got min_pos={min_pos}, leftover={leftover}"
print("Explicit center=True forces centering: OK")

# --- Explicit center=False suppresses centering even with a centered source_dim ------
suppressed = fit_axis(items, target_dim=300, source_dim=1000, center=False)
assert suppressed == legacy, "center=False must suppress centering even for a centered source"
print("Explicit center=False suppresses centering: OK")

print("\nTASK 1: fit_axis centering -- ALL CHECKS PASSED")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd generator/_test_output && python reflow_centering_task1_fit_axis_test.py`
Expected: `TypeError: fit_axis() got an unexpected keyword argument 'source_dim'`

- [ ] **Step 3: Implement `source_dim`/`center` and the recenter step**

Replace `generator/reflow.py` lines 18-132 (the `AxisFitError` class through the end of
`fit_axis`) with:

```python
class AxisFitError(Exception):
    """Raised when target_dim can't fit even the mandatory min_gap floor gaps for this
    many items -- caller (reflow_file's _fit_group) catches this per-axis and reports a
    warning rather than crashing (see the spec's Error handling section)."""


def _center_result(result: dict[str, dict], target_dim: int) -> dict[str, dict]:
    """One uniform shift so `result`'s bounding box sits centered in `target_dim`
    instead of wherever its tier left it -- safe for the same reason fit_axis's own
    Tier 1 translate is (a uniform shift of an already-non-overlapping group can't
    introduce a new overlap). See docs/superpowers/specs/2026-09-10-reflow-centering-
    design.md."""
    min_pos = min(v["pos"] for v in result.values())
    max_pos = max(v["pos"] + v["size"] for v in result.values())
    leftover = target_dim - (max_pos - min_pos)
    shift = leftover // 2 - min_pos
    return {k: {**v, "pos": v["pos"] + shift} for k, v in result.items()}


def fit_axis(
    items: list[tuple[str, int, int]], target_dim: int, min_gap: int = 4,
    source_dim: int | None = None, center: bool | None = None,
) -> dict[str, dict]:
    """3-tier fit for one axis of one group of items being fit together. `items` is
    [(item_id, pos, size)] in any order -- either elements (X axis, within one row) or
    row pseudo-items (Y axis, the row list; see stack_rows). Returns {item_id: {"pos":
    int, "size": int, "scale": float}} -- scale is 1.0 unless tier 3 (scale-down)
    applied.

    Tier 1 (move): if the group's bounding-box span already fits target_dim, shift
    everyone by one constant offset -- relative gaps are preserved exactly.
    Tier 2 (compact): otherwise, shrink internal gaps (order-preserving) toward a
    min_gap floor, linearly interpolated by how much reduction is still needed.
    Tier 3 (scale): if gaps are already at the floor and it's still not enough, scale
    every item's size by one shared factor (reserving room for the mandatory min_gap
    gaps first) and repack at exactly min_gap.

    See the spec's "Why this still can't introduce new overlaps" for the proof this
    relies on: order is never changed, and no gap is ever allowed to go negative.

    `source_dim`/`center` -- ADDED 2026-09-10 (see docs/superpowers/specs/
    2026-09-10-reflow-centering-design.md): after whichever tier above computes the
    fitted span, if centering applies, `_center_result` shifts the WHOLE result so it's
    centered in `target_dim` instead of left/top-anchored. `center=True`/`False` skip
    auto-detection entirely; `center=None` (default) auto-detects from `source_dim`:
    margins of the group's ORIGINAL absolute positions (the `items` passed in, before
    any tier runs) against `source_dim`, centered if
    `abs(left_margin - right_margin) <= max(4, round(0.01 * source_dim))`. A caller
    passing neither `source_dim` nor `center` gets `center=False` -- today's exact
    behavior, unchanged.
    """
    if not items:
        return {}
    n = len(items)
    sorted_items = sorted(items, key=lambda t: t[1])
    ids = [i for i, _, _ in sorted_items]
    positions = [p for _, p, _ in sorted_items]
    sizes = [s for _, _, s in sorted_items]

    if center is None and source_dim is not None:
        left_margin = min(positions)
        right_margin = source_dim - max(p + s for p, s in zip(positions, sizes))
        center = abs(left_margin - right_margin) <= max(4, round(0.01 * source_dim))
    else:
        center = bool(center)

    min_pos = min(positions)
    max_pos = max(p + s for p, s in zip(positions, sizes))
    span = max_pos - min_pos

    # --- Tier 1: rigid group translate -------------------------------------------
    if span <= target_dim:
        if max_pos > target_dim:
            offset = target_dim - max_pos
        elif min_pos < 0:
            offset = -min_pos
        else:
            offset = 0
        result = {
            item_id: {"pos": pos + offset, "size": size, "scale": 1.0}
            for item_id, pos, size in zip(ids, positions, sizes)
        }
        return _center_result(result, target_dim) if center else result

    # Translate so the leading edge is 0 -- tiers 2/3 cascade positions from there.
    positions = [p - min_pos for p in positions]
    total_size = sum(sizes)
    total_gap = span - total_size
    needed_reduction = span - target_dim

    # --- Tier 2: order-preserving whitespace compaction ---------------------------
    # CORRECTED 2026-09-09, twice (task review caught two real bugs; the first fix
    # introduced a smaller residual of the same symptom, caught by the fix's own
    # scoped re-review). Bug 1: the original `max_possible_reduction = total_gap -
    # (n-1)*min_gap` sums ALL gaps uniformly, including any gap already below min_gap
    # (or negative, i.e. overlapping input) -- those gaps must EXPAND to reach the
    # floor, not contribute reduction, so the old formula could credit negative
    # "slack" and under-reduce the span, silently returning a layout wider than
    # target_dim. Fixed by splitting each gap into reducible slack (above the floor)
    # vs. mandatory deficit (below the floor) and budgeting needed_reduction against
    # slack alone, plus deficit -- this part of the fix is unchanged from the first
    # correction. Bug 2 (found in the first fix's own re-review): rounding each
    # position INCREMENTALLY (off the previous ROUNDED position) still let up to
    # ~0.5px of rounding error compound across many gaps, occasionally pushing the
    # final span a few px over target_dim even though every individual gap still met
    # the 4px floor. Fixed the same way Tier 3 fixes its own analogous rounding
    # problem: floor (never round) each gap to an integer before accumulating
    # positions. A float gap is already >= min_gap by construction (the `max(min_gap,
    # ...)` above), and min_gap is an integer, so floor(gap) >= min_gap always --
    # flooring can only ever shrink the accumulated span relative to the exact
    # (target_dim-fitting) float math, never grow it, so no compounding is possible.
    if n > 1:
        gaps = [positions[i + 1] - (positions[i] + sizes[i]) for i in range(n - 1)]
        slack = sum(max(0, g - min_gap) for g in gaps)      # reducible whitespace only
        deficit = sum(max(0, min_gap - g) for g in gaps)    # sub-floor gaps that must expand
        need = needed_reduction + deficit
        if slack > 0 and need <= slack:
            shrink_ratio = need / slack
            new_gaps = [max(min_gap, g - shrink_ratio * max(0, g - min_gap)) for g in gaps]
            int_gaps = [max(min_gap, int(g)) for g in new_gaps]  # floor, never round
            new_positions = [0]
            for i, size in enumerate(sizes[:-1]):
                new_positions.append(new_positions[-1] + size + int_gaps[i])
            result = {
                item_id: {"pos": pos, "size": size, "scale": 1.0}
                for item_id, pos, size in zip(ids, new_positions, sizes)
            }
            return _center_result(result, target_dim) if center else result

    # --- Tier 3: uniform scale-down, last resort, repacked at exactly min_gap -----
    available_for_sizes = target_dim - (n - 1) * min_gap
    if available_for_sizes <= 0:
        raise AxisFitError(
            f"target_dim {target_dim} can't fit even the mandatory {min_gap}px floor "
            f"gaps for {n} items"
        )
    scale = available_for_sizes / total_size
    # CORRECTED 2026-09-09 (task review): round() could push the packed total over
    # target_dim (each item's round() can add up to 0.5px, compounding across many
    # items). int() truncates toward zero, equivalent to floor for these non-negative
    # values, and never overshoots -- the max(1, ...) floor is unchanged (never
    # collapse to 0px; the only remaining, deliberate source of overflow is that 1px
    # floor itself on a pathologically over-crowded axis).
    new_sizes = [max(1, int(size * scale)) for size in sizes]
    new_positions = [0]
    for size in new_sizes[:-1]:
        new_positions.append(new_positions[-1] + size + min_gap)
    result = {
        item_id: {"pos": pos, "size": size, "scale": scale}
        for item_id, pos, size in zip(ids, new_positions, new_sizes)
    }
    return _center_result(result, target_dim) if center else result
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd generator/_test_output && python reflow_centering_task1_fit_axis_test.py`
Expected: all 5 `print(...)` lines, ending `TASK 1: fit_axis centering -- ALL CHECKS PASSED`

- [ ] **Step 5: Run the existing fit_axis test to confirm no regression**

Run: `cd generator/_test_output && python reflow_task3_fit_axis_test.py`
Expected: `TASK 3: fit_axis -- ALL CHECKS PASSED` (unchanged from before this task)

- [ ] **Step 6: Commit**

```bash
git add generator/reflow.py generator/_test_output/reflow_centering_task1_fit_axis_test.py
git commit -m "reflow: fit_axis gains source_dim/center, recenters a fitted group when the source was centered"
```

---

### Task 2: `wrap_rows` tags each output row as a fragment or untouched

**Files:**
- Modify: `generator/reflow.py:168-199` (`wrap_rows`)
- Modify: `generator/_test_output/reflow_task5_wrap_rows_test.py` (update assertions for
  the new return shape)

**Interfaces:**
- Consumes: nothing new.
- Produces: `wrap_rows(rows: list[list[str]], elements: dict[str, dict], target_width: int) -> list[tuple[list[str], bool]]` — return type changed from `list[list[str]]`. The bool is `is_fragment`: `True` for a row produced by peeling (both the shrunk remainder and every peeled-off piece), `False` for a row that passed through untouched (including a naturally single-element row, and a row that was checked but already fit with no peeling needed).

- [ ] **Step 1: Update the existing test's assertions first (they'll fail against the current code — that's the point)**

Replace the full contents of `generator/_test_output/reflow_task5_wrap_rows_test.py` with:

```python
"""Task 5 (original reflow plan) + Task 2 (2026-09-10 centering plan): wrap_rows --
splits a row that doesn't fit target_width by peeling trailing elements onto a new row,
recursively, and tags each output row as a fragment (True, came from a split) or
untouched (False) -- see docs/superpowers/specs/2026-09-10-reflow-centering-design.md's
X axis section: a fragment row is always centered later, an untouched row is only
centered if its own original margins were symmetric."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reflow import wrap_rows  # noqa: E402

def make(*specs):
    # specs: (id, left, width)
    return {eid: {"left": left, "width": width} for eid, left, width in specs}

# --- A row that already fits: no split, untouched (False) ------------------------
elements = make(("a", 0, 100), ("b", 110, 100), ("c", 220, 100), ("d", 330, 100))
assert wrap_rows([["a", "b", "c", "d"]], elements, target_width=500) == [(["a", "b", "c", "d"], False)]
print("already fits, no split, untouched (False): OK")

# --- A row that needs exactly one split: both halves are fragments (True) --------
# span = (330+100) - 0 = 430 > 250; peeling c,d together (a,b alone span 210 <= 250 fits).
result = wrap_rows([["a", "b", "c", "d"]], elements, target_width=250)
assert result == [(["a", "b"], True), (["c", "d"], True)], f"expected one split into two fragment rows, got {result}"
print("exactly one split, both halves fragments (True): OK")

# --- A row dense enough to need multiple splits: every resulting row is a fragment -
dense = make(*[(f"e{i}", i * 110, 100) for i in range(6)])  # e0..e5, 100px wide, 10px gaps
result = wrap_rows([[f"e{i}" for i in range(6)]], dense, target_width=150)
assert result == [([f"e{i}"], True) for i in range(6)], f"expected 6 singleton fragment rows, got {result}"
print("multiple splits down to singletons, all fragments (True): OK")

# --- A single element wider than target_width on its own: left as a 1-element row,
#     never loops, untouched (False) -- it falls through to fit_axis's own
#     compact/scale tiers later.
wide = make(("w", 0, 300))
assert wrap_rows([["w"]], wide, target_width=250) == [(["w"], False)]
print("single too-wide element left unsplit, untouched (False): OK")

# --- Multiple independent rows: only the offending row splits (fragments, True),
#     the other row is untouched (False).
mixed = make(("a", 0, 100), ("b", 110, 100), ("c", 220, 100), ("d", 330, 100), ("z", 0, 50))
result = wrap_rows([["a", "b", "c", "d"], ["z"]], mixed, target_width=250)
assert result == [(["a", "b"], True), (["c", "d"], True), (["z"], False)], f"expected only the first row to split, got {result}"
print("only the offending row splits (True), the other stays untouched (False): OK")

print("\nTASK 5/2: wrap_rows fragment tagging -- ALL CHECKS PASSED")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd generator/_test_output && python reflow_task5_wrap_rows_test.py`
Expected: `AssertionError` on the first `assert` (current code returns
`[["a", "b", "c", "d"]]`, not `[(["a", "b", "c", "d"], False)]`)

- [ ] **Step 3: Implement fragment tagging**

Replace `generator/reflow.py` lines 168-199 (`wrap_rows`) with:

```python
def wrap_rows(rows: list[list[str]], elements: dict[str, dict], target_width: int) -> list[tuple[list[str], bool]]:
    """X-axis wrap tier, run between fit_axis's Tier 1 and Tier 2 (see spec). For each
    row (in order), check the same bounding-box test as fit_axis's own Tier 1 test,
    scoped to just that row's elements; a row that passes needs nothing further. A row
    that fails and has more than one element peels elements off its trailing
    (right-most, by the left-to-right order detect_rows established) end -- ALL of them
    in one pass -- until what remains passes; the peeled elements become one new row,
    inserted immediately after, which itself gets the same check on a later iteration
    (so a very crowded row can split into more than two). A single-element row is
    always left as-is regardless of whether it fits -- wrapping can't help one element;
    that case falls through to fit_axis's own compact/scale tiers when X positions are
    finalized per row (see the spec's Tiers 3/4 note).

    Returns `[(row, is_fragment), ...]` -- ADDED 2026-09-10 (see docs/superpowers/specs/
    2026-09-10-reflow-centering-design.md): `is_fragment` is True for a row produced by
    peeling (both the shrunk remainder and every peeled-off piece), False for a row that
    passed through untouched. `_fit_group` uses this to decide whether a row's centering
    is auto-detected from its own original margins (untouched) or always applied
    (fragment -- a subset of a once-centered row has no meaningful "was it centered"
    answer of its own)."""
    pending = list(rows)
    pending_is_fragment = [False] * len(rows)
    result: list[tuple[list[str], bool]] = []
    i = 0
    while i < len(pending):
        row = pending[i]
        if len(row) <= 1 or _row_fits(row, elements, target_width):
            result.append((row, pending_is_fragment[i]))
            i += 1
            continue
        remainder = row
        peeled: list[str] = []
        while len(remainder) > 1 and not _row_fits(remainder, elements, target_width):
            peeled.insert(0, remainder[-1])
            remainder = remainder[:-1]
        pending[i] = remainder
        pending_is_fragment[i] = True
        pending.insert(i + 1, peeled)
        pending_is_fragment.insert(i + 1, True)
        # Don't advance i: re-check the shrunk `remainder` (now at pending[i]) next
        # iteration -- it passes immediately since peeling stopped exactly when it
        # started fitting (or dropped to one element).
    return result
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd generator/_test_output && python reflow_task5_wrap_rows_test.py`
Expected: `TASK 5/2: wrap_rows fragment tagging -- ALL CHECKS PASSED`

- [ ] **Step 5: Commit**

```bash
git add generator/reflow.py generator/_test_output/reflow_task5_wrap_rows_test.py
git commit -m "reflow: wrap_rows tags each output row as a fragment (from a split) or untouched"
```

*(Note: `_fit_group` and `stack_rows` still call `wrap_rows`/pass row lists in the old
shape at this point — Task 4 rewires them. `reflow_file`'s end-to-end tests will not run
correctly again until Task 4 is done; that's expected, this is an intentionally
mid-refactor state, not a regression to chase down now.)*

---

### Task 3: `stack_rows` gains `source_height`

**Files:**
- Modify: `generator/reflow.py:202-267` (`stack_rows`)
- Test: `generator/_test_output/reflow_centering_task3_stack_rows_test.py` (new)

**Interfaces:**
- Consumes: `fit_axis(..., source_dim=None, center=None)` from Task 1.
- Produces: `stack_rows(rows: list[list[str]], elements: dict[str, dict], target_height: int, min_gap: int = 4, source_height: int | None = None) -> dict[str, dict]` — same return shape as today; `rows` is still a plain `list[list[str]]` (Y axis doesn't need the fragment flag — see the spec's Y axis section).

- [ ] **Step 1: Write the failing test**

Create `generator/_test_output/reflow_centering_task3_stack_rows_test.py`:

```python
"""Task 3: stack_rows gains source_height -- a vertically-centered source row-stack
comes back centered in target_height instead of pinned to the top."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reflow import stack_rows  # noqa: E402

# Two rows, each one element, 50px tall, at top=400 and top=500 in a 1000px-tall source
# -- top_margin=400, bottom_margin=1000-550=450 -- close enough to call centered
# (tolerance = max(4, round(0.01*1000)) = 10 -- 50px diff would NOT pass; use exactly
# symmetric values instead): top=400 and top=500, each height 50 -> bottom=550,
# top_margin=400, bottom_margin=1000-550=450. Not quite symmetric enough (diff 50 > 10)
# -- adjust to genuinely symmetric: row0 top=400 height=50 (ends 450), row1 top=500
# height=100 (ends 600) -> group top=400, bottom=600, top_margin=400,
# bottom_margin=1000-600=400. Centered (diff 0).
rows = [["a"], ["b"]]
elements = {"a": {"top": 400, "height": 50}, "b": {"top": 500, "height": 100}}
result = stack_rows(rows, elements, target_height=300, source_height=1000)

# Legacy (no source_height): today's exact edge-anchored behavior, for comparison.
legacy = stack_rows(rows, elements, target_height=300)
assert result != legacy, "a centered source row-stack must come back different from the legacy edge-anchored result"

min_top = min(result["a"]["top"], result["b"]["top"])
max_bottom = max(result["a"]["top"] + result["a"]["height"], result["b"]["top"] + result["b"]["height"])
leftover = 300 - (max_bottom - min_top)
assert min_top == leftover // 2, f"expected centered leftover split, got min_top={min_top}, leftover={leftover}"
print("Vertically-centered source row-stack -> centered result: OK")

# --- No source_height: unchanged legacy behavior (backward-compat regression guard) --
assert stack_rows(rows, elements, target_height=300) == legacy
print("No source_height -> unchanged legacy edge-anchored behavior: OK")

print("\nTASK 3: stack_rows centering -- ALL CHECKS PASSED")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd generator/_test_output && python reflow_centering_task3_stack_rows_test.py`
Expected: `TypeError: stack_rows() got an unexpected keyword argument 'source_height'`

- [ ] **Step 3: Implement `source_height`**

In `generator/reflow.py`, change the `stack_rows` signature (line 202) from:

```python
def stack_rows(rows: list[list[str]], elements: dict[str, dict], target_height: int, min_gap: int = 4) -> dict[str, dict]:
```

to:

```python
def stack_rows(rows: list[list[str]], elements: dict[str, dict], target_height: int, min_gap: int = 4, source_height: int | None = None) -> dict[str, dict]:
```

Append to `stack_rows`'s docstring (after the existing final paragraph, before the closing
`"""`):

```
    `source_height` -- ADDED 2026-09-10 (see docs/superpowers/specs/
    2026-09-10-reflow-centering-design.md): forwarded to the internal fit_axis call as
    `source_dim` so a vertically-centered source row-stack comes back centered in
    target_height instead of pinned to the top. One auto-detected decision for the
    whole stack (no fragment concept on this axis -- row-wrap only affects X-axis
    grouping, not what a row contributes to this Y-axis pseudo-item list).
```

Change the `fit_axis` call (currently `row_fit = fit_axis(row_items, target_height, min_gap=min_gap)`) to:

```python
    row_fit = fit_axis(row_items, target_height, min_gap=min_gap, source_dim=source_height)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd generator/_test_output && python reflow_centering_task3_stack_rows_test.py`
Expected: `TASK 3: stack_rows centering -- ALL CHECKS PASSED`

- [ ] **Step 5: Run the existing stack_rows test to confirm no regression**

Run: `cd generator/_test_output && python reflow_task6_stack_rows_test.py`
Expected: `TASK 6: stack_rows -- ALL CHECKS PASSED` (unchanged from before this task)

- [ ] **Step 6: Commit**

```bash
git add generator/reflow.py generator/_test_output/reflow_centering_task3_stack_rows_test.py
git commit -m "reflow: stack_rows gains source_height, recenters a vertically-centered row-stack"
```

---

### Task 4: Wire `_fit_group`/`reflow_file` — fragments always center, untouched rows auto-detect

**Files:**
- Modify: `generator/reflow.py` (`_fit_group` and the `_fit_group(...)` call site inside
  `reflow_file`)
- Test: `generator/_test_output/reflow_centering_task4_end_to_end_test.py` (new)

**Interfaces:**
- Consumes: `wrap_rows(...) -> list[tuple[list[str], bool]]` (Task 2),
  `stack_rows(..., source_height=None)` (Task 3), `fit_axis(..., source_dim=None, center=None)` (Task 1).
- Produces: `_fit_group(elements, target_width, target_height, source_width, source_height, path, query, warnings) -> dict[str, dict] | None` — signature gains `source_width`/`source_height` (inserted after `target_height`, before `path`).

- [ ] **Step 1: Write the failing end-to-end test**

Create `generator/_test_output/reflow_centering_task4_end_to_end_test.py`:

```python
"""Task 4: end-to-end -- replays the real bug (found 2026-09-10 in the user's
ReflowTest.cuig): a button row centered in a 1280px landscape source, reflowed into an
800px portrait target via fit_axis's Tier 1 path (the row already fits, so today's code
never moves it at all -- exactly the shape that produced a flush-right result in
Construct instead of a centered one)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))

from reflow import reflow_file  # noqa: E402
from devices import ORIENTATION_ENUM  # noqa: E402
import layout  # noqa: E402
import compare  # noqa: E402

OUT = Path(__file__).resolve().parent / "ReflowCenteringE2E"
OUT.mkdir(parents=True, exist_ok=True)


def make_file(path: Path, css: str) -> None:
    path.write_text(
        "{FileMetadata}\nSchema = \"1.0.0.0\"\n"
        "\n{Html}\n<div id=\"a\"></div><div id=\"b\"></div><div id=\"c\"></div>\n"
        f"\n{{Css}}\n{css}\n"
        "\n{PageAttributes}\n\n[Attributes]\nName = \"P\"\n",
        encoding="utf-8",
    )


source = {"width": 1280, "height": 800, "orientation": ORIENTATION_ENUM["landscape"]}
target = {"width": 800, "height": 1280, "orientation": ORIENTATION_ENUM["portrait"]}

source_query = layout.orientation_media_query("landscape", 1280, 800)
target_query = layout.orientation_media_query("portrait", 800, 1280)

# 3 buttons, 100px wide, centered in the 1280px-wide source: lefts 450, 590, 730 (gaps
# of 40), spanning 450-830 -- left_margin=450, right_margin=1280-830=450, centered.
css = (
    f"@media {source_query}{{"
    "#a{display: block; left: 450px; top: 20px; position: absolute; width: 100px; height: 50px;}"
    "#b{display: block; left: 590px; top: 20px; position: absolute; width: 100px; height: 50px;}"
    "#c{display: block; left: 730px; top: 20px; position: absolute; width: 100px; height: 50px;}"
    "}"
)
path = OUT / "CenteredRow.cuig"
make_file(path, css)

result = reflow_file(path, target_resolution=target, source_resolution=source, mode="pin_existing")
assert result.warnings == [], f"expected no warnings, got {result.warnings}"
assert compare.round_trip_check(path)

new_css = compare.parse_file(path).sections[2][2]
new_block = layout.find_media_block(new_css, target_query)
assert new_block is not None, "expected a new @media block for the target resolution"
fitted = layout.parse_position_rules(new_block)

assert set(fitted) == {"a", "b", "c"}
# Hand-traced expected result (see the design spec / Task 1's fit_axis-level test for
# the same arithmetic): Tier 1 first clamps the group flush against the target's right
# edge (span 380 <= 800, but original max_pos 830 > 800 -- old behavior would stop
# here, flush right at left=70,210,350). Centering then re-centers within the 800px
# target: leftover = 800 - 380 = 420, shift so the group starts at 420 // 2 = 210.
assert fitted["a"]["left"] == 210, fitted["a"]
assert fitted["b"]["left"] == 350, fitted["b"]
assert fitted["c"]["left"] == 490, fitted["c"]
for eid in ("a", "b", "c"):
    assert fitted[eid]["width"] == 100 and fitted[eid]["height"] == 50, fitted[eid]

# Explicitly prove it's no longer flush against either edge (the exact symptom reported).
min_left = min(fitted[eid]["left"] for eid in fitted)
max_right = max(fitted[eid]["left"] + fitted[eid]["width"] for eid in fitted)
assert min_left > 0, f"must not be flush against the left edge, got min_left={min_left}"
assert max_right < 800, f"must not be flush against the right edge, got max_right={max_right}"
assert min_left == 800 - max_right, f"left and right margins must be equal (centered), got {min_left} vs {800 - max_right}"

print("End-to-end: centered source row reflows into a centered (not edge-anchored) target row: OK")
print("\nTASK 4: end-to-end centering -- ALL CHECKS PASSED")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd generator/_test_output && python reflow_centering_task4_end_to_end_test.py`
Expected: `TypeError: wrap_rows(...) ...` or an assertion failure (`_fit_group` still
unpacks `wrap_rows`'s old plain-list shape and calls `fit_axis`/`stack_rows` without the
new params, so the result is still the old flush-right/flush-top layout, not centered)

- [ ] **Step 3: Wire `_fit_group` and `reflow_file`**

In `generator/reflow.py`, change `_fit_group`'s signature and body (currently):

```python
def _fit_group(
    elements: dict[str, dict], target_width: int, target_height: int,
    path: Path, query: str, warnings: list[str],
) -> dict[str, dict] | None:
    """Fit one group of elements (all of source in full_refit, or just the new ones in
    pin_existing) into target_width x target_height: group into rows (detect_rows),
    let overflowing rows wrap (wrap_rows), fit X positions per row (fit_axis), then
    stack the resulting rows on Y (stack_rows). None if any fit_axis call raises
    AxisFitError -- caller skips this target block entirely for this file, other files
    in the project are unaffected."""
    rows = detect_rows(elements)
    wrapped_rows = wrap_rows(rows, elements, target_width)

    x_fit: dict[str, dict] = {}
    for row in wrapped_rows:
        row_items = [(eid, elements[eid]["left"], elements[eid]["width"]) for eid in row]
        try:
            x_fit.update(fit_axis(row_items, target_width))
        except AxisFitError as e:
            warnings.append(f"{path.name}: X axis for {query} -- {e}")
            return None

    try:
        y_fit = stack_rows(wrapped_rows, elements, target_height)
    except AxisFitError as e:
        warnings.append(f"{path.name}: Y axis for {query} -- {e}")
        return None
```

to:

```python
def _fit_group(
    elements: dict[str, dict], target_width: int, target_height: int,
    source_width: int, source_height: int,
    path: Path, query: str, warnings: list[str],
) -> dict[str, dict] | None:
    """Fit one group of elements (all of source in full_refit, or just the new ones in
    pin_existing) into target_width x target_height: group into rows (detect_rows),
    let overflowing rows wrap (wrap_rows), fit X positions per row (fit_axis), then
    stack the resulting rows on Y (stack_rows). None if any fit_axis call raises
    AxisFitError -- caller skips this target block entirely for this file, other files
    in the project are unaffected.

    `source_width`/`source_height` -- ADDED 2026-09-10 (see docs/superpowers/specs/
    2026-09-10-reflow-centering-design.md): the SOURCE canvas dimensions the elements'
    absolute positions were authored against, needed to detect whether a row/row-stack
    was centered there. An untouched (non-wrap-split) row auto-detects against its own
    original margins; a wrap-split fragment row is always centered (see wrap_rows's
    docstring)."""
    rows = detect_rows(elements)
    wrapped_rows = wrap_rows(rows, elements, target_width)

    x_fit: dict[str, dict] = {}
    for row, is_fragment in wrapped_rows:
        row_items = [(eid, elements[eid]["left"], elements[eid]["width"]) for eid in row]
        try:
            if is_fragment:
                x_fit.update(fit_axis(row_items, target_width, center=True))
            else:
                x_fit.update(fit_axis(row_items, target_width, source_dim=source_width))
        except AxisFitError as e:
            warnings.append(f"{path.name}: X axis for {query} -- {e}")
            return None

    row_lists = [row for row, _ in wrapped_rows]
    try:
        y_fit = stack_rows(row_lists, elements, target_height, source_height=source_height)
    except AxisFitError as e:
        warnings.append(f"{path.name}: Y axis for {query} -- {e}")
        return None
```

(The rest of `_fit_group`'s body — the `fitted: dict[str, dict] = {}` loop and `return
fitted` — is unchanged.)

Then in `reflow_file`, change the `_fit_group` call (currently):

```python
    fitted = _fit_group(to_fit, target_resolution["width"], target_resolution["height"], path, target_query, warnings)
```

to:

```python
    fitted = _fit_group(
        to_fit, target_resolution["width"], target_resolution["height"],
        source_resolution["width"], source_resolution["height"],
        path, target_query, warnings,
    )
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd generator/_test_output && python reflow_centering_task4_end_to_end_test.py`
Expected: `TASK 4: end-to-end centering -- ALL CHECKS PASSED`

- [ ] **Step 5: Commit**

```bash
git add generator/reflow.py generator/_test_output/reflow_centering_task4_end_to_end_test.py
git commit -m "reflow: wire source_width/source_height through _fit_group/reflow_file so centering actually applies"
```

---

### Task 5: Full regression run, re-verify against the real GenTestProject2, update README

**Files:**
- Verify only (no source changes expected): every existing test under
  `generator/_test_output/`
- Verify: `C:\Solutions\ClaudeGenTest\GenTestProject2\ReflowTest.cuig`,
  `ButtonVariants.cuig`, `MyWidget.cuiw` (the real files)
- Modify: `README.md` (Current phase + Log, per this project's standing convention)

**Interfaces:**
- Consumes: everything from Tasks 1-4.
- Produces: nothing new — this task is verification + documentation only.

- [ ] **Step 1: Run every existing generator test and confirm zero regressions**

Run (from `generator/_test_output/`):

```bash
for f in phase2_smoke_test.py phase3_smoke_test.py phase4_smoke_test.py phase5_smoke_test.py reflow_task3_fit_axis_test.py reflow_task5_wrap_rows_test.py reflow_task6_stack_rows_test.py reflow_task9_reflow_file_test.py reflow_task10_integration_test.py reflow_partial_device_block_regression_test.py reflow_centering_task1_fit_axis_test.py reflow_centering_task3_stack_rows_test.py reflow_centering_task4_end_to_end_test.py; do
  python "$f" > out.txt 2>&1
  status=$?
  if [ $status -ne 0 ]; then echo "FAILED: $f"; cat out.txt; else echo "OK: $f"; fi
done
```

Expected: every file reports `OK`. If any of `reflow_task9_reflow_file_test.py` /
`reflow_task10_integration_test.py` / `phase5_smoke_test.py` fails: inspect whether the
failure is centering now correctly applying to a fixture that happens to be centered
within tolerance (none of their current fixtures are — verified by hand during planning:
every position in those files has a left/right or top/bottom margin difference far
outside the `max(4, 1%)` tolerance) — if so, that fixture's hand-computed expected value
in the test needs updating to match the new (correct) centered output, not the code. If
a genuinely new bug is found instead, treat it as a new task per
`superpowers:systematic-debugging`, not a quick patch.

- [ ] **Step 2: Re-run the real portrait reflow against GenTestProject2 and verify centering**

```bash
cd generator
python -c "
import sys
from pathlib import Path
sys.path.insert(0, str(Path(r'C:\ClaudeProjects\ConstructUISkill2\harness')))
import reflow, compare

PROJECT_DIR = Path(r'C:\Solutions\ClaudeGenTest\GenTestProject2')
source_resolution = {'width': 1280, 'height': 800, 'orientation': 1}
target_resolution = {'width': 800, 'height': 1280, 'orientation': 2}

for name in ['ButtonVariants.cuig', 'ReflowTest.cuig', 'MyWidget.cuiw']:
    path = PROJECT_DIR / name
    result = reflow.reflow_file(path, target_resolution=target_resolution, source_resolution=source_resolution, mode='full_refit')
    ok = compare.round_trip_check(path)
    print(f'{name}: warnings={result.warnings or \"(none)\"} round_trip={\"OK\" if ok else \"FAILED\"}')"
```

Expected: no warnings, all round-trips OK (same as the previous reflow run — this task
only changes WHERE elements land, not whether the file parses/writes correctly).

- [ ] **Step 3: Programmatically confirm ReflowTest.cuig's rows are now centered, not edge-anchored**

```bash
python -c "
import re
path = r'C:\Solutions\ClaudeGenTest\GenTestProject2\ReflowTest.cuig'
raw = open(path, encoding='utf-8').read()
m = re.search(r'\{Css\}\n(.*?)\n\n\{PageAttributes\}', raw, re.S)
css = m.group(1)
blocks = re.findall(r'@media[^{]*\{((?:[^{}]*\{[^{}]*\})*[^{}]*)\}', css)
def rules(block):
    return dict(re.findall(r'#(\S+?)\{([^}]*)\}', block))
portrait = rules(blocks[2])
def parse_left_width(decls):
    d = dict(p.strip().split(':', 1) for p in decls.split(';') if ':' in p)
    return int(d['left'].rstrip('px')), int(d['width'].rstrip('px'))
# The 'Source' row (8 buttons, top=44 in the earlier -- now possibly different -- run):
# group by top value instead of hardcoding ids, since exact ids vary by file content.
import collections
by_top = collections.defaultdict(list)
for eid, decls in portrait.items():
    d = dict(p.strip().split(':', 1) for p in decls.split(';') if ':' in p)
    if 'left' not in d or 'top' not in d:
        continue
    by_top[d['top']].append((eid, int(d['left'].rstrip('px')), int(d['width'].rstrip('px'))))
for top, items in sorted(by_top.items(), key=lambda kv: len(kv[1]), reverse=True)[:2]:
    lefts = [l for _, l, _ in items]
    rights = [l + w for _, l, w in items]
    left_margin, right_margin = min(lefts), 800 - max(rights)
    print(f'row at top={top}: {len(items)} items, left_margin={left_margin}, right_margin={right_margin}')
"
```

Expected: for the row(s) with the most items (the button rows that were centered in the
source), `left_margin` and `right_margin` should now be equal or within 1px of each
other (integer-division rounding) — not the previous `52` vs `0` asymmetry.

- [ ] **Step 4: Update README.md**

Read `README.md`'s current top of `## Current phase` and top of `## Log` (they currently
describe the width/height-fallback reflow fix). Prepend a new `## Current phase` entry
(pushing the previous one down, marked superseded per this file's existing convention)
summarizing: the centering gap found in `ReflowTest.cuig`'s portrait layout, the
brainstorming-approved design (`docs/superpowers/specs/2026-09-10-reflow-centering-
design.md`), what was built (Tasks 1-4 above), and the verified real-file result from
Steps 2-3. Add a matching entry at the top of `## Log`. Follow the file's own established
style exactly (see any existing entry for the level of detail/citation expected).

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "docs: update README for the reflow centering fix"
```
