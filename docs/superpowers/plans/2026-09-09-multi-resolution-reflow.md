# Multi-resolution reflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make adding a resolution (or adding new controls to an already-multi-resolution
page) automatically produce a correctly-positioned `@media` block for every resolution
that's missing it, instead of leaving components off-canvas, absent, or needlessly
shrunk when there's room to wrap them onto a new line instead.

**Architecture:** A new `generator/reflow.py` module implements per-axis fitting that is
no longer symmetric between axes: **X** gets a 4-tier fallback (move, then **wrap**
overflowing rows onto new rows below, then compact whitespace, then scale down) and
**Y** keeps a 3-tier fallback (move, compact, scale) but operates on **rows** (inferred
from source Y-overlap) instead of individual elements. Two modes (`pin_existing`
default, `full_refit`) sit on top of the same fitter. This builds on two new low-level
CSS parsing/building helpers added to the existing `generator/layout.py`.
`generator/project.py::add_resolutions_to_project` is extended to call it automatically;
a second call site (the skill layer, when adding new elements to an existing
multi-resolution page) is documented but not implemented here — it just needs to call
the same `reflow_file`, per the spec's Integration section.

**Tech Stack:** Python 3.11+ (stdlib only: `re`, `dataclasses`, `pathlib`). No new
dependencies. Tests are plain assert-script files run directly with `python`, matching
every existing `generator/_test_output/phaseN_smoke_test.py` in this repo — this project
does not use pytest.

**Spec:** `docs/superpowers/specs/2026-09-08-multi-resolution-reflow-design.md`
(this plan supersedes `docs/superpowers/plans/2026-09-08-multi-resolution-reflow.md`,
which was written against the design before the row-wrap tier was added — that file is
now stale, superseded by this one)

## Global Constraints

- Minimum visual gap between neighboring elements/rows on an axis is **4px** (tiers 2
  and 3, and the gap between stacked rows).
- Elements are grouped into **rows** by source Y-overlap (`detect_rows`) before any
  fitting happens. Only an overflowing row may split (the wrap tier); elements never
  reorder within a row or across rows — reading order (top-to-bottom, then
  left-to-right within a row) is always preserved. Full 2D bin-packing/rearrangement
  and column-wrap (the height-constrained mirror of row-wrap) are both out of scope.
- Fitting is per-axis but asymmetric: **X** runs 4 tiers per row (move → wrap → compact
  → scale); **Y** runs the original 3 tiers (move → compact → scale) on the row list
  once wrapping has settled row membership, not on individual elements.
- A row created by an X-axis wrap split shares its original source `top` with the row
  it split from (splitting doesn't move anything vertically by itself) — `stack_rows`
  must use a **pre-stacked anchor**, not each row's raw `min(top)`, or two sibling rows
  can tie and overlap on Y. See Task 6 and the spec's Y axis section.
- No tier may cause an element's (or row's) on-axis gap to a same-tier neighbor to go
  negative, and nothing may reorder relative to a same-group neighbor — this is what
  the spec's no-new-overlap proof depends on. Do not "optimize" this away.
- `pin_existing` mode never modifies a pinned (pre-existing) element's parsed values.
  Overlap between a newly-fit element and a pinned element is reported, never silently
  accepted and never blocks the write.
- Every new fact confirmed from `C:\Git\CCIDE` source during this plan must be written
  into `docs/architecture/10-reflow.md` in the same task that confirms it — this
  project's established practice (see `01-index.md` and every prior phase's log entry).
- Round-trip every file this code touches through `harness/compare.py::round_trip_check`
  in tests — this project's standing verification requirement (see `README.md`).

---

## Task 1: Confirm and add `orientation_media_query` (portrait formula)

Adds the one CSS formula the whole feature depends on for anything portrait, which was
flagged unconfirmed project-wide until now. Confirmed by reading
`C:\Git\CCIDE\Crestron.IDE\Projects\UiEditor\PageDesigner\PageDesigner.Server\JS\src\pd-utils\src\breakpoint.ts`'s
`createRawQuery(devOrientation, devWidth, devHeight)`, and cross-checked against two real
files: `C:\Git\CCIDE\CrestronConstruct_RIDE\Solutions\MySolution\SolutionCCIDE5225\Bug_CCIDE_5225_Widget2.cuiw`
and `...Widget5.cuiw`, both containing:
```
@media (orientation: portrait) and (max-height: 1323px) and (max-width: 1025px), (orientation: portrait) and (max-height: 1321px) { ... }
```
for a 1024×1322 portrait resolution — i.e. `(max-height: H+1px) and (max-width: W+1px), (max-height: H-1px)`, the same `±1` pattern as landscape but with height leading and being the sole clause in the second alternative (source's `createRawQuery` confirms this exactly, branching only on which dimension leads and which one appears alone).

**Files:**
- Modify: `generator/layout.py`
- Create: `docs/architecture/10-reflow.md`
- Test: `generator/_test_output/reflow_task1_media_query_test.py`

**Interfaces:**
- Produces: `orientation_media_query(orientation: str, width: int, height: int) -> str`
  (orientation is `"landscape"` or `"portrait"`). `landscape_media_query(width, height)`
  keeps its existing signature/behavior, now implemented as a thin wrapper.

- [ ] **Step 1: Write the failing test**

```python
# generator/_test_output/reflow_task1_media_query_test.py
"""Task 1: orientation_media_query, confirmed against breakpoint.ts::createRawQuery and
two real portrait sample files (Bug_CCIDE_5225_Widget2.cuiw / Widget5.cuiw)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from layout import orientation_media_query, landscape_media_query  # noqa: E402

# Real confirmed landscape formula, unchanged (existing behavior must not regress).
assert landscape_media_query(1280, 800) == orientation_media_query("landscape", 1280, 800)
assert orientation_media_query("landscape", 1280, 800) == (
    "(orientation: landscape) and (max-width: 1281px) and (max-height: 801px), "
    "(orientation: landscape) and (max-width: 1279px)"
)

# Real confirmed portrait formula (1024x1322, from the two real .cuiw files above).
assert orientation_media_query("portrait", 1024, 1322) == (
    "(orientation: portrait) and (max-height: 1323px) and (max-width: 1025px), "
    "(orientation: portrait) and (max-height: 1321px)"
)

print("TASK 1: orientation_media_query -- landscape unchanged, portrait confirmed. PASSED")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python generator/_test_output/reflow_task1_media_query_test.py`
Expected: `ImportError: cannot import name 'orientation_media_query'`

- [ ] **Step 3: Implement**

In `generator/layout.py`, replace the existing `landscape_media_query` function with:

```python
def orientation_media_query(orientation: str, width: int, height: int) -> str:
    """Device-specific breakpoint for a WxH resolution in the given orientation.
    Confirmed against C:\\Git\\CCIDE's breakpoint.ts::createRawQuery (the real
    client-side source that generates these) and cross-checked against two real
    portrait sample files (Bug_CCIDE_5225_Widget2.cuiw / Widget5.cuiw, both
    1024x1322): landscape leads with max-width, portrait leads with max-height --
    same +-1px pattern either way, just which dimension is named first/alone differs.
    See docs/architecture/10-reflow.md for the full derivation."""
    if orientation == "landscape":
        return (
            f"(orientation: landscape) and (max-width: {width + 1}px) and (max-height: {height + 1}px), "
            f"(orientation: landscape) and (max-width: {width - 1}px)"
        )
    elif orientation == "portrait":
        return (
            f"(orientation: portrait) and (max-height: {height + 1}px) and (max-width: {width + 1}px), "
            f"(orientation: portrait) and (max-height: {height - 1}px)"
        )
    else:
        raise ValueError(f"unsupported orientation {orientation!r} -- expected 'landscape' or 'portrait'")


def landscape_media_query(width: int, height: int) -> str:
    """Confirmed formula (see module docstring) -- device-specific landscape breakpoint
    for a WxH primary landscape resolution. Kept as a thin wrapper so existing callers
    (page.py, this module's own build_position_css) are unaffected."""
    return orientation_media_query("landscape", width, height)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python generator/_test_output/reflow_task1_media_query_test.py`
Expected: `TASK 1: ... PASSED`

- [ ] **Step 5: Also run the existing Phase 4/5 smoke tests to confirm no regression**

Run: `python generator/_test_output/phase4_smoke_test.py && python generator/_test_output/phase5_smoke_test.py`
Expected: both print their existing `ALL CHECKS PASSED` / final success lines, unchanged.

- [ ] **Step 6: Write the architecture doc**

Create `docs/architecture/10-reflow.md` with this content:

```markdown
# Multi-resolution reflow

Source-grounded confirmations for `docs/superpowers/specs/2026-09-08-multi-resolution-reflow-design.md`.

## Portrait media-query formula (previously unconfirmed project-wide)

Confirmed by reading `C:\Git\CCIDE\Crestron.IDE\Projects\UiEditor\PageDesigner\
PageDesigner.Server\JS\src\pd-utils\src\breakpoint.ts`'s `createRawQuery(devOrientation,
devWidth, devHeight)` -- the real client-side TypeScript source that generates these
breakpoints (same file/method family as the already-confirmed landscape formula).
Cross-checked against two real portrait sample files elsewhere in the CCIDE repo
(`CrestronConstruct_RIDE\Solutions\MySolution\SolutionCCIDE5225\Bug_CCIDE_5225_Widget2.cuiw`
and `...Widget5.cuiw`, both a 1024x1322 portrait resolution) -- source and samples agree
exactly:

```
(orientation: portrait) and (max-height: {H+1}px) and (max-width: {W+1}px), (orientation: portrait) and (max-height: {H-1}px)
```

Same `+-1px` shape as the already-confirmed landscape formula, just with height leading
(and being the sole clause in the second alternative) instead of width -- `createRawQuery`
branches on orientation only to decide which dimension leads, not on any other logic.
`generator/layout.py::orientation_media_query` implements both branches;
`landscape_media_query` is now a thin wrapper for backward compatibility.
```

- [ ] **Step 7: Commit**

```bash
git add generator/layout.py generator/_test_output/reflow_task1_media_query_test.py docs/architecture/10-reflow.md
git commit -m "$(cat <<'EOF'
Reflow task 1: confirm portrait media-query formula

Reads C:\Git\CCIDE\...\breakpoint.ts::createRawQuery directly and cross-
checks against two real portrait sample files, resolving a gap flagged
unconfirmed since Phase 4 (layout.py's own docstring, 04-ch5-schema.md).
orientation_media_query(orientation, width, height) generalizes the
existing landscape_media_query, kept as a thin wrapper.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01Nw79wQq7o3YvzNBtP5GiEV
EOF
)"
```

---

## Task 2: CSS block parsing/building helpers

**Files:**
- Modify: `generator/layout.py`
- Test: `generator/_test_output/reflow_task2_parse_build_test.py`

**Interfaces:**
- Consumes: `orientation_media_query` (Task 1).
- Produces:
  - `find_media_block_span(css_text: str, query: str) -> tuple[int, int] | None` —
    `(start, end)` char indices of the whole `@media {query}{...}` block (brace-depth
    matched), or `None` if no block with that exact query string exists.
  - `find_media_block(css_text: str, query: str) -> str | None` — the block's inner
    content only (between its outer braces), or `None`.
  - `parse_position_rules(block_css: str) -> dict[str, dict]` — `{element_id: {"left":
    int, "top": int, "width": int, "height": int, "z_index": int | None, "extra_vars":
    dict[str, str]}}`, parsed from one block's flat `#id{...}` rules only (nested/child
    selectors like the theme-selector rule are structurally excluded — see Step 3).
  - `build_reflow_block(elements: dict[str, dict], orientation: str, width: int, height: int) -> str`
    — one `@media {orientation_media_query(...)}{...}` block with one `#id{...}` rule
    per element (device-specific shape: no `z-index`, matching `build_position_css`'s
    existing device block).

- [ ] **Step 1: Write the failing test**

