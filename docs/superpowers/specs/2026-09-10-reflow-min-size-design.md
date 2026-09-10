# Reflow: minimum-size floors — design spec

Amends `docs/superpowers/specs/2026-09-08-multi-resolution-reflow-design.md` (Tier 3,
`fit_axis`'s uniform scale-down) and the same day's centering/columns amendments.
Tiers 1/2, `wrap_rows`, centering, and column grouping are unchanged — this only
generalizes Tier 3's floor from a flat 1px to a per-item minimum.

## Problem

Found 2026-09-10, live-testing TSW-570 (640x360) in Construct: real buttons were
scaled down to 28px tall — legible-adjacent but too small at runtime, per the user.
Today's Tier 3 (`generator/reflow.py:148-168`) applies one uniform scale factor to
every item in a group and floors each result at a flat, meaningless 1px — there's no
concept that a real component has its own practical minimum size below which it either
becomes illegible (a text-bearing button) or, for some component types, literally
isn't supported by Construct at all. Confirmed via the SDK's own schema
(`sdk.context_for(tag)["minSizes"]`): `ch5-dpad` → `minWidth: "100px"`, `ch5-keypad` →
`minWidth: "210px"` — real, enforced technical floors, not a legibility preference.
`ch5-button`/`ch5-slider` have no `minSizes` entry at all in the schema — Crestron
doesn't publish a floor for these because scaling a button that small is a design
choice, not a technical limit, so this is exactly where a user-configurable fallback
constant belongs.

## Scope

Only changes Tier 3's own floor, in `fit_axis` and (indirectly, via a derived
per-row minimum) `stack_rows`. Tiers 1/2 (move, compact) never change size at all, so
they're unaffected — a minimum only ever matters once Tier 3 is reached (nothing else
in the tier order shrinks anything). `wrap_rows`'s own fit-decision
(`_columns_fit`, compaction-feasibility) is unaffected: it reasons about *original*
widths, never shrunk ones, so it has nothing to do with minimum sizes.

Out of scope: a full per-instance/per-attribute minimum-size configuration system.
Two sources only: the SDK's own `minSizes` schema entry (when present) and one
module-level fallback constant (when absent) — matches the two cases this project has
concrete evidence for (real Crestron-enforced floors vs. no data at all).

## Minimum-size lookup

New `generator/reflow.py::_component_min_size(sdk, tag_name) -> int`:

```python
FALLBACK_MIN_SIZE_PX = 30  # tune freely -- only applies to component types the SDK's
                            # own schema doesn't already constrain (see below).

def _component_min_size(sdk, tag_name) -> int:
    try:
        ctx = sdk.context_for(tag_name)
    except (KeyError, StopIteration):
        return FALLBACK_MIN_SIZE_PX
    min_width = ctx.get("minSizes", {}).get("minWidth")
    return int(min_width.rstrip("px")) if min_width else FALLBACK_MIN_SIZE_PX
```

Applies to both width and height (confirmed by the user's answer — a real button can
be unreadably *narrow* too, not just short). Only ever consulted when `sdk` and a
resolved tag are both available — mirrors every other schema-driven check already
gated this way in `_fit_group` (`_is_aspect_locked`, `_component_size_css_vars`); a
legacy call with no `sdk` gets zero minimum-size enforcement, identical to today.

## Algorithm: Tier 3 becomes minimum-size-aware

`fit_axis` gains one new parameter: `min_sizes: dict[str, int] | None = None` — maps
`item_id -> minimum size`. **`min_sizes=None` (the default) must take a COMPLETELY
SEPARATE code path, not "the general path with every minimum defaulting to 1"** — see
the self-review note below for why that distinction is load-bearing, not cosmetic.

