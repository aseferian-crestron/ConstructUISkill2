"""
Multi-resolution reflow -- Phase 5 continuation.

Source-grounded, per docs/superpowers/specs/2026-09-08-multi-resolution-reflow-design.md
and docs/architecture/10-reflow.md.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from devices import ORIENTATION_ENUM

import layout
import sdk as sdk_module


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


def stack_rows(rows: list[list[str]], elements: dict[str, dict], target_height: int, min_gap: int = 4, source_height: int | None = None) -> dict[str, dict]:
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
    int, "scale": float}}.

    `source_height` -- ADDED 2026-09-10 (see docs/superpowers/specs/
    2026-09-10-reflow-centering-design.md): forwarded to the internal fit_axis call as
    `source_dim` so a vertically-centered source row-stack comes back centered in
    target_height instead of pinned to the top. One auto-detected decision for the
    whole stack (no fragment concept on this axis -- row-wrap only affects X-axis
    grouping, not what a row contributes to this Y-axis pseudo-item list)."""
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
    row_fit = fit_axis(row_items, target_height, min_gap=min_gap, source_dim=source_height)

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


def _size_selector_mapping(sdk: "sdk_module.UiSdk", tag_name: str) -> list[dict] | None:
    """The `idSelector` `classToVariableMapping` entry for `tag_name` (see
    ch5_button.py::button_size_css_vars, which this generalizes) -- `None` if the SDK
    has no such entry for this tag (most component types don't expose a size-mirroring
    CSS var at all)."""
    try:
        ctx = sdk.context_for(tag_name)
    except (KeyError, StopIteration):
        return None
    entry = next((e for e in ctx.get("classToVariableMapping", []) if e.get("className") == "idSelector"), None)
    return entry["propertyMapping"] if entry else None


def _component_size_css_vars(
    sdk: "sdk_module.UiSdk", tag_name: str, *, width: int, height: int, orientation: str = "horizontal",
) -> dict[str, str]:
    """Generic version of ch5_button.py::button_size_css_vars, driven by the same SDK
    `classToVariableMapping` schema for ANY component type, not just ch5-button --
    ADDED 2026-09-10 after a real user-authored page (ReflowTest.cuig) exposed that
    reflow's old scaling logic only recognized CSS var names containing the literal
    substrings "width"/"height", silently leaving `--ch5-dpad--regular-size` (which
    contains neither) unscaled -- the component kept rendering at its original size
    regardless of what the fitted box computed, which is what actually produced the
    visible overlap the user reported, not a flaw in the tier math itself. Returns
    {css_var_name: "Npx"} for every var this tag's schema maps from width/height;
    empty if the tag has no such mapping."""
    mapping = _size_selector_mapping(sdk, tag_name)
    if not mapping:
        return {}
    values = {"width": width, "height": height}
    css_vars: dict[str, str] = {}
    for prop_mapping in mapping:
        target = prop_mapping["targetProperty"]
        for cond in prop_mapping.get("condition", []):
            if cond["property"] == "orientation" and cond["value"] == orientation and cond["action"] == "swaptarget":
                target = cond["alternateTargetProperty"]
        css_vars[target] = f"{values[prop_mapping['sourceProperty']]}px"
    return css_vars


def _is_aspect_locked(sdk: "sdk_module.UiSdk", tag_name: str) -> bool:
    """True if `tag_name`'s rendered size is driven by a SINGLE axis-sourced CSS var
    with no independent counterpart for the other axis -- e.g. ch5-dpad's
    `--ch5-dpad--regular-size`, schema-mapped only from `width`, with no separate
    height-sourced var at all. Confirmed against a real resized D-pad instance
    (`C:\\Solutions\\ClaudeSamples\\Components\\Component - Keypad - DPad.cuig`, id
    `ixo7`): width, height, and the var are always numerically identical -- real
    Construct never lets this component's box go non-square. `_fit_group` uses this to
    force width=height=min(fitted_width, fitted_height) for such an element after both
    axes have been fit independently, since nothing else in this pipeline otherwise
    keeps a square component square when its row (X) and row-stack (Y) are fit
    separately -- only ever shrinking, so it can't introduce a new overlap (a smaller
    box is always contained within space already proven safe for the bigger one)."""
    mapping = _size_selector_mapping(sdk, tag_name)
    if not mapping:
        return False
    source_props = {m["sourceProperty"] for m in mapping}
    return source_props in ({"width"}, {"height"})