```python
# generator/_test_output/reflow_task2_parse_build_test.py
"""Task 2: find_media_block(_span)/parse_position_rules/build_reflow_block."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from layout import (  # noqa: E402
    find_media_block, find_media_block_span, parse_position_rules, build_reflow_block,
    orientation_media_query,
)

CSS = (
    '@media (max-width: 99999px){'
    '#i1{display: block; left: 10px; top: 20px; position: absolute; z-index: 1; width: 100px; height: 50px; --ch5-button--regular-width: 100px; --ch5-button--regular-height: 50px;}'
    '#i1 .ch5-button :not(i):not(svg) {font-family: "Roboto";}'
    '#i2{display: block; left: 200px; top: 20px; position: absolute; z-index: 2; width: 80px; height: 40px;}'
    '}'
    '@media (orientation: landscape) and (max-width: 1281px) and (max-height: 801px), (orientation: landscape) and (max-width: 1279px){'
    '#i1{display: block; left: 10px; top: 20px; position: absolute; width: 100px; height: 50px;}'
    '}'
)

# find_media_block(_span) locates by exact query string.
catch_all_query = "(max-width: 99999px)"
span = find_media_block_span(CSS, catch_all_query)
assert span is not None and CSS[span[0]:span[1]].startswith("@media (max-width: 99999px){")
block = find_media_block(CSS, catch_all_query)
assert block is not None and block.startswith("#i1{") and block.endswith("}")
missing = find_media_block(CSS, "(orientation: portrait) and (max-height: 999px)")
assert missing is None

# parse_position_rules: only the two flat #id{} rules, NOT the theme-selector rule.
elements = parse_position_rules(block)
assert set(elements) == {"i1", "i2"}, f"theme-selector rule leaked into result: {elements}"
assert elements["i1"] == {
    "left": 10, "top": 20, "width": 100, "height": 50, "z_index": 1,
    "extra_vars": {"--ch5-button--regular-width": "100px", "--ch5-button--regular-height": "50px"},
}
assert elements["i2"] == {"left": 200, "top": 20, "width": 80, "height": 40, "z_index": 2, "extra_vars": {}}

# device-specific block found by its landscape query has no extra_vars/z-index issue either.
device_block = find_media_block(CSS, orientation_media_query("landscape", 1280, 800))
assert device_block == "#i1{display: block; left: 10px; top: 20px; position: absolute; width: 100px; height: 50px;}"

# build_reflow_block: matches the shape of a real device block -- no z-index, extra_vars carried.
built = build_reflow_block(
    {"i1": {"left": 5, "top": 6, "width": 100, "height": 50, "z_index": 1, "extra_vars": {"--x": "100px"}}},
    "portrait", 1024, 1322,
)
assert built == (
    f"@media {orientation_media_query('portrait', 1024, 1322)}"
    "{#i1{display: block; left: 5px; top: 6px; position: absolute; width: 100px; height: 50px; --x: 100px;}}"
)

print("TASK 2: CSS block parsing/building. PASSED")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python generator/_test_output/reflow_task2_parse_build_test.py`
Expected: `ImportError: cannot import name 'find_media_block_span'`

- [ ] **Step 3: Implement**

Append to `generator/layout.py`:

```python
import re

_FLAT_RULE_RE = re.compile(r"#(?P<id>[A-Za-z0-9_]+)\{(?P<decls>[^{}]*)\}")


def find_media_block_span(css_text: str, query: str) -> tuple[int, int] | None:
    """(start, end) char indices of the whole `@media {query}{...}` block, brace-depth
    matched since the inner rules themselves contain braces (a plain regex can't find
    the correct closing brace). None if no block with this exact query exists."""
    needle = f"@media {query}{{"
    start = css_text.find(needle)
    if start == -1:
        return None
    open_brace = start + len(needle) - 1
    depth = 0
    for i in range(open_brace, len(css_text)):
        if css_text[i] == "{":
            depth += 1
        elif css_text[i] == "}":
            depth -= 1
            if depth == 0:
                return start, i + 1
    raise ValueError(f"unterminated @media block for query {query!r}")


def find_media_block(css_text: str, query: str) -> str | None:
    """Inner content of the `@media {query}{...}` block (between its outer braces)."""
    span = find_media_block_span(css_text, query)
    if span is None:
        return None
    start, end = span
    open_brace = css_text.index("{", start)
    return css_text[open_brace + 1:end - 1]


def parse_position_rules(block_css: str) -> dict[str, dict]:
    """Parse one block's flat `#id{...}` rules into position/size dicts. The regex
    requires `{` immediately after the id -- a nested/child selector like
    `#id .ch5-button :not(i):not(svg) {...}` has a space before its `{`, so it never
    matches here and is correctly left alone (it carries no position data)."""
    elements: dict[str, dict] = {}
    for m in _FLAT_RULE_RE.finditer(block_css):
        decls: dict[str, str] = {}
        for decl in m.group("decls").split(";"):
            decl = decl.strip()
            if not decl or ":" not in decl:
                continue
            key, _, value = decl.partition(":")
            decls[key.strip()] = value.strip()
        if "left" not in decls or "width" not in decls:
            continue
        extra_vars = {k: v for k, v in decls.items() if k.startswith("--")}
        elements[m.group("id")] = {
            "left": int(decls["left"].rstrip("px")),
            "top": int(decls["top"].rstrip("px")),
            "width": int(decls["width"].rstrip("px")),
            "height": int(decls["height"].rstrip("px")),
            "z_index": int(decls["z-index"]) if "z-index" in decls else None,
            "extra_vars": extra_vars,
        }
    return elements


def build_reflow_block(elements: dict[str, dict], orientation: str, width: int, height: int) -> str:
    """One @media block, one flat #id{} rule per element -- same device-specific shape
    build_position_css already produces (no z-index), generalized to N elements."""
    query = orientation_media_query(orientation, width, height)
    rules = []
    for element_id, e in elements.items():
        extra_decls = "".join(f" {name}: {value};" for name, value in e.get("extra_vars", {}).items())
        rules.append(
            f"#{element_id}{{display: block; left: {e['left']}px; top: {e['top']}px; "
            f"position: absolute; width: {e['width']}px; height: {e['height']}px;{extra_decls}}}"
        )
    return f"@media {query}{{{''.join(rules)}}}"
```

Add `from __future__ import annotations` stays at top (already present); move the new
`import re` to the top of the file alongside existing imports rather than inline.

- [ ] **Step 4: Run test to verify it passes**

Run: `python generator/_test_output/reflow_task2_parse_build_test.py`
Expected: `TASK 2: ... PASSED`

- [ ] **Step 5: Commit**

```bash
git add generator/layout.py generator/_test_output/reflow_task2_parse_build_test.py
git commit -m "$(cat <<'EOF'
Reflow task 2: CSS block parse/find/build helpers in layout.py

find_media_block_span/find_media_block locate one @media block by its
exact query string (brace-depth matched, since inner rules contain
braces). parse_position_rules reads a block's flat #id{} rules back into
the per-element dict shape the reflow algorithm operates on -- nested
selectors (theme rules) are structurally excluded by requiring '{'
immediately after the id. build_reflow_block emits the N-element
device-specific block shape.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01Nw79wQq7o3YvzNBtP5GiEV
EOF
)"
```

---

## Task 3: `fit_axis` — the core per-axis 3-tier algorithm

`fit_axis` is the shared low-level fitter reused throughout this feature: Task 5's
per-row X fitting and Task 6's row-stacking Y fitting both call it directly, on
different kinds of `(id, pos, size)` groups (elements within one row, or the row list
itself as pseudo-items). Its own internal behavior does not know or care about rows —
that's exactly why it's reusable.

**Files:**
- Create: `generator/reflow.py`
- Test: `generator/_test_output/reflow_task3_fit_axis_test.py`

**Interfaces:**
- Produces:
  - `class AxisFitError(Exception)` — raised when `target_dim` can't fit even the
    mandatory `(n-1)*min_gap` floor gaps for the item count.
  - `fit_axis(items: list[tuple[str, int, int]], target_dim: int, min_gap: int = 4) -> dict[str, dict]`
    — `items` is `[(item_id, pos, size)]` for one axis of one group. Returns `{item_id:
    {"pos": int, "size": int, "scale": float}}`; `scale` is `1.0` unless tier 3 applied.

- [ ] **Step 1: Write the failing test**

```python
# generator/_test_output/reflow_task3_fit_axis_test.py
"""Task 3: fit_axis -- one test per tier, plus the insufficient-room edge case."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reflow import fit_axis, AxisFitError  # noqa: E402

# --- Tier 1: bounding box already fits once translated -- gaps byte-for-byte unchanged.
items = [("a", 800, 100), ("b", 950, 100)]  # span 800..1050, gap 50
result = fit_axis(items, target_dim=300)  # span (250) <= 300
assert result["a"]["scale"] == 1.0 and result["b"]["scale"] == 1.0
assert result["b"]["pos"] - (result["a"]["pos"] + result["a"]["size"]) == 50, "tier 1 must preserve the original gap exactly"
assert result["a"]["pos"] >= 0 and result["b"]["pos"] + result["b"]["size"] <= 300
print("tier 1 (move): OK")

# --- Tier 2: span too big to move, but compaction to the 4px floor fits.
items = [("a", 0, 100), ("b", 150, 100), ("c", 300, 100)]  # span 400, two 50px gaps
result = fit_axis(items, target_dim=308)
assert result["a"]["scale"] == 1.0 and result["b"]["scale"] == 1.0 and result["c"]["scale"] == 1.0, "tier 2 must never resize"
assert result["a"]["size"] == 100 and result["b"]["size"] == 100 and result["c"]["size"] == 100
gap_ab = result["b"]["pos"] - (result["a"]["pos"] + result["a"]["size"])
gap_bc = result["c"]["pos"] - (result["b"]["pos"] + result["b"]["size"])
assert gap_ab >= 4 and gap_bc >= 4, f"gaps must never go below the 4px floor, got {gap_ab}, {gap_bc}"
assert result["c"]["pos"] + result["c"]["size"] - result["a"]["pos"] <= 308
print("tier 2 (compact): OK")

# --- Tier 2, genuine interpolation (0 < r < 1), not the r==1.0 boundary above -------
items = [("a", 0, 100), ("b", 150, 100), ("c", 300, 100)]  # same items, looser target
result = fit_axis(items, target_dim=320)  # needed_reduction=80 < slack=92 -- strict interpolation
assert result["a"]["scale"] == 1.0 and result["b"]["scale"] == 1.0 and result["c"]["scale"] == 1.0
span = result["c"]["pos"] + result["c"]["size"] - result["a"]["pos"]
assert span <= 320, f"tier 2 interpolation must still fit target_dim, got span={span}"
gap_ab = result["b"]["pos"] - (result["a"]["pos"] + result["a"]["size"])
gap_bc = result["c"]["pos"] - (result["b"]["pos"] + result["b"]["size"])
assert gap_ab >= 4 and gap_bc >= 4, f"gaps must never go below the 4px floor, got {gap_ab}, {gap_bc}"
print("tier 2 (compact), genuine interpolation path: OK")

# --- Tier 2 with a sub-floor/overlapping input gap -- regression guard. A naive
#     "max_possible_reduction = total_gap - (n-1)*min_gap" formula credits a
#     below-floor (or negative/overlapping) gap as if it were reducible slack, which
#     silently returns a layout WIDER than target_dim. b and c below overlap by 20px
#     in the source (b covers 150-250, c starts at 230).
items = [("a", 0, 100), ("b", 150, 100), ("c", 230, 100)]
result = fit_axis(items, target_dim=315)
span = result["c"]["pos"] + result["c"]["size"] - result["a"]["pos"]
assert span <= 315, f"tier 2 must still fit target_dim even with a sub-floor input gap, got span={span}"
gap_ab = result["b"]["pos"] - (result["a"]["pos"] + result["a"]["size"])
gap_bc = result["c"]["pos"] - (result["b"]["pos"] + result["b"]["size"])
assert gap_ab >= 4 and gap_bc >= 4, f"gaps must never go below the 4px floor, got {gap_ab}, {gap_bc}"
print("tier 2 (compact), sub-floor input gap regression guard: OK")

# --- Tier 2 with many gaps -- regression guard for rounding drift COMPOUNDING across
#     several gaps. An earlier fix rounded each position incrementally off the
#     previous ROUNDED position, which still let up to ~0.5px of error per gap
#     accumulate across many gaps and occasionally push the final span a few px over
#     target_dim even though each individual gap still met the 4px floor -- caught by
#     this exact case during that fix's own re-review. Flooring (not rounding) each
#     gap before accumulating positions closes this for good (see the implementation's
#     comment).
items = [("i0", 0, 100), ("i1", 149, 69), ("i2", 254, 56), ("i3", 346, 106), ("i4", 509, 94), ("i5", 622, 56)]
result = fit_axis(items, target_dim=637)
span = max(v["pos"] + v["size"] for v in result.values()) - min(v["pos"] for v in result.values())
assert span <= 637, f"tier 2 must not overshoot target_dim via rounding drift across many gaps, got span={span}"
sorted_ids = sorted(result, key=lambda i: result[i]["pos"])
for i in range(len(sorted_ids) - 1):
    a, b = result[sorted_ids[i]], result[sorted_ids[i + 1]]
    gap = b["pos"] - (a["pos"] + a["size"])
    assert gap >= 4, f"gap must never go below the 4px floor, got {gap}"
