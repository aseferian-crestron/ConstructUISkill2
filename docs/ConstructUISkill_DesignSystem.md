# ConstructUISkill_DesignSystem.md: Construct UI Skill Design System

This file defines the most important aspect of this skill: it is not just a way to generate Construct data files, it is a design assistant for touch-based control interfaces. When a user already knows what they want, the skill builds it. When a user has no design or color scheme in mind — the same gap the `front-end-design` skill fills for general UI work — this document is what the skill falls back on to still produce a UI that looks professional, consistent, and clearly designed rather than assembled.

Everything below is a POLICY document: a set of rules and defaults the skill applies, not a description of what's already built. Where a rule is already implemented, the real module/function is cited. Where it isn't yet, that's called out explicitly — this doc defines the target, implementation follows as its own phase.

## 1. Layout Patterns

If the user does not provide a design, the skill asks the user to select from the patterns below, and separately confirms whether this is a **Commercial** or **Residential** interface — audience changes which header content and footer/menu items are conventional (see each pattern), not the underlying mechanics.

Every pattern is built from the same primitives already established in `ConstructUISkill.md` §5: a page-based structure where each top-level selection opens its own page, with header/footer as widgets added to every page. §5's hard requirement applies to every pattern below without exception: any widget a pattern adds to every page (header, footer, tab strip, left-side menu rail) must be built with its Global Contract property set true (`page.py::default_widget_html_css(..., is_global=True)`) — it is programmed once, not once per page instance. Each pattern below specifies what varies: its component/widget composition, how it reflows across resolutions and orientations, and which §§2–8 rules constrain it most.

### Header-Content-Footer

The default, safest pattern for control-panel UIs — closest to how nearly every commercial AV touch panel and kiosk interface is structured: a persistent header for context, a content area that swaps per selection, and a persistent footer for primary navigation. This mirrors the mobile "bottom tab bar" pattern (iOS/Material Design bottom navigation) more than a desktop nav bar, which is correct for a device that's touched, not clicked, and usually mounted at a fixed height.

