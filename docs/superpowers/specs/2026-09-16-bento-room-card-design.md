# Bento Box "Room Card" composite (v2) — design spec

**PAUSED (user, 2026-09-17):** Bento Box is no longer a required layout pattern —
see `ConstructUISkill_DesignSystem.md` §2 ("removed from scope" note). This spec is
kept on disk as a record; no implementation plan was ever written against it. Not
resumed unless Bento Box comes back into scope. Current focus is the Tabbed layout
(commercial first, then residential) — see
`docs/ConstructUISkill_Tabbed-Layout-Spec_Commercial.md`.

Supersedes `docs/superpowers/specs/2026-09-16-room-card-design.md` (see that file's
header note). Extends `generator/layout_patterns.py::build_bento_box_page` (§1 Layout
Patterns, `ConstructUISkill_DesignSystem.md`) with a richer per-room card type. Does
not change the plain icon+label card path at all — every existing `bento_box_test.py`
assertion must keep passing unchanged.

## Problem

The user prototyped a real HTML/CSS/JS "Home Panel" bento layout in Claude web and
saved it as `docs/ConstructUISkill_Bento-Home-Panel-Spec_Residential.md` — a richer
room-status card (header with a status dot + subtitle, then one row per subsystem with
an icon/label/value and an optional progress bar) plus a by-room/by-system view
toggle, sized by native CSS flexbox (`display: flex; flex-wrap: wrap`, `flex-grow`/
`flex-basis` computed from row count). Decided: *"the new bento box design should be
used as the new room card"* — this replaces the abandoned Room Card v1 composite
(icon+label+status-text+subsystem-icon-row), not the plain Bento Box card path itself.

That reference doc is a **visual/structural reference, not a literal implementation
spec** — confirmed with the user it must be built with real Construct CH5 components,
not a custom HTML/CSS/JS blob embedded in one `html-div` (Construct has no live DOM
reflow; every element in this generator gets explicit `position: absolute` CSS,
confirmed via `layout.py:124-127` against real Construct files — there is no native
flexbox layout anywhere in this project, and that's deliberate, not an oversight).

## Scope for this pass

Confirmed with the user (2026-09-16), in order:

1. **Static content, not live signal binding.** Like every other composite this
   generator has built (Room Card v1, Bento Box's own `icons`, `theme_chat`'s
   resolved colors), all content here — title, subtitle, status-dot state, row list,
   row values, progress-bar fractions — is caller-supplied once at generation time,
   not wired to a real CH5 receive-state join. A real `ch5-list` component was
   investigated as a live-templated alternative (confirmed real via the project's own
   SDK: `size`/`receivestatesize`, `itemheight`/`itemwidth`, `receivestatetemplatevars`
   + `indexid`) but is out of scope — it exists for live/runtime-driven lists, which
   this project doesn't do anywhere yet, and adopting it here would be new,
   unprecedented, unconfirmed-in-depth surface area for no benefit under a
   static-content contract. Not ruled out for some *future* live-binding initiative.
2. **Only the "by-room" box anatomy.** The reference doc's by-system view (zones,
   idle-room pills, "3 of 6 rooms on" aggregate summaries) and the by-room/by-system
   toggle mechanism are explicitly deferred — a real, separate scope question (how the
   toggle works in Construct — most likely two widgets with Contract-driven Visibility
   swapped by a button — needs its own decision) that this pass does not resolve, same
   discipline as Room Card v1's own deferred-features list.
3. **Styling is out of scope.** Colors/tokens in the reference doc (`--amber`, `--sky`,
   `--sage`, Manrope, JetBrains Mono, `20px`/`9px` radii) are that prototype's own
   choices, not requirements — this project's §1 AI-Based UX Persona resolves color/
   typography/shape per project, same as everywhere else. This spec only defines
   *structure*: which components exist, how they're laid out, what data they need.

## Architecture

One new module, `generator/room_card.py::build_room_card`, replacing the abandoned
Room Card v1 of the same name (that file no longer exists — the `feat/room-card`
worktree/branch it was built on is parked, not merged, not deleted).