print("tier 2 (compact), many-gaps rounding-drift regression guard: OK")

# --- Tier 3: even at the 4px floor, sizes alone exceed target_dim -- must scale down.
items = [("a", 0, 100), ("b", 150, 100)]  # sizes sum 200, 1 gap -> floor-packed min = 204
result = fit_axis(items, target_dim=100)  # too small even for floor-packed sizes
assert result["a"]["scale"] < 1.0 and result["a"]["scale"] == result["b"]["scale"], "tier 3 must apply one shared scale factor"
assert result["a"]["size"] + result["b"]["size"] + 4 <= 100 + 1, "packed (with 4px gap) must fit target_dim (+-1 for rounding)"
gap = result["b"]["pos"] - (result["a"]["pos"] + result["a"]["size"])
assert gap == 4, f"tier 3 must repack at exactly the 4px floor, got gap={gap}"
print("tier 3 (scale): OK")

# --- Edge case: not even the mandatory floor gaps fit for this many elements.
items = [("a", 0, 1), ("b", 10, 1), ("c", 20, 1), ("d", 30, 1)]  # 4 elements, 3 mandatory 4px gaps = 12px minimum just for gaps
try:
    fit_axis(items, target_dim=5)  # smaller than the 3*4=12px of mandatory gaps alone
    assert False, "expected AxisFitError"
except AxisFitError:
    pass
print("insufficient-room edge case: OK")

# --- No-overlap guarantee, direct AABB check, for a denser tier-2/3-forcing scenario.
def overlaps(a_pos, a_size, b_pos, b_size):
    return not (a_pos + a_size <= b_pos or b_pos + b_size <= a_pos)

items = [(f"e{i}", i * 60, 55) for i in range(6)]  # 6 elements, span 0..355 (last starts at 300, size 55)
for target in (308, 200, 100, 50):
    result = fit_axis(items, target_dim=target)
    ids = list(result)
    span = max(v["pos"] + v["size"] for v in result.values()) - min(v["pos"] for v in result.values())
    assert span <= target, f"fitted group must fit target_dim={target}, got span={span}"
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = result[ids[i]], result[ids[j]]
            assert not overlaps(a["pos"], a["size"], b["pos"], b["size"]), f"overlap at target_dim={target}: {ids[i]} vs {ids[j]}"
print("no-overlap guarantee AND target_dim-fit across all tiers: OK")

# --- fit_axis is a generic (id, pos, size) fitter -- it works identically on row
#     pseudo-items (Task 6 will feed it "__row0"-style keys), not just element ids.
row_items = [("__row0", 0, 90), ("__row1", 114, 90)]
row_result = fit_axis(row_items, target_dim=300)
assert row_result["__row0"]["scale"] == 1.0 and row_result["__row1"]["scale"] == 1.0
print("generic over row pseudo-items too: OK")

print("\nTASK 3: fit_axis -- ALL CHECKS PASSED")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python generator/_test_output/reflow_task3_fit_axis_test.py`
Expected: `ModuleNotFoundError: No module named 'reflow'`

- [ ] **Step 3: Implement**

Create `generator/reflow.py`:

```python
"""
Multi-resolution reflow -- Phase 5 continuation.

Source-grounded, per docs/superpowers/specs/2026-09-08-multi-resolution-reflow-design.md
and docs/architecture/10-reflow.md.
"""
from __future__ import annotations


class AxisFitError(Exception):
    """Raised when target_dim can't fit even the mandatory min_gap floor gaps for this
    many items -- caller (reflow_file's _fit_group) catches this per-axis and reports a
    warning rather than crashing (see the spec's Error handling section)."""


def fit_axis(items: list[tuple[str, int, int]], target_dim: int, min_gap: int = 4) -> dict[str, dict]:
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
    """
    if not items:
        return {}
    n = len(items)
    sorted_items = sorted(items, key=lambda t: t[1])
    ids = [i for i, _, _ in sorted_items]
    positions = [p for _, p, _ in sorted_items]
    sizes = [s for _, _, s in sorted_items]

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
        return {
            item_id: {"pos": pos + offset, "size": size, "scale": 1.0}
            for item_id, pos, size in zip(ids, positions, sizes)
        }

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
            return {
                item_id: {"pos": pos, "size": size, "scale": 1.0}
                for item_id, pos, size in zip(ids, new_positions, sizes)
            }

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
    return {
        item_id: {"pos": pos, "size": size, "scale": scale}
        for item_id, pos, size in zip(ids, new_positions, new_sizes)
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python generator/_test_output/reflow_task3_fit_axis_test.py`
Expected: `TASK 3: fit_axis -- ALL CHECKS PASSED`

- [ ] **Step 5: Commit**

```bash
git add generator/reflow.py generator/_test_output/reflow_task3_fit_axis_test.py
git commit -m "$(cat <<'EOF'
Reflow task 3: fit_axis, the core per-axis 3-tier fit algorithm

Move (rigid translate) -> compact whitespace (order-preserving, 4px
floor, linear interpolation toward the floor) -> scale down (uniform
factor, reserves the mandatory floor gaps first, last resort). Raises
AxisFitError when even the floor gaps don't fit the item count. Generic
over (id, pos, size) tuples -- Task 5 (per-row X fit) and Task 6
(row-stacking Y fit) both reuse it unchanged, on elements and on row
pseudo-items respectively. Direct AABB pairwise checks in the test
confirm no tier introduces a new overlap across a range of target
dimensions.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01Nw79wQq7o3YvzNBtP5GiEV
EOF
)"
```

---

## Task 4: `detect_rows` — Y-overlap row grouping

**Files:**
- Modify: `generator/reflow.py`
- Test: `generator/_test_output/reflow_task4_detect_rows_test.py`

**Interfaces:**
- Produces: `detect_rows(elements: dict[str, dict]) -> list[list[str]]` — partitions a
  group's element ids into rows by source Y-overlap. Returned top-to-bottom; within a
  row, ids are ordered left-to-right by `left` (this is the order Task 5's `wrap_rows`
  peels from the trailing end of).

- [ ] **Step 1: Write the failing test**

```python
# generator/_test_output/reflow_task4_detect_rows_test.py
"""Task 4: detect_rows -- groups elements into rows by source Y-overlap."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reflow import detect_rows  # noqa: E402

# --- Single row: three elements whose Y-ranges all mutually overlap ------------------
elements = {
    "a": {"left": 0, "top": 20, "width": 50, "height": 50},
    "b": {"left": 60, "top": 30, "width": 50, "height": 20},
    "c": {"left": 120, "top": 25, "width": 50, "height": 45},
}
assert detect_rows(elements) == [["a", "b", "c"]]
print("single row: OK")

# --- Two cleanly separated rows -------------------------------------------------------
elements2 = {
    "a": {"left": 0, "top": 20, "width": 50, "height": 50},   # range 20-70
    "b": {"left": 0, "top": 100, "width": 50, "height": 50},  # range 100-150, no overlap with a
}
assert detect_rows(elements2) == [["a"], ["b"]]
print("two separate rows: OK")

# --- Row with differing (but Y-overlapping) top/height values ------------------------
elements3 = {
    "d": {"left": 0, "top": 0, "width": 200, "height": 100},   # range 0-100
    "e": {"left": 250, "top": 50, "width": 50, "height": 30},  # range 50-80, overlaps
    "f": {"left": 350, "top": 90, "width": 30, "height": 5},   # range 90-95, overlaps accumulated (0-100)
}
assert detect_rows(elements3) == [["d", "e", "f"]]
print("Y-overlapping-but-different top/height, single row: OK")

# --- Within a row, elements are ordered left-to-right, NOT by the order they were
#     encountered while sorting by top (this is the ordering wrap_rows relies on).
elements4 = {
    "g": {"left": 200, "top": 10, "width": 50, "height": 100},  # sorted-by-top first (top=10)
    "h": {"left": 0, "top": 15, "width": 50, "height": 90},     # sorted-by-top second, but leftmost
}
assert detect_rows(elements4) == [["h", "g"]], "row members must be left-to-right ordered by 'left'"
print("left-to-right ordering within a row: OK")

# --- Empty input ------------------------------------------------------------------
assert detect_rows({}) == []
print("empty input: OK")

print("\nTASK 4: detect_rows -- ALL CHECKS PASSED")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python generator/_test_output/reflow_task4_detect_rows_test.py`
Expected: `ImportError: cannot import name 'detect_rows'`

- [ ] **Step 3: Implement**

Append to `generator/reflow.py`:

```python
def detect_rows(elements: dict[str, dict]) -> list[list[str]]:
    """Partition a group of elements into rows by source Y-overlap: sort by `top`, then
    greedily cluster -- an element joins the current row if its [top, top+height] range
    overlaps the row's accumulated [row_top, row_bottom) range so far (row_bottom grows
    to the tallest member seen); otherwise it starts a new row. Rows are returned
    top-to-bottom; within a row, ids are ordered left-to-right by `left` (NOT by the
    order they were encountered while sorting by top -- wrap_rows peels from this
    left-to-right order's trailing end). See the spec's Row detection section."""
    if not elements:
        return []
    ordered = sorted(elements.items(), key=lambda kv: kv[1]["top"])
    rows: list[list[str]] = []
    current_ids: list[str] = []
    row_bottom = None
    for element_id, e in ordered:
        top, bottom = e["top"], e["top"] + e["height"]
        if row_bottom is None or top < row_bottom:
            current_ids.append(element_id)
            row_bottom = bottom if row_bottom is None else max(row_bottom, bottom)
        else:
            rows.append(sorted(current_ids, key=lambda i: elements[i]["left"]))
            current_ids = [element_id]
            row_bottom = bottom
    rows.append(sorted(current_ids, key=lambda i: elements[i]["left"]))
    return rows
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python generator/_test_output/reflow_task4_detect_rows_test.py`
Expected: `TASK 4: detect_rows -- ALL CHECKS PASSED`

- [ ] **Step 5: Commit**

```bash
git add generator/reflow.py generator/_test_output/reflow_task4_detect_rows_test.py
git commit -m "$(cat <<'EOF'
Reflow task 4: detect_rows -- Y-overlap row grouping

