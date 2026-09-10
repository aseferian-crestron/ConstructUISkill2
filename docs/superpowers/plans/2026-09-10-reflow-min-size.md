# Reflow: Minimum-Size Floors Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tier 3 of reflow's fit algorithm must stop shrinking a real component below a
practical minimum size (28px-tall buttons at TSW-570 were the reported symptom) — each
item gets its own floor, sourced from the SDK schema's `minSizes` when it has one and a
module-level fallback constant when it doesn't.

**Architecture:** `fit_axis` gains an optional `min_sizes: dict[item_id -> int]`. Passing
`None` (every existing caller/test) keeps today's byte-for-byte one-shot Tier 3. Passing a
dict switches to a flexbox-style iterative freeze-and-redistribute: freeze any item whose
uniformly-scaled size would drop below its own floor, reserve exactly that floor, recompute
the scale for the rest, repeat to convergence. `_fit_group` derives per-column floors for
the X axis; `stack_rows` derives a per-row floor for the Y axis from its most-constrained
member. Both pass `min_sizes=None` (never `{}`) whenever `sdk` is `None`, so the legacy
path is genuinely untouched for legacy callers.

**Tech Stack:** Python 3, no new dependencies. Test convention: standalone scripts under
`generator/_test_output/`, run directly with `python <file>.py` (no pytest; a test passes
when it prints its OK lines and exits 0).

**Spec:** `docs/superpowers/specs/2026-09-10-reflow-min-size-design.md`

## Global Constraints

- **Backward compatibility is a hard requirement:** omitting `min_sizes` must reproduce
  today's exact output. `min_sizes is None` runs the original one-shot Tier 3 code
  verbatim; only an actual dict (even `{}`) selects the new logic. Every existing test in
  `generator/_test_output/` must pass unchanged.
- Tiers 1 (move) and 2 (compact) never resize anything, so they are untouched by this
  plan. `wrap_rows`/`_columns_fit` reason about original widths only — also untouched.
- Tier 3 stays **shrink-only**: a minimum is clamped to the item's own current size, so an
  item already smaller than its floor is left alone rather than grown (see Task 2).
- `FALLBACK_MIN_SIZE_PX = 30` — one module-level constant in `generator/reflow.py`.
- Failure mode is unchanged in shape: an unsatisfiable axis raises `AxisFitError`, which
  `_fit_group` already turns into a per-file warning and a skipped target block.
- Per-item `"scale"` in `fit_axis`'s result means "this item's OWN size ratio"
  (`new_size / old_size`). In the legacy branch that's trivially the flat group scale, as
  today; in the dict branch a frozen item reports its own true ratio.

## Spec amendments discovered while planning (evidence-backed, implement as written here)

Verified against the real installed SDK 2.18.0 (dumped every `component-context.json`
entry carrying `minSizes`):

```
ch5-datetime {'minWidth': '40'}          ch5-dpad {'minWidth': '100px'}
ch5-keypad {'minWidth': '210px'}         ch5-media-player {'minWidth': '360px', 'minHeight': '360px'}
ch5-qrcode {'minWidth': '160'}           ch5-tab-button {'minWidth': '110', 'minHeight': '68'}
ch5-text {'minWidth': '10', 'minHeight': '10'}   ch5-toggle {'minWidth': '100px'}
ch5-video-switcher {'minWidth': 300}
```

1. **Values are not uniformly `"Npx"` strings.** Some are unit-less strings (`"40"`,
   `"160"`), and `ch5-video-switcher`'s is a raw JSON **int** (`300`). The spec's
   `int(min_width.rstrip("px"))` raises `AttributeError` on that one. Task 1 parses
   int/float/`"N"`/`"Npx"` and returns `None` for anything unparseable.
2. **`minHeight` exists for three tags** and the spec (written from the dpad/keypad
   evidence only) applies `minWidth` to both axes. Task 1 takes an `axis` argument:
   height prefers `minHeight`, falling back to `minWidth` (which is what the spec asked
   for, and stays correct for the aspect-locked square components), then the constant.
   Width uses `minWidth` then the constant.
3. **Minimums are clamped to the item's own size inside `fit_axis`.** The spec doesn't
   cover a source item already below its own floor (e.g. a `ch5-dpad` authored at 90px, or
   a row whose derived floor exceeds its natural height). Unclamped, such an item would be
   "frozen" LARGER than it started — Tier 3 growing something it was asked to shrink — and
   the `sum(mins) <= available` pre-check would reject axes that fit fine today. Clamping
   makes Tier 3 shrink-only, as it is now.