def _fit_group(
    elements: dict[str, dict], target_width: int, target_height: int,
    source_width: int, source_height: int,
    path: Path, query: str, warnings: list[str],
    id_to_tag: dict[str, str] | None = None, sdk: "sdk_module.UiSdk | None" = None,
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
    docstring).

    `id_to_tag`/`sdk` -- ADDED 2026-09-10 (real D-pad overlap bug, see
    _is_aspect_locked's docstring): when given, aspect-locked components get
    width=height=min(...) reconciliation, and every element's size-mirroring CSS vars
    are recomputed from the FINAL width/height via the SDK schema
    (_component_size_css_vars) instead of ratio-scaled by name-substring matching --
    strictly more robust (no compounding rounding difference between the two methods)
    and the only way `--ch5-dpad--regular-size`-style vars get scaled at all. Either
    argument missing/`None` falls back to today's legacy substring-based scaling with
    no aspect-lock reconciliation, unchanged -- existing callers/tests that don't know
    about component types keep working exactly as before.

    ADDED 2026-09-10 (column-aware, see docs/superpowers/specs/
    2026-09-10-reflow-columns-design.md): the X-loop now fits one item PER COLUMN
    (detect_columns' grouping of each row's elements by source X-range overlap), not
    one item per element -- elements that share a column (e.g. a vertically-stacked
    Up/Down pair) always get the SAME final `left`, each keeping its own width scaled
    by the column's own scale factor. `stack_rows`' Y-axis is unaffected: `row_lists`
    flattens each wrapped row's columns back into a plain element-id list, the same
    shape `stack_rows` already expected."""
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

    fitted: dict[str, dict] = {}
    for eid, e in elements.items():
        x, y = x_fit[eid], y_fit[eid]
        width, height = x["size"], y["height"]

        tag = id_to_tag.get(eid) if id_to_tag else None
        if sdk is not None and tag is not None and _is_aspect_locked(sdk, tag):
            width = height = min(width, height)

        size_vars = _component_size_css_vars(sdk, tag, width=width, height=height) if (sdk is not None and tag is not None) else {}

        extra_vars: dict[str, str] = {}
        for name, value in e.get("extra_vars", {}).items():
            if name in size_vars:
                continue  # handled by the unconditional merge below
            lname = name.lower()
            numeric = float(value[:-2]) if value.endswith("px") else None
            # CORRECTED 2026-09-09 (task review): must use int() truncation, matching
            # fit_axis's/stack_rows's own Tier 3 convention exactly (round() was
            # reintroducing the "outer width/height vs. --ch5-button--* var disagree"
            # class of bug this codebase already fixed once, Phase 4 -- a mirrored var
            # must equal the property it mirrors bit-for-bit, which only holds if both
            # use the same rounding function). Legacy fallback path only (sdk is None)
            # -- see _component_size_css_vars above for the schema-driven replacement,
            # used whenever `sdk` is available.
            if sdk is None and numeric is not None and "width" in lname:
                extra_vars[name] = f"{max(1, int(numeric * x['scale']))}px"
            elif sdk is None and numeric is not None and "height" in lname:
                extra_vars[name] = f"{max(1, int(numeric * y['scale']))}px"
            else:
                extra_vars[name] = value  # not a width/height-mirroring var -- carry through unscaled
        # CORRECTED 2026-09-10 (real bug: a button's adorner correctly showed its new,
        # smaller height, but the button itself rendered at its old, much larger size):
        # `size_vars` must be ADDED here unconditionally, not merged only into whatever
        # keys the loop above already found in the source's own extra_vars. A real
        # "regular"-mode button (the common case for anything not yet resized by hand
        # in Construct) never carries --ch5-button--regular-width/height at all -- that
        # pair only appears once a button has actually been custom-resized -- so when
        # reflow forces such a button to size="custom" (see reflow_file), it MUST also
        # synthesize these vars fresh; leaving them missing (the original bug here)
        # means Construct has nothing to constrain the internal render to the new size,
        # so it falls back to a larger default while the outer box (and the adorner)
        # correctly reflects the smaller computed size.
        extra_vars.update(size_vars)
        fitted[eid] = {
            "left": x["pos"], "top": y["top"], "width": width, "height": height,
            "z_index": e.get("z_index"), "extra_vars": extra_vars,
        }
    return fitted


def _fill_missing_size(
    elements: dict[str, dict], catchall: dict[str, dict], path: Path, query: str, warnings: list[str],
) -> dict[str, dict]:
    """A device-specific block only restates `width`/`height`/`z_index`/`extra_vars`
    when they differ from the catch-all block's value for that element (see
    layout.py::parse_position_rules's docstring) -- fill in whichever are `None`/absent
    from the catch-all's own value for that element id. `z_index` staying `None` after
    this is expected (real device blocks never repeat it at all, confirmed in
    layout.py's module docstring); an element still missing `width`/`height` after the
    merge (present in the device block but never in the catch-all -- shouldn't happen in
    a well-formed file) is dropped with a warning rather than propagated as `None` into
    size-dependent math. `extra_vars` (e.g. `--ch5-button--regular-width`) are merged
    key-by-key with the device block's own values winning on a conflict, the same
    precedence as width/height -- found by this function's own regression test: an
    initial version left `extra_vars` untouched, silently dropping a catch-all-only var
    for any element whose device rule omitted it."""
    filled: dict[str, dict] = {}
    for eid, e in elements.items():
        fallback = catchall.get(eid, {})
        width = e["width"] if e["width"] is not None else fallback.get("width")
        height = e["height"] if e["height"] is not None else fallback.get("height")
        if width is None or height is None:
            warnings.append(f"{path.name}: {eid!r} has no width/height in {query} or the catch-all block -- skipped")
            continue
        filled[eid] = {
            **e,
            "width": width,
            "height": height,
            "z_index": e["z_index"] if e["z_index"] is not None else fallback.get("z_index"),
            "extra_vars": {**fallback.get("extra_vars", {}), **e.get("extra_vars", {})},
        }
    return filled


_TAG_RE = re.compile(r"<[\w-]+[^>]*>")


def _tag_index(html_text: str) -> dict[str, tuple[str, str]]:
    """Map element_id -> (tag_name, full_opening_tag_text) for every element tag in
    `html_text` -- ADDED 2026-09-10. Scans every tag rather than assuming a fixed
    attribute order (a real Construct-authored tag can have `id=` anywhere among its
    attributes), used both to look up a component's type (schema-driven var
    scaling/aspect-lock, see _fit_group) and its current `size` attribute (the
    size="regular"->size="custom" forcing check, see _force_custom_size)."""
    index: dict[str, tuple[str, str]] = {}
    for m in _TAG_RE.finditer(html_text):
        tag_text = m.group(0)
        id_match = re.search(r'\bid="([^"]*)"', tag_text)
        if id_match:
            tag_name = tag_text[1:].split(None, 1)[0].split(">", 1)[0].rstrip("/")
            index[id_match.group(1)] = (tag_name, tag_text)
    return index


def _force_custom_size(html_text: str, page_attrs_text: str, element_id: str, tag_text: str) -> tuple[str, str]:
    """If `tag_text` (this element's own opening tag, from _tag_index) has
    size="regular", rewrite it to size="custom" in both the {Html} tag and the
    matching [[Elements]] TOML block -- ADDED 2026-09-10, confirmed necessary by a
    real user-authored page: size="regular" ignores explicit width/height CSS entirely
    and renders at the theme's fixed preset dimensions, silently undoing whatever
    reflow just computed. This is the same fix this generator's own element-creation
    code already applies (see ch5_button.py::build_default_button_attributes); reflow
    now applies it too, but only to elements it actually resizes (see reflow_file),
    never touching an element it only repositions. Returns the (possibly unchanged)
    html_text/page_attrs_text -- a no-op if `tag_text` isn't size="regular" (already
    "custom", or a component type with no size attribute at all)."""
    if 'size="regular"' not in tag_text:
        return html_text, page_attrs_text
    new_tag_text = tag_text.replace('size="regular"', 'size="custom"', 1)
    html_text = html_text.replace(tag_text, new_tag_text, 1)

    blocks = re.split(r"(?=\[\[Elements\]\])", page_attrs_text)
    id_line = f'id = "{element_id}"'
    for i, block in enumerate(blocks):
        if id_line in block and 'size = "regular"' in block:
            blocks[i] = block.replace('size = "regular"', 'size = "custom"', 1)
            break
    return html_text, "".join(blocks)


def reflow_file(path: Path, target_resolution: dict, source_resolution: dict, mode: str = "pin_existing", sdk: "sdk_module.UiSdk | None" = None) -> ReflowResult:
    """Add or update `target_resolution`'s @media block(s) in `path` so it has a
    position rule for every element `source_resolution`'s block(s) have. See the
    spec's Algorithm section for `mode` semantics (pin_existing default vs.
    full_refit).

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
    task review.

    CORRECTED AGAIN 2026-09-09 (final whole-branch review -- a more severe bug than
    any of the above): the real generator emits ONE @media block PER ELEMENT even
    when several elements share the identical query string (build_position_css is
    called once per element) -- confirmed against a real 3-button page, three
    separate `@media (max-width: 99999px){...}` blocks, not one block with three
    #id{} rules. The single-match `find_media_block`/`find_media_block_span` this
    function used only ever saw the FIRST element for both source and target,
    silently dropping every other element with zero warnings -- the exact
    "components absent" failure this whole feature exists to prevent. Fixed by
    switching to `find_media_block_spans`/`parse_all_position_rules` (plural) for
    both source and target, and, on write, replacing the FIRST matching target span
    with the one consolidated block while DELETING every other matching target span
    entirely (splicing from the end backward so earlier indices stay valid) -- see
    the spec's Data model and Components sections. Also added: a fallback to the
    99999px catch-all block when the source resolution's own dedicated block is
    missing (a page authored before the project had any resolution only ever has the
    catch-all; without this fallback such a page can never gain a device block for
    any resolution added after its first, since the first add has nothing to source
    from and the catch-all was never promoted to a real device block either -- see
    the spec's Error handling section). Also fixed a determinism bug: `pinned`/
    `to_fit` were built by iterating `find_new_elements`'s SETS, whose iteration
    order depends on Python's per-process string-hash randomization, making the
    emitted rule order (and warning order) different on every run of the same input
    -- fixed by iterating `target_elements`/`source_elements` (dict insertion order,
    deterministic) and testing membership in the sets instead.

    `sdk` -- ADDED 2026-09-10 (real D-pad overlap bug found live-testing in Construct;
    see _is_aspect_locked's docstring for the full story): when given, this function
    now also touches {Html} and [[Elements]] TOML for the first time (previously only
    ever rewrote {Css}) -- any element this call actually resizes (fitted width/height
    differs from its source width/height) that's currently `size="regular"` gets
    forced to `size="custom"` in both places (see _force_custom_size), since
    `size="regular"` ignores explicit CSS and silently undoes whatever was just
    computed. `sdk` also enables schema-driven size-var scaling and aspect-lock
    reconciliation in _fit_group. Omitting `sdk` reproduces today's exact behavior
    (Css-only, legacy substring-based var scaling, no aspect-lock) -- existing
    callers/tests are unaffected."""
    if mode not in ("pin_existing", "full_refit"):
        raise ValueError(f"unknown mode {mode!r} -- expected 'pin_existing' or 'full_refit'")

    warnings: list[str] = []
    preamble, sections = _read_sections(path)
    css_index = next((i for i, (name, _, _) in enumerate(sections) if name == "Css"), None)
    if css_index is None:
        warnings.append(f"{path.name}: no {{Css}} section found -- skipped")
        return ReflowResult(warnings=warnings)
    css_text = sections[css_index][2]

    html_index = next((i for i, (name, _, _) in enumerate(sections) if name == "Html"), None)
    page_attrs_index = next((i for i, (name, _, _) in enumerate(sections) if name == "PageAttributes"), None)
    id_to_tag_and_text = _tag_index(sections[html_index][2]) if html_index is not None else {}
    id_to_tag = {eid: t[0] for eid, t in id_to_tag_and_text.items()}

    source_orientation = _orientation_name(source_resolution)
    target_orientation = _orientation_name(target_resolution)
    source_query = layout.orientation_media_query(source_orientation, source_resolution["width"], source_resolution["height"])
    target_query = layout.orientation_media_query(target_orientation, target_resolution["width"], target_resolution["height"])
    catch_all_query = "(max-width: 99999px)"

    try:
        catchall_elements = layout.parse_all_position_rules(css_text, catch_all_query)
    except (ValueError, KeyError) as e:
        warnings.append(f"{path.name}: catch-all block didn't parse cleanly -- {e} -- skipped")
        return ReflowResult(warnings=warnings)

    try:
        source_elements = layout.parse_all_position_rules(css_text, source_query)
    except (ValueError, KeyError) as e:
        warnings.append(f"{path.name}: source block for {source_query} didn't parse cleanly -- {e} -- skipped")
        return ReflowResult(warnings=warnings)
    if not source_elements:
        # Fall back to the 99999px catch-all -- a page authored before the project
        # had any resolution only ever has this block (see the module docstring).
        source_elements = catchall_elements
    else:
        source_elements = _fill_missing_size(source_elements, catchall_elements, path, source_query, warnings)
    if not source_elements:
        warnings.append(f"{path.name}: no source block (device or catch-all) had any position rules -- skipped")
        return ReflowResult(warnings=warnings)

    try:
        target_spans = layout.find_media_block_spans(css_text, target_query)
    except ValueError as e:
        warnings.append(f"{path.name}: target block for {target_query} didn't parse cleanly -- {e} -- skipped")
        return ReflowResult(warnings=warnings)
    try:
        target_elements = layout.parse_all_position_rules(css_text, target_query) if target_spans else {}
    except (ValueError, KeyError) as e:
        warnings.append(f"{path.name}: target block for {target_query} didn't parse cleanly -- {e} -- skipped")
        return ReflowResult(warnings=warnings)
    if target_elements:
        target_elements = _fill_missing_size(target_elements, catchall_elements, path, target_query, warnings)

    if mode == "full_refit" or not target_elements:
        pinned, to_fit = {}, source_elements
    else:
        new_ids, pinned_ids = find_new_elements(source_elements, target_elements)
        pinned = {i: target_elements[i] for i in target_elements if i in pinned_ids}
        to_fit = {i: source_elements[i] for i in source_elements if i in new_ids}

    if not to_fit:
        warnings.append(f"{path.name}: no new elements to fit for {target_query} -- skipped")
        return ReflowResult(warnings=warnings)

    fitted = _fit_group(
        to_fit, target_resolution["width"], target_resolution["height"],
        source_resolution["width"], source_resolution["height"],
        path, target_query, warnings,
        id_to_tag=id_to_tag, sdk=sdk,
    )
    if fitted is None:
        return ReflowResult(warnings=warnings)

    if html_index is not None and page_attrs_index is not None:
        html_text = sections[html_index][2]
        page_attrs_text = sections[page_attrs_index][2]
        for eid, fit in fitted.items():
            source = to_fit[eid]
            if fit["width"] == source["width"] and fit["height"] == source["height"]:
                continue  # only repositioned, not resized -- size="regular" is fine here
            tag_info = id_to_tag_and_text.get(eid)
            if tag_info is None:
                continue
            html_text, page_attrs_text = _force_custom_size(html_text, page_attrs_text, eid, tag_info[1])
        sections[html_index] = ("Html", sections[html_index][1], html_text)
        sections[page_attrs_index] = ("PageAttributes", sections[page_attrs_index][1], page_attrs_text)

    if mode == "pin_existing" and pinned:
        for new_id, pinned_id in check_overlaps(pinned, fitted):
            warnings.append(
                f"{path.name}: new element {new_id!r} may overlap pinned element "
                f"{pinned_id!r} in {target_query} -- review placement in Construct"
            )

    all_elements = {**pinned, **fitted}
    new_block = layout.build_reflow_block(all_elements, target_orientation, target_resolution["width"], target_resolution["height"])

    if target_spans:
        # Replace the FIRST matching target span with the one consolidated block;
        # delete every OTHER matching span entirely (splice from the end backward so
        # earlier indices stay valid -- each deletion only shifts content AFTER it).
        for start, end in reversed(target_spans[1:]):
            css_text = css_text[:start] + css_text[end:]
        start, end = target_spans[0]
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