Sorts elements by top and greedily clusters into rows by [top,
top+height] overlap against each row's accumulated range. Rows are
top-to-bottom; within a row, ids are left-to-right by `left` -- the
order wrap_rows (Task 5) peels its trailing end from. This is the first
piece of the new row-wrap X-axis tier, per the revised design spec
(2026-09-09 row-wrap revision).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01Nw79wQq7o3YvzNBtP5GiEV
EOF
)"
```

---

## Task 5: `wrap_rows` — X-axis wrap tier

**Files:**
- Modify: `generator/reflow.py`
- Test: `generator/_test_output/reflow_task5_wrap_rows_test.py`

**Interfaces:**
- Consumes: nothing new structurally — operates on the row lists `detect_rows` (Task 4)
  produces, plus the same elements dict.
- Produces: `wrap_rows(rows: list[list[str]], elements: dict[str, dict], target_width: int) -> list[list[str]]`

- [ ] **Step 1: Write the failing test**

```python
# generator/_test_output/reflow_task5_wrap_rows_test.py
"""Task 5: wrap_rows -- splits a row that doesn't fit target_width by peeling trailing
elements onto a new row, recursively."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reflow import wrap_rows  # noqa: E402

def make(*specs):
    # specs: (id, left, width)
    return {eid: {"left": left, "width": width} for eid, left, width in specs}

# --- A row that already fits: no split -------------------------------------------
elements = make(("a", 0, 100), ("b", 110, 100), ("c", 220, 100), ("d", 330, 100))
assert wrap_rows([["a", "b", "c", "d"]], elements, target_width=500) == [["a", "b", "c", "d"]]
print("already fits, no split: OK")

# --- A row that needs exactly one split -------------------------------------------
# span = (330+100) - 0 = 430 > 250; peeling c,d together (a,b alone span 210 <= 250 fits).
result = wrap_rows([["a", "b", "c", "d"]], elements, target_width=250)
assert result == [["a", "b"], ["c", "d"]], f"expected one split into two rows, got {result}"
print("exactly one split: OK")

# --- A row dense enough to need multiple splits -----------------------------------
dense = make(*[(f"e{i}", i * 110, 100) for i in range(6)])  # e0..e5, 100px wide, 10px gaps
result = wrap_rows([[f"e{i}" for i in range(6)]], dense, target_width=150)
assert result == [[f"e{i}"] for i in range(6)], f"expected 6 singleton rows, got {result}"
print("multiple splits down to singletons: OK")

# --- A single element wider than target_width on its own: left as a 1-element row,
#     never loops -- it falls through to fit_axis's own compact/scale tiers later.
wide = make(("w", 0, 300))
assert wrap_rows([["w"]], wide, target_width=250) == [["w"]]
print("single too-wide element left unsplit (no infinite loop): OK")

# --- Multiple independent rows: only the offending row splits, the other is untouched.
mixed = make(("a", 0, 100), ("b", 110, 100), ("c", 220, 100), ("d", 330, 100), ("z", 0, 50))
result = wrap_rows([["a", "b", "c", "d"], ["z"]], mixed, target_width=250)
assert result == [["a", "b"], ["c", "d"], ["z"]], f"expected only the first row to split, got {result}"
print("only the offending row splits, others untouched: OK")

print("\nTASK 5: wrap_rows -- ALL CHECKS PASSED")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python generator/_test_output/reflow_task5_wrap_rows_test.py`
Expected: `ImportError: cannot import name 'wrap_rows'`

- [ ] **Step 3: Implement**

Append to `generator/reflow.py`:

```python
def _row_fits(row: list[str], elements: dict[str, dict], target_width: int) -> bool:
    lefts = [elements[eid]["left"] for eid in row]
    rights = [elements[eid]["left"] + elements[eid]["width"] for eid in row]
    return max(rights) - min(lefts) <= target_width


def wrap_rows(rows: list[list[str]], elements: dict[str, dict], target_width: int) -> list[list[str]]:
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
    finalized per row (see the spec's Tiers 3/4 note)."""
    pending = list(rows)
    result: list[list[str]] = []
    i = 0
    while i < len(pending):
        row = pending[i]
        if len(row) <= 1 or _row_fits(row, elements, target_width):
            result.append(row)
            i += 1
            continue
        remainder = row
        peeled: list[str] = []
        while len(remainder) > 1 and not _row_fits(remainder, elements, target_width):
            peeled.insert(0, remainder[-1])
            remainder = remainder[:-1]
        pending[i] = remainder
        pending.insert(i + 1, peeled)
        # Don't advance i: re-check the shrunk `remainder` (now at pending[i]) next
        # iteration -- it passes immediately since peeling stopped exactly when it
        # started fitting (or dropped to one element).
    return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python generator/_test_output/reflow_task5_wrap_rows_test.py`
Expected: `TASK 5: wrap_rows -- ALL CHECKS PASSED`

- [ ] **Step 5: Commit**

```bash
git add generator/reflow.py generator/_test_output/reflow_task5_wrap_rows_test.py
git commit -m "$(cat <<'EOF'
Reflow task 5: wrap_rows -- the new X-axis wrap tier

Inserted between fit_axis's Tier 1 (move) and Tier 2 (compact), per the
revised design spec. A row that doesn't fit target_width via translate
alone peels its trailing elements (in one pass) onto a new row directly
after it; the peeled row recursively gets the same check, so a crowded
row can split more than once. A single element that's still too wide
alone is left unsplit -- wrapping can't help it, so it falls through to
fit_axis's own compact/scale tiers later (Task 9). Preserves reading
order throughout: elements never reorder within or across rows.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01Nw79wQq7o3YvzNBtP5GiEV
EOF
)"
```

---

## Task 6: `stack_rows` — Y-axis row-stacking

This is where the design's tied-anchor gap (found while planning this feature) gets
fixed: a row created by an X-axis wrap split shares its original source `top` with the
row it split from (splitting doesn't move anything vertically), so two sibling rows can
tie on raw `min(top)`. `stack_rows` uses a **pre-stacked anchor** instead — see the
spec's Y axis section (revised 2026-09-09).

**Files:**
- Modify: `generator/reflow.py`
- Test: `generator/_test_output/reflow_task6_stack_rows_test.py`

**Interfaces:**
- Consumes: `fit_axis` (Task 3).
- Produces: `stack_rows(rows: list[list[str]], elements: dict[str, dict], target_height: int, min_gap: int = 4) -> dict[str, dict]`
  — `{element_id: {"top": int, "height": int, "scale": float}}`.

- [ ] **Step 1: Write the failing test**

```python
# generator/_test_output/reflow_task6_stack_rows_test.py
"""Task 6: stack_rows -- Y-axis row-stacking, including the pre-stacked-anchor fix for
rows that share their original top (the wrap-split case)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reflow import stack_rows, fit_axis  # noqa: E402

def make(*specs):
    # specs: (id, top, height)
    return {eid: {"top": top, "height": height} for eid, top, height in specs}

# --- Rows with distinct natural anchors, fitting via row-level Tier 1 (move) ---------
# row0 = [a, b] (anchor 50, natural height 50: a covers 50-100, b covers 60-80)
# row1 = [c]    (anchor 150, natural height 60)
elements = make(("a", 50, 50), ("b", 60, 20), ("c", 150, 60))
rows = [["a", "b"], ["c"]]
expected_row_fit = fit_axis([("__row0", 50, 50), ("__row1", 150, 60)], target_dim=200)
result = stack_rows(rows, elements, target_height=200)
assert result["a"]["top"] == expected_row_fit["__row0"]["pos"], "a's offset from row0's anchor (0) must be preserved"
assert result["b"]["top"] == expected_row_fit["__row0"]["pos"] + (60 - 50), "b's 10px offset from row0's anchor must be preserved exactly"
assert result["c"]["top"] == expected_row_fit["__row1"]["pos"]
assert result["a"]["scale"] == result["b"]["scale"] == result["c"]["scale"] == 1.0
assert result["a"]["height"] == 50 and result["b"]["height"] == 20 and result["c"]["height"] == 60
print("row-level Tier 1 (move), per-element offsets preserved: OK")

# --- A row list needing Tier 3 (scale) -- every element in a scaled row must scale ---
elements2 = make(("a", 0, 100), ("b", 20, 30), ("c", 210, 80))
rows2 = [["a", "b"], ["c"]]  # row0 anchor 0 height 100, row1 anchor 210 height 80
expected2 = fit_axis([("__row0", 0, 100), ("__row1", 210, 80)], target_dim=50)
result2 = stack_rows(rows2, elements2, target_height=50)
scale0 = expected2["__row0"]["scale"]
scale1 = expected2["__row1"]["scale"]
assert scale0 < 1.0 and scale1 < 1.0, "target_height=50 must force Tier 3 scaling"
assert result2["a"]["scale"] == scale0 and result2["b"]["scale"] == scale0
assert result2["c"]["scale"] == scale1
assert result2["a"]["top"] == expected2["__row0"]["pos"]
assert result2["a"]["height"] == expected2["__row0"]["size"], "a alone determines row0's natural height, so a's scaled height must equal the row's own fitted size"
# CORRECTED 2026-09-09 (Task 6's own TDD cycle caught this): "a"'s height above is
# PROVABLY int()-based, not round()-based -- a's own top/height exactly span row0's
# natural extent, so a's own height*scale is the identical expression to row0's own
# fit_axis-computed size, which fit_axis's Tier 3 always computes via int() (never
# round(), per Task 3's own fix). "b" must use the same int() convention for
# consistency -- round() here (as an earlier draft of this test had it) is provably
# inconsistent with the "a" assertion above for this exact scale0 (round(100*scale0)
# == 26 but int(100*scale0) == 25; no single per-element rounding function satisfies
# both assertions except int()).
assert result2["b"]["top"] == round(expected2["__row0"]["pos"] + (20 - 0) * scale0)
assert result2["b"]["height"] == max(1, int(30 * scale0))
assert result2["c"]["top"] == expected2["__row1"]["pos"]
assert result2["c"]["height"] == expected2["__row1"]["size"]
print("row-level Tier 3 (scale), per-element scaling: OK")

# --- The wrap-split case: two rows share the SAME source top (splitting a row doesn't
#     move anything vertically) -- must NOT tie/overlap when stacked. -------------------
elements3 = make(("x", 20, 90), ("y", 20, 90))  # x and y both originally at top=20
rows3 = [["x"], ["y"]]  # wrap_rows already split these into separate rows
result3 = stack_rows(rows3, elements3, target_height=300)
assert result3["y"]["top"] >= result3["x"]["top"] + result3["x"]["height"] + 4, (
    "wrap-split sibling rows sharing the same source top must still end up "
    f"non-overlapping on Y (min 4px gap), got x={result3['x']}, y={result3['y']}"
)
print("wrap-split sibling rows (tied source top) stack without overlap: OK")

# --- Regression guard: ordinary (non-wrap-split) rows with a TIGHT natural gap must
#     be a true no-op -- the original gap is preserved exactly, even below min_gap,
#     never forced up to the floor. An earlier version of stack_rows unconditionally
#     forced every inter-row gap to >=min_gap, which pushed rows with a genuinely tight
#     (but non-degenerate) original gap further apart than they ever were.
elements4 = make(("p", 0, 50), ("q", 52, 50), ("r", 104, 50))  # rows separated by 2px each
rows4 = [["p"], ["q"], ["r"]]
result4 = stack_rows(rows4, elements4, target_height=300)  # ample room -- pure Tier 1 (move)
assert result4["p"]["scale"] == result4["q"]["scale"] == result4["r"]["scale"] == 1.0
assert result4["q"]["top"] - (result4["p"]["top"] + result4["p"]["height"]) == 2, (
    "ordinary rows' original 2px gap must be preserved exactly, not forced to the "
    f"4px floor, got {result4}"
)
assert result4["r"]["top"] - (result4["q"]["top"] + result4["q"]["height"]) == 2
print("ordinary rows with a tight original gap: true no-op regression guard: OK")

# --- Same regression, but flush-stacked (0px gap) rows -- must also be preserved
#     exactly, not forced to 4px, and must NOT be spuriously pushed into Tier 2/3.
elements5 = make(("s", 0, 50), ("t", 50, 50), ("u", 100, 50))  # 0px gaps, span 150 exactly
rows5 = [["s"], ["t"], ["u"]]
result5 = stack_rows(rows5, elements5, target_height=150)  # exactly the natural span
assert result5["s"]["scale"] == result5["t"]["scale"] == result5["u"]["scale"] == 1.0, (
    "flush rows fitting target_height exactly must stay at Tier 1 (move); an "
    f"unconditional 4px floor would force unnecessary Tier 3 scaling here: {result5}"
)
assert result5["t"]["top"] - (result5["s"]["top"] + result5["s"]["height"]) == 0
assert result5["u"]["top"] - (result5["t"]["top"] + result5["t"]["height"]) == 0
print("flush-stacked rows: true no-op, no spurious tier escalation: OK")

# --- Empty input --------------------------------------------------------------------
assert stack_rows([], {}, target_height=100) == {}
print("empty input: OK")

print("\nTASK 6: stack_rows -- ALL CHECKS PASSED")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python generator/_test_output/reflow_task6_stack_rows_test.py`
Expected: `ImportError: cannot import name 'stack_rows'`

- [ ] **Step 3: Implement**

Append to `generator/reflow.py`:

```python
def stack_rows(rows: list[list[str]], elements: dict[str, dict], target_height: int, min_gap: int = 4) -> dict[str, dict]:
    """Y-axis row-stacking (see the spec's 'Y axis: row-stacking', revised 2026-09-09,
    corrected again same-day after a task review caught a real bug -- see below).
    Builds one pseudo-item per row -- natural height `max(top+height) - min(top)` over
    the row's own members, and a PRE-STACKED anchor (not simply the row's own
    min(top): a row created by an X-axis wrap split shares its original top with the
    row it split from, so raw min(top) can tie between sibling rows).

    Row i's anchor is row i-1's anchor plus row i-1's natural height, plus that pair's
    own ORIGINAL gap (`row i's own min(top) - (row i-1's own min(top) + row i-1's
    natural height)`) when that gap is non-negative, or the min_gap floor when it
    isn't. CORRECTED 2026-09-09 (task review): an earlier version used `max(its own
    min(top), row i-1's anchor + row i-1's natural height + min_gap)` -- unconditionally
    forcing EVERY inter-row gap up to at least min_gap, which is wrong: detect_rows
    only guarantees a non-negative inter-row gap (`top >= row_bottom`), not a
    >=min_gap one, so two ordinarily-adjacent rows separated by 1-3px in the source
    would get pushed further apart than they ever were -- contradicting fit_axis's own
    Tier 1 principle (rigid translate preserves original gaps exactly, even below
    min_gap; the floor is only enforced where compaction/scaling actually happens).
    Worse, that injected spacing could push a row list that fit target_height
    perfectly into needing Tier 2/3 compaction/scaling it never needed. The corrected
    formula is a true no-op for every ordinary row (original gap preserved exactly,
    even 0px) and clamps only the genuinely degenerate case (a tied or negative gap --
    the wrap-split sibling scenario this pre-stacking step exists for).

    Feeds the row pseudo-items to fit_axis against target_height, then maps each row's
    (pos, scale) back onto its own elements: new_top = row_pos + (element's own top -
    the row's own raw min(top)) * scale, new_height = int(element.height * scale) --
    int(), NOT round() -- (only when scale != 1.0, floored at 1px like fit_axis's own
    tier 3). CORRECTED 2026-09-09 (found during this task's own TDD cycle): height
    MUST use int() truncation, not round() -- the element that alone spans a row's
    full natural extent has `own height * scale` as literally the same expression as
    that row's own fit_axis-computed size, and fit_axis's Tier 3 always computes sizes
    via int() (never round(), per Task 3's fix), so using round() here would make that
    element's height mismatch its own row's fitted size. `top` keeps round() -- it has
    no equivalent identity to preserve. Returns {element_id: {"top": int, "height":
    int, "scale": float}}."""
    if not rows:
        return {}
    row_keys = [f"__row{i}" for i in range(len(rows))]
    own_min_top = [min(elements[eid]["top"] for eid in row) for row in rows]
    natural_height = [
        max(elements[eid]["top"] + elements[eid]["height"] for eid in row) - own_min_top[i]
        for i, row in enumerate(rows)
    ]
    anchors = [own_min_top[0]]
    for i in range(1, len(rows)):
        original_gap = own_min_top[i] - (own_min_top[i - 1] + natural_height[i - 1])
        anchors.append(anchors[i - 1] + natural_height[i - 1] + (original_gap if original_gap >= 0 else min_gap))

    row_items = list(zip(row_keys, anchors, natural_height))
    row_fit = fit_axis(row_items, target_height, min_gap=min_gap)

    result: dict[str, dict] = {}
    for i, row in enumerate(rows):
        row_pos = row_fit[row_keys[i]]["pos"]
        row_scale = row_fit[row_keys[i]]["scale"]
        for eid in row:
            e = elements[eid]
            offset = (e["top"] - own_min_top[i]) * row_scale
            result[eid] = {
                "top": round(row_pos + offset),
                "height": max(1, int(e["height"] * row_scale)) if row_scale != 1.0 else e["height"],
                "scale": row_scale,
            }
    return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python generator/_test_output/reflow_task6_stack_rows_test.py`
