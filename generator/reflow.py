"""
Multi-resolution reflow -- Phase 5 continuation.

Source-grounded, per docs/superpowers/specs/2026-09-08-multi-resolution-reflow-design.md
and docs/architecture/10-reflow.md.
"""
from __future__ import annotations

from devices import ORIENTATION_ENUM


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
