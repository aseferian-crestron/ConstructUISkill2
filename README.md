# ConstructUISkill2 — Status

This file reflects current status in realtime. It is updated in the same turn as any
work it describes — never batched for later. Newest entries at the top of the Log.

See `docs/ConstructUISkill.md` for the feature spec and
`docs/architecture/` for the source-grounded architecture documentation this project is
built on (see **Approach** below).

## Current phase

**Regenerated the live Bento Box output end-to-end with actual persona-driven
design decisions -- the concrete follow-through on §1/§10, not just policy
text.** User: *"apply this persona-driven approach to actually re-generate the
Bento Box output."* Target: `C:\Solutions\ClaudeGenTest\GenTestProject2\
BentoBox.cuig` (the live file the user had reviewed in Construct and found
"not very good" -- backed up first to `BentoBox.cuig.bak` before overwriting).

Read the file as it stood: 7 cards (including a redundant "Clock" tile), an
existing but undocumented warm orange/charcoal palette and 12px rounded
corners from an earlier ad-hoc pass, and -- confirmed directly -- NONE of the
new font-size/icon-size fix applied yet (that code didn't exist when this file
was last written), several cards missing icons entirely.

Acting as §1's persona (senior touch-UI UX designer, luxury-residential
register -- these labels are a home's rooms/subsystems) for every decision
§10 now calls for, not a mechanical default:
- **Composition:** dropped "Clock" -- redundant with header date/time content
  (design doc's own Header-Content-Footer rule), wastes a dominant-action slot
  on a Bento grid. Kept "Currently Playing" as the sole "large" card (the
  single most-reached-for control in a media-forward home is the right
  dominant action), "Living Room" as the one "wide" card (the one
  multi-purpose gathering space), Kitchen/Bedroom/Guest Bathroom/Front Door as
  peer "small" cards.
- **Icons:** every one of the 6 cards gets a real Font Awesome icon now (play/
  couch/utensils/bed/lightbulb/door-open) -- §1's own "icons are the primary
  at-a-glance visual language" applied literally, not left partial like the
  first pass.
- **Color:** a considered warm brass/amber (`#C89B5D`) card fill on a deep warm
  charcoal (`#2A2622`) page background, dark warm-brown text/icon (`#211D17`)
  -- refined and justified rather than carried over unexplained; contrast
  verified via `color_words.contrast_ratio` (brass/text = 6.6:1, bg/card =
  5.9:1, both comfortable AA passes). Chosen specifically AGAINST a generic
  cold-blue "tech dashboard" look, which doesn't fit a luxury-residential
  register.
- **Shape:** "rounded" (12px) radius preset -- softer, warmer register fits
  residential better than "sharp," which is reserved for a commercial/
  boardroom project.
- **Typography/sizing:** kept `Manrope` (already a good, warm geometric-sans
  choice) as the one project-wide font; applied this session's new
  `TIER_TYPE_ROLE` scaling for real this time -- 28px label/40px icon on the
  large card, 22px/32px on wide, 18px/24px on the four small cards.

Rebuilt via the real generator functions end-to-end (`build_bento_box_page` ->
`shape.apply_radius_preset` per element -> `write_cuig` -> `theme_chat.
apply_palette_to_page_all_types` with `derive_states=True` -> `page.
set_page_background_color`), not hand-edited. Verified at every stage:
byte-identical round-trip after the structural write AND after the
theming pass, all 6 icons present, all 3 tiers' exact font-size/icon-size
pairs present, brass background-color present on every card (catch-all +
primary, per the project's own cascade rule), derived pressed (`#a27537`,
darker)/selected (`#d8b78b`, lighter) states present, page background
updated. Full suite re-run clean except the two known pre-existing unrelated
failures. Awaiting the user's live Construct confirmation that this actually
reads as "very good" now, not just mechanically correct.

**§1 persona is now the stated driver of every design decision, not a
preamble.** User: *"yes, the AI-Based Persona should drive everythign any time
a design has not been provided."* Previously §10 framed the doc's own numbers
(§§3-8) as defaults the skill mechanically plugs in -- exactly the "generic
templated" failure the user rejected in the first Bento Box run. Rewrote §10:
when no design is given, the skill ADOPTS the §1 persona for every real
decision across §§2-9 (layout pattern, accent hue, font pairing, radius/
elevation preset, icon choice, density trade-offs), with §§3-8's numeric
floors/ceilings as constraints those decisions must satisfy, not the decision
itself -- same precedent as `theme_chat.py`'s own move away from a hardcoded
color-name lookup table (no code table can enumerate every luxury-residential/
yacht/boardroom/nightclub look a project might need). Also aligned §2's
opening line, which still said the skill "asks the user to select from the
patterns below," contradicting both the existing "Choosing a Layout"
(deliberate recommendation, not blind pick) and this same directive -- now
recommends per §1, only asking the user for audience/context info only they
can supply. Policy-doc change only, no code -- persona-driven resolution is
chat-AI reasoning, not something a generator function encodes.

Separately noted (not acted on): an unrelated OLDER "construct-ui-skill"
plugin package exists at `~/.claude/plugins/marketplaces/crestron-construct-
skills/` -- appears to be the paused v1 skill (see `project_construct_skill.md`
memory), not this project. Flagged to the user in case it's ever the copy that
actually loads instead of ConstructUISkill2.

**Fixed the actual root cause of the Bento Box quality complaint: labels/icons
were rendering at CH5's own tiny built-in default, never sized.**
`build_bento_box_page` never wrote a font-size for a card's label or its icon
-- confirmed via `style.style_property_catalog` that these are two DISTINCT
real stylable properties (`.ch5-button--label`'s `--ch5-button--regular-
font-size` vs. `.ch5-button--icon`'s `--ch5-button--regular-icon-size`), same
parallel structure across all three button-family types. `typography.py`
gains `ICON_SCALE` (paired 1:1 with the existing `TYPE_SCALE` roles) +
`apply_icon_scale`. `layout_patterns.py` gains `TIER_TYPE_ROLE`
(large->heading, wide->body, small->label) and now ALWAYS applies both scales
per card by tier -- baked into the builder by default (not a separate caller
styling pass), matching how touch-target enforcement is already baked in
everywhere else. New `primary_query` kwarg threads through, matching this
project's "catch-all + primary resolution only" rule. `bento_box_test.py`
extended: label/icon size match tier for the right cards, `primary_query`
duplicates both into that resolution's own block. Full suite re-run clean
except the two known pre-existing unrelated failures. Cross-referenced into
`ConstructUISkill_DesignSystem.md` §4.

**New design-system §1: "AI-Based UX Persona" -- reaction to the Bento Box
quality bar not being met.** User: *"i was not happy with the first run of the
Bento box design. The icons and fonts were too small and the overall look &
feel was not very good. I updated the ConstructUISkill_DesignSystem.md file
with a directive that must be followed any time a skill user has not provided
a design or color palette."* Added directly by the user: when no design/color
scheme is given, the skill must act under a stated persona -- a senior
touch-UI UX designer specializing in luxury residential/yacht and commercial
conference/event/hospitality spaces. Every other design-system section shifted
down one (§1 Layout Patterns -> §2, ... §9 How the Skill Should Use -> §10).
Also added to `ConstructUISkill.md`: a "two purposes" framing (natural-language
project editing + access to an AI-driven professional UX developer).

**Same local edit reverted several already-confirmed sections -- third
occurrence of this exact stale-local-copy pattern.** Diffed the user's
working-tree change before merging (this project's own discipline: never
silently accept an edit that also deletes settled, source-grounded content).
Confirmed reverted, unrelated to the new persona work: the `.cuib` "Out of
scope" note, the whole "Page-based project rules" section (theme color,
page/widget background, background-image mechanism), the Contract-based
navigation hard requirement, the §5 Global Contract citation inside the Layout
Patterns intro, and the `html-div` control-grouping mechanism note under
Information Density. Also found the confirmed "disabled state has zero
stylable properties" research finding replaced with new text implying it's
merely "not yet covered." Surfaced all of this to the user directly (via
`AskUserQuestion`) rather than assuming intent either way -- got two clear
answers: restore everything reverted, and the disabled-state rewrite was ALSO
accidental (not a deliberate reopening toward an opacity/desaturation
approach) -- restore the confirmed finding there too.

Restored all of it while keeping the user's new content, then fixed every
internal §-cross-reference in the design-system doc that went stale from the
new §1 insertion (every old §N reference to Color/Typography/Spacing/
Interaction/Elevation/Density/Cross-Resolution needed +1) -- these were left
unrenumbered in the user's own edit and would have pointed at the wrong
section. Two commits. No code changed -- policy-doc reconciliation only. The
actual Bento Box quality-bar fix (bigger icons/fonts, applying the new
persona to real output) is the next real task.

**Bento Box cards now support icons + a chosen font -- real UX bar, not
defaults.** User ran the first Bento Box output through the
`frontend-design` skill's own standard and correctly rejected it: flat
single-color cards, no icons, no typography pairing, unused elevation
tooling -- the generic template that skill explicitly warns against, not a
considered design.

`component.py::build_component_attributes` now forwards `icon_class`/
`icon_library` to `ch5-button`'s own builder (`ch5_button.py` already
supported them end-to-end; the generic dispatch just never passed them
through) -- `ch5-button`-only, ignored for other types, same treatment as
`label`/`active_font`. `layout_patterns.py::build_bento_box_page` gains
`icons` (label -> `(icon_class, icon_library)`, real Font Awesome values)
and `active_font`. A card WITH an icon switches from the schema's
dead-centered default to icon-above-label (`orientation=vertical`,
`iconposition=top`, `halignlabel=left`, `valignlabel=bottom` -- all 4
confirmed real schema enum values), via `style.set_html_attribute`, the same
post-build attribute-flip shape `apply_radius_preset` already uses. A card
with no `icons[]` entry is untouched.

`bento_box_test.py` extended: icon/library attributes present, exactly the
icon-bearing cards get the layout flip (not the rest), `active_font`
applied, written `.cuig` round-trips. Full suite re-run clean except the two
known pre-existing unrelated failures.

**Design System Phase 7 (§1 layout patterns): Bento Box built end to end.**
An asymmetric grid of variously-sized cards, placed by a new
`_pack_bento_grid` helper -- CSS Grid's own default "sparse" row-major
auto-placement algorithm (a well-known, standard algorithm, not invented for
this project): for each item, scan rows top-to-bottom then columns
left-to-right for the first position where its cell-span fits unoccupied.
Three named size tiers per §1's own example and "2-3 card sizes max" rule:
`"large"` (2x2 cells), `"wide"` (2x1), `"small"` (1x1) -- cells kept square
(one `cell_size` derived from page width/column count, reused for height) so
"grid units" stays one measure, not independent width/height scales.

Each card is an ordinary `ch5-button` -- no extra navigation wiring needed at
all, since the prior turn's Visibility=Contract work already means the
control system (not the button) decides what's shown; a card just needs its
normal default contract signals, which `component.build_component` already
applies. Styling (background/border/shape) deliberately left to the caller
(`palette.py`/`shape.py`), matching the footer/header builders. Raises
`ValueError` for a column count that would push cells below the touch-target
floor, and for a card count/size needing more height than the page provides
-- same "raise rather than silently overflow" discipline as the footer's
`_layout_row`. §7's density ceiling stays a standalone advisory
(`density.py::check_density`) the caller runs itself, not wired into this
builder's return shape.

Verified against a real written `.cuig`: round-trips byte-identical, correct
labels, and -- directly on the actual written geometry, not just the input
spec -- the size hierarchy holds (`area("Currently Playing", large) >
area("Living Room", wide) > area("Guest Bathroom Lights", small)`), proving
§1's own intent ("size communicates importance") survives all the way to the
file. Full suite re-run clean except the two known pre-existing unrelated
failures. Plan doc detailed just-in-time before coding, same convention as
footer/header.

Remaining in Phase 7: Card-Based, Tabbed, Left-Side Menu, then Phase 8
(top-level orchestration).

**Navigation is contract-driven, not page-flip -- prerequisite for Bento Box's
"cards open a page/popup" composition, resolved before building it.** While
scoping Bento Box, found that "each card opens a page or popup" had no real
mechanism behind it either: every button this generator writes carries
`pageflip="0"`, but no reference file anywhere shows a real non-zero value, so
I didn't know how a button tells Construct which page to open. Asked the user;
their answer: *"no one uses local page flip programming. your job is to
properly name the components and enable contract support for each
component... every page in the project should have the Page Visibility Join
set to Contract. Every widget that is added to a page should have its
Visibility property set to Contract."* -- the control system decides what's
shown, not local pageflip logic on a button. This replaces a dead-end
investigation with the mechanism this project already uses for everything
else.

- `page.py::build_page_attributes`: `VisibilityJoin` now defaults to
  `contracts.CONTRACT_ENABLED` ("Contract Enabled") instead of `"0"`.
  Confirmed real (not guessed) via `C:\Git\CCIDE`'s `PersistenceHelper.cs`
  (`VisibilityJoin` is a plain STRING, join-bindable page attribute, not a
  numeric-only join) and `ContractGenerationHelper.cs` (writes the identical
  `"Contract Enabled"` sentinel this project's own `contracts.CONTRACT_ENABLED`
  already models for every other signal -- one generic mechanism, confirmed
  to generalize, not a page-specific fact).
- `page.py::make_widget_reference`/`add_widget_reference_to_page`: now take
  `sdk` and always enable the `<ch5-template>` widget-reference element's
  `Visibility`/`Visibility_fb` signals. Confirmed via
  `contracts.contract_signals(sdk, "ch5-template")`, which already resolves
  `sendeventonshow`/`pd-receivestateshow` through `component-context.json`'s
  `global` attributeProperties fallback (`ch5-template` defines neither
  itself) -- the exact same global-fallback path `JoinNameProviderHelper.cs`
  uses on the real C# side, so this needed zero new signal-resolution code,
  just calling the existing `contracts.enable_contract_signals` with the
  right tag/names.
- `phase3_smoke_test.py` updated: the real `Widget on Page.cuig` reference
  predates this rule (captured with default/unset visibility), so its
  exact-attribute-set assertion against that file now explicitly accounts for
  the 2 new signal keys rather than silently widening the check. Full suite
  re-run clean except the two known pre-existing unrelated failures.
  Cross-referenced into `ConstructUISkill.md`'s Page-based project rules as a
  new hard requirement.

Bento Box itself (card grid, sizing tiers, hierarchy) starts next now that
both blocking gaps (control grouping via `html-div`, navigation via
Visibility=Contract) are resolved.

**New component: `html-div`, the real mechanism behind §7's control-grouping
rule — blocking requirement, resolved before Bento Box.** User: *"do you have in
your documents anywhere that the DIV component should be used to
group/surround components so they look organized?"* No — §7 named the policy
("Related controls grouped visually -- shared background, spacing, or a
border") but never a mechanism. User then: *"The DIV component is a pure HTML5
component inside Construct... You MUST utilize this component and figure out
how to use it for styling as well. This is a requirement that blocks
everything until you finish."* User added two real reference instances to the
sample project (`Component - DIV.cuig`, `Component - HTML - DIV.cuig`).

Traced from those: `html-div` is genuinely NOT a `ch5-*` custom element --
confirmed absent from `component-context.json`'s own 50-tag schema (checked
directly via `sdk.read_sdk(...).component_context`) -- so unlike every other
component this project builds, there is no SDK catalog to read attributes or
style properties from; grounded entirely against the two real files instead.
Two confirmed, non-guessable quirks: the Html tag is literally `<div>` while
the TOML `[[Elements]]` `Type` is the separate literal `"html-div"`;
`ccid_lteHTMLOnly` is a bare boolean attribute in Html but an ordinary
`"true"`-valued key in TOML -- a real asymmetry, not a bug. The two reference
files disagreed on `[[Elements]]` shape (the older one carries extra
`Name=""`/`Status=""`/`Content=""`); treated the newer (2026-09-15) file as
authoritative, same precedent this project already applies when two real files
disagree.

**Styling answer (the "figure out how to use it for styling" half):** unlike
every `ch5-*` component (styled via `--ch5-*` CSS custom properties because
that's what the CH5 web component's own property grid reads), a div's
background-color/border-*/border-radius are PLAIN literal CSS declarations
written straight into its `#id{}` rule -- confirmed against the reference.
This is exactly the shape `layout.py::build_position_css`'s existing
`extra_vars` parameter and `update_element_declarations`'s existing
merge-by-name logic already handle -- both reused as-is, no new CSS-writing
mechanism needed. Also confirmed duplicated into the PRIMARY-resolution block,
matching the already-established catch-all + primary rule.

`generator/html_div.py` (new): `build_html_div` (initial placement, same
`(html, css, Element)` return shape as `component.py::build_component` so it
drops into any layout-pattern builder's assembly) + `style_html_div` (restyle
an EXISTING div, touching only the properties given). `html_div_test.py`
covers: attribute-for-attribute match against the real reference (name, order,
bare-vs-valued shape), every real style property present in both the catch-all
and primary blocks, a written `.cuig` round-trips byte-identical, position/size
still parses correctly alongside the extra literal declarations (proving it
coexists with the existing reflow machinery the same way a themed button's
custom properties already do), and two sequential restyle calls that only ever
touch the property each one names. Full suite re-run clean except the two
known pre-existing unrelated failures. Cross-referenced into
`ConstructUISkill_DesignSystem.md` §7 (mechanism note + function pointer),
same treatment as the Global Contract hard requirement.

Bento Box (next in Phase 7) can now use `html-div` for its card
backgrounds/borders -- this was the blocking gap.

**Design System Phase 7 (§1 layout patterns): header widget built end to end.**
`build_header_widget` composes the Header-Content-Footer pattern's header --
genuinely heterogeneous content, unlike the footer's N-equal-buttons. Source
check confirmed only 2 of the design doc's 4 header content items (§1: "time,
weather, area status, active source" / "date/time, active source, corporate
logo") are real distinct component types -- `ch5-datetime` and `ch5-image`
(commercial only, per the doc's own line); "weather"/"area status"/"active
source" have no dedicated component, so they're `ch5-text` with caller-supplied
`status_items` labels (this generator doesn't invent a project's own status
text, same reasoning `theme_chat.py` uses for leaving color *resolution* to the
driving chat AI). New `_layout_header_row` helper (deliberately NOT a reuse of
the footer's `_layout_row` -- different problem shape, fixed-width items
(logo/datetime) alongside flexible status-text items dividing remaining space
evenly, no touch-target floor since this content is informational, not
interactive). `ch5-datetime`'s fixed width (200x35) transcribed from a real
instance (`Component-Widgets-DateTime.cuig`), not guessed. Task detailed
just-in-time in the plan doc before coding, matching this project's own
convention. Verified against 2 real written `.cuiw` files (commercial: logo +
datetime + 1 status text; residential: datetime + 3 status texts, no logo):
both byte-identical round-trips, `globalControlContract="on"` present on both.
Full suite re-run clean except the two known pre-existing unrelated failures
(the 74-vs-75 catalog count, and a `page_background_color_test.py` live-project
drift -- confirmed via `git stash` that both predate this session's changes).
Remaining: the other 4 layout patterns (Bento Box, Card-Based, Tabbed,
Left-Side Menu).

**Design System Phase 7 (§1 layout patterns) started -- footer built end to end.**
The first genuinely new widget-building orchestration this project has generated
(no header/footer code existed before this phase). `layout_patterns.py::
choose_layout` (item count is the strongest constraint per §1's decision order,
audience/orientation nudge within that) + `build_footer_widget` (composes widget
creation + `is_global=True` + N placed buttons via the new `_layout_row` helper,
which enforces §4's touch-target/spacing rules and raises rather than silently
overflowing). Verified against a real written `.cuiw`: byte-identical round-trip,
`globalControlContract="on"` present, every button meets the touch-target floor.
§8 cross-resolution acceptance criterion satisfied by construction (same CSS shape
reflow.py already handles generically) rather than a redundant reflow test. No
regressions. Remaining: `build_header_widget` (different problem --
time/weather/logo content, not N-equal-buttons) and the other 4 layout patterns.

**Design System Phase 6 built (§7 information density).**
`density.py::DENSITY_CEILINGS` (3 breakpoints by panel diagonal) + `check_density`
-- advisory-only, never raises, never writes, returns warnings naming the real
count/ceiling/panel size. Not a file-format writer, no source-grounding needed.
"One dominant action" + control grouping deliberately not modeled as standalone
functions -- real shape decided when Phase 7 (Layout Patterns) starts.

**Design System Phase 5 built (§6 elevation/shape).**
`shape.py::RADIUS_PRESETS` (sharp/subtle/rounded) + `apply_radius_preset`, scoped to
`ch5-button` only -- corner-radius is also stylable for button-list/datetime/text
but their `shape="custom"` gate isn't confirmed, not extended without that check
(same discipline as Phase 3). `shape.py::ELEVATION_LEVELS` -- confirmed zero
shadow/elevation style properties exist anywhere, so this is the design doc's own
anticipated border-width-step fallback, needing no new writer at all (plugs
directly into `palette.apply_palette`'s existing `border_width` key). Both verified
against a real button, byte-identical round-trips. No regressions.

**Design System Phase 4 built (§3 typography scale).** Source check confirmed
`font-size` is a real `--ch5-*` targetProperty for every text-bearing type already
in `palette.PALETTE_MAPPING` -- and caught a real trap: each type's schema also
carries an unrelated synthetic `custom-font-size` source property (no `--` prefix,
not a real CSS var) that could easily have been used by mistake.
`typography.py::TYPE_SCALE` (5 roles, strictly ascending, body/label matching the
design doc's own floors) + `apply_type_scale` (reuses the exact same selector
`PALETTE_MAPPING` already has for each tag's `text_color` -- no duplicate table
needed). Verified against a real component in a scratch copy of `GenTestProject2`:
byte-identical round-trip, sibling elements untouched. No regressions.

**Design System Phase 3 investigated -- confirmed NOT buildable (§5 disabled state).**
Ran the source check the plan required before writing any code: `style.style_property_
catalog` for every currently-mapped type (button/toggle/dpad/signal-level-gauge/
slider) has ZERO `disabled`-scoped entries, vs. dozens for `pressed`/`selected`; a raw
`component-context.json` search confirms `disabled` is only a plain attribute
default, never inside `classToVariableMapping`. Real platform limit, not a curation
gap -- whatever a disabled component looks like is baked into CH5's own component
styling, not exposed for override. No code to write; updated
`ConstructUISkill_DesignSystem.md` §5 and the plan to record the finding so a future
session doesn't re-attempt it.

**Design System Phase 2 built (§2 color roles).** 2 commits:
`color_words.py::adjust_saturation`/`rotate_hue` +
`palette.py::resolve_color_roles(primary, secondary=None, accent=None)` (secondary =
desaturated primary, accent = 30° analogous hue shift -- judgment calls, documented
as such, same precedent as `derive_states`); `palette.py::SEMANTIC_COLORS`
(success/warning/error/info) + `NEUTRAL_SCALE` (3 grays, ordering verified via real
WCAG luminance). No regressions. Phases 3-8 not started.

**Design System implementation plan written + Phase 1 built.**
`docs/superpowers/plans/2026-09-15-design-system.md` sequences the design-system
doc's 9 sections into phases (only Phase 1 detailed to step-by-step code; the rest
scoped -- real files/functions, confirmed vs. needs-source-check flags -- to be
detailed just-in-time, matching this project's own `docs/architecture/01-index.md`
convention). Phase 1 (the two prerequisite-free, pure-policy foundations, no
`C:\Git\CCIDE` source-grounding needed) is done, 3 commits:
- `generator/spacing.py` (§4): `SPACING_UNIT`/`MIN_TOUCH_TARGET`/`EDGE_PADDING` +
  `snap_to_spacing`/`meets_touch_target`/`enforce_touch_target`. TDD caught a real
  bug before it shipped: the first draft's `round(value / SPACING_UNIT) *
  SPACING_UNIT` sent `snap_to_spacing(4)` to `0` instead of `8` -- Python's
  `round()` is round-half-to-even ("banker's rounding"), wrong for a spacing scale.
  Fixed to a floor-based round-half-up formula; plan updated to match what shipped.
- `color_words.py::contrast_ratio` (§2): standard WCAG 2.1 relative-luminance +
  contrast formula, verified against known reference pairs (white/black=21:1,
  `#767676`/white≈4.54:1 -- the textbook "just barely passes AA" gray).
- `palette.py::check_contrast` (§2): wraps `contrast_ratio` against a resolved
  palette's `background_color`/`text_color`, returns `(None, None)` rather than
  raising when either key is missing. Re-ran `palette_test.py` -- no regression.

Phases 2-8 (color roles, disabled state, typography, shape/elevation, density,
layout patterns, top-level orchestration) not started -- paused here deliberately
(user is near their weekly usage cap) rather than continuing into less-scripted,
more exploration-heavy phases today.

**Cross-referenced the Global Contract hard requirement into the design-system doc.**
User: *"the header/footer is part of the Design System document"* -- correcting my
framing of the previous entry, which called header/footer-building orchestration an
untracked gap; it's actually already scoped as §1's Layout Patterns (Header-Content-
Footer, Tabbed, Left-Side Menu all build header/footer/menu widgets). Added one note
to §1's shared intro (covers all five patterns, not repeated per-pattern): any widget
a pattern adds to every page must be built with `is_global=True` per §5's hard
requirement, citing the exact function (`default_widget_html_css`) landed last turn.
No code change -- doc cross-reference only.

**New hard requirement: common (all-pages) widgets must set "Global Contract" true.**
User added to `ConstructUISkill.md` §5: *"Any time a common widget is added to all
pages, the Global Contract property for the widget must be set true."* (Their edit
again reverted the `.cuib` "Out of scope" note and the whole "Page-based project
rules" section -- same pair as last time; restored both, kept the new line. Second
occurrence of the identical pair, worth the user checking whether they're editing
from a stale local copy of this file.)

Confirmed from `C:\Git\CCIDE` source before implementing (no reference project has
this attribute set, so source-reading was the only path, per this project's core
approach): `WidgetDto.cs`'s `IsGlobal` and `components.ts`'s property-grid trait
(category "Interactions", label "Global Contract", `name: globalControlContract`)
confirm the property name; `SubpageTemplate.json`'s widgetContainer root element
declares `globalControlContract` as a `DefaultAttribute`; `GlobalSubpageConverter.cs`
settles the exact serialization -- the SAME value (`"on"` if true) is written
unconditionally into both the Html section (`SetAttributeValue`) and the TOML
`PageElementDto.Attributes` (`.Attributes.Add`), never just one. (The converter's own
true/false *detection* heuristic is legacy Import-path logic, flagged mid-refactor in
the source itself with a dangling TODO -- not used here; the generator sets this
explicitly at build time since the caller already knows a widget is being built as
common/global, no inference needed.)

Implemented: `page.py::default_widget_html_css` gains `is_global: bool = False`.
When true, writes `globalControlContract="on"` into the widget root div's Html and
adds the same key/value to the widgetContainer Element's TOML attributes; when
false (the default), the attribute is omitted entirely from both -- no reference
file confirms Construct's own UI-editor save path (as opposed to the Import-only
converter read here) always writes an empty-string form for ordinary widgets too,
so left unguessed rather than speculatively applied to every widget. New
`global_widget_test.py`: round-trips both a global and an ordinary widget
byte-identical, asserts the attribute's presence/absence in Html AND TOML for each.
Re-ran `phase3_smoke_test.py` (the only other caller of this function) -- no
regression, all prior assertions unchanged (new parameter is kwarg-only,
default-False). No header/footer-building orchestration exists yet to actually call
this with `is_global=True` (still not built, per §1's own layout-pattern status) --
this lands the file-format capability so that work can use it once it starts.

**`generator/_test_output` regenerated output is no longer tracked in git.**
Every test script in that folder wipes and rebuilds its own output on each run
(one even recopies from the live external project), so the previous partial
`.gitignore` rules (by file extension + by named Smoke/Reflow dir) still let
`ContractsAutoStale/`, `ContractsE2E/`, `ContractsTask3/`, and `FontsGlobalSwap/`
through -- exactly the four dirs that kept dirtying `git status` after every
test run (see the two entries below). Replaced the whole enumerated list with
`generator/_test_output/*` + `!generator/_test_output/*.py` -- ignore
everything in the folder by default, re-include only the 61 top-level
`*_test.py` scripts (the real source; confirmed none are nested deeper, so the
one-level re-include is complete). `git rm -r --cached` on the 59 previously
tracked non-`.py` files (output data only, verified by folder) removed them
from tracking without touching them on disk.

**Fixed the flagged font-regex bug + cleaned up `generator/_test_output` churn.**
`fonts.py::_FONT_FAMILY_RE` required a leading quote character, so it silently
skipped an unquoted `font-family:Creepster;` value in the live project's
`ReflowTest.cuig` (every other occurrence there is quoted) -- `set_project_font`
would report success while leaving that one rule on the old font. Fixed:
`_FONT_FAMILY_RE` now has a quoted/unquoted alternative, and a new
`_font_family_repl` helper picks the right replacement shape (quoted stays
quoted with the same quote char, unquoted stays unquoted) instead of the old
fixed replacement string, which couldn't express "no quote." RED/GREEN
verified: added 3 unquoted cases to `fonts_global_swap_test.py` (bare
`;`-terminated, spaced, `}`-terminated), confirmed they failed against the old
regex, then passed after the fix, then re-ran the full file -- all existing
quoted/case/selector-shape assertions still pass, `set_project_font` against
the live `FontsGlobalSwap` copy now reports the file as touched.

Separately, noticed `generator/_test_output/{ContractsAutoStale,ContractsE2E,
ContractsTask3,FontsGlobalSwap}` are tracked in git despite every one of their
test scripts wiping and rebuilding that directory from scratch on each run
(`fonts_global_swap_test.py` even re-copies from the live external project at
`C:\Solutions\ClaudeGenTest\GenTestProject2`) -- so every run produces pure
diff noise (fresh timestamps/GUIDs) unrelated to any real generator change.
Discarded that noise back to the last commit rather than committing it (twice
-- once before this fix, once after re-running the test to verify it). Not a
code change, just working-tree hygiene; `.gitignore` already excludes this
exact class of thing for the *Smoke/Reflow* test dirs by name, it just doesn't
cover these four. Worth adding to `.gitignore` in a future session if this
keeps recurring.

**Design-system policy doc: §1 Layout Patterns filled in.** User added the five
patterns directly (Header-Content-Footer, Bento Box, Card-Based, Tabbed,
Left-Side Menu) plus the rule that the skill asks Commercial-vs-Residential
when no design is given. I then fleshed out each pattern to match the rest of
the doc's rigor -- per pattern: composition (grounded in `ConstructUISkill.md`
§5's page-per-selection + header/footer-as-widget rules, e.g. Tabbed reuses the
header widget as a tab strip, Left-Side Menu is structurally a widget pinned
like a footer), when to use it, how it reflows across resolutions, and which
§§2-8 rules constrain it most (e.g. Bento Box flagged as most likely to violate
§7's density ceiling; Tabbed's selected state reuses the already-built
`derive_states` rather than inventing a new one). Grounded the item-count/size
thresholds in real touch-UI conventions: ~5-item cap on Header-Content-Footer's
footer and ~5-7 tabs before overflow (both from Material Design's bottom-nav/tab
guidance), Left-Side Menu gated to landscape/larger panels with an explicit
collapse-to-footer rule instead of letting the rail keep shrinking. Added a new
**Choosing a Layout** section: a decision order (Residential/Commercial ->
top-level item count -> panel size/orientation) so the skill can make a first
recommendation instead of listing all five and asking the user to pick blind.
All 9 sections of the doc now have content -- still a POLICY document only, no
generator code changed this turn. Committed.

**New design-system policy doc started: `docs/ConstructUISkill_DesignSystem.md`.**
User: *"this skill should assist users with building a full user interface that
follows common industry practices and patterns for touch based user interfaces...
i want this skill to have the same feature [as the `front-end-design` skill] when
a user doesn't have a design or color scheme in mind."* This is a POLICY document
(a draft, user is continuing to write/refine it), not a record of new code --
covers color roles (primary/secondary/semantic/neutral, beyond the already-built
`palette.py` keys), a contrast-ratio rule not yet enforced, a type scale,
a spacing unit + minimum touch-target size (the most commonly-skipped thing that
makes a touch UI feel unfinished), interaction states (cites the already-built
`derive_states` pressed/selected policy, flags a not-yet-built `disabled` state),
elevation/shape, information density limits (touch panels reward fewer, larger
elements than desktop/mobile), and a cross-resolution-consistency rule tying back
to this session's reflow/catch-all-plus-primary work. §1 (Layout Patterns --
header/footer, bento box, card-based, etc.) is left for the user to fill in
separately. Not yet committed -- user is actively iterating on it.

**Phase 7 (themes), Stage 3 source (online style guide) + page/widget background
color support.** User: *"i want to test pointing the skill to an online style
guide... i want the project styled according to this guide:
https://brand.cornell.edu/design-center/colors/ and it should include any
background colors required."*

Same architecture as the NY Giants/Halloween case: no new resolution logic
needed in the generator -- I (the driving chat AI) fetch and read the real
page, extract the actual published colors, and call the existing
`apply_palette_project_wide_all_types` with a resolved dict. Real Cornell
palette fetched (`brand.cornell.edu/design-center/colors/`): Carnelian
`#B31B1B` (primary), Dark gray `#222222`, White `#FFFFFF`, Light gray
`#F7F7F7` (secondary/neutral).

One real gap surfaced by "should include any background colors required":
page/widget SOLID background color (`DisplayBackgroundColor`/`BackgroundColor`
in `{PageAttributes}`) had a WRITE path only at project-CREATION time
(`page.py::build_page_attributes`/`build_widget_attributes`) -- no way to set
it on an EXISTING page, which is all this live project has. Added
`page.py::set_page_background_color(page_path, background_color, *,
display=True)`: edits only the `[Attributes]` table's own lines via the same
text-splicing discipline used throughout this project (never a full TOML
round-trip, which would risk the confirmed-load-bearing attribute order) --
`{Html}`/`{Css}`/the `[[Elements]]` tree are provably untouched.
`page_background_color_test.py` (new) covers: setting on a fresh page (flag
flips, color inserted right after `DisplayBackgroundColor`, Html/Css
byte-identical, round-trips), re-applying a different color updates in place
with no duplicate line, and the same function works on a real widget (`.cuiw`)
too. Full suite re-run: clean except the one known pre-existing unrelated
catalog-count failure, PLUS a newly-noticed SECOND pre-existing drift item
(unrelated to this work, confirmed by inspection): `fonts_global_swap_test.py`
now fails against the live project's `ReflowTest.cuig` because one slider's
theme-selector rule carries an unquoted `font-family:Creepster;` (every other
occurrence in the project is quoted) -- `fonts.py::set_project_font`'s regex
doesn't match the unquoted form. Not caused by today's work (`set_page_
background_color` never touches fonts); flagged for a future session, not
fixed now.

Applied live to `GenTestProject2`: real Cornell brand colors --
`background_color`/`text_color`/`border_color`/`icon_color` =
Carnelian/White/Dark gray/White applied project-wide across every mapped
component type (`apply_palette_project_wide_all_types`, full 3-state
coverage), and `#F7F7F7` (Cornell's own secondary/neutral light gray) set as
the solid background on all 12 pages/widgets via the new
`set_page_background_color` -- a neutral canvas reserving the bold primary
red for interactive elements, standard brand-usage practice rather than
painting every page background the same saturated primary color. Verified on
disk: every file round-trips byte-identical. Awaiting the user's live
Construct confirmation.

**Phase 7 (themes) SECOND CORRECTION: styling was over-replicating into every
resolution block; corrected to catch-all + primary only, matching real CSS
cascade.** User demonstrated the real rule directly in Construct: *"i just added
a new button to the Check page and what i did was set three different fill
colors to demonstrate cascading. primary resolution (including 99999) has red...
no changes to TSW-760 so no media query is written... the only thing that should
ever be written to a media query is a delta between the parent query and the
active query. this is the pattern of cascading style sheets. the ONLY deviation
is that Construct replicates the primary resolution data... into a media query
at 99999. other than that, no replicated data in any media query should exist."*

My PREVIOUS fix (see the entry below this one) over-corrected: after finding the
property-grid-needs-an-explicit-value problem, I made `layout.py` write every
style property into EVERY configured resolution's block unconditionally. Wrong
-- that's un-cascaded duplication real Construct never does. The correct rule,
now implemented: catch-all always gets it (mirrors primary); the PRIMARY
resolution's own block gets it too (Construct's one real deviation); every
OTHER resolution is left alone entirely, relying on real CSS cascade.

- `layout.py::update_element_declarations`: now takes `extra_queries` (typically
  just the primary resolution's query) instead of writing everywhere. Also
  reports `blocks_updated` correctly and raises only if the catch-all itself has
  no rule for the element.
- `style.py::set_component_style` / `palette.py::apply_palette`: gained
  `primary_query: str | None`, forwarded down to `update_element_declarations`.
- `theme_chat.py::_primary_query_for(project_dir)` (new): finds the project's
  one `.cuip`, resolves its primary landscape/portrait resolution, and returns
  that resolution's own media query. Every apply function
  (`apply_palette_to_page(_all_types)`, `apply_palette_project_wide(_all_types)`,
  `apply_chat_style`) now computes this once (project-wide callers) or
  auto-computes it per page (`primary_query="auto"` sentinel default) and
  threads it through, so a themed value reaches the primary block too, without
  the caller needing to know about it.

`custom_style_test.py` rewritten: the earlier (now-wrong) "device block also
gets it" assertion inverted to a before/after byte-identical comparison (no
`primary_query` given -> the device block is provably untouched, whatever its
pre-existing content), plus new coverage that an explicit `primary_query`'s own
block DOES get the value while a different, non-primary block still doesn't.
Full suite re-run clean except the one known pre-existing unrelated failure.

**A real mishap during live cleanup, disclosed in full**: re-applying the
corrected code to `GenTestProject2` still left every earlier (wrongly
over-replicated) resolution block carrying stale style declarations, so I wrote
an ad-hoc script to strip them back out everywhere except catch-all/primary.
That script had a real bug: when a block's rule contained *only* a style
declaration and nothing else (exactly the correct minimal-delta shape the
user's own Check.cuig demonstration used), stripping the key left an empty,
invalid `#id{;}` rule instead of removing the rule entirely. This destroyed the
actual fill-color value the user had set by hand on `Check.cuig`'s new button
for the TSW-570 resolution -- the specific value is UNRECOVERABLE; only the
structural corruption (the empty rule) could be fixed. Confirmed via direct
inspection that this was the ONLY casualty -- the other three files the same
cleanup touched (`AllComponents - Buttons.cuig`, `ButtonVariants.cuig`,
`ReflowTest.cuig`) were checked rule-by-rule and are correct (position/size
intact everywhere, only the out-of-scope style keys removed from non-primary
blocks). The user needs to re-set that one TSW-570 color by hand; I cannot
recover it. Lesson: an ad-hoc data-rewriting script against LIVE user data
needs the same "prove it first, small-scale" discipline as generator code --
this one was run directly at full scope without first checking whether
stripping could ever produce a degenerate empty rule.

**Phase 7 (themes): normal/pressed/selected 3-state styling.** User: *"you are
not styling the 3 states of a button. normal, pressed and selected. this needs
to be covered when you style components and you should apply standard
practices for web components when you need to show a normal, pressed and
selected state."* Real gap -- Stage 1/2 only ever covered the "default"/normal
state. Confirmed via `style.style_property_catalog` that `ch5-button`/
`ch5-button-list`/`ch5-tab-button` (the three button-family types) carry a full
PARALLEL pressed/selected property set in the real schema (their own background/
border/label/icon selectors, sectorPrefix `pressedAppearance_`/`pressedLabel_`/
`pressedIcon_` and the `selected` equivalents) -- not guessed, the same
schema-survey discipline as every other palette entry.

- `palette.py`: `_BUTTON_PALETTE`/`_BUTTON_LIST_PALETTE`/`_TAB_BUTTON_PALETTE`
  extended from 6 keys to 18 (`pressed_background_color`, `selected_border_color`,
  etc. -- full parallel set for all three types).
- `palette.py::derive_states` (new): expands a normal-state-only palette into a
  full 3-state one using STANDARD UI CONVENTION (not a Construct fact, a
  judgment call, clearly flagged as such) -- pressed = background darkened 15%
  ("pushed in"), selected = background lightened 12% ("highlighted"); border/
  text/icon carry over UNCHANGED to both states (ordinary button behavior: only
  the fill visibly shifts). Never overwrites a `pressed_*`/`selected_*` key the
  caller already set explicitly -- only fills in what's missing.
- `theme_chat.py`'s apply functions (`apply_palette_to_page(_all_types)`,
  `apply_palette_project_wide(_all_types)`, `apply_chat_style`) now call
  `derive_states` by default (`derive_states=True`) before applying -- "theme my
  project" requests get full 3-state coverage automatically going forward, per
  the user's ask. `derive_states=False` available for exact, no-magic control
  (tests, or a caller that already fully specifies every state itself).

`palette_test.py` extended: derivation math verified directly (darken/lighten
formula, unchanged-carryover for border/text/icon), explicit values never
overwritten, a derived 3-state palette applied end-to-end to a real button
(all `--ch5-button--default-{pressed,selected}-*` vars present and correct).
Full suite re-run clean except the one known pre-existing unrelated failure.

Re-applied live to `GenTestProject2` with 3-state coverage (NY Giants colors
project-wide, spring theme on `ReflowTest.cuig`) -- verified directly that
every `@media` block for a themed button carries the pressed/selected vars AND
their sector-prefix counterparts. One real mishap along the way, caught and
handled per the user's own call: the project-wide re-apply's glob touched
`Check.cuig` too, overwriting the user's own manually-set red test button with
the project's blue theme -- flagged immediately; user's call was to leave it
(it was a debugging artifact, not real project content). Awaiting the user's
live Construct confirmation that pressed/selected states now render correctly.

**Phase 7 (themes) MAJOR CORRECTION: custom-mode styling was writing an
incomplete rule the whole time -- property grid and canvas disagreed.** User:
*"the property grid and the objects on the canvas are not in sync. are you sure
you are setting both the CSS and XML sections of the data files when theming
components?"* Then, after I first (wrongly) proposed writing to every `@media`
block was the fix and the user tested this themselves in Construct and reported
it contradicted normal cascade: *"i just created a new page called Check and
dropped a button on the primary resolution and changed the fill color to red.
the button remains red through all of the breakpoints without having to
explicitly define red on each one."* Real, confirmed, two-part bug -- found by
diffing this exact real file (`Check.cuig`, Construct's own hand-styled button)
against what this generator was writing:

1. **The property grid does not read the `--ch5-*` CSS var at all.** Traced to
   `style-manager.ts::updateStyleManagerIndividualSectorPropertyView`'s
   `getNearestPropValue` lookup. `Check.cuig` shows the REAL mechanism: a
   literal `{sectorPrefix}{sourceProperty}` pseudo-property
   (`Appearance_background-color:#ff0000`) written SIDE BY SIDE with the real
   `--ch5-button--default-background-color:#ff0000` CSS var in the same rule
   -- one for the web component's actual render, one for the property grid's
   display. `style_property_catalog` had captured `sector_prefix` from day
   one but `set_component_style` never wrote it anywhere -- an unused field,
   not a deliberate omission.
2. **Values ARE duplicated into every configured resolution's own block, not
   just the catch-all.** The user's live test is real (Construct's UI lets you
   set a color once and it applies everywhere) but that's Construct fanning
   the value out at write time, not the file relying on runtime CSS cascade --
   confirmed directly: `Check.cuig`'s `--ch5-button--default-background-color`
   appears in BOTH its catch-all and its 1280x800 device block. Matches the
   same duplication this generator's own size vars already use everywhere
   else; the style-property code had been the one inconsistent corner.

Fixed both in one pass: `layout.py::update_element_declarations` (renamed from
a query-scoped version) now finds and updates the element's rule in EVERY
`@media` block via new `find_all_media_block_spans`, splicing edits from the
end backward (the same technique `reflow_file` already uses for multi-span
replacement) rather than the recursive first-draft attempt that got reverted
mid-session for being needlessly complex. `style.py::set_component_style` now
writes the sector-prefixed pseudo-property alongside the real CSS var for
every property that has one. `custom_style_test.py` extended: asserts the
sector-prefix property is present, and that the CSS var now correctly appears
in the device block too (inverting the old, wrong assertion that it must NOT).
Full suite re-run clean except the one known pre-existing unrelated failure.

Re-applied to every live-themed element in `GenTestProject2` with the corrected
code (NY Giants colors project-wide, spring theme on `ReflowTest.cuig`),
verified directly against the real file: every block containing a themed
button's rule now carries both the CSS var and its sector-prefixed
counterpart. Awaiting the user's live Construct confirmation that the
property grid and canvas now agree.

**Phase 7 (themes), Stage 2 extended: palette coverage for every real component
type that has ANY stylable property, not just ch5-button.** User: *"what other
components dont have palette mapping? that should be addressed now."* Surveyed
every remaining type directly via `style.style_property_catalog` (not guessed)
and split them cleanly in two:

- **17 new curated mappings added** to `palette.py::PALETTE_MAPPING` (18 total
  now): `ch5-button-list`/`ch5-tab-button` (button-family types sharing
  ch5-button's own `--ch5-button--*` var namespace for their default state),
  `ch5-toggle` (label/on-icon only, no fill), `ch5-signal-level-gauge`/
  `ch5-wifi-signal-level-gauge` (mapped to the active/"selected" segment
  color), `ch5-slider` (background/border/text mapped to the filled "connect"
  portion -- track and handle are real but distinct parts, deliberately not
  exposed under these generic keys yet), `ch5-dpad`/`ch5-keypad` (their
  default/unpressed state), `ch5-animation` (its one `color` property, mapped
  to `icon_color`), `ch5-subpage-reference-list` (Widget List, background
  only), `ch5-video-switcher`, `ch5-color-chip`, `ch5-datetime`, `ch5-qrcode`
  (border only), `ch5-text`, `ch5-textinput`, `ch5-image` (border only).
- **11 types confirmed genuinely unstylable via this mechanism**, not a gap:
  `ch5-button-list-individual-button`, `ch5-tab-button-individual-button`,
  `ch5-segmented-gauge`, `ch5-dpad-button`, `ch5-keypad-button`, `ch5-video`,
  `ch5-video-switcher-screen`, `ch5-video-switcher-source`,
  `ch5-media-player`, `ch5-color-picker`, `ch5-template` -- each has a
  genuinely EMPTY `classToVariableMapping` (confirmed, not assumed). Recorded
  as `palette.NO_STYLABLE_PROPERTIES` so warnings can distinguish "nothing
  this mechanism could ever do" from a real coverage gap.

New `palette.py::applicable_subset(tag_name, resolved_palette)` filters a
SHARED palette down to only the keys a given type supports (e.g. `icon_color`
silently drops for `ch5-text`, which has no icon) -- needed because "style all
objects" naturally means applying one palette across many DIFFERENT types that
don't all expose the same properties, not an error case.
`theme_chat.py::apply_palette_to_page_all_types`/`apply_palette_project_wide_all_types`
(new) apply a resolved palette across EVERY mapped type on a page/project, not
one `tag_name` at a time -- this is what "style all objects" actually needs;
the existing single-tag_name functions are unchanged, still useful when a
caller genuinely means one type.

`palette_test.py` extended: every one of the 18 mappings self-checks against
its own real schema, every `NO_STYLABLE_PROPERTIES` type confirmed to actually
have an empty catalog, `applicable_subset` covered directly.
`theme_all_types_test.py` (new) covers the ReflowTest.cuig case end-to-end in a
scratch copy: buttons get their full 4-key subset, the dpad gets only its
2-key subset (no border/icon), the genuinely-unstylable dpad-button produces
no warning noise, file round-trips. Full suite re-run clean except the one
known pre-existing unrelated failure.

Re-applied live: the earlier spring theme on `GenTestProject2`'s
`ReflowTest.cuig` now correctly covers its dpad too (previously left
unstyled and flagged as a real gap -- now closed), applied via
`apply_palette_to_page_all_types` with zero warnings. Verified on disk,
round-trips. Awaiting the user's live Construct confirmation.

**Phase 7 (themes), Stage 3 source #1: single-page scope + explicit unmapped-type
warnings.** User: *"please style all objects on the ReflowTest page with a spring
theme."* Two real gaps this surfaced: `apply_palette_project_wide` only ever
operated whole-project (no way to scope to one page), and it silently said
nothing about component types the request implied ("all objects") that
`palette.py`'s `PALETTE_MAPPING` doesn't cover yet (Stage 2 scope is `ch5-button`
only).

`theme_chat.py::apply_palette_to_page` (new): the real per-page worker,
extracted from `apply_palette_project_wide` (which is now just that function
called over every page/widget file). Also now reports every OTHER real
component type found on the page that has no palette mapping yet (e.g. a dpad,
a slider) as an explicit warning -- "left unstyled, see
palette.py::supported_tags()" -- rather than quietly only doing the buttons and
saying nothing about the rest. `theme_chat_test.py`'s existing whole-project run
against GenTestProject2 now surfaces these warnings for real (button-list,
tab-button, toggle, gauges, dpad, keypad, media-player, video-switcher, text,
textinput, datetime, qrcode, color-chip/picker, image, template, div -- the
full real inventory of what this project's test pages contain beyond buttons).
Full suite re-run clean except the one known pre-existing unrelated failure.

Applied live: resolved "spring theme" myself (pale green background `#98fb98`,
dark green text `#1b4d1b` for contrast, blossom-pink border `#ffb6c1`, khaki
icon accent `#f0e68c`) and applied it to `GenTestProject2`'s `ReflowTest.cuig`
only (not project-wide, per the request) -- all real `ch5-button` instances on
that page got it; the page's `ch5-dpad`/`ch5-dpad-button` were correctly
reported as unmapped rather than silently skipped. Verified on disk,
round-trips. Awaiting the user's live Construct confirmation.

**Phase 7 (themes), Stage 3 source #1 corrected: no theme-name lookup table --
resolution is the driving chat AI's job, not this generator's.** User, after I
proposed adding a `NAMED_THEMES` preset dict (Halloween, Christmas, etc.):
*"most of the time, users arent goign to know they exact colors they want. they
will describe things in broad terms. as long at the AI chat engine can resolve
the description into actionable colors it will work. I.E. I want to style my
user interface using colors from the NY Giants football team."* Correct call --
no lookup table this generator could maintain covers every sports team,
holiday, brand, or mood a user might name; that's a knowledge/reasoning task
belonging to whatever chat AI is driving the skill (it already knows the
Giants are blue and red), not hardcoded data here.

Split `theme_chat.py` into two concerns instead of building the lookup table:
`apply_palette_project_wide(resolved_palette, project_dir, sdk)` (new) takes an
ALREADY-RESOLVED palette dict -- however it was produced -- and applies it
across every matching component instance in the project; `parse_style_description`/
`apply_chat_style` (unchanged behavior) remain the narrow, literal path for
descriptions that already name real CSS colors directly, now just one caller of
the new function rather than the only path. `theme_chat_test.py` extended to
cover `apply_palette_project_wide` directly with a real resolved example (NY
Giants colors, `#0b2265`/`#a71930`) against all 24 real button instances. Full
suite re-run clean except the one known pre-existing unrelated failure. Applied
live to `GenTestProject2`: NY Giants colors themed every real button across
every button-bearing page (including `ComplexContracts.cuig`, not covered by
the earlier "dark green" demo's page count), verified on disk, every file
round-trips. Awaiting the user's live Construct confirmation.

**Phase 7 (themes), Stage 3, source #1: chat-described theming.** User: "yes,
start with chat-described values." Two new modules:

- `generator/color_words.py`: the real, standardized CSS Color Module Level 4 /
  SVG 1.1 extended color keyword table (147 names, not invented) +
  `adjust_lightness` (plain HSL math). `resolve_color_phrase` prefers an EXACT
  named color over a computed one -- "dark blue" resolves to `darkblue`'s real
  spec hex (`#00008b`), not `blue` algorithmically darkened, since CSS itself
  defines a distinct hex for many "light X"/"dark X" combinations; only a
  combination with no real CSS name (e.g. "dark yellow") falls back to an HSL
  lightness shift.
- `generator/theme_chat.py`: `parse_style_description` splits a description on
  "and"/"with"/commas into segments, resolves each segment's color via
  `color_words.py`, and matches a property keyword (background/text/border/icon)
  within the same segment -- a segment naming a color with no property keyword
  defaults to `background_color` (the natural reading of "make the buttons X").
  Intentionally simple and inspectable, not an LLM/black box. `apply_chat_style`
  applies the parsed palette to EVERY `ch5-button` instance across EVERY page/
  widget in the project -- "theme my project" in the whole-project sense the
  original request was about, not one component at a time. Scope: `ch5-button`
  only, matching `palette.py`'s own `PALETTE_MAPPING` (Stage 2) -- extending to
  more types is the same per-type-verified work already used throughout this
  project.

`generator/_test_output/color_words_test.py` and `theme_chat_test.py` cover:
exact CSS names, the real-name-wins-over-computed rule, the HSL fallback for
combinations CSS has no name for, unrecognized words resolving to `None` rather
than a guess, and (whole-project) applying "dark blue buttons with white text and
an orange border" against a scratch copy of GenTestProject2 -- all 24 real
`ch5-button` instances across all 3 pages that have any got the full palette,
non-button elements completely unaffected, every touched file round-trips. Full
suite re-run clean except the one known pre-existing unrelated failure. Applied
live: "dark green buttons with white text and a gold border" themed all 24 real
buttons across `GenTestProject2`'s 3 button-bearing pages uniformly (superseding
the individually hand-set demo colors from the Stage 1/2 live checks, which is
the intended whole-project effect). Verified on disk, every file round-trips.
Awaiting the user's live Construct confirmation. Sources #2 (reference-project
extraction) and #3 (deferred design-doc/image) are next.

**Page/widget background rules (new capability, entered from a "before we get to
Stage 3" detour, not itself a theming/Stage 3 piece).** User's standing rule,
2026-09-11: *"Construct projects need to be 'page based', rules need to be
applied. First rule is that the Override Theme Color in the project properties
should always be set to black... Second, pages and widgets both support local
controls for background colors so those should be used when a color needs to be
applied at the page or widget level. When a custom image needs to be used as a
page background, the rule is you use an image component at the lowest z-order at
0,0 at the page size (this needs to be supported in your reflow logic)... If the
user specifies that they need to have the video component supported in the
project, then the image component should not be used and the background
component used instead."*

Three pieces:

1. **`OverrideThemeColor`/`ThemePageColor` default to `"True"`/`"#000000"`**
   (`project.py::build_project_attributes`), still explicitly overridable.
   Confirmed from `ProjectItemThemePageColor.razor.cs`: `OverrideThemeColor=False`
   makes Construct continuously auto-sync `ThemePageColor` to whatever the
   CURRENTLY SELECTED theme's own default page color is, silently drifting if the
   theme ever changes -- only `True` + an explicit value actually pins the
   page-flip color to black regardless of theme. Fixed live on GenTestProject2 too
   (was `False`/`"#ffffff"`).
2. **Solid page/widget background color needs no new code** -- `page.py`'s
   existing `DisplayBackgroundColor`/`BackgroundColor` `{PageAttributes}`
   mechanism (Phase 3) is already the right tool; just documented as such.
3. **`generator/background.py` (new): background IMAGE placement.** Two new
   `component.py::PROFILES` entries, both transcribed from real instances (not
   guessed): `ch5-background` from `C:\Solutions\ClaudeSamples\Components\
   Component - Images - Background.cuig` (that reference project's own real CSS:
   `width:100%;height:100%;z-index:-99;overflow:hidden;left:0;top:0` in the
   catch-all block); `ch5-image` (no instance in that project) from
   `C:\Solutions\ClaudeSamples\ClaudeCustomModeProject\Page1.cuig` instead --
   `component_flat_types_test.py`/`component_css_shape_test.py` both got a
   documented `NO_REFERENCE`-style carve-out for `ch5-image`, verified instead by
   this feature's own `background_test.py` against that file. `choose_background_tag`
   picks `ch5-background` when the project needs video (the user's own stated
   reason: an image component conflicts with video), `ch5-image` otherwise.

   `add_page_background` places it at (0,0), the project's landscape/portrait
   primary resolution's exact size, `z-index: -99` (matching the real file
   verbatim -- it parses fine, unlike the deliberately NOT-reproduced percentage
   width/height, see below), inserts it into an EXISTING page/widget via direct
   section-text splicing (append-before-trailing-whitespace, the same pattern
   `reflow.py`'s own CSS-block insertion already uses -- a first version got this
   backwards for the `{Html}` section specifically, silently eating the newline
   before `{Css}` and breaking every later section read; caught by this feature's
   own test, not a live mishap), then propagates into every OTHER
   already-configured resolution via `reflow.reflow_file` (same mechanism
   `add_resolutions_to_project` already uses, just resolution-vs-new-element
   instead of new-resolution-vs-existing-elements).

   **`reflow.py` extended** with `BACKGROUND_MARKER_ATTR`
   (`ccid_pageBackground="true"`, a marker this project's own generator invents
   and reads back, not a real CH5 attribute) and background-forcing inside
   `reflow_file`: any element carrying it is excluded from the normal row/column
   fit (it isn't a member of any "row", it covers the whole canvas) and forced
   directly to `(0,0)` + the target resolution's exact size on every NEWLY-ADDED
   resolution too -- proven end-to-end by `background_test.py`, which adds a
   background to an existing page, THEN adds a brand-new resolution afterward and
   confirms the background gets force-pinned into it as well, not just at initial
   placement. Also excluded from `check_overlaps`'s new-vs-pinned check (a
   full-canvas element overlapping everything is by design, not a real conflict).

   Deliberately NOT matching the real file's exact CSS shape: PIXEL-exact
   width/height/left/top instead of percentages/bare-zero, and no `overflow:
   hidden` -- found while building this that `layout.py::_px()` can't parse a
   percentage value, and `_fill_missing_size` (already-proven, unmodified) would
   silently DROP the element from every future resolution add, treating an
   unparseable width as "no size at all"; `overflow: hidden` has no home in
   `parse_position_rules`'/`build_reflow_block`'s declaration model (no generic
   non-var slot). Functionally identical (full canvas cover, lowest z-order);
   documented divergence, not an oversight.

`background_test.py` covers `choose_background_tag`, the `ch5-image` PROFILES
entry matching its own real reference instance exactly, initial placement +
propagation into all of GenTestProject2's pre-existing resolutions on a scratch
copy (pre-existing elements untouched, round-trips), and a resolution added
afterward still getting the background forced in. Full suite re-run clean except
the one known pre-existing unrelated failure. Applied live: `GenTestProject2`'s
`ThemePageColor`/`OverrideThemeColor` fixed, and a `ch5-image` background placed on
`MainPage.cuig` (assetid left at "0" -- no real image assigned yet, this phase was
about correct placement/reflow, not asset selection). Awaiting the user's live
Construct confirmation.

**Phase 7 (themes), Stage 2: a palette layer (`generator/palette.py`, new) sitting
on top of Stage 1's raw per-property catalog.** User: *"go ahead and start Stage
2."* A palette is a small set of logical keys (`background_color`, `border_color`,
`border_width`, `border_style`, `text_color`, `icon_color`) mapped per component
type onto the real Stage-1 catalog entries -- e.g. `apply_palette(css, "ibtncheck",
sdk, "ch5-button", {"background_color": "#204060", "text_color": "#ffffff", ...})`
resolves each key through the curated mapping and calls `style.set_component_style`
once. This is curation of ALREADY-DISCOVERED real schema data (naming it), not the
kind of guessing the user rejected for Stage 1 -- flagged explicitly in the module
docstring to keep that distinction clear for later readers.

Deliberately NOT built as a generic auto-derived mapping across every type: checked
ch5-button/ch5-toggle/ch5-slider/ch5-textinput side by side and their real schemas
are not uniform enough to name generically -- `ch5-toggle` has no
`background-color` concept at all (an on/off switch styled by label/icon color
only), `ch5-slider` has THREE separate background-color-bearing selectors (track/
filled-portion/handle) with no single "the" background without knowing what each
part visually is. `PALETTE_MAPPING` covers `ch5-button` only so far (default state,
not pressed/selected), built the same incremental, per-type-verified way as
`component.py::PROFILES`; `apply_palette` raises `KeyError` up front for an
unmapped type or an unmapped key, never silently drops what the caller asked for.

`generator/_test_output/palette_test.py` (new) covers: every `_BUTTON_PALETTE`
entry resolving against the real schema (a self-check catching drift),
`supported_tags()`, unmapped-tag/unmapped-key both raising before any write, and
the full flow (5 palette keys in one call) against a real button in a scratch copy
of GenTestProject2 with position/size preserved and the `.cuig` round-tripping.
`custom_shape_test.py`'s own target button needed swapping from `ibtnimage` to
`ibtncheck` -- the same kind of live-project-drift fixup as before, since
`ibtnimage`'s shape was flipped to "custom" for real in the prior session entry.
Full suite re-run clean except the one known pre-existing unrelated failure.
Applied live to GenTestProject2's `ButtonVariants.cuig` (`ibtncheck`): navy
background, light-blue 2px border, white label, yellow icon -- all 5 keys from one
`apply_palette` call. Verified on disk, round-trips. Awaiting the user's live
Construct confirmation. Stage 3 (the three style-value sources) is next.

**Phase 7 (themes), Stage 1 extended: button `shape="custom"` + per-corner
border-radius, at the user's direction before Stage 2 started.** User: *"buttons
support fixed Shapes + a custom mode when the 4 radius need to be set custom... make
sure you support the ability to set the button Shape to Custom so you can set the
radius to custom values."* Confirmed: `shape`'s real schema enum is
rounded-rectangle/rectangle/tab/circle/oval -- "custom" isn't in it, the same
undocumented-but-real pattern already established for `size="custom"`
(`component.py::build_component_attributes`). The 4 corner border-radius properties
were ALREADY covered by Stage 1's existing catalog (`.ch5-button--rounded-rectangle`
class, all `targetProperty`-backed) -- the missing piece was purely that
`set_component_style` only ever touched CSS, never an HTML attribute, and flipping
`shape` to `"custom"` is what the user says actually makes the per-corner values take
effect instead of snapping back to the shape preset's own fixed radius.