- **Composition:** header widget + footer widget (per §5, added to every page), content area is the page itself; footer selections are mutually exclusive and open/close a page (§5's existing rule).
- **Header content:** Residential — time, weather, area status, active source. Commercial — date/time, active source, corporate logo.
- **Footer content:** menu selections (Power, Lights, Shades, Volume, etc.), same set on every page.
- **When to use:** the default choice; works at every panel size, so it's the fallback when no other pattern is a clearly better fit. The footer's item count is the real limiter — Material Design's own bottom-nav guidance caps at 5 destinations before requiring overflow, and the same ceiling holds here once §4's touch-target minimum and edge padding are respected at the panel's smallest configured resolution.
- **Reflow:** header/footer stay pinned at their configured height across every device resolution; the content page reflows independently underneath. At a narrow/portrait secondary resolution, footer items shrink in width before ever wrapping to a second row — shrinking is preferred over wrapping, down to §4's touch-target floor.

### Bento Box

An asymmetric grid of variously-sized cards, each representing an area (residential) or subsystem (commercial). This is the "dashboard" pattern used by smart-home apps and OS home screens (widget grids, tile layouts): size communicates importance without needing a color or label to say so.

- **Composition:** one page (typically the home/landing page) containing a grid of card components; each card opens either a subsystem/area page or a popup widget.
- **When to use:** when top-level items genuinely differ in importance or frequency of use (e.g., "Currently Playing" deserves a bigger card than "Guest Bathroom Lights"). This is §7's "one dominant action per screen" rule made literal — the largest card IS the dominant action.
- **Sizing rule:** 2–3 card sizes max (e.g., 2x2, 2x1, 1x1 grid units). More than that stops reading as intentional hierarchy and starts reading as random. Every size is still built from the §4 spacing unit so gaps and card padding stay consistent.
- **Reflow:** column count changes per resolution, but a card's size relative to the others is preserved. This is where §8's cross-resolution-consistency rule matters most for this pattern — a hierarchy that only reads correctly at the primary resolution has failed.
- **Density:** governed directly by §7's density ceiling. This is the pattern most likely to accidentally violate it, since it's always tempting to add one more card.

### Card-Based

The same idea as Bento Box with the asymmetry removed: every card is the same size. Simpler and more predictable, at the cost of no visual hierarchy — the standard "grid of equal choices" pattern (a room list, a source list) rather than a dashboard.

- **Composition:** one page with a uniform grid of same-sized card components, each opening a subsystem page, an area page, or a popup widget.
- **When to use:** when top-level items are genuinely peers with no inherent priority order (a list of rooms, a list of sources). Switch to Bento Box the moment one item is legitimately more important than the others.
- **Reflow:** predictable row/column count change per resolution (e.g., 2 columns on a small panel, 4 on a large tabletop panel) — with no hierarchy to preserve, this is the simplest of the five patterns to keep §8-consistent.
- **Density:** §7's density ceiling sets the max card count directly. If the item count exceeds what fits at the minimum touch-target size (§4) even at 1 column, that's a signal to use a scrollable list instead, or split across Tabbed/Left-Side-Menu.

### Tabbed

The header area doubles as primary navigation: each tab is a top-level menu selection, and selecting one swaps the content area — standard tab-bar UX (Material Design tabs, iOS segmented/tab bars) — with a footer still available underneath for controls that should persist regardless of active tab (e.g., volume).

- **Composition:** header widget re-purposed as a tab strip (one tab per top-level selection) + content page area + optional footer widget for persistent global controls.
- **When to use:** when the top-level item count is small and stable. 5–7 tabs is the practical ceiling before individual tab width drops below §4's touch-target minimum or a scroll/overflow affordance becomes necessary — past that, prefer Left-Side Menu, which scales via vertical scroll instead of horizontal compression.
- **Active-tab treatment:** the selected tab needs a clear, consistent visual state distinct from the rest — exactly what §5's `selected_*` state (`derive_states`) already provides; a tab strip uses it rather than inventing a separate selection treatment.
- **Reflow:** tab count is fixed across resolutions, so what reflows is each tab's width. The same §4 floor applies — a tab that would shrink below the touch-target minimum at a narrow resolution switches to a scrollable tab strip rather than continuing to shrink.

### Left-Side Menu

A vertical, persistent menu rail (Power, Shades, Lights, Volume, etc.) with content filling the remaining width — the same structural idea as a navigation rail or a desktop app's sidebar, adapted for touch.

- **Composition:** a menu widget pinned to the left edge (structurally the same role as a footer/header widget: added once, present on every page) + content area filling the rest of the page.
- **When to use:** panels with enough horizontal width to spare a persistent rail without starving the content area or the rail's own touch targets — practically, this favors larger tabletop/lobby panels over small in-wall panels, and favors landscape orientation strongly (in portrait, the rail competes directly with content width in a way a header/footer never does). Scales to more menu items than Tabbed or a footer, since it can scroll vertically without hitting the touch-target floor.
- **Reflow:** the rail's width is typically fixed in absolute terms across resolutions, so it consumes a shrinking percentage of a smaller panel's content area. Below some resolution threshold this pattern should collapse to Header-Content-Footer rather than keep compressing the rail — which is why the skill should not offer this pattern for panels below a landscape width threshold in the first place.

## Choosing a Layout

When the user gives no design direction, the skill should make a deliberate first recommendation rather than just listing all five and asking the user to pick blind:

1. **Residential vs. Commercial** narrows header/footer content (per each pattern above) and nudges the choice itself — Bento Box (area-based, personality-driven) skews residential; Tabbed and Card-Based (subsystem-based, utilitarian) skew commercial, though neither is exclusive.
2. **Top-level item count** is the strongest structural constraint: ≤5 items fits Header-Content-Footer cleanly; 5–7 still fits Tabbed; beyond that, prefer Left-Side Menu (large panel) or Card-Based as a browsable grid (any panel) over cramming a footer/tab strip past §4's touch-target floor.
3. **Panel size and orientation** rules Left-Side Menu in or out first (needs landscape width to spare), then affects Bento Box's practicality — a dashboard with size hierarchy needs enough total area to read as intentional, not cramped.
4. Whatever is chosen still inherits every rule in §§2–8 (color roles, type scale, spacing/touch-target minimums, interaction states, elevation, density, cross-resolution consistency) — the layout pattern decides structure, not an exemption from the rest of this document.



## 2. Color System

A color system is roles, not hex values — "the buttons are red" is not a system,
"background_color is the brand's primary color, used only on the single most
important action per screen" is.

**Roles** (maps directly to `palette.py`'s already-implemented keys):
- `background_color` / `border_color` / `text_color` / `icon_color` — the base
  (normal-state) look, per component type.
- `pressed_*` / `selected_*` — interaction-state variants (see §5).

**Roles not yet implemented, needed for a real system:**
- **Primary vs. secondary vs. accent.** A UI where every button is the same
  saturated brand color has no hierarchy — nothing tells the user what's important.
  Rule: the brand's primary color is reserved for the single most important action per screen; everything else uses a secondary/neutral treatment. (Seen directly in the Cornell brand theming test this session: Carnelian reserved for components, a neutral light gray used for page backgrounds — not the same red painted everywhere.)

- **Semantic colors** — success/warning/error/info — distinct from brand colors,
  reserved exclusively for status feedback (a receive-signal indicator, a
  connection-lost state) so they're never ambiguous with a branded accent color.
- **Neutral/surface scale** — 2–3 grays for backgrounds, borders, and disabled
  states, so "gray" is a defined set of values, not whatever hex a page happened
  to get.

**Contrast rule (not yet enforced, should be):** text color against its own
background must meet a minimum contrast ratio (WCAG AA, ~4.5:1 for normal text,
~3:1 for large text). This is a legibility requirement, not polish — touch panels
are routinely viewed at a distance and under uncontrolled ambient lighting, more
like signage than a phone screen. `derive_states`' pressed/selected lightness
shifts already move toward/away from a base color; a future automated theming
pass should check the resulting text/background pair against this ratio and warn
(or pick a different text color) rather than trust that "white text" is always
safe.

## 3. Typography Scale

A defined hierarchy — title / heading / body / label / caption — each with its own size, not an arbitrary per-component font-size chosen in isolation. One font family with weight/size variation is generally safer on an embedded panel than pairing two different typefaces.

**Minimum readable size:** touch panels are viewed from further away than a phone or even a desktop monitor — a size that reads fine in a design mockup on a laptop may be unreadable on the wall. As a starting default (adjustable per project): body text no smaller than ~22px equivalent at the panel's native resolution, labels no smaller than ~18px, with the type scale increasing from there for headings.

## 4. Spacing & Sizing Scale

**Spacing unit:** a single consistent unit (8px is the common industry default)
that every margin, padding, and gap is a multiple of. This one rule, more than any other, is what separates a UI that looks "designed" from one that looks "placed" — inconsistent, arbitrary spacing is the most common visible signal of an unplanned layout.

**Minimum touch target size:** the single most common thing that makes a touch UI feel cheap when skipped. Industry reference points: 44×44pt (Apple HIG), 48×48dp (Material Design). Below this, users mis-tap, and it reads as an interface that wasn't actually designed for touch. This applies to the full tappable area, not just the visible icon/label inside it.

**Edge/safe-zone padding:** no touch target should sit flush against the panel's
own physical bezel — always reserve a minimum margin (a spacing-scale multiple)
between the outermost controls and the screen edge.

## 5. Interaction States

Already implemented (`palette.py::derive_states`, Phase 7): a component's pressed state defaults to its background darkened 15% ("pushed in"), selected defaults to lightened 12% ("highlighted"), with border/text/icon carrying over unchanged unless explicitly overridden. This document's job is to pin that down as house POLICY, not just a code default — any future per-project override of these deltas should be a deliberate design decision recorded here, not an accidental one-off.

Not yet covered: a `disabled` state. A control that can't currently be interacted with (e.g. a source button for an offline device) needs its own consistent visual treatment — conventionally reduced opacity or a desaturated variant of the normal state — so "this can't be tapped right now" is communicated visually, not just by the tap silently doing nothing.

## 6. Elevation & Shape

**Border radius:** a small, reused set of values (e.g. sharp/subtle/rounded —
2–3 options total) applied consistently by component role, not chosen per-instance. This skill already supports per-corner custom radius (`shape="custom"`, Stage 1) — the design-system role is deciding which of a small fixed set of radius values each component type uses, not inventing a new radius per button.

**Shadow/elevation:** if a project uses layering (cards, popups, modals), the
depth cues (shadow strength, or a border/background-contrast substitute where CH5 doesn't support real shadows) should follow a small consistent scale — "raised slightly" vs. "raised a lot" as two or three defined levels, not an arbitrary value per component.

## 7. Information Density & Hierarchy

Touch panels reward fewer, larger elements far more than desktop or even mobile
UIs do — a screen that would look sparse on a monitor often looks correctly
uncluttered on a wall-mounted panel viewed from a few feet away.

- A rule of thumb ceiling on controls per screen/widget, appropriate to the
  panel's physical size and viewing distance (a 5" in-wall panel and a 15"
  tabletop panel don't share the same density budget).
- One dominant action per screen — everything else visually subordinate (smaller,
  neutral-colored, or positioned less prominently) so the user's eye has an
  obvious first stop.
- Related controls grouped visually (shared background, spacing, or a border)
  rather than scattered at equal visual weight across the canvas.

## 8. Cross-Resolution Consistency

This skill already reflows content across every configured resolution
(`generator/reflow.py`) and, as of this session, correctly writes a themed
property to the catch-all and primary-resolution blocks so it's picked up
everywhere via real CSS cascade (`layout.py::update_element_declarations`). The
design-system rule this enables: every rule above (spacing scale, touch target
minimums, type scale, density ceiling) applies at EVERY configured resolution and orientation, not just the primary one. A layout that only respects these rules at its primary breakpoint and degrades at a secondary one isn't finished — reflow correctness is a prerequisite for design-system correctness, not a separate concern.

## 9. How the Skill Should Use This Document

When a user provides no design/color scheme (the `front-end-design`-skill-parity
case this document exists for): the skill should apply the defaults in §§2–7 as a starting point — a real, opinionated color/type/spacing system, not a blank or
arbitrary one — rather than asking the user to specify every value before
anything can be built. When a user provides partial direction (a brand color, a
style-guide URL, "make it feel modern") the skill resolves that into the SAME
role structure (§2's primary/secondary/semantic/neutral roles, not just one flat
color), so a minimal user request still produces a complete, consistent system
rather than one branded color applied inconsistently.