**Self-review correction**: an earlier draft of this spec defaulted every item's
minimum to `1` and always ran the new iterative algorithm below. That turns out to
silently change today's actual output even when no real minimum is in play: today's
Tier 3 applies ONE scale to every item in a single pass and floors each independently
(`max(1, int(size * scale))`), which the module's own existing comment already
documents as sometimes overshooting `target_dim` slightly ("the only remaining,
deliberate source of overflow is that 1px floor itself on a pathologically
over-crowded axis"). The iterative algorithm below does NOT have that overshoot — it
reserves a frozen item's exact floor and recomputes scale for the rest — which is
arguably better, but it is a DIFFERENT number, and "omitting `min_sizes` reproduces
today's exact behavior" is a hard requirement (every existing caller/test omits it).
So: `min_sizes is None` runs the untouched original one-shot formula, verbatim, and
only `min_sizes` being an actual dict (even `{}`) switches to the new logic below.

**`min_sizes is None`** — Tier 3 is completely unchanged from today (same code,
same `available_for_sizes <= 0` check, same one-shot `scale`/`max(1, int(size*scale))`
formula, same flat per-group `"scale"` in the result).

**`min_sizes` is a dict** — a uniform scale can't be used directly, since different
items can have different minimums. First, the failure mode (per the user's answer,
matching the existing gap-floor precedent): check `available_for_sizes >=
sum(mins.values())` (`mins[item_id] = min_sizes.get(item_id, 1)` — an id absent from
the dict still defaults to `1`, only the *no dict at all* case gets the legacy path).
If it fails, raise `AxisFitError` — the caller (`_fit_group`) already treats this as
"skip this target block, warn, don't crash the rest of the project," unchanged.

Then: iteratively freeze any item whose *uniformly*-scaled size would fall below its
own minimum, at that minimum, and redistribute the remaining available space among the
still-free items with a recomputed scale — repeat until no item newly freezes. Same
shape as CSS flexbox's own shrink-with-min-width algorithm. Guaranteed to converge
(each iteration either freezes at least one more item or stops; only `n` items exist
to freeze) and never go negative (the pre-check already proved the fully-frozen case
fits).

```python
if min_sizes is None:
    # Untouched legacy Tier 3 -- byte-for-byte today's code, no behavior change.
    if available_for_sizes <= 0:
        raise AxisFitError(f"target_dim {target_dim} can't fit even the mandatory {min_gap}px floor gaps for {n} items")
    scale = available_for_sizes / total_size
    new_sizes = [max(1, int(size * scale)) for size in sizes]
    ...  # unchanged packing/result-building, exactly as today
else:
    mins = {item_id: min_sizes.get(item_id, 1) for item_id in ids}
    if available_for_sizes < sum(mins.values()):
        raise AxisFitError(
            f"target_dim {target_dim} can't fit even the mandatory {min_gap}px floor "
            f"gaps AND every item's own minimum size ({sum(mins.values())}px total) for {n} items"
        )
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
    ...  # same packing as today, but per-item "scale" in the result is now
    ...  # new_sizes[i] / sizes[i] (each item's OWN ratio) instead of one flat value
```

Packing (position assignment) is otherwise unchanged in both branches — pack
sequentially at exactly `min_gap` in the same `ids` order. **Per-item `scale` in the
result changes meaning only in the dict branch**: instead of one group-wide factor,
each item reports its OWN effective ratio, `new_sizes[i] / sizes[i]` — a frozen item's
true shrink ratio, not the group's. This is what `_fit_group`'s legacy (no-`sdk`)
extra_vars fallback path already assumes `x['scale']`/`y['scale']` means (an item's
own size ratio); the legacy branch's flat `scale` already satisfies this trivially
(uniform scaling means every item's own ratio equals the group scale), so nothing
about that path's contract changes — it just becomes correct once freezing can happen
at all, in the branch where freezing is possible.

**Hand-traced example**: 3 items, sizes 100/100/100, target_dim=100, min_gap=4,
mins={"a": 60, "b": 1, "c": 1}. `available_for_sizes = 100 - 2*4 = 92`.
`sum(mins)=62 <= 92` — passes. Round 1: `scale = 92/300 = 0.307`; tentative sizes
30.7/30.7/30.7 — `a` (min 60) freezes at 60; `b`/`c` don't (30.7 >= 1). Round 2:
`free_available = 92-60=32`, `free_total=300-100=200`; `scale=32/200=0.16`; tentative
`b`/`c` = 16/16, both `>= 1` — no new freezes, loop stops. `final_scale=0.16`.
`new_sizes = {"a": 60, "b": max(1,int(100*0.16))=16, "c": 16}`. Packed:
`a@0(60), b@64(16), c@84(16)` → ends at 100, exactly `target_dim`. `a`'s reported
`scale` = 60/100 = 0.6 (its own true ratio); `b`/`c` report 0.16 (matches
`final_scale`, since they were never frozen).

## X-axis wiring (`_fit_group`, straightforward)

Each column's minimum is the max minimum among its own members (the column's shared
final size must satisfy every member, and members already share a width per the
columns design — see `docs/superpowers/specs/2026-09-10-reflow-columns-design.md`):

```python
col_min_sizes = {}
for idx, column in enumerate(columns):
    col_key = f"__col{idx}"
    ...
    if sdk is not None and id_to_tag:
        tags = [id_to_tag.get(eid) for eid in column]
        if all(tags):
            col_min_sizes[col_key] = max(_component_min_size(sdk, t) for t in tags)
```

passed as `fit_axis(row_items, target_width, ..., min_sizes=col_min_sizes if sdk is not None else None)`
— **must be `None`, not `{}`, when `sdk` itself is `None`**, so the call takes the
Algorithm section's legacy branch rather than the dict branch with every column
defaulting to `1` (a different, if superficially similar, code path — see the
Algorithm section's self-review note for why the two aren't interchangeable). When
`sdk` IS given but some individual columns lack tag info, `col_min_sizes` legitimately
stays partial for just those columns — that's the normal "absent id defaults to 1
inside the dict branch" case, not the same concern.

## Y-axis wiring (`stack_rows`, the subtle part)

`stack_rows` scales a whole ROW by one factor and applies it to every member — there's
no per-element minimum today. A row's own derived minimum is the tightest constraint
implied by its members: for each member, the SCALE FACTOR at which that member would
hit its own minimum is `member_min_height / member_own_height`; converting that back
into an equivalent ROW-level minimum (in the row's own natural-height units) via
`row_natural_height * max(member_min_height / member_own_height for member in row)`
gives the row pseudo-item's own minimum — the most restrictive member decides it.
This derived value feeds into the SAME generalized Tier 3 mechanism above (`stack_rows`
already calls `fit_axis` for its row-pseudo-item list — it just also builds and passes
a `min_sizes` dict, one entry per row key, using this formula), so no second algorithm
is needed. Same rule as the X-axis wiring: `stack_rows` passes `min_sizes=None` (not an
empty/partial dict) whenever `sdk` itself is `None`, so a legacy call with no SDK
context takes `fit_axis`'s untouched legacy branch, not the dict branch with every row
defaulting to a minimum of `1`.

## Error handling

Unchanged shape: `_fit_group` already catches `AxisFitError` from any `fit_axis`/
`stack_rows` call and turns it into a per-file warning, skipping that target block —
this now also fires when minimum sizes (not just the gap floor) can't all be
satisfied, per the user's explicit choice.

## Components (new/changed code)

- **`generator/reflow.py::FALLBACK_MIN_SIZE_PX`** (new module constant).
- **`generator/reflow.py::_component_min_size`** (new).
- **`generator/reflow.py::fit_axis`** (changed) — gains `min_sizes`, Tier 3 rewritten
  per the Algorithm section; Tiers 1/2 and the centering step are untouched.
- **`generator/reflow.py::_fit_group`** (changed) — builds `col_min_sizes` per row
  before the X-axis `fit_axis` call.
- **`generator/reflow.py::stack_rows`** (changed) — gains two new parameters,
  `id_to_tag: dict[str, str] | None = None` and `sdk: UiSdk | None = None` (it takes
  neither today), used to build the per-row derived minimum described above and pass
  it to its own `fit_axis` call. `_fit_group` must pass its own `id_to_tag`/`sdk`
  through to the `stack_rows` call it already makes.

## Testing

- `fit_axis` unit tests: the hand-traced 3-item example above (one item freezes, two
  don't); a case where NO item needs freezing (identical to today's plain Tier 3,
  regression guard); a case where `sum(mins) > available_for_sizes` (raises
  `AxisFitError`); omitting `min_sizes` entirely reproduces today's exact byte-for-byte
  output (backward-compat regression guard).
- `_component_min_size` unit tests against the real SDK: `ch5-dpad` → 100,
  `ch5-keypad` → 210, `ch5-button`/`ch5-slider` (no `minSizes`) → `FALLBACK_MIN_SIZE_PX`.
- End-to-end: replay the real TSW-570 button-row shape with a button's minimum set low
  enough that no freeze is needed (confirms wiring doesn't regress the just-fixed
  28px-height case) AND a second case with the minimum set high enough to force a
  freeze, confirming the button's height floors at its minimum and the group still
  fits/doesn't overlap. Re-verify against the real `ReflowTest.cuig` afterward.
