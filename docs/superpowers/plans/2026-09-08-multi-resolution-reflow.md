# Multi-resolution reflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make adding a resolution (or adding new controls to an already-multi-resolution
page) automatically produce a correctly-positioned `@media` block for every resolution
that's missing it, instead of leaving components off-canvas or absent entirely.

**Architecture:** A new `generator/reflow.py` module implements a per-axis, 3-tier fit
(move → compact whitespace → scale down) plus two modes (`pin_existing` default,
`full_refit`), building on two new low-level CSS parsing/building helpers added to the
existing `generator/layout.py`. `generator/project.py::add_resolutions_to_project` is
extended to call it automatically; a second call site (the skill layer, when adding new
elements to an existing multi-resolution page) is documented but not implemented here —
it just needs to call the same `reflow_file`, per the spec's Integration section.

**Tech Stack:** Python 3.11+ (stdlib only: `re`, `dataclasses`, `pathlib`). No new
dependencies. Tests are plain assert-script files run directly with `python`, matching
every existing `generator/_test_output/phaseN_smoke_test.py` in this repo — this project
does not use pytest.

**Spec:** `docs/superpowers/specs/2026-09-08-multi-resolution-reflow-design.md`

## Global Constraints

- Minimum visual gap between neighboring elements on an axis is **4px** (tiers 2 and 3).
- Position/size math is per-axis-independent (X: left/width, Y: top/height) — never
  jointly optimized, never 2D bin-packing.
