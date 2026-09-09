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
    # CORRECTED 2026-09-09 (task review caught a real bug in the first version of this
    # formula): the original `max_possible_reduction = total_gap - (n-1)*min_gap` sums
    # ALL gaps uniformly, including any gap already below min_gap (or negative, i.e.
    # overlapping input) -- those gaps must EXPAND to reach the floor, not contribute
    # reduction, so the old formula could credit negative "slack" and under-reduce the
    # span, silently returning a layout wider than target_dim. Fixed by splitting each
    # gap into reducible slack (above the floor) vs. mandatory deficit (below the
    # floor) and budgeting needed_reduction against slack alone, plus deficit. Also
    # fixed: positions were previously accumulated as floats and rounded independently
    # at the very end, which could round a gap that was >= min_gap as a float down to
    # < min_gap as an integer between two INDEPENDENTLY-rounded neighbors -- fixed by
    # rounding incrementally inside the loop and re-clamping to the floor at each step,
    # so every position produced is already an integer honoring the floor.
    if n > 1:
        gaps = [positions[i + 1] - (positions[i] + sizes[i]) for i in range(n - 1)]
        slack = sum(max(0, g - min_gap) for g in gaps)      # reducible whitespace only
        deficit = sum(max(0, min_gap - g) for g in gaps)    # sub-floor gaps that must expand
        need = needed_reduction + deficit
        if slack > 0 and need <= slack:
            shrink_ratio = need / slack
            new_gaps = [max(min_gap, g - shrink_ratio * max(0, g - min_gap)) for g in gaps]
            new_positions = [0]
            for i, size in enumerate(sizes[:-1]):
                prev = new_positions[-1]
                new_positions.append(max(round(prev + size + new_gaps[i]), prev + size + min_gap))
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