Expected: `TASK 6: stack_rows -- ALL CHECKS PASSED`

- [ ] **Step 5: Update the architecture doc**

Append to `docs/architecture/10-reflow.md`:

```markdown
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
```

- [ ] **Step 6: Commit**

```bash
git add generator/reflow.py generator/_test_output/reflow_task6_stack_rows_test.py docs/architecture/10-reflow.md
git commit -m "$(cat <<'EOF'
Reflow task 6: stack_rows -- Y-axis row-stacking, tied-anchor fix

Builds row pseudo-items (natural height + a PRE-STACKED anchor, not raw
min(top)) and feeds them to fit_axis, then maps each row's (pos, scale)
back onto its own elements, preserving each element's offset from its
row's own top. The pre-stacked anchor fixes a real gap found while
planning: a row created by an X-axis wrap split shares its original
source top with the row it split from, so two sibling rows could tie
and overlap without this. For ordinary (non-wrap-split) rows the
pre-stacking is a no-op. Documented in docs/architecture/10-reflow.md
and folded back into the design spec.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01Nw79wQq7o3YvzNBtP5GiEV
EOF
)"
```

---

## Task 7: `find_new_elements` / `check_overlaps`

**Files:**
- Modify: `generator/reflow.py`
- Test: `generator/_test_output/reflow_task7_diff_overlap_test.py`

**Interfaces:**
- Produces:
  - `find_new_elements(source_elements: dict[str, dict], target_elements: dict[str, dict]) -> tuple[set[str], set[str]]`
    — `(new_ids, pinned_ids)`.
  - `check_overlaps(pinned: dict[str, dict], new: dict[str, dict]) -> list[tuple[str, str]]`
    — pairwise AABB check, `[(new_id, pinned_id), ...]` for every conflicting pair.

- [ ] **Step 1: Write the failing test**

```python
# generator/_test_output/reflow_task7_diff_overlap_test.py
"""Task 7: find_new_elements (source/target id diff) and check_overlaps (pairwise AABB)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reflow import find_new_elements, check_overlaps  # noqa: E402

source = {"a": {}, "b": {}, "c": {}}
target = {"a": {}, "d": {}}
new_ids, pinned_ids = find_new_elements(source, target)
assert new_ids == {"b", "c"}
assert pinned_ids == {"a"}
print("find_new_elements: OK")

pinned = {"p1": {"left": 0, "top": 0, "width": 100, "height": 100}}
non_overlapping_new = {"n1": {"left": 200, "top": 0, "width": 50, "height": 50}}
overlapping_new = {"n2": {"left": 50, "top": 50, "width": 100, "height": 100}}
touching_new = {"n3": {"left": 100, "top": 0, "width": 50, "height": 50}}  # edges touch, not overlapping

assert check_overlaps(pinned, non_overlapping_new) == []
assert check_overlaps(pinned, overlapping_new) == [("n2", "p1")]
assert check_overlaps(pinned, touching_new) == [], "exactly-touching rectangles must NOT count as overlapping"
print("check_overlaps: OK")

print("\nTASK 7: find_new_elements / check_overlaps -- ALL CHECKS PASSED")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python generator/_test_output/reflow_task7_diff_overlap_test.py`
Expected: `ImportError: cannot import name 'find_new_elements'`

- [ ] **Step 3: Implement**

Append to `generator/reflow.py`:

```python
def find_new_elements(source_elements: dict[str, dict], target_elements: dict[str, dict]) -> tuple[set[str], set[str]]:
    """(new_ids, pinned_ids): ids in source but not yet in target are new; ids present
    in both are pinned (left untouched in pin_existing mode)."""
    source_ids = set(source_elements)
    target_ids = set(target_elements)
    return source_ids - target_ids, source_ids & target_ids


def _rects_overlap(a: dict, b: dict) -> bool:
    return not (
        a["left"] + a["width"] <= b["left"]
        or b["left"] + b["width"] <= a["left"]
        or a["top"] + a["height"] <= b["top"]
        or b["top"] + b["height"] <= a["top"]
    )


def check_overlaps(pinned: dict[str, dict], new: dict[str, dict]) -> list[tuple[str, str]]:
    """Pairwise AABB overlap check between every new element and every pinned element
    -- used only in pin_existing mode, since new elements are only fit against each
    other, not against pinned space (see the spec's best-effort/flagged design)."""
    conflicts = []
    for new_id, new_rect in new.items():
        for pinned_id, pinned_rect in pinned.items():
            if _rects_overlap(new_rect, pinned_rect):
                conflicts.append((new_id, pinned_id))
    return conflicts
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python generator/_test_output/reflow_task7_diff_overlap_test.py`
Expected: `TASK 7: ... ALL CHECKS PASSED`

- [ ] **Step 5: Commit**

```bash
git add generator/reflow.py generator/_test_output/reflow_task7_diff_overlap_test.py
git commit -m "$(cat <<'EOF'
Reflow task 7: find_new_elements / check_overlaps

find_new_elements diffs source vs. target element ids into new/pinned
sets for pin_existing mode. check_overlaps is the pairwise AABB check
that surfaces the "best-effort, flagged" warning the spec calls for when
a newly-fit element overlaps a pinned one -- exactly-touching rectangles
correctly do not count as overlapping.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01Nw79wQq7o3YvzNBtP5GiEV
EOF
)"
```

---

## Task 8: `pick_primary` / `choose_source_resolution`

**Files:**
- Modify: `generator/reflow.py`
- Test: `generator/_test_output/reflow_task8_source_selection_test.py`

**Interfaces:**
- Consumes: `devices.ORIENTATION_ENUM` (existing, Phase 5).
- Produces:
  - `pick_primary(resolutions: list[dict], orientation: str) -> dict | None`
  - `choose_source_resolution(existing_resolutions: list[dict], new_resolution: dict) -> dict | None`

Both operate on `{DeviceResolutionSource}`-shaped dicts (i.e. `devices.py::
to_project_resolution`'s output, or entries read back via `project.py::read_cuip`) —
`orientation` is the **int** DisplayOrientation encoding on these dicts, not the string
name `parse_position_rules`/`build_reflow_block` use, so this task converts internally.

- [ ] **Step 1: Write the failing test**

```python
# generator/_test_output/reflow_task8_source_selection_test.py
"""Task 8: pick_primary / choose_source_resolution."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reflow import pick_primary, choose_source_resolution  # noqa: E402
from devices import ORIENTATION_ENUM  # noqa: E402

def res(width, height, orientation):
    return {"id": f"R-{width}x{height}-{orientation}", "width": width, "height": height, "orientation": ORIENTATION_ENUM[orientation]}

tsw = res(1280, 800, "landscape")
tst_l = res(1920, 1200, "landscape")
tst_p = res(1200, 1920, "portrait")

# pick_primary: highest width in the given orientation; None if that orientation is absent.
assert pick_primary([tsw, tst_l], "landscape") == tst_l  # 1920 > 1280
assert pick_primary([tsw, tst_l], "portrait") is None
assert pick_primary([], "landscape") is None
print("pick_primary: OK")

# choose_source_resolution: same-orientation primary when one exists.
new_landscape = res(640, 360, "landscape")
assert choose_source_resolution([tsw, tst_l, tst_p], new_landscape) == tst_l
print("choose_source_resolution (same-orientation primary): OK")

# Bootstrap case: no existing resolution in the new one's orientation -- use the other's primary.
assert choose_source_resolution([tsw, tst_l], res(800, 1280, "portrait")) == tst_l
print("choose_source_resolution (orientation-bootstrap): OK")

# Nothing to reflow from at all.
assert choose_source_resolution([], new_landscape) is None
print("choose_source_resolution (zero existing resolutions): OK")

print("\nTASK 8: pick_primary / choose_source_resolution -- ALL CHECKS PASSED")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python generator/_test_output/reflow_task8_source_selection_test.py`
Expected: `ImportError: cannot import name 'pick_primary'`

- [ ] **Step 3: Implement**

Append to `generator/reflow.py` (add the import at the top of the file):

```python
from devices import ORIENTATION_ENUM

_ORIENTATION_NAMES = {v: k for k, v in ORIENTATION_ENUM.items()}


def _orientation_name(resolution: dict) -> str:
    return _ORIENTATION_NAMES[resolution["orientation"]]


def pick_primary(resolutions: list[dict], orientation: str) -> dict | None:
    """Highest-width resolution in the given orientation, or None if the project has
    no resolution in that orientation."""
    candidates = [r for r in resolutions if _orientation_name(r) == orientation]
    if not candidates:
        return None
    return max(candidates, key=lambda r: r["width"])


def choose_source_resolution(existing_resolutions: list[dict], new_resolution: dict) -> dict | None:
    """Which existing resolution to fit FROM when adding `new_resolution`: that
    orientation's own primary if the project already has one, else the other
    orientation's primary (bootstrap case), else None (project has no existing
    resolutions at all -- nothing to reflow from, see the spec's Error handling)."""
    new_orientation = _orientation_name(new_resolution)
    other_orientation = "portrait" if new_orientation == "landscape" else "landscape"
    return pick_primary(existing_resolutions, new_orientation) or pick_primary(existing_resolutions, other_orientation)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python generator/_test_output/reflow_task8_source_selection_test.py`
Expected: `TASK 8: ... ALL CHECKS PASSED`

- [ ] **Step 5: Commit**

```bash
git add generator/reflow.py generator/_test_output/reflow_task8_source_selection_test.py
git commit -m "$(cat <<'EOF'
Reflow task 8: pick_primary / choose_source_resolution

Reuses Phase 5's devices.ORIENTATION_ENUM (converting its int encoding
to the string names layout.py's orientation_media_query expects).
choose_source_resolution implements the spec's "same-orientation primary,
else other orientation's primary (bootstrap), else nothing to reflow
from" rule.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01Nw79wQq7o3YvzNBtP5GiEV
EOF
)"
```

---

## Task 9: `reflow_file` — ties it all together, both modes, row/wrap/stack-aware

**Files:**
- Modify: `generator/reflow.py`
- Test: `generator/_test_output/reflow_task9_reflow_file_test.py`

**Interfaces:**
- Consumes: everything from Tasks 1-8 (`layout.orientation_media_query`,
  `layout.find_media_block_span/find_media_block`, `layout.parse_position_rules`,
  `layout.build_reflow_block`, `fit_axis`, `AxisFitError`, `detect_rows`, `wrap_rows`,
  `stack_rows`, `find_new_elements`, `check_overlaps`, `_orientation_name`).
- Produces:
  - `@dataclass class ReflowResult: warnings: list[str] = field(default_factory=list)`
  - `reflow_file(path: Path, target_resolution: dict, source_resolution: dict, mode: str = "pin_existing") -> ReflowResult`
    — reads the file's `{Css}` section, fits new elements per mode (row detection ->
    wrap -> per-row X fit -> row-stacking Y fit), writes the file back untouched except
    for that one section's content (Html/PageAttributes/FileMetadata byte-identical).

