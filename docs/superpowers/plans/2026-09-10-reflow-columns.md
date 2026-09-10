# Reflow: Column-Aware Row Fitting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Elements within a `detect_rows` row that don't actually Y-overlap each other
(e.g. a vertically-stacked Up/Down button pair sharing a row only because a tall
neighbor like a D-pad bridges them) must be recognized as one shared-X column and
always travel together through wrapping, instead of being fit/peeled as independent
flat items.

**Architecture:** New `detect_columns` groups a row's members by source X-range overlap
(the exact transpose of `detect_rows`' own Y-overlap clustering). `wrap_rows` and
`_fit_group`'s X-loop operate on columns instead of raw elements; `stack_rows`'s Y-axis
is untouched (columns are purely an X-axis fitting-time construct).

**Tech Stack:** Python 3, no new dependencies. Existing test convention: standalone
scripts under `generator/_test_output/`, run directly with `python <file>.py`.

**Spec:** `docs/superpowers/specs/2026-09-10-reflow-columns-design.md`

## Global Constraints

- Backward compatibility: a row with no overlapping-`left`-range members produces one
  single-element column per element — behaviorally identical to today's flat
  per-element fitting for every row shape already covered by existing tests.
- A column's members always travel together through `wrap_rows`' peeling — a peel
  boundary may fall between columns, never between two members of the same column.
- `stack_rows` and `fit_axis`'s centering (`source_dim`/`center`) are unmodified by
  this plan — `stack_rows` still receives plain flat per-row element-id lists.

---

### Task 1: `detect_columns` — the X-axis transpose of `detect_rows`

**Files:**
- Modify: `generator/reflow.py:173-197` (add `detect_columns` immediately after
  `detect_rows`)
- Test: `generator/_test_output/reflow_columns_task1_detect_columns_test.py` (new)

**Interfaces:**
- Produces: `detect_columns(elements: dict[str, dict], row: list[str]) -> list[list[str]]`

- [ ] **Step 1: Write the failing test**

Create `generator/_test_output/reflow_columns_task1_detect_columns_test.py`:

```python
"""Task 1: detect_columns -- the X-axis transpose of detect_rows, scoped to one
already-detected row's members. See docs/superpowers/specs/
2026-09-10-reflow-columns-design.md."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reflow import detect_columns  # noqa: E402


def make(*specs):
    # specs: (id, left, width, top)  -- top is only for verifying within-column order
    return {eid: {"left": left, "width": width, "top": top} for eid, left, width, top in specs}


# --- The real reported shape: two same-left pairs flanking a wide/tall element -------
# iha5b0/i4rvpkl share left=292 (a vertical Up/Down pair); ilqek (D-pad) is disjoint;
# im68at/i66ouw share left=876 (the other pair).
elements = make(
    ("iha5b0", 292, 106, 311), ("i4rvpkl", 292, 106, 409),
    ("ilqek", 474, 332, 234),
    ("im68at", 876, 106, 311), ("i66ouw", 876, 106, 409),
)
row = ["iha5b0", "i4rvpkl", "ilqek", "im68at", "i66ouw"]  # detect_rows' own left-to-right order
result = detect_columns(elements, row)
assert result == [["iha5b0", "i4rvpkl"], ["ilqek"], ["im68at", "i66ouw"]], (
    f"expected 2 pair-columns flanking the D-pad's own column, got {result}"
)
print("real reported shape: 3 columns, pairs grouped, D-pad alone: OK")

# --- Degenerate case: no overlapping left ranges -> one column per element -----------
disjoint = make(("a", 0, 100, 0), ("b", 110, 100, 0), ("c", 220, 100, 0))
result_disjoint = detect_columns(disjoint, ["a", "b", "c"])
assert result_disjoint == [["a"], ["b"], ["c"]], f"expected 3 singleton columns, got {result_disjoint}"
print("degenerate case (no X-overlap): one column per element: OK")

# --- Transitive closure: 3+ elements chained by overlapping (not identical) ranges ---
# a: [0,150), b: [100,250) overlaps a, c: [200,350) overlaps b but not a directly --
# still one column via the same accumulated-range growth detect_rows itself uses.
chained = make(("a", 0, 150, 0), ("b", 100, 150, 10), ("c", 200, 150, 20))
result_chained = detect_columns(chained, ["a", "b", "c"])
assert result_chained == [["a", "b", "c"]], f"expected one transitively-closed column, got {result_chained}"
print("transitive closure (chained overlaps): one column: OK")

# --- Within-column order is top-to-bottom, not input/left order ----------------------
# iha5b0 (top=311) must come before i4rvpkl (top=409) in the pair's own column.
assert result[0] == ["iha5b0", "i4rvpkl"], "within-column order must be top-to-bottom"
print("within-column order is top-to-bottom: OK")

# --- Empty row -------------------------------------------------------------------
assert detect_columns({}, []) == []
print("empty row: OK")

print("\nTASK 1: detect_columns -- ALL CHECKS PASSED")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd generator/_test_output && python reflow_columns_task1_detect_columns_test.py`
Expected: `ImportError: cannot import name 'detect_columns' from 'reflow'`

- [ ] **Step 3: Implement `detect_columns`**

In `generator/reflow.py`, immediately after `detect_rows` (currently ending at line
197, right before `_row_fits`), insert:

```python
def detect_columns(elements: dict[str, dict], row: list[str]) -> list[list[str]]:
    """X-axis transpose of detect_rows (see docs/superpowers/specs/
    2026-09-10-reflow-columns-design.md), scoped to one already-detected row's member
    ids: sort by `left`, then greedily cluster -- an element joins the current column
    if its [left, left+width) range overlaps the column's accumulated [column_left,
    column_right) range so far (column_right grows to the widest member seen);
    otherwise it starts a new column. Columns are returned left-to-right; within a
    column, ids are ordered top-to-bottom by `top` (the transpose of detect_rows' own
    left-to-right member ordering) -- natural reading order for a vertical stack like a
    Up/Down button pair.

    A row with no overlapping `left` ranges produces one single-element column per
    element -- identical in effect to fitting each element independently, so this is
    additive over today's flat per-element behavior for every row shape without this
    kind of stacked sub-group."""
    if not row:
        return []
    ordered = sorted(row, key=lambda eid: elements[eid]["left"])
    columns: list[list[str]] = []
    current_ids: list[str] = []
    column_right = None
    for element_id in ordered:
        e = elements[element_id]
        left, right = e["left"], e["left"] + e["width"]
        if column_right is None or left < column_right:
            current_ids.append(element_id)
            column_right = right if column_right is None else max(column_right, right)
        else:
            columns.append(sorted(current_ids, key=lambda i: elements[i]["top"]))
            current_ids = [element_id]
            column_right = right
    columns.append(sorted(current_ids, key=lambda i: elements[i]["top"]))
    return columns
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd generator/_test_output && python reflow_columns_task1_detect_columns_test.py`
Expected: `TASK 1: detect_columns -- ALL CHECKS PASSED`

- [ ] **Step 5: Commit**

```bash
git add generator/reflow.py generator/_test_output/reflow_columns_task1_detect_columns_test.py
git commit -m "reflow: add detect_columns, the X-axis transpose of detect_rows"
```

---

### Task 2: `wrap_rows` becomes column-aware

**Files:**
- Modify: `generator/reflow.py:200-248` (`_row_fits` and `wrap_rows`)
- Modify: `generator/_test_output/reflow_task5_wrap_rows_test.py` (update for the new
  return shape, add a column-preserving-peel case)

**Interfaces:**
- Consumes: `detect_columns(elements, row) -> list[list[str]]` (Task 1)
- Produces: `wrap_rows(rows: list[list[str]], elements: dict[str, dict], target_width: int) -> list[tuple[list[list[str]], bool]]` — return type changed: a "row" is now `list[list[str]]` (a list of columns, each a list of element ids), not `list[str]`.

- [ ] **Step 1: Update the existing test's assertions first (they'll fail against the current code — that's the point)**

Replace the full contents of `generator/_test_output/reflow_task5_wrap_rows_test.py`
with:

```python
"""Task 5 (original reflow plan) + Task 2 (2026-09-10 centering plan) + Task 2
(2026-09-10 columns plan): wrap_rows -- splits a row that doesn't fit target_width by
peeling trailing COLUMNS onto a new row (a column's own members, e.g. a stacked Up/Down
pair, always travel together -- see docs/superpowers/specs/
2026-09-10-reflow-columns-design.md), tagging each output row as a fragment (True, came
from a split) or untouched (False)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reflow import wrap_rows  # noqa: E402

def make(*specs):
    # specs: (id, left, width, top)
    return {eid: {"left": left, "width": width, "top": top} for eid, left, width, top in specs}

# --- A row that already fits: no split, untouched (False) ------------------------
# No overlapping left ranges -> every element is its own column.
elements = make(("a", 0, 100, 0), ("b", 110, 100, 0), ("c", 220, 100, 0), ("d", 330, 100, 0))
assert wrap_rows([["a", "b", "c", "d"]], elements, target_width=500) == [([["a"], ["b"], ["c"], ["d"]], False)]
print("already fits, no split, untouched (False), one column per element: OK")

# --- A row that needs exactly one split: both halves are fragments (True) --------
# span = (330+100) - 0 = 430 > 250; peeling c,d together (a,b alone span 210 <= 250 fits).
result = wrap_rows([["a", "b", "c", "d"]], elements, target_width=250)
assert result == [([["a"], ["b"]], True), ([["c"], ["d"]], True)], f"expected one split into two fragment rows, got {result}"
print("exactly one split, both halves fragments (True): OK")

# --- A row dense enough to need multiple splits: every resulting row is a fragment -
dense = make(*[(f"e{i}", i * 110, 100, 0) for i in range(6)])  # e0..e5, 100px wide, 10px gaps
result = wrap_rows([[f"e{i}" for i in range(6)]], dense, target_width=150)
assert result == [([[f"e{i}"]], True) for i in range(6)], f"expected 6 singleton fragment rows, got {result}"
print("multiple splits down to singletons, all fragments (True): OK")

# --- A single element wider than target_width on its own: left as a 1-column row,
#     never loops, untouched (False).
wide = make(("w", 0, 300, 0))
assert wrap_rows([["w"]], wide, target_width=250) == [([["w"]], False)]
print("single too-wide element left unsplit, untouched (False): OK")

# --- Multiple independent rows: only the offending row splits (fragments, True),
#     the other row is untouched (False).
mixed = make(("a", 0, 100, 0), ("b", 110, 100, 0), ("c", 220, 100, 0), ("d", 330, 100, 0), ("z", 0, 50, 0))
result = wrap_rows([["a", "b", "c", "d"], ["z"]], mixed, target_width=250)
assert result == [([["a"], ["b"]], True), ([["c"], ["d"]], True), ([["z"]], False)], f"expected only the first row to split, got {result}"
print("only the offending row splits (True), the other stays untouched (False): OK")

# --- NEW (Task 2, columns): a stacked pair (same left) always travels together -------
# Two columns: a pair at left=0 (two elements, same left) and a lone wide element at
# left=200 that doesn't fit alongside the pair. The peel must move the WHOLE pair or
# the WHOLE lone column, never split the pair's two members apart.
paired = make(("p1", 0, 80, 0), ("p2", 0, 80, 50), ("wide", 200, 300, 0))
result = wrap_rows([["p1", "p2", "wide"]], paired, target_width=150)
# columns: [["p1","p2"], ["wide"]] (span 0-500=500>150) -- must split into exactly these
# two columns, each a fragment; the pair's members must never be separated into
# different output rows.
assert result == [([["p1", "p2"]], True), ([["wide"]], True)], f"pair must travel together, got {result}"
print("a stacked pair (same left) always travels together through a peel: OK")

print("\nTASK 5/2/2: wrap_rows column-aware peeling -- ALL CHECKS PASSED")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd generator/_test_output && python reflow_task5_wrap_rows_test.py`
Expected: `AssertionError` on the first `assert` (current code returns
`[(["a", "b", "c", "d"], False)]`, not `[([["a"], ["b"], ["c"], ["d"]], False)]`)

- [ ] **Step 3: Implement column-aware `wrap_rows`**

Replace `generator/reflow.py` lines 200-248 (`_row_fits` and `wrap_rows`) with:

```python
def _columns_fit(columns: list[list[str]], elements: dict[str, dict], target_width: int) -> bool:
    ids = [eid for column in columns for eid in column]
    lefts = [elements[eid]["left"] for eid in ids]
    rights = [elements[eid]["left"] + elements[eid]["width"] for eid in ids]
    return max(rights) - min(lefts) <= target_width


def wrap_rows(rows: list[list[str]], elements: dict[str, dict], target_width: int) -> list[tuple[list[list[str]], bool]]:
    """X-axis wrap tier, run between fit_axis's Tier 1 and Tier 2 (see spec). For each
    row (in order), check the same bounding-box test as fit_axis's own Tier 1 test,
    scoped to just that row's elements; a row that passes needs nothing further. A row
    that fails and has more than one COLUMN peels columns off its trailing (right-most)
    end -- ALL of them in one pass -- until what remains passes; the peeled columns
    become one new row, inserted immediately after, which itself gets the same check on
    a later iteration (so a very crowded row can split into more than two). A row
    already down to one column is always left as-is regardless of whether it fits --
    wrapping can't help split it further; that case falls through to fit_axis's own
    compact/scale tiers when X positions are finalized per row (see the spec's Tiers
    3/4 note).

    Returns `[(columns, is_fragment), ...]` -- UPDATED 2026-09-10 (column-aware, see
    docs/superpowers/specs/2026-09-10-reflow-columns-design.md): each input `row` is
    first grouped into columns (detect_columns) before peeling -- a column's own
    members (e.g. a vertically-stacked Up/Down button pair sharing a row only because a
    taller neighbor bridges them) always travel together; a peel boundary may fall
    between columns, never between two members of the same column. `is_fragment` is
    True for a row produced by peeling (both the shrunk remainder and every peeled-off
    piece), False for a row that passed through untouched. `_fit_group` uses this to
    decide whether a row's centering is auto-detected from its own original margins
    (untouched) or always applied (fragment -- a subset of a once-centered row has no
    meaningful "was it centered" answer of its own)."""
    pending: list[list[list[str]]] = [detect_columns(elements, row) for row in rows]
    pending_is_fragment = [False] * len(rows)
    result: list[tuple[list[list[str]], bool]] = []
    i = 0
    while i < len(pending):
        columns = pending[i]
        if len(columns) <= 1 or _columns_fit(columns, elements, target_width):
            result.append((columns, pending_is_fragment[i]))
            i += 1
            continue
        remainder = columns
        peeled: list[list[str]] = []
        while len(remainder) > 1 and not _columns_fit(remainder, elements, target_width):
            peeled.insert(0, remainder[-1])
            remainder = remainder[:-1]
        pending[i] = remainder
        pending_is_fragment[i] = True
        pending.insert(i + 1, peeled)
        pending_is_fragment.insert(i + 1, True)
        # Don't advance i: re-check the shrunk `remainder` (now at pending[i]) next
        # iteration -- it passes immediately since peeling stopped exactly when it
        # started fitting (or dropped to one column).
    return result
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd generator/_test_output && python reflow_task5_wrap_rows_test.py`
Expected: `TASK 5/2/2: wrap_rows column-aware peeling -- ALL CHECKS PASSED`

- [ ] **Step 5: Commit**

```bash
git add generator/reflow.py generator/_test_output/reflow_task5_wrap_rows_test.py
git commit -m "reflow: wrap_rows peels whole columns, never splits a stacked pair's members"
```

*(Note: `_fit_group` still expects `wrap_rows`' OLD flat-element return shape at this
point -- Task 3 rewires it. `reflow_file`-dependent tests will not pass again until
Task 3 is done; expected, not a regression to chase down now, same as the equivalent
note in the 2026-09-10 centering plan's Task 2.)*

---

### Task 3: Wire `_fit_group`'s X-loop to fit columns, not elements

**Files:**
- Modify: `generator/reflow.py:483-534` (`_fit_group`'s row/wrap/X-fit/Y-fit section)
- Test: `generator/_test_output/reflow_columns_task3_end_to_end_test.py` (new)

**Interfaces:**
- Consumes: `wrap_rows(...) -> list[tuple[list[list[str]], bool]]` (Task 2)
- Produces: `_fit_group`'s external signature/return type are UNCHANGED — this task only changes its internal X-fitting logic.

- [ ] **Step 1: Write the failing end-to-end test**

Create `generator/_test_output/reflow_columns_task3_end_to_end_test.py`:

```python
"""Task 3: end-to-end -- replays the real bug (found 2026-09-10 in the user's
ReflowTest.cuig, TSW-570/640x360): a D-pad flanked by two same-left Up/Down button
pairs, reflowed into a target narrow enough that the flat 5-element model wrapped
(tearing pairs apart and forcing extra vertical compression), but the column-aware
model fits via Tier 2 compaction alone -- no wrap needed at all (hand-traced in the
design spec: needed_reduction=50, slack=138)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))

from reflow import reflow_file  # noqa: E402
from devices import ORIENTATION_ENUM  # noqa: E402
import layout  # noqa: E402
import compare  # noqa: E402

OUT = Path(__file__).resolve().parent / "ReflowColumnsE2E"
OUT.mkdir(parents=True, exist_ok=True)


def make_file(path: Path, html: str, css: str) -> None:
    path.write_text(
        "{FileMetadata}\nSchema = \"1.0.0.0\"\n"
        f"\n{{Html}}\n{html}\n"
        f"\n{{Css}}\n{css}\n"
        "\n{PageAttributes}\n\n[Attributes]\nName = \"P\"\n",
        encoding="utf-8",
    )


source = {"width": 1280, "height": 800, "orientation": ORIENTATION_ENUM["landscape"]}
target = {"width": 640, "height": 360, "orientation": ORIENTATION_ENUM["landscape"]}

source_query = layout.orientation_media_query("landscape", 1280, 800)

ids = ["iha5b0", "i4rvpkl", "ilqek", "im68at", "i66ouw"]
html = "".join(f'<div id="{eid}"></div>' for eid in ids)
css = (
    f"@media {source_query}{{"
    "#iha5b0{display: block; left: 292px; top: 311px; position: absolute; width: 106px; height: 79px;}"
    "#i4rvpkl{display: block; left: 292px; top: 409px; position: absolute; width: 106px; height: 79px;}"
    "#ilqek{display: block; left: 474px; top: 234px; position: absolute; width: 332px; height: 332px;}"
    "#im68at{display: block; left: 876px; top: 311px; position: absolute; width: 106px; height: 79px;}"
    "#i66ouw{display: block; left: 876px; top: 409px; position: absolute; width: 106px; height: 79px;}"
    "}"
)
path = OUT / "DpadPairs.cuig"
make_file(path, html, css)

result = reflow_file(path, target_resolution=target, source_resolution=source, mode="pin_existing")
assert result.warnings == [], f"expected no warnings, got {result.warnings}"
assert compare.round_trip_check(path)

new_css = compare.parse_file(path).sections[2][2]
target_query = layout.orientation_media_query("landscape", 640, 360)
new_block = layout.find_media_block(new_css, target_query)
assert new_block is not None
fitted = layout.parse_position_rules(new_block)
assert set(fitted) == set(ids)

# The actual point of the fix: each pair's two members always share the same left.
assert fitted["iha5b0"]["left"] == fitted["i4rvpkl"]["left"], (
    f"Up/Down pair must share left, got {fitted['iha5b0']['left']} vs {fitted['i4rvpkl']['left']}"
)
assert fitted["im68at"]["left"] == fitted["i66ouw"]["left"], (
    f"Up/Down pair must share left, got {fitted['im68at']['left']} vs {fitted['i66ouw']['left']}"
)
print("Both Up/Down pairs share a left position after reflow: OK")

# Hand-traced in the design spec: Tier 2 compaction alone fits this -- no wrap needed,
# so every element keeps its original TOP-level row structure (no element scaled down).
for eid in ids:
    assert fitted[eid]["width"] in (106, 332), f"{eid} must not be scaled (Tier 2 alone should suffice), got {fitted[eid]}"
print("No scaling needed -- Tier 2 compaction alone fits the row (confirms the spec's hand-trace): OK")

# Zero overlaps, everything on-canvas.
def overlaps(a, b):
    return not (
        a["left"] + a["width"] <= b["left"] or b["left"] + b["width"] <= a["left"]
        or a["top"] + a["height"] <= b["top"] or b["top"] + b["height"] <= a["top"]
    )

for i in range(len(ids)):
    for j in range(i + 1, len(ids)):
        assert not overlaps(fitted[ids[i]], fitted[ids[j]]), f"overlap: {ids[i]} vs {ids[j]}"
for eid in ids:
    e = fitted[eid]
    assert e["left"] + e["width"] <= 640 and e["top"] + e["height"] <= 360, f"{eid} off-canvas: {e}"
print("Zero overlaps, everything on-canvas: OK")

print("\nTASK 3: column-aware end-to-end -- ALL CHECKS PASSED")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd generator/_test_output && python reflow_columns_task3_end_to_end_test.py`
Expected: an exception or assertion failure (`_fit_group` still unpacks `wrap_rows`'
old shape and builds one `fit_axis` item per element, so the pairs still get corrupted)

- [ ] **Step 3: Wire `_fit_group`**

Replace `generator/reflow.py` lines 513-533 (from `rows = detect_rows(elements)`
through the `y_fit = stack_rows(...)` block) with:

```python
    rows = detect_rows(elements)
    wrapped_rows = wrap_rows(rows, elements, target_width)

    x_fit: dict[str, dict] = {}
    for columns, is_fragment in wrapped_rows:
        row_items = []
        for idx, column in enumerate(columns):
            col_key = f"__col{idx}"
            col_left = min(elements[eid]["left"] for eid in column)
            col_right = max(elements[eid]["left"] + elements[eid]["width"] for eid in column)
            row_items.append((col_key, col_left, col_right - col_left))
        try:
            if is_fragment:
                col_fit = fit_axis(row_items, target_width, center=True)
            else:
                col_fit = fit_axis(row_items, target_width, source_dim=source_width)
        except AxisFitError as e:
            warnings.append(f"{path.name}: X axis for {query} -- {e}")
            return None
        for idx, column in enumerate(columns):
            fit = col_fit[f"__col{idx}"]
            for eid in column:
                own_width = elements[eid]["width"]
                x_fit[eid] = {
                    "pos": fit["pos"],
                    "size": max(1, int(own_width * fit["scale"])) if fit["scale"] != 1.0 else own_width,
                    "scale": fit["scale"],
                }

    row_lists = [[eid for column in columns for eid in column] for columns, _ in wrapped_rows]
    try:
        y_fit = stack_rows(row_lists, elements, target_height, source_height=source_height)
    except AxisFitError as e:
        warnings.append(f"{path.name}: Y axis for {query} -- {e}")
        return None
```

Also update `_fit_group`'s docstring: after the existing `id_to_tag`/`sdk` paragraph,
append:

```
    ADDED 2026-09-10 (column-aware, see docs/superpowers/specs/
    2026-09-10-reflow-columns-design.md): the X-loop now fits one item PER COLUMN
    (detect_columns' grouping of each row's elements by source X-range overlap), not
    one item per element -- elements that share a column (e.g. a vertically-stacked
    Up/Down pair) always get the SAME final `left`, each keeping its own width scaled
    by the column's own scale factor. `stack_rows`' Y-axis is unaffected: `row_lists`
    flattens each wrapped row's columns back into a plain element-id list, the same
    shape `stack_rows` already expected.
```

(The rest of `_fit_group`'s body — the `fitted: dict[str, dict] = {}` loop building
`width, height = x["size"], y["height"]` etc. — is unchanged; it already only reads
`x_fit[eid]["size"]`/`["scale"]`/`["pos"]`, which the new per-member loop above still
populates identically in shape.)

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd generator/_test_output && python reflow_columns_task3_end_to_end_test.py`
Expected: `TASK 3: column-aware end-to-end -- ALL CHECKS PASSED`

- [ ] **Step 5: Commit**

```bash
git add generator/reflow.py generator/_test_output/reflow_columns_task3_end_to_end_test.py
git commit -m "reflow: _fit_group fits one item per column, not per element"
```

---

### Task 4: Full regression run, re-verify against the real GenTestProject2, update README

**Files:**
- Verify only (no source changes expected): every existing test under
  `generator/_test_output/`
- Verify: `C:\Solutions\ClaudeGenTest\GenTestProject2\ReflowTest.cuig`,
  `ButtonVariants.cuig`, `MyWidget.cuiw` (the real files)
- Modify: `.gitignore` (add `generator/_test_output/ReflowColumnsE2E/`)
- Modify: `README.md` (Current phase + Log, per this project's standing convention)

**Interfaces:**
- Consumes: everything from Tasks 1-3.
- Produces: nothing new — this task is verification + documentation only.

- [ ] **Step 1: Run every existing generator test and confirm zero regressions**

Run (from `generator/_test_output/`):

```bash
for f in phase2_smoke_test.py phase3_smoke_test.py phase4_smoke_test.py phase5_smoke_test.py reflow_task3_fit_axis_test.py reflow_task5_wrap_rows_test.py reflow_task6_stack_rows_test.py reflow_task9_reflow_file_test.py reflow_task10_integration_test.py reflow_partial_device_block_regression_test.py reflow_centering_task1_fit_axis_test.py reflow_centering_task3_stack_rows_test.py reflow_centering_task4_end_to_end_test.py reflow_aspect_lock_dpad_test.py reflow_force_custom_size_test.py reflow_missing_size_vars_test.py reflow_columns_task1_detect_columns_test.py reflow_columns_task3_end_to_end_test.py; do
  python "$f" > out.txt 2>&1
  status=$?
  if [ $status -ne 0 ]; then echo "FAILED: $f"; cat out.txt; else echo "OK: $f"; fi
done
```

Expected: every file reports `OK`. `reflow_task9_reflow_file_test.py`/
`reflow_task10_integration_test.py`/`phase5_smoke_test.py`/
`reflow_aspect_lock_dpad_test.py`/`reflow_force_custom_size_test.py`/
`reflow_missing_size_vars_test.py` don't use any same-left-position elements in their
fixtures (verified during planning), so column-grouping degenerates to one column per
element for all of them — no assertion changes expected. If one does fail, inspect
whether it's a genuinely column-worthy fixture whose expected values need updating
(new correct behavior) vs. an actual bug (new task per
`superpowers:systematic-debugging`, not a quick patch).

- [ ] **Step 2: Re-run the real TSW-570 reflow against GenTestProject2**

```bash
cd generator
python -c "
import sys
from pathlib import Path
sys.path.insert(0, str(Path(r'C:\ClaudeProjects\ConstructUISkill2\harness')))
import reflow, compare
from sdk import read_sdk

ui_sdk = read_sdk('2.18.0')
PROJECT_DIR = Path(r'C:\Solutions\ClaudeGenTest\GenTestProject2')
source_resolution = {'width': 1280, 'height': 800, 'orientation': 1}
target_resolution = {'width': 640, 'height': 360, 'orientation': 1}

for name in ['ButtonVariants.cuig', 'ReflowTest.cuig', 'MyWidget.cuiw']:
    path = PROJECT_DIR / name
    result = reflow.reflow_file(path, target_resolution=target_resolution, source_resolution=source_resolution, mode='full_refit', sdk=ui_sdk)
    ok = compare.round_trip_check(path)
    print(f'{name}: warnings={result.warnings or \"(none)\"} round_trip={\"OK\" if ok else \"FAILED\"}')"
```

Expected: no warnings, all round-trips OK.

- [ ] **Step 3: Programmatically confirm the Up/Down pairs now share the D-pad's row without wrapping, and every button is legibly sized**

```bash
python -c "
import re
path = r'C:\Solutions\ClaudeGenTest\GenTestProject2\ReflowTest.cuig'
raw = open(path, encoding='utf-8').read()
m = re.search(r'\{Css\}\n(.*?)\n\n\{PageAttributes\}', raw, re.S)
css = m.group(1)
import layout
q = layout.orientation_media_query('landscape', 640, 360)
els = layout.parse_all_position_rules(css, q)
for eid in ['iha5b0tdmap0q','i4rvpkl9kjg7k','ilqek','im68athbnopv5','i66ouwpdb2vjg']:
    print(eid, els.get(eid))
print()
print('Source-row button heights (expect much closer to the original ~42px than 21px, since Tier 3 should no longer need to compress this hard):')
for eid in ['i8pg','ihe13ug9gr']:
    print(eid, els.get(eid))
"
```

Expected: `iha5b0tdmap0q`/`i4rvpkl9kjg7k` share the same `left`;
`im68athbnopv5`/`i66ouwpdb2vjg` share the same `left`; per the design spec's hand-trace,
none of these 5 elements should be scaled down at all (widths 106/106/332/106/106,
unchanged from source). Source-row button heights should be visibly larger than the
previous 21px (confirms less aggressive Y-axis compression now that the row-stack
doesn't waste height on an unnecessary extra row).

- [ ] **Step 4: Update README.md**

Read `README.md`'s current top of `## Current phase` and top of `## Log`. Prepend a new
`## Current phase` entry (pushing the previous one down, marked superseded per this
file's existing convention) summarizing: the Up/Down-pair/D-pad row-corruption gap
found live-testing TSW-570, the brainstorming-approved column model
(`docs/superpowers/specs/2026-09-10-reflow-columns-design.md`), what was built (Tasks
1-3 above), and the verified real-file result from Steps 2-3 (pairs now share a `left`,
no longer wrapped/scaled unnecessarily). Add a matching entry at the top of `## Log`.
Follow the file's own established style exactly.

- [ ] **Step 5: Commit**

```bash
git add .gitignore README.md
git commit -m "docs: update README for column-aware row fitting"
```