**Known limitation, deliberately out of scope** (document in the docstring, don't fix): a
column's floor is the max over its members, and members are then scaled by the column's own
ratio, so a member much narrower than its column-mate could still land under its own floor.
Real columns are stacked pairs of equal width, so this can't bite the shapes this project
has evidence for.

---

### Task 1: `FALLBACK_MIN_SIZE_PX` + `_component_min_size`

**Files:**
- Modify: `generator/reflow.py` (add both immediately after `_is_aspect_locked`, ~line 548)
- Test: `generator/_test_output/reflow_min_size_task1_lookup_test.py` (new)

**Interfaces:**
- Produces: `FALLBACK_MIN_SIZE_PX: int` (= 30);
  `_parse_min_size(value: object) -> int | None`;
  `_component_min_size(sdk: UiSdk, tag_name: str, axis: str = "width") -> int`

- [ ] **Step 1: Write the failing test**

Create `generator/_test_output/reflow_min_size_task1_lookup_test.py`:

```python
"""Task 1: _component_min_size -- per-component minimum size from the SDK's own
`minSizes` schema entry, with a module-constant fallback for the (many) types the
schema doesn't constrain. See docs/superpowers/specs/2026-09-10-reflow-min-size-design.md."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reflow import FALLBACK_MIN_SIZE_PX, _component_min_size, _parse_min_size  # noqa: E402
from sdk import read_sdk  # noqa: E402

ui_sdk = read_sdk("2.18.0")

# --- Real, schema-published technical floors ---------------------------------------
assert _component_min_size(ui_sdk, "ch5-dpad") == 100, "ch5-dpad's schema minWidth is '100px'"
assert _component_min_size(ui_sdk, "ch5-keypad") == 210, "ch5-keypad's schema minWidth is '210px'"
print("schema-published minWidth (dpad 100, keypad 210): OK")

# --- No minSizes entry at all -> the tunable fallback constant ----------------------
assert _component_min_size(ui_sdk, "ch5-button") == FALLBACK_MIN_SIZE_PX
assert _component_min_size(ui_sdk, "ch5-slider") == FALLBACK_MIN_SIZE_PX
print(f"unconstrained types fall back to {FALLBACK_MIN_SIZE_PX}px: OK")

# --- An unknown tag must never raise -- it's the fallback, same as no entry ---------
assert _component_min_size(ui_sdk, "div") == FALLBACK_MIN_SIZE_PX
assert _component_min_size(ui_sdk, "ch5-not-a-real-tag") == FALLBACK_MIN_SIZE_PX
print("unknown tag falls back without raising: OK")

# --- Value-format robustness: the schema is NOT uniformly "Npx" strings -------------
# ch5-qrcode's is the unit-less string "160"; ch5-video-switcher's is a raw JSON int.
assert _component_min_size(ui_sdk, "ch5-qrcode") == 160, "unit-less string minWidth"
assert _component_min_size(ui_sdk, "ch5-video-switcher") == 300, "raw int minWidth"
assert _parse_min_size("100px") == 100 and _parse_min_size("40") == 40
assert _parse_min_size(300) == 300 and _parse_min_size(12.7) == 12
assert _parse_min_size(None) is None and _parse_min_size("auto") is None
assert _parse_min_size("0px") == 1, "never return a 0/negative floor"
print("value parsing (px string / bare string / int / float / junk): OK")

# --- Per-axis: minHeight wins on the height axis, minWidth is its fallback ----------
assert _component_min_size(ui_sdk, "ch5-tab-button", "width") == 110
assert _component_min_size(ui_sdk, "ch5-tab-button", "height") == 68, "own minHeight"
assert _component_min_size(ui_sdk, "ch5-dpad", "height") == 100, "no minHeight -> minWidth"
assert _component_min_size(ui_sdk, "ch5-button", "height") == FALLBACK_MIN_SIZE_PX
print("per-axis lookup (minHeight preferred, minWidth fallback): OK")

print("\nTask 1: all assertions passed.")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:\ClaudeProjects\ConstructUISkill2\generator\_test_output && python reflow_min_size_task1_lookup_test.py`
Expected: FAIL — `ImportError: cannot import name 'FALLBACK_MIN_SIZE_PX' from 'reflow'`

- [ ] **Step 3: Write minimal implementation**

In `generator/reflow.py`, immediately after `_is_aspect_locked` (before `_fit_group`):

```python
FALLBACK_MIN_SIZE_PX = 30
"""Minimum size (px, both axes) for component types the SDK's own schema doesn't
constrain -- ch5-button/ch5-slider and most others have no `minSizes` entry at all,
because scaling one of those down is a legibility judgement, not a technical limit.
Tune freely: it never overrides a real schema-published floor, only fills the gap
where Crestron publishes nothing. Found necessary 2026-09-10, live-testing TSW-570
(640x360): real buttons were being scaled to 28px tall -- too small at runtime."""


def _parse_min_size(value: object) -> int | None:
    """One `minSizes` value -> px int, or None if it isn't a usable number. The real
    schema is NOT uniformly "Npx" strings (verified against SDK 2.18.0): ch5-dpad has
    "100px", ch5-qrcode has the unit-less "160", and ch5-video-switcher has a raw JSON
    int 300 -- a naive `.rstrip("px")` raises AttributeError on the last one."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return max(1, int(value))
    text = str(value).strip().lower()
    if text.endswith("px"):
        text = text[:-2].strip()
    try:
        return max(1, int(float(text)))
    except ValueError:
        return None


def _component_min_size(sdk: "sdk_module.UiSdk", tag_name: str, axis: str = "width") -> int:
    """`tag_name`'s practical minimum size on `axis` ("width"/"height"), in px --
    Tier 3's per-item floor (see fit_axis's `min_sizes`). Two sources, in order: the
    SDK's own `minSizes` schema entry (a real, Construct-enforced technical floor --
    ch5-dpad 100px, ch5-keypad 210px) and FALLBACK_MIN_SIZE_PX for every type the
    schema says nothing about. The height axis prefers `minHeight` when the schema
    publishes one (ch5-tab-button: 110 wide / 68 tall) and otherwise reuses
    `minWidth`, which is correct for the square, single-axis-sourced components that
    dominate this set (see _is_aspect_locked). Never raises: an unknown tag is
    indistinguishable from a tag with no floor."""
    try:
        ctx = sdk.context_for(tag_name)
    except (KeyError, StopIteration):
        return FALLBACK_MIN_SIZE_PX
    min_sizes = ctx.get("minSizes") if isinstance(ctx, dict) else None
    if isinstance(min_sizes, dict):
        keys = ("minHeight", "minWidth") if axis == "height" else ("minWidth",)
        for key in keys:
            parsed = _parse_min_size(min_sizes.get(key))
            if parsed is not None:
                return parsed
    return FALLBACK_MIN_SIZE_PX
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python reflow_min_size_task1_lookup_test.py`
Expected: PASS — every OK line, then "Task 1: all assertions passed."

- [ ] **Step 5: Commit**

```bash
git add generator/reflow.py generator/_test_output/reflow_min_size_task1_lookup_test.py
git commit -m "reflow: per-component minimum-size lookup from the SDK's minSizes schema"
```

---

### Task 2: `fit_axis` — minimum-size-aware Tier 3

**Files:**
- Modify: `generator/reflow.py:38-171` (`fit_axis` signature + docstring + the Tier 3 block at the end)
- Test: `generator/_test_output/reflow_min_size_task2_fit_axis_test.py` (new)

**Interfaces:**
- Consumes: nothing from Task 1 (the dict is built by callers, not by `fit_axis`).
- Produces: `fit_axis(items, target_dim, min_gap=4, source_dim=None, center=None, min_sizes: dict[str, int] | None = None)`.
  Result shape is unchanged: `{item_id: {"pos": int, "size": int, "scale": float}}`.

- [ ] **Step 1: Write the failing test**

Create `generator/_test_output/reflow_min_size_task2_fit_axis_test.py`:

```python
"""Task 2: fit_axis's Tier 3 becomes minimum-size-aware -- iterative freeze-and-
redistribute (the same shape as CSS flexbox's shrink-with-min-width), gated so that
omitting `min_sizes` runs the untouched legacy one-shot formula. See
docs/superpowers/specs/2026-09-10-reflow-min-size-design.md."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reflow import fit_axis, AxisFitError  # noqa: E402

# --- The spec's hand-traced example: one item freezes, two don't --------------------
# 3x100px items, target 100, min_gap 4 -> available_for_sizes = 92; mins a=60.
# Round 1: scale 92/300=0.307 -> a would be 30.7 < 60, freezes at 60.
# Round 2: free 32 over 200 -> scale 0.16 -> b,c = 16 each, no new freezes.
items = [("a", 0, 100), ("b", 200, 100), ("c", 400, 100)]
result = fit_axis(items, target_dim=100, min_sizes={"a": 60, "b": 1, "c": 1})
assert result["a"]["size"] == 60, f"frozen at its own minimum, got {result['a']['size']}"
assert result["b"]["size"] == 16 and result["c"]["size"] == 16, result
assert (result["a"]["pos"], result["b"]["pos"], result["c"]["pos"]) == (0, 64, 84), result
assert result["c"]["pos"] + result["c"]["size"] == 100, "packs to exactly target_dim"
assert abs(result["a"]["scale"] - 0.6) < 1e-9, "a frozen item reports its OWN ratio"
assert abs(result["b"]["scale"] - 0.16) < 1e-9, result["b"]["scale"]
print("hand-traced freeze example (60/16/16, packed to exactly 100): OK")

# --- No item needs freezing -> identical to plain Tier 3 (regression guard) ---------
items = [("a", 0, 100), ("b", 200, 100), ("c", 400, 100)]
legacy = fit_axis(items, target_dim=200)
with_mins = fit_axis(items, target_dim=200, min_sizes={"a": 10, "b": 10, "c": 10})
assert legacy == with_mins, f"no freeze must match legacy exactly\n{legacy}\n{with_mins}"
print("no-freeze case matches legacy output exactly: OK")

# --- Omitting min_sizes entirely reproduces today's exact output --------------------
# (Crowded enough that the flat 1px floor and the iterative algorithm would genuinely
# disagree -- the legacy branch must not change.)
items = [("a", 0, 100), ("b", 200, 100), ("c", 400, 100)]
before = fit_axis(items, target_dim=10)   # available_for_sizes = 2 over 300
assert [before[i]["size"] for i in "abc"] == [1, 1, 1], before
assert all(abs(before[i]["scale"] - 2 / 300) < 1e-9 for i in "abc"), "flat group scale"
print("legacy branch (min_sizes omitted) unchanged, 1px floor + flat scale: OK")

# --- Unsatisfiable: every minimum together doesn't fit -> AxisFitError --------------
try:
    fit_axis(items, target_dim=100, min_sizes={"a": 60, "b": 60, "c": 60})
except AxisFitError as e:
    assert "minimum size" in str(e), f"error must name the new cause, got {e!r}"
    print(f"unsatisfiable minimums raise AxisFitError: OK ({e})")
else:
    raise AssertionError("expected AxisFitError when sum(mins) > available_for_sizes")

# --- Cascading freeze: freezing one item pushes a second under its own floor --------
# 4 items, sizes 100/100/100/100, target 250 -> available = 250 - 3*4 = 238.
# Round 1: scale .595 -> a (min 100) freezes. Round 2: free 138/300 = .46 -> b (min 50)
# freezes. Round 3: free 88/200 = .44 -> c,d = 44 each, no more freezes.
items4 = [("a", 0, 100), ("b", 200, 100), ("c", 400, 100), ("d", 600, 100)]
r = fit_axis(items4, target_dim=250, min_sizes={"a": 100, "b": 50, "c": 1, "d": 1})
assert r["a"]["size"] == 100 and r["b"]["size"] == 50, r
assert r["c"]["size"] == 44 and r["d"]["size"] == 44, r
assert r["d"]["pos"] + r["d"]["size"] <= 250, "must still fit target_dim"
print("cascading freeze (a then b, c/d absorb the rest): OK")

# --- Shrink-only clamp: a floor above the item's own size never grows it ------------
# `b` is 20px in the source but its component type's floor is 60 -- Tier 3 must leave
# it at (or below) 20, never inflate it, and the pre-check must not reject the axis.
items = [("a", 0, 100), ("b", 200, 20), ("c", 400, 100)]
r = fit_axis(items, target_dim=120, min_sizes={"a": 30, "b": 60, "c": 30})
assert r["b"]["size"] <= 20, f"an already-undersized item must never grow, got {r['b']}"
assert r["a"]["size"] >= 30 and r["c"]["size"] >= 30, r
assert r["c"]["pos"] + r["c"]["size"] <= 120, r
print("shrink-only clamp on an already-undersized item: OK")

# --- An id absent from the dict defaults to a floor of 1 (not the fallback) ---------
items = [("a", 0, 100), ("b", 200, 100)]
r = fit_axis(items, target_dim=80, min_sizes={"a": 60})
assert r["a"]["size"] == 60 and r["b"]["size"] == 16, r
print("id absent from min_sizes defaults to 1: OK")

# --- min_sizes={} is the dict branch, not the legacy branch, and still fits ---------
r = fit_axis(items, target_dim=80, min_sizes={})
assert r["b"]["pos"] + r["b"]["size"] <= 80, r
print("empty dict takes the dict branch without error: OK")

# --- Tiers 1/2 are unaffected by min_sizes -----------------------------------------
items = [("a", 800, 100), ("b", 950, 100)]  # span 250, fits 300 -> Tier 1
r = fit_axis(items, target_dim=300, min_sizes={"a": 999, "b": 999})
assert r["a"]["size"] == 100 and r["b"]["size"] == 100 and r["a"]["scale"] == 1.0
assert r["b"]["pos"] - (r["a"]["pos"] + r["a"]["size"]) == 50, "Tier 1 gap preserved"
print("Tier 1 ignores min_sizes entirely (nothing shrinks there): OK")

# --- Centering still applies on top of a frozen result ------------------------------
items = [("a", 0, 100), ("b", 200, 100), ("c", 400, 100)]
r = fit_axis(items, target_dim=140, min_sizes={"a": 40, "b": 40, "c": 40}, center=True)
left = min(v["pos"] for v in r.values())
right = 140 - max(v["pos"] + v["size"] for v in r.values())
assert abs(left - right) <= 1, f"centered result, got margins {left}/{right}"
print("centering composes with frozen sizes: OK")

print("\nTask 2: all assertions passed.")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python reflow_min_size_task2_fit_axis_test.py`
Expected: FAIL — `TypeError: fit_axis() got an unexpected keyword argument 'min_sizes'`

- [ ] **Step 3: Write minimal implementation**

3a. Change the signature (`generator/reflow.py:38-41`) to:

```python
def fit_axis(
    items: list[tuple[str, int, int]], target_dim: int, min_gap: int = 4,
    source_dim: int | None = None, center: bool | None = None,
    min_sizes: dict[str, int] | None = None,
) -> dict[str, dict]:
```

3b. Append this paragraph to `fit_axis`'s docstring, just before the closing `"""`:

```
    `min_sizes` -- ADDED 2026-09-10 (see docs/superpowers/specs/
    2026-09-10-reflow-min-size-design.md): {item_id: minimum size in px}, the floor
    Tier 3 may not scale that item below. `None` (the default, and what every legacy
    caller passes) runs the ORIGINAL one-shot Tier 3 verbatim -- deliberately a
    separate code path, not "the general path with every minimum defaulting to 1",
    because the two genuinely disagree: the one-shot formula floors each item
    independently at 1px and can therefore overshoot target_dim slightly, while the
    iterative algorithm reserves each frozen item's exact floor and recomputes the
    scale for the rest, so it doesn't. An actual dict (even empty) selects the
    iterative path; an id absent from it gets a floor of 1. Every floor is clamped to
    the item's OWN current size first, so Tier 3 stays shrink-only -- an item already
    below its component type's minimum (or a row whose derived floor exceeds its
    natural height) is left as-is rather than grown. `AxisFitError` if the floors
    can't all be satisfied at once. In the dict branch each item's reported "scale"
    is its OWN size ratio rather than one group-wide factor (a frozen item shrank
    less than its neighbours); the legacy branch satisfies that contract trivially,
    since uniform scaling makes every item's own ratio equal the group's.
```

3c. Replace the Tier 3 block (from `available_for_sizes = ...` to the final `return`)
with:

```python
    # --- Tier 3: scale-down, last resort, repacked at exactly min_gap -------------
    available_for_sizes = target_dim - (n - 1) * min_gap
    if min_sizes is None:
        # LEGACY PATH -- byte-for-byte today's code. Do not "unify" this with the
        # branch below (see the docstring): the two produce different, both-defensible
        # numbers, and every existing caller/test depends on this one.
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
        scales = [scale] * n
    else:
        # Clamp every floor to the item's own size: Tier 3 only ever shrinks, so an
        # item already below its type's minimum stays where it is instead of being
        # "frozen" bigger than it started (which would also make the pre-check below
        # reject axes that fit perfectly well today).
        mins = {
            item_id: min(max(1, int(min_sizes.get(item_id, 1))), max(1, size))
            for item_id, size in zip(ids, sizes)
        }
        total_min = sum(mins.values())
        if available_for_sizes < total_min:
            raise AxisFitError(
                f"target_dim {target_dim} can't fit the mandatory {min_gap}px floor gaps "
                f"AND every item's own minimum size ({total_min}px total) for {n} items"
            )
        # Flexbox-style shrink-with-minimum: freeze whoever would fall through their own
        # floor at the current uniform scale, reserve exactly that floor, redistribute
        # what's left over everyone still free, repeat. Terminates (each pass freezes at
        # least one of n items or stops) and can't go negative (the pre-check proved even
        # the all-frozen case fits).
        size_by_id = dict(zip(ids, sizes))
        frozen: dict[str, int] = {}
        free_ids = list(ids)
        free_available, free_total = available_for_sizes, total_size
        while free_total > 0:
            scale = free_available / free_total
            newly_frozen = [i for i in free_ids if size_by_id[i] * scale < mins[i]]
            if not newly_frozen:
                break
            for item_id in newly_frozen:
                frozen[item_id] = mins[item_id]
                free_available -= mins[item_id]
                free_total -= size_by_id[item_id]
            free_ids = [i for i in free_ids if i not in frozen]
        final_scale = free_available / free_total if free_total > 0 else 1.0
        new_sizes = [
            frozen[item_id] if item_id in frozen else max(1, int(size_by_id[item_id] * final_scale))
            for item_id in ids
        ]
        scales = [
            (new_size / size) if size else 1.0
            for new_size, size in zip(new_sizes, sizes)
        ]
    new_positions = [0]
    for size in new_sizes[:-1]:
        new_positions.append(new_positions[-1] + size + min_gap)
    result = {
        item_id: {"pos": pos, "size": size, "scale": item_scale}
        for item_id, pos, size, item_scale in zip(ids, new_positions, new_sizes, scales)
    }
    return _center_result(result, target_dim) if center else result
```

- [ ] **Step 4: Run the new test AND every existing reflow test**

```bash
cd C:\ClaudeProjects\ConstructUISkill2\generator\_test_output
python reflow_min_size_task2_fit_axis_test.py
for f in *_test.py; do echo "== $f"; python "$f" > /dev/null || echo "FAILED: $f"; done
```
Expected: the new test PASSES; no `FAILED:` line for any existing test (the backward-
compatibility guarantee — `fit_axis` is called by `stack_rows`, `_fit_group`, and four
existing test files directly).

- [ ] **Step 5: Commit**

```bash
git add generator/reflow.py generator/_test_output/reflow_min_size_task2_fit_axis_test.py
git commit -m "reflow: minimum-size-aware Tier 3 in fit_axis, legacy path untouched"
```

---

### Task 3: X-axis wiring — per-column floors in `_fit_group`

**Files:**
- Modify: `generator/reflow.py:589-612` (`_fit_group`'s X loop) + its docstring
- Test: `generator/_test_output/reflow_min_size_task3_x_axis_test.py` (new)

**Interfaces:**
- Consumes: `_component_min_size(sdk, tag, "width")` (Task 1); `fit_axis(..., min_sizes=...)` (Task 2).
- Produces: no new public names — `_fit_group`'s existing signature is unchanged;
  behavior changes only when its existing `sdk`/`id_to_tag` arguments are both supplied.

- [ ] **Step 1: Write the failing test**

Create `generator/_test_output/reflow_min_size_task3_x_axis_test.py`:

```python
"""Task 3: _fit_group derives each COLUMN's width floor (max over its members) and
hands it to fit_axis, so an X-axis Tier 3 squeeze can't scale a real component below
its own minimum. See docs/superpowers/specs/2026-09-10-reflow-min-size-design.md."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reflow import _fit_group, FALLBACK_MIN_SIZE_PX  # noqa: E402
from sdk import read_sdk  # noqa: E402

ui_sdk = read_sdk("2.18.0")
PATH = Path("Fake.cuig")

# One row of 4 wide buttons squeezed hard on X -> forces X-axis Tier 3 well under 30px.
elements = {
    f"b{i}": {"left": i * 210, "top": 0, "width": 200, "height": 100, "extra_vars": {}}
    for i in range(4)
}
id_to_tag = {eid: "ch5-button" for eid in elements}
warnings: list[str] = []
fitted = _fit_group(
    elements, target_width=160, target_height=400, source_width=1280, source_height=800,
    path=PATH, query="q", warnings=warnings, id_to_tag=id_to_tag, sdk=ui_sdk,
)
assert fitted is not None and warnings == [], (fitted, warnings)
widths = [fitted[f"b{i}"]["width"] for i in range(4)]
assert all(w >= FALLBACK_MIN_SIZE_PX for w in widths), f"floored at the fallback, got {widths}"
print(f"buttons floored at {FALLBACK_MIN_SIZE_PX}px wide instead of scaling away: OK {widths}")

# Legacy call (no sdk) must be untouched -- it still scales straight through the floor.
warnings = []
legacy = _fit_group(
    elements, target_width=160, target_height=400, source_width=1280, source_height=800,
    path=PATH, query="q", warnings=warnings,
)
assert legacy is not None and warnings == []
legacy_widths = [legacy[f"b{i}"]["width"] for i in range(4)]
assert min(legacy_widths) < FALLBACK_MIN_SIZE_PX, (
    f"legacy (no sdk) must keep today's unfloored behavior, got {legacy_widths}")
print(f"legacy no-sdk call unchanged: OK {legacy_widths}")

# A schema-published floor beats the fallback: a ch5-keypad's 210px minWidth.
elements = {
    "pad": {"left": 0, "top": 0, "width": 400, "height": 400, "extra_vars": {}},
    "b1": {"left": 500, "top": 0, "width": 200, "height": 100, "extra_vars": {}},
}
warnings = []
fitted = _fit_group(
    elements, target_width=420, target_height=500, source_width=1280, source_height=800,
    path=PATH, query="q", warnings=warnings,
    id_to_tag={"pad": "ch5-keypad", "b1": "ch5-button"}, sdk=ui_sdk,
)
assert fitted is not None and warnings == [], (fitted, warnings)
assert fitted["pad"]["width"] >= 210, f"keypad's schema floor, got {fitted['pad']['width']}"
assert fitted["b1"]["width"] >= FALLBACK_MIN_SIZE_PX, fitted["b1"]
right = max(v["left"] + v["width"] for v in fitted.values())
assert right <= 420, f"must still fit the canvas, got right={right}"
print(f"keypad floored at its own 210px schema minimum: OK ({fitted['pad']['width']}px)")

# Members of one column share the column's floor and its final left.
elements = {
    "up":   {"left": 0, "top": 0,   "width": 300, "height": 80, "extra_vars": {}},
    "down": {"left": 0, "top": 100, "width": 300, "height": 80, "extra_vars": {}},
    "side": {"left": 400, "top": 0, "width": 300, "height": 80, "extra_vars": {}},
}
warnings = []
fitted = _fit_group(
    elements, target_width=120, target_height=400, source_width=1280, source_height=800,
    path=PATH, query="q", warnings=warnings,
    id_to_tag={k: "ch5-button" for k in elements}, sdk=ui_sdk,
)
assert fitted is not None and warnings == [], (fitted, warnings)
assert fitted["up"]["left"] == fitted["down"]["left"], "a column travels together"
assert all(fitted[k]["width"] >= FALLBACK_MIN_SIZE_PX for k in elements), fitted
print("stacked column keeps a shared left and both members respect the floor: OK")

print("\nTask 3: all assertions passed.")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python reflow_min_size_task3_x_axis_test.py`
Expected: FAIL on the first assertion — widths come back below 30 because nothing floors
them yet.

- [ ] **Step 3: Write minimal implementation**

In `_fit_group`, replace the X loop's column-building and both `fit_axis` calls:

```python
    for columns, is_fragment in wrapped_rows:
        row_items = []
        col_min_sizes: dict[str, int] = {}
        for idx, column in enumerate(columns):
            col_key = f"__col{idx}"
            col_left, col_width = _column_bounds(column, elements)
            row_items.append((col_key, col_left, col_width))
            if sdk is not None and id_to_tag:
                tags = [id_to_tag.get(eid) for eid in column]
                if all(tags):
                    col_min_sizes[col_key] = max(_component_min_size(sdk, t, "width") for t in tags)
        # None, never {}, when there's no SDK: that selects fit_axis's untouched legacy
        # Tier 3 rather than the iterative path with every floor defaulted to 1 (the two
        # are NOT interchangeable -- see fit_axis's docstring).
        min_sizes = col_min_sizes if sdk is not None else None
        try:
            if is_fragment:
                col_fit = fit_axis(row_items, target_width, center=True, min_sizes=min_sizes)
            else:
                col_fit = fit_axis(row_items, target_width, source_dim=source_width, min_sizes=min_sizes)
        except AxisFitError as e:
            warnings.append(f"{path.name}: X axis for {query} -- {e}")
            return None
```

Then append to `_fit_group`'s docstring:

```
    ADDED 2026-09-10 (minimum-size floors, see docs/superpowers/specs/
    2026-09-10-reflow-min-size-design.md): when `sdk`/`id_to_tag` are given, each
    column contributes a width floor to its row's fit_axis call -- the MAX over its own
    members' `_component_min_size`, since the column's single fitted width has to
    satisfy every member. Known limitation, deliberate: members are then scaled by the
    column's own ratio, so a member much narrower than its column-mate could still land
    under its own floor; real columns are stacked pairs of equal width, so no shape this
    project has evidence for can hit that.
```

- [ ] **Step 4: Run the new test AND the full suite**

```bash
python reflow_min_size_task3_x_axis_test.py
for f in *_test.py; do echo "== $f"; python "$f" > /dev/null || echo "FAILED: $f"; done
```
Expected: new test PASSES, no `FAILED:` lines.

- [ ] **Step 5: Commit**

```bash
git add generator/reflow.py generator/_test_output/reflow_min_size_task3_x_axis_test.py
git commit -m "reflow: per-column width floors on the X axis"
```

---

### Task 4: Y-axis wiring — derived per-row floors in `stack_rows`

**Files:**
- Modify: `generator/reflow.py:317-390` (`stack_rows` signature, docstring, `fit_axis` call)
- Modify: `generator/reflow.py` (`_fit_group`'s single `stack_rows(...)` call — pass `id_to_tag`/`sdk` through)
- Test: `generator/_test_output/reflow_min_size_task4_y_axis_test.py` (new)

**Interfaces:**
- Consumes: `_component_min_size(sdk, tag, "height")` (Task 1); `fit_axis(..., min_sizes=...)` (Task 2).
- Produces: `stack_rows(rows, elements, target_height, min_gap=4, source_height=None, id_to_tag: dict[str, str] | None = None, sdk: UiSdk | None = None)`.
  Result shape unchanged: `{element_id: {"top": int, "height": int, "scale": float}}`.

- [ ] **Step 1: Write the failing test**

Create `generator/_test_output/reflow_min_size_task4_y_axis_test.py`:

```python
"""Task 4: stack_rows derives each ROW's height floor from its most-constrained member
(the member whose own minimum forces the largest row-level scale) and passes it into
the same minimum-aware Tier 3. See docs/superpowers/specs/2026-09-10-reflow-min-size-
design.md."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reflow import stack_rows, FALLBACK_MIN_SIZE_PX  # noqa: E402
from sdk import read_sdk  # noqa: E402

ui_sdk = read_sdk("2.18.0")

# Four rows of 100px-tall buttons squeezed far too hard on Y.
rows = [["a"], ["b"], ["c"], ["d"]]
elements = {
    eid: {"left": 0, "top": i * 150, "width": 200, "height": 100}
    for i, eid in enumerate(["a", "b", "c", "d"])
}
id_to_tag = {eid: "ch5-button" for eid in elements}

legacy = stack_rows(rows, elements, target_height=100)
assert min(v["height"] for v in legacy.values()) < FALLBACK_MIN_SIZE_PX, legacy
print(f"legacy (no sdk) still squeezes below the floor: OK "
      f"{[legacy[e]['height'] for e in 'abcd']}")

floored = stack_rows(rows, elements, target_height=160, id_to_tag=id_to_tag, sdk=ui_sdk)
heights = [floored[e]["height"] for e in "abcd"]
assert all(h >= FALLBACK_MIN_SIZE_PX for h in heights), f"floored at 30px, got {heights}"
bottom = max(v["top"] + v["height"] for v in floored.values())
assert bottom <= 160, f"must still fit target_height, got {bottom}"
print(f"buttons floored at {FALLBACK_MIN_SIZE_PX}px tall: OK {heights}")

# A row's floor comes from its MOST constrained member, expressed in row units:
# the dpad (min 100 on height, via minWidth) alone in a 300px row -> row floor 100.
rows = [["pad"], ["b1"], ["b2"]]
elements = {
    "pad": {"left": 0, "top": 0, "width": 300, "height": 300},
    "b1": {"left": 0, "top": 400, "width": 200, "height": 100},
    "b2": {"left": 0, "top": 550, "width": 200, "height": 100},
}
floored = stack_rows(
    rows, elements, target_height=200,
    id_to_tag={"pad": "ch5-dpad", "b1": "ch5-button", "b2": "ch5-button"}, sdk=ui_sdk,
)
assert floored["pad"]["height"] >= 100, f"dpad's schema floor, got {floored['pad']}"
assert floored["b1"]["height"] >= FALLBACK_MIN_SIZE_PX, floored["b1"]
assert floored["b2"]["height"] >= FALLBACK_MIN_SIZE_PX, floored["b2"]
bottom = max(v["top"] + v["height"] for v in floored.values())
assert bottom <= 200, f"must still fit target_height, got {bottom}"
print(f"dpad row floored at its own 100px minimum: OK ({floored['pad']['height']}px)")

# A multi-member row: the floor is set by whichever member hits its own minimum first.
# Row natural height 300 (the dpad); the 40px button's floor of 30 needs scale 0.75,
# the dpad's 100/300 only needs 0.33 -> the button decides, row floor = ceil(300*.75).
rows = [["pad", "small"]]
elements = {
    "pad": {"left": 0, "top": 0, "width": 300, "height": 300},
    "small": {"left": 400, "top": 100, "width": 100, "height": 40},
}
floored = stack_rows(
    rows, elements, target_height=180,
    id_to_tag={"pad": "ch5-dpad", "small": "ch5-button"}, sdk=ui_sdk,
)
assert floored["small"]["height"] >= FALLBACK_MIN_SIZE_PX, floored["small"]
assert max(v["top"] + v["height"] for v in floored.values()) <= 180
print("most-constrained member sets the row floor: OK")

# Shrink-only: a row already shorter than its derived floor is left alone, not grown.
rows = [["tiny"]]
elements = {"tiny": {"left": 0, "top": 0, "width": 100, "height": 10}}
r = stack_rows(rows, elements, target_height=200, id_to_tag={"tiny": "ch5-button"}, sdk=ui_sdk)
assert r["tiny"]["height"] == 10, f"never grow an already-tiny element, got {r['tiny']}"
print("already-undersized row is not grown: OK")

print("\nTask 4: all assertions passed.")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python reflow_min_size_task4_y_axis_test.py`
Expected: FAIL — `TypeError: stack_rows() got an unexpected keyword argument 'id_to_tag'`

- [ ] **Step 3: Write minimal implementation**

3a. Add `import math` to the imports at the top of `generator/reflow.py` (after `import re`).

3b. Change `stack_rows`' signature to:

```python
def stack_rows(
    rows: list[list[str]], elements: dict[str, dict], target_height: int, min_gap: int = 4,
    source_height: int | None = None, id_to_tag: dict[str, str] | None = None,
    sdk: "sdk_module.UiSdk | None" = None,
) -> dict[str, dict]:
```

3c. Append to `stack_rows`' docstring:

```
    `id_to_tag`/`sdk` -- ADDED 2026-09-10 (see docs/superpowers/specs/
    2026-09-10-reflow-min-size-design.md): when both are given, each row pseudo-item
    carries its own height floor into fit_axis's minimum-aware Tier 3. A row scales as
    ONE unit, so a member's own minimum has to be converted into row units first: the
    scale at which member m would hit its floor is `min_height(m) / m.height`, and the
    row can't go below `ceil(row_natural_height * max(that ratio over all members))` --
    the most constrained member decides. ceil, not round, because the member's own
    height is later derived back out with int() truncation, and rounding down here
    would let it land 1px under its floor. Omitting either argument passes
    `min_sizes=None` (never `{}`) to fit_axis -- the untouched legacy Tier 3, exactly
    today's behavior.
```

3d. Build the dict and pass it, replacing the existing `row_fit = fit_axis(...)` line:

```python
    row_min_sizes: dict[str, int] | None = None
    if sdk is not None and id_to_tag:
        row_min_sizes = {}
        for i, row in enumerate(rows):
            tags = [id_to_tag.get(eid) for eid in row]
            if not all(tags):
                continue  # partial tag info -- this row just gets the default floor of 1
            worst_ratio = 0.0
            for eid, tag in zip(row, tags):
                own_height = elements[eid]["height"]
                if own_height > 0:
                    worst_ratio = max(worst_ratio, _component_min_size(sdk, tag, "height") / own_height)
            if worst_ratio > 0:
                row_min_sizes[row_keys[i]] = max(1, math.ceil(natural_height[i] * worst_ratio))

    row_fit = fit_axis(
        row_items, target_height, min_gap=min_gap, source_dim=source_height,
        min_sizes=row_min_sizes,
    )
```

3e. In `_fit_group`, pass the two arguments through to its existing `stack_rows` call:

```python
        y_fit = stack_rows(
            row_lists, elements, target_height, source_height=source_height,
            id_to_tag=id_to_tag, sdk=sdk,
        )
```

- [ ] **Step 4: Run the new test AND the full suite**

```bash
python reflow_min_size_task4_y_axis_test.py
for f in *_test.py; do echo "== $f"; python "$f" > /dev/null || echo "FAILED: $f"; done
```
Expected: new test PASSES, no `FAILED:` lines.

- [ ] **Step 5: Commit**

```bash
git add generator/reflow.py generator/_test_output/reflow_min_size_task4_y_axis_test.py
git commit -m "reflow: derived per-row height floors on the Y axis"
```

---

### Task 5: End-to-end + real-file verification + README

**Files:**
- Test: `generator/_test_output/reflow_min_size_task5_end_to_end_test.py` (new)
- Modify: `README.md` (Current phase + Log entry)

**Interfaces:**
- Consumes: `reflow_file(path, target_resolution, source_resolution, mode, sdk)` — unchanged signature.
- Produces: nothing new.

- [ ] **Step 1: Write the failing test**

Create `generator/_test_output/reflow_min_size_task5_end_to_end_test.py`:

```python
"""Task 5: end-to-end through reflow_file -- replays the real reported shape (found
2026-09-10 live-testing TSW-570/640x360 in Construct: real buttons scaled to 28px
tall, too small to use). Two runs of the same file: without an SDK (today's behavior,
buttons go under the floor) and with one (every button/dpad respects its own minimum,
nothing overlaps, everything still fits the canvas)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))

from reflow import reflow_file, FALLBACK_MIN_SIZE_PX, _rects_overlap  # noqa: E402
from devices import ORIENTATION_ENUM  # noqa: E402
from sdk import read_sdk  # noqa: E402
import layout  # noqa: E402
import compare  # noqa: E402

OUT = Path(__file__).resolve().parent / "ReflowMinSizeE2E"
OUT.mkdir(parents=True, exist_ok=True)
ui_sdk = read_sdk("2.18.0")

source = {"width": 1280, "height": 800, "orientation": ORIENTATION_ENUM["landscape"]}
target = {"width": 640, "height": 360, "orientation": ORIENTATION_ENUM["landscape"]}
source_query = layout.orientation_media_query("landscape", 1280, 800)
target_query = layout.orientation_media_query("landscape", 640, 360)

# Five rows of buttons plus a dpad -- crowded enough on Y that Tier 3 has to scale.
BUTTONS = [(f"b{r}{c}", 40 + c * 220, 30 + r * 120) for r in range(5) for c in range(3)]
html = "".join(f'<ch5-button id="{eid}" size="custom"></ch5-button>' for eid, _, _ in BUTTONS)
html += '<ch5-dpad id="pad" size="custom"></ch5-dpad>'
rules = "".join(
    f"#{eid}{{display: block; left: {left}px; top: {top}px; position: absolute; "
    f"width: 200px; height: 100px;}}"
    for eid, left, top in BUTTONS
)
rules += ("#pad{display: block; left: 900px; top: 30px; position: absolute; "
          "width: 300px; height: 300px; --ch5-dpad--regular-size: 300px;}")
css = f"@media {source_query}{{{rules}}}"
toml = "".join(
    f'\n[[Elements]]\nType = "Ch5 Button"\nEditable = true\n\n'
    f'[Elements.Attributes]\nid = "{eid}"\nsize = "custom"\n' for eid, _, _ in BUTTONS
) + '\n[[Elements]]\nType = "Ch5 Dpad"\nEditable = true\n\n[Elements.Attributes]\nid = "pad"\nsize = "custom"\n'


def make_file(path: Path) -> None:
    path.write_text(
        "{FileMetadata}\nSchema = \"1.0.0.0\"\n"
        f"\n{{Html}}\n{html}\n"
        f"\n{{Css}}\n{css}\n"
        f"\n{{PageAttributes}}\n\n[Attributes]\nName = \"P\"\n{toml}",
        encoding="utf-8",
    )


def fitted_for(path: Path) -> dict:
    new_css = compare.parse_file(path).sections[2][2]
    block = layout.find_media_block(new_css, target_query)
    assert block is not None, "target block missing"
    return layout.parse_position_rules(block)


# --- Without an SDK: today's behavior, buttons squeezed under the floor -------------
legacy_path = OUT / "NoSdk.cuig"
make_file(legacy_path)
result = reflow_file(legacy_path, target_resolution=target, source_resolution=source, mode="pin_existing")
assert result.warnings == [], result.warnings
legacy_heights = [v["height"] for k, v in fitted_for(legacy_path).items() if k != "pad"]
assert min(legacy_heights) < FALLBACK_MIN_SIZE_PX, (
    f"the bug being fixed: buttons squeezed below {FALLBACK_MIN_SIZE_PX}px, got {min(legacy_heights)}")
print(f"reproduced the reported bug without an SDK: min button height {min(legacy_heights)}px")

# --- With the SDK: every component respects its own floor ---------------------------
path = OUT / "MinSize.cuig"
make_file(path)
result = reflow_file(path, target_resolution=target, source_resolution=source, mode="pin_existing", sdk=ui_sdk)
assert result.warnings == [], f"expected no warnings, got {result.warnings}"
assert compare.round_trip_check(path)

fitted = fitted_for(path)
assert set(fitted) == {eid for eid, _, _ in BUTTONS} | {"pad"}, sorted(fitted)
heights = {k: v["height"] for k, v in fitted.items() if k != "pad"}
assert min(heights.values()) >= FALLBACK_MIN_SIZE_PX, (
    f"every button must clear the {FALLBACK_MIN_SIZE_PX}px floor, got "
    f"{sorted(heights.items(), key=lambda kv: kv[1])[:3]}")
assert fitted["pad"]["height"] >= 100 and fitted["pad"]["width"] >= 100, fitted["pad"]
print(f"with the SDK: min button height {min(heights.values())}px, dpad "
      f"{fitted['pad']['width']}x{fitted['pad']['height']}")

# --- Still a valid layout: on-canvas, no overlaps, vars match their boxes -----------
for eid, box in fitted.items():
    assert box["left"] >= 0 and box["top"] >= 0, (eid, box)
    assert box["left"] + box["width"] <= 640, (eid, box)
    assert box["top"] + box["height"] <= 360, (eid, box)
ids = sorted(fitted)
for i, a in enumerate(ids):
    for b in ids[i + 1:]:
        assert not _rects_overlap(fitted[a], fitted[b]), f"{a} overlaps {b}: {fitted[a]} {fitted[b]}"
for eid, box in fitted.items():
    for name, value in (box.get("extra_vars") or {}).items():
        lname = name.lower()
        if "width" in lname:
            assert value == f"{box['width']}px", (eid, name, value, box)
        elif "height" in lname:
            assert value == f"{box['height']}px", (eid, name, value, box)
assert (fitted["pad"].get("extra_vars") or {}).get("--ch5-dpad--regular-size") == f"{fitted['pad']['width']}px", fitted["pad"]
print("on-canvas, zero overlaps, every size var matches its own box: OK")

print("\nTask 5: all assertions passed.")
```

- [ ] **Step 2: Run the test**

Run: `python reflow_min_size_task5_end_to_end_test.py`
Expected: PASS once Tasks 1-4 are complete. If it fails on the "reproduced the reported
bug" assertion, the synthetic shape isn't crowded enough — add rows (`range(5)` →
`range(6)`) until the no-SDK run genuinely squeezes below 30px, so the test is a real
guard rather than a tautology.

- [ ] **Step 3: Verify against the real project files**

The standing practice for reflow work (see README): re-run the real `GenTestProject2`
pages so the user can check them in Construct. Back them up first, then re-fit with
`mode="full_refit"` (NOT `add_resolutions_to_project`, which would duplicate the
already-added TSW-570 resolution).

```bash
cp -r "/c/Solutions/ClaudeGenTest/GenTestProject2" "$SCRATCH/GenTestProject2.bak"
```

Then run this from `generator/` (scratch script, not committed):

```python
import sys; sys.path.insert(0, ".")
from pathlib import Path
from reflow import reflow_file, _component_min_size, _tag_index, _read_sections
from sdk import read_sdk
from devices import ORIENTATION_ENUM
import layout

ui_sdk = read_sdk("2.18.0")
src = {"width": 1280, "height": 800, "orientation": ORIENTATION_ENUM["landscape"]}
tgt = {"width": 640, "height": 360, "orientation": ORIENTATION_ENUM["landscape"]}
proj = Path(r"C:\Solutions\ClaudeGenTest\GenTestProject2")
for f in ["ReflowTest.cuig", "ButtonVariants.cuig", "MainPage.cuig", "MyWidget.cuiw"]:
    p = proj / f
    r = reflow_file(p, target_resolution=tgt, source_resolution=src, mode="full_refit", sdk=ui_sdk)
    print(f, "warnings:", r.warnings or "(none)")
    _, sections = _read_sections(p)
    html = next((t for n, _, t in sections if n == "Html"), "")
    tags = {eid: v[0] for eid, v in _tag_index(html).items()}
    css = next(t for n, _, t in sections if n == "Css")
    block = layout.find_media_block(css, layout.orientation_media_query("landscape", 640, 360))
    if not block:
        continue
    fitted = layout.parse_position_rules(block)
    under = [(eid, b["width"], b["height"]) for eid, b in fitted.items()
             if b["width"] < _component_min_size(ui_sdk, tags.get(eid, ""), "width")
             or b["height"] < _component_min_size(ui_sdk, tags.get(eid, ""), "height")]
    ids = sorted(fitted)
    over = [(a, b) for i, a in enumerate(ids) for b in ids[i+1:]
            if not (fitted[a]["left"] + fitted[a]["width"] <= fitted[b]["left"]
                    or fitted[b]["left"] + fitted[b]["width"] <= fitted[a]["left"]
                    or fitted[a]["top"] + fitted[a]["height"] <= fitted[b]["top"]
                    or fitted[b]["top"] + fitted[b]["height"] <= fitted[a]["top"])]
    print("  elements:", len(fitted), "| under their own floor:", under or "none",
          "| overlaps:", over or "none",
          "| max right:", max(b["left"] + b["width"] for b in fitted.values()),
          "| max bottom:", max(b["top"] + b["height"] for b in fitted.values()))
```

Expected: zero warnings, "under their own floor: none" for every file (an element whose
SOURCE size is already below its floor is the one legitimate exception — clamped,
shrink-only, so it can legitimately appear here; call it out explicitly rather than
ignoring it), zero overlaps, max right ≤ 640 and max bottom ≤ 360. Record the actual
before/after button height (28px is the baseline to beat) for the README.

If any file reports an `AxisFitError` warning, that's a real regression of this change
(the whole block would be skipped) — lower `FALLBACK_MIN_SIZE_PX` only as a last resort,
and report the tradeoff rather than silently tuning it away.

- [ ] **Step 4: Run the complete suite one final time**

```bash
cd C:\ClaudeProjects\ConstructUISkill2\generator\_test_output
for f in *_test.py; do echo "== $f"; python "$f" > /dev/null || echo "FAILED: $f"; done
```
Expected: no `FAILED:` lines across all test files (19 existing + 5 new).

- [ ] **Step 5: Update README and commit**

Add a new **Current phase** entry at the top of `README.md` (demoting the current one),
covering: the reported 28px symptom, the two-source floor model (SDK `minSizes` vs.
`FALLBACK_MIN_SIZE_PX`), the three spec amendments found while planning (int/unit-less
schema values, per-axis `minHeight`, the shrink-only clamp), the freeze-and-redistribute
algorithm, the deliberate legacy/dict two-path split, the measured before/after numbers
from Step 3, and **Next**: user re-checks TSW-570 in Construct.

```bash
git add README.md generator/_test_output/reflow_min_size_task5_end_to_end_test.py
git commit -m "reflow: end-to-end minimum-size test, verified against the real TSW-570 block"
```