- [ ] **Step 1: Write the failing test**

```python
# generator/_test_output/reflow_task9_reflow_file_test.py
"""Task 9: reflow_file -- both modes, against a hand-built minimal .cuig-shaped file."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))

from reflow import reflow_file  # noqa: E402
from devices import ORIENTATION_ENUM  # noqa: E402
import layout  # noqa: E402
import compare  # noqa: E402

OUT = Path(__file__).resolve().parent / "Phase5bReflowSmoke"
OUT.mkdir(parents=True, exist_ok=True)


def make_file(path: Path, css: str) -> None:
    # Minimal but structurally real .cuig: FileMetadata/Html/Css/PageAttributes, in
    # the confirmed fixed order (harness/compare.py::SECTION_ORDER), so
    # harness.compare.round_trip_check can verify this task never corrupts the file
    # outside the Css section.
    path.write_text(
        "{FileMetadata}\nSchema = \"1.0.0.0\"\n"
        "\n{Html}\n<div id=\"i1\"></div><div id=\"i2\"></div><div id=\"i3\"></div>\n"
        f"\n{{Css}}\n{css}\n"
        "\n{PageAttributes}\n\n[Attributes]\nName = \"P\"\n",
        encoding="utf-8",
    )


primary = {"width": 1280, "height": 800, "orientation": ORIENTATION_ENUM["landscape"]}
smaller = {"width": 640, "height": 400, "orientation": ORIENTATION_ENUM["landscape"]}

primary_query = layout.orientation_media_query("landscape", 1280, 800)
smaller_query = layout.orientation_media_query("landscape", 640, 400)
source_css = (
    f"@media {primary_query}{{"
    "#i1{display: block; left: 800px; top: 20px; position: absolute; width: 100px; height: 50px;}"
    "#i2{display: block; left: 950px; top: 20px; position: absolute; width: 100px; height: 50px;}"
    "}"
)

# --- Case A: pin_existing with an EMPTY target block (Trigger 1's case) --------------
path_a = OUT / "CaseA.cuig"
make_file(path_a, source_css)
result_a = reflow_file(path_a, target_resolution=smaller, source_resolution=primary, mode="pin_existing")
assert result_a.warnings == [], f"expected no warnings, got {result_a.warnings}"
assert compare.round_trip_check(path_a), "reflow_file must not corrupt Html/PageAttributes/FileMetadata"
new_css = compare.parse_file(path_a).sections[2][2]  # Css is the 3rd section: FileMetadata, Html, Css, PageAttributes
new_block = layout.find_media_block(new_css, smaller_query)
assert new_block is not None, "expected a new @media block for the smaller resolution"
new_elements = layout.parse_position_rules(new_block)
assert set(new_elements) == {"i1", "i2"}
assert new_elements["i1"]["left"] + new_elements["i1"]["width"] <= 640
assert new_elements["i2"]["left"] + new_elements["i2"]["width"] <= 640
print("Case A (pin_existing, empty target = Trigger 1): OK")

# --- Case B: pin_existing with a NON-EMPTY target -- pinned element must be byte-identical,
#     new element i3 is positioned (via row/wrap/stack) already on-canvas at (20,10),
#     deliberately overlapping the pinned i1's TARGET rect (0,0,50,50) -- this is what
#     actually gets checked for the overlap warning, not i3's source-resolution position.
path_b = OUT / "CaseB.cuig"
existing_target_block = "#i1{display: block; left: 0px; top: 0px; position: absolute; width: 50px; height: 50px;}"
source_with_new = (
    f"@media {primary_query}{{"
    "#i1{display: block; left: 800px; top: 20px; position: absolute; width: 100px; height: 50px;}"
    "#i3{display: block; left: 20px; top: 10px; position: absolute; width: 40px; height: 20px;}"
    "}"
    f"@media {smaller_query}{{{existing_target_block}}}"
)
make_file(path_b, source_with_new)
result_b = reflow_file(path_b, target_resolution=smaller, source_resolution=primary, mode="pin_existing")
assert compare.round_trip_check(path_b)
css_b = compare.parse_file(path_b).sections[2][2]
block_b = layout.find_media_block(css_b, smaller_query)
elements_b = layout.parse_position_rules(block_b)
assert elements_b["i1"] == {"left": 0, "top": 0, "width": 50, "height": 50, "z_index": None, "extra_vars": {}}, "pinned element must be untouched"
assert elements_b["i3"] == {"left": 20, "top": 10, "width": 40, "height": 20, "z_index": None, "extra_vars": {}}, "i3 is already on-canvas at its source position, so X/Y Tier 1 apply zero offset"
assert any("i3" in w and "i1" in w for w in result_b.warnings), f"expected an overlap warning naming i3 and i1, got {result_b.warnings}"
print("Case B (pin_existing, non-empty target, pinned preserved + overlap flagged): OK")

# --- Case C: full_refit -- ignores whatever was in target, refits everything fresh --
path_c = OUT / "CaseC.cuig"
make_file(path_c, source_with_new)
result_c = reflow_file(path_c, target_resolution=smaller, source_resolution=primary, mode="full_refit")
assert compare.round_trip_check(path_c)
css_c = compare.parse_file(path_c).sections[2][2]
block_c = layout.find_media_block(css_c, smaller_query)
elements_c = layout.parse_position_rules(block_c)
assert set(elements_c) == {"i1", "i3"}
assert elements_c["i1"] != {"left": 0, "top": 0, "width": 50, "height": 50, "z_index": None, "extra_vars": {}}, "full_refit must NOT preserve the old target position -- proves the two modes differ"
print("Case C (full_refit, old target position discarded): OK")

# --- Case D (added 2026-09-09, task review): regression guard for two bugs found by
#     review -- (1) universal-newline translation in Path.read_text/write_text
#     silently rewrote every line ending in the file (LF -> CRLF on Windows), breaking
#     the "leave everything outside Css byte-identical" contract for any non-native-
#     newline file; (2) compare.round_trip_check alone can't catch this since it only
#     verifies the file splits/reassembles self-consistently, not that content matches
#     what was there BEFORE reflow_file ran -- which is exactly why Case A/B/C's
#     round_trip_check calls didn't catch it. This case writes a hand-built LF-only
#     file with write_bytes (never silently re-encoded to the platform's native line
#     ending the way write_text would), and compares the non-Css sections' bytes
#     before vs. after reflow_file, not just internal self-consistency.
path_d = OUT / "CaseD.cuig"
path_d.write_bytes(
    b'{FileMetadata}\nSchema = "1.0.0.0"\n'
    b'\n{Html}\n<div id="i1"></div><div id="i2"></div>\n'
    + f"\n{{Css}}\n{source_css}\n".encode("utf-8")
    + b'\n{PageAttributes}\n\n[Attributes]\nName = "P"\n'
)
before_sections = {name: content for name, _, content in compare.parse_file(path_d).sections}
result_d = reflow_file(path_d, target_resolution=smaller, source_resolution=primary, mode="pin_existing")
assert result_d.warnings == [], f"expected no warnings, got {result_d.warnings}"
assert compare.round_trip_check(path_d)
after_sections = {name: content for name, _, content in compare.parse_file(path_d).sections}
for section_name in ("FileMetadata", "Html", "PageAttributes"):
    assert after_sections[section_name] == before_sections[section_name], (
        f"{section_name} section must be byte-identical (including line endings) "
        "before vs. after reflow_file -- reflow_file must only ever touch Css"
    )
assert b"\r\n" not in path_d.read_bytes(), "reflow_file must not introduce CRLF into an LF-only file"
print("Case D (LF-only file, non-Css sections byte-identical before/after reflow_file): OK")

# --- Case E (added 2026-09-09, task review): malformed input must produce a warning,
#     never raise -- reflow_file's first draft let a StopIteration (missing {Css}
#     section) escape uncaught.
path_e = OUT / "CaseE.cuig"
path_e.write_text(
    "{FileMetadata}\nSchema = \"1.0.0.0\"\n\n{Html}\n<div id=\"i1\"></div>\n"
    "\n{PageAttributes}\n\n[Attributes]\nName = \"P\"\n",  # no {Css} section at all
    encoding="utf-8",
)
result_e = reflow_file(path_e, target_resolution=smaller, source_resolution=primary, mode="pin_existing")
assert any("Css" in w for w in result_e.warnings), f"expected a warning naming the missing Css section, got {result_e.warnings}"
print("Case E (missing {Css} section produces a warning, does not raise): OK")

# --- Case F (added 2026-09-09, task review): an invalid mode must always raise,
#     regardless of whether the target block happens to be empty -- the first draft
#     only validated mode AFTER branching on the target block's emptiness, so a typo'd
#     mode silently performed a full refit instead of raising when the target was empty.
path_f = OUT / "CaseF.cuig"
make_file(path_f, source_css)  # empty target block -- the branch that used to skip validation
try:
    reflow_file(path_f, target_resolution=smaller, source_resolution=primary, mode="pin_exsiting")  # typo, deliberate
    assert False, "expected ValueError for an invalid mode, even with an empty target block"
except ValueError:
    pass
print("Case F (invalid mode always raises, independent of target-block emptiness): OK")

print("\nTASK 9: reflow_file -- ALL CHECKS PASSED")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python generator/_test_output/reflow_task9_reflow_file_test.py`
Expected: `ImportError: cannot import name 'reflow_file'`

- [ ] **Step 3: Implement**

Append to `generator/reflow.py` (add `re`, `dataclasses`, `pathlib`, and `layout` to the
imports at the top of the file):