- Elements never reorder relative to each other on an axis, and no tier may cause an
  element's on-axis gap to a same-tier neighbor to go negative — this is what the spec's
  no-new-overlap proof depends on. Do not "optimize" this away.
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
Claude-Session: https://claude.ai/code/session_015YVkY34nDqvRb7geVWPrVh
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
Claude-Session: https://claude.ai/code/session_015YVkY34nDqvRb7geVWPrVh
EOF
)"
```

---

## Task 3: `fit_axis` — the 3-tier per-axis algorithm

**Files:**
- Create: `generator/reflow.py`
- Test: `generator/_test_output/reflow_task3_fit_axis_test.py`

**Interfaces:**
- Produces:
  - `class AxisFitError(Exception)` — raised when `target_dim` can't fit even the
    mandatory `(n-1)*min_gap` floor gaps for the element count.
  - `fit_axis(items: list[tuple[str, int, int]], target_dim: int, min_gap: int = 4) -> dict[str, dict]`
    — `items` is `[(element_id, pos, size)]` for one axis. Returns `{element_id:
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
result = fit_axis(items, target_dim=220)  # need span <= 220; sizes alone = 300 > 220 -- wait, must choose a target where compaction (not scaling) suffices
# sizes sum = 300; with 2 gaps at 4px floor minimum span = 300 + 8 = 308min possible via tier2 alone (no scaling)
result = fit_axis(items, target_dim=308)
assert result["a"]["scale"] == 1.0 and result["b"]["scale"] == 1.0 and result["c"]["scale"] == 1.0, "tier 2 must never resize"
assert result["a"]["size"] == 100 and result["b"]["size"] == 100 and result["c"]["size"] == 100
gap_ab = result["b"]["pos"] - (result["a"]["pos"] + result["a"]["size"])
gap_bc = result["c"]["pos"] - (result["b"]["pos"] + result["b"]["size"])
assert gap_ab >= 4 and gap_bc >= 4, f"gaps must never go below the 4px floor, got {gap_ab}, {gap_bc}"
assert result["c"]["pos"] + result["c"]["size"] - result["a"]["pos"] <= 308
print("tier 2 (compact): OK")

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
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = result[ids[i]], result[ids[j]]
            assert not overlaps(a["pos"], a["size"], b["pos"], b["size"]), f"overlap at target_dim={target}: {ids[i]} vs {ids[j]}"
print("no-overlap guarantee across all tiers: OK")

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
    many elements -- caller (reflow_file) catches this per-axis and reports a warning
    rather than crashing (see the spec's Error handling section)."""


def fit_axis(items: list[tuple[str, int, int]], target_dim: int, min_gap: int = 4) -> dict[str, dict]:
    """3-tier fit for one axis (X: left/width, or Y: top/height) of one group of
    elements being fit together. `items` is [(element_id, pos, size)] in any order.
    Returns {element_id: {"pos": int, "size": int, "scale": float}} -- scale is 1.0
    unless tier 3 (scale-down) applied.

    Tier 1 (move): if the group's bounding-box span already fits target_dim, shift
    everyone by one constant offset -- relative gaps are preserved exactly.
    Tier 2 (compact): otherwise, shrink internal gaps (order-preserving) toward a
    min_gap floor, linearly interpolated by how much reduction is still needed.
    Tier 3 (scale): if gaps are already at the floor and it's still not enough, scale
    every element's size by one shared factor (reserving room for the mandatory
    min_gap gaps first) and repack at exactly min_gap.

    See the spec's "Why this can't introduce new overlaps" for the proof this relies
    on: order is never changed, and no gap is ever allowed to go negative.
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
            element_id: {"pos": pos + offset, "size": size, "scale": 1.0}
            for element_id, pos, size in zip(ids, positions, sizes)
        }

    # Translate so the leading edge is 0 -- tiers 2/3 cascade positions from there.
    positions = [p - min_pos for p in positions]
    total_size = sum(sizes)
    total_gap = span - total_size
    needed_reduction = span - target_dim

    # --- Tier 2: order-preserving whitespace compaction ---------------------------
    if n > 1:
        gaps = [positions[i + 1] - (positions[i] + sizes[i]) for i in range(n - 1)]
        max_possible_reduction = max(0, total_gap - (n - 1) * min_gap)
        if max_possible_reduction > 0 and needed_reduction <= max_possible_reduction:
            shrink_ratio = needed_reduction / max_possible_reduction
            new_gaps = [max(min_gap, g - shrink_ratio * (g - min_gap)) for g in gaps]
            new_positions = [0]
            for i, size in enumerate(sizes[:-1]):
                new_positions.append(new_positions[-1] + size + new_gaps[i])
            return {
                element_id: {"pos": round(pos), "size": size, "scale": 1.0}
                for element_id, pos, size in zip(ids, new_positions, sizes)
            }

    # --- Tier 3: uniform scale-down, last resort, repacked at exactly min_gap -----
    available_for_sizes = target_dim - (n - 1) * min_gap
    if available_for_sizes <= 0:
        raise AxisFitError(
            f"target_dim {target_dim} can't fit even the mandatory {min_gap}px floor "
            f"gaps for {n} elements"
        )
    scale = available_for_sizes / total_size
    new_sizes = [max(1, round(size * scale)) for size in sizes]  # never collapse to 0px
    new_positions = [0]
    for size in new_sizes[:-1]:
        new_positions.append(new_positions[-1] + size + min_gap)
    return {
        element_id: {"pos": pos, "size": size, "scale": scale}
        for element_id, pos, size in zip(ids, new_positions, new_sizes)
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python generator/_test_output/reflow_task3_fit_axis_test.py`
Expected: `TASK 3: fit_axis -- ALL CHECKS PASSED`

- [ ] **Step 5: Commit**

```bash
git add generator/reflow.py generator/_test_output/reflow_task3_fit_axis_test.py
git commit -m "$(cat <<'EOF'
Reflow task 3: fit_axis, the 3-tier per-axis fit algorithm

Move (rigid translate) -> compact whitespace (order-preserving, 4px
floor, linear interpolation toward the floor) -> scale down (uniform
factor, reserves the mandatory floor gaps first, last resort). Raises
AxisFitError when even the floor gaps don't fit the element count.
Direct AABB pairwise checks in the test confirm no tier introduces a
new overlap across a range of target dimensions.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_015YVkY34nDqvRb7geVWPrVh
EOF
)"
```

---

## Task 4: `find_new_elements` / `check_overlaps`

**Files:**
- Modify: `generator/reflow.py`
- Test: `generator/_test_output/reflow_task4_diff_overlap_test.py`

**Interfaces:**
- Produces:
  - `find_new_elements(source_elements: dict[str, dict], target_elements: dict[str, dict]) -> tuple[set[str], set[str]]`
    — `(new_ids, pinned_ids)`.
  - `check_overlaps(pinned: dict[str, dict], new: dict[str, dict]) -> list[tuple[str, str]]`
    — pairwise AABB check, `[(new_id, pinned_id), ...]` for every conflicting pair.

- [ ] **Step 1: Write the failing test**

```python
# generator/_test_output/reflow_task4_diff_overlap_test.py
"""Task 4: find_new_elements (source/target id diff) and check_overlaps (pairwise AABB)."""
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

print("\nTASK 4: find_new_elements / check_overlaps -- ALL CHECKS PASSED")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python generator/_test_output/reflow_task4_diff_overlap_test.py`
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

Run: `python generator/_test_output/reflow_task4_diff_overlap_test.py`
Expected: `TASK 4: ... ALL CHECKS PASSED`

- [ ] **Step 5: Commit**

```bash
git add generator/reflow.py generator/_test_output/reflow_task4_diff_overlap_test.py
git commit -m "$(cat <<'EOF'
Reflow task 4: find_new_elements / check_overlaps

find_new_elements diffs source vs. target element ids into new/pinned
sets for pin_existing mode. check_overlaps is the pairwise AABB check
that surfaces the "best-effort, flagged" warning the spec calls for when
a newly-fit element overlaps a pinned one -- exactly-touching rectangles
correctly do not count as overlapping.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_015YVkY34nDqvRb7geVWPrVh
EOF
)"
```

---

## Task 5: `pick_primary` / `choose_source_resolution`

**Files:**
- Modify: `generator/reflow.py`
- Test: `generator/_test_output/reflow_task5_source_selection_test.py`

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
# generator/_test_output/reflow_task5_source_selection_test.py
"""Task 5: pick_primary / choose_source_resolution."""
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

print("\nTASK 5: pick_primary / choose_source_resolution -- ALL CHECKS PASSED")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python generator/_test_output/reflow_task5_source_selection_test.py`
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

Run: `python generator/_test_output/reflow_task5_source_selection_test.py`
Expected: `TASK 5: ... ALL CHECKS PASSED`

- [ ] **Step 5: Commit**

```bash
git add generator/reflow.py generator/_test_output/reflow_task5_source_selection_test.py
git commit -m "$(cat <<'EOF'
Reflow task 5: pick_primary / choose_source_resolution

Reuses Phase 5's devices.ORIENTATION_ENUM (converting its int encoding
to the string names layout.py's orientation_media_query expects).
choose_source_resolution implements the spec's "same-orientation primary,
else other orientation's primary (bootstrap), else nothing to reflow
from" rule.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_015YVkY34nDqvRb7geVWPrVh
EOF
)"
```

---

## Task 6: `reflow_file` — ties it all together, both modes

**Files:**
- Modify: `generator/reflow.py`
- Test: `generator/_test_output/reflow_task6_reflow_file_test.py`

**Interfaces:**
- Consumes: everything from Tasks 1-5 (`layout.orientation_media_query`,
  `layout.find_media_block_span/find_media_block`, `layout.parse_position_rules`,
  `layout.build_reflow_block`, `fit_axis`, `AxisFitError`, `find_new_elements`,
  `check_overlaps`, `_orientation_name`).
- Produces:
  - `@dataclass class ReflowResult: warnings: list[str] = field(default_factory=list)`
  - `reflow_file(path: Path, target_resolution: dict, source_resolution: dict, mode: str = "pin_existing") -> ReflowResult`
    — reads the file's `{Css}` section, fits new elements per mode, writes the file
    back untouched except for that one section's content (Html/PageAttributes/
    FileMetadata byte-identical).

- [ ] **Step 1: Write the failing test**

```python
# generator/_test_output/reflow_task6_reflow_file_test.py
"""Task 6: reflow_file -- both modes, against a hand-built minimal .cuig-shaped file."""
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
        "\n{Html}\n<div id=\"i1\"></div><div id=\"i2\"></div>\n"
        f"\n{{Css}}\n{css}\n"
        "\n{PageAttributes}\n\n[Attributes]\nName = \"P\"\n",
        encoding="utf-8",
    )


primary = {"width": 1280, "height": 800, "orientation": ORIENTATION_ENUM["landscape"]}
smaller = {"width": 640, "height": 400, "orientation": ORIENTATION_ENUM["landscape"]}

primary_query = layout.orientation_media_query("landscape", 1280, 800)
source_css = f"@media {primary_query}{{#i1{{display: block; left: 800px; top: 20px; position: absolute; width: 100px; height: 50px;}}#i2{{display: block; left: 950px; top: 20px; position: absolute; width: 100px; height: 50px;}}}}"

# --- Case A: pin_existing with an EMPTY target block (Trigger 1's case) --------------
path_a = OUT / "CaseA.cuig"
make_file(path_a, source_css)
result_a = reflow_file(path_a, target_resolution=smaller, source_resolution=primary, mode="pin_existing")
assert result_a.warnings == [], f"expected no warnings, got {result_a.warnings}"
assert compare.round_trip_check(path_a), "reflow_file must not corrupt Html/PageAttributes/FileMetadata"
new_css = compare.parse_file(path_a).sections[2][2]  # Css is the 3rd section: FileMetadata, Html, Css, PageAttributes
smaller_query = layout.orientation_media_query("landscape", 640, 400)
new_block = layout.find_media_block(new_css, smaller_query)
assert new_block is not None, "expected a new @media block for the smaller resolution"
new_elements = layout.parse_position_rules(new_block)
assert set(new_elements) == {"i1", "i2"}
assert new_elements["i1"]["left"] + new_elements["i1"]["width"] <= 640
assert new_elements["i2"]["left"] + new_elements["i2"]["width"] <= 640
print("Case A (pin_existing, empty target = Trigger 1): OK")

# --- Case B: pin_existing with a NON-EMPTY target -- pinned element must be byte-identical, plus overlap flagged
path_b = OUT / "CaseB.cuig"
# target already has i1 fitted (pinned); source now also has a NEW i3 near i1's fitted spot.
existing_target_block = "#i1{display: block; left: 0px; top: 0px; position: absolute; width: 50px; height: 50px;}"
source_with_new = (
    f"@media {primary_query}{{"
    "#i1{display: block; left: 800px; top: 20px; position: absolute; width: 100px; height: 50px;}"
    "#i3{display: block; left: 810px; top: 30px; position: absolute; width: 40px; height: 20px;}"  # deliberately near i1's fitted spot to force a flagged overlap
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
assert "i3" in elements_b, "new element must be fit into the target"
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

print("\nTASK 6: reflow_file -- ALL CHECKS PASSED")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python generator/_test_output/reflow_task6_reflow_file_test.py`
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
    verification tool."""
    raw = path.read_text(encoding="utf-8")
    matches = list(_SECTION_RE.finditer(raw))
    preamble = raw[: matches[0].start()] if matches else raw
    sections = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
        sections.append((m.group(1), m.group(0), raw[start:end]))
    return preamble, sections


def _write_sections(path: Path, preamble: str, sections: list[tuple[str, str, str]]) -> None:
    path.write_text(preamble + "".join(header + content for _, header, content in sections), encoding="utf-8")


@dataclass
class ReflowResult:
    warnings: list[str] = field(default_factory=list)


def _fit_group(
    elements: dict[str, dict], target_width: int, target_height: int,
    path: Path, query: str, warnings: list[str],
) -> dict[str, dict] | None:
    """Fit one group of elements (all of source in full_refit, or just the new ones in
    pin_existing) into target_width x target_height. None if either axis raises
    AxisFitError -- caller skips this target block entirely for this file, other files
    in the project are unaffected."""
    x_items = [(eid, e["left"], e["width"]) for eid, e in elements.items()]
    y_items = [(eid, e["top"], e["height"]) for eid, e in elements.items()]
    try:
        x_fit = fit_axis(x_items, target_width)
    except AxisFitError as e:
        warnings.append(f"{path.name}: X axis for {query} -- {e}")
        return None
    try:
        y_fit = fit_axis(y_items, target_height)
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
            if numeric is not None and "width" in lname:
                extra_vars[name] = f"{round(numeric * x['scale'])}px"
            elif numeric is not None and "height" in lname:
                extra_vars[name] = f"{round(numeric * y['scale'])}px"
            else:
                extra_vars[name] = value  # not a width/height-mirroring var -- carry through unscaled
        fitted[eid] = {
            "left": x["pos"], "top": y["pos"], "width": x["size"], "height": y["size"],
            "z_index": e.get("z_index"), "extra_vars": extra_vars,
        }
    return fitted


def reflow_file(path: Path, target_resolution: dict, source_resolution: dict, mode: str = "pin_existing") -> ReflowResult:
    """Add or update `target_resolution`'s @media block in `path` so it has a position
    rule for every element `source_resolution`'s block has. See the spec's Algorithm
    section for `mode` semantics (pin_existing default vs. full_refit)."""
    warnings: list[str] = []
    preamble, sections = _read_sections(path)
    css_index = next(i for i, (name, _, _) in enumerate(sections) if name == "Css")
    css_text = sections[css_index][2]

    source_orientation = _orientation_name(source_resolution)
    target_orientation = _orientation_name(target_resolution)
    source_query = layout.orientation_media_query(source_orientation, source_resolution["width"], source_resolution["height"])
    target_query = layout.orientation_media_query(target_orientation, target_resolution["width"], target_resolution["height"])

    source_block = layout.find_media_block(css_text, source_query)
    if source_block is None:
        warnings.append(f"{path.name}: no existing @media block for source resolution ({source_query}) -- skipped")
        return ReflowResult(warnings=warnings)
    source_elements = layout.parse_position_rules(source_block)
    if not source_elements:
        warnings.append(f"{path.name}: source block for {source_query} parsed but contained no position rules -- skipped")
        return ReflowResult(warnings=warnings)

    target_span = layout.find_media_block_span(css_text, target_query)
    target_block = layout.find_media_block(css_text, target_query) if target_span else None
    target_elements = layout.parse_position_rules(target_block) if target_block else {}

    if mode == "full_refit" or not target_elements:
        pinned, to_fit = {}, source_elements
    elif mode == "pin_existing":
        new_ids, pinned_ids = find_new_elements(source_elements, target_elements)
        pinned = {i: target_elements[i] for i in pinned_ids}
        to_fit = {i: source_elements[i] for i in new_ids}
    else:
        raise ValueError(f"unknown mode {mode!r} -- expected 'pin_existing' or 'full_refit'")

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
        css_text = css_text + new_block
    sections[css_index] = ("Css", sections[css_index][1], css_text)

    _write_sections(path, preamble, sections)
    return ReflowResult(warnings=warnings)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python generator/_test_output/reflow_task6_reflow_file_test.py`
Expected: `TASK 6: reflow_file -- ALL CHECKS PASSED`

- [ ] **Step 5: Commit**

```bash
git add generator/reflow.py generator/_test_output/reflow_task6_reflow_file_test.py
git commit -m "$(cat <<'EOF'
Reflow task 6: reflow_file -- both modes wired together

pin_existing (default): pinned elements re-emitted byte-identical, only
new elements go through fit_axis, overlap-with-pinned is checked and
reported as a warning (best-effort, never blocks the write). full_refit:
ignores whatever was in the target, refits everything from source fresh.
An empty target block (Trigger 1's case) degenerates cleanly to
pin_existing with zero pinned elements, per the spec.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_015YVkY34nDqvRb7geVWPrVh
EOF
)"
```

---

## Task 7: Wire into `add_resolutions_to_project`, end-to-end scenarios, doc writeup

**Files:**
- Modify: `generator/project.py`
- Modify: `docs/architecture/10-reflow.md`
- Test: `generator/_test_output/reflow_task7_integration_test.py`

**Interfaces:**
- Consumes: `reflow.choose_source_resolution`, `reflow.reflow_file` (Tasks 5-6).
- Changes: `add_resolutions_to_project(cuip_path: Path, new_resolutions: list[dict]) -> list[str]`
  (return type changes from `None` to `list[str]` of aggregated warnings — additive,
  existing callers that ignore the return value are unaffected).

- [ ] **Step 1: Write the failing test**

```python
# generator/_test_output/reflow_task7_integration_test.py
"""Task 7: add_resolutions_to_project now reflows existing pages/widgets, end-to-end,
including the orientation-bootstrap case and a tier-2/tier-3-forcing scenario."""
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

# --- Add a smaller landscape resolution (TSW-570-shaped, forces move/compact) --------
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

# --- Orientation-bootstrap: add a portrait resolution to a landscape-only project ----
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

# --- Existing Phase 5 behavior (no .cuig/.cuiw files present) must be unaffected -----
attrs0, drs0 = build_project_attributes(name="NoPages", sdk_id="CH5:2.18.0")
zero_path = OUT / "NoPages.cuip"
write_cuip(zero_path, attrs0, drs0)
warnings3 = add_resolutions_to_project(zero_path, [tsw])
assert warnings3 == [], "adding a resolution to a project with no pages/widgets must produce no warnings"
assert compare.round_trip_check(zero_path)
print("Regression: add_resolutions_to_project with zero pages/widgets still works: OK")

print("\nTASK 7: end-to-end integration -- ALL CHECKS PASSED")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python generator/_test_output/reflow_task7_integration_test.py`
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

Run: `python generator/_test_output/reflow_task7_integration_test.py`
Expected: `TASK 7: end-to-end integration -- ALL CHECKS PASSED`

- [ ] **Step 5: Run every prior smoke test to confirm zero regressions**

Run:
```bash
cd generator/_test_output
for f in phase2_smoke_test.py phase3_smoke_test.py phase4_smoke_test.py phase5_smoke_test.py phase9_assets_smoke_test.py reflow_task1_media_query_test.py reflow_task2_parse_build_test.py reflow_task3_fit_axis_test.py reflow_task4_diff_overlap_test.py reflow_task5_source_selection_test.py reflow_task6_reflow_file_test.py reflow_task7_integration_test.py; do
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

Append to `docs/architecture/10-reflow.md` (after the portrait-formula section from
Task 1):

```markdown
## Algorithm and integration summary

Full design: `docs/superpowers/specs/2026-09-08-multi-resolution-reflow-design.md`.
Implementation: `generator/reflow.py` (fit_axis, find_new_elements, check_overlaps,
pick_primary, choose_source_resolution, reflow_file, ReflowResult) plus new CSS
parsing/building helpers in `generator/layout.py` (find_media_block_span,
find_media_block, parse_position_rules, build_reflow_block). Wired into
`generator/project.py::add_resolutions_to_project`, which now also returns the
aggregated list of any reflow warnings (previously returned None).

Confirmed via `generator/_test_output/reflow_task1..7_*.py` and manual Construct
verification against `C:\Solutions\ClaudeGenTest\GenTestProject` (see Task 7, Step 6).

**Not yet wired up:** Trigger 2 (the skill asking the user which mode to use when new
elements are added to an already-multi-resolution page) is a conversational/process
step at the skill layer per the spec's Integration section, not new code in
`generator/` -- `reflow_file`'s `mode` parameter is what a future skill-layer call would
choose between; this plan only builds and proves the underlying mechanism.
```

- [ ] **Step 8: Commit**

```bash
git add generator/project.py docs/architecture/10-reflow.md generator/_test_output/reflow_task7_integration_test.py generator/_test_output/reflow_manual_verification_setup.py
git commit -m "$(cat <<'EOF'
Reflow task 7: wire into add_resolutions_to_project, end-to-end scenarios

add_resolutions_to_project now calls reflow.reflow_file for every
*.cuig/*.cuiw in the project's folder, once per newly-added resolution,
using choose_source_resolution to pick which existing resolution to fit
from (same-orientation primary, or the other orientation's primary for
the bootstrap case). Return type changes from None to list[str]
(aggregated reflow warnings) -- additive, existing callers unaffected.
Scenario tests cover an edge-placed element landing on-canvas after a
smaller resolution is added, the orientation-bootstrap case, and zero
regression when a project has no pages/widgets yet. Manual Construct
verification prepared against the existing GenTestProject.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_015YVkY34nDqvRb7geVWPrVh
EOF
)"
```

- [ ] **Step 9: Update README.md**

Per this project's standing rule, update `README.md`'s Current phase and Log with this
phase's completion (multi-resolution reflow built and verified — both the resolution-add
trigger and the underlying mechanism Trigger 2 will call), and commit it in the same
turn, before reporting the plan complete.
