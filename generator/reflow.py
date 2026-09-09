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