```python
import re
from dataclasses import dataclass, field
from pathlib import Path

import layout

_SECTION_RE = re.compile(r"^\{(\w+)\}[ \t]*\r?\n?", re.MULTILINE)


def _read_sections(path: Path) -> tuple[str, list[tuple[str, str, str]]]:
    """Split a .cuig/.cuiw's raw text into (name, header_text, content) triples, in
    order -- same section-splitting rule as project.py::read_cuip / harness/compare.py
    (fixed FileMetadata/Html/Css/PageAttributes header-per-line convention). Kept local
    (not imported from harness/) matching this project's existing precedent of each
    writer owning its own small section reader rather than depending on the harness
    verification tool.

    CORRECTED 2026-09-09 (task review): Path.read_text()/write_text() perform universal
    newline translation -- '\\r\\n'/'\\r' are normalized to '\\n' on read, and '\\n' is
    re-expanded to the platform's os.linesep on write. On Windows that silently turns
    every bare-LF line ending in the file into CRLF, breaking this function's whole
    contract (leave everything outside the Css section byte-identical) for any file
    that isn't already using the platform's native line endings. Fixed by opening with
    `newline=""`, which disables translation in both directions -- whatever line
    endings the file already had are read and written back completely unchanged."""
    with open(path, "r", encoding="utf-8", newline="") as f:
        raw = f.read()
    matches = list(_SECTION_RE.finditer(raw))
    preamble = raw[: matches[0].start()] if matches else raw
    sections = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
        sections.append((m.group(1), m.group(0), raw[start:end]))
    return preamble, sections


def _write_sections(path: Path, preamble: str, sections: list[tuple[str, str, str]]) -> None:
    """See _read_sections' CORRECTED note -- newline="" here too, for the same reason."""
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(preamble + "".join(header + content for _, header, content in sections))


@dataclass
class ReflowResult:
    warnings: list[str] = field(default_factory=list)


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

    fitted: dict[str, dict] = {}
    for eid, e in elements.items():
        x, y = x_fit[eid], y_fit[eid]
        extra_vars: dict[str, str] = {}
        for name, value in e.get("extra_vars", {}).items():
            lname = name.lower()
            numeric = float(value[:-2]) if value.endswith("px") else None
            # CORRECTED 2026-09-09 (task review): must use int() truncation, matching
            # fit_axis's/stack_rows's own Tier 3 convention exactly (round() was
            # reintroducing the "outer width/height vs. --ch5-button--* var disagree"
            # class of bug this codebase already fixed once, Phase 4 -- a mirrored var
            # must equal the property it mirrors bit-for-bit, which only holds if both
            # use the same rounding function).
            if numeric is not None and "width" in lname:
                extra_vars[name] = f"{max(1, int(numeric * x['scale']))}px"
            elif numeric is not None and "height" in lname:
                extra_vars[name] = f"{max(1, int(numeric * y['scale']))}px"
            else:
                extra_vars[name] = value  # not a width/height-mirroring var -- carry through unscaled
        fitted[eid] = {
            "left": x["pos"], "top": y["top"], "width": x["size"], "height": y["height"],
            "z_index": e.get("z_index"), "extra_vars": extra_vars,
        }
    return fitted


def reflow_file(path: Path, target_resolution: dict, source_resolution: dict, mode: str = "pin_existing") -> ReflowResult:
    """Add or update `target_resolution`'s @media block in `path` so it has a position
    rule for every element `source_resolution`'s block has. See the spec's Algorithm
    section for `mode` semantics (pin_existing default vs. full_refit).

    CORRECTED 2026-09-09 (task review): every failure mode below must produce a
    warning and a clean ReflowResult return, never raise -- per the spec's Error
    handling section ("never a hard crash that aborts reflowing the rest of the
    project's files"), which this function's own first draft violated in three
    places: a missing {Css} section raised a bare StopIteration from the `next(...)`
    call with no predicate default; a malformed/unterminated @media block raised
    ValueError out of layout.find_media_block(_span); and a position rule with a
    non-"Npx" value (or missing a required property) raised ValueError/KeyError out
    of layout.parse_position_rules. All three are now caught and turned into warnings.
    `mode` is also now validated up front, before any other branch -- previously an
    invalid mode only raised when the target block was non-empty, silently performing
    a full refit instead when it was empty/missing, an inconsistency also caught by
    task review."""
    if mode not in ("pin_existing", "full_refit"):
        raise ValueError(f"unknown mode {mode!r} -- expected 'pin_existing' or 'full_refit'")

    warnings: list[str] = []
    preamble, sections = _read_sections(path)
    css_index = next((i for i, (name, _, _) in enumerate(sections) if name == "Css"), None)
    if css_index is None:
        warnings.append(f"{path.name}: no {{Css}} section found -- skipped")
        return ReflowResult(warnings=warnings)
    css_text = sections[css_index][2]

    source_orientation = _orientation_name(source_resolution)
    target_orientation = _orientation_name(target_resolution)
    source_query = layout.orientation_media_query(source_orientation, source_resolution["width"], source_resolution["height"])
    target_query = layout.orientation_media_query(target_orientation, target_resolution["width"], target_resolution["height"])

    try:
        source_block = layout.find_media_block(css_text, source_query)
    except ValueError as e:
        warnings.append(f"{path.name}: source block for {source_query} didn't parse cleanly -- {e} -- skipped")
        return ReflowResult(warnings=warnings)
    if source_block is None:
        warnings.append(f"{path.name}: no existing @media block for source resolution ({source_query}) -- skipped")
        return ReflowResult(warnings=warnings)
    try:
        source_elements = layout.parse_position_rules(source_block)
    except (ValueError, KeyError) as e:
        warnings.append(f"{path.name}: source block for {source_query} didn't parse cleanly -- {e} -- skipped")
        return ReflowResult(warnings=warnings)
    if not source_elements:
        warnings.append(f"{path.name}: source block for {source_query} parsed but contained no position rules -- skipped")
        return ReflowResult(warnings=warnings)

    try:
        target_span = layout.find_media_block_span(css_text, target_query)
    except ValueError as e:
        warnings.append(f"{path.name}: target block for {target_query} didn't parse cleanly -- {e} -- skipped")
        return ReflowResult(warnings=warnings)
    target_block = layout.find_media_block(css_text, target_query) if target_span else None
    try:
        target_elements = layout.parse_position_rules(target_block) if target_block else {}
    except (ValueError, KeyError) as e:
        warnings.append(f"{path.name}: target block for {target_query} didn't parse cleanly -- {e} -- skipped")
        return ReflowResult(warnings=warnings)

    if mode == "full_refit" or not target_elements:
        pinned, to_fit = {}, source_elements
    else:
        new_ids, pinned_ids = find_new_elements(source_elements, target_elements)
        pinned = {i: target_elements[i] for i in pinned_ids}
        to_fit = {i: source_elements[i] for i in new_ids}

    if not to_fit:
        warnings.append(f"{path.name}: no new elements to fit for {target_query} -- skipped")
        return ReflowResult(warnings=warnings)

    fitted = _fit_group(to_fit, target_resolution["width"], target_resolution["height"], path, target_query, warnings)
    if fitted is None:
        return ReflowResult(warnings=warnings)

    if mode == "pin_existing" and pinned:
        for new_id, pinned_id in check_overlaps(pinned, fitted):
            warnings.append(
                f"{path.name}: new element {new_id!r} may overlap pinned element "
                f"{pinned_id!r} in {target_query} -- review placement in Construct"
            )

    all_elements = {**pinned, **fitted}
    new_block = layout.build_reflow_block(all_elements, target_orientation, target_resolution["width"], target_resolution["height"])

    if target_span is not None:
        start, end = target_span
        css_text = css_text[:start] + new_block + css_text[end:]
    else:
        # CORRECTED 2026-09-09 (Task 9's own TDD cycle caught this): appending
        # new_block onto the raw end of css_text lands it AFTER the Css section's own
        # trailing whitespace (e.g. "...}\n\n"), directly abutting the next section's
        # header with no separating newline ("...}<new_block>{PageAttributes}") --
        # _SECTION_RE (and, per its own docstring, real Construct's header scan) only
        # recognizes a header at the start of a physical line, so this silently
        # swallows every section after Css into Css's own content. Fixed by inserting
        # new_block before the trailing whitespace instead of after it, so the
        # original newline(s) separating Css from the next section are preserved.
        stripped = css_text.rstrip()
        css_text = stripped + new_block + css_text[len(stripped):]
    sections[css_index] = ("Css", sections[css_index][1], css_text)

    _write_sections(path, preamble, sections)
    return ReflowResult(warnings=warnings)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python generator/_test_output/reflow_task9_reflow_file_test.py`
Expected: `TASK 9: reflow_file -- ALL CHECKS PASSED`

- [ ] **Step 5: Commit**

```bash
git add generator/reflow.py generator/_test_output/reflow_task9_reflow_file_test.py
git commit -m "$(cat <<'EOF'
Reflow task 9: reflow_file -- both modes, row/wrap/stack-aware

_fit_group now runs detect_rows -> wrap_rows -> per-row fit_axis (X) ->
stack_rows (Y) instead of a single flat fit_axis call per axis, so
reflow_file automatically gets the new row-wrap behavior. pin_existing
(default): pinned elements re-emitted byte-identical, only new elements
go through row detection and fitting, overlap-with-pinned is checked and
reported as a warning (best-effort, never blocks the write). full_refit:
ignores whatever was in the target, refits everything from source fresh.
An empty target block (Trigger 1's case) degenerates cleanly to
pin_existing with zero pinned elements, per the spec.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01Nw79wQq7o3YvzNBtP5GiEV
EOF
)"
```

---

## Task 10: Wire into `add_resolutions_to_project`, end-to-end scenarios (incl. row-wrap), doc writeup

**Files:**
- Modify: `generator/project.py`
- Modify: `docs/architecture/10-reflow.md`
- Test: `generator/_test_output/reflow_task10_integration_test.py`

**Interfaces:**
- Consumes: `reflow.choose_source_resolution`, `reflow.reflow_file` (Tasks 8-9).
- Changes: `add_resolutions_to_project(cuip_path: Path, new_resolutions: list[dict]) -> list[str]`
  (return type changes from `None` to `list[str]` of aggregated warnings — additive,
  existing callers that ignore the return value are unaffected).

- [ ] **Step 1: Write the failing test**

