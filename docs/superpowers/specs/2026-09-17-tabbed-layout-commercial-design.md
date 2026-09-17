# Tabbed Layout (Commercial) — Phase 1 shell design spec

Implements the **Tabbed** layout pattern (`ConstructUISkill_DesignSystem.md` §2,
now the project's active layout pattern per the 2026-09-17 scope pivot —
`docs/superpowers/specs/2026-09-16-bento-room-card-design.md`'s pause note).
Reference: `docs/ConstructUISkill_Tabbed-Layout-Spec_Commercial.md` (the user's
framework-agnostic commercial "Boardroom Panel" spec) and
`layout_ideas/commercial_splash_page.png`.

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
  boolean. `ch5-tab-button`'s `receivestateselectedbutton` (a real, confirmed
  numeric-join attribute) is exposed so the control system can drive which
  tab is selected and which widget is shown — the generator wires the named
  signals, the control system decides the mapping (same division of
  responsibility as footer navigation already has).
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

- **`generator/modal.py`** (new): `build_modal_widget(sdk, title, content, *,
  closable=True, dismissable=True, active_font=None) -> (html, css, elements)`
  wrapped as a widget-buildable unit (same shape as `build_html_div` returns,
  so it composes with `page.py`'s existing widget-creation path). `closable`
  controls whether the close-icon button is added; `dismissable` controls
  whether the transparent backdrop-tap button is added. Layout-agnostic —
  nothing here knows about Tabbed, Camera, or Construct pages.
- **`generator/camera_control.py`** (new): `build_camera_control(sdk, presets,
  *, active_font=None) -> (html, css, elements)`. Composition: `ch5-dpad`
  (native center/home button via `hidecenterbutton`/`disablecenterbutton`) +
  separate Zoom In/Zoom Out `ch5-button`s + a `ch5-button-list` single-select
  tile group for `presets` (caller-supplied list, per `ConstructUISkill.md`
  §11 — no hardcoded preset names) + a power `ch5-toggle`. Standalone; no
  knowledge of modals or pages.
- **`layout_patterns.py::build_tabbed_shell`** (new): composes —
  - **Splash page**: 3 action tiles (`ch5-button`s), `Visibility=Contract`
    per `ConstructUISkill.md` §5.
  - **Main Panel page**: header row (room-identity + status `ch5-text`,
    reusing `_layout_header_row`'s fixed/flexible-item split where it fits) +
    `ch5-tab-button` strip (3 tabs, selected-state via the already-built
    `derive_states`) + 3 tab-content widget references (Power/Video
    Call/Audio Call — placeholder `ch5-text` content this phase) + the
    3-zone footer widget (left: 3 modal-launcher `ch5-button`s; center:
    Privacy Mute `ch5-toggle`; right: volume `ch5-slider` + mute
    `ch5-toggle` — a new shape, not a reuse of the equal-N-button
    `_layout_row` footer) + 3 modal widget references via `modal.py`
    (Camera's content is `camera_control.build_camera_control`'s real
    output; Environment/Audio modals built via `modal.py` with empty
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