Added `style.py::set_html_attribute(html_text, element_id, attr_name, value)` --
replaces or inserts one attribute on the one opening tag matching `id="element_id"`.
Built via strict attribute-grammar regex first; replaced after it silently failed to
match on a REAL live tag (`ButtonVariants.cuig`'s `ibtnimage`) carrying an unescaped
embedded quote in `devicesVisited="["TSW-1070, TSW-1070"]"` (vs. the reference
project's properly `&quot;`-escaped form) -- now boundary-finding instead (nearest
`<` before the `id="..."` match, nearest `>` after), the same pragmatic
no-literal-bracket-in-values assumption `layout.py`'s own CSS rule parsing already
makes, not a general HTML parser.

Incidentally confirmed while investigating: this live button's tag also carries a
full `ccid_sync_{state}_{sector}_{property}="syncEnabled"/"syncDisabled"` attribute
set (Construct's own per-property theme-sync bookkeeping, materialized once a
button's property grid has been touched in the real app) -- border-color and label
color were still `"syncEnabled"` on the FIRST button styled live in this project
(`ibtnicon`) and their custom values still rendered correctly (per the user's
confirmed screenshot), so `set_component_style` does not need to manage these sync
attributes at all; they don't gate whether a CSS var override visually applies.

`generator/_test_output/custom_shape_test.py` (new) covers: `shape`'s real enum
excluding "custom", all 4 corners resolving to real CSS vars via the existing
catalog, `set_html_attribute` replacing/inserting/raising correctly with a sibling
element proven untouched, the full flow (flip shape + write 4 asymmetric corner
values) against a real button in a scratch copy of GenTestProject2 with
pre-existing position/size preserved, and the `.cuig` round-tripping. Full suite
re-run clean except the one known pre-existing unrelated failure. Applied live to
GenTestProject2's `ButtonVariants.cuig` (`ibtnimage`): `shape="custom"`, corners
25px/0/0/25px (diagonal rounded look). Verified on disk, round-trips. Awaiting the
user's live Construct confirmation.

**Phase 7 (themes), Stage 1: custom-mode component styling (`generator/style.py`,
new), entered from the "theme my projects" / custom-mode-CSS angle rather than a
theme-file angle.** User's own framing: *"i want to work on custom mode CSS so you
can theme my projects."* Brainstormed as bounded (superpowers:brainstorming): the
mechanism generalizes component.py's own `size_css_vars`, not a new subsystem --
`component-context.json`'s `classToVariableMapping` schema, already proven correct
for width/height, turns out to carry the FULL style property set too (background/
border color+width+style, label color/font-size/font-weight/text-decoration/
letter-spacing, icon color/font-size/margins, per component type), confirmed
universal across every type checked (`propertyPattern.customVsThemeHandler ==
"customThemeSize-pattern"` on ch5-button/toggle/slider/dpad/textinput/tab-button/
button-list/keypad/animation), not button-specific as an earlier reading of this
generator's own `component.py::PROFILES` (`vstheme="theme"` default for most
types) suggested.

I initially asked for a hand-styled reference project to ground this against, the
way sizing/fonts were grounded -- the user correctly pushed back: *"why do you
need a sample since every component drops on the canvas in custom mode and
Construct exposes the CSS properties of every component, dont you just need to
create a map... i shouldnt have to model anything."* Right call -- the schema
itself is the complete, authoritative map; no sample was needed to discover it.

**Stage 1 scope** (agreed with the user before building): only properties with a
real `targetProperty` (a `--ch5-{tag}--...` CSS custom property, same mechanism as
size) are covered -- this is the actual theming set. A smaller subset with no
`targetProperty` (e.g. `ch5-text`'s border-radius corners, letter-spacing) needs a
different, nested-selector placement (see `layout.py`'s `theme_selectors`/
`customThemeRequiredSelectors` precedent, already used for font-family) --
deliberately deferred as a named follow-up, not guessed at.

`style_property_catalog(sdk, tag_name)` reads the real per-type catalog straight
off the schema (no per-tag modeling); `set_component_style(css_text, element_id,
sdk, tag_name, style_values)` resolves each `(class_name, source_property, value)`
against it and writes the `--ch5-*` vars into the element's own catch-all `#id{}`
rule via new `layout.py::update_element_declarations` (merges in place --
existing declarations, including position/size and any pre-existing style vars,
keep their position; a re-applied property updates rather than duplicating).
Style values are not resolution-dependent, so unlike size they're written once,
in the catch-all block only -- normal CSS cascade carries them into every
per-resolution device block.

`generator/_test_output/custom_style_test.py` (new) covers the catalog against
the real ch5-button schema, width/height correctly excluded, a nonexistent
property raising `KeyError`, applying real values to a real button in a scratch
copy of GenTestProject2 (pre-existing position/size/size-vars preserved, an
untouched sibling element completely unaffected, re-applying updates in place
with no duplicate declaration, the per-resolution device block carries no style
vars, and the `.cuig` still round-trips section-for-section), and confirms the
Stage-1 boundary itself (`ch5-text`'s no-`targetProperty` letter-spacing is
correctly excluded, not silently mishandled). Full suite re-run clean except the
one known pre-existing unrelated failure (`phase5_smoke_test.py`'s 74-vs-75
catalog count) -- `custom_resolution_test.py`'s own precondition also needed a
small update (it now must check only for ITS OWN resolution id being absent,
not that the live project has zero custom resolutions, since the prior entry
in this log added one there for real).

Applied live to `C:\Solutions\ClaudeGenTest\GenTestProject2`'s `ButtonVariants.cuig`
(`ibtnicon`, already `customvstheme="custom"`): dark navy background (#1a2b3c),
orange 3px border (#ffcc00), white label text. Verified on disk: the new vars are
present alongside the pre-existing size vars, position/size unchanged, file
round-trips byte-identical. Awaiting the user's live Construct confirmation.
Stage 2 (a palette layer sitting on top of these raw properties) and Stage 3 (the
three requested style-value sources -- chat-described values, extraction from a
reference project, a design-doc/image source) are next.

**Custom language file support (Phase 10) removed from scope, at the user's
direction: "we can remove the custom language support from this skill for now as
well .. i will add that later."** Unlike Hard Buttons, this is a deferral, not a
permanent descope -- the user intends to add it back later. No code had been
written against it (only the base `RuntimeLanguageJoin`/`DefaultLanguageFile`/
`ProjectLanguageFiles` project-attribute plumbing in `project.py` exists, which is
part of core project-creation shape/round-tripping, not the language-file-import
feature itself, so nothing there needed removal). `docs/ConstructUISkill.md`'s
§8 skill-function list no longer lists it (removed at the user's own explicit
request, matching the exact list they pasted back), and
`docs/architecture/01-index.md`'s Language files row now says "Out of scope for
now" / "deferred" rather than "Mapped"/"Not found". Current/forward-looking phase
counts from here on: themes (7) and the skill layer (languages dropped entirely
from the count, to be re-added when the user picks it back up).

**Phase 5 (resolutions): genuinely custom (non-catalog) resolutions can now be added
to a project and actually reflow -- the gap both `devices.py` and `project.py` had
self-documented ("this module still has no 'add a genuinely custom resolution'
builder") is closed.** User's own framing: *"we have tested adding standard
resolutions but we have not tested adding a custom resolution and allowing the
reflow to trigger."* Added `devices.py::to_custom_resolution(width, height,
orientation, name)`, shaped against a real hand-authored entry (`C:\Solutions\
Polkampally Project\Polkampally Project.cuip`'s own `{DeviceResolutionSource}`) --
`id` format `Custom-<L|P>-<fresh uuid4>-<width>-<height>` (confirmed the embedded
GUID is NOT the project's own `Id`), `resolutionId` `<L|P>-<width>-<height>`,
`resolutionType: "custom"`, `IsCustom: true`. Fixed `project.py::
add_resolutions_to_project`, which previously wrote `{DeviceResolutionSource}` back
completely UNCHANGED regardless of what was added -- it now appends any new
resolution carrying `IsCustom: true` there (and only those; catalog picks still
never go there, preserving the 2026-09-10 phantom-duplicate fix), while every
pre-existing `{DeviceResolutionSource}` entry survives untouched.

Testing this against the real component-showcase pages (never previously reflowed)
surfaced two real, pre-existing crash bugs in `reflow.py`, both the same root
pattern -- catch-all-sourced elements reaching size-dependent math without going
through `_fill_missing_size`, so a genuinely no-size element (content-sized, or a
`canResize:false` type per `component.py::can_resize`, e.g. segmented/signal/wifi
gauges) hit `TypeError: unsupported operand type(s) for +: 'int' and 'NoneType'` in
`detect_rows`: (1) the "no source block yet, fall back to the catch-all" branch
assigned `catchall_elements` straight through; (2) the "inherited" catch-all-only
elements merged into an existing device block did the same. Both now route through
`_fill_missing_size` like every other path in the file, so a truly sizeless element
is dropped with a warning instead of crashing -- not new behavior, just making an
already-established pattern apply consistently. Also fixed
`_component_size_css_vars`: it assumed every `classToVariableMapping` entry was a
persisted width/height var and crashed (`KeyError: 'targetProperty'`) on
`ch5-text`/`ch5-datetime`'s real schema, which also lists style-only entries
(font-weight, border-radius, ...) with `persist: false` and no `targetProperty` --
now skips anything whose `sourceProperty` isn't width/height or that has no
`targetProperty`.

`generator/_test_output/custom_resolution_test.py` (new) covers: `to_custom_resolution`
shape vs. the real file, fresh GUID per call, portrait encoding, the
`{DeviceResolutionSource}`-write fix itself, preservation of pre-existing custom
entries, `.cuip` round-trip integrity, and -- the actual point -- confirming reflow
produced a populated `@media` block for the new resolution across every page/widget
in a scratch copy of GenTestProject2. Full suite re-run clean except the one known
pre-existing unrelated failure (`phase5_smoke_test.py`'s 74-vs-75 catalog count).
Then applied live to the real `C:\Solutions\ClaudeGenTest\GenTestProject2`: added a
1000x700 landscape "Custom Panel" resolution, verified on disk (not from the
function's return value) that `DeviceResolutionIds` includes it, its own definition
is in `{DeviceResolutionSource}`, `ContractIsStale` is set, the `.cuip` still
round-trips byte-identical, and every page/widget got a real populated `@media`
block for `(orientation: landscape) and (max-width: 1001px) and (max-height:
701px), (orientation: landscape) and (max-width: 999px)`. Awaiting the user's live
Construct confirmation.

**Hard buttons (`.cuib`) removed from scope, at the user's direction: "not needed in
the skill."** Previously Phase 11, listed "Mapped" in the architecture index and
recurring in every "remaining phases" list since. Descoped rather than deprioritized
-- `docs/architecture/01-index.md`'s row now says so explicitly instead of implying
it is still pending, and `docs/ConstructUISkill.md`'s `.cuib` line is marked
out of scope. No code had been written against it, so nothing to remove there.
Historical README log entries that mention it (many -- it was on the standard
"remaining phases" list for a while) are left as-is: they are an accurate record of
the plan AT THE TIME they were written, not something to retroactively rewrite.
Current/forward-looking phase counts from here on: themes (7), languages (10), and
the skill layer.

**Phase 8 (fonts): Fontsource added as a second search source -- restricted to the
120 fonts genuinely NOT already reachable via Google Fonts.** Measuring Fontsource's
real catalog (2,100 fonts) found 1,980 marked `type: "google"` -- literal duplicates
of the same fonts `google_fonts.py` already searches, re-served through a different
CDN. The user's own call once that was measured: *"if they are duplicates of Google
Fonts no reason to add this."* `fontsource.py::search_fontsource` filters to exactly
the 120 `type: "other"` entries (real fonts, real open licenses -- OFL-1.1,
Apache-2.0, CC0-1.0 all seen), so a query never returns two different "sources" for
the same actual font, and searching a common name like "Roboto"/"Open Sans" correctly
finds nothing here (that is `google_fonts.py`'s job).

Same shape and independence rule as `google_fonts.py` (neither of the three modules
imports either of the other two): `search_fontsource(query)` against the real,
keyless `api.fontsource.org/v1/fonts` catalog; `download_fontsource_file(family_name,
weight=..., style=..., subset=...)` against jsDelivr's public CDN
(`cdn.jsdelivr.net/fontsource/fonts/...`), validating the requested weight/style/
subset against what the font actually publishes BEFORE requesting anything, rather
than discovering a bad combination via a failed download. Verified live: "Adwaita
Sans" downloads as 513,028 real bytes with valid TrueType magic; downloading
"Roboto" through this module is refused (Google-sourced); an end-to-end test installs
a real Fontsource-unique font through the exact same `fonts.py` pipeline Google Fonts
uses and confirms it validates as selectable.

Full 50-file suite green except the one pre-existing, unrelated failure noted in the
entry below (the stale 74-vs-75 resolution-catalog count).

**CONFIRMED IN CONSTRUCT 2026-09-11: "font install and swap is working."** Ran the
whole pipeline live, twice, end to end: search (name-based, no theme/mood field
exists in either API so a "Halloween font" query had to try naming patterns --
"creep" -> found "Creepster", the well-known horror-display Google Font) -> download
-> `import_font_file` into the real, global Webfonts library -> `set_project_font`
across all 11 files in `GenTestProject2` -> user closes/reopens Construct -> font
shows up as selectable, exactly per the spec's own restart requirement. First run
used "Share Tech Mono" (a computer/terminal-style monospace, found the same way);
both installs verified on disk before being reported (real byte count, `.ttf` magic,
`DefaultFontFamily` updated, no leftover mention of the prior font, every file still
round-tripping) -- and both confirmed working by the user in the live app. The
"go find me a font" feature, across both sources, is done.

**Phase 8 (fonts): "go find me a font" -- search + download from Google Fonts, and
install any font file into the library -- BUILT, verified against the real Google
Fonts service, AWAITING A LIVE CONSTRUCT CHECK.** Follows the same pattern as the
earlier "use a library font" slice: brainstormed as bounded, one clarifying round on
scope (local file vs. URL vs. real web search -- the user corrected this: "when
someone says go find me a font the expectation is that you go out to teh web and
download the file"), a second round on which API (an undocumented but keyless
endpoint vs. the official Developer API requiring a Google API key -- keyless chosen).

**New `generator/google_fonts.py`**, the only module in the generator that makes a
network call, deliberately independent of `fonts.py` (neither imports the other --
confirmed by a test that composes them from outside rather than adding a
cross-dependency): `search_google_fonts(query)` matches against the real, live
catalog (`fonts.google.com/metadata/fonts`, 1,946 real family names, exact match
ranked first), `download_google_font_file(family_name)` pulls the actual `.ttf` bytes
from Google's own CDN via the documented `css2` endpoint. Both verified live, not
mocked -- "Roboto Slab" downloads as 101,564 real bytes with valid TrueType magic
(`\x00\x01\x00\x00`); a nonexistent family raises `ValueError` naming it, not a
silent empty/garbage result.

**New in `fonts.py`:** `validate_font_family_name`/`sanitize_font_family_name` (the
spec's exact regex + 2-31 length bound, source-cited in
`docs/ConstructUISkill_FontImport.md`) and `import_font_file(data, family_name,
target_dir=...)`, which writes `<family_name><ext>` -- the filename, not any name
embedded in the font file or carried in from a download, since that filename IS what
Construct exposes (the spec's own §2 finding). Defaults to `global_webfonts_path()`;
`project_webfonts_path()` also usable. Validates before writing, so a rejected import
never leaves a partial file.

Every test runs against real infrastructure -- the live Google Fonts endpoints, and
`fonts.webfont_names()`/`available_fonts()` (built for the earlier slice) -- writing
only to scratch directories, explicitly asserting the real, global webfont library is
never touched by a test run.

Full 48-file suite green (one unrelated, pre-existing failure noted below, not
touched: `phase5_smoke_test.py`'s hardcoded resolution-catalog count is now stale --
Construct's own catalog on this machine gained a 75th device between sessions,
unconnected to anything in this phase).

**Awaiting the live check:** actually use the skill/generator to search for and
install a real font, then confirm -- after closing and reopening Construct (per the
user's own live-tested finding, recorded in the spec) -- that it appears as a
selectable Font Family.

**Also noticed, not investigated:** `docs/ConstructUISkill_FontImport.md` reverted
to its original, pre-correction content sometime during this build (the sourced
findings from the last three turns -- the Webfonts path formula, the regex, the
restart-requirement correction -- are no longer in the working file). Those findings
are still fully preserved in git history (commits `48ea867`, `02e5a5a`, `8b08719`)
and are what this build actually implements against; only the on-disk copy of the
doc changed. Not acted on without knowing why -- flagging for the user rather than
guessing whether it was intentional.

**Phase 8 (fonts): global swap now works for fonts already in Construct's own font
library, not only the 5 hardcoded SDK names -- BUILT, applied to the live project,
CONFIRMED IN CONSTRUCT 2026-09-11: every component is using Stylish Comic.** The
user's exact request: "please replace the font
everywhere with Stylish Comic that is in my library" -- and they corrected the framing
up front: fonts are APPLICATION-specific in Construct, not machine-specific, with a
Webfonts folder that is part of the install path on both platforms.

**Traced from source, then confirmed against this machine's real, running install --
not assumed:** `EnvironmentUtility.cs::CombineStoragePaths` resolves `solutionsPath` as
`<Documents>/Crestron/Crestron Construct/Solutions` (SAME formula on Windows and
macOS -- both call `Environment.GetFolderPath(SpecialFolder.MyDocuments)`, only what
that path itself resolves to differs per OS), and `ThemeAndFontUpdateHandler.cs`'s
`webFontDirectory` is that folder's own SIBLING, named `"Webfonts"`. On Windows,
`MyDocuments` is NOT simply `~/Documents` -- it is whatever the registry's
`...\Explorer\User Shell Folders\Personal` value says, which OneDrive's "back up your
Documents folder" rewrites. Confirmed exactly against this machine: the registry
value, Construct's own startup log ("EnvironmentUtility solutionsPath:
C:/Users/aseferian/OneDrive - Crestron Electronics/Documents/Crestron/Crestron
Construct/Solutions"), and the real Webfonts folder next to it -- 23 real font files,
including Stylish Comic.ttf -- all agree.

**New in `fonts.py`:** `documents_path()` (per-OS, registry-aware on Windows),
`global_webfonts_path()`, `project_webfonts_path()` (a project's own `webfonts/`
sibling, for portability -- distinct from the global one), `webfont_names()` (filename
without extension, filtered to Construct's 5 real webfont extensions --
`.woff2/.woff/.ttf/.eot/.svg`, from `CommonThemeAndFontHelper.cs`), and
`available_fonts()` extended to fold in whichever directories are passed.
`set_project_font` now checks both the global library and the project's own folder by
default, so "a font that is in my library" just works without the caller naming any
paths.

**What is still genuinely deferred, and why it is a smaller/different claim than what
just shipped:** importing a brand-new font FILE the library does not have yet --
copying it in and everything the build/packaging step needs to bundle it. This session
has still never created a project that does that, so there is nothing real to verify a
fresh import's shape against. Using a font ALREADY on disk in a location fully traced
from source and confirmed against the real install is a materially smaller, lower-risk
claim, which is why it was safe to build now.

Applied to the live `GenTestProject2` (verified: no file still mentions the old font,
round-trip intact). Full 45-file suite green (2 new files: the corrected/hardened
swap test, and the new library-discovery test).

Global font-swap, including library fonts, is done and live-verified.

**Next:** genuinely new webfont import (deferred, still needs a real sample), then
languages (10), hard buttons (11), and the skill layer.

`generator/fonts.py::set_project_font(cuip_path, new_font)` rewrites, in one call: the
`.cuip`'s `DefaultFontFamily`, and every `ccid_ActiveFont` attribute + Construct-generated
`font-family` CSS declaration in every `.cuig`/`.cuiw` beside it. Grounded in
`FontUpgradeHelper.cs` (Construct's own font-writing code) and its four literal CSS
selector shapes in `FontSupportConstants` (`UiEditor.Server\Constants.cs:262`), all four
confirmed byte-for-byte against the reference project.

**Verification found two real bugs before the code ever reached a live file, because the
test ran against a COPY of the actual GenTestProject2 harness project rather than a
synthetic fixture** -- the first time in this project a test has used the real live
project as its own oracle rather than the separate `C:\Solutions\ClaudeSamples\Components` sample:

1. **Attribute-name casing.** Construct's own Html view lowercases attribute names on
   save (`ccid_activefont`); the mirrored PageAttributes TOML preserves the authored
   casing (`ccid_ActiveFont`) -- confirmed with zero exceptions across 12 reference
   files. The first version of the regex was case-sensitive and silently missed every
   Html-view mention on any file that had been through a real Construct save
   (`ComplexContracts.cuig`, built from transplanted real components). Now
   case-insensitive on the key, preserving whichever casing is actually present.
2. **`font-family` quote style.** `layout.py` always writes double quotes with a space;
   `ReflowTest.cuig` -- a real, long-lived file, not something this session wrote fresh
   -- carries single quotes with no space in 21 places. Both are valid CSS and Construct
   evidently accepts either. Now matches `['"]`, preserving whichever quote character was
   actually used rather than normalizing it.

**A related finding, deliberately NOT acted on in this phase:** the generator's own Html
output writes attribute names in their original camelCase (`ccid_ActiveFont`), never
lowercased the way a real Construct save does. This appears functionally harmless (HTML
attribute names are case-insensitive to parsers) and is unconfirmed either way -- flagged
here rather than fixed, since rewriting HTML-casing behavior across every component
builder is a cross-cutting change well outside this phase's scope, and would touch
Phase 4's already user-confirmed-live button code.

Applied to the live `GenTestProject2` (Roboto -> Montserrat; backup taken in the session
scratchpad first). Verified independently before this was written: no file mentions
Roboto anymore, every file still round-trips section-for-section, `.cuip` reads
`DefaultFontFamily = "Montserrat"`. Full 44-file suite green.

**Awaiting the live check:** open `GenTestProject2` in Construct and confirm the project
now shows Montserrat (or its own system fallback, if Montserrat is not installed) rather
than Roboto.

**CONFIRMED IN CONSTRUCT 2026-09-11: all six component pages look good.** Every
component type the generator can build -- 21 types, 38 nested children -- renders
correctly at the size its selection adorner shows. Component generation (flat and
container) is complete and live-verified.

Getting here took four rounds of the user finding sizing bugs by eye, and the reason is
recorded in **Approach** above rather than buried here: the attribute diff against the
reference ran on every test run, the CSS diff did not exist, and prose directives in
this README did not prevent me from shipping without it. `component_css_shape_test.py`
closes that gap and found four more mismatches the moment it was written. The rule is
now mechanical: an automated comparison must cover the dimension that changed before
generated output goes to the user.

**What the sizing model ended up being**, all from published SDK data rather than
inference:

| source | what it decides |
|---|---|
| `defaults.style` | the drop size, and which dimensions a type states -- including the literal `auto` |
| `canResize` | types that cannot be sized at all (animation, segmented/signal gauges) |
| `supportedSizeFormat` | the aspect-locked class (`widthOnly`, `containerWidthOnly`, `handleWidthOnly`, ...) |
| `classToVariableMapping` "idSelector" | the CSS custom properties a component RENDERS from, with its swaptarget/ignore conditions |

Plus two facts no data expresses: `size="custom"` (a Construct mode absent from the
schema's own enum) is what makes an explicit size take effect, and a dpad is locked 1:1
so a non-square request is squared.

**Known limitation, not a bug:** for `height: auto` components the rendered height is
unknowable to the generator, so the showcase packer reserves a 120px guess. Nothing
collided in practice here, but a taller-than-guessed component would overlap what is
below it on a generated page.

Full 43-file suite green.

**`showtickvalues` resolved -- after I first misread the instruction.** "I don't need
you to generate a slider with ticks" means the attribute IS present and turned off, not
that the attribute is dropped. My first pass removed it entirely. The schema default is
`"false"`, so simply emitting it gives exactly what was asked: attribute there, ticks
off. A generated slider is back to 22 attributes with `showtickvalues="false"`.

The reference instance carries no such attribute, so this stays a recorded delta -- but
a deliberate one with a reason, no longer the "unexplained, possibly a defect" it was
listed as before.

**Next / open threads:** (1) themes (7), fonts (8), languages (10), hard buttons (11);
(2) the skill layer; (3) offered but not built -- a `Stop` hook that runs the suite so
the diffs cannot be skipped regardless of what I remember.

**Deferred by the user, not forgotten:** `FALLBACK_MIN_SIZE_PX = 35` gets validated when
we start building live projects, where real pages at real resolutions will exercise it.

**The CSS was never diffed against the reference -- that is why every sizing bug reached
the user.** They asked why they were being sent pages to check when they had supplied a
sample, and they were right: this project's own Approach section says an automated diff
runs before any manual testing in Construct. The attribute diff did. Nothing diffed CSS.

`component_css_shape_test.py` now compares, for all 21 types, which of width/height the
generated rule states and whether each is a pixel value or the literal `auto`, against
the reference instances. **It found four more mismatches immediately** -- including
inside the fix shipped minutes earlier:

- `ch5-keypad`, `ch5-textinput`, `ch5-video`: the reference states `height: auto`. I had
  "fixed" them by OMITTING height, which is not the same thing.
- `ch5-wifi-signal-level-gauge`: the reference states `width: auto; height: auto`; we
  stated nothing.

**And the root cause of the 816px widget list was upstream of all of it.** The showcase
took each type's size from a reference INSTANCE, which has been resized and configured.
`component-context.json`'s `defaults.style` is the drop size and was there all along:
a widget list drops at `200px / auto`, a button list at `510x68`, a slider at `300x30`,
a media player at `800x600`, a toggle at `100px` wide with no height. `defaults.style`
now drives both the emitted shape and the showcase's sizes, outranking the reference.

Two further published fields replaced things I had been inferring: `canResize` (already
in use) and `supportedSizeFormat` (`widthOnly`, `containerWidthOnly`, `widthOnlyNoSize`,
`handleWidthOnly`), which names the aspect-locked class directly.

Full 43-file suite green; all six pages regenerated and their CSS verified against the
reference before this was written.

**Showcase components are FRESH, unconfigured instances again.** The user asked why the
widget list arrived with a widget reference already assigned: it should be added empty.
They are right, and it defeated the purpose -- the question these pages answer is
whether a newly CREATED component matches a newly DROPPED one, and a pre-configured
instance cannot answer it. The override (a widget reference and 3 items, added while
chasing the wrong diagnosis) is gone, and `OVERRIDES` is now deliberately empty with
that reasoning recorded in the file so it is not "helpfully" repopulated later.

The widget list is once again `widgetid=""`, `numberofitems=1`, positioned with no
explicit size -- which is the actual fix, and is independent of whether a widget is
assigned.

`widget_reference_id()` stays in component.py: the `w{GUID}` convention is verified
against the reference project and any real widget list will need it. It is simply not
something the showcase should apply.

**One operational note:** a write to `AllComponents - Media 2.cuig` failed with
`PermissionError` while Construct had it open, so the regeneration silently left that
page stale until retried. Worth remembering when a regenerated page appears not to have
changed -- and worth handling in the harness if this recurs.

Full 42-file suite green; all six pages regenerated.

**Confirmed good in Construct:** Buttons, Keypads, Gauges, Media. **Pending re-check:**
Media 2 and Text.

**Widget list corrected -- and my diagnosis of it was wrong.** I attributed its wrong
size to an empty `widgetid` (nothing referenced, so nothing rendered inside the box).
The user disproved that directly: dropping an EMPTY widget list in Construct gives
something "much smaller than yours", so the initial size was wrong before any widget was
assigned. The empty widgetid was real but beside the point.

The actual cause is the same family as the gauges: a widget list's rendered size is the
widget it references multiplied by its item count -- a small placeholder when it
references nothing -- so it is CONTENT-sized and no explicit box belongs in its CSS.

`CONTENT_SIZED_TAGS` is **transcribed, not derived**, and the code says so: `canResize`
is True for it, and its componentProperties differ from `ch5-button-list`'s only in ways
too incidental to hang a rule on. `ch5-button-list` is the control -- same "no
render-size variables" bucket, but it does lay out to its box and is confirmed good in
Construct -- so the test asserts both behaviours side by side to keep the distinction
honest.

`widget_reference_id()` stays (the `w{GUID}` convention is real and the showcase's list
still points at the project's widget), but its docstring now records that an empty one
is legitimate and was not the bug.

**Sizing rules now, all four:** `canResize: False` or content-sized -> no box;
aspect-locked -> width only; aspect-locked at 1:1 (dpad) -> both, squaring a non-square
request; everything else -> both.

Full 42-file suite green; showcase regenerated.

**Confirmed good in Construct:** Buttons, Keypads, Gauges, Media. **Pending re-check:**
Media 2 (video, video switcher, widget list) and Text (text input).

**Sizing resolved as a CLASS, plus a separate widget-list cause.** The user checked the
remaining pages: Media good; Media 2 wrong on the video switcher, the video and the
widget list. The first two turned out to be the keypad's problem again, and the third a
different problem entirely.

**The class.** Video, video switcher, keypad, toggle and text input are all
ASPECT-LOCKED -- their render-size variables are sourced from a single axis, so height
follows width and an explicit height is a guess. Having had three independent reports
of the same class, the per-type flags are gone and `writes_css_size()` derives it:

1. `canResize: False` (animation, the three gauges) -> no width, no height.
2. Aspect-locked -> width only.
3. Aspect-locked at 1:1 (the dpad) -> both, with a non-square request squared.
4. Everything else -> both.

That derivation reproduces every outcome already confirmed good in Construct (button,
slider, media player, button list, tab button, dpad, the gauges) and fixes the two
reported. **ch5-textinput is fixed by the same rule without waiting for a fourth
report** -- it is in the class, and its variable is preset-named
(`--ch5-textinput--small-width`), which made it suspect already.

**The widget list was NOT a sizing bug.** Its `widgetid` was empty, so it referenced no
widget and rendered nothing inside a box that still sized the adorner. `widgetid` is the
widget's `Id` GUID with a literal "w" in front -- confirmed in the reference, where
`WidgetListReference.cuiw` (`eb72224e-...`) is referenced as `web72224e-...`, the same
`w{GUID}` convention a ch5-template uses for `templateid`. The generator still allows an
empty one (Construct creates them that way, you pick the widget afterwards), but
`widget_reference_id()` builds the reference and the showcase now points its widget list
at the project's own MyWidget with 3 items.

Full 42-file suite green; showcase regenerated.

**Confirmed good in Construct:** Buttons, Keypads, Gauges, Media. **Pending re-check:**
Media 2 (video, video switcher, widget list) and Text (text input, changed by the class
rule above).

**Sizing, third correction: aspect-locked types.** The user found the adorner mismatch
on the keypad while the dpad looked right. Both are aspect-locked -- their rendered size
is driven by a SINGLE axis, which `reflow.py::_is_aspect_locked` already had a test for
-- so their height follows their width and an explicit one is a guess. The dpad only
looked right because the showcase happened to hand it a square; a non-square request
would have rendered a square component inside a rectangular adorner.

- A **keypad** now writes width and no height, like the toggle.
- A **dpad** squares a non-square request: every real instance is square (118x118,
  221x221) and Construct never lets its box go otherwise. reflow.py does the same when
  fitting one to a new resolution.
- Fixed-size detection now reads `componentProperties.canResize`, the SDK's own
  published flag, instead of inferring it from an empty render-size mapping. It names
  exactly the four the user identified (animation, segmented, signal level, wifi) --
  same answer, from the authority rather than a proxy.

**Confirmed good in Construct so far:** Buttons, Keypads (dpad), Gauges. Keypad pending
re-check after this fix.

**The three aspect-locked types not yet looked at are the likely next reports**, since
they are the same class as the keypad: `ch5-textinput`, `ch5-video`, `ch5-video-switcher`
all currently get an explicit height. They were left alone deliberately -- their
reference instances DO carry a height and nothing has shown them broken, so changing
them on suspicion risks breaking what works. `ch5-textinput` is the most suspect: its
render-size variable is `--ch5-textinput--small-width`, preset-named unlike every other
type's, and its reference instance uses `size="small"` with no variable at all.

Full 42-file suite green; showcase regenerated.

**Sizing corrected again, this time for the fixed-size types.** The user checked the
Gauges page and found the same adorner mismatch on the segmented, signal-level and wifi
gauges, adding the fact that settles it: **"signal level and wifi only support fixed
sizes"**.

The first fix over-applied. It set `size="custom"` on every type with a preset `size`
attribute, but a component can only be CSS-resized if the SDK gives it render-size
variables to drive -- and those three have an EMPTY `propertyMapping`. They lay
themselves out from their own attributes (`numberofsegments`, `numberofbars`, the
preset), so `size="custom"` set a preset that does not exist and the explicit
width/height sized an adorner around a component that ignored it. The reference agrees:
the segmented and signal gauges carry **no width or height in CSS at all**.

**The rule is now two conditions, both from SDK data:** a type is custom-sized only if
it has a preset `size` attribute AND `size_css_vars()` yields variables. Everything else
keeps its preset and is positioned without a CSS box (`css_width`/`css_height` on the
profile). That also caught a second over-reach on the way: `ch5-color-chip` HAS
render-size variables but no `size` attribute, so the first version invented one no real
instance carries.

Result: 12 custom-sizable types carry their variables; 9 fixed-size types keep their
preset. The three gauges are positioned and never given a size.

**Both of these were fixes to a fix**, and the pattern is worth naming: the reference
diff cannot see either bug, because the reference instances were never resized, so their
CSS says nothing about what happens when we DO size one. Rendering is the only oracle
for that, which is why the user's screenshots found what 42 green tests did not.

Showcase pages regenerated. Full 42-file suite green.

**Still to check in Construct:** the remaining showcase pages (Text, Media, Media 2) --
Buttons and Keypads already confirmed good.

**Adorner-vs-render size mismatch FIXED -- a regression I introduced, on a bug that had
already been fixed once.** The user opened the showcase pages and found the selection
adorner larger than the component on a toggle and a button, and said this was fixed
before. It was: Phase 4 hit exactly this on ch5-button.

**Why it came back.** A CH5 component does not lay itself out from the plain
`width`/`height` on its `#id` rule -- those size the canvas ADORNER. Its own rendering
reads CSS custom properties, and it only honours an explicit size when `size="custom"`.
`ch5_button.py` does both. `component.py`'s generic `build_component` did neither: it
called `build_position_css` without `extra_vars`, and never overrode `size`. That broke
every type -- including ch5-button, whose ATTRIBUTES delegate to the confirmed builder
but whose CSS came from the generic path. Carrying a fix across a generalisation is
exactly what a reference diff cannot check, because the reference instances were never
resized either.

**The fix is per-type SDK data, not a table.** `size_css_vars()` reads
`component-context.json`'s `classToVariableMapping` "idSelector" entry: a toggle maps
width -> `--ch5-toggle--handle-size-regular`, a dpad -> `--ch5-dpad--regular-size`, a
keypad -> `--ch5-keypad--regular-container-width`, a button width AND height. Both
condition kinds in that data are honoured -- `swaptarget` (a vertical button's width
drives the HEIGHT variable) and `ignore` (a horizontal slider ignores its height
mapping). `size="custom"` is now set for every type with a preset-enum size attribute;
notably "custom" is NOT in the schema's own enum, it is a Construct-level mode, which is
why it cannot be derived and had to come from the real files.

**A toggle also writes no explicit height** (`ComponentProfile.css_height=False`). Its
height follows its handle size, its reference instance carries width only, and an
explicit height is itself an adorner-too-tall bug -- which is what the user's screenshot
showed.

**One earlier note was wrong and is corrected:** the toggle's `size="custom"` had been
recorded as "the user resized this instance". It is not instance state -- it is required
for any explicitly-sized component, which is precisely the bug.

`component_size_vars_test.py` pins all of it, including that the variables appear in
BOTH @media blocks. Showcase pages regenerated. Full 42-file suite green.

**Still awaiting the live check** of the six `AllComponents - *` pages in Construct.

**Showcase pages generated for every component type -- AWAITING THE USER'S CHECK IN
CONSTRUCT.** `harness/build_component_showcase.py` writes six pages into
`GenTestProject2`, carrying all 21 profiled types built entirely by
`generator/component.py`:

| page | components |
|---|---|
| AllComponents - Buttons | tab button, button list, toggle, button (13 nested children) |
| AllComponents - Keypads | keypad, dpad (18 nested children) |
| AllComponents - Gauges | segmented, signal level, wifi signal level, slider |
| AllComponents - Text | colour picker, text input, qrcode, text, datetime, colour chip |
| AllComponents - Media | media player (800x600, fills its page) |
| AllComponents - Media 2 | widget list, video switcher, video, animation (7 children) |

Sizes are taken from each type's reference instance rather than invented, so components
appear at realistic proportions; layout is a shelf pack into the primary 1280x800 that
spills to another page when a row will not fit.

Verified on disk before handing over: every page round-trips byte-identically, all 21
types present, every component inside the 1280x800 panel, zero overlaps, all 38 nested
children written, and the `.cuip` marked stale (by `write_cuig` itself now).

**This is the check the reference diff cannot make.** Matching a Construct-authored
file's attributes is not the same as Construct rendering the result -- the contract work
already showed live checking catching what static diffing does not.

**One more parser bug found while doing it**, same family as the spaced-CSS one: a real
page carries `width:auto` on a component never given an explicit size, and
`parse_position_rules` called `int()` on it and raised -- aborting the parse of EVERY
element in that page, not just the one rule. A non-numeric length now means "not
stated", which is the meaning a missing width already had; a rule with no numeric
POSITION is skipped entirely. Full 41-file suite green.

**Next / open threads:** (1) the live check of these pages; (2) the `showtickvalues`
slider delta, the one difference from the reference not explainable as instance state;
(3) `FALLBACK_MIN_SIZE_PX = 35` validation; (4) themes (7), fonts (8), languages (10),
hard buttons (11); (5) the skill layer.

**Container component types DONE -- every CH5 component type the reference project
contains now generates, parents and nested children alike.** Together with the flat
slice, `generator/component.py` covers all 20 profiled types.

**Where the child definitions come from, and it is two different places:**
- **Counts are SDK data.** A button list's `numberofitems` (10), a tab button's
  `numberofitems` (3), a video switcher's `numberofsources` (5) and `numberofscreens`
  (2) -- each read off the parent's own attributes, and each matching its reference
  instance's child count exactly.
- **The dpad's and keypad's fixed sets are NOT in the SDK.** They are hardcoded in
  `pd-metadata-resolver\MetaDataResolver.ts:103-135`, which pushes literal child tags:
  five dpad buttons (up/down/left/right with `fa-caret-*` icons, centre with none) and
  thirteen keypad buttons (1-9 with their letter groups, 0/+, star, hash, and
  `buttonextra` carrying `fas fa-phone`). Transcribed into `DPAD_KEYS`/`KEYPAD_KEYS`
  with the source cited; the test asserts the shapes still match.

`ch5-subpage-reference-list` turned out NOT to be a container: its only child in the
reference is a textnode, so it builds flat.

**Two defects the reference diff caught**, both of which would have shipped silently:
- **Booleans were written as Python `True`.** `component-context.json` holds real JSON
  booleans for some defaults (`ch5-subpage-reference-list`'s `centeritems`), and `str()`
  turns those into `"True"` -- not what the file or CH5 want. Now normalised.
- **`disabled` was being emitted as a default.** The reference settles it by
  contradiction: the dpad and signal gauge have it, the video switcher does not. It
  records what the user set in the properties panel, so a fresh component never carries
  it (`NEVER_EMIT`).

**`component_container_types_test.py` checks children, not just parents** -- count, each
child's attribute keys, and each child's values. A dpad with four buttons, or a keypad
whose `buttonstar` had the wrong label, would look plausible and behave wrong, so the
count assertion explains what a mismatch means (we read the wrong parent attribute). It
also asserts children reach the Html view and that generated child ids are unique.

Recorded deltas are instance state again, and the notes are self-checking: the keypad's
first TEN children match exactly, while star/hash/extra carry an `id` and an empty
`labelminor` that MetaDataResolver never writes -- Construct assigns those once a child
has been touched.

Full 41-file suite green.

**Next:** the remaining `showtickvalues` slider question (the one delta not explainable
as instance state), `FALLBACK_MIN_SIZE_PX = 35` validation, themes (7), fonts (8),
languages (10), hard buttons (11), and the skill layer. Worth considering soon: nothing
generated by `component.py` has been opened in Construct yet -- the reference diff is a
strong oracle but it is not the same as Construct rendering it.

**Component builders: all 15 flat types now reproduce their reference instance --
key-for-key and value-for-value.** The source read resolved both open questions, and
both answers were things no amount of further inference would have reached.

**1. The sync block is not general.** `ccid_sync_*` was being generated for any tag with
sass-schema sectors, which is 21 of them -- producing 72 attributes on a datetime whose
real instance has 17. In the entire reference project **only `ch5-button` carries a
single sync attribute**. Theme mode is not the gate (a theme-mode button still has 78 of
them); `setSyncData` lives in `commonButtonTraitsMixins`, the button family's own mixin.
`SYNC_TAGS = ("ch5-button",)`, and the test asserts the generator and the reference agree
about which types carry sync, in both directions.

**2. `defaults.attributes` and the trait defaults are BOTH written, not either/or.** The
base layer short-circuited to the context's `defaults.attributes` whenever a tag declared
them. That is exactly backwards for the affected types: a slider declares 10 context
defaults and STILL gets `min`/`max`/`step` from the trait pass, a signal gauge gets
`numberofbars`/`value`. Merging the two sources (context defaults first, winning on
value) took the exact-match count from 3/15 to 15/15.

Two supporting source findings, both from `MetaDataResolver.ts`: `supportsAttribute`
builds a tag's trait set from its own `attributeProperties` UNION `global`'s -- the same
own-then-global pattern the contract lookup needed -- and `:214-229` overrides some
defaults in code rather than reading schema.json (a slider's `min`/`max`/`step` are null
in the schema, hardcoded there).

**`ch5-button` delegates to `ch5_button.py`** rather than going through the generic path:
it already has a builder confirmed attribute-for-attribute in Phase 4, including the
icon/image/checkbox variants the generic path knows nothing about.

**`component_flat_types_test.py` diffs every type against the reference on every run** --
keys and 256 attribute values -- rather than restating expectations by hand. Differences
are recorded per type with a reason and are themselves checked: a recorded delta that
stops being true fails the test, so the notes cannot rot. The recorded ones are
user-typed content (a qrcode's text, a toggle's labels), state flags Construct sets when
the user acts (`demoMode`, `ccid_customSizeSet`, chosen sizes), and the universal `oldID`
-- which every reference instance has because it records a duplicated component's
previous id, and a fresh component has none.

**One suspected defect, recorded not hidden:** we emit `showtickvalues` on a slider from
its non-null schema default and the reference slider does not carry it. The slider mixin
is the likeliest place it is dropped. It is the single delta here that is not explainable
as instance state.

Full 40-file suite green.

**Next:** container types -- ch5-dpad, ch5-keypad, ch5-button-list, ch5-tab-button,
ch5-video-switcher, ch5-subpage-reference-list -- which need a nested-child builder
(`ch5-dpad-button`, `ch5-keypad-button`, individual buttons, sources/screens). They
currently raise `NotImplementedError` rather than emit a childless shell that would look
right and behave wrong. Then: `FALLBACK_MIN_SIZE_PX = 35` validation, themes (7), fonts
(8), languages (10), hard buttons (11), and the skill layer.

**Component builders: pipeline built, layer 1 NOT yet correct -- WIP, do not use.**
`generator/component.py` generalises Phase 4's button into `build_component(sdk, tag,
...)` for the flat (childless) types. Four of its five layers are right; the base
attribute layer reproduces only 3 of 15 types exactly and is the open work.

**What is solid:**
- The layer structure generalises, which was the design bet. Measuring every reference
  component against the button's layers showed the unexplained attributes were almost
  entirely the same common-wiring keys the button hardcoded.
- `PROFILES`: the per-type wiring facts, transcribed from the reference project because
  they are NOT derivable from the SDK -- `ccid_ComponentType` is "Formatted-Text" for
  `ch5-text`, "Widget List" for `ch5-subpage-reference-list`, "Signal Gauge" for
  `ch5-signal-level-gauge`, and which types carry `ccid_ActiveFont`/`ccid_Label` varies.
- Container types raise `NotImplementedError` rather than emitting a childless shell
  that would look right and behave wrong (that is the next slice regardless).
- **`oldID` is correctly NOT emitted**: every reference instance has one, but it is an
  artifact of the user duplicating components, not something a fresh component carries.
- Two source findings: `MetaDataResolver.ts::supportsAttribute` builds a tag's trait set
  from its own `attributeProperties` UNION `global`'s -- the same own-then-global pattern
  the contract lookup needed -- and `MetaDataResolver.ts:214-229` OVERRIDES some defaults
  in code rather than reading schema.json (a slider's `min`/`max`/`step`, which are null
  in the schema). Both are now in the code.

**What is wrong:** the base layer currently short-circuits to
`component-context.json`'s `defaults.attributes` when a tag declares them, and
trait-filters the schema otherwise. Against the reference: `ch5-color-picker`,
`ch5-textinput` and `ch5-video` match exactly; the rest are off. Under-produces on the
slider (no `min`/`max`/`step` -- the short-circuit skips the override path), the signal
and wifi gauges (`numberofbars`, `value`, `minvalue`, `maxvalue`), the toggle
(`labelon`/`labeloff`), the qrcode and datetime. Over-produces `ccid_sync_*` on
`ch5-datetime`, `ch5-text`, `ch5-qrcode` and `ch5-color-chip` -- the sass-schema sectors
are being applied to types whose real instances carry none of them.

**Next step, and it is source work not inference:** read `MetaDataResolver.ts`'s trait
loop properly -- how `defaults.attributes` and the trait set combine (they are clearly
not either/or), and what gates the sync-attribute block per type. Three iterations of
inferring the rule from samples each matched some types and broke others, which is the
signal to stop guessing and read the code.

Full 39-file suite green (component.py has no tests yet -- deliberately, since nothing
about it should be treated as confirmed).

**Writing a page or widget now marks its project's contract stale automatically -- a
real gap the user found by asking the right question.** They noticed Construct gave no
"contract has been updated" toast when the button list's new signal was added, and asked
whether we set the flag for EVERY contract-relevant change (components added or removed,
signals, etc.). Two separate answers came out of checking:

**1. The change did take effect.** `GenTestProject2.cuic` was rewritten 0.4s after the
page write, and `ItemSelected` is present in the generated
`output/.../ComplexContracts/ButtonListTheme.g.cs`. So the missing toast did not mean a
missed update. Worth knowing WHY there was no toast: the notification comes from
`PersistenceHelper.cs:646` (`SaveContract`), on Construct's own in-app save path.
`ContractGenerationBehavior` -- which sets the flag and schedules generation -- is driven
by `SaveProjectCmd`/`ProjectItemUpdatedCmd`, i.e. edits made INSIDE Construct. Our
file-level edits reach it only via the file watcher, and the exact conditions under which
the toast is or is not raised on that path were not traced. **Unverified; do not treat
the toast as the signal that a generated change landed -- check the .cuic timestamp and
the generated output instead.**

**2. The audit found a genuine hole.** `write_cuig` -- the function behind creating a
page, creating a widget, adding a component, and enabling a signal -- never touched the
`.cuip`. Every correct case so far was a caller remembering by hand (both ad-hoc scripts
did it explicitly); nothing enforced it, and a forgotten one ships a project whose
contract does not match its pages, with no symptom until someone opens the Contract
Editor.

`write_cuig` now marks the `.cuip` beside the file it wrote
(`contracts.py::mark_project_stale_for`), deriving the project from the folder rather
than taking it as a parameter -- an optional "also mark the project" argument is exactly
what gets forgotten. Every write marks, including a rewrite: nothing in the written file
distinguishes a renamed component from a no-op, and over-marking costs one regeneration
on next open while under-marking is silent corruption. `mark_project_stale=False` opts
out. A page written where no `.cuip` sits (most of the test suite) is not an error; two
`.cuip`s in one folder raises rather than guessing.

That guard also caught a pre-existing test bug: `reflow_task10_integration_test`'s
"project with no pages" was sitting in the same folder as another project's pages, so
`add_resolutions_to_project` had been globbing those pages -- it was not testing the
zero-page case it claimed to. Given its own folder.

Full 38-file suite green.

**Coverage of the flag now:** new project (`build_project_attributes` defaults it true),
resolutions added (`add_resolutions_to_project`), any page/widget write (`write_cuig`),
and directly via `mark_contract_stale(cuip)`. Component/signal/rename changes all reach
disk through `write_cuig`, so they are covered by construction rather than by discipline.
**Deleting** a page or widget is the one contract-relevant change with no generator path
at all yet -- when one is added it must mark the project too.

**Complex-component contracts VERIFIED IN CONSTRUCT 2026-09-10, with one addition.** The
user checked the generated contract in the actual program: dpad, keypad, tab button and
media player all came out right, so the complex components' own contract strategies DO
honour what the file says -- the open question from the last two entries is closed. The
button list needed one more signal, **"Button Selected"**, which they had missed when
setting up the sample; added to `DEFAULT_SIGNALS` and the page regenerated.

**That signal is only sayable by its DISPLAY name**, which forced a better lookup.
`pd-buttonreceivestateselected` contracts as "ItemSelected" -- a name it shares with
`pd-receivestateselectedbutton` ("List Item Selected") -- so the contract name cannot
pick it out. Names now resolve in three layers: raw attribute, then contract name, then
the name Construct's UI displays. Two layers rather than one merged index, because each
resolves collisions the other has: the button list's and the video switcher's duplicates
are distinguished only by display name, while `ch5-color-chip`'s send/receive halves BOTH
display as "Red Value" and are distinguished only by contract name ("Red Value" vs
"RedValue_fb"). Only `ch5-spinner` is still genuinely ambiguous -- identical in both
layers -- and still raises.

**`REFERENCE_GAPS` records the one place we now deviate from the sample** (the button
list's Button Selected) with the reason. The defaults test still holds every other type
to the reference exactly, and will fail telling us to drop the entry once the sample
catches up.

**Correction earlier in this exchange, user-caught:** the first version of the
verification page also wrote a synthetic non-default signal (`pd-receivestateenable`)
onto all five components as a probe for whether a strategy honours the file. The user saw
"Enable" enabled everywhere and asked where it came from. It was unnecessary as well as
wrong -- an overriding strategy shows up as the contract having more or fewer signals
than the reference specifies, no invented signal required -- and it made the page stop
matching the ground truth it exists to check. Removed; the script now asserts the page
carries exactly the intended set.

Verified on disk after regenerating: TOML `[Elements.Attributes]` and the Html view agree
signal-for-signal on all five components, page round-trips byte-identically, everything
inside the 1280x800 primary, `.cuip` marked stale. Full 37-file suite green.

**Phase 6 (contracts) is complete** -- simple and complex components both confirmed live.
**Next / open threads:** (1) `layout.py::parse_position_rules` only matches compact CSS --
`parse_position_rules("#it8l { left: 124px; ... }")` returns `{}`, so reflowing a
Construct-authored page in the spaced format (as `Component-Widgets-Media Player.cuig`
is) would silently do nothing, no error; verified directly, unfixed; (2) whether
`FALLBACK_MIN_SIZE_PX = 35` holds across more pages and resolutions; (3) the remaining
generator phases -- themes (7), fonts (8), languages (10), hard buttons (11), and the
skill layer; (4) real builders for the complex component types, which is what would let
us stop transplanting.

**Complex-component contracts verified on the canvas; contract listing still to check.** Only the simple path (ch5-button) had ever been opened in Construct,
while dpad, keypad, button list, tab button and media player each go through their own
contract strategy, some of which force signals on regardless of the file
(`DpadStrategy.cs:91`, `KeypadStrategy.cs:94`). We have no generator builders for those
types yet, so the user chose the transplant route: copy each component's
element/html/css out of the reference project and let OUR `contracts.py` write the
signals.

`harness/transplant_reference_components.py` builds
`GenTestProject2/ComplexContracts.cuig` from five reference components and marks the
project stale. Each carries **exactly** the signals the user set on it in the reference
project -- dpad and keypad `Digital Start`, button list `ItemPress`, tab button `_Press`
+ `_Selected`, media player its seven -- so the page is a faithful restatement of their
spec and Construct's contract can be compared against it directly.

**Correction, user-caught:** the first version of this page ALSO wrote a synthetic
non-default signal (`pd-receivestateenable`) onto all five, as a probe for whether a
complex strategy honours the file. The user saw "Enable" enabled everywhere and rightly
asked where it came from. It was unnecessary as well as wrong: a strategy that overrides
the file shows up as the contract having MORE or FEWER signals than the reference
specifies, which needs no invented signal to detect -- and the invented one made the page
stop matching the ground truth it exists to check. Removed; the script now asserts the
page carries exactly the reference's signal set and nothing beyond it.

Verified on disk: page round-trips byte-identically, all 5 elements present, each
component's signals match the reference project exactly in BOTH the TOML
`[Elements.Attributes]` and the Html view, positions present, all inside the 1280x800
primary, no element-id collides with another page, `.cuip` reads `ContractIsStale =
"true"`.

**Also found while using the API for real:** `signal_map`'s friendly-name keys had been
lower-cased by the ambiguity refactor, so `"Enable" in signal_map(...)` was false for
every component. Fixed and pinned. And the reference files are not uniformly formatted --
most are compact CSS, `Component-Widgets-Media Player.cuig` is spaced -- which the
transplant tolerates but reflow does not (see open threads).

**Next / open threads:** (1) **the live check** -- open `GenTestProject2` and compare the
`ComplexContracts` contract against the reference project's signals for those five types;
(2) **`layout.py::parse_position_rules` only matches compact CSS** --
`parse_position_rules("#it8l { left: 124px; ... }")` returns `{}`, so reflowing a
Construct-authored page written in the spaced format would silently do nothing, no error
(verified directly; unfixed, it is reflow rather than contract work); (3) whether
`FALLBACK_MIN_SIZE_PX = 35` holds across more pages and resolutions; (4) the remaining
generator phases -- themes (7), fonts (8), languages (10), hard buttons (11), and the
skill layer; (5) real builders for the complex component types, which is what would let
us stop transplanting.

**Phase 6 corrected against the user's updated reference project — DONE.** The user
confirmed live that Construct generates Press and Selected for the buttons, then went
further and set the intended contract signals on EVERY component in
`C:\Solutions\ClaudeSamples\Components`, noting that some types need none. Checking our
discovery against that ground truth immediately found **two defects in what had just
shipped** — both of which had passed a green suite, because the suite only tested the
model against itself:

1. **Only the component's own `attributeProperties` was read.** Construct reads the
   tag's entry and then falls back to `global`; `JoinNameProviderHelper.cs` says so in
   its own comment, *"search more specific first, then global"*. `ch5-color-picker`
   declares no signal entries at all, so all six signals the user enabled on it were
   unnameable. `ch5-button` went from 5 signals to **10**, gaining `Enable` — which the
   real hand-authored i12 Multicam button has enabled and we previously could not name.
2. **The gate was `extenderPosition`.** That governs the project-level extender, not
   what a component can expose. `ch5-dpad`/`ch5-keypad`'s `sendeventonclickstart`
   ("Digital Start") have none — they are `removeOnContractUse` — yet the user enabled
   them. The gate is now the category prefix (`Send `/`Receive `), because merely having
   a category is far too loose: 179 entries are "Interactions" (`orientation`,
   `customvstheme`, `z-index`) and admitting those offers signals Construct cannot
   generate.

**The standing check that would have caught both**, now a test: walk every component in
the reference project and assert all 95 enabled signals are nameable.

**Attribute placement was also wrong, and the reference settled it.** Signals go LAST,
after the `ccid_sync_*` block — all six reference buttons end with exactly
`sendeventontouch`, `pd-receivestateselected`. The old position (between common wiring
and sync) was flagged in the code as a guess. `phase4_smoke_test`'s exact key-order diff
against the real `Button1` now passes with the default signals present rather than
suppressed, which is a stronger check than before.

**`DEFAULT_SIGNALS` now covers 15 component types**, transcribed from the reference, plus
six the user confirmed should expose none by design (video, video switcher, subpage
reference list, background, datetime, qrcode — each HAS signals available, so "none" is
a decision). The table is not trusted on its own: the test recomputes it from the
reference files every run, so if the user changes a component in Construct the test
reports the difference instead of us drifting.

Also fixed a latent hazard the extraction exposed: three tags have two distinct signals
sharing one friendly name (`ch5-button-list` "ItemSelected", `ch5-spinner` "Selected
Item", `ch5-video-switcher` "_Label"). The old lookup silently kept whichever came last;
ambiguous names now raise and list the attributes to choose between.

Full 37-file suite green. **Next / open threads** (nothing in flight): (1) contract
enablement for the COMPLEX components is still unverified in Construct — dpad, keypad,
button list, tab button, widget list, video switcher and media player each have their own
contract strategy, and some force signals on regardless of the file
(`DpadStrategy.cs:91`, `KeypadStrategy.cs:94`); the defaults are transcribed from the
user's files but no generated complex component has been opened in Construct yet;
(2) whether `FALLBACK_MIN_SIZE_PX = 35` holds across more pages and resolutions; (3) the
remaining generator phases — themes (7), fonts (8), languages (10), hard buttons (11),
and the skill layer.

**Phase 6 (contracts) — DONE, and far smaller than the phase index implied.** The user
corrected the scope up front: we never author a `.cuic`. Construct generates it, and all
we have to leave behind is (1) the signals enabled on each component and (2)
`ContractIsStale = "true"` in the `.cuip`. Both halves confirmed in CCIDE source before
any code was written — `ProjectOpenBehavior.cs:72-99` reads the flag on open, schedules
generation, clears it and saves; `ContractGenerationHelper.cs:1177` shows Construct
writing the `"Contract Enabled"` sentinel itself. Half of it was already built:
`project.py` has written `ContractIsStale="true"` for new projects since Phase 2.

**Enablement turned out to be pure SDK data**, so `generator/contracts.py` hardcodes
nothing per-component: `component-context.json`'s `attributeProperties` entries carrying
an `extenderPosition` ARE the contract-capable signals (the same gate Construct uses in
`CreateProjectComponent`), and their keys already have the storage prefix applied. The
prefix rule itself (`JoinPropertyProvider.cs:151`: state -> `pd-`, event -> bare) is
cross-checked against `schema.json`'s join direction for the whole catalog — 132 signals,
all agreeing — so a future SDK that disagrees fails a test instead of silently writing an
attribute Construct ignores. For `ch5-button` there are exactly five signals: Visibility,
Visibility_fb, Press, Selected, Mode.

**Three findings, each from measurement rather than assumption:**

1. **`component-context.json` outranks `schema.json`.** `ch5-media-player`'s
   `pd-receivestateusemessage` has no schema attribute at all, yet the hand-authored
   reference project writes it as a live signal. The planned hard "raise on disagreement"
   cross-check would have rejected a real signal; it now treats a schema entry as
   corroboration (`ContractSignal.schema_backed`) and the test pins the exception set.
2. **Signal names are not attribute names.** `pd-receivestateshow` contracts as
   "Visibility_fb", not "Visibility"; a slider's `pd-receivestatevalue` is "Lower Touch
   fb", not "Value". Hence resolution by the SDK's own names, with an unknown name raising
   and listing the valid options rather than silently skipping.
3. **Complex components are a separate path.** Dpads, keypads, button/widget lists, tab
   buttons, video switchers and media players each have their own contract strategy, and
   some (`DpadStrategy.cs:91`, `KeypadStrategy.cs:94`) force `ButtonPress` on regardless
   of the file. Phase 6's work is verified for simple components only — flagged in
   `docs/architecture/06-contracts.md` and in the index row.

**A new button now carries Press + Selected by default** (the user's choice), overridable
via `contract_signals=...` and disableable with `()`. `phase4_smoke_test` builds its
reference-comparison button with `()` so it still diffs like-for-like against the real
Button1, which has no signals — and now asserts that premise instead of assuming it.

**Live project updated for verification**: `GenTestProject2/ButtonVariants.cuig`'s three
buttons (IconButton/ImageButton/CheckboxButton) now carry both signals in the TOML *and*
the Html, and the `.cuip` is marked stale. Backup in the session scratchpad as
`GenTestProject2.bak-contracts-20260910-215713`. The edit was a targeted text insertion,
not a regeneration: the harness's byte-identical round-trip proves our section SPLITTER
matches Construct's, not that our TOML writer reproduces a real page.

Full 35-file suite green (4 new: signal discovery, enablement, button wiring,
end-to-end). **PENDING LIVE CHECK**: user opens GenTestProject2 in Construct and confirms
the Contract Editor shows Press and Selected for the three buttons. **Next / open
threads**: (1) that live check; (2) contract enablement for complex components, whenever
one of those component types is built; (3) whether `FALLBACK_MIN_SIZE_PX = 35` holds up
across more pages and resolutions; (4) the remaining generator phases — themes (7), fonts
(8), languages (10), hard buttons (11), and the skill layer.

**Relaxation redesigned as water-fill capping, after the user's own page proved the
first two designs wrong — DONE.** User clarified the intent: 35px is "the minimum allowed
size WHEN you have to shrink", not a target size (correcting a suggestion to raise the
constant to 40/45 to get bigger buttons — that's not what the knob is for; the floor is
clamped to each item's authored size and can only stop shrinking, never grow anything).
Sweeping their real `ReflowTest.cuig` down through smaller panels to prove the floor
actually engages then exposed a genuine defect in the relaxation path, and fixing it
properly took three attempts, each ruled out by measurement rather than argument:

1. **Drop the most demanding rows' floors, honor the rest in full** (the original). At
   400x240 this produced **1px** buttons and a 1px D-pad where no floor at all gave
   16-30px/87px — the rows still frozen at their full floor ate everything and starved
   the relaxed ones.
2. **Scale every floor by one factor.** Fixed the crush, but let a single inflated demand
   dominate: a 40px button sharing a row with a 300px D-pad forces that row to reserve
   263px (a row scales as ONE unit), and scaling 263 down proportionally still leaves it
   huge — ordinary button rows that were easily satisfiable fell from 50px to 26px.
3. **Water-fill capping** (`reflow.py::_cap_floors`, shipped). Both failures are the same
   failure: the expensive demands are exactly the ones asking for a large FRACTION of
   their own row. So bisect for the largest single cap `lambda` such that no row may
   reserve more than `lambda x its own natural height`, trim every floor above it, and
   leave affordable floors completely untouched.

Plus the rule that makes the whole thing safe: **a floor may never make a component
smaller than it would have been with no floor at all.** `_cap_floors` takes `min_cap` =
Tier 3's own uniform scale and refuses any capping below it, so the caller can't fund one
group's floors out of another's. Schema-backed floors (a real Construct limit) are still
held whole while that's affordable; when it isn't, everything degrades together instead of
the D-pad holding 100px while buttons are crushed to pay for it. Capping every floor
always succeeds, since at `lambda = min_cap` the capped total is at most `available`.

**Measured on the real `ReflowTest.cuig` (floor = 35):**

| target | with floors | without floors |
|---|---|---|
| 640x360 | btn 36-68, dpad 198 | btn 36-68, dpad 198 (floor not reached) |
| 480x272 | **btn 35-40, dpad 116** | btn 27-51, dpad 147 (floor engages, D-pad donates) |
| 400x240 | btn 16-30, dpad 88 | btn 16-30, dpad 87 (degraded to no-floor, gracefully) |
| 320x240 | btn 10-20, dpad 58 | btn 10-19, dpad 56 (never worse) |

New tests pin the invariant that the first design violated: a 30-point sweep over target
heights on a realistic shape asserting the smallest component is never smaller than the
no-floor result, plus a proportional bound on the deliberately pathological E2E fixture.
Full 31-file suite green.

**CONFIRMED IN CONSTRUCT 2026-09-10**: user opened the regenerated `GenTestProject2` and
reported the TSW-570 (640x360) layout looks correct -- closing out the chain of pending
live checks from the last three entries (aspect-lock/size-var fix, column-aware + wrap
compaction, and now minimum-size floors). The on-disk result is idempotent under the
final code: buttons 36px, Up/Down 68px, D-pad 198px, 21 elements, zero overlaps, inside
640x360. **Next / open threads** (nothing in flight): (1) whether
`FALLBACK_MIN_SIZE_PX = 35` still holds up across more pages and resolutions -- on this
page the floor isn't even reached at 640x360, it engages from ~480x272 down; (2) the
generator phases after reflow (contracts, themes, fonts, languages, hard buttons, skill
layer) per the original plan.

**Floor raised to 35px + the real page actually regenerated + a real source-selection
bug fixed to make that possible — DONE.** User re-checked `ReflowTest.cuig` in Construct,
still saw 28px buttons, and asked for a 35px minimum "which should force the dpad to be
made smaller". Two things were true: the 28px really was stale output (the file had never
been rewritten — the previous session verified on a COPY), and refreshing it for real was
blocked by a bug worth fixing on its own.

**`reflow_file` treated a non-empty source device block as the complete source layout.**
A device block is an OVERRIDE of the catch-all, not a replacement — Construct only restates
a rule where it differs. `ReflowTest.cuig`'s 1280x800 block holds exactly ONE rule (the
D-pad's `left`/`top`, byte-identical to the catch-all's), so reflowing from it produced a
one-element target block and silently dropped the other twenty: the exact "components
absent at the new resolution" failure this feature exists to prevent. Fixed as the
element-level counterpart of what `_fill_missing_size` already does at field level — every
catch-all element the device block doesn't mention is inherited into the source, catch-all
order first for determinism, with the block's own restated rule still winning for the
element it names. New regression test `reflow_source_block_union_test.py` covers both
halves (all three elements carried over; the restated one keeps its override).

**`FALLBACK_MIN_SIZE_PX` 30 -> 35** (one test fixture's target height retuned, since its
derived row floor no longer fit). Full 31-file suite green.

**Real files regenerated** (`mode="full_refit"`, SDK wired in; backup taken first, in the
session scratchpad as `GenTestProject2.bak-20260910-180206`): `ReflowTest.cuig` 21 -> 21
elements, source/menu buttons **28 -> 36px**, Up/Down **54 -> 68px**, D-pad **228 ->
198px**, zero overlaps, zero elements under their floor, max right 639 / bottom 358 within
640x360. `ButtonVariants.cuig` and `MyWidget.cuiw` unchanged (already fit).

**Worth knowing before tuning further: at 35 the floor never actually binds on this page.**
The uniform Tier 3 factor already lands the buttons at 36, so the D-pad's 228 -> 198 comes
from the column/compaction wrap fixes, not from the minimum. Swept the constant against the
real file to find where it does bite: 40 -> buttons 40px / D-pad 184; 45 -> buttons 42px /
D-pad 176; 50, 55, 60 -> unchanged at 42/176. It saturates because 42px is the buttons'
own authored height and the floor is deliberately shrink-only (clamped to each item's own
size, so it never grows a component past what the user drew) — once every button row sits
at its natural size, the D-pad simply takes the remainder (344 - 4*42 = 176). **Next**:
user re-checks TSW-570 in Construct and says whether to go to 40/45 for bigger buttons.

**Reflow: minimum-size floors for Tier 3 — DONE, implemented + verified against the
real files; one real finding the user should know about.** User reviewed the min-size
design spec (`docs/superpowers/specs/2026-09-10-reflow-min-size-design.md`, written at
the end of the previous session after real buttons came out 28px tall at TSW-570) and
asked to build it. Went spec -> plan (`docs/superpowers/plans/2026-09-10-reflow-min-size.md`)
-> inline TDD execution, five tasks, one commit each. Tier 3 now takes an optional
per-item floor: `fit_axis(min_sizes=...)` runs a flexbox-style iterative
freeze-and-redistribute (freeze whoever falls through their own floor at the current
uniform scale, reserve exactly that floor, recompute the scale for everyone still free,
repeat to convergence), while `min_sizes=None` — every legacy caller — runs the original
one-shot formula verbatim. That two-path split is load-bearing and now pinned by tests: at
`target_dim=10` the legacy branch's independent 1px floors span 11px (its documented,
deliberate overshoot) where the dict branch always packs to exactly `target_dim`. Floors
come from two sources: the SDK's own `minSizes` schema (`ch5-dpad` 100px, `ch5-keypad`
210px — real Construct-enforced limits) and `FALLBACK_MIN_SIZE_PX = 30` for the types
Crestron publishes nothing for (`ch5-button`, `ch5-slider`).

**Three corrections to the spec, all evidence-backed** (the spec was written from the
dpad/keypad entries alone): (1) `minSizes` values are NOT uniformly `"Npx"` strings —
`ch5-qrcode`'s is the unit-less `"160"` and `ch5-video-switcher`'s is a raw JSON **int**,
so the spec's `int(v.rstrip("px"))` would have raised `AttributeError`; (2) three tags
publish their own `minHeight` (`ch5-tab-button` is 110 wide / 68 tall), so the lookup is
per-axis with `minWidth` as the height fallback rather than `minWidth` for both; (3) every
floor is clamped to the item's own current size, keeping Tier 3 shrink-only — without it an
element already below its type's minimum would be "frozen" LARGER than it started.

**The X and Y axes turned out not to be symmetric, which the spec had assumed.** A row can
only ever reach X-axis Tier 3 with ONE column, because `wrap_rows`' peel loop exits only
when the remainder passes `_columns_fit` (Tier 2 compaction alone suffices) or when a
single unpeelable column is left — verified directly and now pinned by an assertion. So
freeze-and-redistribute never engages on X; there the floor only converts "silently emit a
component narrower than its own technical minimum" into an `AxisFitError`, which needs a
target narrower than the component's own floor (210px for a keypad) and so no real device
reaches it. The Y axis (`stack_rows`, no wrap tier) is where floors actually change
layouts.

**Deviation from the spec's error handling, forced by an existing test.**
`reflow_aspect_lock_dpad_test.py` immediately caught the spec's plain `AxisFitError`
doing real damage: a Y floor is DERIVED, not technical — keeping a 40px button at its own
30px minimum forces its whole 300px row to stay 225px tall — so a crowded stack can demand
more than `target_height` even when every individual component is satisfiable, and the
error made `_fit_group` skip the ENTIRE device block. That turns a legibility problem into
missing components, the exact failure `reflow_file` exists to prevent. `stack_rows` now
relaxes instead: it gives up SOFT (fallback) floors before schema-backed ones — a
`ch5-dpad` under 100px isn't just ugly, Construct doesn't support it — largest floor first
so the fewest rows are sacrificed, and warns how many rows lost their floor. A relaxed row
lays out exactly as it does today, so this can never be worse than current behavior.

**Verified against the real `GenTestProject2` (on a copy, the real files were NOT
touched):** `ReflowTest.cuig` reflows to all 21 elements, zero overlaps, inside 640x360,
zero elements under their own floor. **The finding worth knowing: the 28px buttons still
sitting in that file are stale output.** Re-running *today's* code produces 36px even with
floors disabled — the reported symptom was already fixed by the same-day column-aware +
compaction-aware wrap work, and the file just still holds the pre-fix block. So the floors
changed nothing on that page; they're a safety net, and the E2E test uses two fixtures that
genuinely exercise them instead (a tall unconstrained `ch5-image` donating height so
buttons hold 30px: 29px -> 30px; and an over-crowded page where relaxation takes
components at a usable size from 0 to 15 while the dpad holds its 100px schema floor).
5 new test files, full 30-file suite green with every pre-existing test unchanged except
`reflow_aspect_lock_dpad_test.py`, which now expects the one relaxation warning (its layout
assertions are untouched and still pass).

**Also spotted, NOT fixed (needs its own decision):** `reflow_file` treats a non-empty
source device block as the complete source, rather than the catch-all overridden by that
block. `ReflowTest.cuig`'s 1280x800 block holds exactly ONE rule (Construct only restates
a device rule when it differs from the catch-all), so a plain re-run from 1280x800 would
reflow ONE element and drop the other 20. That's why the verification above deleted that
block on its copy to source from the 21-element catch-all. **Next**: user decides whether
to (a) have the real project refreshed so TSW-570 can be re-checked in Construct — worth
doing, since the file's current block predates two rounds of fixes — and (b) whether the
source-block/catch-all union above is the next thing to fix.

**Reflow: column-aware row fitting + compaction-aware wrap decisions — DONE, verified
against the real TSW-570 (640x360) block.** User's next question after the D-pad/
missing-var fixes: "why do the Up/Down buttons move to a second row — there's certainly
room to have them in the same row." Investigated and found a genuinely deeper gap:
`detect_rows` correctly groups a D-pad with two Up/Down button pairs into one row (the
D-pad's height Y-overlaps both pairs), but the row's own X-fitting had no concept that
`iha5b0`/`i4rvpkl` (Up/Down, sharing the exact same source `left=292`) don't compete for
horizontal space — they're a vertical stack. Went through the full brainstorm -> spec ->
plan process (`docs/superpowers/specs/2026-09-10-reflow-columns-design.md`,
`docs/superpowers/plans/2026-09-10-reflow-columns.md`) given this touches the row/wrap
model and its overlap-safety proof, per the user's explicit choice of the general
"sub-column" approach over a narrower patch. Built `detect_columns` (the X-axis
transpose of `detect_rows`, grouping a row's members by source X-range overlap) and
wired `wrap_rows`/`_fit_group`'s X-loop to fit/peel whole columns instead of individual
elements — a stacked pair now always travels together. **Self-caught a second, deeper
bug while re-verifying**: my own spec's hand-trace claimed compaction alone would fit
the real D-pad row with no wrap needed, but the actual re-run still split it — because
`wrap_rows` decides whether to peel using the row's RAW (uncompacted) span vs.
target_width, never checking whether Tier 2 compaction alone (the very next tier, tried
immediately after wrap) would have sufficed on its own. Fixed with the same floor
formula Tier 3 already uses (`sum(widths) + (n-1)*min_gap <= target_width`), applied one
tier earlier before committing to a peel. Together, both fixes eliminate an entire
unnecessary Y-stacking slot on the real page, which is what had been forcing every other
row to compress harder than necessary. 4 new regression tests (one per fix, including
a hand-traced reproduction of the exact reported shape); full 19-file suite passes with
zero regressions (confirmed during planning that every existing wrap_rows test case's
outcome is unchanged under the new compaction-feasibility check — only genuinely-fits-
after-compaction cases like this one behave differently). Re-verified against the real
files: both Up/Down pairs still share their `left` position; source-row button height
improved from 21px to 28px, D-pad from 166px to 228px (both real, measurable
improvements, not just "no worse"); 21 elements, zero overlaps, everything within the
640x360 canvas, zero CSS-var/box mismatches anywhere in the block. **Next**: user to
re-check TSW-570 in Construct.

**Reflow bug fix (superseded above) — a resized button's adorner showed the correct new size, but the
button rendered much bigger — DONE.** Same session as the D-pad/aspect-lock work below,
found immediately after by the user re-checking TSW-570 in Construct: a "Source 2"
button's selection adorner correctly showed 21px height, but the button itself rendered
far larger. Root cause: the size-var fix from the D-pad bug only *recomputed* CSS vars
that already existed in an element's source `extra_vars` — it never *added* a missing
one. A real `size="regular"` button (confirmed: `--ch5-button--regular-width/height`
only ever appears once a button has actually been custom-resized in Construct) has NO
such vars in its source CSS at all, so when reflow forces it to `size="custom"` (see
below), Construct has nothing telling it to constrain the internal render to the new
size — it falls back to a larger default while the outer box (and the adorner) correctly
reflects what reflow computed. Fixed: `_fit_group` now `extra_vars.update(size_vars)`
unconditionally after the per-var loop, synthesizing the vars fresh whenever missing,
not just updating ones that happened to already be there. New regression test
(`reflow_missing_size_vars_test.py`) replicates the exact shape (a plain `size="regular"`
button with empty source `extra_vars`) and asserts the vars are present and match the
final box exactly. Full 16-file suite passes. Re-ran against the real files: zero
width/height/var mismatches across the entire TSW-570 block (programmatically checked
every element, not just the one the user spotted) — "Source 2" now has
`--ch5-button--regular-width: 84px`/`-height: 21px`, matching its box exactly. **Not yet
addressed** (user's next-flagged issue, needs the same brainstorm-first rigor as other
reflow algorithm changes since it touches the wrap model): the wrap tier always drops
peeled/overflow elements onto a brand-new row below rather than considering unused
width beside an already-tall sibling row (e.g. the D-pad's row) — user's hypothesis,
plausible but unconfirmed, is that fixing this would reduce how hard the Y-axis needs to
compress everything else, which is what drove some buttons down to an illegibly-small
21px in the first place (a texture/overlap symptom, not a true box overlap — confirmed
separately: wrapped sub-rows have a clean 4px gap, not a collision). **Next**: user to
re-check TSW-570 in Construct for the adorner/render-size fix, then decide whether to
proceed with the wrap-placement redesign.

**Reflow: SDK-schema-driven size scaling + aspect-lock reconciliation + size="custom"
forcing — DONE, verified against the real `GenTestProject2` at TSW-570 (640x360), the
smallest/most stressful resolution added yet.** After the centering fix (below), the
user added TSW-760 and TSW-570 to `GenTestProject2` and hit two new real bugs at 640x360
(small enough to force genuine wrap + compaction + scaling together for the first time):
(1) a `ch5-dpad` sharing a row with other content visibly overlapped its neighbors in
Construct even though the computed box math was provably non-overlapping — traced to
`_fit_group`'s extra_vars scaling only recognizing CSS var names containing the literal
substrings "width"/"height"; `--ch5-dpad--regular-size` (the D-pad's actual rendered-size
var, confirmed via the SDK's `classToVariableMapping` schema to be sourced from `width`)
matches neither, so it stayed at its original unscaled value regardless of what the box
computed — the box was safe, the RENDER wasn't; (2) a wrapped second line of real
(user-authored, not generator-authored) buttons ran off-canvas because those buttons had
`size="regular"`, which ignores explicit CSS and renders at a fixed preset size — the
same bug this generator's own element-creation code already works around at creation
time, just never applied by reflow. The user pushed back on an initial fix proposal
(schema-driven var scaling alone) by asking me to actually test it against the real
D-pad shape first — correctly caught that it was incomplete: X and Y are fit completely
independently, so even with the var wired to the *correct* schema-mapped axis, that
axis's own scale factor could still be 1.0 (unchanged) while the OTHER axis did all the
shrinking, leaving the var (and the real render) unscaled regardless. Real fix, verified
against a genuine resized D-pad in the reference project
(`C:\Solutions\ClaudeSamples\Components\Component - Keypad - DPad.cuig`, id `ixo7`:
width/height/var are always numerically identical, confirming the component is
fundamentally square): after both axes fit independently, any element the SDK schema
marks single-axis-sourced (`_is_aspect_locked`) gets width=height=`min(fitted_width,
fitted_height)` — shrinking only, so it can't introduce a new overlap. Built (all in
`generator/reflow.py`, gated behind an optional `sdk` param so every existing caller/test
that doesn't pass one keeps today's exact legacy behavior unchanged): `_component_size_css_vars`
(generalizes `ch5_button.py::button_size_css_vars` to any component type via the same
schema, recomputing size vars from the FINAL reconciled width/height instead of
ratio-scaling — strictly more robust, no compounding rounding difference between two
methods), `_is_aspect_locked`, `_tag_index` + `_force_custom_size` (reflow's first-ever
edits to `{Html}`/`[[Elements]]` TOML, not just `{Css}` — forces `size="custom"` on any
element actually resized that's currently `"regular"`, leaves repositioned-only elements
and already-`"custom"` elements untouched). `project.py::add_resolutions_to_project` now
loads the project's own installed SDK (from its `SdkId` attribute) and passes it through,
non-fatally (a project whose SDK can't be loaded still gets reflowed with legacy
behavior, flagged with a warning, never aborted). Two new regression tests hand-verify
both fixes against realistic shapes (`reflow_aspect_lock_dpad_test.py`:
a D-pad forced non-square by asymmetric X/Y scaling now reconciles to square, var
matches, zero overlaps; `reflow_force_custom_size_test.py`: a resized `"regular"` button
becomes `"custom"` in both Html and TOML, an already-`"custom"` resized button is a
no-op, a merely-repositioned `"regular"` button is left untouched). Full existing suite
(15 files) still passes with zero regressions. Re-ran the TSW-570 reflow against the
real files: D-pad now 166x166 (was 332x166, non-square), zero overlaps, everything
within the 640x360 canvas; the real Menu-row buttons that got genuinely resized are now
`size="custom"` in both Html and TOML. **Next**: user to re-check `ReflowTest.cuig` at
TSW-570 in Construct.

**Reflow: preserve centering (superseded above) — DONE, verified against the real
`ReflowTest.cuig`.** After
the width/height-fallback fix (below) got the portrait layout showing all 21 elements
on-canvas and non-overlapping, the user caught a subtler issue: the "Source" and "Menu"
button rows were centered in the 1280px landscape source (left margin 265px, right margin
266px) but came out flush against the portrait target's right edge (52px left, 0px right)
— none of `fit_axis`'s three tiers ever center a result; Tier 1 leaves an already-fitting
group at its original absolute position (meaningless once the canvas width changed), and
Tiers 2/3 both pack from a fixed left/top anchor. `stack_rows` reuses `fit_axis` for the Y
axis, so the row-stack had the identical gap (leaving ~600px of empty space below the
content in the 1280px-tall portrait canvas). Went through the full brainstorming → spec →
plan process given this touches the algorithm's core overlap-safety argument: design spec
at `docs/superpowers/specs/2026-09-10-reflow-centering-design.md`, implementation plan at
`docs/superpowers/plans/2026-09-10-reflow-centering.md` (5 tasks, executed inline).
**Design, approved by the user via 3 targeted questions**: (1) only recenter a row/stack
that was ALREADY centered in the source (detected via `abs(left_margin - right_margin) <=
max(4, round(0.01 * source_dim))`), not force-center everything; (2) evaluated per row
independently, not as one whole-page decision; (3) applied to both X and Y axes. The
trickiest piece: a row that `wrap_rows` splits into sub-rows has no meaningful "was IT
centered" answer of its own (it's a subset of a once-centered row) — resolved (user's
choice) by always centering a wrap-split fragment row, like a fresh flex-wrap line.
**Built**: `fit_axis` gained `source_dim`/`center` params and a final uniform-shift
`_center_result` step (safe by the same argument as Tier 1's existing translate — a
uniform shift of an already-non-overlapping group can't introduce a new overlap);
`wrap_rows` now tags each output row as a fragment (from a split) or untouched, so
`_fit_group` knows which centering rule to apply; `stack_rows` gained `source_height` for
the Y-axis case (a single whole-stack decision, no fragment concept). Every task's numeric
test case was hand-traced during planning before being written down. Verified: full
existing suite (13 files, phases 2-5 + every reflow task) passes with zero regressions —
confirmed during planning that none of the existing tests' synthetic fixtures are
accidentally centered within tolerance, so none needed adjusting except
`reflow_task5_wrap_rows_test.py`'s assertions (updated for `wrap_rows`'s new return
shape, an intentional, expected change). Re-ran the portrait reflow against the real
`ButtonVariants.cuig`/`ReflowTest.cuig`/`MyWidget.cuiw`: the 8-item and 2-item button rows
that were centered in the source now come back with byte-identical left/right margins in
the portrait target (26px/26px and 55px/55px respectively, was 52px/0px before this fix);
all 21 elements still present, zero pairwise overlaps, everything on-canvas. **Next**:
user to re-check `ReflowTest.cuig`'s portrait layout in Construct.

**Reflow bug fix (superseded above) — device-specific blocks that omit width/height (real Construct-authored
pages routinely do this) were silently dropping elements; fixed, verified against the
user's real `ReflowTest.cuig`.** After adding TSW-770 + TST-1080 (Portrait) to
`GenTestProject2` (see the `{DeviceResolutionSource}` fix below for that step), the user
opened the project in Construct and reported the portrait layout was broken — most
components weren't reflowed at all, several overflowing off the right edge of the canvas.
Root cause: `layout.py::parse_position_rules` required a `width` declaration to accept an
element's rule, but a real page authored directly in Construct (not by this generator,
`ReflowTest.cuig`) only restates `width`/`height`/`z-index` in a device-specific block when
they DIFFER from the catch-all block's value — most of its 21 elements had never been
resized, so their landscape-block rule was just `left:Npx;top:Npx;position:absolute;`. 18
of 21 elements were silently dropped from the source set as a result; reflow only ever fit
the 3 elements whose device rule happened to redundantly restate their size. This
generator's own output always restates the full property set, which is why 9+ prior tasks
of reflow work never exercised this path — every test (and every generator-authored
sample) had the shape the bug needed to hide behind, the same class of blind spot as the
per-element-`@media`-block bug found in the original reflow closeout. Fixed:
`parse_position_rules` now only requires `left`/`top` (width/height/z_index come back as
`None` when absent); new `reflow.py::_fill_missing_size` fills any `None` width/height/
z_index/extra_vars from the catch-all block's own value for that element id, dropping
(with a warning, not a crash) the rare element still missing size after that. New
regression test `reflow_partial_device_block_regression_test.py` (a hand-built page
mirroring the real shape: one element with a fully-restated device rule, two with only
left/top/position, one of *those* also carrying a catch-all-only `extra_vars` entry — the
test's first run caught a second gap, `extra_vars` not being merged the same way
width/height are, fixed in the same pass). Re-ran the portrait reflow against the real
`ButtonVariants.cuig`/`ReflowTest.cuig`/`MyWidget.cuiw` with `mode="full_refit"` (not
`add_resolutions_to_project` again, which would have duplicated the already-added
resolution id) — verified programmatically: all 21 of `ReflowTest.cuig`'s elements now
present in the portrait block, zero pairwise overlaps, everything fits the 800×1280 canvas
(max right exactly 800px). Full existing suite (phases 2-5, reflow tasks 9-10) still
passes clean. **Next**: user to re-check `ReflowTest.cuig`'s portrait layout in Construct.

**Phase 5 bug fix, corrected version — `{DeviceResolutionSource}` should never contain a
catalog-sourced resolution at all; the field-level "fix" earlier today was still wrong.**
Full arc: user was live-testing resolution add + reflow in `GenTestProject`'s Resolution
Manager and caught that an added resolution (TSW-570) looked wrong/duplicated. A first fix
pass (see superseded entry below) treated this as a field-value bug (`IsCustom`/
`resolutionType`/`resolutionName` mismatched vs. real sample files) and made
`to_project_resolution` write those fields into `{DeviceResolutionSource}` to match ~62
sampled real entries. The user then discovered the REAL root cause while fixing their own
environment: their machine's `resolutionData.user.json` (this machine's saved custom
resolutions) had an actual invalid duplicate resolution literally named "TSW-1070" —
colliding with the real catalog device name, which Construct is supposed to prevent but
evidently didn't always enforce — and that corruption had leaked into the reference sample
project (`C:\Solutions\ClaudeSamples\Components`) too. After the user cleaned both up,
`Components.cuip`'s `{DeviceResolutionSource}` became `[]` while `DeviceResolutionIds`
kept its one real id — direct proof the two aren't meant to be kept in lockstep the way
this module assumed. Traced this to source and confirmed definitively:
`PersistenceHelper.cs`'s `WriteProject`/`SaveProject` only ever assign
`uiProject.CustomDeviceResolutions` to `projectSource.DeviceResolutionSource` — catalog
picks are represented purely by id in `DeviceResolutionIds`, resolved against the global
catalog at runtime (`ResolutionHelper.cs::GenerateDeviceResolutionDto`); on load,
`OpenProjectHandlerHelper.cs` copies `{DeviceResolutionSource}` verbatim into
`CustomDeviceResolutions`, which the Resolution Manager renders as a second,
separately-removable list — exactly the duplicate/deletable row the user saw. So the
morning's field-level fix was solving the wrong problem: the real bug was ever writing a
catalog resolution into `{DeviceResolutionSource}` at all. Rewrote
`generator/devices.py::to_project_resolution` (no longer touches `IsCustom`/
`resolutionType`/`resolutionName` — the dict is now purely an id/width/height/orientation
carrier for `DeviceResolutionIds` + reflow math) and
`generator/project.py::build_project_attributes`/`add_resolutions_to_project` (catalog
resolutions only ever extend `DeviceResolutionIds`; `{DeviceResolutionSource}` is read and
written back untouched; `add_resolutions_to_project`'s reflow source-resolution lookup now
resolves existing ids against the global catalog, since it can no longer assume
`{DeviceResolutionSource}` holds every existing resolution). Also added macOS support to
`default_app_storage_path()` in both `devices.py` and `sdk.py` (confirmed via
`EnvironmentUtility.cs`: `~/Library/Application Support/crestron-construct/AppStorage`,
not the more commonly-documented `~/.config`), per the user's ask. Regenerated the
already-broken `GenTestProject2.cuip` in place (same Id, `{DeviceResolutionSource}` now
correctly `[]`) — flagged one unrelated, NOT fixed side-observation: the rewrite reset
`ThemePageColor` to `""` (the generator's long-standing, un-investigated default) where
real Construct-managed files (including this one, before the rewrite) show `"#ffffff"`;
out of scope for this fix, not touched further. `docs/architecture/05-resolutions.md`
updated with a correction section citing the exact source. **Not yet done**: this
module still has no "create a genuinely custom resolution" builder — when one is added,
it should validate that the resolution's name doesn't collide with a standard catalog
device name (the exact rule Construct itself is supposed to, but evidently doesn't always,
enforce). User is still mid-way through re-testing reflow in Construct; next step is
waiting on their signal to add resolutions to whichever project they're now using.

**Phase 5 bug fix (SUPERSEDED, see above — this fix was incomplete/wrong) —
`to_project_resolution`'s catalog->project field mapping was wrong.** User was
live-testing resolution add + reflow together in `GenTestProject` (Construct's Resolution
Manager) and caught that a resolution added by `add_resolutions_to_project` (TSW-570)
looked wrong/"custom" compared to the project's original TSW-1070 entry. Root cause,
confirmed against 62 real `DeviceResolutionSource` entries across 30+ human-authored
projects under `C:\Solutions` (not just the one reference project): Construct does NOT
copy a catalog entry's `IsCustom`/`resolutionType`/`resolutionName` verbatim into a
project. Fixed in `generator/devices.py::to_project_resolution` (hardcoded
`IsCustom: True`/`resolutionType: "generic"`). **This survey's ground truth turned out to
be contaminated** — see the superseding entry above for why, and the actual fix.

**Phase 5 continuation (superseded above) — multi-resolution reflow DONE, visually confirmed in
Construct.** All 10 tasks plus a final whole-branch review's fix wave are complete
and merged to `master` (29 commits). The final review caught the most severe bug in
the whole plan: the real generator emits one `@media` block PER ELEMENT even when
several elements share the identical query (`build_position_css` is called once per
element), so the reflow subsystem's single-match block lookup silently found and
reflowed only the FIRST element on any real multi-element page — the exact
"components absent" failure this feature exists to prevent, undetected through 9
tasks of review because every test (including the integration suite) hand-authored a
single combined block, a shape the generator never produces. Fixed with plural
`find_media_block_spans`/`parse_all_position_rules` in `generator/layout.py` and a
consolidating write path in `reflow_file`; verified against the real
`C:\Solutions\ClaudeGenTest\GenTestProject` (`ButtonVariants.cuig`'s 3 buttons all
correctly found and fit, was 1 before the fix) and now **visually confirmed by the
user in Construct** — all 3 buttons render on-canvas and non-overlapping at the
TSW-570 resolution. Also fixed in the same final-review pass: non-deterministic rule
ordering (iterated hash-randomized sets instead of the already-deterministic source
dicts), a missing fallback to the `99999px` catch-all block when a page predates the
project's first resolution, and two documentation overclaims. One known limitation
documented, not fixed, then re-assessed as lower-risk after the user corrected the
model's assumption about typical workflow: Construct projects are authored top-down
(largest resolution = primary, created first; smaller ones added and adapted down
afterward, never the reverse) — that's also the cascade-safe order, so the risk case
(a LARGER resolution added to a project that already has a smaller one) is contrary
to normal usage, not an everyday concern — see `docs/architecture/10-reflow.md`'s
"Known limitation" note. Full history in
`docs/superpowers/plans/2026-09-09-multi-resolution-reflow.md` and
`docs/superpowers/specs/2026-09-08-multi-resolution-reflow-design.md` (both kept as
an accurate corrected record, not left stale after the fix rounds). **Next**: another
component type, Trigger 2's skill-layer wiring (the mode-choice prompt when adding
elements to an already-multi-resolution page — `reflow_file`'s `mode` parameter is
the mechanism, not yet wired to the skill layer), or user's direction.

**Phase 5 continuation (superseded above) — multi-resolution reflow BUILT AND VERIFIED end-to-end
(both triggers' underlying mechanism, including row-wrap).** All 10 tasks of
`docs/superpowers/plans/2026-09-09-multi-resolution-reflow.md` complete.
`generator/reflow.py` (`fit_axis`, `detect_rows`, `wrap_rows`, `stack_rows`,
`find_new_elements`, `check_overlaps`, `pick_primary`, `choose_source_resolution`,
`reflow_file`) plus new CSS helpers in `generator/layout.py` are wired into
`generator/project.py::add_resolutions_to_project` (Task 10), which now calls
`reflow_file` for every `*.cuig`/`*.cuiw` in a project's folder each time a resolution
is added, and returns the aggregated list of any reflow warnings (return type changed
from `None` to `list[str]`, additive). End-to-end scenario tests
(`generator/_test_output/reflow_task10_integration_test.py`) cover an edge-placed
element landing on-canvas after a smaller resolution is added, the
orientation-bootstrap case, a genuine row-wrap scenario (a 4-button single row split
across two lines on a much narrower resolution — hand-verified: rows split to
`[b0,b1]`/`[b2,b3]`, tops `20`/`114`, no element scaled, no pairwise overlap), and
zero regression when a project has no pages/widgets yet. Task 10 also found and fixed
a real bug exercising real catalog data end-to-end for the first time: a real `.cuip`'s
`{DeviceResolutionSource}` stores `width`/`height` as `"Npx"` strings (confirmed
against `Components.cuip`), but `reflow.py`/`layout.py` do plain arithmetic on those
fields — every earlier task's unit tests only used plain-int synthetic resolutions, so
this never surfaced until Task 10 called `devices.py::to_project_resolution` for real.
Fixed with new `project.py::_numeric_dim`/`_numeric_resolution`, applied only to the
copies fed into the reflow subsystem — the `.cuip` on disk still gets the real string
form. All 15 smoke/task tests pass (zero regressions). Manual Construct verification
prepared against the existing `C:\Solutions\ClaudeGenTest\GenTestProject` (a second,
640x360 landscape resolution added; setup script reported no warnings) —
**visual confirmation in Construct is still pending the user opening the project.**
Trigger 2 (the skill prompting `pin_existing`/`full_refit` when new elements are added
to an already-multi-resolution page) remains explicitly NOT built — a skill-layer
conversational step, not generator code; `reflow_file`'s `mode` parameter is the
mechanism a future skill call would choose between. See
`docs/architecture/10-reflow.md`'s "Algorithm and integration summary" section.
**Next**: user confirms the manual Construct check, then another component type,
Trigger 2's skill-layer wiring, or user's direction.

**Phase 5 continuation (superseded above) — multi-resolution reflow: row-wrap design
approved, NEW 10-task implementation plan written, ready to build.** Superseding the
entry directly below: the new plan lives at
`docs/superpowers/plans/2026-09-09-multi-resolution-reflow.md` (the 2026-09-08 plan is
now stale/superseded, kept for history only). Tasks 1-3 and 7-8 carry over from the old
plan unchanged (portrait media query, CSS parse/build helpers, `fit_axis`,
`find_new_elements`/`check_overlaps`, `pick_primary`/`choose_source_resolution`) since
the core per-axis fitter's own behavior didn't change. Three new tasks implement the
row-wrap mechanism itself: Task 4 `detect_rows` (Y-overlap row grouping), Task 5
`wrap_rows` (the X-axis wrap tier — peel-and-recurse row splitting, hand-verified
against the spec), Task 6 `stack_rows` (Y-axis row-stacking). Tasks 9-10 (`reflow_file`,
integration) route through the new row/wrap/stack pipeline instead of a flat per-axis
`fit_axis` call, and Task 10 adds a genuine row-wrap end-to-end scenario (a 4-button row
split across two lines on a much narrower resolution, confirming no element gets scaled
and no pair overlaps). While translating the design into concrete code, found and fixed
a real spec gap: two rows produced by splitting the same original row share the exact
source `top` (splitting doesn't move anything vertically), so naively stacking them by
raw `min(top)` would tie sibling rows and overlap them — fixed with a pre-stacked
anchor, folded back into the design spec before Task 6 was written against it. Plan
self-review passed (full spec coverage, one placeholder-adjacent issue found and fixed
in Task 2's own test scaffolding, every function signature confirmed used consistently
across tasks). **Next**: user has been offered the execution-approach choice
(Subagent-Driven vs. Inline) — awaiting answer.

**Phase 5 continuation (superseded above) — multi-resolution reflow design REVISED
AGAIN (X axis gains a row-wrap tier), approved, implementation plan is now STALE and
needs to be rewritten.**
User revisited the design before answering the execution-approach question from the
prior session, pointing out the algorithm was pinned to pure per-axis scaling and
should behave like a real responsive layout — when horizontal space is tight but
vertical space is available, elements should wrap onto new rows below rather than only
ever compact/scale in place. Worked through the shape via clarifying questions: rows
are inferred from source elements' Y-overlap (not authored explicitly), the new wrap
tier sits between move and compact/scale (`move -> wrap -> compact -> scale` on X),
wrapping is row-only (no symmetric column-wrap for height-constrained cases), and
wrapping preserves source row groupings — only an overflowing row splits, trailing
elements peel onto a new row directly below it, rather than a full greedy re-pack that
could merge/reorder rows. The Y axis keeps its original 3-tier fallback but now
operates on the row list (as pseudo-items) instead of individual elements, so rows
stack top-to-bottom the same way elements used to. The "no new overlaps within the
fitted group" proof still holds without new 2D collision checks: same-row elements
stay disjoint on X (unchanged argument), different-row elements stay disjoint on Y
since each row's Y-extent is self-contained and rows themselves never overlap. Full
rewrite at `docs/superpowers/specs/2026-09-08-multi-resolution-reflow-design.md`
(Scope, Algorithm, Components, Error handling, and Testing sections all updated; new
`detect_rows`/`wrap_rows`/`stack_rows` components added to `generator/reflow.py`'s
planned shape). **The previously-written 7-task implementation plan
(`docs/superpowers/plans/2026-09-08-multi-resolution-reflow.md`) was written against
the old per-axis-only algorithm and is now stale — it has NOT been rewritten yet.**
**Next**: get the user's review/sign-off on the revised spec (asked, awaiting answer),
then invoke writing-plans to redo the implementation plan, then get the
execution-approach answer (Subagent-Driven vs. Inline) that was never answered last
session either.

**Phase 5 continuation (superseded above) — multi-resolution reflow IMPLEMENTATION
PLAN WRITTEN, ready to build.** 7-task TDD plan at
`docs/superpowers/plans/2026-09-08-multi-resolution-reflow.md`, source-grounded like
every prior phase: confirmed the previously-unconfirmed portrait media-query formula by
reading `C:\Git\CCIDE`'s `breakpoint.ts::createRawQuery` directly and cross-checking two
real portrait `.cuiw` sample files elsewhere in that repo (`(orientation: portrait) and
(max-height: {H+1}px) and (max-width: {W+1}px), (orientation: portrait) and (max-height:
{H-1}px)` — same `±1px` shape as the already-confirmed landscape formula, just leading
with height instead of width), closing a gap flagged unconfirmed since Phase 4. Tasks:
(1) `orientation_media_query` + doc writeup, (2) CSS block parse/find/build helpers in
`layout.py`, (3) `fit_axis` (the 3-tier algorithm itself, unit-tested per tier plus the
insufficient-room edge case, with direct pairwise AABB checks proving no overlap across
a range of target sizes), (4) `find_new_elements`/`check_overlaps`, (5)
`pick_primary`/`choose_source_resolution`, (6) `reflow_file` tying both modes together
against a hand-built minimal file, (7) wiring into `add_resolutions_to_project` plus
end-to-end scenarios (an edge-placed element landing on-canvas, the
orientation-bootstrap case, zero regression on projects with no pages yet) and manual
Construct verification against the existing `GenTestProject`. Trigger 2 (the skill
prompting for `pin_existing`/`full_refit` when adding elements to an existing
multi-resolution page) is explicitly noted as NOT built by this plan — it's a
skill-layer conversational step that calls the same `reflow_file` this plan builds, not
new generator code. **RESUME POINT (session paused 2026-09-08, picking up next
session):** user was offered the execution choice (Subagent-Driven vs. Inline, per the
writing-plans skill's handoff) and hasn't answered yet — ask that question first, don't
re-derive it. No implementation code has been written yet; the plan file is the only
new artifact. **Next**: get the execution-approach answer, then start Task 1.

**Phase 5 continuation — multi-resolution reflow design spec REVISED AGAIN (reflow
generalized into a standalone, repeatable operation with two fit modes), approved,
ready for an implementation plan.** User pointed out UI work isn't a one-time event —
new controls get added to existing pages long after resolutions are set up (e.g. Apple
TV controls today, Cable box controls next week), and every resolution besides the one
they're authored against needs the same "missing block" fix reflow already solves for
newly-added resolutions. Reflow is now a standalone `reflow_file` operation with two
callers: `add_resolutions_to_project` (target starts empty) and a new skill-level
trigger when new elements are added to an already-multi-resolution page (target already
has content) — the skill asks the user which of two modes to use: `pin_existing`
(default — leave existing controls alone, fit only the new ones; the new elements are
guaranteed not to overlap each other but only best-effort/flagged against pre-existing
pinned elements, since real 2D obstacle avoidance was explicitly ruled out of scope) or
`full_refit` (recompute everything from the source resolution, discarding whatever was
in the target — same full overlap-safety guarantee as the original single-shot design).
Adding a brand-new resolution turns out to be `pin_existing` with zero pinned elements —
no special-casing needed, one mechanism covers both triggers. The still-approved 3-tier
per-axis fit math (move, then compact whitespace to a 4px floor, then scale down) is
unchanged from the previous revision; see
`docs/superpowers/specs/2026-09-08-multi-resolution-reflow-design.md` for the full,
current design. **Next**: write the implementation plan and build it.

**Phase 9 (assets) pulled forward — local image import DONE, confirmed live in
Construct.** User caught that the Phase 4 image-button variant couldn't actually be
verified without a real asset behind it. Built `generator/assets.py`, confirmed exactly
against the real `CrimsonSilk.cuia`/`.jpg` (which is also the exact asset the reference
project's own image-type button already references), wired it into the on-disk
verification project, and the user confirmed the image now renders correctly on the
button in Construct. See `docs/architecture/09-assets.md`. Phase 4's button work (plain +
icon + image + checkbox variants) is now fully closed out end-to-end. **Next**: back to
Phase 5 (full reflow) or another component type, per user direction.

**Phase 5 — resolutions: catalog + add-resolutions-to-a-project DONE.** User chose the
smaller first slice over bundling in full reflow math. Confirmed the real
device/resolution catalog (74 entries, `resolutionData.json`), resolved both
previously-flagged open questions (catalog-vs-per-project-selection, orientation enum
semantics), corrected an unconfirmed guess in `project.py`'s own example (no real
"TSW-1070 Portrait" catalog entry exists — TSW-1070 is landscape-only hardware), and built
`generator/devices.py` + `generator/project.py::add_resolutions_to_project`. See
`docs/architecture/05-resolutions.md`. **Next**: full multi-resolution reflow (deliberately
deferred, bigger/separate slice), another component type, or user's direction.

**Phase 4 — add a CH5 component: button DONE (plain + icon + image + checkbox
variants).** A freshly-created "Ch5 Button" matches real Construct-authored buttons
exactly for the plain and icon configurations, and produces a clean (intentionally
edit-history-free) result for image; checkbox is sanity-checked only since no real sample
exists to confirm against. All schema-driven from the installed SDK's
`component-context.json` + `sass-schema.json` (see `docs/architecture/04-ch5-schema.md`).
**Next**: multi-mode/advanced buttons, another component type, or Phase 5 (resolutions),
per the user's direction.

## Approach

This is a from-scratch rebuild of the Construct UI project generator (previous attempt:
`C:\ClaudeProjects\ConstructUISkill`, kept as-is, not reused). The key change: file-format
rules are being confirmed by reading Construct's own source
(`C:\Git\CCIDE\Crestron.IDE\Projects\UiEditor`), not inferred from sample files by
trial and error. Every phase is proven against a known-good reference project
(`C:\Solutions\ClaudeSamples\Components`) with an automated diff (`harness/compare.py`)
before any manual testing inside Construct itself.

**This directive was violated for the whole of the component-sizing work (2026-09-10/11)
and prose did not prevent it.** The attribute diff ran on every test run; nothing diffed
the generated CSS, so four sizing bugs in a row reached the user, who found each by eye
across several rounds. Writing the rule down twice -- here and in the user's own notes --
changed nothing. What changed it was a TEST: `component_css_shape_test.py`, which found
four more mismatches the moment it existed, including ones inside the fix that had just
shipped.

So the rule is mechanical, not aspirational: **before generated output goes to the user,
an automated comparison must cover the dimension that changed** -- attributes, CSS,
children, file structure. If no such comparison exists, write it first; it is 60 lines.
A live check in Construct is only for what a diff structurally cannot see (does it
RENDER correctly), never a substitute for the diff.

## Log

- 2026-09-10: **Reflow: column-aware row fitting + compaction-aware wrap decisions --
  DONE, verified against real TSW-570.** User asked why Up/Down buttons still moved to
  a second row when "there's certainly room." Found `detect_rows` correctly groups a
  D-pad with two button pairs into one row (Y-overlap via the D-pad's height), but
  X-fitting had no concept that a pair sharing the same source `left` doesn't compete
  for horizontal space. Went through brainstorm -> spec -> plan (user chose the general
  "sub-column" approach); built `detect_columns` (X-axis transpose of `detect_rows`)
  and wired `wrap_rows`/`_fit_group` to fit/peel columns, not elements. Self-caught a
  second bug re-verifying: `wrap_rows` decided to peel using the row's RAW span, never
  checking whether Tier 2 compaction alone would have sufficed -- fixed with Tier 3's
  own floor formula, applied one tier earlier. Together: an entire unnecessary
  Y-stacking slot eliminated on the real page. 4 new tests, full 19-file suite passes.
  Re-verified: pairs still share `left`; button height improved 21px->28px, D-pad
  166px->228px; 21 elements, zero overlaps, zero var mismatches. See Current phase
  above for the full writeup.
- 2026-09-10: **Reflow: missing size-var bug (adorner right, button rendered bigger) --
  DONE.** User re-checked TSW-570 in Construct right after the D-pad/aspect-lock fix and
  caught it immediately: a resized button's adorner showed the new smaller size, but the
  actual render stayed big. The size-var fix only recomputed vars ALREADY present in an
  element's extra_vars -- a plain size="regular" button (the common case for anything
  not yet hand-resized) has none at all, so forcing it to size="custom" left Construct
  with nothing to constrain the render, even though the box CSS was correct. Fixed with
  an unconditional `extra_vars.update(size_vars)` so the vars get synthesized fresh when
  missing. New test `reflow_missing_size_vars_test.py`; full 16-file suite passes;
  re-verified zero width/height/var mismatches across the entire real TSW-570 block. See
  Current phase above -- also flags the user's next question (wrap-placement/Up-Down
  beside the D-pad) as not yet addressed, pending a decision on scope.
- 2026-09-10: **Reflow: SDK-schema-driven size scaling + aspect-lock + size="custom"
  forcing -- DONE, verified against real GenTestProject2 at TSW-570 (640x360).** User
  added TSW-760 then TSW-570 and hit two real bugs at the smallest resolution yet: a
  ch5-dpad visibly overlapped neighbors in Construct despite non-overlapping box math
  (its `--ch5-dpad--regular-size` var, schema-confirmed sourced from width, wasn't
  recognized by the old substring-based scaling and stayed unscaled); a wrapped real
  button ran off-canvas because `size="regular"` ignores explicit CSS entirely. User
  caught that my first fix proposal (schema-driven var scaling alone) was incomplete
  by asking me to test it first -- X/Y are fit independently, so the var's mapped axis
  could still have scale 1.0 while the OTHER axis did the shrinking. Real fix,
  confirmed against a genuine resized D-pad in the reference project (width=height=var
  always, confirming it's fundamentally square): after independent X/Y fitting, force
  width=height=min(...) for any SDK-schema-flagged single-axis component (shrink-only,
  can't introduce overlap). Built `_component_size_css_vars`/`_is_aspect_locked` (SDK
  schema-driven, generalizes ch5_button.py's existing button-only helper) and
  `_tag_index`/`_force_custom_size` (reflow's first edits to Html/TOML, not just Css) in
  reflow.py, gated behind an optional `sdk` param so every existing caller/test is
  unaffected; `add_resolutions_to_project` now loads the project's own SDK and passes
  it through, non-fatally. 2 new regression tests, full 15-file suite passes. Re-ran
  against the real files: D-pad now 166x166 (was 332x166), zero overlaps, resized real
  buttons now size="custom" in both Html and TOML. See Current phase above.
- 2026-09-10: **Reflow: preserve centering -- DONE, verified against the real
  ReflowTest.cuig.** User caught that a button row centered in the 1280px landscape
  source came out flush against the portrait target's edge instead of staying centered
  (none of fit_axis's 3 tiers ever center a result; stack_rows' Y axis had the same
  gap). Went through brainstorming -> spec
  (`docs/superpowers/specs/2026-09-10-reflow-centering-design.md`) -> plan
  (`docs/superpowers/plans/2026-09-10-reflow-centering.md`, 5 tasks) given this touches
  the algorithm's overlap-safety argument. User's approved design: only recenter a
  row/stack that was already centered in the source (tolerance `max(4, 1%)`), decided
  per row independently, applied to both axes; a wrap-split fragment row always centers
  (no meaningful "was it centered" answer of its own). Built: `fit_axis` gained
  `source_dim`/`center` + a final uniform-shift step; `wrap_rows` tags fragment vs.
  untouched rows; `stack_rows` gained `source_height`. Full existing suite passes with
  zero regressions (verified during planning no fixture was accidentally centered,
  except `reflow_task5_wrap_rows_test.py`'s assertions, intentionally updated for the
  new return shape). Re-ran against the real files: previously-centered rows now come
  back with byte-identical left/right margins (26/26, 55/55 -- was 52/0), all 21
  elements present, zero overlaps. See Current phase above for the full writeup.
- 2026-09-10: **Reflow: device-specific blocks omitting width/height were silently
  dropping elements -- found and fixed after the user's real `ReflowTest.cuig` reflowed
  broken (most components not moved, several overflowing off-canvas) for TST-1080
  Portrait.** Root cause: `layout.py::parse_position_rules` required `width` to accept a
  rule; a real Construct-authored device block only restates width/height/z-index when
  they differ from the catch-all's value, so 18 of `ReflowTest.cuig`'s 21 elements (whose
  device rule was just `left/top/position`) were silently dropped. This generator's own
  output always restates the full set, so no prior task/test ever exercised the omitted
  case. Fixed: `parse_position_rules` now only requires left/top; new
  `reflow.py::_fill_missing_size` fills missing width/height/z_index/extra_vars from the
  catch-all block per element (the new regression test's first run also caught extra_vars
  not being merged, fixed in the same pass). Re-ran the portrait reflow against the real
  files with `mode="full_refit"`; verified programmatically (all 21 elements present, zero
  pairwise overlaps, fits the 800x1280 canvas). See Current phase above for the full
  writeup.
- 2026-09-10: **`{DeviceResolutionSource}` architecture bug found and fixed (supersedes
  the same-day field-level fix below, which was still wrong).** User fixed their own
  corrupted environment (an invalid custom resolution named "TSW-1070", colliding with
  the real device, in `resolutionData.user.json`, which had leaked into the reference
  sample project too) and, watching `Components.cuip`'s `{DeviceResolutionSource}` become
  `[]` after cleanup while `DeviceResolutionIds` stayed populated, that was the tell that
  this module's whole model was backwards. Traced to source
  (`PersistenceHelper.cs::WriteProject`/`SaveProject`): `{DeviceResolutionSource}` only
  ever persists genuinely custom resolutions, never catalog picks — confirmed via a
  `Grep` across `C:\Git\CCIDE` landing on the exact two-line assignment. Rewrote
  `generator/devices.py::to_project_resolution` and
  `generator/project.py::build_project_attributes`/`add_resolutions_to_project`
  accordingly; `phase5_smoke_test.py`'s regression check rewritten to assert
  `{DeviceResolutionSource}` stays `[]` for catalog-only adds (the opposite of what it
  asserted a few hours earlier). Also added macOS support to `default_app_storage_path()`
  in `devices.py`/`sdk.py` at the user's request, grounded in `EnvironmentUtility.cs`.
  Regenerated the real `GenTestProject2.cuip` on disk to match (same Id, now-empty
  `{DeviceResolutionSource}`). Full test suite (phases 2-4, reflow task 10, phase 5) still
  passes clean. See Current phase above for the full writeup, including one flagged-but-
  not-fixed side observation (`ThemePageColor` default).
- 2026-09-10: **`to_project_resolution` catalog->project field bug "fixed" (SUPERSEDED —
  wrong fix, see entry above).** User caught it live-testing in `GenTestProject`; root
  cause was believed to be `IsCustom`/`resolutionType`/`resolutionName` field mismatches,
  "confirmed" against 62 real `DeviceResolutionSource` entries scraped from 30+
  human-authored `.cuip` files under `C:\Solutions`. That survey's ground truth turned out
  to be contaminated by the same machine-level corruption described above — the real bug
  was structural, not field-level. Left in the log for an honest record of how this was
  actually debugged (two passes, not one).
- 2026-09-09: **Correction: Construct projects are authored top-down, not
  smallest-first.** User corrected an assumption in the just-written "known
  limitation" note (cascade ordering risk when resolutions are added out of size
  order): Construct projects work like desktop-first responsive web design — the
  largest resolution is always created first and is the primary; smaller resolutions
  are added afterward and adapted down from it, never the reverse. This is also the
  cascade-safe order (a later-added smaller resolution's block lands later in the
  file, correctly overriding the primary at smaller viewports), so the risk case
  documented (a larger resolution added after an existing smaller one) is contrary to
  normal usage, not an everyday concern as the original note implied. Reworded the
  known-limitation note in `docs/architecture/10-reflow.md` and this file's Current
  phase section to reflect the corrected understanding — the limitation itself is
  still real and still unfixed, just lower-priority than first stated.
- 2026-09-09: **Multi-resolution reflow — CLOSED OUT: final whole-branch review's
  Critical bug fixed and visually confirmed in Construct.** The final review (after
  all 10 tasks individually passed) found the real generator emits one `@media` block
  PER ELEMENT even when several elements share the identical query
  (`build_position_css` runs once per element), but `layout.py`'s `find_media_block`
  only ever finds the FIRST such block — silently reflowing only one element on any
  real multi-element page, zero warnings. Confirmed against the real
  `ButtonVariants.cuig` (3 buttons, 3 separate `99999px` blocks, not one combined
  block) before ruling; every task's tests had hand-authored the combined-block shape
  for convenience, which is why 9 tasks of review missed it. Fixed with plural
  `find_media_block_spans`/`parse_all_position_rules` (find every matching block) and
  a consolidating write path (replace the first matching target span, delete the
  rest); also fixed in the same pass: non-deterministic rule ordering (was iterating
  hash-randomized sets), a missing `99999px` catch-all fallback for pages that
  predate a project's first resolution, and two documentation overclaims. Independently
  verified via standalone scratch scripts before writing the fix into the design spec
  and plan, then via a scoped re-review (adversarial splice stress test, 4 different
  `PYTHONHASHSEED` values) after the fix landed — clean, no new breakage. One known
  limitation documented but not fixed: resolutions added out of ascending size order
  can invert the CSS cascade (latent, unreached by any test or the real project — see
  `docs/architecture/10-reflow.md`). User then opened `GenTestProject` in Construct,
  switched to the newly-added TSW-570 resolution, and confirmed all 3 buttons on
  `ButtonVariants.cuig` render on-canvas and non-overlapping — the one remaining
  unconfirmed item from Task 10, now closed. **Next**: another component type,
  Trigger 2's skill-layer wiring, or user's direction.
- 2026-09-09: **Multi-resolution reflow — Task 10 (final task) DONE: wired into
  `add_resolutions_to_project`, end-to-end scenarios including row-wrap, doc
  writeup.** `add_resolutions_to_project` now calls `reflow.reflow_file` for every
  `*.cuig`/`*.cuiw` in a project's folder, once per newly-added resolution, using
  `choose_source_resolution` to pick which existing resolution to fit from
  (same-orientation primary, or the other orientation's primary for the bootstrap
  case); return type changed from `None` to `list[str]` of aggregated reflow warnings
  (additive, existing callers unaffected). New
  `generator/_test_output/reflow_task10_integration_test.py` covers 4 scenarios: an
  edge-placed element landing on-canvas after a smaller resolution is added, the
  orientation-bootstrap case, a genuine row-wrap scenario (4-button single row onto a
  much narrower resolution — hand-traced to confirm the algorithm's own output before
  trusting the test's assertions: rows split `[b0,b1]`/`[b2,b3]`, tops land at `20`/
  `114`, all 4 buttons stay their original 150x90 size, zero pairwise overlaps), and a
  zero-pages regression check. Found and fixed a real bug while wiring real catalog
  data through the pipeline end-to-end for the first time (every earlier task's unit
  tests used hand-built plain-int resolution dicts, never the real catalog shape): a
  real `.cuip`'s `{DeviceResolutionSource}` stores `width`/`height` as `"Npx"` strings
  (confirmed against `Components.cuip`), but `reflow.py`/`layout.py` do plain
  arithmetic on those fields (`width + 1`, `pick_primary`'s width comparison) and
  crashed with a `TypeError`. Fixed at the `add_resolutions_to_project` wiring
  boundary — new `_numeric_dim`/`_numeric_resolution` coerce width/height to `int`
  only for the copies fed into the reflow subsystem, leaving what's written to the
  `.cuip` on disk in the real, confirmed string form. All 15 smoke/task tests pass
  (zero regressions). Manual verification prepared against the real
  `C:\Solutions\ClaudeGenTest\GenTestProject` (a 640x360 landscape resolution added
  via the reflow path; setup script printed no warnings) — visual confirmation in
  Construct itself is still pending the user opening the project, not yet claimed as
  confirmed. `docs/architecture/10-reflow.md` updated with the algorithm/integration
  summary and this bug's writeup. This closes out the 10-task multi-resolution reflow
  plan in full.
- 2026-09-09: **Multi-resolution reflow — X axis redesigned with a row-wrap tier
  (`move -> wrap -> compact -> scale`), via the brainstorming skill.** User asked to
  revisit the reflow logic before answering the still-outstanding execution-approach
  question, objecting that the design was "pinned to a pure horizontal space" — pure
  per-axis scaling/compaction, never letting elements use available vertical room by
  moving below other elements. Classified as an architectural revision (changes an
  already-approved design's core algorithm, reopens a line explicitly marked
  out-of-scope). Resolved via one-at-a-time clarifying questions: rows are inferred
  from source Y-overlap (not authored explicitly); the wrap tier is inserted between
  move and compact (wrap preferred over shrinking); row-wrap only, no symmetric
  column-wrap; and wrapping splits only overflowing source rows (trailing elements
  peel onto a new row below), rather than a full greedy re-pack that could merge or
  reorder rows. Y axis keeps its original 3-tier fallback (move/compact/scale)
  unchanged in kind, but now operates on the row list as pseudo-items instead of
  individual elements. Reworked the "no new overlaps" proof to cover the new
  structure: same-row elements stay disjoint on X (original argument, unchanged
  wording only), different-row elements stay disjoint on Y since each row's Y-extent
  is self-contained and rows themselves never overlap — no new 2D collision detection
  needed. Rewrote Scope, Algorithm, Components, Error handling, and Testing sections
  of `docs/superpowers/specs/2026-09-08-multi-resolution-reflow-design.md` in place
  (same file, per this project's established revision pattern); self-review caught and
  fixed two stale "3-tier fit"/pre-wrap-tier-order wording spots left over from the
  previous revision. Committed (`fde5733`). **The existing 7-task implementation plan
  was written against the old algorithm and is now stale — not yet rewritten.**
  **Next**: user reviews the revised spec, then re-run writing-plans for a fresh
  implementation plan, then get the still-unanswered execution-approach choice.
- 2026-09-08: **Multi-resolution reflow — implementation plan written** (7 TDD tasks,
  `docs/superpowers/plans/2026-09-08-multi-resolution-reflow.md`), following the
  writing-plans skill against the now-approved spec. Before writing it, did the source
  research the spec's scenarios actually require but didn't yet have: the portrait
  media-query formula, unconfirmed project-wide since Phase 4 (flagged in `layout.py`'s
  own docstring and `04-ch5-schema.md`). Found and read `C:\Git\CCIDE`'s
  `breakpoint.ts::createRawQuery` directly (the real client-side source that generates
  these breakpoints) and cross-checked it against two real portrait `.cuiw` files
  elsewhere in that repo (`Bug_CCIDE_5225_Widget2.cuiw`/`Widget5.cuiw`, both a
  1024x1322 portrait resolution) — source and samples agree exactly, closing the gap
  rather than letting the plan bake in a guess. Also worked out concrete tier-2/tier-3
  math not fully nailed down in the spec's prose: whitespace compaction is a linear
  interpolation from each gap's original size toward the 4px floor (weighted by how
  much reduction is still needed), and tier-3 scaling reserves room for the mandatory
  `(n-1)*4px` floor gaps before computing the shared scale factor, then repacks at
  exactly 4px rather than edge-to-edge. Plan self-review passed: full spec coverage
  (every Components-section function has a task), no placeholders, and a
  cross-checked-against-the-actual-codebase pass confirming `Element`'s dataclass
  defaults, `write_cuig`'s signature, and `harness.compare`'s section-index ordering
  all match what the plan's own test code assumes. **Next**: execute the plan.
- 2026-09-08: **Multi-resolution reflow — generalized from a one-shot,
  resolution-add-only operation into a standalone `reflow_file` callable any time a
  resolution's block is missing elements that exist elsewhere in the file.** User
  pushed back on the spec's implicit assumption that reflow only ever happens at the
  moment a resolution is added — real projects gain new controls on existing pages long
  after resolutions are set up, and those controls hit the identical "other resolutions
  have no CSS rule for this element" gap. Resolved two design forks via clarifying
  questions: (1) when new controls are added to a page that already has fitted content
  in other resolutions, the user wants to be **prompted** each time (not a fixed
  policy) — leave the existing controls alone and fit just the new ones, or re-fit the
  whole page — so `reflow_file` gained a `mode` parameter (`pin_existing` default vs.
  `full_refit`) instead of one hardcoded behavior; (2) in `pin_existing` mode, new
  elements are only guaranteed not to overlap *each other* — guaranteeing they avoid
  the pinned pre-existing elements too would need real 2D obstacle-avoidance placement,
  which the user agreed to explicitly rule out of scope in favor of a best-effort fit
  plus a flagged warning (`check_overlaps`) for manual nudging in Construct. New
  components added to the spec: `find_new_elements` (id-set diff between source and
  target blocks) and `check_overlaps` (pairwise AABB check for the warning surface);
  `reflow_file` now returns a `ReflowResult` carrying `warnings` instead of assuming a
  silently-clean result. `add_resolutions_to_project` (Trigger 1) turns out to be the
  degenerate case of `pin_existing` with zero pinned elements, so it needed no special
  casing — one mechanism now covers both the resolution-add trigger and the new
  add-elements-to-an-existing-multi-resolution-page trigger. Full rewrite at
  `docs/superpowers/specs/2026-09-08-multi-resolution-reflow-design.md` (Problem,
  Scope, Algorithm, Integration, Components, Error handling, and Testing sections all
  updated). **Next**: user reviews the rewritten spec, then the implementation plan.
- 2026-09-08: **Multi-resolution reflow — fit-strategy redesigned to a 3-tier fallback
  (move, then compact whitespace, then scale), at the user's direction.** The
  just-approved spec (previous entry below) always scaled first and only repositioned
  as a last-resort clamp; the user asked for the opposite priority — try repositioning
  first, then reducing whitespace, and only scale down if neither works. Clarified two
  ambiguities before rewriting: (1) the "move" tier must be collision-aware, not
  independent per-element clamping — resolved by proving that rigid group translation
  (tier 1) plus order-preserving, never-negative-gap compaction (tiers 2/3) can never
  introduce a new overlap, since two elements non-overlapping in the source are always
  disjoint on at least one axis and that disjointness survives any monotonic shrink; (2)
  whitespace reduction preserves element order (no bin-packing/rearrangement) and the
  final scale is one uniform factor per axis, both per the user's explicit choice. User
  then set the minimum gap floor at 4px, applied through both tier 2 (compaction) and
  tier 3 (scale-down reserves `(n-1)*4px` for mandatory gaps before scaling the
  remainder) rather than allowing gaps to reach 0. Spec rewritten in place at
  `docs/superpowers/specs/2026-09-08-multi-resolution-reflow-design.md` (Algorithm,
  Components, Error handling, and Testing sections all updated; new insufficient-room
  edge case documented for when even 4px floor gaps don't fit the element count).
  **Next**: user reviews the rewritten spec, then the implementation plan.
- 2026-09-08: **Multi-resolution reflow — design spec written and approved.** Covers the
  gap left by Phase 5's first slice: `add_resolutions_to_project` updates the `.cuip`'s
  resolution list but does nothing to existing pages'/widgets' component
  positions/sizes, so content near the edge of an original canvas can land off-canvas on
  a newly-added smaller/differently-oriented resolution. Design: parse each file's
  `99999px` catch-all CSS block (the confirmed single source of truth for current
  position/size) into per-element `{left, top, width, height, extra_vars}`, scale
  per-axis from a chosen source resolution (same-orientation primary, or the other
  orientation's primary for the bootstrap case), then clamp any still-off-canvas element
  by repositioning only (never resizing). Emits one new `@media` block per newly-added
  resolution; the existing catch-all block is untouched. New components planned:
  `layout.py::parse_position_rules`/`build_reflow_block` (extending, not replacing, the
  existing single-element device-block logic) and a new `generator/reflow.py`
  (`reflow_file`, `pick_primary`, `choose_source_resolution`), wired into
  `add_resolutions_to_project`. Explicitly out of scope: resolution removal,
  shrink-to-fit, and reflowing hand-authored non-generator CSS. Full spec at
  `docs/superpowers/specs/2026-09-08-multi-resolution-reflow-design.md`. **Next**: write
  the implementation plan.
- 2026-09-08: **Phase 9 (assets) pulled forward — local image import DONE.** User was
  checking the image-button variant in the generated project and pointed out it couldn't
  really be called verified without an actual image asset imported and referenced —
  correctly identified that no asset-import code existed yet (it's Phase 9, unstarted).
  Found the real reference project's image-type button already references a specific real
  asset (`C:\Solutions\ClaudeSamples\Components\assets\CrimsonSilk.cuia`/`.jpg`, Id
  `498f8b9e-eade-4d9d-9475-49bb03d4324b`) — about as strong a ground truth as this project
  has had. Confirmed the `.cuia` format (`{FileMetadata}` + `{AssetAttributes}`, the
  latter a plain `Dictionary<string,string>` whose real key-insertion order — Id, Name,
  SourceUri, AspectRatio, AssetSourceType, Username, Password — was found in
  `SaveAssetMetadataHandler.cs`, confirmed 7/7 against the real file), that
  `MinimumProjectApp=""` for assets specifically (not a typo, a genuinely different
  default than every other file type), and that `AspectRatio` (`width/height` as a
  double) computed independently in Python via Pillow matches C#'s ImageSharp-computed
  value byte-for-byte (`1.588550983899821`) for the real file. Also confirmed no new code
  was needed to reference an asset from a button — `ch5_button.py`'s existing `asset_id`
  param already does the right thing (the real button has no static `iconurl` attribute at
  all; Construct resolves it dynamically from `assetid`). Built `generator/assets.py`
  (`import_asset`), verified via `phase9_assets_smoke_test.py` (imports the real
  CrimsonSilk.jpg, diffs the generated `.cuia` against the real one — exact match) plus a
  new dependency on Pillow. Imported the same real asset into the on-disk verification
  project and rewired `ButtonVariants.cuig`'s image button to use it, for the user to
  check in Construct. Full writeup in `docs/architecture/09-assets.md`.
- 2026-09-08: **Phase 5 — device/resolution catalog + add-resolutions-to-a-project DONE.**
  User asked whether the rest of the components or resolutions should come first;
  recommended resolutions first since `generator/layout.py` (built in Phase 4) is now a
  shared foundation every future component will call, and doing Phase 5 while only one
  component type exists avoids rework across many later. User agreed, then chose the
  smaller "catalog + add resolution" slice over bundling in full reflow math when asked.
  Research resolved both Phase 2-flagged open questions: (1) `UiEditorResolutionDao.cs`
  vs. inline `.cuip` `{DeviceResolutionSource}` are NOT overlapping — the DAO reads a
  global, not-per-project catalog file, the `.cuip` section stores which catalog entries a
  project has selected; (2) `DisplayOrientation` enum confirmed
  (`None=0,Landscape=1,Portrait=2,Both=3`), serialized as int inside `.cuip` but as a
  string in the global catalog file (two different JSON contexts for the same enum).
  Found the real catalog on disk (`%APPDATA%\crestron-construct\AppStorage\data\ui\
  resolution\resolutionData.json`, 74 entries) and confirmed/corrected a previously
  fabricated example in `project.py`'s own `__main__` block: no "TSW-1070 Portrait" exists
  in the real catalog (TSW-1070 is landscape-only hardware); TST-1080 genuinely supports
  both orientations and is used instead. Built `generator/devices.py` (catalog reader —
  found and worked around a real collision: this machine's own custom-resolutions file has
  a personal entry also named "TSW-1070", so `include_custom` defaults to False; also
  normalizes an orientation int-vs-string inconsistency between the two catalog files) and
  `generator/project.py::read_cuip`/`add_resolutions_to_project` (extends an existing
  project's resolutions, handles both the "already has resolutions" and "starts with zero"
  cases, the latter correctly inserting `DeviceResolutionIds` at the confirmed key
  position rather than just appending). Factored `override_attr` out of `ch5_button.py`
  into `toml_util.py` since `project.py` needed the identical operation. All verified via
  `generator/_test_output/phase5_smoke_test.py` (harness round-trip + structural checks;
  no real multi-resolution `.cuip` exists in the reference project to diff against, so
  verified against `build_project_attributes`' own confirmed shape instead, same standard
  used for Phase 2). Full writeup in `docs/architecture/05-resolutions.md`. Full
  multi-resolution reflow (the actual CSS math for non-primary resolutions) deliberately
  NOT built this slice — flagged as a separate, bigger follow-up.
- 2026-09-08: **`--ch5-button--regular-{width,height}` CSS var bug found and fixed.** User
  checked again after the `size="custom"` fix and the adorner still mismatched the actual
  button, asking directly: "are you 100% sure the CSS values match the property grid or
  vice versa and the TOML as well? check the sample project to be sure." Re-verified —
  property grid/CSS/TOML DID all agree; the remaining issue was that `ch5-button`'s own
  shadow-DOM rendering reads its visual size from CSS custom properties, not the plain
  outer `width`/`height` the adorner uses. Found the exact mechanism in
  `component-context.json`'s `classToVariableMapping` "idSelector" entry (already read
  once for the sync-attribute work, but this entry unused until now): `width` ->
  `--ch5-button--regular-width`, `height` -> `--ch5-button--regular-height` (swapped for
  vertical orientation, unconfirmed — no vertical button in the reference project). New
  `ch5_button.py::button_size_css_vars` derives these from that schema entry; wired into
  `layout.py::build_position_css`'s new `extra_vars` param, written in both `@media`
  blocks. Verified value-for-value against real ButtonWithIcon (190x58 ->
  `--ch5-button--regular-width: 190px`/`-height: 58px`, exact match). Rebuilt
  `MainPage.cuig`/`ButtonVariants.cuig` again for the user to re-check. Full writeup in
  `docs/architecture/04-ch5-schema.md`.
- 2026-09-08: **`size="custom"` bug found and fixed.** User checked the CSS fix in
  Construct and caught a follow-on bug: the canvas selection adorner was visibly larger
  than the button's actual rendered size. Cause: `size="regular"` (the raw SDK default,
  used verbatim until now) renders the button at its theme's fixed preset dimensions,
  ignoring whatever explicit width/height CSS is written — didn't show up in the earlier
  "112/112 exact match" claim only because Button1's chosen size (84x42) happened to equal
  that preset exactly. Fixed at the user's direction: `size` is now always forced to
  `"custom"` in `ch5_button.py::build_default_button_attributes` (`ccid_lastSizeSelected`
  left untouched, a separate "restore" bookkeeping field, confirmed distinct from `size`
  in the real file's own resized instances) — also consistent with every real button
  instance in the reference file that had actually been resized. Smoke test's plain-button
  comparison updated to exclude `size` from the exact-match assertion (documented as
  intentional). Rebuilt `MainPage.cuig`/`ButtonVariants.cuig` again for the user to
  re-check. Full writeup in `docs/architecture/04-ch5-schema.md`.
- 2026-09-08: **Position/size CSS bug found and fixed.** User checked the icon/checkbox
  button variants in Construct and reported "size can never be auto, even when you are
  using a fixed size" — the Properties panel showed Left/Top/Width/Height as "auto" for
  every generated button. Root cause: `build_default_button_element` never wrote any
  `{Css}` rule at all, only `[[Elements]]` TOML attributes — position/size lives entirely
  in CSS. Fixed with new `generator/layout.py::build_position_css`, confirmed against real
  Button1's CSS rule in `Component - Button.cuig` (two `@media` blocks: 99999px catch-all
  + device-specific landscape breakpoint; theme-selector child rule sourced from the SDK's
  own `componentProperties.customThemeRequiredSelectors`, schema-driven not hardcoded).
  While fixing this, **also found and fixed a related Phase 3 gap**: widget's default CSS
  (`page.py::default_widget_html_css`) always used a hardcoded 2560x1440 "no devices yet"
  fallback breakpoint, flagged unconfirmed at the time — now confirmed wrong by direct
  inspection of a real widget in a project WITH a device defined (`Widget.cuiw`, which
  contains a button): it uses the real device breakpoint, not the fallback. Both now share
  one confirmed formula (`layout.py::landscape_media_query`, matched against two
  independent real files at two different widths/heights). `x`/`y`/`width`/`height`/
  `z_index`/`resolution` are now required parameters on `build_default_button_element`
  (matches the widget function's existing "explicit size, no invented default"
  precedent). All Phase 3/4 smoke tests updated with position-CSS regression checks (`"auto"
  not in css`). Rebuilt `MyWidget.cuiw`/`MainPage.cuig`/`ButtonVariants.cuig` in the real
  on-disk verification project with correct CSS for the user to re-check. Full writeup in
  `docs/architecture/04-ch5-schema.md`.
- 2026-09-08: **Phase 4 — button icon/image/checkbox variants added.** User confirmed the
  plain button looked correct on the canvas in Construct, then asked to cover the
  variants. Turned out nearly free once the sync-attribute derivation existed:
  `build_sync_attributes` already selects sectors purely from `showWhen` matching on
  current attribute values, so a variant is just different input values, not new logic.
  **Icon** (`icon_class`/`icon_library` params): exact match against the real
  "ButtonWithIcon" instance, excluding 2 confirmed UI-state artifacts (`oldID`,
  `ccid_customSizeSet`) and 1 independent `size` customization. **Image**
  (`image_icon_type="imageasset"`): found and deliberately did NOT reproduce a real
  discrepancy — the reference file's image-type button also carries a stale, unused Icon
  sync sector (16 keys), traced to `setSyncData`'s "only add, never remove" attribute
  guard combined with that specific instance's edit history (authored as icon-type, later
  switched to image-type); a single fresh "add as image button" would never produce that,
  so the generator emits the clean result instead (sanity-checked: exactly 16 new
  `imagesector` keys). **Checkbox** (`checkbox_show=True`): same mechanism, but no real
  checkbox-enabled button exists anywhere in the reference project, so this one is
  sanity-checked only, not confirmed — flagged as needing a real reference file the same
  way the user added one for background-color in Phase 3, if/when it matters. All 4
  configurations round-trip clean in `generator/_test_output/phase4_smoke_test.py`.
  `docs/architecture/04-ch5-schema.md` updated with the full derivation writeup.
- 2026-09-08: **Phase 4 (add a CH5 component) — "Ch5 Button", default configuration,
  DONE.** User asked "if you do not address the 90 additional attributes how can I fully
  test component integration?" after an initial pass found a real button carries ~112
  attributes from 3 different sources, not 1 — pushed the research further rather than
  shipping a partial slice. Findings: `schema.json` (the ch5-button web component's own 60
  runtime attributes) is NOT what a freshly-dropped button's `[Elements.Attributes]` looks
  like; `component-context.json`'s `ch5-button.defaults.attributes` (24 keys) IS the real
  base payload (confirmed order-for-order against a real button); the ~80
  `ccid_sync_{state}_{sector}sector_{property}` "Advanced Style Manager" attributes are
  generated by **client-side TypeScript**
  (`pd-ch5-components/mixins/common/commonButtonTraitsMixins.ts::setSyncData`, real source
  present in `C:\Git\CCIDE`, not compiled/obfuscated) — traced the exact algorithm and
  found its authoritative data source is `sass-schema.json`'s per-tag sector list (NOT
  `component-context.json`'s `classToVariableMapping`, which has a different, over-broad
  property shape). Built `generator/sdk.py` (locates and reads an installed SDK's
  `schema.json`/`component-context.json`/`sass-schema.json` from
  `%APPDATA%\crestron-construct\AppStorage\data\ui\sdk\<version>\data\`) and
  `generator/ch5_button.py` (`build_default_button_element` /
  `build_sync_attributes` — the sync-attribute derivation is written generically off
  `sass-schema.json`'s shape, not button-specific, so should carry over to other component
  types). Verified: `generator/_test_output/phase4_smoke_test.py` — page-with-button
  round-trips byte-identical, AND the generated button's 112 attributes match a real
  Construct-authored plain button (`Component - Button.cuig`'s "Button1", id `i9nb`)
  **exactly** — same 112 keys in the same order, 0 value mismatches. Written up in
  `docs/architecture/04-ch5-schema.md` (includes the full derivation + flagged gaps: only
  the plain/default button variant is covered, not icon/image/checkbox/advanced-mode
  buttons; common wiring keys' universality across component types is unconfirmed beyond
  button). `01-index.md` updated. Also generated one into the real on-disk verification
  project (`C:\Solutions\ClaudeGenTest\GenTestProject\MainPage.cuig`) for the user to
  check in Construct.
- 2026-09-08: **End-to-end manual verification project generated in Construct's own
  Solutions folder**, at the user's request, to sanity-check Phases 1-3 outside the
  harness before starting Phase 4: `C:\Solutions\ClaudeGenTest\ClaudeGenTest.csln` ->
  project `GenTestProject` (CH5:2.18.0 SDK, light theme, TSW-1070 landscape resolution,
  matching real `Components.cuip` values) -> page `MainPage.cuig` (start page) -> widget
  `MyWidget.cuiw` (400x300) added to the page via the real `<ch5-template>` reference.
  Every step passed `harness/compare.py`'s round-trip check. User confirmed it looks good
  after opening in Construct. User also asked about adding multiple landscape/portrait
  resolutions to a project; deferred to Phase 5 (device catalog / orientation semantics
  are explicitly out of scope until then) at the user's direction, rather than guessing at
  unconfirmed device dimensions.
- 2026-09-03: **Background color verification against user-added reference files.**
  User added `Page with Bkd Color.cuig` / `Widget with Bkd Color.cuiw` to
  `C:\Solutions\ClaudeSamples\Components` specifically to test this. Confirmed
  `DisplayBackgroundColor`/`BackgroundColor` attribute placement was already correct
  (matches source exactly, no fix needed) — but the test **did** catch a real bug:
  `generator/page.py::default_widget_html_css`'s root `widgetContainer` element was
  missing `Name=""`/`Status=""`/`Content=""`/`Draggable=False`/`Copyable=False`, all of
  which `CreateNewWidgetHandler.cs`'s real payload sets explicitly (not null) — fixed
  and now matches the real file's element field-for-field. Also resolved (partially) an
  open question: even with a background color set, a page's `{Html}`/`{Css}` stay
  completely empty — the previously-unexplained `#<id>{background-color:#ffffff;}` rule
  seen on other pages is confirmed **unrelated** to this feature (still don't know what
  it is, but now know it's not this). One new open, non-blocking flag: the widget's
  color value has 8 hex digits (`#1900ffff`) vs. the page's 6 (`#ff0000`) — an alpha
  channel is suspected but its byte order (`RRGGBBAA` vs `AARRGGBB`) is unconfirmed;
  doesn't matter for the generator since color strings are passed through verbatim,
  never interpreted. All of this is now permanent regression coverage in
  `generator/_test_output/phase3_smoke_test.py`, not just a one-off check. Written up
  in `docs/architecture/03-page-widget-creation.md`.
- 2026-09-03: **Phase 3 (create page / create widget / add widget to page) complete.**
  Source-grounded in `PersistenceHelper.CreatePageSource` (two overloads: page vs.
  widget — confirmed the widget overload's 4-key `{PageAttributes}` order matches the
  real `Widget.cuiw` exactly), `CreateNewPageHandler.cs` (brand-new page = zero
  elements, empty Html/Css), `CreateNewWidgetHandler.cs` (brand-new widget's default
  `<div id="...">` + sizing CSS + bare `widgetContainer` element), and
  `AddHtmlViewDependencyHandler.cs` (the page→widget dependency graph is in-memory
  bookkeeping only — the actual persisted proof of "widget added to page" is the
  `<ch5-template>` element itself, confirmed attribute-for-attribute against the real
  `Widget on Page.cuig`, including `templateid = "w" + widget's own Id`). Derived —
  not guessed — the `[[Elements]]` nesting/blank-line rule directly from
  `ElementSource.cs`'s field declaration order: this **structurally explains** v1's
  empirically-discovered "BUG #2" (a widget container's own trailing
  `[Elements.Attributes]` landing after all its children's blocks) as a natural
  consequence of `Components` being declared before `Attributes`, rather than a
  special case to patch around. Built `generator/elements.py` (`Element` +
  `to_toml_lines`), `generator/page.py` (page/widget attribute builders, widget-default
  HTML/CSS, `make_widget_reference`, `write_cuig`). **Found and fixed a real bug while
  building a nested-element test**: the TOML string escaper only handled `\`/`"`, not
  control characters — a raw embedded newline (as in a real `Content = "\n..."` value)
  produced invalid TOML that `tomllib` refused to parse. Fixed by centralizing escaping
  in a new `generator/toml_util.py`, now imported by every writer instead of each
  module keeping its own copy. Verified: empty page/widget both round-trip and match
  real reference-file attribute order exactly; add-widget-to-page's `Ch5 Template`
  element matches the real file's `Type`/`Attributes` key set exactly; a synthetic
  3-level nested tree (`widgetContainer → Button → textnode`) proves the nesting +
  blank-line + escaping rules generally, not just against the one sample file. Written
  up in `docs/architecture/03-page-widget-creation.md`; `01-index.md` updated.
  Remaining known gap (flagged, not blocking): exactly when/how the `widget-container`
  CSS class + checkerboard background get added to a widget after its bare creation
  payload is untraced.
- 2026-09-03: **Phase 2 (create solution / create project) complete.** Source-grounded
  in `UiEditor.Server\Helpers\PersistenceHelper.cs::WriteProject` (exact ordered
  `{ProjectAttributes}` key list + omission rules), `CreateProjectHandler.cs` (defaults:
  SDK auto-detect, theme color, component mode, schema version), and
  `Solution.Server\Dao\SolutionDao.cs`/`AddProjectHandler.cs` for `.csln`. Built
  `generator/project.py` (`build_project_attributes` + `write_cuip`) and
  `generator/solution.py` additions (`write_solution`, `create_solution`,
  `add_project_to_solution`). **User caught a gap**: project creation must support
  *multiple* themes and *multiple* device resolutions selected at once, not just one of
  each — reworked `build_project_attributes` to take `themes: list[str]` (+
  `default_theme`) and `resolutions: list[dict]`, correctly producing comma-joined
  `ProjectThemeIds`/`DeviceResolutionIds` and a multi-entry `{DeviceResolutionSource}`
  JSON array. Verified programmatically (not eyeballed): generated `.cuip`'s
  `{ProjectAttributes}` key **order** matches
  `C:\Solutions\ClaudeSamples\Components\Components.cuip` exactly (17/17 keys), and
  `{DeviceResolutionSource}` entry key set matches exactly. Generated `.csln`'s
  structure matches `ClaudeSamples.csln` exactly (top-level, `_fileMetadata`,
  `_solution`, `_projects[0]` keys). Full end-to-end smoke test
  (`generator/_test_output/phase2_smoke_test.py`: create solution → create project with
  2 themes + 1 resolution → add to solution → re-read and confirm correct folder
  resolution) passed. Also resolved the Phase 1 "active project persisted state" open
  question while reading `CreateSolutionHandler.cs`: Construct has a `.cse` sidecar
  file, but it's Explorer-tree open/closed UI bookkeeping, not a single "active
  project" flag — our own `select_active_project` remains the right owner of that
  concept for this skill. Written up in
  `docs/architecture/02-project-creation.md`; `01-index.md` updated. Remaining known
  gap (flagged, not blocking): the device catalog and `orientation` enum semantics
  are unconfirmed — deferred to Phase 5.
- 2026-09-03: **Phase 1 (Foundation) complete.** Built `harness/compare.py`: a
  section-header splitter for `.cuip`/`.cuig`/`.cuiw`/`.cuia` based on the exact
  header-per-line convention confirmed in every known-good file examined (not yet
  stress-tested against Construct's more permissive in-content header scan — see the
  file's own docstring). Round-trip identity (parse -> reassemble -> byte-compare)
  verified **byte-for-byte across every file** in three real projects: all of
  `C:\Solutions\ClaudeSamples\Components` (23 `.cuig`, 2 `.cuiw`, 1 `.cuip`, 1 `.cuia`),
  all of `C:\Solutions\ClaudeSamples\ClaudeCustomModeProject` (4 `.cuig`, 1 `.cuiw`,
  1 `.cuip`), and all 36 files of v1's
  `ConstructUISkill\samples\CrestronDesignIdeas\BasicTemplate_v1_0_2` — including
  several files well over 400,000 characters, far past the 70,000-char threshold where
  Construct's own `UiEditorPageDao` has to work around a real Nett TOML
  stack-overflow bug (see `docs/architecture/00-overview.md`). Also built
  `generator/solution.py` (`.csln` JSON reader + `select_active_project`, spec §7):
  verified against `C:\Solutions\ClaudeSamples\ClaudeSamples.csln` — correctly resolves
  a named project to its real folder, and correctly refuses to guess when a solution
  has multiple projects and none was named.
- 2026-09-03: Planning session completed and approved. Folder structure created
  (`docs/architecture/`, `harness/`, `generator/`, `skills/`). Two source-code research
  passes over `C:\Git\CCIDE` confirmed the serialization mechanics for `.csln`/`.cuip`/
  `.cuig`/`.cuiw`/`.cuia`/`.cuib`/`.cuic` (DAOs, models, TOML library = Nett 0.15.0,
  JSON via `System.Text.Json`), plus contract generation, CH5 SDK schema
  (`schema.json`/`component-context.json`, machine-readable per-SDK-version), themes,
  fonts, hard buttons, and language files. Findings written to
  `docs/architecture/00-overview.md` and `01-index.md`. Decisions locked: fully
  independent codebase from v1; architecture docs written just-in-time per phase, not
  all upfront; generator language is Python (default, flagged to user given source is
  C#). Full plan on file at `C:\Users\aseferian\.claude\plans\jolly-coalescing-quiche.md`.