```python
# generator/_test_output/reflow_task10_integration_test.py
"""Task 10: add_resolutions_to_project now reflows existing pages/widgets, end-to-end,
including the orientation-bootstrap case and a genuine row-wrap scenario."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))

from project import build_project_attributes, write_cuip, add_resolutions_to_project  # noqa: E402
from devices import read_catalog, to_project_resolution  # noqa: E402
from page import write_cuig  # noqa: E402
from elements import Element  # noqa: E402
import layout  # noqa: E402
import compare  # noqa: E402

OUT = Path(__file__).resolve().parent / "Phase5bReflowIntegration"
OUT.mkdir(parents=True, exist_ok=True)
catalog = read_catalog()

tsw = to_project_resolution(catalog.by_id_name("TSW-1070"))  # 1280x800 landscape
attrs, drs = build_project_attributes(name="ReflowIntegration", sdk_id="CH5:2.18.0", resolutions=[tsw])
cuip_path = OUT / "ReflowIntegration.cuip"
write_cuip(cuip_path, attrs, drs)

# A page with one element deliberately near the right/bottom edge of the 1280x800 canvas.
primary_query = layout.orientation_media_query("landscape", 1280, 800)
element_id = "iedge1"
css = (
    f"@media (max-width: 99999px){{#{element_id}{{display: block; left: 1100px; top: 700px; position: absolute; z-index: 1; width: 150px; height: 90px;}}}}"
    f"@media {primary_query}{{#{element_id}{{display: block; left: 1100px; top: 700px; position: absolute; width: 150px; height: 90px;}}}}"
)
page_path = OUT / "EdgePage.cuig"
write_cuig(page_path, [("Name", "EdgePage"), ("PageMode", "absolute"), ("Id", "p1"), ("StartPage", "True"), ("PreloadPage", "True"), ("CachePage", "False"), ("VisibilityJoin", "0"), ("DisplayBackgroundColor", "False")], html=f'<div id="{element_id}"></div>', css=css, elements=[Element(type="Ch5 Button", attributes=[("id", element_id)])])

# --- Scenario 1: add a smaller landscape resolution (forces move/compact) -----------
smaller = to_project_resolution(catalog.by_id_name("TST-1080", orientation="landscape"))
smaller["width"], smaller["height"] = 640, 360  # deliberately smaller than the element's own position, to force tier 1/2 to actually do something
warnings = add_resolutions_to_project(cuip_path, [smaller])
assert isinstance(warnings, list), "add_resolutions_to_project must now return a list of warnings"
assert compare.round_trip_check(cuip_path)
assert compare.round_trip_check(page_path), "reflow must not corrupt the page file"

new_css = compare.parse_file(page_path).sections[2][2]
smaller_query = layout.orientation_media_query("landscape", 640, 360)
new_block = layout.find_media_block(new_css, smaller_query)
assert new_block is not None, "expected a new @media block for the smaller resolution"
fitted = layout.parse_position_rules(new_block)
assert element_id in fitted
assert fitted[element_id]["left"] + fitted[element_id]["width"] <= 640, "element must be on-canvas (right edge)"
assert fitted[element_id]["top"] + fitted[element_id]["height"] <= 360, "element must be on-canvas (bottom edge)"
print("Scenario 1 (edge element, smaller landscape resolution): on-canvas -- OK")

# --- Scenario 2: orientation-bootstrap -- add a portrait resolution to a landscape-only project
portrait = to_project_resolution(catalog.by_id_name("TST-1080", orientation="portrait"))
warnings2 = add_resolutions_to_project(cuip_path, [portrait])
assert compare.round_trip_check(page_path)
portrait_query = layout.orientation_media_query("portrait", portrait["width"], portrait["height"])
portrait_css = compare.parse_file(page_path).sections[2][2]
portrait_block = layout.find_media_block(portrait_css, portrait_query)
assert portrait_block is not None, "orientation-bootstrap must still produce a block (source = the other orientation's primary)"
portrait_fitted = layout.parse_position_rules(portrait_block)
assert element_id in portrait_fitted
assert portrait_fitted[element_id]["left"] + portrait_fitted[element_id]["width"] <= portrait["width"]
assert portrait_fitted[element_id]["top"] + portrait_fitted[element_id]["height"] <= portrait["height"]
print("Scenario 2 (orientation-bootstrap, portrait added to landscape-only project): OK")

# --- Scenario 3: genuine row-wrap -- a 4-button single row onto a much narrower resolution
button_specs = [("b0", 0), ("b1", 180), ("b2", 360), ("b3", 540)]  # left offsets; all top=20, width150, height90
catch_all_rules = "".join(
    f"#{bid}{{display: block; left: {left}px; top: 20px; position: absolute; z-index: 1; width: 150px; height: 90px;}}"
    for bid, left in button_specs
)
device_rules = "".join(
    f"#{bid}{{display: block; left: {left}px; top: 20px; position: absolute; width: 150px; height: 90px;}}"
    for bid, left in button_specs
)
css3 = f"@media (max-width: 99999px){{{catch_all_rules}}}" f"@media {primary_query}{{{device_rules}}}"
html3 = "".join(f'<div id="{bid}"></div>' for bid, _ in button_specs)
elements3 = [Element(type="Ch5 Button", attributes=[("id", bid)]) for bid, _ in button_specs]
page_path3 = OUT / "WrapPage.cuig"
write_cuig(page_path3, [("Name", "WrapPage"), ("PageMode", "absolute"), ("Id", "p2"), ("StartPage", "False"), ("PreloadPage", "True"), ("CachePage", "False"), ("VisibilityJoin", "0"), ("DisplayBackgroundColor", "False")], html=html3, css=css3, elements=elements3)

narrow = to_project_resolution(catalog.by_id_name("TST-1080", orientation="landscape"))
narrow["width"], narrow["height"] = 400, 300
warnings4 = add_resolutions_to_project(cuip_path, [narrow])
assert compare.round_trip_check(page_path3)

narrow_query = layout.orientation_media_query("landscape", 400, 300)
narrow_css = compare.parse_file(page_path3).sections[2][2]
narrow_block = layout.find_media_block(narrow_css, narrow_query)
assert narrow_block is not None
fitted3 = layout.parse_position_rules(narrow_block)
assert set(fitted3) == {"b0", "b1", "b2", "b3"}

# No element scaled down -- wrap must be preferred over scaling, per the approved tier order.
for bid in fitted3:
    assert fitted3[bid]["width"] == 150 and fitted3[bid]["height"] == 90, f"{bid} was scaled, expected wrap instead: {fitted3[bid]}"

# The row actually split -- more than one distinct top value among the 4 elements.
tops = {fitted3[bid]["top"] for bid in fitted3}
assert len(tops) > 1, f"expected the row to wrap onto more than one line, got a single top value: {tops}"

# On-canvas and pairwise non-overlapping (direct AABB check across ALL elements, not
# just within a row -- proving the cross-row Y-separation argument holds in practice).
def overlaps(r1, r2):
    return not (
        r1["left"] + r1["width"] <= r2["left"] or r2["left"] + r2["width"] <= r1["left"]
        or r1["top"] + r1["height"] <= r2["top"] or r2["top"] + r2["height"] <= r1["top"]
    )

ids3 = list(fitted3)
for bid in ids3:
    assert fitted3[bid]["left"] + fitted3[bid]["width"] <= 400
    assert fitted3[bid]["top"] + fitted3[bid]["height"] <= 300
for i in range(len(ids3)):
    for j in range(i + 1, len(ids3)):
        assert not overlaps(fitted3[ids3[i]], fitted3[ids3[j]]), f"overlap: {ids3[i]} vs {ids3[j]}"
print("Scenario 3 (row-wrap, 4-button row onto a much narrower resolution): OK")

# --- Regression: existing Phase 5 behavior (no .cuig/.cuiw files present) unaffected -
attrs0, drs0 = build_project_attributes(name="NoPages", sdk_id="CH5:2.18.0")
zero_path = OUT / "NoPages.cuip"
write_cuip(zero_path, attrs0, drs0)
warnings3 = add_resolutions_to_project(zero_path, [tsw])
assert warnings3 == [], "adding a resolution to a project with no pages/widgets must produce no warnings"
assert compare.round_trip_check(zero_path)
print("Regression: add_resolutions_to_project with zero pages/widgets still works: OK")

print("\nTASK 10: end-to-end integration -- ALL CHECKS PASSED")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python generator/_test_output/reflow_task10_integration_test.py`
Expected: `AssertionError: add_resolutions_to_project must now return a list of warnings` (it
currently returns `None`) — confirming the wiring isn't in place yet.

- [ ] **Step 3: Implement**

In `generator/project.py`, add `import reflow` near the top (alongside the existing
`from devices import ...`-style local imports), then replace `add_resolutions_to_project`:

```python
def add_resolutions_to_project(cuip_path: Path, new_resolutions: list[dict]) -> list[str]:
    """Add one or more already-shaped resolution dicts (see generator/devices.py::
    to_project_resolution) to an existing project's .cuip, updating `DeviceResolutionIds`
    and `{DeviceResolutionSource}` and marking `ContractIsStale`. Mirrors
    build_project_attributes' own DeviceResolutionIds/DeviceResolutionSource wiring, so a
    project ends up in the identical shape whether its resolutions were set at creation
    time or added afterward.

    Also reflows every existing *.cuig/*.cuiw in the project's folder so each newly-added
    resolution gets a correctly-fitted @media block for whatever elements already exist
    (see generator/reflow.py and docs/superpowers/specs/2026-09-08-multi-resolution-
    reflow-design.md) -- returns the aggregated list of any reflow warnings (e.g. a new
    element flagged as possibly overlapping a pinned one), never raises for them.
    """
    import reflow

    attrs, device_resolution_source, metadata = read_cuip(cuip_path)
    project_id = dict(attrs)["Id"]
    project_dir = cuip_path.parent
    warnings: list[str] = []

    for r in new_resolutions:
        existing_before = list(device_resolution_source)
        source = reflow.choose_source_resolution(existing_before, r)
        device_resolution_source.append({"ProjectId": project_id, **r})
        if source is not None:
            page_files = list(project_dir.glob("*.cuig")) + list(project_dir.glob("*.cuiw"))
            for page_path in page_files:
                result = reflow.reflow_file(page_path, target_resolution=r, source_resolution=source, mode="pin_existing")
                warnings.extend(result.warnings)

    ids_csv = ",".join(r["id"] for r in device_resolution_source)

    keys = [k for k, _ in attrs]
    if "DeviceResolutionIds" in keys:
        override_attr(attrs, "DeviceResolutionIds", ids_csv)
    else:
        attrs.insert(keys.index("DefaultFontFamily") + 1, ("DeviceResolutionIds", ids_csv))
    override_attr(attrs, "ContractIsStale", "true")

    write_cuip(cuip_path, attrs, device_resolution_source, metadata=metadata)
    return warnings
```

(The `import reflow` is placed inside the function, matching this file's existing
`__main__` block's own local-import style, and avoids a module-level circular import
risk since `reflow.py` doesn't import `project.py`, but keeping it function-local costs
nothing and matches precedent already in this file.)

- [ ] **Step 4: Run test to verify it passes**

Run: `python generator/_test_output/reflow_task10_integration_test.py`
Expected: `TASK 10: end-to-end integration -- ALL CHECKS PASSED`

- [ ] **Step 5: Run every prior smoke test to confirm zero regressions**

Run:
```bash
cd generator/_test_output
for f in phase2_smoke_test.py phase3_smoke_test.py phase4_smoke_test.py phase5_smoke_test.py phase9_assets_smoke_test.py reflow_task1_media_query_test.py reflow_task2_parse_build_test.py reflow_task3_fit_axis_test.py reflow_task4_detect_rows_test.py reflow_task5_wrap_rows_test.py reflow_task6_stack_rows_test.py reflow_task7_diff_overlap_test.py reflow_task8_source_selection_test.py reflow_task9_reflow_file_test.py reflow_task10_integration_test.py; do
  python "$f" || echo "FAILED: $f"
done
```
Expected: every file prints its own success line, no `FAILED:` lines.

- [ ] **Step 6: Generate into the real on-disk verification project for manual Construct check**

This project's standing practice (every prior phase) is to also produce a real,
Construct-openable result for the user to confirm visually — automated tests can't see
the canvas. Using the same pattern as Phase 5/9's `C:\Solutions\ClaudeGenTest\
GenTestProject`: add a second, smaller landscape resolution to that existing verification
project via `add_resolutions_to_project`, so the user can switch resolutions in Construct
and confirm the existing button is repositioned on-canvas, not clipped.

```python
# generator/_test_output/reflow_manual_verification_setup.py
"""Not an automated test -- prepares the real on-disk verification project for the user
to check in Construct (this project's standing practice, see Phase 5/9)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from project import add_resolutions_to_project  # noqa: E402
from devices import read_catalog, to_project_resolution  # noqa: E402

GEN_TEST_CUIP = Path(r"C:\Solutions\ClaudeGenTest\GenTestProject\GenTestProject.cuip")
catalog = read_catalog()
smaller = to_project_resolution(catalog.by_id_name("TST-1080", orientation="landscape"))
smaller["width"], smaller["height"] = 640, 360

warnings = add_resolutions_to_project(GEN_TEST_CUIP, [smaller])
print(f"Added a 640x360 landscape resolution to {GEN_TEST_CUIP}.")
print(f"Warnings: {warnings or '(none)'}")
print("Open the project in Construct, switch to the new resolution, and confirm the "
      "existing button is on-canvas (not clipped) and not overlapping anything.")
```

Run: `python generator/_test_output/reflow_manual_verification_setup.py`, then have the
user open `C:\Solutions\ClaudeGenTest\GenTestProject` in Construct and confirm. This
step's outcome depends on the user's confirmation — report back what they see rather
than assuming success.

- [ ] **Step 7: Finish the architecture doc writeup**

Append to `docs/architecture/10-reflow.md` (after the sections from Tasks 1 and 6):

```markdown
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

Confirmed via `generator/_test_output/reflow_task1..10_*.py` and manual Construct
verification against `C:\Solutions\ClaudeGenTest\GenTestProject` (see Task 10, Step 6).

**Not yet wired up:** Trigger 2 (the skill asking the user which mode to use when new
elements are added to an already-multi-resolution page) is a conversational/process
step at the skill layer per the spec's Integration section, not new code in
`generator/` -- `reflow_file`'s `mode` parameter is what a future skill-layer call would
choose between; this plan only builds and proves the underlying mechanism.
```

- [ ] **Step 8: Commit**

```bash
git add generator/project.py docs/architecture/10-reflow.md generator/_test_output/reflow_task10_integration_test.py generator/_test_output/reflow_manual_verification_setup.py
git commit -m "$(cat <<'EOF'
Reflow task 10: wire into add_resolutions_to_project, end-to-end scenarios

add_resolutions_to_project now calls reflow.reflow_file for every
*.cuig/*.cuiw in the project's folder, once per newly-added resolution,
using choose_source_resolution to pick which existing resolution to fit
from (same-orientation primary, or the other orientation's primary for
the bootstrap case). Return type changes from None to list[str]
(aggregated reflow warnings) -- additive, existing callers unaffected.
Scenario tests cover an edge-placed element landing on-canvas after a
smaller resolution is added, the orientation-bootstrap case, a genuine
row-wrap scenario (a 4-button single row split across two lines on a
much narrower resolution, with no element scaled down and a direct
pairwise AABB check confirming no overlaps), and zero regression when a
project has no pages/widgets yet. Manual Construct verification prepared
against the existing GenTestProject.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01Nw79wQq7o3YvzNBtP5GiEV
EOF
)"
```

- [ ] **Step 9: Update README.md**

Per this project's standing rule, update `README.md`'s Current phase and Log with this
phase's completion (multi-resolution reflow built and verified — both the resolution-add
trigger and the underlying mechanism Trigger 2 will call, including the row-wrap
behavior added in the 2026-09-09 design revision), and commit it in the same turn,
before reporting the plan complete.
