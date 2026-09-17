# Tabbed Layout (Commercial) — Phase 1 shell design spec

Implements the **Tabbed** layout pattern (`ConstructUISkill_DesignSystem.md` §2,
now the project's active layout pattern per the 2026-09-17 scope pivot —
`docs/superpowers/specs/2026-09-16-bento-room-card-design.md`'s pause note).
Reference: `docs/ConstructUISkill_Tabbed-Layout-Spec_Commercial.md` (the user's
framework-agnostic commercial "Boardroom Panel" spec),
`layout_ideas/commercial_splash_page.png`, and
`docs/construct-tabbed-ui-screens-commercial.pdf` (stakeholder-reviewed visual
mockups of all 7 screens/modals — confirms the modal/header/footer structure
below matches; the plan's Camera-modal Position section was adjusted to match
it: dpad centered on top, Zoom Out/Zoom In side by side below, not beside the
dpad — the §1 persona's judgment is to follow an already-reviewed mockup
closely rather than invent a different arrangement).

**Updated 2026-09-17** after the user added a "Generic Specifications" section
to the reference spec, generalizing 3 things this design now reflects:
- **Header is 2 rows**, not 1: top row is room name (upper) with date/time
  directly underneath it (lower) on the left, bottom row is the system-mode
  tab strip, and the company logo spans the FULL header height (both rows),
  anchored right.
- **System modes are caller-configurable**, not a fixed 3-tab set: "System
  Power" is always included by default; Presentation/Video Call/Audio Call
  are included only if the caller asks for them.
- **Footer subsystem buttons are caller-configurable**, not fixed to exactly
  Environment/Audio/Camera: an open list (Environment/Security/Cameras/Audio/
  etc.), each opening the same centered-card modal.
- **Modal geometry confirmed**: asked the user directly since the new
  "always open a full screen modal dialog" footer language conflicted with
  §5's "centered, modal overlay... not a full navigation away" description —
  confirmed centered card over a dimmed backdrop (not truly edge-to-edge);
  "full screen" describes how much visual attention it commands, not its
  literal geometry. `modal.py`'s design (below) is unaffected.

## Problem

The Tabbed layout is structurally new to this generator: a splash landing
screen, a persistent header doubling as tab navigation, per-tab content that
swaps in place, a persistent 3-zone footer, and modal overlays reachable from
the footer. None of these five pieces exist in this generator today —
Header-Content-Footer's header/footer builders don't fit (different content
shape, different navigation model), and this project has never built a modal
or an in-place content-swap region before.

## Scope for this spec (Phase 1)

Per the user's decision to build a proving slice rather than the whole spec
end to end: this phase builds the **navigational shell** — splash→main-panel
transition, tab strip ↔ content-swap wiring, the persistent footer, and one
fully real modal (**Camera**) wired to a real subsystem-control composite —
with the Environment and Audio modals present but empty, and the Power/Video
Call/Audio Call tab bodies present but placeholder. Filling those in is
explicitly deferred to follow-on phases, once this shell is verified working
in Construct.

Also explicitly out of scope for this spec: HVAC and Security subsystem
composites (no layout needs them yet — built when one does, not ahead of
need), and the exact splash-tile→modal/tab wiring logic the control system
runs (this generator's job, per `ConstructUISkill.md` §6, is to expose
correctly-named contract signals, not to program control-system logic).

## Architecture: two new tiers, not one

Per the user's correction mid-design: subsystem controls (Lights, Shades,
HVAC, Security, Camera, Audio) and system-mode content (Presentation, Video
Call, Audio Call, Power) must be generic, layout-independent composites reused
by any layout — not code embedded inside "the Tabbed layout." This adds a
tier between this project's existing primitives and layout patterns:

1. **Primitives** (existing): `ch5_button.py`, `html_div.py`, `component.py`'s
   per-type builders — one CH5 element at a time.
2. **Subsystem-control / system-mode composites** (new tier, this spec adds
   the first one): a self-contained chunk of real functionality, returned as
   `(html, css, elements)` — the same shape `build_component`/`build_html_div`
   already use — so it drops into a modal, a tab body, a page, or a future
   layout's own container unchanged. `generator/camera_control.py` is the
   first of these.
3. **Layout patterns** (existing tier, extended): owns the container/chrome
   and reflow, places tier-2 composites inside. `layout_patterns.py` already
   has this role for Header-Content-Footer; this spec adds
   `build_tabbed_shell`.

