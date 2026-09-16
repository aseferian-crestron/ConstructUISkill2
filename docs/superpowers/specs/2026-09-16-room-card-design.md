# Bento Box "Room Card" composite — design spec

Extends `generator/layout_patterns.py::build_bento_box_page` (§1 Layout Patterns,
`ConstructUISkill_DesignSystem.md`) with an opt-in richer card type. Does not change
the plain icon+label card path at all — every existing `bento_box_test.py` assertion
must keep passing unchanged.

## Problem

The current Bento Box card is a single `ch5-button`: an icon and one label, flat color
fill. The user shared a real reference (a luxury smart-home app's "Rooms" screen) and
asked for real per-room/per-space cards to show more than that: a status summary line
and a row of per-subsystem indicators, the same way that reference does. Confirmed with
the user (2026-09-16) which parts of that reference to build now and which to defer:

**In scope:** status-summary text line, per-subsystem status icon row.
**Out of scope (deferred, not this spec):** background room photo, floor/category
grouping, notification bell / favorite heart, list-vs-grid view toggle.

The user separately corrected an early framing: this must work for BOTH residential
and commercial projects, not just residential rooms — a boardroom's "AV / occupancy /
HVAC" status row is the same mechanism as a home's "lighting / climate / lock" row, so
nothing here hardcodes a residential vocabulary.

## Scope

A new composite, "Room Card," usable per-item inside Bento Box wherever the caller
supplies the extra content; every other Bento Box item continues to render exactly as
today (plain icon+label). Only `large`/`wide` tiers may use it — see **Tier
restriction** below. Content (status text, which subsystems, which are active) is
ALWAYS caller-supplied, never invented by the generator — same precedent as chat-driven
color-theme resolution (`theme_chat.py`) and the plain card's own `icons` param: the
generator provides the mechanism, the driving chat AI or user provides the facts.

Out of scope for this spec (real future work, not attempted here): validating that a
project's real signal/join values match the caller-supplied `active` flags (this is a
static content-authoring feature, not a live-feedback-driven one); an open/closed
enum of "standard" subsystem icons (rejected by the user in favor of a fully open list,
see **Subsystem vocabulary** below); reusing `ch5-button-list` for the icon row instead
of N individual buttons (a real alternative, but `ch5-button-list`'s per-item icon +
per-item independent coloring is not yet confirmed against the real schema the way
`ch5-button`'s icon mechanism already is — YAGNI until a real need for that specific
component surfaces).

## Composition & mechanism

A Room Card is three elements sharing one card footprint (`x, y, width, height`),
stacked by z-index:

1. **Base layer — the existing `ch5-button`** (unchanged mechanism): the card's ONLY
   interactive element, spanning the full card footprint, still the single tap target
   that opens the target page/popup via its Visibility=Contract join (no change to
   this navigation mechanism at all). Its own icon+label rendering is re-tuned for this
   composite (see **Icon repositioning** below) rather than left centered.
2. **Status text overlay — new `ch5-text`**, positioned below the button's icon+label,
   full card width (minus edge padding), one line.
3. **Subsystem icon row overlay — new small icon-only `ch5-button`s**, one per
   `subsystems` entry, positioned in a row near the card's bottom edge.