**Base + overlays** (same proven shape as Room Card v1, carried over unchanged): one
`ch5-button` is the card's only interactive element (tap target, opens the room's page
or popup — same as every other Bento Box card), its own label suppressed
(`label=""`). Every visible piece of content is a non-interactive overlay on top of
it, marked `pointer-events: none` via `layout.update_element_declarations` so taps
still reach the base button — confirmed real via Construct's own `ch5-wifi-signal-
level-gauge` component (`Component - Gauge - Wifi.cuig`), same precedent Room Card v1
already established.

**Header band** (top of the card):
- Title — `ch5-text`, the room name.
- Status dot — a small round `html-div` (confirmed real, sanctioned mechanism for
  literal decorative shapes — already used for card backgrounds/borders/grouping,
  NOT the "custom HTML/JS app in a div" approach ruled out above), accent-colored
  when the room is occupied/active, a neutral gray otherwise. Color values are
  caller-supplied (persona-resolved), never hardcoded.
- Subtitle — `ch5-text`, one line (e.g. an occupancy string), dimmer/smaller than
  the title.

**Row band** (below the header, one row per caller-supplied subsystem):
- Icon — a small non-interactive `ch5-button` (icon-only, `label=""`), same
  mechanism as Room Card v1's subsystem icons.
- Label — `ch5-text`, left-aligned (e.g. "Lights").
- Value — `ch5-text`, right-aligned (e.g. "70%", "71°F", "Locked").
- Progress bar (optional, level-type rows only — lights/climate) — two stacked
  `html-div`s (a full-width track + a narrower fill sized to the row's own
  `progress_fraction`), same sanctioned literal-CSS-shape mechanism as the status
  dot. Rows without a `progress_fraction` render label+value only, no bar.

Row layout reuses the header widget's existing `_layout_header_row` shape (fixed
items alongside flexible items dividing remaining space) rather than the footer's
`_layout_row` (which enforces `spacing.MIN_TOUCH_TARGET` — wrong here, these rows are
informational, not tap targets, same reasoning Room Card v1 already established for
its subsystem icon row).

## Sizing

The reference doc's native-flexbox `flex-grow`/`flex-basis` algorithm cannot run here
(no native reflow in Construct) — translated to this project's existing patterns
instead, chosen over inventing a new continuous/masonry packing algorithm because the
design system's own §2 Bento Box rule already argues against it ("2–3 card sizes
max... more than that stops reading as intentional hierarchy"):

1. **Row count → tier.** Each room's subsystem-row count picks one of Bento Box's
   existing discrete tiers (`small`/`wide`/`large`, `TIER_SPANS`) via a new mapping
   function. Reuses the existing `_pack_bento_grid` packing algorithm unchanged — no
   new geometry code for placement, only for the row-count-to-tier choice.
2. **Row height scales within the chosen tier**, proportional to the tier's own
   available body height (card height minus header band minus edge padding) divided
   by row count — same "proportional to footprint, floored at a readability minimum"
   technique `typography.apply_font_size`/`apply_icon_size` already use elsewhere,
   floored at `typography.TYPE_SCALE["caption"]` / `ICON_SCALE["caption"]`.
3. **Raises `ValueError`** if even the floor doesn't fit within "large" for that
   project's real `page_width`/`columns`, same "raise rather than silently overflow"
   discipline as every other layout-pattern builder in this project (`_layout_row`,
   `build_bento_box_page`'s own touch-target/height checks, Room Card v1's band-fit
   check).

**Confirmed with real numbers** (2026-09-16, against this project's own
`bento_box_test.py` fixture scale: `page_width=960, columns=4` → cell_size 226px →
"large" 460×460, "wide" 460×226): a 460×460 "large" card has roughly 344px of body
height after a ~76px header band; at a ~36px per-row floor (20px icon + progress-bar
allowance + gaps), that fits **up to ~9 rows**, with 5 rows rendering generously above
the floor (≈69px/row). "Wide" (226px tall) only fits ~3 rows at the floor — a 4-5
subsystem room needs "large," not "wide." These numbers scale with each project's own
real `page_width`/`columns` and are recomputed at build time, not hardcoded.

## Data contract

Everything is caller-supplied, matching this project's "generator never invents
content" rule (Room Card v1, Bento Box's `icons`, `theme_chat`'s resolved colors):

- Room title, subtitle text, status-dot active/inactive + its two colors.
- The subsystem row list: for each row, icon class/library, label text, value text,
  and an optional `progress_fraction` (0–1) for the level-type rows.

Row count is read directly from this list's length to pick the tier (§ Sizing) — the
caller decides which subsystems a room has, the generator never guesses or invents
one.

## Testing

Same house style as every other module in this project: standalone script under
`generator/_test_output/`, run directly with `python <file>.py`, plain `assert` +
per-assertion-group print + a final "all assertions passed" line. Covers (at minimum):
element count matches header (title+dot+subtitle) + row content, base button
suppressed label + non-interactive overlays marked `pointer-events: none`, row-count-
to-tier mapping picks the right tier at real boundary counts (including the
~9-row/"large" ceiling confirmed above), row height scales down as row count
increases and stays above the readability floor, progress bar present only on rows
with a `progress_fraction`, a written `.cuig` round-trips byte-identical, and the
too-many-rows-for-any-tier case raises `ValueError` rather than silently cramming.

## Deferred (not built in this pass)

By-system view (zones, idle-room pills, aggregate summaries), the by-room/by-system
toggle mechanism, background room photos, floor/category grouping, notification bell/
favorite heart, list-vs-grid view toggle, and any real live signal/join binding for
continuously-updating values. Each is its own real scope question needing its own
brainstorming pass, same discipline as Room Card v1's own deferred list.