## Mechanism grounding

Before designing the shell, the CH5 SDK's `component-context.json` was
checked (`sdk.py::read_sdk(...).component_context`) for a native tab-strip
content-swap component and a native modal/dialog component. `ch5-modal-dialog`,
`ch5-overlay-panel`, and `ch5-triggerview`/`ch5-triggerview-child` all exist in
the underlying CH5 web-component schema with plausible-looking attributes —
but **the user caught that this is not sufficient**: a component must also be
exposed in Construct's own editor to be usable, and none of these three carry
`viewProperties.showOnUI: true` (confirmed directly against the loaded SDK,
cross-checked against zero real authored `.cuig`/`.cuiw` files anywhere in
`C:\Solutions\ClaudeSamples` or `C:\Git\CCIDE` using any of the three — a real
absence, not a search gap). By contrast `ch5-tab-button`, `ch5-dpad`,
`ch5-button-list`, `ch5-slider`, `ch5-toggle`, and `ch5-button` all carry
`showOnUI: true` and have real reference files (`Component - TabButtons.cuig`,
`Component - Keypad - DPad.cuig`, `Component - Lists - Button Lis.cuig`).

Both mechanisms were redesigned around only the confirmed-exposed palette,
collapsing to a mechanism this project has already fully proven — page/widget
`Visibility=Contract` (`ConstructUISkill.md` §5's hard requirement,
`page.py::build_page_attributes`/`make_widget_reference`) — applied to new
shapes rather than inventing anything new:

- **Tab content swap**: each tab's body is an ordinary **widget** added as a
  widget reference to the Main Panel page (exactly like header/footer, just 3
  of them on one page instead of 1), each with its own `Visibility=Contract`
  boolean. CORRECTED (2026-09-17 final review): an earlier version of this
  section claimed `ch5-tab-button`'s `receivestateselectedbutton` was "a
  real, confirmed numeric-join attribute" exposed for the control system to
  drive tab selection — that is factually wrong. `receivestateselectedbutton`
  has no contract metadata in the installed SDK's `component-context.json`
  (confirmed: `contracts.contract_signals(sdk, "ch5-tab-button")` doesn't
  resolve it at all). The REAL, actually contract-capable mechanism — which
  the code already correctly uses — is a per-tab `_Press`/`_Selected` signal
  pair on each individual tab button (`contracts.DEFAULT_SIGNALS["ch5-tab-button"]
  = ("_Press", "_Selected")`), not a single numeric join naming the selected
  index: the generator names each tab's own Press/Selected signals, and the
  control system presses the tab for the mode it wants shown and reads back
  which one is selected, driving the matching content widget's
  `Visibility=Contract` boolean (same division of responsibility as footer
  navigation already has).