Overlays 2 and 3 are **non-interactive**: every element in the subsystem row gets a
literal `pointer-events: none` CSS declaration so a tap anywhere on the card — including
directly over an icon in the row — still reaches the base button underneath, not the
decorative icon. This is a REAL, already-used Construct mechanism, not a novel one:
confirmed via `C:\Solutions\ClaudeSamples\Components\Component - Gauge - Wifi.cuig`,
where Construct's own generator writes `.ch5-wifi-signal-level-gauge--inner-container{
pointer-events:none;}` for exactly the same reason (an inner decorative container that
must not intercept taps meant for something else). Written the same way `html-div`'s
own literal (non `--ch5-*`) CSS properties are — plain declarations via
`layout.py::build_position_css`'s `extra_vars` / `layout.update_element_declarations`'s
existing merge-by-name logic, no new CSS-writing mechanism needed.

`ch5-text` is not independently interactive in this schema (no click/focus behavior of
its own), so `pointer-events: none` on it is defensive rather than load-bearing; it is
applied anyway for consistency and because it costs nothing extra to write.

## Icon repositioning (base button)

Today's plain card centers a large icon as the card's whole visual identity — that
made sense with nothing else on the card. A Room Card has three things competing for
vertical space, so the base button's OWN icon+label rendering changes from centered to
a small icon next to the name near the top of the card (`iconposition`, `halignlabel`,
`valignlabel` re-tuned accordingly — exact attribute values confirmed against the real
schema at implementation time, same discipline as the existing plain-card icon
attributes). This uses the SAME button/icon mechanism already built — no new component,
just different attribute values and a smaller proportional icon size for this
composite's context.

## Vertical space allocation

Card height splits into three bands, top to bottom, as fractions of the card's own
height (not fixed pixels — must still scale correctly across `large` vs `wide`, which
differ in height):

1. **Icon + name band** (~50% of height): the base button's own rendering.
2. **Status text band** (~15%): one line, font-size a fraction of the name's own
   proportional size (reusing `typography.py::apply_font_size`, not a new sizing
   mechanism), floored at `typography.TYPE_SCALE["caption"]` (16px) so it never drops
   below the design system's own readability floor.
3. **Subsystem icon row band** (~15%): icon-only buttons evenly spaced across the
   card's width (reusing the existing row-layout math shape already proven in
   `_layout_row`/footer building, not reinvented), each sized via
   `typography.py::apply_icon_size` floored at `typography.ICON_SCALE["label"]` (24px).

Remaining ~20% is edge padding/whitespace between bands (`spacing.SPACING_UNIT`
multiples, same discipline as every other gap in this project). Exact fractions are
tunable at implementation time against a real written `.cuig` (verify visually/
structurally, not just asserted) — the ~50/15/15/20 split is a first estimate, not a
locked spec number in itself; what IS locked is the ORDER (icon+name, then status,
then subsystem row, top to bottom) and that all three must fit within the given card
height without overlapping.

## Subsystem vocabulary

Fully open, caller-supplied — confirmed with the user specifically because the same
mechanism must serve both a home (`lighting`/`climate`/`lock`/`shades`/`media`) and a
commercial space (`AV`/`occupancy`/`HVAC`) without the generator hardcoding either
list. Each entry is `(icon_class: str, icon_library: str, active: bool)` — the same
real Font Awesome value shape the plain card's own `icons` param already uses. `active`
drives color only (see **Icon states**), never presence: an icon the caller includes is
always rendered, whether on or off. Deciding WHICH subsystems apply to a given
room/space and whether each is currently active is the driving chat AI's or user's job,
same precedent as status text and chat-resolved color themes.

## Icon states

Confirmed with the user: color-coded, not show/hide. `active=True` → the icon's
`icon_color` is the project's accent/theme color (whatever `palette.py` has already
resolved for this project — Room Card does not invent a new color role). `active=False`
→ a fixed neutral gray (`palette.NEUTRAL_SCALE`'s own existing gray steps — exact shade
picked at implementation time from that already-built table, not a new color
introduced here).

## API shape

```python
# generator/room_card.py (new module)
def build_room_card(
    sdk: UiSdk, *, component_name: str, x: int, y: int, width: int, height: int,
    resolution: tuple[int, int] | None,
    icon_class: str, icon_library: str, active_font: str,
    status_text: str,
    subsystems: list[tuple[str, str, bool]],  # (icon_class, icon_library, active)
    primary_query: str | None = None,
) -> tuple[str, str, list[Element]]:
    """(html, css, elements) for ONE composite Room Card -- a base ch5-button
    (tap target, re-tuned icon+label positioning) plus a status ch5-text and a
    row of non-interactive icon-only ch5-buttons for `subsystems`. Raises
    ValueError if `height` is too small to fit all three bands without
    overlap (see Tier restriction) -- same "raise rather than silently
    overflow" discipline as every other layout-pattern builder in this
    project.
    """
```

`layout_patterns.py::build_bento_box_page`'s `items` gains an opt-in: an item can be
`(label, tier)` (today's shape, unchanged) or paired with room-card content via a new
optional parameter (exact shape — e.g. a parallel `room_info: dict[label, RoomCardInfo]`
keyed the same way `icons`/`icons.get(label)` already works — decided at implementation
time to match that existing per-label-lookup pattern rather than changing `items`'
tuple shape itself, which would be a breaking change to every existing caller). Cards
without room-card content keep building through the existing plain-button path
unchanged.

## Tier restriction

Confirmed with the user: Room Card content is only accepted for `large`/`wide` tiers.
`build_bento_box_page` raises `ValueError` if a `small`-tier item is given room-card
content — a 242×242 (at this session's live-project scale) card has no real room for
three stacked bands without reading as cramped; same "raise rather than silently
degrade" discipline as the touch-target-floor and height-overflow checks this function
already has.

## Testing

New `generator/_test_output/room_card_test.py`:
- All 3 element groups present (base button + status text + N subsystem icons) with
  correct attributes.
- Every subsystem icon carries `pointer-events: none`.
- Subsystem icon colors match their `active` flags (accent vs. gray).
- Status text content matches the caller-supplied string exactly.
- A real written `.cuig` round-trips byte-identical.
- `small`-tier item + room-card content raises `ValueError`.
- The three bands don't visually overlap (position/size assertions against the real
  written geometry, same technique `bento_box_test.py` already uses for its size-
  hierarchy check).

`bento_box_test.py` extended: a `large`/`wide` item WITH room-card content builds via
the new path; every existing assertion (plain cards, icon-only cards, proportional
sizing, orientation square-only gate) continues to pass completely unchanged, proving
this is additive, not a rework of the existing card path.

## Open items for implementation time (not blocking this spec)

- Exact `iconposition`/`halignlabel`/`valignlabel` values for the re-tuned small
  corner icon — confirmed against the real schema the same way the existing centered-
  icon attributes were, not guessed.
- Exact band-height fractions (the ~50/15/15/20 split above) — tuned against a real
  written `.cuig`'s actual geometry, not locked here.
- Exact gray shade from `palette.NEUTRAL_SCALE` for `active=False` icons.