- **Modal**: a composite **widget** built entirely from already-proven
  primitives — a full-panel `html-div` backdrop (semi-transparent, high
  z-order — reusing the Room Card overlay's stacking precedent) + a centered
  `html-div` card (rounded corners via `shape.py`, background via
  `palette.py`) holding a title `ch5-text`, an optional close-icon
  `ch5-button`, and the caller-supplied content — plus a **transparent
  full-size `ch5-button` behind the card** for backdrop-tap dismiss, since
  the real `html-div` reference files confirm it has no click/tap signal of
  its own (checked directly: no `sendevent*` attribute anywhere in
  `Component - DIV.cuig`). The widget's own `Visibility=Contract` is the
  open/close signal.

This means Phase 1 needs **no new component-type grounding work** — every
primitive it touches is already confirmed real, either via `showOnUI: true` +
a real reference file, or (for `html-div`) via the file-format grounding
already done before Bento Box.

## Module plan

- **`generator/modal.py`** (new): `build_modal_widget(sdk, *, widget_width,
  widget_height, widget_name, title, card_width, card_height,
  content_builder, closable=True, dismissable=True, active_font="Roboto") ->
  (widget_id, widget_attrs, html, css, elements)`. `widget_width`/
  `widget_height` are the full panel the backdrop covers; `card_width`/
  `card_height` the visible centered dialog box. `content_builder(x, y,
  width, height, z_index) -> (html, css, elements)` is called once, with the
  content area already computed inside the card below its title bar — this
  keeps `modal.py` a one-call primitive (matching `build_footer_widget`/
  `build_header_widget`'s own ergonomics) while staying fully layout- and
  content-agnostic (nothing here knows about Tabbed, Camera, or pages).
  `closable` adds a close-icon `ch5-button`; `dismissable` adds the
  transparent backdrop-tap `ch5-button`. Returns the widget's own id (unlike
  `build_footer_widget`/`build_header_widget`) since a modal may be
  referenced from more than one page (e.g. Environment from both Splash and
  the Main Panel).
- **`generator/camera_control.py`** (new): `build_camera_control(sdk, *,
  x, y, width, height, z_index, resolution, presets, active_font="Roboto")
  -> (html, css, elements)`. Composition: `ch5-dpad` (native center/home
  button via `hidecenterbutton`/`disablecenterbutton`) + separate Zoom
  In/Zoom Out `ch5-button`s + a `ch5-button-list` single-select tile group
  for `presets` (caller-supplied list, per `ConstructUISkill.md` §11 — no
  hardcoded preset names) + a power `ch5-toggle`, laid out within the given
  box. Standalone; no knowledge of modals or pages — matches
  `content_builder`'s expected signature directly.
- **`layout_patterns.py::build_tabbed_shell`** (new): composes —
  - **Splash page**: caller-supplied action tiles (`ch5-button`s;
    `docs/ConstructUISkill_Tabbed-Layout-Spec_Commercial.md`'s new Generic
    Specifications section: the skill must ask whether the project wants
    anything on Splash at all — an empty/omitted tile list is valid),
    `Visibility=Contract` per `ConstructUISkill.md` §5.
  - **Main Panel page, 2-row header**: top row = room-name `ch5-text` (upper)
    + `ch5-datetime` directly underneath it (lower, using its own real fixed
    35px reference height), left-aligned; bottom row = `ch5-tab-button`
    strip over the caller-supplied `system_modes` list ("System Power"
    always included by default, Presentation/Video Call/Audio Call only if
    asked for — not a fixed 3-tab set); company logo (`ch5-image`, square,
    spanning the FULL header height) anchored right. + one tab-content
    widget reference per system mode (placeholder `ch5-text` content this
    phase, each its own `Visibility=Contract`) + the 3-zone footer widget
    (left: one modal-launcher `ch5-button` per caller-supplied subsystem
    name — Environment/Security/Cameras/Audio/etc., an open list per the
    spec's Generic Specifications, not fixed to exactly 3; center: Privacy
    Mute `ch5-toggle`; right: volume `ch5-slider` + mute `ch5-toggle` — a
    new shape, not a reuse of the equal-N-button `_layout_row` footer) +
    one modal widget reference per subsystem via `modal.py` (Camera's
    content is `camera_control.build_camera_control`; every other
    subsystem's modal is built via `modal.py` with empty
    placeholder content this phase).

## Testing approach

Same discipline as every other composite in this project: each new module
gets its own `_test.py`, verified against a real written `.cuig`/`.cuiw` —
byte-identical round-trip, correct `Visibility`/contract-signal attributes
present, right widget count, `closable`/`dismissable` toggling the expected
elements on/off. No new reference-file grounding is needed (see Mechanism
grounding above), so — unlike `html-div` or Room Card — this phase does not
block on the user adding sample files first.

## Error handling

Reuses this project's existing "raise rather than silently overflow"
discipline, not new policy: the tab strip's per-tab width still can't drop
below §5's touch-target floor at the panel's narrowest configured resolution
(already stated as a Tabbed-pattern rule in `ConstructUISkill_DesignSystem.md`
§2); the modal card must fit within the panel's smallest configured
resolution without cropping; the camera preset tile-group's item count is
still subject to §8's density ceiling like any other tile group.

## Explicitly deferred (not this spec)

- Real content for the Power/Video Call/Audio Call tab bodies.
- Real content for the Environment and Audio modals (lights/shades zone rows,
  per-mic rows) — `lights_control.py`/`shades_control.py`/`audio_control.py`
  as their own subsystem composites, same tier as `camera_control.py`.
- The residential Tabbed pass (commercial ships first per the user's
  decision).
- HVAC and Security subsystem composites (no current layout needs them).
- Confirming real device/zone/mic/preset counts and names for any actual
  project — per `ConstructUISkill.md` §11, always caller-supplied, never
  invented by the skill.
